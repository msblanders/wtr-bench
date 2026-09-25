"""196 existing debug questions plus 24 separate A/B explanation controls.

python -m wtrbench.explanation_debug generate
python -m wtrbench.explanation_debug run [--resume]
python -m wtrbench.explanation_debug inspect PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, model_validator

from wtrbench.calibration import LETTER_END
from wtrbench.explanation_calibration import (
    MODEL,
    APIOutput,
    ExplanationItem,
    _request_matches,
    _unique_object,
    ending,
    request_settings,
)
from wtrbench.explanation_calibration import (
    generate_items as calibration_items,
)
from wtrbench.inference import (
    AGGREGATE_SETS,
    DEBUG_TASKS,
    PILOT_LADDER,
    InferenceItem,
    Probe,
    generate_inference_items,
)
from wtrbench.run import Response, RunExists, items_hash
from wtrbench.score import ScoreReport, ladder_estimate, report_markdown, score

PROTOCOL = "debug-explanation-v1"
OUT = Path("runs/debug-explanation")
RESPONDER = "anthropic:" + MODEL


class DebugItem(BaseModel):
    item_id: str
    block: Literal["control", "debug"]
    prompt: str
    source: InferenceItem | ExplanationItem

    @model_validator(mode="after")
    def check_source(self) -> Self:
        if self.block == "debug":
            if not isinstance(self.source, InferenceItem):
                raise ValueError("Debug source must be an inference item")
        elif (not isinstance(self.source, ExplanationItem)
              or self.source.reply_format != "letter"
              or self.source.expected_recipient is None):
            raise ValueError("Control source must be a known-answer A/B calibration item")
        return self

    @property
    def keyed_option(self) -> Literal["A", "B"]:
        if isinstance(self.source, InferenceItem):
            return self.source.keyed_option
        return "A" if (self.source.expected_recipient == "SAM") == self.source.sam_first else "B"


def _identifier(block: str, prompt: str, source: InferenceItem | ExplanationItem) -> str:
    content = {"protocol": PROTOCOL, "block": block, "prompt": prompt,
               "source": source.model_dump(mode="json")}
    return "wtrdebugbasis-" + hashlib.sha256(
        json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]


def generate_items() -> list[DebugItem]:
    controls = [i for i in calibration_items() if i.reply_format == "letter"
                and i.expected_recipient is not None]
    debug = generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))
    items = []
    sources: list[InferenceItem | ExplanationItem] = [*controls, *debug]
    for source in sources:
        block: Literal["control", "debug"] = (
            "debug" if isinstance(source, InferenceItem) else "control")
        if block == "debug":
            if not source.prompt.endswith(LETTER_END):
                raise ValueError("Original debug reply instruction changed")
            prompt = source.prompt.removesuffix(LETTER_END) + ending("letter")
        else:
            prompt = source.prompt
        items.append(DebugItem(item_id=_identifier(block, prompt, source), block=block,
                               prompt=prompt, source=source))
    return items


def batch_hash(items: list[DebugItem]) -> str:
    return hashlib.sha256("".join(i.item_id for i in items).encode()).hexdigest()[:16]


def config(items: list[DebugItem]) -> dict[str, Any]:
    debug = [i.source for i in items if isinstance(i.source, InferenceItem)]
    return {"mode": PROTOCOL, "model": MODEL, "n_items": len(items),
            "n_controls": sum(i.block == "control" for i in items), "n_debug": len(debug),
            "items_hash": batch_hash(items), "source_debug_hash": items_hash(debug),
            "sequence": "controls then debug, preserving each source sequence",
            "generator": {"ladder": list(PILOT_LADDER), "tasks": [t.value for t in DEBUG_TASKS],
                          "set_roles": ["debug"], "form": 0},
            "transport_max_retries": 0, "request": request_settings("letter")}


def request_body(item: DebugItem) -> dict[str, Any]:
    return {"model": MODEL, **request_settings("letter"),
            "messages": [{"role": "user", "content": item.prompt}]}


class DebugResponse(Response):
    model: str
    block: Literal["control", "debug"]
    brief_basis: str | None
    request_body: dict[str, Any]
    api_response: dict[str, Any]


def decode(item: DebugItem, output: APIOutput) -> DebugResponse:
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
                    and isinstance(value["answer"], str)
                    and value["answer"].upper() in ("A", "B")):
                basis = value["brief_basis"]
                choice = "A" if value["answer"].upper() == "A" else "B"
        except (ValueError, TypeError):
            pass
    return DebugResponse(
        item_id=item.item_id, model=MODEL, responder=RESPONDER, block=item.block,
        raw=raw, choice=choice, keyed=None if choice is None else choice == item.keyed_option,
        brief_basis=basis, stop_reason=body.get("stop_reason"), returned_model=body.get("model"),
        request_id=output.request_id, usage=body.get("usage"),
        request_body=request_body(item), api_response=body,
    )


class DebugResponder:
    def __init__(self) -> None:
        from anthropic import Anthropic

        self.client = Anthropic(max_retries=0)

    def __call__(self, item: DebugItem) -> APIOutput:
        body = request_body(item)
        msg = self.client.messages.create(
            model=MODEL, max_tokens=body["max_tokens"], system=body["system"],
            messages=body["messages"], output_config=body["output_config"],
            extra_body={"temperature": body["temperature"]},
        )
        return APIOutput(api_response=msg.model_dump(mode="json"),
                         request_id=getattr(msg, "_request_id", None))


def validate(items: list[DebugItem], rows: list[DebugResponse]) -> dict[str, DebugResponse]:
    known = {i.item_id: i for i in items}
    if len(known) != len(items):
        raise ValueError("Duplicate item ID")
    for i in items:
        if i.item_id != _identifier(i.block, i.prompt, i.source):
            raise ValueError("Item content or source changed")
    found = {}
    requests: set[str] = set()
    messages: set[str] = set()
    for row in rows:
        if row.item_id not in known or row.item_id in found:
            raise ValueError("Unknown or duplicate response ID")
        if row.model != MODEL or row.returned_model != MODEL or row.responder != RESPONDER:
            raise ValueError("Response model mismatch")
        for ident, seen in ((row.request_id, requests), (row.api_response.get("id"), messages)):
            if ident is not None:
                if ident in seen:
                    raise ValueError("Duplicate API request or message ID")
                seen.add(ident)
        rebuilt = decode(known[row.item_id], APIOutput(
            api_response=row.api_response, request_id=row.request_id))
        if rebuilt != row or not _request_matches(row.request_body, rebuilt.request_body):
            raise ValueError("Response decoding, metadata or request body mismatch")
        found[row.item_id] = row
    return found


def load_run(path: Path, items: list[DebugItem]) -> list[DebugResponse]:
    cfg = json.loads(path.with_suffix(path.suffix + ".config.json").read_text())
    saved = {k: v for k, v in cfg.items() if k != "started"}
    expected = config(items)
    if saved != expected or not _request_matches(saved["request"], expected["request"]):
        raise ValueError("Item set or request protocol changed; use the recorded source revision")
    rows = [DebugResponse.model_validate_json(line) for line in path.read_text().splitlines()
            if line.strip()]
    validate(items, rows)
    return rows


def run(items: list[DebugItem], responder: Callable[[DebugItem], APIOutput], path: Path,
        *, resume: bool = False) -> list[DebugResponse]:
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
        # Preserve unexpected model output before validation stops further calls.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(row.model_dump_json() + "\n")
        rows.append(row)
        validate(items, rows)
    return rows


def debug_score(items: list[DebugItem], rows: list[DebugResponse]) -> ScoreReport:
    found = validate(items, rows)
    originals, projected = [], []
    for item in items:
        if not isinstance(item.source, InferenceItem):
            continue
        originals.append(item.source)
        if row := found.get(item.item_id):
            fields = {f: getattr(row, f) for f in Response.model_fields}
            fields["item_id"] = item.source.item_id
            projected.append(Response.model_validate(fields))
    # Always pass every planned debug item: omitted/unusable answers stay missing.
    return score(originals, projected, RESPONDER)


def control_review(items: list[DebugItem], rows: list[DebugResponse]) -> list[dict[str, Any]]:
    found = validate(items, rows)
    records = []
    for item in items:
        source = item.source
        if not isinstance(source, ExplanationItem):
            continue
        row = found.get(item.item_id)
        values = None
        if source.kind == "explicit_rule":
            _, weight, amount = source.case.split("_")
            own, other = Decimal(amount), Decimal(weight) * 10
            a, b = (own, other) if source.sam_first else (other, own)
            values = {"A": float(a), "B": float(b)}
        records.append({
            "item_id": item.item_id, "source_item_id": source.item_id,
            "source_calibration_item_id": source.source_calibration_item_id,
            "case": source.case, "kind": source.kind, "sam_first": source.sam_first,
            "prompt": item.prompt, "expected_answer": item.keyed_option,
            "expected_recipient": source.expected_recipient, "true_option_values": values,
            "recorded": row is not None, "usable": row is not None and row.choice is not None,
            "answer": row.choice if row else None, "correct": row.keyed if row else None,
            "brief_basis": row.brief_basis if row else None, "raw": row.raw if row else None,
            "calculation_review": "pending_manual_review" if values else "not_applicable",
        })
    return records


def _pair_counts(pairs: dict[Any, dict[Any, bool | None]]) -> tuple[int, int, int]:
    complete = [list(p.values()) for p in pairs.values() if len(p) == 2
                and all(x is not None for x in p.values())]
    return sum(p[0] != p[1] for p in complete), len(complete), len(pairs)


def _pair_key(source: InferenceItem, *, evidence: bool = False) -> str:
    exclude = {"item_id", "index_within_form", "prompt",
               "choices_swapped" if evidence else "keyed_option"}
    return json.dumps(source.model_dump(mode="json", exclude=exclude), sort_keys=True)


def _cell(source: InferenceItem) -> str:
    if source.family == "attribution":
        return f"boxes/{source.cause.value}"  # type: ignore[union-attr]
    return (f"{AGGREGATE_SETS[source.agg_set].name}/{source.diagnostic.value}/"  # type: ignore[index,union-attr]
            f"{source.totals.value}/"  # type: ignore[union-attr]
            f"{'swapped' if source.choices_swapped else 'original'}")


def _symbol(value: bool | None) -> str:
    return "—" if value is None else "K" if value else "G"


def report(items: list[DebugItem], rows: list[DebugResponse]) -> str:
    found = validate(items, rows)
    controls = control_review(items, rows)
    correct = sum(r["correct"] is True for r in controls)
    lines = ["# Exploratory explanation debug", "", f"Protocol: `{PROTOCOL}`; model: `{MODEL}`.",
             f"Recorded {len(rows)}/{len(items)}; item hash `{batch_hash(items)}`.",
             "Pilot remains paused. Model outputs require review; green execution is not approval.",
             "Explanations are generated outputs, not access to internal reasoning.", "",
             "Stop reasons: " + str(dict(Counter(r.stop_reason for r in rows))), ""]
    for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens"):
        total = sum(v for r in rows if r.usage and isinstance(v := r.usage.get(key), int))
        lines.append(f"- {key}: {total}")
    lines += ["", "## Separate known-answer controls", "",
              f"Final-answer accuracy: {correct}/{len(controls)} planned controls.",
              "Returned calculation accuracy: pending manual review, even with correct final labels.",
              "The prior rule_1_20 / Sam-second false-tie explanation is a known concern.", "",
              "| Control | Correct/planned | Missing | Unusable | Disagree/complete/planned pairs |",
              "|---|---:|---:|---:|---:|"]
    for kind in ("recipient_lookup", "quantity", "explicit_rule"):
        cs = [c for c in controls if c["kind"] == kind]
        pairs: dict[Any, dict[Any, bool | None]] = defaultdict(dict)
        for c in cs:
            pairs[c["case"]][c["sam_first"]] = c["correct"]
        d, n, planned = _pair_counts(pairs)
        lines.append(f"| {kind} | {sum(c['correct'] is True for c in cs)}/{len(cs)} | "
                     f"{sum(not c['recorded'] for c in cs)} | "
                     f"{sum(c['recorded'] and not c['usable'] for c in cs)} | {d}/{n}/{planned} |")
    lines += ["", "### Controls by option order", "",
              "| Sam position | Correct/planned | Missing | Unusable |", "|---|---:|---:|---:|"]
    for first in (True, False):
        cs = [c for c in controls if c["sam_first"] == first]
        lines.append(f"| {'first' if first else 'second'} | "
                     f"{sum(c['correct'] is True for c in cs)}/{len(cs)} | "
                     f"{sum(not c['recorded'] for c in cs)} | "
                     f"{sum(c['recorded'] and not c['usable'] for c in cs)} |")
    lines += ["", "### Rule calculations to review (not automatically graded)", "",
              "True values are audit metadata, never sent to the API. Full rows: control-review.jsonl.",
              "| Case | Sam position | True A / B values | Expected / returned | Brief basis |",
              "|---|---|---|---|---|"]
    for c in controls:
        if c["true_option_values"] is None:
            continue
        v = c["true_option_values"]
        basis = (c["brief_basis"] or "missing/unusable").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {c['case']} | {'first' if c['sam_first'] else 'second'} | "
                     f"{v['A']:g} / {v['B']:g} | {c['expected_answer']} / "
                     f"{c['answer'] or '—'} | {basis} |")
    debug = [i for i in items if isinstance(i.source, InferenceItem)]
    lines += ["", "## Debug collection and option-order checks", "",
              "Disagreements compare semantic keyed choices, not the printed answer letters.",
              "Only two usable answers make a complete pair. Missing pairs remain in planned counts.",
              "| Family/probe | Usable/planned | Missing | Unusable | Disagree/complete/planned pairs |",
              "|---|---:|---:|---:|---:|"]
    groups: dict[str, list[DebugItem]] = defaultdict(list)
    for item in debug:
        s = item.source
        assert isinstance(s, InferenceItem)
        groups[f"{s.family}/{s.probe.value}"].append(item)
    for label, group in sorted(groups.items()):
        pairs = defaultdict(dict)
        for item in group:
            s = item.source
            assert isinstance(s, InferenceItem)
            row = found.get(item.item_id)
            pairs[_pair_key(s)][s.keyed_option] = row.keyed if row else None
        d, n, planned = _pair_counts(pairs)
        missing = sum(i.item_id not in found for i in group)
        unusable = sum(i.item_id in found and found[i.item_id].choice is None for i in group)
        lines.append(f"| {label} | {len(group)-missing-unusable}/{len(group)} | {missing} | "
                     f"{unusable} | {d}/{n}/{planned} |")
    lines += ["", "## Inferred-choice ladders by evidence order", "",
              "K = partner keeps own payoff; G = gives to you; — = missing/unusable.",
              "Each rung lists keyed-A / keyed-B. Decreases count observed K-to-G reversals as",
              "the partner payoff increases, separately for each displayed order.", "",
              ("| Cell | Rung: keyed-A/keyed-B | Disagree/complete/planned pairs | "
               "Observed decreases A/B | Bound or gap | Status | Fit violations | Missing |"),
              "|---|---|---:|---:|---|---|---:|---:|"]
    ladders: dict[str, list[tuple[float, str, bool | None]]] = defaultdict(list)
    evidence: dict[str, dict[str, dict[bool, bool | None]]] = defaultdict(lambda: defaultdict(dict))
    binaries: dict[str, dict[str, bool | None]] = defaultdict(dict)
    for item in debug:
        s = item.source
        assert isinstance(s, InferenceItem)
        row = found.get(item.item_id)
        keyed = row.keyed if row else None
        if s.probe == Probe.INFER:
            assert s.realized_ratio is not None
            ladders[_cell(s)].append((s.realized_ratio, s.keyed_option, keyed))
            if s.family == "aggregate":
                assert s.choices_swapped is not None
                label = f"{s.diagnostic.value}/{s.totals.value}"  # type: ignore[union-attr]
                evidence[label][_pair_key(s, evidence=True)][s.choices_swapped] = keyed
        else:
            binaries[f"{_cell(s)}/{s.probe.value}"][s.keyed_option] = keyed
    for label, pts in sorted(ladders.items()):
        by_r: dict[float, dict[str, bool | None]] = defaultdict(dict)
        for ratio, option, value in pts:
            by_r[ratio][option] = value
        d, n, planned = _pair_counts(dict(by_r))
        pattern = " ".join(f"{r:g}:{_symbol(p.get('A'))}/{_symbol(p.get('B'))}"
                           for r, p in sorted(by_r.items()))
        decreases = []
        for option in ("A", "B"):
            values = [p[option] for _, p in sorted(by_r.items()) if p.get(option) is not None]
            decreases.append(sum(a is True and b is False for a, b in pairwise(values)))
        e = ladder_estimate([(r, k) for r, _, k in pts])
        status = e.censored if e.censored != "none" else (
            "interior" if e.identified else "unidentified")
        lo = "unbounded" if e.lower is None else f"{e.lower:g}"
        hi = "unbounded" if e.upper is None else f"{e.upper:g}"
        bound = f"{lo} to {hi}" if e.n else "undetermined"
        lines.append(f"| {label} | {pattern} | {d}/{n}/{planned} | "
                     f"{decreases[0]}/{decreases[1]} | {bound} | {status} | "
                     f"{e.violations} | {e.n_missing} |")
    lines += ["", "## Aggregate evidence-order checks", "",
              "Compare original/swapped history at the same ratio and displayed option order.",
              "| Diagnostic/totals | Disagree/complete/planned pairs |", "|---|---:|"]
    for label, epairs in sorted(evidence.items()):
        d, n, planned = _pair_counts(dict(epairs))
        lines.append(f"| {label} | {d}/{n}/{planned} |")
    lines += ["", "## Willingness and ability pairs", "",
              "Keyed means would agree (willingness) or would manage (ability). No truth key is assigned.",
              "| Cell/probe | Keyed option A | Keyed option B | Agreement |", "|---|---|---|---|"]
    for label, binary_values in sorted(binaries.items()):
        a, b = binary_values.get("A"), binary_values.get("B")
        labels = ["missing/unusable" if v is None else "yes" if v else "no" for v in (a, b)]
        agreement = "undetermined" if a is None or b is None else str(a == b)
        lines.append(f"| {label} | {labels[0]} | {labels[1]} | {agreement} |")
    lines += ["", "## Existing interval-aware scores (196 debug items only)", "",
              "Exploratory comparisons, not preregistered results. Controls never enter these fits.",
              "Missingness, order effects and violations must be reviewed before interpreting bounds.",
              "Only one debug scenario and one numerical set are tested; no pilot approval is automatic.",
              "", report_markdown(debug_score(items, rows)), "", "## Unusable responses", ""]
    lines.extend(f"- {r.item_id} ({r.block}, stop={r.stop_reason}): {r.raw!r}"
                 for r in rows if r.choice is None)
    return "\n".join(lines) + "\n"


def save_reports(path: Path, items: list[DebugItem], rows: list[DebugResponse]) -> str:
    rendered = report(items, rows)
    path.with_suffix(".md").write_text(rendered)
    path.with_suffix(".score.json").write_text(debug_score(items, rows).model_dump_json(indent=2)+"\n")
    path.with_name("control-review.jsonl").write_text(
        "".join(json.dumps(c) + "\n" for c in control_review(items, rows)))
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate")
    args_run = sub.add_parser("run")
    args_run.add_argument("--resume", action="store_true")
    args_run.add_argument("--out", type=Path, default=OUT / "responses.jsonl")
    args_inspect = sub.add_parser("inspect")
    args_inspect.add_argument("path", type=Path)
    args = parser.parse_args()
    items = generate_items()
    if args.command == "generate":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "items.jsonl").write_text("".join(i.model_dump_json()+"\n" for i in items))
        (OUT / "protocol.json").write_text(json.dumps(config(items), indent=2)+"\n")
        print(f"{len(items)} requests; hash {batch_hash(items)}; no API calls")
    elif args.command == "inspect":
        print(save_reports(args.path, items, load_run(args.path, items)))
    else:
        rows = run(items, DebugResponder(), args.out, resume=args.resume)
        print(save_reports(args.out, items, rows))


if __name__ == "__main__":
    main()
