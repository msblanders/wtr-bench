"""Matched original / explicit-payoff history controls: 288 fixed requests."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from wtrbench.validation_recovery import (
    RecoveryItem,
)
from wtrbench.validation_recovery import (
    generate_items as recovery_items,
)

PROTOCOL = "payoff-presentation-v1"
PRESENTATIONS = ("original", "explicit_payoffs")
Presentation = Literal["original", "explicit_payoffs"]


class PresentationItem(RecoveryItem):
    presentation: Presentation
    source_item_id: str
    source_template_id: str


def stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def explicit_payoffs(prompt: str) -> str:
    """Render each existing alternative as a complete outcome; add no inference."""
    pattern = (r"The choice was (\d+) points for Sam or (\d+) points for you; "
               r"Sam chose the (\d+) points for (Sam|you)\.")

    def history(match: re.Match[str]) -> str:
        own, other, selected, recipient = match.groups()
        if selected != (own if recipient == "Sam" else other):
            raise ValueError("History choice disagrees with its displayed payoff")
        chosen = 1 if recipient == "Sam" else 2
        return ("\n\nThe available outcomes in this decision were:\n"
                "| Outcome | Points for Sam | Points for you |\n"
                "|---|---:|---:|\n"
                f"| 1 | {own} | 0 |\n| 2 | 0 | {other} |\n"
                f"Sam chose outcome {chosen}.")

    rendered, n = re.subn(pattern, history, prompt)
    if n != 2:
        raise ValueError("Expected exactly two choice-history decisions")
    options = re.findall(r"\(([AB])\) (Sam|You) receives? (\d+) points\.", rendered)
    if len(options) != 2 or [k for k, _, _ in options] != ["A", "B"]:
        raise ValueError("Expected ordered A/B alternatives")
    lines = ["| Option | Points for Sam | Points for you |", "|---|---:|---:|"]
    for letter, who, amount in options:
        own, other = (amount, "0") if who == "Sam" else ("0", amount)
        lines.append(f"| {letter} | {own} | {other} |")
    rendered = re.sub(r"\(A\) (?:Sam|You) receives? \d+ points\.\n"
                      r"\(B\) (?:Sam|You) receives? \d+ points\.", "\n".join(lines), rendered)
    return "\n".join(line.rstrip() for line in rendered.splitlines())


def generate_items() -> list[PresentationItem]:
    result = []
    for source in recovery_items():
        if source.arm != "choice_history":
            continue
        for presentation in PRESENTATIONS:
            prompt = source.prompt if presentation == "original" else explicit_payoffs(source.prompt)
            template = "wtr-presentation-template-" + stable_hash(
                [PROTOCOL, source.template_id, presentation, prompt])[:16]
            result.append(PresentationItem.model_validate({**source.model_dump(),
                "presentation": presentation, "source_item_id": source.item_id,
                "source_template_id": source.template_id, "prompt": prompt,
                "template_id": template,
                "item_id": "wtr-presentation-" + stable_hash([template, source.repetition])[:16]}))
    # Both presentations are interleaved within each pass, in one prospective sequence.
    return sorted(result, key=lambda i: (i.repetition, stable_hash([PROTOCOL, i.item_id])))


def main() -> None:
    from wtrbench.presentation_run import main as run_main

    run_main()


if __name__ == "__main__":
    main()
