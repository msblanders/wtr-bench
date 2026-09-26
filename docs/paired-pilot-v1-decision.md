# Decision to prepare and enable the one paired social pilot

Recorded 25 September 2026 (America/Los_Angeles), before paid pilot requests.

## Evidence reviewed

Paired natural v3.2 at source `8adf2fb47174209ab6988693704fa7685f8d7343`,
run https://github.com/msblanders/wtr-bench/actions/runs/36200022149,
met its unchanged gate: 240/240 controls correct and all 280 records usable.
Its 40 exploratory responses were all in the predicted direction, not scored
as correctness and not used to determine the gate. The supplied completed audit
reproduced the frozen generator/scorer, all 240 literal control keys, all 420
planned presentation checks, and archived hashes. Its review found no material
control premise/answer contradiction; it is unblinded assistant text review,
not independent human validation. Original artifact SHA256:
`79af87fdbf892338a51e22c84965d3dc43ce34e2f602323916dad8d8bddf77d8`.

Frozen validation plan:
https://github.com/msblanders/wtr-bench/blob/8adf2fb47174209ab6988693704fa7685f8d7343/docs/paired-natural-v3.2.md

The v2 numerical failure remains unchanged. The v3.2 pass is a limited
premise-following result, not a social dissociation or internal-mechanism result.

## Researcher request and prospective implementation decision

Following the completed validation review, the researcher requested:
"great, let's continue building that. let me know when it's ready for launch";
a subsequent "can you continue?" asked to resume the interrupted implementation.
The request is to publish the already scoped pilot, not to launch paid API calls
on the researcher's behalf. The initial interrupted attempt saved social.py on
a feature branch; no pilot workflow or complete freeze had yet been published.

Decision: implement and enable exactly `paired-pilot-v1` as specified in
`paired-pilot-v1.md`, with six scenarios, unable versus unwilling, three probes,
name/order crossing and two passes (144 calls). Both primary directions must be
reported, and no answer is a known-truth key. Different-task ability has no
required direction. No second allocation payoff or new control category is added.

Publication to main is conditional on reviewed complete prompts and passing
repository CI, freeze verification and offline artifact generation. The merge
records fulfillment of those software conditions in its PR. The researcher
can then authorize the one paid batch by the explicit manual collect action
`COLLECT_144`; deployment alone sends no model requests. No further validation
round is required. The successful validation need not and must not be rerun.

The specific material and scoring choices are frozen in the linked plan and
source, not left for post-result selection. This decision and the plan are both
included in the pilot freeze. Earlier statements that a pilot was not yet
authorized are historical; this record enables this specific pilot's manual
launch only after publication conditions are met. The old larger pilots remain
paused and their workflows are not changed.
