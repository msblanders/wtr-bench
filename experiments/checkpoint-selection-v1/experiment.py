"""Prospective checkpoint-selection comparison on shared fresh training trajectories."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import time
from pathlib import Path

import baseline
import external
import models
import numpy as np
import torch
import worlds

HERE = Path(__file__).resolve().parent
VERSION = "checkpoint-selection-v1.0"
PREDECESSOR = "219cacde3a7f1b4e6837ff30183836e9c543ba36"
MERGED_BASELINE = "bacaf04e6522dd786962eb26d1e2f1e355624f79"
CONFIG = dict(baseline.CONFIG, replicates=8, policies=["joint", "guarded_choice", "raw_last"],
              methods=["evolved", "matched_gradient"], selection_execution_margin=.002,
              development_objective="joint versus minimum choice subject to execution guard",
              seed_namespace="241000000-250000007")
METHODS = tuple(CONFIG["methods"])
POLICIES = tuple(CONFIG["policies"])
READOUTS = models.READOUTS
SUITES = baseline.SUITES
FILES = ("experiment.py", "baseline.py", "models.py", "worlds.py", "external.py",
         "requirements.txt", "README.md", "test_integrity.py")
write_json, digest = baseline.write_json, baseline.digest


def seeds_for(seed):
    return {"initialization": 241000000+seed, "training": 242000000+seed,
            "validation": 243000000+seed, "evolution": 244000000+seed,
            "random_search": 245000000+seed, "evaluation": 246000000+1000*seed,
            "diagnostics": 247000000+seed, "donors": 249000000+1000*seed,
            "replay": 250000000+seed}


def make_bank(seed, config):
    rng = np.random.default_rng(seeds_for(seed)["training"])
    bank = [worlds.synthetic(rng, config["batch_size"], config["max_history"], training=True)
            for _ in range(config["bank_batches"])]
    cached = [models.inputs(data) for data in bank]
    hasher = hashlib.sha256()
    for data in bank:
        baseline.stream_update(hasher, data)
    rng = np.random.default_rng(seeds_for(seed)["replay"])
    order = np.concatenate([np.arange(len(bank))]+[rng.permutation(len(bank))
                           for _ in range(config["generations"]//len(bank)-1)])
    if len(order) != config["generations"]:
        raise ValueError("Generation budget must contain complete bank passes")
    return bank, cached, order, hasher.hexdigest()


def component_scores(theta, data, data_inputs, readout):
    """Use only observed outcomes; joint arithmetic matches the predecessor exactly."""
    with torch.no_grad():
        pred = models.small(torch.from_numpy(theta[None]), data_inputs, readout)
        choice, execution = pred
        y = torch.from_numpy(data["y_choice"]).long()
        picked = choice[0, torch.arange(len(y)), y]
        c = (.5*(choice[0].square().sum(-1)-2*picked+1)).mean()
        e = (execution[0]-torch.from_numpy(data["y_ability"])).square().mean()
        joint = baseline.joint_loss(pred, data)[0]
    result = {"choice": float(c), "execution": float(e), "joint": float(joint)}
    if not all(np.isfinite(v) for v in result.values()):
        raise ValueError("Nonfinite development score")
    return result


def select_policies(records, budget, config):
    """Only development scores and step numbers are accepted by the selector."""
    stride = budget//config["development_candidates"]
    pool = [r for r in records if r["step"] <= budget and r["step"] % stride == 0]
    if len(pool) != config["development_candidates"]+1:
        raise ValueError("Unequal development candidate count")
    joint = min(pool, key=lambda r: (r["joint"], r["step"]))
    limit = joint["execution"]+config["selection_execution_margin"]
    feasible = [r for r in pool if r["execution"] <= limit]
    guarded = min(feasible, key=lambda r: (r["choice"], r["step"]))
    raw = next(r for r in pool if r["step"] == budget)
    return {"joint": dict(joint), "guarded_choice": dict(guarded), "raw_last": dict(raw)}, {
        "candidate_count": len(pool), "guarded_feasible_count": len(feasible),
        "guard_reference_step": joint["step"], "development_execution_limit": limit,
        "candidate_steps": [r["step"] for r in pool]}


def train(seed, config, out, readout, method, bank_info):
    baseline.check_config(config)
    if method not in METHODS:
        raise ValueError(method)
    seeds = seeds_for(seed)
    bank, cached, order, bank_hash = bank_info
    validation = worlds.synthetic(np.random.default_rng(seeds["validation"]),
                                  config["validation_lifetimes"], config["max_history"], training=True)
    vi = models.inputs(validation)
    initial = models.initial_mean()+np.random.default_rng(seeds["initialization"]).normal(
        0, config["initial_sd"], models.PARAMETERS).astype(np.float32)
    candidates = {0: initial.copy()}
    records = [dict(step=0, **component_scores(initial, validation, vi, readout))]
    rng = np.random.default_rng(seeds["evolution"])
    means = models.initial_mean()
    sd = np.full(models.PARAMETERS, config["initial_sd"], dtype=np.float32)
    weights = np.log(config["elites"]+.5)-np.log(np.arange(1, config["elites"]+1))
    weights = (weights/weights.sum()).astype(np.float32)
    torch.manual_seed(seeds["initialization"])
    model = models.Small(initial, readout)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["adam_lr"])
    hasher, prefixes = hashlib.sha256(), {}
    started = time.perf_counter()
    for step, bank_id in enumerate(order, start=1):
        data, di = bank[bank_id], cached[bank_id]
        baseline.stream_update(hasher, data)
        if method == "evolved":
            population = means+sd*rng.standard_normal((config["population"], models.PARAMETERS)).astype(np.float32)
            population[0] = means
            losses = baseline.vector_loss(population, data, di, readout)
            elite = population[np.argsort(losses, kind="stable")[:config["elites"]]]
            new_mean = (weights[:, None]*elite).sum(0)
            new_sd = np.sqrt((weights[:, None]*(elite-means)**2).sum(0))
            means = (1-config["mean_rate"])*means+config["mean_rate"]*new_mean
            sd = np.clip((1-config["sd_rate"])*sd+config["sd_rate"]*new_sd,
                         config["min_sd"], config["max_sd"])
            theta = means
        else:
            loss = baseline.joint_loss(model(di), data)[0]
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = baseline.nn_clip(model, config["gradient_clip"])
            if not np.isfinite(float(loss.detach())) or not np.isfinite(norm):
                raise ValueError("Nonfinite training")
            optimizer.step()
            theta = model.theta.detach().numpy()
        if baseline.due_budgets(step, config):
            candidates[step] = theta.copy()
            records.append(dict(step=step, **component_scores(theta, validation, vi, readout)))
        if step in config["budgets"]:
            prefixes[str(step)] = hasher.hexdigest()
        if step % 256 == 0 or step == config["generations"]:
            print(json.dumps({"replicate": seed, "readout": readout, "method": method,
                              "step": step, "seconds": time.perf_counter()-started}), flush=True)
    if not all(np.isfinite(v).all() for v in candidates.values()):
        raise ValueError("Nonfinite candidate")
    selection, pools = {}, {}
    for budget in config["budgets"]:
        selection[str(budget)], pools[str(budget)] = select_policies(records, budget, config)
    out.mkdir(parents=True, exist_ok=True)
    steps = np.array(list(candidates), dtype=np.int64)
    theta = np.stack(list(candidates.values()))
    np.savez_compressed(out/f"{method}-candidates.npz", steps=steps, theta=theta,
                        **{k: np.array([r[k] for r in records]) for k in ("choice", "execution", "joint")})
    write_json(out/f"{method}-development.json", records)
    if method == "evolved":
        np.savez(out/"search-distribution.npz", mean=means, sd=sd)
    vh = hashlib.sha256()
    baseline.stream_update(vh, validation)
    metadata = {"readout": readout, "method": method, "selection": selection, "selection_pools": pools,
        "candidate_theta_sha256": hashlib.sha256(theta.tobytes()).hexdigest(),
        "candidate_steps_sha256": hashlib.sha256(steps.tobytes()).hexdigest(),
        "training_stream_sha256": hasher.hexdigest(), "training_prefix_sha256": prefixes,
        "bank_sha256": bank_hash, "validation_sha256": vh.hexdigest(),
        "unique_training_lifetimes": len(bank)*config["batch_size"],
        "training_presentations": len(order)*config["batch_size"],
        "unique_development_evaluations": len(records),
        "resources": models.resources(method, readout), "training_seconds": time.perf_counter()-started}
    return candidates, metadata


def evaluate(seed, candidates, metadata, protocol, config):
    namespace = external.load(protocol/"upstream")
    hashes, donor_hashes, references = {}, {}, {}
    for arm in metadata.values():
        for record in arm.values():
            record["policies"] = {p: {"budgets": {str(b): {k: {} for k in ("intact", "no_memory", "donor_history")}
                                                  for b in config["budgets"]}} for p in POLICIES}
    for si, suite in enumerate(SUITES):
        hashes[suite], donor_hashes[suite], references[suite] = {}, {}, {}
        for length in config["test_lengths"]:
            rng = np.random.default_rng(seeds_for(seed)["evaluation"]+100*(0 if suite.startswith("canonical") else si)+length)
            if suite == "external_games":
                data = worlds.external_games(rng, config["evaluation_lifetimes"], length, namespace)
            else:
                data = worlds.synthetic(rng, config["evaluation_lifetimes"], length,
                                        suite="canonical" if suite.startswith("canonical") else suite)
            if suite == "canonical_seen":
                data = baseline.seen_context(data)
            donors, permutation = baseline.donor_histories(
                data, np.random.default_rng(seeds_for(seed)["donors"]+100*si+length))
            h = hashlib.sha256()
            baseline.stream_update(h, data)
            hashes[suite][str(length)] = h.hexdigest()
            donor_hashes[suite][str(length)] = hashlib.sha256(permutation.tobytes()).hexdigest()
            references[suite][str(length)] = baseline.score(worlds.functional_reference(data), data)
            for readout in READOUTS:
                for method in METHODS:
                    record = metadata[readout][method]
                    cache = {}
                    for budget in config["budgets"]:
                        for policy in POLICIES:
                            step = record["selection"][str(budget)][policy]["step"]
                            if step not in cache:
                                model = models.Small(candidates[readout][method][step], readout)
                                cache[step] = {
                                    "intact": baseline.score(baseline.predictions(model, data), data),
                                    "no_memory": baseline.score(baseline.predictions(model, data, no_memory=True), data),
                                    "donor_history": baseline.score(baseline.predictions(model, donors), data)}
                            cell = record["policies"][policy]["budgets"][str(budget)]
                            for kind, values in cache[step].items():
                                cell[kind].setdefault(suite, {})[str(length)] = values
        print(json.dumps({"evaluated": suite, "replicate": seed}), flush=True)
    return hashes, donor_hashes, references


def run(out, seed, protocol):
    manifest = validate(protocol)
    if seed not in range(CONFIG["replicates"]):
        raise ValueError("Unknown replicate")
    baseline.configure()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"manifest.json", manifest)
    bank = make_bank(seed, CONFIG)
    candidates, metadata = {}, {}
    readout_order = READOUTS if seed % 2 == 0 else READOUTS[::-1]
    started = time.perf_counter()
    for readout in readout_order:
        candidates[readout], metadata[readout] = {}, {}
        for method in METHODS:
            candidates[readout][method], metadata[readout][method] = train(
                seed, CONFIG, out/readout, readout, method, bank)
    for field in ("training_stream_sha256", "bank_sha256", "validation_sha256"):
        if len({m[field] for arm in metadata.values() for m in arm.values()}) != 1:
            raise ValueError("Unmatched data: "+field)
    # All policy choices are fixed before any holdout generation or scoring.
    write_json(out/"selection-before-evaluation.json", {
        r: {m: record["selection"] for m, record in arm.items()} for r, arm in metadata.items()})
    hashes, donor_hashes, references = evaluate(seed, candidates, metadata, protocol, CONFIG)
    weights = {str(b): {r: {m: {p: {"theta": candidates[r][m][metadata[r][m]["selection"][str(b)][p]["step"]].tolist()}
                               for p in POLICIES} for m in METHODS} for r in READOUTS} for b in CONFIG["budgets"]}
    write_json(out/"final-weights.json", {"replicate": seed, "config_sha256": manifest["config_sha256"], "models": weights})
    row = {"version": VERSION, "replicate": seed, "config_sha256": manifest["config_sha256"],
           "source_hashes": manifest["source_hashes"], "models": metadata, "seeds": seeds_for(seed),
           "evaluation_hashes": hashes, "donor_permutation_hashes": donor_hashes, "references": references,
           "bank_order_sha256": hashlib.sha256(bank[2].tobytes()).hexdigest(),
           "elapsed_seconds": time.perf_counter()-started, "api_cost_usd": 0}
    write_json(out/f"result-seed-{seed}.json", row)
    print(json.dumps({"completed": seed, "elapsed_seconds": row["elapsed_seconds"]}), flush=True)


def score(row, readout, method, suite, budget, policy, kind, metric, lengths=None):
    cells = row["models"][readout][method]["policies"][policy]["budgets"][str(budget)][kind][suite]
    return float(np.mean([cells[str(n)][metric] for n in (CONFIG["primary_lengths"] if lengths is None else lengths)]))


def contrasts(row):
    values = {}
    for suite in SUITES:
        for method in METHODS:
            for readout in READOUTS:
                for metric in (("choice_brier",) if suite == "external_games" else ("choice_brier", "execution_brier")):
                    prefix = f"{suite}/{method}/{readout}/{metric}/"
                    def get(b, p, k="intact", s=suite, m=method, a=readout, metric_name=metric):
                        return score(row, a, m, s, b, p, k, metric_name)
                    for b, label in ((512, "low"), (2048, "high")):
                        for policy, short in (("guarded_choice", "guarded"), ("raw_last", "raw")):
                            values[prefix+label+"_joint_minus_"+short] = get(b, "joint")-get(b, policy)
                            values[prefix+label+"_"+short+"_minus_joint_donor_gain"] = (
                                get(b, policy, "donor_history")-get(b, policy)
                                -get(b, "joint", "donor_history")+get(b, "joint"))
                        for policy in POLICIES:
                            for kind, effect in (("donor_history", "donor_gain"), ("no_memory", "memory_gain")):
                                values[prefix+policy+"/"+label+"_"+effect] = get(b, policy, kind)-get(b, policy)
                    for policy in POLICIES:
                        values[prefix+policy+"/low_minus_high"] = get(512, policy)-get(2048, policy)
                        values[prefix+policy+"/donor_gain_growth"] = (
                            get(2048, policy, "donor_history")-get(2048, policy)
                            -get(512, policy, "donor_history")+get(512, policy))
    # Prospective secondary replication of the preceding exploratory, same-length contrast.
    growth = {}
    for policy in ("joint", "raw_last"):
        benefits = [score(row, "interaction", "evolved", "canonical_seen", b, policy,
                          "donor_history", "choice_brier", [24])
                    -score(row, "interaction", "evolved", "canonical_seen", b, policy,
                           "intact", "choice_brier", [24]) for b in (512, 2048)]
        growth[policy] = benefits[1]-benefits[0]
        values["raw_replication_24/"+policy+"_donor_growth"] = growth[policy]
    values["raw_replication_24/raw_minus_joint_donor_growth"] = growth["raw_last"]-growth["joint"]
    return values


def primary_rules():
    prefix = "canonical_seen/evolved/interaction/"
    return {prefix+"choice_brier/high_joint_minus_guarded": 0.,
            prefix+"choice_brier/high_guarded_minus_joint_donor_gain": 0.,
            prefix+"choice_brier/guarded_choice/high_donor_gain": 0.,
            prefix+"execution_brier/guarded_choice/high_donor_gain": 0.,
            prefix+"execution_brier/high_joint_minus_guarded": -CONFIG["execution_noninferiority_margin"]}


def estimate(values):
    a = np.asarray(values, dtype=np.float64)
    indices = np.random.default_rng(248000000).integers(0, len(a), (10000, len(a)))
    return {"mean": float(a.mean()), "paired_bootstrap_95ci": np.quantile(a[indices].mean(1), [.025, .975]).tolist(),
            "run_differences": a.tolist()}


def aggregate(inputs, out, protocol):
    manifest = validate(protocol)
    rows = [json.loads(p.read_text()) for p in sorted(inputs.rglob("result-seed-*.json"))]
    if [r["replicate"] for r in rows] != list(range(CONFIG["replicates"])):
        raise ValueError("Missing, duplicate or unordered replicates")
    for row in rows:
        if row["config_sha256"] != manifest["config_sha256"] or row["source_hashes"] != manifest["source_hashes"]:
            raise ValueError("Mixed protocols")
        if row["seeds"] != seeds_for(row["replicate"]):
            raise ValueError("Unexpected seeds")
        for readout in READOUTS:
            for method in METHODS:
                record = row["models"][readout][method]
                for b in CONFIG["budgets"]:
                    choices = record["selection"][str(b)]
                    pool = record["selection_pools"][str(b)]
                    if pool["candidate_count"] != 513 or choices["raw_last"]["step"] != b:
                        raise ValueError("Invalid selection pool")
                    if choices["guarded_choice"]["execution"] > pool["development_execution_limit"]:
                        raise ValueError("Execution guard failed")
                    if choices["guarded_choice"]["choice"] > choices["joint"]["choice"]:
                        raise ValueError("Choice selection failed")
    differences = [contrasts(r) for r in rows]
    effects = {k: estimate([d[k] for d in differences]) for k in differences[0]}
    criteria = primary_rules()
    decisions = {k: effects[k]["paired_bootstrap_95ci"][0] > limit for k, limit in criteria.items()}
    cells = {s: {str(b): {r: {m: {p: {
        "choice_brier": float(np.mean([score(row, r, m, s, b, p, "intact", "choice_brier") for row in rows])),
        "execution_brier": None if s == "external_games" else float(np.mean([
            score(row, r, m, s, b, p, "intact", "execution_brier") for row in rows])),
        "selected_steps": [row["models"][r][m]["selection"][str(b)][p]["step"] for row in rows]}
        for p in POLICIES} for m in METHODS} for r in READOUTS} for b in CONFIG["budgets"]} for s in SUITES}
    summary = {"version": VERSION, "replicates": len(rows), "training_trajectories": 32,
               "policy_budget_model_records": 192, "final_scores": cells, "contrasts": effects,
               "joint_primary_criteria": criteria, "primary_decisions": decisions,
               "joint_primary_pass": all(decisions.values()), "config_sha256": manifest["config_sha256"],
               "source_hashes": manifest["source_hashes"], "api_cost_usd": 0}
    out.mkdir(parents=True, exist_ok=False)
    for name, value in (("summary.json", summary), ("replicate-results.json", rows), ("manifest.json", manifest)):
        write_json(out/name, value)
    lines = ["# Checkpoint-selection pilot", "", f"Primary conjunction: {summary['joint_primary_pass']}.",
             f"Requirements passed: {sum(decisions.values())}/5. Eight paired fresh runs; no API calls.", "",
             "| Requirement | Mean | 95% interval | Pass |", "|---|---:|---|---|"]
    for key, passed in decisions.items():
        e = effects[key]
        lines.append(f"| {key} | {e['mean']:+.6f} | {e['paired_bootstrap_95ci']} | {passed} |")
    (out/"README.md").write_text("\n".join(lines)+"\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as f:
            f.write("\n".join(lines)+"\n")
    print("SUMMARY_JSON:"+json.dumps(summary, separators=(",", ":")), flush=True)


def freeze(out, upstream):
    external.verify(upstream)
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        shutil.copyfile(HERE/name, out/name)
    shutil.copytree(upstream, out/"upstream")
    manifest = {"version": VERSION, "config": CONFIG, "config_sha256": digest(CONFIG),
                "source_hashes": {n: hashlib.sha256((out/n).read_bytes()).hexdigest() for n in FILES},
                "predecessor": PREDECESSOR, "merged_baseline": MERGED_BASELINE,
                "external_commit": external.COMMIT, "external_sha256": external.HASHES,
                "seed_plan": [seeds_for(s) for s in range(CONFIG["replicates"])],
                "bootstrap_seed": 248000000, "python": platform.python_version(),
                "numpy": np.__version__, "torch": torch.__version__, "github_sha": os.environ.get("GITHUB_SHA"),
                "api_cost_usd": 0, "status": "frozen before training and holdout evaluation"}
    write_json(out/"manifest.json", manifest)


def validate(protocol):
    manifest = json.loads((protocol/"manifest.json").read_text())
    if HERE.resolve() != protocol.resolve():
        raise ValueError("Execute frozen source")
    for name, expected in manifest["source_hashes"].items():
        if hashlib.sha256((protocol/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source mismatch: "+name)
    if manifest["config"] != CONFIG or manifest["config_sha256"] != digest(CONFIG):
        raise ValueError("Config mismatch")
    if manifest["numpy"] != np.__version__ or manifest["torch"] != torch.__version__:
        raise ValueError("Runtime mismatch")
    external.verify(protocol/"upstream")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "aggregate"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--protocol", type=Path, default=HERE)
    parser.add_argument("--upstream", type=Path)
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.out, args.upstream)
    elif args.command == "run":
        run(args.out, args.seed, args.protocol)
    else:
        aggregate(args.inputs, args.out, args.protocol)


if __name__ == "__main__":
    main()
