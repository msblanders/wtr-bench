"""Recovery collection preserves truth, frozen requests, missingness and review status."""

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from wtrbench import recovery_run as runner
from wtrbench.explanation_calibration import APIOutput
from wtrbench.recovery_report import analyse, review_summary, save_reports
from wtrbench.run import RunExists
from wtrbench.validation_recovery import generate_items, request_body


@pytest.fixture(scope="module")
def items():
    return generate_items()


def output(i, answer=None, *, raw=None, stop="end_turn", model=runner.MODEL):
    return APIOutput(request_id="req_"+i.item_id, api_response={
        "id": "msg_"+i.item_id, "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": raw if raw is not None else json.dumps({
            "brief_basis": "Programmed test fixture, not an LLM observation.",
            "answer": answer or i.expected_answer})}],
        "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 40}})


def oracle(items):
    return [runner.decode(i, output(i)) for i in items]


def test_frozen_items_are_identical_to_reviewed_draft(items):
    assert runner.items_hash(items) == "88551d8c5c48cf5c"
    content = "".join(i.model_dump_json()+"\n" for i in items)
    assert hashlib.sha256(content.encode()).hexdigest() == (
        "4b0c5841e8dd70c6ca4fb298b1457bf89937f20d40cb7a20116d2922e799a1f2")
    runner.verify_freeze(items)


def test_truth_keys_independently_derived_from_actual_displayed_text(items):
    for i in items:
        displayed = re.findall(r"\(([AB])\) (Sam|You) receives? (\d+) points\.", i.prompt)
        assert len(displayed) == 2
        options = {who: (letter, Decimal(amount)) for letter, who, amount in displayed}
        ratio = options["Sam"][1]/options["You"][1]
        if i.arm == "explicit_weight":
            match = re.search(r"Sam's points plus ([\d.]+) times", i.prompt)
            assert match
            keep = ratio > Decimal(match[1])
        else:
            history = re.findall(r"The choice was (\d+) points for Sam or (\d+) points for you; "
                                 r"Sam chose the (\d+) points for (Sam|you)\.", i.prompt)
            assert len(history) == 2
            lower = max(Decimal(a)/Decimal(b) for a, b, _, recipient in history if recipient == "you")
            upper = min(Decimal(a)/Decimal(b) for a, b, _, recipient in history if recipient == "Sam")
            assert ratio < lower or ratio > upper
            for a, b, chosen, who in history:
                assert chosen == (a if who == "Sam" else b)
            keep = ratio > upper
        assert options["Sam" if keep else "You"][0] == i.expected_answer


def test_arm_recovery_and_review_do_not_collapse_into_one_pass(items):
    report = analyse(items, oracle(items))
    s = report["summary"]
    assert s["choice_status"] == "clear_pass" and s["known_task_choice_gate"]
    assert s["collection"]["correct"] == 216 and s["recovered_fits"] == 54
    assert s["by_arm"]["explicit_weight"]["recovered_fits"] == 18
    assert s["by_arm"]["choice_history"]["recovered_fits"] == 36
    assert s["explanation_review"]["pending"] == 216
    for kind, n in (("option_order", 108), ("repeat", 108), ("history_order", 72)):
        assert s["comparisons"][kind] == {"planned": n, "complete": n, "incomplete": 0,
                                         "disagree": 0, "rate_among_complete": 0}
    broken = [runner.decode(i, output(i, "A" if i.arm == "choice_history" else i.expected_answer))
              for i in items]
    s = analyse(items, broken)["summary"]
    assert s["by_arm"]["explicit_weight"]["choice_clear_pass"]
    assert not s["by_arm"]["choice_history"]["choice_clear_pass"]
    assert s["comparisons"]["option_order"]["disagree"] == 72
    assert s["comparisons"]["repeat"]["disagree"] == 0


@pytest.mark.parametrize("mode,comparison,count", [("repeat", "repeat", 108),
                                                     ("history", "history_order", 72)])
def test_targeted_perturbations_show_the_correct_disagreement(items, mode, comparison, count):
    rows = []
    for i in items:
        flip = i.repetition == 2 if mode == "repeat" else i.history_swapped is True
        answer = ("B" if i.expected_answer == "A" else "A") if flip else i.expected_answer
        rows.append(runner.decode(i, output(i, answer)))
    s = analyse(items, rows)["summary"]
    assert s["comparisons"][comparison]["disagree"] == count
    assert s["comparisons"]["option_order"]["disagree"] == 0
    assert s["comparisons"]["history_order" if mode == "repeat" else "repeat"]["disagree"] == 0


def test_missing_and_unusable_keep_planned_denominators(items):
    result = analyse(items, [])
    assert result["summary"]["choice_status"] == "incomplete"
    assert result["summary"]["collection"]["missing"] == 216
    assert all(p["complete"] == 0 and p["rate_among_complete"] is None
               for p in result["summary"]["comparisons"].values())
    assert all(f["fit"]["n"] == 0 and f["fit"]["n_missing"] > 0 for f in result["fits"])
    history = next(i for i in items if i.arm == "choice_history")
    rows = [r for r in oracle(items) if r.item_id != history.item_id]
    s = analyse(items, rows)["summary"]
    assert all(p["incomplete"] == 1 for p in s["comparisons"].values())
    rows.append(runner.decode(history, output(history, stop="max_tokens")))
    s = analyse(items, rows)["summary"]
    assert s["collection"]["unusable"] == 1 and s["collection"]["missing"] == 0
    assert s["choice_status"] == "mixed_or_failed" and not s["known_task_choice_gate"]


def test_history_review_uses_intervals_and_explicit_review_uses_exact_values(items, tmp_path):
    rows = oracle(items)
    packet = analyse(items, rows)["explanation-review-template"]
    assert len(packet) == 216
    for p in packet:
        if p["arm"] == "choice_history":
            assert p["exact_option_values"] is None
            assert set(p["weight_information"]) == {"lower", "upper", "endpoints_included"}
            assert not p["weight_information"]["endpoints_included"]
            assert len(p["compatible_option_value_intervals"]) == 2
        else:
            assert p["compatible_option_value_intervals"] is None
            assert max(p["exact_option_values"], key=lambda k: Decimal(p["exact_option_values"][k])) == p["expected_answer"]
    coded = [{**p, "label": "consistent", "notes": "Offline label fixture."} for p in packet]
    assert review_summary(packet, coded)["status"] == "complete"
    assert review_summary(packet, coded[:1])["pending"] == 215
    for bad in ([coded[0], coded[0]], [{**coded[0], "review_id": "unknown"}],
                [{**coded[0], "response_digest": "different-run"}],
                [{**coded[0], "label": "correct"}], [{**coded[0], "notes": ""}],
                [{**coded[0], "label": "unusable_or_missing"}]):
        with pytest.raises(ValueError):
            review_summary(packet, bad)
    empty = analyse(items, [])["explanation-review-template"]
    with pytest.raises(ValueError, match="different response"):
        review_summary(empty, coded)
    labels = tmp_path / "labels.jsonl"
    labels.write_text("".join(json.dumps(r)+"\n" for r in coded))
    original = labels.read_bytes()
    path = tmp_path / "responses.jsonl"
    report = save_reports(path, items, rows, labels_path=labels)
    assert "216/216 reviewed; 0 pending" in report and labels.read_bytes() == original
    assert path.with_suffix(".accepted-explanation-labels.json").exists()
    template = path.with_suffix(".explanation-review-template.jsonl")
    template.write_text(json.dumps(coded[0])+"\n")
    with pytest.raises(ValueError, match="Template contains"):
        save_reports(path, items, rows)


@pytest.mark.parametrize("raw", ['A', '{"answer":"A","brief_basis":"x"}',
    '{"brief_basis":"x","answer":"SAM"}', '{"brief_basis":"x","answer":" A "}',
    '{"brief_basis":"x","answer":"A","answer":"B"}',
    '{"brief_basis":"","answer":"A"}', '{"brief_basis":"x","answer":"A","extra":1}'])
def test_strict_parser_and_unusable_preservation(items, raw):
    for arm in ("explicit_weight", "choice_history"):
        i = next(i for i in items if i.arm == arm)
        r = runner.decode(i, output(i, raw=raw))
        assert r.raw == raw and r.choice is None and r.correct is None and r.keyed is None


@pytest.mark.parametrize("stop", ["max_tokens", "refusal", "stop_sequence", None])
def test_complete_looking_truncated_output_is_not_repaired(items, stop):
    r = runner.decode(items[0], output(items[0], stop=stop))
    assert r.choice is None and r.brief_basis is None


def test_validation_and_freeze_fail_before_calls(items, tmp_path, monkeypatch):
    calls = []
    def respond(i):
        calls.append(i.item_id)
        return output(i)
    for changed in (items[:-1], list(reversed(items)),
                    [items[0].model_copy(update={"prompt": "changed"}), *items[1:]]):
        with pytest.raises(ValueError, match="freeze differs"):
            runner.run(changed, respond, tmp_path / "blocked.jsonl")
    altered = tmp_path / "plan.md"
    altered.write_text(runner.PLAN.read_text()+"Changed.")
    monkeypatch.setattr(runner, "PLAN", altered)
    with pytest.raises(ValueError, match="freeze differs"):
        runner.run(items, respond, tmp_path / "blocked.jsonl")
    monkeypatch.setattr(runner, "RecoveryResponder", lambda: pytest.fail("Client must not be created"))
    monkeypatch.setattr("sys.argv", ["validation_recovery", "run"])
    with pytest.raises(ValueError, match="freeze differs"):
        runner.main()
    assert calls == [] and not (tmp_path / "blocked.jsonl").exists()


def test_schema_field_order_is_frozen(items, monkeypatch, tmp_path):
    manifest = json.loads(runner.FREEZE.read_text())
    schema = manifest["config"]["request"]["output_config"]["format"]["schema"]
    schema["properties"] = dict(reversed(list(schema["properties"].items())))
    altered = tmp_path / "freeze.json"
    altered.write_text(json.dumps(manifest))
    monkeypatch.setattr(runner, "FREEZE", altered)
    with pytest.raises(ValueError, match="freeze differs"):
        runner.verify_freeze(items)


def test_partial_resume_never_reissues_saved_unusable_answers(items, tmp_path):
    called = []
    def interrupted(i):
        if len(called) == 17:
            raise RuntimeError("transport failure")
        called.append(i.item_id)
        return output(i, stop="max_tokens")
    path = tmp_path / "responses.jsonl"
    with pytest.raises(RuntimeError):
        runner.run(items, interrupted, path)
    original = path.read_bytes()
    rest = []
    def finish(i):
        rest.append(i.item_id)
        return output(i)
    rows = runner.run(items, finish, path, resume=True)
    assert len(rest) == 199 and not set(rest) & set(called)
    assert len(rows) == 216 and all(r.choice is None for r in rows[:17])
    assert path.read_bytes().startswith(original) and runner.load_run(path, items) == rows
    with pytest.raises(RunExists):
        runner.run(items, finish, path)
    saved = path.read_bytes()
    path.write_text("".join(r.model_dump_json()+"\n" for r in reversed(rows)))
    with pytest.raises(ValueError, match="request order"):
        runner.load_run(path, items)
    path.write_bytes(saved)
    cfg_path = path.with_suffix(".jsonl.config.json")
    cfg = json.loads(cfg_path.read_text())
    cfg["request"]["max_tokens"] = 512
    cfg_path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="configuration changed"):
        runner.run(items, finish, path, resume=True)
    assert len(rest) == 199


def test_integrity_checks_and_wrong_model_preservation(items, tmp_path):
    rows = oracle(items[:2])
    for field, value in (("correct", not rows[0].correct), ("repetition", 2),
                         ("template_id", "wrong"), ("brief_basis", "altered")):
        with pytest.raises(ValueError, match="mismatch"):
            runner.validate(items, [rows[0].model_copy(update={field: value})])
    with pytest.raises(ValueError, match="Duplicate API"):
        runner.validate(items, [rows[0], rows[1].model_copy(update={"request_id": rows[0].request_id})])
    with pytest.raises(ValueError, match="duplicate response"):
        runner.validate(items, rows+rows[:1])
    path = tmp_path / "wrong.jsonl"
    with pytest.raises(ValueError, match="model mismatch"):
        runner.run(items, lambda i: output(i, model="wrong"), path)
    assert len(path.read_text().splitlines()) == 1
    orphan = tmp_path / "orphan.jsonl"
    orphan.with_suffix(".jsonl.config.json").write_text("{}")
    with pytest.raises(RunExists, match="Orphaned"):
        runner.run(items, output, orphan)


def test_actual_sdk_wire_has_no_hidden_history_answers_and_no_retry(items, monkeypatch):
    import anthropic
    import httpx2

    selected = [next(i for i in items if i.arm == arm and i.profile == profile)
                for arm in ("explicit_weight", "choice_history") for profile in ("low", "middle", "high")]
    bodies, factories = [], []
    def respond(request):
        bodies.append(json.loads(request.content))
        if len(bodies) > len(selected):
            return httpx2.Response(500, json={"type": "error", "error": {
                "type": "api_error", "message": "offline failure"}})
        return httpx2.Response(200, headers={"request-id": f"wire-{len(bodies)}"},
                               json=output(selected[len(bodies)-1]).api_response)
    with anthropic.Anthropic(api_key="offline", max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(respond))) as client:
        def factory(**kwargs):
            factories.append(kwargs)
            return client
        monkeypatch.setattr(anthropic, "Anthropic", factory)
        responder = runner.RecoveryResponder()
        for i in selected:
            row = runner.decode(i, responder(i))
            assert row.correct is True
        with pytest.raises(anthropic.InternalServerError):
            responder(selected[0])
    assert factories == [{"max_retries": 0}] and len(bodies) == len(selected)+1
    for i, body in zip(selected, bodies[:-1], strict=True):
        assert body == request_body(i)
        assert body["temperature"] == 0 and body["max_tokens"] == 256
        assert list(body["output_config"]["format"]["schema"]["properties"]) == ["brief_basis", "answer"]
        assert body["messages"] == [{"role": "user", "content": i.prompt}]


def test_generated_artifacts_and_manual_workflow_cannot_dispatch_pilot(items, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "OUT", tmp_path)
    runner.generate_artifacts(items)
    assert len((tmp_path / "items.jsonl").read_text().splitlines()) == 216
    oracle_check = json.loads((tmp_path / "programmed-oracle-check.json").read_text())
    assert not oracle_check["uses_model_responses"] and oracle_check["known_task_choice_gate"]
    assert (tmp_path / "analysis-plan.md").read_bytes() == runner.PLAN.read_bytes()
    doc = yaml.safe_load(Path(".github/workflows/inference-recovery-diagnostic.yml").read_text())
    assert doc.get("on", doc.get(True)) == {"workflow_dispatch": None}
    job = doc["jobs"]["diagnostic"]
    assert job["timeout-minutes"] == 45
    calls = [s for s in job["steps"] if s.get("run", "").strip().endswith("validation_recovery run")]
    assert len(calls) == 1 and "ANTHROPIC_API_KEY" in calls[0]["env"]
    assert all("robustness_pilot run" not in s.get("run", "") for s in job["steps"])
    uploads = [s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact")]
    assert len(uploads) == 1 and uploads[0]["if"] == "always()"
    assert uploads[0]["with"]["retention-days"] == 90
