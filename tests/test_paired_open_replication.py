"""Programmed fixtures only. No test or CI action makes a model call."""
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
from wtrbench.paired import open_replication as r
from wtrbench.paired import social as s


@pytest.fixture(scope="module")
def items():
    return s.generate_items()


def catalog():
    return json.loads((r.ROOT / r.PROVIDER).read_text())["entry"]


def api(k=0, answer="C", text=None):
    return {"id": f"msg_{k}", "object": "chat.completion", "model": r.MODEL,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": text if text is not None else json.dumps({
                    "brief_basis": "Programmed fixture, not empirical evidence.", "answer": answer})}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


def http(value, k=0, status=200):
    raw = value if isinstance(value, bytes) else n.wire(value).encode()
    return {"status": status, "body_base64": base64.b64encode(raw).decode(),
            "request_id": f"req_{k}", "content_type": "application/json"}


def row(item, k=0, answer="C", text=None):
    return {"item_id": item["item_id"], "request_body": r.request_body(item),
            "http_response": http(api(k, answer, text), k)}


def test_identical_frozen_items_and_response_contract(items):
    old, new = s.verify_freeze(), r.verify_freeze()
    assert old["items_jsonl_sha256"] == new["items_jsonl_sha256"] == (
        "8544ce8f81447f4074e21efa8b8af013409c11eba4940640765f03f608a1890e")
    assert new["request_bodies_jsonl_sha256"] != old["request_bodies_jsonl_sha256"]
    for item in items:
        a, b = n.request_body(item), r.request_body(item)
        assert b["messages"] == [{"role": "system", "content": a["system"]}, *a["messages"]]
        assert b["response_format"]["json_schema"]["schema"] == a["output_config"]["format"]["schema"]
        assert b["temperature"] == a["temperature"] == 0
        assert b["max_tokens"] == a["max_tokens"] == 256
        assert b["reasoning_effort"] == "none"
        assert b["model"] == r.MODEL and b["stream"] is False and b["n"] == 1


@pytest.mark.parametrize("size", [0, 17, 144])
def test_scoring_equivalence_with_original_for_all_semantics(items, size):
    # Includes predicted/reversed directions, C, D, invalid JSON, wrong order and truncation.
    texts = [json.dumps({"brief_basis": "fixture", "answer": a}) for a in "ABCD"]
    texts += ['bad json', '{"answer":"A","brief_basis":"wrong order"}']
    original, replica = [], []
    for k, item in enumerate(items[:size]):
        text = texts[k % len(texts)]
        stop = "length" if k % 11 == 0 else "stop"
        response = api(k, text=text)
        response["choices"][0]["finish_reason"] = stop
        replica.append({"item_id": item["item_id"], "request_body": r.request_body(item),
                        "http_response": http(response, k)})
        original.append({"item_id": item["item_id"], "request_body": n.request_body(item),
                         "request_id": f"req_{k}", "api_response": {
                             "id": f"msg_{k}", "model": n.MODEL,
                             "stop_reason": "end_turn" if stop == "stop" else "max_tokens",
                             "content": [{"type": "text", "text": text}]}})
    a, b = s.summarize(items, original), r.summarize(items, replica)
    b["protocol"] = a["protocol"]
    for cell in b["cells"]:
        for answer in cell["answers"]:
            answer["stop_reason"] = {"stop": "end_turn", "length": "max_tokens"}.get(answer["stop_reason"])
    assert a == b
    assert s.pair_audit(s.observations(items, original)) == r.pair_audit(r.observations(items, replica))


@pytest.mark.parametrize("text", [
    '```json\n{"brief_basis":"x","answer":"A"}\n```',
    '{"answer":"A","brief_basis":"x"}',
    '{"brief_basis":"x","answer":"A","answer":"B"}',
    '{"brief_basis":"x","answer":"a"}',
    '{"brief_basis":" ","answer":"A"}',
    '{"brief_basis":"x","answer":"A","extra":0}',
    '<think></think>{"brief_basis":"x","answer":"A"}',
])
def test_invalid_content_is_not_repaired(items, text):
    obs = r.observations(items, [row(items[0], text=text)])
    assert obs[0]["semantic"] == "invalid" and obs[0]["raw"] == text
    assert obs[1]["semantic"] == "missing"


@pytest.mark.parametrize("key,value", [
    ("reasoning_content", "unexpected reasoning"), ("reasoning", "unexpected"),
    ("tool_calls", [{"id": "tool"}]), ("refusal", "no"), ("role", "user"),
])
def test_nonstandard_completion_is_invalid(items, key, value):
    value_api = api()
    value_api["choices"][0]["message"][key] = value
    record = row(items[0]); record["http_response"] = http(value_api)
    assert r.observations(items, [record])[0]["semantic"] == "invalid"


@pytest.mark.parametrize("mutation", ["model", "message", "request", "order", "body", "fingerprint", "http", "envelope"])
def test_provenance_failures_stop(items, mutation):
    records = [row(items[0]), row(items[1], 1)]
    response = api(1)
    if mutation == "model": response["model"] = "replacement/model"
    elif mutation == "message": response["id"] = "msg_0"
    elif mutation == "fingerprint": response["system_fingerprint"] = "new_backend"
    records[1]["http_response"] = http(response, 1)
    if mutation == "request": records[1]["http_response"]["request_id"] = "req_0"
    elif mutation == "order": records.reverse()
    elif mutation == "body": records[1]["request_body"]["temperature"] = 0.7
    elif mutation == "http": records[1]["http_response"]["status"] = 429
    elif mutation == "envelope": records[1]["http_response"] = http(b'not json', 1)
    with pytest.raises(ValueError): r.validate(items, records)


@pytest.mark.parametrize("key,value", [
    ("model_name", "replacement"), ("deprecated", 0), ("replaced_by", "other"),
    ("quantization", "fp4"), ("tags", ["openai"]),
])
def test_catalog_drift_prevents_model_calls(tmp_path, key, value):
    entry = catalog(); entry[key] = value
    calls = []
    with pytest.raises(ValueError):
        r.collect(tmp_path, lambda body: calls.append(body), catalog=lambda: entry)
    assert not calls and not (tmp_path / "collection-started.json").exists()
    assert json.loads((tmp_path / "provider-preflight.json").read_text()) == entry


@pytest.mark.parametrize("bad", [b'not-json', b'{"model":"wrong"}', b'{"id":"x","id":"y"}'])
def test_raw_bytes_survive_integrity_failure(tmp_path, bad):
    calls = []
    def send(body):
        calls.append(body)
        return http(bad)
    with pytest.raises(ValueError): r.collect(tmp_path, send, catalog=catalog)
    assert len(calls) == 1
    record = json.loads((tmp_path / "responses.jsonl").read_text())
    assert base64.b64decode(record["http_response"]["body_base64"]) == bad
    assert (tmp_path / "integrity-stop.json").exists()
    with pytest.raises(ValueError): r.report(tmp_path)
    assert json.loads((tmp_path / "integrity-report.json").read_text())["completion"] == "INTEGRITY_STOP"
    with pytest.raises(FileExistsError): r.collect(tmp_path, send, catalog=catalog)
    assert len(calls) == 1


def test_partial_transport_no_retry_and_missing_denominator(tmp_path):
    calls = []
    def send(body):
        k = len(calls); calls.append(body)
        if k == 2: raise TimeoutError("fixture")
        return http(api(k), k)
    with pytest.raises(TimeoutError): r.collect(tmp_path, send, catalog=catalog)
    assert len(calls) == 3
    result = r.report(tmp_path)
    assert result["recorded"] == 2 and result["counts"]["missing"] == 142
    assert result["counts"]["equal"] == 2 and result["completion"] == "INCOMPLETE"
    assert json.loads((tmp_path / "transport-stop.json").read_text())["delivery_unknown"] is True


def test_full_collection_snapshot_independent_reproduction(tmp_path, items):
    calls = []
    def send(body):
        k = len(calls); calls.append(body)
        return http(api(k, "ABCD"[k % 4]), k)
    r.collect(tmp_path, send, catalog=catalog)
    assert len(calls) == 144
    assert (tmp_path / "frozen-source/.github/workflows/paired-open-v1.yml").exists()
    expected = (tmp_path / "report.json").read_bytes()
    cfg = json.loads((tmp_path / "collection-started.json").read_text())
    assert cfg["data_origin"] == "programmed_test_fixture"
    env = {**os.environ, "PYTHONPATH": str(tmp_path / "frozen-source/src")}
    subprocess.run([sys.executable, "-m", "wtrbench.paired.open_replication", "check"],
                   cwd=tmp_path, env=env, check=True, capture_output=True)
    subprocess.run([sys.executable, "-m", "wtrbench.paired.open_replication", "report",
                    "--out", str(tmp_path)], cwd=tmp_path, env=env, check=True, capture_output=True)
    assert (tmp_path / "report.json").read_bytes() == expected
    result = json.loads(expected)
    assert result["completion"] == "COMPLETE" and result["usage"]["total_tokens"] == 2160
    assert result["usage"]["estimated_cost"] is None
    assert result["scientific_pass_fail"] is None
    assert len(json.loads((tmp_path / "pair-audit.json").read_text())) == 216
    assert (tmp_path / "items.jsonl").read_text() == ''.join(n.wire(i) + '\n' for i in items)
    with pytest.raises(FileExistsError): r.collect(tmp_path, send, catalog=catalog)


def test_real_transport_preserves_http_error_and_never_retries(monkeypatch):
    calls = []
    headers = Message(); headers["x-request-id"] = "error-request"
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            assert request.full_url == r.ENDPOINT and timeout == 120
            assert request.headers["Authorization"] == "Bearer fixture-secret"
            raise urllib.error.HTTPError(r.ENDPOINT, 429, "fixture", headers, io.BytesIO(b'raw-error'))
    monkeypatch.setenv("DEEPINFRA_API_KEY", "fixture-secret")
    monkeypatch.setattr(r.urllib.request, "build_opener", lambda handler: Opener())
    result = r.send_deepinfra({"model": r.MODEL})
    assert len(calls) == 1 and result["status"] == 429
    assert base64.b64decode(result["body_base64"]) == b'raw-error'
    assert "fixture-secret" not in n.wire(result)
    assert r.NoRedirect().redirect_request(None, None, None, None, None, None) is None


@pytest.mark.parametrize("confirmation,attempt,has_key", [(None, "1", True), (144, "2", True), (144, "1", False)])
def test_cli_requires_confirmation_first_attempt_and_key(monkeypatch, confirmation, attempt, has_key):
    args = ["replication", "run"] + (["--confirm", str(confirmation)] if confirmation else [])
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", attempt)
    if has_key: monkeypatch.setenv("DEEPINFRA_API_KEY", "fixture")
    else: monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    def forbidden(*args, **kwargs): raise AssertionError("must not collect")
    monkeypatch.setattr(r, "collect", forbidden)
    with pytest.raises(SystemExit): r.main()


def test_report_rejects_altered_request_artifact(tmp_path):
    def send(body): raise TimeoutError("fixture")
    with pytest.raises(TimeoutError): r.collect(tmp_path, send, catalog=catalog)
    (tmp_path / "requests.jsonl").write_text("altered\n")
    with pytest.raises(ValueError, match="altered"): r.report(tmp_path)


def test_workflow_is_manual_and_snapshot_includes_hidden_files():
    workflow = (r.ROOT / '.github/workflows/paired-open-v1.yml').read_text()
    assert 'workflow_dispatch:' in workflow and 'schedule:' not in workflow
    assert 'default: generate' in workflow and 'COLLECT_144' in workflow
    assert 'include-hidden-files: true' in workflow
    assert 'path: runs/paired-open-v1/' in workflow
    assert 'secrets.DEEPINFRA_API_KEY' in workflow
