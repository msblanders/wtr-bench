"""Calibration checks protect truth keys, held-out items, and billed-call resume."""

import json
from collections import Counter

import pytest

from wtrbench.calibration import (
    FORMATS,
    SYSTEMS,
    CalibrationResponse,
    calibration_report,
    decode_recipient,
    generate_calibration_items,
    run_calibration,
)
from wtrbench.inference import DEBUG_TASKS, PILOT_LADDER, generate_inference_items
from wtrbench.run import AnthropicResponder, ModelOutput, RunExists


@pytest.fixture
def calibration_items():
    return generate_calibration_items()


def test_controls_are_balanced_and_debug_bridge_excludes_pilot(calibration_items):
    items = calibration_items
    assert len(items) == len({i.item_id for i in items}) == 72
    assert Counter(i.reply_format for i in items) == {"letter": 36, "recipient": 36}
    assert Counter(i.kind for i in items) == {
        "recipient_lookup": 16, "quantity": 8, "explicit_rule": 24, "debug_bridge": 24,
    }
    debug = {i.item_id: i for i in generate_inference_items(
        ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))}
    pilot = {i.item_id for i in generate_inference_items(ladder=PILOT_LADDER)}
    for fmt in FORMATS:
        controls = [i for i in items if i.reply_format == fmt and i.expected_recipient]
        assert Counter(i.expected_recipient for i in controls) == {"SAM": 12, "YOU": 12}
        assert sum((i.expected_recipient == "SAM") == i.sam_first for i in controls) == 12
    for it in items:
        if it.kind == "debug_bridge":
            assert it.source_item_id in debug and it.source_item_id not in pilot
            assert it.expected_recipient is None
            if it.reply_format == "letter":
                assert it.prompt == debug[it.source_item_id].prompt
    assert items == generate_calibration_items()


def test_control_truth_and_option_reversal(calibration_items):
    examples = {"rule_0.5_2": "YOU", "rule_0.5_8": "SAM", "rule_1_5": "YOU",
                "rule_1_20": "SAM", "rule_2_10": "YOU", "rule_2_40": "SAM",
                "quantity_2": "YOU", "quantity_20": "SAM",
                "lookup_SAM_2": "SAM", "lookup_YOU_20": "YOU"}
    for it in calibration_items:
        if it.case in examples:
            assert it.expected_recipient == examples[it.case]
        if it.reply_format == "letter":
            assert decode_recipient(it, "A") == ("SAM" if it.sam_first else "YOU")
            assert decode_recipient(it, "B") == ("YOU" if it.sam_first else "SAM")


def test_no_answer_is_extracted_from_prose(calibration_items):
    for it in calibration_items:
        for text in ("I think B", "Answer: SAM", "SAM or YOU", "B because...", ""):
            assert decode_recipient(it, text) is None
        if it.reply_format == "recipient":
            assert decode_recipient(it, " sam\n") == "SAM"
            assert decode_recipient(it, "A") is None


def test_letter_follower_and_fixed_recipient_are_not_validated(calibration_items, tmp_path):
    # The letter follower is inaccurate AND order-dependent on known controls.
    def follower(it):
        return ModelOutput(raw="B" if it.reply_format == "letter" else "SAM")

    rows = run_calibration(calibration_items, follower, "fake", tmp_path / "rows.jsonl")
    report = calibration_report(calibration_items, rows)
    assert "| letter | recipient_lookup | 4/8 | 0 | 4/4 |" in report
    assert "| letter | quantity | 2/4 | 0 | 2/2 |" in report
    assert "| letter | explicit_rule | 6/12 | 0 | 6/6 |" in report
    # A fixed recipient is order-stable but still only half correct.
    assert "| recipient | explicit_rule | 6/12 | 0 | 0/6 |" in report


def test_correct_controls_and_partial_pair_denominators(calibration_items, tmp_path):
    def oracle(it):
        who = it.expected_recipient or "YOU"
        letter = "A" if (who == "SAM") == it.sam_first else "B"
        return ModelOutput(raw=letter if it.reply_format == "letter" else who)

    rows = run_calibration(calibration_items, oracle, "fake", tmp_path / "rows.jsonl")
    report = calibration_report(calibration_items, rows)
    for fmt in FORMATS:
        assert f"| {fmt} | explicit_rule | 12/12 | 0 | 0/6 |" in report
    assert "| letter | recipient_lookup | 1/8 | 7 | 0/0 |" in calibration_report(
        calibration_items, rows[:1])
    with pytest.raises(ValueError, match="duplicate"):
        calibration_report(calibration_items, rows + rows[:1])


def test_resume_retains_unparsed_and_does_not_repeat_paid_calls(calibration_items, tmp_path):
    path = tmp_path / "rows.jsonl"
    calls = []

    def interrupted(it):
        if len(calls) == 5:
            raise RuntimeError("outage")
        calls.append(it.item_id)
        return ModelOutput(raw="Answer: B")

    with pytest.raises(RuntimeError, match="outage"):
        run_calibration(calibration_items, interrupted, "fake", path)
    remaining = []

    def resume(it):
        remaining.append(it.item_id)
        return ModelOutput(raw="B")

    rows = run_calibration(calibration_items, resume, "fake", path, resume=True)
    assert len(rows) == 72 and len(remaining) == 67
    assert not set(calls) & set(remaining)
    assert all(r.raw == "Answer: B" and r.recipient is None for r in rows[:5])
    with pytest.raises(RunExists):
        run_calibration(calibration_items, resume, "fake", path)
    with pytest.raises(ValueError, match="changed"):
        run_calibration(calibration_items, resume, "different", path, resume=True)
    with pytest.raises(ValueError, match="changed"):
        run_calibration(calibration_items[:-1], resume, "fake", path, resume=True)
    cfg_path = path.with_suffix(".jsonl.config.json")
    cfg = json.loads(cfg_path.read_text())
    cfg["requests"]["recipient"]["max_tokens"] = 128
    cfg_path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="changed"):
        run_calibration(calibration_items, resume, "fake", path, resume=True)
    assert len(remaining) == 67


def test_wrong_semantic_decoding_is_rejected(calibration_items):
    item = calibration_items[0]
    row = CalibrationResponse(item_id=item.item_id, model="fake", reply_format="letter",
                              raw="A", recipient="YOU")
    assert item.sam_first
    with pytest.raises(ValueError, match="decoded"):
        calibration_report(calibration_items, [row])


def test_calibration_wire_requests_use_matching_format(calibration_items, monkeypatch, tmp_path):
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        raw = "SAM" if body["system"] == SYSTEMS["recipient"] else "A"
        return httpx2.Response(200, headers={"request-id": f"req_test_{len(requests)}"}, json={
            "id": "msg_test", "type": "message", "role": "assistant", "model": "test-model",
            "content": [{"type": "text", "text": raw}], "stop_reason": "end_turn",
            "stop_sequence": None, "usage": {"input_tokens": 12, "output_tokens": 4},
        })

    with anthropic.Anthropic(api_key="offline-test-key", http_client=httpx2.Client(
        transport=httpx2.MockTransport(respond),
    )) as client:
        monkeypatch.setattr(anthropic, "Anthropic", lambda: client)
        responders = {f: AnthropicResponder("test-model", format_system=SYSTEMS[f]) for f in FORMATS}
        rows = run_calibration(calibration_items[:2], lambda i: responders[i.reply_format](i),
                               "test-model", tmp_path / "rows.jsonl")
    assert [r.recipient for r in rows] == ["SAM", "SAM"]
    for item, body, row in zip(calibration_items[:2], requests, rows, strict=True):
        assert body["system"] == SYSTEMS[item.reply_format]
        assert body["max_tokens"] == 64 and body["temperature"] == 0
        assert body["messages"] == [{"role": "user", "content": item.prompt}]
        assert row.stop_reason == "end_turn" and row.usage["input_tokens"] == 12
        assert row.returned_model == "test-model" and row.request_id.startswith("req_test_")
