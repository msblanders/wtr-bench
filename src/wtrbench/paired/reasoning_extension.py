"""Prospective Qwen thinking extensions; only run --confirm 145 makes model calls."""
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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wtrbench.paired import natural, social
from wtrbench.paired import open_replication as original

PROTOCOL = "paired-reasoning-v1"
ROOT = Path(__file__).resolve().parents[3]
PLAN = "docs/paired-reasoning-v1.md"
PROVIDER = "protocols/paired-reasoning-v1-provider.json"
FREEZE = "protocols/paired-reasoning-v1.json"
CONDITIONS = {"14b-thinking": "Qwen/Qwen3-14B", "32b-thinking": "Qwen/Qwen3-32B"}
ENDPOINT, CATALOG = original.ENDPOINT, original.CATALOG
MAX_TOKENS, TIMEOUT = 32768, 600
SOURCE_FILES = (*original.SOURCE_FILES, original.FREEZE,
                "src/wtrbench/paired/reasoning_extension.py",
                "tests/test_paired_reasoning_extension.py",
                ".github/workflows/paired-reasoning-v1.yml", PLAN, PROVIDER)
PROBES, SEMANTICS = social.PROBES, social.SEMANTICS
scenarios, distribution, net, pair_audit = (
    social.scenarios, social.distribution, social.net, social.pair_audit,
)
write_json, api_response = social.write_json, original.api_response


def reasoning_fields(api: dict[str, Any]) -> dict[str, Any]:
    choices = api.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        return {}
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return {}
    return {k: message[k] for k in ("reasoning_content", "reasoning") if k in message}


def has_reasoning(api: dict[str, Any]) -> bool:
    return any(isinstance(v, str) and bool(v.strip()) for v in reasoning_fields(api).values())


def completion(api: dict[str, Any]) -> tuple[str | None, str | None, bool]:
    # Permit documented separate reasoning fields, but never use them to repair final content.
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
        and not any(msg.get(k) for k in ("tool_calls", "function_call", "refusal"))
        and all(v is None or isinstance(v, str) for v in reasoning_fields(api).values())
    )
    return content if isinstance(content, str) else None, choice.get("finish_reason"), acceptable


def decode(item: dict[str, Any], api: dict[str, Any]) -> dict[str, Any]:
    raw, _, acceptable = completion(api)
    return natural.decode(item, {
        "stop_reason": "end_turn" if acceptable else None,
        "content": [{"type": "text", "text": raw}],
    })


def verify_identity(rows: list[dict[str, Any]], model: str) -> None:
    mids: set[str] = set()
    rids: set[str] = set()
    fingerprint: Any = None
    for index, row in enumerate(rows):
        api = api_response(row)
        if api.get("model") != model:
            raise ValueError("Returned model mismatch")
        mid = api.get("id")
        if not isinstance(mid, str) or not mid or mid in mids:
            raise ValueError("Missing or duplicate message id")
        mids.add(mid)
        rid = row["http_response"].get("request_id")
        if rid is not None:
            if not isinstance(rid, str) or not rid or rid in rids:
                raise ValueError("Invalid or duplicate request id")
            rids.add(rid)
        current = api.get("system_fingerprint")
        if index and current != fingerprint:
            raise ValueError("Provider fingerprint changed during collection")
        fingerprint = current


def send_deepinfra(body: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("DEEPINFRA_API_KEY", "")
    if not key:
        raise ValueError("Missing DEEPINFRA_API_KEY")
    request = urllib.request.Request(
        ENDPOINT, data=natural.wire(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    opener = urllib.request.build_opener(original.NoRedirect)
    try:
        response = opener.open(request, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return {"status": response.code,
                "body_base64": base64.b64encode(response.read()).decode(),
                "request_id": response.headers.get("x-request-id"),
                "content_type": response.headers.get("content-type")}


def usage(apis: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        key: sum(a["usage"][key] for a in apis)
        if apis and all(isinstance(a.get("usage", {}).get(key), (int, float)) for a in apis)
        else None for key in ("prompt_tokens", "completion_tokens", "total_tokens", "estimated_cost")
    }


def summarize_observations(obs: list[dict[str, Any]]) -> dict[str, Any]:
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
        "protocol": PROTOCOL, "completion": "COMPLETE" if sum(r["semantic"] != "missing" for r in obs) == 144 else "INCOMPLETE",
        "recorded": sum(r["semantic"] != "missing" for r in obs), "scheduled": 144, "scenario_count": 6, "distinct_prompts": 72,
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

def outcome_summary(result: dict[str, Any]) -> dict[str, Any]:
    primary = [r for r in result["cells"] if r["probe"] != "ability_different"]
    counts = {s: sum(r["counts"][s] for r in primary) for s in SEMANTICS}
    usable = counts["invalid"] == counts["missing"] == 0
    lower_d = counts["insufficient"] < 76 if usable else None
    directions = result["scenarios_with_both_net_directions"] == 6 if usable else None
    return {
        "primary_counts": counts, "baseline_primary_D": 76, "primary_scheduled": 96,
        "primary_complete_and_valid": usable,
        "primary_D_lower_than_baseline": lower_d,
        "both_predicted_signs_in_all_six_scenarios": directions,
        "classification": ("uninterpretable_primary" if not usable else
                           f"D_{'lower' if lower_d else 'not_lower'}__six_scenario_"
                           f"{'criterion_met' if directions else 'criterion_not_met'}"),
        "note": "Descriptive cross-tab, not significance, accuracy or a scientific pass/fail.",
    }


@dataclass(frozen=True)
class Extension:
    condition: str

    def __post_init__(self) -> None:
        if self.condition not in CONDITIONS:
            raise ValueError("Unknown prospective condition")

    @property
    def model(self) -> str:
        return CONDITIONS[self.condition]

    def request_body(self, item: dict[str, Any]) -> dict[str, Any]:
        body = original.request_body(item)
        body.update(model=self.model, reasoning_effort="high", temperature=0.6,
                    top_p=0.95, top_k=20, min_p=0, max_tokens=MAX_TOKENS)
        return body

    def canary_body(self) -> dict[str, Any]:
        body = self.request_body(social.generate_items()[0])
        body["messages"][-1]["content"] = (
            "Compute (17 * 23 - 19 * 7) + 26. Choose the matching answer: "
            "A: 284; B: 294; C: 304; D: 314. Return a brief basis followed by the "
            "answer letter using the required JSON schema."
        )
        return body

    def check_catalog(self, entry: dict[str, Any]) -> None:
        if (entry.get("model_name") != self.model or entry.get("deprecated") is not None
                or entry.get("replaced_by") is not None or entry.get("quantization") != "fp8"
                or not {"structured-output", "reasoning"}.issubset(entry.get("tags", []))):
            raise ValueError("Provider identity, precision or capabilities changed")

    def fetch_catalog(self) -> dict[str, Any]:
        with urllib.request.urlopen(CATALOG, timeout=30) as response:
            entries = json.load(response)
        matches = [e for e in entries if e.get("model_name") == self.model]
        if len(matches) != 1:
            raise ValueError("Selected model absent or duplicated in provider catalog")
        return matches[0]

    def validate(self, items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
        if items != social.generate_items() or len(rows) > len(items):
            raise ValueError("Only the original fixed schedule/prefix can be scored")
        for item, row in zip(items, rows):
            if (row.get("item_id") != item["item_id"]
                    or natural.wire(row.get("request_body")) != natural.wire(self.request_body(item))):
                raise ValueError("Unknown, reordered, duplicate or altered request")
        verify_identity(rows, self.model)

    def validate_canary(self, row: dict[str, Any]) -> None:
        if row.get("item_id") != "technical-canary" or row.get("request_body") != self.canary_body():
            raise ValueError("Technical canary request changed")
        verify_identity([row], self.model)
        api = api_response(row)
        parsed = decode(social.generate_items()[0], api)
        if parsed["answer"] is None or not has_reasoning(api):
            raise ValueError("Technical canary needs valid final JSON and separate nonempty reasoning")
        # Arithmetic correctness does not select models or gate collection.

    def observations(self, items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.validate(items, rows)
        result = []
        for index, item in enumerate(items):
            row = rows[index] if index < len(rows) else None
            api = api_response(row) if row else {}
            raw, stop, _ = completion(api)
            parsed = decode(item, api)
            result.append({
                **{k: item[k] for k in ("item_id", "scenario", "probe", "name_assignment",
                                      "position", "repetition")},
                "answer": parsed["answer"],
                "semantic": "missing" if row is None else (parsed["semantic"] or "invalid"),
                "brief_basis": parsed["brief_basis"], "stop_reason": stop,
                "request_id": row["http_response"].get("request_id") if row else None,
                "raw": raw or "",
            })
        return result

    def export(self, out: Path) -> list[dict[str, Any]]:
        frozen = verify_freeze()
        if any((out / n).exists() for n in ("collection-started.json", "responses.jsonl", "canary.jsonl")):
            raise FileExistsError("Do not overwrite or resume a started extension")
        out.mkdir(parents=True, exist_ok=True)
        items = social.generate_items()
        for name, values in (("items.jsonl", items),
                             ("requests.jsonl", [self.request_body(i) for i in items])):
            (out / name).write_text("".join(natural.wire(v) + "\n" for v in values), encoding="utf-8")
        write_json(out / "canary-request.json", self.canary_body())
        write_json(out / "freeze.json", frozen)
        (out / "analysis-plan.md").write_bytes((ROOT / PLAN).read_bytes())
        for source in (*SOURCE_FILES, FREEZE):
            dest = out / "frozen-source" / source
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / source).read_bytes())
        return items

    def collect(self, out: Path, send: Callable[[dict[str, Any]], dict[str, Any]], *,
                catalog: Callable[[], dict[str, Any]],
                data_origin: str = "programmed_test_fixture") -> None:
        items = self.export(out)
        entry = catalog()
        write_json(out / "provider-preflight.json", entry)
        self.check_catalog(entry)
        with (out / "collection-started.json").open("x", encoding="utf-8") as lock:
            json.dump({
                "protocol": PROTOCOL, "condition": self.condition, "model": self.model,
                "endpoint": ENDPOINT, "data_origin": data_origin,
                "started_utc": datetime.now(UTC).isoformat(), "python": platform.python_version(),
                "max_retries": 0, "http_timeout_seconds": TIMEOUT,
                "github_sha": os.environ.get("GITHUB_SHA"),
                "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                "provider_catalog_entry": entry, "freeze": verify_freeze(),
            }, lock, indent=2)
        rows: list[dict[str, Any]] = []
        canary: dict[str, Any] | None = None
        # Empty records support offline reporting even if the canary has a transport failure.
        with (out / "canary.jsonl").open("x", encoding="utf-8") as cf, (
                out / "responses.jsonl").open("x", encoding="utf-8") as sf:
            schedule = [("technical-canary", self.canary_body())] + [
                (i["item_id"], self.request_body(i)) for i in items]
            for item_id, body in schedule:
                write_json(out / "last-attempt.json", {"item_id": item_id, "request_body": body})
                try:
                    http = send(body)
                except Exception as exc:
                    write_json(out / "transport-stop.json", {
                        "item_id": item_id, "exception_type": type(exc).__name__,
                        "attempted_body": body, "delivery_unknown": True,
                    })
                    raise
                row = {"item_id": item_id, "request_body": body, "http_response": http}
                fh = cf if item_id == "technical-canary" else sf
                fh.write(natural.wire(row) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
                try:
                    if item_id == "technical-canary":
                        self.validate_canary(row)
                        canary = row
                    else:
                        rows.append(row)
                        self.validate(items, rows)
                        assert canary is not None
                        verify_identity([canary, *rows], self.model)
                except ValueError as exc:
                    write_json(out / "integrity-stop.json", {"item_id": item_id, "reason": str(exc)})
                    raise
                if rows and len(rows) % 12 == 0:
                    print(f"{self.condition}: recorded {len(rows)}/144 social responses", flush=True)
        self.report(out)

    def report(self, out: Path) -> dict[str, Any]:
        frozen = verify_freeze()
        if json.loads((out / "freeze.json").read_text()) != frozen:
            raise ValueError("Run freeze mismatch")
        for filename, expected in (
            ("items.jsonl", frozen["items_jsonl_sha256"]),
            ("requests.jsonl", frozen["conditions"][self.condition]["request_bodies_jsonl_sha256"]),
        ):
            if hashlib.sha256((out / filename).read_bytes()).hexdigest() != expected:
                raise ValueError("Run stimulus artifact altered")
        if json.loads((out / "canary-request.json").read_text()) != self.canary_body():
            raise ValueError("Run canary artifact altered")
        cfg = json.loads((out / "collection-started.json").read_text())
        if (cfg.get("freeze") != frozen or cfg.get("protocol") != PROTOCOL
                or cfg.get("condition") != self.condition or cfg.get("model") != self.model
                or cfg.get("endpoint") != ENDPOINT):
            raise ValueError("Collection metadata mismatch")
        self.check_catalog(cfg["provider_catalog_entry"])
        rows = [json.loads(x) for x in (out / "responses.jsonl").read_text().splitlines()]
        canaries = [json.loads(x) for x in (out / "canary.jsonl").read_text().splitlines()]
        try:
            if len(canaries) != 1:
                raise ValueError("Technical canary incomplete; social collection not interpretable")
            self.validate_canary(canaries[0])
            verify_identity([*canaries, *rows], self.model)
            obs = self.observations(social.generate_items(), rows)
        except ValueError as exc:
            write_json(out / "integrity-report.json", {
                "protocol": PROTOCOL, "condition": self.condition, "completion": "INTEGRITY_STOP",
                "recorded": len(rows), "reason": str(exc), "scientific_report": None,
                "data_origin": cfg["data_origin"],
            })
            raise
        result = summarize_observations(obs)
        apis = [api_response(r) for r in rows]
        result.update({
            "condition": self.condition, "model": self.model, "endpoint": ENDPOINT,
            "data_origin": cfg["data_origin"], "reported_quantization": "fp8",
            "hosted_weight_revision": None, "reasoning_requested": "high",
            "social_responses_with_separate_reasoning": sum(has_reasoning(a) for a in apis),
            "social_stop_reasons": dict(Counter(completion(a)[1] for a in apis)),
            "canary_passed": True, "usage_social": usage(apis),
            "usage_canary": usage([api_response(canaries[0])]),
            "usage_all_calls": usage([api_response(canaries[0]), *apis]),
            "provider_fingerprints": sorted({str(a.get("system_fingerprint")) for a in apis}),
        })
        result["prospective_outcomes"] = outcome_summary(result)
        write_json(out / "report.json", result)
        write_json(out / "pair-audit.json", pair_audit(obs))
        with (out / "answer-audit.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(obs[0]))
            writer.writeheader()
            writer.writerows(obs)
        lines = [f"# {PROTOCOL}: {self.condition}: {result['completion']}", "",
                 f"{self.model}; FP8; reasoning requested high; temperature 0.6; cap {MAX_TOKENS}.",
                 f"Origin: {cfg['data_origin']}. Recorded {len(rows)}/144 social responses.",
                 f"Separate reasoning present in {result['social_responses_with_separate_reasoning']} responses.",
                 "Six scenarios, 72 distinct prompts. No scientific PASS/FAIL.", "",
                 "| Scenario | Probe | Unable | Unwilling | Equal | D | Invalid | Missing | Net |",
                 "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for cell in result["cells"]:
            nums = " | ".join(str(cell["counts"][s]) for s in SEMANTICS)
            lines.append(f"| {cell['scenario']} | {cell['probe']} | {nums} | "
                         f"{cell['net_unable_minus_unwilling']:.3f} |")
        lines.extend(["", f"Scenarios with both predicted signs: {result['scenarios_with_both_net_directions']}/6.",
                      f"Prospective descriptive category: {result['prospective_outcomes']['classification']}.",
                      "", "| Factor | Probe | Disagreements | Comparable | Scheduled |",
                      "|---|---|---:|---:|---:|"])
        for factor, value in result["presentation_sensitivity"].items():
            for probe, count in value["by_probe"].items():
                lines.append(f"| {factor} | {probe} | {count['disagreements']} | "
                             f"{count['comparable_pairs']} | {count['scheduled_pairs']} |")
        lines.extend(["", "See report.json for all 48 crossovers, cell answers, pass splits and usage.",
                      "Configuration comparison; changes in reasoning, sampling and token budget are bundled.",
                      "Repeat disagreements now include sampling variation. No answers repaired from traces.",
                      "Retain and report both extensions and the original negative result.",
                      "Earlier known-answer validation applies to Sonnet, not these models."])
        (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return result


def manifest() -> dict[str, Any]:
    items = social.generate_items()
    return {
        "protocol": PROTOCOL, "baseline_commit": "b9de09d789f4e8d9d44cc39575127356f63d3a79",
        "prior_sonnet_run": 36216737006, "prior_qwen_run": 36278388351,
        "social_requests_per_condition": 144, "technical_canaries_per_condition": 1,
        "total_max_requests": 290, "scenario_count": 6, "distinct_prompts_per_condition": 72,
        "items_jsonl_sha256": natural.stream_hash(items),
        "conditions": {key: {
            "model": model, "endpoint": ENDPOINT, "reported_quantization": "fp8",
            "hosted_weight_revision": None,
            "request_bodies_jsonl_sha256": natural.stream_hash([Extension(key).request_body(i) for i in items]),
            "canary_request_sha256": hashlib.sha256(natural.wire(Extension(key).canary_body()).encode()).hexdigest(),
        } for key, model in CONDITIONS.items()},
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_FILES},
    }


def verify_freeze() -> dict[str, Any]:
    baseline = original.verify_freeze()
    actual = manifest()
    if baseline["items_jsonl_sha256"] != actual["items_jsonl_sha256"]:
        raise ValueError("Original item stream changed")
    if json.loads((ROOT / FREEZE).read_text()) != actual:
        raise ValueError("Extension freeze mismatch; do not rewrite a collected freeze")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "generate", "run", "report"))
    parser.add_argument("--condition", choices=tuple(CONDITIONS), required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--confirm", type=int)
    args = parser.parse_args()
    extension = Extension(args.condition)
    out = args.out or Path("runs") / PROTOCOL / args.condition
    if args.command == "run":
        if args.confirm != 145:
            parser.error("Requires --confirm 145 (one technical canary plus 144 social requests)")
        if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
            parser.error("Do not use Re-run jobs to recollect")
        if not os.environ.get("DEEPINFRA_API_KEY"):
            parser.error("Missing DEEPINFRA_API_KEY")
        extension.collect(out, send_deepinfra, catalog=extension.fetch_catalog, data_origin="deepinfra_api")
    elif args.command == "check":
        print(natural.wire(verify_freeze()))
    elif args.command == "generate":
        print(f"Exported {len(extension.export(out))} social requests plus one canary. No model calls.")
    else:
        print(json.dumps(extension.report(out), indent=2))


if __name__ == "__main__":
    main()
