"""Fixed 156-request range/conditional diagnostic; no pilot calls.

python -m wtrbench.measurement_diagnostic generate
python -m wtrbench.measurement_diagnostic run [--resume]
python -m wtrbench.measurement_diagnostic inspect PATH
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
from typing import Any, Literal

from wtrbench.explanation_calibration import MODEL, APIOutput, _request_matches, request_settings
from wtrbench.explanation_debug import (
    RESPONDER,
    DebugItem,
    DebugResponder,
    DebugResponse,
    decode,
    request_body,
)
from wtrbench.explanation_debug import generate_items as original_items
from wtrbench.explanation_debug import load_run as load_source_run
from wtrbench.inference import Cause, InferenceItem, Probe, Totals
from wtrbench.run import RunExists
from wtrbench.score import ladder_contrast, ladder_estimate

PROTOCOL = "measurement-diagnostic-v1"
OUT = Path("runs/measurement-diagnostic")
REFERENCE = Path(__file__).resolve().parents[2] / "results/debug/36095971330/responses.jsonl"
RATIOS = ("0.01", "0.05", "0.1", "0.2", "0.5", "2", "4", "8")
ORIGINAL_RATIOS = ("0.1", "0.2", "0.5", "2")
FRACTION_RULES = (("0.1", "0.005"), ("0.1", "0.05"),
                  ("0.5", "0.02"), ("0.5", "0.1"))
CLARIFICATIONS = {
    Probe.WILL_SAME: ("For this question, take Sam's availability and physical ability at that "
                     "future time as given, regardless of any earlier limitation. "),
    Probe.ABLE_DIFF: ("For this question, take Sam's effort and available time as given, "
                     "regardless of any earlier willingness to help. "),
}


class DiagnosticItem(DebugItem):
    """Source is the unmodified seed; actual amounts/ratio below override seed metadata."""

    source_debug_item_id: str
    kind: Literal["control", "valuation", "binary"]
    variant: Literal["original", "extended", "decimal_anchor", "fraction_control", "clarified"]
    cell: str
    ratio: float | None = None
    own_amount: str | None = None
    fixed_amount: str | None = None
    rule_weight: str | None = None
    expected_option_values: dict[str, float] | None = None


def identifier(fields: dict[str, Any]) -> str:
    payload = {"protocol": PROTOCOL, **fields}
    return "wtrmeasure-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def make(seed: DebugItem, **changes: Any) -> DiagnosticItem:
    fields = {**seed.model_dump(mode="json", exclude={"item_id"}),
              "source_debug_item_id": seed.item_id, **changes}
    item = DiagnosticItem(item_id="pending", **fields)
    return item.model_copy(update={"item_id": identifier(
        item.model_dump(mode="json", exclude={"item_id"}))})


def values(own: str, weight: str, keyed_first: bool) -> dict[str, float]:
    a, b = Decimal(own), Decimal(weight) * 10
    if not keyed_first:
        a, b = b, a
    return {"A": float(a), "B": float(b)}


def generate_items() -> list[DiagnosticItem]:
    seeds = original_items()
    result = []
    for seed in seeds[:24]:
        source = seed.source
        assert not isinstance(source, InferenceItem)
        audit_values, weight, own = None, None, None
        if source.kind == "explicit_rule":
            _, weight, own = source.case.split("_")
            audit_values = values(own, weight, source.sam_first)
        result.append(make(seed, kind="control", variant="original", cell=source.case,
                           own_amount=own, fixed_amount="10" if own else None,
                           rule_weight=weight, expected_option_values=audit_values))
    # New fractional controls balance both semantic choices and both displayed orders.
    for own, weight in FRACTION_RULES:
        keep = Decimal(own) > Decimal(weight) * 10
        case = "rule_0.5_8" if keep else "rule_0.5_2"
        for first in (True, False):
            seed = next(s for s in seeds[:24] if not isinstance(s.source, InferenceItem)
                        and s.source.case == case and s.source.sam_first == first)
            old_own = "8" if keep else "2"
            prompt = seed.prompt.replace(f"Sam receives {old_own} points.",
                                         f"Sam receives {own} points.")
            prompt = prompt.replace("plus 0.5 times your points", f"plus {weight} times your points")
            result.append(make(seed, prompt=prompt, kind="control", variant="fraction_control",
                               cell=f"fraction_{own}_{weight}", own_amount=own, fixed_amount="10",
                               rule_weight=weight, expected_option_values=values(own, weight, first)))

    # Two attribution conditions span opposite ends; numerical T2 includes the prior mismatch.
    valuation_start = len(result)
    base = [s for s in seeds if isinstance(s.source, InferenceItem)
            and s.source.probe == Probe.INFER and s.source.realized_ratio == 0.1
            and ((s.source.family == "attribution"
                  and s.source.cause in (Cause.UNABLE, Cause.UNWILLING))
                 or (s.source.family == "aggregate" and s.source.totals == Totals.T2))]
    for seed in base:
        source = seed.source
        assert isinstance(source, InferenceItem)
        cell = (f"boxes/{source.cause.value}" if source.cause else
                f"debug/{source.diagnostic.value}/t2/"  # type: ignore[union-attr]
                f"{'swapped' if source.choices_swapped else 'original'}")
        for ratio in RATIOS:
            amount = format((Decimal(ratio) * 10).normalize(), "f")
            prompt = seed.prompt.replace("Sam receives 1 points.", f"Sam receives {amount} points.")
            exact = next((s for s in seeds if s.prompt == prompt), None)
            if ratio in ORIGINAL_RATIOS:
                assert exact is not None
            result.append(make(exact or seed, prompt=prompt, kind="valuation", cell=cell,
                               variant="original" if exact else "extended", ratio=float(ratio),
                               own_amount=amount, fixed_amount="10"))
    cell_order = {cell: n for n, cell in enumerate(dict.fromkeys(
        i.cell for i in result[valuation_start:]))}
    result[valuation_start:] = sorted(result[valuation_start:], key=lambda i: (
        cell_order[i.cell], i.ratio or 0, i.keyed_option))
    # Separate notation check at the exact same allocation, excluded from all ladder fits.
    for seed in base:
        original = next(i for i in result if i.source_debug_item_id == seed.item_id
                        and i.variant == "original")
        result.append(make(seed, prompt=seed.prompt.replace("Sam receives 1 points.",
                                                          "Sam receives 1.0 points."),
                           kind="valuation", variant="decimal_anchor", cell=original.cell,
                           ratio=0.1, own_amount="1.0", fixed_amount="10"))
    # Affected cases and the opposite-cause comparisons, original then clarified per order.
    for seed in seeds[24:]:
        source = seed.source
        assert isinstance(source, InferenceItem)
        if source.cause not in (Cause.UNABLE, Cause.UNWILLING) or source.probe not in CLARIFICATIONS:
            continue
        cell = f"boxes/{source.cause.value}/{source.probe.value}"
        result.append(make(seed, kind="binary", variant="original", cell=cell))
        prompt = seed.prompt.replace("Which is more likely?",
                                     CLARIFICATIONS[source.probe] + "Which is more likely?")
        result.append(make(seed, prompt=prompt, kind="binary", variant="clarified", cell=cell))
    assert len(result) == 156 and len({i.prompt for i in result}) == 156
    return result


def batch_hash(items: list[DiagnosticItem]) -> str:
    return hashlib.sha256("".join(i.item_id for i in items).encode()).hexdigest()[:16]


def config(items: list[DiagnosticItem]) -> dict[str, Any]:
    return {"mode": PROTOCOL, "model": MODEL, "n_items": len(items),
            "items_hash": batch_hash(items), "request": request_settings("letter"),
            "transport_max_retries": 0, "source_run": "36095971330",
            "source_debug_hash": "bfe1d39e753b7316",
            "ratios": list(RATIOS), "fixed_amount": "10",
            "fraction_rules": [list(rule) for rule in FRACTION_RULES],
            "counts": dict(Counter(f"{i.kind}/{i.variant}" for i in items)),
            "sequence": "24 original controls; 8 fraction controls; 96 ladder; 12 notation; 16 binary",
            "stopping_rule": "one fixed batch; no outcome-adaptive calls, retries or follow-up"}


def validate(items: list[DiagnosticItem], rows: list[DebugResponse]) -> dict[str, DebugResponse]:
    known = {i.item_id: i for i in items}
    if len(known) != len(items):
        raise ValueError("Duplicate item ID")
    for item in items:
        if item.item_id != identifier(item.model_dump(mode="json", exclude={"item_id"})):
            raise ValueError("Item content or diagnostic metadata changed")
    found: dict[str, DebugResponse] = {}
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


def load_run(path: Path, items: list[DiagnosticItem]) -> list[DebugResponse]:
    saved = json.loads(path.with_suffix(path.suffix + ".config.json").read_text())
    saved.pop("started", None)
    expected = json.loads(json.dumps(config(items)))
    if saved != expected or not _request_matches(saved["request"], expected["request"]):
        raise ValueError("Item set or request protocol changed; use the recorded source revision")
    rows = [DebugResponse.model_validate_json(line) for line in path.read_text().splitlines()
            if line.strip()]
    validate(items, rows)
    return rows


def run(items: list[DiagnosticItem], responder: Callable[[DiagnosticItem], APIOutput], path: Path,
        *, resume: bool = False) -> list[DebugResponse]:
    validate(items, [])
    cfg = path.with_suffix(path.suffix + ".config.json")
    if path.exists():
        if not resume:
            raise RunExists(f"{path} exists; use --resume for this exact protocol")
        old = validate(items, load_run(path, items))
    else:
        if cfg.exists():
            raise RunExists(f"Orphaned configuration {cfg}; choose a new output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(json.dumps({**config(items), "started": datetime.now(UTC).isoformat()},
                                  indent=2) + "\n")
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


def pairs(values: list[tuple[bool | None, bool | None]]) -> dict[str, int]:
    complete = [(a, b) for a, b in values if a is not None and b is not None]
    return {"planned": len(values), "complete": len(complete),
            "disagree": sum(a != b for a, b in complete)}


def summarize(items: list[DiagnosticItem], rows: list[DebugResponse]) -> dict[str, Any]:
    found = validate(items, rows)

    def choice(item: DiagnosticItem) -> bool | None:
        return found[item.item_id].keyed if item.item_id in found else None

    collection = {}
    controls, binaries = [], []
    groups: dict[str, list[DiagnosticItem]] = defaultdict(list)
    for item in items:
        groups[f"{item.kind}/{item.variant}"].append(item)
        row = found.get(item.item_id)
        if item.kind in ("control", "binary"):
            record: dict[str, Any] = {
                      "item_id": item.item_id, "source_debug_item_id": item.source_debug_item_id,
                      "cell": item.cell, "variant": item.variant, "prompt": item.prompt,
                      "keyed_option": item.keyed_option, "keyed": choice(item),
                      "answer": row.choice if row else None,
                      "brief_basis": row.brief_basis if row else None,
                      "recorded": row is not None}
            if item.kind == "control":
                record.update(expected_answer=item.keyed_option,
                              expected_option_values=item.expected_option_values,
                              calculation_review=("pending_manual_review"
                                                  if item.expected_option_values else "not_applicable"))
                controls.append(record)
            else:
                record.update(condition_review="pending_manual_review",
                              review_labels=["respects_condition", "contradicts_condition",
                                             "unclear_or_no_checkable_basis", "unusable_or_missing"])
                binaries.append(record)
    for label, group in groups.items():
        collection[label] = {"planned": len(group),
                             "recorded": sum(i.item_id in found for i in group),
                             "usable": sum(choice(i) is not None for i in group)}
    ladders = {}
    for cell in sorted({i.cell for i in items if i.kind == "valuation"}):
        group = [i for i in items if i.cell == cell and i.variant != "decimal_anchor"]
        points = [(i.ratio, choice(i)) for i in group if i.ratio is not None]
        rungs = {r: {i.keyed_option: choice(i) for i in group if i.ratio == float(r)} for r in RATIOS}
        by_order = {}
        for order in ("A", "B"):
            pts = sorted((i.ratio, choice(i)) for i in group if i.keyed_option == order
                         and i.ratio is not None)
            observed = [k for _, k in pts if k is not None]
            by_order[order] = {"fit": ladder_estimate(pts).model_dump(mode="json"),
                               "observed_decreases": sum(a and not b for a, b in pairwise(observed))}
        ladders[cell] = {"fit": ladder_estimate(points).model_dump(mode="json"),
                         "by_option_order": by_order, "rungs": rungs,
                         "option_pairs": pairs([(p.get("A"), p.get("B")) for p in rungs.values()])}
    notation: list[dict[str, Any]] = []
    wording: list[dict[str, Any]] = []
    for item in items:
        if item.variant not in ("decimal_anchor", "clarified"):
            continue
        old = next(i for i in items if i.variant == "original" and i.cell == item.cell
                   and i.ratio == item.ratio and i.keyed_option == item.keyed_option)
        record = {"cell": item.cell, "keyed_option": item.keyed_option,
                  "original_item_id": old.item_id, "changed_item_id": item.item_id,
                  "original": choice(old), "changed": choice(item)}
        (notation if item.variant == "decimal_anchor" else wording).append(record)
    binary_pairs: dict[str, Any] = {}
    for cell in sorted({i.cell for i in items if i.kind == "binary"}):
        binary_pairs[cell] = {}
        for variant in ("original", "clarified"):
            p = {i.keyed_option: choice(i) for i in items if i.cell == cell and i.variant == variant}
            binary_pairs[cell][variant] = {"choices": p,
                                           "option_pairs": pairs([(p.get("A"), p.get("B"))])}
    evidence = {}
    for variant in ("ladder", "decimal_anchor"):
        epairs = []
        for item in items:
            s = item.source
            if (item.kind != "valuation" or not isinstance(s, InferenceItem)
                    or s.family != "aggregate" or s.choices_swapped
                    or (item.variant == "decimal_anchor") != (variant == "decimal_anchor")):
                continue
            other = next(i for i in items if i.cell == item.cell.replace("original", "swapped")
                         and i.variant == item.variant and i.ratio == item.ratio
                         and i.keyed_option == item.keyed_option)
            epairs.append((choice(item), choice(other)))
        evidence[variant] = pairs(epairs)
    contrasts = {}
    for order in ("original", "swapped"):
        low = [i for i in items if i.cell == f"debug/low/t2/{order}"
               and i.variant != "decimal_anchor"]
        high = [i for i in items if i.cell == f"debug/high/t2/{order}"
                and i.variant != "decimal_anchor"]
        if low and high:
            a = ladder_estimate([(i.ratio, choice(i)) for i in low if i.ratio is not None])
            b = ladder_estimate([(i.ratio, choice(i)) for i in high if i.ratio is not None])
            contrasts[f"low_minus_high/{order}"] = ladder_contrast(a, b, "t2").model_dump(mode="json")
    anchors = []
    if REFERENCE.exists():
        prior = {r.item_id: r for r in load_source_run(REFERENCE, original_items())}
        for item in items:
            if item.variant != "original":
                continue
            previous = prior[item.source_debug_item_id]
            if not _request_matches(previous.request_body, request_body(item)):
                raise ValueError("Original anchor request differs from archived source")
            anchors.append({"item_id": item.item_id, "source_debug_item_id": previous.item_id,
                            "kind": item.kind, "cell": item.cell, "ratio": item.ratio,
                            "prior": previous.keyed, "current": choice(item)})
    return {"protocol": PROTOCOL, "items_hash": batch_hash(items), "collection": collection,
            "stop_reasons": dict(Counter(r.stop_reason for r in rows)),
            "usage": {k: sum(r.usage.get(k, 0) for r in rows if r.usage) for k in (
                "input_tokens", "output_tokens", "cache_creation_input_tokens",
                "cache_read_input_tokens")},
            "controls": controls, "ladders": ladders, "binary_review": binaries,
            "binary_pairs": binary_pairs, "notation_comparisons": notation,
            "wording_comparisons": wording, "evidence_pairs": evidence,
            "low_high_contrasts": contrasts, "anchor_comparisons": anchors,
            "anchor_reference_available": REFERENCE.exists(), "pilot_approved": False}


def _pair_text(p: dict[str, int]) -> str:
    return f"{p['disagree']}/{p['complete']}/{p['planned']}"


def report(items: list[DiagnosticItem], rows: list[DebugResponse]) -> str:
    s = summarize(items, rows)
    lines = ["# Fixed measurement diagnostic", "",
             f"Protocol `{PROTOCOL}`; model `{MODEL}`; hash `{batch_hash(items)}`.",
             f"Recorded {len(rows)}/{len(items)}. Pilot remains paused; no automatic approval.",
             "Explanations are generated outputs, not access to internal reasoning.", "",
             f"Stop reasons: {s['stop_reasons']}; usage: {s['usage']}", "",
             "## Collection", "", "| Block | Usable/planned | Missing | Unusable |",
             "|---|---:|---:|---:|"]
    for label, c in s["collection"].items():
        lines.append(f"| {label} | {c['usable']}/{c['planned']} | "
                     f"{c['planned']-c['recorded']} | {c['recorded']-c['usable']} |")
    lines += ["", "## Controls", "", "Final accuracy and stated calculations are separate.",
              "Calculations require manual review, including correct final answers.", "",
              "| Variant | Correct/planned | Option disagreements/complete/planned |",
              "|---|---:|---:|"]
    for variant in ("original", "fraction_control"):
        cs = [c for c in s["controls"] if c["variant"] == variant]
        cp = defaultdict(list)
        for c in cs:
            cp[c["cell"]].append(c["keyed"])
        ps = pairs([(v[0], v[1]) for v in cp.values()])
        lines.append(f"| {variant} | {sum(c['keyed'] is True for c in cs)}/{len(cs)} | {_pair_text(ps)} |")
    lines += ["", "Full prompts, expected values and bases: control-review.jsonl.", "",
              "## Range ladders", "", "K = Sam keeps; G = gives to you; — = missing/unusable.",
              "Decimal spelling anchors and all controls are excluded from fits.",
              "Bounds are threshold fits, not confidence intervals; tied fits remain unidentified.",
              "Each pattern is keyed-A/keyed-B. Full fits by displayed order are in the JSON.", "",
              "| Cell | Rungs | Disagree/complete/planned | Decreases A/B | Bounds | Status | Violations | Missing |",
              "|---|---|---:|---:|---|---|---:|---:|"]
    symbol = {True: "K", False: "G", None: "—"}
    for cell, c in s["ladders"].items():
        f = c["fit"]
        status = ("missing" if not f["n"] else f["censored"] if f["censored"] != "none"
                  else "interior" if f["identified"] else "unidentified")
        pattern = " ".join(f"{r}:{symbol[p.get('A')]}/{symbol[p.get('B')]}"
                           for r, p in c["rungs"].items())
        dec = "/".join(str(c["by_option_order"][o]["observed_decreases"]) for o in ("A", "B"))
        bound = " to ".join("unbounded" if f[x] is None else str(f[x]) for x in ("lower", "upper"))
        lines.append(f"| {cell} | {pattern} | {_pair_text(c['option_pairs'])} | {dec} | "
                     f"{bound} | {status} | {f['violations']} | {f['n_missing']} |")
    lines += ["", "## Matched comparisons", "",
              "Disagree/complete/planned; a wording change is sensitivity, not itself an error.", ""]
    for label, key in (("1 versus 1.0 notation", "notation_comparisons"),
                       ("Original versus clarified binary", "wording_comparisons")):
        ps = pairs([(c["original"], c["changed"]) for c in s[key]])
        lines.append(f"- {label}: {_pair_text(ps)}")
    for variant, ps in s["evidence_pairs"].items():
        lines.append(f"- Evidence order ({variant}): {_pair_text(ps)}")
    if s["anchor_reference_available"]:
        for kind in ("control", "valuation", "binary"):
            ps = pairs([(c["prior"], c["current"]) for c in s["anchor_comparisons"] if c["kind"] == kind])
            lines.append(f"- Exact requests versus run 36095971330 ({kind}): {_pair_text(ps)}")
        lines.append("Previous responses are compared only; they never enter current fits.")
    else:
        lines.append("- Previous-run anchor comparison unavailable: archived file not installed.")
    lines += ["", "## Conditional probes", "",
              "Yes means agrees/manages; no social correctness key is assigned.",
              "Review all 16 explanations using binary-review.jsonl; no keyword auto-grading.", "",
              "| Cell | Wording | Keyed first | Keyed second | Disagree/complete/planned |",
              "|---|---|---|---|---:|"]
    label = {True: "yes", False: "no", None: "missing/unusable"}
    for cell, variants in s["binary_pairs"].items():
        for variant, p in variants.items():
            lines.append(f"| {cell} | {variant} | {label[p['choices'].get('A')]} | "
                         f"{label[p['choices'].get('B')]} | {_pair_text(p['option_pairs'])} |")
    lines += ["", "## Exploratory LOW minus HIGH bounds", "",
              "Report each history order separately; no effect direction is a pass requirement.", ""]
    for name, c in s["low_high_contrasts"].items():
        lines.append(f"- {name}: {c['sign']}; point difference {c['point']}; {c['note']}")
    lines += ["", "One fixed batch only. Inspect missingness, controls, decimal notation, both order",
              "checks and conditional fidelity before discussing social contrasts. Stable null or",
              "contrary results are valid outcomes. Do not rerun until a preferred pattern appears.",
              "This diagnostic covers two boxes causes and numerical T2 only, not all debug cells.", ""]
    return "\n".join(lines)


def save_reports(path: Path, items: list[DiagnosticItem], rows: list[DebugResponse]) -> str:
    summary = summarize(items, rows)
    rendered = report(items, rows)
    path.with_suffix(".md").write_text(rendered)
    path.with_suffix(".diagnostic.json").write_text(json.dumps(summary, indent=2) + "\n")
    for name, key in (("control-review.jsonl", "controls"), ("binary-review.jsonl", "binary_review")):
        path.with_name(name).write_text("".join(json.dumps(c) + "\n" for c in summary[key]))
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
        (OUT / "items.jsonl").write_text("".join(i.model_dump_json() + "\n" for i in items))
        (OUT / "protocol.json").write_text(json.dumps(config(items), indent=2) + "\n")
        print(f"{len(items)} requests; hash {batch_hash(items)}; no API calls")
    elif args.command == "inspect":
        print(save_reports(args.path, items, load_run(args.path, items)))
    else:
        rows = run(items, DebugResponder(), args.out, resume=args.resume)
        print(save_reports(args.out, items, rows))


if __name__ == "__main__":
    main()
