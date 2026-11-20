"""Verify factorial isolation against actual v1 payloads and text-derived expectations."""

import unittest
from collections import Counter
from itertools import product

from order_study import CLAUSES, STORIES, bank, classify, request_body, summarize
from sealed_materials import items as historical_items
from test_sealed import oracle


class FactorialChecks(unittest.TestCase):
    def setUp(self):
        self.rows, self.keys, _ = bank()
        self.text = {r["id"]: r["body"]["messages"][0]["content"].splitlines() for r in self.rows}

    def test_two_factors_and_mirror(self):
        for family, draw in product(STORIES, ("stand", "swap")):
            left, right = CLAUSES[family]
            for position, assignment in product(("first","second"), ("anchor","exchanged")):
                prefix = f"{family}-{position}-{assignment}"
                a = self.text[f"{prefix}-primary-{draw}-forecast-1"]
                self.assertEqual(a, self.text[f"{prefix}-primary-{draw}-forecast-2"])
                order_other = "second" if position == "first" else "first"
                b = self.text[f"{family}-{order_other}-{assignment}-primary-{draw}-forecast-1"]
                self.assertEqual(a[1:], b[1:])
                self.assertIn(f"{right} and {left}" if position == "first" else f"{left} and {right}", a[0])
                owner_other = "exchanged" if assignment == "anchor" else "anchor"
                b = self.text[f"{family}-{position}-{owner_other}-primary-{draw}-forecast-1"]
                self.assertEqual(a[:2]+a[4:], b[:2]+b[4:])
                for x, y in zip(a[2:4], b[2:4], strict=True):
                    self.assertNotEqual(x.split()[0], y.split()[0])
                    self.assertEqual(x.split()[1:], y.split()[1:])
                b = self.text[f"{prefix}-mirror-{draw}-forecast-1"]
                self.assertEqual(b, a[:2] + list(reversed(a[2:4])) + a[4:])
                other_draw = "swap" if draw == "stand" else "stand"
                b = self.text[f"{prefix}-primary-{other_draw}-forecast-1"]
                self.assertEqual([i for i,(x,y) in enumerate(zip(a,b,strict=True)) if x!=y], [6])
                self.assertEqual(len(a),13)

    def test_exact_anchor_and_controls(self):
        hist = {r["id"]:request_body(r) for r in historical_items()}
        for row, k in zip(self.rows,self.keys,strict=True):
            if k["form"] == 3 and k["mode"] == "primary":
                old_id = f"{k['family']}-3-{k['outcome']}-{k['probe']}-{k['repeat']}"
                self.assertEqual(row["body"], hist[old_id])
        self.assertEqual(len(self.rows),96)
        self.assertEqual(len({r["id"] for r in self.rows}),96)
        self.assertEqual(Counter(Counter(tuple(x) for x in self.text.values()).values()), {1:48, 2:24})

    def test_scorer(self):
        for rule, desired in ((True,"toward"), (False,"stable")):
            answers = {r["id"]:oracle(r["body"]["messages"][0]["content"],rule) for r in self.rows}
            result = summarize(self.keys,answers)
            self.assertEqual(len(result["forms"]),12)
            for form in result["forms"]:
                self.assertEqual((form["primary"],form["mirror"]),(desired,desired))
                self.assertTrue(form["paired_facts_correct"])
        self.assertEqual(classify(["original","equal"],["other","other"]),"mixed_repeats")
        self.assertEqual(classify(["insufficient"]*2,["insufficient"]*2),"stable")
        self.assertEqual(classify(["other"]*2,["original"]*2),"away")
        self.assertEqual(classify(["invalid"]*2,["original"]*2),"incomplete")
        for form in summarize(self.keys,{})["forms"]:
            self.assertEqual(form["primary"],"incomplete")


if __name__=="__main__":
    unittest.main()
