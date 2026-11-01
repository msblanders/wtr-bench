"""Offline integrity checks: actual prompts, identical starts, state handoffs and replay."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path


def audit(out):
    spec = importlib.util.spec_from_file_location("frozen_v5", out / "experiment.py")
    assert spec and spec.loader
    e = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(e)
    manifest = json.loads((out / "manifest.json").read_text())
    hashes_ok = all(e.v1.digest(out / name) == value for name, value in manifest["files"].items())
    if not hashes_ok:
        raise ValueError("Frozen file hash mismatch")
    cases = json.loads((out / "cases.json").read_text())
    gold = json.loads((out / "gold.json").read_text())
    regenerated_cases, regenerated_gold = [], []
    for phase, count in (("development", 2), ("main", manifest["main_trajectories"])):
        c, g = e.make_cases(phase, count)
        regenerated_cases.extend(c)
        regenerated_gold.extend(g)
    if regenerated_cases != cases or regenerated_gold != gold:
        raise ValueError("Fixture regeneration mismatch")
    call_rows = e.v2.read_jsonl(out / "calls.jsonl")
    rec_rows = e.v2.read_jsonl(out / "records.jsonl")
    calls = {(r["case_id"], r["arm"], int(r["stage"])): r for r in call_rows}
    records = {(r["case_id"], r["kind"], r["step"]): r for r in rec_rows}
    expected = {(c["case_id"], arm, step) for c in cases for arm in e.ARMS for step in e.PAID_STEPS}
    if len(calls) != len(call_rows) or len(records) != len(rec_rows):
        raise ValueError("Duplicate keys")
    if set(calls) != expected or set(records) != expected:
        raise ValueError("Incomplete or unexpected call/record keys")
    checked_prompts, checked_responses, matched_first_requests = 0, 0, 0
    for case in cases:
        initial_requests = []
        for arm in e.ARMS:
            state = copy.deepcopy(case["initial_state"])
            for step in e.PAID_STEPS:
                key = (case["case_id"], arm, step)
                call, record = calls[key], records[key]
                if call["request"] != e.payload(case, step, arm, state):
                    raise ValueError("Unexpected request or state handoff")
                checked_prompts += 1
                if step == 1:
                    p = copy.deepcopy(call["request"])
                    p["messages"][0]["content"] = p["messages"][0]["content"].replace(e.RETENTION[arm], "POLICY")
                    initial_requests.append(p)
                try:
                    returned = e.v2.tool_input(call.get("response", {}), "submit_state")
                except (ValueError, KeyError, TypeError):
                    if "data" in record:
                        raise ValueError("Record contains data absent from completed response") from None
                    continue
                if returned != record.get("data"):
                    raise ValueError("Saved response differs from record")
                checked_responses += 1
                try:
                    derived = e.calculate(returned)
                except (KeyError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
                    derived = {"error": type(exc).__name__}
                state = {"record": returned, "derived_beliefs": derived}
        if initial_requests[0] != initial_requests[1]:
            raise ValueError("First-call conditions differ beyond retention policy")
        matched_first_requests += 1
    before = json.loads((out / "summary.json").read_text())
    with contextlib.redirect_stdout(io.StringIO()):
        e.report(out)
    after = json.loads((out / "summary.json").read_text())
    if before != after:
        raise ValueError("Report changed on replay")
    summary = {"frozen_hashes_match": hashes_ok, "fixtures_regenerated_identically": True,
               "unique_complete_call_and_record_keys": True,
               "matched_first_request_pairs": matched_first_requests,
               "requests_and_state_handoffs_verified": checked_prompts,
               "response_record_pairs_verified": checked_responses,
               "aggregate_report_identical_on_replay": True,
               "no_model_calls_in_audit": True}
    e.v1.write_json(out / "integrity_audit.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    audit(parser.parse_args().out)
