"""Paired natural v3.2: premise-following validation in natural language.

v3.0 was reviewed before collection and revised: its "known answers" rested on
plausible social inferences (a helpful person will give; matched experience
means equal ability) rather than on stipulation, and its D option excluded
relevant-but-insufficient evidence. v3.0 was never collected. In v3.1 every
gated key follows from an explicit premise in the prompt: a standing rule for
the allocation, stipulated equal or unequal chances at the task, or stipulated
absence or randomness of information. Regard cues appear only as distractors.
The deeds-and-statements inference is kept as an ungated exploratory category
with an expected answer, not a key. v3.2 (pre-collection revision of v3.1):
the allocation rules are exception-free, so two people under the same rule
have entailed-equal giving likelihood rather than merely "reliable"
compliance; the distinct-prompt disclosure and the description of the two
dimension controls are corrected; the exploratory pair count is labelled
as-expected rather than correct. Neither v3.1 nor v3.0 was collected.

python -m wtrbench.paired.natural generate --out runs/paired-v3
python -m wtrbench.paired.natural run --out runs/paired-v3 --confirm 280
python -m wtrbench.paired.natural report --out runs/paired-v3

Successor to paired-ordinal-v2, which failed its gate. v2 is recorded as a
failure of that numerical inference-and-response procedure; nothing here
treats it as evidence that qualitative inference works. This batch checks the
things a gate can check without computation: following a stated rule to a
comparative answer, preserving stipulated equality, abstaining under
stipulated insufficiency, and following the requested dimension when regard
and ability cues conflict. The only numbers are the fixed keep/give amounts
in the question and, in two cases, badge numbers stipulated to be random.

There is deliberately no social-pilot generator or collection route here. The
pilot will reuse ``render_pair`` so its preamble and options are identical.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from typing import Any

PROTOCOL = "paired-natural-v3.2"
MODEL = "claude-sonnet-4-5-20250929"
BASE = "061880e0c8c50bd7b858b1df470f867b69cd3706"
ROOT = Path(__file__).resolve().parents[3]
PLAN = "docs/paired-natural-v3.2.md"
FREEZE = "protocols/paired-natural-v3.2.json"
GATED = ("policy_determined", "policy_equal", "insufficient",
         "ability_conflict", "ability_equal", "valuation_distractor")
EXPLORATORY = ("regard_deeds",)
CATEGORIES = GATED + EXPLORATORY
SOURCE_FILES = ("src/wtrbench/paired/__init__.py", "src/wtrbench/paired/natural.py",
                "tests/test_paired_natural_v3.py", PLAN,
                ".github/workflows/paired-natural-v3.2.yml")

# --------------------------------------------------------------------------- #
# Materials. Gated keys come only from STIPULATIONS. Regard cues (WARM / COLD)
# and the exploratory deeds pools are never keys; they are distractors or
# substantive predictions. None of the six held-out pilot scenarios or their
# follow-up tasks appear here (enforced by a test).
# --------------------------------------------------------------------------- #

GIVE_RULE = ("In this points task, whenever {n} is offered the exact choice described below, "
             "{n} always gives you the points, without exception.")
KEEP_RULE = ("In this points task, whenever {n} is offered the exact choice described below, "
             "{n} always keeps the points, without exception.")
NO_INFO = ("You know {n} only by name and have no information about how {n} treats you or "
           "chooses in situations like this.")
RANDOM_LABEL = ("{n}'s badge number is {k}; badge numbers were assigned at random and are "
                "unrelated to anything else about the person.")
ABILITY_UNEQUAL = ("With genuine effort and enough time, {skilled} is far more likely than "
                   "{unskilled} to manage to {task}: {skilled} does it routinely and "
                   "{unskilled} has never done it. Their attitudes toward you do not change "
                   "those chances.")
ABILITY_EQUAL = ("With genuine effort and enough time, {a} and {b} have equal chances of "
                 "managing to {task}. Their differing attitudes toward you do not change "
                 "those chances.")

WARM = (
    "{n} has been generous to you in the past and speaks warmly of you.",
    "{n} once went out of the way to help you and says you can count on {n}.",
    "{n} has always been friendly and considerate toward you.",
    "{n} helped you through a hard week and has said that you matter to {n}.",
    "{n} has treated you kindly whenever your paths have crossed.",
)
COLD = (
    "{n} has been dismissive of you in the past and speaks coolly of you.",
    ("{n} once declined to help you when it would have been easy, and says your problems "
    "are your own."),
    "{n} has been distant and offhand toward you.",
    "{n} ignored you during a hard week and has said that you do not much matter to {n}.",
    "{n} has treated you curtly whenever your paths have crossed.",
)
HIGH_REGARD = (
    ("{n} lent you a car for a week when yours broke down and would not hear of being paid, "
    "and has said more than once that you can count on {n}."),
    ("{n} drove across town late one night to bring you the keys you had left behind, and "
    "told you afterward that it was no trouble and to ask any time."),
    ("{n} took a day off work to sit with you in the hospital, and has gone out of the way "
    "for you on several occasions since."),
    ("{n} spoke up for you at length when a colleague criticized you unfairly, knowing it "
    "would cost {n} some goodwill, and has said that you matter to {n}."),
    ("{n} covered two of your shifts at short notice without needing to be asked twice, and "
    "has told you that helping you is something {n} is glad to do."),
)
LOW_REGARD = (
    ("{n} left you stranded at a train station rather than cut a lunch short, and has said "
    "more than once that what happens to you is not really {n}'s concern."),
    ("{n} declined to bring you the keys you had left behind, though {n} was free and lived "
    "nearby, and told you afterward that it was not {n}'s problem."),
    ("{n} did not visit or call when you were in the hospital, though {n} knew, and has said "
    "that {n} does not see why {n} should go out of the way for you."),
    ("{n} joined in when a colleague criticized you unfairly, and has said that {n} does not "
    "much care how things turn out for you."),
    ("{n} refused to cover a shift for you when {n} was free to, and has told you plainly "
    "that your problems are yours to deal with."),
)
SKILL_TASKS = (
    "repair a flat bicycle tire", "bake bread for a party", "file a straightforward tax return",
    "change a car tire at the roadside", "tune a guitar by ear",
)
BADGES = ((4471, 3082), (1905, 7734), (6210, 2588), (9147, 5306), (3359, 8821))
OWN_AMOUNTS = (5, 10, 5, 10, 5)
OTHER_AMOUNT = 10


def wire(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def stream_hash(values: list[Any]) -> str:
    return hashlib.sha256("".join(wire(v) + "\n" for v in values).encode()).hexdigest()


def cases() -> list[dict[str, Any]]:
    """Thirty-five base cases: six gated categories and one exploratory category,
    five materials sets each. Person P and Q each get a list of sentences; some
    sentences are joint (mention both) and are appended once, after both."""
    out = []
    for category in CATEGORIES:
        for j in range(5):
            p: list[str] = []
            q: list[str] = []
            joint: list[str] = []
            probe = "valuation"
            if category == "policy_determined":
                # cues aligned (j=0,1), conflicting (j=2,3), absent (j=4); rule decides
                if j in (0, 1):
                    p, q = [WARM[j]], [COLD[j]]
                elif j in (2, 3):
                    p, q = [COLD[j]], [WARM[j]]
                p, q = [*p, GIVE_RULE], [*q, KEEP_RULE]
            elif category == "policy_equal":
                rule = GIVE_RULE if j < 3 else KEEP_RULE
                p, q = [WARM[j], rule], [COLD[j], rule]
            elif category == "insufficient":
                if j < 3:
                    p, q = [NO_INFO], [NO_INFO]
                else:
                    p, q = [RANDOM_LABEL.replace("{k}", str(BADGES[j][0]))], \
                           [RANDOM_LABEL.replace("{k}", str(BADGES[j][1]))]
            elif category == "ability_conflict":
                p, q, joint, probe = [WARM[j]], [COLD[j]], ["ability_unequal:Q"], "ability"
            elif category == "ability_equal":
                p, q, joint, probe = [WARM[j]], [COLD[j]], ["ability_equal"], "ability"
            elif category == "valuation_distractor":
                p, q, joint = [WARM[j], GIVE_RULE], [COLD[j], KEEP_RULE], ["ability_unequal:Q"]
            else:  # regard_deeds: exploratory, no key
                p, q = [HIGH_REGARD[j]], [LOW_REGARD[j]]
            out.append({"case_id": f"{category}-{j + 1}", "category": category,
                        "P": p, "Q": q, "joint": joint, "probe": probe,
                        "task": SKILL_TASKS[j], "own": OWN_AMOUNTS[j]})
    return out


def truth(case: dict[str, Any]) -> str | None:
    """Expected semantic answer: 'P', 'Q', 'equal', 'insufficient', or None (exploratory)."""
    return {
        "policy_determined": "P", "policy_equal": "equal", "insufficient": "insufficient",
        "ability_conflict": "Q", "ability_equal": "equal", "valuation_distractor": "P",
        "regard_deeds": None,
    }[case["category"]]


def expected_exploratory(case: dict[str, Any]) -> str | None:
    """The substantive prediction for an exploratory case (reported, never gated)."""
    return "P" if case["category"] == "regard_deeds" else None


def render_pair(first: str, second: str, evidence: list[str], probe: str, *,
                own: int, task: str) -> str:
    """Shared by the validation batch and, later, the pilot: identical preamble and options.

    C means the information supports equal likelihood. D means the information is
    insufficient to support either an ordering or equal likelihood, which covers
    absent, incomplete and conflicting information. Precedence when nothing
    relevant is given about either person: D, stated in the preamble.
    """
    lines = [
        (f"{first} and {second} are two people you know. Answer using only the information "
         "given below. Choose A or B if the information supports one of them being more "
         "likely. Choose C only if the information supports their being equally likely. "
         "Choose D if the information is insufficient to support either an ordering or equal "
         "likelihood, including when there is no relevant information about either person."),
        "",
        *evidence,
        "",
    ]
    if probe == "valuation":
        lines.append(f"Now each of them must choose exactly one option: keep {own} points for "
                     f"themselves, or give you {OTHER_AMOUNT} points. Which of them is more "
                     f"likely to give you the {OTHER_AMOUNT} points?")
    else:
        lines.append(f"Suppose next month each of them makes a real effort to {task} for you, "
                     "with enough time to do it. Which of them is more likely to manage it?")
    lines.extend([f"(A) {first}", f"(B) {second}",
                  "(C) The information supports their being equally likely.",
                  ("(D) The information is insufficient to support either an ordering or "
                   "equal likelihood.")])
    return "\n".join(lines)


def render(case: dict[str, Any], assignment: int, position: int) -> tuple[str, dict[str, str]]:
    # Bind names to people BEFORE choosing presentation order: two distinct factors.
    names = dict(zip(("P", "Q"), ("Priya", "Sam") if assignment else ("Sam", "Priya")))
    order = ("Q", "P") if position else ("P", "Q")
    evidence: list[str] = []
    for who in order:
        evidence.extend(t.format(n=names[who]) for t in case[who])
    for stip in case["joint"]:
        first, second = names[order[0]], names[order[1]]
        if stip == "ability_equal":
            evidence.append(ABILITY_EQUAL.format(a=first, b=second, task=case["task"]))
        else:  # "ability_unequal:<skilled person>"
            skilled = names[stip.split(":")[1]]
            unskilled = names["P" if stip.endswith("Q") else "Q"]
            evidence.append(ABILITY_UNEQUAL.format(skilled=skilled, unskilled=unskilled,
                                                   task=case["task"]))
    prompt = render_pair(names[order[0]], names[order[1]], evidence, case["probe"],
                         own=case["own"], task=case["task"])
    mapping = {"A": order[0], "B": order[1], "C": "equal", "D": "insufficient"}
    return prompt, mapping


def generate_items() -> list[dict[str, Any]]:
    out = []
    for repetition in (1, 2):
        batch = []
        for case, assignment, position in product(cases(), (0, 1), (0, 1)):
            prompt, mapping = render(case, assignment, position)
            item = {"case_id": case["case_id"], "category": case["category"],
                    "gated": case["category"] in GATED,
                    "name_assignment": assignment, "position": position, "repetition": repetition,
                    "prompt": prompt, "semantic_map": mapping, "expected_private": truth(case),
                    "exploratory_expected_private": expected_exploratory(case)}
            item["item_id"] = PROTOCOL + "-" + digest(item)[:20]
            batch.append(item)
        batch.sort(key=lambda x: digest([PROTOCOL, x["item_id"]]))
        out.extend(batch)
    return out


def request_body(item: dict[str, Any]) -> dict[str, Any]:
    return {"model": MODEL, "temperature": 0, "max_tokens": 256,
        "system": 'Return exactly two JSON fields in this order: "brief_basis", a one- or '
                  'two-sentence explanation using the supplied information; then "answer", '
                  'one of A, B, C, D. Do not include any other fields.',
        "messages": [{"role": "user", "content": item["prompt"]}],
        "output_config": {"format": {"type": "json_schema", "schema": {
            "type": "object", "properties": {"brief_basis": {"type": "string"},
            "answer": {"type": "string", "enum": ["A", "B", "C", "D"]}},
            "required": ["brief_basis", "answer"], "additionalProperties": False}}}}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, field in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = field
    return value


def decode(item: dict[str, Any], api: dict[str, Any]) -> dict[str, Any]:
    answer, basis = None, None
    blocks = api.get("content")
    if (api.get("stop_reason") == "end_turn" and isinstance(blocks, list) and len(blocks) == 1
            and isinstance(blocks[0], dict) and blocks[0].get("type") == "text"):
        try:
            value = json.loads(blocks[0]["text"], object_pairs_hook=_unique_object)
            if (isinstance(value, dict) and list(value) == ["brief_basis", "answer"]
                    and isinstance(value["brief_basis"], str) and value["brief_basis"].strip()
                    and isinstance(value["answer"], str) and value["answer"] in ("A", "B", "C", "D")):
                answer, basis = value["answer"], value["brief_basis"]
        except (ValueError, TypeError, KeyError):
            pass
    semantic = item["semantic_map"].get(answer)
    expected = item["expected_private"]
    return {"answer": answer, "brief_basis": basis, "semantic": semantic,
            "correct": (semantic is not None and semantic == expected) if expected else None,
            "as_expected": (semantic == item["exploratory_expected_private"])
            if item["exploratory_expected_private"] else None}


def manifest() -> dict[str, Any]:
    items = generate_items()
    return {"protocol": PROTOCOL, "baseline_commit": BASE, "n_requests": len(items),
            "n_base_cases": len(cases()), "items_jsonl_sha256": stream_hash(items),
            "request_bodies_jsonl_sha256": stream_hash([request_body(i) for i in items]),
            "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                              for p in SOURCE_FILES}}


def verify_freeze() -> dict[str, Any]:
    actual = manifest()
    if json.loads((ROOT / FREEZE).read_text()) != actual:
        raise ValueError("Freeze mismatch: use the committed revision; do not rewrite a used freeze")
    return actual


def validate_records(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    if len(rows) > len(items):
        raise ValueError("Too many records")
    messages: set[str] = set()
    requests: set[str] = set()
    for item, row in zip(items, rows):
        if row.get("item_id") != item["item_id"] or wire(row.get("request_body")) != wire(request_body(item)):
            raise ValueError("Unknown, reordered, duplicate, or altered request")
        api = row["api_response"]
        if api.get("model") != MODEL:
            raise ValueError("Returned model mismatch")
        mid = api.get("id")
        if not isinstance(mid, str) or not mid or mid in messages:
            raise ValueError("Missing or duplicate message id")
        messages.add(mid)
        rid = row.get("request_id")
        if rid is not None:
            if not isinstance(rid, str) or not rid or rid in requests:
                raise ValueError("Invalid or duplicate request id")
            requests.add(rid)


def summarize(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    if items != generate_items():
        raise ValueError("Only the complete fixed schedule may be scored")
    validate_records(items, rows)
    decoded = {r["item_id"]: decode(i, r["api_response"]) for i, r in zip(items, rows)}
    missing = {"answer": None, "semantic": None, "correct": False, "as_expected": None}
    stats: dict[str, dict[str, Any]] = {}
    for category in CATEGORIES:
        gated = category in GATED
        subset = [i for i in items if i["category"] == category]
        answers = [decoded.get(i["item_id"], missing) for i in subset]
        d: dict[str, Any] = {"gated": gated, "base_cases": 5, "scheduled_answers": 40,
            "correct": sum(bool(a["correct"]) for a in answers) if gated else None,
            "as_expected": None if gated else sum(bool(a["as_expected"]) for a in answers),
            "unusable_or_missing": sum(a["answer"] is None for a in answers),
            "C": sum(a["answer"] == "C" for a in answers),
            "D": sum(a["answer"] == "D" for a in answers),
            "strict_ordering": sum(a["answer"] in ("A", "B") for a in answers)}
        for factor, fields in {
            "position": ("case_id", "name_assignment", "repetition"),
            "name": ("case_id", "position", "repetition"),
            "repeat": ("case_id", "name_assignment", "position"),
        }.items():
            pairs: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
            for item in subset:
                pairs[tuple(item[f] for f in fields)].append(item)
            joint: Counter[str] = Counter()
            comparable = disagree = 0
            for pair in pairs.values():
                if len(pair) != 2:
                    raise ValueError("Incomplete factorial pair")
                a, b = [decoded.get(i["item_id"], missing) for i in pair]
                if a["semantic"] is not None and b["semantic"] is not None:
                    comparable += 1
                    disagree += a["semantic"] != b["semantic"]
                hit = (a["correct"] and b["correct"]) if gated else (a["as_expected"] and b["as_expected"])
                if hit:
                    joint[str(pair[0]["repetition"])] += 1
            d[factor] = {"scheduled_pairs": len(pairs), "comparable_pairs": comparable,
                         "disagreements": disagree}
            if factor == "position":
                label = "joint_correct" if gated else "joint_as_expected"
                d[label] = sum(joint.values())
                d["joint_by_pass"] = {str(r): joint[str(r)] for r in (1, 2)}
                d["joint_rate"] = sum(joint.values()) / 20
                d["pass_gate"] = all(joint[str(r)] >= 9 for r in (1, 2)) if gated else None
        d["base_cases_all_eight_correct"] = sum(
            all(bool(decoded.get(i["item_id"], missing)["correct"]) for i in subset if i["case_id"] == cid)
            for cid in {i["case_id"] for i in subset}) if gated else None
        stats[category] = d
    d_errors = sum(stats[c]["D"] for c in GATED if c != "insufficient")
    false_orderings = stats["policy_equal"]["strict_ordering"] + stats["ability_equal"]["strict_ordering"]
    complete = len(rows) == len(items)
    passes = complete and all(stats[c]["pass_gate"] for c in GATED) and d_errors <= 10
    return {"protocol": PROTOCOL, "data_origin": "Recorded outputs; provenance in collection-started.json",
            "complete": complete, "recorded": len(rows), "scheduled": len(items),
            "distinct_prompts": len({i["prompt"] for i in items}),
            "categories": stats, "D_on_determined": {"count": d_errors, "denominator": 200},
            "false_strict_ordering_on_stipulated_equality": {"count": false_orderings, "denominator": 80},
            "gate": "PASS" if passes else ("FAIL" if complete else "INCOMPLETE"),
            "gate_scope": "The six gated categories only; regard_deeds is exploratory and never gated.",
            "explanation_review": "Not performed by this scorer; answers are never repaired from prose",
            "pilot_authorized": False,
            "pilot_eligibility": ("A PASS makes the pilot eligible; authorization is a separate review "
                                  "decision recorded after the pilot's own plan and scorer are committed."),
            "interpretation": "Chosen finite-set development tolerance, not a population error bound."}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export(out: Path) -> list[dict[str, Any]]:
    frozen = verify_freeze()
    if (out / "collection-started.json").exists() or (out / "responses.jsonl").exists():
        raise FileExistsError("Do not overwrite a started collection")
    out.mkdir(parents=True, exist_ok=True)
    items = generate_items()
    for name, values in (("items.jsonl", items), ("requests.jsonl", [request_body(i) for i in items])):
        (out / name).write_text("".join(wire(v) + "\n" for v in values), encoding="utf-8")
    write_json(out / "freeze.json", frozen)
    (out / "analysis-plan.md").write_bytes((ROOT / PLAN).read_bytes())
    return items


def report(out: Path) -> dict[str, Any]:
    verify_freeze()
    if json.loads((out / "freeze.json").read_text()) != manifest():
        raise ValueError("Run freeze mismatch")
    rows = [json.loads(line) for line in (out / "responses.jsonl").read_text().splitlines()]
    items = generate_items()
    result = summarize(items, rows)
    write_json(out / "report.json", result)
    by_id = {r["item_id"]: r for r in rows}
    with (out / "answer-audit.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = ["item_id", "case_id", "category", "gated", "name_assignment", "position",
                  "repetition", "expected_private", "exploratory_expected_private", "answer",
                  "semantic", "correct", "as_expected", "brief_basis", "stop_reason"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for item in items:
            row = by_id.get(item["item_id"], {})
            api = row.get("api_response", {})
            writer.writerow({**{f: item[f] for f in fields if f in item}, **decode(item, api),
                             "stop_reason": api.get("stop_reason", "missing")})
    text = [f"# {PROTOCOL}: {result['gate']}", "",
            (f"Records: {len(rows)}/280. Base cases: 35 (six gated categories, one exploratory). "
            f"Distinct prompts: {result['distinct_prompts']}. Six categories have 20 distinct prompts "
            "shown twice; insufficient has 12 across 40 requests (eight shown twice, two four "
            "times, and two eight times)."),
            "The gate concerns the six gated categories only; it does not authorize a social pilot.", "",
            ("| Category | Gated | Correct or as-expected / 40 | Joint pass 1 / 10 | Joint pass 2 / 10 "
            "| C | D | A/B | Unusable/missing |"),
            "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for cat, s in result["categories"].items():
        n_ok = s["correct"] if s["gated"] else s["as_expected"]
        text.append(f"| {cat} | {'yes' if s['gated'] else 'no'} | {n_ok} | {s['joint_by_pass']['1']} | "
                    f"{s['joint_by_pass']['2']} | {s['C']} | {s['D']} | {s['strict_ordering']} | "
                    f"{s['unusable_or_missing']} |")
    text.extend(["", "See report.json for position, name and repeat comparisons with denominators.",
                 "See answer-audit.csv for every scheduled item, including missing responses.",
                 "Repeated presentations are not independent participants or fresh scenarios."])
    (out / "report.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return result


def collect(out: Path, send: Callable[[dict[str, Any]], tuple[dict[str, Any], str | None]],
            *, data_origin: str = "programmed_test_fixture") -> None:
    items = export(out)
    with (out / "collection-started.json").open("x", encoding="utf-8") as lock:
        json.dump({"data_origin": data_origin, "started_utc": datetime.now(UTC).isoformat(),
            "github_sha": os.environ.get("GITHUB_SHA"), "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "python": platform.python_version(),
            "sdk_version": importlib.metadata.version("anthropic") if data_origin == "anthropic_api" else None,
            "max_retries": 0, "freeze": manifest()}, lock, indent=2)
    rows = []
    with (out / "responses.jsonl").open("x", encoding="utf-8") as fh:
        for item in items:
            body = request_body(item)
            try:
                api, request_id = send(body)
            except Exception as exc:
                write_json(out / "transport-stop.json", {"item_id": item["item_id"],
                           "exception_type": type(exc).__name__, "attempted_body": body})
                raise
            row = {"item_id": item["item_id"], "request_body": body,
                   "api_response": api, "request_id": request_id}
            fh.write(wire(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            rows.append(row)  # Preserve raw output before any integrity failure.
            validate_records(items, rows)
            if len(rows) % 20 == 0:
                print(f"Recorded {len(rows)}/280", flush=True)
    report(out)


_CLIENT: Any = None


def send_anthropic(body: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    global _CLIENT
    if _CLIENT is None:
        from anthropic import Anthropic
        _CLIENT = Anthropic(max_retries=0, timeout=120.0)
    message = _CLIENT.messages.create(
        model=body["model"], max_tokens=body["max_tokens"], system=body["system"],
        messages=body["messages"], output_config=body["output_config"],
        extra_body={"temperature": body["temperature"]})
    return message.model_dump(mode="json"), getattr(message, "_request_id", None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check", "report", "run", "samples"))
    parser.add_argument("--out", type=Path, default=Path("runs/paired-v3"))
    parser.add_argument("--confirm", type=int)
    args = parser.parse_args()
    if args.command == "run":
        if args.confirm != 280:
            parser.error("Collection requires --confirm 280 after reviewing the committed plan")
        if os.environ.get("GITHUB_RUN_ATTEMPT", "1") != "1":
            parser.error("GitHub Re-run jobs is disabled for this collection")
        collect(args.out, send_anthropic, data_origin="anthropic_api")
    elif args.command == "report":
        print(json.dumps(report(args.out), indent=2))
    elif args.command == "check":
        print(wire(verify_freeze()))
    elif args.command == "samples":
        for case in cases():
            if case["case_id"].endswith("-1"):
                prompt, _ = render(case, 0, 0)
                key = truth(case) or f"(exploratory; expected {expected_exploratory(case)})"
                print(f"### {case['case_id']}  key={key}\n\n```text\n{prompt}\n```\n")
    else:
        print(f"Exported {len(export(args.out))} scheduled requests. No model calls.")


if __name__ == "__main__":
    main()
