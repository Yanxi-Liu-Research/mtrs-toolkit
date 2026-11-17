"""Ensemble generators for the six MTRS uncertainty sources.

The MTRS test treats a scenario ranking as a function of a decision
matrix X (scenarios x indicators) and an indicator-weight vector w. Six
uncertainty sources are modelled as ensembles of perturbed (X, w)
realisations:

    1. model_structure : alternative matrices produced by different model
                         structures (demand model forms, assignment rules).
    2. parameter        : lognormal multiplicative noise on matrix cells.
    3. data_year        : alternative data vintages (per-indicator shifts).
    4. policy_mapping   : alternative scenario-to-indicator mappings.
    5. weight           : indicator weights drawn from a Dirichlet
                         distribution around the nominal weights.
    6. area_structure   : the same scenario set evaluated under
                         alternative metropolitan-area structures
                         (zoning systems, aggregation schemes); drives the
                         cross-area transferability rule.

Every generator is a function of a ``random.Random`` instance, so the
whole analysis is reproducible from a single seed.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Optional, Sequence, Tuple

_SOURCES = (
    "model_structure",
    "parameter",
    "data_year",
    "policy_mapping",
    "weight",
    "area_structure",
)

Matrix = List[List[float]]
Generator = Callable[[random.Random], Tuple[Matrix, List[float]]]


class UncertaintySpec:
    """Container for the six MTRS uncertainty-source definitions.

    A source is *active* when its attribute is not ``None``; inactive
    sources are skipped by :func:`build_generators`.

    Parameters
    ----------
    parameter : dict, optional
        ``{"sigma": float or per-indicator sequence}``. Multiplicative
        lognormal noise with expectation 1: the draw is
        ``exp(N(0, sigma) - sigma^2 / 2)``, so the ensemble is unbiased.
    data_year : list of ``(name, shift_matrix)``, optional
        ``shift_matrix`` is a scenario x indicator matrix of relative
        adjustments (same shape as the base matrix); each draw samples
        one vintage and applies ``cell * (1 + shift_ij)`` elementwise.
        Vintage shifts vary across scenarios, which is what makes data
        vintage affect the ranking (uniform per-indicator shifts would
        cancel in the min-max normalisation).
    model_structure : sequence of matrices, optional
        Alternative decision matrices (same shape as the base matrix).
    policy_mapping : sequence of matrices, optional
        Same shape as the base matrix; entries re-map scenario outcomes
        to indicator values multiplicatively.
    weight : dict, optional
        ``{"alpha": float or per-indicator sequence}`` - Dirichlet
        concentration parameters for the indicator-weight ensemble.
        Larger values concentrate draws around the nominal weights.
    area_structure : sequence of matrices, optional
        Alternative-area matrices (same shape as the base matrix). Used
        exclusively for the cross-area transferability rule.
    """

    def __init__(
        self,
        parameter: Optional[dict] = None,
        data_year: Optional[list] = None,
        model_structure: Optional[Sequence[Matrix]] = None,
        policy_mapping: Optional[Sequence[Matrix]] = None,
        weight: Optional[dict] = None,
        area_structure: Optional[Sequence[Matrix]] = None,
    ):
        self.parameter = parameter
        self.data_year = data_year
        self.model_structure = model_structure
        self.policy_mapping = policy_mapping
        self.weight = weight
        self.area_structure = area_structure

    def active_sources(self) -> List[str]:
        """Names of the uncertainty sources configured in this spec."""
        return [s for s in _SOURCES if getattr(self, s) is not None]


def _shape(matrix: Matrix) -> Tuple[int, int]:
    return len(matrix), len(matrix[0])


def _check_shape(matrix: Matrix, shape: Tuple[int, int], what: str) -> None:
    if len(matrix) != shape[0] or any(len(row) != shape[1] for row in matrix):
        raise ValueError(
            "%s matrix has shape %s, expected %s" % (what, _shape(matrix), shape)
        )


def _as_row(value: float | Sequence[float], width: int) -> List[float]:
    """Normalise a scalar or sequence to a per-indicator list."""
    if isinstance(value, (int, float)):
        return [float(value)] * width
    row = [float(v) for v in value]
    if len(row) != width:
        raise ValueError("expected %d values, got %d" % (width, len(row)))
    return row


def _gen_parameter(base: Matrix, sigma: float | Sequence[float], rng: random.Random) -> Matrix:
    """Lognormal multiplicative noise with expectation 1 per cell."""
    sigmas = _as_row(sigma, len(base[0]))
    out = []
    for row in base:
        out.append(
            [cell * math.exp(rng.gauss(0.0, s) - 0.5 * s * s) for cell, s in zip(row, sigmas)]
        )
    return out


def _gen_data_year(base: Matrix, vintages: Sequence[Tuple[str, Matrix]], rng: random.Random) -> Matrix:
    """Apply a randomly sampled data-vintage shift matrix elementwise.

    Each vintage is a scenario x indicator matrix of relative shifts;
    ``cell * (1 + shift_ij)`` is applied per cell, so a vintage changes
    indicators *differently across scenarios* (a uniform per-indicator
    shift would cancel in the min-max normalisation).
    """
    _, shifts = rng.choice(vintages)
    return [[cell * (1.0 + sh) for cell, sh in zip(row, shift_row)]
            for row, shift_row in zip(base, shifts)]


def _gen_pick(base: Matrix, alternatives: Sequence[Matrix], rng: random.Random) -> Matrix:
    """Pick one alternative matrix (model structure / area structure)."""
    chosen = rng.choice(alternatives)
    return [list(row) for row in chosen]


def _gen_mapping(base: Matrix, mappings: Sequence[Matrix], rng: random.Random) -> Matrix:
    """Apply one alternative scenario-to-indicator mapping elementwise."""
    chosen = rng.choice(mappings)
    return [[c * m for c, m in zip(row, map_row)] for row, map_row in zip(base, chosen)]


def _gen_weight(nominal: List[float], alpha: float | Sequence[float], rng: random.Random) -> List[float]:
    """Draw indicator weights from Dirichlet(alpha).

    ``alpha`` may be a scalar (symmetric Dirichlet) or a per-indicator
    concentration vector. Entries with ``alpha <= 0`` are fixed at zero
    weight (structural exclusion). The nominal vector is returned only in
    the degenerate case where every draw is zero.
    """
    alphas = _as_row(alpha, len(nominal))
    draws = []
    for a in alphas:
        draws.append(0.0 if a <= 0 else rng.gammavariate(a, 1.0))
    total = sum(draws)
    if total <= 0:
        return list(nominal)
    return [d / total for d in draws]


def build_generators(
    spec: UncertaintySpec, base_matrix: Matrix, base_weights: List[float]
) -> Dict[str, Generator]:
    """Return ``{source_name: callable(rng) -> (matrix, weights)}`` for
    every active source in ``spec``."""
    shape = _shape(base_matrix)
    gens: Dict[str, Generator] = {}

    if spec.parameter is not None:
        sigma = spec.parameter["sigma"]
        gens["parameter"] = lambda rng: (_gen_parameter(base_matrix, sigma, rng), list(base_weights))

    if spec.data_year is not None:
        vintages = [tuple(v) for v in spec.data_year]
        gens["data_year"] = lambda rng: (_gen_data_year(base_matrix, vintages, rng), list(base_weights))

    if spec.model_structure is not None:
        for m in spec.model_structure:
            _check_shape(m, shape, "model_structure")
        alternatives = [list(m) for m in spec.model_structure]
        gens["model_structure"] = lambda rng: (_gen_pick(base_matrix, alternatives, rng), list(base_weights))

    if spec.policy_mapping is not None:
        for m in spec.policy_mapping:
            _check_shape(m, shape, "policy_mapping")
        mappings = [list(m) for m in spec.policy_mapping]
        gens["policy_mapping"] = lambda rng: (_gen_mapping(base_matrix, mappings, rng), list(base_weights))

    if spec.weight is not None:
        alpha = spec.weight["alpha"]
        gens["weight"] = lambda rng: (base_matrix, _gen_weight(base_weights, alpha, rng))

    if spec.area_structure is not None:
        for m in spec.area_structure:
            _check_shape(m, shape, "area_structure")
        areas = [list(m) for m in spec.area_structure]
        gens["area_structure"] = lambda rng: (_gen_pick(base_matrix, areas, rng), list(base_weights))

    return gens
