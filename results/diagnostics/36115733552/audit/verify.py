"""Offline audit of literal payoffs, paired outcomes, fits and manual-label binding.

Uses the archived recovery audit's independent threshold enumerator, never the
production scorer. No API calls, repairs, or automatic explanation classifier.
"""

import hashlib
import json
import math
import re
import runpy
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIOR = ROOT.parent / "36111049496"
HELPERS = runpy.run_path(str(PRIOR / "audit/verify.py"))


def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def table_truth(prompt):
    history = re.findall(r"\| 1 \| (\d+) \| (\d+) \|\n\| 2 \| (\d+) \| (\d+) \|\n"
                         r"Sam chose outcome ([12])\.", prompt)
    assert len(history) == 2
    bounds = {}
    for own, zero_you, zero_sam, other, chosen in history:
        assert zero_you == zero_sam == "0"
        bounds[chosen] = Fraction(int(own), int(other))
    lo, hi = bounds["2"], bounds["1"]
    assert 0 <= lo < hi
    options = re.findall(r"\| ([AB]) \| (\d+) \| (\d+) \|", prompt)
    assert len(options) == 2 and [x[0] for x in options] == ["A", "B"]
    own_letter, own = next((letter, int(s)) for letter, s, y in options if int(s))
    other_letter, other = next((letter, int(y)) for letter, s, y in options if int(y))
    assert own_letter != other_letter
    assert all((int(s) == 0) != (int(y) == 0) for _, s, y in options)
    ratio = Fraction(own, other)
    assert ratio < lo or ratio > hi
    return (own_letter if ratio > hi else other_letter), own_letter, own, other, ratio, lo, hi


def counts(group):
    return {"n": len(group), "correct": sum(r["correct"] for r in group),
            "incorrect": sum(not r["correct"] for r in group)}


def main():
    manifest = (ROOT / "SHA256SUMS").read_text().splitlines()
    assert len(manifest) == 16
    for line in manifest:
        expected, name = line.split("  ", 1)
        assert sha((ROOT / name).read_bytes()) == expected, name
    freeze = json.loads((ROOT / "freeze.json").read_text())
    assert sha((ROOT / "items.jsonl").read_bytes()) == freeze["items_jsonl_sha256"]
    assert sha((ROOT / "analysis-plan.md").read_bytes()) == freeze["config"]["analysis_plan_sha256"]
    items, responses = lines(ROOT / "items.jsonl"), lines(ROOT / "responses.jsonl")
    assert len(items) == len(responses) == 288
    assert len({i["item_id"] for i in items}) == 288
    assert len({r["request_id"] for r in responses}) == 288
    assert len({r["api_response"]["id"] for r in responses}) == 288
    assert sha("".join(json.dumps(r["request_body"])+"\n" for r in responses).encode()) == freeze["request_bodies_jsonl_sha256"]
    records, by_id = [], {}
    fit_groups, pair_groups = defaultdict(list), defaultdict(list)
    for i, response in zip(items, responses, strict=True):
        assert i["item_id"] == response["item_id"]
        body, api = response["request_body"], response["api_response"]
        assert body["messages"] == [{"role": "user", "content": i["prompt"]}]
        assert api["model"] == body["model"] == "claude-sonnet-4-5-20250929"
        assert api["stop_reason"] == "end_turn" and len(api["content"]) == 1
        assert api["content"][0]["type"] == "text"
        raw = api["content"][0]["text"]
        assert raw == response["raw"]
        obj = json.loads(raw, object_pairs_hook=HELPERS["strict_object"])
        assert list(obj) == ["brief_basis", "answer"]
        assert isinstance(obj["brief_basis"], str) and obj["brief_basis"].strip()
        choice = obj["answer"].upper()
        assert choice in ("A", "B")
        assert (choice, obj["brief_basis"]) == (response["choice"], response["brief_basis"])
        truth = HELPERS["prompt_truth"] if i["presentation"] == "original" else table_truth
        expected, own_letter, own, other, ratio, lo, hi = truth(i["prompt"])
        assert (own, other, own_letter == "A") == (i["own_amount"], i["other_amount"], i["sam_first"])
        assert (lo, hi) == tuple(map(Fraction, i["history_interval_private_audit"]))
        assert expected == i["expected_answer"]
        correct, keep = choice == expected, choice == own_letter
        assert (correct, keep) == (response["correct"], response["keyed"])
        r = {**i, "choice": choice, "correct": correct, "keep": keep, "ratio": ratio}
        records.append(r)
        by_id[i["item_id"]] = (i, response)
        for order in ("pooled", "sam_first" if i["sam_first"] else "sam_second"):
            fit_groups[i["presentation"], i["profile"], i["history_swapped"], i["repetition"], order].append(r)
        pair_groups["presentation", i["source_item_id"]].append(r)
        pair_groups["option_order", i["presentation"], i["profile"], i["history_swapped"], i["repetition"], own].append(r)
        pair_groups["history_order", i["presentation"], i["profile"], i["repetition"], own, own_letter].append(r)
        pair_groups["repeat", i["template_id"]].append(r)
    fits = lines(ROOT / "responses.fits.jsonl")
    assert len(fits) == len(fit_groups) == 72
    fit_results, failures = {}, defaultdict(Counter)
    recovered_counts = defaultdict(Counter)
    for f in fits:
        key = tuple(f[k] for k in ("presentation", "profile", "history_swapped", "repetition", "option_order"))
        fit = HELPERS["threshold_fit"](fit_groups[key])
        for k, value in fit.items():
            assert (math.isclose(value, f["fit"][k], abs_tol=1e-14)
                    if k == "estimate" and value is not None else value == f["fit"][k]), (key, k)
        weight = float(fit_groups[key][0]["weight_private_audit"])
        recovered = (fit["violations"] == fit["n_missing"] == 0 and fit["estimate"] is not None
                     and fit["lower"] < weight < fit["upper"])
        assert recovered == f["recovered_interval"]
        assert key not in fit_results
        fit_results[key] = recovered
        recovered_counts[key[0]][key[1]] += recovered
        if not recovered:
            failures[key[0]]["tied_fit" if not fit["identified"] else
                             "violations" if fit["violations"] else
                             "censored" if fit["censored"] != "none" else "wrong_interval"] += 1
    original_pairs = {(r["comparison"], frozenset(r["item_ids"])): r for r in lines(ROOT / "responses.pairs.jsonl")}
    assert len(original_pairs) == len(pair_groups) == 576
    paired = Counter()
    comparisons = defaultdict(Counter)
    for key, group in pair_groups.items():
        assert len(group) == 2
        source = original_pairs[key[0], frozenset(r["item_id"] for r in group)]
        assert source["complete"]
        disagree = group[0]["keep"] != group[1]["keep"]
        assert disagree == source["disagree"]
        name = key[0] if key[0] == "presentation" else group[0]["presentation"]+"/"+key[0]
        comparisons[name].update(planned=1, complete=1, disagree=int(disagree))
        if key[0] == "repeat":
            assert by_id[group[0]["item_id"]][1]["request_body"] == by_id[group[1]["item_id"]][1]["request_body"]
        if key[0] == "presentation":
            group.sort(key=lambda r: r["presentation"] != "original")
            assert source["item_ids"] == [r["item_id"] for r in group]
            assert group[0]["expected_answer"] == group[1]["expected_answer"]
            paired[str(tuple(r["correct"] for r in group))] += 1
    labels = lines(ROOT / "audit/explanation-labels.jsonl")
    old_items = {r["item_id"]: r for r in lines(PRIOR / "items.jsonl")}
    old_rows = {r["item_id"]: r for r in lines(PRIOR / "responses.jsonl")}
    old_labels = {r["item_id"]: r for r in lines(PRIOR / "audit/explanation-labels.jsonl")}
    packet = {r["item_id"]: r for r in lines(ROOT / "responses.explanation-review-template.jsonl")}
    assert len(labels) == len({r["item_id"] for r in labels}) == 288
    labels_by_id = {r["item_id"]: r for r in labels}
    ratings, methods = defaultdict(Counter), Counter()
    for i, response, label in zip(items, responses, labels, strict=True):
        assert label["item_id"] == i["item_id"]
        p = packet[i["item_id"]]
        assert label["review_id"] == p["review_id"]
        assert label["response_digest"] == p["response_digest"] == sha(json.dumps({"item": i, "response": response}, sort_keys=True).encode())
        assert label["reviewer"] == "assistant" and label["notes"].strip()
        method = label["review_method"]
        assert method in ("fresh_assistant_review", "exact_prompt_raw_match_to_prior_assistant_review",
                          "exact_prompt_raw_duplicate_within_run")
        assert ("prior_item_id" in label) == (method == "exact_prompt_raw_match_to_prior_assistant_review")
        assert bool(label.get("duplicate_of_item_id")) == (method == "exact_prompt_raw_duplicate_within_run")
        methods.update([method])
        if "prior_item_id" in label:
            old = label["prior_item_id"]
            assert (i["prompt"], response["raw"]) == (old_items[old]["prompt"], old_rows[old]["raw"])
            assert label["label"] == old_labels[old]["label"]
            assert label["prior_review_id"] == old_labels[old]["review_id"]
            assert label["prior_response_digest"] == old_labels[old]["response_digest"] == sha(json.dumps({"item": old_items[old], "response": old_rows[old]}, sort_keys=True).encode())
        if label.get("duplicate_of_item_id"):
            prior_i, prior_r = by_id[label["duplicate_of_item_id"]]
            assert (i["prompt"], response["raw"]) == (prior_i["prompt"], prior_r["raw"])
            assert label["label"] == labels_by_id[prior_i["item_id"]]["label"]
        ratings[i["presentation"]].update([label["label"]])
        ratings[i["presentation"]+"/final_correct_"+str(response["correct"])].update([label["label"]])
    fit_pairs = Counter(str((passed, fit_results[("explicit_payoffs", *key[1:])]))
                        for key, passed in fit_results.items() if key[0] == "original")
    summary = {
        "checks": "All 16 original hashes, 288 literal-prompt truth keys and strict responses, 72 independently enumerated fits, 576 pairs and 288 response-bound labels verified.",
        "by_presentation_profile": {p+"/"+profile: counts([r for r in records if r["presentation"] == p and r["profile"] == profile]) for p in ("original", "explicit_payoffs") for profile in ("low", "middle", "high")},
        "by_presentation_pass": {p+"/"+str(rep): counts([r for r in records if r["presentation"] == p and r["repetition"] == rep]) for p in ("original", "explicit_payoffs") for rep in (1, 2)},
        "matched_choice_outcomes_original_then_explicit": dict(paired),
        "comparisons": {k: dict(v) for k, v in sorted(comparisons.items())},
        "recovered_fits_by_profile": {k: dict(v) for k, v in recovered_counts.items()},
        "nonrecovered_fit_types": {k: dict(v) for k, v in failures.items()},
        "matched_fit_recovery_original_then_explicit": dict(fit_pairs),
        "assistant_explanation_labels": {k: dict(v) for k, v in ratings.items()},
        "review_methods": dict(methods),
        "limits": "Fixed-set descriptive evidence. Fits overlap. Assistant coding is unblinded, including disclosed exact-text label reuse. No internal-mechanism or social-pilot validation claim.",
    }
    (ROOT / "audit/independent-summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
