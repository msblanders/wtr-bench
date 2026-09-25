"""Protect the 220-request debug boundary, strict outputs and unchanged estimators."""

import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from wtrbench.calibration import LETTER_END
from wtrbench.explanation_calibration import (
    MODEL,
    APIOutput,
    ending,
    request_settings,
)
from wtrbench.explanation_calibration import (
    generate_items as calibration_items,
)
from wtrbench.explanation_debug import (
    RESPONDER,
    DebugItem,
    DebugResponder,
    batch_hash,
    control_review,
    debug_score,
    decode,
    generate_items,
    load_run,
    report,
    request_body,
    run,
    save_reports,
    validate,
)
from wtrbench.inference import DEBUG_TASKS, PILOT_LADDER, InferenceItem, generate_inference_items
from wtrbench.run import RunExists, items_hash
from wtrbench.run import run as old_run
from wtrbench.score import score
from wtrbench.synthetic import standard_responders


def output(item, answer="A", basis="Offline fixture.", *, raw=None, stop="end_turn", model=MODEL):
    return APIOutput(request_id="req_"+item.item_id, api_response={
        "id": "msg_"+item.item_id, "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": raw if raw is not None else json.dumps(
            {"brief_basis": basis, "answer": answer})}],
        "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 40},
    })


@pytest.fixture(scope="module")
def items():
    return generate_items()


def test_exact_batch_and_source_preservation(items):
    originals = generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))
    controls = [i for i in calibration_items() if i.reply_format == "letter"
                and i.expected_recipient is not None]
    assert len(items) == len({i.item_id for i in items}) == 220
    assert batch_hash(items) == "bfe1d39e753b7316"
    assert [i.block for i in items] == ["control"]*24 + ["debug"]*196
    assert items_hash(originals) == "43e45d7065200983"
    assert [i.source for i in items[:24]] == controls
    assert [i.prompt for i in items[:24]] == [c.prompt for c in controls]
    assert [i.source for i in items[24:]] == originals
    assert Counter(i.source.kind for i in items[:24]) == {
        "recipient_lookup": 8, "quantity": 4, "explicit_rule": 12}
    assert Counter(i.keyed_option for i in items[:24]) == {"A": 12, "B": 12}
    for new, old in zip(items[24:], originals, strict=True):
        assert new.prompt == old.prompt.removesuffix(LETTER_END)+ending("letter")
        assert new.keyed_option == old.keyed_option
        assert new.source.model_dump() == old.model_dump()
    assert not {i.source.item_id for i in items[24:]} & {
        i.item_id for i in generate_inference_items(ladder=PILOT_LADDER)}
    assert all(DebugItem.model_validate_json(i.model_dump_json()) == i for i in items)
    assert items == generate_items()
    # The 12 reused social calibration prompts are unchanged, too.
    bridge = {i.source_item_id: i for i in calibration_items()
              if i.reply_format == "letter" and i.kind == "debug_bridge"}
    assert len(bridge) == 12
    for new in items[24:]:
        if new.source.item_id in bridge:
            assert new.prompt == bridge[new.source.item_id].prompt


@pytest.mark.parametrize("raw", [
    'A', '```json\n{"brief_basis":"x","answer":"A"}\n```',
    '{"answer":"A"}', '{"brief_basis":"A is best."}',
    '{"answer":"A","brief_basis":"x"}',
    '{"brief_basis":"","answer":"A"}', '{"brief_basis":"  ","answer":"A"}',
    '{"brief_basis":3,"answer":"A"}', '{"brief_basis":null,"answer":"A"}',
    '{"brief_basis":"x","answer":true}', '{"brief_basis":"x","answer":"SAM"}',
    '{"brief_basis":"x","answer":" A "}', '{"brief_basis":"x","answer":"A","extra":1}',
    '{"brief_basis":"x","answer":"A","answer":"B"}',
    '{"brief_basis":"x","brief_basis":"y","answer":"A"}',
    '{"brief_basis":"x","answer":"A"} trailing', 'null', '[]',
])
def test_strict_parser_applies_to_controls_ladders_and_binaries(items, raw):
    for i in (items[0], items[24], items[36]):
        row = decode(i, output(i, raw=raw))
        assert row.choice is None and row.keyed is None and row.brief_basis is None
        assert row.raw == raw


@pytest.mark.parametrize("stop", ["max_tokens", "refusal", "stop_sequence", None])
def test_complete_looking_output_is_unusable_without_end_turn(items, stop):
    row = decode(items[0], output(items[0], stop=stop))
    assert row.choice is None and row.api_response["stop_reason"] == stop


def test_only_answer_field_controls_all_probe_mappings(items):
    for i in items:
        r = decode(i, output(i, answer="b", basis="A is best. Final: A. SAM."))
        assert r.choice == "B" and r.keyed == (i.keyed_option == "B")
    abnormal = output(items[0])
    abnormal.api_response["content"].append({"type": "thinking", "thinking": "preserve this"})
    r = decode(items[0], abnormal)
    assert r.choice is None and r.api_response == abnormal.api_response


def test_existing_synthetic_estimators_are_unchanged_and_controls_excluded(items):
    originals = [i.source for i in items[24:]]
    for synthetic in standard_responders():
        old = score(originals, old_run(originals, synthetic, RESPONDER), RESPONDER)
        # Reconstruct for seeded/random responders so the call sequence is identical.
        fresh = next(s for s in standard_responders() if s.name == synthetic.name)
        rows = [decode(i, output(i, answer=fresh(i.source))) for i in items[24:]]
        actual = debug_score(items, rows)
        assert actual == old
        assert actual.n_items == 196 and actual.n_missing == 0
        wrong_controls = [decode(i, output(i, answer="B" if i.keyed_option == "A" else "A"))
                          for i in items[:24]]
        assert debug_score(items, wrong_controls+rows) == actual


def test_partial_rows_remain_missing_in_scores_and_pair_denominators(items):
    a, b = items[24:26]
    rows = [decode(a, output(a)), decode(b, output(b, stop="max_tokens"))]
    assert debug_score(items, rows).n_missing == 195
    text = report(items, rows)
    assert "Final-answer accuracy: 0/24 planned controls." in text
    assert "| attribution/p_infer | 1/60 | 58 | 1 | 0/0/30 |" in text
    assert "| aggregate/p_infer | 0/96 | 96 | 0 | 0/0/48 |" in text
    assert "| high/t1 | 0/0/12 |" in text
    assert text.count("undetermined") > 0
    assert "not approval" in text


def test_option_following_and_evidence_order_disagreements_remain_visible(items):
    rows = [decode(i, output(i)) for i in items]
    text = report(items, rows)
    assert "| aggregate/p_infer | 96/96 | 0 | 0 | 48/48/48 |" in text
    assert all(not c.infer.identified for c in debug_score(items, rows).aggregate)
    assert all(not c.infer.identified for c in debug_score(items, rows).attribution)
    rows = []
    for i in items:
        answer = i.keyed_option
        if isinstance(i.source, InferenceItem) and i.source.choices_swapped:
            answer = "B" if answer == "A" else "A"
        rows.append(decode(i, output(i, answer)))
    text = report(items, rows)
    assert "| aggregate/p_infer | 96/96 | 0 | 0 | 0/48/48 |" in text
    for case in ("low/t1", "low/t2", "high/t1", "high/t2"):
        assert f"| {case} | 12/12/12 |" in text
        a = next(s for s in text.splitlines() if s.startswith(f"| debug/{case}/original |"))
        b = next(s for s in text.splitlines() if s.startswith(f"| debug/{case}/swapped |"))
        assert "0.1:K/K" in a and " | left | " in a
        assert "0.1:G/G" in b and " | right | " in b


def test_nonmonotonic_answers_are_shown_in_each_display_order(items):
    rows = []
    for i in items:
        positive = not (isinstance(i.source, InferenceItem)
                        and i.source.realized_ratio in (0.1, 0.5))
        answer = i.keyed_option if positive else ("B" if i.keyed_option == "A" else "A")
        rows.append(decode(i, output(i, answer)))
    line = next(s for s in report(items, rows).splitlines() if s.startswith("| boxes/baseline |"))
    assert "0.1:G/G 0.2:K/K 0.5:G/G 1:K/K" in line
    assert " | 0/6/6 | 1/1 | " in line
    assert " | unidentified | 2 | 0 |" in line


def test_correct_answer_does_not_clear_wrong_calculation_review(items):
    i = next(i for i in items[:24] if i.source.case == "rule_1_20" and not i.source.sam_first)
    row = decode(i, output(i, "B", "Option A is 10 + 1(10) = 20; B is 20. A tie."))
    records = control_review(items, [row])
    focal = next(r for r in records if r["item_id"] == i.item_id)
    assert focal["correct"] is True and focal["true_option_values"] == {"A": 10, "B": 20}
    assert focal["calculation_review"] == "pending_manual_review"
    assert "pending manual review" in report(items, [row])
    for c in records:
        if c["kind"] != "explicit_rule":
            assert c["true_option_values"] is None
            continue
        # Check report annotations against independently parsed actual prompt allocations.
        w = Decimal(re.search(r"plus ([\d.]+) times your points", c["prompt"])[1])
        alloc = re.findall(r"\(([AB])\) (Sam|You) receive[s]? (\d+) points", c["prompt"])
        truth = {a: float(Decimal(n)*(1 if who == "Sam" else w)) for a, who, n in alloc}
        assert c["true_option_values"] == truth
        assert c["expected_answer"] == max(truth, key=truth.get)


def test_resume_preserves_unusable_rows_and_rejects_changed_protocol(items, tmp_path):
    path = tmp_path/"responses.jsonl"
    called = []

    def fail_after_controls(i):
        if len(called) == 25:
            raise RuntimeError("interrupted")
        called.append(i.item_id)
        return output(i, stop="max_tokens")

    with pytest.raises(RuntimeError):
        run(items, fail_after_controls, path)
    original = path.read_bytes()
    new_calls = []

    def finish(i):
        new_calls.append(i.item_id)
        return output(i, i.keyed_option)

    rows = run(items, finish, path, resume=True)
    assert len(new_calls) == 195 and not set(called) & set(new_calls)
    assert path.read_bytes().startswith(original)
    assert all(r.choice is None for r in rows[:25])
    assert len(rows) == 220 and load_run(path, items) == rows
    with pytest.raises(RunExists):
        run(items, finish, path)
    with pytest.raises(ValueError, match="protocol changed"):
        run(items[1:], finish, path, resume=True)
    cfg_path = path.with_suffix(".jsonl.config.json")
    original_cfg = json.loads(cfg_path.read_text())
    for field, value in (("mode", "calibration-explanation-v1"), ("model", "other"),
                         ("request", {**original_cfg["request"], "max_tokens": 64})):
        cfg_path.write_text(json.dumps({**original_cfg, field: value}))
        with pytest.raises(ValueError, match="protocol changed"):
            run(items, finish, path, resume=True)
    altered = json.loads(json.dumps(original_cfg))
    schema = altered["request"]["output_config"]["format"]["schema"]
    schema["properties"] = dict(reversed(list(schema["properties"].items())))
    cfg_path.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="protocol changed"):
        run(items, finish, path, resume=True)
    assert len(new_calls) == 195


def test_validation_checks_metadata_ids_sources_and_preserves_wrong_model(items, tmp_path):
    rows = [decode(i, output(i)) for i in items[:2]]
    with pytest.raises(ValueError, match="duplicate response"):
        validate(items, rows+rows[:1])
    with pytest.raises(ValueError, match="Duplicate API"):
        validate(items, [rows[0], rows[1].model_copy(update={"request_id": rows[0].request_id})])
    for field, value in (("choice", "B"), ("block", "debug"), ("brief_basis", "altered")):
        with pytest.raises(ValueError, match="mismatch"):
            validate(items, [rows[0].model_copy(update={field: value})])
    changed = items[0].model_copy(update={"prompt": "changed"})
    with pytest.raises(ValueError, match="source changed"):
        validate([changed], [])
    with pytest.raises(ValueError, match="model mismatch"):
        run(items, lambda i: output(i, model="wrong"), tmp_path/"wrong.jsonl")
    assert len((tmp_path/"wrong.jsonl").read_text().splitlines()) == 1


def test_sdk_wire_uses_identical_calibration_settings_for_all_probes(items, monkeypatch, tmp_path):
    import anthropic
    import httpx2

    selected = items[:1]+[next(i for i in items[24:] if i.source.probe.value == probe)
                         for probe in ("p_infer", "p_will_same", "p_will_diff",
                                       "p_able_same", "p_able_diff")]
    requests = []
    factories = []

    def respond(request):
        requests.append(json.loads(request.content))
        payload = output(selected[len(requests)-1]).api_response
        return httpx2.Response(200, headers={"request-id": f"req_wire_{len(requests)}"}, json=payload)

    with anthropic.Anthropic(api_key="offline-test-key", max_retries=0,
                             http_client=httpx2.Client(transport=httpx2.MockTransport(respond))) as c:
        def factory(**kwargs):
            factories.append(kwargs)
            return c
        monkeypatch.setattr(anthropic, "Anthropic", factory)
        rows = run(selected, DebugResponder(), tmp_path/"wire.jsonl")
    assert factories == [{"max_retries": 0}]
    assert len(requests) == len(selected)
    for item, body, row in zip(selected, requests, rows, strict=True):
        assert body == request_body(item) == row.request_body
        assert {k: v for k, v in body.items() if k not in {"model", "messages"}} == request_settings("letter")
        assert body["model"] == MODEL and body["max_tokens"] == 256 and body["temperature"] == 0
        assert body["messages"] == [{"role": "user", "content": item.prompt}]
        assert set(body) == {"model", "max_tokens", "temperature", "system", "output_config", "messages"}
        assert list(body["output_config"]["format"]["schema"]["properties"]) == ["brief_basis", "answer"]
        assert row.api_response["content"][0]["text"] == row.raw
        assert row.request_id.startswith("req_wire_")


@pytest.mark.parametrize("status", [400, 500])
def test_api_failure_stops_without_retry_or_fallback(items, monkeypatch, tmp_path, status):
    import anthropic
    import httpx2

    calls = []

    def reject(request):
        calls.append(json.loads(request.content))
        return httpx2.Response(status, json={"type": "error", "error": {
            "type": "invalid_request_error" if status == 400 else "api_error",
            "message": "offline rejection"}})

    with anthropic.Anthropic(api_key="offline-test-key", max_retries=0,
                             http_client=httpx2.Client(transport=httpx2.MockTransport(reject))) as c:
        monkeypatch.setattr(anthropic, "Anthropic", lambda **kwargs: c)
        with pytest.raises(anthropic.APIStatusError):
            run(items, DebugResponder(), tmp_path/"failed.jsonl")
    assert len(calls) == 1 and (tmp_path/"failed.jsonl").read_text() == ""
    assert (tmp_path/"failed.jsonl.config.json").exists()


def test_reports_roundtrip_and_workflow_is_only_manual(items, tmp_path):
    path = tmp_path/"responses.jsonl"
    rows = run(items, lambda i: output(i, i.keyed_option), path)
    text = save_reports(path, items, rows)
    assert report(items, load_run(path, items)) == text == path.with_suffix(".md").read_text()
    assert json.loads(path.with_suffix(".score.json").read_text())["n_items"] == 196
    assert len(path.with_name("control-review.jsonl").read_text().splitlines()) == 24
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load((root/".github/workflows/inference-debug-explanation.yml").read_text(),
                         Loader=yaml.BaseLoader)
    assert workflow["on"] == {"workflow_dispatch": ""}
    steps = workflow["jobs"]["debug"]["steps"]
    calls = [s for s in steps if s.get("run") == "uv run --frozen python -m wtrbench.explanation_debug run"]
    assert len(calls) == 1
    assert steps.index(calls[0]) > next(n for n, s in enumerate(steps) if "pytest" in s.get("run", ""))
    assert steps[-1]["if"] == steps[-2]["if"] == "always()"
    assert steps[-1]["with"]["path"] == "runs/debug-explanation/"
