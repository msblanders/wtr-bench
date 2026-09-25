"""Truth keys must be entailed by constructed histories, never by the social theory."""

from collections import Counter, defaultdict
from decimal import Decimal

import pytest

from wtrbench.validation_recovery import (
    generate_items,
    original_history_bounds,
    recovery_report,
    request_body,
)


@pytest.fixture(scope="module")
def items():
    return generate_items()


def test_fixed_draft_budget_and_exact_repeated_requests(items):
    assert len(items) == len({i.item_id for i in items}) == 216
    assert Counter(i.arm for i in items) == {"explicit_weight": 72, "choice_history": 144}
    templates = defaultdict(list)
    for i in items:
        templates[i.template_id].append(i)
    assert len(templates) == 108
    for first, second in templates.values():
        assert (first.repetition, second.repetition) == (1, 2)
        assert request_body(first) == request_body(second)
    assert items == generate_items()


def test_truth_is_identified_over_entire_history_interval(items):
    for i in items:
        lo, hi = map(Decimal, i.history_interval_private_audit)
        w = Decimal(i.weight_private_audit)
        r = Decimal(i.own_amount)/i.other_amount
        assert lo < w < hi
        assert r < lo or r > hi  # No request has an ambiguous prediction within the bracket.
        expected_keep = r > hi
        assert (i.expected_answer == "A") == (expected_keep == i.sam_first)
        if i.arm == "choice_history":
            assert "unknown weight" in i.prompt
            assert i.weight_private_audit not in i.prompt
        body = request_body(i)
        assert set(body) == {"model", "system", "max_tokens", "temperature", "output_config", "messages"}
        assert body["messages"][0]["content"] == i.prompt


def test_oracle_recovers_intervals_not_exact_midpoints(items):
    report = recovery_report(items, {i.item_id: i.expected_answer for i in items})
    assert report["known_task_choice_gate"] and report["correct"] == 216
    assert len(report["fits"]) == 54
    expected = {"low": (0.2, 0.5), "middle": (0.5, 1), "high": (1.5, 2)}
    for f in report["fits"]:
        assert f["recovered_interval"]
        assert (f["fit"]["lower"], f["fit"]["upper"]) == expected[f["profile"]]


@pytest.mark.parametrize("strategy", ["A", "B", "keep", "give", "missing"])
def test_shortcut_and_missing_responders_fail(items, strategy):
    choices = {}
    for i in items:
        choices[i.item_id] = (None if strategy == "missing" else strategy if strategy in ("A", "B")
                             else "A" if ((strategy == "keep") == i.sam_first) else "B")
    report = recovery_report(items, choices)
    assert not report["known_task_choice_gate"] and report["planned"] == 216
    assert not all(f["recovered_interval"] for f in report["fits"])


def test_original_histories_do_not_force_theory_ordering():
    rows = original_history_bounds()
    assert len(rows) == 16 and all(not r["point_identified"] for r in rows)
    assert all(r["common_weight_0_05_compatible"] for r in rows)
    # Both equality and LOW > HIGH are compatible with these upper bounds.
    assert all(Decimal(r["reversed_order_example_weight"]) < Decimal(r["upper"]) for r in rows)
