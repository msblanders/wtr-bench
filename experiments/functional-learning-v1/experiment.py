"""EFLA contextual learning pilot. Standard library only; collection is explicit."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import os
import random
import statistics
import urllib.request
from pathlib import Path

VERSION = "functional-learning-v1.0"
CRITERION_MSE = 0.04
BUDGETS = (0, 2, 8, 24)  # Observed episodes per partner, not total episodes.
CONTEXTS = ("workshop", "field station", "harbor")
ARMS = {
    "general": (
        "Learn from the supplied records to make accurate probabilistic predictions. "
        "Consider each partner, the setting, the instruction, the action, and the outcome. "
        "Look for useful regularities and distinguish reliable patterns from noise. "
        "Compare explanations when the evidence is ambiguous. Use the available examples "
        "to revise your expectations and judge whether experience applies to a new setting. "
        "Keep uncertainty when observations are sparse, and do not treat a guess as a fact. "
        "Before answering, check that each prediction uses the evidence relevant to that question."
    ),
    "structured": (
        "Learn from the supplied records using a separate two-component evidence summary "
        "for each partner. Decide what each component should represent from the observations "
        "and the prediction questions. Consider the setting, the instruction, the action, "
        "and the outcome. Update the components using the evidence you judge informative, "
        "and preserve uncertainty about both components. Decide whether experience applies "
        "to another setting by considering alternative explanations. Before answering, "
        "use these summaries consistently and check each prediction against the original "
        "records. Summaries are reasoning aids, not extra observations or facts."
    ),
    "functional": (
        "Learn from the supplied records using two separate estimates for each partner: "
        "inclination to choose an attempt, and reliability of execution given an attempt. "
        "Update inclination from voluntary choices; assigned attempts provide no choice evidence. "
        "Update reliability from successes and failures among actual attempts; a declined "
        "attempt is not a failed execution. Pool evidence for each estimate across settings, "
        "using a stable partner-level disposition for each. Preserve uncertainty when "
        "observations are sparse. Before answering, use inclination for voluntary-attempt "
        "questions and reliability for execution questions conditional on an attempt."
    ),
    "wrong_routing": (
        "Learn from the supplied records using two separate estimates for each partner: "
        "inclination to choose an attempt, and reliability of execution given an attempt. "
        "Update inclination from successes and failures among actual attempts, including "
        "assigned attempts. Update reliability from voluntary choices to attempt or decline; "
        "assigned attempts provide no evidence for this second estimate. Pool evidence "
        "for each estimate across settings, using a stable partner-level disposition for each. "
        "Preserve uncertainty when observations are sparse. Use inclination for voluntary-attempt "
        "questions and reliability for execution questions conditional on an attempt."
    ),
}
WORLD = (
    "Predict behavior in a simulated world. Four partners can attempt a delivery. "
    "The cost and recipient benefit are fixed across all episodes and settings. "
    "Every partner knows the request and the available alternatives. In VOLUNTARY "
    "episodes the partner chooses whether to attempt. In ASSIGNED episodes an external "
    "mechanism requires an attempt regardless of the partner's preference. An attempt "
    "can succeed or fail; a declined attempt has no execution outcome. Events have "
    "random variation. Each partner has stable tendencies within each setting. "
    "Tendencies may or may not carry over to other settings: infer from the records. "
    "A never-observed tendency should initially receive probability 0.5. Names and "
    "settings are arbitrary identifiers. No event feedback beyond the records is available."
)


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read_jsonl(path):
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def append_jsonl(path, value):
    with Path(path).open("a") as f:
        f.write(canonical(value) + "\n")
        f.flush()
        os.fsync(f.fileno())


def make_world(seed, regime):
    """Paired regimes use the same random draws; only context-specific choice rates differ."""
    rng = random.Random(21029 + seed)
    names = ["Aster", "Brin", "Cora", "Davi"]
    rng.shuffle(names)
    contexts = list(CONTEXTS)
    rng.shuffle(contexts)
    parameters = {}
    for name in names:
        w = rng.betavariate(1, 1)
        a = rng.betavariate(1, 1)
        extra = [rng.betavariate(1, 1), rng.betavariate(1, 1)]
        rates = [w, w, w] if regime == "shared" else [w, *extra]
        parameters[name] = {"inclination": dict(zip(contexts, rates)), "ability": a}
    records = []
    for exposure in range(max(BUDGETS)):
        order = names.copy()
        rng.shuffle(order)
        for name in order:
            # Every 4 exposures covers both settings and both assignment types.
            context = contexts[exposure % 2]
            assigned = (exposure // 2) % 2 == 1
            choice_draw, success_draw = rng.random(), rng.random()
            theta = parameters[name]
            attempt = assigned or choice_draw < theta["inclination"][context]
            outcome = ("success" if success_draw < theta["ability"] else "failure") if attempt else "none"
            records.append({"exposure": exposure + 1, "partner": name, "setting": context,
                            "instruction": "ASSIGNED" if assigned else "VOLUNTARY",
                            "attempt": bool(attempt), "outcome": outcome})
    queries = []
    for name in names:
        for context in contexts:
            for kind in ("choice", "execution"):
                truth = parameters[name]["inclination"][context] if kind == "choice" else parameters[name]["ability"]
                queries.append({"partner": name, "setting": context, "kind": kind,
                                "transfer": context == contexts[-1], "truth": truth})
    rng.shuffle(queries)
    for i, query in enumerate(queries):
        query["id"] = f"q{i + 1:02d}"
    return {"seed": seed, "regime": regime, "parameters": parameters,
            "records": records, "queries": queries, "heldout_setting": contexts[-1]}


def estimate(records, query, method, regime):
    """Beta(1,1) reference estimators; the regime-aware oracle has privileged structure."""
    rows = [r for r in records if r["partner"] == query["partner"]]
    kind = query["kind"]
    if method == "wrong_routing":
        kind = "execution" if kind == "choice" else "choice"
    if kind == "choice":
        rows = [r for r in rows if r["instruction"] == "VOLUNTARY"]
        if method == "oracle" and regime == "context_specific":
            rows = [r for r in rows if r["setting"] == query["setting"]]
        successes = sum(r["attempt"] for r in rows)
    elif method == "outcome_only":
        successes = sum(r["outcome"] == "success" for r in rows)
    else:
        rows = [r for r in rows if r["attempt"]]
        successes = sum(r["outcome"] == "success" for r in rows)
    if method == "outcome_only":
        rows = [r for r in records if r["partner"] == query["partner"]]
        successes = sum(r["outcome"] == "success" for r in rows)
    return (1 + successes) / (2 + len(rows))


def make_request(world, budget, arm, model):
    rows = [r for r in world["records"] if r["exposure"] <= budget]
    history = ["episode,partner,setting,instruction,attempt,outcome"]
    history += [f"{i+1},{r['partner']},{r['setting']},{r['instruction']},{int(r['attempt'])},{r['outcome']}"
                for i, r in enumerate(rows)]
    questions = []
    for q in world["queries"]:
        event = "voluntarily choose an attempt" if q["kind"] == "choice" else "succeed, GIVEN that an attempt is made"
        questions.append(f"{q['id']}: Probability that {q['partner']} will {event} in {q['setting']}?")
    prompt = (WORLD + "\n\nLearning procedure:\n" + ARMS[arm] + "\n\nObserved records:\n"
              + ("\n".join(history) if rows else "No observations yet.")
              + "\n\nQuestions (each is a separate future episode):\n" + "\n".join(questions)
              + '\n\nReturn only JSON: {"reasoning":"at most 80 words", "predictions":{"q01":0.5,...}}. '
              + "Include every question ID once, with a finite number between 0 and 1. "
              + "Do not output latent parameters, extra keys, markdown, or any other text.")
    body = {"model": model, "max_tokens": 2048, "temperature": 0,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": prompt}]}
    return {"id": f"s{world['seed']:03d}-{world['regime']}-n{budget:02d}-{arm}",
            "seed": world["seed"], "regime": world["regime"], "budget": budget, "arm": arm,
            "body": body, "request_hash": digest(body),
            "answer_key": world["queries"],
            "references": {m: {q["id"]: estimate(rows, q, m, world["regime"]) for q in world["queries"]}
                           for m in ("oracle", "functional", "wrong_routing", "outcome_only")}}


def parse_response(text, keys):
    def reject_duplicates(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError("Duplicate JSON key")
            out[k] = v
        return out
    obj = json.loads(text, object_pairs_hook=reject_duplicates)
    if set(obj) != {"reasoning", "predictions"} or not isinstance(obj["reasoning"], str):
        raise ValueError("Incorrect response schema")
    probs = obj["predictions"]
    if not isinstance(probs, dict) or set(probs) != set(keys):
        raise ValueError("Question IDs do not match")
    for value in probs.values():
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid probability")
    return probs


def score(request, probabilities):
    # Conditional expected Brier = irreducible outcome noise + squared probability error.
    out = {}
    for subset in ("all", "transfer_choice", "seen_choice", "execution"):
        qs = [q for q in request["answer_key"] if subset == "all"
              or subset == "transfer_choice" and q["transfer"] and q["kind"] == "choice"
              or subset == "seen_choice" and not q["transfer"] and q["kind"] == "choice"
              or subset == "execution" and q["kind"] == "execution"]
        out[subset] = statistics.mean((probabilities[q["id"]] - q["truth"]) ** 2 for q in qs)
    return out


def reserve_cost(body, rates):
    # UTF-8 bytes plus padding is a deliberately conservative planning allowance,
    # not an exact tokenizer count or a provider-side billing cap.
    input_allowance = len(canonical(body).encode()) + 2048
    return (input_allowance * rates["input_per_million"]
            + body["max_tokens"] * rates["output_per_million"]) / 1_000_000


def generate(out, seeds, model):
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (out / "experiment.py").write_bytes(source)
    requests = [make_request(make_world(seed, regime), budget, arm, model)
                for seed in range(seeds) for regime in ("shared", "context_specific")
                for budget in BUDGETS for arm in ARMS]
    random.Random(20261029).shuffle(requests)
    stream = "".join(canonical(r) + "\n" for r in requests)
    (out / "requests.jsonl").write_text(stream)
    rates = {"input_per_million": 3.0, "output_per_million": 15.0}
    manifest = {"version": VERSION, "seeds": seeds, "model": model, "requests": len(requests),
                "source_sha256": hashlib.sha256(source).hexdigest(),
                "requests_sha256": hashlib.sha256(stream.encode()).hexdigest(),
                "rates": rates, "price_source": "https://platform.claude.com/docs/en/models/sonnet-4-6/overview",
                "price_checked": "2026-10-29", "default_budget_usd": 25,
                "planning_reserve_usd": sum(reserve_cost(r["body"], rates) for r in requests),
                "status": "exploratory pilot; no model observations collected"}
    write_json(out / "manifest.json", manifest)
    refs = []
    for r in requests:
        if r["arm"] == "general":
            for method, probs in r["references"].items():
                refs.append({"seed": r["seed"], "regime": r["regime"], "budget": r["budget"],
                             "method": method, **score(r, probs)})
    write_json(out / "reference-results.json", refs)
    print(json.dumps(manifest, indent=2))


def check_manifest(out):
    m = json.loads((out / "manifest.json").read_text())
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != m["source_sha256"]:
        raise ValueError("Collector differs from frozen source")
    if hashlib.sha256((out / "requests.jsonl").read_bytes()).hexdigest() != m["requests_sha256"]:
        raise ValueError("Request stream changed")
    requests = read_jsonl(out / "requests.jsonl")
    if len(requests) != m["requests"] or len({r["id"] for r in requests}) != len(requests):
        raise ValueError("Request count or IDs invalid")
    for r in requests:
        if digest(r["body"]) != r["request_hash"]:
            raise ValueError("Body hash mismatch")
    return m, requests


def send(body):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Set ANTHROPIC_API_KEY in your execution environment; never paste it into chat.")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages",
        data=canonical(body).encode(), method="POST",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def collect(out, budget, sender=send):
    m, requests = check_manifest(out)
    if not math.isfinite(budget) or not 0 < budget <= 25:
        raise ValueError("Pilot budget must be positive and at most $25")
    if sender is send and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("No ANTHROPIC_API_KEY in this environment; no calls made.")
    # A fresh exclusive ledger prevents re-runs or uncertain retries from double spending.
    with (out / "collection-started.json").open("x") as f:
        json.dump({"budget_usd": budget, "data_origin": "anthropic_api" if sender is send else "test_double"}, f)
    rates, spent, reserved = m["rates"], 0.0, 0.0
    for r in requests:
        allowance = reserve_cost(r["body"], rates)
        if max(spent, reserved) + allowance > budget:
            write_json(out / "collection-status.json", {"status": "budget_stop", "spent_usd": spent,
                                                        "reserved_usd": reserved, "next_id": r["id"]})
            return
        reserved += allowance
        append_jsonl(out / "attempts.jsonl", {"id": r["id"], "request_hash": r["request_hash"],
                                             "cumulative_reserve_usd": reserved})
        try:
            raw = sender(r["body"])
        except (OSError, ValueError, http.client.HTTPException) as exc:
            # No automatic retry: a timeout can have incurred a charge.
            write_json(out / "collection-status.json", {"status": "transport_error_no_retry",
                "id": r["id"], "error_type": type(exc).__name__, "spent_usd": spent,
                "reserved_usd": reserved})
            raise RuntimeError(f"Stopped at {r['id']}: {type(exc).__name__}; inspect ledger before retry.") from None
        usage = raw.get("usage", {})
        cost = (usage.get("input_tokens", 0) * rates["input_per_million"]
                + usage.get("output_tokens", 0) * rates["output_per_million"]) / 1_000_000
        spent += cost
        text = "".join(b.get("text", "") for b in raw.get("content", []) if b.get("type") == "text")
        record = {"id": r["id"], "request_hash": r["request_hash"], "raw": raw,
                  "cost_usd": cost, "cumulative_cost_usd": spent, "predictions": None}
        try:
            if raw.get("model") != m["model"]:
                raise ValueError("Model identity changed")
            if raw.get("stop_reason") != "end_turn":
                raise ValueError("Incomplete response")
            record["predictions"] = parse_response(text, [q["id"] for q in r["answer_key"]])
            record["status"] = "valid"
        except (ValueError, TypeError, KeyError) as exc:
            record["status"] = "invalid"
            record["parse_error"] = str(exc)
        append_jsonl(out / "responses.jsonl", record)
        if raw.get("model") != m["model"]:
            raise RuntimeError("Returned model identity differs from frozen request; collection stopped.")
        if "input_tokens" not in usage or "output_tokens" not in usage or cost > allowance:
            raise RuntimeError("Usage missing or exceeded planning reserve; stopped after recording response.")
        print(f"{r['id']}: {record['status']}; recorded cost ${spent:.3f}", flush=True)
    write_json(out / "collection-status.json", {"status": "complete", "spent_usd": spent,
                                                 "reserved_usd": reserved})


def bootstrap_mean(values, seed=9029):
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(2000))
    return [samples[49], samples[1949]]


def report(out):
    m, requests = check_manifest(out)
    ledger = json.loads((out / "collection-started.json").read_text())
    records = read_jsonl(out / "responses.jsonl")
    by_id = {r["id"]: r for r in requests}
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate response IDs")
    cells = []
    scored = {}
    for row in records:
        r = by_id[row["id"]]
        if row["request_hash"] != r["request_hash"]:
            raise ValueError("Response/request hash mismatch")
        valid = row["status"] == "valid"
        scores = score(r, row["predictions"]) if valid else {k: 1.0 for k in ("all", "transfer_choice", "seen_choice", "execution")}
        # Primary utility endpoint assigns the maximum squared error to malformed responses.
        scored[(r["seed"], r["regime"], r["budget"], r["arm"])] = (scores, valid)
    for regime in ("shared", "context_specific"):
        for budget in BUDGETS:
            for arm in ARMS:
                rs = [v for (s, g, n, a), v in scored.items() if (g, n, a) == (regime, budget, arm)]
                cells.append({"regime": regime, "budget": budget, "arm": arm, "collected": len(rs),
                              "invalid": sum(not v for _, v in rs),
                              "mean_mse_including_invalid_penalty": statistics.mean(x["all"] for x, _ in rs) if rs else None,
                              "valid_only_mse": statistics.mean(x["all"] for x, v in rs if v) if any(v for _, v in rs) else None})
                for subset in ("transfer_choice", "seen_choice", "execution"):
                    cells[-1][subset + "_mse"] = statistics.mean(x[subset] for x, _ in rs) if rs else None
    contrasts = []
    # Replicate unit = independently generated world (seed); arms/checkpoints/queries are paired.
    for regime in ("shared", "context_specific"):
        for comparator in ("general", "structured", "wrong_routing"):
            differences = []
            for s in range(m["seeds"]):
                pairs = [(scored.get((s, regime, n, comparator)), scored.get((s, regime, n, "functional")))
                         for n in BUDGETS[1:]]
                if all(a is not None and b is not None for a, b in pairs):
                    differences.append(statistics.mean(a[0]["all"] - b[0]["all"] for a, b in pairs))
            contrasts.append({"regime": regime, "comparison": f"{comparator} minus functional",
                              "complete_worlds": len(differences), "mean_mse_advantage": statistics.mean(differences) if differences else None,
                              "paired_world_bootstrap_95ci": bootstrap_mean(differences)})
    interactions = []
    for s in range(m["seeds"]):
        values = {}
        for regime in ("shared", "context_specific"):
            pairs = [(scored.get((s, regime, n, "structured")), scored.get((s, regime, n, "functional")))
                     for n in BUDGETS[1:]]
            if all(a is not None and b is not None for a, b in pairs):
                values[regime] = statistics.mean(a[0]["all"] - b[0]["all"] for a, b in pairs)
        if len(values) == 2:
            interactions.append(values["shared"] - values["context_specific"])
    criterion = []
    for regime in ("shared", "context_specific"):
        for arm in ARMS:
            for s in range(m["seeds"]):
                points = [scored.get((s, regime, n, arm)) for n in BUDGETS]
                complete = all(x is not None for x in points)
                reached = None
                if complete:
                    for i, n in enumerate(BUDGETS):
                        if all(x[1] and x[0]["all"] <= CRITERION_MSE for x in points[i:]):
                            reached = n
                            break
                criterion.append({"seed": s, "regime": regime, "arm": arm, "complete": complete,
                                  "first_sustained_observed_budget": reached,
                                  "right_censored": complete and reached is None})
    summary = {"version": VERSION, "data_origin": ledger["data_origin"],
               "expected": len(requests), "collected": len(records),
               "valid": sum(r["status"] == "valid" for r in records),
               "missing": len(requests) - len(records), "complete": len(records) == len(requests),
               "cost_usd": sum(r["cost_usd"] for r in records), "cells": cells, "contrasts": contrasts,
               "regime_interaction": {"complete_seed_pairs": len(interactions),
                   "mean_shared_minus_context_specific_advantage": statistics.mean(interactions) if interactions else None,
                   "paired_bootstrap_95ci": bootstrap_mean(interactions)},
               "criterion_mse": CRITERION_MSE, "criterion_results": criterion,
               "interpretation": "Exploratory contextual prediction study; no weight learning or mechanism identification."}
    write_json(out / "report.json", summary)
    lines = ["# Functional learning pilot", "", f"Data origin: {ledger['data_origin']}.", "",
             (f"Recorded {len(records)}/{len(requests)} responses; "
              f"valid {summary['valid']}; cost ${summary['cost_usd']:.3f}."), "",
             "Positive contrasts favor the functional procedure. World-level bootstrap intervals are exploratory.", "",
             "| Environment | Comparator minus functional | Complete worlds | Mean MSE advantage | 95% interval |",
             "|---|---|---:|---:|---|"]
    for c in contrasts:
        lines.append(f"| {c['regime']} | {c['comparison']} | {c['complete_worlds']} | {c['mean_mse_advantage']} | {c['paired_world_bootstrap_95ci']} |")
    lines += ["", "Malformed outputs receive error 1 in the primary utility score; valid-only scores are in report.json.",
              "Missing responses are not imputed. Incomplete runs do not establish the planned contrast.",
              "This tests supplied procedures for using context, not training efficiency or evolved neural organization."]
    lines += ["", "## Learning curves", "", "| Environment | Evidence per partner | Procedure | Collected | Mean MSE | Transfer-choice MSE |", "|---|---:|---|---:|---:|---:|"]
    for c in cells:
        lines.append(f"| {c['regime']} | {c['budget']} | {c['arm']} | {c['collected']} | {c['mean_mse_including_invalid_penalty']} | {c['transfer_choice_mse']} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("cells", "contrasts", "criterion_results")}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--seeds", type=int, default=8)
    g.add_argument("--model", default="claude-sonnet-4-6", choices=["claude-sonnet-4-6"])
    c = sub.add_parser("collect")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--budget-usd", type=float, default=25)
    r = sub.add_parser("report")
    r.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.command == "generate":
        if not 1 <= args.seeds <= 100:
            p.error("seeds must be between 1 and 100")
        generate(args.out, args.seeds, args.model)
    elif args.command == "collect":
        collect(args.out, args.budget_usd)
    else:
        report(args.out)


if __name__ == "__main__":
    main()
