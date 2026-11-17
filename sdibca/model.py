"""SDI-BCA: Staged-Delay-Inclusive Benefit-Cost Analysis model.

The module models a staged transport programme as a directed graph of
stages. A stage becomes operational only when (a) its own construction
is complete and (b) every prerequisite stage is operational. Delays are
therefore *staged-delay inclusive*: a delay on one stage propagates to
all downstream stages through the dependency graph, and the economic
effect of overlapping delays is captured by the graph rather than by
summing stage-level effects independently.

Cash-flow convention
--------------------
- Years are offsets from ``base_year`` (default 0).
- Construction cost accrues uniformly over the construction period
  (``annual_cost`` per year); fractional years are pro-rated.
- Benefits accrue from the year the stage opens, optionally with a
  linear ramp-up to the full ``annual_benefit`` over ``ramp_up`` years.
  Year buckets use a mid-year approximation for the ramp fraction.
- Discounting uses the end-of-year convention (see :func:`npv`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .metrics import bcr, npv


@dataclass
class Stage:
    """One stage of a transport programme.

    Parameters
    ----------
    name : str
        Unique stage identifier.
    start_year : int
        Planned construction start (offset from the programme base year).
    duration : int
        Construction duration in years.
    annual_cost : float
        Construction cost accrued per year of construction.
    annual_benefit : float
        Annual benefit once the stage is fully operational.
    ramp_up : float, optional
        Years over which benefits ramp up linearly from zero to full.
    handover_lag : float, optional
        Years required between a prerequisite stage opening and this
        stage starting construction (procurement, tendering, testing).
    depends_on : tuple of str, optional
        Names of prerequisite stages; this stage cannot start before
        every prerequisite is operational.
    """

    name: str
    start_year: int
    duration: int
    annual_cost: float
    annual_benefit: float
    ramp_up: float = 0.0
    handover_lag: float = 0.0
    depends_on: Tuple[str, ...] = ()


@dataclass
class SDIBCAResult:
    """Outcome of a base-vs-delayed SDI-BCA comparison."""

    base: dict  #: {"npv", "bcr", "pv_benefits", "pv_costs"} without delays
    delayed: dict  #: same keys, with the delay schedule applied
    delta_npv: float  #: delayed NPV - base NPV
    delta_bcr: float  #: delayed BCR - base BCR
    marginal: dict  #: stage name -> delta NPV if only that stage is delayed
    interaction: float  #: delta_npv - sum(marginal), the staged-delay interaction
    effective_opens: dict  #: stage name -> (base open year, delayed open year)


def _overlap(a: float, b: float, c: float, d: float) -> float:
    """Length of the intersection of intervals [a, b) and [c, d)."""
    return max(0.0, min(b, d) - max(a, c))


class SDIBCAModel:
    """A staged programme with delay propagation through dependencies.

    Parameters
    ----------
    stages : sequence of Stage
        Programme stages; dependency names must refer to other stages and
        the dependency graph must be acyclic.
    discount_rate : float
        Annual discount rate, e.g. 0.05 for 5%.
    horizon : int
        Number of years over which cash flows are evaluated (offsets
        0..horizon-1 from ``base_year``).
    base_year : int, optional
        Calendar year corresponding to offset 0 (reporting convenience).
    """

    def __init__(self, stages: Sequence[Stage], discount_rate: float, horizon: int, base_year: int = 0):
        if not stages:
            raise ValueError("at least one stage is required")
        if discount_rate <= -1.0:
            raise ValueError("discount rate must be greater than -1")
        if horizon <= 0:
            raise ValueError("horizon must be positive")
        self.stages = list(stages)
        self.discount_rate = float(discount_rate)
        self.horizon = int(horizon)
        self.base_year = int(base_year)
        self._index = {s.name: i for i, s in enumerate(self.stages)}
        for i, s in enumerate(self.stages):
            if s.duration <= 0:
                raise ValueError("stage %r: duration must be positive" % s.name)
            if s.annual_cost < 0 or s.annual_benefit < 0:
                raise ValueError("stage %r: costs and benefits must be non-negative" % s.name)
            for dep in s.depends_on:
                if dep not in self._index:
                    raise ValueError("stage %r: unknown dependency %r" % (s.name, dep))
        self._topo = self._topological_order()

    def _topological_order(self) -> List[int]:
        """Kahn's algorithm; raises on circular dependencies."""
        indeg = {i: len(self.stages[i].depends_on) for i in range(len(self.stages))}
        children: Dict[int, List[int]] = {i: [] for i in range(len(self.stages))}
        for i, s in enumerate(self.stages):
            for dep in s.depends_on:
                children[self._index[dep]].append(i)
        order: List[int] = []
        queue = [i for i in range(len(self.stages)) if indeg[i] == 0]
        while queue:
            i = queue.pop(0)
            order.append(i)
            for c in children[i]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    queue.append(c)
        if len(order) != len(self.stages):
            raise ValueError("circular stage dependency")
        return order

    def effective_start(self, stage_idx: int, delays: Dict[str, float]) -> float:
        """Actual construction-start year for a stage under ``delays``.

        ``delays`` maps stage names to delays in years. A stage cannot
        start before every prerequisite is operational, plus its
        ``handover_lag``.
        """
        s = self.stages[stage_idx]
        start = float(s.start_year) + delays.get(s.name, 0.0)
        for dep in s.depends_on:
            dep_idx = self._index[dep]
            dep_open = self.effective_start(dep_idx, delays) + self.stages[dep_idx].duration
            start = max(start, dep_open + s.handover_lag)
        return start

    def effective_opens(self, delays: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Map stage name -> year it becomes operational under ``delays``."""
        delays = dict(delays or {})
        return {
            s.name: self.effective_start(i, delays) + s.duration
            for i, s in enumerate(self.stages)
        }

    def _cashflows(self, delays: Dict[str, float]) -> Tuple[List[float], List[float]]:
        """Build (benefits, costs) year vectors under a delay schedule."""
        benefits = [0.0] * self.horizon
        costs = [0.0] * self.horizon
        for i, s in enumerate(self.stages):
            start = self.effective_start(i, delays)
            open_year = start + s.duration
            self._add_cost(costs, start, s.duration, s.annual_cost)
            self._add_benefit(benefits, open_year, s.annual_benefit, s.ramp_up)
        return benefits, costs

    def _add_cost(self, costs: List[float], start: float, duration: int, annual_cost: float) -> None:
        for y in range(self.horizon):
            frac = _overlap(y, y + 1.0, start, start + duration)
            if frac > 0:
                costs[y] += annual_cost * frac

    def _add_benefit(self, benefits: List[float], open_year: float,
                     annual_benefit: float, ramp_up: float) -> None:
        for y in range(self.horizon):
            frac_year = _overlap(y, y + 1.0, open_year, open_year + 1e9)
            if frac_year <= 0:
                continue
            if ramp_up <= 0:
                ramp_frac = 1.0
            else:
                # mid-year approximation of the linear ramp
                t = (y + 0.5) - open_year
                ramp_frac = min(max(t / ramp_up, 0.0), 1.0)
            benefits[y] += annual_benefit * frac_year * ramp_frac

    def run(self, delays: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Evaluate the programme under a delay schedule.

        Returns ``{"npv", "bcr", "pv_benefits", "pv_costs"}``. With
        ``delays=None`` this is the base (undelayed) case.
        """
        delays = dict(delays or {})
        unknown = set(delays) - set(self._index)
        if unknown:
            raise ValueError("unknown stage(s) in delay schedule: %s" % ", ".join(sorted(unknown)))
        benefits, costs = self._cashflows(delays)
        pv_b = npv(benefits, self.discount_rate)
        pv_c = npv(costs, self.discount_rate)
        return {
            "npv": pv_b - pv_c,
            "bcr": bcr(benefits, costs, self.discount_rate),
            "pv_benefits": pv_b,
            "pv_costs": pv_c,
        }

    def analyse(self, delays: Dict[str, float]) -> SDIBCAResult:
        """Compare the base case with a delayed case, decomposing the NPV
        impact into marginal stage contributions and the staged-delay
        interaction term (the part not attributable to any single delay)."""
        delays = dict(delays or {})
        base = self.run({})
        delayed = self.run(delays)
        marginal = {}
        for name in delays:
            marginal[name] = self.run({name: delays[name]})["npv"] - base["npv"]
        delta_npv = delayed["npv"] - base["npv"]
        interaction = delta_npv - sum(marginal.values())
        opens_base = self.effective_opens({})
        opens_del = self.effective_opens(delays)
        return SDIBCAResult(
            base=base,
            delayed=delayed,
            delta_npv=delta_npv,
            delta_bcr=delayed["bcr"] - base["bcr"],
            marginal=marginal,
            interaction=interaction,
            effective_opens={name: (opens_base[name], opens_del[name]) for name in opens_base},
        )
