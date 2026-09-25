# Calibration 36081054221: audit and next step

Reviewed 25 September 2026. **Neither tested reply protocol passed the
calibration; keep the 888-item pilot paused.**

- [Run 36081054221, attempt 1](https://github.com/msblanders/wtr-bench/actions/runs/36081054221)
- Source: `b61de9c5d2b55c453fbffc0dbd766f7e19b136a1`, package v0.4.3.
- Requested and returned model: `claude-sonnet-4-5-20250929` on all 72 rows.
- Item hash: `299094bf02c5a1d1`; temperature 0; maximum output tokens 64.
- Artifact ID: `10841024421`; original ZIP SHA-256:
  `be2cef1b890cdca9379e9ffb31eb15d1890e635bdd743dd25cba063cc2bcb2b4`.
- [Original extracted records and checksums](../results/calibration/36081054221/).

All 72 expected item IDs and API request IDs are unique. There are no missing
or extra items. Saved prompts match the generator byte for byte; config,
strict parsing, semantic decoding and both reports reproduce. The inspect
report contains an additional trailing newline. No scoring or artifact
integrity defect was found. Network-level API request captures were not
included in that artifact.

| Check | A/B | SAM/YOU |
|---|---:|---:|
| Recipient lookup | 8/8 correct | 8/8 correct |
| Larger quantity | 4/4 correct | 4/4 correct |
| Explicit choice rule | 0/12 usable | 0/12 usable |
| Social order disagreements | 6/6 complete pairs | 1/3 complete pairs; 3 incomplete |

All explicit-rule responses began a calculation in prose and stopped at
exactly 64 output tokens. The original report's `0/12 correct` uses all
planned items as the denominator: this is a failure to collect final
answers, not 12 demonstrated calculation errors per format. No answer was
extracted from the unfinished explanations.

Overall, 43/72 replies parsed and ended with `end_turn`; the other 29 were
all truncated at 64 tokens with `max_tokens`. They comprise all 24 rule
controls and five recipient-format social questions. Recorded usage was
8,600 input and 2,035 output tokens, with zero recorded cache tokens.

All 12 A/B social answers were B, reproducing their raw replies from the
earlier Sonnet debug run. Every option swap therefore reversed the predicted
recipient. The SAM/YOU format supplied seven usable social replies: two
complete pairs agreed, one disagreed, and three could not be evaluated.
Neither reply format supports interpreting the target valuation contrasts.

The follow-up is the separate [structured-answer calibration](inference-calibration-structured.md):
same model, cases and option reversals, with an API-constrained final-answer
field and a 256-token allowance. It is a new protocol, not a rescore or
resume of this run. All prior results remain part of the development record.
Correct formatting, if achieved, still requires checking correctness and
order stability before proceeding to the full debug battery.
