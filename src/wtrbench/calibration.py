"""Exploratory answer-format calibration, separate from the inference pilot.

48 known-answer controls plus 24 prompts from already examined debug cases.
Crosses option order with A/B versus SAM/YOU replies. No valuation estimates
or confirmatory comparisons are calculated here.

    python -m wtrbench.calibration generate
    python -m wtrbench.calibration run MODEL [--resume]
    python -m wtrbench.calibration inspect PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from wtrbench.inference import DEBUG_TASKS, PILOT_LADDER, Probe, generate_inference_items
from wtrbench.run import FORMAT_SYSTEM, AnthropicResponder, ModelOutput, RunExists, parse_choice

ReplyFormat = Literal["letter", "recipient"]
Recipient = Literal["SAM", "YOU"]
FORMATS: tuple[ReplyFormat, ...] = ("letter", "recipient")
RECIPIENT_SYSTEM = FORMAT_SYSTEM.replace(
    "one uppercase letter: A or B", "one uppercase word: SAM or YOU"
)
SYSTEMS = {"letter": FORMAT_SYSTEM, "recipient": RECIPIENT_SYSTEM}
LETTER_END = "Answer with A or B only."
RECIPIENT_END = "Answer with SAM or YOU only, naming the recipient in the selected option."


class CalibrationItem(BaseModel):
    item_id: str
    case: str
    kind: Literal["recipient_lookup", "quantity", "explicit_rule", "debug_bridge"]
    reply_format: ReplyFormat
    sam_first: bool
    prompt: str
    expected_recipient: Recipient | None
    source_item_id: str | None = None


class CalibrationResponse(ModelOutput):
    item_id: str
    model: str
    reply_format: ReplyFormat
    recipient: Recipient | None


def generate_calibration_items() -> list[CalibrationItem]:
    items: list[CalibrationItem] = []

    def add(case: str, kind: str, sam_first: bool, prompt: str,
            expected: Recipient | None, source: str | None = None) -> None:
        for fmt in FORMATS:
            rendered = prompt if fmt == "letter" else prompt.replace(LETTER_END, RECIPIENT_END)
            fields = {"case": case, "kind": kind, "reply_format": fmt,
                      "sam_first": sam_first, "prompt": rendered,
                      "expected_recipient": expected, "source_item_id": source}
            digest = hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:16]
            items.append(CalibrationItem.model_validate({"item_id": "wtrcal-" + digest, **fields}))

    def control(case: str, kind: str, amount: int, question: str,
                expected: Recipient, rule: str = "") -> None:
        for sam_first in (True, False):
            opts = [f"Sam receives {amount} points.", "You receive 10 points."]
            if not sam_first:
                opts.reverse()
            prompt = ("Sam is an acquaintance. " + rule + "\n\nThe options are:\n"
                      f"(A) {opts[0]}\n(B) {opts[1]}\n{question} {LETTER_END}")
            add(case, kind, sam_first, prompt, expected)

    recipients: tuple[Recipient, ...] = ("SAM", "YOU")
    for amount in (2, 20):
        for who in recipients:
            target = "Sam" if who == "SAM" else "you"
            control(f"lookup_{who}_{amount}", "recipient_lookup", amount,
                    f"Which option gives points to {target}?", who)
        control(f"quantity_{amount}", "quantity", amount,
                "Which option awards the larger number of points?",
                "SAM" if amount > 10 else "YOU")
    for weight, amounts in ((0.5, (2, 8)), (1.0, (5, 20)), (2.0, (10, 40))):
        rule = (f"For this hypothetical decision, Sam assigns value equal to Sam's points "
                f"plus {weight:g} times your points, and always chooses the option with the "
                "greater value. The recipient not named in an option receives 0 points.")
        for amount in amounts:
            control(f"rule_{weight:g}_{amount}", "explicit_rule", amount,
                    "Which option will Sam choose?", "SAM" if amount > weight * 10 else "YOU",
                    rule)

    # Only previously examined boxes/debug-set cases; never confirmatory items.
    debug = generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))
    for it in debug:
        if it.probe != Probe.INFER:
            continue
        if (it.cause is not None and it.cause.value in ("unable", "unwilling")
                and it.realized_ratio in (0.1, 1.0)):
            case = f"boxes_{it.cause.value}_{it.realized_ratio:g}"
        elif (it.family == "aggregate" and it.totals is not None and it.totals.value == "t1"
              and it.choices_swapped is False and it.realized_ratio == 0.5):
            assert it.diagnostic is not None
            case = f"debug_numeric_{it.diagnostic.value}_0.5"
        else:
            continue
        add(case, "debug_bridge", it.keyed_option == "A", it.prompt, None, it.item_id)
    return items


def calibration_hash(items: list[CalibrationItem]) -> str:
    return hashlib.sha256("".join(i.item_id for i in items).encode()).hexdigest()[:16]


def decode_recipient(item: CalibrationItem, raw: str) -> Recipient | None:
    if item.reply_format == "recipient":
        value = raw.strip().upper()
        if value == "SAM":
            return "SAM"
        return "YOU" if value == "YOU" else None
    letter = parse_choice(raw)
    if letter is None:
        return None
    return "SAM" if (letter == "A") == item.sam_first else "YOU"


def load_calibration_responses(path: Path) -> list[CalibrationResponse]:
    return [CalibrationResponse.model_validate_json(s) for s in path.read_text().splitlines()
            if s.strip()]


def validate_responses(items: list[CalibrationItem], rows: list[CalibrationResponse],
                       model: str | None = None) -> dict[str, CalibrationResponse]:
    known = {it.item_id: it for it in items}
    if len(known) != len(items):
        raise ValueError("Duplicate calibration item IDs")
    found: dict[str, CalibrationResponse] = {}
    for row in rows:
        if row.item_id not in known or row.item_id in found:
            raise ValueError("Unknown or duplicate response ID")
        it = known[row.item_id]
        if row.reply_format != it.reply_format or row.recipient != decode_recipient(it, row.raw):
            raise ValueError("Response format or decoded answer mismatch")
        if model is not None and row.model != model:
            raise ValueError("Response model mismatch")
        found[row.item_id] = row
    return found


def run_calibration(items: list[CalibrationItem], responder: Callable[[CalibrationItem], ModelOutput],
                    model: str, path: Path, *, resume: bool = False) -> list[CalibrationResponse]:
    cfg = {"mode": "calibration-v1", "model": model, "n_items": len(items),
           "items_hash": calibration_hash(items), "requests": {
               fmt: {"temperature": 0, "max_tokens": 64, "system": SYSTEMS[fmt]}
               for fmt in FORMATS}}
    cfg_path = path.with_suffix(path.suffix + ".config.json")
    old: dict[str, CalibrationResponse] = {}
    if path.exists():
        if not resume:
            raise RunExists(f"{path} exists; pass --resume to continue this exact run")
        prior = json.loads(cfg_path.read_text())
        if {k: v for k, v in prior.items() if k != "started"} != cfg:
            raise ValueError("Model, item set or request protocol changed; refusing resume")
        old = validate_responses(items, load_calibration_responses(path), model)
    else:
        if cfg_path.exists():
            raise RunExists(f"Orphaned configuration {cfg_path}; choose a new output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps({**cfg, "started": datetime.now(UTC).isoformat()}, indent=2))
        path.touch(exist_ok=False)
    rows = []
    for it in items:
        if it.item_id in old:
            rows.append(old[it.item_id])
            continue
        output = responder(it)
        row = CalibrationResponse(**output.model_dump(), item_id=it.item_id, model=model,
                                  reply_format=it.reply_format,
                                  recipient=decode_recipient(it, output.raw))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(row.model_dump_json() + "\n")
        rows.append(row)
    return rows


def calibration_report(items: list[CalibrationItem], rows: list[CalibrationResponse]) -> str:
    found = validate_responses(items, rows)
    lines = ["# Exploratory response calibration", "",
             f"Recorded {len(rows)}/{len(items)} responses; item hash `{calibration_hash(items)}`.",
             "No WTR estimates or confirmatory tests are computed.", "",
             "Stop reasons: " + str(dict(Counter(r.stop_reason for r in rows))), ""]
    for key in ("input_tokens", "output_tokens"):
        total = sum(v for r in rows if r.usage and isinstance(v := r.usage.get(key), int))
        lines.append(f"- {key}: {total}")
    lines += ["", "## Known-answer controls", "",
              "Accuracy uses all planned items as denominator; missing and unparsed answers",
              "are also shown. Order agreement uses only pairs with two parsed responses.", "",
              ("| Format | Control | Correct / planned | Missing or unparsed | "
               "Order disagreements / complete pairs |"),
              "|---|---|---:|---:|---:|"]
    for fmt in FORMATS:
        for kind in ("recipient_lookup", "quantity", "explicit_rule"):
            subset = [i for i in items if i.reply_format == fmt and i.kind == kind]
            answers = [found.get(i.item_id) for i in subset]
            correct = sum(r is not None and r.recipient == i.expected_recipient
                          for i, r in zip(subset, answers, strict=True))
            missing = sum(r is None or r.recipient is None for r in answers)
            dis, complete = _order_counts(subset, found)
            lines.append(f"| {fmt} | {kind} | {correct}/{len(subset)} | {missing} "
                         f"| {dis}/{complete} |")
    lines += ["", "## Previously examined debug cases (no correct answer assigned)", "",
              "SAM/YOU names the payoff recipient, not the responding model's own choice.", "",
              "| Case | Format | Sam option first | Sam option second | Order agreement |",
              "|---|---|---|---|---|"]
    cases = sorted({i.case for i in items if i.kind == "debug_bridge"})
    for case in cases:
        for fmt in FORMATS:
            pair = {i.sam_first: found.get(i.item_id) for i in items
                    if i.case == case and i.reply_format == fmt}
            a, b = pair.get(True), pair.get(False)
            pair_complete = (a is not None and b is not None and a.recipient is not None
                             and b.recipient is not None)
            agree = (str(a.recipient == b.recipient)
                     if pair_complete and a and b else "undetermined")
            labels = [r.recipient if r and r.recipient else "missing/unparsed" for r in (a, b)]
            lines.append(f"| {case} | {fmt} | {labels[0]} | {labels[1]} | {agree} |")
    lines += ["", "## Raw response counts", ""]
    for fmt in FORMATS:
        lines.append(f"- {fmt}: {dict(Counter(r.raw for r in rows if r.reply_format == fmt))!r}")
    lines += ["", "## Unparsed responses", ""]
    lines.extend(f"- {r.item_id}: {r.raw!r} (stop={r.stop_reason})"
                 for r in rows if r.recipient is None)
    return "\n".join(lines) + "\n"


def _order_counts(items: list[CalibrationItem], found: dict[str, CalibrationResponse]
                  ) -> tuple[int, int]:
    pairs: dict[str, dict[bool, Recipient]] = defaultdict(dict)
    for it in items:
        row = found.get(it.item_id)
        if row and row.recipient:
            pairs[it.case][it.sam_first] = row.recipient
    complete = [p for p in pairs.values() if len(p) == 2]
    return sum(p[True] != p[False] for p in complete), len(complete)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate")
    run_args = sub.add_parser("run")
    run_args.add_argument("model")
    run_args.add_argument("--resume", action="store_true")
    run_args.add_argument("--out", type=Path)
    inspect_args = sub.add_parser("inspect")
    inspect_args.add_argument("path", type=Path)
    args = parser.parse_args()
    items = generate_calibration_items()
    if args.command == "generate":
        out = Path("runs/calibration")
        out.mkdir(parents=True, exist_ok=True)
        (out / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items))
        print(f"{len(items)} calibration items; hash {calibration_hash(items)}; no API calls")
        return
    if args.command == "inspect":
        cfg = json.loads(args.path.with_suffix(args.path.suffix + ".config.json").read_text())
        if cfg["items_hash"] != calibration_hash(items):
            raise ValueError("Item hash changed; inspect with the run's source revision")
        rows = load_calibration_responses(args.path)
        validate_responses(items, rows, cfg["model"])
        print(calibration_report(items, rows))
        return
    path = args.out or Path("runs/calibration") / (args.model.replace("/", "_") + ".jsonl")
    responders = {fmt: AnthropicResponder(args.model, format_system=SYSTEMS[fmt]) for fmt in FORMATS}
    rows = run_calibration(items, lambda i: responders[i.reply_format](i), args.model, path,
                           resume=args.resume)
    report = calibration_report(items, rows)
    path.with_suffix(".md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
