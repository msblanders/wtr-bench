"""Fixed-evidence optimization budgets with matched development-selection opportunities."""
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
VERSION = "search-budget-v1.0"
CONFIG = {"replicates": 8, "generations": 2048, "population": 32, "elites": 8, "batch_size": 64,
          "max_history": 24, "validation_lifetimes": 256, "evaluation_lifetimes": 512,
          "diagnostic_lifetimes": 256, "test_lengths": [4, 12, 24, 48], "primary_lengths": [4, 12, 24],
          "budgets": [512, 2048], "bank_batches": 512, "development_candidates": 512, "initial_sd": .5, "mean_rate": .3, "sd_rate": .15,
          "min_sd": .05, "max_sd": 2., "adam_lr": .003, "gradient_clip": 1.0,
          "readouts": ["interaction", "wide_control"], "execution_noninferiority_margin": .002,
          "objective": "0.5*(choice_brier+execution_brier)", "development_objective": "0.5*(choice_brier+execution_brier)"}
METHODS = ("evolved", "random_search", "matched_gradient")
READOUTS = models.READOUTS
EXECUTION_MARGIN = .002
SUITES = ("canonical_seen", "canonical_heldout", "shifted", "external_games")
PREDECESSOR = "4aa0e4dc6a62b87805dce673028d2ffbb6968556"
FILES = ("experiment.py", "models.py", "worlds.py", "external.py", "requirements.txt", "README.md")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def configure():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def seeds_for(seed):
    return {"initialization": 181000000+seed, "training": 182000000+seed,
            "validation": 183000000+seed, "evolution": 184000000+seed,
            "random_search": 185000000+seed, "evaluation": 186000000+1000*seed,
            "diagnostics": 187000000+seed, "donors": 189000000+1000*seed, "replay": 190000000+seed}


def stream_update(hasher, data):
    for key in ("x", "lengths", "query", "query_mask", "query_context", "y_choice", "y_ability"):
        hasher.update(np.ascontiguousarray(data[key]).tobytes())


def joint_loss(pred, data):
    """Both observed future targets; neither latent truth nor architecture enters fitness."""
    choice, ability = pred
    y = torch.from_numpy(data["y_choice"]).long()
    selected = choice.gather(-1, y[None, :, None].expand(len(choice), -1, 1))[..., 0]
    brier = .5*(choice.square().sum(-1)-2*selected+1)
    a = torch.from_numpy(data["y_ability"])
    if bool((a < 0).any()):
        raise ValueError("Joint fitness requires observed execution targets")
    return .5*(brier+(ability-a).square()).mean(-1)


def vector_loss(vectors, data, data_inputs=None, readout="interaction"):
    """Joint observed-outcome loss for training and development selection."""
    with torch.no_grad():
        pred = models.small(torch.from_numpy(np.asarray(vectors, dtype=np.float32)),
                            models.inputs(data) if data_inputs is None else data_inputs, readout)
        return joint_loss(pred, data).numpy().astype(np.float64)


def make_bank(seed, config):
    rng = np.random.default_rng(seeds_for(seed)["training"])
    bank = [worlds.synthetic(rng, config["batch_size"], config["max_history"], training=True)
            for _ in range(config["bank_batches"])]
    data_inputs = [models.inputs(data) for data in bank]
    hasher = hashlib.sha256()
    for data in bank:
        stream_update(hasher, data)
    rng = np.random.default_rng(seeds_for(seed)["replay"])
    order = np.concatenate([np.arange(len(bank))]+[rng.permutation(len(bank))
                          for _ in range(config["generations"]//len(bank)-1)])
    if len(order) != config["generations"]:
        raise ValueError("Generation budget must contain complete bank passes")
    return bank, data_inputs, order, hasher.hexdigest()


def due_budgets(step, config):
    return [budget for budget in config["budgets"]
            if step <= budget and step % (budget//config["development_candidates"]) == 0]


def check_config(config):
    if config["generations"] != max(config["budgets"]) or min(config["budgets"]) < config["bank_batches"]:
        raise ValueError("Invalid budgets")
    if any(b % config["development_candidates"] or b % config["bank_batches"] for b in config["budgets"]):
        raise ValueError("Budgets must divide into equal validation grids and bank passes")


def search(seed, config, out, readout, bank_info):
    """One trajectory; equal development candidate counts for each budget champion."""
    check_config(config)
    seeds = seeds_for(seed)
    erng, rrng = (np.random.default_rng(seeds[k]) for k in ("evolution", "random_search"))
    bank, cached_inputs, order, bank_hash = bank_info
    validation = worlds.synthetic(np.random.default_rng(seeds["validation"]), config["validation_lifetimes"],
                                   config["max_history"], training=True)
    vi = models.inputs(validation)
    vhash = hashlib.sha256()
    stream_update(vhash, validation)
    initial = models.initial_mean()+np.random.default_rng(seeds["initialization"]).normal(
        0, config["initial_sd"], models.PARAMETERS).astype(np.float32)
    initial_loss = float(vector_loss(initial[None], validation, vi, readout)[0])
    best = {m: {b: initial.copy() for b in config["budgets"]} for m in METHODS[:2]}
    losses_best = {m: dict.fromkeys(config["budgets"], initial_loss) for m in METHODS[:2]}
    selected = {m: dict.fromkeys(config["budgets"], 0) for m in METHODS[:2]}
    checkpoints = {m: {0: initial.copy()} for m in METHODS[:2]}
    counts = dict.fromkeys(config["budgets"], 1)
    means = models.initial_mean()
    sd = np.full(models.PARAMETERS, config["initial_sd"], dtype=np.float32)
    weights = np.log(config["elites"]+.5)-np.log(np.arange(1, config["elites"]+1))
    weights = (weights/weights.sum()).astype(np.float32)
    hasher, logs, prefixes = hashlib.sha256(), [], {}
    unique_development = 1
    started = time.perf_counter()
    for generation, bank_id in enumerate(order, start=1):
        data, di = bank[bank_id], cached_inputs[bank_id]
        stream_update(hasher, data)
        candidates = means+sd*erng.standard_normal((config["population"], models.PARAMETERS)).astype(np.float32)
        candidates[0] = means
        losses = vector_loss(candidates, data, di, readout)
        elite = candidates[np.argsort(losses, kind="stable")[:config["elites"]]]
        new_mean = (weights[:, None]*elite).sum(0)
        new_sd = np.sqrt((weights[:, None]*(elite-means)**2).sum(0))
        means = (1-config["mean_rate"])*means+config["mean_rate"]*new_mean
        sd = np.clip((1-config["sd_rate"])*sd+config["sd_rate"]*new_sd, config["min_sd"], config["max_sd"])
        random_candidates = models.initial_mean()+config["initial_sd"]*rrng.standard_normal(
            (config["population"], models.PARAMETERS)).astype(np.float32)
        random_losses = vector_loss(random_candidates, data, di, readout)
        proposed = {"evolved": means, "random_search": random_candidates[int(random_losses.argmin())]}
        due = due_budgets(generation, config)
        if due:
            unique_development += 1
            for budget in due:
                counts[budget] += 1
            for method, theta in proposed.items():
                loss = float(vector_loss(theta[None], validation, vi, readout)[0])
                if not np.isfinite(loss):
                    raise ValueError("Nonfinite selection fitness")
                for budget in due:
                    if loss < losses_best[method][budget]:
                        best[method][budget] = theta.copy()
                        losses_best[method][budget] = loss
                        selected[method][budget] = generation
        if generation in config["budgets"]:
            prefixes[str(generation)] = hasher.hexdigest()
            for method in METHODS[:2]:
                checkpoints[method][generation] = best[method][generation].copy()
            checkpoints["evolved"][f"raw_{generation}"] = means.copy()
        if generation % 128 == 0 or generation == config["generations"]:
            record = {"generation": generation, "evolved_batch_best": float(losses.min()),
                      "evolved_batch_mean_candidate": float(losses[0]), "random_batch_best": float(random_losses.min()),
                      "selected_validation_joint_brier": losses_best.copy(), "mean_search_sd": float(sd.mean())}
            # Deep-copy nested dictionaries before subsequent updates.
            logs.append(copy.deepcopy(record))
            print(json.dumps({"search_progress": record, "replicate": seed, "readout": readout}), flush=True)
    elapsed = time.perf_counter()-started
    np.savez(out/"search-distribution.npz", mean=means, sd=sd)
    results = {}
    for method in METHODS[:2]:
        np.savez(out/f"{method}-checkpoints.npz", **{str(k): v for k, v in checkpoints[method].items()})
        results[method] = {"readout": readout, "training_stream_sha256": hasher.hexdigest(),
            "training_prefix_sha256": prefixes, "bank_sha256": bank_hash, "validation_sha256": vhash.hexdigest(),
            "training_seconds_joint_two_searches": elapsed, "unique_training_lifetimes": len(bank)*config["batch_size"],
            "training_presentations": config["generations"]*config["batch_size"],
            "development_evaluations_by_budget": counts, "unique_development_evaluations_shared_trajectory": unique_development,
            "budget_selection": {str(b): {"selected_generation": selected[method][b],
                "selected_validation_joint_brier": losses_best[method][b],
                "candidate_fitness_evaluations": config["population"]*b,
                "training_presentations": b*config["batch_size"]} for b in config["budgets"]},
            "resources": models.resources(method, readout), "training_log": logs}
    return checkpoints, results, validation, initial


def gradient(method, seed, config, out, validation, initial, readout, bank_info):
    check_config(config)
    torch.manual_seed(seeds_for(seed)["initialization"])
    model = models.Small(initial, readout)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["adam_lr"])
    bank, cached_inputs, order, bank_hash = bank_info
    vi = models.inputs(validation)
    with torch.no_grad():
        initial_loss = float(joint_loss(model(vi), validation)[0])
    best = {b: copy.deepcopy(model.state_dict()) for b in config["budgets"]}
    losses_best = dict.fromkeys(config["budgets"], initial_loss)
    selected, counts = dict.fromkeys(config["budgets"], 0), dict.fromkeys(config["budgets"], 1)
    checkpoints = {0: copy.deepcopy(model.state_dict())}
    hasher, logs, prefixes = hashlib.sha256(), [], {}
    unique_development = 1
    started = time.perf_counter()
    for update, bank_id in enumerate(order, start=1):
        data = bank[bank_id]
        stream_update(hasher, data)
        loss = joint_loss(model(cached_inputs[bank_id]), data)[0]
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = nn_clip(model, config["gradient_clip"])
        if not np.isfinite(float(loss.detach())) or not np.isfinite(norm):
            raise ValueError("Nonfinite gradient training")
        optimizer.step()
        due = due_budgets(update, config)
        if due:
            unique_development += 1
            with torch.no_grad():
                score = float(joint_loss(model(vi), validation)[0])
            for budget in due:
                counts[budget] += 1
                if score < losses_best[budget]:
                    best[budget], losses_best[budget] = copy.deepcopy(model.state_dict()), score
                    selected[budget] = update
        if update in config["budgets"]:
            prefixes[str(update)] = hasher.hexdigest()
            checkpoints[update] = copy.deepcopy(best[update])
            checkpoints[f"raw_{update}"] = copy.deepcopy(model.state_dict())
        if update % 128 == 0 or update == config["generations"]:
            logs.append({"update": update, "training_brier": float(loss.detach()),
                         "best_validation_joint_brier": dict(losses_best)})
    torch.save(checkpoints, out/f"{method}-checkpoints.pt")
    vhash = hashlib.sha256()
    stream_update(vhash, validation)
    metadata = {"readout": readout, "training_stream_sha256": hasher.hexdigest(), "training_prefix_sha256": prefixes,
        "bank_sha256": bank_hash, "validation_sha256": vhash.hexdigest(),
        "training_seconds": time.perf_counter()-started, "unique_training_lifetimes": len(bank)*config["batch_size"],
        "training_presentations": config["generations"]*config["batch_size"],
        "development_evaluations_by_budget": counts, "unique_development_evaluations_shared_trajectory": unique_development,
        "budget_selection": {str(b): {"selected_generation": selected[b], "selected_validation_joint_brier": losses_best[b],
            "gradient_updates": b, "training_presentations": b*config["batch_size"]} for b in config["budgets"]},
        "resources": models.resources(method, readout), "training_log": logs}
    print(json.dumps({"trained": method, "seed": seed, "readout": readout, "seconds": metadata["training_seconds"]}), flush=True)
    return checkpoints, metadata


def nn_clip(model, maximum):
    return float(torch.nn.utils.clip_grad_norm_(model.parameters(), maximum))


def restored(method, state, readout):
    if method in METHODS[:2]:
        return models.Small(state, readout)
    model = models.Small(np.zeros(models.PARAMETERS, np.float32), readout)
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


def seen_context(data):
    """Valid only in the shared-trait suites: query context cannot change target probabilities."""
    return dict(data, query_context=data["contexts"][:, 0].copy())


def donor_histories(data, rng):
    """Derange complete histories within query-context and length strata."""
    permutation = np.arange(len(data["x"]))
    for context in range(3):
        for length in np.unique(data["lengths"]):
            rows = np.flatnonzero((data["query_context"] == context) & (data["lengths"] == length))
            if len(rows) == 0:
                continue
            if len(rows) == 1:
                raise ValueError("Cannot derange a singleton stratum")
            order = rng.permutation(rows)
            permutation[order] = np.roll(order, 1)
    if np.any(permutation == np.arange(len(permutation))):
        raise ValueError("Donor history contains its own target")
    changed = dict(data)
    for key in ("x", "lengths", "history_menus", "history_masks", "actions", "voluntary", "success", "observed", "contexts"):
        changed[key] = data[key][permutation].copy()
    return changed, permutation


def run(out, seed, protocol):
    manifest = validate(protocol)
    if seed not in range(CONFIG["replicates"]):
        raise ValueError("Unknown seed")
    configure()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"manifest.json", manifest)
    started = time.perf_counter()
    bank_info = make_bank(seed, CONFIG)
    snapshots, metadata = {}, {}
    readout_order = READOUTS if seed % 2 == 0 else READOUTS[::-1]
    for readout in readout_order:
        folder = out/readout
        folder.mkdir()
        snapshots[readout], metadata[readout], validation, initial = search(seed, CONFIG, folder, readout, bank_info)
        snapshots[readout]["matched_gradient"], metadata[readout]["matched_gradient"] = gradient(
            "matched_gradient", seed, CONFIG, folder, validation, initial, readout, bank_info)
    for key in ("training_stream_sha256", "bank_sha256", "validation_sha256"):
        if len({m[key] for arm in metadata.values() for m in arm.values()}) != 1:
            raise ValueError("Unmatched data: "+key)
    print(json.dumps({"all_training_complete": True, "seed": seed}), flush=True)
    namespace = external.load(protocol/"upstream")
    references, hashes, donor_hashes = {}, {}, {}
    for readout in READOUTS:
        for method in METHODS:
            model = metadata[readout][method]
            model["initial"] = {}
            model["budgets"] = {str(b): {"intact": {}, "no_memory": {}, "donor_history": {},
                                         "drop_extra": {}, "raw_last": {}} for b in CONFIG["budgets"]}
    for suite_index, suite in enumerate(SUITES):
        references[suite], hashes[suite], donor_hashes[suite] = {}, {}, {}
        for length in CONFIG["test_lengths"]:
            seed_index = 0 if suite.startswith("canonical") else suite_index
            rng = np.random.default_rng(seeds_for(seed)["evaluation"]+100*seed_index+length)
            if suite == "external_games":
                data = worlds.external_games(rng, CONFIG["evaluation_lifetimes"], length, namespace)
            else:
                data = worlds.synthetic(rng, CONFIG["evaluation_lifetimes"], length,
                                        suite="canonical" if suite.startswith("canonical") else suite)
            if suite == "canonical_seen":
                data = seen_context(data)
            donors, permutation = donor_histories(data, np.random.default_rng(seeds_for(seed)["donors"]+100*suite_index+length))
            hasher = hashlib.sha256()
            stream_update(hasher, data)
            hashes[suite][str(length)] = hasher.hexdigest()
            donor_hashes[suite][str(length)] = hashlib.sha256(permutation.tobytes()).hexdigest()
            references[suite][str(length)] = {
                "intact": score(worlds.functional_reference(data), data),
                "no_memory": score(worlds.functional_reference(dict(data, lengths=np.zeros(len(data["x"]), dtype=int))), data),
                "donor_history": score(worlds.functional_reference(donors), data)}
            for readout in READOUTS:
                for method in METHODS:
                    record = metadata[readout][method]
                    initial_model = restored(method, snapshots[readout][method][0], readout)
                    record["initial"].setdefault(suite, {})[str(length)] = score(predictions(initial_model, data), data)
                    for budget in CONFIG["budgets"]:
                        cell = record["budgets"][str(budget)]
                        model = restored(method, snapshots[readout][method][budget], readout)
                        for kind, pred in (("intact", predictions(model, data)),
                                           ("no_memory", predictions(model, data, no_memory=True)),
                                           ("donor_history", predictions(model, donors)),
                                           ("drop_extra", predictions(model, data, drop_extra=True))):
                            cell[kind].setdefault(suite, {})[str(length)] = score(pred, data)
                        if suite == "canonical_seen" and length == 24 and method != "random_search":
                            last = restored(method, snapshots[readout][method][f"raw_{budget}"], readout)
                            cell["raw_last"] = {"intact": score(predictions(last, data), data),
                                "no_memory": score(predictions(last, data, no_memory=True), data),
                                "donor_history": score(predictions(last, donors), data)}
        print(json.dumps({"evaluated": suite, "seed": seed}), flush=True)
    diagnostic = worlds.synthetic(np.random.default_rng(seeds_for(seed)["diagnostics"]), CONFIG["diagnostic_lifetimes"], 8)
    final_weights = {str(b): {} for b in CONFIG["budgets"]}
    for budget in CONFIG["budgets"]:
        for readout in READOUTS:
            final_weights[str(budget)][readout] = {}
            for method in METHODS:
                model = restored(method, snapshots[readout][method][budget], readout)
                metadata[readout][method]["budgets"][str(budget)]["diagnostics"] = {
                    "seen": diagnose(model, seen_context(diagnostic)), "heldout": diagnose(model, diagnostic)}
                weights = {key: value.detach().numpy().tolist() for key, value in model.state_dict().items()}
                final_weights[str(budget)][readout][method] = weights
                print("WEIGHTS_JSON:"+json.dumps({"budget": budget, "readout": readout, "method": method, "state": weights}, separators=(",", ":")), flush=True)
    write_json(out/"final-weights.json", {"config_sha256": manifest["config_sha256"], "replicate": seed, "models": final_weights})
    row = {"version": VERSION, "replicate": seed, "config_sha256": manifest["config_sha256"],
           "source_hashes": manifest["source_hashes"], "models": metadata, "references": references,
           "evaluation_hashes": hashes, "donor_permutation_hashes": donor_hashes, "seeds": seeds_for(seed),
           "readout_order": list(readout_order), "bank_order_sha256": hashlib.sha256(bank_info[2].tobytes()).hexdigest(),
           "elapsed_seconds": time.perf_counter()-started, "api_cost_usd": 0}
    write_json(out/f"result-seed-{seed}.json", row)
    print("ROW_JSON:"+json.dumps({k: v for k, v in row.items() if k != "models"}, separators=(",", ":")), flush=True)
    for readout, arm in metadata.items():
        for method, value in arm.items():
            print("MODEL_JSON:"+json.dumps({"readout": readout, "method": method, "value": value}, separators=(",", ":")), flush=True)


def freeze(out, upstream):
    external.verify(upstream)
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        shutil.copyfile(HERE/name, out/name)
    shutil.copytree(upstream, out/"upstream")
    hashes = {name: hashlib.sha256((out/name).read_bytes()).hexdigest() for name in FILES}
    manifest = {"version": VERSION, "config": CONFIG, "config_sha256": digest(CONFIG), "source_hashes": hashes,
                "readouts": READOUTS, "suites": SUITES, "predecessor": PREDECESSOR,
                "unchanged_predecessor_sources": {name: hashes[name] for name in ("models.py", "worlds.py", "external.py", "requirements.txt")},
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


def mean_score(row, readout, method, suite, budget, kind="intact", metric="choice_brier"):
    cells = row["models"][readout][method]["budgets"][str(budget)][kind][suite]
    return float(np.mean([cells[str(n)][metric] for n in CONFIG["primary_lengths"]]))


def contrasts(row):
    values = {}
    low, high = CONFIG["budgets"]
    for suite in SUITES:
        metrics = ("choice_brier",) if suite == "external_games" else ("choice_brier", "execution_brier", "brier")
        for method in METHODS:
            for metric in metrics:
                for readout in READOUTS:
                    def get(budget, kind="intact", m=method, s=suite, a=readout, metric_name=metric):
                        return mean_score(row, a, m, s, budget, kind, metric_name)
                    prefix = f"{suite}/{method}/{readout}/{metric}/"
                    values[prefix+"low_minus_high"] = get(low)-get(high)
                    for budget, label in ((low, "low"), (high, "high")):
                        for kind, effect in (("no_memory", "memory_gain"), ("donor_history", "donor_gain"), ("drop_extra", "extra_gain")):
                            values[prefix+label+"_"+effect] = get(budget, kind)-get(budget)
                    values[prefix+"donor_gain_growth"] = values[prefix+"high_donor_gain"]-values[prefix+"low_donor_gain"]
                prefix = f"{suite}/{method}/readouts/{metric}/"
                for budget, label in ((low, "low"), (high, "high")):
                    values[prefix+label+"_control_minus_interaction"] = mean_score(row, "wide_control", method, suite, budget, metric=metric)-mean_score(row, "interaction", method, suite, budget, metric=metric)
                values[prefix+"advantage_growth"] = values[prefix+"high_control_minus_interaction"]-values[prefix+"low_control_minus_interaction"]
    return values


def primary_rules():
    prefix = "canonical_seen/evolved/interaction/"
    return {prefix+"choice_brier/low_minus_high": 0.,
            prefix+"choice_brier/donor_gain_growth": 0.,
            prefix+"choice_brier/high_donor_gain": 0.,
            prefix+"execution_brier/high_donor_gain": 0.,
            prefix+"execution_brier/low_minus_high": -EXECUTION_MARGIN}


def original_architecture_rules(label):
    prefix = "canonical_seen/evolved/"
    return {prefix+f"readouts/choice_brier/{label}_control_minus_interaction": 0.,
            prefix+f"interaction/choice_brier/{label}_donor_gain": 0.,
            prefix+f"interaction/execution_brier/{label}_donor_gain": 0.,
            prefix+f"readouts/execution_brier/{label}_control_minus_interaction": -EXECUTION_MARGIN}


def bootstrap(values):
    rng = np.random.default_rng(188000000)
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
        for key in ("training_stream_sha256", "bank_sha256", "validation_sha256"):
            if len({m[key] for arm in row["models"].values() for m in arm.values()}) != 1:
                raise ValueError("Unmatched data")
    difference_rows = [contrasts(r) for r in rows]
    differences = {}
    for key in difference_rows[0]:
        v = [r[key] for r in difference_rows]
        differences[key] = {"mean": float(np.mean(v)), "paired_bootstrap_95ci": bootstrap(v), "run_differences": v}
    cells = {suite: {str(budget): {readout: {method: {
        "choice_brier": float(np.mean([mean_score(r, readout, method, suite, budget) for r in rows])),
        "execution_brier": None if suite == "external_games" else float(np.mean([
            mean_score(r, readout, method, suite, budget, metric="execution_brier") for r in rows])),
        "selected_generations": [r["models"][readout][method]["budget_selection"][str(budget)]["selected_generation"] for r in rows]}
        for method in METHODS} for readout in READOUTS} for budget in CONFIG["budgets"]} for suite in SUITES}
    primary = primary_rules()
    original = {label: {"criteria": original_architecture_rules(label),
        "pass": all(differences[k]["paired_bootstrap_95ci"][0] > t for k, t in original_architecture_rules(label).items())}
        for label in ("low", "high")}
    summary = {"version": VERSION, "replicates": len(rows), "final_scores": cells, "contrasts": differences,
               "joint_primary_criteria": primary,
               "joint_primary_pass": all(differences[k]["paired_bootstrap_95ci"][0] > threshold for k, threshold in primary.items()),
               "secondary_original_architecture_checks": original,
               "config_sha256": manifest["config_sha256"], "source_hashes": manifest["source_hashes"], "api_cost_usd": 0}
    out.mkdir(parents=True, exist_ok=False)
    write_json(out/"summary.json", summary)
    write_json(out/"replicate-results.json", rows)
    write_json(out/"manifest.json", manifest)
    lines = ["# Fixed-evidence search-budget pilot", "", "Eight paired runs; 48 training trajectories; 96 budget-selected models; no API calls.", "",
             "| Suite | Steps | Readout | Evolution | Random search | Matched gradient |",
             "|---|---:|---|---:|---:|---:|"]
    for suite, budgets in cells.items():
        for budget, arms in budgets.items():
            for readout, cell in arms.items():
                lines.append("| "+suite+" | "+budget+" | "+readout+" | "+" | ".join(f"{cell[m]['choice_brier']:.6f}" for m in METHODS)+" |")
    lines += ["", "Joint primary criteria satisfied: "+str(summary["joint_primary_pass"]), "",
              "The longer budget replays the same training evidence. Each budget selects among 512 development candidates plus the initial model. External benchmarks and architecture-superiority checks are secondary."]
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
