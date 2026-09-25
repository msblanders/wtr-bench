"""Known-answer accuracy, interval recovery and separate explanation review."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from wtrbench.recovery_run import RecoveryResponse, items_hash, sha, validate
from wtrbench.validation_recovery import MODEL, PROTOCOL, RecoveryItem, recovery_report

REVIEW_LABELS = {"consistent", "incorrect_calculation_or_mapping", "unsupported_inference",
                 "unclear_or_no_checkable_basis", "unusable_or_missing"}


def pairs(items: list[RecoveryItem], found: dict[str, RecoveryResponse]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, Any], list[RecoveryItem]] = defaultdict(list)
    for i in items:
        groups["option_order", (i.arm, i.profile, i.history_swapped,
                                 i.repetition, i.own_amount)].append(i)
        groups["repeat", i.template_id].append(i)
        if i.arm == "choice_history":
            groups["history_order", (i.profile, i.repetition, i.own_amount, i.sam_first)].append(i)
    result = []
    for (comparison, _), group in sorted(groups.items(), key=lambda p: str(p[0])):
        if len(group) != 2:
            raise ValueError("Incomplete planned comparison pair")
        values = [found[i.item_id].keyed if i.item_id in found else None for i in group]
        complete = all(v is not None for v in values)
        result.append({"comparison": comparison, "arm": group[0].arm,
                       "profile": group[0].profile,
                       "repetition": "both" if comparison == "repeat" else group[0].repetition,
                       "item_ids": [i.item_id for i in group], "semantic_keep_choices": values,
                       "complete": complete,
                       "disagree": values[0] != values[1] if complete else None})
    return result


def pair_counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    complete = sum(r["complete"] for r in records)
    disagree = sum(r["disagree"] is True for r in records)
    return {"planned": len(records), "complete": complete, "incomplete": len(records)-complete,
            "disagree": disagree, "rate_among_complete": disagree/complete if complete else None}


def review_template(items: list[RecoveryItem], found: dict[str, RecoveryResponse]
                    ) -> list[dict[str, Any]]:
    result = []
    for i in items:
        row = found.get(i.item_id)
        own_letter = "A" if i.sam_first else "B"
        other_letter = "B" if i.sam_first else "A"
        exact = None
        intervals = None
        if i.arm == "explicit_weight":
            exact = {own_letter: str(i.own_amount),
                     other_letter: str(Decimal(i.weight_private_audit)*i.other_amount)}
        else:
            lo, hi = map(Decimal, i.history_interval_private_audit)
            intervals = {own_letter: {"lower": str(i.own_amount), "upper": str(i.own_amount),
                                      "endpoints_included": True},
                         other_letter: {"lower": str(lo*i.other_amount),
                                        "upper": str(hi*i.other_amount), "endpoints_included": False}}
        result.append({"review_id": "explanation-"+sha(i.item_id)[:20], "item_id": i.item_id,
            "response_digest": sha(json.dumps({"item": i.model_dump(mode="json"),
                "response": row.model_dump(mode="json") if row else None}, sort_keys=True)),
            "arm": i.arm, "profile": i.profile, "history_swapped": i.history_swapped,
            "repetition": i.repetition, "prompt": i.prompt, "expected_answer": i.expected_answer,
            "returned_answer": row.choice if row else None, "final_correct": row.correct if row else None,
            "response_usable": row is not None and row.choice is not None,
            "brief_basis": row.brief_basis if row else None, "raw": row.raw if row else None,
            "exact_option_values": exact, "compatible_option_value_intervals": intervals,
            "weight_information": {"exact": i.weight_private_audit} if exact else {
                "lower": i.history_interval_private_audit[0],
                "upper": i.history_interval_private_audit[1], "endpoints_included": False},
            "label": None, "notes": ""})
    return sorted(result, key=lambda r: r["review_id"])


def review_summary(packet: list[dict[str, Any]], labels: list[dict[str, Any]] | None
                   ) -> dict[str, Any]:
    known = {r["review_id"]: r for r in packet}
    accepted: dict[str, str] = {}
    seen = set()
    for row in labels or []:
        rid = row.get("review_id")
        if not isinstance(rid, str) or rid not in known or rid in seen:
            raise ValueError("Unknown or duplicate explanation review ID")
        seen.add(rid)
        if row.get("response_digest") != known[rid]["response_digest"]:
            raise ValueError("Explanation label belongs to a different response")
        label = row.get("label")
        if label is None:
            continue
        if (not isinstance(label, str) or label not in REVIEW_LABELS
                or not isinstance(row.get("notes"), str) or not row["notes"].strip()):
            raise ValueError("Review requires an allowed label and supporting notes")
        if (label == "unusable_or_missing") == known[rid]["response_usable"]:
            raise ValueError("Review label conflicts with response usability")
        accepted[rid] = label

    def counts(group: list[dict[str, Any]]) -> dict[str, Any]:
        values = Counter(accepted[r["review_id"]] for r in group if r["review_id"] in accepted)
        return {"planned": len(group), "reviewed": sum(values.values()),
                "pending": len(group)-sum(values.values()),
                "labels": {label: values[label] for label in sorted(REVIEW_LABELS)}}

    return {**counts(packet), "status": "complete" if len(accepted) == len(packet) else "pending_review",
            "by_arm": {arm: counts([r for r in packet if r["arm"] == arm])
                       for arm in ("explicit_weight", "choice_history")}}


def analyse(items: list[RecoveryItem], rows: list[RecoveryResponse], *,
            labels: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    found = validate(items, rows)
    recovery = recovery_report(items, {k: r.choice for k, r in found.items()})
    pair_rows = pairs(items, found)
    packet = review_template(items, found)
    review = review_summary(packet, labels)

    def counts(group: list[RecoveryItem]) -> dict[str, Any]:
        recorded = sum(i.item_id in found for i in group)
        usable = sum(i.item_id in found and found[i.item_id].choice is not None for i in group)
        correct = sum(i.item_id in found and found[i.item_id].correct is True for i in group)
        return {"planned": len(group), "recorded": recorded, "usable": usable, "correct": correct,
                "incorrect_usable": usable-correct, "missing": len(group)-recorded,
                "unusable": recorded-usable, "accuracy_among_usable": correct/usable if usable else None,
                "correct_fraction_planned": correct/len(group) if group else None}

    arms = {}
    for arm in ("explicit_weight", "choice_history"):
        group = [i for i in items if i.arm == arm]
        fits = [f for f in recovery["fits"] if f["arm"] == arm]
        c = counts(group)
        arms[arm] = {**c, "planned_fits": len(fits),
                     "recovered_fits": sum(f["recovered_interval"] for f in fits),
                     "choice_clear_pass": c["correct"] == len(group) and
                     all(f["recovered_interval"] for f in fits)}
    cells: dict[str, list[RecoveryItem]] = defaultdict(list)
    for i in items:
        cells[f"{i.arm}/{i.profile}/history-{i.history_swapped}/pass-{i.repetition}/"
              f"{'sam-first' if i.sam_first else 'sam-second'}"].append(i)
    summary = {"data_origin": "recorded_API_responses", "protocol": PROTOCOL, "model": MODEL,
        "items_hash": items_hash(items), "collection": counts(items), "by_arm": arms,
        "by_cell": {k: counts(g) for k, g in sorted(cells.items())},
        "known_task_choice_gate": recovery["known_task_choice_gate"],
        "choice_status": ("incomplete" if len(rows) < len(items) else
                          "clear_pass" if recovery["known_task_choice_gate"] else "mixed_or_failed"),
        "planned_fits": len(recovery["fits"]),
        "recovered_fits": sum(f["recovered_interval"] for f in recovery["fits"]),
        "explanation_review": review,
        "comparisons": {kind: pair_counts([r for r in pair_rows if r["comparison"] == kind])
                        for kind in ("option_order", "repeat", "history_order")},
        "comparisons_by_arm_profile": {f"{arm}/{profile}/{kind}": pair_counts([
            r for r in pair_rows if r["arm"] == arm and r["profile"] == profile and r["comparison"] == kind])
            for arm in arms for profile in ("low", "middle", "high")
            for kind in ("option_order", "repeat", "history_order")},
        "stop_reasons": dict(Counter(r.stop_reason for r in rows)),
        "tokens": {key: sum(v for r in rows if r.usage and isinstance(v := r.usage.get(key), int))
                   for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                               "cache_read_input_tokens")},
        "interpretation": "Constructed-task recovery only. Social pilot remains paused; review explanations."}
    return {"summary": summary, "fits": recovery["fits"], "pairs": pair_rows,
            "explanation-review-template": packet}


def markdown(summary: dict[str, Any]) -> str:
    c, review = summary["collection"], summary["explanation_review"]
    lines = ["# Known-partner recovery diagnostic", "", f"Protocol `{PROTOCOL}`; model `{MODEL}`.",
        (f"Recorded {c['recorded']}/{c['planned']}; usable {c['usable']}; "
         f"missing {c['missing']}; unusable {c['unusable']}."),
        "Data source: recorded API responses. The separate programmed-oracle file is not model evidence.",
        "", "| Condition | Correct / planned | Usable | Recovered / planned fits |",
        "|---|---:|---:|---:|"]
    for arm, a in summary["by_arm"].items():
        lines.append(f"| {arm} | {a['correct']}/{a['planned']} | {a['usable']} | "
                     f"{a['recovered_fits']}/{a['planned_fits']} |")
    lines += ["", f"Choice-only status: **{summary['choice_status']}**.",
        "Fits include pooled and separate option orders, each history order and each pass.",
        "They overlap; 54 fits are not 54 independent participants or replications.",
        "", "| Comparison | Disagree | Complete pairs | Planned pairs |", "|---|---:|---:|---:|"]
    for kind, p in summary["comparisons"].items():
        lines.append(f"| {kind} | {p['disagree']} | {p['complete']} | {p['planned']} |")
    lines += ["", "Pair comparisons use semantic keep/give choices, not printed letters.",
        "", (f"Explanation review: **{review['reviewed']}/{review['planned']} reviewed; "
        f"{review['pending']} pending**."), "Labels: " + json.dumps(review["labels"], sort_keys=True),
        "Correct choices do not guarantee correct returned calculations or inferences.",
        "History explanations are checked against the supported interval, not the private generating weight.",
        "Do not interpret brief explanations as access to internal reasoning.",
        "", "## Decision", "",
        "Inspect errors by arm/profile/order/pass and review the explanations before deciding next steps.",
        "A complete choice pass supports recovery on these constructed controls only.",
        "The social pilot remains paused. This workflow never launches it or repeats the diagnostic.",
        "Do not rerun to select a perfect batch; partial and negative results remain part of the record.",
        "", "Full counts, fits, pair records and review material are saved beside the response JSONL.",
        "Token use: " + json.dumps(summary["tokens"], sort_keys=True), ""]
    return "\n".join(lines)


def save_reports(path: Path, items: list[RecoveryItem], rows: list[RecoveryResponse], *,
                 labels_path: Path | None = None) -> str:
    template_path = path.with_suffix(".explanation-review-template.jsonl")
    labels = None
    if labels_path is not None:
        if labels_path.resolve() == template_path.resolve():
            raise ValueError("Copy the explanation template to a separate labels file first")
        labels = [json.loads(line) for line in labels_path.read_text().splitlines() if line.strip()]
    if template_path.exists() and any(json.loads(line).get("label") is not None
                                     for line in template_path.read_text().splitlines() if line.strip()):
        raise ValueError("Template contains review labels; move it to a separate labels file first")
    result = analyse(items, rows, labels=labels)
    for name, data in result.items():
        if name == "summary":
            path.with_suffix(".summary.json").write_text(json.dumps(data, indent=2)+"\n")
        else:
            path.with_suffix(f".{name}.jsonl").write_text("".join(json.dumps(r)+"\n" for r in data))
    if labels is not None:
        path.with_suffix(".accepted-explanation-labels.json").write_text(json.dumps(labels, indent=2)+"\n")
    report = markdown(result["summary"])
    path.with_suffix(".report.md").write_text(report)
    return report
