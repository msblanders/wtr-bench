# Review of the uploaded paired-comparison v1 candidate

Reviewed before any v2 model calls. The user's methodological recommendation is
sound: direct comparisons are a better-matched candidate for the ordinal question.
The attached implementation still needed corrections before use.

## Source record

Uploaded outer ZIP SHA256: `b011a52a57330782b9bf9f27d8956c38f4c73d0c375bd009860e21153f9be2db`

Nested `wtr-bench-paired-v1.zip` SHA256: `d3d73d42d103d435f9b7183372aca6afd8647ee1e4582b4e92b2726e0cbcbe9b`

Uploaded `comparison.py` SHA256: `f6ba445d4f0fc13ca937d0f2d3c03db2e97be3033732deb58911eaf67e177806`

These are provenance hashes of supplied files, not claims that they were run or
committed to the remote repository. The original files remain unchanged.

## Findings and prospective changes

**Name/position coupling.** In `_validation_items` and `_pilot_items`, v1 assigns
`a, b` from the position factor and then binds the first presentation name `n1`
to `a`. At fixed `names_swapped`, changing `pos` therefore changes which name
carries which underlying profile/cause as well as changing profile position.
The four combinations cover the displays, but the nominal position-pair
comparison does not isolate position while preserving person-name identity.
V2 binds names to P/Q first, then changes the presentation order. Tests read the
literal named histories and verify that the reversal leaves them unchanged.

**Ability keys stronger than their premises.** V1's equal-skill text is
"Both Sam and Priya have fixed leaking faucets before." That does not logically
entail equal future success probabilities. "Has fixed many" versus "has never
attempted one" also supports an inference rather than determining exact ability.
V2 stipulates exact success probabilities independent of point-choice preferences.
These intentionally easy controls test dimension following, not natural ability
inference. The lower-weight partner is more skilled in the conflict category.

**No correct D cases.** V1 permits insufficient-evidence responses but all its
validation keys are A/B/C. V2 includes a separately scored underdetermined category
where compatible weights imply different comparisons and no prior is stipulated.
Correct D responses are not counted against the determined-item abstention cap.

**Freshness and holdout.** V1 reuses the previous three numerical profiles and
uses the faucet task in controls. V2 uses 30 new numerical parameterizations and
five non-pilot task phrases. None of the six natural scenarios is imported,
generated, or submitted by the new module. This does not claim absence from
pretraining, nor that the proposed v1 validation had already contaminated anything.

**Gate denominators.** V1 pools different skill probes within categories and
allows 80% within-category accuracy behind a 90% overall rule. V2 separately
requires 9/10 jointly correct position pairs in every category and every pass.
Repeated/name-varied questions do not establish a population error bound. The
old rationale equating the observed 90% rate with errors below one in six is
removed. This is a prospective change, not a reinterpretation of an old result.

**Scope.** V1's executable pilot expands the user's focused three-probe design to
four probes and 192 calls across two passes. V2 keeps only validation executable.
The accompanying plan proposes the focused 72 requests per pass (144 with two
passes), with one valuation tradeoff; any larger pilot requires a separate
pre-collection decision. No natural-scenario truth key is introduced.

## Software checks and reporting

The literal-prompt test oracle parses displayed payoffs/names and independently
enumerates compatible rational weights. It does not call the production truth
function. Tests also cover constant letters/people, name-only preference,
nonzero error tolerance, the D cap, missingness, strict decoding, duplicates,
request/property-order tampering, freeze tampering, transport stops, preservation
of a wrong-model response, and continued collection of unusable answers.

Local targeted tests passed: **37 tests**. These are programmed software tests,
not model data. The full repository CI result must be checked separately on the
published commit; local access did not provide the complete repository or its
lint/type-checking dependencies. A PASS from the programmed fixture must never
be described as successful model validation.

No paid experimental model requests were made in preparing this revision.
The archived development findings remain available for an honest methods
article irrespective of whether the new instrument passes.
