#!/usr/bin/env python3
"""Offline SPS migration helpers, Python 3.10+, standard library only.

No network, embedded molecular-weight database, engineering defaults or credentials.
All JSON outputs are conversion evidence, not runnable NexusFlow model files.
"""
import argparse
import bisect
import json
import math
import re
import sys
from pathlib import Path


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected a finite number")
    if not math.isfinite(value):
        raise ValueError(f"{name}: expected a finite number")
    return float(value)


def positive(value, name):
    value = number(value, name)
    if value <= 0:
        raise ValueError(f"{name}: must be positive")
    return value


def gas(data):
    rows = data["components"]
    if not rows:
        raise ValueError("components must not be empty")
    seen, amounts, mass_sum = set(), [], 0.0
    for row in rows:
        name = row["name"]
        if not isinstance(name, str) or not name.strip() or name in seen:
            raise ValueError("component names must be nonempty and unique")
        seen.add(name)
        weight = number(row["mass_weight"], "mass_weight")
        if weight < 0:
            raise ValueError("mass_weight must not be negative")
        mw = positive(row["molecular_weight"], "molecular_weight")
        mass_sum += weight
        amounts.append((name, weight / mw))
    total = positive(math.fsum(v for _, v in amounts), "molar total")
    positive(mass_sum, "mass total")
    return {
        "status": "DATA_CONVERTED_NOT_EXECUTED",
        "mass_weight_sum": mass_sum,
        "mole_fraction": [[name, v / total] for name, v in amounts],
        "mole_percent": [[name, v / total * 100] for name, v in amounts],
    }


def curve(data):
    ref = data["reference"]
    n = number(ref["n_poly"], "n_poly")
    if n <= 1:
        raise ValueError("n_poly must exceed one")
    head = positive(ref["head_m"], "reference head")
    ratio = number(ref["absolute_ratio"], "absolute_ratio")
    if ratio <= 1:
        raise ValueError("reference absolute_ratio must exceed one")
    if not isinstance(ref.get("provenance"), str) or not ref["provenance"].strip():
        raise ValueError("reference.provenance is required")
    a = (n - 1) / n
    b = positive(a * head / math.expm1(a * math.log(ratio)), "effective B")
    rows, seen = [], set()
    for row in data["head_efficiency_flow_speed"]:
        if len(row) != 4:
            raise ValueError("curve row must contain H, efficiency %, actual flow, rpm")
        h, e, q, rpm = [positive(v, "curve value") for v in row]
        if e > 100:
            raise ValueError("polytropic efficiency must be in (0, 100]")
        if (rpm, q) in seen:
            raise ValueError("duplicate flow point at one speed")
        seen.add((rpm, q))
        log_ratio = math.log1p(a * h / b) / a
        pr = math.exp(log_ratio)
        eta = math.expm1(a * log_ratio) / math.expm1(a * log_ratio / (e / 100))
        if not (math.isfinite(pr) and 0 < eta <= 1):
            raise ValueError("invalid converted performance point")
        rows.append([rpm, q, pr, eta])
    if not rows:
        raise ValueError("curve must not be empty")
    rows.sort(key=lambda r: (r[0], r[1]))
    counts = {rpm: sum(r[0] == rpm for r in rows) for rpm in {r[0] for r in rows}}
    if min(counts.values()) < 2:
        raise ValueError("each speed line requires at least two flow points")
    return {
        "status": "APPROXIMATE_FROZEN_REFERENCE_NOT_EXECUTED",
        "warning": "Constant-exponent approximation; not exact real-gas BWRS equivalence.",
        "reference": ref,
        "effective_B_m": b,
        "columns": ["rpm", "inlet_actual_m3_per_h", "absolute_ratio", "efficiency_fraction"],
        "points": rows,
        "speed_lines": [{"rpm": rpm, "count": counts[rpm]} for rpm in sorted(counts)],
    }


def points(values):
    if not values:
        raise ValueError("time series must not be empty")
    result = []
    for p in values:
        if len(p) != 2:
            raise ValueError("point must be [time, value]")
        t, v = number(p[0], "time"), number(p[1], "value")
        if result and t <= result[-1][0]:
            raise ValueError("times must be strictly increasing")
        result.append([t, v])
    return result


def linear_value(series, time, hold_last=False):
    p = points(series)
    t = number(time, "query time")
    if t < p[0][0] or (t > p[-1][0] and not hold_last):
        raise ValueError("query time is outside available data; extrapolation refused")
    if t >= p[-1][0]:
        return p[-1][1]
    hi = bisect.bisect_left([x[0] for x in p], t)
    if p[hi][0] == t:
        return p[hi][1]
    lo = hi - 1
    f = (t - p[lo][0]) / (p[hi][0] - p[lo][0])
    return p[lo][1] + f * (p[hi][1] - p[lo][1])


def ramp_gas(data):
    if data.get("semantics") != "linear_raw_mass_weights_then_normalize":
        raise ValueError("explicit verified mass-ramp semantics required")
    if data.get("after_last") not in ("hold", "error"):
        raise ValueError("after_last must be hold or error")
    base = data["components"]
    gas({"components": base})  # Validate the complete source composition first.
    names = {r["name"] for r in base}
    ramps = data["ramps"]
    if not set(ramps).issubset(names):
        raise ValueError("ramp references an unknown component")
    initial_time = number(data["initial_time_min"], "initial_time_min")
    for name, explicit in ramps.items():
        p = points(explicit)
        if p[0][0] <= initial_time or any(v < 0 for _, v in p):
            raise ValueError("explicit knots must follow initial time and have nonnegative weights")
    output = []
    for time in data["times_min"]:
        time = number(time, "query time")
        if time < initial_time:
            raise ValueError("query time precedes the initial state")
        components = []
        for row in base:
            item = dict(row)
            if row["name"] in ramps:
                p = [[initial_time, row["mass_weight"]], *ramps[row["name"]]]
                item["mass_weight"] = linear_value(p, time, data["after_last"] == "hold")
            components.append(item)
        output.append({"time_min": time, "raw_mass_weights": components, **gas({"components": components})})
    return {"status": "DATA_CONVERTED_NOT_EXECUTED", "semantics": data["semantics"], "samples": output}


def parse_ramps(text):
    """Extract only explicit, numeric RAMP blocks; fail on unsupported RAMP syntax.

    SPS trailing /* comments are treated as end-of-line comments here.
    Non-RAMP instructions are NOT interpreted, a limitation included in output.
    """
    text = re.sub(r"/\*[^\r\n]*", "", text)
    starts = list(re.finditer(r"(?mi)^[ \t]*RAMP[ \t]+", text))
    output = []
    for i, start in enumerate(starts):
        block = text[start.end():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        match = re.match(
            r"(?is)^([A-Z0-9_#.-]+:[A-Z0-9_.-]+)\s*=\s*(.*?)"
            r"\+\s*TIME\s*=\s*(.*?)\+\s*REPEAT\s*=\s*(NO|YES)\b([^\r\n]*)", block)
        if not match or match[4].upper() != "NO" or match[5].strip():
            raise ValueError("unsupported RAMP; require explicit numeric lists and REPEAT=NO")
        def numeric_list(body):
            # Remove continuation markers only at the start of a line.
            body = re.sub(r"(?m)^[ \t]*\+[ \t]*", "", body)
            vals = []
            for token in re.split(r"[\s,]+", body.strip()):
                if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?", token):
                    raise ValueError("RAMP expressions/macros require a source-aware parser")
                vals.append(number(float(re.sub(r"[Dd]", "e", token)), "RAMP value"))
            return vals
        values, times = numeric_list(match[2]), numeric_list(match[3])
        if len(values) != len(times):
            raise ValueError("RAMP value/time counts differ")
        output.append({"target": match[1], "explicit_points": points(list(zip(times, values))), "repeat": False})
    return {"status": "EXPLICIT_RAMPS_ONLY", "ramps": output,
            "limitation": "Other instructions and implicit initial values are not parsed; this is not a complete case import."}


def sample(data):
    series = data["series"]
    continuous, discrete = data["continuous"], data["discrete"]
    names = continuous + discrete
    if not names or len(names) != len(set(names)):
        raise ValueError("declare unique, nonempty continuous/discrete variables")
    ts = []
    for row in series:
        t = number(row["time_min"], "time_min")
        if ts and t <= ts[-1]:
            raise ValueError("times must be strictly increasing")
        if set(row["values"]) != set(names):
            raise ValueError("each row must contain exactly the declared variables")
        for key in continuous:
            number(row["values"][key], key)
        for key in discrete:
            if row["values"][key] is None or isinstance(row["values"][key], (list, dict)):
                raise ValueError("discrete states must be non-null scalar values")
        ts.append(t)
    t = number(data["time_min"], "time_min")
    if not ts or t < ts[0] or t > ts[-1]:
        raise ValueError("no bracketing reference data; extrapolation refused")
    hi = bisect.bisect_left(ts, t)
    lo = hi if ts[hi] == t else hi - 1
    w = 0 if hi == lo else (t - ts[lo]) / (ts[hi] - ts[lo])
    values, unresolved = {}, []
    for key in continuous:
        a, b = series[lo]["values"][key], series[hi]["values"][key]
        values[key] = a + w * (b - a)
    for key in discrete:
        a, b = series[lo]["values"][key], series[hi]["values"][key]
        values[key] = a if a == b else None
        if a != b:
            unresolved.append(key)
    return {"status": "UNRESOLVED_DISCRETE_STATE" if unresolved else "REFERENCE_SAMPLED",
            "time_min": t, "bracket_min": [ts[lo], ts[hi]], "interpolated": lo != hi,
            "interpolation_weight": w, "values": values, "unresolved_states": unresolved}


def topology(data):
    ports = data["ports"]
    declared = data["source_nodes"]
    if len(declared) != len(set(declared)) or not declared:
        raise ValueError("source_nodes must be unique and nonempty")
    parent, source = {}, {}
    for row in ports:
        p = tuple(row["port"])
        if len(p) != 2 or not all(isinstance(x, str) and x for x in p) or p in source:
            raise ValueError("ports must be unique [component_id, port_key] string pairs")
        if row["source_node"] not in declared:
            raise ValueError("port references undeclared source node")
        parent[p], source[p] = p, row["source_node"]
    def find(p):
        while p != parent[p]:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p
    errors = []
    for edge in data["connections"]:
        a, b = tuple(edge["from"]), tuple(edge["to"])
        if a not in parent or b not in parent:
            errors.append({"kind": "unknown_port", "edge": edge})
            continue
        if a == b:
            errors.append({"kind": "self_connection", "edge": edge})
        if source[a] != source[b]:
            errors.append({"kind": "shorted_source_nodes", "edge": edge})
        parent[find(b)] = find(a)
    for node in declared:
        roots = {find(p) for p in parent if source[p] == node}
        if len(roots) != 1:
            errors.append({"kind": "missing_node" if not roots else "split_source_node", "source_node": node})
    return {"status": "TOPOLOGY_OK" if not errors else "TOPOLOGY_FAILED", "errors": errors,
            "port_count": len(ports), "source_node_count": len(declared),
            "connected_components": len({find(p) for p in parent})}


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["gas", "curve", "ramps", "ramp-gas", "sample", "topology"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, help="New output file; existing files are never overwritten")
    args = parser.parse_args()
    try:
        text = args.input.read_text(encoding="utf-8-sig")
        if args.command == "ramps":
            result = parse_ramps(text)
        else:
            data = json.loads(text, object_pairs_hook=unique_object,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON value")))
            result = {"gas": gas, "curve": curve, "ramp-gas": ramp_gas, "sample": sample, "topology": topology}[args.command](data)
        rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        else:
            print(rendered, end="")
        return 2 if result["status"] in ("TOPOLOGY_FAILED", "UNRESOLVED_DISCRETE_STATE") else 0
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        # Do not echo input documents, source paths or values in malformed JSON errors.
        print(f"Conversion failed ({type(exc).__name__}); check the input contract and output path.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
