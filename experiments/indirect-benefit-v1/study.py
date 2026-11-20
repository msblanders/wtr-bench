"""Collect and score the indirect-benefit pilot using the voucher pilot's transport."""

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from materials import STORIES, items

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
from wtrbench.paired.natural import request_body


def wire(x):
    return (json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def bank():
    rows = items()
    requests = [{"id": row["id"], "body": request_body(row)} for row in rows]
    keys = [{k: v for k, v in row.items() if k != "prompt"} for row in rows]
    def digest(data):
        return hashlib.sha256(b"".join(map(wire, data))).hexdigest()
    return requests, keys, {"requests": digest(requests), "keys": digest(keys)}


def engine_for(digest):
    # Use an isolated instance of the original transport and decoder. Its ledger
    # checks BANK_SHA on every open; bind that identity to the new request bank.
    spec = importlib.util.spec_from_file_location("voucher_transport", HERE.parent / "voucher-pilot-64/pilot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BANK_SHA = digest
    return module


def cell_total(table, probe, category):
    return sum(table[f"{probe}/{access}"].get(category, 0) for access in ("seen", "unseen"))


def summarize(keys, answers):
    cells = defaultdict(Counter)
    pairs = defaultdict(dict)
    for k in keys:
        probe, access = k["probe"], k["access"]
        answer = answers.get(k["id"], "missing")
        who = k["options"]["AB".index(answer)] if answer in ("A", "B") else None
        if who is None:
            outcome = {"C": "equal", "D": "insufficient"}.get(answer, answer)
        elif probe in ("actual", "expected"):
            outcome = "correct" if who == k[probe] else "incorrect"
        else:
            outcome = "expected_beneficiary" if who == k["expected"] else "other_helper"
        cells[(k["family"], probe, access)][outcome] += 1
        pairs[(k["family"], k["form"])][(probe, access)] = outcome
    result = {}
    for family in STORIES:
        table = {f"{probe}/{access}": dict(counts) for (fam, probe, access), counts in cells.items()
                 if fam == family}
        both_forecasts = all_controls = flips_with_controls = 0
        for (fam, _), pair in pairs.items():
            if fam != family:
                continue
            reversal = all(pair["forecast", a] == "expected_beneficiary" for a in ("seen", "unseen"))
            controls = all(pair[p, a] == "correct" for a in ("seen", "unseen") for p in ("actual", "expected"))
            both_forecasts += reversal
            all_controls += controls
            flips_with_controls += reversal and controls
        neutral = cell_total(table, "assigned_forecast", "equal") + cell_total(table, "assigned_forecast", "insufficient")
        result[family] = {"cells": table, "predicted_forecast_reversals_out_of_4": both_forecasts,
                          "all_four_comprehension_answers_correct_out_of_4": all_controls,
                          "forecast_reversals_with_all_controls_out_of_4": flips_with_controls,
                          "primary_met": both_forecasts >= 3 and cell_total(table, "actual", "correct") >= 7
                                         and cell_total(table, "expected", "correct") >= 7,
                          "assigned_nondirectional_out_of_8": neutral, "assigned_gate_met": neutral >= 6}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["check", "collect", "report"])
    args = parser.parse_args()
    rows, keys, digests = bank()
    if digests != json.loads((HERE / "freeze.json").read_text()) or len({r["id"] for r in rows}) != 96:
        raise SystemExit("Unexpected bank or scoring key")
    engine = engine_for(digests["requests"])
    if len(rows) * engine.RESERVE > engine.BUDGET:
        raise SystemExit("Bank exceeds the spending guard")
    if args.mode == "check":
        print(json.dumps({"unique": len(rows), "reserved_usd": len(rows)*engine.RESERVE/1e6, **digests}))
        return
    out = HERE / "run"
    out.mkdir(exist_ok=True)
    path = out / "records.sqlite3"
    if args.mode == "collect":
        if not os.environ.get("ANTHROPIC_API_KEY") or time.strftime("%Y-%m-%d", time.gmtime()) >= "2026-11-30":
            raise SystemExit("Funded key and an active pinned model are required")
        lock = (out / "collect.lock").open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        (out / "requests.jsonl").write_bytes(b"".join(map(wire, rows)))
    elif not path.exists():
        raise SystemExit("No collection ledger")
    db = engine.open_records(path)
    try:
        if args.mode == "collect":
            def post(route, body):
                return engine.api_post(route, body, os.environ["ANTHROPIC_API_KEY"])
            engine.collect(db, rows, post)
        records = list(db.execute("SELECT * FROM attempts"))
        answers = {r["id"]: engine.decode(json.loads(r["response"])) if r["status"] == "received"
                   else r["status"] for r in records}
        report = {"families": summarize(keys, answers), "attempts": len(records),
                  "received": sum(r["status"] == "received" for r in records),
                  "unknown_usage": sum(r["cost"] is None for r in records),
                  "known_usd": sum(r["cost"] or 0 for r in records)/1e6,
                  "answers": answers, "freeze": digests}
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items() if k != "answers"}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
