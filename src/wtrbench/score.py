"""Scoring for the inference module.

Ladders: a Guttman threshold fit per cell. The keyed response (partner takes
own payoff) is predicted iff ratio > w. Candidate thresholds are the gaps
between rungs plus one below the lowest and one above the highest; the fit
picks the candidates with the fewest misclassifications.

- Exactly one best candidate, interior: identified. Interval = that gap; the
  point estimate is its geometric midpoint.
- Exactly one best candidate at an end: censored (left: w below the lowest
  rung; right: w above the highest). Interval is one-sided; no point estimate.
- Several best candidates: unidentified. Interval = the union of the tied
  gaps; no point estimate. An always-A responder lands here at every cell.

Contrasts between two ladder cells are decided from the intervals, never from
point estimates: a - b is positive only if a's whole interval lies at or above
b's, negative only if the reverse, and otherwise undetermined. Censored cells
therefore enter as bounds, and a bound can still decide a contrast (a refusal
left-censored at 0.1 against an interior 0.5-1.0 is a determinate positive).
A point difference is reported alongside only when both cells are identified.

Predicted signs exist only for the preregistered comparisons. Descriptive
comparisons carry no predicted sign and no "consistent" count.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from itertools import pairwise
from typing import Literal

from pydantic import BaseModel

from wtrbench.inference import (
    AGGREGATE_SETS,
    Cause,
    Diagnostic,
    InferenceItem,
    Probe,
    Task,
    Totals,
)
from wtrbench.run import Response

Censor = Literal["none", "left", "right"]
Sign = Literal["+", "-", "0", "undetermined"]


class LadderEstimate(BaseModel):
    identified: bool
    estimate: float | None  # only when identified and uncensored
    lower: float | None  # None = unbounded below (left-censored)
    upper: float | None  # None = unbounded above (right-censored)
    censored: Censor
    violations: int
    n: int
    n_missing: int


def ladder_estimate(points: list[tuple[float, bool | None]]) -> LadderEstimate:
    obs = sorted((r, k) for r, k in points if k is not None)
    n_missing = sum(1 for _, k in points if k is None)
    if not obs:
        return LadderEstimate(identified=False, estimate=None, lower=None, upper=None,
                              censored="none", violations=0, n=0, n_missing=n_missing)
    rungs = sorted({r for r, _ in obs})
    cands: list[tuple[float | None, float | None]] = [(None, rungs[0])]
    cands += list(pairwise(rungs))
    cands += [(rungs[-1], None)]
    errors = []
    for lo, _hi in cands:
        w = -math.inf if lo is None else lo
        errors.append(sum(1 for r, k in obs if (r > w) != k))
    min_err = min(errors)
    best = [c for c, e in zip(cands, errors, strict=True) if e == min_err]
    lo, hi = best[0][0], best[-1][1]
    if len(best) > 1:
        return LadderEstimate(identified=False, estimate=None, lower=lo, upper=hi,
                              censored="none", violations=min_err, n=len(obs),
                              n_missing=n_missing)
    if lo is None:
        return LadderEstimate(identified=True, estimate=None, lower=None, upper=hi,
                              censored="left", violations=min_err, n=len(obs),
                              n_missing=n_missing)
    if hi is None:
        return LadderEstimate(identified=True, estimate=None, lower=lo, upper=None,
                              censored="right", violations=min_err, n=len(obs),
                              n_missing=n_missing)
    return LadderEstimate(identified=True, estimate=math.sqrt(lo * hi), lower=lo, upper=hi,
                          censored="none", violations=min_err, n=len(obs), n_missing=n_missing)


class BinaryEstimate(BaseModel):
    proportion: float | None
    n: int
    n_missing: int


def binary_estimate(keyed: list[bool | None]) -> BinaryEstimate:
    obs = [k for k in keyed if k is not None]
    return BinaryEstimate(proportion=(sum(obs) / len(obs)) if obs else None, n=len(obs),
                          n_missing=len(keyed) - len(obs))


class Contrast(BaseModel):
    unit: str
    sign: Sign
    min_abs: float | None  # lower bound on |a - b| implied by the intervals
    point: float | None  # a - b using point estimates, only when both identified
    note: str = ""


def ladder_contrast(a: LadderEstimate, b: LadderEstimate, unit: str) -> Contrast:
    notes = [f"a:{a.censored}" for _ in [0] if a.censored != "none"]
    notes += [f"b:{b.censored}" for _ in [0] if b.censored != "none"]
    notes += ["a:unidentified"] if not a.identified else []
    notes += ["b:unidentified"] if not b.identified else []
    if a.n == 0 or b.n == 0:
        return Contrast(unit=unit, sign="undetermined", min_abs=None, point=None, note="missing")
    point = (a.estimate - b.estimate) if (a.estimate is not None and b.estimate is not None) else None
    if a.lower is not None and b.upper is not None and a.lower >= b.upper:
        return Contrast(unit=unit, sign="+", min_abs=a.lower - b.upper, point=point,
                        note=" ".join(notes))
    if a.upper is not None and b.lower is not None and a.upper <= b.lower:
        return Contrast(unit=unit, sign="-", min_abs=b.lower - a.upper, point=point,
                        note=" ".join(notes))
    return Contrast(unit=unit, sign="undetermined", min_abs=None, point=point,
                    note=" ".join(notes + ["intervals overlap"]))


def binary_contrast(a: BinaryEstimate, b: BinaryEstimate, unit: str) -> Contrast:
    if a.proportion is None or b.proportion is None:
        return Contrast(unit=unit, sign="undetermined", min_abs=None, point=None, note="missing")
    d = a.proportion - b.proportion
    sign: Sign = "+" if d > 0 else "-" if d < 0 else "0"
    return Contrast(unit=unit, sign=sign, min_abs=abs(d), point=d)


class Summary(BaseModel):
    label: str
    predicted_sign: Literal["+", "-"] | None  # None = descriptive
    values: list[Contrast]
    n_units: int
    n_consistent: int | None  # None for descriptive comparisons
    n_undetermined: int
    median_point: float | None
    boot_lower: float | None
    boot_upper: float | None


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def summarize(label: str, predicted: Literal["+", "-"] | None, contrasts: list[Contrast],
              boot: int = 2000, seed: int = 0) -> Summary:
    n_und = sum(1 for c in contrasts if c.sign == "undetermined")
    consistent = None if predicted is None else sum(1 for c in contrasts if c.sign == predicted)
    pts = [c.point for c in contrasts if c.point is not None]
    med = _median(pts) if pts else None
    lo = hi = None
    if len(pts) >= 2 and boot > 0:
        rng = random.Random(seed)
        meds = sorted(_median([rng.choice(pts) for _ in pts]) for _ in range(boot))
        lo, hi = meds[int(0.025 * boot)], meds[int(0.975 * boot) - 1]
    return Summary(label=label, predicted_sign=predicted, values=contrasts, n_units=len(contrasts),
                   n_consistent=consistent, n_undetermined=n_und, median_point=med,
                   boot_lower=lo, boot_upper=hi)


class AttributionCell(BaseModel):
    task: Task
    cause: Cause
    infer: LadderEstimate
    will_same: BinaryEstimate
    will_diff: BinaryEstimate
    able_same: BinaryEstimate
    able_diff: BinaryEstimate


class AggregateCell(BaseModel):
    agg_set: int
    set_name: str
    role: str
    diagnostic: Diagnostic
    totals: Totals
    infer: LadderEstimate  # pooled over both choice orders
    infer_by_order: dict[str, LadderEstimate]


class ScoreReport(BaseModel):
    responder: str
    n_items: int
    n_missing: int
    attribution: list[AttributionCell]
    aggregate: list[AggregateCell]
    required_valuation: Summary  # per scenario: w[unable] - w[unwilling], predicted +
    required_ability: Summary  # per scenario: able_same[unwilling] - able_same[unable], predicted +
    diagnostic_by_set: list[Summary]  # per set: w[LOW] - w[HIGH] within totals row, predicted -
    descriptive: dict[str, Summary]  # everything else; no predicted sign


def score(items: list[InferenceItem], responses: list[Response], responder: str = "") -> ScoreReport:
    by_id: dict[str, Response] = {}
    for r in responses:
        if r.item_id in by_id:
            raise ValueError(f"duplicate response for item {r.item_id}")
        by_id[r.item_id] = r
    attr: dict[tuple[Task, Cause], dict[Probe, list]] = defaultdict(lambda: defaultdict(list))
    aggr: dict[tuple[int, Diagnostic, Totals], dict[bool, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    n_missing = 0
    for it in items:
        resp = by_id.get(it.item_id)
        keyed = None if resp is None else resp.keyed
        if keyed is None:
            n_missing += 1
        if it.family == "attribution":
            assert it.task is not None and it.cause is not None
            if it.probe in (Probe.INFER, Probe.OWN):
                attr[(it.task, it.cause)][it.probe].append((it.realized_ratio, keyed))
            else:
                attr[(it.task, it.cause)][it.probe].append(keyed)
        elif it.probe is Probe.INFER:
            assert it.agg_set is not None and it.diagnostic and it.totals
            assert it.choices_swapped is not None
            aggr[(it.agg_set, it.diagnostic, it.totals)][it.choices_swapped].append(
                (it.realized_ratio, keyed)
            )

    cells = [
        AttributionCell(
            task=task, cause=cause,
            infer=ladder_estimate(p[Probe.INFER]),
            will_same=binary_estimate(p[Probe.WILL_SAME]),
            will_diff=binary_estimate(p[Probe.WILL_DIFF]),
            able_same=binary_estimate(p[Probe.ABLE_SAME]),
            able_diff=binary_estimate(p[Probe.ABLE_DIFF]),
        )
        for (task, cause), p in sorted(attr.items(), key=lambda kv: (kv[0][0].value, kv[0][1].value))
    ]
    acells = [
        AggregateCell(
            agg_set=k, set_name=AGGREGATE_SETS[k].name, role=AGGREGATE_SETS[k].role,
            diagnostic=d, totals=t, infer=ladder_estimate(o[False] + o[True]),
            infer_by_order={"original": ladder_estimate(o[False]),
                            "swapped": ladder_estimate(o[True])},
        )
        for (k, d, t), o in sorted(aggr.items(),
                                   key=lambda kv: (kv[0][0], kv[0][1].value, kv[0][2].value))
    ]

    get = {(c.task, c.cause): c for c in cells}
    tasks = sorted({c.task for c in cells}, key=lambda x: x.value)

    def have(t: Task, *cs: Cause) -> bool:
        return all((t, c) in get for c in cs)

    req_val = [ladder_contrast(get[(t, Cause.UNABLE)].infer, get[(t, Cause.UNWILLING)].infer, t.value)
               for t in tasks if have(t, Cause.UNABLE, Cause.UNWILLING)]
    req_abl = [binary_contrast(get[(t, Cause.UNWILLING)].able_same,
                               get[(t, Cause.UNABLE)].able_same, t.value)
               for t in tasks if have(t, Cause.UNABLE, Cause.UNWILLING)]

    aget = {(c.agg_set, c.diagnostic, c.totals): c for c in acells}
    sets = sorted({c.agg_set for c in acells})
    diag_sums = [
        summarize(f"{AGGREGATE_SETS[k].name} ({AGGREGATE_SETS[k].role}): w[LOW] - w[HIGH]", "-",
                  [ladder_contrast(aget[(k, Diagnostic.LOW, t)].infer,
                                   aget[(k, Diagnostic.HIGH, t)].infer, t.value) for t in Totals],
                  boot=0)
        for k in sets
    ]

    descriptive: dict[str, Summary] = {}
    for k in sets:
        label = f"{AGGREGATE_SETS[k].name}: w[T1] - w[T2] (totals, descriptive)"
        descriptive[label] = summarize(label, None, [
            ladder_contrast(aget[(k, d, Totals.T1)].infer, aget[(k, d, Totals.T2)].infer, d.value)
            for d in Diagnostic], boot=0)
    for k in sets:
        base_name = AGGREGATE_SETS[k].scales
        if base_name is None:
            continue
        base = next((j for j in sets if AGGREGATE_SETS[j].name == base_name), None)
        if base is None:
            continue
        label = f"{AGGREGATE_SETS[k].name} - {base_name}: stakes (descriptive)"
        descriptive[label] = summarize(label, None, [
            ladder_contrast(aget[(k, d, t)].infer, aget[(base, d, t)].infer, f"{d.value}/{t.value}")
            for d in Diagnostic for t in Totals], boot=0)

    def attr_rows(label: str, field: str, a: Cause, b: Cause) -> None:
        rows: list[Contrast] = []
        for t in tasks:
            if not have(t, a, b):
                continue
            ea, eb = getattr(get[(t, a)], field), getattr(get[(t, b)], field)
            rows.append(ladder_contrast(ea, eb, t.value) if field == "infer"
                        else binary_contrast(ea, eb, t.value))
        descriptive[label] = summarize(label, None, rows)

    attr_rows("infer: unwilling - baseline", "infer", Cause.UNWILLING, Cause.BASELINE)
    attr_rows("infer: unable - baseline", "infer", Cause.UNABLE, Cause.BASELINE)
    attr_rows("infer: constrained - baseline", "infer", Cause.CONSTRAINED, Cause.BASELINE)
    attr_rows("infer: helped - baseline", "infer", Cause.HELPED, Cause.BASELINE)
    attr_rows("will_same: unable - unwilling", "will_same", Cause.UNABLE, Cause.UNWILLING)
    attr_rows("will_diff: unable - unwilling", "will_diff", Cause.UNABLE, Cause.UNWILLING)
    attr_rows("able_diff: unwilling - unable (transfer control)", "able_diff",
              Cause.UNWILLING, Cause.UNABLE)

    return ScoreReport(
        responder=responder, n_items=len(items), n_missing=n_missing,
        attribution=cells, aggregate=acells,
        required_valuation=summarize("infer: unable - unwilling", "+", req_val),
        required_ability=summarize("able_same: unwilling - unable", "+", req_abl),
        diagnostic_by_set=diag_sums, descriptive=descriptive,
    )


def report_markdown(rep: ScoreReport) -> str:
    def f(x: float | None) -> str:
        return "—" if x is None else f"{x:.2f}"

    def row(s: Summary) -> str:
        cons = "—" if s.n_consistent is None else f"{s.n_consistent}/{s.n_units}"
        ci = "" if s.boot_lower is None else f" [{f(s.boot_lower)}, {f(s.boot_upper)}]"
        pred = s.predicted_sign or "(descriptive)"
        return (f"| {s.label} | {pred} | {cons} | {s.n_undetermined}/{s.n_units} | "
                f"{f(s.median_point)}{ci} |")

    hdr = ["| contrast | predicted | consistent | undetermined | median point diff [boot 95%] |",
           "|---|---|---|---|---|"]
    lines = [f"## Responder: {rep.responder}", "",
             f"Items: {rep.n_items}; missing/unparsed: {rep.n_missing}", "",
             "### Required contrasts (unit = scenario; sign decided from intervals)", "", *hdr,
             row(rep.required_valuation), row(rep.required_ability), "",
             "### Aggregate: tradeoff pattern at matched totals (unit = totals row, within set)",
             "", *hdr, *[row(s) for s in rep.diagnostic_by_set], "",
             "### Descriptive comparisons (no predicted sign)", "", *hdr,
             *[row(s) for s in rep.descriptive.values()], "",
             "### Attribution cells", "",
             "| scenario | cause | w interval | point | status | viol. | will_same | able_same |",
             "|---|---|---|---|---|---|---|---|"]
    for c in rep.attribution:
        e = c.infer
        status = e.censored if e.censored != "none" else ("ok" if e.identified else "unidentified")
        lines.append(f"| {c.task.value} | {c.cause.value} | {f(e.lower)}–{f(e.upper)} | "
                     f"{f(e.estimate)} | {status} | {e.violations} | "
                     f"{f(c.will_same.proportion)} | {f(c.able_same.proportion)} |")
    return "\n".join(lines)
