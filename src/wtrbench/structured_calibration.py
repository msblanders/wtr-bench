"""Structured-answer follow-up to calibration-v1; no inference pilot calls.

python -m wtrbench.structured_calibration generate
python -m wtrbench.structured_calibration run [--resume]
python -m wtrbench.structured_calibration inspect PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from wtrbench.calibration import (
    FORMATS,
    LETTER_END,
    RECIPIENT_END,
    CalibrationItem,
    CalibrationResponse,
    Recipient,
    ReplyFormat,
    calibration_hash,
    generate_calibration_items,
)
from wtrbench.run import RunExists

MODEL = "claude-sonnet-4-5-20250929"
PROTOCOL = "calibration-structured-v1"
OUT = Path("runs/calibration-structured")
LABELS = {"letter": ["A", "B"], "recipient": ["SAM", "YOU"]}


def ending(fmt: ReplyFormat) -> str:
    labels = "A or B" if fmt == "letter" else "SAM or YOU"
    recipient = ", naming the recipient in the selected option" if fmt == "recipient" else ""
    return (f'Return a JSON object with exactly one field, "answer", whose value is {labels}'
            f"{recipient}. Do not include an explanation or other fields.")


def request_settings(fmt: ReplyFormat) -> dict[str, Any]:
    return {
        "temperature": 0,
        "max_tokens": 256,
        "system": "For each question, " + ending(fmt),
        "output_config": {"format": {"type": "json_schema", "schema": {
            "type": "object",
            "properties": {"answer": {"type": "string", "enum": list(LABELS[fmt])}},
            "required": ["answer"],
            "additionalProperties": False,
        }}},
    }


class StructuredItem(CalibrationItem):
    source_calibration_item_id: str


def generate_items() -> list[StructuredItem]:
    items = []
    for old in generate_calibration_items():
        suffix = LETTER_END if old.reply_format == "letter" else RECIPIENT_END
        if not old.prompt.endswith(suffix):
            raise ValueError("Original calibration reply instruction changed")
        fields = old.model_dump(exclude={"item_id"})
        fields.update(source_calibration_item_id=old.item_id,
                      prompt=old.prompt.removesuffix(suffix) + ending(old.reply_format))
        digest = hashlib.sha256(json.dumps(
            {"protocol": PROTOCOL, **fields}, sort_keys=True).encode()).hexdigest()[:16]
        items.append(StructuredItem.model_validate({"item_id": "wtrcaljson-" + digest, **fields}))
    return items


def config(items: list[StructuredItem]) -> dict[str, Any]:
    return {"mode": PROTOCOL, "model": MODEL, "n_items": len(items),
            "items_hash": calibration_hash(list(items)), "transport_max_retries": 0,
            "requests": {fmt: request_settings(fmt) for fmt in FORMATS}}


def request_body(item: StructuredItem) -> dict[str, Any]:
    return {"model": MODEL, **request_settings(item.reply_format),
            "messages": [{"role": "user", "content": item.prompt}]}


class APIOutput(BaseModel):
    api_response: dict[str, Any]
    request_id: str | None = None


class StructuredResponse(CalibrationResponse):
    answer: str | None
    request_body: dict[str, Any]
    api_response: dict[str, Any]


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode(item: StructuredItem, output: APIOutput) -> StructuredResponse:
    body = output.api_response
    blocks = body.get("content", [])
    raw = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    answer = None
    if (body.get("stop_reason") == "end_turn" and len(blocks) == 1
            and blocks[0].get("type") == "text"):
        try:
            value = json.loads(raw, object_pairs_hook=_unique_object)
            if (isinstance(value, dict) and set(value) == {"answer"}
                    and isinstance(value["answer"], str)
                    and value["answer"].upper() in LABELS[item.reply_format]):
                answer = value["answer"].upper()
        except (ValueError, TypeError):
            pass
    recipient: Recipient | None = None
    if answer is not None:
        if item.reply_format == "recipient":
            recipient = "SAM" if answer == "SAM" else "YOU"
        else:
            recipient = "SAM" if (answer == "A") == item.sam_first else "YOU"
    return StructuredResponse(
        raw=raw, stop_reason=body.get("stop_reason"), returned_model=body.get("model"),
        request_id=output.request_id, usage=body.get("usage"), item_id=item.item_id,
        model=MODEL, reply_format=item.reply_format, recipient=recipient, answer=answer,
        request_body=request_body(item), api_response=body,
    )


class StructuredResponder:
    def __init__(self) -> None:
        from anthropic import Anthropic

        # Failed requests stop the batch; no retries or fallback to unconstrained text.
        self.client = Anthropic(max_retries=0)

    def __call__(self, item: StructuredItem) -> APIOutput:
        body = request_body(item)
        msg = self.client.messages.create(
            model=MODEL, max_tokens=body["max_tokens"], system=body["system"],
            messages=body["messages"], output_config=body["output_config"],
            extra_body={"temperature": body["temperature"]},
        )
        return APIOutput(api_response=msg.model_dump(mode="json"),
                         request_id=getattr(msg, "_request_id", None))


def load_rows(path: Path) -> list[StructuredResponse]:
    return [StructuredResponse.model_validate_json(line) for line in path.read_text().splitlines()
            if line.strip()]


def validate(items: list[StructuredItem], rows: list[StructuredResponse]
             ) -> dict[str, StructuredResponse]:
    known = {i.item_id: i for i in items}
    if len(known) != len(items):
        raise ValueError("Duplicate item ID")
    found: dict[str, StructuredResponse] = {}
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
            raise ValueError("Response decoding, metadata or request body mismatch")
        found[row.item_id] = row
    return found


def load_run(path: Path, items: list[StructuredItem]) -> list[StructuredResponse]:
    saved = json.loads(path.with_suffix(path.suffix + ".config.json").read_text())
    if {k: v for k, v in saved.items() if k != "started"} != config(items):
        raise ValueError("Item set or request protocol changed; use the recorded source revision")
    rows = load_rows(path)
    validate(items, rows)
    return rows


def run(items: list[StructuredItem], responder: Callable[[StructuredItem], APIOutput], path: Path,
        *, resume: bool = False) -> list[StructuredResponse]:
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
        # Persist even an unexpected model before validation stops further requests.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(row.model_dump_json() + "\n")
        rows.append(row)
        validate(items, rows)
    return rows


def _pairs(items: list[StructuredItem], found: dict[str, StructuredResponse]) -> tuple[int, int]:
    pairs: dict[str, dict[bool, Recipient]] = defaultdict(dict)
    for item in items:
        row = found.get(item.item_id)
        if row and row.recipient:
            pairs[item.case][item.sam_first] = row.recipient
    complete = [p for p in pairs.values() if len(p) == 2]
    return sum(p[True] != p[False] for p in complete), len(complete)


def report(items: list[StructuredItem], rows: list[StructuredResponse]) -> str:
    found = validate(items, rows)
    lines = ["# Structured response calibration", "", f"Protocol: `{PROTOCOL}`; model: `{MODEL}`.",
             (f"Recorded {len(rows)}/{len(items)} responses; "
              f"item hash `{calibration_hash(list(items))}`."),
             "No WTR estimates or confirmatory tests are computed.", "",
             "Stop reasons: " + str(dict(Counter(r.stop_reason for r in rows))), ""]
    for key in ("input_tokens", "output_tokens"):
        total = sum(v for r in rows if r.usage and isinstance(v := r.usage.get(key), int))
        lines.append(f"- {key}: {total}")
    lines += ["", "## Known-answer controls", "",
              "Correct/planned includes missing and unusable answers in the denominator.",
              "Order disagreements include only pairs with two usable answers.", "",
              "| Format | Control | Correct/planned | Missing | Unusable | Disagree/complete |",
              "|---|---|---:|---:|---:|---:|"]
    for fmt in FORMATS:
        for kind in ("recipient_lookup", "quantity", "explicit_rule"):
            subset = [i for i in items if i.reply_format == fmt and i.kind == kind]
            correct = sum(i.item_id in found and found[i.item_id].recipient == i.expected_recipient
                          for i in subset)
            missing = sum(i.item_id not in found for i in subset)
            unusable = sum(i.item_id in found and found[i.item_id].recipient is None for i in subset)
            disagree, complete = _pairs(subset, found)
            lines.append(f"| {fmt} | {kind} | {correct}/{len(subset)} | {missing} | {unusable} "
                         f"| {disagree}/{complete} |")
    lines += ["", "## Controls by displayed option order", "",
              "| Format | Control | Sam option position | Correct/planned | Usable/planned |",
              "|---|---|---|---:|---:|"]
    for fmt in FORMATS:
        for kind in ("recipient_lookup", "quantity", "explicit_rule"):
            for first in (True, False):
                subset = [i for i in items if i.reply_format == fmt and i.kind == kind
                          and i.sam_first == first]
                correct = sum(i.item_id in found
                              and found[i.item_id].recipient == i.expected_recipient for i in subset)
                usable = sum(i.item_id in found and found[i.item_id].recipient is not None
                             for i in subset)
                position = "first" if first else "second"
                lines.append(f"| {fmt} | {kind} | {position} | {correct}/{len(subset)} "
                             f"| {usable}/{len(subset)} |")
    lines += ["", "## Existing debug judgments (no correct answer assigned)", "",
              "SAM/YOU denotes the payoff recipient in the predicted choice.", "",
              "| Case | Format | Sam option first | Sam option second | Agreement |",
              "|---|---|---|---|---|"]
    for case in sorted({i.case for i in items if i.kind == "debug_bridge"}):
        for fmt in FORMATS:
            pair = {i.sam_first: found.get(i.item_id) for i in items
                    if i.case == case and i.reply_format == fmt}
            a, b = pair.get(True), pair.get(False)
            agree = (str(a.recipient == b.recipient)
                     if a and b and a.recipient and b.recipient else "undetermined")
            labels = [r.recipient if r and r.recipient else "missing/unusable" for r in (a, b)]
            lines.append(f"| {case} | {fmt} | {labels[0]} | {labels[1]} | {agree} |")
    lines += ["", "## Candidate for full debug (not pilot approval)", ""]
    for fmt in FORMATS:
        controls = [i for i in items if i.reply_format == fmt and i.kind != "debug_bridge"]
        bridge = [i for i in items if i.reply_format == fmt and i.kind == "debug_bridge"]
        correct = sum(i.item_id in found and found[i.item_id].recipient == i.expected_recipient
                      for i in controls)
        disagree, complete = _pairs(bridge, found)
        passed = correct == 24 and complete == 6 and disagree == 0
        lines.append(f"- {fmt}: {'candidate' if passed else 'not ready'} "
                     f"({correct}/24 correct controls; {complete}/6 complete debug pairs; "
                     f"{disagree} disagreements).")
    lines += ["", "## Raw replies", ""]
    for fmt in FORMATS:
        lines.append(f"- {fmt}: " + repr(dict(Counter(r.raw for r in rows if r.reply_format == fmt))))
    lines += ["", "## Unusable responses", ""]
    lines.extend(f"- {r.item_id}: {r.raw!r} (stop={r.stop_reason})"
                 for r in rows if r.recipient is None)
    return "\n".join(lines) + "\n"


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
        print(f"{len(items)} structured calibration items; "
              f"hash {calibration_hash(list(items))}; no API calls")
    elif args.command == "inspect":
        print(report(items, load_run(args.path, items)))
    else:
        rows = run(items, StructuredResponder(), args.out, resume=args.resume)
        rendered = report(items, rows)
        args.out.with_suffix(".md").write_text(rendered)
        print(rendered)


if __name__ == "__main__":
    main()
