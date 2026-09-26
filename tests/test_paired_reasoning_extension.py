"""Programmed fixtures only; no empirical answer is consulted or model called."""
import base64
import io
import json
import os
import subprocess
import sys
import urllib.error
from email.message import Message

import pytest

from wtrbench.paired import natural as n
from wtrbench.paired import open_replication as old
from wtrbench.paired import reasoning_extension as r
from wtrbench.paired import social as s


@pytest.fixture(scope="module")
def items():
    return s.generate_items()


@pytest.fixture(params=tuple(r.CONDITIONS))
def ext(request):
    return r.Extension(request.param)


def catalog(ext):
    return json.loads((r.ROOT / r.PROVIDER).read_text())["entries"][ext.condition]


def api(ext, k=0, answer="C", text=None, reasoning="Programmed trace, not empirical data."):
    return {"id": f"msg_{k}", "model": ext.model,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "reasoning_content": reasoning,
                "content": text if text is not None else json.dumps({
                    "brief_basis": "Programmed fixture, not empirical evidence.", "answer": answer})}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


def http(value, k=0, status=200):
    raw = value if isinstance(value, bytes) else n.wire(value).encode()
    return {"status": status, "body_base64": base64.b64encode(raw).decode(),
            "request_id": f"req_{k}", "content_type": "application/json"}


def row(ext, item, k=0, **kwargs):
    return {"item_id": item["item_id"], "request_body": ext.request_body(item),
            "http_response": http(api(ext, k, **kwargs), k)}


def canary(ext, **kwargs):
    return {"item_id": "technical-canary", "request_body": ext.canary_body(),
            "http_response": http(api(ext, "canary", **kwargs), "canary")}


def test_both_old_freezes_unchanged_and_stimuli_identical(ext, items):
    before = old.verify_freeze()
    after = r.verify_freeze()
    assert before["items_jsonl_sha256"] == after["items_jsonl_sha256"]
    assert after["total_max_requests"] == 290
    for item in items:
        a, b = old.request_body(item), ext.request_body(item)
        assert a["messages"] == b["messages"]
        assert a["response_format"] == b["response_format"]
        assert b["reasoning_effort"] == "high"
        assert (b["temperature"], b["top_p"], b["top_k"], b["min_p"]) == (0.6, 0.95, 20, 0)
        assert b["max_tokens"] == 32768
    other = r.Extension("32b-thinking" if ext.condition == "14b-thinking" else "14b-thinking")
    a, b = ext.request_body(items[0]), other.request_body(items[0])
    assert a.pop("model") != b.pop("model")
    assert a == b


@pytest.mark.parametrize("size", [0, 17, 144])
def test_frozen_scoring_equivalence_with_reasoning_present(ext, items, size):
    texts = [json.dumps({"brief_basis": "fixture", "answer": a}) for a in "ABCD"]
    texts += ['bad json', '{"answer":"A","brief_basis":"wrong order"}']
    old_rows, new_rows = [], []
    for k, item in enumerate(items[:size]):
        a = api(ext, k, text=texts[k % len(texts)])
        if k % 11 == 0:
            a["choices"][0]["finish_reason"] = "length"
        new_rows.append({"item_id": item["item_id"], "request_body": ext.request_body(item),
                         "http_response": http(a, k)})
        a["model"] = old.MODEL
        del a["choices"][0]["message"]["reasoning_content"]
        old_rows.append({"item_id": item["item_id"], "request_body": old.request_body(item),
                         "http_response": http(a, k)})
    expected = old.summarize(items, old_rows)
    actual = r.summarize_observations(ext.observations(items, new_rows))
    actual["protocol"] = expected["protocol"]
    assert actual == expected


@pytest.mark.parametrize("text", [
    '```json\n{"brief_basis":"x","answer":"A"}\n```',
    '{"answer":"A","brief_basis":"x"}',
    '{"brief_basis":"x","answer":"A","answer":"B"}',
    '{"brief_basis":"x","answer":"a"}',
    '{"brief_basis":" ","answer":"A"}',
    '{"brief_basis":"x","answer":"A","extra":0}',
    '<think>fixture</think>{"brief_basis":"x","answer":"A"}',
])
def test_no_final_answer_repair_even_if_reasoning_contains_valid_json(items, text):
    ext = r.Extension("14b-thinking")
    record = row(ext, items[0], text=text,
                 reasoning='{"brief_basis":"valid but never scored","answer":"A"}')
    obs = ext.observations(items, [record])
    assert obs[0]["semantic"] == "invalid" and obs[0]["raw"] == text
    assert obs[1]["semantic"] == "missing"


@pytest.mark.parametrize("reasoning", [None, "", " "])
def test_absent_social_trace_does_not_change_answer_but_canary_stops(ext, items, reasoning):
    record = row(ext, items[0], reasoning=reasoning)
    assert ext.observations(items, [record])[0]["semantic"] == "equal"
    assert not r.has_reasoning(r.api_response(record))
    with pytest.raises(ValueError, match="nonempty reasoning"):
        ext.validate_canary(canary(ext, reasoning=reasoning))


def test_canary_is_format_only_not_arithmetic_accuracy_gate(ext):
    for answer in "ABCD":
        ext.validate_canary(canary(ext, answer=answer))


@pytest.mark.parametrize("key,value", [
    ("reasoning_content", ["bad type"]), ("tool_calls", [{"id": "tool"}]),
    ("refusal", "no"), ("role", "user"),
])
def test_bad_envelope_content_invalid(items, key, value):
    ext = r.Extension("14b-thinking")
    response = api(ext)
    response["choices"][0]["message"][key] = value
    record = row(ext, items[0]); record["http_response"] = http(response)
    assert ext.observations(items, [record])[0]["semantic"] == "invalid"


@pytest.mark.parametrize("mutation", ["model", "message", "request", "order", "body", "fingerprint", "http", "envelope"])
def test_provenance_failure(items, mutation):
    ext = r.Extension("14b-thinking")
    records = [row(ext, items[0]), row(ext, items[1], 1)]
    response = api(ext, 1)
    if mutation == "model": response["model"] = "replacement/model"
    elif mutation == "message": response["id"] = "msg_0"
    elif mutation == "fingerprint": response["system_fingerprint"] = "new_backend"
    records[1]["http_response"] = http(response, 1)
    if mutation == "request": records[1]["http_response"]["request_id"] = "req_0"
    elif mutation == "order": records.reverse()
    elif mutation == "body": records[1]["request_body"]["temperature"] = 0
    elif mutation == "http": records[1]["http_response"]["status"] = 429
    elif mutation == "envelope": records[1]["http_response"] = http(b'not json', 1)
    with pytest.raises(ValueError): ext.validate(items, records)


@pytest.mark.parametrize("key,value", [
    ("model_name", "replacement"), ("deprecated", 0), ("replaced_by", "other"),
    ("quantization", "fp4"), ("tags", ["structured-output", "non-reasoning"]),
])
def test_catalog_drift_prevents_all_paid_calls(tmp_path, key, value):
    ext = r.Extension("14b-thinking")
    entry = catalog(ext); entry[key] = value
    calls = []
    with pytest.raises(ValueError):
        ext.collect(tmp_path, lambda body: calls.append(body), catalog=lambda: entry)
    assert not calls and not (tmp_path / "collection-started.json").exists()


@pytest.mark.parametrize("failure", ["no_reasoning", "inline_reasoning", "http", "envelope", "truncated"])
def test_failed_canary_preserved_and_never_launches_social(tmp_path, failure):
    ext = r.Extension("14b-thinking")
    response = api(ext, reasoning="" if failure == "no_reasoning" else "fixture trace")
    if failure == "inline_reasoning":
        response["choices"][0]["message"]["content"] = '<think>fixture</think>{"brief_basis":"x","answer":"A"}'
    if failure == "truncated": response["choices"][0]["finish_reason"] = "length"
    raw = b'not json' if failure == "envelope" else n.wire(response).encode()
    calls = []
    def send(body):
        calls.append(body)
        return http(raw, status=402 if failure == "http" else 200)
    with pytest.raises(ValueError): ext.collect(tmp_path, send, catalog=lambda: catalog(ext))
    assert len(calls) == 1 and (tmp_path / "responses.jsonl").read_bytes() == b''
    saved = json.loads((tmp_path / "canary.jsonl").read_text())
    assert base64.b64decode(saved["http_response"]["body_base64"]) == raw
    with pytest.raises(ValueError): ext.report(tmp_path)
    assert (tmp_path / "integrity-report.json").exists()
    with pytest.raises(FileExistsError): ext.collect(tmp_path, send, catalog=lambda: catalog(ext))
    assert len(calls) == 1


@pytest.mark.parametrize("stop_at", [0, 3])
def test_transport_failure_no_retry_and_preserved_prefix(tmp_path, stop_at):
    ext = r.Extension("14b-thinking")
    calls = []
    def send(body):
        k = len(calls); calls.append(body)
        if k == stop_at: raise TimeoutError("fixture")
        return http(api(ext, k), k)
    with pytest.raises(TimeoutError): ext.collect(tmp_path, send, catalog=lambda: catalog(ext))
    assert len(calls) == stop_at + 1
    assert json.loads((tmp_path / "transport-stop.json").read_text())["delivery_unknown"] is True
    if stop_at:
        result = ext.report(tmp_path)
        assert result["recorded"] == 2 and result["counts"]["missing"] == 142
        assert result["prospective_outcomes"]["classification"] == "uninterpretable_primary"
    else:
        with pytest.raises(ValueError, match="canary incomplete"): ext.report(tmp_path)


@pytest.mark.parametrize("mutation", ["message", "request", "fingerprint"])
def test_identity_cannot_change_between_canary_and_social(tmp_path, mutation):
    ext = r.Extension("14b-thinking")
    calls = []
    def send(body):
        k = len(calls); calls.append(body)
        a = api(ext, k)
        if mutation == "message": a["id"] = "same"
        if mutation == "fingerprint" and k: a["system_fingerprint"] = "new"
        return http(a, 0 if mutation == "request" else k)
    with pytest.raises(ValueError): ext.collect(tmp_path, send, catalog=lambda: catalog(ext))
    assert len(calls) == 2
    assert len((tmp_path / "responses.jsonl").read_text().splitlines()) == 1
    with pytest.raises(ValueError): ext.report(tmp_path)


def test_full_collection_snapshot_offline_replay_and_invalids_continue(tmp_path, ext):
    calls = []
    def send(body):
        k = len(calls); calls.append(body)
        a = api(ext, k, answer="ABCD"[k % 4])
        if k == 4: a["choices"][0]["finish_reason"] = "length"
        if k == 5: a["choices"][0]["message"]["reasoning_content"] = None
        return http(a, k)
    ext.collect(tmp_path, send, catalog=lambda: catalog(ext))
    assert len(calls) == 145 and calls[0] == ext.canary_body()
    expected = (tmp_path / "report.json").read_bytes()
    env = {**os.environ, "PYTHONPATH": str(tmp_path / "frozen-source/src")}
    for command in ["check", "report"]:
        subprocess.run([sys.executable, "-m", "wtrbench.paired.reasoning_extension", command,
                        "--condition", ext.condition, "--out", str(tmp_path)],
                       cwd=tmp_path, env=env, check=True, capture_output=True)
    assert expected == (tmp_path / "report.json").read_bytes()
    result = json.loads(expected)
    assert result["counts"]["invalid"] == 1 and result["counts"]["missing"] == 0
    assert result["social_responses_with_separate_reasoning"] == 143
    assert result["usage_all_calls"]["total_tokens"] == 2175
    assert result["usage_social"]["total_tokens"] == 2160
    assert result["usage_canary"]["total_tokens"] == 15
    assert result["usage_all_calls"]["estimated_cost"] is None
    assert result["data_origin"] == "programmed_test_fixture"
    assert result["scientific_pass_fail"] is None
    assert len(json.loads((tmp_path / "pair-audit.json").read_text())) == 216
    for source in (*r.SOURCE_FILES, r.FREEZE):
        assert (tmp_path / "frozen-source" / source).read_bytes() == (r.ROOT / source).read_bytes()
    with pytest.raises(FileExistsError): ext.collect(tmp_path, send, catalog=lambda: catalog(ext))


@pytest.mark.parametrize("d_count,signs,invalid,expected", [
    (75, 6, 0, "D_lower__six_scenario_criterion_met"),
    (75, 5, 0, "D_lower__six_scenario_criterion_not_met"),
    (76, 6, 0, "D_not_lower__six_scenario_criterion_met"),
    (77, 0, 0, "D_not_lower__six_scenario_criterion_not_met"),
    (0, 6, 1, "uninterpretable_primary"),
])
def test_prospective_categories_keep_output_failure_distinct(d_count, signs, invalid, expected):
    counts = dict.fromkeys(r.SEMANTICS, 0)
    counts.update(insufficient=d_count, invalid=invalid)
    result = {"cells": [{"probe": "valuation", "counts": counts}],
              "scenarios_with_both_net_directions": signs}
    assert r.outcome_summary(result)["classification"] == expected


def test_transport_long_budget_no_redirect_or_retry(monkeypatch):
    calls = []
    headers = Message(); headers["x-request-id"] = "error-request"
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            assert request.full_url == r.ENDPOINT and timeout == 600
            assert request.headers["Authorization"] == "Bearer fixture-secret"
            raise urllib.error.HTTPError(r.ENDPOINT, 429, "fixture", headers, io.BytesIO(b'raw-error'))
    monkeypatch.setenv("DEEPINFRA_API_KEY", "fixture-secret")
    monkeypatch.setattr(r.urllib.request, "build_opener", lambda handler: Opener())
    result = r.send_deepinfra({"model": "Qwen/Qwen3-14B"})
    assert len(calls) == 1 and result["status"] == 429
    assert base64.b64decode(result["body_base64"]) == b'raw-error'
    assert "fixture-secret" not in n.wire(result)


@pytest.mark.parametrize("confirmation,attempt,has_key", [(None, "1", True), (144, "1", True), (145, "2", True), (145, "1", False)])
def test_cli_requires_145_first_attempt_key(monkeypatch, confirmation, attempt, has_key):
    args = ["extension", "run", "--condition", "14b-thinking"]
    if confirmation: args += ["--confirm", str(confirmation)]
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", attempt)
    if has_key: monkeypatch.setenv("DEEPINFRA_API_KEY", "fixture")
    else: monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    def forbidden(*args, **kwargs): raise AssertionError("must not collect")
    monkeypatch.setattr(r.Extension, "collect", forbidden)
    with pytest.raises(SystemExit): r.main()


def test_artifact_tampering_rejected(tmp_path):
    ext = r.Extension("14b-thinking")
    def send(body): raise TimeoutError("fixture")
    with pytest.raises(TimeoutError): ext.collect(tmp_path, send, catalog=lambda: catalog(ext))
    (tmp_path / "requests.jsonl").write_text("altered\n")
    with pytest.raises(ValueError, match="altered"): ext.report(tmp_path)


def test_workflow_collects_both_fixed_conditions_even_if_one_fails():
    workflow = (r.ROOT / '.github/workflows/paired-reasoning-v1.yml').read_text()
    assert 'condition: [14b-thinking, 32b-thinking]' in workflow
    assert 'fail-fast: false' in workflow
    assert 'workflow_dispatch:' in workflow and 'schedule:' not in workflow
    assert 'default: generate' in workflow and 'COLLECT_290' in workflow
    assert 'include-hidden-files: true' in workflow
    assert 'secrets.DEEPINFRA_API_KEY' in workflow
