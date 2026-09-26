"""Frozen 144-request social pilot; no known-answer keys or scientific pass gate.

check/generate/report/samples are offline. Only run --confirm 144 calls the API.
The shared v3.2 renderer, response protocol and strict decoder stay unchanged.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

from wtrbench.paired import natural

PROTOCOL = "paired-pilot-v1"
BASE = "8adf2fb47174209ab6988693704fa7685f8d7343"
ROOT = Path(__file__).resolve().parents[3]
PLAN = "docs/paired-pilot-v1.md"
DECISION = "docs/paired-pilot-v1-decision.md"
SCENARIOS = "protocols/paired-pilot-v1-scenarios.json"
PACKED = "protocols/paired-pilot-v1-items.jsonl.gz"
FREEZE = "protocols/paired-pilot-v1.json"
SAMPLES = "docs/paired-pilot-v1-samples.md"
OUT = Path("runs/paired-pilot-v1")
PROBES = ("valuation", "ability_same", "ability_different")
SEMANTICS = ("unable", "unwilling", "equal", "insufficient", "invalid", "missing")
SOURCE_FILES = (
    "src/wtrbench/__init__.py", "src/wtrbench/paired/__init__.py", "src/wtrbench/paired/natural.py",
    "src/wtrbench/paired/social.py", "tests/test_paired_social_pilot.py",
    PLAN, DECISION, SCENARIOS, SAMPLES, PACKED,
    ".github/workflows/paired-pilot-v1.yml",
)
CONTEXT = (
    "The following accounts describe two separate occasions. Each occasion involved only "
    "the person named in that account, not both people together."
)
PERSISTENCE = (
    "For the future situations below, each person's task-relevant knowledge and physical "
    "limitations remain as described."
)


def scenarios() -> list[dict[str, str]]:
    return json.loads((ROOT / SCENARIOS).read_text(encoding="utf-8"))


def render(
    scenario: dict[str, str], probe: str, assignment: int, position: int,
) -> tuple[str, dict[str, str], list[str]]:
    if probe not in PROBES or assignment not in (0, 1) or position not in (0, 1):
        raise ValueError("Unknown probe or counterbalancing level")
    names = dict(zip(("unable", "unwilling"), ("Priya", "Sam") if assignment else ("Sam", "Priya")))
    order = ("unwilling", "unable") if position else ("unable", "unwilling")
    evidence = [CONTEXT]
    for cause in order:
        name = names[cause]
        evidence.append(
            f"{name} is an acquaintance. Last week you asked {name} to {scenario['help']}. "
            + scenario[cause].format(name=name) + " " + scenario["outcome_fail"]
        )
    evidence.append(PERSISTENCE)
    task = scenario["diff_ask"] if probe == "ability_different" else scenario["same_ask"]
    prompt = natural.render_pair(
        names[order[0]], names[order[1]], evidence,
        "valuation" if probe == "valuation" else "ability", own=5, task=task,
    )
    mapping = {"A": order[0], "B": order[1], "C": "equal", "D": "insufficient"}
    return prompt, mapping, evidence


def generate_items() -> list[dict[str, Any]]:
    items = []
    for repetition in (1, 2):
        batch = []
        for scenario, probe, assignment, position in product(scenarios(), PROBES, (0, 1), (0, 1)):
            prompt, mapping, evidence = render(scenario, probe, assignment, position)
            item = {
                "protocol": PROTOCOL, "scenario": scenario["scenario"], "probe": probe,
                "name_assignment": assignment, "position": position, "repetition": repetition,
                "semantic_map": mapping, "evidence": evidence, "prompt": prompt,
                # Shared decoder fields are null: predictions are NOT correctness keys.
                "expected_private": None, "exploratory_expected_private": None,
            }
            item["item_id"] = PROTOCOL + "-" + natural.digest(item)[:20]
            batch.append(item)
        batch.sort(key=lambda item: natural.digest([PROTOCOL, item["item_id"]]))
        items.extend(batch)
    return items


def samples_text() -> str:
    parts = ["# Paired pilot v1: all six scenarios, canonical presentation", "",
             "These are stimuli, not model data. Each scenario has all three probes below.",
             "Names/order are crossed by the frozen generator. All 144 scheduled items are",
             "also committed as protocols/paired-pilot-v1-items.jsonl.gz.", ""]
    for scenario, probe in product(scenarios(), PROBES):
        prompt, _, _ = render(scenario, probe, 0, 0)
        parts.extend([f"## {scenario['scenario']} / {probe}", "", "```text", prompt, "```", ""])
    return "\n".join(parts) + "\n"


def manifest() -> dict[str, Any]:
    items = generate_items()
    return {
        "protocol": PROTOCOL, "baseline_commit": BASE, "validation_run": 36200022149,
        "n_requests": 144, "n_scenarios": 6, "n_distinct_prompts": 72,
        "items_jsonl_sha256": natural.stream_hash(items),
        "request_bodies_jsonl_sha256": natural.stream_hash([natural.request_body(i) for i in items]),
        "source_sha256": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_FILES
        },
    }


def verify_freeze() -> dict[str, Any]:
    actual = manifest()
    if json.loads((ROOT / FREEZE).read_text()) != actual:
        raise ValueError("Pilot freeze mismatch; use the frozen revision, not an edited freeze")
    items = generate_items()
    packed = gzip.decompress((ROOT / PACKED).read_bytes()).decode()
    if packed != "".join(natural.wire(i) + "\n" for i in items):
        raise ValueError("Committed items differ from generated schedule")
    if (ROOT / SAMPLES).read_text() != samples_text():
        raise ValueError("Committed sample prompts differ")
    if len(items) != 144 or len({i["prompt"] for i in items}) != 72:
        raise ValueError("Pilot schedule size changed")
    return actual


def validate(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    if items != generate_items():
        raise ValueError("Only the complete fixed pilot schedule can be scored")
    natural.validate_records(items, rows)


def observations(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validate(items, rows)
    by_id = {r["item_id"]: r for r in rows}
    result = []
    for item in items:
        row = by_id.get(item["item_id"])
        api = {} if row is None else row["api_response"]
        decoded = natural.decode(item, api)
        semantic = "missing" if row is None else (decoded["semantic"] or "invalid")
        result.append({
            **{k: item[k] for k in (
                "item_id", "scenario", "probe", "name_assignment", "position", "repetition",
            )},
            "answer": decoded["answer"], "semantic": semantic,
            "brief_basis": decoded["brief_basis"], "stop_reason": api.get("stop_reason"),
            "request_id": None if row is None else row.get("request_id"),
            "raw": "".join(b.get("text", "") for b in api.get("content", [])
                           if isinstance(b, dict) and b.get("type") == "text"),
        })
    return result


def distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(r["semantic"] for r in rows)
    return {s: counts[s] for s in SEMANTICS}


def net(rows: list[dict[str, Any]]) -> float:
    """Difference of scheduled response proportions, NOT a WTR or giving probability."""
    counts = distribution(rows)
    return (counts["unable"] - counts["unwilling"]) / len(rows)


def pair_audit(obs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    factors = {
        "position": ("scenario", "probe", "name_assignment", "repetition"),
        "name": ("scenario", "probe", "position", "repetition"),
        "repeat": ("scenario", "probe", "name_assignment", "position"),
    }
    for factor, fields in factors.items():
        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in obs:
            groups[tuple(row[k] for k in fields)].append(row)
        for key, pair in groups.items():
            if len(pair) != 2:
                raise ValueError("Broken pair")
            a, b = pair
            comparable = all(r["semantic"] not in ("invalid", "missing") for r in pair)
            results.append({
                "factor": factor, **dict(zip(fields, key)),
                "item_ids": [a["item_id"], b["item_id"]],
                "semantics": [a["semantic"], b["semantic"]], "comparable": comparable,
                "disagreement": a["semantic"] != b["semantic"] if comparable else None,
            })
    return results


def summarize(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    obs = observations(items, rows)
    pairs = pair_audit(obs)
    cells = []
    crossovers = []
    for scenario in scenarios():
        sid = scenario["scenario"]
        subset = [r for r in obs if r["scenario"] == sid]
        for probe in PROBES:
            cell = sorted((r for r in subset if r["probe"] == probe), key=lambda r: (
                r["repetition"], r["name_assignment"], r["position"],
            ))
            cells.append({
                "scenario": sid, "probe": probe, "scheduled": 8,
                "counts": distribution(cell), "net_unable_minus_unwilling": net(cell),
                "by_pass": {str(rep): distribution([r for r in cell if r["repetition"] == rep])
                            for rep in (1, 2)},
                "answers": cell,
            })
        forms: dict[tuple[int, int, int], dict[str, str]] = defaultdict(dict)
        for row in subset:
            key = (row["name_assignment"], row["position"], row["repetition"])
            forms[key][row["probe"]] = row["semantic"]
        counts: Counter[str] = Counter()
        for value in forms.values():
            v, a = value["valuation"], value["ability_same"]
            if "missing" in (v, a) or "invalid" in (v, a):
                counts["invalid_or_missing"] += 1
            elif (v, a) == ("unable", "unwilling"):
                counts["predicted_crossover"] += 1
            elif (v, a) == ("unwilling", "unable"):
                counts["reverse_crossover"] += 1
            elif v in ("unable", "unwilling") and a in ("unable", "unwilling"):
                counts["same_person_on_both"] += 1
            else:
                counts["includes_equal_or_insufficient"] += 1
        vn = net([r for r in subset if r["probe"] == "valuation"])
        an = net([r for r in subset if r["probe"] == "ability_same"])
        crossovers.append({
            "scenario": sid, "scheduled_matched_forms": 8,
            "counts": {k: counts[k] for k in (
                "predicted_crossover", "reverse_crossover", "same_person_on_both",
                "includes_equal_or_insufficient", "invalid_or_missing",
            )},
            "valuation_net": vn, "same_ability_net": an, "net_difference": vn - an,
            "both_net_directions_as_predicted": vn > 0 and an < 0,
        })
    sensitivity = {}
    for factor in ("position", "name", "repeat"):
        group = [p for p in pairs if p["factor"] == factor]
        sensitivity[factor] = {
            "scheduled_pairs": len(group), "comparable_pairs": sum(p["comparable"] for p in group),
            "disagreements": sum(p["disagreement"] is True for p in group),
            "by_probe": {probe: {
                "scheduled_pairs": 24,
                "comparable_pairs": sum(p["comparable"] for p in group if p["probe"] == probe),
                "disagreements": sum(p["disagreement"] is True for p in group if p["probe"] == probe),
            } for probe in PROBES},
        }
    return {
        "protocol": PROTOCOL, "completion": "COMPLETE" if len(rows) == 144 else "INCOMPLETE",
        "recorded": len(rows), "scheduled": 144, "scenario_count": 6, "distinct_prompts": 72,
        "counts": distribution(obs), "cells": cells, "crossovers": crossovers,
        "by_probe": {probe: distribution([r for r in obs if r["probe"] == probe]) for probe in PROBES},
        "presentation_sensitivity": sensitivity,
        "scenarios_with_both_net_directions": sum(c["both_net_directions_as_predicted"] for c in crossovers),
        "scientific_pass_fail": None,
        "interpretation": (
            "Descriptive predictions, not known-answer accuracy. Six selected scenarios; "
            "repetitions and presentation variants are not independent scenarios. "
            "C, D, invalid and missing are separate; no answers are repaired from explanations."
        ),
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export(out: Path) -> list[dict[str, Any]]:
    frozen = verify_freeze()
    if any((out / name).exists() for name in ("collection-started.json", "responses.jsonl")):
        raise FileExistsError("Do not overwrite a started pilot")
    out.mkdir(parents=True, exist_ok=True)
    items = generate_items()
    for name, values in (("items.jsonl", items), ("requests.jsonl", [natural.request_body(i) for i in items])):
        (out / name).write_text("".join(natural.wire(v) + "\n" for v in values), encoding="utf-8")
    write_json(out / "freeze.json", frozen)
    for source, name in ((PLAN, "analysis-plan.md"), (DECISION, "decision.md"), (SAMPLES, "samples.md")):
        (out / name).write_bytes((ROOT / source).read_bytes())
    # Self-contained source snapshot of everything bound by this freeze.
    # Include the manifest at its normal path so check/report run inside the snapshot.
    # It is deliberately not hashed by itself in SOURCE_FILES.
    for source in (*SOURCE_FILES, FREEZE):
        dest = out / "frozen-source" / source
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / source).read_bytes())
    return items


def report(out: Path) -> dict[str, Any]:
    frozen = verify_freeze()
    if json.loads((out / "freeze.json").read_text()) != frozen:
        raise ValueError("Run freeze mismatch")
    for filename, key in (("items.jsonl", "items_jsonl_sha256"), ("requests.jsonl", "request_bodies_jsonl_sha256")):
        if hashlib.sha256((out / filename).read_bytes()).hexdigest() != frozen[key]:
            raise ValueError("Run stimulus artifact altered")
    cfg = json.loads((out / "collection-started.json").read_text())
    if cfg.get("freeze") != frozen or cfg.get("protocol") != PROTOCOL:
        raise ValueError("Collection metadata mismatch")
    rows = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines()]
    items = generate_items()
    result = summarize(items, rows)
    result["data_origin"] = cfg["data_origin"]
    obs = observations(items, rows)
    write_json(out / "report.json", result)
    write_json(out / "pair-audit.json", pair_audit(obs))
    with (out / "answer-audit.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(obs[0]))
        writer.writeheader()
        writer.writerows(obs)
    lines = [f"# {PROTOCOL}: {result['completion']}", "",
             f"Data origin: {cfg['data_origin']}. Records: {len(rows)}/144. No scientific PASS/FAIL.",
             "Six scenarios, three probes, eight presentations per cell; 72 distinct prompts.", "",
             "| Scenario | Probe | Unable | Unwilling | Equal | Insufficient | Invalid | Missing | Net |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for cell in result["cells"]:
        nums = " | ".join(str(cell["counts"][s]) for s in SEMANTICS)
        lines.append(f"| {cell['scenario']} | {cell['probe']} | {nums} | {cell['net_unable_minus_unwilling']:.3f} |")
    lines.extend(["", "## Matched valuation / same-task ability responses", "",
                  "| Scenario | Predicted crossover / 8 | Reverse / 8 | Same person | Includes C/D | Invalid/missing | V net | Ability net |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for row in result["crossovers"]:
        c = row["counts"]
        lines.append(
            f"| {row['scenario']} | {c['predicted_crossover']} | {c['reverse_crossover']} | "
            f"{c['same_person_on_both']} | {c['includes_equal_or_insufficient']} | "
            f"{c['invalid_or_missing']} | {row['valuation_net']:.3f} | {row['same_ability_net']:.3f} |"
        )
    lines.extend(["", "## Presentation sensitivity", "",
                  "| Factor | Disagreements | Comparable pairs | Scheduled pairs |",
                  "|---|---:|---:|---:|"])
    for factor, value in result["presentation_sensitivity"].items():
        lines.append(f"| {factor} | {value['disagreements']} | {value['comparable_pairs']} | 72 |")
    lines.extend(["", "Net = (unable selections - unwilling selections) / 8 scheduled responses.",
                  "C/D/invalid/missing add no directional count but stay separately visible.",
                  "Net is not a giving probability or WTR. An interaction-like difference alone",
                  "does not establish both predicted directions. No control correctness keys apply.",
                  "See report.json for all eight responses in each cell and all pass splits.",
                  "No explanation review is performed by this scorer. Do not rerun collection."])
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def collect(
    out: Path, send: Callable[[dict[str, Any]], tuple[dict[str, Any], str | None]], *,
    data_origin: str = "programmed_test_fixture",
) -> None:
    items = export(out)
    with (out / "collection-started.json").open("x", encoding="utf-8") as lock:
        json.dump({
            "protocol": PROTOCOL, "data_origin": data_origin,
            "started_utc": datetime.now(UTC).isoformat(), "python": platform.python_version(),
            "github_sha": os.environ.get("GITHUB_SHA"), "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "max_retries": 0,
            "sdk_version": importlib.metadata.version("anthropic") if data_origin == "anthropic_api" else None,
            "freeze": manifest(),
        }, lock, indent=2)
    rows = []
    with (out / "responses.jsonl").open("x", encoding="utf-8") as fh:
        for item in items:
            body = natural.request_body(item)
            try:
                api, request_id = send(body)
            except Exception as exc:
                write_json(out / "transport-stop.json", {
                    "item_id": item["item_id"], "exception_type": type(exc).__name__,
                    "attempted_body": body,
                })
                raise
            row = {"item_id": item["item_id"], "request_body": body,
                   "api_response": api, "request_id": request_id}
            fh.write(natural.wire(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            rows.append(row)
            try:
                natural.validate_records(items, rows)
            except ValueError as exc:
                write_json(out / "integrity-stop.json", {"item_id": item["item_id"], "reason": str(exc)})
                raise
            if len(rows) % 12 == 0:
                print(f"Recorded {len(rows)}/144", flush=True)
    report(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "generate", "samples", "run", "report"))
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--confirm", type=int)
    args = parser.parse_args()
    if args.command == "run":
        if args.confirm != 144:
            parser.error("Collection requires --confirm 144 for the one reviewed pilot")
        if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
            parser.error("Do not use Re-run jobs to recollect")
        collect(args.out, natural.send_anthropic, data_origin="anthropic_api")
    elif args.command == "check":
        print(natural.wire(verify_freeze()))
    elif args.command == "generate":
        print(f"Exported {len(export(args.out))} scheduled requests. No model calls.")
    elif args.command == "samples":
        print(samples_text(), end="")
    else:
        print(json.dumps(report(args.out), indent=2))


if __name__ == "__main__":
    main()
