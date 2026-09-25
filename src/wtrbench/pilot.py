"""Command-line pilot: generate -> run -> score -> markdown report.

    python -m wtrbench.pilot synthetic                 # all synthetic responders (no API)
    python -m wtrbench.pilot debug  MODEL [--resume]   # debug scenario + debug set only
    python -m wtrbench.pilot pilot  MODEL [--resume]   # confirmatory items, one form
    python -m wtrbench.pilot inspect runs/<file>.jsonl # raw answers next to the items

MODEL is an Anthropic model id. Responses go to runs/<mode>_<model>.jsonl with a
.config.json beside it. An existing file is refused unless --resume is given,
in which case only unanswered items are called.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from wtrbench.inference import (
    AGGREGATE_SETS,
    DEBUG_TASKS,
    PILOT_LADDER,
    generate_inference_items,
)
from wtrbench.run import AnthropicResponder, RunExists, load_responses, run
from wtrbench.score import ladder_estimate, report_markdown, score
from wtrbench.synthetic import standard_responders


def _items_for(cfg: dict[str, object]) -> list:
    gen = cfg.get("generator", {})
    assert isinstance(gen, dict)
    ladder = tuple(float(x) for x in gen.get("ladder", PILOT_LADDER))  # type: ignore[union-attr]
    if gen.get("tasks") == "confirmatory":
        return generate_inference_items(ladder=ladder)
    return generate_inference_items(ladder=ladder, tasks=DEBUG_TASKS, set_roles=("debug",))


def inspect_run(path: Path) -> str:
    """Raw answers next to their items: unparsed text, ladder patterns per cell
    with option-order disagreements, and the cells that ended censored or
    unidentified. For reading before anything is frozen."""
    import json as _json

    cfg = _json.loads(path.with_suffix(path.suffix + ".config.json").read_text())
    items = {i.item_id: i for i in _items_for(cfg)}
    resp = load_responses(path)
    lines = [f"# {path.name}  ({len(resp)} responses; model={cfg.get('model')})", ""]
    stops = Counter(r.stop_reason or "not recorded" for r in resp)
    lines += ["## Response collection", "",
              "Stop reasons: " + ", ".join(f"{k}={v}" for k, v in sorted(stops.items())), ""]
    usages = [r.usage for r in resp if r.usage is not None]
    if usages:
        for usage_key in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                          "cache_read_input_tokens"):
            total = sum(v for u in usages if isinstance(v := u.get(usage_key), int))
            lines.append(f"- {usage_key}: {total} "
                         f"(metadata available for {len(usages)}/{len(resp)} responses)")
        lines.append("")
    lines += ["| family | recorded | A | B | unparsed |", "|---|---|---|---|---|"]
    for family in ("attribution", "aggregate"):
        subset = [r for r in resp if r.item_id in items and items[r.item_id].family == family]
        counts = Counter(r.choice for r in subset)
        lines.append(f"| {family} | {len(subset)} | {counts['A']} | {counts['B']} | {counts[None]} |")
    unparsed = [r for r in resp if r.choice is None]
    lines += ["", f"## Unparsed responses: {len(unparsed)}", ""]
    for r in unparsed:
        it = items.get(r.item_id)
        tag = f"{it.family} / {it.probe.value} / {it.cause.value if it.cause else ''}" if it else "?"
        lines.append(f"- [{r.item_id}; {tag}; stop={r.stop_reason or 'not recorded'}] {r.raw!r}")
    cells: dict[tuple, list] = {}
    for r in resp:
        it = items.get(r.item_id)
        if it is None or it.probe.value != "p_infer":
            continue
        key: tuple[str, ...] = (it.family, it.task.value if it.task else AGGREGATE_SETS[it.agg_set].name,  # type: ignore[index]
               it.cause.value if it.cause else f"{it.diagnostic.value}/{it.totals.value}")  # type: ignore[union-attr]
        if it.family == "aggregate":
            # Each evidence order has its own A/B pair. Pooling them here
            # would silently overwrite one order's answers in by_r below.
            key += ("swapped" if it.choices_swapped else "original",)
        cells.setdefault(key, []).append((it.realized_ratio, it.keyed_option, r.keyed))
    head = ("## Inferred-WTR ladders (K = partner keeps own payoff, . = gives; "
            "shown as keyed-A then keyed-B at each rung)")
    cols = "| cell | pattern by rung | order disagreements / complete pairs | fit |"
    lines += ["", head, "", cols, "|---|---|---|---|"]
    for key, pts in sorted(cells.items()):
        by_r: dict[float, dict[str, bool | None]] = {}
        for ratio, opt, keyed in pts:
            by_r.setdefault(ratio, {})[opt] = keyed
        pat = " ".join(
            f"{r:g}:{_sym(v.get('A'))}{_sym(v.get('B'))}" for r, v in sorted(by_r.items())
        )
        complete = [v for v in by_r.values() if v.get("A") is not None and v.get("B") is not None]
        dis = sum(v["A"] != v["B"] for v in complete)
        pair_count = f"{dis}/{len(complete)}" if complete else "— (0 complete)"
        est = ladder_estimate([(r, k) for r, _, k in pts])
        fit = (est.censored if est.censored != "none"
               else f"{est.lower:g}-{est.upper:g}" if est.identified else "unidentified")
        lines.append(f"| {' / '.join(key)} | {pat} | {pair_count} | {fit} (viol {est.violations}) |")
    lines += ["", ("Only rungs with two parsed answers enter the option-order denominator. "
              "Missing responses can make a threshold fit look more precise by removing "
              "conflicting answers; inspect coverage, order effects and violations before "
              "interpreting any fitted bound.")]
    return "\n".join(lines)


def _sym(k: bool | None) -> str:
    return "?" if k is None else ("K" if k else ".")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("synthetic", "debug", "pilot", "inspect"):
        print(__doc__)
        return 2
    mode = argv[0]
    out = Path("runs")
    out.mkdir(exist_ok=True)
    if mode == "inspect":
        if len(argv) < 2:
            print("path to a runs/*.jsonl required")
            return 2
        print(inspect_run(Path(argv[1])))
        return 0
    if mode == "synthetic":
        items = generate_inference_items(ladder=PILOT_LADDER)
        for r in standard_responders():
            name = r.name
            rep = score(items, run(items, r, name), name)  # type: ignore[arg-type]
            (out / f"synthetic_{name}.md").write_text(report_markdown(rep))
            v, a = rep.required_valuation, rep.required_ability
            print(f"{name:24s} valuation {v.n_consistent}/{v.n_units}  ability "
                  f"{a.n_consistent}/{a.n_units}  diag "
                  f"{[f'{s.n_consistent}/{s.n_units}' for s in rep.diagnostic_by_set]}")
        return 0
    if len(argv) < 2:
        print("MODEL required")
        return 2
    model = argv[1]
    resume = "--resume" in argv[2:]
    if mode == "debug":
        gen = {"ladder": PILOT_LADDER, "tasks": [t.value for t in DEBUG_TASKS],
               "set_roles": ["debug"], "form": 0}
        items = generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))
    else:
        gen = {"ladder": PILOT_LADDER, "tasks": "confirmatory", "set_roles": "confirmatory",
               "form": 0}
        items = generate_inference_items(ladder=PILOT_LADDER)
    responder = AnthropicResponder(model)
    tag = f"{mode}_{model}".replace("/", "_")
    print(f"{mode}: {len(items)} items -> runs/{tag}.jsonl")
    try:
        responses = run(items, responder, responder.name, out / f"{tag}.jsonl", resume=resume,
                        config={"mode": mode, "model": model, "generator": gen,
                                "request": responder.request_config})
    except RunExists as e:
        print(f"{e}\nRe-run with --resume to finish it, or move the file aside.")
        return 1
    rep = score(items, responses, responder.name)
    (out / f"{tag}.md").write_text(report_markdown(rep))
    print(report_markdown(rep).split("### Descriptive")[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
