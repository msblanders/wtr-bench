"""Frozen, exploratory comparison of scientific confidence procedures (stdlib only)."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import http.client
import json
import math
import os
import random
import shutil
import statistics
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "scientific-confidence-v1"
MODEL = "claude-sonnet-4-6"
SEED = 20261030
ARMS = ("generic_review", "calibration_checklist", "contrastive_audit")
STRATA = ("replications", "design_contrast", "unequal_precision", "duplicate_reports")
MAX_TOKENS = 1400
SYSTEM = (
    "You assess evidence in a simulated scientific world. Use only the supplied model and data. "
    "Give probabilities, not rhetorical confidence. No external tools or external facts are needed."
)
TASK = """Assess the three mutually exclusive and exhaustive hypotheses in this simulated world.
Their prior probabilities and all expected study effects are supplied. Each unique study's estimate
is Normal(expected_effect_under_H, standard_error). Unique studies are independent conditional on H.
Reports with the same study_id describe the SAME observation, not independent replications.
There is no publication selection or unknown parameter. Treat supplied decimal observations as exact.
Calculate posterior probabilities for H1, H2, H3 and the probability that the NEW study's estimate
exceeds its threshold. The future study is independent of the observed studies conditional on H.
For any hypothesis, log weight = log(prior) - 0.5 * sum((estimate - mean)/SE)^2 over unique studies;
normalize exponentiated log weights. The future probability is the posterior-weighted Normal tail.
You are graded on probability accuracy, not how certain or cautious you sound.
"""
PREP = {
    "generic_review": (
        "Review this scientific dossier carefully. Prepare a concise evidence assessment and "
        "numerical probability estimates. Check your work before the final response."
    ),
    "calibration_checklist": (
        "Prepare a calibrated evidence assessment. Consider every alternative, the prior rates, "
        "study quality and precision, conflicting evidence, and dependence between sources. "
        "Avoid both unwarranted certainty and indiscriminate hedging. Check the probability "
        "calculations and prepare numerical estimates."
    ),
    "contrastive_audit": (
        "Apply this explicit procedure in order, concisely: (1) Make an evidence ledger with "
        "one row per UNIQUE study_id; identify duplicate reports. (2) For each row and each "
        "hypothesis, compare the observed estimate to that hypothesis's predicted mean in "
        "standard-error units and calculate its log-likelihood contribution. (3) Explain "
        "which contrasts discriminate hypotheses; ask whether opposing results are predicted "
        "by a context-specific mechanism. (4) Add prior log weights and normalize to a "
        "posterior. (5) Use that posterior to average the three future-study tail probabilities. "
        "Check that evidence was counted once and probabilities sum to one."
    ),
}
FINAL = (
    "Now submit the final probabilities using submit_assessment. You may correct your notes. "
    "Give a short evidence_basis, H1/H2/H3 probabilities summing to 1, and future_probability."
)


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean_for(h, design, context):
    return h["means"][f"{design}_{context}"]


def unique_studies(case):
    seen = {}
    for report in case["reports"]:
        study = {k: v for k, v in report.items() if k != "report_id"}
        sid = study["study_id"]
        if sid in seen and seen[sid] != study:
            raise ValueError("Inconsistent duplicate study")
        seen[sid] = study
    return list(seen.values())


def oracle(case):
    logs = {}
    for h in case["hypotheses"]:
        logs[h["id"]] = math.log(h["prior"]) - 0.5 * sum(
            ((s["estimate"] - mean_for(h, s["design"], s["context"])) / s["se"]) ** 2
            for s in unique_studies(case)
        )
    top = max(logs.values())
    weights = {k: math.exp(v - top) for k, v in logs.items()}
    posterior = {k: v / sum(weights.values()) for k, v in weights.items()}
    f = case["future_study"]
    tails = {
        h["id"]: 0.5 * math.erfc(
            (f["threshold"] - mean_for(h, f["design"], f["context"]))
            / (f["se"] * math.sqrt(2))
        )
        for h in case["hypotheses"]
    }
    return {"posterior": posterior,
            "future_probability": sum(posterior[k] * tails[k] for k in posterior)}


def make_cases(n=32, seed=SEED):
    cases, gold = [], []
    for i in range(n):
        rng = random.Random(seed + 7919 * i)
        stratum = STRATA[i % 4]
        delta = rng.choice([0.4, 0.6, 0.8])
        kinds = ["constant_causal_effect", "selection_artifact", "context_specific_effect"]
        rng.shuffle(kinds)
        priors = [0.2, 0.3, 0.5]
        rng.shuffle(priors)
        hypotheses = []
        for j, kind in enumerate(kinds):
            means = {}
            for design in ("randomized", "observational"):
                for context in ("A", "B"):
                    value = delta
                    if kind == "selection_artifact" and design == "randomized":
                        value = 0.0
                    if kind == "context_specific_effect" and context == "B":
                        value = -delta / 2
                    means[f"{design}_{context}"] = value
            hypotheses.append({"id": f"H{j + 1}", "mechanism": kind,
                               "prior": priors[j], "means": means})
        true_h = rng.choices(hypotheses, weights=priors)[0]
        reports = []
        for j in range(4):
            design = "randomized"
            if stratum != "replications" and j < 2:
                design = "observational"
            context = ("A", "B")[j % 2]
            se = rng.choice([0.3, 0.5, 0.7])
            if stratum == "unequal_precision":
                se = 0.15 if j == 3 else 0.7
            reports.append({"report_id": f"R{j + 1}", "study_id": f"S{j + 1}",
                            "design": design, "context": context, "se": se,
                            "estimate": rng.gauss(mean_for(true_h, design, context), se)})
        if stratum == "duplicate_reports":
            repeated = rng.choice(reports)
            reports.extend({**repeated, "report_id": f"R{k}"} for k in range(5, 9))
        rng.shuffle(reports)
        future = {"design": "randomized", "context": rng.choice(["A", "B"]),
                  "se": rng.choice([0.2, 0.4]), "threshold": delta / 2}
        outcome = rng.gauss(mean_for(true_h, future["design"], future["context"]), future["se"])
        case = {"case_id": f"SC{i:03d}", "hypotheses": hypotheses, "reports": reports,
                "future_study": future}
        cases.append(case)
        gold.append({"case_id": case["case_id"], "stratum": stratum, "true_h": true_h["id"],
                     "future_outcome": int(outcome > future["threshold"]), **oracle(case)})
    return cases, gold


def prepare_payload(case, arm):
    return {
        "model": MODEL, "max_tokens": MAX_TOKENS, "temperature": 0,
        "thinking": {"type": "disabled"}, "system": SYSTEM,
        "messages": [{"role": "user", "content": TASK + canonical(case) + "\n" + PREP[arm]}],
    }


def final_payload(case, note=None, supplied_posterior=None):
    number = {"type": "number", "minimum": 0, "maximum": 1}
    props = {k: number for k in ("H1", "H2", "H3")}
    schema = {
        "type": "object", "properties": {
            "evidence_basis": {"type": "string"},
            "probabilities": {"type": "object", "properties": props,
                              "required": list(props), "additionalProperties": False},
            "future_probability": number,
        }, "required": ["evidence_basis", "probabilities", "future_probability"],
        "additionalProperties": False,
    }
    messages = [{"role": "user", "content": TASK + canonical(case)}]
    if note is not None:
        messages.extend([{"role": "assistant", "content": note},
                         {"role": "user", "content": FINAL}])
    else:
        messages[0]["content"] += (
            "\nDiagnostic control: the exact posterior is " + canonical(supplied_posterior)
            + ". Use it to predict the future study. " + FINAL
        )
    return {"model": MODEL, "max_tokens": MAX_TOKENS, "temperature": 0,
            "thinking": {"type": "disabled"}, "system": SYSTEM, "messages": messages,
            "tools": [{"name": "submit_assessment", "description": "Submit probability estimates.",
                       "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": "submit_assessment"}}


def parse_assessment(response):
    blocks = [b for b in response.get("content", [])
              if b.get("type") == "tool_use" and b.get("name") == "submit_assessment"]
    if len(blocks) != 1 or response.get("stop_reason") != "tool_use":
        raise ValueError("Missing or truncated assessment")
    data = blocks[0]["input"]
    p = data["probabilities"]
    if set(p) != {"H1", "H2", "H3"}:
        raise ValueError("Wrong hypothesis keys")
    nums = [*p.values(), data["future_probability"]]
    if any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in nums):
        raise ValueError("Invalid probability")
    total = sum(p.values())
    if abs(total - 1) > 0.005:
        raise ValueError("Probabilities do not sum to one")
    # Only roundoff-sized normalization is allowed, and its size is logged.
    return {"probabilities": {k: v / total for k, v in p.items()},
            "future_probability": data["future_probability"],
            "normalization_delta": total - 1, "evidence_basis": data.get("evidence_basis", "")}


def generate(out, n=32):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite an existing freeze")
    out.mkdir(parents=True, exist_ok=True)
    cases, gold = make_cases(n)
    write_json(out / "cases.json", cases)
    write_json(out / "gold.json", gold)
    shutil.copyfile(__file__, out / "experiment.py")
    readme = Path(__file__).with_name("README.md")
    if readme.exists():
        shutil.copyfile(readme, out / "PROTOCOL.md")
    write_json(out / "manifest.json", {
        "version": VERSION, "seed": SEED, "model": MODEL, "n_cases": n,
        "arms": list(ARMS), "diagnostic": "oracle_readout", "planned_calls": 7 * n,
        "max_output_tokens_per_call": MAX_TOKENS, "thinking": "disabled",
        "primary_comparison": "contrastive_audit minus calibration_checklist",
        "primary_metric": "mean squared Euclidean distance to exact posterior",
        "max_budget_usd": 25, "prices_per_million": {"input": 3, "output": 15},
        "files": {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()},
    })
    print(f"Frozen {n} cases; planned {7 * n} calls.", flush=True)


class Collector:
    """Reserve before sending; retain reservation on ambiguous failures; never retry."""

    def __init__(self, out, budget):
        self.out, self.budget = out, budget
        self.lock = threading.Lock()
        self.committed = 0.0
        self.actual = 0.0
        self.stop = False
        self.key = os.environ["ANTHROPIC_API_KEY"]

    def call(self, case_id, arm, stage, payload):
        raw = canonical(payload).encode()
        # Each UTF-8 byte is a conservative input token allowance; 4096 more for tool overhead.
        reserve = ((len(raw) + 4096) * 3 + payload["max_tokens"] * 15) / 1_000_000
        with self.lock:
            if self.stop or self.committed + reserve > self.budget:
                raise RuntimeError("Collection stopped or budget exhausted")
            self.committed += reserve
        record = {"case_id": case_id, "arm": arm, "stage": stage,
                  "request": payload, "reserved_usd": reserve, "start_time": time.time()}
        started = time.monotonic()
        response, error = None, None
        try:
            request = urllib.request.Request(
                "https://api.anthropic.com/v1/messages", data=raw,
                headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(request, timeout=150) as handle:
                response = json.load(handle)
            usage = response["usage"]
            cost = (usage["input_tokens"] * 3 + usage["output_tokens"] * 15) / 1_000_000
            record.update(response=response, cost_usd=cost)
            with self.lock:
                self.actual += cost
                self.committed += cost - reserve
                if cost > reserve:
                    self.stop = True
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException) as exc:
            # Provider messages and request headers may contain sensitive data: never log them.
            error = type(exc).__name__
            record["error"] = error
            if isinstance(exc, urllib.error.HTTPError):
                record["http_status"] = exc.code
            with self.lock:
                self.stop = True  # Preserve results and halt on infrastructure errors.
        record["elapsed_seconds"] = time.monotonic() - started
        with self.lock:
            with (self.out / "calls.jsonl").open("a") as stream:
                stream.write(canonical(record) + "\n")
            write_json(self.out / "spend.json", {
                "actual_recorded_usd": self.actual, "committed_upper_usd": self.committed,
                "budget_usd": self.budget,
            })
        if error:
            raise RuntimeError(error)
        return response

    def task(self, case, arm, gold):
        cid = case["case_id"]
        result = {"case_id": cid, "arm": arm, "valid": False}
        try:
            if arm == "oracle_readout":
                payload = final_payload(case, supplied_posterior=gold["posterior"])
            else:
                prep = self.call(cid, arm, "prepare", prepare_payload(case, arm))
                note = "\n".join(b["text"] for b in prep["content"] if b["type"] == "text")
                result["preparation_truncated"] = prep.get("stop_reason") == "max_tokens"
                if not note:
                    raise ValueError("Empty preparation")
                payload = final_payload(case, note=note)
            response = self.call(cid, arm, "final", payload)
            result.update(parse_assessment(response), valid=True)
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            result["error"] = type(exc).__name__
        with self.lock:
            with (self.out / "responses.jsonl").open("a") as stream:
                stream.write(canonical(result) + "\n")
            print(f"{cid} {arm}: valid={result['valid']}; recorded=${self.actual:.4f}", flush=True)
        return result


def collect(out, budget):
    if not 0 < budget <= 25:
        raise ValueError("Budget must be between zero and the frozen $25 ceiling")
    if (out / "collection.started").exists():
        raise ValueError("Collection already attempted; no automatic resume or repeat billing")
    manifest = json.loads((out / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if digest(out / name) != expected:
            raise ValueError(f"Freeze hash mismatch: {name}")
    if digest(Path(__file__)) != manifest["files"]["experiment.py"]:
        raise ValueError("Must collect using frozen runner")
    collector = Collector(out, budget)
    (out / "collection.started").write_text(str(time.time()))
    cases = json.loads((out / "cases.json").read_text())
    gold = {g["case_id"]: g for g in json.loads((out / "gold.json").read_text())}
    jobs = [(c, a, gold[c["case_id"]]) for c in cases for a in (*ARMS, "oracle_readout")]
    random.Random(SEED + 1).shuffle(jobs)
    # One real planned task doubles as API smoke check; no score-dependent gate.
    collector.task(*jobs.pop(0))
    if not collector.stop:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda job: collector.task(*job), jobs))
    report(out)
    if collector.stop:
        raise RuntimeError("Infrastructure or reservation check halted collection; see records")


def squared_distance(p, q):
    return sum((p[k] - q[k]) ** 2 for k in q)


def bootstrap_delta(values, seed=SEED + 2):
    if not values:
        return None
    rng = random.Random(seed)
    boot = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(10000))
    return {"n_paired_cases": len(values), "mean_delta": statistics.mean(values),
            "bootstrap_95_percentile_interval": [boot[249], boot[9749]]}


def report(out):
    manifest = json.loads((out / "manifest.json").read_text())
    gold = {g["case_id"]: g for g in json.loads((out / "gold.json").read_text())}
    path = out / "responses.jsonl"
    responses = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    scores, index = [], {}
    for r in responses:
        key = (r["case_id"], r["arm"])
        if key in index:
            raise ValueError("Duplicate assessment")
        index[key] = r
        if not r["valid"]:
            continue
        g = gold[r["case_id"]]
        row = {"case_id": r["case_id"], "arm": r["arm"], "stratum": g["stratum"],
               "posterior_regret": squared_distance(r["probabilities"], g["posterior"]),
               "future_regret": (r["future_probability"] - g["future_probability"]) ** 2,
               "realized_hypothesis_brier": squared_distance(
                   r["probabilities"], {k: int(k == g["true_h"]) for k in g["posterior"]}),
               "realized_future_brier": (r["future_probability"] - g["future_outcome"]) ** 2}
        scores.append(row)
    metrics = ("posterior_regret", "future_regret", "realized_hypothesis_brier",
               "realized_future_brier")
    summary = {"version": VERSION, "n_cases": len(gold), "arms": {}}
    for arm in (*ARMS, "oracle_readout"):
        rows = [r for r in scores if r["arm"] == arm]
        attempted = [r for r in responses if r["arm"] == arm]
        summary["arms"][arm] = {
            "valid": len(rows), "invalid": len(attempted) - len(rows),
            "missing": len(gold) - len(attempted),
            "preparation_truncated": sum(r.get("preparation_truncated", False) for r in attempted),
            **{m: statistics.mean(r[m] for r in rows) if rows else None for m in metrics},
            "by_stratum": {s: {
                "n": len(part := [r for r in rows if r["stratum"] == s]),
                "posterior_regret": statistics.mean(r["posterior_regret"] for r in part)
                if part else None} for s in STRATA},
        }
    score_index = {(r["case_id"], r["arm"]): r for r in scores}
    delta = []
    for cid in gold:
        a = score_index.get((cid, "contrastive_audit"))
        b = score_index.get((cid, "calibration_checklist"))
        if a and b:
            delta.append(a["posterior_regret"] - b["posterior_regret"])
    summary["primary_paired_comparison"] = bootstrap_delta(delta)
    calls_path = out / "calls.jsonl"
    calls = [json.loads(x) for x in calls_path.read_text().splitlines()] if calls_path.exists() else []
    summary["calls"] = len(calls)
    summary["planned_calls"] = manifest["planned_calls"]
    summary["recorded_cost_usd"] = sum(c.get("cost_usd", 0) for c in calls)
    summary["unknown_cost_calls"] = sum("cost_usd" not in c for c in calls)
    summary["cost_by_arm_usd"] = {
        a: sum(c.get("cost_usd", 0) for c in calls if c["arm"] == a)
        for a in (*ARMS, "oracle_readout")}
    write_json(out / "scores.json", scores)
    write_json(out / "summary.json", summary)
    lines = ["# Scientific confidence v1: exploratory pilot", "",
             (f"Recorded API cost: ${summary['recorded_cost_usd']:.4f}. "
              f"Calls: {len(calls)}/{manifest['planned_calls']}."), "",
             "Lower regret is better. Oracle readout is an answer-supplied diagnostic.", "",
             "| Arm | Valid | Invalid / missing | Posterior regret | Future regret |",
             "|---|---:|---:|---:|---:|"]
    for arm, s in summary["arms"].items():
        vals = [f"{s[m]:.6f}" if s[m] is not None else "NA"
                for m in ("posterior_regret", "future_regret")]
        lines.append(f"| {arm} | {s['valid']} | {s['invalid']} / {s['missing']} | "
                     + " | ".join(vals) + " |")
    lines.extend(["", "Primary paired comparison (audit minus checklist; negative favors audit):",
                  "", "```json", json.dumps(summary["primary_paired_comparison"], indent=2),
                  "```", "", ("Exploratory, one model/configuration, 32 simulated cases by default. "
                  "Matched call/token ceilings, not equal actual compute. No weights were trained. "
                  "The supplied models are exhaustive and correctly specified; real science is not. "
                  "This measures probabilistic model comparison, not general scientific reasoning. "
                  "Do not select or tune a procedure on this pilot and call its result confirmation.")])
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "collect", "report"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", type=int, default=32)
    parser.add_argument("--budget-usd", type=float, default=25)
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.out, args.cases)
    elif args.command == "collect":
        collect(args.out, args.budget_usd)
    else:
        report(args.out)


if __name__ == "__main__":
    main()
