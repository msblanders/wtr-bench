"""Outcome-selected learning procedures and frozen transfer to an independent simulator."""
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

import external
import models
import numpy as np
import torch
import worlds

HERE = Path(__file__).resolve().parent
VERSION = "discovery-transfer-v1.0"
CONFIG = {"replicates": 8, "generations": 512, "population": 32, "elites": 8, "batch_size": 64,
          "max_history": 24, "validation_lifetimes": 256, "evaluation_lifetimes": 512,
          "diagnostic_lifetimes": 256, "test_lengths": [4, 12, 24, 48], "primary_lengths": [4, 12, 24],
          "checkpoints": [0, 128, 512], "initial_sd": .5, "mean_rate": .3, "sd_rate": .15,
          "min_sd": .05, "max_sd": 2., "adam_lr": .003, "gradient_clip": 1.0}
METHODS = ("evolved", "random_search", "matched_gradient", "dense_gradient")
FILES = ("experiment.py", "models.py", "worlds.py", "external.py", "requirements.txt", "README.md")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def configure():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def seeds_for(seed):
    return {"initialization": 121000000+seed, "training": 122000000+seed,
            "validation": 123000000+seed, "evolution": 124000000+seed,
            "random_search": 125000000+seed, "evaluation": 126000000+1000*seed,
            "diagnostics": 127000000+seed}


def stream_update(hasher, data):
    for key in ("x", "lengths", "query", "query_mask", "query_context", "y_choice", "y_ability"):
        hasher.update(np.ascontiguousarray(data[key]).tobytes())


def vector_loss(vectors, data, data_inputs=None):
    with torch.no_grad():
        pred = models.small(torch.from_numpy(np.asarray(vectors, dtype=np.float32)),
                            models.inputs(data) if data_inputs is None else data_inputs)
        return models.observed_loss(pred, data).numpy().astype(np.float64)


def search(seed, config, out):
    """Rank-weighted Gaussian evolution versus equal-budget independent random search."""
    seeds = seeds_for(seed)
    rng, erng, rrng = (np.random.default_rng(seeds[k]) for k in ("training", "evolution", "random_search"))
    validation = worlds.synthetic(np.random.default_rng(seeds["validation"]), config["validation_lifetimes"],
                                   config["max_history"], training=True)
    validation_inputs = models.inputs(validation)
    vhash = hashlib.sha256()
    stream_update(vhash, validation)
    initial = models.initial_mean()+np.random.default_rng(seeds["initialization"]).normal(
        0, config["initial_sd"], models.PARAMETERS).astype(np.float32)
    best = {m: initial.copy() for m in METHODS[:2]}
    best_loss = {m: float(vector_loss(initial[None], validation, validation_inputs)[0]) for m in METHODS[:2]}
    checkpoints = {m: {0: initial.copy()} for m in METHODS[:2]}
    means = models.initial_mean()
    sd = np.full(models.PARAMETERS, config["initial_sd"], dtype=np.float32)
    weights = np.log(config["elites"]+.5)-np.log(np.arange(1, config["elites"]+1))
    weights = (weights/weights.sum()).astype(np.float32)
    hasher, logs = hashlib.sha256(), []
    started = time.perf_counter()
    for generation in range(1, config["generations"]+1):
        data = worlds.synthetic(rng, config["batch_size"], config["max_history"], training=True)
        stream_update(hasher, data)
        data_inputs = models.inputs(data)
        candidates = means+sd*erng.standard_normal((config["population"], models.PARAMETERS)).astype(np.float32)
        candidates[0] = means
        losses = vector_loss(candidates, data, data_inputs)
        elite = candidates[np.argsort(losses, kind="stable")[:config["elites"]]]
        new_mean = (weights[:, None]*elite).sum(0)
        new_sd = np.sqrt((weights[:, None]*(elite-means)**2).sum(0))
        means = (1-config["mean_rate"])*means+config["mean_rate"]*new_mean
        sd = np.clip((1-config["sd_rate"])*sd+config["sd_rate"]*new_sd, config["min_sd"], config["max_sd"])
        random_candidates = models.initial_mean()+config["initial_sd"]*rrng.standard_normal(
            (config["population"], models.PARAMETERS)).astype(np.float32)
        random_losses = vector_loss(random_candidates, data, data_inputs)
        proposed = {"evolved": means, "random_search": random_candidates[int(random_losses.argmin())]}
        for method, theta in proposed.items():
            loss = float(vector_loss(theta[None], validation, validation_inputs)[0])
            if not np.isfinite(loss):
                raise ValueError("Nonfinite selection fitness")
            if loss < best_loss[method]:
                best[method], best_loss[method] = theta.copy(), loss
        if generation in config["checkpoints"]:
            for method in METHODS[:2]:
                checkpoints[method][generation] = best[method].copy()
        if generation % 32 == 0 or generation == config["generations"]:
            record = {"generation": generation, "evolved_batch_best": float(losses.min()),
                      "evolved_batch_mean_candidate": float(losses[0]), "random_batch_best": float(random_losses.min()),
                      "selected_validation_brier": dict(best_loss), "mean_search_sd": float(sd.mean())}
            logs.append(record)
            print(json.dumps({"search_progress": record, "replicate": seed}), flush=True)
    elapsed = time.perf_counter()-started
    np.savez(out/"search-distribution.npz", mean=means, sd=sd)
    results = {}
    for method in METHODS[:2]:
        np.savez(out/f"{method}-checkpoints.npz", **{str(k): v for k, v in checkpoints[method].items()})
        results[method] = {"training_stream_sha256": hasher.hexdigest(), "validation_sha256": vhash.hexdigest(),
            "training_seconds_joint_two_searches": elapsed, "candidate_fitness_evaluations": config["population"]*config["generations"],
            "unique_training_lifetimes": config["batch_size"]*config["generations"],
            "validation_candidate_evaluations": config["generations"]+1,
            "selected_validation_brier": best_loss[method], "resources": models.resources(method), "training_log": logs}
    return checkpoints, results, validation, initial


def gradient(method, seed, config, out, validation, initial):
    torch.manual_seed(seeds_for(seed)["initialization"])
    model = models.Small(initial) if method == "matched_gradient" else models.Dense()
    optimizer = torch.optim.Adam(model.parameters(), lr=config["adam_lr"])
    rng = np.random.default_rng(seeds_for(seed)["training"])
    vi = models.inputs(validation)
    with torch.no_grad():
        best_loss = float(models.observed_loss(model(vi), validation)[0])
    best = copy.deepcopy(model.state_dict())
    checkpoints = {0: copy.deepcopy(best)}
    hasher, logs = hashlib.sha256(), []
    started = time.perf_counter()
    for update in range(1, config["generations"]+1):
        data = worlds.synthetic(rng, config["batch_size"], config["max_history"], training=True)
        stream_update(hasher, data)
        loss = models.observed_loss(model(models.inputs(data)), data)[0]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = nn_clip(model, config["gradient_clip"])
        if not np.isfinite(float(loss.detach())) or not np.isfinite(norm):
            raise ValueError("Nonfinite gradient training")
        optimizer.step()
        with torch.no_grad():
            score = float(models.observed_loss(model(vi), validation)[0])
        if score < best_loss:
            best, best_loss = copy.deepcopy(model.state_dict()), score
        if update in config["checkpoints"]:
            checkpoints[update] = copy.deepcopy(best)
        if update % 32 == 0 or update == config["generations"]:
            logs.append({"update": update, "training_brier": float(loss.detach()), "best_validation_brier": best_loss})
    torch.save(checkpoints, out/f"{method}-checkpoints.pt")
    torch.save(model.state_dict(), out/f"{method}-last-update.pt")
    metadata = {"training_stream_sha256": hasher.hexdigest(), "training_seconds": time.perf_counter()-started,
                "unique_training_lifetimes": config["batch_size"]*config["generations"],
                "gradient_updates": config["generations"], "validation_candidate_evaluations": config["generations"]+1,
                "selected_validation_brier": best_loss, "resources": models.resources(method), "training_log": logs}
    print(json.dumps({"trained": method, "seed": seed, "seconds": metadata["training_seconds"]}), flush=True)
    return checkpoints, metadata


def nn_clip(model, maximum):
    return float(torch.nn.utils.clip_grad_norm_(model.parameters(), maximum))


def restored(method, state):
    if method in METHODS[:2]:
        return models.Small(state)
    model = models.Small(np.zeros(models.PARAMETERS, np.float32)) if method == "matched_gradient" else models.Dense()
    model.load_state_dict(state)
    return model


def predictions(model, data, **kwargs):
    with torch.no_grad():
        p, a = model(models.inputs(data), **kwargs)
    return p[0].numpy().astype(np.float64), a[0].numpy().astype(np.float64)


def score(pred, data):
    p, a = pred
    choice_brier = .5*(np.square(p).sum(-1)-2*p[np.arange(len(p)), data["y_choice"]]+1)
    choice_excess_truth = .5*np.square(p-data["truth_choice"]).sum(-1)
    ability_observed = bool(np.all(data["y_ability"] >= 0))
    ability_brier = float(np.mean((a-data["y_ability"])**2)) if ability_observed else None
    return {"brier": float((choice_brier.mean()+ability_brier)/2) if ability_observed else float(choice_brier.mean()),
            "choice_brier": float(choice_brier.mean()), "execution_brier": ability_brier,
            "choice_truth_excess": float(choice_excess_truth.mean()),
            "execution_truth_excess": float(np.mean((a-data["truth_ability"])**2)) if ability_observed else None}


def diagnose(model, data):
    # Append at a seen context; query a standard voluntary offer in the held-out context.
    n = len(data["x"])
    query = np.tile(np.array([[[0., 0.], [-1., 3.]]], np.float32), (n, 1, 1))
    baseline = dict(data, query=query, query_mask=np.ones((n, 2), bool))
    variants = {"baseline": None, "decline": (1, 0, 0, 0), "voluntary_failure": (1, 1, 0, 1),
                "voluntary_success": (1, 1, 1, 1), "assigned_failure": (0, 1, 0, 1), "assigned_success": (0, 1, 1, 1)}
    values, references = {}, {}
    for name, event in variants.items():
        changed = dict(baseline)
        if event is not None:
            v, action, success, observed = event
            menus = query[:, None].astype(np.float64)
            context = data["contexts"][:, :1]
            extra = worlds.encode(menus, np.ones((n, 1, 2), bool), np.full((n, 1), action),
                                  np.full((n, 1), v), np.full((n, 1), success), np.full((n, 1), observed), context)
            changed["x"] = np.concatenate((data["x"], extra), axis=1)
            changed["lengths"] = data["lengths"]+1
            for key, extra_value in (("history_menus", menus), ("history_masks", np.ones((n, 1, 2), bool)),
                                     ("actions", np.full((n, 1), action)), ("voluntary", np.full((n, 1), v, bool)),
                                     ("success", np.full((n, 1), success)), ("observed", np.full((n, 1), observed, bool)),
                                     ("contexts", context)):
                changed[key] = np.concatenate((data[key], extra_value), axis=1)
        p, a = predictions(model, changed)
        q, qa = worlds.functional_reference(changed)
        values[name], references[name] = np.stack((p[:, 1], a), -1), np.stack((q[:, 1], qa), -1)
    pairs = {"failure_vs_decline": ("voluntary_failure", "decline"),
             "success_vs_failure": ("voluntary_success", "voluntary_failure"),
             "assigned_success_vs_failure": ("assigned_success", "assigned_failure"),
             "assigned_failure_vs_baseline": ("assigned_failure", "baseline"),
             "decline_vs_baseline": ("decline", "baseline")}
    result = {}
    for name, (a, b) in pairs.items():
        delta, reference = values[a]-values[b], references[a]-references[b]
        informative = np.abs(reference) > 1e-9
        result[name] = {"mean_choice_execution_delta": delta.mean(0).tolist(),
            "mean_reference_delta": reference.mean(0).tolist(), "delta_mse": float(np.mean((delta-reference)**2)),
            "informative_direction_accuracy": float(np.mean(delta[informative]*reference[informative] > 0)),
            "null_channel_mean_abs_change": float(np.abs(delta[~informative]).mean()) if (~informative).any() else None}
    return result


def run(out, seed, protocol):
    manifest = validate(protocol)
    if seed not in range(CONFIG["replicates"]):
        raise ValueError("Unknown seed")
    configure()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"manifest.json", manifest)
    started = time.perf_counter()
    checkpoints, metadata, validation, initial = search(seed, CONFIG, out)
    gradient_order = METHODS[2:] if seed % 2 == 0 else METHODS[:1:-1]
    for method in gradient_order:
        checkpoints[method], metadata[method] = gradient(method, seed, CONFIG, out, validation, initial)
    if len({m["training_stream_sha256"] for m in metadata.values()}) != 1:
        raise ValueError("Unmatched training streams")
    # Finalize every method before generating any holdout or external histories/outcomes.
    print(json.dumps({"all_training_complete": True, "seed": seed}), flush=True)
    namespace = external.load(protocol/"upstream")
    eval_hashes, references = {}, {}
    for method in METHODS:
        metadata[method]["checkpoints"] = {str(c): {} for c in CONFIG["checkpoints"]}
        metadata[method]["no_memory"] = {}
        metadata[method]["state_lesions"] = {}
    for suite_index, suite in enumerate(worlds.SUITES):
        eval_hashes[suite], references[suite] = {}, {}
        for length in CONFIG["test_lengths"]:
            rng = np.random.default_rng(seeds_for(seed)["evaluation"]+100*suite_index+length)
            data = worlds.external_games(rng, CONFIG["evaluation_lifetimes"], length, namespace) if suite == "external_games" else worlds.synthetic(
                rng, CONFIG["evaluation_lifetimes"], length, suite=suite)
            hasher = hashlib.sha256()
            stream_update(hasher, data)
            eval_hashes[suite][str(length)] = hasher.hexdigest()
            references[suite][str(length)] = score(worlds.functional_reference(data), data)
            for method in METHODS:
                for checkpoint in CONFIG["checkpoints"]:
                    model = restored(method, checkpoints[method][checkpoint])
                    record = metadata[method]["checkpoints"][str(checkpoint)]
                    record.setdefault(suite, {})[str(length)] = score(predictions(model, data), data)
                # The last restored model is the frozen final model selected on development data.
                metadata[method]["no_memory"].setdefault(suite, {})[str(length)] = score(predictions(model, data, no_memory=True), data)
                if method == "evolved" and length == 24 and suite in ("canonical", "external_games"):
                    metadata[method]["state_lesions"][suite] = {str(i): score(predictions(model, data, lesion=i), data) for i in range(models.HIDDEN)}
        print(json.dumps({"evaluated": suite, "seed": seed}), flush=True)
    diagnostic = worlds.synthetic(np.random.default_rng(seeds_for(seed)["diagnostics"]), CONFIG["diagnostic_lifetimes"], 8)
    for method in METHODS:
        metadata[method]["diagnostics"] = diagnose(restored(method, checkpoints[method][CONFIG["generations"]]), diagnostic)
    row = {"version": VERSION, "replicate": seed, "config_sha256": manifest["config_sha256"],
           "source_hashes": manifest["source_hashes"], "models": metadata, "references": references,
           "evaluation_hashes": eval_hashes, "seeds": seeds_for(seed), "elapsed_seconds": time.perf_counter()-started,
           "api_cost_usd": 0}
    write_json(out/f"result-seed-{seed}.json", row)
    print("ROW_JSON:"+json.dumps({k: v for k, v in row.items() if k != "models"}, separators=(",", ":")), flush=True)
    for method, value in metadata.items():
        print("MODEL_JSON:"+json.dumps({"method": method, "value": value}, separators=(",", ":")), flush=True)


def freeze(out, upstream):
    external.verify(upstream)
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        shutil.copyfile(HERE/name, out/name)
    shutil.copytree(upstream, out/"upstream")
    hashes = {name: hashlib.sha256((out/name).read_bytes()).hexdigest() for name in FILES}
    manifest = {"version": VERSION, "config": CONFIG, "config_sha256": digest(CONFIG), "source_hashes": hashes,
                "external_commit": external.COMMIT, "external_sha256": external.HASHES,
                "python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__,
                "github_sha": os.environ.get("GITHUB_SHA"), "api_cost_usd": 0,
                "status": "frozen before study selection and holdout evaluation",
                "seed_plan": [seeds_for(i) for i in range(CONFIG["replicates"])]}
    write_json(out/"manifest.json", manifest)
    print("FROZEN_JSON:"+json.dumps(manifest), flush=True)


def validate(protocol):
    manifest = json.loads((protocol/"manifest.json").read_text())
    for name, expected in manifest["source_hashes"].items():
        if hashlib.sha256((protocol/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source mismatch: "+name)
    if HERE.resolve() != protocol.resolve():
        raise ValueError("Execute frozen source")
    if manifest["config"] != CONFIG or manifest["config_sha256"] != digest(CONFIG):
        raise ValueError("Config mismatch")
    if manifest["numpy"] != np.__version__ or manifest["torch"] != torch.__version__:
        raise ValueError("Runtime mismatch")
    external.verify(protocol/"upstream")
    return manifest


def mean_score(row, method, suite, kind="final", metric="brier"):
    model = row["models"][method]
    cells = model["no_memory"][suite] if kind == "no_memory" else model["checkpoints"][str(CONFIG["generations"])][suite]
    return float(np.mean([cells[str(n)][metric] for n in CONFIG["primary_lengths"]]))


def contrasts(row):
    values = {}
    for suite in worlds.SUITES:
        value = mean_score(row, "evolved", suite)
        values[suite+"_memory_gain"] = mean_score(row, "evolved", suite, "no_memory")-value
        for method in METHODS[1:]:
            values[suite+"_"+method+"_minus_evolved"] = mean_score(row, method, suite)-value
    return values


def bootstrap(values):
    rng = np.random.default_rng(128000000)
    means = rng.choice(values, size=(10000, len(values)), replace=True).mean(1)
    return np.quantile(means, [.025, .975]).tolist()


def aggregate(inputs, out, protocol):
    manifest = validate(protocol)
    rows = [json.loads(p.read_text()) for p in sorted(inputs.rglob("result-seed-*.json"))]
    if sorted(r["replicate"] for r in rows) != list(range(CONFIG["replicates"])):
        raise ValueError("Missing or duplicate replicates")
    for row in rows:
        if row["source_hashes"] != manifest["source_hashes"] or row["config_sha256"] != manifest["config_sha256"]:
            raise ValueError("Mixed protocols")
        if len({m["training_stream_sha256"] for m in row["models"].values()}) != 1:
            raise ValueError("Unmatched training streams")
    difference_rows = [contrasts(r) for r in rows]
    differences = {}
    for key in difference_rows[0]:
        v = [r[key] for r in difference_rows]
        differences[key] = {"mean": float(np.mean(v)), "paired_bootstrap_95ci": bootstrap(v), "run_differences": v}
    cells = {suite: {method: float(np.mean([mean_score(r, method, suite) for r in rows])) for method in METHODS} for suite in worlds.SUITES}
    refs = {suite: float(np.mean([r["references"][suite][str(n)]["brier"] for r in rows for n in CONFIG["primary_lengths"]])) for suite in worlds.SUITES}
    primary = ("shifted_memory_gain", "shifted_random_search_minus_evolved", "external_games_memory_gain")
    summary = {"version": VERSION, "replicates": len(rows), "final_brier": cells, "functional_reference_brier": refs,
               "contrasts": differences, "joint_primary_criteria": list(primary),
               "joint_primary_pass": all(differences[key]["paired_bootstrap_95ci"][0] > 0 for key in primary),
               "config_sha256": manifest["config_sha256"], "source_hashes": manifest["source_hashes"], "api_cost_usd": 0}
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"summary.json", summary)
    write_json(out/"replicate-results.json", rows)
    write_json(out/"manifest.json", manifest)
    lines = ["# Discovery and external transfer pilot", "", "Eight independent selection/training runs; no API calls.", "",
             "| Suite | Evolved | Random search | Matched gradient | Dense gradient | Supplied reference |",
             "|---|---:|---:|---:|---:|---:|"]
    for suite, cell in cells.items():
        lines.append("| "+suite+" | "+" | ".join(f"{cell[m]:.6f}" for m in METHODS)+f" | {refs[suite]:.6f} |")
    lines += ["", "Joint primary criteria satisfied: "+str(summary["joint_primary_pass"]), "",
              "External results concern two-player games and static selfish/altruistic actors from the pinned upstream implementation. They do not establish human fit, full reciprocal-game competence, or multi-domain evolutionary differentiation."]
    (out/"README.md").write_text("\n".join(lines)+"\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as f:
            f.write("\n".join(lines)+"\n")
    print("SUMMARY_JSON:"+json.dumps(summary, separators=(",", ":")), flush=True)


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
        if args.upstream is None:
            parser.error("--upstream required")
        freeze(args.out, args.upstream)
    elif args.command == "run":
        run(args.out, args.seed, args.protocol)
    else:
        if args.inputs is None:
            parser.error("--inputs required")
        aggregate(args.inputs, args.out, args.protocol)


if __name__ == "__main__":
    main()
