#!/usr/bin/env python3
"""MTRS worked example.

Case A (CSV-driven): five urban transport policy scenarios scored on six
indicators, with all six uncertainty sources active. Demonstrates a full
assessment report and writes the machine-readable report to
``examples/output/mtrs_report.json``.

Cases B and C are small inline examples demonstrating the REVERSAL and
NON-TRANSFERABLE verdicts.

Usage:
    python3 examples/mtrs_example.py [n_draws]
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mtrs import (  # noqa: E402
    MTRSAnalysis,
    UncertaintySpec,
    load_matrix,
    load_vector,
    load_vintages,
    render_json_report,
    render_text_report,
)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def case_a(n_draws):
    """Full CSV-driven assessment with all six uncertainty sources."""
    matrix, scenarios, indicators = load_matrix(os.path.join(DATA, "mtrs_matrix.csv"))
    weights = [w for _, w in load_vector(os.path.join(DATA, "mtrs_weights.csv"))]
    model_a, _, _ = load_matrix(os.path.join(DATA, "mtrs_model_a.csv"))
    model_b, _, _ = load_matrix(os.path.join(DATA, "mtrs_model_b.csv"))
    mapping_a, _, _ = load_matrix(os.path.join(DATA, "mtrs_mapping_a.csv"))
    mapping_b, _, _ = load_matrix(os.path.join(DATA, "mtrs_mapping_b.csv"))
    area_a, _, _ = load_matrix(os.path.join(DATA, "mtrs_area_a.csv"))
    area_b, _, _ = load_matrix(os.path.join(DATA, "mtrs_area_b.csv"))
    vintages, _ = load_vintages(os.path.join(DATA, "mtrs_vintages.csv"))

    # public_cost_per_trip is lower-better; all other indicators are
    # higher-better.
    directions = [1, 1, 1, -1, 1, 1]

    spec = UncertaintySpec(
        parameter={"sigma": 0.06},
        data_year=vintages,
        model_structure=[model_a, model_b],
        policy_mapping=[mapping_a, mapping_b],
        # concentrate the weight ensemble around the nominal weights:
        # Dirichlet concentration = 1 + k * w, so the mode stays at w
        weight={"alpha": [1.0 + 24.0 * w for w in weights]},
        area_structure=[area_a, area_b],
    )

    analysis = MTRSAnalysis(
        matrix,
        scenario_names=scenarios,
        indicator_names=indicators,
        weights=weights,
        directions=directions,
        spec=spec,
    )
    return analysis.run(n_draws=n_draws, seed=20260320)


def case_b(n_draws):
    """Two near-tied front-runners under substantial parameter noise."""
    matrix = [[1.0, 1.0], [1.0, 1.0], [0.3, 0.3]]
    spec = UncertaintySpec(parameter={"sigma": 0.35})
    return MTRSAnalysis(
        matrix, scenario_names=["Plan X", "Plan Y", "Baseline"], spec=spec
    ).run(n_draws=n_draws, seed=7)


def case_c(n_draws):
    """Ranking re-orders under an alternative metropolitan-area structure."""
    matrix = [[3.0], [2.0], [1.0]]
    alt_area = [[3.0], [1.0], [2.0]]
    spec = UncertaintySpec(area_structure=[alt_area])
    return MTRSAnalysis(
        matrix, scenario_names=["Metro", "BRT", "Baseline"], spec=spec
    ).run(n_draws=n_draws, seed=11)


def main():
    n_draws = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

    result = case_a(n_draws)
    print(render_text_report(result, title="MTRS Assessment Report - Case A (CSV demo)"))

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "mtrs_report.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_json_report(result))
    print("\nJSON report written to examples/output/mtrs_report.json\n")

    for label, case in (
        ("Case B (reversal demo)", case_b),
        ("Case C (transferability demo)", case_c),
    ):
        r = case(n_draws)
        print(
            "%s -> verdict: %s  (S=%.3f, reversal_p=%.3f, transfer_fail=%s)"
            % (label, r.verdict, r.stability_score, r.reversal_probability, r.transfer_failure_rate)
        )


if __name__ == "__main__":
    main()
