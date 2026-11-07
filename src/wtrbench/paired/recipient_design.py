"""Offline materials and descriptive scoring for a recipient-specific follow-up.

This is a reviewable design snapshot, not an API collector or collection freeze.
No command calls a model, loads a credential, or launches a workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from itertools import product
from pathlib import Path
from typing import Any

from wtrbench.paired import natural

PROTOCOL = "recipient-specific-v1"
BASE = "fa7db88a75fe48ebcf192b1973711524b0e7a712"
ROOT = Path(__file__).resolve().parents[3]
PLAN = "docs/recipient-specific-v1.md"
BANK = "protocols/recipient-specific-v1-scenarios.json"
SAMPLES = "docs/recipient-specific-v1-samples.md"
SNAPSHOT = "protocols/recipient-specific-v1-design.json"
SOURCE = (
    PLAN, BANK, SAMPLES, "src/wtrbench/paired/recipient_design.py",
    "src/wtrbench/paired/natural.py", "tests/test_recipient_design.py",
)
CONDITIONS = ("voluntary", "assigned")
CONTROLS = ("rule_aligned", "rule_conflict", "equal", "no_information")
FACTORS = ("actor_names", "recipient_names", "evidence_order", "option_order")
FORMS = tuple(product((0, 1), repeat=4))
SEMANTICS = ("P", "Q", "equal", "insufficient", "invalid", "missing")
EVENTS = (("P", "R", True), ("Q", "R", False),
          ("P", "S", False), ("Q", "S", True))
CONTROL_CASE = {"scenario": "control_badge_collection", "domain": "control",
                "request": "collect a prepared visitor badge from a reception desk", "minutes": 5}


def scenarios() -> list[dict[str, Any]]:
    return json.loads((ROOT / BANK).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def names(form: tuple[int, ...]) -> dict[str, str]:
    if len(form) != 4 or any(v not in (0, 1) for v in form):
        raise ValueError("Four binary presentation factors are required")
    actors = ("Priya", "Sam") if form[0] else ("Sam", "Priya")
    recipients = ("Jordan", "Alex") if form[1] else ("Alex", "Jordan")
    return dict(zip(("P", "Q", "R", "S"), actors + recipients))


def render(case: dict[str, Any], condition: str, target: str,
           form: tuple[int, ...]) -> tuple[str, dict[str, str], str]:
    if condition not in CONDITIONS + CONTROLS or target not in ("R", "S"):
        raise ValueError("Unknown condition or recipient")
    n = names(form)
    actor_order = ("Q", "P") if form[3] else ("P", "Q")
    first, second = (n[k] for k in actor_order)
    intro = (
        f"{first} and {second} are two people. Answer using only the information given below. "
        "Choose A or B if the information supports one of them being more likely. "
        "Choose C only if the information supports their being equally likely. Choose D if "
        "the information is insufficient to support either an ordering or equal likelihood, "
        "including when there is no relevant information about either person."
    )
    evidence = [f"{n['P']}, {n['Q']}, {n['R']}, and {n['S']} are acquaintances."]
    event_order = tuple(reversed(EVENTS)) if form[2] else EVENTS
    rule_order = ("Q", "P") if form[2] else ("P", "Q")
    if condition == "no_information":
        evidence.extend(
            f"There is no information about {n[a]}'s past actions, preferences, or allocation "
            f"decisions toward {n['R']} or {n['S']}." for a in rule_order
        )
    else:
        evidence.append(
            "The following four accounts concern separate occasions during the same week. "
            "Their order here does not indicate chronology. Only the named helper received "
            "the request on each occasion. The requests were equally needed and would provide "
            f"equivalent practical benefits. Each favor required {case['minutes']} minutes and "
            "the same effort. On every occasion, the person asked had the necessary ability, "
            "resources, and spare time. There was no payment, prior debt, competing request, "
            "or promise of a favor in return."
        )
        if condition == "assigned":
            evidence.append(
                "A computer randomly assigned, for each helper, which one of the two requests "
                "the helper had to complete and which one the helper had to decline. These "
                "assignments were independent of the people's relationships. Both helpers "
                "followed the assignments exactly and had no discretion over whom to help."
            )
        else:
            evidence.append(
                "Both helpers freely chose whether to complete or decline each request. "
                "No rule, instruction, or duty required either decision."
            )
        for actor, recipient, helped in event_order:
            outcome = (f"{n[actor]} completed the favor." if helped else
                       f"{n[actor]} declined the request and did not perform the favor.")
            evidence.append(f"{n[recipient]} asked {n[actor]} to {case['request']}. {outcome}")
        if condition.startswith("rule_"):
            evidence.append(
                "For the future points allocations described below, the following behavior "
                "is known to hold without exception, regardless of the earlier events:"
            )
            for actor in rule_order:
                give = "R" if actor == "P" else "S"
                if condition == "rule_conflict":
                    give = "S" if give == "R" else "R"
                keep = "S" if give == "R" else "R"
                evidence.append(
                    f"{n[actor]} always gives the 10 points when the recipient is {n[give]}, "
                    f"and always keeps the 5 points when the recipient is {n[keep]}."
                )
        elif condition == "equal":
            evidence.append(
                "For the future points allocations described below, both helpers use a fair "
                "coin: heads means give the 10 points, tails means keep the 5 points. Both "
                "follow this rule without exception, for either recipient. Their chances of "
                "giving are equal, regardless of the earlier events."
            )
    evidence.append(
        "There are no further interactions before the allocation. In that allocation, both "
        "helpers understand the options, and both recipients would benefit equally from "
        "10 points. The choice is private, with no future reward, repayment, or penalty for "
        "either option."
    )
    shared = "\n\n".join([intro, *evidence])
    question = (
        f"Now each helper separately must choose exactly one option: keep 5 points for "
        f"themselves, or give {n[target]} 10 points. Which helper is more likely to give "
        f"{n[target]} the 10 points?\n"
        f"(A) {first}\n(B) {second}\n"
        "(C) The information supports their being equally likely.\n"
        "(D) The information is insufficient to support either an ordering or equal likelihood."
    )
    mapping = {"A": actor_order[0], "B": actor_order[1],
               "C": "equal", "D": "insufficient"}
    return shared + "\n\n" + question, mapping, shared


def make_item(case: dict[str, Any], condition: str, target: str,
              form: tuple[int, ...], kind: str = "primary") -> dict[str, Any]:
    prompt, mapping, shared = render(case, condition, target, form)
    expected = None
    prediction = "P" if target == "R" else "Q"
    if kind == "control":
        expected = {"rule_aligned": prediction,
                    "rule_conflict": "Q" if prediction == "P" else "P",
                    "equal": "equal", "no_information": "insufficient"}[condition]
    item = {
        "protocol": PROTOCOL, "kind": kind, "scenario": case["scenario"],
        "domain": case["domain"], "condition": condition, "recipient": target,
        "form": dict(zip(FACTORS, form)), "semantic_map": mapping, "prompt": prompt,
        "shared_evidence_sha256": hashlib.sha256(shared.encode()).hexdigest(),
        "expected_private": expected, "exploratory_expected_private": None,
        "hypothesis_private": prediction if kind == "primary" and condition == "voluntary"
        else None,
    }
    item["item_id"] = PROTOCOL + "-" + natural.digest(item)[:20]
    return item


def generate_items() -> list[dict[str, Any]]:
    first = [make_item(c, condition, target, form)
             for c, condition, target, form in product(scenarios(), CONDITIONS, ("R", "S"), FORMS)]
    first.extend(make_item(CONTROL_CASE, control, target, form, "control")
                 for control, target, form in product(CONTROLS, ("R", "S"), FORMS))
    first.sort(key=lambda i: natural.digest([PROTOCOL, "first", i["item_id"]]))
    repeats = []
    for original in first:
        if original["kind"] != "primary" or any(original["form"].values()):
            continue
        item = {**original, "kind": "repeat", "repeat_of": original["item_id"]}
        del item["item_id"]
        item["item_id"] = PROTOCOL + "-" + natural.digest(item)[:20]
        repeats.append(item)
    repeats.sort(key=lambda i: natural.digest([PROTOCOL, "repeat", i["item_id"]]))
    return first + repeats


def samples_text() -> str:
    text = ["# Recipient-specific v1: review materials", "",
            "Design stimuli only. No model responses have been collected.", "",
            "All 24 task variants use the exact common wrapper shown in the canonical examples.",
            "Each has voluntary and computer-assigned versions and both recipient questions.",
            "The generator expands these into all 16 independent presentation forms.", "",
            "| Scenario | Domain | Exact request after 'to' | Minutes |",
            "|---|---|---|---:|"]
    for case in scenarios():
        text.append(f"| {case['scenario']} | {case['domain']} | {case['request']} | {case['minutes']} |")
    text.extend(["", "## Canonical experimental prompts", ""])
    for condition, target in product(CONDITIONS, ("R", "S")):
        prompt, _, _ = render(scenarios()[0], condition, target, (0, 0, 0, 0))
        text.extend([f"### {condition} / recipient {target}", "", "```text", prompt, "```", ""])
    text.extend(["## Canonical known-answer controls", "",
                 "Keys belong to these explicit-rule controls only, not to natural-history items.", ""])
    for control in CONTROLS:
        item = make_item(CONTROL_CASE, control, "R", (0, 0, 0, 0), "control")
        text.extend([f"### {control}; semantic key {item['expected_private']}", "",
                     "```text", item["prompt"], "```", ""])
    return "\n".join(text).rstrip() + "\n"


def manifest() -> dict[str, Any]:
    items = generate_items()
    return {
        "protocol": PROTOCOL, "status": "design_snapshot_not_collection_freeze",
        "prepared_utc_date": "2026-10-14", "baseline_commit": BASE,
        "n_requests": len(items), "n_scenarios": len(scenarios()),
        "kind_counts": dict(Counter(i["kind"] for i in items)),
        "n_distinct_request_bodies": len({natural.digest(natural.request_body(i)) for i in items}),
        "items_jsonl_sha256": natural.stream_hash(items),
        "request_bodies_jsonl_sha256": natural.stream_hash([natural.request_body(i) for i in items]),
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE},
        "collection_implemented": False,
        "design_budget_usd": 25,
        "planning_input_tokens_per_request": 2000,
        "max_output_tokens_per_request": 256,
        "standard_price_usd_per_million": {"input": 3, "output": 15},
        "conditional_planning_ceiling_usd": round(len(items) * (2000 * 3 + 256 * 15) / 1e6, 4),
    }


def check() -> dict[str, Any]:
    current = manifest()
    if json.loads((ROOT / SNAPSHOT).read_text()) != current:
        raise ValueError("Design snapshot mismatch; do not silently rewrite reviewed materials")
    if (ROOT / SAMPLES).read_text() != samples_text():
        raise ValueError("Sample prompts do not reproduce")
    return current


def score(answers: dict[str, str]) -> dict[str, Any]:
    """Score semantic answers, not rationales. Missing IDs remain in scheduled denominators.

    Keys are item IDs; values are P/Q/equal/insufficient/invalid. This is an offline
    semantic scorer, not a raw-response integrity auditor or model-data report runner.
    """
    items = generate_items()
    ids = {i["item_id"] for i in items}
    if set(answers) - ids or any(v not in SEMANTICS[:-1] for v in answers.values()):
        raise ValueError("Unknown item ID or semantic response")

    def answer(item: dict[str, Any]) -> str:
        return answers.get(item["item_id"], "missing")

    def counts(selected: list[dict[str, Any]]) -> dict[str, int]:
        c = Counter(answer(i) for i in selected)
        return {s: c[s] for s in SEMANTICS}

    def paired(selected: list[dict[str, Any]], factor: str) -> dict[str, int]:
        lookup = {(i["scenario"], i["condition"], i["recipient"], tuple(i["form"].values())): i
                  for i in selected}
        total = comparable = disagreement = 0
        k = FACTORS.index(factor)
        for key, left in lookup.items():
            form = key[3]
            if form[k]:
                continue
            other = list(form)
            other[k] = 1
            right = lookup[(key[0], key[1], key[2], tuple(other))]
            a, b = answer(left), answer(right)
            total += 1
            if a not in ("missing", "invalid") and b not in ("missing", "invalid"):
                comparable += 1
                disagreement += a != b
        return {"scheduled": total, "comparable": comparable, "disagreements": disagreement}

    families: list[dict[str, Any]] = []
    primary = [i for i in items if i["kind"] == "primary"]
    for case in scenarios():
        conditions: dict[str, Any] = {}
        for condition in CONDITIONS:
            selected = [i for i in primary if i["scenario"] == case["scenario"]
                        and i["condition"] == condition]
            cells = {target: counts([i for i in selected if i["recipient"] == target])
                     for target in ("R", "S")}
            nets = {target: (cell["P"] - cell["Q"]) / 16 for target, cell in cells.items()}
            lookup = {(tuple(i["form"].values()), i["recipient"]): i for i in selected}
            matrix = {a: {b: 0 for b in SEMANTICS} for a in SEMANTICS}
            for form in FORMS:
                matrix[answer(lookup[(form, "R")])][answer(lookup[(form, "S")])] += 1
            conditions[condition] = {
                "counts": cells, "nets": nets, "recipient_index": (nets["R"] - nets["S"]) / 2,
                "both_predicted_signs": nets["R"] > 0 and nets["S"] < 0,
                "predicted_crossovers": matrix["P"]["Q"],
                "reverse_crossovers": matrix["Q"]["P"], "pair_matrix": matrix,
            }
        families.append({"scenario": case["scenario"], "domain": case["domain"],
                         "conditions": conditions,
                         "voluntary_minus_assigned": conditions["voluntary"]["recipient_index"]
                         - conditions["assigned"]["recipient_index"]})
    controls = {}
    for category in CONTROLS:
        selected = [i for i in items if i["kind"] == "control" and i["condition"] == category]
        controls[category] = {"counts": counts(selected), "scheduled": len(selected),
                              "correct": sum(answer(i) == i["expected_private"] for i in selected)}
    repeat_pairs = [(answers.get(i["repeat_of"], "missing"), answer(i))
                    for i in items if i["kind"] == "repeat"]
    comparable = [(a, b) for a, b in repeat_pairs
                  if a not in ("missing", "invalid") and b not in ("missing", "invalid")]
    means = {c: sum(f["conditions"][c]["recipient_index"] for f in families) / len(families)
             for c in CONDITIONS}
    return {
        "protocol": PROTOCOL, "data_status": "offline_semantic_summary_not_integrity_audited",
        "scheduled": len(items), "provided": len(answers),
        "primary_counts": counts(primary), "families": families,
        "mean_recipient_index": means,
        "mean_voluntary_minus_assigned": means["voluntary"] - means["assigned"],
        "families_both_predicted_signs": {
            c: sum(f["conditions"][c]["both_predicted_signs"] for f in families) for c in CONDITIONS},
        "controls": controls,
        "control_quality_flag": all(c["correct"] >= 30 for c in controls.values()),
        "presentation_pairs": {c: {factor: paired([i for i in primary if i["condition"] == c], factor)
                                    for factor in FACTORS} for c in CONDITIONS},
        "repeat_pairs": {"scheduled": len(repeat_pairs), "comparable": len(comparable),
                         "disagreements": sum(a != b for a, b in comparable)},
        "index_warning": "C/D/invalid/missing contribute zero to numerators, but stay distinct. "
        "Missing or invalid responses are not evidence of equality or a null effect.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "generate", "score"))
    parser.add_argument("--out", type=Path, default=Path("runs/recipient-specific-v1-design"))
    parser.add_argument("--answers", type=Path)
    args = parser.parse_args()
    info = check()
    if args.command == "check":
        print(json.dumps({k: v for k, v in info.items() if k != "source_sha256"}, indent=2))
    elif args.command == "generate":
        args.out.mkdir(parents=True, exist_ok=False)
        items = generate_items()
        for name, values in (("items.jsonl", items),
                             ("request-bodies.jsonl", [natural.request_body(i) for i in items])):
            (args.out / name).write_text("".join(natural.wire(i) + "\n" for i in values))
        (args.out / "design-snapshot.json").write_text(json.dumps(info, indent=2) + "\n")
        print(f"Generated {len(items)} planned requests offline in {args.out}")
    else:
        if args.answers is None:
            parser.error("score requires --answers containing an item-ID-to-semantic-answer JSON object")
        print(json.dumps(score(json.loads(args.answers.read_text())), indent=2))


if __name__ == "__main__":
    main()
