"""Plot reported cells and paired contrasts; does not select or modify estimands."""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("results", type=Path)
args = parser.parse_args()
summary = json.loads((args.results/"summary.json").read_text())
rows = json.loads((args.results/"replicate-results.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none"})
colors = {"shared": "#2563eb", "separate": "#a21caf"}
labels = {"shared": "Shared updates", "separate": "Separate updates"}
fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True, sharey="row")
steps = np.array([64, 256, 1024])
for i, h in enumerate((2, 12)):
    for j, eco in enumerate(("stable", "changing", "mixed")):
        ax = axes[i, j]
        key = f"{eco}-h{h}"
        for method in ("shared", "separate"):
            trajectories = np.array([[r["conditions"][key][method]["checkpoints"][str(u)]["excess_brier"]
                                      for u in steps] for r in rows])
            for trajectory in trajectories:
                ax.plot(steps, trajectory, color=colors[method], linewidth=.7, alpha=.18)
            ax.plot(steps, trajectories.mean(axis=0), color=colors[method], marker="o",
                    linewidth=2.2, markersize=4, label=labels[method])
        ax.set_xscale("log", base=2)
        ax.set_xticks(steps, [str(s) for s in steps])
        ax.grid(alpha=.2)
        ax.set_title(f"{eco.capitalize()} | {2*h} state values")
        if j == 0:
            ax.set_ylabel("Excess Brier loss (lower is better)")
        if i == 1:
            ax.set_xlabel("Training updates")
handles, names = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, names, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(.5,.94))
fig.suptitle("Does limited memory make sharing costly in a mixed ecology?", y=.99, fontsize=14)
fig.text(.5, .015, "Thin lines: eight paired replicates. Bold lines: means. Equal memory and forward matrix arithmetic within each pair; unequal parameter counts.",
         ha="center", fontsize=9)
fig.tight_layout(rect=(0,.04,1,.9))
fig.savefig(args.results/"learning-curves.svg")
fig.savefig(args.results/"learning-curves.png", dpi=180)
plt.close(fig)

names = ["ecology_interaction_h2", "ecology_interaction_h12", "primary_memory_ecology_interaction"]
titles = ["Mixture-specific sharing cost\n4 state values", "Mixture-specific sharing cost\n24 state values",
          "Primary: small minus large\nmemory interaction"]
fig, ax = plt.subplots(figsize=(9, 4.5))
for i, name in enumerate(names):
    c = summary["contrasts"][name]
    vals = np.array(c["run_differences"])
    ax.scatter(np.linspace(i-.12, i+.12, len(vals)), vals, color="#64748b", s=24, alpha=.65)
    lo, hi = c["paired_bootstrap_95ci"]
    ax.vlines(i, lo, hi, color="#0f172a", linewidth=2.5)
    ax.scatter([i], [c["mean"]], color="#0f172a", marker="D", s=40, zorder=3)
ax.axhline(0, color="#94a3b8", linewidth=1)
ax.set_xticks(range(3), titles)
ax.set_ylabel("Paired error contrast")
ax.set_title("Prespecified ecology and memory contrasts")
ax.grid(axis="y", alpha=.2)
fig.text(.5, .02, "Dots: eight full replicates. Diamonds: means. Bars: exploratory paired bootstrap 95% intervals.", ha="center", fontsize=9)
fig.tight_layout(rect=(0,.05,1,1))
fig.savefig(args.results/"paired-contrasts.svg")
plt.close(fig)
