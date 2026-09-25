"""Control equivalence, truthful paired reporting and bounded collection, offline."""

import json
import re
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import pairwise
from pathlib import Path

import pytest
import yaml

from wtrbench import presentation_run as runner
from wtrbench.explanation_calibration import APIOutput
from wtrbench.payoff_presentation import generate_items
from wtrbench.presentation_report import analyse, save_reports
from wtrbench.run import RunExists
from wtrbench.validation_recovery import request_body


@pytest.fixture(scope="module")
def items():
    return generate_items()


def output(i, answer=None, *, stop="end_turn", model=runner.MODEL, raw=None):
    return APIOutput(request_id="req_"+i.item_id, api_response={
        "id": "msg_"+i.item_id, "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": raw if raw is not None else json.dumps({
            "brief_basis": "Programmed test fixture, not an LLM observation.",
            "answer": answer or i.expected_answer})}],
        "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 40}})


def oracle(items):
    return [runner.decode(i, output(i)) for i in items]


def test_full_matched_scope_and_identical_original_api_requests(items):
    assert len(items) == len({i.item_id for i in items}) == 288
    assert Counter(i.presentation for i in items) == {"original": 144, "explicit_payoffs": 144}
    assert {i.arm for i in items} == {"choice_history"}
    prior = {r["item_id"]: r for r in map(json.loads, Path(
        "results/diagnostics/36111049496/responses.jsonl").read_text().splitlines())}
    templates, matches = defaultdict(list), defaultdict(list)
    for i in items:
        templates[i.template_id].append(i)
        matches[i.source_item_id].append(i)
        body = request_body(i)
        assert set(body) == {"model", "system", "max_tokens", "temperature", "output_config", "messages"}
        assert body["messages"] == [{"role": "user", "content": i.prompt}]
        assert i.weight_private_audit not in i.prompt
        assert i.source_item_id not in json.dumps(body)
        assert body["temperature"] == 0 and body["max_tokens"] == 256
        assert list(body["output_config"]["format"]["schema"]["properties"]) == ["brief_basis", "answer"]
        if i.presentation == "original":
            assert json.dumps(body) == json.dumps(prior[i.source_item_id]["request_body"])
        else:
            assert "Points for Sam | Points for you" in i.prompt
    assert len(templates) == len(matches) == 144
    for a, b in templates.values():
        assert (a.repetition, b.repetition) == (1, 2)
        assert request_body(a) == request_body(b)
    for a, b in matches.values():
        assert a.presentation != b.presentation and a.expected_answer == b.expected_answer
        assert a.source_template_id == b.source_template_id and a.repetition == b.repetition
    assert all(i.repetition == 1 for i in items[:144])
    assert all(i.repetition == 2 for i in items[144:])
    for rep in (1, 2):
        presentations = [i.presentation for i in items if i.repetition == rep]
        assert sum(a != b for a, b in pairwise(presentations)) > 30
    assert items == generate_items()
    runner.verify_freeze(items)


def test_table_truth_and_payoff_equivalence_from_literal_text(items):
    originals = {i.source_item_id: i for i in items if i.presentation == "original"}
    for i in items:
        if i.presentation == "original":
            continue
        old = originals[i.source_item_id]
        history = re.findall(r"The choice was (\d+) points for Sam or (\d+) points for you; "
                             r"Sam chose the (\d+) points for (Sam|you)\.", old.prompt)
        tables = re.findall(r"\| 1 \| (\d+) \| (\d+) \|\n\| 2 \| (\d+) \| (\d+) \|\n"
                            r"Sam chose outcome ([12])\.", i.prompt)
        assert len(tables) == len(history) == 2
        bounds = {}
        for (own, other, selected, who), (s1, y1, s2, y2, chosen) in zip(history, tables, strict=True):
            assert (s1, y1, s2, y2) == (own, "0", "0", other)
            assert chosen == ("1" if who == "Sam" else "2")
            assert selected == (own if chosen == "1" else other)
            # Under the fixed rule: give implies w > own/other; keep implies w < own/other.
            bounds[chosen] = Fraction(int(s1), int(y2))
        lower, upper = bounds["2"], bounds["1"]
        assert lower < upper
        options = re.findall(r"\| ([AB]) \| (\d+) \| (\d+) \|", i.prompt)
        assert len(options) == 2 and [x[0] for x in options] == ["A", "B"]
        old_options = re.findall(r"\(([AB])\) (Sam|You) receives? (\d+) points\.", old.prompt)
        for (letter, own, other), (old_letter, recipient, amount) in zip(options, old_options, strict=True):
            assert letter == old_letter
            assert (own, other) == ((amount, "0") if recipient == "Sam" else ("0", amount))
        own_letter, own_amount = next((k, int(s)) for k, s, y in options if int(s))
        other_letter, other_amount = next((k, int(y)) for k, s, y in options if int(y))
        ratio = Fraction(own_amount, other_amount)
        assert ratio < lower or ratio > upper
        assert i.expected_answer == (own_letter if ratio > upper else other_letter)
        assert tuple(map(Fraction, i.history_interval_private_audit)) == (lower, upper)


def test_programmed_recovery_pair_denominators_and_review_pending(items):
    result = analyse(items, oracle(items))
    s = result["summary"]
    assert s["collection"]["correct"] == 288 and s["recovered_fits"] == 72
    assert s["explanation_review"]["pending"] == 288
    assert s["matched_presentation"]["both_correct"] == 144
    assert s["matched_presentation"]["net_correct_gain_on_complete_pairs"] == 0
    assert len(result["pairs"]) == 576
    for p in ("original", "explicit_payoffs"):
        assert s["by_presentation"][p]["choice_clear_pass"]
        assert s["by_presentation"][p]["recovered_fits"] == 36
        for v in s["within_presentation_comparisons"][p].values():
            assert v == {"planned": 72, "complete": 72, "incomplete": 0,
                         "disagree": 0, "rate_among_complete": 0}
    expected = {"low": (0.2, 0.5), "middle": (0.5, 1), "high": (1.5, 2)}
    assert all((f["fit"]["lower"], f["fit"]["upper"]) == expected[f["profile"]]
               for f in result["fits"])


@pytest.mark.parametrize("bad_presentation,field", [
    ("original", "explicit_payoffs_only_correct"), ("explicit_payoffs", "original_only_correct")])
def test_paired_gains_and_regressions_are_not_reversed(items, bad_presentation, field):
    rows = [runner.decode(i, output(i, ("B" if i.expected_answer == "A" else "A")
                                   if i.presentation == bad_presentation else i.expected_answer))
            for i in items]
    s = analyse(items, rows)["summary"]
    pair = s["matched_presentation"]
    assert pair[field] == 144 and pair["disagree"] == 144
    sign = 1 if bad_presentation == "original" else -1
    assert pair["net_correct_gain_on_complete_pairs"] == sign*144
    assert pair["correct_fraction_difference_planned"] == sign
    assert not s["by_presentation"][bad_presentation]["choice_clear_pass"]
    for factor, groups in s["matched_by_factor"].items():
        assert sum(g["planned"] for g in groups.values()) == 144, factor
        assert sum(g[field] for g in groups.values()) == 144, factor


@pytest.mark.parametrize("strategy", ["A", "B", "keep", "give"])
def test_simple_strategies_do_not_pass_known_history_recovery(items, strategy):
    rows = []
    for i in items:
        answer = strategy if strategy in ("A", "B") else "A" if (
            (strategy == "keep") == i.sam_first) else "B"
        rows.append(runner.decode(i, output(i, answer)))
    s = analyse(items, rows)["summary"]
    assert all(not a["choice_clear_pass"] for a in s["by_presentation"].values())
    for p in ("original", "explicit_payoffs"):
        comparisons = s["within_presentation_comparisons"][p]
        assert comparisons["repeat"]["disagree"] == 0
        assert comparisons["option_order"]["disagree"] == (72 if strategy in ("A", "B") else 0)


def test_unusable_and_missing_keep_denominators_without_fabricated_gain(items):
    empty = analyse(items, [])["summary"]
    assert empty["collection"]["missing"] == 288
    assert empty["matched_presentation"]["incomplete"] == 144
    assert empty["matched_presentation"]["accuracy_difference_on_complete_pairs"] is None
    assert all(a["choice_status"] == "incomplete" for a in empty["by_presentation"].values())
    omitted = next(i for i in items if i.presentation == "original")
    rows = [runner.decode(i, output(i, stop="max_tokens" if i == omitted else "end_turn")) for i in items]
    result = analyse(items, rows)
    s = result["summary"]
    assert s["collection"]["unusable"] == 1 and s["collection"]["correct"] == 287
    matched = s["matched_presentation"]
    assert matched["complete"] == 143 and matched["incomplete"] == 1
    assert matched["explicit_payoffs_only_correct"] == 0
    assert matched["correct_fraction_difference_planned"] == 1/144
    assert matched["accuracy_difference_on_complete_pairs"] == 0
    assert all(v["incomplete"] == 1 for v in s["within_presentation_comparisons"]["original"].values())
    assert sum(f["fit"]["n_missing"] for f in result["fits"]) == 2
    rows = [r for r in rows if r.item_id != omitted.item_id]
    assert analyse(items, rows)["summary"]["collection"]["missing"] == 1


def test_presentation_specific_review_and_stale_label_rejection(items, tmp_path):
    rows = oracle(items)
    packet = analyse(items, rows)["explanation-review-template"]
    assert all(p["exact_option_values"] is None and p["compatible_option_value_intervals"] for p in packet)
    assert Counter(p["presentation"] for p in packet) == {"original": 144, "explicit_payoffs": 144}
    coded = [{**p, "label": "consistent", "notes": "Offline reviewer fixture."} for p in packet]
    assert analyse(items, rows, labels=coded)["summary"]["explanation_review"]["status"] == "complete"
    partial = [r for r in coded if r["presentation"] == "original"]
    s = analyse(items, rows, labels=partial)["summary"]["explanation_review"]
    assert s["pending"] == 144 and s["by_presentation"]["original"]["pending"] == 0
    for bad in ([coded[0], coded[0]], [{**coded[0], "response_digest": "stale"}],
                [{**coded[0], "review_id": "wrong"}], [{**coded[0], "notes": ""}],
                [{**coded[0], "label": "unusable_or_missing"}]):
        with pytest.raises(ValueError):
            analyse(items, rows, labels=bad)
    path, labels = tmp_path / "responses.jsonl", tmp_path / "labels.jsonl"
    labels.write_text("".join(json.dumps(r)+"\n" for r in coded))
    before = labels.read_bytes()
    assert "288/288 reviewed; 0 pending" in save_reports(path, items, rows, labels_path=labels)
    assert labels.read_bytes() == before and path.with_suffix(".accepted-explanation-labels.json").exists()
    template = path.with_suffix(".explanation-review-template.jsonl")
    with pytest.raises(ValueError, match="separate labels"):
        save_reports(path, items, rows, labels_path=template)
    template.write_text(json.dumps(coded[0])+"\n")
    with pytest.raises(ValueError, match="Template contains"):
        save_reports(path, items, rows)


def test_corrupt_request_metadata_and_freeze_are_rejected_before_calls(items, tmp_path, monkeypatch):
    rows = oracle(items[:2])
    for field, value in (("correct", not rows[0].correct), ("presentation", "altered"),
                         ("source_item_id", "other"), ("brief_basis", "altered")):
        with pytest.raises(ValueError, match="mismatch"):
            runner.validate(items, [rows[0].model_copy(update={field: value})])
    with pytest.raises(ValueError, match="Duplicate API"):
        runner.validate(items, [rows[0], rows[1].model_copy(update={"request_id": rows[0].request_id})])
    calls = []
    def responder(i):
        calls.append(i.item_id)
        return output(i)
    for changed in (items[:-1], list(reversed(items)),
                    [items[0].model_copy(update={"prompt": "changed"}), *items[1:]]):
        with pytest.raises(ValueError, match="freeze differs"):
            runner.run(changed, responder, tmp_path / "blocked.jsonl")
    plan = tmp_path / "plan.md"
    plan.write_text(runner.PLAN.read_text()+"Changed.")
    monkeypatch.setattr(runner, "PLAN", plan)
    monkeypatch.setattr(runner, "RecoveryResponder", lambda: pytest.fail("No client before freeze"))
    monkeypatch.setattr("sys.argv", ["payoff_presentation", "run"])
    with pytest.raises(ValueError, match="freeze differs"):
        runner.main()
    assert calls == [] and not (tmp_path / "blocked.jsonl").exists()


def test_strict_schema_order_and_source_implementation_are_frozen(items, tmp_path, monkeypatch):
    original = json.loads(runner.FREEZE.read_text())
    altered = tmp_path / "freeze.json"
    monkeypatch.setattr(runner, "FREEZE", altered)
    for change in ("schema", "source"):
        manifest = json.loads(json.dumps(original))
        if change == "schema":
            schema = manifest["config"]["request"]["output_config"]["format"]["schema"]
            schema["properties"] = dict(reversed(list(schema["properties"].items())))
        else:
            manifest["config"]["implementation_sha256"]["src/wtrbench/presentation_run.py"] = "changed"
        altered.write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="freeze differs"):
            runner.verify_freeze(items)


def test_resume_saves_errors_and_never_reissues_saved_responses(items, tmp_path):
    called = []
    def interrupted(i):
        if len(called) == 11:
            raise RuntimeError("offline transport failure")
        called.append(i.item_id)
        return output(i, stop="max_tokens")
    path = tmp_path / "responses.jsonl"
    with pytest.raises(RuntimeError):
        runner.run(items, interrupted, path)
    initial = path.read_bytes()
    rest = []
    def finish(i):
        rest.append(i.item_id)
        return output(i)
    rows = runner.run(items, finish, path, resume=True)
    assert len(rows) == 288 and len(rest) == 277 and not set(rest) & set(called)
    assert path.read_bytes().startswith(initial) and all(r.choice is None for r in rows[:11])
    assert runner.load_run(path, items) == rows
    with pytest.raises(RunExists):
        runner.run(items, finish, path)
    original = path.read_bytes()
    path.write_text("".join(r.model_dump_json()+"\n" for r in reversed(rows)))
    with pytest.raises(ValueError, match="request order"):
        runner.load_run(path, items)
    path.write_bytes(original)
    cfg = path.with_suffix(".jsonl.config.json")
    saved = json.loads(cfg.read_text())
    saved["request"]["max_tokens"] = 512
    cfg.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="configuration changed"):
        runner.run(items, finish, path, resume=True)
    assert len(rest) == 277
    wrong = tmp_path / "wrong.jsonl"
    with pytest.raises(ValueError, match="model mismatch"):
        runner.run(items, lambda i: output(i, model="wrong-model"), wrong)
    assert len(wrong.read_text().splitlines()) == 1


@pytest.mark.parametrize("raw,stop", [
    ('A', 'end_turn'), ('{"answer":"A","brief_basis":"x"}', 'end_turn'),
    ('{"brief_basis":"x","answer":"A","answer":"B"}', 'end_turn'),
    ('{"brief_basis":"x","answer":"A"}', 'max_tokens'),
    ('{"brief_basis":"x","answer":"A"}', 'refusal'),
    ('{"brief_basis":"x","answer":"A","extra":1}', 'end_turn')])
def test_no_repair_of_malformed_or_truncated_response(items, raw, stop):
    r = runner.decode(items[0], output(items[0], raw=raw, stop=stop))
    assert r.raw == raw and r.choice is None and r.correct is None and r.brief_basis is None


def test_actual_wire_for_both_presentations_has_no_metadata_or_retries(items, monkeypatch):
    import anthropic
    import httpx2

    selected = [next(i for i in items if i.presentation == p and i.profile == profile)
                for p in ("original", "explicit_payoffs") for profile in ("low", "middle", "high")]
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
            assert runner.decode(i, responder(i)).correct is True
        with pytest.raises(anthropic.InternalServerError):
            responder(selected[0])
    assert factories == [{"max_retries": 0}] and len(bodies) == 7
    assert bodies[:-1] == [request_body(i) for i in selected]


def test_generated_artifacts_and_single_manual_collection_workflow(items, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "OUT", tmp_path)
    runner.generate_artifacts(items)
    assert len((tmp_path / "items.jsonl").read_text().splitlines()) == 288
    oracle_check = json.loads((tmp_path / "programmed-oracle-check.json").read_text())
    assert not oracle_check["uses_model_responses"] and oracle_check["all_intervals_recovered"]
    assert len(oracle_check["fits"]) == 72 and (tmp_path / "prompt-examples.md").exists()
    assert (tmp_path / "analysis-plan.md").read_bytes() == runner.PLAN.read_bytes()
    doc = yaml.safe_load(Path(".github/workflows/inference-payoff-presentation.yml").read_text())
    assert doc.get("on", doc.get(True)) == {"workflow_dispatch": None}
    job = doc["jobs"]["diagnostic"]
    assert job["timeout-minutes"] == 60
    calls = [s for s in job["steps"] if s.get("run", "").strip().endswith("payoff_presentation run")]
    assert len(calls) == 1 and "ANTHROPIC_API_KEY" in calls[0]["env"]
    assert all("robustness_pilot run" not in s.get("run", "") for s in job["steps"])
    uploads = [s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact")]
    assert len(uploads) == 1 and uploads[0]["if"] == "always()"
    assert uploads[0]["with"]["retention-days"] == 90
