"""One frozen Qwen3-14B replication. Only run --confirm 144 makes model calls."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import platform
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wtrbench.paired import natural, social

PROTOCOL = "paired-open-v1"
MODEL = "Qwen/Qwen3-14B"
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
CATALOG = "https://api.deepinfra.com/models/list"
QUANTIZATION = "fp8"
ROOT = Path(__file__).resolve().parents[3]
PLAN = "docs/paired-open-v1.md"
PROVIDER = "protocols/paired-open-v1-provider.json"
FREEZE = "protocols/paired-open-v1.json"
OUT = Path("runs/paired-open-v1")
SOURCE_FILES = (*social.SOURCE_FILES, social.FREEZE,
                "src/wtrbench/paired/open_replication.py", "tests/test_paired_open_replication.py",
                ".github/workflows/paired-open-v1.yml", PLAN, PROVIDER, "pyproject.toml", "uv.lock")
# Pure scoring operations from the original frozen pilot. No model identity is rewritten.
PROBES, SEMANTICS = social.PROBES, social.SEMANTICS
scenarios, distribution, net, pair_audit = (
    social.scenarios, social.distribution, social.net, social.pair_audit,
)
write_json = social.write_json


def request_body(item: dict[str, Any]) -> dict[str, Any]:
    original = natural.request_body(item)
    return {
        "model": MODEL, "temperature": 0, "max_tokens": 256, "stream": False, "n": 1,
        "reasoning_effort": "none",
        "messages": [{"role": "system", "content": original["system"]}, *original["messages"]],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "paired_response", "strict": True,
            "schema": original["output_config"]["format"]["schema"],
        }},
    }


def manifest() -> dict[str, Any]:
    items = social.generate_items()
    return {
        "protocol": PROTOCOL, "model": MODEL, "endpoint": ENDPOINT,
        "reported_quantization": QUANTIZATION, "hosted_weight_revision": None,
        "original_run": 36216737006,
        "baseline_commit": "ff507473ff7fcdd229f7f8c7e23a52fb7b24a605",
        "n_requests": 144, "n_scenarios": 6, "n_distinct_prompts": 72,
        "items_jsonl_sha256": natural.stream_hash(items),
        "request_bodies_jsonl_sha256": natural.stream_hash([request_body(i) for i in items]),
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                          for p in SOURCE_FILES},
    }


def verify_freeze() -> dict[str, Any]:
    original = social.verify_freeze()
    actual = manifest()
    if actual["items_jsonl_sha256"] != original["items_jsonl_sha256"]:
        raise ValueError("Original item stream changed")
    if json.loads((ROOT / FREEZE).read_text()) != actual:
        raise ValueError("Replication freeze mismatch; do not rewrite a collected freeze")
    return actual


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward the credential or silently change an inference endpoint."""

    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any,
                         headers: Any, newurl: Any) -> None:
        return None


def fetch_catalog() -> dict[str, Any]:
    with urllib.request.urlopen(CATALOG, timeout=30) as response:
        entries = json.load(response)
    matches = [e for e in entries if e.get("model_name") == MODEL]
    if len(matches) != 1:
        raise ValueError("Selected model absent or duplicated in provider catalog")
    return matches[0]


def check_catalog(entry: dict[str, Any]) -> None:
    if (entry.get("model_name") != MODEL or entry.get("deprecated") is not None
            or entry.get("replaced_by") is not None
            or entry.get("quantization") != QUANTIZATION
            or not {"structured-output", "non-reasoning"}.issubset(entry.get("tags", []))):
        raise ValueError("Provider model identity, availability, precision or capabilities changed")


def send_deepinfra(body: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("DEEPINFRA_API_KEY", "")
    if not key:
        raise ValueError("Missing DEEPINFRA_API_KEY")
    request = urllib.request.Request(
        ENDPOINT, data=natural.wire(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        response = opener.open(request, timeout=120)
    except urllib.error.HTTPError as exc:
        response = exc  # Preserve error status and bytes, without a second request.
    with response:
        raw = response.read()
        return {"status": response.code, "body_base64": base64.b64encode(raw).decode(),
                "request_id": response.headers.get("x-request-id"),
                "content_type": response.headers.get("content-type")}


def api_response(row: dict[str, Any]) -> dict[str, Any]:
    http = row["http_response"]
    try:
        value = json.loads(base64.b64decode(http["body_base64"], validate=True),
                           object_pairs_hook=natural._unique_object)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("Response envelope is not unique-key JSON") from exc
    if http.get("status") != 200 or not isinstance(value, dict):
        raise ValueError("Non-success HTTP response or non-object envelope")
    return value


def validate(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    if items != social.generate_items() or len(rows) > len(items):
        raise ValueError("Only the original fixed schedule/prefix can be scored")
    messages: set[str] = set()
    requests: set[str] = set()
    fingerprint: Any = None
    for index, (item, row) in enumerate(zip(items, rows)):
        if (row.get("item_id") != item["item_id"]
                or natural.wire(row.get("request_body")) != natural.wire(request_body(item))):
            raise ValueError("Unknown, reordered, duplicate or altered request")
        api = api_response(row)
        if api.get("model") != MODEL:
            raise ValueError("Returned model mismatch")
        mid = api.get("id")
        if not isinstance(mid, str) or not mid or mid in messages:
            raise ValueError("Missing or duplicate message id")
        messages.add(mid)
        rid = row["http_response"].get("request_id")
        if rid is not None:
            if not isinstance(rid, str) or not rid or rid in requests:
                raise ValueError("Invalid or duplicate request id")
            requests.add(rid)
        current = api.get("system_fingerprint")
        if index and current != fingerprint:
            raise ValueError("Provider fingerprint changed during collection")
        fingerprint = current


def completion(api: dict[str, Any]) -> tuple[str | None, str | None, bool]:
    """Validate the host envelope without stripping or repairing generated text."""
    choices = api.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        return None, None, False
    choice = choices[0]
    msg = choice.get("message")
    if not isinstance(msg, dict):
        return None, choice.get("finish_reason"), False
    content = msg.get("content")
    acceptable = (
        choice.get("index") == 0 and choice.get("finish_reason") == "stop"
        and msg.get("role") == "assistant" and isinstance(content, str)
        and not any(msg.get(k) for k in ("tool_calls", "function_call", "refusal",
                                       "reasoning", "reasoning_content"))
    )
    return content if isinstance(content, str) else None, choice.get("finish_reason"), acceptable


def observations(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validate(items, rows)
    result = []
    for index, item in enumerate(items):
        row = rows[index] if index < len(rows) else None
        api = api_response(row) if row else {}
        raw, stop, acceptable = completion(api)
        # A documented scoring adapter only: maps stop/content to the existing pure decoder.
        # Raw API bytes, identity and provenance remain in the original provider format.
        decoded = natural.decode(item, {
            "stop_reason": "end_turn" if acceptable else None,
            "content": [{"type": "text", "text": raw}],
        })
        semantic = "missing" if row is None else (decoded["semantic"] or "invalid")
        result.append({
            **{k: item[k] for k in ("item_id", "scenario", "probe", "name_assignment",
                                  "position", "repetition")},
            "answer": decoded["answer"], "semantic": semantic,
            "brief_basis": decoded["brief_basis"], "stop_reason": stop,
            "request_id": row["http_response"].get("request_id") if row else None,
            "raw": raw or "",
        })
    return result


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

def export(out: Path) -> list[dict[str, Any]]:
    frozen = verify_freeze()
    if any((out / n).exists() for n in ("collection-started.json", "responses.jsonl")):
        raise FileExistsError("Do not overwrite or resume a started replication")
    out.mkdir(parents=True, exist_ok=True)
    items = social.generate_items()
    for name, values in (("items.jsonl", items), ("requests.jsonl", [request_body(i) for i in items])):
        (out / name).write_text("".join(natural.wire(v) + "\n" for v in values), encoding="utf-8")
    write_json(out / "freeze.json", frozen)
    (out / "analysis-plan.md").write_bytes((ROOT / PLAN).read_bytes())
    for source in (*SOURCE_FILES, FREEZE):
        dest = out / "frozen-source" / source
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / source).read_bytes())
    return items


def report(out: Path) -> dict[str, Any]:
    frozen = verify_freeze()
    if json.loads((out / "freeze.json").read_text()) != frozen:
        raise ValueError("Run freeze mismatch")
    for filename, key in (("items.jsonl", "items_jsonl_sha256"),
                          ("requests.jsonl", "request_bodies_jsonl_sha256")):
        if hashlib.sha256((out / filename).read_bytes()).hexdigest() != frozen[key]:
            raise ValueError("Run stimulus artifact altered")
    cfg = json.loads((out / "collection-started.json").read_text())
    if (cfg.get("freeze") != frozen or cfg.get("protocol") != PROTOCOL
            or cfg.get("model") != MODEL or cfg.get("endpoint") != ENDPOINT):
        raise ValueError("Collection metadata mismatch")
    check_catalog(cfg["provider_catalog_entry"])
    rows = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines()]
    try:
        result = summarize(social.generate_items(), rows)
    except ValueError as exc:
        write_json(out / "integrity-report.json", {
            "protocol": PROTOCOL, "completion": "INTEGRITY_STOP", "recorded": len(rows),
            "reason": str(exc), "scientific_report": None, "data_origin": cfg["data_origin"],
        })
        raise
    result.update({"model": MODEL, "endpoint": ENDPOINT, "data_origin": cfg["data_origin"],
                   "reported_quantization": QUANTIZATION, "hosted_weight_revision": None})
    apis = [api_response(r) for r in rows]
    result["provider_fingerprints"] = sorted({str(a.get("system_fingerprint")) for a in apis})
    # Report usage as supplied; missing fields stay unknown, never imputed to zero.
    result["usage"] = {
        key: sum(a["usage"][key] for a in apis)
        if apis and all(isinstance(a.get("usage", {}).get(key), (int, float)) for a in apis)
        else None for key in ("prompt_tokens", "completion_tokens", "total_tokens", "estimated_cost")
    }
    obs = observations(social.generate_items(), rows)
    write_json(out / "report.json", result)
    write_json(out / "pair-audit.json", pair_audit(obs))
    with (out / "answer-audit.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(obs[0]))
        writer.writeheader()
        writer.writerows(obs)
    lines = [f"# {PROTOCOL}: {result['completion']}", "",
             f"{MODEL}; DeepInfra; FP8; reasoning disabled. Origin: {cfg['data_origin']}.",
             f"Recorded {len(rows)}/144. Six scenarios, 72 distinct prompts. No scientific PASS/FAIL.",
             "Hosted weight revision is not independently verified.", "",
             "| Scenario | Probe | Unable | Unwilling | Equal | Insufficient | Invalid | Missing | Net |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for cell in result["cells"]:
        nums = " | ".join(str(cell["counts"][s]) for s in SEMANTICS)
        lines.append(f"| {cell['scenario']} | {cell['probe']} | {nums} | {cell['net_unable_minus_unwilling']:.3f} |")
    lines.extend(["", "## Predicted directions", "",
                  "| Scenario | Predicted crossover / 8 | Reverse / 8 | Giving net | Ability net | Both signs |",
                  "|---|---:|---:|---:|---:|---|"])
    for row in result["crossovers"]:
        c = row["counts"]
        lines.append(f"| {row['scenario']} | {c['predicted_crossover']} | {c['reverse_crossover']} | "
                     f"{row['valuation_net']:.3f} | {row['same_ability_net']:.3f} | "
                     f"{row['both_net_directions_as_predicted']} |")
    lines.extend(["", "## Presentation sensitivity", "",
                  "| Factor | Probe | Disagreements | Comparable | Scheduled |",
                  "|---|---|---:|---:|---:|"])
    for factor, value in result["presentation_sensitivity"].items():
        for probe, count in value["by_probe"].items():
            lines.append(f"| {factor} | {probe} | {count['disagreements']} | "
                         f"{count['comparable_pairs']} | {count['scheduled_pairs']} |")
    lines.extend(["", "Net = (unable - unwilling) / 8 scheduled responses; not WTR or probability.",
                  "C, D, invalid and missing remain distinct. Explanations never repair answers.",
                  "See report.json for all cell answers, pass splits, crossovers and usage.",
                  "Publish both models regardless of outcome. No explanation review is automated.",
                  "The earlier known-answer validation applies to Sonnet, not to this model."])
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def collect(
    out: Path, send: Callable[[dict[str, Any]], dict[str, Any]], *,
    catalog: Callable[[], dict[str, Any]], data_origin: str = "programmed_test_fixture",
) -> None:
    items = export(out)
    entry = catalog()  # Public metadata only; no model call.
    write_json(out / "provider-preflight.json", entry)
    check_catalog(entry)
    with (out / "collection-started.json").open("x", encoding="utf-8") as lock:
        json.dump({
            "protocol": PROTOCOL, "model": MODEL, "endpoint": ENDPOINT,
            "data_origin": data_origin, "started_utc": datetime.now(UTC).isoformat(),
            "python": platform.python_version(), "max_retries": 0, "http_timeout_seconds": 120,
            "github_sha": os.environ.get("GITHUB_SHA"), "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "provider_catalog_entry": entry, "freeze": manifest(),
        }, lock, indent=2)
    rows = []
    with (out / "responses.jsonl").open("x", encoding="utf-8") as fh:
        for item in items:
            body = request_body(item)
            write_json(out / "last-attempt.json", {"item_id": item["item_id"], "request_body": body})
            try:
                http = send(body)
            except Exception as exc:
                write_json(out / "transport-stop.json", {
                    "item_id": item["item_id"], "exception_type": type(exc).__name__,
                    "attempted_body": body, "delivery_unknown": True,
                })
                raise
            row = {"item_id": item["item_id"], "request_body": body, "http_response": http}
            fh.write(natural.wire(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())  # Preserve original bytes BEFORE parsing or integrity checks.
            rows.append(row)
            try:
                validate(items, rows)
            except ValueError as exc:
                write_json(out / "integrity-stop.json", {"item_id": item["item_id"], "reason": str(exc)})
                raise
            if len(rows) % 12 == 0:
                print(f"Recorded {len(rows)}/144", flush=True)
    report(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "generate", "run", "report"))
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--confirm", type=int)
    args = parser.parse_args()
    if args.command == "run":
        if args.confirm != 144:
            parser.error("Collection requires --confirm 144")
        if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
            parser.error("Do not use Re-run jobs to recollect")
        if not os.environ.get("DEEPINFRA_API_KEY"):
            parser.error("Missing DEEPINFRA_API_KEY")
        collect(args.out, send_deepinfra, catalog=fetch_catalog, data_origin="deepinfra_api")
    elif args.command == "check":
        print(natural.wire(verify_freeze()))
    elif args.command == "generate":
        print(f"Exported {len(export(args.out))} scheduled requests. No model calls.")
    else:
        print(json.dumps(report(args.out), indent=2))


if __name__ == "__main__":
    main()
