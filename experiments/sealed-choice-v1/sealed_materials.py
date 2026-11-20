"""Matched post-choice randomization in three fictional settings."""

import hashlib
from itertools import product

STORIES = {
    "breakfast": {
        "people": ("Eli", "Noor"), "helpers": ("Mira", "Jon"),
        "intro": (
            "Two presenters have tomorrow's dawn and noon radio shows. The station lists Eli at "
            "dawn and Noor at noon. A breakfast kit prepared for a show will be served to whichever "
            "presenter hosts it. Both volunteers privately read this schedule and understood it to be final."
        ),
        "jobs": ("prepared the kit to be served before sunrise", "prepared the kit to be served at midday"),
        "setting": "show assignments",
    },
    "equipment": {
        "people": ("Inez", "Leon"), "helpers": ("Asha", "Finn"),
        "intro": (
            "Two photographers have camera bookings for tomorrow. The desk lists Inez for the "
            "square-socket camera and Leon for the round-socket camera. Each spare battery fits only "
            "the matching socket. Charging it gives the eventual user an extra hour. Both technicians "
            "privately read the bookings and understood them to be final."
        ),
        "jobs": ("charged the spare with four straight sides", "charged the spare with the circular connector"),
        "setting": "camera bookings",
    },
    "archive": {
        "people": ("Bea", "Drew"), "helpers": ("Leah", "Omar"),
        "intro": (
            "Two researchers will use the archive tomorrow. The briefing lists Bea for the maps and "
            "Drew for the interviews. Repairing the punch mechanism unlocks the maps' card index. "
            "Repairing the reel drive unlocks the interviews' recorded index. Whoever uses a collection "
            "gets the benefit of its working index. Both restorers privately read the briefing and "
            "understood these assignments to be final."
        ),
        "jobs": ("repaired the jammed punch mechanism", "restored the faulty reel drive"),
        "setting": "collection assignments",
    },
}
CHOICE = (
    "Both helpers could do nothing for free or spend three personal credits on either job. "
    "Each chose privately. The jobs cost the same, and neither brought the helper any return. "
    "Both jobs succeeded."
)


def material(story, family_index, form, outcome, probe):
    target_index, flip = divmod(form, 2)
    target = story["people"][target_index]
    helpers = story["helpers"]
    owners = helpers[::1 if flip == 0 else -1]
    options = helpers[::1 if (target_index + family_index) % 2 == 0 else -1]
    order = (0, 1) if (flip + family_index) % 2 == 0 else (1, 0)
    actions = [f"{owners[i]} {story['jobs'][i]}." for i in order]
    sealed = (
        f"Next, each helper privately sealed a separate decision about whether to keep five points "
        f"or give ten points to {target}. Either could afford it. Both decisions were final once "
        "sealed. Neither saw the other's decision. The two recipients had equal need, and no other "
        "relationship information is available."
    )
    draw = (
        "Only after the decisions were sealed, an administrator used a fresh fair coin to settle "
        f"the {story['setting']}. No helper knew there would be a draw. Its result was independent "
        "of the people, the jobs, and the sealed decisions."
    )
    event = {"stand": "The draw left the two assignments as originally listed.",
             "swap": "The draw exchanged the two assignments."}[outcome]
    question = (f"Which helper was more likely to have sealed a decision to give {target} the ten points?"
                if probe == "forecast" else f"Whose earlier work actually provided the benefit that {target} received?")
    text = "\n".join([story["intro"], CHOICE, *actions, sealed, draw, event,
                      "Both recipients used their final assignments. The sealed decisions remain undisclosed.",
                      question, f"(A) {options[0]}", f"(B) {options[1]}",
                      "(C) Equally likely", "(D) Insufficient evidence"])
    return text, {"original": owners[target_index], "other": owners[1 - target_index],
                  "target": target, "options": list(options),
                  "actual": owners[target_index if outcome == "stand" else 1 - target_index]}


def items():
    rows = []
    for idx, (family, story) in enumerate(STORIES.items()):
        for form, outcome, probe in product(range(4), ("stand", "swap"), ("forecast", "fact")):
            text, key = material(story, idx, form, outcome, probe)
            for repeat in range(2 if probe == "forecast" else 1):
                ident = f"{family}-{form}-{outcome}-{probe}-{repeat+1}"
                rows.append({"id": ident, "prompt": text, "family": family, "form": form,
                             "outcome": outcome, "probe": probe, "repeat": repeat+1, **key})
    return sorted(rows, key=lambda r: hashlib.sha256(("sealed-choice-v1/" + r["id"]).encode()).digest())
