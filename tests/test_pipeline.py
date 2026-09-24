"""End-to-end recovery checks: the scoring pipeline must reproduce the orderings
each synthetic rule was programmed to produce, must not manufacture them from
rules that lack them, and must not invent precision where none exists."""

import json

import pytest

from wtrbench.inference import (
    AGGREGATE_SETS,
    DEBUG_TASKS,
    PILOT_LADDER,
    Cause,
    generate_inference_items,
)
from wtrbench.run import RunExists, load_responses, parse_choice, run
from wtrbench.score import ladder_contrast, ladder_estimate, score
from wtrbench.synthetic import (
    CAUSE_BLIND,
    FLAT,
    THEORY,
    OrderFollower,
    RandomResponder,
    SyntheticResponder,
    bayesian_rule,
    min_ratio_rule,
    totals_rule,
)


@pytest.fixture(scope="module")
def items():
    return generate_inference_items(ladder=PILOT_LADDER)


def _report(items, responder):
    return score(items, run(items, responder, responder.name), responder.name)


# ----------------------------------------------------------------- parsing

def test_parse_choice_is_full_string_only() -> None:
    for ok, want in (("A", "A"), (" b. ", "B"), ("(B)", "B"), ("A)", "A"), ('"A"', "A"),
                     ("**B**", "B"), ("`a`", "A")):
        assert parse_choice(ok) == want, ok
    for drift in ("A or C", "B since", "A and B", "AB", "", "Answer: A", "I think A",
                  "A because", "C", "(A) and (B)", "A."*2):
        assert parse_choice(drift) is None, drift


# ------------------------------------------------------------ estimation

def test_ladder_identified_censored_unidentified() -> None:
    e = ladder_estimate([(0.2, False), (0.5, False), (1.0, True), (1.5, True)])
    assert e.identified and e.censored == "none" and (e.lower, e.upper) == (0.5, 1.0)
    assert e.estimate == pytest.approx((0.5 * 1.0) ** 0.5)
    left = ladder_estimate([(0.2, True), (0.5, True)])
    assert left.identified and left.censored == "left" and left.estimate is None
    assert (left.lower, left.upper) == (None, 0.2)
    right = ladder_estimate([(0.2, False), (0.5, False)])
    assert right.censored == "right" and right.estimate is None and right.lower == 0.5
    # always-A: keyed on half the items at every rung -> every candidate ties
    tie = ladder_estimate([(r, k) for r in (0.1, 0.2, 0.5, 1.0) for k in (True, False)])
    assert not tie.identified and tie.estimate is None and tie.violations == 4
    assert (tie.lower, tie.upper) == (None, None)
    # tie with different implications: F F T F T
    amb = ladder_estimate([(0.2, False), (0.5, False), (1.0, True), (1.5, False), (2.0, True)])
    assert not amb.identified and amb.estimate is None and (amb.lower, amb.upper) == (0.5, 2.0)


def test_contrast_decided_from_intervals_not_points() -> None:
    a = ladder_estimate([(0.2, False), (0.5, False), (1.0, True), (1.5, True)])  # (0.5, 1.0)
    b = ladder_estimate([(0.2, True), (0.5, True), (1.0, True)])  # left-censored at 0.2
    c = ladder_contrast(a, b, "x")
    assert c.sign == "+" and c.min_abs == pytest.approx(0.3) and c.point is None
    same = ladder_contrast(a, a, "x")
    assert same.sign == "undetermined"
    amb = ladder_estimate([(0.2, False), (0.5, False), (1.0, True), (1.5, False), (2.0, True)])
    assert ladder_contrast(amb, a, "x").sign == "undetermined"
    assert ladder_contrast(amb, b, "x").sign == "+"  # union (0.5, 2.0) still clears a bound at 0.2


# --------------------------------------------------------------- recovery

def test_theory_rule_recovered(items) -> None:
    rep = _report(items, SyntheticResponder("theory", THEORY, min_ratio_rule))
    assert rep.n_missing == 0
    assert rep.required_valuation.n_consistent == rep.required_valuation.n_units == 6
    assert rep.required_ability.n_consistent == 6
    assert all(s.n_consistent == 2 for s in rep.diagnostic_by_set)
    assert all(c.infer.identified and c.infer.censored == "none" for c in rep.attribution)


def test_bayesian_rule_recovered_and_distinct_from_min_ratio(items) -> None:
    bayes = _report(items, SyntheticResponder("bayes", THEORY, bayesian_rule))
    minr = _report(items, SyntheticResponder("minr", THEORY, min_ratio_rule))
    assert all(s.n_consistent == 2 for s in bayes.diagnostic_by_set)
    # set1 HIGH cells: min-ratio threshold 1.20 (above the 1.0 rung), Bayesian 0.69/0.57
    # (below it), so the two rules answer the 1.0 rung differently there.
    set1 = next(k for k, s in enumerate(AGGREGATE_SETS) if s.name == "set1")
    hi_b = [c.infer for c in bayes.aggregate if c.agg_set == set1 and c.diagnostic.value == "high"]
    hi_m = [c.infer for c in minr.aggregate if c.agg_set == set1 and c.diagnostic.value == "high"]
    assert all(e.upper == 1.0 for e in hi_b) and all(e.lower == 1.0 for e in hi_m)


def test_rules_without_the_pattern_do_not_show_it(items) -> None:
    blind = _report(items, SyntheticResponder("blind", CAUSE_BLIND, min_ratio_rule))
    assert blind.required_valuation.n_consistent == 0
    assert blind.required_valuation.n_undetermined == 6  # same gap in both cells
    flat = _report(items, SyntheticResponder("flat", FLAT, min_ratio_rule))
    assert flat.required_valuation.n_consistent == 0 and flat.required_ability.n_consistent == 0
    totals = _report(items, SyntheticResponder("totals", THEORY, totals_rule))
    assert all(s.n_consistent == 0 for s in totals.diagnostic_by_set)


def test_order_follower_is_unidentified_everywhere_not_estimated(items) -> None:
    rep = _report(items, OrderFollower("A"))
    assert all(not c.infer.identified and c.infer.estimate is None for c in rep.attribution)
    assert all(not c.infer.identified for c in rep.aggregate)
    assert rep.required_valuation.n_consistent == 0
    assert rep.required_valuation.n_undetermined == 6


def test_random_responder_mostly_undetermined(items) -> None:
    rep = _report(items, RandomResponder(seed=1))
    v = rep.required_valuation
    assert v.n_undetermined + (v.n_consistent or 0) <= v.n_units


def test_descriptive_rows_have_no_consistency_count(items) -> None:
    rep = _report(items, SyntheticResponder("t", THEORY, min_ratio_rule))
    assert all(s.predicted_sign is None and s.n_consistent is None for s in rep.descriptive.values())
    assert any("totals" in k for k in rep.descriptive) and any("stakes" in k for k in rep.descriptive)


# ---------------------------------------------------------------- runner

def test_missing_responses_are_counted_not_coerced(items) -> None:
    resp = run(items[:50], lambda item: "I refuse to answer", "refuser")
    assert all(r.choice is None and r.keyed is None for r in resp)
    assert score(items[:50], resp, "refuser").n_missing == 50


def test_runner_refuses_existing_file_and_resumes_cleanly(items, tmp_path) -> None:
    out = tmp_path / "r.jsonl"
    responder = SyntheticResponder("t", THEORY, min_ratio_rule)
    calls: list[str] = []
    armed = {"die": True}

    def flaky(item):  # simulates an interrupted run: dies on the 11th call, once
        calls.append(item.item_id)
        if armed["die"] and len(calls) == 11:
            armed["die"] = False
            raise RuntimeError("network")
        return responder(item)

    with pytest.raises(RuntimeError):
        run(items[:25], flaky, "t", out)
    assert len(load_responses(out)) == 10 and (tmp_path / "r.jsonl.config.json").exists()
    with pytest.raises(RunExists):  # same file, no resume flag
        run(items[:25], responder, "t", out)
    calls.clear()
    full = run(items[:25], flaky, "t", out, resume=True)
    assert len(full) == 25 and len(calls) == 15  # only the unfinished 15 were called
    assert len(load_responses(out)) == 25 and len({r.item_id for r in full}) == 25
    with pytest.raises(ValueError):  # a different item set may not resume this file
        run(items[:30], responder, "t", out, resume=True)


def test_scorer_rejects_duplicate_responses(items) -> None:
    resp = run(items[:5], SyntheticResponder("t", THEORY, min_ratio_rule), "t")
    with pytest.raises(ValueError):
        score(items[:5], resp + resp[:1], "t")


def test_resume_requires_same_model_and_settings(items, tmp_path) -> None:
    out = tmp_path / "r.jsonl"
    responder = SyntheticResponder("t", THEORY, min_ratio_rule)
    run(items[:5], responder, "t", out, config={"model": "m1", "mode": "debug"})
    with pytest.raises(ValueError, match="model"):
        run(items[:5], responder, "t", out, resume=True, config={"model": "m2", "mode": "debug"})
    with pytest.raises(ValueError, match="responder"):
        run(items[:5], responder, "other", out, resume=True,
            config={"model": "m1", "mode": "debug"})
    assert len(run(items[:5], responder, "t", out, resume=True,
                   config={"model": "m1", "mode": "debug"})) == 5


def test_inspect_run_reads_a_finished_file(items, tmp_path, monkeypatch) -> None:
    from wtrbench.pilot import inspect_run

    monkeypatch.chdir(tmp_path)
    out = tmp_path / "debug_x.jsonl"
    debug_items = generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))
    run(debug_items, SyntheticResponder("t", THEORY, min_ratio_rule), "t", out,
        config={"mode": "debug", "model": "x",
                "generator": {"ladder": list(PILOT_LADDER), "tasks": ["boxes"],
                              "set_roles": ["debug"], "form": 0}})
    text = inspect_run(out)
    assert "Unparsed / refused: 0" in text and "boxes / unwilling" in text
    assert "0.1-0.2 (viol 0)" in text  # theory's refusal threshold lands in the lowest gap


def test_item_ids_do_not_depend_on_enum_vs_string(items) -> None:
    a = {i.item_id for i in generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS,
                                                     set_roles=("debug",))}
    b = {i.item_id for i in generate_inference_items(ladder=PILOT_LADDER, tasks=("boxes",),  # type: ignore[arg-type]
                                                     set_roles=("debug",))}
    assert a == b


def test_config_records_item_hash(items, tmp_path) -> None:
    out = tmp_path / "r.jsonl"
    run(items[:3], SyntheticResponder("t", THEORY, min_ratio_rule), "t", out,
        config={"model": "x"})
    cfg = json.loads((tmp_path / "r.jsonl.config.json").read_text())
    assert cfg["model"] == "x" and cfg["n_items"] == 3 and len(cfg["items_hash"]) == 16


def test_resume_normalizes_cli_generator_settings(items, tmp_path) -> None:
    out = tmp_path / "r.jsonl"
    config = {"model": "x", "generator": {"ladder": PILOT_LADDER, "form": 0}}
    run(items[:3], lambda item: "A", "x", out, config=config)

    def must_not_call(item):
        raise AssertionError("Completed items must not be called again")

    assert len(run(items[:3], must_not_call, "x", out, resume=True, config=config)) == 3
    changed = {"model": "x", "generator": {"ladder": (0.1, 0.5), "form": 0}}
    with pytest.raises(ValueError, match="generator"):
        run(items[:3], must_not_call, "x", out, resume=True, config=changed)


def test_inspect_preserves_both_aggregate_evidence_orders(tmp_path) -> None:
    from wtrbench.pilot import inspect_run

    items = generate_inference_items(
        ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",)
    )
    path = tmp_path / "debug_x.jsonl"

    def by_evidence_order(item):
        if item.family == "aggregate" and item.choices_swapped:
            return "B" if item.keyed_option == "A" else "A"
        return item.keyed_option

    run(items, by_evidence_order, "x", path,
        config={"model": "x", "generator": {"tasks": ["boxes"], "ladder": PILOT_LADDER}})
    text = inspect_run(path)
    rows = [line for line in text.splitlines() if line.startswith("| aggregate / debug /")]
    assert len(rows) == 8
    assert all("0.1:KK" in line and "left" in line for line in rows if " / original |" in line)
    assert all("0.1:.." in line and "right" in line for line in rows if " / swapped |" in line)


def test_binaries_have_two_items_per_cell(items) -> None:
    rep = _report(items, SyntheticResponder("t", THEORY, min_ratio_rule))
    assert all(c.will_same.n == 2 and c.able_same.n == 2 for c in rep.attribution)
    assert all(c.cause in Cause for c in rep.attribution)


def test_anthropic_request_with_installed_sdk(items, monkeypatch) -> None:
    anthropic = pytest.importorskip("anthropic")
    httpx2 = pytest.importorskip("httpx2")
    from wtrbench.run import AnthropicResponder

    requests = []
    model = "claude-haiku-4-5-20251001"

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx2.Response(200, json={
            "id": "msg_offline_test", "type": "message", "role": "assistant",
            "model": model, "content": [{"type": "text", "text": "A"}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 1},
        })

    with anthropic.Anthropic(
        api_key="offline-test-key",
        http_client=httpx2.Client(transport=httpx2.MockTransport(respond)),
    ) as client:
        monkeypatch.setattr(anthropic, "Anthropic", lambda: client)
        responder = AnthropicResponder(model)
        assert responder(items[0]) == "A"

    assert len(requests) == 1
    assert requests[0]["model"] == model
    assert requests[0]["temperature"] == 0
    assert requests[0]["max_tokens"] == 4
    assert requests[0]["messages"] == [{"role": "user", "content": items[0].prompt}]
