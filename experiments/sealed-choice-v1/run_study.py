"""Run and score a frozen, single-model sealed-choice study."""

import argparse
import fcntl
import hashlib
import json
import os
import sys
import time
from collections import Counter
from itertools import product
from pathlib import Path

from sealed_materials import STORIES, items

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "indirect-benefit-v1"))
from study import engine_for, request_body, wire

VALID = {"original", "other", "equal", "insufficient"}
VALUE = {"original": 1, "other": -1, "equal": 0, "insufficient": 0}


def stream(rows):
    return b"".join(wire(r) for r in rows)


def bank():
    materials = items()
    rows = [{"id": m["id"], "body": request_body(m)} for m in materials]
    keys = [{k: v for k, v in m.items() if k != "prompt"} for m in materials]
    digests = {name: hashlib.sha256(stream(data)).hexdigest()
               for name, data in (("requests", rows), ("keys", keys))}
    return rows, keys, digests


def semantic(key, answer):
    if answer in ("A", "B"):
        helper = key["options"]["AB".index(answer)]
        return "original" if helper == key["original"] else "other"
    return {"C": "equal", "D": "insufficient"}.get(answer, answer)


def score(keys, answers):
    results = {}
    for family in STORIES:
        data = {}
        counts = {"fact_correct": 0, "complete_forecast_forms": 0, "mixed": 0, "stable": 0,
                  "toward_outcome": 0, "away_from_outcome": 0, "other_stable_shift": 0,
                  "incomplete": 0, "within_equal": 0, "within_pairs": 0,
                  "cross_equal": 0, "cross_pairs": 0, "stable_with_both_facts": 0,
                  "toward_with_both_facts": 0}
        cells = {probe + "/" + condition: Counter() for probe, condition in
                 product(("forecast", "fact"), ("stand", "swap"))}
        effects = []
        for k in keys:
            if k["family"] == family:
                answer = semantic(k, answers.get(k["id"], "missing"))
                data[k["form"], k["outcome"], k["probe"], k["repeat"]] = answer
                cells[k["probe"] + "/" + k["outcome"]][answer] += 1
        for form in range(4):
            fact_stand = data[form, "stand", "fact", 1] == "original"
            fact_swap = data[form, "swap", "fact", 1] == "other"
            counts["fact_correct"] += int(fact_stand) + int(fact_swap)
            stand = [data[form, "stand", "forecast", rep] for rep in (1, 2)]
            swap = [data[form, "swap", "forecast", rep] for rep in (1, 2)]
            for a, b in (stand, swap):
                if a in VALID and b in VALID:
                    counts["within_pairs"] += 1
                    counts["within_equal"] += a == b
            for a, b in product(stand, swap):
                if a in VALID and b in VALID:
                    counts["cross_pairs"] += 1
                    counts["cross_equal"] += a == b
            if not set(stand + swap) <= VALID:
                counts["incomplete"] += 1
                continue
            counts["complete_forecast_forms"] += 1
            effects.append((sum(VALUE[a] for a in stand) - sum(VALUE[b] for b in swap))/4)
            if stand[0] != stand[1] or swap[0] != swap[1]:
                label = "mixed"
            elif stand[0] == swap[0]:
                label = "stable"
            elif (stand[0], swap[0]) == ("original", "other"):
                label = "toward_outcome"
            elif (stand[0], swap[0]) == ("other", "original"):
                label = "away_from_outcome"
            else:
                label = "other_stable_shift"
            counts[label] += 1
            if fact_stand and fact_swap and label in ("stable", "toward_outcome"):
                counts["stable_with_both_facts" if label == "stable" else "toward_with_both_facts"] += 1
        results[family] = {"counts": counts, "cells": cells, "form_effects": effects}
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["check", "collect", "report"])
    mode = parser.parse_args().mode
    rows, keys, digests = bank()
    engine = engine_for(digests["requests"])
    if (digests != json.loads((ROOT / "freeze.json").read_text()) or len(rows) != 72
            or len({r["id"] for r in rows}) != 72 or len(rows) * engine.RESERVE > engine.BUDGET):
        raise SystemExit("Unexpected materials or spending limit")
    if mode == "check":
        print(json.dumps({"attempt_limit": len(rows), "reserved_usd": len(rows)*engine.RESERVE/1e6, **digests}))
        return
    out = ROOT / "run"
    path = out / "records.sqlite3"
    out.mkdir(exist_ok=True)
    if mode == "collect":
        if not os.environ.get("ANTHROPIC_API_KEY") or time.strftime("%Y-%m-%d", time.gmtime()) >= "2026-11-30":
            raise SystemExit("The pinned live model and a funded credential are required")
        lock = (out / "collect.lock").open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (out / "requests.jsonl").write_bytes(stream(rows))
    elif not path.exists():
        raise SystemExit("No ledger to score")
    db = engine.open_records(path)
    try:
        if mode == "collect":
            def post(route, body):
                return engine.api_post(route, body, os.environ["ANTHROPIC_API_KEY"])
            engine.collect(db, rows, post)
        records = list(db.execute("SELECT * FROM attempts"))
        answers = {r["id"]: engine.decode(json.loads(r["response"])) if r["status"] == "received"
                   else r["status"] for r in records}
        report = {"model": engine.MODEL, "attempts": len(records), "received": sum(r["status"] == "received" for r in records),
                  "unknown_usage": sum(r["cost"] is None for r in records), "usd": sum(r["cost"] or 0 for r in records)/1e6,
                  "answers": answers, "families": score(keys, answers), "freeze": digests}
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items() if k != "answers"}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
