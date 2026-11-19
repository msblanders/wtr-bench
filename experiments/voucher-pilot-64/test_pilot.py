"""Offline fixtures use synthetic answers only. No keys or network required."""

import json
import tempfile
import unittest
from pathlib import Path

import pilot


def response(answer="A", stop="end_turn"):
    return {"model": pilot.MODEL, "stop_reason": stop, "content": [
        {"type": "text", "text": json.dumps({"brief_basis": "Synthetic fixture.", "answer": answer})}],
        "usage": {"input_tokens": 220, "output_tokens": 18}}


class PilotChecks(unittest.TestCase):
    def setUp(self):
        self.rows = pilot.requests()

    def test_two_rules_and_presentation_controls(self):
        for strategy in ("selected", "delivered", "A", "C", "D"):
            records = {}
            for row in self.rows:
                text = row["body"]["messages"][0]["content"]
                events = [line.split() for line in text.splitlines()[1:3]]
                q = text.splitlines()[3]
                if strategy in ("A", "C", "D"):
                    letter = strategy
                else:
                    destination = "Alex" if "Alex" in q else "Jordan"
                    word = 2 if strategy == "selected" and q.startswith("Each helper") else -1
                    who, = [e[0] for e in events if e[word].rstrip(".") == destination]
                    letter = "A" if f"(A) {who}" in text else "B"
                records[row["id"]] = {"status": "received", "response": json.dumps(response(letter))}
            result = pilot.score(self.rows, records)
            cells = result["cells"]
            for c in cells.values():
                self.assertEqual(sum(c.values()), 16)
            conflict = cells["future_choice/swapped"]
            if strategy in ("selected", "delivered"):
                label = "chosen_only" if strategy == "selected" else "delivered_only"
                self.assertEqual(dict(conflict), {label: 16})
                self.assertEqual(cells["future_choice/aligned"]["both"], 16)
                self.assertEqual(cells["actual_delivery/swapped"]["actual_donor"], 16)
                self.assertEqual(result["matched_swapped_history_factual_and_forecast"]["actual_donor | " + label], 16)
                self.assertEqual(result["option_order_pairs"]["same"], 32)
                self.assertEqual(result["name_swap_pairs"]["helpers"]["same"], 32)
            elif strategy == "A":
                self.assertEqual(conflict["chosen_only"], 8)
                self.assertEqual(conflict["delivered_only"], 8)
                self.assertEqual(result["option_order_pairs"]["changed"], 32)
            else:
                self.assertEqual(conflict[pilot.outcome({}, strategy)], 16)
        missing = pilot.score(self.rows, {})["cells"]
        self.assertTrue(all(c["missing"] == 16 for c in missing.values()))

    def test_decoder(self):
        self.assertEqual(pilot.decode(response("D")), "D")
        self.assertEqual(pilot.decode(response("X")), "invalid")
        self.assertEqual(pilot.decode(response("A", "max_tokens")), "truncated")
        self.assertEqual(pilot.decode(response("A", "refusal")), "refusal")
        raw = response()
        for malformed in ('{}','{"brief_basis":"x","answer":"A","answer":"B"}',
                          '{"answer":"A","brief_basis":"x"}','{"brief_basis":"","answer":"A"}'):
            raw["content"][0]["text"] = malformed
            self.assertEqual(pilot.decode(raw), "invalid")

    def test_collection_contract_and_resume(self):
        paid = []
        def transport(path, payload):
            if path:
                self.assertEqual(set(payload), {"model", "system", "messages", "output_config"})
                return {"input_tokens": 250}
            self.assertEqual(set(payload), {"model", "temperature", "max_tokens", "system", "messages", "output_config"})
            paid.append(payload)
            if len(paid) == 2:
                raise TimeoutError("simulated ambiguous request")
            return response("B")
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"record.db"
            db=pilot.open_records(path)
            with self.assertRaises(TimeoutError):
                pilot.collect(db, self.rows, transport)
            db.close()
            db=pilot.open_records(path)
            pilot.collect(db, self.rows, transport)
            pilot.collect(db, self.rows, transport)
            records={r["id"]:r for r in db.execute("SELECT * FROM attempts")}
            db.close()
        self.assertEqual(len(paid), 64)
        self.assertEqual(len(records), 64)
        self.assertEqual(len({r["messages"][0]["content"] for r in paid}), 64)
        self.assertEqual(sum(r["status"] == "unresolved" for r in records.values()), 1)
        self.assertEqual(sum(r["reserved"] for r in records.values()), 638976)
        self.assertEqual(sum(r["cost"] or 0 for r in records.values()), 63*(3*220+15*18))

    def test_guard(self):
        db = pilot.open_records(":memory:")
        with self.assertRaises(RuntimeError):
            pilot.collect(db,self.rows,lambda path,body: {"input_tokens":pilot.COUNT_MAX+1} if path else self.fail("paid POST"))
        self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 0)
        with db:
            db.execute("INSERT INTO attempts(id,reserved,status,counted) VALUES ('fixture',?,'pending',200)",(pilot.BUDGET,))
        with self.assertRaises(RuntimeError):
            pilot.collect(db,self.rows,lambda path,body: {"input_tokens":150} if path else self.fail("paid POST"))
        db.close()

    def test_model_mismatch(self):
        db=pilot.open_records(":memory:")
        raw=response()
        raw["model"]="unexpected"
        with self.assertRaises(RuntimeError):
            pilot.collect(db,self.rows,lambda path,body: {"input_tokens":250} if path else raw)
        with self.assertRaises(RuntimeError):
            pilot.collect(db,self.rows,lambda *args: self.fail("request after mismatch"))
        db.close()


if __name__ == "__main__":
    unittest.main()
