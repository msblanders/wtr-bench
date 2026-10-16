"""Synthetic software fixtures only: none of these answers came from a model."""
from collections import Counter
from itertools import product

import pytest

from wtrbench.paired import natural
from wtrbench.paired import recipient_design as design


def test_exact_schedule_and_counterbalance():
    items = design.generate_items()
    assert len(items) == len({i["item_id"] for i in items}) == 1760
    assert Counter(i["kind"] for i in items) == {"primary": 1536, "control": 128, "repeat": 96}
    assert all(i["kind"] == "repeat" for i in items[1664:])
    assert len(design.scenarios()) == 24
    domains = Counter(c["domain"] for c in design.scenarios())
    assert len(domains) == 6 and set(domains.values()) == {4}
    for case, condition, target in product(design.scenarios(), design.CONDITIONS, ("R", "S")):
        cell = [i for i in items if i["kind"] == "primary" and i["scenario"] == case["scenario"]
                and i["condition"] == condition and i["recipient"] == target]
        assert {tuple(i["form"].values()) for i in cell} == set(design.FORMS)
        assert all(i["expected_private"] is None for i in cell)
    assert design.generate_items() == items


def test_recipient_questions_share_all_evidence():
    for case, condition, form in product(design.scenarios(), design.CONDITIONS, design.FORMS):
        r, rmap, rshared = design.render(case, condition, "R", form)
        s, smap, sshared = design.render(case, condition, "S", form)
        assert r != s
        assert rmap == smap
        assert rshared == sshared
        n = design.names(form)
        assert f"give {n['R']} 10 points" in r
        assert f"give {n['S']} 10 points" in s


def test_action_counts_identical_and_conditions_change_only_cause_sentence():
    for case, form in product(design.scenarios(), design.FORMS):
        voluntary, _, _ = design.render(case, "voluntary", "R", form)
        assigned, _, _ = design.render(case, "assigned", "R", form)
        vp, ap = voluntary.split("\n\n"), assigned.split("\n\n")
        assert sum(a != b for a, b in zip(vp, ap, strict=True)) == 1
        assert "freely chose" in voluntary and "no discretion" in assigned
        for prompt in (voluntary, assigned):
            for actor in ("Sam", "Priya"):
                assert prompt.count(f"{actor} completed the favor.") == 1
                assert prompt.count(f"{actor} declined the request") == 1


def test_option_and_evidence_order_are_independent():
    c = design.scenarios()[0]
    base, bm, bs = design.render(c, "voluntary", "R", (0, 0, 0, 0))
    opt, om, os = design.render(c, "voluntary", "R", (0, 0, 0, 1))
    ev, em, es = design.render(c, "voluntary", "R", (0, 0, 1, 0))
    assert bm == em != om
    # Option order changes the opening names and options, not the story paragraphs.
    assert bs.split("\n\n")[1:] == os.split("\n\n")[1:]
    assert es.split("\n\n")[4:8] == list(reversed(bs.split("\n\n")[4:8]))
    assert base.split("\n\n")[-1] == ev.split("\n\n")[-1]
    assert base.split("\n\n")[-1] != opt.split("\n\n")[-1]


def test_repeats_are_exact_requests_with_original_ids():
    items = design.generate_items()
    by_id = {i["item_id"]: i for i in items}
    for item in items[1664:]:
        original = by_id[item["repeat_of"]]
        assert original["kind"] == "primary"
        assert not any(original["form"].values())
        assert natural.request_body(item) == natural.request_body(original)


def test_body_and_decoder_preserve_original_format_without_private_metadata():
    for item in design.generate_items():
        body = natural.request_body(item)
        assert body["model"] == "claude-sonnet-4-5-20250929"
        assert body["temperature"] == 0 and body["max_tokens"] == 256
        assert set(body) == {"model", "temperature", "max_tokens", "system", "messages", "output_config"}
        assert body["messages"] == [{"role": "user", "content": item["prompt"]}]
    item = design.generate_items()[0]
    api = {"stop_reason": "end_turn", "content": [{"type": "text", "text":
           '{"brief_basis":"Synthetic fixture.","answer":"A"}'}]}
    assert natural.decode(item, api)["semantic"] == item["semantic_map"]["A"]
    api["stop_reason"] = "max_tokens"
    assert natural.decode(item, api)["semantic"] is None


def fixture(strategy):
    answers = {}
    for item in design.generate_items():
        answers[item["item_id"]] = (item["expected_private"] if item["kind"] == "control"
                                     else strategy(item))
    return design.score(answers)


def test_selective_pattern_is_one_and_one_not_extra_weighted_by_repeats():
    result = fixture(lambda i: ("P" if i["recipient"] == "R" else "Q")
                     if i["condition"] == "voluntary" else "insufficient")
    assert result["mean_recipient_index"] == {"voluntary": 1, "assigned": 0}
    assert result["mean_voluntary_minus_assigned"] == 1
    assert result["families_both_predicted_signs"] == {"voluntary": 24, "assigned": 0}
    assert result["primary_counts"]["insufficient"] == 768
    assert result["control_quality_flag"]
    for category in result["controls"].values():
        assert category["correct"] == category["scheduled"] == 32
    for comparisons in result["presentation_pairs"].values():
        assert all(c == {"scheduled": 384, "comparable": 384, "disagreements": 0}
                   for c in comparisons.values())
    assert result["repeat_pairs"] == {"scheduled": 96, "comparable": 96, "disagreements": 0}


def test_association_only_strategy_does_not_pass_choice_sensitivity_contrast():
    result = fixture(lambda i: "P" if i["recipient"] == "R" else "Q")
    assert result["mean_recipient_index"] == {"voluntary": 1, "assigned": 1}
    assert result["mean_voluntary_minus_assigned"] == 0


@pytest.mark.parametrize("strategy", [
    lambda i: "P", lambda i: "equal", lambda i: "insufficient",
    lambda i: "P" if i["form"]["actor_names"] == 0 else "Q",  # always Sam
    lambda i: i["semantic_map"]["A"],  # always answer-position A
])
def test_recipient_insensitive_strategies_do_not_make_a_directional_effect(strategy):
    result = fixture(strategy)
    assert result["mean_recipient_index"] == {"voluntary": 0, "assigned": 0}
    assert result["families_both_predicted_signs"] == {"voluntary": 0, "assigned": 0}


def test_reverse_and_one_sided_patterns_remain_distinct():
    reverse = fixture(lambda i: "Q" if i["recipient"] == "R" else "P")
    assert reverse["mean_recipient_index"]["voluntary"] == -1
    assert reverse["families"][0]["conditions"]["voluntary"]["reverse_crossovers"] == 16
    one_sided = fixture(lambda i: "P" if i["recipient"] == "R" else "insufficient")
    assert one_sided["mean_recipient_index"]["voluntary"] == 0.5
    assert one_sided["families_both_predicted_signs"]["voluntary"] == 0


def test_partial_and_invalid_data_are_not_silently_dropped_or_relabeled():
    item = next(i for i in design.generate_items() if i["kind"] == "primary")
    result = design.score({item["item_id"]: "invalid"})
    assert result["provided"] == 1 and result["scheduled"] == 1760
    assert result["primary_counts"]["invalid"] == 1
    assert result["primary_counts"]["missing"] == 1535
    assert result["primary_counts"]["equal"] == result["primary_counts"]["insufficient"] == 0
    assert not result["control_quality_flag"]
    assert result["repeat_pairs"]["comparable"] == 0
    with pytest.raises(ValueError):
        design.score({"unknown": "P"})
    with pytest.raises(ValueError):
        design.score({item["item_id"]: "A"})


def test_snapshot_samples_and_budget_reproduce():
    snapshot = design.check()
    assert snapshot["collection_implemented"] is False
    assert snapshot["conditional_planning_ceiling_usd"] == 17.3184
    assert snapshot["status"] == "design_snapshot_not_collection_freeze"
