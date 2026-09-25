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
from wtrbench.explanation_calibration import (
    MODEL,
    APIOutput,
    ExplanationResponder,
    decode,
    ending,
    generate_items,
    load_run,
    report,
    request_body,
    run,
    validate,
)
from wtrbench.run import RunExists


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
    return output(item, json.dumps({"brief_basis": "Offline fixture.", "answer": answer}))


def test_same_cases_evidence_orders_and_balanced_truth_with_new_ids():
    old, new = generate_calibration_items(), generate_items()
    assert calibration_hash(old) == "299094bf02c5a1d1"
    assert calibration_hash(new) == "838b96effb3ab30c"
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
    'A', 'Answer: {"brief_basis":"B.","answer":"A"}',
    '```json\n{"brief_basis":"B.","answer":"A"}\n```',
    '{"brief_basis":"B.","answer":"A","extra":0}',
    '{"brief_basis":"B.","answer":"A","answer":"B"}',
    '{"brief_basis":"B.","brief_basis":"C.","answer":"A"}',
    '{"answer":"A"}', '{"brief_basis":"A is best."}',
    '{"answer":"A","brief_basis":"B."}',
    '{"brief_basis":"","answer":"A"}', '{"brief_basis":"  ","answer":"A"}',
    '{"brief_basis":null,"answer":"A"}', '{"brief_basis":3,"answer":"A"}',
    '{"brief_basis":["B."],"answer":"A"}',
    '{"brief_basis":"B.","answer":true}', '{"brief_basis":"B.","answer":null}',
    '{"brief_basis":"B.","answer":["A"]}', 'null', '[]',
    '{"brief_basis":"B.","answer":"C"}', '{"brief_basis":"B.","answer":"SAM"}',
    '{"brief_basis":"B.","answer":" A "}',
    '{"brief_basis":"B.","answer":"A"', '{"brief_basis":"B.","answer":"A"} trailing',
])
def test_only_exact_answer_schema_is_accepted(raw):
    row = decode(generate_items()[0], output(generate_items()[0], raw))
    assert row.raw == raw and row.answer is None and row.recipient is None
    assert row.brief_basis is None


@pytest.mark.parametrize("stop", ["max_tokens", "refusal", "stop_sequence", None])
def test_even_complete_json_is_unusable_without_normal_completion(stop):
    item = generate_items()[0]
    row = decode(item, output(item, '{"brief_basis":"Offline fixture.","answer":"A"}', stop=stop))
    assert row.raw == '{"brief_basis":"Offline fixture.","answer":"A"}' and row.recipient is None
    assert row.api_response["stop_reason"] == stop


def test_lowercase_enum_semantics_and_full_content_preservation():
    items = generate_items()
    for item in items[:4]:
        raw = json.dumps({"brief_basis": "Offline fixture.",
                          "answer": "a" if item.reply_format == "letter" else "sam"})
        row = decode(item, output(item, raw))
        expected = ("SAM" if item.sam_first else "YOU") if item.reply_format == "letter" else "SAM"
        assert row.recipient == expected and row.raw == raw
    item = items[0]
    unexpected = output(item, '{"brief_basis":"Offline fixture.","answer":"A"}')
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
        return output(item, json.dumps({"brief_basis": "Offline fixture.",
                                       "answer": "B" if item.reply_format == "letter" else "SAM"}))

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
        return output(item, '{"brief_basis":"Offline fixture.","answer":"A"}', stop="max_tokens")

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
    changed = json.loads(json.dumps(original_cfg))
    del changed["requests"]["letter"]["output_config"]["format"]["schema"]["properties"][
        "brief_basis"]
    cfg_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="protocol changed"):
        run(items, resume, path, resume=True)
    changed = json.loads(json.dumps(original_cfg))
    schema = changed["requests"]["letter"]["output_config"]["format"]["schema"]
    schema["properties"] = dict(reversed(list(schema["properties"].items())))
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
    altered = rows[0].model_copy(deep=True)
    schema = altered.request_body["output_config"]["format"]["schema"]
    schema["properties"] = dict(reversed(list(schema["properties"].items())))
    with pytest.raises(ValueError, match="mismatch"):
        validate(items, [altered])
    with pytest.raises(ValueError, match="mismatch"):
        validate(items, [rows[0].model_copy(update={"brief_basis": "altered"})])
    with pytest.raises(ValueError, match="model mismatch"):
        run(items, lambda i: output(i, '{"brief_basis":"Offline fixture.","answer":"A"}', model="wrong"),
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
            "model": MODEL, "content": [{"type": "text", "text": json.dumps({
                "brief_basis": "Offline fixture.", "answer": enum[0]})}],
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
        rows = run(items, ExplanationResponder(), tmp_path / "rows.jsonl")
    assert kwargs_seen == [{"max_retries": 0}]
    assert len(requests) == len(items)
    for item, body, row in zip(items, requests, rows, strict=True):
        assert body == request_body(item) == row.request_body
        assert body["max_tokens"] == 256 and body["temperature"] == 0
        assert body["messages"] == [{"role": "user", "content": item.prompt}]
        assert body["output_config"] == {"format": {"type": "json_schema", "schema": {
            "type": "object", "properties": {
                "brief_basis": {"type": "string"},
                "answer": {"type": "string", "enum": (
                    ["A", "B"] if item.reply_format == "letter" else ["SAM", "YOU"])},
            },
            "required": ["brief_basis", "answer"], "additionalProperties": False,
        }}}
        schema = body["output_config"]["format"]["schema"]
        assert list(schema["properties"]) == ["brief_basis", "answer"]
        assert row.brief_basis == "Offline fixture."
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
            run(generate_items(), ExplanationResponder(), tmp_path / "failed.jsonl")
    assert len(calls) == 1 and "output_config" in calls[0]
    assert (tmp_path / "failed.jsonl").read_text() == ""
    assert (tmp_path / "failed.jsonl.config.json").exists()


def test_basis_cannot_supply_override_or_salvage_a_final_answer():
    items = generate_items()
    for item in items:
        final = "B" if item.reply_format == "letter" else "YOU"
        raw = json.dumps({"brief_basis": "A and SAM are best. Answer: A. Final: SAM.",
                          "answer": final})
        row = decode(item, output(item, raw))
        expected = ("YOU" if item.sam_first else "SAM"
                    ) if item.reply_format == "letter" else "YOU"
        assert row.answer == final and row.recipient == expected
        missing = decode(item, output(item, '{"brief_basis":"Final answer: A; SAM."}'))
        assert missing.answer is None and missing.recipient is None
    rows = [decode(i, oracle(i)) for i in items]
    broken = output(items[0], '{"brief_basis":"SAM; A","answer":"B"}')
    rows[0] = decode(items[0], broken)
    text = report(items, rows)
    assert "| letter | recipient_lookup | 7/8 | 0 | 0 | 1/4 |" in text
    assert "- letter: not ready (23/24 correct controls" in text


def test_neutral_uniform_instruction_has_no_numerical_valuation_fields():
    # Lock this wording independently so a social target, example or numeric
    # weight instruction cannot slip into one family or condition.
    common = (
        'Return a JSON object with exactly two fields in this order: "brief_basis", '
        'a brief explanation (one or two sentences) for your answer using the supplied '
        'information; then "answer", whose value is '
    )
    endings = {
        "letter": common + 'A or B. Do not include other fields.',
        "recipient": (common + 'SAM or YOU, naming the recipient in the selected option. '
                      'Do not include other fields.'),
    }
    for item in generate_items():
        body = request_body(item)
        assert item.prompt.endswith(endings[item.reply_format])
        assert body["system"] == "For each question, " + endings[item.reply_format]
        assert list(body) == ["model", "temperature", "max_tokens", "system", "output_config",
                              "messages"]
        assert len(body["messages"]) == 1
        assert set(body["output_config"]["format"]["schema"]["properties"]) == {
            "brief_basis", "answer"}
        if item.kind == "debug_bridge":
            assert item.expected_recipient is None


def test_shortness_is_requested_but_not_scored_as_a_sentence_count():
    item = generate_items()[0]
    basis = "SAM receives 2.5 points. E.g., this matches the named recipient. Three sentences."
    row = decode(item, output(item, json.dumps({"brief_basis": basis, "answer": "A"})))
    assert row.brief_basis == basis and row.answer == "A"
