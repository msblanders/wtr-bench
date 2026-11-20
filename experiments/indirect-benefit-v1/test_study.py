"""Offline checks deriving rival predictions from the text visible to the model."""

import unittest
from collections import Counter, defaultdict

from study import bank, summarize

# Independent worked examples. Columns give first beneficiary on the old roster,
# then the work expression for that slot, the second beneficiary and second job.
WORLD = (
    ("Eli", "prepared the first meal", "Noor", "cooked the second meal", "stayed in the studio"),
    ("Inez", "charged the spare with the four", "Leon", "charged the spare with the circular", "never contacted"),
    ("Bea", "repaired the jammed", "Drew", "restored the faulty", "Neither restorer attended"),
)


def predict(text, rule):
    lines = text.splitlines()
    question = lines[-5]
    options = [line.split()[-1] for line in lines[-4:-2]]
    for first, job_one, second, job_two, hidden_phrase in WORLD:
        if first in lines[0] and second in lines[0]:
            break
    else:
        raise ValueError("Unknown story")
    old_slot = int(second in question)
    jobs = [job_one, job_two]
    is_fact = question.startswith("Whose work actually")
    old = hidden_phrase in text and not is_fact
    if rule == "original_only":
        old = not is_fact
    elif rule == "delivery_only":
        old = False
    if "A fair lottery" in text and rule == "knowledge_and_agency":
        return "D"
    slot = old_slot if old else 1 - old_slot
    who, = [line.split()[0] for line in lines[3:5] if jobs[slot] in line]
    return "AB"[options.index(who)]


class Checks(unittest.TestCase):
    def setUp(self):
        self.rows, self.keys, _ = bank()

    def test_matched_pairs(self):
        by_form = defaultdict(dict)
        for row, key in zip(self.rows, self.keys, strict=True):
            self.assertEqual(row["id"], key["id"])
            text = row["body"]["messages"][0]["content"]
            self.assertTrue(all(p not in line for p in ("Eli","Noor","Inez","Leon","Bea","Drew")
                                for line in text.splitlines()[3:5]))
            by_form[key["family"],key["form"],key["probe"]][key["access"]] = text.splitlines()
        self.assertEqual(len(by_form), 48)
        for pair in by_form.values():
            self.assertEqual([i for i,(a,b) in enumerate(zip(pair["seen"],pair["unseen"],strict=True)) if a != b], [1])
        matches = defaultdict(list)
        for row, key in zip(self.rows, self.keys, strict=True):
            if key["probe"] in ("forecast", "assigned_forecast"):
                matches[key["family"],key["form"],key["access"]].append(row["body"]["messages"][0]["content"].splitlines())
        for a,b in matches.values():
            self.assertEqual([i for i,(x,y) in enumerate(zip(a,b,strict=True)) if x != y], [2])

    def test_rivals(self):
        for rule in ("knowledge_and_agency", "delivery_only", "original_only", "ignore_lottery"):
            answers = {r["id"]: predict(r["body"]["messages"][0]["content"],rule) for r in self.rows}
            families = summarize(self.keys, answers)
            for s in families.values():
                good = rule in ("knowledge_and_agency","ignore_lottery")
                self.assertEqual(s["predicted_forecast_reversals_out_of_4"], 4 if good else 0)
                self.assertEqual(s["primary_met"], good)
                self.assertEqual(s["assigned_gate_met"],rule=="knowledge_and_agency")
                if rule == "knowledge_and_agency":
                    self.assertEqual(s["forecast_reversals_with_all_controls_out_of_4"],4)
                    self.assertEqual(s["assigned_nondirectional_out_of_8"],8)

    def test_letter_and_name_balance(self):
        cells = defaultdict(Counter)
        helpers = defaultdict(Counter)
        for r,k in zip(self.rows,self.keys,strict=True):
            if k["probe"] != "assigned_forecast":
                letter=predict(r["body"]["messages"][0]["content"],"knowledge_and_agency")
                cell=(k["family"],k["access"],k["probe"])
                cells[cell][letter]+=1
                helpers[cell][k["options"]["AB".index(letter)]]+=1
        self.assertTrue(all(cell=={"A":2,"B":2} for cell in cells.values()))
        self.assertTrue(all(sorted(cell.values())==[2,2] for cell in helpers.values()))

    def test_no_model_answers(self):
        for s in summarize(self.keys,{}).values():
            self.assertFalse(s["primary_met"])
            self.assertTrue(all(v=={"missing":4} for v in s["cells"].values()))


if __name__ == "__main__":
    unittest.main()
