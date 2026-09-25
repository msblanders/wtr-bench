"""Offline recovery, held-out scope, freeze, response integrity and pilot budget."""

import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest
import yaml

from wtrbench import robustness_pilot as pilot
from wtrbench.calibration import LETTER_END
from wtrbench.explanation_calibration import APIOutput, ending
from wtrbench.inference import CONFIRMATORY_TASKS, InferenceItem, Probe
from wtrbench.robustness_report import analyse, condition_review, save_reports
from wtrbench.run import RunExists


def output(item, answer=None, *, stop="end_turn", model=pilot.MODEL, raw=None):
    return APIOutput(request_id="req_" + item.item_id, api_response={
        "id": "msg_" + item.item_id, "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": raw if raw is not None else json.dumps({
            "brief_basis": "Offline fixture; not a model observation.",
            "answer": answer or item.keyed_option})}],
        "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 40},
    })


@pytest.fixture(scope="module")
def items():
    return pilot.generate_items()


def rows_for(items, semantic):
    return [pilot.decode(i, output(i, i.keyed_option if semantic(i) else
                                   "B" if i.keyed_option == "A" else "A")) for i in items]


def test_fixed_budget_repetition_source_and_scope(items):
    assert len(items) == len({i.item_id for i in items}) == 816
    assert pilot.batch_hash(items) == "4ab84d33ef76d50e"
    pilot.verify_freeze(items)
    assert items == pilot.generate_items()
    assert Counter((i.kind, i.wording) for i in items) == {
        ("control", "original"): 48, ("valuation", "original"): 480,
        ("binary", "original"): 144, ("binary", "clarified"): 144}
    templates = defaultdict(list)
    for i in items:
        templates[i.template_id].append(i)
        if isinstance(i.source, InferenceItem):
            assert i.source.form == 0
            assert i.source.task in (*CONFIRMATORY_TASKS, None)
            expected = i.source.prompt.removesuffix(LETTER_END) + ending("letter")
            if i.wording == "clarified":
                assert i.kind == "binary"
                expected = expected.replace("Which is more likely?",
                    pilot.clarification(i.source) + "Which is more likely?")
            assert i.prompt == expected
        else:
            assert i.source.reply_format == "letter" and i.prompt == i.source.prompt
    assert len(templates) == 408
    for first, second in templates.values():
        assert (first.repetition, second.repetition) == (1, 2)
        assert pilot.request_body(first) == pilot.request_body(second)
        assert first.item_id != second.item_id
    for start in (0, 408):
        assert [i.block for i in items[start:start+408]] == ["control"]*24 + ["pilot"]*384
    assert [i.template_id for i in items[:408]] != [i.template_id for i in items[408:]]
    assert {i.unit for i in items if isinstance(i.source, InferenceItem)
            and i.source.family == "aggregate"} == {"set0", "set1"}


def test_social_sources_unexposed_in_archived_development_calls(items):
    ids, prompts = set(), set()
    for path in Path("results").rglob("*items.jsonl"):
        for line in path.read_text().splitlines():
            data = json.loads(line)
            while "source" in data:
                data = data["source"]
            if "family" in data:
                ids.add(data["item_id"])
                prompts.add(data["prompt"])
    assert ids  # The check must actually read the archived development items.
    social = [i.source for i in items if isinstance(i.source, InferenceItem)]
    assert not ids & {s.item_id for s in social}
    assert not prompts & {s.prompt for s in social}


def test_always_a_exposes_option_failures_but_repeats(items):
    result = analyse(items, [pilot.decode(i, output(i, "A")) for i in items])
    s = result["summary"]
    assert s["comparisons"]["option_order/pilot"] == {
        "planned": 384, "complete": 384, "incomplete": 0, "disagree": 384,
        "disagreement_rate_among_complete": 1}
    assert s["comparisons"]["repeat/pilot"]["disagree"] == 0
    assert s["comparisons"]["repeat/pilot"]["planned"] == 384
    assert s["comparisons"]["repeat/control"]["planned"] == 24
    assert s["comparisons"]["wording/pilot"]["planned"] == 144
    assert s["comparisons"]["history_order/pilot"]["planned"] == 96
    assert s["condition_adherence"]["reviewed"] == 0
    assert s["condition_adherence"]["pending"] == 288
    assert s["exploratory_wtr"]["complete_zero_violation_interior_cells"] == 0
    assert all(not l["fit"]["identified"] for l in result["ladders"]
               if l["keyed_option"] == "pooled")
    assert {l["fit"]["censored"] for l in result["ladders"]
            if l["keyed_option"] != "pooled"} == {"left", "right"}


@pytest.mark.parametrize("mode,target,count", [
    ("repeat", "repeat/pilot", 384), ("wording", "wording/pilot", 144),
    ("history", "history_order/pilot", 96),
])
def test_planted_sensitivity_is_not_misreported_as_option_bias(items, mode, target, count):
    def choice(i):
        if mode == "repeat":
            return i.repetition == 1
        if mode == "wording":
            return i.wording == "original"
        return not (isinstance(i.source, InferenceItem) and i.source.choices_swapped)
    s = analyse(items, rows_for(items, choice))["summary"]
    assert s["comparisons"][target]["disagree"] == count
    assert s["comparisons"]["option_order/pilot"]["disagree"] == 0
    for other in {"repeat/pilot", "wording/pilot", "history_order/pilot"} - {target}:
        assert s["comparisons"][other]["disagree"] == 0


def test_threshold_recovery_separate_cells_orders_passes_and_missingness(items):
    def planted(i):
        return (i.source.realized_ratio > 0.6 if i.kind == "valuation"
                and isinstance(i.source, InferenceItem) else True)
    result = analyse(items, rows_for(items, planted))
    assert len(result["ladders"]) == 168
    assert result["summary"]["exploratory_wtr"]["pooled_cells"] == 56
    assert result["summary"]["exploratory_wtr"]["complete_zero_violation_interior_cells"] == 56
    for l in result["ladders"]:
        assert l["fit"]["lower"] == 0.5
        assert l["fit"]["upper"] == (1.0 if l["unit"] not in {"set0", "set1"} else 2.0)
        assert l["downward_steps"] == 0
        assert l["repetition"] in (1, 2)
    assert sum(l["planned_adjacent_steps"] for l in result["ladders"]
               if l["keyed_option"] == "pooled") == 368
    empty = analyse(items, [])
    assert empty["summary"]["collection"] == {
        "planned": 816, "recorded": 0, "usable": 0, "missing": 816, "unusable": 0}
    assert all(p["complete"] == 0 and p["disagreement_rate_among_complete"] is None
               for p in empty["summary"]["comparisons"].values())
    assert all(l["fit"]["n"] == 0 and l["fit"]["n_missing"] > 0 for l in empty["ladders"])
    rows = rows_for(items, planted)
    changed = next(i for i in items if i.kind == "binary")
    partial = [r for r in rows if r.item_id != changed.item_id]
    s = analyse(items, partial)["summary"]
    for comparison in ("option_order/pilot", "repeat/pilot", "wording/pilot"):
        assert s["comparisons"][comparison]["incomplete"] == 1
    partial.append(pilot.decode(changed, output(changed, stop="max_tokens")))
    assert analyse(items, partial)["summary"]["collection"]["unusable"] == 1


def test_manual_review_is_response_bound_and_not_social_answer_scoring(items, tmp_path):
    # Both semantic answers can be coded as respecting conditions; no truth key is imposed.
    result = analyse(items, rows_for(items, lambda i: i.keyed_option == "A"))
    packet, key = result["condition-review-template"], result["condition-review-key"]
    assert len(packet) == len({r["review_id"] for r in packet}) == 288
    assert all(set(r) == {"review_id", "response_digest", "prompt", "brief_basis",
                          "response_usable", "label", "notes"} for r in packet)
    coded = [{**r, "label": "respects_condition", "notes": "The basis accepts the supplied premise."}
             for r in packet]
    review = condition_review(packet, key, coded)
    assert review["status"] == "complete" and review["labels"]["respects_condition"] == 288
    assert condition_review(packet, key, coded[:1])["pending"] == 287
    for bad in ([coded[0], coded[0]], [{**coded[0], "review_id": "unknown"}],
                [{**coded[0], "response_digest": "other-run"}],
                [{**coded[0], "label": "correct"}], [{**coded[0], "notes": ""}],
                [{**coded[0], "label": "unusable_or_missing"}]):
        with pytest.raises(ValueError):
            condition_review(packet, key, bad)
    empty = analyse(items, [])
    with pytest.raises(ValueError, match="different response"):
        condition_review(empty["condition-review-template"], empty["condition-review-key"], coded)
    labels_path = tmp_path / "my-labels.jsonl"
    labels_path.write_text("".join(json.dumps(r)+"\n" for r in coded))
    original = labels_path.read_bytes()
    path = tmp_path / "responses.jsonl"
    text = save_reports(path, items, rows_for(items, lambda i: i.keyed_option == "A"),
                        labels_path=labels_path)
    assert "288/288 reviewed; 0 pending" in text and labels_path.read_bytes() == original
    assert path.with_suffix(".accepted-condition-labels.json").exists()
    template = path.with_suffix(".condition-review-template.jsonl")
    template.write_text(json.dumps(coded[0]) + "\n")
    with pytest.raises(ValueError, match="contains labels"):
        save_reports(path, items, [])


def test_control_values_are_separate_from_returned_calculation_accuracy(items):
    records = analyse(items, rows_for(items, lambda i: True))["controls"]
    assert len(records) == 48 and sum(r["correct"] for r in records) == 48
    rules = [r for r in records if r["true_option_values"] is not None]
    assert len(rules) == 24
    for r in rules:
        assert max(r["true_option_values"], key=r["true_option_values"].get) == r["expected_answer"]
        assert r["calculation_review"] == "pending_manual_review"
    known = [r for r in rules if r["case"] == "rule_1_20" and not r["sam_first"]]
    assert len(known) == 2
    assert all(r["true_option_values"] == {"A": 10, "B": 20} for r in known)


def test_freeze_blocks_changes_before_calls(items, monkeypatch, tmp_path):
    calls = []
    def respond(i):
        calls.append(i.item_id)
        return output(i)
    for modified in (items[:-1], list(reversed(items)),
                     [items[0].model_copy(update={"prompt": "changed"}), *items[1:]]):
        with pytest.raises(ValueError, match="freeze differs"):
            pilot.run(modified, respond, tmp_path / "blocked.jsonl")
    changed_plan = tmp_path / "plan.md"
    changed_plan.write_text(pilot.PLAN.read_text()+"Altered.")
    monkeypatch.setattr(pilot, "PLAN", changed_plan)
    with pytest.raises(ValueError, match="freeze differs"):
        pilot.run(items, respond, tmp_path / "blocked.jsonl")
    assert calls == [] and not (tmp_path / "blocked.jsonl").exists()


def test_freeze_preserves_json_schema_field_order(items, monkeypatch, tmp_path):
    original = json.loads(pilot.FREEZE.read_text())
    schema = original["config"]["request"]["output_config"]["format"]["schema"]
    schema["properties"] = dict(reversed(list(schema["properties"].items())))
    altered = tmp_path / "altered-freeze.json"
    altered.write_text(json.dumps(original))
    monkeypatch.setattr(pilot, "FREEZE", altered)
    with pytest.raises(ValueError, match="freeze differs"):
        pilot.verify_freeze(items)


def test_partial_resume_preserves_unusable_rows_and_calls_only_remaining(items, tmp_path):
    called = []
    def interrupted(i):
        if len(called) == 25:
            raise RuntimeError("transport interruption")
        called.append(i.item_id)
        return output(i, stop="max_tokens")
    path = tmp_path / "responses.jsonl"
    with pytest.raises(RuntimeError):
        pilot.run(items, interrupted, path)
    original = path.read_bytes()
    rest = []
    def finish(i):
        rest.append(i.item_id)
        return output(i)
    rows = pilot.run(items, finish, path, resume=True)
    assert len(rest) == 791 and not set(rest) & set(called)
    assert len(rows) == 816 and all(r.choice is None for r in rows[:25])
    assert path.read_bytes().startswith(original) and pilot.load_run(path, items) == rows
    complete = path.read_bytes()
    path.write_text("".join(r.model_dump_json()+"\n" for r in reversed(rows)))
    with pytest.raises(ValueError, match="request order"):
        pilot.load_run(path, items)
    path.write_bytes(complete)
    with pytest.raises(RunExists):
        pilot.run(items, finish, path)
    cfg_path = path.with_suffix(".jsonl.config.json")
    cfg = json.loads(cfg_path.read_text())
    cfg["request"]["max_tokens"] = 512
    cfg_path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="configuration changed"):
        pilot.run(items, finish, path, resume=True)
    assert len(rest) == 791


def test_record_integrity_and_unexpected_model_preservation(items, tmp_path):
    row = pilot.decode(items[0], output(items[0]))
    for field, value in (("repetition", 2), ("template_id", "wrong"), ("brief_basis", "altered")):
        with pytest.raises(ValueError, match="mismatch"):
            pilot.validate(items, [row.model_copy(update={field: value})])
    row2 = pilot.decode(items[1], output(items[1]))
    with pytest.raises(ValueError, match="Duplicate API"):
        pilot.validate(items, [row, row2.model_copy(update={"request_id": row.request_id})])
    with pytest.raises(ValueError, match="duplicate response"):
        pilot.validate(items, [row, row])
    path = tmp_path / "wrong.jsonl"
    with pytest.raises(ValueError, match="model mismatch"):
        pilot.run(items, lambda i: output(i, model="other"), path)
    assert len(path.read_text().splitlines()) == 1
    orphan = tmp_path / "orphan.jsonl"
    orphan.with_suffix(".jsonl.config.json").write_text("{}")
    with pytest.raises(RunExists, match="Orphaned"):
        pilot.run(items, lambda i: output(i), orphan)


@pytest.mark.parametrize("invalid", ["A", '{"answer":"A","brief_basis":"x"}',
    '{"brief_basis":"x","answer":"A","answer":"B"}',
    '{"brief_basis":"","answer":"A"}'])
def test_strict_parser_for_every_pilot_kind(items, invalid):
    for kind in ("control", "binary", "valuation"):
        i = next(i for i in items if i.kind == kind)
        row = pilot.decode(i, output(i, raw=invalid))
        assert row.choice is None and row.keyed is None and row.raw == invalid


def test_actual_sdk_wire_and_no_retry(items, monkeypatch):
    import anthropic
    import httpx2

    selected = [items[0]] + [next(i for i in items if isinstance(i.source, InferenceItem)
        and i.source.probe == probe and i.wording == wording)
        for probe, wording in ((Probe.INFER, "original"), (Probe.WILL_SAME, "original"),
                               (Probe.ABLE_SAME, "clarified"), (Probe.ABLE_DIFF, "clarified"))]
    bodies, factories = [], []
    def respond(request):
        bodies.append(json.loads(request.content))
        if len(bodies) > len(selected):
            return httpx2.Response(500, json={"type": "error", "error": {
                "type": "api_error", "message": "offline failure"}})
        return httpx2.Response(200, headers={"request-id": "wire-"+str(len(bodies))},
                               json=output(selected[len(bodies)-1]).api_response)
    with anthropic.Anthropic(api_key="offline", max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(respond))) as client:
        def factory(**kwargs):
            factories.append(kwargs)
            return client
        monkeypatch.setattr(anthropic, "Anthropic", factory)
        responder = pilot.PilotResponder()
        for i in selected:
            row = pilot.decode(i, responder(i))
            assert row.choice is not None and row.block == i.block
        with pytest.raises(anthropic.InternalServerError):
            responder(selected[0])
    assert factories == [{"max_retries": 0}]
    assert len(bodies) == len(selected)+1
    for i, body in zip(selected, bodies[:-1], strict=True):
        assert body == pilot.request_body(i)
        assert body["max_tokens"] == 256 and body["temperature"] == 0
        assert list(body["output_config"]["format"]["schema"]["properties"]) == ["brief_basis", "answer"]
        assert body["messages"] == [{"role": "user", "content": i.prompt}]
        assert set(body) == {"messages", "model", "system", "temperature", "max_tokens", "output_config"}


def test_workflow_is_manual_one_collection_and_always_preserves_artifacts():
    doc = yaml.safe_load(Path(".github/workflows/inference-robustness-pilot.yml").read_text())
    assert doc.get("on", doc.get(True)) == {"workflow_dispatch": None}
    job = doc["jobs"]["pilot"]
    assert job["if"] == "${{ false }}"
    assert job["timeout-minutes"] == 90
    calls = [s for s in job["steps"] if s.get("run", "").strip().endswith("robustness_pilot run")]
    assert len(calls) == 1 and "ANTHROPIC_API_KEY" in calls[0]["env"]
    uploads = [s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact")]
    assert len(uploads) == 1 and uploads[0]["if"] == "always()"
    assert uploads[0]["with"]["retention-days"] == 90


def test_cli_pause_happens_before_api_client_creation(monkeypatch):
    def forbidden():
        pytest.fail("Paused CLI must not create an API client")
    monkeypatch.setattr(pilot, "PilotResponder", forbidden)
    monkeypatch.setattr("sys.argv", ["robustness_pilot", "run"])
    with pytest.raises(SystemExit) as stopped:
        pilot.main()
    assert stopped.value.code == 2
