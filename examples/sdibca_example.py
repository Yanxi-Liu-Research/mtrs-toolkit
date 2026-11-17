#!/usr/bin/env python3
"""SDI-BCA worked example: staged-delay analysis of a three-stage
BRT -> fare-integration -> LRT programme.

Usage:
    python3 examples/sdibca_example.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sdibca import SDIBCAModel, Stage  # noqa: E402
from mtrs.io import load_stages  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def main():
    stages = [Stage(**row) for row in load_stages(os.path.join(DATA, "sdibca_stages.csv"))]
    model = SDIBCAModel(stages, discount_rate=0.05, horizon=20, base_year=2026)

    delays = {"BRT corridor": 1.0, "LRT extension": 1.0}
    result = model.analyse(delays)

    print("=" * 72)
    print("SDI-BCA staged-delay analysis")
    print("discount rate: %.2f   horizon: %d years   base year: %d"
          % (model.discount_rate, model.horizon, model.base_year))
    print("=" * 72)
    print("\nEffective opening years (base -> with delay):")
    for name, (op_base, op_del) in result.effective_opens.items():
        print("  %-16s %6.2f -> %6.2f" % (name, op_base, op_del))

    print("\nBase case:     NPV = %9.2f   BCR = %.3f"
          % (result.base["npv"], result.base["bcr"]))
    print("Delayed case:  NPV = %9.2f   BCR = %.3f"
          % (result.delayed["npv"], result.delayed["bcr"]))
    print("Delay impact:  dNPV = %9.2f  dBCR = %+.3f"
          % (result.delta_npv, result.delta_bcr))

    print("\nMarginal delay contributions to dNPV:")
    for name, dn in result.marginal.items():
        print("  %-16s %+9.2f" % (name, dn))
    print("Staged-delay interaction term:     %+9.2f" % result.interaction)
    print("\n(interaction = total dNPV - sum of marginal dNPVs; it is non-zero")
    print(" when overlapping delays interact through the stage dependency graph)")


if __name__ == "__main__":
    main()
