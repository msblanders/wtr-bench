"""Small, auditable selection of evidence gates and transfer. No network calls."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import random
import shutil
import statistics
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WORLD_SOURCE = HERE / "world_v1.py"
if not WORLD_SOURCE.exists():
    WORLD_SOURCE = HERE.parent / "functional-learning-v1" / "experiment.py"
spec = importlib.util.spec_from_file_location("selection_world", WORLD_SOURCE)
assert spec is not None and spec.loader is not None
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)

VERSION = "rule-selection-v1.0"
ECOLOGIES = {"both_shared": (True, True), "both_local": (False, False),
             "w_shared_a_local": (True, False), "w_local_a_shared": (False, True)}
CHECKPOINTS = (0, 2, 8, 24, 96)
FIT_INDEX = (1, 2, 3)
EVENTS = ("voluntary_decline", "voluntary_failure", "voluntary_success",
          "assigned_failure", "assigned_success")
# 0 ignore; 1 positive; 2 negative. No such reference enters the initial populations.
CORRECT_GATES = ((2, 1, 1, 0, 0), (0, 2, 1, 2, 1))
GATES = np.array(list(itertools.product(range(3), repeat=5)), dtype=np.int8)
POWERS = np.array([81, 27, 9, 3, 1], dtype=np.int64)
DEFAULTS = {"replicates": 8, "selection_worlds": 64, "evaluation_worlds": 256, "seed_base": 100000,
            "population": 64, "generations": 40, "elite": 4, "mutation_probability": 1/12}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def event_index(record):
    if record["instruction"] == "ASSIGNED":
        return 4 if record["outcome"] == "success" else 3
    if not record["attempt"]:
        return 0
    return 2 if record["outcome"] == "success" else 1


def make_world(seed, ecology):
    share_w, share_a = ECOLOGIES[ecology]
    base = v1.make_world(seed, "shared" if share_w else "context_specific")
    names = sorted(base["parameters"])
    contexts = list(dict.fromkeys(r["setting"] for r in base["records"])) + [base["heldout_setting"]]
    rng = random.Random(62029 + seed)
    abilities = {}
    for name in names:
        a = base["parameters"][name]["ability"]
        alternatives = [rng.random(), rng.random()]
        abilities[name] = dict(zip(contexts, [a, a, a] if share_a else [a, *alternatives]))
    records = []
    for exposure in range(1, max(CHECKPOINTS) + 1):
        template = [r for r in base["records"] if r["exposure"] == (exposure - 1) % 24 + 1]
        for original in template:
            r = dict(original, exposure=exposure)
            choice_draw, success_draw = rng.random(), rng.random()
            if exposure > 24:
                r["attempt"] = (r["instruction"] == "ASSIGNED"
                    or choice_draw < base["parameters"][r["partner"]]["inclination"][r["setting"]])
            a = abilities[r["partner"]][r["setting"]]
            r["outcome"] = ("success" if success_draw < a else "failure") if r["attempt"] else "none"
            records.append(r)
    truth = {(name, context): (base["parameters"][name]["inclination"][context], abilities[name][context])
             for name in names for context in contexts}
    return {"records": records, "truth": truth, "names": names, "contexts": contexts}


def pack_world(world):
    """Representation uses observations and arbitrary identities; truth is a separate scoring array."""
    counts = np.zeros((len(CHECKPOINTS), 4, 3, 5), dtype=np.float64)
    name_id = {name: i for i, name in enumerate(world["names"])}
    context_id = {context: i for i, context in enumerate(world["contexts"])}
    current = np.zeros((4, 3, 5), dtype=np.float64)
    by_exposure = {}
    for r in world["records"]:
        by_exposure.setdefault(r["exposure"], []).append(r)
    for exposure in range(1, max(CHECKPOINTS) + 1):
        for r in by_exposure[exposure]:
            current[name_id[r["partner"]], context_id[r["setting"]], event_index(r)] += 1
        if exposure in CHECKPOINTS:
            counts[CHECKPOINTS.index(exposure)] = current
    truth = np.array([[world["truth"][name, context] for context in world["contexts"]]
                      for name in world["names"]])
    return counts, truth


def dataset(seeds, ecology):
    packed = [pack_world(make_world(seed, ecology)) for seed in seeds]
    return np.stack([c for c, _ in packed], axis=1), np.stack([t for _, t in packed])


def decode_rule(index):
    return [*map(int, GATES[index % 243]), int(index // 243)]


def encode_rule(genes):
    return int(np.dot(genes[:5], POWERS) + 243 * genes[5])


def predict_rule(counts, genes):
    evidence = np.broadcast_to(counts.sum(axis=-2, keepdims=True), counts.shape) if genes[5] else counts
    gates = np.asarray(genes[:5])
    return (1 + evidence[..., gates == 1].sum(axis=-1)) / (2 + evidence[..., gates != 0].sum(axis=-1))


def predict(counts, genotype):
    return np.stack([predict_rule(counts, genotype[:6]), predict_rule(counts, genotype[6:])], axis=-1)


def contextual_predict(counts, genotype):
    """One shared interpreter, with the query selecting its instruction row; equivalent function class."""
    result = np.empty((*counts.shape[:-1], 2))
    table = np.array(genotype).reshape(2, 6)
    for query in range(2):
        result[..., query] = predict_rule(counts, table[query])
    return result


def loss_table(counts, truth):
    """Compile finite per-channel fitnesses. Search accesses only queried genotype fitnesses."""
    counts = counts[list(FIT_INDEX)]
    losses = np.empty((2, 486))
    for pool in range(2):
        evidence = np.broadcast_to(counts.sum(axis=-2, keepdims=True), counts.shape) if pool else counts
        flat = evidence.reshape(-1, 5)
        positive = flat @ (GATES == 1).T
        total = flat @ (GATES != 0).T
        predictions = (1 + positive) / (2 + total)
        for channel in range(2):
            target = np.broadcast_to(truth[..., channel], counts.shape[:-1]).reshape(-1)
            losses[channel, pool*243:(pool+1)*243] = ((predictions - target[:, None])**2).mean(axis=0)
    return losses


def population_fitness(population, losses):
    i = population[:, :5] @ POWERS + 243 * population[:, 5]
    j = population[:, 6:11] @ POWERS + 243 * population[:, 11]
    return (losses[0, i] + losses[1, j]) / 2


def founders(rng, n, tied):
    p = rng.integers(0, 3, size=(n, 12), dtype=np.int64)
    p[:, 5] = rng.integers(0, 2, size=n)
    p[:, 11] = p[:, 5] if tied else rng.integers(0, 2, size=n)
    return p


def search(losses, seed, config, mode):
    rng = np.random.default_rng(seed)
    tied = mode == "tied"
    population = founders(rng, config["population"], tied)
    best_loss, best = float("inf"), None
    trace, unique = [], set()
    for generation in range(config["generations"]):
        fitness = population_fitness(population, losses)
        unique.update(tuple(map(int, x)) for x in population)
        index = int(np.argmin(fitness))
        if fitness[index] < best_loss:
            best_loss, best = float(fitness[index]), population[index].copy()
        trace.append({"generation": generation, "best_so_far": best_loss,
                      "population_mean": float(fitness.mean())})
        if mode == "random":
            population = founders(rng, config["population"], False)
        elif generation + 1 < config["generations"]:
            elite = population[np.argsort(fitness, kind="stable")[:config["elite"]]].copy()
            offspring = []
            for _ in range(config["population"] - config["elite"]):
                parents = []
                for _ in range(2):
                    contestants = rng.integers(0, len(population), size=3)
                    parents.append(population[contestants[np.argmin(fitness[contestants])]])
                child = np.where(rng.random(12) < 0.5, parents[0], parents[1]).copy()
                for gene in range(11 if tied else 12):
                    if rng.random() < config["mutation_probability"]:
                        choices = 2 if gene in (5, 11) else 3
                        child[gene] = (child[gene] + rng.integers(1, choices)) % choices
                if tied:
                    child[11] = child[5]
                offspring.append(child)
            population = np.concatenate((elite, offspring))
    assert best is not None
    if tied:
        optimum = min((losses[0, p*243:(p+1)*243].min() + losses[1, p*243:(p+1)*243].min())/2
                      for p in range(2))
    else:
        optimum = losses.min(axis=1).mean()
    return {"genotype": list(map(int, best)), "selection_mse": best_loss,
            "exact_class_selection_optimum": float(optimum), "optimization_gap": float(best_loss-optimum),
            "candidate_evaluations": config["population"]*config["generations"],
            "unique_genotypes": len(unique), "trace": trace}


def reference_genotype(ecology):
    return [*CORRECT_GATES[0], int(ECOLOGIES[ecology][0]), *CORRECT_GATES[1], int(ECOLOGIES[ecology][1])]


def log_evidence(s, f):
    return math.lgamma(float(s)+1) + math.lgamma(float(f)+1) - math.lgamma(float(s+f)+2)


def adaptive_predict(counts):
    result = np.empty((*counts.shape[:-1], 2))
    for channel, gates in enumerate(CORRECT_GATES):
        positive = counts[..., np.array(gates) == 1].sum(axis=-1)
        negative = counts[..., np.array(gates) == 2].sum(axis=-1)
        for budget in range(len(CHECKPOINTS)):
            for world in range(counts.shape[1]):
                s, f = positive[budget, world], negative[budget, world]
                sp, fp = s.sum(axis=-1), f.sum(axis=-1)
                log_shared = sum(log_evidence(a, b) for a, b in zip(sp, fp))
                log_local = sum(log_evidence(a, b) for a, b in zip(s.flat, f.flat))
                delta = log_shared - log_local
                weight = 1/(1+math.exp(-delta)) if delta >= 0 else math.exp(delta)/(1+math.exp(delta))
                pooled, local = (1+sp)/(2+sp+fp), (1+s)/(2+s+f)
                result[budget, world, ..., channel] = weight*pooled[:, None] + (1-weight)*local
    return result


def evaluation(predictions, truth):
    error = (predictions - truth[None])**2
    return {"mse": float(error[list(FIT_INDEX)].mean()),
            "transfer_mse": float(error[list(FIT_INDEX), ..., 2, :].mean()),
            "channel_mse": error[list(FIT_INDEX)].mean(axis=(0, 1, 2, 3)).tolist(),
            "curve": [{"exposures": n, "mse": float(error[b].mean()),
                       "transfer_mse": float(error[b, ..., 2, :].mean())} for b, n in enumerate(CHECKPOINTS)]}


def freeze(out, config):
    out.mkdir(parents=True, exist_ok=False)
    sources = {"experiment.py": Path(__file__), "world_v1.py": WORLD_SOURCE,
               "protocol.md": HERE/"README.md", "requirements.txt": HERE/"requirements.txt"}
    hashes = {}
    for name, src in sources.items():
        shutil.copyfile(src, out/name)
        hashes[name] = hashlib.sha256((out/name).read_bytes()).hexdigest()
    base = config["seed_base"]
    seed_plan = [{"replicate": r, "selection": list(range(base+10000*r, base+10000*r+config["selection_worlds"])),
                  "evaluation": list(range(base+5000+10000*r, base+5000+10000*r+config["evaluation_worlds"]))}
                 for r in range(config["replicates"])]
    manifest = {"version": VERSION, "config": config, "seed_plan": seed_plan,
                "source_hashes": hashes, "numpy_version": np.__version__, "api_budget_usd": 0,
                "checkpoints": CHECKPOINTS, "ecologies": ECOLOGIES,
                "status": "prospectively frozen exploratory simulation; no outcomes collected"}
    write_json(out/"manifest.json", manifest)
    print(json.dumps({"version": VERSION, "run_ecology_combinations": len(seed_plan)*len(ECOLOGIES),
                      "api_budget_usd": 0, "source_hashes": hashes}), flush=True)


def validate(out):
    manifest = json.loads((out/"manifest.json").read_text())
    for name, expected in manifest["source_hashes"].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest() == expected, name
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == manifest["source_hashes"]["experiment.py"]
    assert hashlib.sha256(WORLD_SOURCE.read_bytes()).hexdigest() == manifest["source_hashes"]["world_v1.py"]
    assert np.__version__ == manifest["numpy_version"]
    return manifest


def run(out):
    manifest = validate(out)
    with (out/"started.json").open("x") as f:
        json.dump({"data_origin": "synthetic_selection_experiment", "api_cost_usd": 0}, f)
    config = manifest["config"]
    start = time.monotonic()
    for plan in manifest["seed_plan"]:
        for ecology, sharing in ECOLOGIES.items():
            tick = time.monotonic()
            counts, truth = dataset(plan["selection"], ecology)
            losses = loss_table(counts, truth)
            searches = {mode: search(losses, 870000+plan["replicate"], config, mode)
                        for mode in ("flexible", "tied", "random")}
            # Holdout is constructed only after all three genotype searches have finished.
            counts, truth = dataset(plan["evaluation"], ecology)
            outputs, metrics = {}, {}
            for mode, result in searches.items():
                genotype = result["genotype"]
                outputs[mode] = predict(counts, genotype)
                assert np.array_equal(outputs[mode], contextual_predict(counts, genotype))
                metrics[mode] = evaluation(outputs[mode], truth)
                result["correct_event_instructions"] = sum(a == b for a, b in zip(
                    genotype[:5]+genotype[6:11], list(CORRECT_GATES[0])+list(CORRECT_GATES[1])))
                result["correct_transfer_bits"] = sum(genotype[i] == int(expected)
                    for i, expected in zip((5, 11), sharing))
            flexible = searches["flexible"]["genotype"]
            swapped_pool = flexible.copy()
            swapped_pool[5], swapped_pool[11] = swapped_pool[11], swapped_pool[5]
            controls = {"fixed_functional": reference_genotype("both_shared"),
                        "regime_informed": reference_genotype(ecology),
                        "swap_transfer": swapped_pool,
                        "swap_programs": flexible[6:]+flexible[:6]}
            for name, genotype in controls.items():
                metrics[name] = evaluation(predict(counts, genotype), truth)
            metrics["adaptive"] = evaluation(adaptive_predict(counts), truth)
            opposite = next(k for k, v in ECOLOGIES.items() if v == tuple(not x for x in sharing))
            opposite_counts, opposite_truth = dataset(plan["evaluation"], opposite)
            metrics["flexible_in_opposite_ecology"] = evaluation(predict(opposite_counts, flexible), opposite_truth)
            result = {"replicate": plan["replicate"], "ecology": ecology,
                      "searches": searches, "evaluation": metrics,
                      "contextual_interpreter_exactly_equivalent": True,
                      "compiled_single_channel_programs": 486,
                      "compiled_program_target_scores": 972,
                      "elapsed_seconds": time.monotonic()-tick}
            write_json(out/f"result-{plan['replicate']:02d}-{ecology}.json", result)
            print(json.dumps({"replicate": plan["replicate"], "ecology": ecology,
                "elapsed_seconds": round(result["elapsed_seconds"], 2),
                "evaluation_mse": {k: round(v["mse"], 6) for k, v in metrics.items()}}), flush=True)
    write_json(out/"completed.json", {"elapsed_seconds": time.monotonic()-start, "api_cost_usd": 0})


def interval(values):
    rng = np.random.default_rng(97129)
    samples = rng.choice(values, size=(4000, len(values)), replace=True).mean(axis=1)
    return np.quantile(samples, [0.025, 0.975]).tolist()


def summarize(out):
    manifest = validate(out)
    rows = [json.loads(p.read_text()) for p in sorted(out.glob("result-*.json"))]
    assert len(rows) == manifest["config"]["replicates"]*len(ECOLOGIES), "Incomplete run: no aggregate inference"
    cells, contrasts = [], []
    for ecology in ECOLOGIES:
        subset = [r for r in rows if r["ecology"] == ecology]
        for method in subset[0]["evaluation"]:
            values = [r["evaluation"][method]["mse"] for r in subset]
            cells.append({"ecology": ecology, "method": method, "mse": statistics.mean(values),
                          "replicates": len(values), "bootstrap_95ci": interval(values)})
        for comparator in ("tied", "random", "adaptive", "swap_transfer", "swap_programs"):
            differences = [r["evaluation"][comparator]["mse"]-r["evaluation"]["flexible"]["mse"] for r in subset]
            contrasts.append({"ecology": ecology, "comparison": comparator+" minus flexible",
                "mean": statistics.mean(differences), "bootstrap_95ci": interval(differences),
                "run_differences": differences})
    interaction = []
    for r in range(manifest["config"]["replicates"]):
        per_ecology = {x["ecology"]: x["evaluation"]["tied"]["mse"]-x["evaluation"]["flexible"]["mse"]
                      for x in rows if x["replicate"] == r}
        interaction.append((per_ecology["w_shared_a_local"]+per_ecology["w_local_a_shared"]
                            -per_ecology["both_shared"]-per_ecology["both_local"])/2)
    summary = {"version": VERSION, "data_origin": "synthetic_selection_experiment",
        "api_cost_usd": 0, "cells": cells, "contrasts": contrasts,
        "primary_interaction": {"meaning": "tied-minus-flexible advantage: heterogeneous minus homogeneous ecologies",
            "mean": statistics.mean(interaction), "bootstrap_95ci": interval(interaction), "run_differences": interaction},
        "flexible_exact_rule_recovery": sum(x["searches"]["flexible"]["correct_event_instructions"] == 10
            and x["searches"]["flexible"]["correct_transfer_bits"] == 2 for x in rows),
        "run_ecology_combinations": len(rows),
        "shared_contextual_interpreter_equivalent": all(x["contextual_interpreter_exactly_equivalent"] for x in rows),
        "elapsed_seconds": json.loads((out/"completed.json").read_text())["elapsed_seconds"]}
    write_json(out/"summary.json", summary)
    lines = ["# Rule-selection pilot results", "", "Exploratory synthetic selection; zero API calls.", "",
             "MSE averages exposure checkpoints 2, 8, 24 on evaluation worlds; lower is better.", "",
             "| Ecology | Method | MSE |", "|---|---|---:|"]
    lines += [f"| {c['ecology']} | {c['method']} | {c['mse']:.6f} |" for c in cells]
    lines += ["", "Primary paired interaction: " + json.dumps(summary["primary_interaction"]), "",
        f"Exact theory-reference program recovery: {summary['flexible_exact_rule_recovery']}/{len(rows)}.",
        "A shared contextual interpreter exactly reproduces all selected programs. These results concern evidence gating and transfer inside a fixed counting algorithm; they do not establish distinct physical modules or newly invented learning algorithms."]
    (out/"report.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("cells", "contrasts")}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "report"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.out, DEFAULTS)
    elif args.command == "run":
        run(args.out)
    else:
        summarize(args.out)


if __name__ == "__main__":
    main()
