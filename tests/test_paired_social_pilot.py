"""Offline programmed fixtures for the social pilot; these are not model data."""
import csv
import gzip
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import product

import pytest

from wtrbench.inference import TASKS, Task
from wtrbench.paired import natural as n
from wtrbench.paired import social as s


@pytest.fixture(scope="module")
def items():
    return s.generate_items()


def api(answer="C", mid="msg_0"):
    return {"id": mid, "model": n.MODEL, "stop_reason": "end_turn",
            "content": [{"type": "text", "text": json.dumps({
                "brief_basis": "Programmed software fixture, not a model judgment.",
                "answer": answer})}]}


def rows_for(items, choose):
    return [{"item_id": item["item_id"], "request_body": n.request_body(item),
             "api_response": api(choose(item), f"msg_{k}"), "request_id": f"req_{k}"}
            for k, item in enumerate(items)]


def semantic_letter(item, semantic):
    return next(letter for letter, value in item["semantic_map"].items() if value == semantic)


def predicted(item):
    return semantic_letter(item, {"valuation": "unable", "ability_same": "unwilling",
                                  "ability_different": "insufficient"}[item["probe"]])


def fake_sender(choose=lambda item: "C"):
    items = s.generate_items()
    calls = []

    def send(body):
        k = len(calls)
        assert body == n.request_body(items[k])
        calls.append(body)
        return api(choose(items[k]), f"msg_{k}"), f"req_{k}"

    return send, calls


def test_schedule_scenarios_and_repeat_identity(items):
    expected = ("couch", "faucet", "spreadsheet", "translate", "dog", "presentation")
    assert tuple(x["scenario"] for x in s.scenarios()) == expected
    for scenario in s.scenarios():
        baseline = TASKS[Task(scenario["scenario"])].model_dump()
        assert {k: v for k, v in scenario.items() if k != "scenario"} == {
            k: baseline[k] for k in ("help", "unwilling", "unable", "outcome_fail",
                                     "same_ask", "diff_ask")}
    assert len(items) == len({i["item_id"] for i in items}) == 144
    assert set(Counter(i["prompt"] for i in items).values()) == {2}
    assert len({i["prompt"] for i in items}) == 72
    assert Counter((i["scenario"], i["probe"]) for i in items) == {
        (scenario, probe): 8 for scenario, probe in product(expected, s.PROBES)}
    assert [i["repetition"] for i in items] == [1] * 72 + [2] * 72
    assert items == s.generate_items()
    p1, p2 = ([i["prompt"] for i in items if i["repetition"] == rep] for rep in (1, 2))
    assert sorted(p1) == sorted(p2) and p1 != p2
    groups = defaultdict(list)
    for item in items:
        groups[(item["scenario"], item["probe"], item["name_assignment"], item["position"])].append(item)
    for a, b in groups.values():
        assert n.request_body(a) == n.request_body(b)
        assert {k: v for k, v in a.items() if k not in ("item_id", "repetition")} == {
            k: v for k, v in b.items() if k not in ("item_id", "repetition")}


def test_literal_person_identity_and_identical_evidence(items):
    # Decode person identity from displayed refusal, independently of semantic_map.
    # This catches a renderer that swaps names but forgets to swap the answer map.
    evidence_groups = defaultdict(set)
    for item in items:
        prompt = item["prompt"]
        unwilling = re.findall(r"(Sam|Priya) was free that day and could easily have done it, but said no\.", prompt)
        assert len(unwilling) == 1
        unable = ({"Sam", "Priya"} - set(unwilling)).pop()
        assert unable == ("Priya" if item["name_assignment"] else "Sam")
        displayed = dict(re.findall(r"^\(([AB])\) (Sam|Priya)$", prompt, re.MULTILINE))
        assert item["semantic_map"] == {
            **{letter: "unable" if name == unable else "unwilling" for letter, name in displayed.items()},
            "C": "equal", "D": "insufficient"}
        assert displayed["A"] == (unwilling[0] if item["position"] else unable)
        accounts = re.findall(r"^(Sam|Priya) is an acquaintance\.", prompt, re.MULTILINE)
        assert accounts == [displayed["A"], displayed["B"]]
        assert prompt.count(s.CONTEXT) == prompt.count(s.PERSISTENCE) == 1
        rendered_evidence = prompt.split("\n\n")[1]
        assert rendered_evidence == "\n".join(item["evidence"])
        evidence_groups[(item["scenario"], item["name_assignment"], item["position"],
                         item["repetition"])].add(rendered_evidence)
        scenario = next(x for x in s.scenarios() if x["scenario"] == item["scenario"])
        assert prompt.count(scenario["outcome_fail"]) == 2
        if item["probe"] == "valuation":
            assert "keep 5 points" in prompt and "give you 10 points" in prompt
        else:
            task = scenario["same_ask" if item["probe"] == "ability_same" else "diff_ask"]
            assert f"makes a real effort to {task} for you, with enough time to do it" in prompt
        assert "without exception" not in prompt and "equal chances" not in prompt
    assert all(len(evidence) == 1 for evidence in evidence_groups.values())


def test_shared_request_protocol_and_absence_of_answer_keys(items):
    for item in items:
        body = n.request_body(item)
        assert body["model"] == "claude-sonnet-4-5-20250929"
        assert body["temperature"] == 0 and body["max_tokens"] == 256
        assert body["messages"] == [{"role": "user", "content": item["prompt"]}]
        assert item["expected_private"] is None and item["exploratory_expected_private"] is None
        assert n.decode(item, api())["correct"] is None
        assert n.decode(item, api())["as_expected"] is None
        for private in ("semantic_map", "expected_private", "repetition", "item_id", "name_assignment"):
            assert private not in json.dumps(body)


@pytest.mark.parametrize("direction", [1, -1])
def test_predicted_and_reverse_crossover_are_descriptive(items, direction):
    def choose(item):
        answer = predicted(item)
        if direction < 0 and answer in ("A", "B"):
            return "B" if answer == "A" else "A"
        return answer
    report = s.summarize(items, rows_for(items, choose))
    assert report["completion"] == "COMPLETE" and report["scientific_pass_fail"] is None
    assert report["scenarios_with_both_net_directions"] == (6 if direction > 0 else 0)
    for cell in report["cells"]:
        assert sum(cell["counts"].values()) == 8
        assert all(sum(counts.values()) == 4 for counts in cell["by_pass"].values())
    for cross in report["crossovers"]:
        key = "predicted_crossover" if direction > 0 else "reverse_crossover"
        assert cross["counts"][key] == 8
        assert (cross["valuation_net"], cross["same_ability_net"], cross["net_difference"]) == (
            direction, -direction, 2 * direction)
    assert all(x["comparable_pairs"] == 72 and x["disagreements"] == 0
               for x in report["presentation_sensitivity"].values())


@pytest.mark.parametrize("strategy", ["A", "B", "Sam", "Priya", "unable", "unwilling", "C", "D"])
def test_constant_letter_name_person_and_nonordering_strategies(items, strategy):
    def choose(item):
        if strategy in ("A", "B", "C", "D"):
            return strategy
        if strategy in ("unable", "unwilling"):
            return semantic_letter(item, strategy)
        return next(letter for letter, name in re.findall(r"^\(([AB])\) (Sam|Priya)$", item["prompt"], re.MULTILINE)
                    if name == strategy)
    report = s.summarize(items, rows_for(items, choose))
    assert report["scenarios_with_both_net_directions"] == 0
    audit = report["presentation_sensitivity"]
    assert audit["position"]["disagreements"] == (72 if strategy in ("A", "B") else 0)
    assert audit["name"]["disagreements"] == (72 if strategy in ("Sam", "Priya") else 0)
    assert audit["repeat"]["disagreements"] == 0
    for cross in report["crossovers"]:
        key = "includes_equal_or_insufficient" if strategy in ("C", "D") else "same_person_on_both"
        assert cross["counts"][key] == 8
        assert cross["net_difference"] == 0


def test_positive_net_difference_alone_is_not_crossover(items):
    rows = rows_for(items, lambda item: semantic_letter(item, "unable") if item["probe"] == "valuation" else "C")
    report = s.summarize(items, rows)
    assert report["scenarios_with_both_net_directions"] == 0
    assert all(c["net_difference"] == 1 and not c["both_net_directions_as_predicted"]
               for c in report["crossovers"])


def test_c_d_invalid_missing_and_scheduled_pair_denominators(items):
    rows = rows_for(items[:4], lambda item: "C")
    rows[1]["api_response"] = api("D", "msg_1")
    rows[2]["api_response"]["stop_reason"] = "max_tokens"
    rows[3]["api_response"]["content"][0]["text"] = '{"brief_basis":"Choose A."}'
    report = s.summarize(items, rows)
    assert report["completion"] == "INCOMPLETE"
    assert report["counts"] == {"unable": 0, "unwilling": 0, "equal": 1,
                                "insufficient": 1, "invalid": 2, "missing": 140}
    assert all(sum(counts.values()) == 48 for counts in report["by_probe"].values())
    pairs = s.pair_audit(s.observations(items, rows))
    assert len(pairs) == 216
    for factor, summary in report["presentation_sensitivity"].items():
        group = [p for p in pairs if p["factor"] == factor]
        assert summary["scheduled_pairs"] == 72
        assert summary["comparable_pairs"] == sum(p["comparable"] for p in group)
        assert all(p["disagreement"] is None for p in group if not p["comparable"])
        assert all(p["scheduled_pairs"] == 24 for p in summary["by_probe"].values())
    empty = s.summarize(items, [])
    assert empty["counts"]["missing"] == 144
    assert all(x["comparable_pairs"] == 0 for x in empty["presentation_sensitivity"].values())


@pytest.mark.parametrize("text", [
    '{"answer":"A","brief_basis":"x"}',
    '{"brief_basis":"x","answer":"A","extra":0}',
    '{"brief_basis":"x","answer":"A","answer":"B"}',
    '{"brief_basis":" ","answer":"A"}',
    '{"brief_basis":"A is more likely","answer":"a"}',
    'A',
])
def test_strict_decoder_never_repairs_explanation(items, text):
    rows = rows_for(items[:1], lambda item: "A")
    rows[0]["api_response"]["content"][0]["text"] = text
    assert s.observations(items, rows)[0]["semantic"] == "invalid"


@pytest.mark.parametrize("damage", ["item", "body", "model", "message", "request", "reorder", "duplicate"])
def test_integrity_rejects_corrupt_records(items, damage):
    rows = rows_for(items[:3], lambda item: "C")
    if damage == "item":
        rows[1]["item_id"] = "unknown"
    elif damage == "body":
        rows[1]["request_body"]["messages"][0]["content"] += " altered"
    elif damage == "model":
        rows[1]["api_response"]["model"] = "other-model"
    elif damage == "message":
        rows[1]["api_response"]["id"] = rows[0]["api_response"]["id"]
    elif damage == "request":
        rows[1]["request_id"] = rows[0]["request_id"]
    elif damage == "reorder":
        rows.reverse()
    else:
        rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError):
        s.summarize(items, rows)
    altered_items = deepcopy(items)
    altered_items[0]["semantic_map"]["A"] = "equal"
    with pytest.raises(ValueError):
        s.summarize(altered_items, [])


def test_export_freeze_and_snapshot_reproduce_offline(tmp_path, items):
    frozen = s.verify_freeze()
    assert frozen == s.manifest()
    assert set(frozen["source_sha256"]) == set(s.SOURCE_FILES)
    assert s.export(tmp_path) == items
    assert not (tmp_path / "responses.jsonl").exists()
    expected_stream = "".join(n.wire(i) + "\n" for i in items)
    assert gzip.decompress((s.ROOT / s.PACKED).read_bytes()).decode() == expected_stream
    assert (tmp_path / "items.jsonl").read_text() == expected_stream
    assert json.loads((tmp_path / "freeze.json").read_text()) == frozen
    snapshot = tmp_path / "frozen-source"
    assert json.loads((snapshot / s.FREEZE).read_text()) == frozen
    env = {**os.environ, "PYTHONPATH": str(snapshot / "src")}
    result = subprocess.run([sys.executable, "-m", "wtrbench.paired.social", "check"],
                            cwd=snapshot, env=env, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == frozen
    (snapshot / s.SCENARIOS).write_text("[]")
    changed = subprocess.run([sys.executable, "-m", "wtrbench.paired.social", "check"],
                             cwd=snapshot, env=env, text=True, capture_output=True, check=False)
    assert changed.returncode != 0 and "freeze mismatch" in changed.stderr


def test_collection_reports_and_snapshot_report_reproduce(tmp_path):
    send, calls = fake_sender(predicted)
    s.collect(tmp_path, send)
    assert len(calls) == 144
    cfg = json.loads((tmp_path / "collection-started.json").read_text())
    assert cfg["data_origin"] == "programmed_test_fixture" and cfg["max_retries"] == 0
    result = json.loads((tmp_path / "report.json").read_text())
    assert result["scenarios_with_both_net_directions"] == 6
    before = {name: (tmp_path / name).read_bytes() for name in (
        "report.json", "report.md", "answer-audit.csv", "pair-audit.json")}
    snapshot = tmp_path / "frozen-source"
    subprocess.run([sys.executable, "-m", "wtrbench.paired.social", "report", "--out", str(tmp_path)],
                   cwd=snapshot, env={**os.environ, "PYTHONPATH": str(snapshot / "src")},
                   text=True, capture_output=True, check=True)
    assert before == {name: (tmp_path / name).read_bytes() for name in before}
    with (tmp_path / "answer-audit.csv").open() as fh:
        assert len(list(csv.DictReader(fh))) == 144
    for operation in (lambda: s.export(tmp_path), lambda: s.collect(tmp_path, send)):
        with pytest.raises(FileExistsError):
            operation()
    assert len(calls) == 144


@pytest.mark.parametrize("failure_at", [0, 2])
def test_transport_failure_stops_without_retry_and_reports_partial(tmp_path, failure_at):
    calls = []

    def send(body):
        k = len(calls)
        calls.append(body)
        if k == failure_at:
            raise TimeoutError("offline fixture")
        return api("C", f"msg_{k}"), f"req_{k}"

    with pytest.raises(TimeoutError):
        s.collect(tmp_path, send)
    assert len(calls) == failure_at + 1
    stop = json.loads((tmp_path / "transport-stop.json").read_text())
    assert stop["attempted_body"] == calls[-1]
    assert stop["item_id"] == s.generate_items()[failure_at]["item_id"]
    report = s.report(tmp_path)
    assert report["recorded"] == failure_at and report["counts"]["missing"] == 144 - failure_at
    with pytest.raises(FileExistsError):
        s.collect(tmp_path, send)


def test_integrity_stop_preserves_raw_response_before_raising(tmp_path):
    calls = []

    def send(body):
        calls.append(body)
        response = api()
        response["model"] = "unexpected-model"
        return response, "req_bad"

    with pytest.raises(ValueError, match="model mismatch"):
        s.collect(tmp_path, send)
    assert len(calls) == 1
    raw = json.loads((tmp_path / "responses.jsonl").read_text())
    assert raw["api_response"]["model"] == "unexpected-model"
    assert (tmp_path / "integrity-stop.json").exists()
    with pytest.raises(ValueError):
        s.report(tmp_path)
    assert not (tmp_path / "report.json").exists()


def test_invalid_answers_do_not_trigger_extra_calls(tmp_path):
    send, calls = fake_sender(lambda item: "lowercase-invalid")
    s.collect(tmp_path, send)
    report = s.report(tmp_path)
    assert len(calls) == 144 and report["counts"]["invalid"] == 144
    assert report["completion"] == "COMPLETE" and report["scientific_pass_fail"] is None


@pytest.mark.parametrize("target", ["items.jsonl", "requests.jsonl", "freeze.json", "collection-started.json"])
def test_report_rejects_altered_artifacts(tmp_path, target):
    # A zero-response stopped run is enough to exercise report provenance checks.
    def stopped(body):
        raise TimeoutError("fixture")
    with pytest.raises(TimeoutError):
        s.collect(tmp_path, stopped)
    path = tmp_path / target
    if target.endswith(".jsonl"):
        path.write_text(path.read_text() + "\n")
    else:
        value = json.loads(path.read_text())
        value["protocol"] = "altered"
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        s.report(tmp_path)


@pytest.mark.parametrize("confirmation,attempt", [(None, "1"), (143, "1"), (144, "2")])
def test_cli_requires_exact_confirmation_and_first_attempt(monkeypatch, confirmation, attempt):
    args = ["social", "run"] + ([] if confirmation is None else ["--confirm", str(confirmation)])
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", attempt)
    monkeypatch.setattr(s, "collect", lambda *a, **k: pytest.fail("collection must not start"))
    with pytest.raises(SystemExit):
        s.main()
