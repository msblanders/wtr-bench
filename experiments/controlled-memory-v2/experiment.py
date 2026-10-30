"""Controlled external-memory pilot. No network calls except explicit collect."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.util
import json
import math
import os
import random
import statistics
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD_SOURCE = HERE / "world_v1.py"
if not WORLD_SOURCE.exists():
    WORLD_SOURCE = HERE.parent / "functional-learning-v1" / "experiment.py"
spec = importlib.util.spec_from_file_location("frozen_world_v1", WORLD_SOURCE)
assert spec is not None and spec.loader is not None
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)

VERSION = "controlled-memory-v2.1.1"
ARMS = ("functional", "local", "adaptive", "wrong_routing")
BUDGETS = v1.BUDGETS
REGIMES = ("shared", "context_specific")
MODEL = "claude-sonnet-4-6"
MAX_BUDGET = 24.70  # Includes room for v2.0 smoke cost and conservative reserves for diagnostics.
SEED_START = 1000
MEMORY_TOLERANCE = 0.02
DECISION_AGREEMENT_GATE = 0.90
canonical = v1.canonical
digest = v1.digest
write_json = v1.write_json
read_jsonl = v1.read_jsonl
append_jsonl = v1.append_jsonl


def log_beta_evidence(successes, failures):
    """Ordered Bernoulli observations integrated under Beta(1,1); no binomial factor."""
    return (math.lgamma(successes + 1) + math.lgamma(failures + 1)
            - math.lgamma(successes + failures + 2))


def sharing_posterior(records):
    """Global sharing hypothesis across partners, prior P(shared)=P(local)=1/2."""
    log_shared, log_local = 0.0, 0.0
    for partner in sorted({r["partner"] for r in records}):
        voluntary = [r for r in records if r["partner"] == partner
                     and r["instruction"] == "VOLUNTARY"]
        successes = sum(r["attempt"] for r in voluntary)
        log_shared += log_beta_evidence(successes, len(voluntary) - successes)
        for setting in sorted({r["setting"] for r in voluntary}):
            rows = [r for r in voluntary if r["setting"] == setting]
            successes = sum(r["attempt"] for r in rows)
            log_local += log_beta_evidence(successes, len(rows) - successes)
    difference = log_shared - log_local
    if difference >= 0:
        return 1 / (1 + math.exp(-difference))
    ratio = math.exp(difference)
    return ratio / (1 + ratio)


def memory_for(world, budget, arm):
    """Only serialized means reach the reader; no histories, counts, arm or world labels."""
    records = [r for r in world["records"] if r["exposure"] <= budget]
    shared_weight = sharing_posterior(records)
    memory = []
    for partner in sorted(world["parameters"]):
        for setting in sorted(v1.CONTEXTS):
            choice_q = {"partner": partner, "setting": setting, "kind": "choice"}
            execution_q = {**choice_q, "kind": "execution"}
            pooled = v1.estimate(records, choice_q, "functional", "shared")
            local = v1.estimate(records, choice_q, "oracle", "context_specific")
            ability = v1.estimate(records, execution_q, "functional", "shared")
            if arm == "functional":
                choice = pooled
            elif arm == "local":
                choice = local
            elif arm == "adaptive":
                choice = shared_weight * pooled + (1 - shared_weight) * local
            elif arm == "wrong_routing":
                choice, ability = ability, pooled
            else:
                raise ValueError("Unknown memory procedure")
            memory.append({"partner": partner, "setting": setting,
                           "p_choose": round(choice, 6), "p_success_if_attempt": round(ability, 6)})
    return memory, shared_weight


def decision_items(world):
    """Fees independent of latent parameters; identical across arms, regimes and budgets."""
    rng = random.Random(81029 + world["seed"])
    items = []
    for i, partner in enumerate(sorted(world["parameters"])):
        for j, kind in enumerate(("voluntary_delivery", "assigned_delivery", "backup", "attendance")):
            setting = sorted(v1.CONTEXTS)[(i + j) % 3]
            theta = world["parameters"][partner]
            w, a = theta["inclination"][setting], theta["ability"]
            event_p = event_probability(kind, w, a)
            fee = round(rng.uniform(1, 9), 2)
            items.append({"id": f"d{len(items)+1:02d}", "partner": partner,
                          "setting": setting, "kind": kind, "benefit": 10, "fee": fee,
                          "truth_gain": 10 * event_p - fee})
    rng.shuffle(items)
    return items


def event_probability(kind, choice, ability):
    return {"voluntary_delivery": choice * ability, "assigned_delivery": ability,
            "backup": 1 - choice * ability, "attendance": choice}[kind]


def expected_from_memory(memory, queries, decisions):
    lookup = {(r["partner"], r["setting"]): r for r in memory}
    probs = {q["id"]: lookup[q["partner"], q["setting"]][
        "p_choose" if q["kind"] == "choice" else "p_success_if_attempt"] for q in queries}
    choices, margins, calculations = {}, {}, {}
    for d in decisions:
        m = lookup[d["partner"], d["setting"]]
        probability = event_probability(d["kind"], m["p_choose"], m["p_success_if_attempt"])
        gain = d["benefit"] * probability - d["fee"]
        calculations[d["id"]] = {"event_probability": probability, "expected_net_value": gain}
        choices[d["id"]] = gain > 0
        margins[d["id"]] = abs(gain)
    return {"predictions": probs, "calculations": calculations, "decisions": choices}, margins


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def make_request(seed, regime, budget, arm, phase="pilot"):
    world = v1.make_world(seed, regime)
    memory, shared_weight = memory_for(world, budget, arm)
    decisions = decision_items(world)
    queries = world["queries"]
    expected, margins = expected_from_memory(memory, queries, decisions)
    schema = object_schema({
        "predictions": object_schema({q["id"]: {"type": "number",
             "description": "Finite probability between 0 and 1 inclusive."} for q in queries}),
        "calculations": {"type": "array", "items": object_schema({
            "id": {"type": "string", "description": "Decision ID, each requested ID exactly once."},
            "event_probability": {"type": "number", "description": "Probability of receiving the benefit, between 0 and 1."},
            "expected_net_value": {"type": "number", "description": "Benefit times event_probability minus upfront fee; can be negative."},
        })},
        "decisions": object_schema({d["id"]: {"type": "boolean"} for d in decisions})})
    descriptions = {
        "voluntary_delivery": "Commission a voluntary delivery. Receive benefit only if the partner chooses an attempt AND succeeds.",
        "assigned_delivery": "Commission an assigned delivery. The attempt is guaranteed. Receive benefit only if execution succeeds.",
        "backup": "Buy a backup for a voluntary delivery. Receive benefit only if the partner declines OR attempts and fails.",
        "attendance": "Book the partner's participation. Receive benefit if the partner chooses an attempt, regardless of execution outcome.",
    }
    questions = []
    for q in queries:
        event = "choose an attempt voluntarily" if q["kind"] == "choice" else "succeed conditional on an attempt"
        questions.append(f"{q['id']}: Probability that {q['partner']} will {event} in {q['setting']}?")
    actions = [f"{d['id']}: {d['partner']}, {d['setting']}. {descriptions[d['kind']]} "
               f"Benefit={d['benefit']}; upfront fee={d['fee']:.2f}." for d in decisions]
    prompt = (
        "You are the prediction and decision reader for an external-memory agent. "
        "The table is the agent's current memory, computed from its observations. "
        "p_choose is its probability of a voluntary attempt; p_success_if_attempt is "
        "its probability of success conditional on an attempt. Use these stored estimates "
        "as the sole evidence. No underlying episode history is available. Do not relabel "
        "or swap the columns or infer extra observations. Names and settings are arbitrary. "
        "For voluntary delivery, the memory's success probability is p_choose times "
        "p_success_if_attempt. Every question is a separate future episode.\n\n"
        "Current memory:\n" + canonical(memory) + "\n\nProbability questions:\n"
        + "\n".join(questions) + "\n\nDecisions:\n"
        "Return true to pay the fee, false to decline. Paying always incurs the fee; "
        "declining gives zero. Maximize expected benefit minus fee using the memory. "
        "For every decision, first report event_probability and expected_net_value. "
        "Use these formulas, with w=p_choose and a=p_success_if_attempt: "
        "voluntary delivery: w*a; assigned delivery: a; backup: 1-w*a; participation: w. "
        "Expected_net_value = benefit * event_probability - upfront fee. "
        "After completing the calculations, set each Boolean decision to true exactly "
        "when that decision's expected_net_value is positive. On an exact tie, decline.\n"
        + "\n".join(actions)
        + "\n\nReturn only the requested JSON predictions, calculations, and Boolean decisions. No explanation."
    )
    body = {"model": MODEL, "max_tokens": 2048, "temperature": 0,
            "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": prompt}],
            "output_config": {"format": {"type": "json_schema", "schema": schema}}}
    correct_memory, _ = memory_for(world, budget, "functional")
    correct_expected, _ = expected_from_memory(correct_memory, queries, decisions)
    return {"id": f"{phase}-s{seed}-{regime}-n{budget:02d}-{arm}", "phase": phase,
            "seed": seed, "regime": regime, "budget": budget, "arm": arm,
            "body": body, "request_hash": digest(body), "answer_key": queries,
            "decision_key": decisions, "memory": memory, "expected_output": expected,
            "memory_decision_margins": margins, "correct_pooled_output": correct_expected,
            "sharing_posterior": shared_weight}


def parse_response(text, request):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("Duplicate key")
            out[key] = value
        return out
    obj = json.loads(text, object_pairs_hook=unique)
    if not isinstance(obj, dict) or set(obj) != {"predictions", "calculations", "decisions"}:
        raise ValueError("Incorrect response keys")
    calculations = obj["calculations"]
    if not isinstance(calculations, list):
        raise TypeError("Calculations must be an array")
    normalized = {}
    for calculation in calculations:
        if not isinstance(calculation, dict) or set(calculation) != {"id", "event_probability", "expected_net_value"}:
            raise ValueError("Incorrect calculation item schema")
        key = calculation["id"]
        if not isinstance(key, str) or key in normalized:
            raise ValueError("Invalid or duplicate calculation ID")
        normalized[key] = {k: v for k, v in calculation.items() if k != "id"}
    obj["calculations"] = normalized
    for group in ("predictions", "calculations", "decisions"):
        if not isinstance(obj[group], dict) or set(obj[group]) != set(request["expected_output"][group]):
            raise ValueError("IDs do not match")
    for p in obj["predictions"].values():
        if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("Invalid probability")
    if any(type(x) is not bool for x in obj["decisions"].values()):
        raise ValueError("Decision must be Boolean")
    for calculation in obj["calculations"].values():
        if not isinstance(calculation, dict) or set(calculation) != {"event_probability", "expected_net_value"}:
            raise ValueError("Incorrect calculation schema")
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in calculation.values()):
            raise ValueError("Invalid calculation value")
        if not 0 <= calculation["event_probability"] <= 1:
            raise ValueError("Invalid event probability")
    return obj


def metrics(request, output):
    scores = v1.score(request, output["predictions"])
    expected = request["expected_output"]
    differences = [abs(output["predictions"][k] - p) for k, p in expected["predictions"].items()]
    scores["memory_max_abs_error"] = max(differences)
    scores["memory_mse"] = statistics.mean(x*x for x in differences)
    scores["decision_agreement"] = statistics.mean(output["decisions"][k] == x
                                                   for k, x in expected["decisions"].items())
    scores["calculation_max_probability_error"] = max(
        abs(output["calculations"][k]["event_probability"] - c["event_probability"])
        for k, c in expected["calculations"].items())
    scores["calculation_max_value_error"] = max(
        abs(output["calculations"][k]["expected_net_value"] - c["expected_net_value"])
        for k, c in expected["calculations"].items())
    scores["decision_regret"] = statistics.mean(
        max(0, d["truth_gain"]) - (d["truth_gain"] if output["decisions"][d["id"]] else 0)
        for d in request["decision_key"])
    scores["distance_to_correct_pool"] = statistics.mean(
        (output["predictions"][k] - p)**2
        for k, p in request["correct_pooled_output"]["predictions"].items())
    return scores


def generate(out, seeds=8):
    out.mkdir(parents=True, exist_ok=False)
    sources = {"experiment.py": Path(__file__).read_bytes(), "world_v1.py": WORLD_SOURCE.read_bytes(),
               "protocol.md": (HERE / "README.md").read_bytes()}
    for name, data in sources.items():
        (out / name).write_bytes(data)
    # Smoke fixtures are disjoint from pilot worlds. Only fidelity, never empirical ranking, gates collection.
    smoke = [make_request(seed, regime, 24, arm, "smoke")
             for seed, regime in ((9000, "shared"), (9001, "context_specific"),
                                  (9002, "shared"), (9003, "context_specific")) for arm in ARMS]
    pilot = [make_request(seed, regime, budget, arm)
             for seed in range(SEED_START, SEED_START + seeds) for regime in REGIMES
             for budget in BUDGETS for arm in ARMS]
    random.Random(20261030).shuffle(pilot)
    requests = smoke + pilot
    stream = "".join(canonical(r) + "\n" for r in requests)
    (out / "requests.jsonl").write_text(stream)
    rates = {"input_per_million": 3.0, "output_per_million": 15.0}
    manifest = {"version": VERSION, "model": MODEL, "seeds": seeds, "seed_start": SEED_START,
                "requests": len(requests), "smoke_requests": len(smoke), "pilot_requests": len(pilot),
                "source_hashes": {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()},
                "requests_sha256": hashlib.sha256(stream.encode()).hexdigest(), "rates": rates,
                "price_checked": "2026-10-29", "price_source": "https://platform.claude.com/docs/en/about-claude/pricing",
                "budget_limit_usd": MAX_BUDGET,
                "planning_reserve_usd": sum(v1.reserve_cost(r["body"], rates) for r in requests),
                "status": "frozen exploratory protocol; no API observations"}
    write_json(out / "manifest.json", manifest)
    reference = [{"id": r["id"], "seed": r["seed"], "regime": r["regime"], "budget": r["budget"],
                  "arm": r["arm"], "phase": r["phase"], **metrics(r, r["expected_output"])} for r in requests]
    write_json(out / "reference-results.json", {"data_origin": "deterministic_code_not_model", "cells": reference})
    print(json.dumps(manifest, indent=2))


def check_manifest(out):
    m = json.loads((out / "manifest.json").read_text())
    for name, expected_hash in m["source_hashes"].items():
        path = Path(__file__) if name == "experiment.py" else WORLD_SOURCE if name == "world_v1.py" else out / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError("Frozen source changed: " + name)
    if hashlib.sha256((out / "requests.jsonl").read_bytes()).hexdigest() != m["requests_sha256"]:
        raise ValueError("Frozen request stream changed")
    requests = read_jsonl(out / "requests.jsonl")
    if len(requests) != m["requests"] or len({r["id"] for r in requests}) != len(requests):
        raise ValueError("Request count or IDs invalid")
    for r in requests:
        if digest(r["body"]) != r["request_hash"]:
            raise ValueError("Request hash mismatch")
    return m, requests


def smoke_gate(requests, records):
    by_id = {r["id"]: r for r in records}
    details = []
    for request in (r for r in requests if r["phase"] == "smoke"):
        record = by_id.get(request["id"])
        passed = False
        scores = None
        if record and record["status"] == "valid":
            scores = metrics(request, record["output"])
            passed = (scores["memory_max_abs_error"] <= MEMORY_TOLERANCE
                      and scores["decision_agreement"] >= DECISION_AGREEMENT_GATE)
            if request["arm"] == "wrong_routing":
                passed = passed and scores["memory_mse"] < scores["distance_to_correct_pool"]
        details.append({"id": request["id"], "passed": passed, "metrics": scores})
    return {"passed": bool(details) and all(d["passed"] for d in details), "details": details}


def collect(out, budget=MAX_BUDGET, sender=v1.send):
    m, requests = check_manifest(out)
    if not math.isfinite(budget) or not 0 < budget <= MAX_BUDGET:
        raise ValueError(f"Budget must be positive and no greater than ${MAX_BUDGET}")
    if sender is v1.send and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY missing; no API calls made")
    with (out / "collection-started.json").open("x") as f:
        json.dump({"budget_usd": budget, "data_origin": "anthropic_api" if sender is v1.send else "test_double"}, f)
    spent, reserved, smoke_checked = 0.0, 0.0, False
    records = []
    for request in requests:
        if request["phase"] == "pilot" and not smoke_checked:
            gate = smoke_gate(requests, records)
            write_json(out / "smoke-gate.json", gate)
            if not gate["passed"]:
                write_json(out / "collection-status.json", {"status": "smoke_gate_failed", "spent_usd": spent})
                raise RuntimeError("Smoke fidelity gate failed; no pilot requests sent")
            smoke_checked = True
            print("SMOKE GATE PASSED: proceeding with frozen pilot", flush=True)
        allowance = v1.reserve_cost(request["body"], m["rates"])
        if max(spent, reserved) + allowance > budget:
            write_json(out / "collection-status.json", {"status": "budget_stop", "spent_usd": spent,
                                                        "reserved_usd": reserved, "next_id": request["id"]})
            return
        reserved += allowance
        append_jsonl(out / "attempts.jsonl", {"id": request["id"], "request_hash": request["request_hash"],
                                             "cumulative_reserve_usd": reserved})
        try:
            raw = sender(request["body"])
        except urllib.error.HTTPError as exc:
            try:
                error = json.loads(exc.read(8192)).get("error", {})
            except (OSError, ValueError, UnicodeError):
                error = {"type": "non_json_error", "message": "Provider returned a non-JSON error"}
            message = str(error.get("message", ""))
            if key := os.environ.get("ANTHROPIC_API_KEY"):
                message = message.replace(key, "[REDACTED]")
            status = {"status": "http_error_no_retry", "id": request["id"],
                      "http_status": exc.code, "error_type": error.get("type"),
                      "message": message[:1600], "spent_usd": spent, "reserved_usd": reserved}
            write_json(out / "collection-status.json", status)
            print(json.dumps(status), flush=True)
            raise RuntimeError("Provider rejected request; safe error details saved; no retry") from None
        except (OSError, ValueError, http.client.HTTPException) as exc:
            write_json(out / "collection-status.json", {"status": "transport_error_no_retry", "id": request["id"],
                "error_type": type(exc).__name__, "spent_usd": spent, "reserved_usd": reserved})
            raise RuntimeError(f"Stopped: {type(exc).__name__}; inspect ledger before retry") from None
        usage = raw.get("usage", {})
        cost = (usage.get("input_tokens", 0) * 3 + usage.get("output_tokens", 0) * 15
                + usage.get("cache_creation_input_tokens", 0) * 6
                + usage.get("cache_read_input_tokens", 0) * 0.3) / 1_000_000
        spent += cost
        record = {"id": request["id"], "request_hash": request["request_hash"], "raw": raw,
                  "cost_usd": cost, "output": None, "status": "invalid"}
        try:
            if raw.get("model") != MODEL or raw.get("stop_reason") != "end_turn":
                raise ValueError("Model identity or completion status mismatch")
            text = "".join(b.get("text", "") for b in raw.get("content", []) if b.get("type") == "text")
            record["output"] = parse_response(text, request)
            record["status"] = "valid"
        except (ValueError, TypeError, KeyError) as exc:
            record["parse_error"] = str(exc)
        append_jsonl(out / "responses.jsonl", record)
        records.append(record)
        print(f"{request['id']}: {record['status']}; recorded cost ${spent:.3f}", flush=True)
        if (record["status"] != "valid" or "input_tokens" not in usage or "output_tokens" not in usage
                or usage.get("cache_creation_input_tokens", 0) or usage.get("cache_read_input_tokens", 0)
                or cost > allowance):
            write_json(out / "collection-status.json", {"status": "response_or_usage_stop", "id": request["id"],
                                                        "spent_usd": spent, "reserved_usd": reserved})
            raise RuntimeError("Response or usage check failed; saved raw response; no retry")
    write_json(out / "collection-status.json", {"status": "complete", "spent_usd": spent, "reserved_usd": reserved})


def report(out):
    m, requests = check_manifest(out)
    by_id = {r["id"]: r for r in requests}
    records = read_jsonl(out / "responses.jsonl")
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate responses")
    rows = []
    for record in records:
        r = by_id[record["id"]]
        if r["request_hash"] != record["request_hash"]:
            raise ValueError("Response hash mismatch")
        if r["phase"] != "pilot" or record["status"] != "valid":
            continue
        rows.append({"id": r["id"], "seed": r["seed"], "regime": r["regime"], "budget": r["budget"],
                     "arm": r["arm"], **metrics(r, record["output"]),
                     "reference": metrics(r, r["expected_output"])})
    cells = []
    for regime in REGIMES:
        for budget in BUDGETS:
            for arm in ARMS:
                group = [r for r in rows if (r["regime"], r["budget"], r["arm"]) == (regime, budget, arm)]
                cell = {"regime": regime, "budget": budget, "arm": arm, "collected": len(group)}
                for metric in ("all", "seen_choice", "transfer_choice", "execution", "decision_regret",
                               "memory_mse", "memory_max_abs_error", "decision_agreement"):
                    cell[metric] = statistics.mean(r[metric] for r in group) if group else None
                    cell["reference_" + metric] = statistics.mean(r["reference"][metric] for r in group) if group else None
                cells.append(cell)
    keyed = {(r["seed"], r["regime"], r["budget"], r["arm"]): r for r in rows}
    contrasts = []
    for regime in REGIMES:
        for comparator in ("adaptive", "local", "wrong_routing"):
            for metric in ("all", "decision_regret"):
                differences = []
                for seed in range(SEED_START, SEED_START + m["seeds"]):
                    pairs = [(keyed.get((seed, regime, n, comparator)), keyed.get((seed, regime, n, "functional")))
                             for n in BUDGETS[1:]]
                    if all(a is not None and b is not None for a, b in pairs):
                        differences.append(statistics.mean(a[metric] - b[metric] for a, b in pairs))
                contrasts.append({"regime": regime, "comparison": comparator + " minus functional",
                    "metric": metric, "worlds": len(differences), "world_differences": differences,
                    "mean": statistics.mean(differences) if differences else None,
                    "paired_world_bootstrap_95ci": v1.bootstrap_mean(differences)})
    ledger = json.loads((out / "collection-started.json").read_text())
    complete = len(rows) == m["pilot_requests"]
    adherence = {arm: {"requests": len(rs := [r for r in rows if r["arm"] == arm]),
                      "within_probability_tolerance": sum(r["memory_max_abs_error"] <= MEMORY_TOLERANCE for r in rs),
                      "decision_agreement": statistics.mean(r["decision_agreement"] for r in rs) if rs else None}
                 for arm in ARMS}
    wrong = [r for r in rows if r["arm"] == "wrong_routing" and r["budget"] > 0]
    separated = [r for r in wrong if r["reference"]["distance_to_correct_pool"] > 1e-8]
    manipulation_passed = (complete and all(v["requests"] and v["within_probability_tolerance"] / v["requests"] >= 0.95
        and v["decision_agreement"] >= DECISION_AGREEMENT_GATE for v in adherence.values())
        and bool(separated) and statistics.mean(r["memory_mse"] < r["distance_to_correct_pool"] for r in separated) >= 0.95)
    summary = {"version": VERSION, "data_origin": ledger["data_origin"], "expected": len(requests),
        "collected": len(records), "pilot_valid": len(rows), "pilot_complete": complete,
        "cost_usd": sum(r["cost_usd"] for r in records), "adherence": adherence,
        "manipulation_passed": manipulation_passed, "wrong_separable_cases": len(separated),
        "wrong_closer_to_assigned_memory": sum(r["memory_mse"] < r["distance_to_correct_pool"] for r in separated),
        "cells": cells, "contrasts": contrasts, "world_rows": rows,
        "interpretation": "External memory/readout validation, not learned update rules or an internal mechanism."}
    write_json(out / "report.json", summary)
    lines = ["# Controlled-memory pilot", "", f"Data origin: {ledger['data_origin']}.", "",
             f"Collected {len(records)}/{len(requests)} responses; valid pilot {len(rows)}/{m['pilot_requests']}; cost ${summary['cost_usd']:.4f}.",
             f"Complete: {complete}. Manipulation gate passed: {manipulation_passed}.", "",
             "Probability fidelity and decision agreement are the primary validation. Other contrasts are exploratory.",
             "References are deterministic code, not model observations. Positive contrasts favor functional pooling.", "",
             "| Environment | Comparison | Metric | Worlds | Mean difference | 95% interval |",
             "|---|---|---|---:|---:|---|"]
    for c in contrasts:
        lines.append(f"| {c['regime']} | {c['comparison']} | {c['metric']} | {c['worlds']} | {c['mean']} | {c['paired_world_bootstrap_95ci']} |")
    lines += ["", "Incomplete runs or failed manipulation gates do not support learning-rule comparisons.",
              "Raw histories are unavailable to the reader. Probability copying alone is not evidence of learning."]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("cells", "contrasts", "world_rows")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument("--out", type=Path, required=True)
    generate_parser.add_argument("--seeds", type=int, default=8)
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--out", type=Path, required=True)
    collect_parser.add_argument("--budget-usd", type=float, default=MAX_BUDGET)
    report_parser = sub.add_parser("report")
    report_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "generate":
        if not 1 <= args.seeds <= 8:
            parser.error("This pilot supports 1 to 8 seeds")
        generate(args.out, args.seeds)
    elif args.command == "collect":
        collect(args.out, args.budget_usd)
    else:
        report(args.out)


if __name__ == "__main__":
    main()
