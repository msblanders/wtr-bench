"""Offline independent truth, parsing, threshold and pair audit (stdlib only).

Run from any directory: python results/diagnostics/36111049496/audit/verify.py
No API calls, outcome repair or automatic explanation-quality classifier.
Manual assistant labels are checked for binding/completeness and counted only.
"""

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_lines(name):
    return [json.loads(line) for line in (ROOT / name).read_text().splitlines()]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def counts(rows):
    return {
        "planned": len(rows),
        "usable": sum(r["choice"] is not None for r in rows),
        "correct": sum(r["correct"] is True for r in rows),
        "incorrect_usable": sum(r["correct"] is False for r in rows),
        "unusable": sum(r["choice"] is None for r in rows),
    }


def strict_object(pairs):
    assert len({k for k, _ in pairs}) == len(pairs), "Duplicate JSON key"
    return dict(pairs)


def prompt_truth(prompt):
    options = re.findall(r"\(([AB])\) (Sam|You) receives? (\d+) points\.", prompt)
    assert len(options) == 2 and {p for _, p, _ in options} == {"Sam", "You"}
    own_letter, own_amount = next((k, int(n)) for k, p, n in options if p == "Sam")
    other_amount = next(int(n) for _, p, n in options if p == "You")
    explicit = re.search(r"Sam's points plus ([0-9.]+) times your points", prompt)
    if explicit:
        lo = hi = Fraction(explicit[1])
    else:
        history = re.findall(
            r"The choice was (\d+) points for Sam or (\d+) points for you; "
            r"Sam chose the (\d+) points for (Sam|you)\.", prompt
        )
        assert len(history) == 2
        bounds = {}
        for own, other, selected, recipient in history:
            assert int(selected) == int(own if recipient == "Sam" else other)
            bounds[recipient] = Fraction(int(own), int(other))
        lo, hi = bounds["you"], bounds["Sam"]
        assert 0 <= lo < hi
    ratio = Fraction(own_amount, other_amount)
    assert ratio < lo or ratio > hi, "Choice must be identified for all compatible weights"
    keep = ratio > hi
    answer = own_letter if keep else ("B" if own_letter == "A" else "A")
    return answer, own_letter, own_amount, other_amount, ratio, lo, hi


def threshold_fit(group):
    observed = [r for r in group if r["choice"] is not None]
    rungs = sorted({r["ratio"] for r in observed})
    assert rungs
    # Enumerate each partition of observed rungs into give (below) / keep (above).
    losses = [sum(r["keep"] != (rungs.index(r["ratio"]) >= cut) for r in observed)
              for cut in range(len(rungs) + 1)]
    best = [cut for cut, loss in enumerate(losses) if loss == min(losses)]
    low = rungs[min(best) - 1] if min(best) else None
    high = rungs[max(best)] if max(best) < len(rungs) else None
    identified = len(best) == 1
    interior = identified and low is not None and high is not None
    return {
        "identified": identified,
        "estimate": math.sqrt(float(low * high)) if interior else None,
        "lower": float(low) if low is not None else None,
        "upper": float(high) if high is not None else None,
        "censored": ("left" if low is None else "right" if high is None else "none")
                    if identified else "none",
        "violations": min(losses),
        "n": len(observed),
        "n_missing": len(group) - len(observed),
    }


def main():
    checksums = (ROOT / "SHA256SUMS").read_text().splitlines()
    assert len(checksums) == 16
    for line in checksums:
        expected, name = line.split("  ", 1)
        assert digest((ROOT / name).read_bytes()) == expected, name
    freeze = json.loads((ROOT / "freeze.json").read_text())
    assert digest((ROOT / "items.jsonl").read_bytes()) == freeze["items_jsonl_sha256"]
    assert digest((ROOT / "analysis-plan.md").read_bytes()) == freeze["config"]["analysis_plan_sha256"]
    items, responses = read_lines("items.jsonl"), read_lines("responses.jsonl")
    assert len(items) == len(responses) == 216
    assert len({i["item_id"] for i in items}) == 216
    assert len({r["request_id"] for r in responses}) == 216
    assert len({r["api_response"]["id"] for r in responses}) == 216
    requests = "".join(json.dumps(r["request_body"]) + "\n" for r in responses)
    assert digest(requests.encode()) == freeze["request_bodies_jsonl_sha256"]
    records = []
    fit_groups, pair_groups = defaultdict(list), defaultdict(list)
    for i, response in zip(items, responses, strict=True):
        assert i["item_id"] == response["item_id"]
        body = response["request_body"]
        assert body["messages"] == [{"role": "user", "content": i["prompt"]}]
        truth, own_letter, own, other, ratio, lo, hi = prompt_truth(i["prompt"])
        assert truth == i["expected_answer"]
        assert (own, other, own_letter == "A") == (i["own_amount"], i["other_amount"], i["sam_first"])
        if i["arm"] == "choice_history":
            assert (lo, hi) == tuple(map(Fraction, i["history_interval_private_audit"]))
        else:
            assert lo == hi == Fraction(i["weight_private_audit"])
        api = response["api_response"]
        assert api["model"] == body["model"] == "claude-sonnet-4-5-20250929"
        raw = "".join(b["text"] for b in api["content"] if b["type"] == "text")
        assert raw == response["raw"]
        choice = basis = None
        if (api["stop_reason"] == "end_turn" and len(api["content"]) == 1
                and api["content"][0]["type"] == "text"):
            obj = json.loads(raw, object_pairs_hook=strict_object)
            assert list(obj) == ["brief_basis", "answer"]
            assert isinstance(obj["brief_basis"], str) and obj["brief_basis"].strip()
            assert isinstance(obj["answer"], str) and obj["answer"].upper() in ("A", "B")
            choice, basis = obj["answer"].upper(), obj["brief_basis"]
        assert (choice, basis) == (response["choice"], response["brief_basis"])
        correct = None if choice is None else choice == truth
        keep = None if choice is None else choice == own_letter
        assert (correct, keep) == (response["correct"], response["keyed"])
        r = {**i, "choice": choice, "correct": correct, "keep": keep, "ratio": ratio}
        records.append(r)
        for order in ("pooled", "sam_first" if i["sam_first"] else "sam_second"):
            fit_groups[i["arm"], i["profile"], i["history_swapped"], i["repetition"], order].append(r)
        pair_groups["option_order", i["arm"], i["profile"], i["history_swapped"], i["repetition"], own].append(r)
        pair_groups["repeat", i["template_id"]].append(r)
        if i["arm"] == "choice_history":
            pair_groups["history_order", i["profile"], i["repetition"], own, own_letter].append(r)
    fits = read_lines("responses.fits.jsonl")
    assert len(fit_groups) == len(fits) == 54
    failure_types = Counter()
    recovered_by_arm = Counter()
    for f in fits:
        key = tuple(f[k] for k in ("arm", "profile", "history_swapped", "repetition", "option_order"))
        group = fit_groups[key]
        fit = threshold_fit(group)
        for k, value in fit.items():
            if k == "estimate" and value is not None:
                assert math.isclose(value, f["fit"][k], abs_tol=1e-14)
            else:
                assert value == f["fit"][k], (key, k)
        weight = float(group[0]["weight_private_audit"])
        recovered = (fit["n_missing"] == fit["violations"] == 0
                     and fit["estimate"] is not None and fit["lower"] < weight < fit["upper"])
        assert recovered == f["recovered_interval"]
        recovered_by_arm[f["arm"]] += recovered
        if not recovered:
            failure_types["missing" if fit["n_missing"] else
                          "tied_fit" if not fit["identified"] else
                          "violations" if fit["violations"] else
                          "censored" if fit["censored"] != "none" else "wrong_interval"] += 1
    original_pairs = {(r["comparison"], frozenset(r["item_ids"])): r
                      for r in read_lines("responses.pairs.jsonl")}
    assert len(original_pairs) == len(pair_groups) == 288
    pair_counts = defaultdict(Counter)
    for key, group in pair_groups.items():
        assert len(group) == 2
        if key[0] == "repeat":
            assert group[0]["prompt"] == group[1]["prompt"]
        original = original_pairs[key[0], frozenset(r["item_id"] for r in group)]
        complete = all(r["keep"] is not None for r in group)
        disagree = group[0]["keep"] != group[1]["keep"] if complete else None
        assert (complete, disagree) == (original["complete"], original["disagree"])
        for name in (key[0], group[0]["arm"] + "/" + key[0]):
            pair_counts[name].update(planned=1, complete=int(complete), disagree=int(disagree is True))
    labels = read_lines("audit/explanation-labels.jsonl")
    packet = {r["item_id"]: r for r in read_lines("responses.explanation-review-template.jsonl")}
    assert len(labels) == len({r["item_id"] for r in labels}) == 216
    label_counts = defaultdict(Counter)
    for i, response, label in zip(items, responses, labels, strict=True):
        assert label["item_id"] == i["item_id"]
        p = packet[i["item_id"]]
        assert label["review_id"] == p["review_id"]
        assert label["response_digest"] == p["response_digest"] == digest(
            json.dumps({"item": i, "response": response}, sort_keys=True).encode())
        assert label["notes"].strip() and label["reviewer"] == "assistant"
        assert (label["label"] == "unusable_or_missing") == (response["choice"] is None)
        label_counts[i["arm"]].update([label["label"]])
        label_counts["final_correct_" + str(response["correct"])].update([label["label"]])
    summary = {
        "checks": "All 16 original hashes; 216 literal-prompt truth keys, strict responses and bound review labels; 54 threshold fits; 288 comparison pairs verified.",
        "collection": counts(records),
        "by_arm_profile": {arm + "/" + profile: counts([r for r in records if r["arm"] == arm and r["profile"] == profile])
                           for arm in ("explicit_weight", "choice_history") for profile in ("low", "middle", "high")},
        "history_by_option_order": {str(first): counts([r for r in records if r["arm"] == "choice_history" and r["sam_first"] == first]) for first in (True, False)},
        "history_by_pass": {str(p): counts([r for r in records if r["arm"] == "choice_history" and r["repetition"] == p]) for p in (1, 2)},
        "recovered_by_arm": dict(recovered_by_arm),
        "nonrecovered_fit_types_mutually_exclusive": dict(failure_types),
        "comparisons": {k: dict(v) for k, v in sorted(pair_counts.items())},
        "assistant_explanation_labels": {k: dict(v) for k, v in sorted(label_counts.items())},
        "interpretation": "Observed fixed diagnostic only; overlapping fits and repeated templates are not independent samples. Labels are unblinded assistant judgments, not inferred internal reasoning. No pilot release.",
    }
    out = ROOT / "audit/independent-summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
