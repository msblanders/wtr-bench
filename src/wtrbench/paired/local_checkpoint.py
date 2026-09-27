"""Pinned local Qwen3-32B bridge. Only run --confirm 145 generates model responses."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wtrbench.paired import natural, social
from wtrbench.paired import reasoning_extension as prior

ROOT = prior.ROOT
PROTOCOL = "paired-local-v1"
MODEL = "Qwen/Qwen3-32B"
REVISION = "9216db5781bf21249d130ec9da846c4624c16137"
FREEZE = "protocols/paired-local-v1.json"
CHECKPOINT = "protocols/paired-local-v1-checkpoint.json"
PLAN = "docs/paired-local-v1.md"
BACKEND = "experiments/local-checkpoint/backend.py"
MAX_TOKENS = 32768
SEED = 26092700
EOS = (151645, 151643)
CLOSE = 151668
OPEN = 151667
SOURCE_FILES = (*prior.SOURCE_FILES, prior.FREEZE,
                "src/wtrbench/paired/local_checkpoint.py",
                "tests/test_paired_local_checkpoint.py", BACKEND,
                "experiments/local-checkpoint/smoke.py",
                "experiments/local-checkpoint/run.sh",
                "experiments/local-checkpoint/pyproject.toml",
                "experiments/local-checkpoint/uv.lock",
                ".github/workflows/local-checkpoint-check.yml", PLAN, CHECKPOINT)
write_json = social.write_json


def checkpoint_spec() -> dict[str, Any]:
    result: dict[str, Any] = json.loads((ROOT / CHECKPOINT).read_text())
    if result["model"] != MODEL or result["revision"] != REVISION:
        raise ValueError("Checkpoint identity mismatch")
    return result


def schedule() -> list[dict[str, Any]]:
    extension = prior.Extension("32b-thinking")
    bodies = [extension.canary_body(), *[extension.request_body(i) for i in social.generate_items()]]
    ids = ["technical-canary", *[i["item_id"] for i in social.generate_items()]]
    return [{"item_id": item_id, "model": MODEL, "revision": REVISION,
             "dtype": "bfloat16", "enable_thinking": True, "seed": SEED + index,
             "messages": body["messages"],
             "schema": body["response_format"]["json_schema"]["schema"],
             "max_new_tokens": MAX_TOKENS, "temperature": 0.6,
             "top_p": 0.95, "top_k": 20, "min_p": 0.0}
            for index, (item_id, body) in enumerate(zip(ids, bodies))]


def manifest() -> dict[str, Any]:
    return {"protocol": PROTOCOL, "model": MODEL, "revision": REVISION,
            "prior_hosted_run": 36281301593, "social_count": 144, "canary_count": 1,
            "items_jsonl_sha256": natural.stream_hash(social.generate_items()),
            "requests_jsonl_sha256": natural.stream_hash(schedule()),
            "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                              for p in SOURCE_FILES}}


def verify_freeze() -> dict[str, Any]:
    previous = prior.verify_freeze()
    actual = manifest()
    if previous["items_jsonl_sha256"] != actual["items_jsonl_sha256"]:
        raise ValueError("Original social item stream changed")
    if json.loads((ROOT / FREEZE).read_text()) != actual:
        raise ValueError("Local freeze mismatch; do not rewrite a collected protocol")
    return actual


def verify_checkpoint(snapshot: Path) -> dict[str, Any]:
    spec = checkpoint_spec()
    for name, expected in spec["files"].items():
        file = snapshot / name
        if file.stat().st_size != expected["size"]:
            raise ValueError(f"Checkpoint file size mismatch: {name}")
        h = hashlib.sha256()
        with file.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != expected["sha256"]:
            raise ValueError(f"Checkpoint checksum mismatch: {name}")
    return spec


def split_tokens(tokens: list[int], decode: Callable[..., str]) -> dict[str, Any]:
    """Use the documented separator, without JSON repair or special-token stripping."""
    ended = bool(tokens) and tokens[-1] in EOS
    body = tokens[:-1] if ended else tokens
    separators = [i for i, t in enumerate(body) if t == CLOSE]
    structural = (len(separators) == 1 and bool(body) and body[0] == OPEN
                  and body.count(OPEN) == 1 and not any(t in EOS for t in body))
    cut = separators[0] if separators else len(body)
    start = 1 if body and body[0] == OPEN else 0
    return {"reasoning": decode(body[start:cut], skip_special_tokens=False),
            "final_content": decode(body[cut + 1:], skip_special_tokens=False) if separators else "",
            "stop_reason": "eos" if ended else "length",
            "structure_valid": structural,
            "thinking_token_count": cut,
            "final_token_count": len(body) - cut - 1 if separators else 0}


def parsed_response(item: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    acceptable = (response.get("stop_reason") == "eos"
                  and response.get("structure_valid") is True
                  and isinstance(response.get("reasoning"), str)
                  and bool(response["reasoning"].strip()))
    return natural.decode(item, {"stop_reason": "end_turn" if acceptable else None,
                                "content": [{"type": "text", "text": response.get("final_content")}]})


def load_backend() -> Any:
    spec = importlib.util.spec_from_file_location("wtrbench_local_backend", ROOT / BACKEND)
    if spec is None or spec.loader is None:
        raise ValueError("Missing optional backend")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_record(file: Any, request: dict[str, Any], response: dict[str, Any]) -> None:
    payload = {"request": request, "response": response}
    row = {**payload, "payload_sha256": hashlib.sha256(natural.wire(payload).encode()).hexdigest()}
    file.write(natural.wire(row) + "\n")
    file.flush()
    os.fsync(file.fileno())


def collect(out: Path, factory: Callable[[], Callable[..., dict[str, Any]]],
            runtime: dict[str, Any], *, data_origin: str = "programmed_test_fixture") -> None:
    frozen = verify_freeze()
    # An existing output folder is never reused, including after an interrupted load.
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "freeze.json", frozen)
    write_json(out / "collection-started.json", {
        "protocol": PROTOCOL, "model": MODEL, "revision": REVISION,
        "data_origin": data_origin, "started_utc": datetime.now(UTC).isoformat(),
        "runtime": runtime, "max_retries": 0, "freeze": frozen,
    })
    for path in (*SOURCE_FILES, FREEZE):
        dest = out / "frozen-source" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / path).read_bytes())
    requests = schedule()
    (out / "requests.jsonl").write_text("".join(natural.wire(r) + "\n" for r in requests))
    (out / "items.jsonl").write_text("".join(natural.wire(i) + "\n" for i in social.generate_items()))
    stage = "load-model"
    try:
        with (out / "responses.jsonl").open("x") as fh:
            send = factory()
            for index, request in enumerate(requests):
                stage = request["item_id"]
                write_json(out / "last-attempt.json", request)
                response = send(request, out / "last-input.json")
                append_record(fh, request, response)  # Persist before parsing/gating.
                if index == 0 and parsed_response(social.generate_items()[0], response)["answer"] is None:
                    raise ValueError("Technical canary requires nonempty thinking and valid final JSON")
                if index == 0 or index % 12 == 0:
                    print(f"Recorded canary + {index}/144 social responses", flush=True)
    except Exception as exc:
        write_json(out / "technical-stop.json", {"stage": stage, "exception_type": type(exc).__name__,
                                                 "message": str(exc)})
        raise
    finally:
        report(out)


def validate_rows(rows: list[dict[str, Any]]) -> None:
    expected = schedule()
    if len(rows) > len(expected):
        raise ValueError("Too many response rows")
    for row, request in zip(rows, expected):
        if row.get("request") != request:
            raise ValueError("Unknown, duplicate, changed or reordered request")
        payload = {k: row[k] for k in ("request", "response")}
        if hashlib.sha256(natural.wire(payload).encode()).hexdigest() != row.get("payload_sha256"):
            raise ValueError("Response checksum mismatch")
        response = row["response"]
        tokens = response.get("generated_token_ids")
        if not isinstance(tokens, list) or not tokens or any(type(t) is not int for t in tokens):
            raise ValueError("Missing generated token record")
        if len(tokens) > MAX_TOKENS:
            raise ValueError("Output exceeded the fixed token cap")
        # Check structural fields against tokens without loading the tokenizer or model.
        split = split_tokens(tokens, lambda *a, **k: "")
        for key in ("stop_reason", "structure_valid", "thinking_token_count", "final_token_count"):
            if response.get(key) != split[key]:
                raise ValueError("Response structure disagrees with token record")


def report(out: Path) -> dict[str, Any]:
    frozen = verify_freeze()
    cfg = json.loads((out / "collection-started.json").read_text())
    if (cfg.get("protocol") != PROTOCOL or cfg.get("model") != MODEL
            or cfg.get("revision") != REVISION or cfg.get("freeze") != frozen
            or json.loads((out / "freeze.json").read_text()) != frozen):
        raise ValueError("Run identity/freeze mismatch")
    for path, key in (("requests.jsonl", "requests_jsonl_sha256"),
                      ("items.jsonl", "items_jsonl_sha256")):
        if hashlib.sha256((out / path).read_bytes()).hexdigest() != frozen[key]:
            raise ValueError("Run stimulus artifact changed")
    rows = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines()]
    validate_rows(rows)
    canary_ok = bool(rows) and parsed_response(social.generate_items()[0], rows[0]["response"])["answer"] is not None
    if not canary_ok:
        result = {"protocol": PROTOCOL, "completion": "TECHNICAL_STOP", "canary_passed": False,
                  "recorded_social": max(0, len(rows) - 1), "scientific_report": None,
                  "data_origin": cfg["data_origin"]}
        write_json(out / "report.json", result)
        (out / "report.md").write_text("# Local checkpoint: technical stop\n\nNo interpretable social result. See technical-stop.json and raw records.\n")
        return result
    obs = []
    for index, item in enumerate(social.generate_items()):
        response = rows[index + 1]["response"] if index + 1 < len(rows) else None
        parsed = parsed_response(item, response or {})
        obs.append({**{k: item[k] for k in ("item_id", "scenario", "probe", "name_assignment",
                                          "position", "repetition")},
                    "answer": parsed["answer"], "brief_basis": parsed["brief_basis"],
                    "semantic": "missing" if response is None else (parsed["semantic"] or "invalid"),
                    "stop_reason": response.get("stop_reason") if response else None,
                    "raw": response.get("final_content", "") if response else ""})
    result = prior.summarize_observations(obs)
    valid = all(r["semantic"] not in ("missing", "invalid") for r in obs if r["probe"] != "ability_different")
    directions = result["scenarios_with_both_net_directions"] == 6 if valid else None
    result.update(protocol=PROTOCOL, model=MODEL, revision=REVISION, dtype="bfloat16",
                  data_origin=cfg["data_origin"], canary_passed=True,
                  primary_complete_and_valid=valid,
                  bridge_outcome=("primary_pattern_reproduced" if directions else
                                  "primary_pattern_not_reproduced") if valid else "incomplete_or_invalid_primary",
                  runtime=cfg["runtime"],
                  total_generated_tokens=sum(len(r["response"]["generated_token_ids"]) for r in rows),
                  technical_stop=(out / "technical-stop.json").exists())
    write_json(out / "report.json", result)
    write_json(out / "pair-audit.json", social.pair_audit(obs))
    with (out / "answer-audit.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(obs[0]))
        writer.writeheader()
        writer.writerows(obs)
    lines = [f"# {PROTOCOL}: {result['completion']}", "", f"Origin: {cfg['data_origin']}.",
             f"{MODEL} @ {REVISION}; BF16; thinking enabled; temperature 0.6.", "",
             "| Probe | Unable | Unwilling | Equal | Insufficient | Invalid | Missing |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for probe, counts in result["by_probe"].items():
        lines.append(f"| {probe} | " + " | ".join(str(counts[s]) for s in social.SEMANTICS) + " |")
    cross = sum(c["counts"]["predicted_crossover"] for c in result["crossovers"])
    lines += ["", f"Predicted matched crossovers: {cross}/48.",
              f"Scenarios with both predicted net directions: {result['scenarios_with_both_net_directions']}/6.",
              f"Prospective descriptive outcome: {result['bridge_outcome']}.", "",
              "See report.json and pair-audit.json for all cells, passes and name/order/repeat disagreements.",
              "This is a checkpoint/implementation bridge, not a causal mechanism study or exact hosted replay.",
              "Six scenarios; repeated forms are not independent scenarios. No scientific accuracy/pass score."]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return result


def package(out: Path) -> Path:
    report(out)
    checksums = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(out.rglob("*")) if p.is_file() and p.name != "checksums.json"}
    write_json(out / "checksums.json", checksums)
    target = out.parent / (out.name + ".zip")
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                zf.write(path, str(path.relative_to(out)))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "doctor", "download", "run", "report", "package"))
    parser.add_argument("--cache", type=Path, default=Path("runs/checkpoint-cache"))
    parser.add_argument("--out", type=Path, default=Path("runs/paired-local-v1"))
    parser.add_argument("--confirm", type=int)
    args = parser.parse_args()
    verify_freeze()
    if args.command == "check":
        print("All previous freezes and the local freeze verified. 144 identical social items; no model loaded.")
    elif args.command == "report":
        print(json.dumps(report(args.out), indent=2))
    elif args.command == "package":
        print(package(args.out))
    elif args.command == "run":
        if args.confirm != 145:
            parser.error("Requires --confirm 145: one technical canary plus the frozen 144 social items")
        if args.out.exists():
            parser.error("Output folder already exists; preserve it. No automatic resume/recollection.")
        backend = load_backend()
        runtime = backend.doctor()
        snapshot = backend.cached_snapshot(checkpoint_spec(), args.cache)
        print("Verifying all checkpoint file hashes before loading weights...", flush=True)
        runtime["verified_checkpoint"] = verify_checkpoint(snapshot)
        collect(args.out, lambda: backend.Backend(snapshot, schedule()[0]["schema"]),
                runtime, data_origin="local_transformers_checkpoint")
        print(f"Finished. Package with: python -m wtrbench.paired.local_checkpoint package --out {args.out}")
    else:
        backend = load_backend()
        if args.command == "doctor":
            print(json.dumps(backend.doctor(), indent=2))
        else:
            snapshot = backend.download(checkpoint_spec(), args.cache)
            verify_checkpoint(snapshot)
            print(f"Downloaded and verified the pinned checkpoint: {snapshot}")


if __name__ == "__main__":
    main()
