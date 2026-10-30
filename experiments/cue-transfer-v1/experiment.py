"""Learn cue routing and test cross-context transfer from observed future outcomes."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import shutil
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
VERSION = "cue-transfer-v1.0"
CONFIG = {"replicates": 8, "updates": 1024, "batch_size": 64, "max_history": 24,
          "train_lengths": [0, 2, 8, 24], "test_lengths": [2, 8, 24],
          "checkpoints": [0, 64, 256, 1024], "evaluation_lifetimes": 1024,
          "diagnostic_lifetimes": 512, "learning_rate": 0.003, "clip_norm": 1.0, "criterion_excess": 0.002}
METHODS = ("functional", "history", "wrong_rules")
REGIMES = ("shared", "context_specific")
SUITES = {"canonical": [0.1, 0.9, 0.5], "reversed": [0.9, 0.1, 0.5],
          "assigned_only": [1.0, 1.0, 1.0], "voluntary_only": [0.0, 0.0, 0.0]}
CHANNELS = ("willingness", "ability")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def seed_plan(seed, regime):
    i = REGIMES.index(regime)
    return {"initialization": 101000000+1000*seed+100*i,
            "training": 102000000+1000*seed+100*i,
            "evaluation": 104000000+1000*seed+100*i,
            "diagnostics": 105000000+1000*seed+100*i}


def batch(rng, size, length, regime, suite="canonical", random_lengths=False):
    """One fresh partner per row; columns are voluntary, attempt, success, context one-hot."""
    if regime not in REGIMES:
        raise ValueError("Unknown regime")
    raw_w = rng.random((size, 3))
    w = np.repeat(raw_w[:, :1], 3, axis=1) if regime == "shared" else raw_w
    a = rng.random(size)
    heldout = rng.integers(0, 3, size)
    seen = np.stack(((heldout+1) % 3, (heldout+2) % 3), axis=1)
    selector = rng.integers(0, 2, (size, length))
    contexts = np.take_along_axis(seen, selector, axis=1)
    assignment_draw = rng.random((size, length))
    choice_draw, success_draw = rng.random((size, length)), rng.random((size, length))
    assigned = assignment_draw < np.asarray(SUITES[suite])[contexts]
    attempt = assigned | (choice_draw < np.take_along_axis(w, contexts, axis=1))
    success = attempt & (success_draw < a[:, None])
    x = np.concatenate(((~assigned)[..., None], attempt[..., None], success[..., None],
                        np.eye(3)[contexts]), axis=-1).astype(np.float32)
    lengths = rng.choice(CONFIG["train_lengths"], size=size) if random_lengths else np.full(size, length)
    if np.any(lengths > length):
        raise ValueError("Padding shorter than a requested history")
    x[np.arange(length)[None, :] >= lengths[:, None]] = 0
    truth = np.stack((w, np.broadcast_to(a[:, None], w.shape)), axis=-1)
    # Independent future voluntary-choice and guaranteed-attempt execution probes in all contexts.
    targets = (rng.random(truth.shape) < truth).astype(np.float32)
    return {"x": x, "lengths": lengths, "heldout": heldout, "truth": truth, "targets": targets}


def posterior(x, lengths, regime):
    """Known-regime exact Beta reference. No reference value enters training."""
    x = x.astype(np.float64)
    active = np.arange(x.shape[1])[None, :] < lengths[:, None]
    voluntary, attempt, success = (x[..., k] for k in range(3))
    wm = active*voluntary
    am = active*attempt
    if regime == "shared":
        wp = ((1+(wm*attempt).sum(1))/(2+wm.sum(1)))[:, None]
        wp = np.repeat(wp, 3, axis=1)
    elif regime == "context_specific":
        by_context = wm[..., None]*x[..., 3:]
        wp = (1+(by_context*attempt[..., None]).sum(1))/(2+by_context.sum(1))
    else:
        raise ValueError("Unknown regime")
    ap = (1+(am*success).sum(1))/(2+am.sum(1))
    return np.stack((wp, np.repeat(ap[:, None], 3, axis=1)), axis=-1).astype(np.float64)


def tensors(data):
    return torch.from_numpy(data["x"]), torch.from_numpy(data["lengths"]).long()


def filtered_inputs(x, lengths, wrong=False):
    """Compact the two observation streams; invalid events cannot enter a bank's state."""
    b, t, _ = x.shape
    active = torch.arange(t, device=x.device)[None, :] < lengths[:, None]
    masks = [active, active] if wrong else [active & (x[..., 0] == 1), active & (x[..., 1] == 1)]
    inputs, counts = [], []
    for bank, (mask, field) in enumerate(zip(masks, (1, 2))):
        priority = torch.arange(t, device=x.device)[None, :].expand(b, t)+t*(~mask).long()
        order = priority.argsort(dim=1)
        values = x[..., field].gather(1, order)
        identity = torch.eye(2, dtype=x.dtype, device=x.device)[bank].expand(b, t, 2)
        inputs.append(torch.cat((values[..., None], identity), dim=-1))
        counts.append(mask.sum(1))
    return torch.cat(inputs, dim=0), torch.cat(counts, dim=0)


def last_state(states, lengths):
    index = (lengths-1).clamp_min(0)
    state = states[torch.arange(states.shape[0], device=states.device), index]
    return state*(lengths > 0)[:, None]


class Learner(nn.Module):
    def __init__(self, method):
        super().__init__()
        self.method = method
        if method == "history":
            self.core = nn.GRU(6, 16, batch_first=True)
            self.readout = nn.Sequential(nn.Linear(19, 16), nn.Tanh(), nn.Linear(16, 2))
        elif method in ("functional", "wrong_rules"):
            self.core = nn.GRU(3, 8, batch_first=True)
            self.heads = nn.ModuleList([nn.Linear(8, 1) for _ in range(2)])
        else:
            raise ValueError("Unknown method")

    def forward(self, x, lengths):
        if self.method == "history":
            states, _ = self.core(x)
            state = last_state(states, lengths)
            contexts = torch.eye(3, dtype=x.dtype, device=x.device)[None].expand(len(x), 3, 3)
            return self.readout(torch.cat((state[:, None].expand(-1, 3, -1), contexts), -1)).sigmoid()
        inputs, counts = filtered_inputs(x, lengths, wrong=self.method == "wrong_rules")
        states, _ = self.core(inputs)
        pair = last_state(states, counts).reshape(2, len(x), 8)
        values = torch.cat([head(pair[i]).sigmoid() for i, head in enumerate(self.heads)], dim=-1)
        return values[:, None].expand(-1, 3, -1)


def resources(model):
    return {"parameters": sum(p.numel() for p in model.parameters()), "state_values": 16,
            "approx_recurrent_matrix_macs_per_episode": 1056 if model.method == "history" else 528,
            "readout_matrix_macs_per_prediction_batch_of_three_contexts": 1008 if model.method == "history" else 16,
            "bank_updates": "all events" if model.method != "functional" else "eligible events only"}


def configure():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def train(method, seed, regime, config, out):
    seeds = seed_plan(seed, regime)
    torch.manual_seed(seeds["initialization"])
    model = Learner(method)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    rng = np.random.default_rng(seeds["training"])
    stream_hash = hashlib.sha256()
    snapshots, logs = {}, []
    start = time.perf_counter()
    for update in range(config["updates"]+1):
        if update in config["checkpoints"]:
            snapshots[update] = copy.deepcopy(model.state_dict())
            torch.save(snapshots[update], out/f"{method}-{update}.pt")
        if update == config["updates"]:
            break
        data = batch(rng, config["batch_size"], config["max_history"], regime, random_lengths=True)
        for key in ("x", "lengths", "targets"):
            stream_hash.update(data[key].tobytes())
        x, lengths = tensors(data)
        y = torch.from_numpy(data["targets"])
        optimizer.zero_grad(set_to_none=True)
        p = model(x, lengths).clamp(1e-6, 1-1e-6)
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
    metadata = {"training_seconds": time.perf_counter()-start, "training_stream_sha256": stream_hash.hexdigest(),
                "resources": resources(model), "training_log": logs, "seeds": seeds}
    print(json.dumps({"trained": method, "regime": regime, "replicate": seed,
                      "seconds": metadata["training_seconds"]}), flush=True)
    return model, snapshots, metadata


def predict(model, data, length=None):
    x, lengths = tensors(data)
    if length is not None:
        lengths = torch.full_like(lengths, length)
    with torch.no_grad():
        return model(x, lengths).cpu().numpy().astype(np.float64)


def score(model, data, regime, length):
    p = predict(model, data, length)
    q = posterior(data["x"], np.full(len(p), length), regime)
    excess = (p-q)**2
    heldout = data["heldout"]
    transfer = excess[np.arange(len(p)), heldout]
    delivery = (p.prod(-1)-q.prod(-1))**2
    seen_mask = np.arange(3)[None, :] != heldout[:, None]
    return {"transfer_excess": float(transfer.mean()), "channel_transfer_excess": transfer.mean(0).tolist(),
            "seen_excess": float(excess[seen_mask].mean()), "all_excess": float(excess.mean()),
            "delivery_transfer_excess": float(delivery[np.arange(len(p)), heldout].mean()),
            "latent_parameter_mse": float(((p-data["truth"])**2).mean())}


def diagnose(model, data, regime):
    prefix = 8
    variants = {"baseline": None, "decline": (1, 0, 0), "voluntary_failure": (1, 1, 0),
                "voluntary_success": (1, 1, 1), "assigned_failure": (0, 1, 0), "assigned_success": (0, 1, 1)}
    predictions, references = {}, {}
    b = len(data["x"])
    rows, heldout = np.arange(b), data["heldout"]
    # Append in a context already observed, and query the heldout context.
    context = data["x"][:, 0, 3:].argmax(-1)
    for name, event in variants.items():
        x = data["x"][:, :prefix+1].copy()
        lengths = np.full(b, prefix if event is None else prefix+1)
        x[:, prefix] = 0
        if event is not None:
            x[:, prefix, :3] = event
            x[rows, prefix, 3+context] = 1
        item = {"x": x, "lengths": lengths}
        predictions[name] = predict(model, item)[rows, heldout]
        references[name] = posterior(x, lengths, regime)[rows, heldout]
    pairs = {"failure_vs_decline": ("voluntary_failure", "decline"),
             "success_vs_failure": ("voluntary_success", "voluntary_failure"),
             "assigned_success_vs_failure": ("assigned_success", "assigned_failure"),
             "assigned_failure_vs_baseline": ("assigned_failure", "baseline"),
             "decline_vs_baseline": ("decline", "baseline")}
    metrics = {}
    for name, (a, bname) in pairs.items():
        delta = predictions[a]-predictions[bname]
        expected = references[a]-references[bname]
        nonzero = np.abs(expected) > 1e-9
        metrics[name] = {"mean_prediction_delta": delta.mean(0).tolist(), "mean_reference_delta": expected.mean(0).tolist(),
            "delta_mse": float(((delta-expected)**2).mean()),
            "directional_accuracy_informative_channels": float((delta[nonzero]*expected[nonzero] > 0).mean()) if nonzero.any() else None,
            "mean_abs_change_null_channels": float(np.abs(delta[~nonzero]).mean()) if (~nonzero).any() else None}
    x = data["x"].copy()
    permutation = [1, 0, 2]
    x[..., 3:] = data["x"][..., 3:][..., permutation]
    changed = dict(data, x=x)
    relabeled = predict(model, changed)[:, permutation]
    original = predict(model, data)
    return {"event_contrasts": metrics, "context_relabel_mean_abs_change": float(np.abs(relabeled-original).mean())}


def freeze(out):
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for filename, destination in (("experiment.py", "experiment.py"), ("README.md", "protocol.md"),
                                   ("cue-spec.md", "cue-spec.md"), ("requirements.txt", "requirements.txt")):
        shutil.copyfile(HERE/filename, out/destination)
        hashes[destination] = hashlib.sha256((out/destination).read_bytes()).hexdigest()
    manifest = {"version": VERSION, "config": CONFIG, "suites": SUITES, "source_hashes": hashes,
        "config_sha256": digest({"config": CONFIG, "suites": SUITES}), "torch": torch.__version__,
        "numpy": np.__version__, "python": platform.python_version(), "github_sha": os.environ.get("GITHUB_SHA"),
        "seed_plan": [{"replicate": i, "regime": r, **seed_plan(i, r)} for i in range(CONFIG["replicates"]) for r in REGIMES],
        "api_cost_usd": 0, "status": "frozen before study training and evaluation",
        "world_predecessor": "functional-learning-v1 at commit 5d42a38b37b315c528281aafb0018d9c8927a5ca; same choice/execution equations, modified sampling schedule"}
    write_json(out/"manifest.json", manifest)
    print("FROZEN_JSON:"+json.dumps(manifest), flush=True)


def validate(protocol):
    m = json.loads((protocol/"manifest.json").read_text())
    for name, expected in m["source_hashes"].items():
        if hashlib.sha256((protocol/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source mismatch: "+name)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != m["source_hashes"]["experiment.py"]:
        raise ValueError("Execute frozen source")
    if m["config"] != CONFIG or m["suites"] != SUITES or m["config_sha256"] != digest({"config": CONFIG, "suites": SUITES}):
        raise ValueError("Config mismatch")
    if m["torch"] != torch.__version__ or m["numpy"] != np.__version__:
        raise ValueError("Dependency mismatch")
    return m


def run(out, seed, protocol):
    manifest = validate(protocol)
    if seed not in range(CONFIG["replicates"]):
        raise ValueError("Unknown replicate")
    configure()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"manifest.json", manifest)
    start, trained, order = time.perf_counter(), {}, []
    for regime in (REGIMES if seed % 2 == 0 else REGIMES[::-1]):
        folder = out/regime
        folder.mkdir()
        trained[regime] = {}
        methods = METHODS[seed % 3:]+METHODS[:seed % 3]
        for method in methods:
            order.append([regime, method])
            trained[regime][method] = train(method, seed, regime, CONFIG, folder)
        if len({m[2]["training_stream_sha256"] for m in trained[regime].values()}) != 1:
            raise ValueError("Unmatched training data")
    # Every model finishes before evaluation/diagnostic data are generated.
    results, hashes = {}, {}
    for regime in REGIMES:
        seeds = seed_plan(seed, regime)
        evaluation = {suite: batch(np.random.default_rng(seeds["evaluation"]), CONFIG["evaluation_lifetimes"],
                                  CONFIG["max_history"], regime, suite=suite) for suite in SUITES}
        diagnostic = batch(np.random.default_rng(seeds["diagnostics"]), CONFIG["diagnostic_lifetimes"],
                           CONFIG["max_history"], regime)
        hashes[regime] = {suite: hashlib.sha256(item["x"].tobytes()).hexdigest() for suite, item in evaluation.items()}
        results[regime] = {}
        for method in METHODS:
            model, snapshots, metadata = trained[regime][method]
            metadata["checkpoints"] = {}
            for update in CONFIG["checkpoints"]:
                model.load_state_dict(snapshots[update])
                model.eval()
                metadata["checkpoints"][str(update)] = {
                    suite: {str(n): score(model, item, regime, n) for n in CONFIG["test_lengths"]}
                    for suite, item in evaluation.items()}
            metadata["curve_means"] = {suite: float(np.mean([
                metadata["checkpoints"][str(u)][suite][str(n)]["transfer_excess"]
                for u in CONFIG["checkpoints"] if u > 0 for n in CONFIG["test_lengths"]])) for suite in SUITES}
            reached = [u for u in CONFIG["checkpoints"] if u > 0 and np.mean([
                metadata["checkpoints"][str(u)]["reversed"][str(n)]["transfer_excess"]
                for n in CONFIG["test_lengths"]]) <= CONFIG["criterion_excess"]]
            metadata["criterion_update"] = min(reached) if reached else None
            model.load_state_dict(snapshots[CONFIG["updates"]])
            metadata["diagnostics"] = diagnose(model, diagnostic, regime)
            results[regime][method] = metadata
    row = {"version": VERSION, "replicate": seed, "config_sha256": manifest["config_sha256"],
           "source_hashes": manifest["source_hashes"], "models": results, "training_order": order,
           "evaluation_hashes": hashes, "elapsed_seconds": time.perf_counter()-start, "api_cost_usd": 0}
    write_json(out/f"result-seed-{seed}.json", row)
    print("ROW_JSON:"+json.dumps({k: v for k, v in row.items() if k != "models"}, separators=(",", ":")), flush=True)
    for regime, models in results.items():
        for method, value in models.items():
            print("MODEL_JSON:"+json.dumps({"regime": regime, "method": method, "value": value}, separators=(",", ":")), flush=True)


def bootstrap(v):
    rng = np.random.default_rng(106000000)
    means = rng.choice(v, size=(10000, len(v)), replace=True).mean(1)
    return np.quantile(means, [0.025, 0.975]).tolist()


def contrasts_for_row(row):
    def value(regime, method, suite="reversed"):
        return row["models"][regime][method]["curve_means"][suite]
    result = {}
    for regime in REGIMES:
        result[regime+"_history_minus_functional"] = value(regime, "history")-value(regime, "functional")
        result[regime+"_wrong_minus_functional"] = value(regime, "wrong_rules")-value(regime, "functional")
    for regime in REGIMES:
        def final(method, current_regime=regime):
            return np.mean([row["models"][current_regime][method]["checkpoints"][str(CONFIG["updates"])]["reversed"][str(n)]["transfer_excess"] for n in CONFIG["test_lengths"]])
        result[regime+"_final_history_minus_functional"] = float(final("history")-final("functional"))
    result["boundary_interaction"] = result["shared_history_minus_functional"]-result["context_specific_history_minus_functional"]
    return result


def aggregate(inputs, out, protocol):
    manifest = validate(protocol)
    rows = [json.loads(p.read_text()) for p in sorted(inputs.rglob("result-seed-*.json"))]
    if sorted(r["replicate"] for r in rows) != list(range(CONFIG["replicates"])):
        raise ValueError("Incomplete/duplicate replicates")
    for row in rows:
        if row["config_sha256"] != manifest["config_sha256"] or row["source_hashes"] != manifest["source_hashes"]:
            raise ValueError("Mixed protocols")
        for regime in REGIMES:
            if len({m["training_stream_sha256"] for m in row["models"][regime].values()}) != 1:
                raise ValueError("Unmatched data")
    out.mkdir(parents=True, exist_ok=False)
    cells = {}
    for regime in REGIMES:
        cells[regime] = {}
        for method in METHODS:
            models = [r["models"][regime][method] for r in rows]
            cells[regime][method] = {
                "curve_means": {suite: float(np.mean([m["curve_means"][suite] for m in models])) for suite in SUITES},
                "final_reversed_by_history": {str(n): float(np.mean([
                    m["checkpoints"][str(CONFIG["updates"])]["reversed"][str(n)]["transfer_excess"] for m in models])) for n in CONFIG["test_lengths"]},
                "criterion_updates": [m["criterion_update"] for m in models],
                "resources": models[0]["resources"], "mean_training_seconds": float(np.mean([m["training_seconds"] for m in models]))}
    differences = [contrasts_for_row(r) for r in rows]
    contrasts = {}
    for key in differences[0]:
        v = [r[key] for r in differences]
        contrasts[key] = {"mean": float(np.mean(v)), "paired_bootstrap_95ci": bootstrap(v), "run_differences": v}
    summary = {"version": VERSION, "replicates": len(rows), "models": cells, "contrasts": contrasts,
        "primary_contrast": "shared_history_minus_functional", "positive_favors": "functional",
        "config_sha256": manifest["config_sha256"], "source_hashes": manifest["source_hashes"], "api_cost_usd": 0}
    write_json(out/"summary.json", summary)
    write_json(out/"replicate-results.json", rows)
    write_json(out/"manifest.json", manifest)
    report = ["# Cue transfer results", "", "48 models; eight paired replicates; no API calls.", "",
              "| Regime | Learner | Canonical | Reversed | Assigned only | Voluntary only |",
              "|---|---|---:|---:|---:|---:|"]
    for regime, models in cells.items():
        for method, cell in models.items():
            v = cell["curve_means"]
            report.append(f"| {regime} | {method} | {v['canonical']:.7f} | {v['reversed']:.7f} | {v['assigned_only']:.7f} | {v['voluntary_only']:.7f} |")
    report += ["", "Primary contrast: "+json.dumps(contrasts[summary["primary_contrast"]]), "",
               "Theory-supplied evidence masks are an inductive bias. The functional core itself shares recurrent weights. No evolved mechanism, broad-domain or WTR identification claim follows."]
    text = "\n".join(report)+"\n"
    (out/"README.md").write_text(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as f:
            f.write(text)
    print("SUMMARY_JSON:"+json.dumps(summary, separators=(",", ":")), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "aggregate"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--protocol", type=Path, default=HERE)
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    if args.command == "freeze":
        freeze(args.out)
    elif args.command == "run":
        run(args.out, args.seed, args.protocol)
    else:
        if args.inputs is None:
            parser.error("--inputs required")
        aggregate(args.inputs, args.out, args.protocol)


if __name__ == "__main__":
    main()
