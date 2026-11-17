"""Discounting helpers for benefit-cost analysis."""

from __future__ import annotations

from typing import Sequence


def npv(cashflows: Sequence[float], rate: float) -> float:
    """Net present value of a cash-flow sequence.

    End-of-year convention: the first entry accrues in year 0 and is not
    discounted; ``PV = sum_t CF_t / (1 + rate)^t``.

    >>> round(npv([100.0], 0.10), 6)
    100.0
    >>> round(npv([0.0, 100.0], 0.10), 6)
    90.909091
    """
    if rate <= -1.0:
        raise ValueError("discount rate must be greater than -1")
    return sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cashflows))


def bcr(benefits: Sequence[float], costs: Sequence[float], rate: float) -> float:
    """Benefit-cost ratio: PV(benefits) / PV(costs).

    Returns ``float("inf")`` when the cost stream has zero present value.
    """
    pv_benefits = npv(benefits, rate)
    pv_costs = npv(costs, rate)
    if pv_costs == 0:
        return float("inf")
    return pv_benefits / pv_costs
