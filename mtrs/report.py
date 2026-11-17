"""Report rendering for MTRS results (plain text and JSON)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List

from .core import MTRSResult, _VERDICT_DESCRIPTION

_VERDICT_SYMBOL = {
    "STABLE": "OK",
    "REVERSAL": "REVERSAL",
    "NON-TRANSFERABLE": "NOT TRANSFERABLE",
}


def _bar(share: float, width: int = 40) -> str:
    return "#" * max(1, int(round(share * width))) if share > 0 else "-"


def render_text_report(result: MTRSResult, title: str = "MTRS Assessment Report") -> str:
    """Render a human-readable plain-text assessment report."""
    w = 72
    lines: List[str] = []
    lines.append("=" * w)
    lines.append(title)
    lines.append("generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("seed: %d   draws per source: %d" % (result.seed, result.n_draws))
    lines.append("=" * w)

    lines.append("")
    lines.append("Base ranking (%d scenarios x %d indicators):" % (
        len(result.scenario_names), len(result.indicator_names)))
    order = sorted(range(len(result.scenario_names)),
                   key=lambda i: result.base_ranking[i])
    for i in order:
        lines.append("  rank %-4g  %s" % (result.base_ranking[i], result.scenario_names[i]))

    lines.append("")
    lines.append("Active uncertainty sources: %s" % (
        ", ".join(result.active_sources) if result.active_sources else "(none)"))

    lines.append("")
    lines.append("Stability score S = %.3f" % result.stability_score)
    lines.append("Verdict: %s  [%s]" % (result.verdict, _VERDICT_SYMBOL[result.verdict]))
    lines.append("  %s" % _VERDICT_DESCRIPTION[result.verdict])
    lines.append("  Reversal probability of the top-ranked scenario: %.3f" % result.reversal_probability)
    lines.append("  Cross-area transfer failure rate: %s" % (
        "%.3f" % result.transfer_failure_rate if result.transfer_failure_rate is not None
        else "not assessed (no area_structure source)"))

    lines.append("")
    lines.append("Six-source variance decomposition:")
    lines.append("  %-16s %8s %10s %8s %6s   %s" % (
        "source", "draws", "mean disp", "variance", "share", ""))
    for sd in sorted(result.decomposition, key=lambda s: -s.variance_share):
        lines.append("  %-16s %8d %10.3f %10.4f %6.1f%%  %s" % (
            sd.name, sd.draws, sd.mean_displacement,
            sd.displacement_variance, 100.0 * sd.variance_share,
            _bar(sd.variance_share)))

    lines.append("")
    lines.append("Reporting rules evaluated (thresholds in brackets):")
    th = result.thresholds
    lines.append("  Reportable as stable     : %-5s (S >= %.2f and no reversal risk)"
                 % ("yes" if result.rules["reportable_as_stable"] else "no",
                    th["stability_score"]))
    lines.append("  Reversal risk            : %-5s (p > %.2f)"
                 % ("yes" if result.rules["reversal_risk"] else "no",
                    th["reversal_probability"]))
    lines.append("  Transferable across areas: %-5s (failure rate <= %.2f)"
                 % ("yes" if result.rules["transferable_across_areas"] else
                    ("no" if result.rules["transferable_across_areas"] is not None else "n/a"),
                    th["transfer_failure_rate"]))

    lines.append("")
    lines.append("Notes:")
    lines.append("  - Rank displacement is the sum of absolute rank differences")
    lines.append("    between an ensemble member and the base ranking.")
    lines.append("  - The variance share attributes ranking instability to its")
    lines.append("    six sources; the largest share indicates where additional")
    lines.append("    evidence would most improve ranking confidence.")
    lines.append("=" * w)
    return "\n".join(lines)


def _result_dict(result: MTRSResult) -> Dict:
    return {
        "title": "MTRS Assessment Report",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": {
            "scenarios": list(result.scenario_names),
            "indicators": list(result.indicator_names),
            "active_sources": list(result.active_sources),
            "n_draws": result.n_draws,
            "seed": result.seed,
        },
        "base_ranking": [
            {"scenario": name, "rank": rank}
            for name, rank in zip(result.scenario_names, result.base_ranking)
        ],
        "stability": {
            "score": result.stability_score,
            "verdict": result.verdict,
            "verdict_description": _VERDICT_DESCRIPTION[result.verdict],
            "reversal_probability": result.reversal_probability,
            "transfer_failure_rate": result.transfer_failure_rate,
        },
        "rules": dict(result.rules),
        "decomposition": {
            "total_variance": sum(sd.displacement_variance for sd in result.decomposition),
            "sources": [
                {
                    "source": sd.name,
                    "draws": sd.draws,
                    "mean_displacement": sd.mean_displacement,
                    "displacement_variance": sd.displacement_variance,
                    "variance_share": sd.variance_share,
                    "mean_kendall_tau": sd.mean_tau,
                }
                for sd in result.decomposition
            ],
        },
        "thresholds": dict(result.thresholds),
    }


def render_json_report(result: MTRSResult, indent: int = 2) -> str:
    """Render a machine-readable assessment report as a JSON string."""
    return json.dumps(_result_dict(result), indent=indent)
