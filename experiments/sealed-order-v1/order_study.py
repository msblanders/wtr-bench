"""Factorial follow-up to the sealed-choice pilot, anchored to its fourth form."""

import argparse
import fcntl
import hashlib
import json
import os
import sys
import time
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "sealed-choice-v1"))
from run_study import VALID, engine_for, request_body, score, semantic, stream
from sealed_materials import STORIES, material

# Change only the order of the two complete clauses. Both assignments still hold.
CLAUSES = {
    "breakfast": ("Eli at dawn", "Noor at noon"),
    "equipment": ("Inez for the square-socket camera", "Leon for the round-socket camera"),
    "archive": ("Bea for the maps", "Drew for the interviews"),
}


def render(family, idx, position, assignment, mirror, draw, probe):
    story = STORIES[family]
    text, key = material(story, idx, 3, draw, probe)
    lines = text.splitlines()
    if position == "first":
        left, right = CLAUSES[family]
        listed = f"{left} and {right}"
        if lines[0].count(listed) != 1:
            raise ValueError("Unexpected roster wording")
        lines[0] = lines[0].replace(listed, f"{right} and {left}")
    if assignment == "exchanged":
        first, second = story["helpers"]
        opposite = {first: second, second: first}
        for index in (2, 3):
            name, action = lines[index].split(" ", 1)
            lines[index] = f"{opposite[name]} {action}"
        for field in ("original", "other", "actual"):
            key[field] = opposite[key[field]]
    if mirror:
        lines[2], lines[3] = lines[3], lines[2]
    return "\n".join(lines), key


def bank():
    pairs = []
    for idx, family in enumerate(STORIES):
        for form, draw in product(range(4), ("stand", "swap")):
            position = ("first", "second")[form // 2]
            assignment = ("exchanged", "anchor")[form % 2]
            for mode, probe, repeat in (("primary", "forecast", 1), ("primary", "forecast", 2),
                                        ("primary", "fact", 1), ("mirror", "forecast", 1)):
                text, key = render(family, idx, position, assignment, mode == "mirror", draw, probe)
                ident = f"{family}-{position}-{assignment}-{mode}-{draw}-{probe}-{repeat}"
                meta = dict(id=ident, family=family, form=form, position=position, assignment=assignment,
                            mode=mode, outcome=draw, probe=probe, repeat=repeat, **key)
                pairs.append(({"id": ident, "body": request_body({"prompt": text})}, meta))
    pairs.sort(key=lambda pair: hashlib.sha256(("sealed-order-v1/" + pair[0]["id"]).encode()).digest())
    rows, keys = map(list, zip(*pairs, strict=True))
    digests = {name: hashlib.sha256(stream(data)).hexdigest()
               for name, data in (("requests", rows), ("keys", keys))}
    return rows, keys, digests


def classify(stand, swap):
    if not set(stand + swap) <= VALID:
        return "incomplete"
    if len(set(stand)) > 1 or len(set(swap)) > 1:
        return "mixed_repeats"
    if stand[0] == swap[0]:
        return "stable"
    return {("original", "other"): "toward", ("other", "original"): "away"}.get(
        (stand[0], swap[0]), "other_shift")


def summarize(keys, answers):
    primary_keys = [k for k in keys if k["mode"] == "primary"]
    families = score(primary_keys, answers)
    cell = {(k["family"], k["form"], k["mode"], k["outcome"], k["probe"], k["repeat"]):
            semantic(k, answers.get(k["id"], "missing")) for k in keys}
    data = []
    for family, form in product(STORIES, range(4)):
        def get(mode, draw, probe, repeat=1, current_family=family, current_form=form):
            return cell[current_family, current_form, mode, draw, probe, repeat]
        stand = [get("primary", "stand", "forecast", i) for i in (1, 2)]
        swap = [get("primary", "swap", "forecast", i) for i in (1, 2)]
        mirror_stand = get("mirror", "stand", "forecast")
        mirror_swap = get("mirror", "swap", "forecast")
        facts = [get("primary", "stand", "fact"), get("primary", "swap", "fact")]
        data.append({"family":family, "form":form, "target_position":("first","second")[form // 2],
                     "helper_assignment":("exchanged","anchor")[form % 2],
                     "stand":stand,"swap":swap, "fact_stand_swap":facts,
                     "paired_facts_correct":facts == ["original","other"],
                     "primary":classify(stand,swap),
                     "mirror_stand":mirror_stand, "mirror_swap":mirror_swap,
                     "mirror":classify([mirror_stand],[mirror_swap])})
    return {"forms":data,"families":families}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["check","collect","report"])
    mode=parser.parse_args().mode
    rows,keys,digests=bank()
    engine=engine_for(digests["requests"])
    if (digests != json.loads((ROOT/"freeze.json").read_text()) or len(rows) != 96
            or len({r["id"] for r in rows}) != 96 or len(rows)*engine.RESERVE > engine.BUDGET):
        raise SystemExit("Unexpected bank or reservation")
    if mode=="check":
        print(json.dumps({"trials": len(rows), "reserved_usd": len(rows)*engine.RESERVE/1e6, **digests}))
        return
    out=ROOT/"run"
    out.mkdir(exist_ok=True)
    path=out/"records.sqlite3"
    if mode=="collect":
        if not os.environ.get("ANTHROPIC_API_KEY") or time.strftime("%Y-%m-%d", time.gmtime()) >= "2026-11-30":
            raise SystemExit("The funded credential and the original model are required")
        lock=(out/"collect.lock").open("a")
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        (out/"requests.jsonl").write_bytes(stream(rows))
    elif not path.exists():
        raise SystemExit("No ledger")
    db=engine.open_records(path)
    try:
        if mode=="collect":
            def post(route,body):
                return engine.api_post(route,body,os.environ["ANTHROPIC_API_KEY"])
            engine.collect(db,rows,post)
        rec=list(db.execute("SELECT * FROM attempts"))
        answers={r["id"]:engine.decode(json.loads(r["response"])) if r["status"]=="received"
                 else r["status"] for r in rec}
        result={"attempts":len(rec),"received":sum(r["status"]=="received" for r in rec),
                "unknown_usage":sum(r["cost"] is None for r in rec),
                "usd":sum(r["cost"] or 0 for r in rec)/1e6,"answers":answers,
                **summarize(keys,answers),"freeze":digests}
        (out/"report.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({k: v for k, v in result.items() if k not in ("answers", "families")},indent=2))
    finally:
        db.close()


if __name__=="__main__":
    main()
