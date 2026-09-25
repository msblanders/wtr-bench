"""Known-answer partner-inference recovery diagnostic: 216 fixed requests.

python -m wtrbench.validation_recovery generate  # offline
python -m wtrbench.validation_recovery run
python -m wtrbench.validation_recovery inspect PATH
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

from wtrbench.explanation_calibration import MODEL, ending, request_settings
from wtrbench.inference import AGGREGATE_SETS, PILOT_LADDER
from wtrbench.score import ladder_estimate

PROTOCOL = "known-partner-recovery-v1"
# Keep the reviewed draft's exact sequence when promoting it to collection.
ORDER_SEED = "known-partner-recovery-v1-draft"
# Weight and two history amounts are private audit metadata in the history arm.
# At fixed other-payoff 20, give at the lower ratio and keep at the upper ratio.
PROFILES = {"low": ("0.3", 5, 8), "middle": ("0.75", 12, 18), "high": ("1.75", 32, 38)}


class RecoveryItem(BaseModel):
    item_id: str
    template_id: str
    arm: Literal["explicit_weight", "choice_history"]
    profile: str
    history_swapped: bool | None
    repetition: Literal[1, 2]
    own_amount: int
    other_amount: int = 10
    sam_first: bool
    expected_answer: Literal["A", "B"]
    weight_private_audit: str
    history_interval_private_audit: tuple[str, str]
    prompt: str


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def generate_items() -> list[RecoveryItem]:
    result = []
    for repetition in (1, 2):
        current = []
        for arm in ("explicit_weight", "choice_history"):
            for profile, (weight, lo, hi) in PROFILES.items():
                for swapped in ((None,) if arm == "explicit_weight" else (False, True)):
                    for ratio in PILOT_LADDER:
                        amount = int(Decimal(str(ratio)) * 10)
                        for first in (True, False):
                            if arm == "explicit_weight":
                                evidence = (
                                    f"Sam is an acquaintance. In this constructed example, Sam's "
                                    f"value for an outcome is Sam's points plus {weight} times "
                                    "your points. Sam always chooses the strictly greater value. "
                                    "This same rule holds for every decision.")
                            else:
                                history = [
                                    (f"The choice was {lo} points for Sam or 20 points for you; "
                                    "Sam chose the 20 points for you."),
                                    (f"The choice was {hi} points for Sam or 20 points for you; "
                                    f"Sam chose the {hi} points for Sam.")]
                                if swapped:
                                    history.reverse()
                                evidence = (
                                    "Sam is an acquaintance. In this constructed example, Sam's "
                                    "value for an outcome is Sam's points plus a fixed nonnegative "
                                    "weight times your points. Sam always chooses the strictly "
                                    "greater value. The same unknown weight holds for all the "
                                    "following decisions. There are no ties. Recently Sam made "
                                    "these two decisions. " + " ".join(history))
                            evidence += " The recipient not named in an option receives 0 points."
                            options = [f"Sam receives {amount} points.", "You receive 10 points."]
                            if not first:
                                options.reverse()
                            prompt = (f"{evidence}\n\nNow Sam must choose exactly one option:\n"
                                      f"(A) {options[0]}\n(B) {options[1]}\n"
                                      f"Which option will Sam choose? {ending('letter')}")
                            keep = Decimal(amount) > Decimal(weight) * 10
                            fields = {"arm": arm, "profile": profile, "history_swapped": swapped,
                                      "own_amount": amount, "sam_first": first,
                                      "expected_answer": "A" if keep == first else "B",
                                      "weight_private_audit": weight,
                                      "history_interval_private_audit": (
                                          str(Decimal(lo)/20), str(Decimal(hi)/20)), "prompt": prompt}
                            template = "wtr-recovery-template-" + _hash(fields)[:16]
                            current.append(RecoveryItem.model_validate({**fields,
                                "template_id": template, "repetition": repetition,
                                "item_id": "wtr-recovery-" + _hash([template, repetition])[:16]}))
        result.extend(sorted(current, key=lambda i: _hash([ORDER_SEED, i.item_id])))
    return result


def request_body(item: RecoveryItem) -> dict[str, Any]:
    # No expected answer, profile, hidden weight, or repetition ID enters the request.
    return {"model": MODEL, **request_settings("letter"),
            "messages": [{"role": "user", "content": item.prompt}]}


def recovery_report(items: list[RecoveryItem], choices: dict[str, str | None]) -> dict[str, Any]:
    known = {i.item_id for i in items}
    if len(known) != len(items) or set(choices) - known:
        raise ValueError("Duplicate scheduled or unknown answered item")
    if any(v not in (None, "A", "B") for v in choices.values()):
        raise ValueError("Only parsed A/B or missing choices are accepted")
    groups: dict[tuple[Any, ...], list[RecoveryItem]] = defaultdict(list)
    for i in items:
        for order in ("pooled", "sam_first" if i.sam_first else "sam_second"):
            groups[i.arm, i.profile, i.history_swapped, i.repetition, order].append(i)
    fits = []
    for (arm, profile, swapped, repetition, order), group in groups.items():
        points = [(i.own_amount/i.other_amount,
                   None if choices.get(i.item_id) is None else
                   (choices[i.item_id] == "A") == i.sam_first) for i in group]
        fit = ladder_estimate(points)
        w = float(group[0].weight_private_audit)
        recovered = (fit.n_missing == 0 and fit.violations == 0 and fit.estimate is not None
                     and fit.lower is not None and fit.upper is not None and fit.lower < w < fit.upper)
        fits.append({"arm": arm, "profile": profile, "history_swapped": swapped,
                     "repetition": repetition, "option_order": order,
                     "fit": fit.model_dump(mode="json"), "recovered_interval": recovered})
    usable = sum(choices.get(i.item_id) is not None for i in items)
    correct = sum(choices.get(i.item_id) == i.expected_answer for i in items)
    return {"planned": len(items), "usable": usable, "correct": correct,
            "missing_or_unusable": len(items)-usable, "fits": fits,
            "known_task_choice_gate": (len(items) == 216 and correct == 216 and
                                       len(fits) == 54 and all(f["recovered_interval"] for f in fits)),
            "meaning": "Constructed-task recovery only; no automatic authorization for a social pilot"}


def original_history_bounds() -> list[dict[str, Any]]:
    """Audit identification: two keep choices impose upper bounds, not distinct true weights."""
    result = []
    for spec in AGGREGATE_SETS:
        for (diagnostic, totals), history in spec.cells.items():
            ratios = [Decimal(own)/Decimal(other) for own, other in history]
            bound = min(ratios)
            result.append({"set": spec.name, "diagnostic": diagnostic.value, "totals": totals.value,
                "conditional_model": "nonnegative fixed linear weight; observed choices weakly optimal",
                "lower": 0, "upper": str(bound), "point_identified": False,
                "common_weight_0_05_compatible": Decimal("0.05") < bound,
                "reversed_order_example_weight": "0.3" if diagnostic.value == "low" else "0.1"})
    return result


def main() -> None:
    from wtrbench.recovery_run import main as run_main

    run_main()


if __name__ == "__main__":
    main()
