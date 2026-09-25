"""Frozen collection, strict decoding and provenance for payoff presentation."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wtrbench.explanation_calibration import APIOutput, _request_matches, request_settings
from wtrbench.payoff_presentation import (
    PROTOCOL,
    Presentation,
    PresentationItem,
    generate_items,
)
from wtrbench.recovery_run import RecoveryResponder, RecoveryResponse
from wtrbench.recovery_run import decode as recovery_decode
from wtrbench.run import RunExists
from wtrbench.validation_recovery import MODEL, request_body

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/payoff-presentation-v1.md"
FREEZE = ROOT / "protocols/payoff-presentation-v1.json"
OUT = Path("runs/payoff-presentation")


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def items_hash(items: list[PresentationItem]) -> str:
    return sha("".join(i.item_id for i in items).encode())[:16]


def config(items: list[PresentationItem]) -> dict[str, Any]:
    return {"mode": PROTOCOL, "model": MODEL, "n_requests": len(items),
        "n_templates": len({i.template_id for i in items}), "items_hash": items_hash(items),
        "counts_by_presentation": dict(Counter(i.presentation for i in items)),
        "repetitions": [1, 2], "order_seed": PROTOCOL,
        "sequence": "two passes; presentations interleaved in fixed hash order within each pass",
        "request": request_settings("letter"), "transport_max_retries": 0,
        "analysis_plan_sha256": sha(PLAN.read_bytes()),
        "implementation_sha256": {str(p.relative_to(ROOT)): sha(p.read_bytes())
                                  for p in sorted((ROOT / "src/wtrbench").glob("*.py"))},
        "stopping_rule": "288 scheduled calls once; no answer-accuracy gate during collection"}


def freeze_manifest(items: list[PresentationItem]) -> dict[str, Any]:
    return {"config": config(items),
        "items_jsonl_sha256": sha("".join(i.model_dump_json()+"\n" for i in items).encode()),
        "request_bodies_jsonl_sha256": sha("".join(json.dumps(request_body(i))+"\n"
                                                   for i in items).encode())}


def verify_freeze(items: list[PresentationItem]) -> None:
    expected = freeze_manifest(items)
    saved = json.loads(FREEZE.read_text()) if FREEZE.exists() else None
    if saved != expected or not _request_matches(saved["config"]["request"],
                                                 expected["config"]["request"]):
        raise ValueError("Presentation freeze differs; use the frozen source and plan")


class PresentationResponse(RecoveryResponse):
    presentation: Presentation
    source_item_id: str
    source_template_id: str


def decode(item: PresentationItem, output: APIOutput) -> PresentationResponse:
    row = recovery_decode(item, output)
    return PresentationResponse.model_validate({**row.model_dump(),
        "presentation": item.presentation, "source_item_id": item.source_item_id,
        "source_template_id": item.source_template_id})


def validate_row(item: PresentationItem, row: PresentationResponse,
                 requests: set[str], messages: set[str]) -> None:
    if row.model != MODEL or row.returned_model != MODEL or row.responder != "anthropic:"+MODEL:
        raise ValueError("Response model mismatch")
    for ident, seen in ((row.request_id, requests), (row.api_response.get("id"), messages)):
        if ident is not None:
            if ident in seen:
                raise ValueError("Duplicate API request or message ID")
            seen.add(ident)
    rebuilt = decode(item, APIOutput(api_response=row.api_response, request_id=row.request_id))
    if rebuilt != row or not _request_matches(row.request_body, rebuilt.request_body):
        raise ValueError("Response decoding, request body or metadata mismatch")


def validate(items: list[PresentationItem], rows: list[PresentationResponse]
             ) -> dict[str, PresentationResponse]:
    if items != generate_items():
        raise ValueError("Items differ from the complete fixed presentation schedule")
    known = {i.item_id: i for i in items}
    found: dict[str, PresentationResponse] = {}
    requests: set[str] = set()
    messages: set[str] = set()
    for row in rows:
        if row.item_id not in known or row.item_id in found:
            raise ValueError("Unknown or duplicate response ID")
        validate_row(known[row.item_id], row, requests, messages)
        found[row.item_id] = row
    return found


def load_run(path: Path, items: list[PresentationItem]) -> list[PresentationResponse]:
    cfg = json.loads(path.with_suffix(path.suffix+".config.json").read_text())
    cfg.pop("started", None)
    expected = config(items)
    if cfg != expected or not _request_matches(cfg["request"], expected["request"]):
        raise ValueError("Presentation configuration changed; use the recorded source and plan")
    rows = [PresentationResponse.model_validate_json(line) for line in path.read_text().splitlines()
            if line.strip()]
    if [r.item_id for r in rows] != [i.item_id for i in items[:len(rows)]]:
        raise ValueError("Recorded request order differs from the frozen sequence")
    validate(items, rows)
    return rows


def run(items: list[PresentationItem], responder: Callable[[PresentationItem], APIOutput], path: Path,
        *, resume: bool = False) -> list[PresentationResponse]:
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
        # Save received output before stopping on a wrong model or duplicate API ID.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(row.model_dump_json()+"\n")
        rows.append(row)
        validate_row(item, row, requests, messages)
        if len(rows) % 12 == 0 or len(rows) == len(items):
            print(f"Recorded {len(rows)}/{len(items)}; pass {item.repetition}", flush=True)
    return rows


def generate_artifacts(items: list[PresentationItem]) -> None:
    from wtrbench.presentation_report import fits

    verify_freeze(items)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text("".join(i.model_dump_json()+"\n" for i in items))
    (OUT / "protocol.json").write_text(json.dumps(config(items), indent=2)+"\n")
    (OUT / "analysis-plan.md").write_bytes(PLAN.read_bytes())
    (OUT / "freeze.json").write_bytes(FREEZE.read_bytes())
    oracle = fits(items, {i.item_id: i.expected_answer for i in items})
    (OUT / "programmed-oracle-check.json").write_text(json.dumps({
        "data_origin": "programmed_oracle", "uses_model_responses": False,
        "planned": len(items), "correct": len(items), "fits": oracle,
        "all_intervals_recovered": all(f["recovered_interval"] for f in oracle)}, indent=2)+"\n")
    examples = [next(i for i in items if i.presentation == p and i.profile == "low"
                     and i.own_amount == 2 and i.sam_first and not i.history_swapped
                     and i.repetition == 1) for p in ("original", "explicit_payoffs")]
    (OUT / "prompt-examples.md").write_text("# Matched prompt examples\n\n"+"\n\n".join(
        f"## {i.presentation}\n\n```text\n{i.prompt}\n```" for i in examples)+"\n")
    print(f"Frozen {len(items)} requests / 144 templates; hash {items_hash(items)}. No API calls.")


def main() -> None:
    from wtrbench.presentation_report import save_reports

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
