from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from wtrbench.paired import local_checkpoint as local
from wtrbench.paired import natural, social
from wtrbench.paired import reasoning_extension as prior


def response(answer: str = "D", *, length: bool = False, thinking: bool = True) -> dict:
    tokens = [local.OPEN, 100, local.CLOSE, 101] + ([] if length else [local.EOS[0]])
    texts = {100: "A programmed fixture." if thinking else "", 101: json.dumps({"brief_basis": "Fixture", "answer": answer})}
    parts = local.split_tokens(tokens, lambda ids, **_: "".join(texts.get(i, "") for i in ids))
    return {**parts, "generated_token_ids": tokens, "input_token_ids": [200],
            "rendered_prompt": "fixture", "raw_text": "fixture"}


def collect_fixture(out: Path, fail_at: int | None = None, bad_canary: bool = False):
    def send(request, path):
        index = request["seed"] - local.SEED
        if index == fail_at:
            raise RuntimeError("programmed interruption")
        if index == 0:
            return response("B", thinking=not bad_canary)  # Wrong arithmetic still passes.
        item = social.generate_items()[index - 1]
        semantic = "unable" if item["probe"] == "valuation" else "unwilling"
        answer = next(k for k, v in item["semantic_map"].items() if v == semantic)
        return response(answer)
    local.collect(out, lambda: send, {"fixture": True})


def test_freeze_and_identical_messages():
    frozen = local.verify_freeze()
    assert frozen["items_jsonl_sha256"] == prior.verify_freeze()["items_jsonl_sha256"]
    requests = local.schedule()
    assert len(requests) == 145
    assert len({r["seed"] for r in requests}) == 145
    ext = prior.Extension("32b-thinking")
    for request, item in zip(requests[1:], social.generate_items()):
        old = ext.request_body(item)
        assert request["messages"] == old["messages"]
        assert request["schema"] == old["response_format"]["json_schema"]["schema"]
    assert requests[0]["messages"] == ext.canary_body()["messages"]


@pytest.mark.parametrize("answer", ["A", "B", "C", "D"])
def test_original_strict_decoder(answer):
    parsed = local.parsed_response(social.generate_items()[0], response(answer))
    assert parsed["answer"] == answer


@pytest.mark.parametrize("raw", ['{"answer":"A","brief_basis":"x"}',
                                '{"brief_basis":"x","answer":"A","answer":"B"}',
                                '```json\n{"brief_basis":"x","answer":"A"}\n```',
                                '{"brief_basis":" ","answer":"A"}',
                                '{"brief_basis":"x","answer":"a"}'])
def test_no_answer_repair(raw):
    r = response()
    r["final_content"] = raw
    assert local.parsed_response(social.generate_items()[0], r)["answer"] is None


@pytest.mark.parametrize("kwargs", [{"length": True}, {"thinking": False}])
def test_truncated_or_empty_thinking_invalid(kwargs):
    assert local.parsed_response(social.generate_items()[0], response(**kwargs))["answer"] is None


@pytest.mark.parametrize("tokens", [[], [100, 101, 151645], [100, 151668, 151668, 101, 151645],
                                   [100, 151645, 151668, 101, 151645]])
def test_separator_integrity(tokens):
    assert local.split_tokens(tokens, lambda *a, **k: "text")["structure_valid"] is False


def test_complete_and_package(tmp_path):
    out = tmp_path / "run"
    collect_fixture(out)
    result = local.report(out)
    assert result["data_origin"] == "programmed_test_fixture"
    assert result["recorded"] == 144
    assert result["scenarios_with_both_net_directions"] == 6
    assert result["bridge_outcome"] == "primary_pattern_reproduced"
    assert sum(c["counts"]["predicted_crossover"] for c in result["crossovers"]) == 48
    assert local.package(out).is_file()
    with pytest.raises(FileExistsError):
        collect_fixture(out)


def test_partial_failure_retained(tmp_path):
    out = tmp_path / "run"
    with pytest.raises(RuntimeError):
        collect_fixture(out, fail_at=7)
    result = local.report(out)
    assert result["recorded"] == 6
    assert result["counts"]["missing"] == 138
    assert result["technical_stop"] is True
    assert result["bridge_outcome"] == "incomplete_or_invalid_primary"
    assert local.package(out).is_file()


def test_canary_stops_before_social(tmp_path):
    out = tmp_path / "run"
    with pytest.raises(ValueError, match="canary"):
        collect_fixture(out, bad_canary=True)
    assert len((out / "responses.jsonl").read_text().splitlines()) == 1
    assert local.report(out)["scientific_report"] is None


def test_model_load_failure_retained(tmp_path):
    def fail():
        raise RuntimeError("load failure")
    out = tmp_path / "run"
    with pytest.raises(RuntimeError):
        local.collect(out, fail, {})
    assert local.report(out)["completion"] == "TECHNICAL_STOP"
    assert local.package(out).is_file()


@pytest.mark.parametrize("mutation", ["request", "response", "reorder", "duplicate", "token_structure"])
def test_row_integrity(tmp_path, mutation):
    out = tmp_path / "run"
    collect_fixture(out)
    rows = [json.loads(x) for x in (out / "responses.jsonl").read_text().splitlines()]
    rows = copy.deepcopy(rows)
    if mutation == "request":
        rows[1]["request"]["seed"] += 1
    elif mutation == "response":
        rows[1]["response"]["final_content"] = "changed"
    elif mutation == "reorder":
        rows[1], rows[2] = rows[2], rows[1]
    elif mutation == "duplicate":
        rows[2] = rows[1]
    else:
        rows[1]["response"]["structure_valid"] = False
        payload = {k: rows[1][k] for k in ("request", "response")}
        rows[1]["payload_sha256"] = hashlib.sha256(natural.wire(payload).encode()).hexdigest()
    with pytest.raises(ValueError):
        local.validate_rows(rows)


def test_checkpoint_hash_detects_changed_bytes(tmp_path, monkeypatch):
    content = b"tiny fake weights"
    p = tmp_path / "weights"
    p.write_bytes(content)
    spec = {"files": {"weights": {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}}}
    monkeypatch.setattr(local, "checkpoint_spec", lambda: spec)
    assert local.verify_checkpoint(tmp_path) == spec
    p.write_bytes(b"X" + content[1:])
    with pytest.raises(ValueError, match="checksum"):
        local.verify_checkpoint(tmp_path)
