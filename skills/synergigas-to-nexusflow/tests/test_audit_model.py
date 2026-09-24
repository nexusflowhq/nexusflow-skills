"""All fixtures are invented; no field/model data is used."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("audit_model", Path(__file__).resolve().parents[1] / "scripts" / "audit_model.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    times = ["2000-01-01T00:00:00+00:00", "2000-01-01T00:10:00+00:00"]
    return dict(pressure_basis="absolute", flow_basis="mass", start=times[0], end=times[1],
                nodes=[dict(id="n1"), dict(id="n2")],
                elements=[dict(id="p1", kind="pipe", status="open", **{"from": "n1", "to": "n2"}, length_m=100, inner_diameter_mm=80, roughness_mm=0.01)],
                boundaries=[dict(id="b1", node="n1", type="pressure", series=[[t, 0.6] for t in times]),
                            dict(id="b2", node="n2", type="flow", zero_all_times=True, series=[[t, 0] for t in times])])


class AuditTests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(module.audit(fixture())["valid"])

    def test_zero_for_later_times(self):
        m = fixture()
        m["boundaries"][1]["series"][1][1] = 1
        self.assertIn("ZERO_BOUNDARY", [i["code"] for i in module.audit(m)["issues"]])

    def test_closure_splits_network(self):
        m = fixture()
        m["elements"][0]["status"] = "closed"
        report = module.audit(m)
        self.assertEqual(len(report["components"]), 2)
        self.assertIn("NO_PRESSURE_ANCHOR", [i["code"] for i in report["issues"]])

    def test_multiple_pressure_sources_allowed(self):
        m = fixture()
        m["boundaries"][1].update(type="pressure", zero_all_times=False)
        self.assertTrue(module.audit(m)["valid"])

    def test_duplicate_times(self):
        m = fixture()
        m["boundaries"][0]["series"][1][0] = m["start"]
        codes = [i["code"] for i in module.audit(m)["issues"]]
        self.assertIn("TIME_ORDER", codes)
        self.assertIn("TIME_COVERAGE", codes)

    def test_missing_endpoint(self):
        m = fixture()
        m["elements"][0]["to"] = "missing"
        self.assertFalse(module.audit(m)["valid"])

    def test_nonfinite(self):
        m = fixture()
        m["boundaries"][0]["series"][0][1] = float("nan")
        self.assertFalse(module.audit(m)["valid"])

    def test_mixed_timezones(self):
        m = fixture()
        m["boundaries"][0]["series"][1][0] = "2000-01-01T00:10:00"
        self.assertIn("TIMEZONE", [i["code"] for i in module.audit(m)["issues"]])


if __name__ == "__main__":
    unittest.main()
