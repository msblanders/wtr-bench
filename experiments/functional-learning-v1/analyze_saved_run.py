"""Audit run 40969709564 and extract existing JSON predictions post hoc; no API calls."""
import argparse
import hashlib
import importlib.util
import json
import statistics
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

ARCHIVE_SHA256 = "1bff0a24808ff56e04ae5a60be913dce7e70fa8384935150458a6e4969034290"
RESULTS = Path(__file__).parent / "results/run-40969709564"
REGIMES = ("shared", "context_specific")


def extract_unique(text, keys, parse_response):
    """Select exactly one complete schema-valid object; never change its numbers."""
    candidates = []
    for start, character in enumerate(text):
        if character != "{":
            continue
        try:
            _, length = json.JSONDecoder().raw_decode(text[start:])
            probabilities = parse_response(text[start:start + length], keys)
            candidates.append((probabilities, start, len(text) - start - length))
        except (ValueError, TypeError, KeyError):
            continue
    if len(candidates) != 1:
        raise ValueError(f"Expected one usable object, found {len(candidates)}")
    return candidates[0]


def analyze(directory, destination):
    spec = importlib.util.spec_from_file_location("frozen_pilot", directory / "experiment.py")
    assert spec is not None and spec.loader is not None
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)
    manifest, requests = experiment.check_manifest(directory)
    by_id = {r["id"]: r for r in requests}
    responses = experiment.read_jsonl(directory / "responses.jsonl")
    attempts = experiment.read_jsonl(directory / "attempts.jsonl")
    original = json.loads((directory / "report.json").read_text())
    assert original["data_origin"] == "anthropic_api"
    assert len(responses) == len(requests) == len(attempts) == 256
    assert len({r["id"] for r in responses}) == 256
    assert [r["id"] for r in attempts] == [r["id"] for r in responses]
    assert {r["id"] for r in responses} == set(by_id)
    observations = []
    cost = 0.0
    for row in responses:
        request = by_id[row["id"]]
        assert row["request_hash"] == request["request_hash"]
        raw = row["raw"]
        assert raw["model"] == manifest["model"]
        assert raw["stop_reason"] == "end_turn"
        usage = raw["usage"]
        assert usage.get("cache_creation_input_tokens", 0) == 0
        assert usage.get("cache_read_input_tokens", 0) == 0
        row_cost = (usage["input_tokens"] * manifest["rates"]["input_per_million"]
                    + usage["output_tokens"] * manifest["rates"]["output_per_million"]) / 1e6
        assert abs(row_cost - row["cost_usd"]) < 1e-12
        cost += row_cost
        text = "".join(b.get("text", "") for b in raw["content"] if b["type"] == "text")
        keys = [q["id"] for q in request["answer_key"]]
        probabilities, prefix, suffix = extract_unique(text, keys, experiment.parse_response)
        if row["status"] == "valid":
            assert experiment.parse_response(text, keys) == probabilities == row["predictions"]
        else:
            assert prefix > 0 and suffix == 0
            try:
                experiment.parse_response(text, keys)
            except ValueError:
                pass
            else:
                raise AssertionError("Stored invalid response passed strict parsing")
        distance = {
            method: statistics.mean((probabilities[k] - v) ** 2 for k, v in estimates.items())
            for method, estimates in request["references"].items()
        }
        observations.append({
            "id": row["id"], "seed": request["seed"], "regime": request["regime"],
            "budget": request["budget"], "arm": request["arm"],
            "strict_valid": row["status"] == "valid", "prefix_chars": prefix,
            "scores": experiment.score(request, probabilities), "reference_distance": distance,
        })
    assert abs(cost - original["cost_usd"]) < 1e-10
    cells = []
    for regime in REGIMES:
        for budget in experiment.BUDGETS:
            for arm in experiment.ARMS:
                rows = [r for r in observations if (r["regime"], r["budget"], r["arm"])
                        == (regime, budget, arm)]
                assert len(rows) == manifest["seeds"]
                strict_score = statistics.mean(r["scores"]["all"] if r["strict_valid"] else 1 for r in rows)
                frozen_cell = next(c for c in original["cells"]
                                   if (c["regime"], c["budget"], c["arm"]) == (regime, budget, arm))
                assert abs(strict_score - frozen_cell["mean_mse_including_invalid_penalty"]) < 1e-12
                cells.append({"regime": regime, "budget": budget, "arm": arm,
                              "strict_valid": sum(r["strict_valid"] for r in rows),
                              **{k: statistics.mean(r["scores"][k] for r in rows)
                                 for k in rows[0]["scores"]}})
    contrasts = []
    for regime in REGIMES:
        for comparator in ("general", "structured", "wrong_routing"):
            differences = []
            for seed in range(manifest["seeds"]):
                means = {arm: statistics.mean(r["scores"]["all"] for r in observations
                                             if r["seed"] == seed and r["regime"] == regime
                                             and r["budget"] > 0 and r["arm"] == arm)
                         for arm in (comparator, "functional")}
                differences.append(means[comparator] - means["functional"])
            contrasts.append({"regime": regime, "comparison": f"{comparator} minus functional",
                              "mean_advantage": statistics.mean(differences),
                              "exploratory_paired_world_bootstrap_95ci": experiment.bootstrap_mean(differences),
                              "world_differences": differences})
    structured = [next(c for c in contrasts if c["regime"] == g
                       and c["comparison"] == "structured minus functional") for g in REGIMES]
    interaction = [a - b for a, b in zip(structured[0]["world_differences"], structured[1]["world_differences"])]
    adherence = []
    for regime in REGIMES:
        rows = [r for r in observations if r["regime"] == regime
                and r["arm"] == "wrong_routing" and r["budget"] > 0]
        adherence.append({"regime": regime, "responses": len(rows),
                          "closer_to_functional_than_wrong_reference": sum(
                              r["reference_distance"]["functional"] < r["reference_distance"]["wrong_routing"]
                              for r in rows),
                          "mean_reference_distance": {k: statistics.mean(r["reference_distance"][k] for r in rows)
                                                      for k in ("functional", "wrong_routing")}})
    criterion = []
    for regime in REGIMES:
        for arm in experiment.ARMS:
            achieved = []
            for seed in range(manifest["seeds"]):
                points = [next(r for r in observations
                               if (r["regime"], r["arm"], r["seed"], r["budget"]) == (regime, arm, seed, n))
                          for n in experiment.BUDGETS]
                first = next((n for i, n in enumerate(experiment.BUDGETS)
                              if all(r["scores"]["all"] <= experiment.CRITERION_MSE for r in points[i:])), None)
                achieved.append(first)
            counts = Counter("not_reached" if n is None else str(n) for n in achieved)
            criterion.append({"regime": regime, "arm": arm, "per_world": achieved, "counts": dict(counts)})
    result = {
        "analysis_status": "Exploratory post hoc JSON-object extraction, not the frozen primary analysis",
        "run_id": 40969709564, "model": manifest["model"], "cost_usd": cost,
        "source_sha256": manifest["source_sha256"], "requests_sha256": manifest["requests_sha256"],
        "archive_sha256": ARCHIVE_SHA256, "responses": len(responses),
        "strict_valid": sum(r["strict_valid"] for r in observations), "extracted_valid": len(observations),
        "method": "One complete schema-valid object per response; all original probabilities preserved. No retries or model calls.",
        "cells": cells, "contrasts": contrasts,
        "interaction": {"shared_minus_context_specific_advantage": statistics.mean(interaction),
                        "exploratory_paired_world_bootstrap_95ci": experiment.bootstrap_mean(interaction)},
        "wrong_rule_adherence_diagnostic": adherence, "criterion_mse": experiment.CRITERION_MSE,
        "criterion_results": criterion,
    }
    (destination / "posthoc-results.json").write_text(json.dumps(result, indent=2) + "\n")
    for name in ("report.json", "report.md"):
        (destination / ("original-" + name)).write_bytes((directory / name).read_bytes())
    print(json.dumps({k: v for k, v in result.items() if k not in ("cells", "contrasts", "criterion_results")}, indent=2))
    return result, json.loads((directory / "reference-results.json").read_text())


def plot(result, references, destination):
    import matplotlib.pyplot as plt

    colors = {"general": "#747d8c", "structured": "#cc7722", "functional": "#1674b8", "wrong_routing": "#8b57a5"}
    labels = {"general": "General instructions", "structured": "Structured control",
              "functional": "Functional instructions", "wrong_routing": "Wrong-rule instructions"}
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.7), sharey=True)
    budgets = [0, 2, 8, 24]
    for ax, regime, title in zip(axes, REGIMES, ("Shared across settings", "Willingness differs by setting")):
        for arm, color in colors.items():
            values = [next(c["all"] for c in result["cells"] if (c["regime"], c["budget"], c["arm"])
                           == (regime, n, arm)) for n in budgets]
            ax.plot(budgets, values, color=color, label=labels[arm], marker="o", linewidth=2)
        oracle = [statistics.mean(r["all"] for r in references
                                  if (r["regime"], r["budget"], r["method"]) == (regime, n, "oracle"))
                  for n in budgets]
        ax.plot(budgets, oracle, "--", color="#222222", label="Bayesian reference (knows world structure)", linewidth=1.5)
        ax.set(title=title, xlabel="Observed episodes per partner", xticks=budgets, ylim=(0, .105))
        ax.grid(axis="y", alpha=.18)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Mean squared probability error (lower is better)")
    fig.suptitle("Exploratory learning curves from recovered predictions", fontsize=15, y=.98)
    fig.text(.5, .91, "8 independent worlds per environment; original prediction values unchanged", ha="center", fontsize=10)
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(.5, -.005))
    fig.subplots_adjust(top=.80, bottom=.24, left=.08, right=.98, wspace=.13)
    fig.savefig(destination / "learning-curves.png", dpi=170, bbox_inches="tight")
    fig.savefig(destination / "learning-curves.svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot", action="store_true", help="Requires matplotlib; analysis itself uses standard library only")
    args = parser.parse_args()
    archive = RESULTS / "raw-artifact.zip"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA256
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.namelist():
                assert (directory / member).resolve().is_relative_to(directory.resolve())
            bundle.extractall(directory)
        result, references = analyze(directory, RESULTS)
        if args.plot:
            plot(result, references, RESULTS)


if __name__ == "__main__":
    main()
