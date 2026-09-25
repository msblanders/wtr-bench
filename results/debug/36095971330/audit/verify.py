"""Reproduce the offline audit; no API calls and no writes to original artifacts.

From the repository root: uv run --frozen python results/debug/36095971330/audit/verify.py
Prints the derived summary. Manual explanation assessments are separate data.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from wtrbench.explanation_debug import (
    config,
    control_review,
    debug_score,
    generate_items,
    load_run,
    report,
)

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def cell(source):
    if source["family"] == "attribution":
        return f"boxes/{source['cause']}"
    order = "swapped" if source["choices_swapped"] else "original"
    return f"debug/{source['diagnostic']}/{source['totals']}/{order}"


def verify():
    # Verify the generator, full requests/responses and all original report bytes.
    items = generate_items()
    rows = load_run(ROOT / "responses.jsonl", items)
    assert len(items) == len(rows) == 220
    assert (ROOT / "items.jsonl").read_text() == "".join(
        item.model_dump_json() + "\n" for item in items)
    assert json.loads((ROOT / "protocol.json").read_text()) == config(items)
    assert (ROOT / "git-revision.txt").read_text().strip() == (
        "7388529b9d1ed07cb226dcf0ea0bc338ac318b75")
    rendered = report(items, rows)
    assert (ROOT / "responses.md").read_text() == rendered
    assert (ROOT / "responses.inspect.md").read_text() == rendered + "\n"
    score = debug_score(items, rows)
    assert (ROOT / "responses.score.json").read_text() == score.model_dump_json(indent=2) + "\n"
    assert (ROOT / "control-review.jsonl").read_text() == "".join(
        json.dumps(record) + "\n" for record in control_review(items, rows))
    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ")
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest

    ii = read_lines(ROOT / "items.jsonl")
    rr = read_lines(ROOT / "responses.jsonl")
    found = {r["item_id"]: r for r in rr}
    assert len(found) == len({r["request_id"] for r in rr}) == 220
    assert len({r["api_response"]["id"] for r in rr}) == 220
    assert all(r["request_id"] and r["api_response"]["id"] for r in rr)
    assert all(r["stop_reason"] == "end_turn" and r["choice"] in ("A", "B") for r in rr)
    # Independent control keys from actual prompt text, not case names or saved truth keys.
    controls = Counter()
    rule_values = {}
    for item in ii:
        s, r = item["source"], found[item["item_id"]]
        parsed = json.loads(r["raw"])
        assert parsed["answer"].upper() == r["choice"]
        if item["block"] != "control":
            assert r["keyed"] == (r["choice"] == s["keyed_option"])
            continue
        options = re.findall(r"\(([AB])\) (Sam|You) receives? (\d+) points", item["prompt"])
        assert len(options) == 2
        if s["kind"] == "recipient_lookup":
            who = re.search(r"Which option gives points to (Sam|you)\?", item["prompt"])[1]
            expected = next(label for label, name, _ in options if name.lower() == who.lower())
        elif s["kind"] == "quantity":
            expected = max(options, key=lambda o: int(o[2]))[0]
        else:
            weight = Decimal(re.search(r"plus ([\d.]+) times your points", item["prompt"])[1])
            values = {label: Decimal(amount) * (1 if name == "Sam" else weight)
                      for label, name, amount in options}
            assert values["A"] != values["B"]
            expected = max(values, key=values.get)
            rule_values[item["item_id"]] = {k: float(v) for k, v in values.items()}
        assert expected == r["choice"] and r["keyed"]
        controls[s["kind"]] += 1

    # Explicit grouping and threshold-gap enumeration independent of report helpers.
    pairs, histories, ladders = defaultdict(list), defaultdict(list), defaultdict(list)
    fields = ("family", "task", "cause", "agg_set", "diagnostic", "totals",
              "choices_swapped", "probe", "realized_ratio")
    for item in ii:
        if item["block"] != "debug":
            continue
        s, r = item["source"], found[item["item_id"]]
        pairs[tuple(s[k] for k in fields)].append((item, r))
        if s["probe"] == "p_infer":
            ladders[cell(s)].append((s["realized_ratio"], s["keyed_option"], r["keyed"]))
        if s["family"] == "aggregate":
            histories[(s["diagnostic"], s["totals"], s["realized_ratio"],
                       s["keyed_option"])].append((item, r))
    pair_counts = defaultdict(lambda: {"complete": 0, "disagree": 0})
    disagreements = []
    for values in pairs.values():
        assert len(values) == 2
        values.sort(key=lambda v: v[0]["source"]["keyed_option"])
        s = values[0][0]["source"]
        label = f"{s['family']}/{s['probe']}"
        pair_counts[label]["complete"] += 1
        if values[0][1]["keyed"] != values[1][1]["keyed"]:
            pair_counts[label]["disagree"] += 1
            disagreements.append({"cell": cell(s), "probe": s["probe"],
                                  "ratio": s["realized_ratio"], "responses": [
                                      {"item_id": i["item_id"], "prompt": i["prompt"],
                                       "keyed_option": i["source"]["keyed_option"],
                                       "answer": r["choice"], "keyed": r["keyed"],
                                       "brief_basis": r["brief_basis"]} for i, r in values]})
    assert len(pairs) == 98 and len(disagreements) == 8
    evidence_disagreements = []
    for key, values in histories.items():
        assert len(values) == 2
        if values[0][1]["keyed"] != values[1][1]["keyed"]:
            evidence_disagreements.append(list(key))
    assert len(histories) == 48 and len(evidence_disagreements) == 2
    fits = {}
    for label, points in sorted(ladders.items()):
        rungs = sorted({p[0] for p in points})
        errors = [sum((sum(r >= x for x in rungs) > gap) != k for r, _, k in points)
                  for gap in range(len(rungs) + 1)]
        best = [i for i, e in enumerate(errors) if e == min(errors)]
        status = ("unidentified" if len(best) > 1 else "left" if best[0] == 0
                  else "right" if best[0] == len(rungs) else "interior")
        decreases = {}
        for order in ("A", "B"):
            choices = [k for _, o, k in sorted(points) if o == order]
            decreases[order] = sum(a and not b for a, b in pairwise(choices))
        fits[label] = {"status": status, "violations": min(errors), "n": len(points),
                       "lower": rungs[best[0] - 1] if best[0] else None,
                       "upper": rungs[best[-1]] if best[-1] < len(rungs) else None,
                       "decreases_by_display_order": decreases}

    scored = {f"boxes/{c.cause.value}": c.infer for c in score.attribution}
    for c in score.aggregate:
        for order, fit in c.infer_by_order.items():
            scored[f"debug/{c.diagnostic.value}/{c.totals.value}/{order}"] = fit
    assert set(scored) == set(fits)
    for label, fit in scored.items():
        status = fit.censored if fit.censored != "none" else (
            "interior" if fit.identified else "unidentified")
        assert fits[label]["status"] == status
        for field in ("lower", "upper", "violations", "n"):
            assert fits[label][field] == getattr(fit, field)

    # Compare exact A/B bridge requests with every prior explanation calibration.
    current_by_prompt = {i["prompt"]: found[i["item_id"]] for i in ii}
    bridge = {}
    for run_id in ("36088607405", "36090248661", "36090756872"):
        prior = REPO / "results" / "calibration" / run_id
        old_items = read_lines(prior / "items.jsonl")
        old_rows = {r["item_id"]: r for r in read_lines(prior / "responses.jsonl")}
        matched = Counter()
        for item in old_items:
            if item["reply_format"] != "letter":
                continue
            old = old_rows[item["item_id"]]
            new = current_by_prompt[item["prompt"]]
            assert old["request_body"] == new["request_body"]
            kind = "social" if item["expected_recipient"] is None else "control"
            matched[kind + "_matched"] += 1
            matched[kind + "_same_choice"] += old["answer"] == new["choice"]
        bridge[run_id] = dict(matched)

    # These are human-readable manual labels, not automated grading of free text.
    manual = read_lines(ROOT / "audit" / "control-calculations.jsonl")
    assert {m["item_id"] for m in manual} == set(rule_values) and len(manual) == 12
    for m in manual:
        assert m["expected_values_from_prompt"] == rule_values[m["item_id"]]
        assert m["brief_basis"] == found[m["item_id"]]["brief_basis"]
    assert read_lines(ROOT / "audit" / "order-disagreements.jsonl") == disagreements
    return {"run": "36095971330", "recorded": len(rr), "controls_correct": dict(controls),
            "rule_explanations_manually_reviewed": len(manual),
            "option_pairs": dict(pair_counts), "ladders_by_evidence_order": fits,
            "ladder_status_counts": dict(Counter(f["status"] for f in fits.values())),
            "evidence_pairs": len(histories), "evidence_disagreements": evidence_disagreements,
            "aggregate_keeps": sum(r["keyed"] for i in ii if
                                   i["source"].get("family") == "aggregate"
                                   for r in [found[i["item_id"]]]),
            "prior_calibration_bridge": bridge,
            "usage": {k: sum(r["usage"][k] for r in rr) for k in (
                "input_tokens", "output_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens")}}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2) + "\n", end="")
