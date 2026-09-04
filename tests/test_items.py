from collections import Counter
from itertools import product

import pytest

from wtrbench.items import (
    DEFAULT_LADDER,
    N_FORMS,
    NAMES,
    History,
    Relationship,
    Stakes,
    generate_all_forms,
    generate_items,
)


def test_full_grid_coverage_exactly_once() -> None:
    items = generate_items()
    combos = Counter(
        (i.relationship, i.history, i.stakes, i.target_ratio, i.self_option)
        for i in items
    )
    expected = set(product(Relationship, History, Stakes, DEFAULT_LADDER, ("A", "B")))
    assert set(combos) == expected
    assert all(count == 1 for count in combos.values())
    assert len(items) == 5 * 3 * 2 * 10 * 2


def test_deterministic_full_records() -> None:
    a = [i.model_dump() for i in generate_items()]
    b = [i.model_dump() for i in generate_items()]
    assert a == b


def test_default_ratios_exact() -> None:
    for item in generate_items():
        assert item.realized_ratio == pytest.approx(item.target_ratio, abs=1e-12)


def test_strict_rejects_unrealizable_ladder() -> None:
    with pytest.raises(ValueError):
        generate_items(ladder=(0.24,), strict=True)
    items = generate_items(ladder=(0.24,), strict=False)
    small = [i for i in items if i.stakes is Stakes.SMALL]
    assert small and all(i.realized_ratio != i.target_ratio for i in small)


def test_target_constant_within_cell_ladder() -> None:
    for form in range(N_FORMS):
        items = generate_items(form=form)
        by_cell: dict[tuple[Relationship, History, Stakes], set[str]] = {}
        for i in items:
            by_cell.setdefault((i.relationship, i.history, i.stakes), set()).add(i.name)
        assert all(len(names) == 1 for names in by_cell.values())


def test_paired_orders_share_target() -> None:
    items = generate_items()
    by_point: dict[tuple[Relationship, History, Stakes, float], set[str]] = {}
    for i in items:
        key = (i.relationship, i.history, i.stakes, i.target_ratio)
        by_point.setdefault(key, set()).add(i.name)
    assert all(len(names) == 1 for names in by_point.values())


def test_forms_rotate_every_name_through_every_cell() -> None:
    seen: dict[tuple[Relationship, History, Stakes], set[str]] = {}
    for form in range(N_FORMS):
        for i in generate_items(form=form):
            seen.setdefault((i.relationship, i.history, i.stakes), set()).add(i.name)
    assert all(names == set(NAMES) for names in seen.values())


def test_names_balanced_within_form() -> None:
    names = Counter(i.name for i in generate_items())
    assert set(names) == set(NAMES)
    assert set(names.values()) == {100}  # 5 cells x 10 rungs x 2 orders


def test_option_order_prompts() -> None:
    for item in generate_items():
        a_line = item.prompt.split("(A) ")[1].split("\n")[0]
        if item.self_option == "A":
            assert a_line == f"You receive {item.self_amount} points."
        else:
            assert a_line == f"{item.name} receives {item.other_amount} points."
        assert str(item.self_amount) in item.prompt
        assert str(item.other_amount) in item.prompt


def test_history_uses_recent_interaction_frame() -> None:
    for item in generate_items():
        assert "no prior interaction" not in item.prompt
        assert "In the interaction leading up to this decision" in item.prompt


def test_ids_stable_and_unique_across_full_design() -> None:
    ids_a = [i.item_id for i in generate_items()]
    ids_b = [i.item_id for i in generate_items()]
    assert ids_a == ids_b
    everything = generate_all_forms()
    assert len(everything) == 3600
    assert len({i.item_id for i in everything}) == 3600


def test_ids_are_content_addressed() -> None:
    # Same rendered prompt and hashed metadata => same ID (across configs).
    a = {i.item_id: i.prompt for i in generate_items()}
    b = {i.item_id: i.prompt for i in generate_items(base_amount=20, large_multiplier=50)}
    for item_id in set(a) & set(b):
        assert a[item_id] == b[item_id]
    changed = [i for i in generate_items(base_amount=20, large_multiplier=50)
               if i.stakes is Stakes.SMALL]
    assert all(i.item_id not in a for i in changed)


def test_input_validation() -> None:
    for kwargs in (
        {"base_amount": 0},
        {"base_amount": -10},
        {"large_multiplier": 0},
        {"large_multiplier": -5},
        {"form": N_FORMS},
        {"form": -1},
        {"ladder": ()},
        {"ladder": (0.2, 0.2)},
        {"ladder": (0.4, 0.2)},
        {"ladder": (-0.2, 0.4)},
        {"ladder": (float("inf"),)},
    ):
        with pytest.raises(ValueError):
            generate_items(**kwargs)  # type: ignore[arg-type]
