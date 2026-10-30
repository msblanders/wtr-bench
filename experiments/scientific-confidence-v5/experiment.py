"""Matched verified-start test of evidence retention and reinstatement."""
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
SPEC = importlib.util.spec_from_file_location("confidence_v5_support", SUPPORT)
assert SPEC and SPEC.loader
v2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v2)
v1 = v2.v1
VERSION = "scientific-confidence-v5"
SEEDS = {"development": 90691203, "main": 20691203}
ARMS = ("active_checklist", "versioned_checklist")
EVENTS = ("initial", "alias_duplicate", "numeric_correction", "new_cohort",
          "stale_superseded", "withdrawal", "scope_correction", "stale_withdrawn",
          "new_study", "partial_withdrawal", "reinstatement",
          "post_reinstatement_correction", "second_withdrawal", "review")
PAID_STEPS = tuple(range(1, len(EVENTS)))
POST_STEPS = (10, 11, 12, 13)
MAX_BUDGET = 80
HIDS = v2.HIDS
ROW_FIELDS = ("study_id", "design", "context", "estimate", "se", "predicted_means")
TASK = """Maintain scientific evidence under the following stipulated reporting rules.
The supplied hypotheses are mutually exclusive and exhaustive. Conditional on a hypothesis,
each currently authoritative evidence unit is an independent Normal estimate with its stated SE.
The reference probability is calculated from ORIGINAL priors and the CURRENT ACTIVE data only.
This task is about the current authoritative record, not inference about why reporting errors occurred.
Corrections replace earlier values for that unit; they are not independent observations.
Withdrawn units contribute no likelihood. A withdrawal notice itself is not evidence for any hypothesis.
An authorized reinstatement can make a later revision active again. Reprints, aliases, and later
publication dates do not by themselves reverse a correction or a withdrawal.
A registry can contain multiple explicitly disjoint cohorts. They are distinct independent evidence
units. Reports of the same registry/cohort describe one unit, however their names or document IDs differ.
Use study_id = registry/cohort (exactly as first supplied). A scope correction changes which
design/context-specific prediction applies; a subgroup-only withdrawal does not withdraw other cohorts.
For each hypothesis: log weight = log(original prior) - 0.5*sum(((estimate-mean)/SE)^2) over
active unique units. The fixed future study is independent; its probability is the posterior-weighted
Normal probability of exceeding its threshold. A source-blind calculator handles this arithmetic.
Do not calculate probabilities yourself. Return the evidence state using submit_state.
"""
CHECKLIST = (
    "Maintain a calibrated evidence assessment. Consider every alternative, prior rates, "
    "study quality and precision, conflicting evidence, and dependence between sources. "
    "Review the available material carefully and update the record for the evidence now authoritative."
)
COMMON = (
    "Return priors, entries, future_study, and evidence_basis. Each entry has a canonical study_id, "
    "integer revision, status (active, superseded, withdrawn), identity_refs, design, context, estimate, "
    "SE, and predicted_means for H1/H2/H3. identity_refs can retain document IDs and project aliases "
    "that identify the same unit, including old references after a correction. At most one active "
    "entry per canonical unit is allowed. Keep at least six decimal places for non-simple source "
    "numbers. Keep evidence_basis at most 120 words; it may retain useful provenance for future updates. "
    "The next call receives only your returned state, derived calculator beliefs, the fixed model "
    "specification and the new packet, not the original historical documents."
)
RETENTION = {
    "active_checklist": (
        "Working-record policy: output current ACTIVE entries only. Historical information may be "
        "retained in identity_refs for active units and in evidence_basis; do not output inactive rows."
    ),
    "versioned_checklist": (
        "Working-record policy: retain ALL known revisions, including superseded and withdrawn "
        "entries, alongside current active entries. A unit-wide withdrawal marks all its revisions "
        "withdrawn; reinstatement leaves those old entries withdrawn and adds the authorized active revision."
    ),
}


def schema():
    base = copy.deepcopy(v2.worksheet_schema())
    row = base["properties"].pop("studies")["items"]
    row["properties"].update(
        revision={"type": "integer", "minimum": 1},
        status={"type": "string", "enum": ["active", "superseded", "withdrawn"]},
        identity_refs={"type": "array", "items": {"type": "string"}, "maxItems": 32})
    row["required"] += ["revision", "status", "identity_refs"]
    base["required"].remove("studies")
    base["properties"]["entries"] = {"type": "array", "items": row, "minItems": 1, "maxItems": 32}
    base["properties"]["evidence_basis"] = {"type": "string"}
    base["required"] += ["entries", "evidence_basis"]
    return base


def calculate(state):
    """No source access, revision selection, status repair, or alias resolution."""
    entries = state["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
        raise ValueError("Invalid entries")
    active, seen = [], set()
    for row in entries:
        if row["status"] not in ("active", "superseded", "withdrawn"):
            raise ValueError("Unknown status")
        if type(row["revision"]) is not int or row["revision"] < 1:
            raise ValueError("Invalid revision")
        if row["status"] == "active":
            if row["study_id"] in seen:
                raise ValueError("Multiple active revisions")
            seen.add(row["study_id"])
            active.append({k: row[k] for k in ROW_FIELDS})
    return v2.calculate({"priors": state["priors"], "studies": active,
                         "future_study": state["future_study"]})


def n(x):
    return format(x, ".12g")


def means(hypotheses, row):
    return {h["id"]: v1.mean_for(h, row["design"], row["context"]) for h in hypotheses}


def active_case(state, hypotheses):
    return {"hypotheses": hypotheses, "future_study": {
        k: state["future_study"][k] for k in ("design", "context", "se", "threshold")},
        "reports": [{k: row[k] for k in ("study_id", "design", "context", "estimate", "se")}
                    for row in state["entries"] if row["status"] == "active"]}


def make_cases(phase, count):
    cases, old_gold = v1.make_cases(count, seed=SEEDS[phase])
    output, gold = [], []
    names = ["Juniper", "Cobalt", "Harbor", "Orchid", "Summit", "Willow", "Maple", "Copper"]
    for i, (case, previous_truth) in enumerate(zip(cases, old_gold)):
        cid = ("DEV" if phase == "development" else "TEST") + f"{i:03d}"
        rng = random.Random(SEEDS[phase] + 7919 * i + 40000000)
        labels = rng.sample(names, 4)
        registries = rng.sample(range(1000, 9999), 4)
        ids = [f"RG-{r}/main" for r in registries]
        subgroup = f"RG-{registries[1]}/cohort-b"
        hs = case["hypotheses"]
        true_h = next(h for h in hs if h["id"] == previous_truth["true_h"])
        originals = sorted(v1.unique_studies(case), key=lambda s: s["study_id"])[:3]
        entries, packets, checkpoints = [], [], []

        def create(sid, source, label, study, revision=1, hs=hs):
            row = {k: study[k] for k in ("design", "context", "estimate", "se")}
            row["estimate"] = float(n(row["estimate"]))
            return dict(row, study_id=sid, revision=revision, status="active",
                        identity_refs=[source, label], predicted_means=means(hs, row))

        def describe(row):
            return (f"{row['design']} design, context {row['context']}, effect estimate "
                    f"{n(row['estimate'])}, standard error {n(row['se'])}")

        def take(kind, packet, packets=packets, entries=entries, hs=hs,
                 case=case, checkpoints=checkpoints):
            step = len(packets)
            packets.append({"step": step, "kind": kind, "packet": packet})
            state = {"priors": {h["id"]: h["prior"] for h in hs},
                     "entries": copy.deepcopy(entries),
                     "future_study": dict(case["future_study"], predicted_means=means(hs, case["future_study"])),
                     "evidence_basis": "Reference state; evaluator only."}
            checkpoints.append({"step": step, "event": kind, "state": state,
                                **v1.oracle(active_case(state, hs))})

        initial = []
        for j, study in enumerate(originals):
            row = create(ids[j], f"D{j + 1}", labels[j], study)
            entries.append(row)
            registry, cohort = ids[j].split("/")
            initial.append(f"Document D{j + 1}, project {labels[j]}. Registry {registry}; cohort {cohort}. "
                           f"Revision 1: {describe(row)}. These three units use distinct participants.")
        take("initial", "\n".join(initial))

        alias = labels[0] + " Follow-up"
        entries[0]["identity_refs"] += ["D4", alias]
        forms = [
            (f"Document D4 is titled {alias}. Its methods identify exactly the participants and analysis "
            f"published in D1. It republishes revision 1 unchanged: {describe(entries[0])}. No new observations."),
            (f"The bulletin D4 ({alias}) reproduces D1's original revision-1 estimate, with no new sample "
            f"or analysis: {describe(entries[0])}. Both project names refer to the same evidence unit."),
        ]
        take("alias_duplicate", forms[i % 2])

        old = entries[0]
        old["status"] = "superseded"
        corrected_study = {k: old[k] for k in ("design", "context")}
        corrected_study["se"] = rng.choice([0.2, 0.35, 0.5])
        corrected_study["estimate"] = rng.gauss(v1.mean_for(true_h, old["design"], old["context"]),
                                               corrected_study["se"])
        corrected = create(ids[0], "D5", alias, corrected_study, 2)
        corrected["identity_refs"] += ["D1", "D4", labels[0]]
        entries.append(corrected)
        take("numeric_correction", f"Authoritative correction D5 for the evidence reported in D4/D1 "
             f"({alias}), revision 2. A transcription error affected the reported estimate and SE. "
             f"The authoritative values are now {describe(corrected)}. Revision 1 is superseded; "
             "revision 2 replaces it for the same participants, not a replication.")

        sub_study = {"design": originals[1]["design"], "context": "A", "se": rng.choice([0.25, 0.4, 0.6])}
        sub_study["estimate"] = rng.gauss(v1.mean_for(true_h, sub_study["design"], "B"), sub_study["se"])
        subrow = create(subgroup, "D6", labels[1] + " Extension", sub_study)
        entries.append(subrow)
        take("new_cohort", f"Document D6: {labels[1]} Extension, registry RG-{registries[1]}, "
             f"cohort cohort-b, revision 1. This separately enrolled cohort has NO participants in "
             f"common with the main cohort in D2. It is an independent evidence unit, despite the "
             f"shared registry/project: {describe(subrow)}.")

        take("stale_superseded", f"Document D7, newly published digest of {alias}, reproduces the "
             f"original revision-1 analysis from D4: {describe(old)}. The digest contains no new "
             "data, correction or reinstatement. Its publication date is later than D5.")

        for r in entries:
            if r["study_id"] == ids[0]:
                r["status"] = "withdrawn"
        take("withdrawal", "Authoritative notice D8 withdraws ALL revisions of the single evidence "
             "unit described in D5, including its earlier D1/D4 reports. Those values are no longer "
             "eligible for inference. No other unit or cohort is withdrawn.")

        subrow["status"] = "superseded"
        scopefix = copy.deepcopy(subrow)
        scopefix.update(revision=2, status="active", context="B")
        scopefix["predicted_means"] = means(hs, scopefix)
        scopefix["identity_refs"] += ["D9"]
        entries.append(scopefix)
        take("scope_correction", f"Authoritative scope correction D9 to D6 ({labels[1]} Extension), "
             "revision 2: the separately enrolled cohort-b consists of context-B participants, NOT "
             f"context-A participants. Its numerical estimate and SE are unchanged: "
             f"{n(scopefix['estimate'])} and {n(scopefix['se'])}. The design remains "
             f"{scopefix['design']}. This corrects D6; it adds no participants. D2's main cohort is unchanged.")

        take("stale_withdrawn", f"Document D10, titled {labels[0]} Revisited, reprints D5's revision-2 "
             f"results ({describe(corrected)}) and cites D1 and D4 as the same unit. It supplies no "
             "new data and is NOT an authorized reinstatement; the withdrawal notice remains in force.")

        fresh = {"design": "randomized", "context": rng.choice(["A", "B"]), "se": rng.choice([0.3, 0.5])}
        fresh["estimate"] = rng.gauss(v1.mean_for(true_h, fresh["design"], fresh["context"]), fresh["se"])
        freshrow = create(ids[3], "D11", labels[0] + " Revisited", fresh)
        entries.append(freshrow)
        take("new_study", f"Document D11, project {labels[0]} Revisited. Registry RG-{registries[3]}, "
             f"cohort main, revision 1. Newly enrolled participants are disjoint from all previous "
             f"units, including those discussed in D10: {describe(freshrow)}.")

        for r in entries:
            if r["study_id"] == subgroup:
                r["status"] = "withdrawn"
        take("partial_withdrawal", f"Authoritative notice D12 withdraws only cohort-b in registry "
             f"RG-{registries[1]} (D6, corrected by D9), all revisions. The main cohort in D2 "
             "remains valid, as do all other units not already withdrawn.")

        reinstated = copy.deepcopy(corrected)
        reinstated.update(revision=3, status="active")
        reinstated["identity_refs"] += ["D13", labels[0] + " Restored"]
        reinstated["estimate"] = float(n(corrected["estimate"] + rng.choice([-.15, .15])))
        entries.append(reinstated)
        take("reinstatement", f"Authoritative reinstatement D13, {labels[0]} Restored: the unit in "
             f"D1/D4/D5 is reinstated ONLY as revision 3 with {describe(reinstated)}. These values "
             "supersede the withdrawn reports for that same unit. Old revisions remain withdrawn; "
             "this is not a new independent sample. D12's separate withdrawal remains in force.")
        reinstated["status"] = "superseded"
        finalfix = copy.deepcopy(reinstated)
        finalfix.update(revision=4, status="active", estimate=rng.choice([-.6, 0., .6]), se=.25)
        finalfix["identity_refs"] += ["D14"]
        entries.append(finalfix)
        registry, cohort = ids[0].split("/")
        take("post_reinstatement_correction", f"Authoritative correction D14, registry {registry}, "
             f"cohort {cohort}, revision 4. A re-audit corrects the reinstated revision 3 in D13. "
             f"The authoritative result is {describe(finalfix)}. Revision 4 replaces revision 3 "
             "for exactly the same participants; it is NOT an independent observation. Earlier "
             "withdrawn revisions remain withdrawn. Other registries and cohorts are unchanged.")
        for r in entries:
            if r["study_id"] == ids[0]:
                r["status"] = "withdrawn"
        take("second_withdrawal", f"Authoritative notice D15 withdraws ALL revisions of registry "
             f"{registry}, cohort {cohort}. This unit no longer contributes evidence. This notice "
             "changes no other registry or cohort and does not reinstate any other withdrawn unit.")
        take("review", "No new documents or observations. Review the current record for correctness.")
        assert tuple(p["kind"] for p in packets) == EVENTS
        starting_record = copy.deepcopy(checkpoints[0]["state"])
        starting_record["evidence_basis"] = "Verified initial record: three independent active units; original priors and future-study specification."
        starting_state = {"record": starting_record, "derived_beliefs": calculate(starting_record)}
        assert starting_state["derived_beliefs"] == v1.oracle(active_case(starting_record, hs))
        output.append({"initial_state": starting_state, "case_id": cid, "phase": phase, "hypotheses": hs,
                       "future_study": case["future_study"], "events": packets})
        gold.append({"case_id": cid, "phase": phase, "stratum": previous_truth["stratum"],
                     "checkpoints": checkpoints})
    return output, gold


def payload(case, step, arm, state):
    if step not in PAID_STEPS or arm not in ARMS:
        raise ValueError("Unknown paid step or arm")
    spec = {"hypotheses": case["hypotheses"], "future_study": case["future_study"]}
    instruction = CHECKLIST
    content = (TASK + "\nModel specification:\n" + v1.canonical(spec)
               + f"\nCase {case['case_id']}; update {step}.\n"
               + "Previous working state (not an observation; the initial record was independently verified):\n" + v1.canonical(state)
               + "\nIncoming packet:\n" + case["events"][step]["packet"]
               + "\n" + COMMON + "\n" + RETENTION[arm] + "\n" + instruction)
    return {"model": v1.MODEL, "max_tokens": v2.TOKENS, "temperature": 0,
            "thinking": {"type": "disabled"}, "system": v1.SYSTEM,
            "messages": [{"role": "user", "content": content}],
            "tools": [{"name": "submit_state", "description": "Submit the maintained evidence record.",
                       "input_schema": schema()}],
            "tool_choice": {"type": "tool", "name": "submit_state"}}


def generate(out, count=64):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite freeze")
    if count < 1:
        raise ValueError("Positive sample size required")
    out.mkdir(parents=True, exist_ok=True)
    cases, gold = [], []
    for phase, size in (("development", 2), ("main", count)):
        c, g = make_cases(phase, size)
        cases.extend(c)
        gold.extend(g)
    v1.write_json(out / "cases.json", cases)
    v1.write_json(out / "gold.json", gold)
    shutil.copyfile(__file__, out / "experiment.py")
    shutil.copyfile(SUPPORT, out / "v2_support.py")
    shutil.copyfile(v2.SUPPORT, out / "v1_support.py")
    shutil.copyfile(HERE / "README.md", out / "PROTOCOL.md")
    v1.write_json(out / "manifest.json", {
        "version": VERSION, "seeds": SEEDS, "model": v1.MODEL, "tokens": v2.TOKENS,
        "main_trajectories": count, "development_trajectories": 2, "steps": list(EVENTS),
        "arms": list(ARMS), "paid_steps": list(PAID_STEPS), "post_steps": list(POST_STEPS),
        "planned_calls": (count + 2) * len(ARMS) * len(PAID_STEPS),
        "max_budget_usd": MAX_BUDGET,
        "primary": "versioned_checklist minus active_checklist: post-reinstatement active-state failure fraction",
        "files": {p.name: v1.digest(p) for p in sorted(out.iterdir()) if p.is_file()}})
    print("Frozen provenance experiment.", flush=True)


class Collector(v2.Collector):
    def trajectory(self, case, arm):
        state = copy.deepcopy(case["initial_state"])
        for step in PAID_STEPS:
            rec = {"case_id": case["case_id"], "kind": arm, "step": step, "event": EVENTS[step]}
            try:
                response = self.call(case["case_id"], arm, str(step), payload(case, step, arm, state))
                rec["truncated"] = response.get("stop_reason") == "max_tokens"
                rec["data"] = v2.tool_input(response, "submit_state")
                try:
                    derived = calculate(rec["data"])
                except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
                    derived = {"error": type(exc).__name__}
                state = {"record": rec["data"], "derived_beliefs": derived}
            except (RuntimeError, ValueError, KeyError, TypeError) as exc:
                rec["error"] = type(exc).__name__
            self.save_record(rec)
            if self.stop:
                break


def gate(out):
    calls = [c for c in v2.read_jsonl(out / "calls.jsonl") if c["case_id"].startswith("DEV")]
    problems = []
    if len(calls) != 2 * len(ARMS) * len(PAID_STEPS):
        problems.append("Expected 52 development calls")
    keys = {(c["case_id"], c["arm"], c["stage"]) for c in calls}
    expected = {(f"DEV{i:03d}", arm, str(step)) for i in range(2) for arm in ARMS for step in PAID_STEPS}
    if keys != expected or len(keys) != len(calls):
        problems.append("Missing, duplicate or unexpected development call keys")
    for c in calls:
        try:
            v2.tool_input(c.get("response", {}), "submit_state")
        except (ValueError, KeyError, TypeError):
            problems.append("Missing or unfinished tool response")
        if "cost_usd" not in c:
            problems.append("Unsettled request")
    return {"passed": not problems, "problems": problems,
            "rule": "Transport, finished tool responses, and settled usage only; no accuracy gate"}


def collect(out, budget, phase):
    if not 0 < budget <= MAX_BUDGET:
        raise ValueError("Budget outside frozen ceiling")
    manifest = json.loads((out / "manifest.json").read_text())
    for name, expected in manifest["files"].items():
        if v1.digest(out / name) != expected:
            raise ValueError("Freeze mismatch: " + name)
    if v1.digest(Path(__file__)) != manifest["files"]["experiment.py"]:
        raise ValueError("Use frozen runner")
    marker = out / f"collection.{phase}.started"
    if marker.exists():
        raise ValueError("Phase already attempted")
    collector = Collector(out, budget)
    if phase == "main":
        previous = v2.read_jsonl(out / "calls.jsonl")
        if not gate(out)["passed"] or any(not c["case_id"].startswith("DEV") for c in previous):
            raise ValueError("Clean development phase required")
        collector.actual = sum(c["cost_usd"] for c in previous)
        collector.committed = json.loads((out / "spend.json").read_text())["committed_upper_usd"]
        if abs(collector.actual - collector.committed) > 1e-8:
            raise ValueError("Unsettled reservation")
    marker.write_text(str(time.time()))
    cases = json.loads((out / "cases.json").read_text())
    jobs = [(c, arm) for c in cases if c["phase"] == phase for arm in ARMS]
    random.Random(SEEDS[phase] + 1).shuffle(jobs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda j: collector.trajectory(*j), jobs))
    if phase == "development":
        g = gate(out)
        v1.write_json(out / "development_gate.json", g)
        print("Development gate:", v1.canonical(g), flush=True)
        if not g["passed"]:
            raise RuntimeError("Development transport gate failed")
    if phase == "main":
        report(out)
    if collector.stop:
        raise RuntimeError("Collection stopped; partial records preserved")


def state_diagnostic(state, gold, hypotheses):
    expected, observed = gold["state"], state
    active = [r for r in observed["entries"] if r["status"] == "active"]
    wanted = [r for r in expected["entries"] if r["status"] == "active"]
    got = {r["study_id"]: r for r in active}
    want = {r["study_id"]: r for r in wanted}
    problems = []
    if set(want) - set(got):
        problems.append("missing_active_unit")
    if set(got) - set(want):
        problems.append("extra_active_unit")
    if len(got) != len(active):
        problems.append("multiple_active_versions")
    for sid in set(got) & set(want):
        a, b = got[sid], want[sid]
        if a["revision"] != b["revision"]:
            problems.append("wrong_active_revision")
        if a["design"] != b["design"] or a["context"] != b["context"]:
            problems.append("wrong_scope")
        if any(abs(a[k] - b[k]) > 1e-5 for k in ("estimate", "se")):
            problems.append("wrong_active_values")
        if any(abs(a["predicted_means"][h] - b["predicted_means"][h]) > 1e-8 for h in HIDS):
            problems.append("wrong_prediction_mapping")
    old = {(r["study_id"], r["revision"]): r for r in expected["entries"] if r["status"] != "active"}
    if any((r["study_id"], r["revision"]) in old for r in active):
        problems.append("inactive_revision_reactivated")
    if any(abs(observed["priors"][h] - expected["priors"][h]) > 1e-5 for h in HIDS):
        problems.append("wrong_original_prior")
    future = observed["future_study"]
    target = expected["future_study"]
    if (any(future[k] != target[k] for k in ("design", "context"))
            or any(abs(future[k] - target[k]) > 1e-5 for k in ("se", "threshold"))
            or any(abs(future["predicted_means"][h] - target["predicted_means"][h]) > 1e-8 for h in HIDS)):
        problems.append("wrong_future_parameters")
    history = {(r["study_id"], r["revision"]): r for r in observed["entries"]}
    reference = {(r["study_id"], r["revision"]): r for r in expected["entries"]}
    full_ok = len(history) == len(observed["entries"]) and set(history) == set(reference)
    for key in set(history) & set(reference):
        a, b = history[key], reference[key]
        full_ok &= all(a[k] == b[k] for k in ("status", "design", "context"))
        full_ok &= all(abs(a[k] - b[k]) <= 1e-5 for k in ("estimate", "se"))
        full_ok &= all(abs(a["predicted_means"][h] - b["predicted_means"][h]) <= 1e-8 for h in HIDS)
    return {"active_source_faithful": not problems, "problems": sorted(set(problems)),
            "full_revision_history_faithful": bool(full_ok)}


def score(rec, checkpoint, case):
    row = {"valid": False, "posterior_loss": 2.0, "future_loss": 1.0,
           "active_source_faithful": False, "full_revision_history_faithful": False,
           "problems": ["invalid_or_missing"]}
    try:
        state = rec["data"]
        answer = calculate(state)
        row.update(valid=True, answer=answer,
                   posterior_loss=v1.squared_distance(answer["posterior"], checkpoint["posterior"]),
                   future_loss=(answer["future_probability"] - checkpoint["future_probability"]) ** 2,
                   max_probability_error=max(abs(answer["posterior"][h] - checkpoint["posterior"][h]) for h in HIDS))
        row.update(state_diagnostic(state, checkpoint, case["hypotheses"]))
    except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        row["error"] = type(exc).__name__
    return row


def avg(rows, key):
    return statistics.mean(r[key] for r in rows) if rows else None


def metrics(rows):
    return {"n": len(rows), "valid": sum(r["valid"] for r in rows),
            "active_source_faithful": sum(r["active_source_faithful"] for r in rows),
            "full_revision_history_faithful": sum(r["full_revision_history_faithful"] for r in rows),
            "mean_posterior_loss": avg(rows, "posterior_loss"),
            "mean_future_loss": avg(rows, "future_loss"),
            "valid_only_posterior_loss": avg([r for r in rows if r["valid"]], "posterior_loss"),
            "within_half_percentage_point": sum(r.get("max_probability_error", 2) <= .005 for r in rows),
            "max_probability_error": max((r.get("max_probability_error", 2) for r in rows), default=None)}


def paired_comparison(values):
    result = v1.bootstrap_delta(values, seed=SEEDS["main"] + 2)
    absolute = sum(abs(x) for x in values)
    result.update(
        lower_loss_trajectories=sum(x < -1e-8 for x in values),
        higher_loss_trajectories=sum(x > 1e-8 for x in values),
        negligible_difference_trajectories=sum(abs(x) <= 1e-8 for x in values),
        largest_absolute_share=max((abs(x) for x in values), default=0) / absolute if absolute else 0,
        leave_one_out_mean_range=[min((sum(values) - x) / (len(values) - 1) for x in values),
                                  max((sum(values) - x) / (len(values) - 1) for x in values)]
        if len(values) > 1 else None)
    return result


def report(out):
    manifest = json.loads((out / "manifest.json").read_text())
    frozen_hashes_match = all(v1.digest(out / name) == sha for name, sha in manifest["files"].items())
    if not frozen_hashes_match:
        raise ValueError("Frozen file changed")
    cases = json.loads((out / "cases.json").read_text())
    gold = {g["case_id"]: g for g in json.loads((out / "gold.json").read_text())}
    records = {}
    for rec in v2.read_jsonl(out / "records.jsonl"):
        key = rec["case_id"], rec["kind"], rec["step"]
        if key in records:
            raise ValueError("Duplicate record")
        records[key] = rec
    scores, trajectories, failures = [], [], []
    starting_states_verified = True
    for case in cases:
        cps = gold[case["case_id"]]["checkpoints"]
        initial = case["initial_state"]
        starting_states_verified &= state_diagnostic(initial["record"], cps[0], case["hypotheses"])["active_source_faithful"]
        starting_states_verified &= initial["derived_beliefs"] == calculate(initial["record"])
        for arm in ARMS:
            prior = {"valid": True, "answer": initial["derived_beliefs"], "posterior_loss": 0.0,
                     "active_source_faithful": True}
            part = []
            for step in PAID_STEPS:
                checkpoint = cps[step]
                rec = records.get((case["case_id"], arm, step), {})
                row = score(rec, checkpoint, case)
                row.update(case_id=case["case_id"], phase=case["phase"], arm=arm,
                           step=step, event=EVENTS[step], active_failure=int(not row["active_source_faithful"]),
                           newly_unfaithful=prior["active_source_faithful"] and not row["active_source_faithful"],
                           recovered=not prior["active_source_faithful"] and row["active_source_faithful"])
                if row["valid"] and prior["valid"]:
                    delta = {h: row["answer"]["posterior"][h] - prior["answer"]["posterior"][h] for h in HIDS}
                    target = {h: checkpoint["posterior"][h] - cps[step - 1]["posterior"][h] for h in HIDS}
                    row.update(update_error=v1.squared_distance(delta, target),
                               movement=sum(x * x for x in delta.values()))
                if "data" in rec and isinstance(rec["data"].get("entries"), list):
                    entries = rec["data"]["entries"]
                    row["retained_rows"] = len(entries)
                    row["inactive_rows"] = sum(r.get("status") != "active" for r in entries)
                    row["note_words"] = len(str(rec["data"].get("evidence_basis", "")).split())
                scores.append(row)
                part.append(row)
                if case["phase"] == "main" and not row["active_source_faithful"]:
                    failures.append({"score": row, "returned_state": rec.get("data"), "reference": checkpoint})
                prior = row
            post = [r for r in part if r["step"] in POST_STEPS]
            trajectories.append({"case_id": case["case_id"], "phase": case["phase"], "arm": arm,
                                 "post_failure_fraction": avg(post, "active_failure"),
                                 "post_mean_loss": avg(post, "posterior_loss"),
                                 "mean_loss": avg(part, "posterior_loss"),
                                 "post_mean_future_loss": avg(post, "future_loss"),
                                 "final_loss": part[-1]["posterior_loss"],
                                 "all_active_faithful": all(r["active_source_faithful"] for r in part),
                                 "all_post_faithful": all(r["active_source_faithful"] for r in post),
                                 "first_error_step": next((r["step"] for r in part if r["active_failure"]), None)})
    main = [r for r in scores if r["phase"] == "main"]
    traj = [r for r in trajectories if r["phase"] == "main"]
    idx = {(r["case_id"], r["arm"]): r for r in traj}
    ids = sorted({r["case_id"] for r in traj})
    comparisons = {}
    for label, metric in (("primary_post_active_failure", "post_failure_fraction"),
                          ("secondary_post_posterior_loss", "post_mean_loss"),
                          ("secondary_all_posterior_loss", "mean_loss"),
                          ("secondary_post_future_loss", "post_mean_future_loss")):
        comparisons[label] = dict(first="versioned_checklist", second="active_checklist", metric=metric,
            **paired_comparison([idx[cid, "versioned_checklist"][metric] - idx[cid, "active_checklist"][metric]
                                 for cid in ids]))
    conditions = {}
    for arm in ARMS:
        rows = [r for r in main if r["arm"] == arm]
        part = [r for r in traj if r["arm"] == arm]
        post = [r for r in rows if r["step"] in POST_STEPS]
        by_event = {}
        for step in PAID_STEPS:
            subset = [r for r in rows if r["step"] == step]
            transitions = [r for r in subset if "update_error" in r]
            by_event[EVENTS[step]] = dict(metrics(subset),
                newly_unfaithful=sum(r["newly_unfaithful"] for r in subset),
                recovered=sum(r["recovered"] for r in subset),
                mean_update_error=avg(transitions, "update_error"))
        conditions[arm] = dict(metrics(rows), post_reinstatement=metrics(post),
            post_failure_fraction=avg(part, "post_failure_fraction"),
            all_active_faithful_trajectories=sum(r["all_active_faithful"] for r in part),
            all_post_faithful_trajectories=sum(r["all_post_faithful"] for r in part),
            first_error_step_counts={str(step): sum(r["first_error_step"] == step for r in part)
                                     for step in PAID_STEPS if any(r["first_error_step"] == step for r in part)},
            problem_counts={p: sum(p in r["problems"] for r in rows) for p in sorted({p for r in rows for p in r["problems"]})},
            retention={"mean_rows": avg([r for r in rows if "retained_rows" in r], "retained_rows"),
                       "outputs_with_inactive_rows": sum(r.get("inactive_rows", 0) > 0 for r in rows),
                       "notes_over_120_words": sum(r.get("note_words", 0) > 120 for r in rows)},
            by_event=by_event)
    calls = v2.read_jsonl(out / "calls.jsonl")
    call_keys = [(c["case_id"], c["arm"], int(c["stage"])) for c in calls]
    expected_keys = {(c["case_id"], arm, step) for c in cases for arm in ARMS for step in PAID_STEPS}
    if len(set(call_keys)) != len(call_keys) or set(call_keys) - expected_keys or set(records) - expected_keys:
        raise ValueError("Duplicate or unexpected call/record")
    neutral = ("alias_duplicate", "stale_superseded", "stale_withdrawn", "review")
    changes = {event: [] for event in EVENTS[1:] if event not in neutral}
    for case in cases:
        if case["phase"] != "main":
            continue
        cps = gold[case["case_id"]]["checkpoints"]
        for step in PAID_STEPS:
            if EVENTS[step] in changes:
                changes[EVENTS[step]].append(max(abs(cps[step]["posterior"][h] - cps[step - 1]["posterior"][h]) for h in HIDS))
    summary = {"version": VERSION, "calls": len(calls), "planned_calls": manifest["planned_calls"],
        "complete_call_and_record_keys": set(call_keys) == expected_keys == set(records),
        "frozen_hashes_match": frozen_hashes_match, "starting_states_verified": bool(starting_states_verified),
        "recorded_cost_usd": sum(c.get("cost_usd", 0) for c in calls),
        "unknown_cost_calls": sum("cost_usd" not in c for c in calls),
        "truncated_calls": sum(c.get("response", {}).get("stop_reason") == "max_tokens" for c in calls),
        "n_trajectories": len(ids), "paid_steps": len(PAID_STEPS), "post_steps": list(POST_STEPS),
        "conditions": conditions, "comparisons": comparisons,
        "target_update_sensitivity": {event: {"n": len(xs), "shift_at_least_5pp": sum(x >= .05 for x in xs),
                                             "mean_max_probability_shift": statistics.mean(xs)} for event, xs in changes.items()},
        "cost_by_arm_main": {a: sum(c.get("cost_usd", 0) for c in calls if c["arm"] == a and c["case_id"].startswith("TEST")) for a in ARMS},
        "cost_development": sum(c.get("cost_usd", 0) for c in calls if c["case_id"].startswith("DEV")),
        "tokens": {k: sum(c.get("response", {}).get("usage", {}).get(k, 0) for c in calls) for k in ("input_tokens", "output_tokens")}}
    v1.write_json(out / "scores.json", scores)
    v1.write_json(out / "trajectory_means.json", trajectories)
    v1.write_json(out / "failure_audit.json", failures)
    v1.write_json(out / "summary.json", summary)
    lines = ["# Scientific confidence v5: verified-start results", "",
             f"Calls {len(calls)}/{manifest['planned_calls']}; cost ${summary['recorded_cost_usd']:.6f}.", "",
             "| Condition | Faithful active states | Faithful post-reinstatement states | Post failure fraction | Post posterior loss |",
             "|---|---:|---:|---:|---:|"]
    for arm, result in conditions.items():
        post = result["post_reinstatement"]
        lines.append(f"| {arm} | {result['active_source_faithful']}/{result['n']} | "
                     f"{post['active_source_faithful']}/{post['n']} | {result['post_failure_fraction']:.6g} | "
                     f"{post['mean_posterior_loss']:.8g} |")
    lines += ["", "The primary endpoint is the four-checkpoint failure fraction after reinstatement.",
              f"Intervals resample {len(ids)} paired trajectories, not individual checkpoints.",
              "Initial records are identical and verified; later records are never corrected by the evaluator.",
              "This is current-authoritative-record consistency, not calibration over a publication process.",
              "Incomplete infrastructure runs are not efficacy results.", "", "```json", json.dumps(comparisons, indent=2), "```"]
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n")
    print("V5_SUMMARY_JSON " + v1.canonical(summary), flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("generate", "collect", "report"))
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--trajectories", type=int, default=64)
    p.add_argument("--budget-usd", type=float, default=MAX_BUDGET)
    p.add_argument("--phase", choices=("development", "main"), default="development")
    a = p.parse_args()
    if a.command == "generate":
        generate(a.out, a.trajectories)
    elif a.command == "collect":
        collect(a.out, a.budget_usd, a.phase)
    else:
        report(a.out)


if __name__ == "__main__":
    main()

