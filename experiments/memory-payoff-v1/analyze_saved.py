"""Independent arithmetic verification and scientific figure, with no model selection."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

METHODS = ("evolved", "random_search", "matched_gradient")
READOUTS = ("interaction", "wide_control")
SUITES = ("canonical_seen", "canonical_heldout", "shifted", "external_games")


def value(row, readout, method, suite, kind="intact", metric="choice_brier"):
    record = row["models"][readout][method]
    cells = record["checkpoints"]["512"][suite] if kind == "intact" else record[kind][suite]
    return np.mean([cells[str(n)][metric] for n in (4, 12, 24)])


def interval(values):
    means = np.random.default_rng(168000000).choice(values, (10000, len(values)), replace=True).mean(1)
    return np.quantile(means, [.025, .975])


def analyze(folder):
    index = json.loads((folder/"results-index.json").read_text())
    rows = [json.loads((folder/name).read_text()) for name in index["replicates"]]
    summary = json.loads((folder/"summary.json").read_text())
    assert [row["replicate"] for row in rows] == list(range(8))
    computed = {}
    for suite in SUITES:
        metrics = ("choice_brier",) if suite == "external_games" else ("choice_brier", "execution_brier", "brier")
        for method in METHODS:
            for metric in metrics:
                vals = {a: {k: np.array([value(r, a, method, suite, k, metric) for r in rows])
                            for k in ("intact", "no_memory", "donor_history", "drop_extra")} for a in READOUTS}
                prefix = f"{suite}/{method}/{metric}/"
                computed[prefix+"control_minus_interaction"] = vals["wide_control"]["intact"]-vals["interaction"]["intact"]
                for arm in READOUTS:
                    for kind, label in (("no_memory", "memory_gain"), ("donor_history", "donor_gain"), ("drop_extra", "extra_gain")):
                        computed[prefix+arm+"_"+label] = vals[arm][kind]-vals[arm]["intact"]
                computed[prefix+"donor_gain_interaction"] = computed[prefix+"interaction_donor_gain"]-computed[prefix+"wide_control_donor_gain"]
    assert set(computed) == set(summary["contrasts"])
    for key, values in computed.items():
        recorded = summary["contrasts"][key]
        np.testing.assert_allclose(values, recorded["run_differences"], atol=1e-14, rtol=0)
        np.testing.assert_allclose(np.mean(values), recorded["mean"], atol=1e-14, rtol=0)
        np.testing.assert_allclose(interval(values), recorded["paired_bootstrap_95ci"], atol=1e-14, rtol=0)
    for row in rows:
        assert row["source_hashes"] == summary["source_hashes"]
        assert row["config_sha256"] == summary["config_sha256"]
        assert row["api_cost_usd"] == 0
        for key in ("training_stream_sha256", "validation_sha256"):
            assert len({m[key] for arm in row["models"].values() for m in arm.values()}) == 1
    parameters = 0
    for name in index["final_weights"]:
        weights = json.loads((folder/name).read_text())
        assert weights["config_sha256"] == summary["config_sha256"]
        for arm in READOUTS:
            for method in METHODS:
                theta = np.asarray(weights["models"][arm][method]["theta"], dtype=np.float32)
                assert theta.shape == (269,) and np.isfinite(theta).all()
                parameters += 1
    prefix = "canonical_seen/evolved/"
    rules = {prefix+"choice_brier/control_minus_interaction": 0,
             prefix+"choice_brier/interaction_donor_gain": 0,
             prefix+"execution_brier/interaction_donor_gain": 0,
             prefix+"execution_brier/control_minus_interaction": -.002}
    assert rules == summary["joint_primary_criteria"]
    passed = all(interval(computed[k])[0] > threshold for k, threshold in rules.items())
    assert passed == summary["joint_primary_pass"]
    verification = {"replicates": len(rows), "independently_verified_contrasts_and_intervals": len(computed),
                    "parameter_files_verified_models": parameters, "parameters_each": 269,
                    "matched_training_and_validation": True, "joint_primary_pass": bool(passed)}
    (folder/"verification.json").write_text(json.dumps(verification, indent=2)+"\n")
    print(json.dumps(verification))
    plot(computed, folder)


def plot(computed, folder):
    plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "svg.fonttype": "none",
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 7.8))
    panels = [("choice_brier/control_minus_interaction", "A  Choice forecast improvement", "Control loss − interaction loss"),
              ("choice_brier/interaction_donor_gain", "B  Own-history benefit: choice", "Donor loss − own-history loss (interaction model)"),
              ("execution_brier/control_minus_interaction", "C  Execution forecast improvement", "Control loss − interaction loss"),
              ("execution_brier/interaction_donor_gain", "D  Own-history benefit: execution", "Donor loss − own-history loss (interaction model)")]
    labels = ("Evolution (primary)", "Random search", "Matched gradient")
    for ax, (suffix, title, xlabel) in zip(axes.flat, panels):
        for i, method in enumerate(METHODS):
            values = computed[f"canonical_seen/{method}/{suffix}"]
            m, (lo, hi) = float(values.mean()), interval(values)
            color = ("#17687e", "#8a9098", "#895ba3")[i]
            ax.scatter(values, np.full(8, i), color=color, alpha=.2, s=16)
            ax.errorbar(m, i, xerr=[[m-lo], [hi-m]], fmt="o", color=color, capsize=4, linewidth=2)
        ax.axvline(0, color="#777", linestyle="--", linewidth=1)
        ax.set(yticks=range(3), yticklabels=labels, ylim=(2.6, -.6), title=title, xlabel=xlabel)
        ax.grid(axis="x", alpha=.15)
        if suffix == "execution_brier/control_minus_interaction":
            ax.axvline(-.002, color="#b66a32", linestyle=":", linewidth=1.5, label="−0.002 tolerance")
            ax.legend(frameon=False, fontsize=9, loc="best")
    fig.suptitle("Can explicit memory–query interactions help joint learning?", x=.07, ha="left", fontsize=16, fontweight="bold")
    fig.text(.07, .045, "Canonical environment, observed context; averages over 4, 12 and 24 episodes. Eight paired runs; bootstrap 95% intervals.", fontsize=9, color="#555")
    fig.text(.07, .023, "Both architectures have four memory values and 269 parameters. Interaction branch includes payoffs and execution-query kind.", fontsize=9, color="#555")
    fig.subplots_adjust(left=.19, right=.98, top=.88, bottom=.15, hspace=.55, wspace=.68)
    fig.savefig(folder/"memory-payoff.svg")
    fig.savefig(folder/"memory-payoff.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    analyze(parser.parse_args().folder)
