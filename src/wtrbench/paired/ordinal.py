"""Paired ordinal v2. Generate/check/report are offline; run requires opt-in.

python -m wtrbench.paired.ordinal generate --out runs/paired-v2
python -m wtrbench.paired.ordinal run --out runs/paired-v2 --confirm 240
python -m wtrbench.paired.ordinal report --out runs/paired-v2

There is deliberately no social-pilot generator or collection route here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
from collections import Counter, defaultdict
from datetime import UTC, datetime
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any, Callable

PROTOCOL = "paired-ordinal-v2"
MODEL = "claude-sonnet-4-5-20250929"
BASE = "fcef24a33514ece1306e6c97015c8e3d38737663"
ROOT = Path(__file__).resolve().parents[3]
PLAN = "docs/paired-ordinal-v2.md"
FREEZE = "protocols/paired-ordinal-v2.json"
CATEGORIES = ("discriminating", "both_give", "both_keep", "ability_conflict",
              "ability_equal", "underdetermined")
TASKS = ("calibrate a laboratory scale", "fold a fitted sheet", "tune a ukulele",
         "thread a sewing machine", "solve a tangram puzzle")
SOURCE_FILES = ("src/wtrbench/paired/__init__.py", "src/wtrbench/paired/ordinal.py",
                "tests/test_paired_ordinal_v2.py", PLAN,
                ".github/workflows/paired-ordinal-v2.yml")


def wire(value: Any) -> str:
    """Preserve schema/property ordering in actual request bodies and saved records."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def stream_hash(values: list[Any]) -> str:
    return hashlib.sha256("".join(wire(v) + "\n" for v in values).encode()).hexdigest()


def cases() -> list[dict[str, Any]]:
    """Thirty new numerical parameterizations, not thirty independent reasoning domains."""
    out = []
    for k, category in enumerate(CATEGORIES):
        for j in range(5):
            i = 5 * k + j
            den = 40 + 2 * i
            lo = (2, 5, 10, 15, 20)[j] * den // 10 - 5
            bounds = {"P": (lo, lo + 3, den), "Q": (lo + 8, lo + 12, den)}
            own = 2 * (lo + 5)
            if category == "both_give":
                own = 2 * (lo - 1)
            elif category == "both_keep":
                own = 2 * (lo + 14)
            elif category == "underdetermined":
                bounds = {"P": (lo, lo + 8, den), "Q": (lo + 2, lo + 10, den)}
            skills = {"P": 84 - j * 3, "Q": 24 + j * 4}
            if category == "ability_equal":
                skills = {"P": 61 + j * 4, "Q": 61 + j * 4}
            out.append({"case_id": f"{category}-{j + 1}", "category": category,
                        "bounds": bounds, "own": own, "other": 2 * den,
                        "skills": skills, "task": TASKS[j], "reverse_history": bool(i % 2)})
    return out


def possible_choices(bounds: tuple[int, int, int], own: int, other: int) -> set[str]:
    lo, hi, den = bounds
    ratio = Fraction(own, other)
    choices = set()
    if Fraction(lo, den) < ratio:
        choices.add("keep")
    if ratio < Fraction(hi, den):
        choices.add("give")
    return choices


def truth(case: dict[str, Any]) -> str:
    if case["category"].startswith("ability_"):
        a, b = case["skills"]["P"], case["skills"]["Q"]
        return "equal" if a == b else ("P" if a > b else "Q")
    possibilities = {
        "equal" if p == q else ("P" if p == "give" else "Q")
        for p, q in product(*(possible_choices(case["bounds"][x], case["own"], case["other"])
                              for x in ("P", "Q")))
    }
    if not possibilities:
        raise ValueError("Empty compatible state set")
    return next(iter(possibilities)) if len(possibilities) == 1 else "insufficient"


def render(case: dict[str, Any], assignment: int, position: int) -> tuple[str, dict[str, str]]:
    # Bind names to people BEFORE changing presentation order: genuinely distinct factors.
    names = dict(zip(("P", "Q"), ("Priya", "Sam") if assignment else ("Sam", "Priya")))
    order = ("Q", "P") if position else ("P", "Q")
    lines = [f"{names[order[0]]} and {names[order[1]]} are two people you have dealt with.",
        "For point choices, each uses own points + w times your points, with their own fixed "
        "nonnegative w, and always chooses the strictly higher value. The histories below "
        "and current point choices contain no exact value ties. Choosing points requires no "
        "special skill. For these constructed cases use only the stated facts; do not invent "
        "a probability distribution over unknown weights. If different compatible weights "
        "imply different comparisons, the evidence is insufficient, rather than evidence of "
        "equal probabilities.", ""]
    for who in order:
        name = names[who]
        lo, hi, den = case["bounds"][who]
        histories = [("GIVE", lo), ("KEEP", hi)]
        if case["reverse_history"]:
            histories.reverse()
        for choice, amount in histories:
            lines.append(f"{name} chose {choice} when the alternatives were "
                         f"KEEP ({name}: {amount}; you: 0) or GIVE ({name}: 0; you: {den}).")
    lines.append("")
    if case["category"].startswith("ability_"):
        lines.append(f"For the task '{case['task']}', assume the following exact success "
                     "probabilities for a future attempt with genuine effort and enough time. "
                     "They are independent of the point choices and weights.")
        for who in order:
            lines.append(f"{names[who]}'s success probability: {case['skills'][who]}%.")
        lines.append("Which person is more likely to succeed at that task under those conditions?")
    else:
        lines.append(f"Now each independently chooses between KEEP (self: {case['own']}; you: 0) "
                     f"and GIVE (self: 0; you: {case['other']}). "
                     "Which person is more likely to choose GIVE?")
    lines.extend([f"(A) {names[order[0]]}", f"(B) {names[order[1]]}",
                  "(C) Their probabilities are equal on the stated evidence.",
                  "(D) The stated evidence is insufficient to determine this comparison."])
    mapping = {"A": order[0], "B": order[1], "C": "equal", "D": "insufficient"}
    return "\n".join(lines), mapping


def generate_items() -> list[dict[str, Any]]:
    out = []
    for repetition in (1, 2):
        batch = []
        for case, assignment, position in product(cases(), (0, 1), (0, 1)):
            prompt, mapping = render(case, assignment, position)
            item = {"case_id": case["case_id"], "category": case["category"],
                    "name_assignment": assignment, "position": position, "repetition": repetition,
                    "prompt": prompt, "semantic_map": mapping, "expected_private": truth(case)}
            item["item_id"] = PROTOCOL + "-" + digest(item)[:20]
            batch.append(item)
        batch.sort(key=lambda x: digest([PROTOCOL, x["item_id"]]))
        out.extend(batch)
    return out


def request_body(item: dict[str, Any]) -> dict[str, Any]:
    return {"model": MODEL, "temperature": 0, "max_tokens": 256,
        "system": 'Return exactly two JSON fields in this order: "brief_basis", a one- or '
                  'two-sentence explanation using the supplied information; then "answer", '
                  'one of A, B, C, D. Do not include any other fields.',
        "messages": [{"role": "user", "content": item["prompt"]}],
        "output_config": {"format": {"type": "json_schema", "schema": {
            "type": "object", "properties": {"brief_basis": {"type": "string"},
            "answer": {"type": "string", "enum": ["A", "B", "C", "D"]}},
            "required": ["brief_basis", "answer"], "additionalProperties": False}}}}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, field in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = field
    return value


def decode(item: dict[str, Any], api: dict[str, Any]) -> dict[str, Any]:
    answer, basis = None, None
    blocks = api.get("content")
    if (api.get("stop_reason") == "end_turn" and isinstance(blocks, list) and len(blocks) == 1
            and isinstance(blocks[0], dict) and blocks[0].get("type") == "text"):
        try:
            value = json.loads(blocks[0]["text"], object_pairs_hook=_unique_object)
            if (isinstance(value, dict) and list(value) == ["brief_basis", "answer"]
                    and isinstance(value["brief_basis"], str) and value["brief_basis"].strip()
                    and isinstance(value["answer"], str) and value["answer"] in ("A", "B", "C", "D")):
                answer, basis = value["answer"], value["brief_basis"]
        except (ValueError, TypeError, KeyError):
            pass
    semantic = item["semantic_map"].get(answer)
    return {"answer": answer, "brief_basis": basis, "semantic": semantic,
            "correct": semantic is not None and semantic == item["expected_private"]}


def manifest() -> dict[str, Any]:
    items = generate_items()
    return {"protocol": PROTOCOL, "baseline_commit": BASE, "n_requests": len(items),
            "n_base_cases": len(cases()), "items_jsonl_sha256": stream_hash(items),
            "request_bodies_jsonl_sha256": stream_hash([request_body(i) for i in items]),
            "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                              for p in SOURCE_FILES}}


def verify_freeze() -> dict[str, Any]:
    actual = manifest()
    if json.loads((ROOT / FREEZE).read_text()) != actual:
        raise ValueError("Freeze mismatch: use the committed revision; do not rewrite a used freeze")
    return actual


def validate_records(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    if len(rows) > len(items):
        raise ValueError("Too many records")
    messages: set[str] = set()
    requests: set[str] = set()
    for item, row in zip(items, rows):
        if row.get("item_id") != item["item_id"] or wire(row.get("request_body")) != wire(request_body(item)):
            raise ValueError("Unknown, reordered, duplicate, or altered request")
        api = row["api_response"]
        if api.get("model") != MODEL:
            raise ValueError("Returned model mismatch")
        mid = api.get("id")
        if not isinstance(mid, str) or not mid or mid in messages:
            raise ValueError("Missing or duplicate message id")
        messages.add(mid)
        rid = row.get("request_id")
        if rid is not None:
            if not isinstance(rid, str) or not rid or rid in requests:
                raise ValueError("Invalid or duplicate request id")
            requests.add(rid)


def summarize(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    if items != generate_items():
        raise ValueError("Only the complete fixed schedule may be scored")
    validate_records(items, rows)
    decoded = {r["item_id"]: decode(i, r["api_response"]) for i, r in zip(items, rows)}
    missing = {"answer": None, "semantic": None, "correct": False}
    stats: dict[str, dict[str, Any]] = {}
    for category in CATEGORIES:
        subset = [i for i in items if i["category"] == category]
        answers = [decoded.get(i["item_id"], missing) for i in subset]
        d: dict[str, Any] = {"base_cases": 5, "scheduled_answers": 40,
            "correct": sum(a["correct"] for a in answers),
            "unusable_or_missing": sum(a["answer"] is None for a in answers),
            "C": sum(a["answer"] == "C" for a in answers),
            "D": sum(a["answer"] == "D" for a in answers)}
        for factor, fields in {
            "position": ("case_id", "name_assignment", "repetition"),
            "name": ("case_id", "position", "repetition"),
            "repeat": ("case_id", "name_assignment", "position"),
        }.items():
            pairs: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
            for item in subset:
                pairs[tuple(item[f] for f in fields)].append(item)
            joint: Counter[str] = Counter()
            comparable = disagree = 0
            for pair in pairs.values():
                if len(pair) != 2:
                    raise ValueError("Incomplete factorial pair")
                a, b = [decoded.get(i["item_id"], missing) for i in pair]
                if a["semantic"] is not None and b["semantic"] is not None:
                    comparable += 1
                    disagree += a["semantic"] != b["semantic"]
                if a["correct"] and b["correct"]:
                    joint[str(pair[0]["repetition"])] += 1
            d[factor] = {"scheduled_pairs": len(pairs), "comparable_pairs": comparable,
                         "disagreements": disagree}
            if factor == "position":
                d["joint_correct"] = sum(joint.values())
                d["joint_by_pass"] = {str(r): joint[str(r)] for r in (1, 2)}
                d["joint_rate"] = sum(joint.values()) / 20
                d["pass_gate"] = all(joint[str(r)] >= 9 for r in (1, 2))
        d["base_cases_all_eight_correct"] = sum(
            all(decoded.get(i["item_id"], missing)["correct"] for i in subset if i["case_id"] == cid)
            for cid in {i["case_id"] for i in subset})
        stats[category] = d
    d_errors = sum(stats[c]["D"] for c in CATEGORIES if c != "underdetermined")
    complete = len(rows) == len(items)
    passes = complete and all(d["pass_gate"] for d in stats.values()) and d_errors <= 10
    return {"protocol": PROTOCOL, "data_origin": "Recorded outputs; provenance in collection-started.json",
            "complete": complete, "recorded": len(rows), "scheduled": len(items),
            "categories": stats, "D_on_determined": {"count": d_errors, "denominator": 200},
            "gate": "PASS" if passes else ("FAIL" if complete else "INCOMPLETE"),
            "explanation_review": "Not performed by this scorer; answers are never repaired from prose",
            "pilot_authorized": False,
            "interpretation": "Finite-set development gate, not a population error bound."}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export(out: Path) -> list[dict[str, Any]]:
    frozen = verify_freeze()
    if (out / "collection-started.json").exists() or (out / "responses.jsonl").exists():
        raise FileExistsError("Do not overwrite a started collection")
    out.mkdir(parents=True, exist_ok=True)
    items = generate_items()
    for name, values in (("items.jsonl", items), ("requests.jsonl", [request_body(i) for i in items])):
        (out / name).write_text("".join(wire(v) + "\n" for v in values), encoding="utf-8")
    write_json(out / "freeze.json", frozen)
    (out / "analysis-plan.md").write_bytes((ROOT / PLAN).read_bytes())
    return items


def report(out: Path) -> dict[str, Any]:
    verify_freeze()
    if json.loads((out / "freeze.json").read_text()) != manifest():
        raise ValueError("Run freeze mismatch")
    rows = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines()]
    items = generate_items()
    result = summarize(items, rows)
    write_json(out / "report.json", result)
    by_id = {r["item_id"]: r for r in rows}
    with (out / "answer-audit.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = ["item_id", "case_id", "category", "name_assignment", "position", "repetition",
                  "expected_private", "answer", "semantic", "correct", "brief_basis", "stop_reason"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for item in items:
            row = by_id.get(item["item_id"], {})
            api = row.get("api_response", {})
            writer.writerow({**{f: item[f] for f in fields if f in item}, **decode(item, api),
                             "stop_reason": api.get("stop_reason", "missing")})
    text = [f"# {PROTOCOL}: {result['gate']}", "",
            f"Records: {len(rows)}/240. Base cases: 30 (six constructed categories).",
            "The gate concerns these final answers only; it does not authorize a social pilot.", "",
            "| Category | Correct / 40 | Joint pass 1 / 10 | Joint pass 2 / 10 | C | D | Unusable/missing |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for cat, s in result["categories"].items():
        text.append(f"| {cat} | {s['correct']} | {s['joint_by_pass']['1']} | "
                    f"{s['joint_by_pass']['2']} | {s['C']} | {s['D']} | {s['unusable_or_missing']} |")
    text.extend(["", "See report.json for position, name and repeat comparisons with denominators.",
                 "See answer-audit.csv for every scheduled item, including missing responses.",
                 "Repeated presentations are not independent participants or fresh scenarios."])
    (out / "report.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return result


def collect(out: Path, send: Callable[[dict[str, Any]], tuple[dict[str, Any], str | None]],
            *, data_origin: str = "programmed_test_fixture") -> None:
    items = export(out)
    with (out / "collection-started.json").open("x", encoding="utf-8") as lock:
        json.dump({"data_origin": data_origin, "started_utc": datetime.now(UTC).isoformat(),
            "github_sha": os.environ.get("GITHUB_SHA"), "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "python": platform.python_version(),
            "sdk_version": importlib.metadata.version("anthropic") if data_origin == "anthropic_api" else None,
            "max_retries": 0, "freeze": manifest()}, lock, indent=2)
    rows = []
    with (out / "responses.jsonl").open("x", encoding="utf-8") as fh:
        for item in items:
            body = request_body(item)
            try:
                api, request_id = send(body)
            except Exception as exc:
                write_json(out / "transport-stop.json", {"item_id": item["item_id"],
                           "exception_type": type(exc).__name__, "attempted_body": body})
                raise
            row = {"item_id": item["item_id"], "request_body": body,
                   "api_response": api, "request_id": request_id}
            fh.write(wire(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            rows.append(row)  # Preserve raw output before any integrity failure.
            validate_records(items, rows)
            if len(rows) % 20 == 0:
                print(f"Recorded {len(rows)}/240", flush=True)
    report(out)


_CLIENT: Any = None


def send_anthropic(body: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    global _CLIENT
    if _CLIENT is None:
        from anthropic import Anthropic
        _CLIENT = Anthropic(max_retries=0, timeout=120.0)
    message = _CLIENT.messages.create(
        model=body["model"], max_tokens=body["max_tokens"], system=body["system"],
        messages=body["messages"], output_config=body["output_config"],
        extra_body={"temperature": body["temperature"]})
    return message.model_dump(mode="json"), getattr(message, "_request_id", None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check", "report", "run"))
    parser.add_argument("--out", type=Path, default=Path("runs/paired-v2"))
    parser.add_argument("--confirm", type=int)
    args = parser.parse_args()
    if args.command == "run":
        if args.confirm != 240:
            parser.error("Collection requires --confirm 240 after reviewing the committed plan")
        if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
            parser.error("GitHub Re-run jobs is disabled for this collection")
        collect(args.out, send_anthropic, data_origin="anthropic_api")
    elif args.command == "report":
        print(json.dumps(report(args.out), indent=2))
    elif args.command == "check":
        print(wire(verify_freeze()))
    else:
        print(f"Exported {len(export(args.out))} scheduled requests. No model calls.")


if __name__ == "__main__":
    main()
