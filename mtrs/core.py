"""Core MTRS analysis engine.

Given a decision matrix X (scenarios x indicators) and nominal indicator
weights w, the test

  1. computes the base scenario ranking,
  2. draws an ensemble of perturbed (X', w') realisations from each
     active uncertainty source,
  3. decomposes ranking instability into per-source variance shares,
  4. evaluates the three reporting rules (stable / reversal /
     non-transferable).

The stability score S is defined as

    S = 1 - D / D_max

where D is the mean total rank displacement over the ensemble and
D_max = floor(n^2 / 2) is the largest possible displacement between two
permutations of n scenarios. S = 1 means every ensemble member reproduces
the base ranking exactly.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .metrics import kendall_tau_distance, max_displacement, rank_displacement, rank_vector
from .uncertainty import UncertaintySpec, build_generators

#: Default decision-rule thresholds. Pass ``thresholds={...}`` to
#: :class:`MTRSAnalysis` to override.
DEFAULT_THRESHOLDS = {
    #: minimum stability score S for a ranking reportable as stable
    "stability_score": 0.80,
    #: top-rank flip frequency above which a reversal is declared
    "reversal_probability": 0.10,
    #: share of area-structure draws that must fail for non-transferability
    "transfer_failure_rate": 0.30,
    #: per-draw displacement ratio (displacement / max displacement)
    #: that counts as a transfer failure
    "transfer_displacement": 0.25,
}

_VERDICT_DESCRIPTION = {
    "STABLE": "the ranking is stable under the assessed uncertainty and may be reported as is",
    "REVERSAL": "the ranking may reverse; do not report it as stable",
    "NON-TRANSFERABLE": "the ranking is not transferable across metropolitan-area structures "
    "(or does not meet the stability threshold); do not report or transfer it without further analysis",
}


@dataclass
class SourceDecomposition:
    """Per-source ranking-instability statistics."""

    name: str
    draws: int
    mean_displacement: float
    displacement_variance: float
    variance_share: float  #: fraction of total variance explained, 0..1
    mean_tau: float  #: mean Kendall tau distance to the base ranking


@dataclass
class MTRSResult:
    """Outcome of an MTRS run."""

    scenario_names: List[str]
    indicator_names: List[str]
    base_ranking: List[float]
    stability_score: float
    verdict: str
    reversal_probability: float
    transfer_failure_rate: Optional[float]  #: None when not assessed
    decomposition: List[SourceDecomposition]
    rules: dict
    n_draws: int
    seed: int
    thresholds: dict
    active_sources: List[str]


def _normalise_columns(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    """Min-max normalise each indicator column to [0, 1].

    A constant column carries no ranking information and is mapped to
    zero. (``direction`` is applied later, when scores are computed.)
    """
    n = len(matrix)
    m = len(matrix[0])
    out = [[0.0] * m for _ in range(n)]
    for j in range(m):
        col = [matrix[i][j] for i in range(n)]
        lo, hi = min(col), max(col)
        if hi > lo:
            span = hi - lo
            for i in range(n):
                out[i][j] = (matrix[i][j] - lo) / span
    return out


def _scores(normalised: Sequence[Sequence[float]], weights: Sequence[float],
            directions: Sequence[float]) -> List[float]:
    """Weighted sum of indicator values, honouring benefit directions."""
    return [
        sum(w * d * v for w, d, v in zip(weights, directions, row))
        for row in normalised
    ]


def _top_index(scores: Sequence[float]) -> int:
    """Index of the top-ranked scenario (first maximum, no tie breaking)."""
    return max(range(len(scores)), key=lambda i: scores[i])


class MTRSAnalysis:
    """Configure and run the Multivariate Transport Ranking Stability test.

    Parameters
    ----------
    matrix : sequence of sequences of numbers
        Decision matrix, shape (scenarios, indicators). Values must be
        finite.
    scenario_names : sequence of str, optional
        Defaults to ``S1..Sn``.
    indicator_names : sequence of str, optional
        Defaults to ``I1..Im``.
    weights : sequence of numbers, optional
        Nominal indicator weights; non-negative, normalised internally.
        Defaults to equal weights.
    directions : sequence of +1 / -1, optional
        Benefit direction per indicator: +1 higher-better (default),
        -1 lower-better (e.g. cost indicators).
    spec : UncertaintySpec, optional
        Uncertainty-source definitions. An empty spec runs the base
        ranking only.
    thresholds : dict, optional
        Overrides for :data:`DEFAULT_THRESHOLDS`.
    """

    def __init__(
        self,
        matrix: Sequence[Sequence[float]],
        scenario_names: Optional[Sequence[str]] = None,
        indicator_names: Optional[Sequence[str]] = None,
        weights: Optional[Sequence[float]] = None,
        directions: Optional[Sequence[float]] = None,
        spec: Optional[UncertaintySpec] = None,
        thresholds: Optional[dict] = None,
    ):
        if len(matrix) < 2:
            raise ValueError("at least two scenarios are required")
        n = len(matrix)
        m = len(matrix[0])
        for row in matrix:
            if len(row) != m:
                raise ValueError("decision matrix must be rectangular")
            for cell in row:
                if not math.isfinite(float(cell)):
                    raise ValueError("decision matrix values must be finite")
        self.matrix = [[float(c) for c in row] for row in matrix]
        self.scenario_names = list(scenario_names) if scenario_names else [
            "S%d" % (i + 1) for i in range(n)
        ]
        if len(self.scenario_names) != n:
            raise ValueError("scenario_names must match the number of matrix rows")
        self.indicator_names = list(indicator_names) if indicator_names else [
            "I%d" % (j + 1) for j in range(m)
        ]
        if len(self.indicator_names) != m:
            raise ValueError("indicator_names must match the number of matrix columns")

        if weights is None:
            weights = [1.0] * m
        if len(weights) != m:
            raise ValueError("weights must match the number of indicators")
        if any(w < 0 for w in weights) or sum(weights) <= 0:
            raise ValueError("weights must be non-negative and not all zero")
        total = float(sum(weights))
        self.weights = [w / total for w in weights]

        if directions is None:
            directions = [1.0] * m
        if len(directions) != m or any(d not in (1.0, -1.0) for d in directions):
            raise ValueError("directions must be a sequence of +1/-1 matching the indicators")
        self.directions = [float(d) for d in directions]

        self.spec = spec if spec is not None else UncertaintySpec()
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def run(self, n_draws: int = 1000, seed: int = 42) -> MTRSResult:
        """Run the ensemble analysis and return an :class:`MTRSResult`.

        Parameters
        ----------
        n_draws : int
            Ensemble size per active uncertainty source.
        seed : int
            Random seed; identical inputs and seed reproduce identical
            results.
        """
        if n_draws < 1:
            raise ValueError("n_draws must be at least 1")

        rng = random.Random(seed)
        n = len(self.matrix)
        dmax = max_displacement(n)

        normalised = _normalise_columns(self.matrix)
        base_scores = _scores(normalised, self.weights, self.directions)
        base_rank = rank_vector(base_scores)
        base_top = _top_index(base_scores)

        generators = build_generators(self.spec, self.matrix, self.weights)
        th = self.thresholds

        decomposition: List[SourceDecomposition] = []
        all_displacements: List[float] = []
        reversals = 0
        total_draws = 0
        transfer_failures = 0
        transfer_draws = 0

        for name, gen in generators.items():
            displacements: List[float] = []
            taus: List[float] = []
            for _ in range(n_draws):
                matrix_d, weights_d = gen(rng)
                scores_d = _scores(_normalise_columns(matrix_d), weights_d, self.directions)
                rank_d = rank_vector(scores_d)
                disp = rank_displacement(base_rank, rank_d)
                displacements.append(disp)
                taus.append(kendall_tau_distance(base_rank, rank_d))
                if _top_index(scores_d) != base_top:
                    reversals += 1
                total_draws += 1
                if name == "area_structure":
                    transfer_draws += 1
                    if disp / dmax > th["transfer_displacement"]:
                        transfer_failures += 1

            mean = sum(displacements) / len(displacements)
            var = sum((d - mean) ** 2 for d in displacements) / len(displacements)
            decomposition.append(
                SourceDecomposition(
                    name=name,
                    draws=n_draws,
                    mean_displacement=mean,
                    displacement_variance=var,
                    variance_share=0.0,
                    mean_tau=sum(taus) / len(taus),
                )
            )
            all_displacements.extend(displacements)

        total_variance = sum(sd.displacement_variance for sd in decomposition)
        for sd in decomposition:
            sd.variance_share = sd.displacement_variance / total_variance if total_variance > 0 else 0.0

        mean_total_displacement = (
            sum(all_displacements) / len(all_displacements) if all_displacements else 0.0
        )
        stability_score = max(0.0, 1.0 - mean_total_displacement / dmax)
        reversal_probability = reversals / total_draws if total_draws else 0.0
        transfer_failure_rate = (
            transfer_failures / transfer_draws if transfer_draws else None
        )

        reversal_risk = reversal_probability > th["reversal_probability"]
        transfer_assessed = transfer_failure_rate is not None
        transferable = None
        if transfer_assessed:
            transferable = transfer_failure_rate <= th["transfer_failure_rate"]

        if reversal_risk:
            verdict = "REVERSAL"
        elif transfer_assessed and not transferable:
            verdict = "NON-TRANSFERABLE"
        elif stability_score >= th["stability_score"]:
            verdict = "STABLE"
        else:
            # Fails the stability threshold but shows no clear reversal:
            # conservative default per the method's reporting rules.
            verdict = "NON-TRANSFERABLE"

        rules = {
            "reportable_as_stable": (stability_score >= th["stability_score"]) and not reversal_risk,
            "reversal_risk": reversal_risk,
            "transferable_across_areas": transferable,
            "stability_threshold_met": stability_score >= th["stability_score"],
        }

        return MTRSResult(
            scenario_names=list(self.scenario_names),
            indicator_names=list(self.indicator_names),
            base_ranking=base_rank,
            stability_score=stability_score,
            verdict=verdict,
            reversal_probability=reversal_probability,
            transfer_failure_rate=transfer_failure_rate,
            decomposition=decomposition,
            rules=rules,
            n_draws=n_draws,
            seed=seed,
            thresholds=dict(th),
            active_sources=self.spec.active_sources(),
        )
