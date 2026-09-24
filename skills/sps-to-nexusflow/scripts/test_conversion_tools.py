"""Synthetic, offline verification. No engineering case data or network access."""
import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conversion_tools as c


def synthetic_gas():
    # Deliberately rounded synthetic molecular weights, not a property database.
    return {"components": [{"name": "A", "mass_weight": 50, "molecular_weight": 16},
                           {"name": "B", "mass_weight": 50, "molecular_weight": 28}]}


class ConversionTests(unittest.TestCase):
    def test_mass_answer_and_scale_invariance(self):
        data = synthetic_gas()
        answer = c.gas(data)
        self.assertAlmostEqual(answer["mole_fraction"][0][1], 28 / 44)
        for row in data["components"]:
            row["mass_weight"] /= 100
        self.assertAlmostEqual(c.gas(data)["mole_fraction"][0][1], 28 / 44)
        self.assertAlmostEqual(sum(v for _, v in answer["mole_percent"]), 100)

    def test_invalid_compositions(self):
        for field, value in [("mass_weight", -1), ("molecular_weight", 0),
                             ("mass_weight", math.nan), ("mass_weight", True)]:
            data = synthetic_gas()
            data["components"][0][field] = value
            with self.assertRaises(ValueError):
                c.gas(data)
        data = synthetic_gas()
        data["components"][1]["name"] = "A"
        with self.assertRaises(ValueError):
            c.gas(data)

    def test_all_zero_mass(self):
        data = synthetic_gas()
        for row in data["components"]:
            row["mass_weight"] = 0
        with self.assertRaises(ValueError):
            c.gas(data)

    def test_curve_reference_anchor_and_efficiency(self):
        data = {"reference": {"n_poly": 1.3, "head_m": 1000, "absolute_ratio": 1.2,
                               "provenance": "synthetic reference"},
                "head_efficiency_flow_speed": [[1000, 80, 200, 3000], [800, 100, 300, 3000]]}
        result = c.curve(data)
        self.assertAlmostEqual(result["points"][0][2], 1.2)
        self.assertGreater(result["points"][0][3], 0)
        self.assertLess(result["points"][0][3], .8)
        self.assertAlmostEqual(result["points"][1][3], 1)
        data["head_efficiency_flow_speed"].append([700, 80, 200, 3000])
        with self.assertRaises(ValueError):
            c.curve(data)

    def test_curve_requires_physical_reference(self):
        data = {"reference": {"n_poly": 1, "head_m": 1000, "absolute_ratio": 1.2,
                               "provenance": "synthetic"},
                "head_efficiency_flow_speed": [[1000, 80, 200, 3000], [800, 80, 300, 3000]]}
        with self.assertRaises(ValueError):
            c.curve(data)
        data["reference"]["n_poly"] = 1.3
        data["reference"]["absolute_ratio"] = 1
        with self.assertRaises(ValueError):
            c.curve(data)

    def test_curve_near_unity_ratio(self):
        result = c.curve({"reference": {"n_poly": 1.3, "head_m": 1,
                          "absolute_ratio": 1 + 1e-10, "provenance": "synthetic"},
                          "head_efficiency_flow_speed": [[1, 80, 2, 3], [.8, 80, 3, 3]]})
        self.assertAlmostEqual(result["points"][0][3], .8, places=8)

    def test_ramp_implicit_initial_and_mass_before_mole(self):
        data = synthetic_gas()
        data.update({"semantics": "linear_raw_mass_weights_then_normalize", "initial_time_min": 0,
                     "after_last": "hold", "ramps": {"B": [[100, 150]]}, "times_min": [0, 50, 100, 200]})
        samples = c.ramp_gas(data)["samples"]
        expected = (50 / 16) / (50 / 16 + 100 / 28)
        actual = samples[1]["mole_fraction"][0][1]
        self.assertAlmostEqual(actual, expected)
        linear_mole = (samples[0]["mole_fraction"][0][1] + samples[2]["mole_fraction"][0][1]) / 2
        self.assertGreater(abs(actual - linear_mole), .01)
        self.assertEqual(samples[2]["mole_fraction"], samples[3]["mole_fraction"])

    def test_ramp_rejects_implicit_assumptions(self):
        data = synthetic_gas()
        data.update({"initial_time_min": 0, "after_last": "hold", "ramps": {"B": [[100, 150]]}, "times_min": [50]})
        with self.assertRaises(ValueError):
            c.ramp_gas(data)
        data["semantics"] = "linear_raw_mass_weights_then_normalize"
        data["ramps"] = {"B": [[0, 100]]}
        with self.assertRaises(ValueError):
            c.ramp_gas(data)

    def test_extract_numeric_ramps_and_comments(self):
        text = "BEGIN 0\nRAMP FEED_A:SN2=1\n+ 2\n+ TIME=10\n+ 20\n+ REPEAT=NO /* comment\nSET X=1\n"
        result = c.parse_ramps(text)
        self.assertEqual(result["ramps"][0]["explicit_points"], [[10, 1], [20, 2]])
        self.assertEqual(len(c.parse_ramps(text + text.replace('FEED_A', 'FEED_B'))["ramps"]), 2)

    def test_unsupported_ramps_fail_closed(self):
        for text in ["RAMP A:SN2=1\n+ TIME=10\n+ REPEAT=YES", "RAMP A:SN2=1\n+ TIME=2*5\n+ REPEAT=NO",
                     "RAMP A:SN2=1\n+ 2\n+ TIME=10\n+ REPEAT=NO", "RAMP A:SN2=1\n+ TIME=10"]:
            with self.assertRaises(ValueError):
                c.parse_ramps(text)

    def test_no_extrapolation_or_duplicate_time(self):
        self.assertEqual(c.linear_value([[0, 2], [10, 6]], 5), 4)
        for series, time in [([[0, 2], [0, 6]], 0), ([[0, 2], [10, 6]], 11)]:
            with self.assertRaises(ValueError):
                c.linear_value(series, time)

    def test_states_are_not_interpolated(self):
        data = {"continuous": ["pressure"], "discrete": ["state"], "time_min": 5,
                "series": [{"time_min": 0, "values": {"pressure": 2, "state": "Off"}},
                           {"time_min": 10, "values": {"pressure": 4, "state": "On"}}]}
        result = c.sample(data)
        self.assertEqual(result["values"]["pressure"], 3)
        self.assertIsNone(result["values"]["state"])
        self.assertEqual(result["unresolved_states"], ["state"])
        data["time_min"] = 10
        exact = c.sample(data)
        self.assertEqual(exact["values"]["state"], "On")
        self.assertFalse(exact["interpolated"])

    def test_sample_requires_variable_classification(self):
        with self.assertRaises(ValueError):
            c.sample({"continuous": ["p"], "discrete": [], "time_min": 0,
                      "series": [{"time_min": 0, "values": {"p": 1, "mode": 3}}]})

    def test_topology_short_split_and_missing(self):
        data = {"source_nodes": ["N1", "N2"], "ports": [
            {"port": ["source", "0"], "source_node": "N1"},
            {"port": ["pipe", "0"], "source_node": "N1"},
            {"port": ["pipe", "1"], "source_node": "N2"}],
            "connections": [{"from": ["source", "0"], "to": ["pipe", "0"]}]}
        self.assertEqual(c.topology(data)["status"], "TOPOLOGY_OK")
        split = copy.deepcopy(data)
        split["connections"] = []
        self.assertEqual(c.topology(split)["errors"][0]["kind"], "split_source_node")
        data["connections"].append({"from": ["pipe", "0"], "to": ["pipe", "1"]})
        self.assertEqual(c.topology(data)["errors"][0]["kind"], "shorted_source_nodes")
        data["source_nodes"].append("N3")
        self.assertTrue(any(e["kind"] == "missing_node" for e in c.topology(data)["errors"]))

    def test_cli_no_overwrite_and_duplicate_keys(self):
        script = Path(c.__file__).resolve()
        with tempfile.TemporaryDirectory() as folder:
            inp, out = Path(folder) / "input.json", Path(folder) / "output.json"
            inp.write_text(json.dumps(synthetic_gas()), encoding="utf-8")
            command = [sys.executable, str(script), "gas", str(inp), "--output", str(out)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = out.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(out.read_bytes(), before)
            inp.write_text('{"components": [], "components": []}', encoding="utf-8")
            self.assertNotEqual(subprocess.run(command[:-2], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
