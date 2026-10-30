"""Scientific invariants and paid-collection gates; no live API calls."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "experiments/controlled-memory-v2/experiment.py"
spec = importlib.util.spec_from_file_location("controlled_memory", MODULE)
assert spec is not None and spec.loader is not None
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)


def raw_response(body, output):
    return {"model": body["model"], "stop_reason": "end_turn",
            "usage": {"input_tokens": 100, "output_tokens": 100},
            "content": [{"type": "text", "text": json.dumps(output)}]}


class ControlledMemoryTests(unittest.TestCase):
    def test_channel_swap_is_executed_and_product_tasks_are_invariant(self):
        world = e.v1.make_world(1000, "shared")
        correct, _ = e.memory_for(world, 24, "functional")
        wrong, _ = e.memory_for(world, 24, "wrong_routing")
        self.assertTrue(any(a["p_choose"] != b["p_choose"] for a, b in zip(correct, wrong)))
        for a, b in zip(correct, wrong):
            self.assertEqual(a["p_choose"], b["p_success_if_attempt"])
            self.assertEqual(a["p_success_if_attempt"], b["p_choose"])
        decisions = e.decision_items(world)
        a, _ = e.expected_from_memory(correct, world["queries"], decisions)
        b, _ = e.expected_from_memory(wrong, world["queries"], decisions)
        for d in decisions:
            if d["kind"] in ("backup", "voluntary_delivery"):
                self.assertEqual(a["decisions"][d["id"]], b["decisions"][d["id"]])

    def test_analytic_bayes_factor_and_unseen_prior(self):
        records = [{"partner": "P", "setting": setting, "instruction": "VOLUNTARY",
                    "attempt": attempt} for setting, attempt in [("X", True)]*2 + [("Y", False)]*2]
        # Integrated shared evidence=Beta(3,3)=1/30; separate=(1/3)^2=1/9.
        self.assertAlmostEqual(e.sharing_posterior(records), 3/13)
        self.assertEqual(e.sharing_posterior([]), 0.5)
        world = e.v1.make_world(1000, "context_specific")
        memory, _ = e.memory_for(world, 24, "local")
        self.assertTrue(all(r["p_choose"] == 0.5 for r in memory if r["setting"] == world["heldout_setting"]))

    def test_adaptive_posterior_favors_clear_context_difference(self):
        records = [{"partner": "P", "setting": setting, "instruction": "VOLUNTARY",
                    "attempt": attempt} for setting, attempt in [("X", True)]*20 + [("Y", False)]*20]
        self.assertLess(e.sharing_posterior(records), 1e-8)

    def test_matched_prompts_and_no_privileged_metadata(self):
        requests = [e.make_request(1001, "context_specific", 24, a) for a in e.ARMS]
        bodies = []
        for r in requests:
            prompt = r["body"]["messages"][0]["content"]
            prompt = prompt.replace(e.canonical(r["memory"]), "MEMORY")
            bodies.append(prompt)
            serialized = e.canonical(r["body"])
            for forbidden in ("truth", "answer_key", "expected_output", "sharing_posterior",
                              "context_specific", "wrong_routing", "Observed records", "1001"):
                self.assertNotIn(forbidden, serialized)
            self.assertEqual(r["answer_key"], requests[0]["answer_key"])
            self.assertEqual(r["decision_key"], requests[0]["decision_key"])
        self.assertTrue(all(x == bodies[0] for x in bodies))

    def test_paired_fees_and_reference_regret(self):
        a = e.make_request(1002, "shared", 2, "functional")
        b = e.make_request(1002, "context_specific", 24, "adaptive")
        self.assertEqual([(d["id"], d["fee"], d["kind"], d["setting"]) for d in a["decision_key"]],
                         [(d["id"], d["fee"], d["kind"], d["setting"]) for d in b["decision_key"]])
        output = {"predictions": {q["id"]: q["truth"] for q in a["answer_key"]},
                  "decisions": {d["id"]: d["truth_gain"] > 0 for d in a["decision_key"]}}
        self.assertEqual(e.metrics(a, output)["decision_regret"], 0)
        self.assertEqual(e.metrics(a, output)["all"], 0)

    def test_strict_schema_failure_cases(self):
        r = e.make_request(1000, "shared", 8, "functional")
        output = json.loads(json.dumps(r["expected_output"]))
        self.assertEqual(e.parse_response(json.dumps(output), r), output)
        with self.assertRaises(ValueError):
            e.parse_response("An explanation. " + json.dumps(output), r)
        output["predictions"]["q01"] = True
        with self.assertRaises(ValueError):
            e.parse_response(json.dumps(output), r)
        output = json.loads(json.dumps(r["expected_output"]))
        output["decisions"]["d01"] = 1
        with self.assertRaises(ValueError):
            e.parse_response(json.dumps(output), r)
        duplicate = json.dumps(r["expected_output"]).replace('"q01":', '"q01": 0.5, "q01":')
        with self.assertRaises(ValueError):
            e.parse_response(duplicate, r)

    def test_smoke_gate_detects_reconstructed_correct_rule(self):
        requests = [e.make_request(9000, "shared", 24, arm, "smoke") for arm in e.ARMS]
        records = [{"id": r["id"], "status": "valid", "output": r["expected_output"]} for r in requests]
        self.assertTrue(e.smoke_gate(requests, records)["passed"])
        records[-1]["output"] = requests[-1]["correct_pooled_output"]
        self.assertFalse(e.smoke_gate(requests, records)["passed"])

    def test_failure_stops_before_pilot(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "run"
            e.generate(out, 1)
            requests = e.read_jsonl(out / "requests.jsonl")
            by_hash = {r["request_hash"]: r for r in requests}
            calls = []
            def sender(body):
                calls.append(body)
                r = by_hash[e.digest(body)]
                return raw_response(body, r["correct_pooled_output"] if r["arm"] == "wrong_routing" else r["expected_output"])
            with self.assertRaises(RuntimeError):
                e.collect(out, 25, sender)
            self.assertEqual(len(calls), 8)
            self.assertEqual(json.loads((out / "collection-status.json").read_text())["status"], "smoke_gate_failed")

    def test_frozen_hash_budget_ledger_and_transport_guards(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "budget"
            e.generate(out, 1)
            def forbidden(body):
                raise AssertionError("Should not send")
            e.collect(out, 0.000001, forbidden)
            with self.assertRaises(FileExistsError):
                e.collect(out, 25, forbidden)
            (out / "requests.jsonl").write_text((out / "requests.jsonl").read_text() + "\n")
            with self.assertRaises(ValueError):
                e.check_manifest(out)
            out = Path(root) / "transport"
            e.generate(out, 1)
            calls = []
            def timeout(body):
                calls.append(body)
                raise TimeoutError()
            with self.assertRaises(RuntimeError):
                e.collect(out, 25, timeout)
            self.assertEqual(len(calls), 1)

    def test_invalid_response_stops_immediately_and_is_preserved(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "run"
            e.generate(out, 1)
            def sender(body):
                return raw_response(body, {"predictions": {}, "decisions": {}})
            with self.assertRaises(RuntimeError):
                e.collect(out, 25, sender)
            records = e.read_jsonl(out / "responses.jsonl")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["status"], "invalid")
            self.assertIn("raw", records[0])

    def test_synthetic_end_to_end_and_planned_cost(self):
        with tempfile.TemporaryDirectory() as root, contextlib.redirect_stdout(io.StringIO()):
            out = Path(root) / "run"
            e.generate(out, 2)
            requests = e.read_jsonl(out / "requests.jsonl")
            outputs = {r["request_hash"]: r["expected_output"] for r in requests}
            self.assertTrue(all(r["seed"] >= 1000 for r in requests))
            self.assertFalse({r["seed"] for r in requests if r["phase"] == "smoke"}
                             & {r["seed"] for r in requests if r["phase"] == "pilot"})
            def sender(body):
                return raw_response(body, outputs[e.digest(body)])
            e.collect(out, 25, sender)
            e.report(out)
            result = json.loads((out / "report.json").read_text())
            self.assertTrue(result["pilot_complete"])
            self.assertTrue(result["manipulation_passed"])
            self.assertEqual(result["data_origin"], "test_double")
            self.assertEqual(result["pilot_valid"], 64)
            full = Path(root) / "full"
            e.generate(full, 8)
            manifest = json.loads((full / "manifest.json").read_text())
            self.assertEqual(manifest["requests"], 264)
            self.assertLess(manifest["planning_reserve_usd"], 25)


if __name__ == "__main__":
    unittest.main()
