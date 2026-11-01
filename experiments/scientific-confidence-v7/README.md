# Scientific confidence v7: small SciFact transfer pilot

Prospective exploratory protocol, written before any v7 model calls. Combined API ceiling: **$5**, including development. No sample expansion or prompt tuning after model results. No weight training.

## Question and scope

Does the compact identity/status memory policy improve confidence-weighted scientific claim classification and source identity maintenance when numerical templates are replaced by real published abstracts?

This transfers the **memory component** of v6. It does not pretend that abstract interpretation has the stipulated Normal likelihoods of the earlier simulator. There is no supplied hypothesis-prediction table to compile, and no invented Bayesian calculator. Deterministic validation checks structure and probability sums; it never repairs interpretation, identity or eligibility. Probabilities concern SUPPORT, CONTRADICT and NOT_ENOUGH_INFO as evidence-relation labels, not the real-world truth of a medical or biological claim.

## External reference and fixed sample

Source: [SciFact](https://github.com/allenai/scifact), accompanying Wadden et al., *Fact or Fiction: Verifying Scientific Claims* (EMNLP 2020). [Data schema](https://github.com/allenai/scifact/blob/master/doc/data.md). Claims and abstracts come unchanged from the authors' [dataset archive](https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz), SHA256 `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be`. Original abstracts are retained privately with the run; the public source downloads the fixed archive rather than republishing article text.

Main: 18 claims from the public development split, six per annotation class. Development: three claims from the training split, one per class, excluded from efficacy. All 21 source documents are distinct. Eligibility is fixed: one cited document, no evidence annotations on a different document, a single evidence direction or no annotated evidence, and an abstract of 120–350 whitespace-separated words. Select in SUPPORT, CONTRADICT, NOT_ENOUGH_INFO order; shuffle each eligible list with `Random(str(seed)+label)`, taking the first unused document. Main seed 30801203; development seed 90801203. Main is selected before development. The original source lists preserve their archive order.

The primary reference is the published annotation, including NOT_ENOUGH_INFO for claims with no annotated evidence. This is not a guarantee of scientific truth or flawless annotation. Before any calls, reading the selected abstracts identified three potentially ambiguous reference cases: claim 431 (neuronal-death/ROS wording versus broader FOXO3/SIRT1 stress regulation), 1144 (observed tax effects versus modeled future effects), and 1303 (tirasemtiv versus the unexpanded CK-2017357 drug alias). Keep all three in the primary analysis. A prespecified secondary sensitivity analysis excludes these three only, without substituting other cases. No labels are rewritten. This audit and the exclusion list predate model outcomes.

This is a small, class-balanced, public biomedical benchmark sample, not a representative or contamination-free evaluation. Familiarity with public claims/abstracts and annotation conventions could affect performance. The task is abstract-level classification, not retrieval, full-paper appraisal, meta-analysis or discovery.

## Four sequential packets

Every trajectory starts with the same verified **empty** review record. The first abstract still requires interpretation; an empty start is not a verified extraction of that abstract.

1. Supply the actual claim, canonical document ID, original title and numbered abstract sentences; source is eligible at revision 1.
2. Supply a second catalog listing under a generic heading, explicitly identifying it as the same source and sample, with unchanged evidence. This tests duplicate handling and confidence stability, not genuine overlapping-cohort inference.
3. A clearly fictional review-management notice temporarily excludes that source. No eligible evidence remains, so the task reference is NOT_ENOUGH_INFO. It does not assert a real retraction or introduce a negative finding.
4. A fictional eligibility notice restores the same source through the old listing reference, and supplies its unchanged title/abstract again. The original canonical ID must be restored. Reference classification returns to its original SciFact annotation.

The events are synthetic administrative scaffolding around genuine scientific prose. There are no fabricated numerical study findings. Event order is fixed. There is one source per case: genuinely conflicting studies, partial sample overlap, numerical corrections and multi-source synthesis are not tested by this inexpensive screening pilot.

## Arms and information boundary

Both arms receive the same checklist covering scope, study design, association/causation, modeled/observed effects, missing/contrary evidence and dependence. Both produce current eligible entries with canonical identity, revision, aliases, evidence-relation label, sentence references and a scope note, plus the same 120-word evidence note and three probabilities.

- **Active checklist:** active entries only; identity_index should be empty. Useful history can remain in active references and the common note.
- **Compact index:** active entries plus one small index item per currently excluded source, preserving only canonical identity, revision, excluded status and aliases. On restoration, move references back to the active entry. No abstract, old relation label, rationale, scope or numerical result belongs in the index.

Both use the same output schema; the policy text is the only first-request difference. As in v6, index adherence is measured, not enforced by deleting outputs. Subsequent calls receive only the model's own returned state, claim and new packet. The old abstract is absent at steps 2 and 3, and is resupplied at step 4. No gold annotation or source identity repair enters a request. Differences compare assigned policy/instruction bundles, not perfectly enforced memory contents or token-matched compute.

## Outcomes and analysis

**Primary:** per-case mean multiclass Brier loss across steps **1, 2 and 4**, paired compact minus active. Each Brier score is the sum of squared deviations from the one-hot reference label (range 0–2). The trivial no-evidence exclusion checkpoint is excluded from the primary endpoint. Invalid or missing outputs receive loss 2. No post-treatment exclusions. Compute a 10,000-resample paired percentile interval, resampling whole trajectories within the six-case reference-label strata. The three checkpoints are not independent observations.

Secondary/descriptive: accuracy; high-confidence errors (maximum probability at least .90); by-step results; canonical source/revision correctness; index fidelity and baseline index violations; word-budget violations; API cost; and the fixed 15-case annotation-ambiguity sensitivity analysis. An empty active record can be valid when nothing is eligible. A wrong source ID is a record error even when the semantic label is correct. Sentence indices are checked for bounds, not treated as a complete assessment of reasoning quality.

This is a screening pilot. Report effect size, uncertainty, ties/ceiling and failure types. No claim of established superiority, noninferiority, general calibration or practical real-world reliability follows from 18 cases. Secondary results are not multiplicity-adjusted. If the main run is incomplete or truncated, report infrastructure limitations rather than selecting complete cases for efficacy.

## Calls, budget and collection

claude-sonnet-4-6, temperature 0, thinking disabled, maximum 1,536 output tokens; four concurrent trajectory workers. Three development cases × two arms × four updates = 24 calls. Eighteen main cases × two arms × four updates = 144 calls. **168 calls total**, expected approximately $2–4, with a **$5 combined usage-based ceiling** at the same $3/M input and $15/M output accounting rates used in v6. Estimates are not an account invoice or a live balance query. Current pricing-page retrieval was unavailable during preparation; no claim of a fresh account-rate verification is made.

Before every request, reserve a conservative input allowance (UTF-8 payload bytes plus 4,096 tool-overhead tokens) plus maximum output tokens. Settle from returned token usage, retain reservations for ambiguous failures and stop further sending. Never retry failed requests. All development spending carries into main; no second budget. A freeze, phase markers and workflow run-attempt guard prevent paid repetitions. Only structural validity, complete tool responses, unique expected keys and settled usage gate development; no semantic accuracy gate. Main prompts are not tuned after development.

Freeze code, this protocol, cases, gold, the original public dataset and encryption support before calls. Run the exact integrity audit under the collection's Python 3.11 runtime: regenerate selected fixtures, compare first requests after removing policy text, verify every state handoff and response/state pair, and reproduce the aggregate report exactly. This makes no model calls.

Raw requests/responses, case-level results and aggregate findings are encrypted before artifact upload using the already-tested v6 transport. The private recovery key is saved before launch. Public logs contain call completion and cost, not scientific results or article contents. The completed private package will contain the interpretation and full reproducibility record.
