# Recipient order and helper assignment

Claude Sonnet 4.5 reproduced the earlier switch on the exact breakfast and camera prompts. On the exact archive prompts, both stand forecasts favored the original helper. The two swap forecasts split between the other helper and “equally likely.” Across the historical cases, 11 of 12 forecast answers and all six factual answers matched the previous collection.

## Primary comparison

A reproducible switch means that both forecasts when the draw kept the assignments in place favored the helper initially associated with the target, and both forecasts under an exchange favored the other helper. Every sealed decision preceded the independent draw in both conditions. “Stable” requires the same semantic choice on all four forecasts. “Mixed” means two identical prompts produced different choices.

| Target position in the roster | Who did which job | Switch toward later outcome | Stable | Mixed repeats |
|---|---|---:|---:|---:|
| First | As in earlier switch | 1/3 | 1/3 | 1/3 |
| Second | As in earlier switch | 2/3 | 0/3 | 1/3 |
| First | Helper jobs exchanged | 0/3 | 2/3 | 1/3 |
| Second | Helper jobs exchanged | 0/3 | 2/3 | 1/3 |

With the earlier helper–job assignment, the target-second condition yielded 2/3 switches and target-first yielded 1/3. With the jobs exchanged, both positions yielded 0/3. At the first position the allocation difference was one of three stories; at the second position it was two of three. The prespecified difference of these position contrasts was +1/3 (about 33 percentage points). All 12 forms had complete data. These are descriptive comparisons across three stories selected because of the earlier pattern.

Breakfast switched with either roster order under the earlier allocation. Camera switched reproducibly only when the target was second and the earlier allocation was preserved. Archive produced no repeatable switch. Exchanging jobs removed all repeatable switches, but two exchanged-job comparisons still had variable answers. Job allocation and the order in which the helper names occur on the fixed job lines change together in this primary comparison.

## Same work described in the opposite sentence order

In this secondary check the exact same work and recipients were described with the two whole action sentences in the opposite order. There was one forecast per coin outcome.

| Target position | Helper allocation | Primary breakfast / camera / archive | Reordered sentences, breakfast / camera / archive |
|---|---|---|---|
| First | Exchanged | stable / mixed / stable | stable / stable / stable |
| First | Earlier | switch / stable / mixed | stable / stable / stable |
| Second | Exchanged | stable / mixed / stable | stable / stable / stable |
| Second | Earlier | switch / switch / mixed | switch / stable / stable |

Only the breakfast case with the target second and the earlier job allocation switched in this single-pass comparison. Eleven of 12 reordered cases gave the same forecast across outcomes. Of the eight primary cases with consistent repeats under both outcomes, six had the same switch/stability classification after reordering. A single pass cannot distinguish repeat variability from a presentation effect on any specific reordered case. In the reordered camera anchor, both outcomes favored the helper who originally expected to help the other recipient, illustrating that an invariant forecast can still differ from the usual directional prediction.

## Comprehension, repeatability and scope

All 24 primary factual answers were correct, including both controls for all three reproducible switches. Exact forecast repeats agreed on 20 of 24 comparisons. All four disagreements occurred after an exchange. There were five stable primary forms, three reproducible outcome-following forms and four mixed forms. No form showed a reproducible shift in the opposite direction. All 96 responses were valid and scored. The study tests one model snapshot with one fixed target per setting. The two roster orders and two job allocations are within-story manipulations; the 96 responses do not represent 96 independent stories.

## Verification

[GitHub Actions collection 44665592236](https://github.com/msblanders/wtr-bench/actions/runs/44665592236) made 96 attempts and returned 96 unique provider message IDs. Usage was 53,384 input tokens and 8,451 output tokens, costing **$0.286917** against the $1 guard. The raw archive matched GitHub’s SHA-256 digest `adeb14ec1da5cdb08affac49400e9b05b8ef6f967bfd574ccffd2b86976e047c`. The request stream matched the frozen bank byte for byte. Replaying the scorer and independently mapping named helpers from the prompt text reproduced the primary classifications, mirror classifications and factual scores.
