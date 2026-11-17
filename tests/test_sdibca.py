"""Unit tests for the SDI-BCA package."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from sdibca import SDIBCAModel, Stage, bcr, npv  # noqa: E402


def _demo_programme():
    """BRT -> fare integration -> LRT programme used by several tests."""
    return [
        Stage("BRT corridor", 0, 2, annual_cost=40, annual_benefit=35, ramp_up=1.0),
        Stage(
            "Fare integration", 1, 1, annual_cost=8, annual_benefit=10,
            ramp_up=0.5, handover_lag=0.5, depends_on=("BRT corridor",),
        ),
        Stage(
            "LRT extension", 3, 3, annual_cost=55, annual_benefit=60,
            ramp_up=1.5, depends_on=("BRT corridor", "Fare integration"),
        ),
    ]


class TestDiscounting(unittest.TestCase):
    def test_npv_known_value(self):
        self.assertAlmostEqual(npv([100.0], 0.10), 100.0, places=9)
        self.assertAlmostEqual(npv([0.0, 100.0], 0.10), 90.9090909, places=6)

    def test_npv_zero_rate_is_sum(self):
        self.assertAlmostEqual(npv([1.0, 2.0, 3.0], 0.0), 6.0, places=9)

    def test_npv_invalid_rate(self):
        with self.assertRaises(ValueError):
            npv([1.0], -1.5)

    def test_bcr_known_value(self):
        self.assertAlmostEqual(bcr([100.0], [50.0], 0.0), 2.0, places=9)

    def test_bcr_infinite_for_zero_cost(self):
        self.assertEqual(bcr([100.0], [0.0], 0.05), float("inf"))


class TestModel(unittest.TestCase):
    def test_effective_opens_base(self):
        m = SDIBCAModel(_demo_programme(), 0.05, 20)
        opens = m.effective_opens({})
        self.assertAlmostEqual(opens["BRT corridor"], 2.0)
        self.assertAlmostEqual(opens["Fare integration"], 3.5)
        self.assertAlmostEqual(opens["LRT extension"], 6.5)

    def test_delay_propagation(self):
        m = SDIBCAModel(_demo_programme(), 0.05, 20)
        opens = m.effective_opens({"BRT corridor": 1.0})
        self.assertAlmostEqual(opens["BRT corridor"], 3.0)
        self.assertAlmostEqual(opens["Fare integration"], 4.5)
        self.assertAlmostEqual(opens["LRT extension"], 7.5)

    def test_delayed_npv_lower_with_zero_rate_and_truncation(self):
        # With rate 0 discounting effects disappear; horizon truncation
        # makes a delay strictly lose benefits within the horizon.
        m = SDIBCAModel(_demo_programme(), 0.0, 12)
        base = m.run({})
        delayed = m.run({"BRT corridor": 1.0})
        self.assertLess(delayed["npv"], base["npv"])

    def test_staged_delay_interaction_is_nonzero(self):
        m = SDIBCAModel(_demo_programme(), 0.05, 20)
        r = m.analyse({"BRT corridor": 1.0, "LRT extension": 1.0})
        self.assertNotAlmostEqual(r.interaction, 0.0, places=6)
        self.assertAlmostEqual(
            r.delta_npv, sum(r.marginal.values()) + r.interaction, places=9
        )

    def test_analyse_against_manual(self):
        m = SDIBCAModel(_demo_programme(), 0.05, 20)
        r = m.analyse({"Fare integration": 1.0})
        self.assertAlmostEqual(r.delta_npv, r.delayed["npv"] - r.base["npv"], places=9)
        self.assertAlmostEqual(r.delta_bcr, r.delayed["bcr"] - r.base["bcr"], places=9)

    def test_unknown_stage_and_cycle(self):
        m = SDIBCAModel(_demo_programme(), 0.05, 20)
        with self.assertRaises(ValueError):
            m.run({"No such stage": 1.0})
        with self.assertRaises(ValueError):
            SDIBCAModel(
                [
                    Stage("A", 0, 1, 1, 1, depends_on=("B",)),
                    Stage("B", 0, 1, 1, 1, depends_on=("A",)),
                ],
                0.05, 20,
            )
        with self.assertRaises(ValueError):
            SDIBCAModel([Stage("A", 0, 1, 1, 1, depends_on=("missing",))], 0.05, 20)


if __name__ == "__main__":
    unittest.main()
