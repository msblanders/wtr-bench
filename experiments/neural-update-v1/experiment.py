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
VERSION = "neural-update-v1.0"
CONFIG = {"replicates": 8, "updates": 1024, "batch_size": 64, "train_length": 32,
          "evaluation_length": 64, "evaluation_lifetimes": 1024, "validation_lifetimes": 512,
          "checkpoints": [0, 64, 256, 1024], "learning_rate": 0.003,
          "hazard": 0.08, "observation_error": 0.15, "clip_norm": 1.0}
METHODS = ("dense", "routed", "shared")
FAMILIES = ("stable_rate", "hidden_state")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sequences(rng, batch, length, hazard=0.08, error=0.15):
    """length predictions require length+1 observations. No metadata is part of the input."""
    if batch % 2:
        raise ValueError("Use balanced even batches")
    family = np.repeat(np.arange(2), batch//2)
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


def bayes_mixture(observations, hazard=0.08, error=0.15):
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
        result[:, t] = weight*static_after+(1-weight)*dynamic_after
    return result


def brute_prediction(prefix, hazard=0.08, error=0.15):
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
    return (static_joint+dynamic_joint)/(static_likelihood+dynamic_likelihood)


class Learner(nn.Module):
    def __init__(self, method):
        super().__init__()
        self.method = method
        if method == "dense":
            self.hidden = 18
            self.cells = nn.ModuleList([nn.GRU(1, 18, batch_first=True)])
            self.heads = nn.ModuleList([nn.Linear(18, 1)])
        elif method == "routed":
            self.hidden = 12
            self.cells = nn.ModuleList([nn.GRU(1, 12, batch_first=True) for _ in range(2)])
            self.heads = nn.ModuleList([nn.Linear(12, 1) for _ in range(2)])
            self.gate = nn.Linear(24, 2)
        elif method == "shared":
            self.hidden = 17
            self.cells = nn.ModuleList([nn.GRU(3, 17, batch_first=True)])
            self.heads = nn.ModuleList([nn.Linear(17, 1)])
            self.gate = nn.Linear(34, 2)
        else:
            raise ValueError("Unknown method")

    def forward(self, x, force_gate=None):
        if self.method == "dense":
            state, _ = self.cells[0](x)
            p = self.heads[0](state).squeeze(-1).sigmoid()
            return {"prediction": p}
        if self.method == "routed":
            states = [cell(x)[0] for cell in self.cells]
            experts = torch.cat([head(state).sigmoid() for head, state in zip(self.heads, states)], dim=-1)
        else:
            batch, length, _ = x.shape
            bank = torch.eye(2, dtype=x.dtype, device=x.device)[:, None, None, :].expand(2, batch, length, 2)
            paired = x.unsqueeze(0).expand(2, batch, length, 1)
            inputs = torch.cat((paired, bank), dim=-1).reshape(2*batch, length, 3)
            combined, _ = self.cells[0](inputs)
            states = list(combined.reshape(2, batch, length, self.hidden).unbind(0))
            experts = torch.cat([self.heads[0](state).sigmoid() for state in states], dim=-1)
        gates = self.gate(torch.cat(states, dim=-1)).softmax(dim=-1)
        if force_gate == "uniform":
            gates = torch.full_like(gates, 0.5)
        elif force_gate in (0, 1):
            gates = torch.zeros_like(gates)
            gates[..., force_gate] = 1
        return {"prediction": (gates*experts).sum(dim=-1), "gates": gates, "experts": experts}


def resources(model):
    h = model.hidden
    if model.method == "dense":
        macs, state = 3*h*(1+h)+h, h
    elif model.method == "routed":
        macs, state = 2*3*h*(1+h)+2*h+4*h, 2*h
    else:
        macs, state = 2*3*h*(3+h)+2*h+4*h, 2*h
    return {"parameters": sum(p.numel() for p in model.parameters()), "state_values": state,
            "approx_forward_matrix_macs_per_observation": macs}


def configure():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def train(method, seed, config, out):
    torch.manual_seed(7100000+seed)
    model = Learner(method)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    rng = np.random.default_rng(7200000+seed)
    stream_hash = hashlib.sha256()
    snapshots = {}
    logs = []
    start = time.perf_counter()
    for update in range(config["updates"]+1):
        if update in config["checkpoints"]:
            snapshots[update] = copy.deepcopy(model.state_dict())
            torch.save(snapshots[update], out/f"{method}-update-{update}.pt")
        if update == config["updates"]:
            break
        observations, _ = sequences(rng, config["batch_size"], config["train_length"],
                                    config["hazard"], config["observation_error"])
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
            print(json.dumps({"seed": seed, "model": method, **logs[-1]}), flush=True)
    return model, snapshots, {"training_seconds": time.perf_counter()-start,
        "training_stream_sha256": stream_hash.hexdigest(), "resources": resources(model), "training_log": logs}


def score(prediction, oracle, outcomes, families, main_length):
    p = prediction.detach().cpu().numpy().astype(np.float64)
    excess = (p-oracle)**2
    brier = (p-outcomes)**2
    main = slice(0, main_length)
    return {"excess_brier": float(excess[:, main].mean()),
            "observed_brier": float(brier[:, main].mean()),
            "longer_history_excess": float(excess[:, main_length:].mean()) if p.shape[1] > main_length else None,
            "family_excess": {name: float(excess[families == i, main].mean()) for i, name in enumerate(FAMILIES)},
            "lifetime_curve_excess": excess.mean(axis=0).tolist()}


def evaluate(model, observations, families, config, force_gate=None, inverted=False):
    obs = 1-observations if inverted else observations
    oracle = bayes_mixture(obs[:, :-1], config["hazard"], config["observation_error"])
    model.eval()
    with torch.no_grad():
        result = model(torch.from_numpy(obs[:, :-1, None].copy()), force_gate=force_gate)
    scores = score(result["prediction"], oracle, obs[:, 1:], families, config["train_length"])
    if "gates" in result:
        gates = result["gates"].cpu().numpy()
        scores["mean_gate_by_family"] = {
            name: gates[families == i, :config["train_length"]].mean(axis=(0, 1)).tolist()
            for i, name in enumerate(FAMILIES)}
    return scores


def freeze(out):
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for source, name in ((Path(__file__), "experiment.py"), (HERE/"README.md", "protocol.md"),
                         (HERE/"requirements.txt", "requirements.txt")):
        shutil.copyfile(source, out/name)
        hashes[name] = hashlib.sha256((out/name).read_bytes()).hexdigest()
    manifest = {"version": VERSION, "config": CONFIG, "source_hashes": hashes,
        "config_sha256": digest(CONFIG), "torch": torch.__version__, "numpy": np.__version__,
        "python": platform.python_version(), "github_sha": os.environ.get("GITHUB_SHA"),
        "seed_plan": [{"replicate": i, "initialization": 7100000+i, "training": 7200000+i,
                       "validation": 7300000+i, "evaluation": 7400000+i} for i in range(CONFIG["replicates"])],
        "status": "prospectively frozen before neural training/evaluation", "api_cost_usd": 0}
    write_json(out/"manifest.json", manifest)
    print("FROZEN_JSON:"+json.dumps(manifest), flush=True)


def validate(protocol):
    manifest = json.loads((protocol/"manifest.json").read_text())
    for name, expected in manifest["source_hashes"].items():
        if hashlib.sha256((protocol/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source mismatch: "+name)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != manifest["source_hashes"]["experiment.py"]:
        raise ValueError("Run the frozen source")
    if digest(manifest["config"]) != manifest["config_sha256"]:
        raise ValueError("Config hash mismatch")
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
    trained = {}
    order = METHODS[seed % 3:]+METHODS[:seed % 3]
    for method in order:
        trained[method] = train(method, seed, config, out)
    hashes = {v[2]["training_stream_sha256"] for v in trained.values()}
    if len(hashes) != 1:
        raise ValueError("Training streams differ")
    # No evaluation sequence is generated until all three models finish every scheduled update.
    validation, vf = sequences(np.random.default_rng(7300000+seed), config["validation_lifetimes"],
                               config["train_length"], config["hazard"], config["observation_error"])
    evaluation, ef = sequences(np.random.default_rng(7400000+seed), config["evaluation_lifetimes"],
                               config["evaluation_length"], config["hazard"], config["observation_error"])
    results = {}
    for method in METHODS:
        model, snapshots, metadata = trained[method]
        checkpoints = {}
        for update in config["checkpoints"]:
            model.load_state_dict(snapshots[update])
            checkpoints[str(update)] = evaluate(model, evaluation, ef, config)
        final = config["updates"]
        model.load_state_dict(snapshots[final])
        metadata["checkpoints"] = checkpoints
        metadata["data_efficiency_excess"] = float(np.mean([
            checkpoints[str(u)]["excess_brier"] for u in config["checkpoints"] if u > 0]))
        metadata["inverted_symbols"] = evaluate(model, evaluation, ef, config, inverted=True)
        if method != "dense":
            v0 = evaluate(model, validation, vf, config, force_gate=0)["family_excess"]
            v1 = evaluate(model, validation, vf, config, force_gate=1)["family_excess"]
            normal = v0["stable_rate"]+v1["hidden_state"]
            reversed_assignment = v1["stable_rate"]+v0["hidden_state"]
            metadata["validation_expert_assignment"] = {
                "stable_rate": 0 if normal <= reversed_assignment else 1,
                "hidden_state": 1 if normal <= reversed_assignment else 0}
            metadata["interventions"] = {
                str(g): evaluate(model, evaluation, ef, config, force_gate=g)
                for g in ("uniform", 0, 1)}
        results[method] = metadata
    result = {"version": VERSION, "replicate": seed, "config_sha256": manifest["config_sha256"],
        "source_hashes": manifest["source_hashes"], "training_order": order, "models": results,
        "evaluation_sha256": hashlib.sha256(evaluation.tobytes()).hexdigest(),
        "validation_sha256": hashlib.sha256(validation.tobytes()).hexdigest(),
        "elapsed_seconds": time.perf_counter()-start, "api_cost_usd": 0}
    write_json(out/f"result-seed-{seed}.json", result)
    print("RESULT_JSON:"+json.dumps(result, separators=(",", ":")), flush=True)


def bootstrap(values):
    rng = np.random.default_rng(7510000)
    values = np.asarray(values, dtype=np.float64)
    means = rng.choice(values, size=(4000, len(values)), replace=True).mean(axis=1)
    return np.quantile(means, [0.025, 0.975]).tolist()


def aggregate(inputs, out, protocol):
    manifest = validate(protocol)
    rows = [json.loads(p.read_text()) for p in sorted(inputs.rglob("result-seed-*.json"))]
    if sorted(r["replicate"] for r in rows) != list(range(manifest["config"]["replicates"])):
        raise ValueError("Incomplete or duplicate replicates; no aggregate inference")
    for row in rows:
        if row["config_sha256"] != manifest["config_sha256"] or row["source_hashes"] != manifest["source_hashes"]:
            raise ValueError("Mixed protocols")
        if len({m["training_stream_sha256"] for m in row["models"].values()}) != 1:
            raise ValueError("Unmatched training")
    out.mkdir(parents=True, exist_ok=False)
    final = str(manifest["config"]["updates"])
    cells = {}
    for method in METHODS:
        cells[method] = {
            "mean_data_efficiency_excess": float(np.mean([r["models"][method]["data_efficiency_excess"] for r in rows])),
            "mean_final_excess": float(np.mean([r["models"][method]["checkpoints"][final]["excess_brier"] for r in rows])),
            "mean_final_longer_history_excess": float(np.mean([
                r["models"][method]["checkpoints"][final]["longer_history_excess"] for r in rows])),
            "resources": rows[0]["models"][method]["resources"],
            "mean_training_seconds": float(np.mean([r["models"][method]["training_seconds"] for r in rows]))}
    contrasts = {}
    for comparator in ("shared", "dense"):
        differences = [r["models"][comparator]["data_efficiency_excess"]-
                       r["models"]["routed"]["data_efficiency_excess"] for r in rows]
        contrasts[comparator+"_minus_routed"] = {"mean": float(np.mean(differences)),
            "paired_bootstrap_95ci": bootstrap(differences), "run_differences": differences}
    summary = {"version": VERSION, "replicates": len(rows), "models": cells, "contrasts": contrasts,
        "primary_contrast": "shared_minus_routed", "positive_difference_favors": "routed",
        "api_cost_usd": 0, "config_sha256": manifest["config_sha256"], "source_hashes": manifest["source_hashes"],
        "interpretation": "Learned recurrent update functions on two temporal inference problems; no claim of necessary physical modules or evolutionary-optimizer superiority."}
    write_json(out/"summary.json", summary)
    write_json(out/"replicate-results.json", rows)
    write_json(out/"manifest.json", manifest)
    lines = ["# Neural update comparison", "", "All eight paired training replicates completed. API cost: $0.", "",
             "Excess Brier loss is squared deviation from the optimal observable-history Bayesian mixture; lower is better.", "",
             "| Model | Data-efficiency mean | Final 32-step error | Longer-history error | Parameters |",
             "|---|---:|---:|---:|---:|"]
    for method, cell in cells.items():
        lines.append(f"| {method} | {cell['mean_data_efficiency_excess']:.6f} | {cell['mean_final_excess']:.6f} | {cell['mean_final_longer_history_excess']:.6f} | {cell['resources']['parameters']} |")
    lines += ["", "Primary paired contrast (shared minus routed): "+json.dumps(contrasts["shared_minus_routed"]), "",
        "The shared contextual learner has more parameters, state, and recurrent arithmetic. Data and weight-update budgets match; total FLOPs do not. The dense model is approximately parameter-matched. No holdout result selected checkpoints or training duration.", "",
        "The artifact includes full per-run metrics, routing diagnostics, source hashes and seed plans. Per-seed artifacts preserve all checkpoint weights."]
    report = "\n".join(lines)+"\n"
    (out/"report.md").write_text(report)
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
