"""Offline normalized-model checks. No vendor SDK or network access."""
import argparse
import json
import math
import sys
from datetime import datetime


def audit(model):
    issues = []

    def issue(code, item, message, severity="error"):
        issues.append(dict(severity=severity, code=code, id=item, message=message))

    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    if not isinstance(model, dict):
        raise ValueError("Model must be an object")
    nodes = model.get("nodes", [])
    elements = model.get("elements", [])
    boundaries = model.get("boundaries", [])
    if not all(isinstance(a, list) for a in (nodes, elements, boundaries)):
        raise ValueError("nodes/elements/boundaries must be arrays")
    if not nodes:
        issue("EMPTY_MODEL", "", "No physical nodes")
    for key in ("pressure_basis", "flow_basis"):
        choices = {"pressure_basis": {"absolute", "gauge"}, "flow_basis": {"mass", "standard_volume"}}
        if model.get(key) not in choices[key]:
            issue("BASIS", key, "Declare the normalized physical basis")
    if model.get("flow_basis") == "standard_volume":
        base = model.get("standard_conditions", {})
        for key in ("temperature_K", "pressure_Pa_abs", "Z"):
            if not number(base.get(key)) or base[key] <= 0:
                issue("STANDARD_CONDITION", key, "Positive standard condition required")

    def ids(records, group):
        seen = set()
        for row in records:
            if not isinstance(row, dict):
                raise ValueError(group + " records must be objects")
            ident = row.get("id")
            if not isinstance(ident, str) or not ident:
                issue("ID", group, "Nonempty string ID required")
            elif ident in seen:
                issue("DUPLICATE_ID", ident, group)
            else:
                seen.add(ident)
        return seen

    node_ids = ids(nodes, "nodes")
    ids(elements, "elements")
    ids(boundaries, "boundaries")
    graph = {ident: set() for ident in node_ids}
    for row in elements:
        ident = row.get("id", "")
        a, b = row.get("from"), row.get("to")
        if a not in graph or b not in graph:
            issue("ENDPOINT", ident, "Unknown physical endpoint")
            continue
        if a == b:
            issue("SELF_LOOP", ident, "Element endpoints coincide")
        state = row.get("status")
        if state not in ("open", "closed"):
            issue("STATUS", ident, "Explicit open/closed state required")
        if state == "open":
            graph[a].add(b)
            graph[b].add(a)
        if row.get("kind") == "pipe":
            for key in ("length_m", "inner_diameter_mm"):
                if not number(row.get(key)) or row[key] <= 0:
                    issue("GEOMETRY", ident, key + " must be positive")
            if not number(row.get("roughness_mm")) or row["roughness_mm"] < 0:
                issue("GEOMETRY", ident, "roughness_mm must be nonnegative")

    interval = []
    try:
        interval = [datetime.fromisoformat(model[key]) for key in ("start", "end")]
        if interval[1] < interval[0]:
            raise ValueError("end precedes start")
    except (KeyError, TypeError, ValueError):
        issue("INTERVAL", "", "Valid compatible ISO start/end required")
        interval = []
    boundary_types = {}
    for row in boundaries:
        ident = row.get("id", "")
        node, kind = row.get("node"), row.get("type")
        if node not in node_ids:
            issue("BOUNDARY_NODE", ident, "Unknown boundary node")
        if kind not in ("pressure", "flow"):
            issue("BOUNDARY_TYPE", ident, "Expected pressure or flow")
        if node in node_ids:
            boundary_types.setdefault(node, set()).add(kind)
        series = row.get("series", [])
        if not isinstance(series, list) or not series:
            issue("SERIES", ident, "Nonempty explicit series required")
            continue
        times = []
        for point in series:
            if not isinstance(point, list) or len(point) != 2 or not number(point[1]):
                issue("SERIES_POINT", ident, "Expected [ISO time, finite value]")
                continue
            try:
                times.append(datetime.fromisoformat(point[0]))
            except (TypeError, ValueError):
                issue("TIME", ident, "Invalid ISO timestamp")
            if row.get("zero_all_times") and point[1] != 0:
                issue("ZERO_BOUNDARY", ident, "Nonzero value on zero-flow boundary")
        if row.get("zero_all_times") and kind != "flow":
            issue("ZERO_TYPE", ident, "zero_all_times requires flow boundary")
        try:
            if any(a >= b for a, b in zip(times, times[1:])):
                issue("TIME_ORDER", ident, "Times must be unique and increasing")
            if times and interval and (times[0] > interval[0] or times[-1] < interval[1]):
                issue("TIME_COVERAGE", ident, "Series does not cover simulation interval")
        except TypeError:
            issue("TIMEZONE", ident, "Mixed timezone-aware and naive timestamps")
    for node, kinds in boundary_types.items():
        if "pressure" in kinds and "flow" in kinds:
            issue("DUAL_CONSTRAINT", node, "Pressure and flow imposed at same node; review semantics")

    remaining = set(graph)
    components = []
    while remaining:
        pending, found = [min(remaining)], set()
        while pending:
            node = pending.pop()
            if node in found:
                continue
            found.add(node)
            pending.extend(graph[node] - found)
        remaining -= found
        count = sum("pressure" in boundary_types.get(n, set()) for n in found)
        components.append(dict(nodes=sorted(found), pressure_boundary_count=count))
        if count == 0:
            issue("NO_PRESSURE_ANCHOR", min(found), "Review initial inventory, flow balance and solver support", "warning")
    return dict(valid=not any(i["severity"] == "error" for i in issues), issues=issues, components=components)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", help="Normalized JSON; see audit-contract.md")
    args = parser.parse_args()
    try:
        with open(args.model, encoding="utf-8-sig") as handle:
            report = audit(json.load(handle))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
