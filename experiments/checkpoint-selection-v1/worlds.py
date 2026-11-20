"""Observable histories and future outcomes; latent values are evaluation-only."""
from __future__ import annotations

import numpy as np

INPUTS = 15
SUITES = ("canonical", "shifted", "local_preferences", "correlated_traits", "preference_reversal", "external_games")


def softmax(x, mask=None):
    x = np.where(mask, x, -1e30) if mask is not None else x
    p = np.exp(x-x.max(-1, keepdims=True))
    return p/p.sum(-1, keepdims=True)


def sample(p, rng):
    return (rng.random(p.shape[:-1])[..., None] > p.cumsum(-1)).sum(-1).clip(0, p.shape[-1]-1)


def encode(menus, masks, actions, voluntary, success, observed, contexts):
    """Shared, fixed observation interface; no inferred trait or cue-eligibility labels."""
    count = masks.sum(-1)
    mean = (menus*masks[..., None]).sum(-2)/count[..., None]
    centered = menus-mean[..., None, :]
    variance = (centered**2*masks[..., None]).sum(-2)/count[..., None]
    covariance = (centered[..., 0]*centered[..., 1]*masks).sum(-1)/count
    chosen = np.take_along_axis(menus, actions[..., None, None], axis=-2)[..., 0, :]
    scalars = np.stack((voluntary, actions != 0, success), axis=-1)
    numbers = np.concatenate((chosen/4, mean/4, np.sqrt(variance)/4, covariance[..., None]/16), axis=-1)
    return np.concatenate((scalars, np.arcsinh(numbers), np.log(count)[..., None],
                           np.eye(3)[contexts], observed[..., None]), axis=-1).astype(np.float32)


def pack(history, masks, actions, voluntary, success, observed, contexts, query, query_mask,
         query_context, target_choice, target_ability, lengths, truth_choice, truth_ability):
    x = encode(history, masks, actions, voluntary, success, observed, contexts)
    x[np.arange(x.shape[1])[None, :] >= lengths[:, None]] = 0
    return {"x": x, "lengths": lengths, "query": query.astype(np.float32), "query_mask": query_mask,
            "query_context": query_context, "y_choice": target_choice, "y_ability": target_ability.astype(np.float32),
            "history_menus": history, "history_masks": masks, "actions": actions,
            "voluntary": voluntary, "success": success, "observed": observed, "contexts": contexts,
            "truth_choice": truth_choice, "truth_ability": truth_ability}


def synthetic(rng, size, length, suite="canonical", training=False):
    if suite not in SUITES[:-1]:
        raise ValueError(suite)
    rho = rng.random((size, 3))
    ability = rng.random(size)
    if suite != "local_preferences":
        rho[:] = rho[:, :1]
    if suite == "correlated_traits":
        rho[:] = ability[:, None]
    heldout = rng.integers(0, 3, size)
    contexts = (heldout[:, None]+1+rng.integers(0, 2, (size, length))) % 3
    habitat = rng.integers(0, 3, size)
    cost_ranges = np.array([[.2, 1.2], [.5, 2.0], [0.0, .8]])[habitat]
    benefit_ranges = np.array([[2., 4.], [.5, 3.], [1., 2.]])[habitat]
    if suite == "shifted":
        cost_ranges[:] = [1., 3.]
        benefit_ranges[:] = [1., 5.]
    cost = rng.uniform(cost_ranges[:, :1], cost_ranges[:, 1:], (size, length+1))
    benefit = rng.uniform(benefit_ranges[:, :1], benefit_ranges[:, 1:], (size, length+1))
    menus = np.zeros((size, length+1, 2, 2))
    menus[:, :, 1, 0], menus[:, :, 1, 1] = -cost, benefit
    q_context = rng.integers(0, 3, size) if training else heldout
    history_rho = np.take_along_axis(rho, contexts, axis=1)
    future_rho = rho[np.arange(size), q_context]
    if suite == "preference_reversal":
        history_rho[:, length//2:] = 1-history_rho[:, length//2:]
        future_rho = 1-future_rho
    utility = menus[:, :length, :, 0]+history_rho[..., None]*menus[:, :length, :, 1]
    policy = softmax(utility)
    assignment_rates = np.array([[.15, .85, .5], [.5, .5, .5], [.85, .15, .5]])[habitat]
    assignment = np.take_along_axis(assignment_rates, contexts, axis=1)
    if suite == "shifted":
        assignment[:] = np.where(habitat[:, None] == 0, .05, .95)
    voluntary = rng.random((size, length)) >= assignment
    actions = np.where(voluntary, sample(policy, rng), 1)
    attempted = actions != 0
    observed = attempted & (rng.random((size, length)) < .8)
    success = observed & (rng.random((size, length)) < ability[:, None])
    query = menus[:, -1]
    q_policy = softmax(query[..., 0]+future_rho[:, None]*query[..., 1])
    y_choice = sample(q_policy, rng)
    y_ability = (rng.random(size) < ability).astype(np.float32)
    lengths = rng.choice([0, 4, 12, 24], size=size) if training else np.full(size, length)
    if lengths.max() > length:
        raise ValueError("Short padding")
    return pack(menus[:, :length], np.ones((size, length, 2), dtype=bool), actions, voluntary, success,
                observed, contexts, query, np.ones((size, 2), dtype=bool), q_context, y_choice, y_ability,
                lengths, q_policy, ability)


def external_games(rng, size, length, namespace):
    from external import actor, sample_menu

    kinds = rng.integers(0, 2, size)
    heldout = rng.integers(0, 3, size)
    contexts = (heldout[:, None]+1+rng.integers(0, 2, (size, length))) % 3
    all_menus, all_policies, actions = [], [], []
    for kind in kinds:
        agent = actor(namespace, kind)
        row_menus, row_policies, row_actions = [], [], []
        for _ in range(length+1):
            game = sample_menu(namespace, rng)
            menu = np.array([game.payoffs[a] for a in game.actions])
            probabilities = agent.decide_likelihood(game, [0, 1], tremble=game.tremble)
            row_menus.append(menu)
            row_policies.append(probabilities)
            row_actions.append(int(rng.choice(len(menu), p=probabilities)))
        all_menus.append(row_menus)
        all_policies.append(row_policies[-1])
        actions.append(row_actions)
    width = max(len(m) for row in all_menus for m in row)
    menus = np.zeros((size, length+1, width, 2))
    masks = np.zeros((size, length+1, width), dtype=bool)
    policy = np.zeros((size, width))
    for i, row in enumerate(all_menus):
        for t, menu in enumerate(row):
            menus[i, t, :len(menu)] = menu
            masks[i, t, :len(menu)] = True
        policy[i, :len(row[-1])] = all_policies[i]
    actions = np.array(actions)
    data = pack(menus[:, :length], masks[:, :length], actions[:, :length], np.ones((size, length), bool),
                np.zeros((size, length)), np.zeros((size, length), bool), contexts, menus[:, -1], masks[:, -1],
                heldout, actions[:, -1], np.full(size, -1.), np.full(size, length), policy, np.full(size, np.nan))
    data["upstream_actor_counts"] = np.bincount(kinds, minlength=2).tolist()
    return data


def functional_reference(data):
    """Supplied shared-trait Bayesian rule: 81-point rho grid, Beta(1,1) execution.

    Deliberately uses the same assumptions in every suite; not an external-family oracle.
    """
    grid = np.linspace(0, 1, 81)
    b, t, _k, _ = data["history_menus"].shape
    log_weight = np.zeros((b, len(grid)))
    # Trapezoidal uniform-prior quadrature on the endpoints.
    log_weight[:, [0, -1]] = np.log(.5)
    for n in range(t):
        m = data["history_menus"][:, n]
        u = m[:, None, :, 0]+grid[None, :, None]*m[:, None, :, 1]
        p = softmax(u, data["history_masks"][:, n, None])
        chosen = np.take_along_axis(p, data["actions"][:, n, None, None], -1)[..., 0]
        eligible = data["voluntary"][:, n] & (n < data["lengths"])
        log_weight += np.log(chosen.clip(1e-30))*eligible[:, None]
    weights = softmax(log_weight)
    q = data["query"]
    policy = softmax(q[:, None, :, 0]+grid[None, :, None]*q[:, None, :, 1], data["query_mask"][:, None])
    choice = (weights[..., None]*policy).sum(1)
    mask = data["observed"] & (np.arange(t)[None, :] < data["lengths"][:, None])
    ability = (1+(mask*data["success"]).sum(1))/(2+mask.sum(1))
    return choice, ability
