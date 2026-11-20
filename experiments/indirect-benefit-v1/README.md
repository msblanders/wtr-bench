# Inferring a beneficiary from a costly action

## Question

A helper prepares a meal at dawn, charges a particular spare battery, or repairs one device. Who did the helper have reason to expect would benefit, and does that predict whom the helper might later help? The prior voucher pilot explicitly named the person each helper selected. Here each action names only a task. Linking the action to a person requires combining the work with the arrangement the helper understood to be in effect.

## Frozen design

The 96 independent API conversations cover three fictional stories, four presentation forms, two information conditions, and four questions or controls. There are three authored settings and 12 matched forecast comparisons. The 96 prompts do not constitute 96 independent settings.

In every story the recipients exchange assignments. Both helpers either learned about the change before acting or still relied on the original arrangement. In a matched pair, only the sentence about access changes. Physical actions, cost, actual beneficiaries, options, and the wording of the question stay fixed. A helper who chooses can do nothing for free or spend three personal credits on either job. Each does one job. In the lottery control the same jobs and costs are compulsory. The transfer forecast always concerns a new, voluntary decision with equal resources and equal need.

| Prompt | Number | Prespecified reading |
|---|---:|---|
| Which helper's work actually benefited this recipient? | 24 | Correct helper stays constant across access conditions |
| Whose work could the helpers expect would benefit this recipient? | 24 | Correct helper reverses with access |
| After a voluntary action, who is more likely to give this recipient ten points? | 24 | Directional prediction favors the helper who could expect to benefit the recipient |
| After a randomly required action, who is more likely to give? | 24 | Predicted attenuation of directional responses; C and D are counted separately |

The primary outcome is the number of the four matched forecast pairs per story that select the predicted helper on **both** forms of the information manipulation. The physical actions and delivered benefits stay fixed as the forecast reverses. For the development criterion each story must yield at least three of four forecast reversals, seven of eight correct actual-benefit answers, and seven of eight correct expected-benefit answers. The separate agency criterion calls for six of eight nondirectional lottery forecasts per story. Equality and insufficient evidence remain distinct observed answers. A voluntary forecast has no logically certain answer. Thresholds are descriptive decisions set before collection. Report counts by story and condition, including missing or invalid answers, and the number of forecast reversals accompanied by all four correct comprehension responses. No items are dropped or adapted.

Four forms vary the target, allocation of jobs, line order and option positions. Every directional prediction places each helper and each answer letter first equally often within a story, access condition and probe. The offline tests independently score each text using a mapping for the visible actions. Rules that always follow the original arrangement or always follow the actual beneficiary predict zero of 12 paired reversals. A knowledge-sensitive rule ignoring compulsory allocation passes the voluntary criterion but fails the agency criterion. A scripted rule following both information access and agency can pass the full instrument.

## Collection

Generate and verify the request and key hashes with `python3 study.py check`, then run `python3 -m unittest -v test_study` from this directory. The runner regenerates the complete stimuli deterministically; the GitHub artifact also includes the exact sent request bank. The model, temperature, explanation-then-answer schema, 256-token output limit and strict decoder match the voucher pilot. The model is Claude Sonnet 4.5, pinned as `claude-sonnet-4-5-20250929`. The request contains one fictional vignette and one question. The score keys never enter the model messages.

`python3 study.py collect` uses the shared durable collector with a fresh ledger bound to these exact inputs. It records usage, reserves before each attempt, and skips every previously attempted prompt when reusing its ledger. At standard prices of $3 per million input tokens and $15 per million output tokens, the 96 reservations total $0.958464 with a $1 local guard. A free token count limits sending to requests estimated at 1,024 input tokens or fewer; the reservation allows 2,048 input tokens plus all 256 output tokens. The workflow launches once from the designated initiating push. `python3 study.py report` scores a complete or partial ledger offline.

The experiment observes a model making predictions about fictional people. The between-condition difference tests sensitivity to the helpers' information and freedom of choice. General role-to-recipient matching under the appropriate information set can account for success. Cost stays fixed, so this study does not estimate the effect of raising the price of helping or identify a numerical welfare tradeoff.
