"""Learned shared versus differentiated updates; no API calls."""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import os
import platform
import shutil
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
VERSION = "memory-ecology-v1.0"
CONFIG = {"replicates": 8, "updates": 1024, "batch_size": 64, "train_length": 32,
          "evaluation_length": 64, "evaluation_lifetimes": 1024, "widths": [2, 12],
          "checkpoints": [0, 64, 256, 1024], "learning_rate": 0.003,
          "hazard": 0.08, "observation_error": 0.15, "clip_norm": 1.0}
METHODS = ("shared", "separate")
ECOLOGIES = {"stable": 1.0, "changing": 0.0, "mixed": 0.5}
FAMILIES = ("stable_rate", "hidden_state")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sequences(rng, batch, length, hazard=0.08, error=0.15, stable_prior=0.5):
    """length predictions require length+1 observations. No metadata is part of the input."""
    if batch % 2:
        raise ValueError("Use balanced even batches")
    if stable_prior not in (0.0, 0.5, 1.0):
        raise ValueError("Unknown ecology")
    stable_count = int(batch*stable_prior)
    family = np.concatenate((np.zeros(stable_count, dtype=int), np.ones(batch-stable_count, dtype=int)))
    rng.shuffle(family)
    theta = rng.random(batch)
    state = rng.integers(0, 2, batch).astype(bool)
    observations = np.empty((batch, length+1), dtype=np.float32)
    for t in range(length+1):
        if t:
            state ^= rng.random(batch) < hazard
        probability = np.where(family == 0, theta, error+(1-2*error)*state)
        observations[:, t] = rng.random(batch) < probability
    return observations, family


def bayes_mixture(observations, hazard=0.08, error=0.15, stable_prior=0.5):
    """Exact next-observation predictor integrating unknown family and latent rate/state."""
    batch, length = observations.shape
    result = np.empty((batch, length), dtype=np.float64)
    successes = np.zeros(batch)
    posterior_state = np.full(batch, 0.5)
    log_odds = np.zeros(batch)
    for t in range(length):
        y = observations[:, t]
        static_before = (1+successes)/(2+t)
        prior_state = np.full(batch, 0.5) if t == 0 else hazard+(1-2*hazard)*posterior_state
        dynamic_before = error+(1-2*error)*prior_state
        static_likelihood = np.where(y == 1, static_before, 1-static_before)
        dynamic_likelihood = np.where(y == 1, dynamic_before, 1-dynamic_before)
        log_odds += np.log(static_likelihood)-np.log(dynamic_likelihood)
        posterior_state = prior_state*np.where(y == 1, 1-error, error)/dynamic_likelihood
        successes += y
        static_after = (1+successes)/(3+t)
        dynamic_after = error+(1-2*error)*(hazard+(1-2*hazard)*posterior_state)
        weight = 1/(1+np.exp(-np.clip(log_odds, -700, 700)))
        if stable_prior == 1.0:
            result[:, t] = static_after
        elif stable_prior == 0.0:
            result[:, t] = dynamic_after
        elif stable_prior == 0.5:
            result[:, t] = weight*static_after+(1-weight)*dynamic_after
        else:
            raise ValueError("Unknown ecology")
    return result


def brute_prediction(prefix, hazard=0.08, error=0.15, stable_prior=0.5):
    """Independent enumeration used only by development tests."""
    n, s = len(prefix), sum(prefix)
    static_likelihood = math.factorial(s)*math.factorial(n-s)/math.factorial(n+1)
    static_joint = math.factorial(s+1)*math.factorial(n-s)/math.factorial(n+2)
    dynamic_likelihood, dynamic_joint = 0.0, 0.0
    for states in itertools.product((0, 1), repeat=n+1):
        probability = 0.5
        for t in range(1, n+1):
            probability *= 1-hazard if states[t] == states[t-1] else hazard
        for t, y in enumerate(prefix):
            probability *= 1-error if y == states[t] else error
        dynamic_likelihood += probability
        dynamic_joint += probability*((1-error) if states[-1] else error)
    return (stable_prior*static_joint+(1-stable_prior)*dynamic_joint)/(stable_prior*static_likelihood+(1-stable_prior)*dynamic_likelihood)



class Learner(nn.Module):
    """Same input, state banks, heads and gate; only the recurrent weights are tied/untied."""
    def __init__(self, method, hidden):
        super().__init__()
        if method not in METHODS:
            raise ValueError("Unknown method")
        self.method, self.hidden = method, hidden
        common = nn.GRU(3, hidden, batch_first=True)
        self.cells = nn.ModuleList([common] if method == "shared" else
                                   [common, copy.deepcopy(common)])
        self.heads = nn.ModuleList([nn.Linear(hidden, 1) for _ in range(2)])
        self.gate = nn.Linear(2*hidden, 2)

    def forward(self, x):
        batch, length, _ = x.shape
        banks = torch.eye(2, dtype=x.dtype, device=x.device)[:, None, None, :].expand(2, batch, length, 2)
        paired = x.unsqueeze(0).expand(2, batch, length, 1)
        inputs = torch.cat((paired, banks), dim=-1)
        if self.method == "shared":
            combined, _ = self.cells[0](inputs.reshape(2*batch, length, 3))
            states = list(combined.reshape(2, batch, length, self.hidden).unbind(0))
        else:
            states = [cell(inputs[i])[0] for i, cell in enumerate(self.cells)]
        experts = torch.cat([head(state).sigmoid() for head, state in zip(self.heads, states)], dim=-1)
        gates = self.gate(torch.cat(states, dim=-1)).softmax(dim=-1)
        return {"prediction": (gates*experts).sum(dim=-1), "experts": experts, "gates": gates}


def resources(model):
    h = model.hidden
    return {"parameters": sum(p.numel() for p in model.parameters()), "state_values": 2*h,
            "approx_forward_matrix_macs_per_observation": 2*3*h*(3+h)+6*h}


def configure():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def seed_plan(seed, ecology, hidden):
    i = list(ECOLOGIES).index(ecology)
    return {"initialization": 81000000+1000*seed+100*i+hidden,
            "training": 82000000+1000*seed+100*i,
            "evaluation": 84000000+1000*seed+100*i}


def train(method, seed, config, out, hidden, ecology):
    seeds = seed_plan(seed, ecology, hidden)
    torch.manual_seed(seeds["initialization"])
    model = Learner(method, hidden)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    rng = np.random.default_rng(seeds["training"])
    stream_hash = hashlib.sha256()
    snapshots, logs = {}, []
    start = time.perf_counter()
    for update in range(config["updates"]+1):
        if update in config["checkpoints"]:
            snapshots[update] = copy.deepcopy(model.state_dict())
            torch.save(snapshots[update], out/f"{method}-update-{update}.pt")
        if update == config["updates"]:
            break
        observations, _ = sequences(rng, config["batch_size"], config["train_length"],
            config["hazard"], config["observation_error"], ECOLOGIES[ecology])
        stream_hash.update(observations.tobytes())
        x = torch.from_numpy(observations[:, :-1, None].copy())
        y = torch.from_numpy(observations[:, 1:].copy())
        optimizer.zero_grad(set_to_none=True)
        p = model(x)["prediction"].clamp(1e-6, 1-1e-6)
        loss = nn.functional.binary_cross_entropy(p, y)
        if not torch.isfinite(loss):
            raise ValueError("Nonfinite training loss")
        loss.backward()
        gradient = nn.utils.clip_grad_norm_(model.parameters(), config["clip_norm"])
        if not torch.isfinite(gradient):
            raise ValueError("Nonfinite gradient")
        optimizer.step()
        if (update+1) % 64 == 0:
            logs.append({"update": update+1, "batch_bce": float(loss.detach())})
    elapsed = time.perf_counter()-start
    print(json.dumps({"seed": seed, "ecology": ecology, "hidden": hidden,
                      "method": method, "training_complete": True, "seconds": elapsed}), flush=True)
    return model, snapshots, {"training_seconds": elapsed, "resources": resources(model),
        "training_stream_sha256": stream_hash.hexdigest(), "training_log": logs, "seeds": seeds}


def evaluate(model, observations, families, config, ecology):
    oracle = bayes_mixture(observations[:, :-1], config["hazard"],
                          config["observation_error"], ECOLOGIES[ecology])
    model.eval()
    with torch.no_grad():
        result = model(torch.from_numpy(observations[:, :-1, None].copy()))
    p = result["prediction"].cpu().numpy().astype(np.float64)
    excess = (p-oracle)**2
    n = config["train_length"]
    return {"excess_brier": float(excess[:, :n].mean()),
            "observed_brier": float(((p-observations[:, 1:])**2)[:, :n].mean()),
            "longer_history_excess": float(excess[:, n:].mean()) if p.shape[1] > n else None,
            "family_excess": {name: float(excess[families == i, :n].mean()) if np.any(families == i) else None
                              for i, name in enumerate(FAMILIES)},
            "lifetime_curve_excess": excess.mean(axis=0).tolist()}


def freeze(out):
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for source, name in ((Path(__file__), "experiment.py"), (HERE/"README.md", "protocol.md"),
                         (HERE/"requirements.txt", "requirements.txt")):
        shutil.copyfile(source, out/name)
        hashes[name] = hashlib.sha256((out/name).read_bytes()).hexdigest()
    manifest = {"version": VERSION, "config": CONFIG, "ecologies": ECOLOGIES, "source_hashes": hashes,
        "config_sha256": digest({"config": CONFIG, "ecologies": ECOLOGIES}),
        "torch": torch.__version__, "numpy": np.__version__, "python": platform.python_version(),
        "github_sha": os.environ.get("GITHUB_SHA"), "api_cost_usd": 0,
        "seed_plan": [{"replicate": i, "ecology": ecology, "hidden": h, **seed_plan(i, ecology, h)}
                      for i in range(CONFIG["replicates"]) for ecology in ECOLOGIES for h in CONFIG["widths"]],
        "status": "prospectively frozen before study training/evaluation"}
    write_json(out/"manifest.json", manifest)
    print("FROZEN_JSON:"+json.dumps(manifest), flush=True)


def validate(protocol):
    manifest = json.loads((protocol/"manifest.json").read_text())
    for name, expected in manifest["source_hashes"].items():
        if hashlib.sha256((protocol/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source mismatch: "+name)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != manifest["source_hashes"]["experiment.py"]:
        raise ValueError("Run the frozen source")
    if digest({"config": manifest["config"], "ecologies": manifest["ecologies"]}) != manifest["config_sha256"]:
        raise ValueError("Config hash mismatch")
    if manifest["ecologies"] != ECOLOGIES or manifest["config"] != CONFIG:
        raise ValueError("Executable configuration differs")
    if torch.__version__ != manifest["torch"] or np.__version__ != manifest["numpy"]:
        raise ValueError("Dependency version mismatch")
    return manifest


def run(out, seed, protocol):
    manifest = validate(protocol)
    config = manifest["config"]
    if seed not in range(config["replicates"]):
        raise ValueError("Unknown replicate")
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"manifest.json", manifest)
    configure()
    start = time.perf_counter()
    conditions = [(eco, h) for eco in ECOLOGIES for h in config["widths"]]
    shift = seed % len(conditions)
    conditions = conditions[shift:]+conditions[:shift]
    trained, order = {}, []
    for j, (eco, h) in enumerate(conditions):
        key = f"{eco}-h{h}"
        folder = out/key
        folder.mkdir()
        trained[key] = {}
        for method in (METHODS if (seed+j) % 2 == 0 else METHODS[::-1]):
            order.append([eco, h, method])
            trained[key][method] = train(method, seed, config, folder, h, eco)
    # No evaluation data are generated until all twelve models in this replicate finish training.
    for eco in ECOLOGIES:
        hashes = {trained[f"{eco}-h{h}"][m][2]["training_stream_sha256"]
                  for h in config["widths"] for m in METHODS}
        if len(hashes) != 1:
            raise ValueError("Unmatched data within ecology")
    evaluation_hashes, results = {}, {}
    for eco in ECOLOGIES:
        rng = np.random.default_rng(seed_plan(seed, eco, config["widths"][0])["evaluation"])
        obs, family = sequences(rng, config["evaluation_lifetimes"], config["evaluation_length"],
                               config["hazard"], config["observation_error"], ECOLOGIES[eco])
        evaluation_hashes[eco] = hashlib.sha256(obs.tobytes()).hexdigest()
        for h in config["widths"]:
            key = f"{eco}-h{h}"
            results[key] = {}
            for method in METHODS:
                model, snapshots, metadata = trained[key][method]
                checkpoints = {}
                for update in config["checkpoints"]:
                    model.load_state_dict(snapshots[update])
                    checkpoints[str(update)] = evaluate(model, obs, family, config, eco)
                metadata["checkpoints"] = checkpoints
                metadata["data_efficiency_excess"] = float(np.mean([
                    checkpoints[str(u)]["excess_brier"] for u in config["checkpoints"] if u > 0]))
                model.load_state_dict(snapshots[config["updates"]])
                metadata["inverted_symbols"] = evaluate(model, 1-obs, family, config, eco)
                results[key][method] = metadata
    result = {"version": VERSION, "replicate": seed, "config_sha256": manifest["config_sha256"],
        "source_hashes": manifest["source_hashes"], "training_order": order, "conditions": results,
        "evaluation_sha256": evaluation_hashes, "elapsed_seconds": time.perf_counter()-start, "api_cost_usd": 0}
    write_json(out/f"result-seed-{seed}.json", result)
    print("ROW_JSON:"+json.dumps({k: v for k, v in result.items() if k != "conditions"}, separators=(",", ":")), flush=True)
    for key, value in results.items():
        print("CONDITION_JSON:"+json.dumps({"condition": key, "models": value}, separators=(",", ":")), flush=True)


def bootstrap(values):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(85100000)
    means = rng.choice(values, size=(10000, len(values)), replace=True).mean(axis=1)
    return np.quantile(means, [0.025, 0.975]).tolist()


def contrasts_for_row(row):
    def difference(eco, h):
        pair = row["conditions"][f"{eco}-h{h}"]
        return pair["shared"]["data_efficiency_excess"]-pair["separate"]["data_efficiency_excess"]
    values = {}
    for h in CONFIG["widths"]:
        for eco in ECOLOGIES:
            values[f"sharing_penalty_{eco}_h{h}"] = difference(eco, h)
        values[f"ecology_interaction_h{h}"] = difference("mixed", h)-0.5*(
            difference("stable", h)+difference("changing", h))
    lo, hi = CONFIG["widths"]
    values["primary_memory_ecology_interaction"] = values[f"ecology_interaction_h{lo}"]-values[f"ecology_interaction_h{hi}"]
    return values


def aggregate(inputs, out, protocol):
    manifest = validate(protocol)
    rows = [json.loads(p.read_text()) for p in sorted(inputs.rglob("result-seed-*.json"))]
    if sorted(r["replicate"] for r in rows) != list(range(manifest["config"]["replicates"])):
        raise ValueError("Incomplete or duplicate replicates; no aggregate inference")
    for row in rows:
        if row["config_sha256"] != manifest["config_sha256"] or row["source_hashes"] != manifest["source_hashes"]:
            raise ValueError("Mixed protocols")
        for eco in ECOLOGIES:
            if len({row["conditions"][f"{eco}-h{h}"][m]["training_stream_sha256"]
                    for h in CONFIG["widths"] for m in METHODS}) != 1:
                raise ValueError("Unmatched training")
    out.mkdir(parents=True, exist_ok=False)
    final, cells = str(CONFIG["updates"]), {}
    for key in rows[0]["conditions"]:
        cells[key] = {}
        for method in METHODS:
            models = [row["conditions"][key][method] for row in rows]
            cells[key][method] = {
                "mean_data_efficiency_excess": float(np.mean([m["data_efficiency_excess"] for m in models])),
                "mean_final_excess": float(np.mean([m["checkpoints"][final]["excess_brier"] for m in models])),
                "mean_final_longer_history_excess": float(np.mean([m["checkpoints"][final]["longer_history_excess"] for m in models])),
                "mean_training_seconds": float(np.mean([m["training_seconds"] for m in models])),
                "checkpoint_means": {str(u): float(np.mean([m["checkpoints"][str(u)]["excess_brier"] for m in models]))
                                     for u in CONFIG["checkpoints"]},
                "resources": models[0]["resources"]}
    paired = [contrasts_for_row(r) for r in rows]
    contrasts = {}
    for name in paired[0]:
        v = [p[name] for p in paired]
        contrasts[name] = {"mean": float(np.mean(v)), "paired_bootstrap_95ci": bootstrap(v), "run_differences": v}
    summary = {"version": VERSION, "replicates": len(rows), "conditions": cells, "contrasts": contrasts,
        "primary_contrast": "primary_memory_ecology_interaction", "api_cost_usd": 0,
        "config_sha256": manifest["config_sha256"], "source_hashes": manifest["source_hashes"],
        "interpretation": "Positive primary interaction means heterogeneity penalizes sharing more at small memory; conditional, exploratory architecture evidence, not proof of necessary functional specialization."}
    write_json(out/"summary.json", summary)
    write_json(out/"replicate-results.json", rows)
    write_json(out/"manifest.json", manifest)
    lines = ["# Memory by ecology comparison", "", "Eight paired replicates; 96 trained models; $0 API cost.", "",
        "| Ecology / branch width | Shared error | Separate error | Shared minus separate |",
        "|---|---:|---:|---:|"]
    for key, pair in cells.items():
        s = pair["shared"]["mean_data_efficiency_excess"]
        u = pair["separate"]["mean_data_efficiency_excess"]
        lines.append(f"| {key} | {s:.7f} | {u:.7f} | {s-u:+.7f} |")
    lines += ["", "Prespecified primary interaction: "+json.dumps(contrasts[summary["primary_contrast"]]), "",
        "Identical state budgets, forward matrix arithmetic, initial predictions, data and optimizer steps within each comparison. Untying weights adds trainable parameters. Homogeneous controls estimate a generic untying advantage but do not make this a parameter-matched comparison.",
        "", "Final checkpoints, long histories and symbol inversion are secondary. No independent expert-role or mechanism claim follows from performance."]
    report = "\n".join(lines)+"\n"
    (out/"README.md").write_text(report)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as f:
            f.write(report)
    print("SUMMARY_JSON:"+json.dumps(summary, separators=(",", ":")), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "aggregate"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--protocol", type=Path, default=HERE)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.out)
    elif args.command == "run":
        run(args.out, args.seed, args.protocol)
    else:
        if args.inputs is None:
            parser.error("--inputs is required for aggregate")
        aggregate(args.inputs, args.out, args.protocol)


if __name__ == "__main__":
    main()
