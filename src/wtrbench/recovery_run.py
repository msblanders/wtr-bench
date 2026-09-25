"""Frozen transport and provenance for the constructed-partner diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from wtrbench.explanation_calibration import (
    APIOutput,
    _request_matches,
    _unique_object,
    request_settings,
)
from wtrbench.run import Response, RunExists
from wtrbench.validation_recovery import (
    MODEL,
    ORDER_SEED,
    PROTOCOL,
    RecoveryItem,
    generate_items,
    original_history_bounds,
    recovery_report,
    request_body,
)

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/known-partner-recovery-v1.md"
FREEZE = ROOT / "protocols/known-partner-recovery-v1.json"
OUT = Path("runs/validation-recovery")
RESPONDER = "anthropic:" + MODEL


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def items_hash(items: list[RecoveryItem]) -> str:
    return sha("".join(i.item_id for i in items))[:16]


def config(items: list[RecoveryItem]) -> dict[str, Any]:
    return {"mode": PROTOCOL, "model": MODEL, "n_requests": len(items),
            "n_templates": len({i.template_id for i in items}), "items_hash": items_hash(items),
            "counts_by_arm": dict(Counter(i.arm for i in items)), "repetitions": [1, 2],
            "order_seed": ORDER_SEED, "sequence": "two passes, each in fixed hash order",
            "request": request_settings("letter"), "transport_max_retries": 0,
            "analysis_plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
            "stopping_rule": "216 scheduled calls once; no answer-accuracy gate during collection"}


def freeze_manifest(items: list[RecoveryItem]) -> dict[str, Any]:
    return {"config": config(items),
            "items_jsonl_sha256": sha("".join(i.model_dump_json()+"\n" for i in items)),
            "request_bodies_jsonl_sha256": sha("".join(json.dumps(request_body(i))+"\n"
                                                      for i in items))}


def verify_freeze(items: list[RecoveryItem]) -> None:
    expected = freeze_manifest(items)
    saved = json.loads(FREEZE.read_text()) if FREEZE.exists() else None
    if (saved != expected or not _request_matches(
            saved["config"]["request"], expected["config"]["request"])):
        raise ValueError("Recovery freeze differs; use the frozen source revision and plan")


class RecoveryResponse(Response):
    model: str
    template_id: str
    arm: Literal["explicit_weight", "choice_history"]
    profile: str
    history_swapped: bool | None
    repetition: Literal[1, 2]
    brief_basis: str | None
    correct: bool | None
    request_body: dict[str, Any]
    api_response: dict[str, Any]


def decode(item: RecoveryItem, output: APIOutput) -> RecoveryResponse:
    body = output.api_response
    blocks = body.get("content", [])
    raw = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    choice: Literal["A", "B"] | None = None
    basis = None
    if (body.get("stop_reason") == "end_turn" and len(blocks) == 1
            and blocks[0].get("type") == "text"):
        try:
            value = json.loads(raw, object_pairs_hook=_unique_object)
            if (isinstance(value, dict) and list(value) == ["brief_basis", "answer"]
                    and isinstance(value["brief_basis"], str) and value["brief_basis"].strip()
                    and isinstance(value["answer"], str) and value["answer"].upper() in ("A", "B")):
                basis = value["brief_basis"]
                choice = "A" if value["answer"].upper() == "A" else "B"
        except (ValueError, TypeError):
            pass
    return RecoveryResponse(
        item_id=item.item_id, model=MODEL, responder=RESPONDER, template_id=item.template_id,
        arm=item.arm, profile=item.profile, history_swapped=item.history_swapped,
        repetition=item.repetition, raw=raw, brief_basis=basis, choice=choice,
        keyed=None if choice is None else (choice == "A") == item.sam_first,
        correct=None if choice is None else choice == item.expected_answer,
        stop_reason=body.get("stop_reason"), returned_model=body.get("model"),
        request_id=output.request_id, usage=body.get("usage"),
        request_body=request_body(item), api_response=body)


class RecoveryResponder:
    def __init__(self) -> None:
        from anthropic import Anthropic

        self.client = Anthropic(max_retries=0)

    def __call__(self, item: RecoveryItem) -> APIOutput:
        body = request_body(item)
        msg = self.client.messages.create(
            model=MODEL, max_tokens=body["max_tokens"], system=body["system"],
            messages=body["messages"], output_config=body["output_config"],
            extra_body={"temperature": body["temperature"]})
        return APIOutput(api_response=msg.model_dump(mode="json"),
                         request_id=getattr(msg, "_request_id", None))


def _validate_row(item: RecoveryItem, row: RecoveryResponse,
                  requests: set[str], messages: set[str]) -> None:
    if row.model != MODEL or row.returned_model != MODEL or row.responder != RESPONDER:
        raise ValueError("Response model mismatch")
    for ident, seen in ((row.request_id, requests), (row.api_response.get("id"), messages)):
        if ident is not None:
            if ident in seen:
                raise ValueError("Duplicate API request or message ID")
            seen.add(ident)
    rebuilt = decode(item, APIOutput(api_response=row.api_response, request_id=row.request_id))
    if rebuilt != row or not _request_matches(row.request_body, rebuilt.request_body):
        raise ValueError("Response decoding, request body or metadata mismatch")


def validate(items: list[RecoveryItem], rows: list[RecoveryResponse]) -> dict[str, RecoveryResponse]:
    if items != generate_items():
        raise ValueError("Items differ from the complete fixed recovery schedule")
    known = {i.item_id: i for i in items}
    found: dict[str, RecoveryResponse] = {}
    requests: set[str] = set()
    messages: set[str] = set()
    for row in rows:
        if row.item_id not in known or row.item_id in found:
            raise ValueError("Unknown or duplicate response ID")
        _validate_row(known[row.item_id], row, requests, messages)
        found[row.item_id] = row
    return found


def load_run(path: Path, items: list[RecoveryItem]) -> list[RecoveryResponse]:
    cfg = json.loads(path.with_suffix(path.suffix+".config.json").read_text())
    cfg.pop("started", None)
    expected = config(items)
    if cfg != expected or not _request_matches(cfg["request"], expected["request"]):
        raise ValueError("Recovery configuration changed; use the recorded source revision")
    rows = [RecoveryResponse.model_validate_json(line) for line in path.read_text().splitlines()
            if line.strip()]
    if [r.item_id for r in rows] != [i.item_id for i in items[:len(rows)]]:
        raise ValueError("Recorded request order differs from the frozen sequence")
    validate(items, rows)
    return rows


def run(items: list[RecoveryItem], responder: Callable[[RecoveryItem], APIOutput], path: Path,
        *, resume: bool = False) -> list[RecoveryResponse]:
    verify_freeze(items)
    validate(items, [])
    cfg_path = path.with_suffix(path.suffix+".config.json")
    if path.exists():
        if not resume:
            raise RunExists(f"{path} exists; use --resume with the original files and revision")
        old = validate(items, load_run(path, items))
    else:
        if cfg_path.exists():
            raise RunExists(f"Orphaned configuration {cfg_path}; choose a new output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps({**config(items), "started": datetime.now(UTC).isoformat()},
                                       indent=2)+"\n")
        path.touch(exist_ok=False)
        old = {}
    requests = {r.request_id for r in old.values() if r.request_id is not None}
    messages = {r.api_response["id"] for r in old.values() if r.api_response.get("id") is not None}
    rows = []
    for item in items:
        if item.item_id in old:
            rows.append(old[item.item_id])
            continue
        row = decode(item, responder(item))
        # Preserve wrong-model or unusable output before any integrity stop.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(row.model_dump_json()+"\n")
        rows.append(row)
        _validate_row(item, row, requests, messages)
        if len(rows) % 12 == 0 or len(rows) == len(items):
            print(f"Recorded {len(rows)}/{len(items)}; pass {item.repetition}", flush=True)
    return rows


def generate_artifacts(items: list[RecoveryItem]) -> None:
    verify_freeze(items)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("".join(i.model_dump_json()+"\n" for i in items))
    (OUT / "protocol.json").write_text(json.dumps(config(items), indent=2)+"\n")
    (OUT / "analysis-plan.md").write_bytes(PLAN.read_bytes())
    (OUT / "freeze.json").write_bytes(FREEZE.read_bytes())
    (OUT / "original-history-bounds.json").write_text(json.dumps(original_history_bounds(), indent=2)+"\n")
    oracle = recovery_report(items, {i.item_id: i.expected_answer for i in items})
    (OUT / "programmed-oracle-check.json").write_text(json.dumps({
        "data_origin": "programmed_oracle", "uses_model_responses": False, **oracle}, indent=2)+"\n")
    print(f"Frozen {len(items)} requests / 108 templates; hash {items_hash(items)}. No API calls.")


def main() -> None:
    from wtrbench.recovery_report import save_reports

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("generate")
    go = sub.add_parser("run")
    go.add_argument("--resume", action="store_true")
    go.add_argument("--out", type=Path, default=OUT / "responses.jsonl")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("path", type=Path)
    inspect.add_argument("--labels", type=Path)
    args = parser.parse_args()
    items = generate_items()
    verify_freeze(items)
    if args.command in (None, "generate"):
        generate_artifacts(items)
    elif args.command == "inspect":
        print(save_reports(args.path, items, load_run(args.path, items), labels_path=args.labels))
    else:
        rows = run(items, RecoveryResponder(), args.out, resume=args.resume)
        print(save_reports(args.out, items, rows))
