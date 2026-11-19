# WTR-Bench • When a choice and its outcome disagree
Frozen development pilot • November 19, 2026 • 64 fresh conversations • one vignette

## What the experiment asks

Sam chooses a voucher for Alex. Priya chooses one for Jordan. A clerk sometimes exchanges the deliveries without either helper knowing. If Alex actually got Priya’s voucher, can Claude identify Priya as the donor and still forecast that Sam is more likely to choose to give to Alex next time? All participants in the story are third-person fictional humans.

The earlier WTR-Bench pilot distinguished willingness from ability. A later recipient-specific design could be passed by selecting whoever previously provided the target with help. The clerk manipulation makes that shortcut yield a different forecast from a rule that follows whom each helper deliberately selected. The spending decision here concerns this development set alone.

| Item set | Count | Readout |
|---|---:|---|
| Who actually delivered the voucher, choices and deliveries aligned | 16 | Factual accuracy |
| Who actually delivered the voucher, deliveries swapped | 16 | Factual accuracy |
| Who is more likely to give next, choices and deliveries aligned | 16 | Whether the helper favored by both histories is selected |
| Who is more likely to give next, deliveries swapped | 16 | Deliberate choice versus actual delivery, equality, or insufficient evidence |

The wording of the factual question asks whose voucher the target received. “Donor” means the helper whose voucher arrived. The clerk physically delivers both vouchers. All 64 forms come from a single voucher story. Name substitutions, evidence order, option positions, and target swaps test stability. None is an independent new social situation.

## Frozen elicitation and scoring

The exact model ID is `claude-sonnet-4-5-20250929`. The collector uses the prior social pilot’s system message and response schema, temperature 0, a 256-token output limit, no explicit extended thinking, and no tools. Each request includes one vignette and one question in a fresh conversation. The model returns a brief basis followed by A, B, C or D. The scorer uses the answer field. Reported reasons are model behavior; they cannot establish the computation that produced an answer. No private reading, prior response, answer key, or billing information is included in the model messages.

`requests.jsonl` fixes the request order and exact payloads. Rows are ordered by the SHA-256 of a protocol prefix and prompt ID before collection. `score-key.json` maps response letters to helpers for each form. Both file hashes are pinned in `pilot.py`. The runner never reads the score key to decide which requests to send.

Report every attempted and missing item. Show the numerator and denominator for factually correct answers in each delivery condition. For forecasts report all categories, including C (equally likely), D (insufficient evidence), refusals, truncation, malformed outputs, missing calls, and unresolved attempts when present. Empty categories have count zero. A forward prediction has no objectively guaranteed correct answer. The report also crosses factual and forecast answers for each exactly matched swapped history and counts semantic changes under answer-order, evidence-order, helper-name and recipient-name swaps.

Examine swapped factual comprehension first. If the model frequently misidentifies whose voucher arrived, report that directly and keep interpretation of its forecasts open. If it identifies the donor and forecasts the helper who chose the target, that combination distinguishes the two programmed rules on this story. If it identifies the donor and then abstains, it can track the past while withholding a forecast. A response rule that simply echoes the selected recipient on forward-looking questions can still pass. The next generalization test would use independently worded settings that reveal a choice through behavior without naming a selected recipient. Report descriptive counts and within-history comparisons. The repetitions of this vignette do not support a confidence interval across social settings.

## Cost and execution

The standard first-party prices checked November 19 were $3 per million input tokens and $15 per million output tokens. Each free token-count preflight must return at most 1,024 input tokens. The runner reserves 2,048 input tokens plus the entire 256-token output allowance per message. That totals $0.638976 for all 64 at those prices. The local spending guard is $1 for one shared ledger. The API bills actual usage. Token counts are estimates, and provider billing controls and other account activity are outside this script. It stops on unexpected metered usage, a model mismatch, or a service error. It never substitutes another model. Anthropic lists November 30, 2026 as the retirement date. Collection is disabled starting that date UTC.

Run from one extracted folder on a Unix system with Python 3.10 or later. Use the same folder and ledger throughout. Multiple copies or deletion of the ledger would create independent runs. All tests are offline, use synthetic fixtures, and require no API key.

```sh
python3 pilot.py check
python3 -m unittest -v test_pilot
```

In a private execution environment that already supplies the funded organization's `ANTHROPIC_API_KEY`, the following commands collect the pilot and regenerate its report.

```sh
python3 pilot.py collect
python3 pilot.py report
```

The collector writes a durable SQLite record before each model request. It then records the raw model response, request count estimate, usage, and execution status. A transport failure can leave billing uncertain. The next invocation skips all previously attempted items, including unresolved attempts, and continues with unattempted prompts. Stop and retain the ledger if provider usage or model identity requires review. Only one collector may run at a time in this folder. Preserve `pilot-records.sqlite3` and `report.json` alongside the frozen inputs. The packaged files contain zero model responses.

[Earlier social pilot](https://github.com/msblanders/wtr-bench/blob/main/src/wtrbench/paired/social.py) · [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) · [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) · [Retirement schedule](https://platform.claude.com/docs/en/about-claude/model-deprecations)
