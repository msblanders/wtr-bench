"""Check arithmetic truth, choice consistency and strict collection separately."""

import json
import re
from collections import Counter

import pytest

from wtrbench.calculation_diagnostic import (
    MODEL,
    VALUE_A,
    VALUE_B,
    APIOutput,
    CalculationResponder,
    config,
    decode,
    diagnostics,
    ending,
    generate_items,
    load_run,
    report,
    request_body,
    run,
    validate,
)
from wtrbench.calibration import calibration_hash
from wtrbench.run import RunExists
from wtrbench.structured_calibration import ending as source_ending
from wtrbench.structured_calibration import generate_items as source_items


def output(item, value=None, *, raw=None, stop="end_turn", model=MODEL):
    if raw is None:
        if value is None:
            answer = ("A" if (item.expected_recipient == "SAM") == item.sam_first else "B"
                      ) if item.reply_format == "letter" else item.expected_recipient
            value = {VALUE_A: item.expected_value_a, VALUE_B: item.expected_value_b, "answer": answer}
        raw = json.dumps(value)
    return APIOutput(request_id="req_" + item.item_id, api_response={
        "id": "msg_" + item.item_id, "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": raw}], "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 120, "output_tokens": 35},
    })


def test_exact_original_rule_cases_and_independently_calculated_values():
    items = generate_items()
    source = {i.item_id: i for i in source_items() if i.kind == "explicit_rule"}
    assert len(items) == len({i.item_id for i in items}) == 24
    assert {i.source_structured_item_id for i in items} == set(source)
    assert Counter(i.reply_format for i in items) == {"letter": 12, "recipient": 12}
    assert len({i.case for i in items}) == 6
    assert all(n == 4 for n in Counter(i.case for i in items).values())
    for item in items:
        old = source[item.source_structured_item_id]
        assert item.item_id != old.item_id and item.kind == "explicit_rule"
        assert item.source_item_id is None
        assert item.source_calibration_item_id == old.source_calibration_item_id
        assert item.prompt.removesuffix(ending(item.reply_format)) == old.prompt.removesuffix(
            source_ending(old.reply_format))
        assert (item.case, item.sam_first, item.reply_format, item.expected_recipient) == (
            old.case, old.sam_first, old.reply_format, old.expected_recipient)
        weight = float(re.search(r"plus ([0-9.]+) times", item.prompt).group(1))
        opts = re.findall(r"\([AB]\) (Sam|You) receives? (\d+) points", item.prompt)
        assert len(opts) == 2
        expected = [float(amount) * (1 if who == "Sam" else weight) for who, amount in opts]
        assert (item.expected_value_a, item.expected_value_b) == tuple(expected)
        assert expected[0] != expected[1]
    for fmt in ("letter", "recipient"):
        assert Counter(i.expected_recipient for i in items if i.reply_format == fmt) == {
            "SAM": 6, "YOU": 6}
    assert generate_items() == items
    assert calibration_hash(source_items()) == "ac2f89d22ce87380"


@pytest.mark.parametrize("a,b,choice,expected", [
    (2, 5, "B", (True, True, True, False)),
    (2, 5, "A", (True, False, False, False)),
    (5, 2, "B", (False, True, False, False)),
    (5, 2, "A", (False, False, True, False)),
    (12, 15, "B", (False, True, True, False)),
    (12, 15, "A", (False, False, False, False)),
    (5, 5, "B", (False, True, None, True)),
    (5, 5, "A", (False, False, None, True)),
])
def test_values_choice_and_internal_output_consistency_are_separate(a, b, choice, expected):
    item = generate_items()[0]
    assert item.expected_value_a == 2 and item.expected_value_b == 5
    row = decode(item, output(item, {VALUE_A: a, VALUE_B: b, "answer": choice}))
    d = diagnostics(item, row)
    assert tuple(d[k] for k in ("values_correct", "choice_correct", "follows_values",
                               "reported_tie")) == expected


def test_recipient_answers_are_mapped_to_displayed_values_in_both_orders():
    for item in generate_items():
        row = decode(item, output(item))
        assert diagnostics(item, row) == {
            "values_correct": True, "choice_correct": True, "follows_values": True,
            "reported_tie": False}
        wrong = row.model_copy(update={"recipient": "YOU" if row.recipient == "SAM" else "SAM"})
        assert diagnostics(item, wrong)["follows_values"] is False


@pytest.mark.parametrize("bad", [True, False, None, "2", [2], {}, float("nan"),
                                float("inf"), -float("inf")])
def test_non_numeric_or_nonfinite_values_make_entire_response_unusable(bad):
    item = generate_items()[0]
    row = decode(item, output(item, {VALUE_A: bad, VALUE_B: 5, "answer": "B"}))
    assert row.recipient is None and row.answer is None
    assert row.option_a_value_to_sam is None and row.option_b_value_to_sam is None
    assert all(v is None for v in diagnostics(item, row).values())


def test_strict_schema_completion_and_duplicate_keys():
    item = generate_items()[0]
    good = {VALUE_A: 2, VALUE_B: 5, "answer": "b"}
    assert decode(item, output(item, good)).recipient == "YOU"
    bad_values = [
        {VALUE_A: 2, "answer": "B"}, {**good, "reason": "x"}, {**good, "answer": "YOU"},
        {**good, "answer": " B "}, [], None,
    ]
    for value in bad_values:
        assert decode(item, output(item, raw=json.dumps(value))).recipient is None
    for raw in ('{"option_a_value_to_sam":2,"option_b_value_to_sam":5,"answer":"A","answer":"B"}',
                '```json\n' + json.dumps(good) + '\n```', json.dumps(good) + ' extra'):
        assert decode(item, output(item, raw=raw)).recipient is None
    for stop in ("max_tokens", "refusal", "stop_sequence", None):
        assert decode(item, output(item, good, stop=stop)).recipient is None
    extra = output(item, good)
    extra.api_response["content"].append({"type": "thinking", "thinking": "retained"})
    row = decode(item, extra)
    assert row.recipient is None and row.api_response == extra.api_response


def test_report_denominators_joint_errors_ties_and_pair_counts(tmp_path):
    items = generate_items()
    rows = run(items, output, tmp_path / "rows.jsonl")
    text = report(items, rows)
    for fmt in ("letter", "recipient"):
        assert f"| {fmt} | both | 12 | 0 | 0 | 12/12 | 12/12 | 12/12 | 0 |" in text
        assert f"| {fmt} | 12 | 0 | 0 | 0 |" in text
        assert f"- {fmt}: 0/6 disagreements/complete pairs" in text
    partial = report(items, rows[:1])
    assert "| letter | both | 12 | 11 | 0 | 1/12 | 1/12 | 1/1 | 0 |" in partial
    assert "| recipient | both | 12 | 12 | 0 | 0/12 | 0/12 | 0/0 | 0 |" in partial
    rows[0] = decode(items[0], output(items[0], {VALUE_A: 5, VALUE_B: 5, "answer": "B"}))
    rows[1] = decode(items[1], output(items[1], stop="max_tokens"))
    text = report(items, rows)
    assert "| letter | both | 12 | 0 | 0 | 11/12 | 12/12 | 11/11 | 1 |" in text
    assert "| recipient | both | 12 | 0 | 1 | 11/12 | 11/12 | 11/11 | 0 |" in text
    assert "- recipient: 0/5 disagreements/complete pairs" in text


def test_resume_preserves_unusable_rows_and_rejects_changes(tmp_path):
    items = generate_items()
    path = tmp_path / "rows.jsonl"
    calls = []

    def interrupted(item):
        if len(calls) == 3:
            raise RuntimeError("outage")
        calls.append(item.item_id)
        return output(item, stop="max_tokens")

    with pytest.raises(RuntimeError):
        run(items, interrupted, path)
    original = path.read_bytes()
    remaining = []

    def resume(item):
        remaining.append(item.item_id)
        return output(item)

    rows = run(items, resume, path, resume=True)
    assert len(remaining) == 21 and not set(calls) & set(remaining)
    assert path.read_bytes().startswith(original)
    assert all(r.recipient is None for r in rows[:3])
    assert load_run(path, items) == rows
    with pytest.raises(RunExists):
        run(items, resume, path)
    cfg_path = path.with_suffix(".jsonl.config.json")
    original_cfg = json.loads(cfg_path.read_text())
    for field, value in (("mode", "calibration-structured-v1"), ("model", "different")):
        cfg_path.write_text(json.dumps({**original_cfg, field: value}))
        with pytest.raises(ValueError, match="protocol changed"):
            run(items, resume, path, resume=True)
    changed = json.loads(json.dumps(original_cfg))
    changed["requests"]["letter"]["output_config"]["format"]["schema"]["required"].reverse()
    cfg_path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="protocol changed"):
        run(items, resume, path, resume=True)
    assert len(remaining) == 21


def test_validation_rejects_corruption_duplicates_and_wrong_model(tmp_path):
    items = generate_items()
    rows = run(items[:2], output, tmp_path / "rows.jsonl")
    with pytest.raises(ValueError, match="duplicate response"):
        validate(items, rows + rows[:1])
    for field, value in (("option_a_value_to_sam", 999), ("recipient", "SAM")):
        with pytest.raises(ValueError, match="mismatch"):
            validate(items, [rows[0].model_copy(update={field: value})])
    with pytest.raises(ValueError, match="Duplicate API request"):
        validate(items, [rows[0], rows[1].model_copy(update={"request_id": rows[0].request_id})])
    with pytest.raises(ValueError, match="model mismatch"):
        run(items, lambda i: output(i, model="wrong"), tmp_path / "wrong.jsonl")
    assert len((tmp_path / "wrong.jsonl").read_text().splitlines()) == 1


def test_real_sdk_wire_has_ordered_numeric_fields_and_no_truth_leak(monkeypatch, tmp_path):
    import anthropic
    import httpx2

    requests = []
    kwargs_seen = []
    items = generate_items()[:2]

    def respond(request):
        body = json.loads(request.content)
        item = items[len(requests)]
        requests.append(body)
        return httpx2.Response(200, headers={"request-id": "req_" + item.item_id},
                               json=output(item).api_response)

    with anthropic.Anthropic(api_key="offline-test-key", max_retries=0,
                             http_client=httpx2.Client(transport=httpx2.MockTransport(respond))) as c:
        def client(**kwargs):
            kwargs_seen.append(kwargs)
            return c
        monkeypatch.setattr(anthropic, "Anthropic", client)
        rows = run(items, CalculationResponder(), tmp_path / "rows.jsonl")
    assert kwargs_seen == [{"max_retries": 0}]
    for item, body, row in zip(items, requests, rows, strict=True):
        assert body == request_body(item) == row.request_body
        assert body["max_tokens"] == 256 and body["temperature"] == 0
        assert body["model"] == MODEL
        assert body["messages"] == [{"role": "user", "content": item.prompt}]
        schema = body["output_config"]["format"]["schema"]
        assert schema["type"] == "object" and schema["additionalProperties"] is False
        assert list(schema["properties"]) == schema["required"] == [VALUE_A, VALUE_B, "answer"]
        assert schema["properties"][VALUE_A] == schema["properties"][VALUE_B] == {"type": "number"}
        assert schema["properties"]["answer"]["enum"] == (
            ["A", "B"] if item.reply_format == "letter" else ["SAM", "YOU"])
        assert all(word not in json.dumps(body) for word in (
            "expected_recipient", "expected_value_a", "expected_value_b", item.item_id,
            item.source_structured_item_id))
        assert row.api_response["content"][0]["text"] == row.raw
        assert diagnostics(item, row)["values_correct"] is True


def test_api_error_has_no_retry_or_fallback_and_saves_partial_state(monkeypatch, tmp_path):
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
            run(generate_items(), CalculationResponder(), tmp_path / "failed.jsonl")
    assert len(calls) == 1 and "output_config" in calls[0]
    assert (tmp_path / "failed.jsonl").read_text() == ""
    assert json.loads((tmp_path / "failed.jsonl.config.json").read_text())["mode"] == config(
        generate_items())["mode"]
