# Results of the indirect-beneficiary pilot

Claude Sonnet 4.5 completed all 96 frozen prompts in one collection. Changing what the helpers knew reversed the forecast in the predicted direction on both members of **5 of 12 matched pairs**. The archive story met the prespecified primary criterion. The breakfast and camera stories each produced one of the three reversals required. The separate lottery criterion failed in all three settings.

| Setting | Predicted forecast reversals | Actual-benefit questions correct | Expected-benefit questions correct | Lottery forecasts favoring neither helper |
|---|---:|---:|---:|---:|
| Breakfast shifts | 1/4 | 8/8 | 7/8 | 1/8 |
| Camera batteries | 1/4 | 8/8 | 8/8 | 2/8 |
| Archive repairs | 3/4 | 8/8 | 8/8 | 2/8 |
| Total | 5/12 | 24/24 | 23/24 | 5/24 |

All five predicted forecast reversals were accompanied by four correct comprehension answers for the corresponding pair. Comprehension and forecasting questions were asked in fresh conversations. Each paired comparison kept the actions, their costs, the actual beneficiaries, and the transfer question fixed.

## What happened when expected and actual beneficiaries differed

With the updated information visible, Claude favored the predicted helper on 11/12 voluntary forecasts. When the helpers missed the update, it favored the helper who could expect to benefit the target on 6/12. It favored the helper who actually benefited the target on 5/12 and answered “equally likely” once. There were no “insufficient evidence” answers. Only the hidden-update condition separates the two beneficiary identities within a single prompt.

In camera item `09dea01705becea53c1d`, Claude's own explanation correctly identified Finn as expecting to help Inez and Asha as actually helping Inez. It then forecast that Asha would give to Inez to remain consistent with her past action. The story stated that Asha never learned about the switch. This item illustrates how the forecast can depart from the information the model just described. It does not identify an internal mechanism.

## Per-condition counts

Each row includes four fresh conversations per probe. “Predicted helper” identifies the helper whose action was expected, from the helpers' perspective, to benefit the target. On the lottery forms it is only a way to label the two helpers. The prediction for those forms is a nondirectional forecast.

| Setting | Update | Actual correct | Expected correct | Voluntary: predicted / other / equal / insufficient | Lottery: predicted / other / equal / insufficient |
|---|---|---:|---:|---|---|
| Breakfast | Seen | 4 | 4 | 4 / 0 / 0 / 0 | 3 / 0 / 1 / 0 |
| Breakfast | Unseen | 4 | 3 | 1 / 2 / 1 / 0 | 0 / 4 / 0 / 0 |
| Camera | Seen | 4 | 4 | 4 / 0 / 0 / 0 | 3 / 0 / 1 / 0 |
| Camera | Unseen | 4 | 4 | 1 / 3 / 0 / 0 | 1 / 2 / 1 / 0 |
| Archive | Seen | 4 | 4 | 3 / 1 / 0 / 0 | 3 / 0 / 1 / 0 |
| Archive | Unseen | 4 | 4 | 4 / 0 / 0 / 0 | 3 / 0 / 1 / 0 |

The remaining expected-benefit answer in the breakfast story was “equally likely.” No response was missing, refused, truncated or invalid. The lottery assigned the job and deducted the credits without giving either helper a choice. Claude still favored one helper on 19/24 forecasts. The future decision is unobserved, so the forecasts are evaluated against the directional hypothesis, not scored as facts about human behavior. The result describes this model and these three authored scenarios. The experiment holds cost fixed.

## Run record

[GitHub Actions run 44649365469](https://github.com/msblanders/wtr-bench/actions/runs/44649365469) used the pinned model `claude-sonnet-4-5-20250929` and recorded 50,960 input tokens and 8,164 output tokens. Usage-based cost was **$0.27534** against a $1 local guard. The downloaded artifact matched GitHub's SHA-256 digest `162e1763363e0742d4cce5e392b9ef27cdf8958c8664dceb34098063724725f1`. Its request bank matched the freeze byte for byte. All 96 provider message IDs were unique, and scoring the raw responses reproduced the reported outcomes.
