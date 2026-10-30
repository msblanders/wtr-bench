"""Independent post-run arithmetic checks and presentation; no model selection."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

METHODS = ("evolved", "random_search", "matched_gradient", "dense_gradient")
OBJECTIVES = ("joint", "choice_only")
SUITES = ("canonical_seen", "canonical_heldout", "shifted", "external_games")


def value(row, objective, method, suite, kind="intact", metric="choice_brier"):
    record = row["models"][objective][method]
    cells = record["checkpoints"]["512"][suite] if kind == "intact" else record[kind][suite]
    return np.mean([cells[str(n)][metric] for n in (4, 12, 24)])


def interval(values):
    means = np.random.default_rng(148000000).choice(values, (10000, len(values)), replace=True).mean(1)
    return np.quantile(means, [.025, .975])


def analyze(folder):
    index = json.loads((folder/"results-index.json").read_text())
    rows = [json.loads((folder/name).read_text()) for name in index["replicates"]]
    summary = json.loads((folder/"summary.json").read_text())
    assert sorted(row["replicate"] for row in rows) == list(range(8))
    computed = {}
    for suite in SUITES:
        for method in METHODS:
            vals = {o: {k: np.array([value(r, o, method, suite, k) for r in rows])
                        for k in ("intact", "no_memory", "donor_history")} for o in OBJECTIVES}
            prefix = suite+"/"+method+"/"
            computed[prefix+"joint_minus_choice"] = vals["joint"]["intact"]-vals["choice_only"]["intact"]
            for objective in OBJECTIVES:
                computed[prefix+objective+"_memory_gain"] = vals[objective]["no_memory"]-vals[objective]["intact"]
                computed[prefix+objective+"_donor_gain"] = vals[objective]["donor_history"]-vals[objective]["intact"]
            computed[prefix+"donor_gain_interaction"] = computed[prefix+"choice_only_donor_gain"]-computed[prefix+"joint_donor_gain"]
    assert set(computed) == set(summary["contrasts"])
    for key, values in computed.items():
        result = summary["contrasts"][key]
        np.testing.assert_allclose(values, result["run_differences"], atol=1e-14, rtol=0)
        np.testing.assert_allclose(np.mean(values), result["mean"], atol=1e-14, rtol=0)
        np.testing.assert_allclose(interval(values), result["paired_bootstrap_95ci"], atol=1e-14, rtol=0)
    for row in rows:
        for key in ("training_stream_sha256", "validation_sha256"):
            assert len({m[key] for arm in row["models"].values() for m in arm.values()}) == 1
    verification = {"independent_paired_contrasts_and_intervals_verified": len(computed), "replicates": len(rows),
                    "matched_training_and_validation_streams": True, "primary_pass": summary["joint_primary_pass"]}
    (folder/"verification.json").write_text(json.dumps(verification, indent=2)+"\n")
    print(json.dumps(verification))
    plot(rows, folder)


def plot(rows, folder):
    plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "svg.fonttype": "none",
                         "axes.spines.top": False, "axes.spines.right": False})
    labels = ("Evolution", "Random search", "Matched gradient", "Dense gradient")
    colors = ("#b77b39", "#216b87")
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.5), sharey=True)
    for j, objective in enumerate(OBJECTIVES):
        for i, method in enumerate(METHODS):
            y = i+(-.12 if j == 0 else .12)
            metrics = [np.array([value(r, objective, method, "canonical_seen") for r in rows]),
                       np.array([value(r, objective, method, "canonical_seen", "donor_history")-value(r, objective, method, "canonical_seen") for r in rows]),
                       np.array([value(r, objective, method, "canonical_seen", metric="execution_brier") for r in rows])]
            for ax, values in zip(axes, metrics):
                m, (lo, hi) = float(values.mean()), interval(values)
                ax.errorbar(m, y, xerr=[[m-lo], [hi-m]], fmt="o", color=colors[j], capsize=3, linewidth=1.7,
                            label=("Joint" if j == 0 else "Choice only") if i == 0 else None)
    axes[0].set(yticks=range(4), yticklabels=labels, ylim=(3.6, -.6), title="A  Preference prediction",
                xlabel="Choice Brier (lower is better)")
    axes[1].set(title="B  Benefit of the target’s own history", xlabel="Donor-history loss − own-history loss")
    axes[1].axvline(0, color="#777", linestyle="--", linewidth=1)
    axes[2].set(title="C  Execution prediction", xlabel="Execution Brier (lower is better)")
    for ax in axes:
        ax.grid(axis="x", alpha=.16)
        ax.tick_params(axis="y", length=0)
    fig.suptitle("Does choice-only selection improve preference learning?", x=.08, ha="left", fontsize=16, fontweight="bold")
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc="lower center", bbox_to_anchor=(.53, .085), ncol=2, frameon=False)
    fig.text(.08, .04, "Canonical environment, observed query context. Means across 4, 12 and 24 episodes; eight paired runs; bootstrap 95% intervals.", fontsize=9, color="#555")
    fig.subplots_adjust(left=.13, right=.98, top=.82, bottom=.25, wspace=.36)
    fig.savefig(folder/"choice-objective.svg")
    fig.savefig(folder/"choice-objective.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    analyze(parser.parse_args().folder)
