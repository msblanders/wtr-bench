"""Offline tests for paired-natural-v3.1.

The oracle below derives every gated key from the *displayed stipulation
sentences* (standing rules, stipulated chances, stipulated absence or
randomness of information). It does not import the material pools or call
truth(). A stress test confirms it disagrees with the production keys when the
give/keep rule templates are swapped in memory, which the v3.0 oracle could
not detect. What no oracle can check is whether a stipulation is a *good*
control; that is the plan's job.
"""
import json
import re
from collections import Counter
from copy import deepcopy
from itertools import product

import pytest

from wtrbench.paired import natural as n

RULE = re.compile(r"^In this points task, whenever (\w+) is offered the exact choice described below, "
                  r"\1 always (gives|keeps) (?:you )?the points, without exception\.$")
NO_INFO = re.compile(r"^You know (\w+) only by name and have no information ")
RANDOM = re.compile(r"^(\w+)'s badge number is \d+; badge numbers were assigned at random ")
UNEQUAL = re.compile(r"^With genuine effort and enough time, (\w+) is far more likely than (\w+) ")
EQUAL = re.compile(r"^With genuine effort and enough time, (\w+) and (\w+) have equal chances ")


def literal_key(prompt: str) -> str | None:
    """Independent key from displayed stipulations; None when nothing is stipulated."""
    lines = prompt.splitlines()
    a = next(line[4:] for line in lines if line.startswith("(A) "))
    b = next(line[4:] for line in lines if line.startswith("(B) "))
    ability = "makes a real effort to" in prompt
    if ability:
        for line in lines:
            m = UNEQUAL.match(line)
            if m:
                return "A" if m.group(1) == a else "B"
            m = EQUAL.match(line)
            if m:
                assert {m.group(1), m.group(2)} == {a, b}
                return "C"
        return None
    rules = {m.group(1): m.group(2) for m in map(RULE.match, lines) if m}
    if set(rules) == {a, b}:
        if rules[a] == rules[b]:
            return "C"
        return "A" if rules[a] == "gives" else "B"
    blank = {m.group(1) for line in lines for m in [NO_INFO.match(line) or RANDOM.match(line)] if m}
    if blank == {a, b} and not rules:
        return "D"
    return None


def test_schedule_shape_ids_and_distinct_prompts() -> None:
    items = n.generate_items()
    assert len(items) == 280 and len({i["item_id"] for i in items}) == 280
    assert Counter(i["category"] for i in items) == {c: 40 for c in n.CATEGORIES}
    assert Counter(i["gated"] for i in items) == {True: 240, False: 40}
    assert Counter((i["repetition"], i["name_assignment"], i["position"]) for i in items) == {
        k: 35 for k in product((1, 2), (0, 1), (0, 1))
    }
    assert items == n.generate_items()
    # 132 distinct prompts: 20 per category shown twice, except `insufficient` (12 of 40),
    # whose no-information sentence is identical for both people and repeats across
    # cases with the same payoff. The equality controls do NOT collapse (their cues differ).
    distinct = len({i["prompt"] for i in items})
    assert distinct == 132
    per_cat = {c: len({i["prompt"] for i in items if i["category"] == c}) for c in n.CATEGORIES}
    assert per_cat == {c: (12 if c == "insufficient" else 20) for c in n.CATEGORIES}
    p1 = [i["prompt"] for i in items if i["repetition"] == 1]
    p2 = [i["prompt"] for i in items if i["repetition"] == 2]
    assert sorted(p1) == sorted(p2) and p1 != p2


def test_oracle_agrees_with_every_gated_key_and_abstains_on_exploratory() -> None:
    for item in n.generate_items():
        key = literal_key(item["prompt"])
        if item["gated"]:
            expected = next(k for k, v in item["semantic_map"].items() if v == item["expected_private"])
            assert key == expected, item["case_id"]
        else:
            assert key is None and item["expected_private"] is None
            assert item["exploratory_expected_private"] == "P"


def test_oracle_detects_swapped_rule_templates(monkeypatch) -> None:
    # The v3.0 oracle keyed off pool labels and passed even with pools swapped.
    # This one keys off displayed text, so a swap must produce disagreements.
    give, keep = n.GIVE_RULE, n.KEEP_RULE
    monkeypatch.setattr(n, "GIVE_RULE", keep)
    monkeypatch.setattr(n, "KEEP_RULE", give)
    disagreements = 0
    for item in n.generate_items():
        if item["category"] == "policy_determined":
            expected = next(k for k, v in item["semantic_map"].items() if v == item["expected_private"])
            disagreements += literal_key(item["prompt"]) != expected
    assert disagreements == 40


def test_keys_do_not_depend_on_regard_cues() -> None:
    cases = {c["case_id"]: c for c in n.cases()}
    # aligned, conflicting and absent cues all key to the rule-follower
    for j in range(1, 6):
        assert n.truth(cases[f"policy_determined-{j}"]) == "P"
    assert cases["policy_determined-3"]["P"][0] in n.COLD  # conflicting cue on the giver
    assert cases["policy_determined-5"]["P"] == [n.GIVE_RULE]  # no cue at all
    for j in range(1, 6):
        c = cases[f"policy_equal-{j}"]
        assert c["P"][0] in n.WARM and c["Q"][0] in n.COLD and n.truth(c) == "equal"


def test_conflict_and_distractor_share_ability_stipulation_and_key_opposite_people() -> None:
    cases = {c["case_id"]: c for c in n.cases()}
    for j in range(1, 6):
        conflict, distractor = cases[f"ability_conflict-{j}"], cases[f"valuation_distractor-{j}"]
        assert conflict["joint"] == distractor["joint"] == ["ability_unequal:Q"]
        assert n.truth(conflict) == "Q" and n.truth(distractor) == "P"
        assert conflict["probe"] == "ability" and distractor["probe"] == "valuation"


def test_no_computation_and_no_held_out_material() -> None:
    for item in n.generate_items():
        p = item["prompt"]
        digits = {tok for tok in p.replace(".", " ").replace(",", " ").replace(";", " ").split()
                  if tok.isdigit()}
        badges = {str(b) for pair in n.BADGES for b in pair}
        assert digits <= {"5", "10"} | badges, digits
        for held_out in ("couch", "faucet", "spreadsheet", "spanish", "dog", "presentation",
                         "airport", "application", "furniture", "plumber"):
            assert held_out not in p.lower(), held_out


def test_names_bound_before_position() -> None:
    case = n.cases()[0]
    p00, m00 = n.render(case, 0, 0)
    p01, m01 = n.render(case, 0, 1)
    p10, m10 = n.render(case, 1, 0)
    assert m00 == {"A": "P", "B": "Q", "C": "equal", "D": "insufficient"}
    assert m01["A"] == "Q" and m10["A"] == "P"
    assert p00.startswith("Sam and Priya") and p01.startswith("Priya and Sam")
    assert p10.startswith("Priya and Sam") and p10 != p01


def test_request_body_matches_v2_protocol_and_leaks_nothing() -> None:
    for item in n.generate_items()[:14]:
        body = n.request_body(item)
        assert list(body) == ["model", "temperature", "max_tokens", "system", "messages", "output_config"]
        assert body["output_config"]["format"]["schema"]["properties"]["answer"]["enum"] == ["A", "B", "C", "D"]
        assert body["messages"][0]["content"] == item["prompt"]
        for secret in ("expected", "case_id", "repetition", "semantic", "gated", "exploratory"):
            assert secret not in json.dumps(body)


def _api(text: str, mid: str) -> dict:
    return {"id": mid, "model": n.MODEL, "stop_reason": "end_turn",
            "content": [{"type": "text", "text": text}]}


def _rows(items, letter_for):
    return [{"item_id": i["item_id"], "request_body": n.request_body(i),
             "api_response": _api(json.dumps({"brief_basis": "x", "answer": letter_for(i)}),
                                  f"msg_{k}"), "request_id": f"req_{k}"}
            for k, i in enumerate(items)]


def _key_letter(i):
    target = i["expected_private"] or i["exploratory_expected_private"]
    return next(k for k, v in i["semantic_map"].items() if v == target)


def test_gate_covers_gated_only_and_exploratory_is_reported_not_gated() -> None:
    items = n.generate_items()
    oracle = n.summarize(items, _rows(items, _key_letter))
    assert oracle["gate"] == "PASS" and oracle["pilot_authorized"] is False
    assert all(oracle["categories"][c]["joint_correct"] == 20 for c in n.GATED)
    ex = oracle["categories"]["regard_deeds"]
    assert ex["gated"] is False and ex["correct"] is None and ex["as_expected"] == 40
    assert ex["pass_gate"] is None and ex["joint_as_expected"] == 20 and "joint_correct" not in ex
    # exploratory answers cannot change the gate
    def flip_exploratory(i):
        return "D" if i["category"] == "regard_deeds" else _key_letter(i)
    still = n.summarize(items, _rows(items, flip_exploratory))
    assert still["gate"] == "PASS" and still["categories"]["regard_deeds"]["as_expected"] == 0
    always_a = n.summarize(items, _rows(items, lambda i: "A"))
    assert always_a["gate"] == "FAIL"
    assert always_a["false_strict_ordering_on_stipulated_equality"]["count"] == 80
    always_d = n.summarize(items, _rows(items, lambda i: "D"))
    assert always_d["gate"] == "FAIL" and always_d["D_on_determined"]["count"] == 200
    assert always_d["categories"]["insufficient"]["joint_correct"] == 20
    # exception-free wording is what makes the equality keys entailed
    assert "without exception" in n.GIVE_RULE and "without exception" in n.KEEP_RULE
    assert "reliably" not in n.GIVE_RULE and "reliably" not in n.KEEP_RULE


def test_truncated_and_malformed_outputs_are_unusable_not_repaired() -> None:
    item = n.generate_items()[0]
    truncated = {"id": "m", "model": n.MODEL, "stop_reason": "max_tokens",
                 "content": [{"type": "text", "text": '{"brief_basis": "so A'}]}
    d = n.decode(item, truncated)
    assert d["answer"] is None and d["semantic"] is None and not d["correct"]
    assert n.decode(item, _api(json.dumps({"answer": "A", "brief_basis": "x"}), "m2"))["answer"] is None
    assert n.decode(item, _api("A", "m3"))["answer"] is None


def test_validate_records_rejects_altered_or_duplicate_rows() -> None:
    items = n.generate_items()
    rows = _rows(items[:3], lambda i: "C")
    n.validate_records(items, rows)
    bad = deepcopy(rows)
    bad[1]["request_body"]["messages"][0]["content"] += " "
    with pytest.raises(ValueError):
        n.validate_records(items, bad)
    dup = deepcopy(rows)
    dup[2]["api_response"]["id"] = dup[0]["api_response"]["id"]
    with pytest.raises(ValueError):
        n.validate_records(items, dup)


def test_manifest_hashes_frozen_sources(tmp_path) -> None:
    m = n.manifest()
    assert m["n_requests"] == 280 and m["n_base_cases"] == 35
    assert set(m["source_sha256"]) == set(n.SOURCE_FILES)
    assert n.verify_freeze() == m
    exported = n.export(tmp_path)
    assert exported == n.generate_items()
    assert json.loads((tmp_path / "freeze.json").read_text()) == m
    assert (tmp_path / "items.jsonl").read_text() == "".join(n.wire(i) + "\n" for i in exported)
    assert (tmp_path / "requests.jsonl").read_text() == "".join(
        n.wire(n.request_body(i)) + "\n" for i in exported)
    assert not (tmp_path / "responses.jsonl").exists()
