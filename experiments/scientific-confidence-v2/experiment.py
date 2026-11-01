"""Fresh-case test of evidence representation and arithmetic; no API calls unless collect."""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import math
import random
import shutil
import statistics
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPPORT = HERE / "v1_support.py"
if not SUPPORT.exists():
    SUPPORT = HERE.parent / "scientific-confidence-v1" / "experiment.py"
SPEC = importlib.util.spec_from_file_location("confidence_v1_support", SUPPORT)
assert SPEC is not None and SPEC.loader is not None
v1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v1)

VERSION = "scientific-confidence-v2"
SEEDS = {"development": 90261031, "main": 20261031}
TOKENS = 4096
MAX_BUDGET = 25
HIDS = ("H1", "H2", "H3")
CONDITIONS = ("checklist_verbal", "audit_verbal", "checklist_manual", "checklist_calculated",
              "ledger_manual", "ledger_calculated")
LEDGER_INSTRUCTION = (
    "Prepare a source-linked evidence table using submit_ledger. Keep the original priors. "
    "For each UNIQUE study_id, copy its design, context, estimate, and standard error. "
    "For EACH hypothesis, look up the predicted mean using that study's exact design/context "
    "key. Check each cell against its source; never copy a neighboring hypothesis's mean "
    "without checking. Include the new study and its hypothesis-specific means. "
    "Preserve at least six decimal places for non-simple input numbers. "
    "Do not compute posterior probabilities at this preparation stage."
)
WORKSHEET_FINAL = (
    "Now use submit_worksheet. Recheck the dossier and your preparation. Submit one row per "
    "unique study, original priors, and the future study's prediction under each hypothesis. "
    "Preserve at least six decimal places for non-simple input numbers. Also give your own "
    "posterior probabilities and future probability based on that worksheet. Give a concise "
    "evidence_basis. The probabilities must sum to one. You may correct your preparation."
)


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def worksheet_schema(with_answer=False):
    number = {"type": "number"}
    probability = {"type": "number", "minimum": 0, "maximum": 1}
    means = obj({k: number for k in HIDS})
    design = {"type": "string", "enum": ["randomized", "observational"]}
    context = {"type": "string", "enum": ["A", "B"]}
    row = obj({"study_id": {"type": "string"}, "design": design, "context": context,
               "estimate": number, "se": number, "predicted_means": means})
    properties = {
        "priors": obj({k: probability for k in HIDS}),
        "studies": {"type": "array", "items": row, "minItems": 1, "maxItems": 16},
        "future_study": obj({"design": design, "context": context, "se": number,
                             "threshold": number, "predicted_means": means}),
    }
    if with_answer:
        properties.update(evidence_basis={"type": "string"},
                          probabilities=obj({k: probability for k in HIDS}),
                          future_probability=probability)
    return obj(properties)


def tool_payload(case, instruction, name, schema, note=None):
    messages = [{"role": "user", "content": v1.TASK + v1.canonical(case)}]
    if note is not None:
        messages.extend([{"role": "assistant", "content": note},
                         {"role": "user", "content": instruction}])
    else:
        messages[0]["content"] += "\n" + instruction
    return {"model": v1.MODEL, "max_tokens": TOKENS, "temperature": 0,
            "thinking": {"type": "disabled"}, "system": v1.SYSTEM, "messages": messages,
            "tools": [{"name": name, "description": "Submit the requested structured assessment.",
                       "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": name}}


def preparation(case, arm):
    if arm == "ledger":
        return tool_payload(case, LEDGER_INSTRUCTION, "submit_ledger", worksheet_schema())
    p = v1.prepare_payload(case, "calibration_checklist" if arm == "checklist"
                           else "contrastive_audit")
    p["max_tokens"] = TOKENS
    return p


def final_payload(case, note, worksheet):
    if worksheet:
        return tool_payload(case, WORKSHEET_FINAL, "submit_worksheet", worksheet_schema(True), note)
    p = v1.final_payload(case, note=note)
    p["max_tokens"] = TOKENS
    return p


def tool_input(response, name):
    blocks = [b for b in response.get("content", [])
              if b.get("type") == "tool_use" and b.get("name") == name]
    if response.get("stop_reason") != "tool_use" or len(blocks) != 1:
        raise ValueError("Missing or unfinished tool output")
    return blocks[0]["input"]


def finite(x):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ValueError("Expected finite number")
    return x


def probabilities(data):
    p = data["probabilities"]
    if set(p) != set(HIDS):
        raise ValueError("Wrong hypothesis IDs")
    vals = [finite(x) for x in p.values()]
    future = finite(data["future_probability"])
    if any(not 0 <= x <= 1 for x in [*vals, future]) or abs(sum(vals) - 1) > 0.005:
        raise ValueError("Invalid probability vector")
    return {"posterior": {k: p[k] / sum(vals) for k in HIDS}, "future_probability": future,
            "normalization_delta": sum(vals) - 1}


def calculate(table):
    """Source-blind calculator. It receives neither original dossier nor hidden gold."""
    prior = table["priors"]
    if set(prior) != set(HIDS) or any(not 0 < finite(x) <= 1 for x in prior.values()):
        raise ValueError("Invalid priors")
    if abs(sum(prior.values()) - 1) > 0.005:
        raise ValueError("Unnormalized priors")
    studies = {}
    if not 1 <= len(table["studies"]) <= 16:
        raise ValueError("Invalid number of studies")
    for row in table["studies"]:
        sid = row["study_id"]
        if not isinstance(sid, str) or not sid:
            raise ValueError("Invalid study ID")
        if sid in studies and studies[sid] != row:
            raise ValueError("Inconsistent duplicate rows")
        if row["design"] not in ("randomized", "observational") or row["context"] not in ("A", "B"):
            raise ValueError("Invalid source key")
        finite(row["estimate"])
        if finite(row["se"]) <= 0 or set(row["predicted_means"]) != set(HIDS):
            raise ValueError("Invalid study parameters")
        for value in row["predicted_means"].values():
            finite(value)
        studies[sid] = row
    logs = {
        h: math.log(prior[h]) - 0.5 * sum(
            ((r["estimate"] - r["predicted_means"][h]) / r["se"]) ** 2
            for r in studies.values()) for h in HIDS}
    top = max(logs.values())
    weights = {h: math.exp(logs[h] - top) for h in HIDS}
    posterior = {h: weights[h] / sum(weights.values()) for h in HIDS}
    f = table["future_study"]
    if finite(f["se"]) <= 0 or set(f["predicted_means"]) != set(HIDS):
        raise ValueError("Invalid future parameters")
    finite(f["threshold"])
    for mu in f["predicted_means"].values():
        finite(mu)
    future = sum(posterior[h] * 0.5 * math.erfc(
        (f["threshold"] - f["predicted_means"][h]) / (f["se"] * math.sqrt(2))) for h in HIDS)
    return {"posterior": posterior, "future_probability": future}


def source_diagnostic(table, case):
    """Evaluation only. Never feeds repairs, probabilities, or feedback to collection."""
    rows = {r["study_id"]: r for r in table["studies"]}
    source = {s["study_id"]: s for s in v1.unique_studies(case)}
    hypotheses = {h["id"]: h for h in case["hypotheses"]}
    numeric_errors, mean_errors = [], []
    keys_ok = set(rows) == set(source)
    for sid, study in source.items():
        if sid not in rows:
            continue
        row = rows[sid]
        keys_ok &= row["design"] == study["design"] and row["context"] == study["context"]
        numeric_errors.extend(abs(row[k] - study[k]) for k in ("estimate", "se"))
        mean_errors.extend(abs(row["predicted_means"][h] - v1.mean_for(
            hypotheses[h], study["design"], study["context"])) for h in HIDS)
    for h in HIDS:
        numeric_errors.append(abs(table["priors"][h] - hypotheses[h]["prior"]))
    future, f = table["future_study"], case["future_study"]
    keys_ok &= future["design"] == f["design"] and future["context"] == f["context"]
    numeric_errors.extend(abs(future[k] - f[k]) for k in ("se", "threshold"))
    mean_errors.extend(abs(future["predicted_means"][h] - v1.mean_for(
        hypotheses[h], f["design"], f["context"])) for h in HIDS)
    return {"source_keys_correct": bool(keys_ok), "incorrect_prediction_cells": sum(
        x > 1e-8 for x in mean_errors), "max_numeric_copy_error": max(numeric_errors),
        "source_faithful": bool(keys_ok and all(x <= 1e-8 for x in mean_errors)
                                and all(x <= 1e-5 for x in numeric_errors)),
        "extra_duplicate_rows": len(table["studies"]) - len(rows)}


def make_cases(phase, n):
    cases, gold = v1.make_cases(n, seed=SEEDS[phase])
    for i, (case, g) in enumerate(zip(cases, gold)):
        case["case_id"] = g["case_id"] = ("DEV" if phase == "development" else "TEST") + f"{i:03d}"
        g["phase"] = phase
    return cases, gold


def generate(out, main_cases=32):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite existing freeze")
    out.mkdir(parents=True, exist_ok=True)
    all_cases, all_gold = [], []
    for phase, n in (("development", 4), ("main", main_cases)):
        cases, gold = make_cases(phase, n)
        all_cases.extend(cases)
        all_gold.extend(gold)
    v1.write_json(out / "cases.json", all_cases)
    v1.write_json(out / "gold.json", all_gold)
    shutil.copyfile(__file__, out / "experiment.py")
    shutil.copyfile(SUPPORT, out / "v1_support.py")
    shutil.copyfile(HERE / "README.md", out / "PROTOCOL.md")
    v1.write_json(out / "manifest.json", {
        "version": VERSION, "model": v1.MODEL, "seeds": SEEDS, "main_cases": main_cases,
        "development_cases": 4, "planned_calls": 7 * (4 + main_cases),
        "output_tokens_per_call": TOKENS, "max_budget_usd": MAX_BUDGET,
        "primary": "ledger_calculated minus checklist_calculated: failure-aware posterior loss",
        "invalid_posterior_penalty": 2, "invalid_future_penalty": 1,
        "readouts": list(CONDITIONS),
        "files": {p.name: v1.digest(p) for p in sorted(out.iterdir()) if p.is_file()},
    })
    print(f"Frozen 4 development + {main_cases} main cases; {7 * (4 + main_cases)} calls.", flush=True)


class Collector(v1.Collector):
    def call(self, *args):
        try:
            return super().call(*args)
        except RuntimeError:
            with self.lock:
                self.stop = True
            raise

    def save_record(self, record):
        with self.lock:
            with (self.out / "records.jsonl").open("a") as stream:
                stream.write(v1.canonical(record) + "\n")
            print(f"{record['case_id']} {record['kind']}: "
                  f"recorded cost=${self.actual:.4f}", flush=True)

    def task(self, case, arm):
        cid = case["case_id"]
        kinds = ["verbal", "worksheet"] if arm == "checklist" else [
            "verbal" if arm == "audit" else "worksheet"]
        random.Random(cid).shuffle(kinds)
        prep_truncated, note = False, None
        try:
            prep = self.call(cid, arm, "prepare", preparation(case, arm))
            prep_truncated = prep.get("stop_reason") == "max_tokens"
            if arm == "ledger":
                note = "Prepared evidence table:\n" + v1.canonical(tool_input(prep, "submit_ledger"))
            else:
                note = "\n".join(b["text"] for b in prep["content"] if b["type"] == "text")
            if not note:
                raise ValueError("Empty preparation")
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            for kind in kinds:
                self.save_record({"case_id": cid, "kind": arm + "_" + kind,
                                  "error": type(exc).__name__, "preparation_truncated": prep_truncated})
            return
        for kind in kinds:
            record = {"case_id": cid, "kind": arm + "_" + kind,
                      "preparation_truncated": prep_truncated}
            try:
                response = self.call(cid, arm, kind, final_payload(case, note, kind == "worksheet"))
                record["final_truncated"] = response.get("stop_reason") == "max_tokens"
                record["data"] = tool_input(response, "submit_worksheet" if kind == "worksheet"
                                            else "submit_assessment")
            except (RuntimeError, ValueError, KeyError, TypeError) as exc:
                record["error"] = type(exc).__name__
            self.save_record(record)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def development_gate(out):
    calls = [r for r in read_jsonl(out / "calls.jsonl") if r["case_id"].startswith("DEV")]
    problems = []
    if len(calls) != 28:
        problems.append("Development call count differs from 28")
    for call in calls:
        response = call.get("response", {})
        if response.get("stop_reason") == "max_tokens":
            problems.append(f"Truncated {call['case_id']} {call['arm']} {call['stage']}")
        if "error" in call:
            problems.append("Infrastructure error")
        if call["stage"] in ("worksheet", "verbal") or call["arm"] == "ledger":
            name = "submit_ledger" if call["stage"] == "prepare" else (
                "submit_worksheet" if call["stage"] == "worksheet" else "submit_assessment")
            try:
                tool_input(response, name)
            except (ValueError, KeyError, TypeError):
                problems.append("Unusable structured output")
    # Deliberately no correctness, normalized-probability, or source-faithfulness gate.
    return {"passed": not problems, "problems": problems,
            "rule": "Complete, non-truncated requests and usable tool objects only; scores ignored"}


def collect(out, budget, requested_phase="all"):
    if not 0 < budget <= MAX_BUDGET:
        raise ValueError("Budget exceeds frozen ceiling or is not positive")
    manifest = json.loads((out / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if v1.digest(out / name) != expected:
            raise ValueError(f"Freeze hash mismatch: {name}")
    if v1.digest(Path(__file__)) != manifest["files"]["experiment.py"]:
        raise ValueError("Use the frozen runner")
    collector = Collector(out, budget)
    if requested_phase == "main":
        gate = json.loads((out / "development_gate.json").read_text())
        previous = read_jsonl(out / "calls.jsonl")
        if (not gate["passed"] or not development_gate(out)["passed"]
                or any(not c["case_id"].startswith("DEV") for c in previous)
                or any("cost_usd" not in c for c in previous)):
            raise ValueError("Main requires a completed clean development phase")
        spend = json.loads((out / "spend.json").read_text())
        collector.actual = sum(c["cost_usd"] for c in previous)
        collector.committed = spend["committed_upper_usd"]
        if abs(collector.actual - collector.committed) > 1e-8:
            raise ValueError("Unsettled development reservations")
    cases = json.loads((out / "cases.json").read_text())
    for phase, prefix in (("development", "DEV"), ("main", "TEST")):
        if requested_phase not in ("all", phase):
            continue
        marker = out / f"collection.{phase}.started"
        if marker.exists():
            raise ValueError("Phase already attempted; no automatic resume or repeat billing")
        marker.write_text(str(time.time()))
        jobs = [(c, a) for c in cases if c["case_id"].startswith(prefix)
                for a in ("checklist", "audit", "ledger")]
        random.Random(SEEDS[phase] + 1).shuffle(jobs)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda j: collector.task(*j), jobs))
        if phase == "development":
            gate = development_gate(out)
            v1.write_json(out / "development_gate.json", gate)
            print("Development gate:", v1.canonical(gate), flush=True)
            if not gate["passed"] or collector.stop:
                report(out)
                raise RuntimeError("Development infrastructure/budget gate failed; main not sent")
    report(out)
    if collector.stop:
        raise RuntimeError("Collection halted; partial records preserved")


def score_record(record, condition, case, gold):
    row = {"case_id": case["case_id"], "phase": gold["phase"], "stratum": gold["stratum"],
           "condition": condition, "valid": False, "posterior_loss": 2.0, "future_loss": 1.0}
    if record is None:
        row["error"] = "MissingRecord"
        return row
    row["preparation_truncated"] = record.get("preparation_truncated", False)
    row["final_truncated"] = record.get("final_truncated", False)
    try:
        data = record["data"]
        answer = calculate(data) if condition.endswith("calculated") else probabilities(data)
        row.update(valid=True, answer=answer,
                   posterior_loss=v1.squared_distance(answer["posterior"], gold["posterior"]),
                   future_loss=(answer["future_probability"] - gold["future_probability"]) ** 2)
    except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        row["error"] = type(exc).__name__
    if "worksheet" in record["kind"]:
        try:
            calculate(record["data"])  # Validate numerical structure before diagnostics.
            row["source_diagnostic"] = source_diagnostic(record["data"], case)
        except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError):
            row["source_diagnostic"] = None
    return row


def report(out):
    manifest = json.loads((out / "manifest.json").read_text())
    cases = json.loads((out / "cases.json").read_text())
    gold = {g["case_id"]: g for g in json.loads((out / "gold.json").read_text())}
    records = {}
    for record in read_jsonl(out / "records.jsonl"):
        key = (record["case_id"], record["kind"])
        if key in records:
            raise ValueError("Duplicate output record")
        records[key] = record
    scores = []
    for case in cases:
        for condition in CONDITIONS:
            kind = condition if condition.endswith("verbal") else condition.rsplit("_", 1)[0] + "_worksheet"
            scores.append(score_record(records.get((case["case_id"], kind)), condition,
                                       case, gold[case["case_id"]]))
    main = [s for s in scores if s["phase"] == "main"]
    arms = {}
    for condition in CONDITIONS:
        rows = [s for s in main if s["condition"] == condition]
        valid = [r for r in rows if r["valid"]]
        arms[condition] = {
            "n": len(rows), "valid": len(valid), "invalid_or_missing": len(rows) - len(valid),
            "mean_posterior_loss": statistics.mean(r["posterior_loss"] for r in rows),
            "mean_future_loss": statistics.mean(r["future_loss"] for r in rows),
            "valid_only_posterior_regret": statistics.mean(r["posterior_loss"] for r in valid)
            if valid else None,
            "source_faithful": sum(bool(r.get("source_diagnostic", {}) and
                                       r["source_diagnostic"]["source_faithful"]) for r in rows)
            if not condition.endswith("verbal") else None,
        }
    comparisons = {}
    idx = {(s["case_id"], s["condition"]): s for s in main}
    pairs = [
        ("primary_representation", "ledger_calculated", "checklist_calculated"),
        ("bundle_vs_verbal", "ledger_calculated", "checklist_verbal"),
        ("audit_with_more_room", "audit_verbal", "checklist_verbal"),
        ("arithmetic_checklist", "checklist_calculated", "checklist_manual"),
        ("arithmetic_ledger", "ledger_calculated", "ledger_manual"),
        ("worksheet_output", "checklist_manual", "checklist_verbal"),
    ]
    main_ids = [c["case_id"] for c in cases if gold[c["case_id"]]["phase"] == "main"]
    for label, first, second in pairs:
        delta = [idx[cid, first]["posterior_loss"] - idx[cid, second]["posterior_loss"]
                 for cid in main_ids]
        paired_valid = [cid for cid in main_ids if idx[cid, first]["valid"] and idx[cid, second]["valid"]]
        comparisons[label] = {"first": first, "second": second,
                              **v1.bootstrap_delta(delta), "valid_pairs": len(paired_valid),
                              "valid_only_mean_delta": statistics.mean(
                                  idx[cid, first]["posterior_loss"] - idx[cid, second]["posterior_loss"]
                                  for cid in paired_valid) if paired_valid else None}
    calls = read_jsonl(out / "calls.jsonl")
    summary = {"version": VERSION, "main_cases": len(main_ids), "conditions": arms,
               "comparisons": comparisons, "calls": len(calls),
               "planned_calls": manifest["planned_calls"],
               "recorded_cost_usd": sum(c.get("cost_usd", 0) for c in calls),
               "unknown_cost_calls": sum("cost_usd" not in c for c in calls),
               "main_record_count": sum(cid.startswith("TEST") for cid, kind in records),
               "main_expected_records": 4 * len(main_ids),
               "truncation_by_phase_stage": {phase: {
                   stage: sum(c["case_id"].startswith(prefix) and c["stage"] == stage and
                              c.get("response", {}).get("stop_reason") == "max_tokens" for c in calls)
                   for stage in ("prepare", "verbal", "worksheet")}
                   for phase, prefix in (("development", "DEV"), ("main", "TEST"))},
               "cost_by_phase_usd": {phase: sum(c.get("cost_usd", 0) for c in calls
                                                   if c["case_id"].startswith(prefix))
                                     for phase, prefix in (("development", "DEV"), ("main", "TEST"))}}
    v1.write_json(out / "scores.json", scores)
    v1.write_json(out / "summary.json", summary)
    lines = ["# Scientific confidence v2: frozen results", "",
             f"Calls: {len(calls)}/{manifest['planned_calls']}. "
             + f"Recorded cost: ${summary['recorded_cost_usd']:.6f}.", "",
             "Main evaluation only; 4 development cases excluded. Lower loss is better.", "",
             "| Condition | Valid | Posterior loss | Future loss | Source-faithful tables |",
             "|---|---:|---:|---:|---:|"]
    for name, a in arms.items():
        lines.append(f"| {name} | {a['valid']}/{a['n']} | {a['mean_posterior_loss']:.8f} | "
                     f"{a['mean_future_loss']:.8f} | {a['source_faithful']} |")
    lines.extend(["", "Primary representation comparison (negative favors ledger):", "",
                  "```json", json.dumps(comparisons["primary_representation"], indent=2), "```", "",
                  "Invalid/missing outputs receive posterior loss 2 and future loss 1. "
                  + "See summary.json for valid-only comparisons, truncation, and all secondary contrasts.",
                  "", "Calculated readouts use only the model's worksheet. They are deterministic "
                  + "postprocessing, not additional LLM conditions or independent observations. "
                  + "This is one exploratory run with supplied, correctly specified hypotheses; "
                  + "it does not establish open-ended scientific reasoning or long-horizon stability."])
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "collect", "report"))
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--cases", type=int, default=32)
    parser.add_argument("--budget-usd", type=float, default=MAX_BUDGET)
    parser.add_argument("--phase", choices=("all", "development", "main"), default="all")
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.out, args.cases)
    elif args.command == "collect":
        collect(args.out, args.budget_usd, args.phase)
    else:
        report(args.out)


if __name__ == "__main__":
    main()
