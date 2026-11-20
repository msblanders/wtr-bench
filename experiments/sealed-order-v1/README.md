# Recipient order and helper assignment in forecasts of a sealed choice

In the preceding experiment, Claude Sonnet 4.5 reproducibly changed its forecast after a later independent draw in one presentation form in each of three stories. This follow-up asks which properties of that form travel with the error.

## Design frozen before collection

Within each story, keep the named target fixed at Noor, Leon, or Drew, respectively. Keep the recipient-to-job mapping, wording of each job, answer options and sealed decision fixed. Cross two factors:

1. List the target first or second in the original roster sentence. Reverse the two entire recipient–job phrases so that their assignments stay the same.
2. Keep the original error form's allocation of jobs to helpers (anchor assignment), or exchange the helpers. In the primary comparisons each job stays on the same line; exchanging the names unavoidably also exchanges their order of mention in those lines.

The target-second, anchor-assignment combination reproduces the historical error form's API bodies byte for byte. Each of the four combinations in each story gets a stand and a swap outcome. Collect each forecast twice in a fresh conversation and each factual check once: 48 primary forecasts and 24 factual checks. In a secondary check, reverse the two whole action sentences at each of the 24 forecast prompts and collect each once. These 24 mirror calls distinguish sensitivity to how the actions are presented from sensitivity to the actual helper–job allocation. They cannot establish test–retest reliability on a mirror prompt. In total there are 96 calls with 72 distinct texts. The later fair draw is independent of both sealed decisions in every prompt.

## Scoring and interpretation

A reproducible outcome-following switch requires both stand responses to name the original target's helper and both swap responses to name the other helper. A stable answer repeats the same semantic choice four times, including equality or insufficient evidence. Count opposite switches, other reproducible shifts, mixed repeats and missing/invalid responses separately. On the single-pass mirrors classify the two answers descriptively. Retain all choices and show factual comprehension and exact-repeat agreement. Use the answer field as the primary measure.

First report replication in the three exact historical anchors. Then tabulate reproducible switches per three stories in each factorial cell. Compare first vs. second at each fixed allocation, and anchor vs. exchanged at each fixed roster order. The descriptive interaction is (second minus first at the anchor allocation) minus (second minus first at the exchanged allocation), measured in proportions of complete story forms with a reproducible switch. Report incomplete forms and denominators. If only the double combination reproduces, the result supports dependence on the combination in these materials. Similar counts under both positions or both allocations weaken the corresponding single-factor account. If the anchor fails to recur, the follow-up estimates current behavior and the earlier trigger may be unstable. For the mirror check report the full cell breakdown and concordance with the primary classifications. These conditions share three stories, and the original error cell was selected retrospectively. There is no population-level significance test.

## Reproduction and budget

From this directory run `python3 order_study.py check` and `python3 -m unittest -v test_order`. The bank uses the original pinned model, temperature, instructions, schema, 256-token output cap, and spend-guarded transport. The 96 reservations total $0.958464 under the $1 guard. One initiating push launches collection. The offline `report` command scores a saved ledger. The workflow archives all request bodies, raw responses and usage. The SHA-256 digests in `freeze.json` identify the exact ordered requests and scoring keys.
