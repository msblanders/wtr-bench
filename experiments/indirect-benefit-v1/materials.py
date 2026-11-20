"""Costly actions, helpers' information, and the actual beneficiary."""

import hashlib
from itertools import product

STORIES = {
    "breakfast": {
        "helpers": ("Mira", "Jon"), "people": ("Eli", "Noor"),
        "setup": (
            "At a radio station the presenter at each broadcast gets a hot breakfast if someone "
            "prepares the food for that broadcast. The food is served immediately and cannot "
            "be saved. On the schedule the kitchen volunteers both read, Eli had the dawn show "
            "and Noor had the noon show. Before any food preparation, the producer exchanged "
            "the presenters' shifts. Noor actually hosted at dawn and Eli at noon."
        ),
        "seen": "Both kitchen volunteers read the revised schedule before arranging the breakfasts.",
        "unseen": "The revised schedule stayed in the studio. Both volunteers still relied on the original schedule when arranging the breakfasts.",
        "work": ("prepared the first meal before sunrise", "cooked the second meal just before midday"),
    },
    "equipment": {
        "helpers": ("Asha", "Finn"), "people": ("Inez", "Leon"),
        "setup": (
            "Two photographers borrow different cameras. Only the camera with a square socket "
            "can use a square battery pack, and only the one with a round socket can use a round "
            "pack. Whoever takes a camera gets the extra hour of use if someone charges its spare. "
            "Both technicians saw the original booking: Inez had the square-socket camera and Leon "
            "the round-socket camera. The desk then exchanged their bookings. Inez took the "
            "round-socket camera and Leon took the square-socket camera."
        ),
        "seen": "The desk called both technicians with the corrected bookings before either worked on a spare.",
        "unseen": "The desk never contacted the technicians. When they worked on the spares, both still understood the original bookings to be in effect.",
        "work": ("charged the spare with the four straight sides", "charged the spare with the circular connector"),
    },
    "archive": {
        "helpers": ("Leah", "Omar"), "people": ("Bea", "Drew"),
        "setup": (
            "Two researchers each work with one archive collection. Repairing the punch mechanism "
            "makes the card index usable for the person studying the maps. Restoring the reel "
            "drive makes the recorded index usable for the person studying the interviews. "
            "The restorers were both briefed that Bea would study maps and Drew interviews. "
            "The researchers then traded collections, so Bea used the interviews and Drew the maps."
        ),
        "seen": "Before allocating their time, both restorers attended the meeting explaining the new division of work.",
        "unseen": "Neither restorer attended the meeting or heard about it. Both allocated their time on the understanding given at their original briefing.",
        "work": ("repaired the jammed punch mechanism", "restored the faulty reel drive"),
    },
}
VOLUNTARY = (
    "Each helper privately had the same three options: do nothing for free, or spend three "
    "personal credits on either of the two jobs. Both jobs cost the same and neither brought "
    "the helper any return. Each decided independently."
)
ASSIGNED = (
    "A fair lottery assigned one job to each helper and deducted three personal credits from "
    "each. Neither could decline, change jobs, or alter the deduction. They privately carried "
    "out their assignments."
)
CLOSING = (
    "Both jobs worked. The people receiving the benefits never learned who did the work. "
    "Neither helper received any later information about who benefited. There is no other "
    "information about relationships, and the two recipients have equal need."
)


def items():
    output = []
    for number, (family, story) in enumerate(STORIES.items()):
        helpers, people = story["helpers"], story["people"]
        for form, access, probe in product(range(4), ("seen", "unseen"),
                                           ("actual", "expected", "forecast", "assigned_forecast")):
            target, action_flip = divmod(form, 2)
            action_owner = [helpers[action_flip], helpers[1 - action_flip]]
            options = helpers[::1 if (target + number) % 2 == 0 else -1]
            order = (0, 1) if (action_flip + number) % 2 == 0 else (1, 0)
            lines = [f"{action_owner[j]} {story['work'][j]}." for j in order]
            target_name = people[target]
            if probe == "actual":
                question = f"Whose work actually provided the benefit that {target_name} received?"
            elif probe == "expected":
                question = (f"At the time the helpers took their actions, whose work did the "
                            f"helpers have reason to expect would benefit {target_name}?")
            else:
                question = (f"Later, each helper can privately keep five points or give ten points "
                            f"to {target_name}. Either can afford it and the transfer is guaranteed. "
                            f"Who is more likely to give {target_name} the points?")
            text = "\n".join([story["setup"], story[access],
                              ASSIGNED if probe == "assigned_forecast" else VOLUNTARY,
                              *lines, CLOSING, question, f"(A) {options[0]}", f"(B) {options[1]}",
                              "(C) Equally likely", "(D) Insufficient evidence"])
            ident = hashlib.sha256(text.encode()).hexdigest()[:20]
            old_helper = action_owner[target]
            actual_helper = action_owner[1 - target]
            output.append({"id": ident, "prompt": text, "family": family, "form": form,
                           "access": access, "probe": probe, "target": target_name,
                           "options": list(options), "original": old_helper, "actual": actual_helper,
                           "expected": actual_helper if access == "seen" else old_helper})
    return sorted(output, key=lambda r: hashlib.sha256(("indirect-v1/" + r["id"]).encode()).digest())
