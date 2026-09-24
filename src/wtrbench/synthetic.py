"""Synthetic responders with known rules, for pipeline recovery checks.

Each responder answers InferenceItems from a programmed rule. Running the
scoring pipeline on their answers checks that the pipeline recovers the
orderings each rule was built to produce. This validates the measurement
pipeline, not the psychological interpretation of any real model's answers.

Numeric rules apply to the aggregate family (two observed self-versus-you
choices). Attribution profiles supply programmed quantities by cause. The
Bayesian rule is restricted to the numeric family; it has an explicit prior,
choice-noise model, and prediction rule, all stated here.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field

from wtrbench.inference import (
    AGGREGATE_SETS,
    AggCell,
    Cause,
    InferenceItem,
    Probe,
)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# --------------------------------------------------------------------------- #
# Attribution profiles: programmed quantities by cause.
# valuation = inferred WTR toward "you"; will = P(agree); able_* = P(manage).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AttributionProfile:
    name: str
    valuation: dict[Cause, float]
    will: dict[Cause, float]
    able_same: dict[Cause, float]
    able_diff: dict[Cause, float] = field(default_factory=dict)


_B, _UW, _UA, _CN, _HL = (
    Cause.BASELINE, Cause.UNWILLING, Cause.UNABLE, Cause.CONSTRAINED, Cause.HELPED
)

#: The pattern the theory predicts: refusal lowers valuation and willingness
#: but not ability; trying-and-failing lowers same-task ability but not
#: valuation or willingness; the different-task ability is untouched.
THEORY = AttributionProfile(
    name="theory",
    valuation={_B: 0.6, _UW: 0.15, _UA: 0.8, _CN: 0.8, _HL: 1.3},
    will={_B: 0.7, _UW: 0.15, _UA: 0.8, _CN: 0.8, _HL: 0.95},
    able_same={_B: 0.8, _UW: 0.85, _UA: 0.15, _CN: 0.8, _HL: 0.95},
    able_diff={c: 0.8 for c in Cause},
)

#: Any failure lowers everything by the same amount, regardless of cause.
CAUSE_BLIND = AttributionProfile(
    name="cause_blind",
    valuation={_B: 0.6, _UW: 0.3, _UA: 0.3, _CN: 0.3, _HL: 1.3},
    will={_B: 0.7, _UW: 0.4, _UA: 0.4, _CN: 0.4, _HL: 0.95},
    able_same={_B: 0.8, _UW: 0.5, _UA: 0.5, _CN: 0.5, _HL: 0.95},
    able_diff={_B: 0.8, _UW: 0.5, _UA: 0.5, _CN: 0.5, _HL: 0.95},
)

#: Evidence is ignored entirely; every cause looks like baseline.
FLAT = AttributionProfile(
    name="flat",
    valuation={c: 0.6 for c in Cause},
    will={c: 0.7 for c in Cause},
    able_same={c: 0.8 for c in Cause},
    able_diff={c: 0.8 for c in Cause},
)


# --------------------------------------------------------------------------- #
# Numeric rules: map the observed choice pair to P(partner takes own payoff)
# as a function of the probe ratio x = partner_amount / your_amount.
# --------------------------------------------------------------------------- #

NumericRule = Callable[[AggCell], Callable[[float], float]]


def _threshold(w: float) -> Callable[[float], float]:
    return lambda x: 1.0 if x > w else 0.0


def min_ratio_rule(cell: AggCell) -> Callable[[float], float]:
    """Inferred WTR just below the smallest ratio at which the partner chose self."""
    return _threshold(min(g / lo for g, lo in cell) - 0.05)


def totals_rule(cell: AggCell) -> Callable[[float], float]:
    """Inferred WTR decreases in the total denied to 'you'; pattern ignored."""
    denied = sum(lo for _, lo in cell)
    return _threshold(max(0.05, 1.6 - denied / 50))


def bayesian_rule(cell: AggCell, k: float = 4.0, grid_n: int = 120) -> Callable[[float], float]:
    """Posterior predictive under a logistic noisy-choice model.

    Prior: uniform over w in [0.05, 3.0]. Likelihood of an observed self
    choice at ratio r given w: sigmoid(k * (r - w)). Prediction at probe ratio
    x: posterior-averaged sigmoid(k * (x - w)). Both observations update.
    """
    grid = [0.05 + i * (3.0 - 0.05) / (grid_n - 1) for i in range(grid_n)]
    weights = [1.0] * grid_n
    for g, lo in cell:
        r = g / lo
        weights = [wt * _sigmoid(k * (r - w)) for wt, w in zip(weights, grid, strict=True)]
    z = sum(weights)
    post = [wt / z for wt in weights]

    def predictive(x: float) -> float:
        return sum(p * _sigmoid(k * (x - w)) for p, w in zip(post, grid, strict=True))

    return predictive


# --------------------------------------------------------------------------- #
# Responders
# --------------------------------------------------------------------------- #

def _other(letter: str) -> str:
    return "B" if letter == "A" else "A"


@dataclass
class SyntheticResponder:
    """Answers from an attribution profile plus a numeric rule, with optional noise.

    ``noise`` is the logistic scale on the ladder decision (0 = deterministic)
    and is also used to blur binary probabilities toward 0.5.
    """

    name: str
    profile: AttributionProfile = THEORY
    numeric: NumericRule = min_ratio_rule
    noise: float = 0.0
    seed: int = 0
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def _p_keyed(self, item: InferenceItem) -> float:
        if item.probe in (Probe.INFER, Probe.OWN):
            assert item.realized_ratio is not None
            x = item.realized_ratio
            if item.family == "aggregate":
                assert item.agg_set is not None and item.diagnostic and item.totals
                cell = AGGREGATE_SETS[item.agg_set].cells[(item.diagnostic, item.totals)]
                p = self.numeric(cell)(x)
                if self.noise == 0:  # deterministic: follow the rule's majority prediction
                    return 1.0 if p > 0.5 else 0.0
                if p in (0.0, 1.0):  # blur a hard threshold rule
                    w = min(g / lo for g, lo in cell)
                    p = _sigmoid((x - w) / self.noise)
                return p
            assert item.cause is not None
            w = self.profile.valuation[item.cause]
            return _sigmoid((x - w) / self.noise) if self.noise > 0 else (1.0 if x > w else 0.0)
        assert item.cause is not None
        table = {
            Probe.WILL_SAME: self.profile.will,
            Probe.WILL_DIFF: self.profile.will,
            Probe.ABLE_SAME: self.profile.able_same,
            Probe.ABLE_DIFF: self.profile.able_diff or self.profile.able_same,
        }[item.probe]
        p = table[item.cause]
        if self.noise == 0:  # deterministic: majority answer of the programmed probability
            return 1.0 if p > 0.5 else 0.0
        return 0.5 + (p - 0.5) * (1 - min(self.noise, 1.0))

    def __call__(self, item: InferenceItem) -> str:
        keyed = self._rng.random() < self._p_keyed(item)
        return item.keyed_option if keyed else _other(item.keyed_option)


@dataclass
class OrderFollower:
    """Always answers the same letter, whatever the content."""

    letter: str = "A"
    name: str = "order_follower"

    def __call__(self, item: InferenceItem) -> str:
        return self.letter


@dataclass
class RandomResponder:
    name: str = "random"
    seed: int = 0
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def __call__(self, item: InferenceItem) -> str:
        return self._rng.choice("AB")


def standard_responders(
    noise: float = 0.0, seed: int = 0
) -> list[SyntheticResponder | OrderFollower | RandomResponder]:
    """The rival rules named in docs/inference-module-design.md section 7."""
    return [
        SyntheticResponder("theory+min_ratio", THEORY, min_ratio_rule, noise, seed),
        SyntheticResponder("theory+bayes", THEORY, bayesian_rule, noise, seed),
        SyntheticResponder("theory+totals", THEORY, totals_rule, noise, seed),
        SyntheticResponder("cause_blind+min_ratio", CAUSE_BLIND, min_ratio_rule, noise, seed),
        SyntheticResponder("flat+min_ratio", FLAT, min_ratio_rule, noise, seed),
        OrderFollower("A"),
        RandomResponder(seed=seed),
    ]
