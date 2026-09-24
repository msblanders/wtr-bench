from collections import Counter
from itertools import product

import pytest

from wtrbench.inference import (
    AGGREGATE_SETS,
    BINARY_PROBES,
    CONFIRMATORY_SET_ROLES,
    CONFIRMATORY_TASKS,
    DEBUG_TASKS,
    PILOT_LADDER,
    TASKS,
    Cause,
    Diagnostic,
    InferRelationship,
    Probe,
    Task,
    Totals,
    generate_all_inference_forms,
    generate_inference_items,
)

CONF_SETS = [k for k, s in enumerate(AGGREGATE_SETS) if s.role in CONFIRMATORY_SET_ROLES]
from wtrbench.items import DEFAULT_LADDER, N_FORMS, NAMES


def _n_expected(ladder: tuple[float, ...], n_rel: int, own: bool) -> int:
    n_ladders = 2 if own else 1
    per_ladder = len(ladder) * 2
    attr = len(Cause) * len(CONFIRMATORY_TASKS) * n_rel * (
        n_ladders * per_ladder + len(BINARY_PROBES) * 2
    )
    aggr = len(CONF_SETS) * len(Diagnostic) * len(Totals) * 2 * n_rel * n_ladders * per_ladder
    return attr + aggr


def test_counts() -> None:
    assert len(generate_inference_items()) == _n_expected(DEFAULT_LADDER, 1, False) == 1320
    assert len(generate_inference_items(ladder=PILOT_LADDER)) == _n_expected(PILOT_LADDER, 1, False) == 888
    both = (InferRelationship.ACQUAINTANCE, InferRelationship.FRIEND)
    assert len(generate_inference_items(relationships=both, include_own=True)) == _n_expected(
        DEFAULT_LADDER, 2, True
    )


def test_attribution_grid_once_per_probe_and_order() -> None:
    items = [i for i in generate_inference_items() if i.family == "attribution"]
    ladder = Counter(
        (i.cause, i.task, i.target_ratio, i.keyed_option) for i in items if i.probe is Probe.INFER
    )
    assert set(ladder) == set(product(Cause, CONFIRMATORY_TASKS, DEFAULT_LADDER, "AB"))
    assert set(ladder.values()) == {1}
    binaries = Counter((i.cause, i.task, i.probe, i.keyed_option) for i in items if i.probe in BINARY_PROBES)
    assert set(binaries) == set(product(Cause, CONFIRMATORY_TASKS, BINARY_PROBES, "AB"))
    assert set(binaries.values()) == {1}


def test_aggregate_sets_matched_totals_and_min_ratio() -> None:
    def totals(pair):
        (g1, l1), (g2, l2) = pair
        return g1 + g2, l1 + l2

    def min_ratio(pair):
        return min(g / l for g, l in pair)

    for agg in AGGREGATE_SETS:
        cells = agg.cells
        for t in Totals:
            assert totals(cells[(Diagnostic.LOW, t)]) == totals(cells[(Diagnostic.HIGH, t)])
        for d in Diagnostic:
            assert min_ratio(cells[(d, Totals.T1)]) == pytest.approx(min_ratio(cells[(d, Totals.T2)]))
        assert min_ratio(cells[(Diagnostic.LOW, Totals.T1)]) < min_ratio(cells[(Diagnostic.HIGH, Totals.T1)])
        # T2 must deny "you" strictly more than T1, or the totals factor is empty.
        assert totals(cells[(Diagnostic.LOW, Totals.T2)])[1] > totals(cells[(Diagnostic.LOW, Totals.T1)])[1]
    items = [i for i in generate_inference_items() if i.family == "aggregate"]
    assert all(i.probe is Probe.INFER for i in items)
    assert {(i.agg_set, i.diagnostic, i.totals, i.choices_swapped) for i in items} == set(
        product(CONF_SETS, Diagnostic, Totals, (False, True))
    )
    assert all(AGGREGATE_SETS[i.agg_set].role != "debug" for i in items)


def test_ratios_exact_and_ids_unique_and_stable() -> None:
    a = generate_inference_items()
    b = generate_inference_items()
    assert [i.model_dump() for i in a] == [i.model_dump() for i in b]
    for i in a:
        if i.probe is Probe.INFER:
            assert i.realized_ratio == pytest.approx(i.target_ratio, abs=1e-12)
    everything = generate_all_inference_forms()
    assert len({i.item_id for i in everything}) == len(everything) == 1320 * N_FORMS


def test_names_balanced_across_causes_within_form() -> None:
    # Six tasks per cause and six names: within a form, each cause meets every name once.
    for form in range(N_FORMS):
        items = [i for i in generate_inference_items(form=form) if i.family == "attribution"]
        for cause in Cause:
            assert {i.name for i in items if i.cause is cause} == set(NAMES)


def test_one_name_per_cell_within_form() -> None:
    by_cell: dict[tuple, set[str]] = {}
    for i in generate_inference_items():
        key = (i.family, i.cause, i.task, i.agg_set, i.diagnostic, i.totals, i.choices_swapped)
        by_cell.setdefault(key, set()).add(i.name)
    assert all(len(n) == 1 for n in by_cell.values())


def test_keyed_option_matches_prompt() -> None:
    for i in generate_inference_items(include_own=True):
        a_line = i.prompt.split("(A) ")[1].split("\n")[0]
        keyed = {
            Probe.INFER: f"{i.name} receives {i.varied_amount} points.",
            Probe.OWN: f"You receive {i.varied_amount} points.",
            Probe.WILL_SAME: f"{i.name} would agree to help.",
            Probe.WILL_DIFF: f"{i.name} would agree to help.",
            Probe.ABLE_SAME: f"{i.name} would manage it.",
            Probe.ABLE_DIFF: f"{i.name} would manage it.",
        }[i.probe]
        assert (a_line == keyed) == (i.keyed_option == "A")


def test_failure_causes_share_outcome_and_baseline_has_no_event() -> None:
    items = [i for i in generate_inference_items() if i.family == "attribution"]
    for task in CONFIRMATORY_TASKS:
        with_outcome = {i.cause for i in items if i.task is task and TASKS[task].outcome_fail in i.prompt}
        assert with_outcome == {Cause.UNWILLING, Cause.UNABLE, Cause.CONSTRAINED}
        baseline = [i for i in items if i.task is task and i.cause is Cause.BASELINE]
        assert all("Last week" not in i.prompt for i in baseline)


def test_unable_states_trying_and_persistent_incapacity() -> None:
    # Every unable sentence must say the partner tried; the design doc requires
    # the incapacity to be a standing property, checked here by keyword.
    standing = ("bad back", "bad shoulder", "does not know", "does not understand",
                "not good enough", "allergic", "knows nothing")
    for task, spec in TASKS.items():
        assert "tried" in spec.unable or "took" in spec.unable or "came" in spec.unable, task
        assert any(k in spec.unable for k in standing), task


def test_strict_rejects_unrealizable_ladder() -> None:
    with pytest.raises(ValueError):
        generate_inference_items(ladder=(0.33,))


def test_names_constant_within_set_and_within_scenario() -> None:
    for form in range(N_FORMS):
        by_unit: dict[tuple, set[str]] = {}
        for i in generate_inference_items(form=form):
            unit = ("set", i.agg_set) if i.family == "aggregate" else ("task", i.task)
            by_unit.setdefault(unit, set()).add(i.name)
        assert all(len(n) == 1 for n in by_unit.values())


def test_scaling_set_shares_name_with_its_base_set() -> None:
    items = generate_inference_items()
    names = {AGGREGATE_SETS[i.agg_set].name: i.name for i in items if i.family == "aggregate"}
    assert names["set0x2"] == names["set0"] and names["set1"] != names["set0"]


def test_debug_batch_count() -> None:
    debug = generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))
    assert len(debug) == 5 * (len(PILOT_LADDER) * 2 + 8) + 8 * len(PILOT_LADDER) * 2 == 196


def test_debug_items_are_disjoint_from_confirmatory() -> None:
    conf = {i.item_id for i in generate_inference_items(ladder=PILOT_LADDER)}
    debug = {i.item_id for i in generate_inference_items(
        ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",)
    )}
    assert conf.isdisjoint(debug) and debug
    assert Task.BOXES not in CONFIRMATORY_TASKS
