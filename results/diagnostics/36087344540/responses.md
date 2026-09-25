# Explicit-rule calculation diagnostic

Protocol: `calculation-diagnostic-v1`; model: `claude-sonnet-4-5-20250929`.
Recorded 24/24 responses; item hash `7306b8fde1e80015`.
Six previously examined rule cases; no social judgments or pilot calls.
Returned values are task outputs, not a record of internal reasoning.

Stop reasons: {'end_turn': 24}

- input_tokens: 9976
- output_tokens: 911

## Summary by format and option order

Correctness denominators include every planned item. Missing and unusable
are separate. Ranking consistency excludes reported ties and unusable answers.

| Format | Sam position | Planned | Missing | Unusable | Both values correct | Choice correct | Follows reported ranking | Reported ties |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| letter | both | 12 | 0 | 0 | 12/12 | 12/12 | 12/12 | 0 |
| letter | first | 6 | 0 | 0 | 6/6 | 6/6 | 6/6 | 0 |
| letter | second | 6 | 0 | 0 | 6/6 | 6/6 | 6/6 | 0 |
| recipient | both | 12 | 0 | 0 | 12/12 | 12/12 | 12/12 | 0 |
| recipient | first | 6 | 0 | 0 | 6/6 | 6/6 | 6/6 | 0 |
| recipient | second | 6 | 0 | 0 | 6/6 | 6/6 | 6/6 | 0 |

## Joint correctness (usable answers only)

| Format | Correct values + correct choice | Correct values + wrong choice | Wrong values + correct choice | Wrong values + wrong choice |
|---|---:|---:|---:|---:|
| letter | 12 | 0 | 0 | 0 |
| recipient | 12 | 0 | 0 | 0 |

## Final-choice option-order consistency

- letter: 0/6 disagreements/complete pairs (6 pairs planned).
- recipient: 0/6 disagreements/complete pairs (6 pairs planned).

## Every planned response

Values are in displayed A/B order; final answers are also decoded to recipients.

| Case | Format | Sam first | True A / B | Returned A / B | Answer | Recipient | Values correct | Choice correct | Follows ranking |
|---|---|---|---|---|---|---|---|---|---|
| rule_0.5_2 | letter | True | 2 / 5 | 2 / 5 | B | YOU | True | True | True |
| rule_0.5_2 | recipient | True | 2 / 5 | 2 / 5 | YOU | YOU | True | True | True |
| rule_0.5_2 | letter | False | 5 / 2 | 5 / 2 | A | YOU | True | True | True |
| rule_0.5_2 | recipient | False | 5 / 2 | 5 / 2 | YOU | YOU | True | True | True |
| rule_0.5_8 | letter | True | 8 / 5 | 8 / 5 | A | SAM | True | True | True |
| rule_0.5_8 | recipient | True | 8 / 5 | 8 / 5 | SAM | SAM | True | True | True |
| rule_0.5_8 | letter | False | 5 / 8 | 5 / 8 | B | SAM | True | True | True |
| rule_0.5_8 | recipient | False | 5 / 8 | 5 / 8 | SAM | SAM | True | True | True |
| rule_1_5 | letter | True | 5 / 10 | 5 / 10 | B | YOU | True | True | True |
| rule_1_5 | recipient | True | 5 / 10 | 5 / 10 | YOU | YOU | True | True | True |
| rule_1_5 | letter | False | 10 / 5 | 10 / 5 | A | YOU | True | True | True |
| rule_1_5 | recipient | False | 10 / 5 | 10 / 5 | YOU | YOU | True | True | True |
| rule_1_20 | letter | True | 20 / 10 | 20 / 10 | A | SAM | True | True | True |
| rule_1_20 | recipient | True | 20 / 10 | 20 / 10 | SAM | SAM | True | True | True |
| rule_1_20 | letter | False | 10 / 20 | 10 / 20 | B | SAM | True | True | True |
| rule_1_20 | recipient | False | 10 / 20 | 10 / 20 | SAM | SAM | True | True | True |
| rule_2_10 | letter | True | 10 / 20 | 10 / 20 | B | YOU | True | True | True |
| rule_2_10 | recipient | True | 10 / 20 | 10 / 20 | YOU | YOU | True | True | True |
| rule_2_10 | letter | False | 20 / 10 | 20 / 10 | A | YOU | True | True | True |
| rule_2_10 | recipient | False | 20 / 10 | 20 / 10 | YOU | YOU | True | True | True |
| rule_2_40 | letter | True | 40 / 20 | 40 / 20 | A | SAM | True | True | True |
| rule_2_40 | recipient | True | 40 / 20 | 40 / 20 | SAM | SAM | True | True | True |
| rule_2_40 | letter | False | 20 / 40 | 20 / 40 | B | SAM | True | True | True |
| rule_2_40 | recipient | False | 20 / 40 | 20 / 40 | SAM | SAM | True | True | True |

## Raw replies

- wtrcalc-8c800829f23ae390: '{"option_a_value_to_sam": 2, "option_b_value_to_sam": 5, "answer": "B"}' (stop=end_turn)
- wtrcalc-50e74fe3a5c5d3bc: '{"option_a_value_to_sam": 2, "option_b_value_to_sam": 5, "answer": "YOU"}' (stop=end_turn)
- wtrcalc-629bb988182318e3: '{"option_a_value_to_sam": 5.0, "option_b_value_to_sam": 2.0, "answer": "A"}' (stop=end_turn)
- wtrcalc-a4577fb6018628ce: '{"option_a_value_to_sam": 5, "option_b_value_to_sam": 2, "answer": "YOU"}' (stop=end_turn)
- wtrcalc-8e22ca8db4a8cf0c: '{"option_a_value_to_sam": 8, "option_b_value_to_sam": 5, "answer": "A"}' (stop=end_turn)
- wtrcalc-c77fced6ece26b91: '{"option_a_value_to_sam": 8, "option_b_value_to_sam": 5, "answer": "SAM"}' (stop=end_turn)
- wtrcalc-e97fb402748248bf: '{"option_a_value_to_sam": 5.0, "option_b_value_to_sam": 8.0, "answer": "B"}' (stop=end_turn)
- wtrcalc-168f41faae87a168: '{"option_a_value_to_sam": 5, "option_b_value_to_sam": 8, "answer": "SAM"}' (stop=end_turn)
- wtrcalc-34b3b441bbc3f16f: '{"option_a_value_to_sam": 5, "option_b_value_to_sam": 10, "answer": "B"}' (stop=end_turn)
- wtrcalc-87d0f11c7997f84f: '{"option_a_value_to_sam": 5, "option_b_value_to_sam": 10, "answer": "YOU"}' (stop=end_turn)
- wtrcalc-df42d950c0893f7a: '{"option_a_value_to_sam": 10, "option_b_value_to_sam": 5, "answer": "A"}' (stop=end_turn)
- wtrcalc-8b687beeb5adcd9b: '{"option_a_value_to_sam": 10, "option_b_value_to_sam": 5, "answer": "YOU"}' (stop=end_turn)
- wtrcalc-7ab380454be0a351: '{"option_a_value_to_sam": 20, "option_b_value_to_sam": 10, "answer": "A"}' (stop=end_turn)
- wtrcalc-ee4ee566d5c6d380: '{"option_a_value_to_sam": 20, "option_b_value_to_sam": 10, "answer": "SAM"}' (stop=end_turn)
- wtrcalc-76ea04354a245800: '{"option_a_value_to_sam":10,"option_b_value_to_sam":20,"answer":"B"}' (stop=end_turn)
- wtrcalc-a5dd458151070c5a: '{"option_a_value_to_sam": 10, "option_b_value_to_sam": 20, "answer": "SAM"}' (stop=end_turn)
- wtrcalc-a525634ebfd86b94: '{"option_a_value_to_sam": 10, "option_b_value_to_sam": 20, "answer": "B"}' (stop=end_turn)
- wtrcalc-cbe5a0483ece39c7: '{"option_a_value_to_sam": 10, "option_b_value_to_sam": 20, "answer": "YOU"}' (stop=end_turn)
- wtrcalc-91e255122337ede8: '{"option_a_value_to_sam":20,"option_b_value_to_sam":10,"answer":"A"}' (stop=end_turn)
- wtrcalc-be87b649616e72d8: '{"option_a_value_to_sam": 20, "option_b_value_to_sam": 10, "answer": "YOU"}' (stop=end_turn)
- wtrcalc-72c230cf301ba14e: '{"option_a_value_to_sam": 40, "option_b_value_to_sam": 20, "answer": "A"}' (stop=end_turn)
- wtrcalc-1f379f9f0d15c729: '{"option_a_value_to_sam": 40, "option_b_value_to_sam": 20, "answer": "SAM"}' (stop=end_turn)
- wtrcalc-c59c41aae854ed45: '{"option_a_value_to_sam":20,"option_b_value_to_sam":40,"answer":"B"}' (stop=end_turn)
- wtrcalc-728cfa859eea4a14: '{"option_a_value_to_sam": 20, "option_b_value_to_sam": 40, "answer": "SAM"}' (stop=end_turn)

No automatic progression decision is made. Review calculation errors, choice
inconsistencies, ties, missingness and order effects. Success on this scaffolded
task does not validate the earlier answer-only protocol or the social measure.
