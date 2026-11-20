# Forecasts of a sealed decision after a later coin toss

Claude Sonnet 4.5 kept its forecast stable across the two coin outcomes on **9 of 12 matched forms**. On the other **3 of 12**, changing only the reported draw made it switch toward the helper whose earlier work actually benefited the target. Both repetitions showed each switch. The model answered both matched factual controls correctly for all three switches.

| Setting | Stable forecasts | Repeated switch toward the actual outcome | Exact-repeat agreement | Factual answers correct |
|---|---:|---:|---:|---:|
| Breakfast | 3/4 | 1/4 | 8/8 | 7/8 |
| Camera | 3/4 | 1/4 | 8/8 | 8/8 |
| Archive | 3/4 | 1/4 | 8/8 | 8/8 |
| Total | 9/12 | 3/12 | 24/24 | 23/24 |

For the 11 forms with both factual controls correct, eight had stable forecasts and three had reproducible shifts. On the remaining breakfast form the model described a second, nonexistent swap in its factual answer. The recorded forecast was stable. All 72 responses selected one of the named helpers. No answers were missing, invalid, refused or truncated.

## Which helper the model selected

When the draw preserved the original assignments, all 24 forecast responses favored the helper who could expect to benefit the target. When the draw exchanged assignments, 18 of 24 still favored that helper and six favored the helper whose work ended up benefiting the target. The six responses arose from three forms, each run twice. Across the two coin outcomes, 36 of 48 crossed repeat comparisons agreed. These are correlated comparisons within 12 matched forms. The prespecified signed effect averaged +0.25, with nine forms at zero and three at +1. No form shifted in the opposite direction or had inconsistent repeats.

## What the three shifts have in common

All three shifts occurred in **form 3** (zero-based numbering). This exploratory comparison identifies a shared arrangement: the question targeted the second-listed recipient and the allocation of jobs to the helpers was reversed from form 0. The same switch occurred with different names and different answer letters across settings. The current design cannot attribute the pattern to a single presentation feature. It is also too small to estimate an error rate across social situations.

For example, Mira prepared the noon kit expecting it to go to Noor. When the draw kept the assignments, both forecasts favored Mira as the person who had sealed a gift to Noor. When the draw sent Jon's dawn kit to Noor instead, both forecasts favored Jon. A returned explanation invoked a feeling of reciprocity from Noor receiving Jon's kit. The point decision was already irrevocable, and the fair coin was independent of it. An observer could reasonably favor either helper before the draw; the draw supplies no new evidence about that earlier choice.

## Explanation audit

A single reviewer read all 72 brief explanations in shuffled order with the recorded answer field hidden. The question type, target and answer-option mapping were available. Of 48 forecast explanations, 47 endorsed the recorded choice and one described a stronger connection without explicitly endorsing a forecast. All 24 factual explanations endorsed the recorded choice. There were **zero clear answer–explanation conflicts**. Agreement describes the conclusion expressed in the text and is compatible with factual errors or faulty causal reasoning. The original choices determine every primary score. [Item-level coding](basis-audit.csv)

## Run and cost

[Collection and raw artifact](https://github.com/msblanders/wtr-bench/actions/runs/44655842458). Model `claude-sonnet-4-5-20250929` returned 72 unique message IDs in 72 attempts. Reported usage was 40,080 input and 6,009 output tokens, or **$0.210375** at the study rates. The archive matched GitHub's SHA-256 digest `f07c53b6bcc51c8d239981af08a290dc3e9fd10d9ac156668cd2de8d17eaa5a3`. The sent request bank matched the frozen file digest and regenerated payloads byte for byte. Rescoring all saved responses reproduced the aggregate and item-level results.
