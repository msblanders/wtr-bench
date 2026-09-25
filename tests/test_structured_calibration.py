"""Protect the new protocol, known-answer scoring, and one-call-per-item records."""

import json
from collections import Counter

import pytest

from wtrbench.calibration import (
    LETTER_END,
    RECIPIENT_END,
    calibration_hash,
    generate_calibration_items,
)
from wtrbench.run import RunExists
from wtrbench.structured_calibration import (
    MODEL,
    APIOutput,
    StructuredResponder,
    decode,
    ending,
    generate_items,
    load_run,
    report,
    request_body,
    run,
    validate,
)


def output(item, raw, *, stop="end_turn", model=MODEL):
    return APIOutput(request_id="req_" + item.item_id, api_response={
        "id": "msg_" + item.item_id, "type": "message", "role": "assistant",
        "model": model, "content": [{"type": "text", "text": raw}],
        "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 12},
    })


def oracle(item):
    who = item.expected_recipient or "YOU"
    answer = ("A" if (who == "SAM") == item.sam_first else "B"
              ) if item.reply_format == "letter" else who
    return output(item, json.dumps({"answer": answer}))


def test_same_cases_evidence_orders_and_balanced_truth_with_new_ids():
    old, new = generate_calibration_items(), generate_items()
    assert calibration_hash(old) == "299094bf02c5a1d1"
    assert len(new) == len({i.item_id for i in new}) == 72
    assert not {i.item_id for i in old} & {i.item_id for i in new}
    assert Counter(i.kind for i in new) == {
        "recipient_lookup": 16, "quantity": 8, "explicit_rule": 24, "debug_bridge": 24,
    }
    for a, b in zip(old, new, strict=True):
        assert b.source_calibration_item_id == a.item_id
        for field in ("case", "kind", "sam_first", "expected_recipient", "source_item_id",
                      "reply_format"):
            assert getattr(a, field) == getattr(b, field)
        suffix = LETTER_END if a.reply_format == "letter" else RECIPIENT_END
        assert a.prompt.removesuffix(suffix) == b.prompt.removesuffix(ending(b.reply_format))
    for fmt in ("letter", "recipient"):
        controls = [i for i in new if i.reply_format == fmt and i.expected_recipient]
        assert Counter(i.expected_recipient for i in controls) == {"SAM": 12, "YOU": 12}
    assert new == generate_items()


@pytest.mark.parametrize("raw", [
    'A', 'Answer: {"answer":"A"}', '```json\n{"answer":"A"}\n```',
    '{"answer":"A","reason":"anything"}', '{"answer":"A","answer":"B"}',
    '{"answer":true}', '{"answer":null}', '{"answer":["A"]}', 'null', '[]',
    '{"answer":"C"}', '{"answer":"SAM"}', '{"answer":" A "}',
    '{"answer":"A"', '{"answer":"A"} trailing',
])
def test_only_exact_answer_schema_is_accepted(raw):
    row = decode(generate_items()[0], output(generate_items()[0], raw))
    assert row.raw == raw and row.answer is None and row.recipient is None


@pytest.mark.parametrize("stop", ["max_tokens", "refusal", "stop_sequence", None])
def test_even_complete_json_is_unusable_without_normal_completion(stop):
    item = generate_items()[0]
    row = decode(item, output(item, '{"answer":"A"}', stop=stop))
    assert row.raw == '{"answer":"A"}' and row.recipient is None
    assert row.api_response["stop_reason"] == stop


def test_lowercase_enum_semantics_and_full_content_preservation():
    items = generate_items()
    for item in items[:4]:
        raw = '{"answer":"a"}' if item.reply_format == "letter" else '{"answer":"sam"}'
        row = decode(item, output(item, raw))
        expected = ("SAM" if item.sam_first else "YOU") if item.reply_format == "letter" else "SAM"
        assert row.recipient == expected and row.raw == raw
    item = items[0]
    unexpected = output(item, '{"answer":"A"}')
    unexpected.api_response["content"].append({"type": "thinking", "thinking": "retained"})
    row = decode(item, unexpected)
    assert row.recipient is None
    assert row.api_response == unexpected.api_response


def test_reports_control_accuracy_pair_denominators_and_blocks_constant_answers(tmp_path):
    items = generate_items()
    rows = run(items, oracle, tmp_path / "correct.jsonl")
    text = report(items, rows)
    for fmt in ("letter", "recipient"):
        assert f"| {fmt} | explicit_rule | 12/12 | 0 | 0 | 0/6 |" in text
        assert f"- {fmt}: candidate (24/24 correct controls; 6/6 complete debug pairs; 0" in text
    assert "| letter | recipient_lookup | 1/8 | 7 | 0 | 0/0 |" in report(items, rows[:1])

    def constant(item):
        return output(item, json.dumps({"answer": "B" if item.reply_format == "letter" else "SAM"}))

    rows = run(items, constant, tmp_path / "constant.jsonl")
    text = report(items, rows)
    assert "| letter | explicit_rule | 6/12 | 0 | 0 | 6/6 |" in text
    assert "| recipient | explicit_rule | 6/12 | 0 | 0 | 0/6 |" in text
    assert "- letter: not ready" in text and "- recipient: not ready" in text
    rows[0] = decode(items[0], output(items[0], '{}', stop="max_tokens"))
    assert "| letter | recipient_lookup | 4/8 | 0 | 1 | 3/3 |" in report(items, rows)


def test_resume_does_not_repeat_unusable_responses_and_rejects_protocol_changes(tmp_path):
    items = generate_items()
    path = tmp_path / "rows.jsonl"
    calls = []

    def interrupted(item):
        if len(calls) == 5:
            raise RuntimeError("interrupted")
        calls.append(item.item_id)
        return output(item, '{"answer":"A"}', stop="max_tokens")

    with pytest.raises(RuntimeError):
        run(items, interrupted, path)
    original = path.read_bytes()
    remaining = []

    def resume(item):
        remaining.append(item.item_id)
        return oracle(item)

    rows = run(items, resume, path, resume=True)
    assert len(remaining) == 67 and not set(remaining) & set(calls)
    assert path.read_bytes().startswith(original)
    assert all(r.recipient is None for r in rows[:5])
    assert load_run(path, items) == rows
    with pytest.raises(RunExists):
        run(items, resume, path)
    with pytest.raises(ValueError, match="protocol changed"):
        run(items[:-1], resume, path, resume=True)
    cfg_path = path.with_suffix(".jsonl.config.json")
    original_cfg = json.loads(cfg_path.read_text())
    for key, value in (("mode", "calibration-v1"), ("model", "different-model")):
        cfg_path.write_text(json.dumps({**original_cfg, key: value}))
        with pytest.raises(ValueError, match="protocol changed"):
            run(items, resume, path, resume=True)
    changed = json.loads(json.dumps(original_cfg))
    changed["requests"]["letter"]["output_config"]["format"]["schema"]["properties"][
        "answer"]["enum"].reverse()
    cfg_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="protocol changed"):
        run(items, resume, path, resume=True)
    assert len(remaining) == 67


def test_validation_rejects_corrupt_metadata_duplicate_ids_and_wrong_model(tmp_path):
    items = generate_items()
    rows = run(items[:2], oracle, tmp_path / "rows.jsonl")
    with pytest.raises(ValueError, match="duplicate response"):
        validate(items, rows + rows[:1])
    with pytest.raises(ValueError, match="Duplicate API request"):
        validate(items, [rows[0], rows[1].model_copy(update={"request_id": rows[0].request_id})])
    with pytest.raises(ValueError, match="mismatch"):
        validate(items, [rows[0].model_copy(update={"recipient": "YOU"})])
    altered = rows[0].model_copy(deep=True)
    altered.request_body["max_tokens"] = 64
    with pytest.raises(ValueError, match="mismatch"):
        validate(items, [altered])
    with pytest.raises(ValueError, match="model mismatch"):
        run(items, lambda i: output(i, '{"answer":"A"}', model="wrong"),
            tmp_path / "wrong.jsonl")
    assert len((tmp_path / "wrong.jsonl").read_text().splitlines()) == 1


def test_sdk_wire_request_has_schema_budget_system_and_fresh_context(monkeypatch, tmp_path):
    import anthropic
    import httpx2

    requests = []
    kwargs_seen = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        enum = body["output_config"]["format"]["schema"]["properties"]["answer"]["enum"]
        return httpx2.Response(200, headers={"request-id": f"req_wire_{len(requests)}"}, json={
            "id": f"msg_wire_{len(requests)}", "type": "message", "role": "assistant",
            "model": MODEL, "content": [{"type": "text", "text": json.dumps({"answer": enum[0]})}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 12},
        })

    with anthropic.Anthropic(api_key="offline-test-key", max_retries=0,
                             http_client=httpx2.Client(transport=httpx2.MockTransport(respond))) as c:
        def client(**kwargs):
            kwargs_seen.append(kwargs)
            return c

        monkeypatch.setattr(anthropic, "Anthropic", client)
        items = generate_items()[:2]
        rows = run(items, StructuredResponder(), tmp_path / "rows.jsonl")
    assert kwargs_seen == [{"max_retries": 0}]
    for item, body, row in zip(items, requests, rows, strict=True):
        assert body == request_body(item) == row.request_body
        assert body["max_tokens"] == 256 and body["temperature"] == 0
        assert body["messages"] == [{"role": "user", "content": item.prompt}]
        assert body["output_config"] == {"format": {"type": "json_schema", "schema": {
            "type": "object", "properties": {"answer": {"type": "string", "enum": (
                ["A", "B"] if item.reply_format == "letter" else ["SAM", "YOU"])}},
            "required": ["answer"], "additionalProperties": False,
        }}}
        assert row.api_response["content"][0]["text"] == row.raw
        assert row.recipient == "SAM" and row.request_id.startswith("req_wire_")


def test_api_rejection_stops_without_retry_or_unconstrained_fallback(monkeypatch, tmp_path):
    import anthropic
    import httpx2

    calls = []

    def reject(request):
        calls.append(json.loads(request.content))
        return httpx2.Response(400, json={"type": "error", "error": {
            "type": "invalid_request_error", "message": "unsupported schema"}})

    with anthropic.Anthropic(api_key="offline-test-key", max_retries=0,
                             http_client=httpx2.Client(transport=httpx2.MockTransport(reject))) as c:
        monkeypatch.setattr(anthropic, "Anthropic", lambda **kwargs: c)
        with pytest.raises(anthropic.BadRequestError):
            run(generate_items(), StructuredResponder(), tmp_path / "failed.jsonl")
    assert len(calls) == 1 and "output_config" in calls[0]
    assert (tmp_path / "failed.jsonl").read_text() == ""
    assert (tmp_path / "failed.jsonl.config.json").exists()
