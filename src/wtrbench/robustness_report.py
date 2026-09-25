"""Descriptive pilot outcomes, preserving planned denominators and manual-review status."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import Any

from wtrbench.explanation_calibration import ExplanationItem
from wtrbench.inference import InferenceItem
from wtrbench.robustness_pilot import (
    MODEL,
    PROTOCOL,
    PilotItem,
    PilotResponse,
    batch_hash,
    digest,
    validate,
)
from wtrbench.score import ladder_estimate

CONDITION_LABELS = {
    "respects_condition", "contradicts_condition", "unclear_or_no_checkable_basis",
    "unusable_or_missing",
}


def dimensions(item: PilotItem) -> dict[str, Any]:
    s = item.source
    return {"block": item.block, "unit": item.unit, "kind": item.kind,
            "wording": item.wording, "repetition": item.repetition,
            "probe": s.probe.value if isinstance(s, InferenceItem) else s.kind,
            "cause": s.cause.value if isinstance(s, InferenceItem) and s.cause else None,
            "diagnostic": s.diagnostic.value if isinstance(s, InferenceItem) and s.diagnostic
            else None, "totals": s.totals.value if isinstance(s, InferenceItem) and s.totals
            else None}


def pair_records(items: list[PilotItem], found: dict[str, PilotResponse]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[PilotItem]] = defaultdict(list)
    for i in items:
        groups["repeat", i.template_id].append(i)
        s = i.source
        if not isinstance(s, InferenceItem):
            continue
        common = {"repetition": i.repetition, "wording": i.wording}
        fields = s.model_dump(mode="json", exclude={"item_id", "index_within_form", "prompt"})
        groups["option_order", digest({**common, **{k: v for k, v in fields.items()
                                                   if k != "keyed_option"}})].append(i)
        if i.kind == "binary":
            groups["wording", digest({"repetition": i.repetition,
                                       "source_id": s.item_id})].append(i)
        if s.family == "aggregate":
            groups["history_order", digest({**common, **{k: v for k, v in fields.items()
                                                         if k != "choices_swapped"}})].append(i)
    records = []
    for (comparison, key), group in sorted(groups.items()):
        if len(group) != 2:
            raise ValueError(f"Incomplete planned {comparison} pair: {key}")
        values = [found[i.item_id].keyed if i.item_id in found else None for i in group]
        complete = all(v is not None for v in values)
        dims = dimensions(group[0])
        if comparison == "repeat":
            dims["repetition"] = "both"
        if comparison == "wording":
            dims["wording"] = "both"
        records.append({"comparison": comparison, "pair_id": key, **dims,
                        "item_ids": [i.item_id for i in group], "semantic_choices": values,
                        "complete": complete,
                        "disagree": values[0] != values[1] if complete else None})
    return records


def pair_counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    n = sum(r["complete"] for r in records)
    d = sum(r["disagree"] is True for r in records)
    return {"planned": len(records), "complete": n, "incomplete": len(records) - n,
            "disagree": d, "disagreement_rate_among_complete": d / n if n else None}


def control_records(items: list[PilotItem], found: dict[str, PilotResponse]) -> list[dict[str, Any]]:
    result = []
    for i in items:
        s = i.source
        if not isinstance(s, ExplanationItem):
            continue
        r = found.get(i.item_id)
        values = None
        if s.kind == "explicit_rule":
            _, weight, amount = s.case.split("_")
            own, other = Decimal(amount), Decimal(weight) * 10
            a, b = (own, other) if s.sam_first else (other, own)
            values = {"A": float(a), "B": float(b)}
        result.append({"item_id": i.item_id, "repetition": i.repetition, "kind": s.kind,
                       "case": s.case, "sam_first": s.sam_first, "prompt": i.prompt,
                       "expected_answer": i.keyed_option, "true_option_values": values,
                       "recorded": r is not None, "usable": r is not None and r.choice is not None,
                       "answer": r.choice if r else None, "correct": r.keyed if r else None,
                       "brief_basis": r.brief_basis if r else None, "raw": r.raw if r else None,
                       "calculation_review": "pending_manual_review" if values else "not_applicable"})
    return result


def review_packet(items: list[PilotItem], found: dict[str, PilotResponse]
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    packet, key = [], []
    for i in items:
        if i.kind != "binary":
            continue
        r = found.get(i.item_id)
        rid = "review-" + digest({"review_order": PROTOCOL, "item": i.item_id})[:20]
        # Bind coding to this actual API record, including request/message IDs; missing is explicit.
        rdigest = digest({"item": i.item_id, "response": r.model_dump(mode="json") if r else None})
        packet.append({"review_id": rid, "response_digest": rdigest, "prompt": i.prompt,
                       "brief_basis": r.brief_basis if r else None,
                       "response_usable": r is not None and r.choice is not None,
                       "label": None, "notes": ""})
        key.append({"review_id": rid, "item_id": i.item_id, **dimensions(i)})
    return sorted(packet, key=lambda r: r["review_id"]), sorted(key, key=lambda r: r["review_id"])


def condition_review(packet: list[dict[str, Any]], key: list[dict[str, Any]],
                     labels: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    known = {r["review_id"]: r for r in packet}
    coded: dict[str, str] = {}
    seen = set()
    for r in labels or []:
        rid = r.get("review_id")
        if not isinstance(rid, str) or rid not in known or rid in seen:
            raise ValueError("Unknown or duplicate review ID")
        seen.add(rid)
        if r.get("response_digest") != known[rid]["response_digest"]:
            raise ValueError("Review label belongs to a different response")
        label = r.get("label")
        if label is None:
            continue
        if label not in CONDITION_LABELS or not isinstance(r.get("notes"), str) or not r["notes"].strip():
            raise ValueError("Every review label requires an allowed category and supporting notes")
        if (label == "unusable_or_missing") == known[rid]["response_usable"]:
            raise ValueError("Review category conflicts with response usability")
        coded[rid] = label

    def counts(group: list[dict[str, Any]]) -> dict[str, Any]:
        labels_here = Counter(coded[r["review_id"]] for r in group if r["review_id"] in coded)
        return {"planned": len(group), "reviewed": sum(labels_here.values()),
                "pending": len(group) - sum(labels_here.values()),
                "labels": {label: labels_here[label] for label in sorted(CONDITION_LABELS)}}

    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in key:
        strata[f"pass{r['repetition']}/{r['unit']}/{r['cause']}/{r['probe']}/{r['wording']}"].append(r)
    return {**counts(key), "status": "complete" if len(coded) == len(packet) else "pending_review",
            "by_cell": {s: counts(g) for s, g in sorted(strata.items())}}


def ladder_records(items: list[PilotItem], found: dict[str, PilotResponse]) -> list[dict[str, Any]]:
    groups: dict[str, list[PilotItem]] = defaultdict(list)
    for i in items:
        if i.kind != "valuation":
            continue
        s = i.source
        assert isinstance(s, InferenceItem)
        dims = {**dimensions(i), "history_swapped": s.choices_swapped}
        groups[json.dumps(dims, sort_keys=True)].append(i)
    result = []
    for cell, group in sorted(groups.items()):
        for order in ("A", "B", "pooled"):
            selected = [i for i in group if order == "pooled" or i.keyed_option == order]
            points = []
            for i in selected:
                assert isinstance(i.source, InferenceItem) and i.source.realized_ratio is not None
                r = found.get(i.item_id)
                points.append((i.source.realized_ratio, r.keyed if r else None))
            fit = ladder_estimate(points)
            downward = planned_steps = complete_steps = 0
            for key_option in ("A", "B"):
                sequence = sorted((i for i in selected if i.keyed_option == key_option),
                                  key=lambda i: float(i.source.realized_ratio))  # type: ignore[union-attr,arg-type]
                for left, right in pairwise(sequence):
                    planned_steps += 1
                    a, b = found.get(left.item_id), found.get(right.item_id)
                    if a and b and a.keyed is not None and b.keyed is not None:
                        complete_steps += 1
                        downward += a.keyed and not b.keyed
            result.append({**json.loads(cell), "keyed_option": order,
                           "fit": fit.model_dump(mode="json"), "points": sorted(points,
                                                                                  key=lambda p: p[0]),
                           "downward_steps": downward, "complete_adjacent_steps": complete_steps,
                           "planned_adjacent_steps": planned_steps,
                           "complete_zero_violation_interior": (
                               fit.estimate is not None and fit.n_missing == 0 and fit.violations == 0)})
    return result


def analyse(items: list[PilotItem], rows: list[PilotResponse], *,
            labels: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    found = validate(items, rows)
    pairs = pair_records(items, found)
    packet, key = review_packet(items, found)
    controls = control_records(items, found)
    ladders = ladder_records(items, found)
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in pairs:
        strata[f"{r['comparison']}/{r['block']}/pass{r['repetition']}/{r['unit']}/"
               f"{r['probe']}/{r['wording']}/{r['cause']}/{r['diagnostic']}/{r['totals']}"].append(r)
    usable = sum(r.choice is not None for r in rows)
    binary: dict[str, Counter[str]] = defaultdict(Counter)
    collection: dict[str, Counter[str]] = defaultdict(Counter)
    for i in items:
        response = found.get(i.item_id)
        d = dimensions(i)
        group = f"pass{i.repetition}/{i.unit}/{d['probe']}/{i.wording}"
        collection[group]["planned"] += 1
        collection[group]["missing" if response is None else
                          "unusable" if response.choice is None else "usable"] += 1
        if i.kind == "binary":
            bgroup = f"{group}/{d['cause']}"
            binary[bgroup]["planned"] += 1
            binary[bgroup]["missing_or_unusable" if response is None or response.keyed is None else
                           "yes" if response.keyed else "no"] += 1
    summary = {
        "protocol": PROTOCOL, "model": MODEL, "items_hash": batch_hash(items),
        "collection": {"planned": len(items), "recorded": len(rows), "usable": usable,
                       "missing": len(items) - len(rows), "unusable": len(rows) - usable},
        "collection_by_cell": dict(sorted(collection.items())),
        "comparisons": {f"{kind}/{block}": pair_counts([
            r for r in pairs if r["comparison"] == kind and r["block"] == block])
            for kind, block in (("option_order", "pilot"), ("repeat", "pilot"),
                                ("repeat", "control"), ("wording", "pilot"),
                                ("history_order", "pilot"))},
        "comparisons_by_cell": {s: pair_counts(g) for s, g in sorted(strata.items())},
        "controls": {"planned": len(controls), "correct": sum(c["correct"] is True for c in controls),
                     "usable": sum(c["usable"] for c in controls),
                     "missing": sum(not c["recorded"] for c in controls),
                     "unusable": sum(c["recorded"] and not c["usable"] for c in controls),
                     "rule_calculations": sum(c["true_option_values"] is not None for c in controls),
                     "calculation_review": "pending_manual_review"},
        "condition_adherence": condition_review(packet, key, labels),
        "binary_choices_by_cell": dict(sorted(binary.items())),
        "exploratory_wtr": {"pooled_cells": sum(l["keyed_option"] == "pooled" for l in ladders),
            "complete_zero_violation_interior_cells": sum(l["keyed_option"] == "pooled" and
                l["complete_zero_violation_interior"] for l in ladders),
            "interpretation": "Exploratory threshold fits; not validation of a latent social measure"},
        "stop_reasons": dict(Counter(r.stop_reason for r in rows)),
        "tokens": {key: sum(v for r in rows if r.usage and isinstance(v := r.usage.get(key), int))
                   for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                               "cache_read_input_tokens")},
    }
    return {"summary": summary, "pairs": pairs, "ladders": ladders, "controls": controls,
            "condition-review-template": packet, "condition-review-key": key}


def markdown(summary: dict[str, Any]) -> str:
    c, a = summary["collection"], summary["condition_adherence"]
    lines = ["# Response robustness pilot", "", f"Protocol `{PROTOCOL}`; model `{MODEL}`.",
             (f"Recorded {c['recorded']}/{c['planned']}; usable {c['usable']}; "
             f"missing {c['missing']}; unusable {c['unusable']}."),
             "This is the fixed pilot. Disagreements are outcomes, not a trigger for calibration.",
             "Rates below describe these prompts; repeated requests are not independent scenarios.",
             "", "## Primary response comparisons", "",
             "| Comparison | Disagree | Complete pairs | Planned pairs |", "|---|---:|---:|---:|"]
    for name, p in summary["comparisons"].items():
        lines.append(f"| {name} | {p['disagree']} | {p['complete']} | {p['planned']} |")
    lines += ["", "Option and repeat comparisons are primary; wording/history are secondary.",
              "Disagreement compares semantic choices after reversing the answer-letter mapping.",
              "", "## Stated-condition adherence", "",
              f"Human coding: {a['reviewed']}/{a['planned']} reviewed; {a['pending']} pending.",
              "Labels: " + json.dumps(a["labels"], sort_keys=True),
              "Do not infer adherence from yes/no choices. Review the supplied conditions and basis.",
              "Explanations are returned text, not evidence of internal reasoning.",
              "", "## Controls and exploratory estimates", "",
              (f"Control final choices correct: {summary['controls']['correct']}/"
              f"{summary['controls']['planned']} planned; {summary['controls']['usable']} usable."),
              "All 24 rule calculations remain pending manual review, even when final choices pass.",
              "The recurring rule_1_20 / Sam-second false-tie explanation needs explicit checking.",
              (f"Exploratory pooled ladder cells: {summary['exploratory_wtr']['pooled_cells']}; "
              "complete, zero-violation interior fits: "
              f"{summary['exploratory_wtr']['complete_zero_violation_interior_cells']}."),
              "Bounds, tied fits and missing responses remain visible in ladders.jsonl.",
              "A clean fit would not by itself validate WTR as a latent social measure.",
              "", "## Results by fixed scenario or numerical set", "",
              "| Unit | Option disagreement/complete/planned | Repeat disagreement/complete/planned |",
              "|---|---:|---:|"]
    units = sorted({s.split('/')[3] for s in summary["comparisons_by_cell"]
                    if s.startswith("option_order/pilot/")})
    for unit in units:
        cells = []
        for comparison in ("option_order", "repeat"):
            ps = [v for s, v in summary["comparisons_by_cell"].items()
                  if s.startswith(comparison + "/pilot/") and s.split('/')[3] == unit]
            cells.append("/".join(str(sum(p[k] for p in ps)) for k in
                                  ("disagree", "complete", "planned")))
        lines.append(f"| {unit} | {cells[0]} | {cells[1]} |")
    lines += ["", "Full per-pass/probe/wording/cell counts and denominators: summary.json.",
              "Input/output tokens: " + json.dumps(summary["tokens"], sort_keys=True), ""]
    return "\n".join(lines)


def save_reports(path: Path, items: list[PilotItem], rows: list[PilotResponse], *,
                 labels_path: Path | None = None) -> str:
    labels = None
    if labels_path is not None:
        if labels_path.resolve() == path.with_suffix(".condition-review-template.jsonl").resolve():
            raise ValueError("Copy the review template to a separate labels file before coding")
        labels = [json.loads(line) for line in labels_path.read_text().splitlines() if line.strip()]
    result = analyse(items, rows, labels=labels)
    template_path = path.with_suffix(".condition-review-template.jsonl")
    if template_path.exists() and any(json.loads(line).get("label") is not None
                                     for line in template_path.read_text().splitlines() if line.strip()):
        raise ValueError("Review template contains labels; move it to a separate labels file first")
    for name, data in result.items():
        if name == "summary":
            path.with_suffix(".summary.json").write_text(json.dumps(data, indent=2) + "\n")
        else:
            path.with_suffix(f".{name}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in data))
    report = markdown(result["summary"])
    path.with_suffix(".report.md").write_text(report)
    if labels_path is not None:
        # Archive the precise accepted labels without modifying the reviewer's source file.
        path.with_suffix(".accepted-condition-labels.json").write_text(json.dumps(labels, indent=2) + "\n")
    return report
