"""Unit tests for the MTRS package."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mtrs import (  # noqa: E402
    MTRSAnalysis,
    UncertaintySpec,
    kendall_tau_distance,
    load_matrix,
    max_displacement,
    rank_displacement,
    rank_vector,
    render_json_report,
    render_text_report,
)


class TestRankingMetrics(unittest.TestCase):
    def test_rank_vector_ordering(self):
        self.assertEqual(rank_vector([3.0, 1.0, 2.0]), [1.0, 3.0, 2.0])

    def test_rank_vector_ties(self):
        self.assertEqual(rank_vector([2.0, 2.0, 1.0]), [1.5, 1.5, 3.0])

    def test_kendall_tau_identical(self):
        self.assertEqual(kendall_tau_distance([1, 2, 3], [1, 2, 3]), 0.0)

    def test_kendall_tau_reversal(self):
        self.assertEqual(kendall_tau_distance([1, 2, 3], [3, 2, 1]), 1.0)

    def test_max_displacement(self):
        self.assertEqual(max_displacement(4), 8.0)
        self.assertEqual(max_displacement(5), 12.0)

    def test_rank_displacement_mismatched_length(self):
        with self.assertRaises(ValueError):
            rank_displacement([1, 2], [1, 2, 3])


class TestAnalysis(unittest.TestCase):
    def test_reproducible(self):
        matrix = [[10.0, 8.0], [9.0, 9.0], [4.0, 4.0]]
        spec = UncertaintySpec(parameter={"sigma": 0.1}, weight={"alpha": 2.0})
        a = MTRSAnalysis(matrix, spec=spec).run(n_draws=200, seed=99)
        b = MTRSAnalysis(matrix, spec=spec).run(n_draws=200, seed=99)
        self.assertEqual(a.stability_score, b.stability_score)
        self.assertEqual(a.verdict, b.verdict)
        self.assertEqual(a.reversal_probability, b.reversal_probability)

    def test_stable_verdict(self):
        matrix = [[10.0, 10.0, 10.0], [2.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
        spec = UncertaintySpec(parameter={"sigma": 0.01})
        r = MTRSAnalysis(matrix, spec=spec).run(n_draws=500, seed=1)
        self.assertEqual(r.verdict, "STABLE")
        self.assertGreaterEqual(r.stability_score, 0.8)

    def test_reversal_verdict(self):
        matrix = [[1.0, 1.0], [1.0, 1.0], [0.3, 0.3]]
        spec = UncertaintySpec(parameter={"sigma": 0.35})
        r = MTRSAnalysis(matrix, spec=spec).run(n_draws=2000, seed=7)
        self.assertEqual(r.verdict, "REVERSAL")
        self.assertGreater(r.reversal_probability, 0.1)

    def test_nontransferable_verdict(self):
        matrix = [[3.0], [2.0], [1.0]]
        alt_area = [[3.0], [1.0], [2.0]]
        spec = UncertaintySpec(area_structure=[alt_area])
        r = MTRSAnalysis(matrix, spec=spec).run(n_draws=50, seed=11)
        self.assertEqual(r.verdict, "NON-TRANSFERABLE")
        self.assertEqual(r.transfer_failure_rate, 1.0)
        self.assertEqual(r.reversal_probability, 0.0)

    def test_lower_better_direction(self):
        matrix = [[10.0], [5.0], [20.0]]
        r = MTRSAnalysis(matrix, directions=[-1]).run(n_draws=10, seed=1)
        self.assertEqual(r.base_ranking[1], 1.0)  # lowest cost ranks first
        self.assertEqual(r.base_ranking[2], 3.0)  # highest cost ranks last

    def test_no_active_sources(self):
        matrix = [[3.0, 1.0], [1.0, 3.0], [2.0, 2.0]]
        r = MTRSAnalysis(matrix).run(n_draws=10, seed=1)
        self.assertEqual(r.verdict, "STABLE")
        self.assertEqual(r.stability_score, 1.0)
        self.assertEqual(r.reversal_probability, 0.0)
        self.assertIsNone(r.transfer_failure_rate)

    def test_weights_are_normalised(self):
        matrix = [[10.0, 0.0], [5.0, 5.0], [0.0, 10.0]]
        r1 = MTRSAnalysis(matrix, weights=[1.0, 1.0]).run(n_draws=10, seed=3)
        r2 = MTRSAnalysis(matrix, weights=[7.0, 7.0]).run(n_draws=10, seed=3)
        self.assertEqual(r1.base_ranking, r2.base_ranking)

    def test_decomposition_shares_sum_to_one(self):
        matrix = [[10.0, 8.0, 7.0], [9.0, 9.0, 6.0], [4.0, 4.0, 4.0]]
        spec = UncertaintySpec(
            parameter={"sigma": 0.05},
            data_year=[
                ("v1", [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
                ("v2", [[0.1, -0.1, 0.05], [0.05, 0.1, -0.1], [-0.05, 0.05, 0.1]]),
            ],
            weight={"alpha": 3.0},
        )
        r = MTRSAnalysis(matrix, spec=spec).run(n_draws=300, seed=5)
        total = sum(sd.variance_share for sd in r.decomposition)
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            MTRSAnalysis([[1.0, 2.0]])  # fewer than two scenarios
        with self.assertRaises(ValueError):
            MTRSAnalysis([[1.0, 2.0], [3.0]])  # ragged matrix
        with self.assertRaises(ValueError):
            MTRSAnalysis([[1.0, 2.0], [3.0, 4.0]], weights=[1.0, -1.0])
        with self.assertRaises(ValueError):
            MTRSAnalysis([[1.0, 2.0], [3.0, 4.0]], directions=[1.0, 2.0])


class TestReports(unittest.TestCase):
    def test_json_report_roundtrip(self):
        matrix = [[10.0, 8.0], [9.0, 9.0], [4.0, 4.0]]
        alt_area = [[9.0, 9.0], [10.0, 8.0], [4.0, 4.0]]
        spec = UncertaintySpec(parameter={"sigma": 0.1}, area_structure=[alt_area])
        r = MTRSAnalysis(matrix, spec=spec).run(n_draws=100, seed=2)
        doc = json.loads(render_json_report(r))
        self.assertEqual(doc["model"]["active_sources"], ["parameter", "area_structure"])
        self.assertEqual(len(doc["decomposition"]["sources"]), 2)
        self.assertIn("verdict", doc["stability"])
        text = render_text_report(r)
        self.assertIn(r.verdict, text)


class TestCSVIO(unittest.TestCase):
    def test_load_matrix_roundtrip(self):
        content = "scenario,a,b\nS1,1,2\nS2,3,4\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write(content)
            path = fh.name
        try:
            matrix, rows, cols = load_matrix(path)
            self.assertEqual(rows, ["S1", "S2"])
            self.assertEqual(cols, ["a", "b"])
            self.assertEqual(matrix, [[1.0, 2.0], [3.0, 4.0]])
        finally:
            os.unlink(path)

    def test_load_matrix_ragged(self):
        content = "scenario,a,b\nS1,1\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write(content)
            path = fh.name
        try:
            with self.assertRaises(ValueError):
                load_matrix(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
