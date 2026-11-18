# MTRS / SDI-BCA Toolkit

Reference implementation of two transport policy analysis methods:

- **MTRS** — *Multivariate Transport Ranking Stability test*: assesses how
  stable a ranking of transport policy scenarios is under uncertainty,
  decomposes ranking instability into six sources, and evaluates three
  reporting rules (stable / reversal / non-transferable).
- **SDI-BCA** — *Staged-Delay-Inclusive Benefit-Cost Analysis*: evaluates
  staged transport programmes whose benefit streams depend on the
  operational state of prerequisite stages, so delays propagate through
  the programme's dependency graph.

The MTRS procedure is introduced in Research Report No. 212 (May 2024);
SDI-BCA in Research Report No. 231 (June 2025).

**Project website:** <https://github.com/liuyanxi-2026/mtrs-toolkit/> · **Latest release:** v1.4.0
(2026-03-20) · **License:** MIT

The toolkit is pure Python (standard library only, Python ≥ 3.9) with no
runtime dependencies.

---

## MTRS overview

**Input**

- a decision matrix (scenarios × indicators) scoring policy scenarios on
  transport indicators,
- nominal indicator weights and benefit directions (higher/lower-better),
- an uncertainty specification describing the six uncertainty sources:
  model structure, parameter, data-year, policy-mapping, indicator-weight,
  and metropolitan-area structure.

**Output**

- the base scenario ranking,
- the stability score `S = 1 - D / D_max`, where `D` is the mean total rank
  displacement over the uncertainty ensemble and `D_max = floor(n²/2)` the
  largest possible displacement between two rankings of `n` scenarios,
- a six-source variance decomposition of ranking instability,
- the reversal probability of the top-ranked scenario,
- the cross-area transfer failure rate (from the area-structure source),
- a verdict and a text/JSON report.

**Reporting rules (default thresholds, configurable)**

| Rule | Condition |
| --- | --- |
| Reportable as stable | `S ≥ 0.80` and no reversal risk |
| Reversal risk | top-rank flip probability `> 0.10` |
| Transferable across areas | transfer failure rate `≤ 0.30` |

The headline verdict is `REVERSAL` when reversal risk is detected,
`NON-TRANSFERABLE` when the ranking fails the cross-area check (or the
stability threshold) and `STABLE` otherwise.

## SDI-BCA overview

Stages form a directed dependency graph. A stage opens when its own
construction is complete **and** every prerequisite stage is operational
(plus an optional handover lag). A delay on one stage therefore
propagates to all downstream stages — the *staged-delay inclusive*
property. For a delay schedule, the toolkit reports:

- base and delayed NPV, BCR, PV of benefits and costs,
- `ΔNPV` and `ΔBCR`,
- marginal NPV contribution of each delayed stage,
- the **staged-delay interaction term** — the part of `ΔNPV` not
  attributable to any single delay, capturing overlapping delays that
  interact through the dependency graph.

Cash-flow convention: years are offsets from a base year; construction
cost accrues uniformly over the construction period; benefits accrue from
the opening year with an optional linear ramp-up; discounting is
end-of-year (`PV = Σ CF_t / (1+r)^t`).

## Installation

```bash
git clone https://github.com/liuyanxi-2026/mtrs-toolkit.git
cd mtrs-sdibca-toolkit
pip install .          # optional: the packages also run from the source tree
```

There are no third-party dependencies.

## Quick start

```python
from mtrs import MTRSAnalysis, UncertaintySpec, render_text_report

matrix = [
    [78, 64, 55, 42, 38, 71],
    [69, 58, 61, 30, 44, 64],
    [58, 71, 66, 35, 36, 52],
    [64, 45, 41, 22, 40, 57],
    [40, 40, 40, 26, 30, 40],
]
analysis = MTRSAnalysis(
    matrix,
    scenario_names=["Metro extension", "BRT network",
                    "Road pricing + transit", "TOD intensification", "Baseline"],
    indicator_names=["accessibility", "emissions", "time saving",
                     "cost per trip", "safety", "ridership"],
    weights=[0.20, 0.15, 0.25, 0.15, 0.10, 0.15],
    directions=[1, 1, 1, -1, 1, 1],   # cost per trip is lower-better
    spec=UncertaintySpec(parameter={"sigma": 0.06}),
)
result = analysis.run(n_draws=1000, seed=42)
print(render_text_report(result))
```

```python
from sdibca import SDIBCAModel, Stage

stages = [
    Stage("BRT corridor", 0, 2, annual_cost=40, annual_benefit=35, ramp_up=1.0),
    Stage("Fare integration", 1, 1, annual_cost=8, annual_benefit=10,
          ramp_up=0.5, handover_lag=0.5, depends_on=("BRT corridor",)),
    Stage("LRT extension", 3, 3, annual_cost=55, annual_benefit=60,
          ramp_up=1.5, depends_on=("BRT corridor", "Fare integration")),
]
model = SDIBCAModel(stages, discount_rate=0.05, horizon=20)
result = model.analyse({"BRT corridor": 1.0})
print(result.base["npv"], result.delayed["npv"], result.delta_npv)
```

## Examples and tests

```bash
python3 examples/mtrs_example.py       # full CSV-driven assessment + JSON report
python3 examples/sdibca_example.py     # staged-delay worked example
python3 -m unittest discover -s tests -v
```

The `examples/data/` directory contains the CSV inputs used by the
worked examples (`mtrs/io.py` documents the CSV layouts).

## Package layout

```
mtrs/          MTRS: core engine, uncertainty generators, metrics,
               CSV input helpers, report rendering
sdibca/        SDI-BCA: stage graph, delay propagation, discounting
examples/      worked examples with CSV data
tests/         unit tests (unittest, no external test deps)
```

## Reproducibility

All randomness flows from a single `seed` passed to `MTRSAnalysis.run()`.
Identical inputs and seed reproduce identical results; the example
scripts pin their seeds.

## License

MIT — see [LICENSE](LICENSE).
