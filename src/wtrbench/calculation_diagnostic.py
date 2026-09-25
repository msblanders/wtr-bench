"""24 explicit-rule controls with returned option values and a final choice.

python -m wtrbench.calculation_diagnostic generate
python -m wtrbench.calculation_diagnostic run [--resume]
python -m wtrbench.calculation_diagnostic inspect PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wtrbench.calibration import FORMATS, Recipient, ReplyFormat, calibration_hash
from wtrbench.run import RunExists
from wtrbench.structured_calibration import (
    LABELS,
    MODEL,
    APIOutput,
    StructuredItem,
    StructuredResponder,
    StructuredResponse,
    _unique_object,
)
from wtrbench.structured_calibration import (
    ending as source_ending,
)
from wtrbench.structured_calibration import (
    generate_items as source_items,
)

PROTOCOL = "calculation-diagnostic-v1"
OUT = Path("runs/calculation-diagnostic")
VALUE_A = "option_a_value_to_sam"
VALUE_B = "option_b_value_to_sam"
# Independent scoring specification, checked against all source prompts in tests.
RULES = {"rule_0.5_2": (0.5, 2), "rule_0.5_8": (0.5, 8),
         "rule_1_5": (1.0, 5), "rule_1_20": (1.0, 20),
         "rule_2_10": (2.0, 10), "rule_2_40": (2.0, 40)}


def ending(fmt: ReplyFormat) -> str:
    labels = "A or B" if fmt == "letter" else "SAM or YOU"
    recipient = ", naming the recipient in the selected option" if fmt == "recipient" else ""
    return ("Calculate the value to Sam of each displayed option using the stated rule. "
            f'Return a JSON object with numeric fields "{VALUE_A}" and "{VALUE_B}", '
            f'followed by "answer", whose value is {labels}{recipient}. '
            "Do not include an explanation or other fields.")


def request_settings(fmt: ReplyFormat) -> dict[str, Any]:
    return {
        "temperature": 0, "max_tokens": 256,
        "system": "For each question, calculate the option values and return only the requested JSON.",
        "output_config": {"format": {"type": "json_schema", "schema": {
            "type": "object", "properties": {
                VALUE_A: {"type": "number"}, VALUE_B: {"type": "number"},
                "answer": {"type": "string", "enum": list(LABELS[fmt])},
            }, "required": [VALUE_A, VALUE_B, "answer"], "additionalProperties": False,
        }}},
    }


class CalculationItem(StructuredItem):
    source_structured_item_id: str
    expected_value_a: float
    expected_value_b: float


def generate_items() -> list[CalculationItem]:
    items = []
    for old in source_items():
        if old.kind != "explicit_rule":
            continue
        weight, own_points = RULES[old.case]
        sam_value, you_value = float(own_points), weight * 10
        expected = "SAM" if sam_value > you_value else "YOU"
        if sam_value == you_value or old.expected_recipient != expected:
            raise ValueError("Source truth key disagrees with independent rule calculation")
        if not old.prompt.endswith(source_ending(old.reply_format)):
            raise ValueError("Source reply instruction changed")
        a, b = (sam_value, you_value) if old.sam_first else (you_value, sam_value)
        fields = old.model_dump(exclude={"item_id"})
        fields.update(source_structured_item_id=old.item_id, expected_value_a=a, expected_value_b=b,
                      prompt=old.prompt.removesuffix(source_ending(old.reply_format))
                      + ending(old.reply_format))
        digest = hashlib.sha256(json.dumps(
            {"protocol": PROTOCOL, **fields}, sort_keys=True).encode()).hexdigest()[:16]
        items.append(CalculationItem.model_validate({"item_id": "wtrcalc-" + digest, **fields}))
    if len(items) != 24 or {i.case for i in items} != set(RULES):
        raise ValueError("Expected the original six rule cases in all four conditions")
    return items


def config(items: list[CalculationItem]) -> dict[str, Any]:
    return {"mode": PROTOCOL, "model": MODEL, "n_items": len(items),
            "items_hash": calibration_hash(list(items)), "transport_max_retries": 0,
            "requests": {fmt: request_settings(fmt) for fmt in FORMATS}}


def request_body(item: CalculationItem) -> dict[str, Any]:
    # Truth keys, source IDs and expected values are never sent to the model.
    return {"model": MODEL, **request_settings(item.reply_format),
            "messages": [{"role": "user", "content": item.prompt}]}


class CalculationResponse(StructuredResponse):
    option_a_value_to_sam: float | None
    option_b_value_to_sam: float | None


def _finite_number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def decode(item: CalculationItem, output: APIOutput) -> CalculationResponse:
    body = output.api_response
    blocks = body.get("content", [])
    raw = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    answer = None
    a = b = None
    if (body.get("stop_reason") == "end_turn" and len(blocks) == 1
            and blocks[0].get("type") == "text"):
        try:
            value = json.loads(raw, object_pairs_hook=_unique_object)
            if (isinstance(value, dict) and set(value) == {VALUE_A, VALUE_B, "answer"}
                    and _finite_number(value[VALUE_A]) and _finite_number(value[VALUE_B])
                    and isinstance(value["answer"], str)
                    and value["answer"].upper() in LABELS[item.reply_format]):
                a, b = float(value[VALUE_A]), float(value[VALUE_B])
                answer = value["answer"].upper()
        except (ValueError, TypeError, OverflowError):
            pass
    recipient: Recipient | None = None
    if answer is not None:
        if item.reply_format == "recipient":
            recipient = "SAM" if answer == "SAM" else "YOU"
        else:
            recipient = "SAM" if (answer == "A") == item.sam_first else "YOU"
    return CalculationResponse(
        raw=raw, stop_reason=body.get("stop_reason"), returned_model=body.get("model"),
        request_id=output.request_id, usage=body.get("usage"), item_id=item.item_id,
        model=MODEL, reply_format=item.reply_format, recipient=recipient, answer=answer,
        request_body=request_body(item), api_response=body,
        option_a_value_to_sam=a, option_b_value_to_sam=b,
    )


class CalculationResponder(StructuredResponder):
    def __call__(self, item: StructuredItem) -> APIOutput:
        if not isinstance(item, CalculationItem):
            raise TypeError("Calculation diagnostic requires its own item type")
        body = request_body(item)
        msg = self.client.messages.create(
            model=MODEL, max_tokens=body["max_tokens"], system=body["system"],
            messages=body["messages"], output_config=body["output_config"],
            extra_body={"temperature": body["temperature"]},
        )
        return APIOutput(api_response=msg.model_dump(mode="json"),
                         request_id=getattr(msg, "_request_id", None))


def validate(items: list[CalculationItem], rows: list[CalculationResponse]
             ) -> dict[str, CalculationResponse]:
    known = {i.item_id: i for i in items}
    if len(known) != len(items):
        raise ValueError("Duplicate item ID")
    found: dict[str, CalculationResponse] = {}
    request_ids: set[str] = set()
    for row in rows:
        if row.item_id not in known or row.item_id in found:
            raise ValueError("Unknown or duplicate response ID")
        if row.model != MODEL or row.returned_model != MODEL:
            raise ValueError("Response model mismatch")
        if row.request_id is not None:
            if row.request_id in request_ids:
                raise ValueError("Duplicate API request ID")
            request_ids.add(row.request_id)
        rebuilt = decode(known[row.item_id], APIOutput(
            api_response=row.api_response, request_id=row.request_id))
        if rebuilt != row:
            raise ValueError("Response values, decoding, metadata or request body mismatch")
        found[row.item_id] = row
    return found


def load_run(path: Path, items: list[CalculationItem]) -> list[CalculationResponse]:
    saved = json.loads(path.with_suffix(path.suffix + ".config.json").read_text())
    if {k: v for k, v in saved.items() if k != "started"} != config(items):
        raise ValueError("Item set or request protocol changed; use the recorded source revision")
    rows = [CalculationResponse.model_validate_json(s) for s in path.read_text().splitlines()
            if s.strip()]
    validate(items, rows)
    return rows


def run(items: list[CalculationItem], responder: Callable[[CalculationItem], APIOutput], path: Path,
        *, resume: bool = False) -> list[CalculationResponse]:
    validate(items, [])
    cfg_path = path.with_suffix(path.suffix + ".config.json")
    if path.exists():
        if not resume:
            raise RunExists(f"{path} exists; use --resume for this exact protocol")
        old = validate(items, load_run(path, items))
    else:
        if cfg_path.exists():
            raise RunExists(f"Orphaned configuration {cfg_path}; choose a new output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(
            {**config(items), "started": datetime.now(UTC).isoformat()}, indent=2) + "\n")
        path.touch(exist_ok=False)
        old = {}
    rows = []
    for item in items:
        if item.item_id in old:
            rows.append(old[item.item_id])
            continue
        row = decode(item, responder(item))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(row.model_dump_json() + "\n")
        rows.append(row)
        validate(items, rows)
    return rows


def diagnostics(item: CalculationItem, row: CalculationResponse) -> dict[str, bool | None]:
    a, b = row.option_a_value_to_sam, row.option_b_value_to_sam
    if row.recipient is None or a is None or b is None:
        return {"values_correct": None, "choice_correct": None, "follows_values": None,
                "reported_tie": None}
    chosen_a = (row.recipient == "SAM") == item.sam_first
    return {"values_correct": a == item.expected_value_a and b == item.expected_value_b,
            "choice_correct": row.recipient == item.expected_recipient,
            "follows_values": None if a == b else chosen_a == (a > b),
            "reported_tie": a == b}


def report(items: list[CalculationItem], rows: list[CalculationResponse]) -> str:
    found = validate(items, rows)
    checks = {i.item_id: diagnostics(i, found[i.item_id]) for i in items if i.item_id in found}
    lines = ["# Explicit-rule calculation diagnostic", "",
             f"Protocol: `{PROTOCOL}`; model: `{MODEL}`.",
             (f"Recorded {len(rows)}/{len(items)} responses; "
              f"item hash `{calibration_hash(list(items))}`."),
             "Six previously examined rule cases; no social judgments or pilot calls.",
             "Returned values are task outputs, not a record of internal reasoning.", "",
             "Stop reasons: " + str(dict(Counter(r.stop_reason for r in rows))), ""]
    for key in ("input_tokens", "output_tokens"):
        total = sum(v for r in rows if r.usage and isinstance(v := r.usage.get(key), int))
        lines.append(f"- {key}: {total}")
    lines += ["", "## Summary by format and option order", "",
              "Correctness denominators include every planned item. Missing and unusable",
              "are separate. Ranking consistency excludes reported ties and unusable answers.", "",
              ("| Format | Sam position | Planned | Missing | Unusable | Both values correct | "
               "Choice correct | Follows reported ranking | Reported ties |"),
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for fmt in FORMATS:
        for position in (None, True, False):
            subset = [i for i in items if i.reply_format == fmt
                      and (position is None or i.sam_first == position)]
            cs = [checks[i.item_id] for i in subset if i.item_id in checks]
            missing = sum(i.item_id not in found for i in subset)
            unusable = sum(c["choice_correct"] is None for c in cs)
            values = sum(c["values_correct"] is True for c in cs)
            choice = sum(c["choice_correct"] is True for c in cs)
            follows = sum(c["follows_values"] is True for c in cs)
            ranked = sum(c["follows_values"] is not None for c in cs)
            ties = sum(c["reported_tie"] is True for c in cs)
            label = "both" if position is None else ("first" if position else "second")
            lines.append(f"| {fmt} | {label} | {len(subset)} | {missing} | {unusable} | "
                         f"{values}/{len(subset)} | {choice}/{len(subset)} | "
                         f"{follows}/{ranked} | {ties} |")
    lines += ["", "## Joint correctness (usable answers only)", "",
              ("| Format | Correct values + correct choice | Correct values + wrong choice | "
               "Wrong values + correct choice | Wrong values + wrong choice |"),
              "|---|---:|---:|---:|---:|"]
    for fmt in FORMATS:
        counts = Counter((checks[i.item_id]["values_correct"], checks[i.item_id]["choice_correct"])
                         for i in items if i.reply_format == fmt and i.item_id in checks
                         and checks[i.item_id]["choice_correct"] is not None)
        vals = [counts[pair] for pair in ((True, True), (True, False), (False, True), (False, False))]
        lines.append(f"| {fmt} | " + " | ".join(map(str, vals)) + " |")
    lines += ["", "## Final-choice option-order consistency", ""]
    for fmt in FORMATS:
        pairs: dict[str, dict[bool, Recipient]] = defaultdict(dict)
        for item in items:
            row = found.get(item.item_id)
            if item.reply_format == fmt and row and row.recipient:
                pairs[item.case][item.sam_first] = row.recipient
        complete = [p for p in pairs.values() if len(p) == 2]
        disagreements = sum(p[True] != p[False] for p in complete)
        lines.append(f"- {fmt}: {disagreements}/{len(complete)} disagreements/complete pairs "
                     "(6 pairs planned).")
    lines += ["", "## Every planned response", "",
              "Values are in displayed A/B order; final answers are also decoded to recipients.", "",
              ("| Case | Format | Sam first | True A / B | Returned A / B | Answer | Recipient | "
               "Values correct | Choice correct | Follows ranking |"),
              "|---|---|---|---|---|---|---|---|---|---|"]
    for item in items:
        row = found.get(item.item_id)
        base = (f"| {item.case} | {item.reply_format} | {item.sam_first} | "
                f"{item.expected_value_a:g} / {item.expected_value_b:g} | ")
        if row is None or row.recipient is None:
            label = "missing" if row is None else "unusable"
            lines.append(base + f"{label} | — | — | — | — | — |")
            continue
        check = checks[item.item_id]
        ranking = "tie" if check["reported_tie"] else str(check["follows_values"])
        lines.append(base + f"{row.option_a_value_to_sam:g} / {row.option_b_value_to_sam:g} | "
                     f"{row.answer} | {row.recipient} | {check['values_correct']} | "
                     f"{check['choice_correct']} | {ranking} |")
    lines += ["", "## Raw replies", ""]
    lines.extend(f"- {r.item_id}: {r.raw!r} (stop={r.stop_reason})" for r in rows)
    lines += ["", "No automatic progression decision is made. Review calculation errors, choice",
              "inconsistencies, ties, missingness and order effects. Success on this scaffolded",
              "task does not validate the earlier answer-only protocol or the social measure.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate")
    run_args = sub.add_parser("run")
    run_args.add_argument("--resume", action="store_true")
    run_args.add_argument("--out", type=Path, default=OUT / "responses.jsonl")
    inspect_args = sub.add_parser("inspect")
    inspect_args.add_argument("path", type=Path)
    args = parser.parse_args()
    items = generate_items()
    if args.command == "generate":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items))
        (OUT / "protocol.json").write_text(json.dumps(config(items), indent=2) + "\n")
        print(f"{len(items)} calculation controls; hash {calibration_hash(list(items))}; no API calls")
    elif args.command == "inspect":
        print(report(items, load_run(args.path, items)))
    else:
        rows = run(items, CalculationResponder(), args.out, resume=args.resume)
        rendered = report(items, rows)
        args.out.with_suffix(".md").write_text(rendered)
        print(rendered)


if __name__ == "__main__":
    main()
