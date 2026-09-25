"""Prospectively specified 816-request pilot of observable response robustness.

python -m wtrbench.robustness_pilot generate
python -m wtrbench.robustness_pilot run [--resume]
python -m wtrbench.robustness_pilot inspect PATH [--labels PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from wtrbench.calibration import LETTER_END
from wtrbench.explanation_calibration import (
    MODEL,
    APIOutput,
    ExplanationItem,
    _request_matches,
    ending,
    request_settings,
)
from wtrbench.explanation_calibration import generate_items as calibration_items
from wtrbench.explanation_debug import RESPONDER, DebugItem, DebugResponder
from wtrbench.explanation_debug import decode as decode_transport
from wtrbench.explanation_debug import request_body as transport_request
from wtrbench.inference import (
    AGGREGATE_SETS,
    CONFIRMATORY_TASKS,
    PILOT_LADDER,
    Cause,
    InferenceItem,
    Probe,
    generate_inference_items,
)
from wtrbench.run import Response, RunExists

PROTOCOL = "response-robustness-pilot-v1"
REPETITIONS = (1, 2)
NUMERICAL_RATIOS = (0.1, 0.5, 2.0)
BINARY_PROBES = (Probe.WILL_SAME, Probe.ABLE_SAME, Probe.ABLE_DIFF)
ORDER_SEED = "2026-09-25-response-robustness-v1"
ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/response-robustness-pilot-v1.md"
FREEZE = ROOT / "protocols/response-robustness-pilot-v1.json"
OUT = Path("runs/robustness-pilot")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class PilotTemplate(BaseModel):
    template_id: str
    block: Literal["control", "pilot"]
    kind: Literal["control", "valuation", "binary"]
    wording: Literal["original", "clarified"]
    unit: str
    prompt: str
    source: InferenceItem | ExplanationItem

    @property
    def keyed_option(self) -> Literal["A", "B"]:
        if isinstance(self.source, InferenceItem):
            return self.source.keyed_option
        return "A" if (self.source.expected_recipient == "SAM") == self.source.sam_first else "B"


class PilotItem(PilotTemplate):
    item_id: str
    repetition: Literal[1, 2]
    sequence_index: int


class PilotResponse(Response):
    model: str
    block: Literal["control", "pilot"]
    template_id: str
    repetition: Literal[1, 2]
    brief_basis: str | None
    request_body: dict[str, Any]
    api_response: dict[str, Any]


def template_fields(item: PilotTemplate) -> dict[str, Any]:
    return item.model_dump(mode="json", include={
        "block", "kind", "wording", "unit", "prompt", "source"})


def template_id(fields: dict[str, Any]) -> str:
    return "wtrrobust-template-" + digest({"protocol": PROTOCOL, **fields})[:16]


def item_id(template: str, repetition: int) -> str:
    return "wtrrobust-" + digest({"protocol": PROTOCOL, "template": template,
                                 "repetition": repetition})[:16]


def clarification(source: InferenceItem) -> str:
    if source.probe == Probe.WILL_SAME:
        return (f"For this question, take {source.name}'s availability and ability to do this task "
                "at that future time as given, regardless of any earlier limitation. ")
    return (f"For this question, take {source.name}'s effort and available time as given, "
            "regardless of any earlier willingness to help. ")


def generate_templates() -> list[PilotTemplate]:
    templates = []

    def add(source: InferenceItem | ExplanationItem, kind: str, unit: str,
            prompt: str, wording: str = "original") -> None:
        fields = {"block": "control" if kind == "control" else "pilot", "kind": kind,
                  "wording": wording, "unit": unit, "prompt": prompt,
                  "source": source.model_dump(mode="json")}
        templates.append(PilotTemplate.model_validate({"template_id": template_id(fields), **fields}))

    for control in calibration_items():
        if control.reply_format == "letter" and control.expected_recipient is not None:
            add(control, "control", "controls", control.prompt)
    for source in generate_inference_items(ladder=PILOT_LADDER):
        if source.family == "attribution":
            if source.cause not in (Cause.UNABLE, Cause.UNWILLING):
                continue
            if source.probe not in (Probe.INFER, *BINARY_PROBES):
                continue
            assert source.task is not None
            unit = source.task.value
        else:
            spec = AGGREGATE_SETS[source.agg_set]  # type: ignore[index]
            if spec.role != "construction" or source.realized_ratio not in NUMERICAL_RATIOS:
                continue
            unit = spec.name
        if not source.prompt.endswith(LETTER_END):
            raise ValueError("Original inference reply instruction changed")
        prompt = source.prompt.removesuffix(LETTER_END) + ending("letter")
        kind = "valuation" if source.probe == Probe.INFER else "binary"
        add(source, kind, unit, prompt)
        if kind == "binary":
            add(source, kind, unit, prompt.replace("Which is more likely?",
                clarification(source) + "Which is more likely?"), "clarified")
    assert len(templates) == 408 and len({t.template_id for t in templates}) == 408
    assert len({t.prompt for t in templates}) == 408
    return templates


def generate_items() -> list[PilotItem]:
    templates = generate_templates()
    items: list[PilotItem] = []
    for repetition in REPETITIONS:
        for block in ("control", "pilot"):
            group = sorted((t for t in templates if t.block == block), key=lambda t: digest(
                {"order_seed": ORDER_SEED, "repetition": repetition, "template": t.template_id}))
            for template in group:
                items.append(PilotItem.model_validate({**template.model_dump(mode="json"),
                    "item_id": item_id(template.template_id, repetition),
                    "repetition": repetition, "sequence_index": len(items)}))
    return items


def batch_hash(items: list[PilotItem]) -> str:
    return hashlib.sha256("".join(i.item_id for i in items).encode()).hexdigest()[:16]


def config(items: list[PilotItem]) -> dict[str, Any]:
    return {"mode": PROTOCOL, "model": MODEL, "n_requests": len(items),
            "n_templates": len({i.template_id for i in items}), "repetitions": list(REPETITIONS),
            "items_hash": batch_hash(items), "request": request_settings("letter"),
            "transport_max_retries": 0, "order_seed": ORDER_SEED,
            "sequence": "two passes; 24 controls then 384 social requests per pass; fixed hash order",
            "counts": dict(Counter(f"{i.kind}/{i.wording}" for i in items)),
            "design": {"tasks": [t.value for t in CONFIRMATORY_TASKS],
                       "causes": ["unable", "unwilling"], "numerical_sets": ["set0", "set1"],
                       "attribution_ladder": list(PILOT_LADDER),
                       "numerical_ladder": list(NUMERICAL_RATIOS),
                       "binary_probes": [p.value for p in BINARY_PROBES], "form": 0},
            "stopping_rule": "816 scheduled requests; no accuracy gate or outcome-adaptive extension",
            "analysis_plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest()}


def freeze_manifest(items: list[PilotItem]) -> dict[str, Any]:
    return {"config": config(items), "items_jsonl_sha256": hashlib.sha256(
        "".join(i.model_dump_json() + "\n" for i in items).encode()).hexdigest()}


def verify_freeze(items: list[PilotItem]) -> None:
    expected = freeze_manifest(items)
    saved = json.loads(FREEZE.read_text()) if FREEZE.exists() else None
    if (saved != expected or not _request_matches(
            saved["config"]["request"], expected["config"]["request"])):
        raise ValueError("Pilot freeze differs: use the frozen revision, not a modified plan/item set")


def _transport_item(item: PilotItem) -> DebugItem:
    # Adapter reuses the tested parser/transport while preserving 'pilot' in the actual saved record.
    return DebugItem(item_id=item.item_id, block="control" if item.block == "control" else "debug",
                     source=item.source, prompt=item.prompt)


def request_body(item: PilotItem) -> dict[str, Any]:
    return transport_request(_transport_item(item))


def decode(item: PilotItem, output: APIOutput) -> PilotResponse:
    fields = decode_transport(_transport_item(item), output).model_dump(mode="json")
    fields.update(block=item.block, template_id=item.template_id, repetition=item.repetition)
    return PilotResponse.model_validate(fields)


class PilotResponder:
    def __init__(self) -> None:
        self.transport = DebugResponder()

    def __call__(self, item: PilotItem) -> APIOutput:
        return self.transport(_transport_item(item))


def _validate_row(item: PilotItem, row: PilotResponse, requests: set[str], messages: set[str]) -> None:
    if row.model != MODEL or row.returned_model != MODEL or row.responder != RESPONDER:
        raise ValueError("Response model mismatch")
    for ident, seen in ((row.request_id, requests), (row.api_response.get("id"), messages)):
        if ident is not None:
            if ident in seen:
                raise ValueError("Duplicate API request or message ID")
            seen.add(ident)
    rebuilt = decode(item, APIOutput(api_response=row.api_response, request_id=row.request_id))
    if rebuilt != row or not _request_matches(row.request_body, rebuilt.request_body):
        raise ValueError("Response decoding, request body or repetition metadata mismatch")


def validate(items: list[PilotItem], rows: list[PilotResponse]) -> dict[str, PilotResponse]:
    known = {i.item_id: i for i in items}
    if len(known) != len(items):
        raise ValueError("Duplicate scheduled item ID")
    for n, i in enumerate(items):
        if (i.sequence_index != n or i.template_id != template_id(template_fields(i))
                or i.item_id != item_id(i.template_id, i.repetition)):
            raise ValueError("Item content, sequence or repetition changed")
        _transport_item(i)  # Validate source/block compatibility before any API call.
    found: dict[str, PilotResponse] = {}
    requests: set[str] = set()
    messages: set[str] = set()
    for row in rows:
        if row.item_id not in known or row.item_id in found:
            raise ValueError("Unknown or duplicate response ID")
        _validate_row(known[row.item_id], row, requests, messages)
        found[row.item_id] = row
    return found


def load_run(path: Path, items: list[PilotItem]) -> list[PilotResponse]:
    saved = json.loads(path.with_suffix(path.suffix + ".config.json").read_text())
    saved.pop("started", None)
    expected = config(items)
    if saved != expected or not _request_matches(saved["request"], expected["request"]):
        raise ValueError("Pilot configuration changed; use the recorded source revision")
    rows = [PilotResponse.model_validate_json(line) for line in path.read_text().splitlines()
            if line.strip()]
    if [r.item_id for r in rows] != [i.item_id for i in items[:len(rows)]]:
        raise ValueError("Recorded request order differs from the frozen sequence")
    validate(items, rows)
    return rows


def run(items: list[PilotItem], responder: Callable[[PilotItem], APIOutput], path: Path,
        *, resume: bool = False) -> list[PilotResponse]:
    verify_freeze(items)
    validate(items, [])
    cfg_path = path.with_suffix(path.suffix + ".config.json")
    if path.exists():
        if not resume:
            raise RunExists(f"{path} exists; use --resume for this exact pilot")
        old = validate(items, load_run(path, items))
    else:
        if cfg_path.exists():
            raise RunExists(f"Orphaned configuration {cfg_path}; choose a new output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps({**config(items), "started": datetime.now(UTC).isoformat()},
                                       indent=2) + "\n")
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
        # Save unusable or unexpected-model responses before any integrity failure stops calls.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(row.model_dump_json() + "\n")
        rows.append(row)
        _validate_row(item, row, requests, messages)
        if len(rows) % 24 == 0 or len(rows) == len(items):
            print(f"Recorded {len(rows)}/{len(items)}; pass {item.repetition}; "
                  "continuing the fixed schedule", flush=True)
    return rows


def main() -> None:
    from wtrbench.robustness_report import save_reports

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate")
    args_run = sub.add_parser("run")
    args_run.add_argument("--resume", action="store_true")
    args_run.add_argument("--out", type=Path, default=OUT / "responses.jsonl")
    args_inspect = sub.add_parser("inspect")
    args_inspect.add_argument("path", type=Path)
    args_inspect.add_argument("--labels", type=Path)
    args = parser.parse_args()
    items = generate_items()
    verify_freeze(items)
    if args.command == "generate":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items))
        (OUT / "protocol.json").write_text(json.dumps(config(items), indent=2) + "\n")
        (OUT / "freeze.json").write_bytes(FREEZE.read_bytes())
        (OUT / "analysis-plan.md").write_bytes(PLAN.read_bytes())
        print(f"{len(items)} planned requests / 408 templates; hash {batch_hash(items)}; no API calls")
    elif args.command == "inspect":
        print(save_reports(args.path, items, load_run(args.path, items), labels_path=args.labels))
    else:
        rows = run(items, PilotResponder(), args.out, resume=args.resume)
        print(save_reports(args.out, items, rows))


if __name__ == "__main__":
    main()
