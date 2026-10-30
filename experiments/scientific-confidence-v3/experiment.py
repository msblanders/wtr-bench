"""Fresh one-call confirmation and sequential evidence-state experiment (stdlib only)."""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import importlib.util
import json
import random
import shutil
import statistics
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUPPORT = HERE / "v2_support.py"
if not SUPPORT.exists():
    SUPPORT = HERE.parent / "scientific-confidence-v2" / "experiment.py"
SPEC = importlib.util.spec_from_file_location("confidence_v2_support", SUPPORT)
assert SPEC and SPEC.loader
v2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v2)
v1 = v2.v1

VERSION = "scientific-confidence-v3"
SEEDS = {"development_confirmation": 90371101, "main_confirmation": 20371101,
         "development_sequential": 90481101, "main_sequential": 20481101}
MAX_BUDGET = 80
ARMS = ("checklist_state", "ledger_state", "ledger_rebuild")
STEPS = ("initial", "new_study", "duplicate", "review", "new_study", "duplicate",
         "review", "new_study", "duplicate", "review", "new_study", "review")
CHECKLIST = (
    "Maintain a calibrated evidence assessment. Consider every alternative, prior rates, "
    "study quality and precision, conflicting evidence, and dependence between sources. "
    "Avoid unwarranted certainty and indiscriminate hedging. Review the available material "
    "carefully and update the complete worksheet for the evidence now available."
)
LEDGER = (
    "Maintain a source-linked evidence ledger. Keep the ORIGINAL priors separate from derived "
    "posterior beliefs; never use a previous posterior as the prior when recounting old studies. "
    "Identify every incoming report by study_id. Preserve earlier unique studies, add genuinely "
    "new study IDs once, and count duplicate reports only once. For each hypothesis and study, "
    "check the predicted mean against that study's exact design/context in the model specification. "
    "Preserve source numbers. A review without new evidence may correct an earlier copying error, "
    "but must not create additional evidence. Return the complete updated ledger."
)
COMMON = (
    "Use submit_state. The worksheet must contain all unique studies available so far, their "
    "hypothesis-specific predicted means, original prior probabilities, and the fixed future study. "
    "Preserve at least six decimal places for non-simple numbers. evidence_basis is a concise "
    "readable account of the current evidence (at most 120 words). Do not calculate probabilities: "
    "a separate source-blind calculator will compute them from exactly this worksheet. The next "
    "update will receive this worksheet, evidence_basis, and the calculator's derived beliefs."
)


def state_schema():
    schema = copy.deepcopy(v2.worksheet_schema())
    schema["properties"]["evidence_basis"] = {"type": "string"}
    schema["required"].append("evidence_basis")
    return schema


def number(x):
    return format(x, ".12g")


def report_text(report):
    return (f"Report {report['report_id']}: Study {report['study_id']} used a "
            f"{report['design']} design in context {report['context']}. Its effect estimate "
            f"was {number(report['estimate'])}, with standard error {number(report['se'])}.")


def dossier_at(trajectory, step):
    return {"case_id": trajectory["case_id"], "hypotheses": trajectory["hypotheses"],
            "future_study": trajectory["future_study"],
            "reports": [r for ev in trajectory["events"][:step + 1] for r in ev["reports"]]}


def sequential_cases(phase, n):
    seed = SEEDS[phase + "_sequential"]
    cases, truths = v1.make_cases(n, seed=seed)
    trajectories, gold = [], []
    for i, (case, truth) in enumerate(zip(cases, truths)):
        cid = ("DSEQ" if phase == "development" else "SEQ") + f"{i:03d}"
        studies = sorted(v1.unique_studies(case), key=lambda r: r["study_id"])
        true_h = next(h for h in case["hypotheses"] if h["id"] == truth["true_h"])
        rng = random.Random(seed + 7919 * i + 20000000)
        for j, context in ((5, "B"), (6, "A")):
            se = rng.choice([0.3, 0.5, 0.7])
            studies.append({"study_id": f"S{j}", "design": "randomized", "context": context,
                            "se": se, "estimate": rng.gauss(v1.mean_for(
                                true_h, "randomized", context), se)})
        # The presented decimals, rather than unprinted floating-point tails, are authoritative.
        for s in studies:
            s["estimate"] = float(number(s["estimate"]))
        event_studies = {0: studies[:2], 1: [studies[2]], 2: [studies[0]] * 3,
                         4: [studies[3]], 5: [studies[2]] * 3,
                         7: [studies[4]], 8: [studies[3]] * 3, 10: [studies[5]]}
        events, rid = [], 0
        for step, kind in enumerate(STEPS):
            reports = []
            for s in event_studies.get(step, []):
                rid += 1
                reports.append(dict(s, report_id=f"R{rid}"))
            events.append({"step": step, "kind": kind, "reports": reports})
        trajectory = {"case_id": cid, "phase": phase, "hypotheses": case["hypotheses"],
                      "future_study": case["future_study"], "events": events}
        trajectories.append(trajectory)
        gold.append({"case_id": cid, "phase": phase, "stratum": truth["stratum"],
                     "true_h": truth["true_h"], "checkpoints": [
                         dict(step=t, kind=STEPS[t], **v1.oracle(dossier_at(trajectory, t)))
                         for t in range(len(STEPS))]})
    return trajectories, gold


def sequential_payload(trajectory, step, arm, state):
    event = trajectory["events"][step]
    specification = {"hypotheses": trajectory["hypotheses"],
                     "future_study": trajectory["future_study"]}
    if arm == "ledger_rebuild":
        reports = dossier_at(trajectory, step)["reports"]
        evidence = "Complete original report archive:\n" + "\n".join(map(report_text, reports))
        previous = "Rebuild from original sources; no previous model state is supplied."
    else:
        evidence = "Incoming report packet:\n" + ("\n".join(map(report_text, event["reports"]))
                    or "No new reports. Review the current evidence assessment.")
        previous = "Previous working state (not an additional observation):\n" + v1.canonical(state)
    instruction = CHECKLIST if arm == "checklist_state" else LEDGER
    content = (v1.TASK + "\nModel specification:\n" + v1.canonical(specification)
               + f"\nUpdate {step + 1}.\n" + previous + "\n" + evidence + "\n"
               + instruction + "\n" + COMMON)
    return {"model": v1.MODEL, "max_tokens": v2.TOKENS, "temperature": 0,
            "thinking": {"type": "disabled"}, "system": v1.SYSTEM,
            "messages": [{"role": "user", "content": content}],
            "tools": [{"name": "submit_state", "description": "Submit complete current evidence state.",
                       "input_schema": state_schema()}],
            "tool_choice": {"type": "tool", "name": "submit_state"}}


def generate(out, confirmations=64, trajectories=32):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite freeze")
    if confirmations < 1 or trajectories < 1:
        raise ValueError("Positive sample sizes required")
    out.mkdir(parents=True, exist_ok=True)
    data, gold = {"confirmation": [], "sequential": []}, {"confirmation": [], "sequential": []}
    for phase, nc, ns in (("development", 4, 2), ("main", confirmations, trajectories)):
        cases, truths = v1.make_cases(nc, seed=SEEDS[phase + "_confirmation"])
        for i, (c, g) in enumerate(zip(cases, truths)):
            c["case_id"] = g["case_id"] = ("DCON" if phase == "development" else "CON") + f"{i:03d}"
            g["phase"] = phase
        data["confirmation"].extend(cases)
        gold["confirmation"].extend(truths)
        seq, sg = sequential_cases(phase, ns)
        data["sequential"].extend(seq)
        gold["sequential"].extend(sg)
    v1.write_json(out / "cases.json", data)
    v1.write_json(out / "gold.json", gold)
    shutil.copyfile(__file__, out / "experiment.py")
    shutil.copyfile(SUPPORT, out / "v2_support.py")
    shutil.copyfile(v2.SUPPORT, out / "v1_support.py")
    shutil.copyfile(HERE / "README.md", out / "PROTOCOL.md")
    v1.write_json(out / "manifest.json", {
        "version": VERSION, "seeds": SEEDS, "model": v1.MODEL, "tokens": v2.TOKENS,
        "main_confirmation_cases": confirmations, "main_trajectories": trajectories,
        "steps": list(STEPS), "arms": list(ARMS), "max_budget_usd": MAX_BUDGET,
        "planned_calls": 2 * (4 + confirmations) + 3 * len(STEPS) * (2 + trajectories),
        "primary_sequential": "trajectory-mean ledger_state loss minus checklist_state loss",
        "confirmation_noninferiority_margin": 0.001,
        "files": {p.name: v1.digest(p) for p in sorted(out.iterdir()) if p.is_file()}})
    print("Frozen confirmation and sequential cases.", flush=True)


def calculated_state(table):
    try:
        derived = v2.calculate(table)
    except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        derived = {"error": type(exc).__name__}
    return {"worksheet": table, "derived_beliefs": derived}


class Collector(v2.Collector):
    def confirmation(self, case):
        cid = case["case_id"]
        first = None
        for kind in ("one_call", "two_call"):
            record = {"case_id": cid, "experiment": "confirmation", "kind": kind}
            try:
                if kind == "one_call":
                    payload = v2.preparation(case, "ledger")
                    name = "submit_ledger"
                else:
                    if first is None:
                        raise ValueError("First tool output unavailable")
                    note = "Prepared evidence table:\n" + v1.canonical(first)
                    payload = v2.final_payload(case, note, True)
                    name = "submit_worksheet"
                response = self.call(cid, "confirmation", kind, payload)
                record["truncated"] = response.get("stop_reason") == "max_tokens"
                record["data"] = v2.tool_input(response, name)
                if kind == "one_call":
                    first = record["data"]
            except (RuntimeError, ValueError, KeyError, TypeError) as exc:
                record["error"] = type(exc).__name__
            self.save_record(record)

    def sequential(self, trajectory, arm):
        state = None
        for step in range(len(STEPS)):
            record = {"case_id": trajectory["case_id"], "experiment": "sequential",
                      "kind": arm, "step": step, "event": STEPS[step]}
            try:
                response = self.call(trajectory["case_id"], arm, str(step),
                                     sequential_payload(trajectory, step, arm, state))
                record["truncated"] = response.get("stop_reason") == "max_tokens"
                record["data"] = v2.tool_input(response, "submit_state")
                state = calculated_state(record["data"])
            except (RuntimeError, ValueError, KeyError, TypeError) as exc:
                record["error"] = type(exc).__name__
                # Retain last parseable state on a missing tool response; no source repair.
            self.save_record(record)
            if self.stop:
                break


def development_gate(out):
    calls = [c for c in v2.read_jsonl(out / "calls.jsonl") if c["case_id"].startswith("D")]
    problems = []
    if len(calls) != 80:
        problems.append("Expected 80 development calls")
    for c in calls:
        name = "submit_state" if c["arm"] != "confirmation" else (
            "submit_ledger" if c["stage"] == "one_call" else "submit_worksheet")
        try:
            v2.tool_input(c.get("response", {}), name)
        except (ValueError, KeyError, TypeError):
            problems.append("Missing or truncated tool response")
        if "cost_usd" not in c:
            problems.append("Unsettled request")
    return {"passed": not problems, "problems": problems,
            "rule": "Transport and finished tool objects only; no accuracy or fidelity gate"}


def collect(out, budget, phase):
    if not 0 < budget <= MAX_BUDGET:
        raise ValueError("Budget outside frozen bounds")
    manifest = json.loads((out / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if v1.digest(out / name) != expected:
            raise ValueError(f"Freeze hash mismatch: {name}")
    if v1.digest(Path(__file__)) != manifest["files"]["experiment.py"]:
        raise ValueError("Use the frozen runner")
    marker = out / f"collection.{phase}.started"
    if marker.exists():
        raise ValueError("Phase already attempted; no automatic repeat")
    collector = Collector(out, budget)
    if phase == "main":
        previous = v2.read_jsonl(out / "calls.jsonl")
        if not development_gate(out)["passed"] or any(not c["case_id"].startswith("D") for c in previous):
            raise ValueError("Main requires completed development phase")
        spend = json.loads((out / "spend.json").read_text())
        collector.actual = sum(c["cost_usd"] for c in previous)
        collector.committed = spend["committed_upper_usd"]
        if abs(collector.actual - collector.committed) > 1e-8:
            raise ValueError("Unsettled reservations")
    marker.write_text(str(time.time()))
    data = json.loads((out / "cases.json").read_text())
    is_dev = phase == "development"
    jobs = [("confirmation", c, None) for c in data["confirmation"]
            if c["case_id"].startswith("D") == is_dev]
    jobs.extend(("sequential", t, arm) for t in data["sequential"] if t["phase"] == phase for arm in ARMS)
    random.Random(SEEDS[phase + "_sequential"] + 1).shuffle(jobs)
    def task(job):
        kind, item, arm = job
        if kind == "confirmation":
            collector.confirmation(item)
        else:
            collector.sequential(item, arm)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(task, jobs))
    if phase == "development":
        gate = development_gate(out)
        v1.write_json(out / "development_gate.json", gate)
        print("Development gate:", v1.canonical(gate), flush=True)
        if not gate["passed"]:
            raise RuntimeError("Development infrastructure gate failed")
    if phase == "main":
        report(out)
    if collector.stop:
        raise RuntimeError("Collection halted; partial data preserved")


def score(record, case, gold):
    result = {"valid": False, "posterior_loss": 2.0, "future_loss": 1.0,
              "source_faithful": False}
    try:
        table = record["data"]
        answer = v2.calculate(table)
        result.update(valid=True, answer=answer,
                      posterior_loss=v1.squared_distance(answer["posterior"], gold["posterior"]),
                      future_loss=(answer["future_probability"] - gold["future_probability"]) ** 2,
                      max_probability_error=max(abs(answer["posterior"][h] - gold["posterior"][h])
                                                for h in v2.HIDS))
        result["source_diagnostic"] = v2.source_diagnostic(table, case)
        result["source_faithful"] = result["source_diagnostic"]["source_faithful"]
    except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        result["error"] = type(exc).__name__
    return result


def mean(rows, key):
    return statistics.mean(r[key] for r in rows) if rows else None


def metrics(rows):
    valid = [r for r in rows if r["valid"]]
    return {"n": len(rows), "valid": len(valid), "source_faithful": sum(r["source_faithful"] for r in rows),
            "mean_posterior_loss": mean(rows, "posterior_loss"),
            "mean_future_loss": mean(rows, "future_loss"),
            "valid_only_posterior_loss": mean(valid, "posterior_loss"),
            "within_half_percentage_point": sum(r.get("max_probability_error", 2) <= .005 for r in rows),
            "max_probability_error": max((r.get("max_probability_error", 2) for r in rows), default=None)}


def report(out):
    manifest = json.loads((out / "manifest.json").read_text())
    data = json.loads((out / "cases.json").read_text())
    truth = json.loads((out / "gold.json").read_text())
    raw = {}
    for r in v2.read_jsonl(out / "records.jsonl"):
        key = (r["case_id"], r["kind"], r.get("step"))
        if key in raw:
            raise ValueError("Duplicate record")
        raw[key] = r
    conf_gold = {g["case_id"]: g for g in truth["confirmation"]}
    seq_gold = {g["case_id"]: g for g in truth["sequential"]}
    scores, seq_scores = [], []
    for c in data["confirmation"]:
        for arm in ("one_call", "two_call"):
            r = score(raw.get((c["case_id"], arm, None), {}), c, conf_gold[c["case_id"]])
            scores.append(dict(r, case_id=c["case_id"], arm=arm, phase=conf_gold[c["case_id"]]["phase"]))
    for t in data["sequential"]:
        for arm in ARMS:
            previous = None
            for step, g in enumerate(seq_gold[t["case_id"]]["checkpoints"]):
                r = score(raw.get((t["case_id"], arm, step), {}), dossier_at(t, step), g)
                r.update(case_id=t["case_id"], phase=t["phase"], arm=arm, step=step, event=STEPS[step])
                if step and r["valid"] and previous["valid"]:
                    delta = {h: r["answer"]["posterior"][h] - previous["answer"]["posterior"][h]
                             for h in v2.HIDS}
                    previous_gold = seq_gold[t["case_id"]]["checkpoints"][step - 1]
                    target_delta = {h: g["posterior"][h] - previous_gold["posterior"][h] for h in v2.HIDS}
                    r.update(update_error=v1.squared_distance(delta, target_delta),
                             movement=sum(x * x for x in delta.values()),
                             change_in_loss=r["posterior_loss"] - previous["posterior_loss"])
                seq_scores.append(r)
                previous = r
    conf = [r for r in scores if r["phase"] == "main"]
    seq = [r for r in seq_scores if r["phase"] == "main"]
    ids = sorted({r["case_id"] for r in conf})
    idx = {(r["case_id"], r["arm"]): r for r in conf}
    delta = [idx[cid, "one_call"]["posterior_loss"] - idx[cid, "two_call"]["posterior_loss"] for cid in ids]
    comparison = v1.bootstrap_delta(delta)
    one = metrics([r for r in conf if r["arm"] == "one_call"])
    comparison["passes_prespecified_confirmation"] = (
        comparison["bootstrap_95_percentile_interval"][1] < .001
        and one["within_half_percentage_point"] / len(ids) >= .95
        and one["source_faithful"] / len(ids) >= .95)
    trajectories = []
    for cid in sorted({r["case_id"] for r in seq}):
        for arm in ARMS:
            rows = [r for r in seq if r["case_id"] == cid and r["arm"] == arm]
            trajectories.append({"case_id": cid, "arm": arm, "mean_loss": mean(rows, "posterior_loss"),
                                 "final_loss": rows[-1]["posterior_loss"],
                                 "all_source_faithful": all(r["source_faithful"] for r in rows),
                                 "all_valid": all(r["valid"] for r in rows)})
    ti = {(r["case_id"], r["arm"]): r for r in trajectories}
    tids = sorted({r["case_id"] for r in trajectories})
    comparisons = {}
    for label, a, b in (("primary_operator", "ledger_state", "checklist_state"),
                        ("state_retention_penalty", "ledger_state", "ledger_rebuild")):
        comparisons[label] = dict(first=a, second=b, **v1.bootstrap_delta([
            ti[cid, a]["mean_loss"] - ti[cid, b]["mean_loss"] for cid in tids]))
    arm_results = {}
    for arm in ARMS:
        rows = [r for r in seq if r["arm"] == arm]
        trajs = [r for r in trajectories if r["arm"] == arm]
        events = {}
        for event in ("initial", "new_study", "duplicate", "review"):
            subset = [r for r in rows if r["event"] == event]
            transitions = [r for r in subset if "update_error" in r]
            events[event] = dict(metrics(subset), valid_transitions=len(transitions),
                                 mean_update_error=mean(transitions, "update_error"),
                                 mean_movement=mean(transitions, "movement"),
                                 corrections=sum(r["change_in_loss"] < -1e-10 for r in transitions),
                                 degradations=sum(r["change_in_loss"] > 1e-10 for r in transitions))
        arm_results[arm] = dict(metrics(rows), all_source_faithful_trajectories=sum(
            t["all_source_faithful"] for t in trajs), all_valid_trajectories=sum(
                t["all_valid"] for t in trajs), final_mean_loss=mean(trajs, "final_loss"),
                by_step={str(s): metrics([r for r in rows if r["step"] == s]) for s in range(len(STEPS))},
                by_event=events)
    calls = v2.read_jsonl(out / "calls.jsonl")
    summary = {"version": VERSION, "calls": len(calls), "planned_calls": manifest["planned_calls"],
               "recorded_cost_usd": sum(c.get("cost_usd", 0) for c in calls),
               "unknown_cost_calls": sum("cost_usd" not in c for c in calls),
               "truncated_calls": sum(c.get("response", {}).get("stop_reason") == "max_tokens" for c in calls),
               "confirmation": {"one_call": one, "two_call": metrics([
                   r for r in conf if r["arm"] == "two_call"]), "paired_difference": comparison},
               "sequential": {"n_trajectories": len(tids), "steps": len(STEPS),
                              "arms": arm_results, "comparisons": comparisons},
               "cost_by_group": {arm: sum(c.get("cost_usd", 0) for c in calls if c["arm"] == arm
                                          and not c["case_id"].startswith("D"))
                                 for arm in ("confirmation", *ARMS)},
               "confirmation_one_call_cost": sum(c.get("cost_usd", 0) for c in calls
                   if c["case_id"].startswith("CON") and c["stage"] == "one_call"),
               "cost_development": sum(c.get("cost_usd", 0) for c in calls if c["case_id"].startswith("D"))}
    v1.write_json(out / "scores.json", {"confirmation": scores, "sequential": seq_scores,
                                       "trajectory_means": trajectories})
    v1.write_json(out / "summary.json", summary)
    lines = ["# Scientific confidence v3: frozen results", "",
             f"Calls: {len(calls)}/{manifest['planned_calls']}; cost ${summary['recorded_cost_usd']:.6f}.",
             f"Truncated: {summary['truncated_calls']}; unknown cost: {summary['unknown_cost_calls']}.", "",
             "## Fresh one-call confirmation", "", "```json", json.dumps(summary["confirmation"], indent=2),
             "```", "", "## Sequential evidence state", "",
             "| Arm | Valid checkpoints | Source-faithful | Mean posterior loss | Final loss |",
             "|---|---:|---:|---:|---:|"]
    for arm, r in arm_results.items():
        lines.append(f"| {arm} | {r['valid']}/{r['n']} | {r['source_faithful']}/{r['n']} | "
                     f"{r['mean_posterior_loss']:.8g} | {r['final_mean_loss']:.8g} |")
    lines += ["", "Paired comparisons use independent trajectory means, not checkpoints as replicates.",
              "", "```json", json.dumps(comparisons, indent=2), "```", "",
              "See PROTOCOL.md for frozen hypotheses and limitations. Model class is supplied and correct."]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: summary[k] for k in ("calls", "recorded_cost_usd", "truncated_calls")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "collect", "report"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--confirmations", type=int, default=64)
    parser.add_argument("--trajectories", type=int, default=32)
    parser.add_argument("--budget-usd", type=float, default=MAX_BUDGET)
    parser.add_argument("--phase", choices=("development", "main"), default="development")
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.out, args.confirmations, args.trajectories)
    elif args.command == "collect":
        collect(args.out, args.budget_usd, args.phase)
    else:
        report(args.out)


if __name__ == "__main__":
    main()
