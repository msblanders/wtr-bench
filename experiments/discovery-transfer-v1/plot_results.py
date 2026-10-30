"""Post-run presentation only; this script does not select or evaluate models."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

METHODS = ("evolved", "random_search", "matched_gradient", "dense_gradient")
LABELS = ("Evolution", "Random search", "Matched gradient", "Dense gradient")
COLORS = ("#1b766e", "#9e9e9e", "#5d5fb2", "#d17b26")


def main(folder):
    rows = json.loads((folder/"replicate-results.json").read_text())
    summary = json.loads((folder/"summary.json").read_text())
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "font.family": "DejaVu Sans"})
    fig, axes = plt.subplots(1, 3, figsize=(16.2, 5.3), gridspec_kw={"width_ratios": [1, 1, 1.25]})
    for ax, suite, title in zip(axes[:2], ("shifted", "external_games"),
                               ("A  Held-out synthetic shift", "B  Independent games")):
        for method, label, color in zip(METHODS, LABELS, COLORS):
            points = []
            for checkpoint in (0, 128, 512):
                values = [np.mean([r["models"][method]["checkpoints"][str(checkpoint)][suite][str(n)]["brier"]
                                   for n in (4, 12, 24)]) for r in rows]
                points.append(np.mean(values))
            ax.plot([0, 128, 512], points, marker="o", color=color, label=label, linewidth=2)
        ax.axhline(summary["functional_reference_brier"][suite], color="#34454f", linestyle=":", label="Supplied reference")
        ax.set(xlabel="Selection generation / gradient update", ylabel="Observed-outcome Brier (lower is better)",
               title=title, xticks=[0, 128, 512])
        ax.grid(axis="y", alpha=.18)
    ax = axes[2]
    keys = summary["joint_primary_criteria"]
    names = ["Experience helps\n(synthetic shift)", "Evolution beats\nrandom search", "Experience helps\n(independent games)"]
    for i, key in enumerate(keys):
        result = summary["contrasts"][key]
        mean = result["mean"]
        lo, hi = result["paired_bootstrap_95ci"]
        values = result["run_differences"]
        ax.scatter(values, i+np.linspace(-.12, .12, len(values)), s=18, color=COLORS[0], alpha=.4)
        ax.errorbar(mean, i, xerr=[[mean-lo], [hi-mean]], fmt="o", color=COLORS[0], capsize=4, linewidth=2)
    ax.axvline(0, color="#666", linestyle="--", linewidth=1)
    ax.set(yticks=range(3), yticklabels=names, title="C  Joint primary criteria",
           xlabel="Paired Brier improvement (positive is favorable)", ylim=(2.55, -.55))
    ax.grid(axis="x", alpha=.18)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(.5, .04))
    fig.suptitle("Outcome-selected learning: discovery and external transfer", x=.05, ha="left", fontsize=16, fontweight="bold")
    fig.text(.05, .02, "Eight independent runs. Panels A–B average histories of 4, 12 and 24 episodes; scales differ. Panel C: whole-run bootstrap 95% intervals.", fontsize=9, color="#555")
    fig.subplots_adjust(left=.065, right=.985, top=.85, bottom=.23, wspace=.57)
    fig.savefig(folder/"discovery-transfer.svg")
    fig.savefig(folder/"discovery-transfer.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    main(parser.parse_args().folder)
