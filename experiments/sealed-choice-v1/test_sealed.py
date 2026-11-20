"""Offline counterfactual, duplication, and scoring checks."""

import unittest
from collections import Counter, defaultdict

from run_study import bank, score, wire
from sealed_materials import STORIES

# Text-only checks independent of the generator's helper/recipient indices.
WORLD = (("Eli", "Noor", "prepared the kit to be served before sunrise"),
         ("Inez", "Leon", "charged the spare with four straight sides"),
         ("Bea", "Drew", "repaired the jammed punch mechanism"))


def oracle(text, follow_outcome):
    lines = text.splitlines()
    first, second, work = next(world for world in WORLD if world[0] in lines[0] and world[1] in lines[0])
    options = [line.split()[-1] for line in lines[-4:-2]]
    first_worker, = [line.split()[0] for line in lines[2:4] if work in line]
    target_second = second in lines[-5]
    assert target_second != (first in lines[-5])
    swapped = "exchanged" in lines[6]
    reverse = target_second != (swapped and (follow_outcome or "actually provided" in lines[-5]))
    return "AB"[options.index(first_worker) ^ int(reverse)]


class Design(unittest.TestCase):
    def setUp(self):
        self.rows, self.keys, _ = bank()

    def test_independent_scenarios_and_exact_repeats(self):
        self.assertEqual(len(self.rows), 72)
        self.assertEqual(len(set(r["id"] for r in self.rows)), 72)
        self.assertEqual(Counter(Counter(wire(r["body"]) for r in self.rows).values()), {2: 24, 1: 24})
        pairs = defaultdict(dict)
        balance = defaultdict(Counter)
        for row, key in zip(self.rows, self.keys, strict=True):
            self.assertEqual(row["id"], key["id"])
            body = row["body"]
            text = body["messages"][0]["content"]
            pairs[key["family"], key["form"], key["probe"], key["repeat"]][key["outcome"]] = text.splitlines()
            self.assertLess(text.index("Both decisions were final"), text.index("fresh fair coin"))
            self.assertNotIn(key["id"], text)
            balance[key["family"], key["probe"], key["repeat"], key["outcome"]][oracle(text, True)] += 1
        for versions in pairs.values():
            self.assertEqual([i for i, (x, y) in enumerate(zip(versions["stand"], versions["swap"], strict=True)) if x != y], [6])
        self.assertTrue(all(c == {"A": 2, "B": 2} for c in balance.values()))

    def test_visible_text_oracles(self):
        for rule in ("expectation", "actual", "equal", "insufficient"):
            answers = {}
            for row in self.rows:
                text = row["body"]["messages"][0]["content"]
                a = oracle(text, rule == "actual")
                if "more likely" in text and rule in ("equal", "insufficient"):
                    a = "C" if rule == "equal" else "D"
                answers[row["id"]] = a
            for result in score(self.keys, answers).values():
                c = result["counts"]
                self.assertEqual(c["fact_correct"], 8)
                self.assertEqual(c["within_equal"], 8)
                self.assertEqual(c["toward_outcome"], 4 if rule == "actual" else 0)
                self.assertEqual(c["stable"], 0 if rule == "actual" else 4)
                self.assertEqual(c["cross_equal"], 0 if rule == "actual" else 16)
                self.assertEqual(result["form_effects"], [1.0 if rule == "actual" else 0.0] * 4)

    def test_repeat_variability_and_missing_data(self):
        answers = {r["id"]: "C" if k["repeat"] == 1 else "D" for r,k in zip(self.rows,self.keys,strict=True)}
        result = score(self.keys, answers)
        self.assertEqual(set(result), set(STORIES))
        for f in result.values():
            self.assertEqual(f["counts"]["mixed"], 4)
            self.assertEqual(f["counts"]["within_equal"], 0)
            self.assertEqual(f["counts"]["cross_equal"], 8)
        for f in score(self.keys, {}).values():
            self.assertEqual(f["counts"]["incomplete"], 4)
            self.assertEqual(f["counts"]["within_pairs"], 0)
            self.assertEqual(f["form_effects"], [])


if __name__ == "__main__":
    unittest.main()
