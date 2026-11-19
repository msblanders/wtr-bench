"""Run or score the frozen 64-prompt pilot. Python 3.10+, standard library."""

import argparse
import hashlib
import http.client
import json
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = "claude-sonnet-4-5-20250929"
BANK_SHA = "56df2ec4c9d02ced45628a5ef0ff4a8993dcafe142d38f926661958c1e9e314f"
KEY_SHA = "e1b1387f43c8208071e7654cb1261e429cdcd8682788c603ac00d6c4f73c3d8b"
COUNT_MAX = 1024
INPUT_ALLOWANCE = 2048
MAX_OUTPUT = 256
# Amounts are integer millionths of a US dollar, per standard API pricing.
RESERVE = 3 * INPUT_ALLOWANCE + 15 * MAX_OUTPUT
BUDGET = 1_000_000


def checked_file(name, digest):
    data = (ROOT / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Frozen file differs: {name}")
    return data


def requests():
    rows = [json.loads(s) for s in checked_file("requests.jsonl", BANK_SHA).splitlines()]
    ids = {row["id"] for row in rows}
    if len(ids) != 64 or len(rows) != 64:
        raise ValueError("Expected 64 unique requests")
    for row in rows:
        body = row["body"]
        prompt = body["messages"][0]["content"]
        if (row["id"] != hashlib.sha256(prompt.encode()).hexdigest()[:20]
                or body["model"] != MODEL or body["max_tokens"] != MAX_OUTPUT):
            raise ValueError("Request metadata mismatch")
    return rows


def open_records(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA synchronous=FULL")
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS protocol (singleton INTEGER PRIMARY KEY, digest TEXT NOT NULL)")
        db.execute("INSERT OR IGNORE INTO protocol VALUES (1, ?)", (BANK_SHA,))
        if db.execute("SELECT digest FROM protocol WHERE singleton=1").fetchone()[0] != BANK_SHA:
            raise ValueError("The existing records belong to another protocol")
        db.execute("""CREATE TABLE IF NOT EXISTS attempts
            (id TEXT PRIMARY KEY, reserved INTEGER NOT NULL, status TEXT NOT NULL,
             counted INTEGER NOT NULL, response TEXT, cost INTEGER, detail TEXT)""")
    return db


def api_post(path, payload, key):
    # This client performs one POST. No redirects or automatic retries.
    conn = http.client.HTTPSConnection("api.anthropic.com", timeout=110)
    try:
        conn.request("POST", "/v1/messages" + path, json.dumps(payload).encode(), {
            "content-type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": key})
        result = conn.getresponse()
        data = result.read()
        if result.status != 200:
            raise RuntimeError(f"Anthropic returned HTTP {result.status} for {path or 'messages'}")
        return json.loads(data)
    finally:
        conn.close()


def cost_for(raw):
    usage = raw["usage"]
    n_in, n_out = usage["input_tokens"], usage["output_tokens"]
    if any(type(x) is not int or x < 0 for x in (n_in, n_out)):
        raise ValueError("Unusable usage counts")
    if any(usage.get(x) for x in ("cache_creation_input_tokens", "cache_read_input_tokens", "server_tool_use")):
        raise ValueError("Unexpected billable feature")
    return 3 * n_in + 15 * n_out


def collect(db, rows, post):
    # Leave committed reservations in place across timeouts, exceptions and restarts.
    if db.execute("SELECT 1 FROM attempts WHERE status='review'").fetchone():
        raise RuntimeError("A previous response requires billing or model review. Collection stopped.")
    for row in rows:
        item_id, body = row["id"], row["body"]
        if db.execute("SELECT 1 FROM attempts WHERE id=?", (item_id,)).fetchone():
            continue
        count_body = {k: body[k] for k in ("model", "system", "messages", "output_config")}
        estimate = post("/count_tokens", count_body)["input_tokens"]
        if type(estimate) is not int or not 0 < estimate <= COUNT_MAX:
            raise RuntimeError("Free preflight count exceeds the input limit or is invalid")
        with db:
            db.execute("BEGIN IMMEDIATE")
            committed = db.execute("SELECT COALESCE(SUM(MAX(reserved,COALESCE(cost,0))),0) FROM attempts").fetchone()[0]
            if committed + RESERVE > BUDGET:
                raise RuntimeError("Spending limit reached")
            db.execute("INSERT INTO attempts (id,reserved,status,counted) VALUES (?,?,?,?)",
                       (item_id, RESERVE, "pending", estimate))
        try:
            raw = post("", body)
        except Exception as exc:
            with db:
                db.execute("UPDATE attempts SET status='unresolved', detail=? WHERE id=?",
                           (type(exc).__name__, item_id))
            raise
        with db:
            db.execute("UPDATE attempts SET response=?, status='review' WHERE id=?",
                       (json.dumps(raw), item_id))
        cost = cost_for(raw)
        usage = raw["usage"]
        within = (raw.get("model") == MODEL and usage["input_tokens"] <= INPUT_ALLOWANCE
                  and usage["output_tokens"] <= MAX_OUTPUT)
        with db:
            db.execute("UPDATE attempts SET cost=?,status=? WHERE id=?",
                       (cost, "received" if within else "review", item_id))
        if not within:
            raise RuntimeError("Unexpected model or usage. Collection stopped.")


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field")
        result[key] = value
    return result


def decode(raw):
    if raw.get("stop_reason") == "refusal":
        return "refusal"
    if raw.get("stop_reason") == "max_tokens":
        return "truncated"
    if raw.get("stop_reason") != "end_turn":
        return "invalid"
    try:
        block, = raw["content"]
        if block["type"] != "text":
            return "invalid"
        value = json.loads(block["text"], object_pairs_hook=unique_fields)
        if (
            list(value) == ["brief_basis", "answer"]
            and isinstance(value["brief_basis"], str)
            and value["brief_basis"].strip()
            and value["answer"] in ("A", "B", "C", "D")
        ):
            return value["answer"]
    except (KeyError, TypeError, ValueError):
        pass
    return "invalid"


def outcome(key, answer):
    if answer not in ("A", "B"):
        return {"C": "equally_likely", "D": "insufficient_evidence"}.get(answer, answer)
    name = key["option_names"]["AB".index(answer)]
    matches_choice = name == key["chose_target"]
    matches_delivery = name == key["delivered_to_target"]
    if key["probe"] == "actual_delivery":
        return "actual_donor" if matches_delivery else "other_donor"
    if matches_choice and matches_delivery:
        return "both"
    if matches_choice:
        return "chosen_only"
    return "delivered_only" if matches_delivery else "neither"


def score(rows, records):
    keys = json.loads(checked_file("score-key.json", KEY_SHA))
    cells = defaultdict(Counter)
    pairs = defaultdict(dict)
    option_flips = defaultdict(list)
    event_orders = defaultdict(list)
    name_swaps = {field: defaultdict(list) for field in ("helpers", "recipients")}
    item_rows = []
    for r in rows:
        ident = r["id"]
        k = keys[ident]
        rec = records.get(ident)
        answer = "missing"
        if rec is not None:
            answer = decode(json.loads(rec["response"])) if rec["status"] == "received" else rec["status"]
        result = outcome(k, answer)
        cells[k["probe"] + "/" + k["delivery"]][result] += 1
        h, opts = tuple(k["history"]), tuple(k["option_names"])
        pairs[(k["delivery"], h, opts, k["target"])][k["probe"]] = result
        option_flips[(k["probe"], h, k["target"])].append(result)
        # Reversing evidence-line order preserves all events and displayed options.
        event_orders[(k["probe"], tuple(sorted(h)), opts, k["target"])].append(result)
        prompt = r["body"]["messages"][0]["content"]
        for field, (left, right) in (("helpers", ("Sam", "Priya")), ("recipients", ("Alex", "Jordan"))):
            flipped = re.sub(rf"\b({left}|{right})\b", lambda m, a=left, b=right: b if m[0] == a else a, prompt)
            name_swaps[field][min(prompt, flipped)].append(result)
        item_rows.append(dict(id=ident, answer=answer, category=result, **k))
    valid = {"both", "chosen_only", "delivered_only", "neither", "actual_donor", "other_donor",
             "equally_likely", "insufficient_evidence"}
    def flip_counts(groups):
        counts = Counter()
        for pair in groups.values():
            if len(pair) != 2:
                raise ValueError("Counterbalance pair missing from bank")
            a, b = pair
            counts["unscorable" if a not in valid or b not in valid else "same" if a == b else "changed"] += 1
        return counts
    joint = Counter((pair["actual_delivery"] + " | " + pair["future_choice"])
                    for (delivery, *_), pair in pairs.items() if delivery == "swapped")
    return {"cells": dict(cells), "matched_swapped_history_factual_and_forecast": joint,
            "option_order_pairs": flip_counts(option_flips),
            "evidence_order_pairs": flip_counts(event_orders),
            "name_swap_pairs": {k: flip_counts(v) for k, v in name_swaps.items()}, "items": item_rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "collect", "report"), nargs="?", default="check")
    args = parser.parse_args()
    rows = requests()
    plan = {"model": MODEL, "items": len(rows), "reserve_usd_at_list_prices": len(rows)*RESERVE/1e6,
            "local_spend_guard_usd": BUDGET/1e6}
    if args.mode == "check":
        score(rows, {})
        print(json.dumps(plan, indent=2))
        return
    path = ROOT / "pilot-records.sqlite3"
    if args.mode == "report" and not path.exists():
        raise SystemExit("No collection ledger exists.")
    if args.mode == "collect":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("Collection requires ANTHROPIC_API_KEY in the execution environment.")
        if time.strftime("%Y-%m-%d", time.gmtime()) >= "2026-11-30":
            raise SystemExit("The planned retirement date has arrived. No model substitution is configured.")
        import fcntl
        lock = (ROOT / "collection.lock").open("a")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another collector is active in this folder.")
    db = open_records(path)
    try:
        if args.mode == "collect":
            collect(db, rows, lambda url, body: api_post(url, body, os.environ["ANTHROPIC_API_KEY"]))
        records = {r["id"]: r for r in db.execute("SELECT * FROM attempts")}
        result = score(rows, records)
        result["billing"] = {"attempts_reserved": len(records), "known_usage_usd": sum(r["cost"] or 0 for r in records.values())/1e6,
                             "attempts_without_usage": sum(r["cost"] is None for r in records.values())}
        (ROOT / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k:v for k,v in result.items() if k != "items"}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
