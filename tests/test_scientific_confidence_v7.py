"""Reference-label transfer, frozen handoffs and the shared five-dollar guard."""

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "experiments/scientific-confidence-v7/experiment.py"
SPEC = importlib.util.spec_from_file_location("confidence_v7", SOURCE)
e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(e)


def test_archive(path):
    corpus, dev, train = [], [], []
    for split, offset, target in [("dev", 0, dev), ("train", 100, train)]:
        for j, label in enumerate(e.LABELS):
            for i in range(8):
                cid = offset + j * 10 + i
                did = cid + 1000
                corpus.append(
                    {
                        "doc_id": did,
                        "title": "A study",
                        "abstract": ["Word " * 130],
                        "structured": False,
                    }
                )
                target.append(
                    {
                        "id": cid,
                        "claim": "A scientific claim.",
                        "cited_doc_ids": [did],
                        "evidence": {}
                        if label == "NOT_ENOUGH_INFO"
                        else {str(did): [{"label": label, "sentences": [0]}]},
                    }
                )
    with tarfile.open(path, "w:gz") as tar:
        for name, rows in [
            ("corpus.jsonl", corpus),
            ("claims_dev.jsonl", dev),
            ("claims_train.jsonl", train),
        ]:
            b = "\n".join(json.dumps(r) for r in rows).encode()
            info = tarfile.TarInfo("data/" + name)
            info.size = len(b)
            tar.addfile(info, io.BytesIO(b))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_state(truth, step):
    label = truth["labels"][str(step)]
    return {
        "entries": []
        if step == 3
        else [
            {
                "source_id": truth["source_id"],
                "revision": 1,
                "identity_refs": ["A", "B"],
                "evidence_relation": label,
                "rationale_sentences": [0],
                "scope_note": "Scope",
            }
        ],
        "identity_index": [
            {
                "source_id": truth["source_id"],
                "current_revision": 1,
                "status": "excluded",
                "identity_refs": ["A", "B"],
            }
        ]
        if step == 3
        else [],
        "evidence_basis": "Note",
        "probabilities": {k: float(k == label) for k in e.LABELS},
    }


class ScientificConfidenceV7Tests(unittest.TestCase):
    def test_selection_boundary_and_identical_initial_information(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "data.tar.gz"
            with patch.object(e, "DATA_SHA", test_archive(archive)):
                cases, gold = e.fixtures(archive)
                self.assertEqual(len(cases), 21)
                self.assertEqual(len({g["source_id"] for g in gold}), 21)
                self.assertEqual((cases, gold), e.fixtures(archive))
                for c in cases:
                    a, b = [e.payload(c, 1, arm, c["initial_state"]) for arm in e.ARMS]
                    for p, arm in zip((a, b), e.ARMS):
                        p["messages"][0]["content"] = p["messages"][0]["content"].replace(
                            e.POLICY[arm], "POLICY"
                        )
                        self.assertNotIn("annotation_label", json.dumps(p))
                        self.assertNotIn("evidence_annotations", json.dumps(p))
                    self.assertEqual(a, b)

    def test_scoring_keeps_semantics_separate_from_source_identity(self):
        truth = {
            "source_id": "S2-1",
            "sentence_count": 3,
            "labels": {"1": "SUPPORT", "3": "NOT_ENOUGH_INFO"},
        }
        good = reference_state(truth, 1)
        self.assertEqual(e.score({"data": good}, truth, 1)["brier"], 0)
        bad = copy.deepcopy(good)
        bad["entries"][0]["source_id"] = "wrong"
        result = e.score({"data": bad}, truth, 1)
        self.assertTrue(result["correct"])
        self.assertFalse(result["source_record_correct"])
        bad["probabilities"]["SUPPORT"] = 0.8
        self.assertEqual(e.score({"data": bad}, truth, 1)["brier"], 2)
        excluded = reference_state(truth, 3)
        self.assertTrue(e.score({"data": excluded}, truth, 3)["index_faithful"])

    def test_budget_rejects_before_send_and_keeps_ambiguous_reservation(self):
        with (
            tempfile.TemporaryDirectory() as d,
            patch.dict(e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}),
        ):
            out = Path(d)
            c = e.Collector(out, 0.00001)
            payload = {"max_tokens": 1536}
            with patch.object(e.v1.urllib.request, "urlopen") as request:
                with self.assertRaises(RuntimeError):
                    c.call("x", "a", "1", payload)
                request.assert_not_called()
            c = e.Collector(out, 5)
            with (
                patch.object(
                    e.v1.urllib.request, "urlopen", side_effect=urllib.error.URLError("test")
                ),
                self.assertRaises(RuntimeError),
            ):
                c.call("x", "a", "1", payload)
            self.assertTrue(c.stop)
            self.assertGreater(c.committed, 0)
            self.assertEqual(c.actual, 0)
            with self.assertRaises(ValueError):
                e.collect(out, "main", 5.01)

    def test_full_mocked_run_gate_shared_cost_and_audit(self):
        refs = {}

        def provider(request, timeout):
            import re

            p = json.loads(request.data)
            text = p["messages"][0]["content"]
            cid, step = re.search(r"Case (DEV\d+|TEST\d+); update (\d+)\.", text).groups()
            step = int(step)
            arm = next(a for a in e.ARMS if e.POLICY[a] in text)
            state = reference_state(refs[cid], step)
            if arm == "active_checklist":
                state["identity_index"] = []
            # Deliberately incorrect development semantics must not block collection.
            if cid.startswith("DEV"):
                state["probabilities"] = {"SUPPORT": 0.0, "CONTRADICT": 1.0, "NOT_ENOUGH_INFO": 0.0}
            response = {
                "stop_reason": "tool_use",
                "content": [{"type": "tool_use", "name": "submit_state", "input": state}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }
            return io.BytesIO(json.dumps(response).encode())

        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            archive, out = Path(d) / "data.tar.gz", Path(d) / "freeze"
            with patch.object(e, "DATA_SHA", test_archive(archive)):
                e.generate(out, archive)
                for g in json.loads((out / "gold.json").read_text()):
                    refs[g["case_id"]] = g
                with (
                    patch.dict(e.v1.os.environ, {"ANTHROPIC_API_KEY": "test-placeholder"}),
                    patch.object(e.v1.urllib.request, "urlopen", side_effect=provider) as call,
                ):
                    e.collect(out, "development", 5)
                    self.assertTrue(e.gate(out)["passed"])
                    self.assertEqual(call.call_count, 24)
                    e.collect(out, "main", 5)
                    self.assertEqual(call.call_count, 168)
                    summary = json.loads((out / "summary.json").read_text())
                    self.assertTrue(summary["eligible_for_interpretation"])
                    self.assertAlmostEqual(summary["recorded_cost_usd"], 168 * 0.00105)
                    self.assertEqual(summary["primary"]["mean_compact_minus_active"], 0)
                    e.audit(out)
                    with self.assertRaises(ValueError):
                        e.collect(out, "main", 5)
                    self.assertEqual(call.call_count, 168)
                    (out / "cases.json").write_text("[]")
                    with self.assertRaises(ValueError):
                        e.report(out)


if __name__ == "__main__":
    unittest.main()
