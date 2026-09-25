"""Prespecified paired presentation comparison and separate explanation audit."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from wtrbench.payoff_presentation import PRESENTATIONS, PROTOCOL, PresentationItem
from wtrbench.presentation_run import PresentationResponse, items_hash, validate
from wtrbench.recovery_report import pair_counts, review_summary, review_template
from wtrbench.validation_recovery import MODEL, recovery_report


def fits(items: list[PresentationItem], choices: dict[str, str | None]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for presentation in PRESENTATIONS:
        group = [i for i in items if i.presentation == presentation]
        selected = {i.item_id: choices.get(i.item_id) for i in group}
        result.extend({"presentation": presentation, **f}
                      for f in recovery_report(list(group), selected)["fits"])
    return result


def pairs(items: list[PresentationItem], found: dict[str, PresentationResponse]
          ) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[PresentationItem]] = defaultdict(list)
    for i in items:
        groups["presentation", i.source_item_id].append(i)
        groups["option_order", i.presentation, i.profile, i.history_swapped,
               i.repetition, i.own_amount].append(i)
        groups["history_order", i.presentation, i.profile, i.repetition,
               i.own_amount, i.sam_first].append(i)
        groups["repeat", i.template_id].append(i)
    records = []
    for key, group in sorted(groups.items(), key=lambda p: str(p[0])):
        if len(group) != 2:
            raise ValueError("Incomplete planned comparison pair")
        if key[0] == "presentation":
            group = sorted(group, key=lambda i: PRESENTATIONS.index(i.presentation))
        values = [found[i.item_id].keyed if i.item_id in found else None for i in group]
        correct = [found[i.item_id].correct if i.item_id in found else None for i in group]
        complete = all(v is not None for v in values)
        records.append({"comparison": key[0], "item_ids": [i.item_id for i in group],
            "presentation": "both" if key[0] == "presentation" else group[0].presentation,
            "profile": group[0].profile, "own_amount": group[0].own_amount,
            "history_swapped": "both" if key[0] == "history_order" else group[0].history_swapped,
            "repetition": "both" if key[0] == "repeat" else group[0].repetition,
            "sam_first": "both" if key[0] == "option_order" else group[0].sam_first,
            "semantic_keep_choices": values, "correct": correct,
            "complete": complete, "disagree": values[0] != values[1] if complete else None})
    return records


def matched_counts(records: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [r for r in records if r["complete"]]
    outcomes = Counter(tuple(r["correct"]) for r in complete)
    gains, losses = outcomes[False, True], outcomes[True, False]
    original = sum(r["correct"][0] is True for r in records)
    revised = sum(r["correct"][1] is True for r in records)
    return {**pair_counts(records), "both_correct": outcomes[True, True],
        "explicit_payoffs_only_correct": gains, "original_only_correct": losses,
        "both_incorrect": outcomes[False, False],
        "net_correct_gain_on_complete_pairs": gains-losses,
        "accuracy_difference_on_complete_pairs": (gains-losses)/len(complete) if complete else None,
        "correct_original_planned": original, "correct_explicit_payoffs_planned": revised,
        "correct_fraction_difference_planned": (revised-original)/len(records) if records else None}


def analyse(items: list[PresentationItem], rows: list[PresentationResponse], *,
            labels: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    found = validate(items, rows)
    fit_rows = fits(items, {k: r.choice for k, r in found.items()})
    pair_rows = pairs(items, found)
    packet = review_template(list(items), dict(found))
    item_map = {i.item_id: i for i in items}
    for p in packet:
        i = item_map[p["item_id"]]
        p.update(presentation=i.presentation, source_item_id=i.source_item_id,
                 source_template_id=i.source_template_id)
    review = review_summary(packet, labels)
    review.pop("by_arm")  # Every question is a history question in this diagnostic.
    by_review = {}
    for presentation in PRESENTATIONS:
        group = [p for p in packet if p["presentation"] == presentation]
        ids = {p["review_id"] for p in group}
        coded = [r for r in labels or [] if r.get("review_id") in ids]
        subset = review_summary(group, coded)
        subset.pop("by_arm")
        by_review[presentation] = subset
    review["by_presentation"] = by_review

    def counts(group: list[PresentationItem]) -> dict[str, Any]:
        recorded = sum(i.item_id in found for i in group)
        usable = sum(i.item_id in found and found[i.item_id].choice is not None for i in group)
        correct = sum(i.item_id in found and found[i.item_id].correct is True for i in group)
        return {"planned": len(group), "recorded": recorded, "usable": usable,
            "correct": correct, "incorrect_usable": usable-correct,
            "missing": len(group)-recorded, "unusable": recorded-usable,
            "accuracy_among_usable": correct/usable if usable else None,
            "correct_fraction_planned": correct/len(group) if group else None}

    conditions = {}
    for presentation in PRESENTATIONS:
        c = counts([i for i in items if i.presentation == presentation])
        f = [f for f in fit_rows if f["presentation"] == presentation]
        passed = c["correct"] == c["planned"] and all(x["recovered_interval"] for x in f)
        conditions[presentation] = {**c, "planned_fits": len(f),
            "recovered_fits": sum(x["recovered_interval"] for x in f),
            "choice_clear_pass": passed,
            "choice_status": "incomplete" if c["recorded"] < c["planned"] else
                             "clear_pass" if passed else "mixed_or_failed"}
    cells: dict[str, list[PresentationItem]] = defaultdict(list)
    for i in items:
        cells[f"{i.presentation}/{i.profile}/history-{i.history_swapped}/pass-{i.repetition}/"
              f"{'sam-first' if i.sam_first else 'sam-second'}"].append(i)
    matched = [r for r in pair_rows if r["comparison"] == "presentation"]
    summary = {"data_origin": "recorded_API_responses", "protocol": PROTOCOL, "model": MODEL,
        "items_hash": items_hash(items), "collection": counts(items),
        "by_presentation": conditions, "matched_presentation": matched_counts(matched),
        "matched_by_factor": {factor: {str(value): matched_counts([
            r for r in matched if r[factor] == value]) for value in sorted(
                {r[factor] for r in matched}, key=str)}
            for factor in ("profile", "own_amount", "history_swapped", "repetition", "sam_first")},
        "by_cell": {k: counts(g) for k, g in sorted(cells.items())},
        "within_presentation_comparisons": {p: {kind: pair_counts([
            r for r in pair_rows if r["presentation"] == p and r["comparison"] == kind])
            for kind in ("option_order", "history_order", "repeat")} for p in PRESENTATIONS},
        "planned_fits": len(fit_rows),
        "recovered_fits": sum(f["recovered_interval"] for f in fit_rows),
        "explanation_review": review,
        "stop_reasons": dict(Counter(r.stop_reason for r in rows)),
        "tokens": {k: sum(v for r in rows if r.usage and isinstance(v := r.usage.get(k), int))
                   for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                             "cache_read_input_tokens")},
        "interpretation": "Matched constructed-task presentation comparison; no automatic pilot release."}
    return {"summary": summary, "fits": fit_rows, "pairs": pair_rows,
            "explanation-review-template": packet}


def markdown(summary: dict[str, Any]) -> str:
    c, matched, review = (summary[k] for k in ("collection", "matched_presentation", "explanation_review"))
    lines = ["# Payoff presentation diagnostic", "", f"Protocol `{PROTOCOL}`; model `{MODEL}`.",
        (f"Recorded {c['recorded']}/{c['planned']}; usable {c['usable']}; "
         f"missing {c['missing']}; unusable {c['unusable']}."),
        "Data source: recorded API responses. The programmed-oracle check is software verification only.",
        "", "| Presentation | Correct / planned | Usable | Recovered / planned fits | Choice status |",
        "|---|---:|---:|---:|---|"]
    for p, a in summary["by_presentation"].items():
        lines.append(f"| {p} | {a['correct']}/{a['planned']} | {a['usable']} | "
                     f"{a['recovered_fits']}/{a['planned_fits']} | {a['choice_status']} |")
    lines += ["", "## Matched presentation comparison", "",
        f"Complete {matched['complete']}/{matched['planned']}; incomplete {matched['incomplete']}.",
        (f"Both correct: {matched['both_correct']}; explicit-payoffs only correct: "
        f"{matched['explicit_payoffs_only_correct']}; original only correct: "
         f"{matched['original_only_correct']}; both incorrect: {matched['both_incorrect']}."),
        "Positive differences favor explicit payoffs. Missing/unusable responses remain in planned denominators.",
        "Accuracy difference among complete pairs: " + str(matched["accuracy_difference_on_complete_pairs"]),
        "Correct-fraction difference across planned pairs: " + str(matched["correct_fraction_difference_planned"]),
        "", "| Presentation | Comparison | Disagree | Complete / planned pairs |", "|---|---|---:|---:|"]
    for p, kinds in summary["within_presentation_comparisons"].items():
        for kind, v in kinds.items():
            lines.append(f"| {p} | {kind} | {v['disagree']} | {v['complete']}/{v['planned']} |")
    lines += ["", "Pair comparisons use semantic choices, not printed letters.",
        "Fits overlap and repeats are not independent participants; these are descriptive fixed-set results.",
        "", "## Separate explanation review", "",
        f"**{review['reviewed']}/{review['planned']} reviewed; {review['pending']} pending.**",
        "Labels: " + json.dumps(review["labels"], sort_keys=True)]
    for p, v in review["by_presentation"].items():
        lines.append(f"{p}: {v['reviewed']}/{v['planned']} reviewed; " + json.dumps(v["labels"], sort_keys=True))
    lines += ["", "Correct final answers do not guarantee correct explanations.",
        "Review history inferences against feasible intervals, not a uniquely known private weight.",
        "Returned explanations are not evidence of internal reasoning. Disclose who coded them.",
        "", "## Decision", "",
        "Assess errors, changed intervals, all reversals/repeats and explanations before a decision.",
        "Improvement on this fixed set is not full social-measure validation; do not select a preferred order or pass.",
        "The presentation package changes layout and explicit zero payoffs together; it does not isolate either factor.",
        "Both social pilots remain paused. This workflow never launches them or repeats itself.",
        "Do not rerun until perfect. Any further collection needs a separately documented purpose and fixed plan.",
        "Token use: " + json.dumps(summary["tokens"], sort_keys=True), ""]
    return "\n".join(lines)


def save_reports(path: Path, items: list[PresentationItem], rows: list[PresentationResponse], *,
                 labels_path: Path | None = None) -> str:
    template = path.with_suffix(".explanation-review-template.jsonl")
    if labels_path is not None and labels_path.resolve() == template.resolve():
        raise ValueError("Copy the explanation template to a separate labels file first")
    if template.exists() and any(json.loads(line).get("label") is not None
                                 for line in template.read_text().splitlines() if line.strip()):
        raise ValueError("Template contains review labels; move them to a separate file")
    labels = None if labels_path is None else [json.loads(line) for line in
                                               labels_path.read_text().splitlines() if line.strip()]
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
