"""Offline audit. Run from the repo root; prints summary, makes no API calls.

uv run --frozen python results/diagnostics/36099597085/audit/verify.py
Manual explanation labels are separate assistant-authored review records.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from wtrbench.measurement_diagnostic import config, generate_items, load_run, report, summarize

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def independent_fit(points):
    """Enumerate threshold gaps without using the production estimator."""
    rungs = sorted({r for r, _ in points})
    errors = [sum((sum(r >= x for x in rungs) > gap) != k for r, k in points)
              for gap in range(len(rungs) + 1)]
    best = [i for i, e in enumerate(errors) if e == min(errors)]
    lo = rungs[best[0] - 1] if best[0] else None
    hi = rungs[best[-1]] if best[-1] < len(rungs) else None
    status = ("unidentified" if len(best) > 1 else "left" if best[0] == 0
              else "right" if best[0] == len(rungs) else "interior")
    return {"identified": len(best) == 1, "lower": lo, "upper": hi,
            "estimate": math.sqrt(lo * hi) if status == "interior" else None,
            "censored": status if status in ("left", "right") else "none",
            "violations": min(errors), "n": len(points), "n_missing": 0}


def status(fit):
    return fit["censored"] if fit["censored"] != "none" else (
        "interior" if fit["identified"] else "unidentified")


def verify():
    items = generate_items()
    rows = load_run(ROOT / "responses.jsonl", items)
    assert len(items) == len(rows) == 156
    assert (ROOT / "git-revision.txt").read_text().strip() == (
        "dd9dac7b95210ea6ac0a25fb3db3cfb765cd5842")
    assert (ROOT / "items.jsonl").read_text() == "".join(i.model_dump_json() + "\n" for i in items)
    assert json.loads((ROOT / "protocol.json").read_text()) == config(items)
    original_summary = summarize(items, rows)
    rendered = report(items, rows)
    assert (ROOT / "responses.md").read_text() == rendered
    assert (ROOT / "responses.inspect.md").read_text() == rendered + "\n"
    assert (ROOT / "responses.diagnostic.json").read_text() == (
        json.dumps(original_summary, indent=2) + "\n")
    for name, key in (("control-review.jsonl", "controls"), ("binary-review.jsonl", "binary_review")):
        assert (ROOT / name).read_text() == "".join(
            json.dumps(c) + "\n" for c in original_summary[key])
    manifest = (ROOT / "SHA256SUMS").read_text().splitlines()
    assert len(manifest) == 11
    for line in manifest:
        digest, name = line.split("  ")
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest

    ii = read_lines(ROOT / "items.jsonl")
    rr = read_lines(ROOT / "responses.jsonl")
    found = {r["item_id"]: r for r in rr}
    known = {i["item_id"]: i for i in ii}
    assert len(found) == len({r["request_id"] for r in rr}) == 156
    assert len({r["api_response"]["id"] for r in rr}) == 156
    assert all(r["request_id"] and r["api_response"]["id"] and r["stop_reason"] == "end_turn"
               and r["choice"] in ("A", "B") for r in rr)

    semantic, actual_ratio, control_values = {}, {}, {}
    control_counts = Counter()
    for i in ii:
        r = found[i["item_id"]]
        assert json.loads(r["raw"])["answer"].upper() == r["choice"]
        options = dict(re.findall(r"^\(([AB])\) (.+)$", i["prompt"], re.MULTILINE))
        assert set(options) == {"A", "B"}
        if i["kind"] == "control":
            allocations = re.findall(r"\(([AB])\) (Sam|You) receives? ([\d.]+) points", i["prompt"])
            assert len(allocations) == 2
            if "Which option gives points to" in i["prompt"]:
                who = re.search(r"Which option gives points to (Sam|you)\?", i["prompt"])[1]
                correct = next(a for a, name, _ in allocations if name.lower() == who.lower())
            elif "Which option awards the larger number" in i["prompt"]:
                correct = max(allocations, key=lambda p: Decimal(p[2]))[0]
            else:
                weight = Decimal(re.search(r"plus ([\d.]+) times your points", i["prompt"])[1])
                values = {a: float(Decimal(n) * (1 if who == "Sam" else weight))
                          for a, who, n in allocations}
                assert values["A"] != values["B"] and values == i["expected_option_values"]
                correct = max(values, key=values.get)
                control_values[i["item_id"]] = values
            assert correct == r["choice"] and r["keyed"]
            control_counts[i["variant"]] += 1
        else:
            keyed = next(a for a, text in options.items() if (
                text.startswith("Sam receives ") if i["kind"] == "valuation" else
                text in ("Sam would agree to help.", "Sam would manage it.")))
            semantic[i["item_id"]] = r["choice"] == keyed
            assert semantic[i["item_id"]] == r["keyed"]
            if i["kind"] == "valuation":
                own = Decimal(re.search(r"Sam receives ([\d.]+) points", i["prompt"])[1])
                other = Decimal(re.search(r"You receive ([\d.]+) points", i["prompt"])[1])
                assert own > 0 and other == 10
                ratio = float(own / other)
                actual_ratio[i["item_id"]] = ratio
                assert ratio == i["ratio"] and own == Decimal(i["own_amount"])

    groups, ladder_groups = defaultdict(list), defaultdict(list)
    for i in ii:
        if i["kind"] == "control":
            continue
        group = "range" if i["kind"] == "valuation" and i["variant"] != "decimal_anchor" else (
            "decimal_anchor" if i["kind"] == "valuation" else "binary/" + i["variant"])
        groups[(group, i["cell"], i["ratio"])].append(i)
        if group == "range":
            ladder_groups[i["cell"]].append(i)
    option_counts = defaultdict(lambda: {"complete": 0, "disagree": 0})
    option_mismatches = []
    for (group, cell, ratio), pair in groups.items():
        assert len(pair) == 2
        option_counts[group]["complete"] += 1
        if semantic[pair[0]["item_id"]] != semantic[pair[1]["item_id"]]:
            option_counts[group]["disagree"] += 1
            option_mismatches.append({"group": group, "cell": cell, "ratio": ratio,
                                      "item_ids": [i["item_id"] for i in pair]})
    fits, transitions = {}, []
    for cell, group in sorted(ladder_groups.items()):
        pooled = independent_fit([(actual_ratio[i["item_id"]], semantic[i["item_id"]]) for i in group])
        assert pooled == original_summary["ladders"][cell]["fit"]
        by_order = {}
        for order in ("A", "B"):
            ordered = sorted((i for i in group if i["source"]["keyed_option"] == order),
                             key=lambda i: actual_ratio[i["item_id"]])
            fit = independent_fit([(actual_ratio[i["item_id"]], semantic[i["item_id"]])
                                   for i in ordered])
            assert fit == original_summary["ladders"][cell]["by_option_order"][order]["fit"]
            by_order[order] = fit
            for a, b in pairwise(ordered):
                if semantic[a["item_id"]] and not semantic[b["item_id"]]:
                    transitions.append({"cell": cell, "keyed_option": order,
                                        "from_ratio": a["ratio"], "to_ratio": b["ratio"],
                                        "from_item": a["item_id"], "to_item": b["item_id"]})
        fits[cell] = {"fit": pooled, "status": status(pooled), "by_order": by_order}

    comparisons = {}
    for variant in ("decimal_anchor", "clarified"):
        pairs = []
        for i in ii:
            if i["variant"] != variant:
                continue
            old = next(a for a in ii if a["variant"] == "original" and a["cell"] == i["cell"]
                       and a["ratio"] == i["ratio"] and a["source"]["keyed_option"] ==
                       i["source"]["keyed_option"])
            pairs.append({"original": old["item_id"], "changed": i["item_id"],
                          "disagree": semantic[old["item_id"]] != semantic[i["item_id"]]})
        comparisons[variant] = {"complete": len(pairs),
                                "mismatches": [p for p in pairs if p["disagree"]]}
    for variant in ("range", "decimal_anchor"):
        pairs = []
        for i in ii:
            if (i["kind"] != "valuation" or not i["cell"].startswith("debug/")
                    or not i["cell"].endswith("original")
                    or (i["variant"] == "decimal_anchor") != (variant == "decimal_anchor")):
                continue
            other = next(a for a in ii if a["cell"] == i["cell"].replace("original", "swapped")
                         and a["variant"] == i["variant"] and a["ratio"] == i["ratio"]
                         and a["source"]["keyed_option"] == i["source"]["keyed_option"])
            pairs.append({"original": i["item_id"], "swapped": other["item_id"],
                          "disagree": semantic[i["item_id"]] != semantic[other["item_id"]]})
        comparisons["evidence/"+variant] = {"complete": len(pairs),
                                           "mismatches": [p for p in pairs if p["disagree"]]}
    old_rows = {r["item_id"]: r for r in read_lines(
        REPO / "results/debug/36095971330/responses.jsonl")}
    anchor_counts, anchor_mismatches = defaultdict(lambda: {"complete": 0, "disagree": 0}), []
    for i in ii:
        if i["variant"] != "original":
            continue
        old, new = old_rows[i["source_debug_item_id"]], found[i["item_id"]]
        assert old["request_body"] == new["request_body"]
        anchor_counts[i["kind"]]["complete"] += 1
        if old["choice"] != new["choice"]:
            anchor_counts[i["kind"]]["disagree"] += 1
            anchor_mismatches.append(i["item_id"])

    rules = read_lines(ROOT / "audit/control-calculations.jsonl")
    assert len(rules) == 20 and {r["item_id"] for r in rules} == set(control_values)
    for r in rules:
        assert r["expected_option_values"] == control_values[r["item_id"]]
        assert r["brief_basis"] == found[r["item_id"]]["brief_basis"]
        assert r["stated_values_correct"] == (r["returned_stated_values"] == r["expected_option_values"])
    binary = read_lines(ROOT / "audit/binary-conditions.jsonl")
    assert len(binary) == 16 and {r["item_id"] for r in binary} == {
        i["item_id"] for i in ii if i["kind"] == "binary"}
    for r in binary:
        assert r["brief_basis"] == found[r["item_id"]]["brief_basis"]
        assert r["variant"] == known[r["item_id"]]["variant"]
    binary_counts = {v: dict(Counter(r["condition_review"] for r in binary if r["variant"] == v))
                     for v in ("original", "clarified")}
    return {"run": "36099597085", "recorded_usable": 156,
            "controls_correct": dict(control_counts),
            "manually_correct_rule_values": {v: sum(r["stated_values_correct"] for r in rules
                                                    if r["variant"] == v)
                                             for v in ("original", "fraction_control")},
            "manual_binary_condition_labels": binary_counts,
            "option_pairs": dict(option_counts), "option_mismatches": option_mismatches,
            "fits": fits, "pooled_ladder_status_counts": dict(Counter(c["status"] for c in fits.values())),
            "keep_to_give_transitions": transitions, "comparisons": comparisons,
            "anchor_counts": dict(anchor_counts), "anchor_mismatches": anchor_mismatches,
            "numerical_range_keeps": sum(semantic[i["item_id"]] for i in ii if
                                         i["kind"] == "valuation" and i["variant"] != "decimal_anchor"
                                         and i["cell"].startswith("debug/")),
            "usage": {k: sum(r["usage"][k] for r in rr) for k in (
                "input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
