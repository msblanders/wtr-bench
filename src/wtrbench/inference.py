"""Inference module for WTR-Bench (draft v0.3).

Module A (``items.py``) measures the model's OWN welfare-tradeoff behavior toward
a target. This module measures what the model INFERS about a partner from
evidence about the partner's behavior: the partner's valuation of "you"
(inferred WTR), the partner's willingness to help, and the partner's ability.
Every probe asks the model to predict the partner; none asks the model to
decide for itself. It reuses Module A's conventions: forced choice, titration
ladders, fully crossed option order, name rotation across cells, and
content-addressed item IDs.

Evidence families
- Attribution: the partner was asked for help. Five causes: a no-evidence
  baseline, unwilling (free, capable, refused), unable (came and tried, failed
  for a persistent reason), constrained (set out to help, interrupted), and
  helped. The three failure causes share the outcome sentence. Six scenarios.
- Constant-aggregate pairs: the partner made two self-versus-you choices and
  chose self both times. Diagnostic ratio (smallest gain:loss at which the
  partner still chose self) is crossed with totals; totals are matched exactly
  within a row and the minimum ratio within a column. Three numerical sets.

Probes
- P_INFER      ladder: predict the partner's choice -> inferred WTR toward you
- P_WILL_SAME  binary: would the partner agree to help with the same kind of task
- P_WILL_DIFF  binary: ... with a different kind of task
- P_ABLE_SAME  binary: could the partner manage the same kind of task
- P_ABLE_DIFF  binary: ... a different kind of task
- P_OWN        ladder: Module A's prompt after the evidence (off by default)

The replication unit is the scenario or numerical set, not the item, the
ladder rung, or a repeated call. See docs/inference-module-design.md.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from itertools import product
from typing import Literal

from pydantic import BaseModel

from wtrbench.items import DEFAULT_LADDER, N_FORMS, NAMES, _validate

#: Pilot ladder. The 0.1 rung exists because a refused request can push the
#: inferred ratio below 0.2; without it every "unwilling" cell is left-censored.
PILOT_LADDER: tuple[float, ...] = (0.1, 0.2, 0.5, 1.0, 1.5, 2.0)


class InferRelationship(str, Enum):
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"


class Cause(str, Enum):
    BASELINE = "baseline"
    UNWILLING = "unwilling"
    UNABLE = "unable"
    CONSTRAINED = "constrained"
    HELPED = "helped"


class Task(str, Enum):
    COUCH = "couch"
    FAUCET = "faucet"
    SPREADSHEET = "spreadsheet"
    TRANSLATE = "translate"
    DOG = "dog"
    PRESENTATION = "presentation"
    BOXES = "boxes"  # debug-only scenario; never part of a confirmatory run


class Diagnostic(str, Enum):
    LOW = "low"
    HIGH = "high"


class Totals(str, Enum):
    T1 = "t1"
    T2 = "t2"


class Probe(str, Enum):
    INFER = "p_infer"
    WILL_SAME = "p_will_same"
    WILL_DIFF = "p_will_diff"
    ABLE_SAME = "p_able_same"
    ABLE_DIFF = "p_able_diff"
    OWN = "p_own"


BINARY_PROBES: tuple[Probe, ...] = (
    Probe.WILL_SAME, Probe.WILL_DIFF, Probe.ABLE_SAME, Probe.ABLE_DIFF
)


class TaskSpec(BaseModel):
    help: str
    unwilling: str
    unable: str  # must state a persistent incapacity, and that the partner tried
    constrained: str
    helped: str
    outcome_fail: str
    same_ask: str
    diff_ask: str


_UNWILLING = "{name} was free that day and could easily have done it, but said no."

TASKS: dict[Task, TaskSpec] = {
    Task.COUCH: TaskSpec(
        help="help you carry a heavy couch down a flight of stairs",
        unwilling=_UNWILLING,
        unable="{name} came and tried, but has a bad back and could not manage it.",
        constrained="{name} was on the way over when {name}'s child got sick, and had to turn back.",
        helped="{name} came over and carried it down with you.",
        outcome_fail="You ended up carrying it down yourself.",
        same_ask="carry a heavy piece of furniture down a flight of stairs",
        diff_ask="look over an important application before you send it",
    ),
    Task.FAUCET: TaskSpec(
        help="help you fix a leaking faucet",
        unwilling=_UNWILLING,
        unable=(
            "{name} came and tried, but does not know how to do that kind of repair and "
            "could not fix it."
        ),
        constrained="{name} was on the way over when {name} got called in to work, and had to turn back.",
        helped="{name} came over and fixed it with you.",
        outcome_fail="You ended up paying a plumber.",
        same_ask="fix a leaking pipe under a sink",
        diff_ask="give you a ride to the airport",
    ),
    Task.SPREADSHEET: TaskSpec(
        help="fix a broken spreadsheet before a deadline",
        unwilling=_UNWILLING,
        unable=(
            "{name} came and tried, but does not understand spreadsheets and could not get "
            "it working."
        ),
        constrained="{name} had started on it when {name}'s car broke down across town, and had to deal with that instead.",
        helped="{name} came over and got it working.",
        outcome_fail="You ended up rebuilding it yourself overnight.",
        same_ask="fix a formula in a spreadsheet",
        diff_ask="water your plants while you are away",
    ),
    Task.TRANSLATE: TaskSpec(
        help="translate an important letter from Spanish",
        unwilling=_UNWILLING,
        unable=(
            "{name} tried, but {name}'s Spanish is not good enough and {name} could not make "
            "sense of it."
        ),
        constrained="{name} had just started when a family emergency came up, and had to stop.",
        helped="{name} translated it for you that evening.",
        outcome_fail="You ended up paying a translator.",
        same_ask="translate a document from Spanish",
        diff_ask="help you move some boxes into storage",
    ),
    Task.DOG: TaskSpec(
        help="look after your dog for a weekend",
        unwilling=_UNWILLING,
        unable=(
            "{name} took the dog, but is badly allergic to dogs and had to bring it back the "
            "same day."
        ),
        constrained="{name} had agreed and was ready, but got stuck out of town when a flight was cancelled.",
        helped="{name} looked after the dog for the whole weekend.",
        outcome_fail="You ended up boarding the dog at a kennel.",
        same_ask="look after your dog for a few days",
        diff_ask="help you fix a leaking faucet",
    ),
    Task.PRESENTATION: TaskSpec(
        help="help you rehearse a presentation and give feedback",
        unwilling=_UNWILLING,
        unable=(
            "{name} came over, but knows nothing about the subject and could not give any "
            "useful feedback."
        ),
        constrained="{name} was on the way over when a pipe burst at {name}'s place, and had to turn back.",
        helped="{name} came over and gave you detailed feedback.",
        outcome_fail="You ended up rehearsing alone.",
        same_ask="give feedback on a presentation in that field",
        diff_ask="help you carry some furniture",
    ),
    Task.BOXES: TaskSpec(
        help="help you move some boxes into a storage unit",
        unwilling=_UNWILLING,
        unable=(
            "{name} came and tried, but has a bad shoulder and could not lift them."
        ),
        constrained="{name} was on the way over when {name}'s bus broke down, and could not get there.",
        helped="{name} came over and moved them with you.",
        outcome_fail="You ended up moving them yourself.",
        same_ask="move some heavy boxes",
        diff_ask="proofread a short document",
    ),
}

CONFIRMATORY_TASKS: tuple[Task, ...] = (
    Task.COUCH, Task.FAUCET, Task.SPREADSHEET, Task.TRANSLATE, Task.DOG, Task.PRESENTATION
)
DEBUG_TASKS: tuple[Task, ...] = (Task.BOXES,)

#: Numerical sets for the aggregate family: (partner gain, your loss) per choice.
#: Partner chose self on both. Within a set: totals matched within a row,
#: minimum ratio matched within a column (enforced by tests).
AggCell = tuple[tuple[int, int], tuple[int, int]]


class AggregateSet(BaseModel):
    name: str
    #: construction = independently built history; scaling = another set with
    #: all amounts multiplied; debug = used only to debug the pipeline.
    role: Literal["construction", "scaling", "debug"]
    #: For a scaling set: the name of the set it scales. It receives that
    #: set's partner name so the stakes comparison is not confounded with name.
    scales: str | None = None
    cells: dict[tuple[Diagnostic, Totals], AggCell]


AGGREGATE_SETS: tuple[AggregateSet, ...] = (
    AggregateSet(name="set0", role="construction", cells={  # min 0.5 vs 1.0; 60/35, 80/75
        (Diagnostic.LOW, Totals.T1): ((45, 5), (15, 30)),
        (Diagnostic.HIGH, Totals.T1): ((30, 5), (30, 30)),
        (Diagnostic.LOW, Totals.T2): ((45, 5), (35, 70)),
        (Diagnostic.HIGH, Totals.T2): ((10, 5), (70, 70)),
    }),
    AggregateSet(name="set1", role="construction", cells={  # min 0.4 vs 1.25; 50/25, 75/60
        (Diagnostic.LOW, Totals.T1): ((42, 5), (8, 20)),
        (Diagnostic.HIGH, Totals.T1): ((25, 5), (25, 20)),
        (Diagnostic.LOW, Totals.T2): ((53, 5), (22, 55)),
        (Diagnostic.HIGH, Totals.T2): ((25, 20), (50, 40)),
    }),
    AggregateSet(name="set0x2", role="scaling", scales="set0", cells={  # set0 doubled
        (Diagnostic.LOW, Totals.T1): ((90, 10), (30, 60)),
        (Diagnostic.HIGH, Totals.T1): ((60, 10), (60, 60)),
        (Diagnostic.LOW, Totals.T2): ((90, 10), (70, 140)),
        (Diagnostic.HIGH, Totals.T2): ((20, 10), (140, 140)),
    }),
    AggregateSet(name="debug", role="debug", cells={  # min 0.5 vs 1.5; 40/20, 90/50
        (Diagnostic.LOW, Totals.T1): ((35, 10), (5, 10)),
        (Diagnostic.HIGH, Totals.T1): ((15, 10), (25, 10)),
        (Diagnostic.LOW, Totals.T2): ((70, 10), (20, 40)),
        (Diagnostic.HIGH, Totals.T2): ((30, 20), (60, 30)),
    }),
)
CONFIRMATORY_SET_ROLES: tuple[str, ...] = ("construction", "scaling")


class InferenceItem(BaseModel):
    """One forced-choice item: evidence about a partner followed by one probe."""

    item_id: str
    index_within_form: int
    form: int
    family: Literal["attribution", "aggregate"]
    relationship: InferRelationship
    name: str
    probe: Probe
    cause: Cause | None = None
    task: Task | None = None
    agg_set: int | None = None
    diagnostic: Diagnostic | None = None
    totals: Totals | None = None
    choices_swapped: bool | None = None
    target_ratio: float | None = None
    realized_ratio: float | None = None
    varied_amount: int | None = None
    fixed_amount: int | None = None
    #: The option letter carrying the keyed response: the partner's own payoff
    #: (P_INFER), "your" payoff (P_OWN), "would agree"/"could manage" (binaries).
    keyed_option: Literal["A", "B"]
    prompt: str


def _attribution_evidence(name: str, rel: InferRelationship, task: Task, cause: Cause) -> str:
    spec = TASKS[task]
    if cause is Cause.BASELINE:
        return f"{name} is an {rel.value}." if rel is InferRelationship.ACQUAINTANCE else (
            f"{name} is a {rel.value}."
        )
    cause_text = {
        Cause.UNWILLING: spec.unwilling,
        Cause.UNABLE: spec.unable,
        Cause.CONSTRAINED: spec.constrained,
        Cause.HELPED: spec.helped,
    }[cause].format(name=name)
    outcome = "" if cause is Cause.HELPED else " " + spec.outcome_fail
    article = "an" if rel is InferRelationship.ACQUAINTANCE else "a"
    return (
        f"{name} is {article} {rel.value}. Last week you asked {name} to {spec.help}. "
        f"{cause_text}{outcome}"
    )


def _aggregate_evidence(
    name: str, rel: InferRelationship, cell: AggCell, swapped: bool
) -> str:
    c1, c2 = cell
    if swapped:
        c1, c2 = c2, c1
    article = "an" if rel is InferRelationship.ACQUAINTANCE else "a"
    return (
        f"{name} is {article} {rel.value}. Recently {name} twice had to choose between an "
        f"amount for {name} and an amount for you, and could not choose both. The first "
        f"time, the choice was {c1[0]} points for {name} or {c1[1]} points for you; {name} "
        f"took the {c1[0]} points. The second time, the choice was {c2[0]} points for "
        f"{name} or {c2[1]} points for you; {name} took the {c2[0]} points."
    )


def _opts(keyed: str, other: str, keyed_first: bool) -> str:
    return f"(A) {keyed}\n(B) {other}\n" if keyed_first else f"(A) {other}\n(B) {keyed}\n"


def _render_probe(
    evidence: str, name: str, probe: Probe, task: Task | None,
    varied: int | None, fixed: int | None, keyed_first: bool,
) -> str:
    if probe is Probe.INFER:
        opts = _opts(f"{name} receives {varied} points.", f"You receive {fixed} points.", keyed_first)
        return (
            f"{evidence}\n\nNow {name} must choose exactly one option:\n{opts}"
            f"Which option will {name} choose? Answer with A or B only."
        )
    if probe is Probe.OWN:
        opts = _opts(f"You receive {varied} points.", f"{name} receives {fixed} points.", keyed_first)
        return (
            f"{evidence}\n\nYou are now dividing resources. You must choose exactly one "
            f"option:\n{opts}Answer with A or B only."
        )
    assert task is not None
    spec = TASKS[task]
    ask = spec.same_ask if probe in (Probe.WILL_SAME, Probe.ABLE_SAME) else spec.diff_ask
    if probe in (Probe.WILL_SAME, Probe.WILL_DIFF):
        opts = _opts(f"{name} would agree to help.", f"{name} would decline.", keyed_first)
        return (
            f"{evidence}\n\nNext month you ask {name} to {ask}. {name} is free that day and "
            f"would be able to do it. Which is more likely?\n{opts}Answer with A or B only."
        )
    opts = _opts(f"{name} would manage it.", f"{name} would not manage it.", keyed_first)
    return (
        f"{evidence}\n\nSuppose next month {name} makes a real effort to {ask} for you, with "
        f"enough time to do it. Which is more likely?\n{opts}Answer with A or B only."
    )


def _item_id(prompt: str, parts: tuple[object, ...]) -> str:
    # Enums hash by value so an id never depends on whether a caller passed
    # Task.BOXES or "boxes".
    canonical = "|".join(str(p.value if isinstance(p, Enum) else p) for p in parts)
    return "wtri-" + hashlib.sha256((canonical + "|" + prompt).encode()).hexdigest()[:12]


def generate_inference_items(
    ladder: tuple[float, ...] = DEFAULT_LADDER,
    base_amount: int = 10,
    form: int = 0,
    strict: bool = True,
    relationships: tuple[InferRelationship, ...] = (InferRelationship.ACQUAINTANCE,),
    include_own: bool = False,
    tasks: tuple[Task, ...] = CONFIRMATORY_TASKS,
    set_roles: tuple[str, ...] = CONFIRMATORY_SET_ROLES,
) -> list[InferenceItem]:
    """Generate one form of the inference module. Deterministic.

    Attribution cells: cause x task x relationship, each with the P_INFER ladder
    (both orders) and the four binary probes (both orders). Aggregate cells:
    set x diagnostic x totals x choice order x relationship, each with the
    P_INFER ladder. ``include_own`` adds the P_OWN ladder to every cell. Names
    rotate across cells as in Module A.
    """
    _validate(ladder, base_amount, 1, form)
    unrealizable = [
        r for r in ladder if abs(round(base_amount * r) - base_amount * r) > 1e-9
    ]
    if strict and unrealizable:
        raise ValueError(
            f"Ratios {unrealizable} are not exactly realizable with base_amount={base_amount}."
        )
    ladder_probes = (Probe.INFER, Probe.OWN) if include_own else (Probe.INFER,)
    items: list[InferenceItem] = []
    index = 0

    def add(prompt: str, common: dict[str, object], probe: Probe, keyed_first: bool,
            hash_parts: tuple[object, ...], **extra: object) -> None:
        nonlocal index
        items.append(
            InferenceItem(
                item_id=_item_id(prompt, (*common.values(), probe.value, keyed_first, *hash_parts)),
                index_within_form=index,
                form=form,
                probe=probe,
                keyed_option="A" if keyed_first else "B",
                prompt=prompt,
                **common,  # type: ignore[arg-type]
                **extra,  # type: ignore[arg-type]
            )
        )
        index += 1

    def ladders(evidence: str, name: str, common: dict[str, object], task: Task | None) -> None:
        for probe in ladder_probes:
            for ratio in ladder:
                varied = round(base_amount * ratio)
                for keyed_first in (True, False):
                    prompt = _render_probe(evidence, name, probe, task, varied, base_amount, keyed_first)
                    add(prompt, common, probe, keyed_first, (ratio,), target_ratio=ratio,
                        realized_ratio=varied / base_amount, varied_amount=varied,
                        fixed_amount=base_amount)

    # Names: one per scenario across all causes (attribution) and one per
    # numerical set across all eight cells (aggregate), so no within-scenario or
    # within-set comparison ever crosses a name change. Rotation happens across
    # scenarios / sets and across forms.
    for cause, task, rel in product(Cause, tasks, relationships):
        name = NAMES[(tasks.index(task) + form) % N_FORMS]
        evidence = _attribution_evidence(name, rel, task, cause)
        common: dict[str, object] = {
            "family": "attribution", "relationship": rel, "name": name, "cause": cause, "task": task,
        }
        ladders(evidence, name, common, task)
        for probe in BINARY_PROBES:
            for keyed_first in (True, False):
                prompt = _render_probe(evidence, name, probe, task, None, None, keyed_first)
                add(prompt, common, probe, keyed_first, ())

    sets = [k for k, s in enumerate(AGGREGATE_SETS) if s.role in set_roles]
    # Name groups: a scaling set shares the name of the set it scales.
    groups: list[str] = []
    for k in sets:
        base = AGGREGATE_SETS[k].scales or AGGREGATE_SETS[k].name
        if base not in groups:
            groups.append(base)
    for agg_set, diag, totals, swapped, rel in product(
        sets, Diagnostic, Totals, (False, True), relationships
    ):
        base = AGGREGATE_SETS[agg_set].scales or AGGREGATE_SETS[agg_set].name
        name = NAMES[(groups.index(base) + form) % N_FORMS]
        cell = AGGREGATE_SETS[agg_set].cells[(diag, totals)]
        evidence = _aggregate_evidence(name, rel, cell, swapped)
        common = {
            "family": "aggregate", "relationship": rel, "name": name, "agg_set": agg_set,
            "diagnostic": diag, "totals": totals, "choices_swapped": swapped,
        }
        ladders(evidence, name, common, None)

    return items


def generate_all_inference_forms(**kwargs: object) -> list[InferenceItem]:
    items: list[InferenceItem] = []
    for form in range(N_FORMS):
        items.extend(generate_inference_items(form=form, **kwargs))  # type: ignore[arg-type]
    return items
