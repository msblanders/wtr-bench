"""Present the frozen scores without changing any estimand."""
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
rows = json.loads((args.results/"replicate-results.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})
colors = {"functional": "#15803d", "history": "#2563eb", "wrong_rules": "#c2410c"}
labels = {"functional": "Functional cue rules", "history": "Full history", "wrong_rules": "Wrong cue rules"}
steps, lengths = [64, 256, 1024], [2, 8, 24]
fig, axes = plt.subplots(2, 2, figsize=(10, 7))
for column, regime in enumerate(("shared", "context_specific")):
    for method, color in colors.items():
        trajectories = np.array([[np.mean([r["models"][regime][method]["checkpoints"][str(u)]["reversed"][str(n)]["transfer_excess"]
                                          for n in lengths]) for u in steps] for r in rows])
        for trajectory in trajectories:
            axes[0, column].plot(steps, trajectory, color=color, alpha=.15, linewidth=.7)
        axes[0, column].plot(steps, trajectories.mean(0), color=color, marker="o", linewidth=2, label=labels[method])
        last = np.array([[r["models"][regime][method]["checkpoints"]["1024"]["reversed"][str(n)]["transfer_excess"]
                          for n in lengths] for r in rows])
        axes[1, column].plot(lengths, last.mean(0), color=color, marker="o", linewidth=2)
    for row in range(2):
        ax = axes[row, column]
        ax.set_yscale("log")
        ax.grid(alpha=.18)
        ax.set_ylabel("Transfer excess Brier loss (log scale)")
    axes[0, column].set_title("Shared willingness" if regime == "shared" else "Context-specific willingness")
    axes[0, column].set_xscale("log", base=2)
    axes[0, column].set_xticks(steps, [str(s) for s in steps])
    axes[0, column].set_xlabel("Training updates\n(averaged across history lengths)")
    axes[1, column].set_xticks(lengths)
    axes[1, column].set_xlabel("Observed episodes about a new partner\n(final checkpoint)")
handles, names = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, names, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(.5,.945))
fig.suptitle("Learning and transfer under reversed context cues", fontsize=14, y=.99)
fig.text(.5,.015,"Eight paired training runs. All predictions query a context without partner history. Lower is better; panel scales may differ.",
         ha="center", fontsize=9)
fig.tight_layout(rect=(0,.04,1,.90))
fig.savefig(args.results/"learning-curves.svg")
fig.savefig(args.results/"learning-curves.png", dpi=180)
plt.close(fig)
