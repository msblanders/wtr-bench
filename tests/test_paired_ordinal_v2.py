"""Offline tests; the literal-prompt oracle does not call the production truth function."""
import json
import re
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import product

import pytest

from wtrbench.paired import ordinal as o


def literal_answer(prompt: str) -> str:
    """Read displayed names/payoffs; independently enumerate rational interior weights."""
    labels = dict(re.findall(r"^\(([AB])\) (\w+)$", prompt, re.MULTILINE))
    skills = dict(re.findall(r"^(\w+)'s success probability: (\d+)%\.$", prompt, re.MULTILINE))
    if skills:
        a, b = [int(skills[labels[x]]) for x in ("A", "B")]
        return "C" if a == b else ("A" if a > b else "B")
    pattern = (r"^(\w+) chose (GIVE|KEEP) when the alternatives were "
               r"KEEP \((\w+): (\d+); you: 0\) or GIVE \((\w+): 0; you: (\d+)\)\.$")
    bounds = {}
    for person, choice, keeper, own, giver, other in re.findall(pattern, prompt, re.MULTILINE):
        assert person == keeper == giver
        bounds.setdefault(person, {})[choice] = Fraction(int(own), int(other))
    assert len(bounds) == 2 and all(set(b) == {"GIVE", "KEEP"} for b in bounds.values())
    own, other = map(int, re.search(
        r"Now each independently chooses between KEEP \(self: (\d+); you: 0\) "
        r"and GIVE \(self: 0; you: (\d+)\)", prompt).groups())
    choices = []
    for label in ("A", "B"):
        lo, hi = bounds[labels[label]]["GIVE"], bounds[labels[label]]["KEEP"]
        assert lo < hi
        states = []
        for n in range(1, 80):
            weight = lo + Fraction(n, 80) * (hi - lo)
            if weight * other != own:
                states.append(weight * other > own)
        choices.append(states)
    results = {"C" if a == b else ("A" if a else "B") for a, b in product(*choices)}
    return next(iter(results)) if len(results) == 1 else "D"


def records(rule=None):
    result = []
    for k, item in enumerate(o.generate_items()):
        answer = literal_answer(item["prompt"]) if rule is None else rule(item)
        api = {"id": f"programmed-{k}", "model": o.MODEL, "stop_reason": "end_turn",
               "content": [{"type": "text", "text": json.dumps(
                   {"brief_basis": "PROGRAMMED SOFTWARE TEST, NOT A MODEL RESULT", "answer": answer})}]}
        result.append({"item_id": item["item_id"], "request_body": o.request_body(item),
                       "api_response": api, "request_id": f"test-request-{k}"})
    return result


def test_full_schedule_and_literal_keys():
    items = o.generate_items()
    assert items == o.generate_items() and len(items) == 240
    assert len({i["item_id"] for i in items}) == 240
    assert len({i["case_id"] for i in items}) == 30
    assert len({o.wire(o.request_body(i)) for i in items}) == 120
    assert [i["repetition"] for i in items] == [1] * 120 + [2] * 120
    assert Counter(i["category"] for i in items) == dict.fromkeys(o.CATEGORIES, 40)
    for i in items:
        assert i["semantic_map"][literal_answer(i["prompt"])] == i["expected_private"]


def test_position_preserves_named_people_and_name_swap_preserves_facts():
    for case, assignment in product(o.cases(), (0, 1)):
        p0, m0 = o.render(case, assignment, 0)
        p1, m1 = o.render(case, assignment, 1)
        def histories(prompt):
            return sorted(line for line in prompt.splitlines() if " chose " in line)
        assert histories(p0) == histories(p1)
        assert m0["A"] == m1["B"] and m0["B"] == m1["A"]
        swapped, _ = o.render(case, 1 - assignment, 0)
        renamed = p0.replace("Sam", "__FIRST__").replace("Priya", "Sam").replace("__FIRST__", "Priya")
        assert swapped == renamed


def test_fresh_bounds_and_constructed_cases_do_not_import_social_scenarios():
    assert len({tuple(c["bounds"].items()) for c in o.cases()}) == 30
    for case in o.cases():
        assert all(den >= 40 and 0 <= lo < hi for lo, hi, den in case["bounds"].values())
    forbidden = ("faucet", "spreadsheet", "couch", "Spanish", "dog", "presentation", "boxes")
    assert all(word not in i["prompt"] for i in o.generate_items() for word in forbidden)


def test_requests_have_no_keys_or_repetitions_and_preserve_schema_order():
    for item in o.generate_items():
        body = o.request_body(item)
        assert body["messages"] == [{"role": "user", "content": item["prompt"]}]
        for private in ("expected_private", "semantic_map", item["item_id"], item["case_id"]):
            assert private not in o.wire(body)
        schema = body["output_config"]["format"]["schema"]
        assert list(schema["properties"]) == ["brief_basis", "answer"]
        assert list(json.loads(o.wire(body))["output_config"]["format"]["schema"]["properties"]) == ["brief_basis", "answer"]
    a = {"x": 1, "y": 2}
    b = {"y": 2, "x": 1}
    assert o.stream_hash([a]) != o.stream_hash([b])


def test_oracle_pass_and_all_denominators():
    s = o.summarize(o.generate_items(), records())
    assert s["gate"] == "PASS" and not s["pilot_authorized"]
    for d in s["categories"].values():
        assert d["correct"] == 40 and d["joint_correct"] == 20
        assert d["joint_by_pass"] == {"1": 10, "2": 10}
        assert d["base_cases_all_eight_correct"] == 5
        for factor in ("position", "name", "repeat"):
            assert d[factor] == {"scheduled_pairs": 20, "comparable_pairs": 20, "disagreements": 0}


@pytest.mark.parametrize("letter", ["A", "B", "C", "D"])
def test_constant_letters_fail(letter):
    assert o.summarize(o.generate_items(), records(lambda _: letter))["gate"] == "FAIL"


@pytest.mark.parametrize("semantic", ["P", "Q"])
def test_single_person_on_every_dimension_fails(semantic):
    rows = records(lambda i: next(k for k, v in i["semantic_map"].items() if v == semantic))
    assert o.summarize(o.generate_items(), rows)["gate"] == "FAIL"


def test_always_sam_detected_as_name_not_position_dependence():
    rows = records(lambda i: next(k for k, v in re.findall(r"^\(([AB])\) (\w+)$", i["prompt"], re.MULTILINE)
                                  if v == "Sam"))
    d = o.summarize(o.generate_items(), rows)["categories"]["discriminating"]
    assert d["position"]["disagreements"] == 0
    assert d["name"]["disagreements"] == 20


def test_per_category_per_pass_gate_does_not_require_perfection():
    rows = records()
    items = o.generate_items()
    for cat in o.CATEGORIES:
        for rep in (1, 2):
            idx = next(k for k, i in enumerate(items) if i["category"] == cat and i["repetition"] == rep)
            rows[idx]["api_response"]["content"][0]["text"] = '{"brief_basis":"test","answer":"Z"}'
    summary = o.summarize(items, rows)
    assert summary["gate"] == "PASS"
    assert all(d["joint_by_pass"] == {"1": 9, "2": 9} for d in summary["categories"].values())
    used = {items[k]["case_id"] for k in range(len(items))
            if '"Z"' in rows[k]["api_response"]["content"][0]["text"] and items[k]["category"] == "ability_conflict"}
    idx = next(k for k, i in enumerate(items) if i["category"] == "ability_conflict"
               and i["repetition"] == 1 and i["case_id"] not in used)
    rows[idx]["api_response"]["content"][0]["text"] = '{"brief_basis":"test","answer":"Z"}'
    assert o.summarize(items, rows)["gate"] == "FAIL"


def test_appropriate_D_is_not_counted_as_error_abstention():
    s = o.summarize(o.generate_items(), records())
    assert s["categories"]["underdetermined"]["D"] == 40
    assert s["D_on_determined"] == {"count": 0, "denominator": 200}
    for item in o.generate_items():
        if item["category"] in ("both_give", "both_keep", "ability_equal"):
            assert literal_answer(item["prompt"]) == "C"


@pytest.mark.parametrize("text", [
    '{"answer":"A","brief_basis":"test"}', '{"brief_basis":"","answer":"A"}',
    '{"brief_basis":"test","answer":"a"}', '{"brief_basis":"test","answer":3}',
    '{"brief_basis":"test","answer":"A","answer":"B"}',
    '{"brief_basis":"test","answer":"A","extra":0}', 'not JSON',
])
def test_strict_decoder(text):
    api = {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}
    assert o.decode(o.generate_items()[0], api)["answer"] is None


def test_truncation_not_repaired_from_correct_explanation():
    row = records()[0]
    row["api_response"]["stop_reason"] = "max_tokens"
    assert o.decode(o.generate_items()[0], row["api_response"])["answer"] is None


@pytest.mark.parametrize("change", ["order", "id", "message", "request_id", "model", "schema_order", "amount"])
def test_integrity_rejects_corruption(change):
    rows = records()
    if change == "order":
        rows[0], rows[1] = rows[1], rows[0]
    elif change == "id":
        rows[0]["item_id"] = rows[1]["item_id"]
    elif change == "message":
        rows[0]["api_response"]["id"] = rows[1]["api_response"]["id"]
    elif change == "request_id":
        rows[0]["request_id"] = rows[1]["request_id"]
    elif change == "model":
        rows[0]["api_response"]["model"] = "different-model"
    elif change == "schema_order":
        p = rows[0]["request_body"]["output_config"]["format"]["schema"]["properties"]
        rows[0]["request_body"]["output_config"]["format"]["schema"]["properties"] = dict(reversed(list(p.items())))
    else:
        rows[0]["request_body"]["messages"][0]["content"] += " changed"
    with pytest.raises(ValueError):
        o.summarize(o.generate_items(), rows)


def test_missing_outputs_keep_scheduled_denominator_and_fail_completion():
    s = o.summarize(o.generate_items(), records()[:12])
    assert s["gate"] == "INCOMPLETE" and s["recorded"] == 12
    assert sum(d["unusable_or_missing"] for d in s["categories"].values()) == 228
    assert all(d["position"]["scheduled_pairs"] == 20 for d in s["categories"].values())
    assert o.summarize(o.generate_items(), [])["gate"] == "INCOMPLETE"
    with pytest.raises(ValueError):
        o.summarize(o.generate_items()[:12], records()[:12])


def test_committed_freeze():
    assert o.verify_freeze()["n_requests"] == 240


def test_collector_with_programmed_fixture_and_no_recollect(tmp_path):
    rows = iter(records())
    def send(body):
        row = next(rows)
        assert o.wire(body) == o.wire(row["request_body"])
        return deepcopy(row["api_response"]), row["request_id"]
    o.collect(tmp_path, send)
    assert o.report(tmp_path)["gate"] == "PASS"
    assert json.loads((tmp_path / "collection-started.json").read_text())["data_origin"] == "programmed_test_fixture"
    assert (tmp_path / "answer-audit.csv").exists()
    with pytest.raises(FileExistsError):
        o.collect(tmp_path, send)
    with pytest.raises(FileExistsError):
        o.export(tmp_path)


def test_transport_error_stops_without_retry_and_records_attempt(tmp_path):
    count = 0
    def fail(_):
        nonlocal count
        count += 1
        raise TimeoutError("not saved: possible private detail")
    with pytest.raises(TimeoutError):
        o.collect(tmp_path, fail)
    assert count == 1
    assert "private detail" not in (tmp_path / "transport-stop.json").read_text()
    assert o.report(tmp_path)["gate"] == "INCOMPLETE"


def test_wrong_model_record_is_preserved_before_stop(tmp_path):
    row = records()[0]
    row["api_response"]["model"] = "wrong"
    with pytest.raises(ValueError, match="model"):
        o.collect(tmp_path, lambda _: (row["api_response"], row["request_id"]))
    assert len((tmp_path / "responses.jsonl").read_text().splitlines()) == 1


def test_D_cap_counts_answers_not_pairs():
    items, rows = o.generate_items(), records()
    selected = []
    for cat in o.CATEGORIES:
        if cat == "underdetermined":
            continue
        for rep in (1, 2):
            idx = next(k for k, i in enumerate(items) if i["category"] == cat and i["repetition"] == rep)
            selected.append(idx)
            rows[idx]["api_response"]["content"][0]["text"] = '{"brief_basis":"test","answer":"D"}'
    assert o.summarize(items, rows)["gate"] == "PASS"
    first = items[selected[0]]
    other = next(k for k, i in enumerate(items) if i["case_id"] == first["case_id"]
                 and i["name_assignment"] == first["name_assignment"]
                 and i["repetition"] == first["repetition"] and i["position"] != first["position"])
    rows[other]["api_response"]["content"][0]["text"] = '{"brief_basis":"test","answer":"D"}'
    s = o.summarize(items, rows)
    assert all(d["pass_gate"] for d in s["categories"].values())
    assert s["D_on_determined"]["count"] == 11 and s["gate"] == "FAIL"


def test_source_tampering_breaks_freeze(tmp_path, monkeypatch):
    frozen = o.manifest()
    for rel in o.SOURCE_FILES:
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((o.ROOT / rel).read_bytes())
    dest = tmp_path / o.FREEZE
    dest.parent.mkdir(parents=True, exist_ok=True)
    o.write_json(dest, frozen)
    monkeypatch.setattr(o, "ROOT", tmp_path)
    assert o.verify_freeze() == frozen
    with (tmp_path / o.PLAN).open("a") as fh:
        fh.write("changed after freeze")
    with pytest.raises(ValueError, match="Freeze mismatch"):
        o.verify_freeze()


def test_unusable_answers_do_not_stop_or_trigger_retries(tmp_path):
    rows = iter(records(lambda _: "Z"))
    calls = 0
    def send(_):
        nonlocal calls
        calls += 1
        row = next(rows)
        return row["api_response"], row["request_id"]
    o.collect(tmp_path, send)
    assert calls == 240 and o.report(tmp_path)["gate"] == "FAIL"
