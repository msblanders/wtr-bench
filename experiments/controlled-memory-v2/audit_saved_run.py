"""Audit the stopped v2.1.1 run without executing its code or making API requests."""
import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path

ARTIFACT_SHA256 = "faa415f6a13d641260275c329ef08bf9bd0d4a5e9a963e5656bb378a621eb460"
DEFAULT = Path(__file__).resolve().parent / "results/run-40982656128"


def arithmetic_policy(event_probability, benefit, fee):
    """Use a reported event probability unchanged; compute payoff and action in code."""
    if not all(math.isfinite(x) for x in (event_probability, benefit, fee)):
        raise ValueError("Non-finite input")
    if not 0 <= event_probability <= 1:
        raise ValueError("Probability outside [0,1]")
    expected_value = benefit * event_probability - fee
    return {"expected_net_value": expected_value, "pay": expected_value > 0}


def audit(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARTIFACT_SHA256:
        raise ValueError("Unexpected raw archive digest")
    with zipfile.ZipFile(archive) as bundle:
        def read(name):
            return json.loads(bundle.read(name))
        manifest = read("manifest.json")
        for name, expected in manifest["source_hashes"].items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != expected:
                raise ValueError("Frozen source changed")
        raw_requests = bundle.read("requests.jsonl")
        if hashlib.sha256(raw_requests).hexdigest() != manifest["requests_sha256"]:
            raise ValueError("Frozen requests changed")
        requests = {r["id"]: r for r in map(json.loads, raw_requests.splitlines())}
        responses = list(map(json.loads, bundle.read("responses.jsonl").splitlines()))
        attempts = list(map(json.loads, bundle.read("attempts.jsonl").splitlines()))
        gate = read("smoke-gate.json")
        if [r["id"] for r in responses] != [r["id"] for r in attempts]:
            raise ValueError("Attempt/response mismatch")
    if len({r["id"] for r in responses}) != len(responses):
        raise ValueError("Duplicate responses")
    counts = {"decisions": 0, "original_correct": 0, "arithmetic_correct": 0, "sign_consistent": 0,
              "event_prob_within_02": 0, "event_prob_within_001": 0,
              "probabilities": 0, "exact_probabilities": 0}
    by_case, changed = [], []
    for response in responses:
        request = requests[response["id"]]
        if request["phase"] != "smoke" or response["status"] != "valid":
            raise ValueError("Unexpected response phase or validity")
        if response["request_hash"] != request["request_hash"]:
            raise ValueError("Response hash mismatch")
        raw = response["raw"]
        if raw["model"] != manifest["model"] or raw["stop_reason"] != "end_turn":
            raise ValueError("Unexpected model or stop reason")
        output = json.loads("".join(b["text"] for b in raw["content"] if b["type"] == "text"))
        calculations = {c["id"]: {k: v for k, v in c.items() if k != "id"}
                        for c in output["calculations"]}
        if len(calculations) != len(output["calculations"]):
            raise ValueError("Duplicate calculation IDs")
        for key in ("predictions", "decisions"):
            if output[key] != response["output"][key]:
                raise ValueError("Stored values differ from raw response")
        if calculations != response["output"]["calculations"]:
            raise ValueError("Stored calculations differ from raw response")
        lookup = {(m["partner"], m["setting"]): m for m in request["memory"]}
        case = {"id": request["id"], "original_correct": 0, "arithmetic_correct": 0}
        for question in request["answer_key"]:
            memory = lookup[question["partner"], question["setting"]]
            expected = memory["p_choose" if question["kind"] == "choice" else "p_success_if_attempt"]
            counts["probabilities"] += 1
            counts["exact_probabilities"] += output["predictions"][question["id"]] == expected
        for decision in request["decision_key"]:
            key = decision["id"]
            memory = lookup[decision["partner"], decision["setting"]]
            w, a = memory["p_choose"], memory["p_success_if_attempt"]
            if decision["kind"] == "voluntary_delivery":
                expected_probability = w * a
            elif decision["kind"] == "assigned_delivery":
                expected_probability = a
            elif decision["kind"] == "backup":
                expected_probability = 1 - w * a
            else:
                expected_probability = w
            expected_value = decision["benefit"] * expected_probability - decision["fee"]
            expected_choice = expected_value > 0
            reference = request["expected_output"]
            if (abs(reference["calculations"][key]["event_probability"] - expected_probability) > 1e-12
                    or abs(reference["calculations"][key]["expected_net_value"] - expected_value) > 1e-12
                    or reference["decisions"][key] != expected_choice):
                raise ValueError("Independent recomputation disagrees with original scorer")
            reported = calculations[key]
            policy = arithmetic_policy(reported["event_probability"], decision["benefit"], decision["fee"])
            chosen = output["decisions"][key]
            counts["decisions"] += 1
            counts["original_correct"] += chosen == expected_choice
            counts["arithmetic_correct"] += policy["pay"] == expected_choice
            counts["sign_consistent"] += chosen == (reported["expected_net_value"] > 0)
            counts["event_prob_within_02"] += abs(reported["event_probability"] - expected_probability) <= .02
            counts["event_prob_within_001"] += abs(reported["event_probability"] - expected_probability) <= .001
            case["original_correct"] += chosen == expected_choice
            case["arithmetic_correct"] += policy["pay"] == expected_choice
            if chosen != policy["pay"]:
                changed.append({"request_id": request["id"], "decision_id": key,
                                "kind": decision["kind"], "reported": reported,
                                "benefit": decision["benefit"], "fee": decision["fee"],
                                "model_choice": chosen, "code_policy": policy,
                                "memory_consistent_choice": expected_choice})
        by_case.append(case)
    return {"data_origin": "anthropic_api", "run_id": 40982656128, "version": manifest["version"],
            "artifact_sha256": ARTIFACT_SHA256, "frozen_gate_passed": gate["passed"],
            "smoke_requests": len(responses), "passed_smoke_requests": sum(d["passed"] for d in gate["details"]),
            "pilot_requests_sent": 0, "api_cost_usd": sum(r["cost_usd"] for r in responses),
            "counts": counts, "by_case": by_case, "changed_decisions": changed,
            "interpretation": "Post hoc arithmetic diagnosis. Correct means consistent with assigned memory, not with latent truth. Original model choices and frozen gate are unchanged. No new model calls."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT / "raw-artifact.zip")
    parser.add_argument("--out", type=Path, default=DEFAULT / "diagnostic-analysis.json")
    args = parser.parse_args()
    result = audit(args.archive)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("by_case", "changed_decisions")}, indent=2))
