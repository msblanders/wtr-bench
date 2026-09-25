"""Protect fractional allocations, matched comparisons, and the fixed paid-call boundary."""

import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from wtrbench.explanation_calibration import MODEL, APIOutput, request_settings
from wtrbench.explanation_debug import DebugResponder, decode, request_body
from wtrbench.explanation_debug import generate_items as source_items
from wtrbench.inference import InferenceItem
from wtrbench.measurement_diagnostic import (
    CLARIFICATIONS,
    RATIOS,
    DiagnosticItem,
    batch_hash,
    config,
    generate_items,
    load_run,
    report,
    run,
    save_reports,
    summarize,
    validate,
)
from wtrbench.run import RunExists


def output(item, positive=True, *, raw=None, stop="end_turn", model=MODEL):
    answer = item.keyed_option if positive else ("B" if item.keyed_option == "A" else "A")
    return APIOutput(request_id="req_"+item.item_id, api_response={
        "id": "msg_"+item.item_id, "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": raw if raw is not None else json.dumps(
            {"brief_basis": "Offline fixture, not model evidence.", "answer": answer})}],
        "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 40},
    })


@pytest.fixture(scope="module")
def items():
    return generate_items()


def test_fixed_scope_actual_fractional_ratios_and_original_request_fidelity(items):
    assert len(items) == len({i.item_id for i in items}) == len({i.prompt for i in items}) == 156
    assert batch_hash(items) == "a23f46bf6a51a8c8"
    assert Counter((i.kind, i.variant) for i in items) == {
        ("control", "original"): 24, ("control", "fraction_control"): 8,
        ("valuation", "original"): 48, ("valuation", "extended"): 48,
        ("valuation", "decimal_anchor"): 12,
        ("binary", "original"): 8, ("binary", "clarified"): 8}
    seeds = {i.item_id: i for i in source_items()}
    assert all(DiagnosticItem.model_validate_json(i.model_dump_json()) == i for i in items)
    for item in items:
        seed = seeds[item.source_debug_item_id]
        assert item.source == seed.source  # Seed remains raw provenance, not actual payoff metadata.
        if item.variant == "original":
            assert item.prompt == seed.prompt
            assert request_body(item) == request_body(seed)
        if item.kind == "valuation":
            own = Decimal(re.search(r"Sam receives ([\d.]+) points", item.prompt)[1])
            other = Decimal(re.search(r"You receive ([\d.]+) points", item.prompt)[1])
            assert own > 0 and other == 10 and float(own/other) == item.ratio
            assert own == Decimal(item.own_amount) and other == Decimal(item.fixed_amount)
            assert item.prompt.split("\n\n")[0] == seed.prompt.split("\n\n")[0]
    ranges = [i for i in items if i.kind == "valuation" and i.variant != "decimal_anchor"]
    assert {i.cell for i in ranges} == {
        "boxes/unable", "boxes/unwilling", "debug/low/t2/original", "debug/low/t2/swapped",
        "debug/high/t2/original", "debug/high/t2/swapped"}
    for cell in {i.cell for i in ranges}:
        assert Counter(i.ratio for i in ranges if i.cell == cell) == {float(r): 2 for r in RATIOS}
        assert {i.own_amount for i in ranges if i.cell == cell} == {
            "0.1", "0.5", "1", "2", "5", "20", "40", "80"}
    assert len([i for i in items if i.variant == "original"]) == 80
    assert items == generate_items()


def test_rule_truth_from_actual_prompt_not_original_seed_amounts(items):
    rules = [i for i in items if i.expected_option_values is not None]
    assert len(rules) == 20
    for item in rules:
        w = Decimal(re.search(r"plus ([\d.]+) times your points", item.prompt)[1])
        options = re.findall(r"\(([AB])\) (Sam|You) receives? ([\d.]+) points", item.prompt)
        truth = {a: float(Decimal(n) * (1 if who == "Sam" else w)) for a, who, n in options}
        assert truth == item.expected_option_values and truth["A"] != truth["B"]
        assert max(truth, key=truth.get) == item.keyed_option
    fractional = [i for i in items if i.variant == "fraction_control"]
    assert Counter(i.keyed_option for i in fractional) == {"A": 4, "B": 4}
    assert Counter(i.source.expected_recipient for i in fractional) == {"SAM": 4, "YOU": 4}


def test_matched_notation_and_condition_edits_preserve_other_information(items):
    for item in items:
        if item.variant not in ("decimal_anchor", "clarified"):
            continue
        seed = next(i for i in items if i.variant == "original" and i.cell == item.cell
                    and i.keyed_option == item.keyed_option and i.ratio == item.ratio)
        if item.variant == "decimal_anchor":
            assert item.prompt == seed.prompt.replace("Sam receives 1 points.",
                                                      "Sam receives 1.0 points.")
        else:
            assert item.prompt == seed.prompt.replace("Which is more likely?",
                CLARIFICATIONS[item.source.probe] + "Which is more likely?")
            assert item.prompt.split("\n\n")[0] == seed.prompt.split("\n\n")[0]


def planted_rows(items):
    thresholds = {"boxes/unable": 3, "boxes/unwilling": .03,
                  "debug/low/t2/original": .03, "debug/low/t2/swapped": .03,
                  "debug/high/t2/original": .3, "debug/high/t2/swapped": .3}
    return [decode(i, output(i, i.ratio > thresholds[i.cell] if i.ratio is not None else True))
            for i in items]


def test_new_range_recovers_both_ends_and_excludes_controls_and_spelling_anchors(items):
    rows = planted_rows(items)
    s = summarize(items, rows)
    assert all(c["fit"]["identified"] and c["fit"]["censored"] == "none"
               and c["fit"]["violations"] == 0 and c["fit"]["n"] == 16
               for c in s["ladders"].values())
    assert s["ladders"]["boxes/unable"]["fit"]["lower"] == 2
    assert s["ladders"]["boxes/unable"]["fit"]["upper"] == 4
    assert s["ladders"]["boxes/unwilling"]["fit"]["lower"] == .01
    assert s["ladders"]["boxes/unwilling"]["fit"]["upper"] == .05
    assert all(c["sign"] == "-" for c in s["low_high_contrasts"].values())
    changed = [decode(i, output(i, False)) if i.kind == "control" or i.variant == "decimal_anchor"
               else r for i, r in zip(items, rows, strict=True)]
    s2 = summarize(items, changed)
    assert s2["ladders"] == s["ladders"] and s2["low_high_contrasts"] == s["low_high_contrasts"]
    assert s2["pilot_approved"] is False
    assert len(s["anchor_comparisons"]) == 80
    assert {r["calculation_review"] for r in s["controls"] if r["expected_option_values"]} == {
        "pending_manual_review"}


def test_missing_unusable_and_order_following_have_full_denominators(items):
    a = next(i for i in items if i.cell == "boxes/unable" and i.variant == "original")
    rows = [decode(a, output(a, stop="max_tokens"))]
    s = summarize(items, rows)
    assert sum(c["recorded"] for c in s["collection"].values()) == 1
    assert sum(c["usable"] for c in s["collection"].values()) == 0
    for c in s["ladders"].values():
        assert c["fit"]["n_missing"] == 16
        assert c["option_pairs"] == {"planned": 8, "complete": 0, "disagree": 0}
    assert s["evidence_pairs"]["ladder"] == {"planned": 32, "complete": 0, "disagree": 0}
    assert len(s["notation_comparisons"]) == 12 and len(s["wording_comparisons"]) == 8
    assert "0/0/12" in report(items, rows) and "missing" in report(items, rows)
    always_a = [decode(i, output(i, raw='{"brief_basis":"fixture","answer":"A"}')) for i in items]
    s = summarize(items, always_a)
    for c in s["ladders"].values():
        assert c["fit"]["identified"] is False
        assert c["option_pairs"] == {"planned": 8, "complete": 8, "disagree": 8}


def test_evidence_order_notation_wording_and_nonmonotonicity_checks(items):
    rows = []
    for i in items:
        positive = True
        if i.kind == "valuation":
            positive = i.ratio != .2  # A keep-to-give decrease at .2.
            if isinstance(i.source, InferenceItem) and i.source.choices_swapped:
                positive = not positive
            if i.variant == "decimal_anchor":
                positive = not positive
        if i.variant == "clarified":
            positive = False
        rows.append(decode(i, output(i, positive)))
    s = summarize(items, rows)
    assert s["ladders"]["boxes/unable"]["by_option_order"]["A"]["observed_decreases"] == 1
    assert s["evidence_pairs"]["ladder"] == {"planned": 32, "complete": 32, "disagree": 32}
    assert s["evidence_pairs"]["decimal_anchor"] == {"planned": 4, "complete": 4, "disagree": 4}
    assert all(c["original"] != c["changed"] for c in s["notation_comparisons"])
    assert all(c["original"] != c["changed"] for c in s["wording_comparisons"])
    assert all(c["condition_review"] == "pending_manual_review" for c in s["binary_review"])


@pytest.mark.parametrize("raw,stop", [
    ('{"answer":"A","brief_basis":"x"}', "end_turn"),
    ('{"brief_basis":"x","answer":"A","answer":"B"}', "end_turn"),
    ('{"brief_basis":"","answer":"A"}', "end_turn"),
    ('{"brief_basis":"x","answer":"SAM"}', "end_turn"),
    ('{"brief_basis":"x","answer":"A"}', "max_tokens"),
])
def test_reused_strict_decoder_applies_to_every_new_variant(items, raw, stop):
    for variant in {i.variant for i in items}:
        i = next(i for i in items if i.variant == variant)
        r = decode(i, output(i, raw=raw, stop=stop))
        assert r.choice is None and r.keyed is None and r.raw == raw


def test_resume_never_repeats_saved_unusable_rows_and_rejects_changed_configuration(items, tmp_path):
    path = tmp_path/"responses.jsonl"
    called = []

    def partial(item):
        if len(called) == 34:
            raise RuntimeError("offline interruption")
        called.append(item.item_id)
        return output(item, stop="max_tokens")

    with pytest.raises(RuntimeError, match="interruption"):
        run(items, partial, path)
    original = path.read_bytes()
    remaining = []

    def finish(item):
        remaining.append(item.item_id)
        return output(item)

    rows = run(items, finish, path, resume=True)
    assert len(remaining) == 122 and not set(remaining) & set(called)
    assert path.read_bytes().startswith(original)
    assert load_run(path, items) == rows and all(r.choice is None for r in rows[:34])
    with pytest.raises(RunExists):
        run(items, finish, path)
    cfg = path.with_suffix(".jsonl.config.json")
    saved = json.loads(cfg.read_text())
    for field, value in (("ratios", ["0.1"]), ("model", "other"),
                         ("request", {**saved["request"], "max_tokens": 512})):
        cfg.write_text(json.dumps({**saved, field: value}))
        with pytest.raises(ValueError, match="protocol changed"):
            run(items, finish, path, resume=True)
    cfg.write_text(json.dumps(saved))
    changed = [items[0].model_copy(update={"cell": "changed"}), *items[1:]]
    with pytest.raises(ValueError, match="metadata changed"):
        run(changed, finish, path, resume=True)
    orphan = tmp_path/"orphan.jsonl"
    orphan.with_suffix(".jsonl.config.json").write_text("{}")
    with pytest.raises(RunExists):
        run(items, finish, orphan)
    assert len(remaining) == 122


def test_integrity_rejects_wrong_models_duplicate_ids_and_saved_request_edits(items, tmp_path):
    row = decode(items[0], output(items[0]))
    with pytest.raises(ValueError, match="duplicate response"):
        validate(items, [row, row])
    second = decode(items[1], output(items[1]))
    with pytest.raises(ValueError, match="Duplicate API request"):
        validate(items, [row, second.model_copy(update={"request_id": row.request_id})])
    bad = row.model_copy(update={"choice": "B"})
    with pytest.raises(ValueError, match="decoding"):
        validate(items, [bad])
    edited = row.model_copy(update={"request_body": {**row.request_body, "temperature": 1}})
    with pytest.raises(ValueError, match="request body"):
        validate(items, [edited])
    called = []

    def wrong(item):
        called.append(item.item_id)
        return output(item, model="unexpected-model")

    path = tmp_path/"wrong.jsonl"
    with pytest.raises(ValueError, match="model mismatch"):
        run(items, wrong, path)
    assert len(called) == 1 and "unexpected-model" in path.read_text()


def test_real_sdk_wire_preserves_protocol_and_sends_only_actual_prompts(items, monkeypatch):
    import anthropic
    import httpx2

    calls = []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        fixture = output(items[len(calls)-1])
        return httpx2.Response(200, json=fixture.api_response,
                              headers={"request-id": f"req_wire_{len(calls)}"})

    selected = [next(i for i in items if i.variant == v) for v in (
        "original", "fraction_control", "extended", "decimal_anchor", "clarified")]
    with anthropic.Anthropic(api_key="offline-test-key", max_retries=0,
                             http_client=httpx2.Client(transport=httpx2.MockTransport(respond))) as c:
        monkeypatch.setattr(anthropic, "Anthropic", lambda **kwargs: c)
        responder = DebugResponder()
        for i in selected:
            responder(i)
    for i, body in zip(selected, calls, strict=True):
        assert body == request_body(i)
        assert body["messages"] == [{"role": "user", "content": i.prompt}]
        assert {k: body[k] for k in request_settings("letter")} == request_settings("letter")
        assert set(body) == {"model", "max_tokens", "temperature", "system", "output_config", "messages"}
        assert list(body["output_config"]["format"]["schema"]["properties"]) == ["brief_basis", "answer"]


@pytest.mark.parametrize("status", [400, 500])
def test_api_error_stops_new_runner_without_retry_or_fallback(items, monkeypatch, tmp_path, status):
    import anthropic
    import httpx2

    calls = []

    def reject(request):
        calls.append(request)
        return httpx2.Response(status, json={"type": "error", "error": {
            "type": "api_error", "message": "offline rejection"}})

    with anthropic.Anthropic(api_key="offline-test-key", max_retries=0,
                             http_client=httpx2.Client(transport=httpx2.MockTransport(reject))) as c:
        monkeypatch.setattr(anthropic, "Anthropic", lambda **kwargs: c)
        path = tmp_path/"error.jsonl"
        with pytest.raises(anthropic.APIStatusError):
            run(items, DebugResponder(), path)
    assert len(calls) == 1 and path.read_text() == ""


def test_report_roundtrip_and_workflow_has_one_manual_call_step(items, tmp_path):
    path = tmp_path/"responses.jsonl"
    rows = run(items, output, path)
    rendered = save_reports(path, items, rows)
    assert report(items, load_run(path, items)) == rendered == path.with_suffix(".md").read_text()
    assert len(path.with_name("control-review.jsonl").read_text().splitlines()) == 32
    assert len(path.with_name("binary-review.jsonl").read_text().splitlines()) == 16
    summary = json.loads(path.with_suffix(".diagnostic.json").read_text())
    assert summary["items_hash"] == config(items)["items_hash"] and not summary["pilot_approved"]
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.load((root/".github/workflows/inference-measurement-diagnostic.yml").read_text(),
                         Loader=yaml.BaseLoader)
    assert workflow["on"] == {"workflow_dispatch": ""}
    steps = workflow["jobs"]["diagnostic"]["steps"]
    calls = [s for s in steps if s.get("run") == (
        "uv run --frozen python -m wtrbench.measurement_diagnostic run")]
    assert len(calls) == 1
    assert steps.index(calls[0]) > next(n for n, s in enumerate(steps) if "pytest" in s.get("run", ""))
    assert steps[-1]["if"] == steps[-2]["if"] == "always()"
    assert steps[-1]["with"]["path"] == "runs/measurement-diagnostic/"
