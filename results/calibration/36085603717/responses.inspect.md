# Structured response calibration

Protocol: `calibration-structured-v1`; model: `claude-sonnet-4-5-20250929`.
Recorded 72/72 responses; item hash `ac2f89d22ce87380`.
No WTR estimates or confirmatory tests are computed.

Stop reasons: {'end_turn': 72}

- input_tokens: 22532
- output_tokens: 665

## Known-answer controls

Correct/planned includes missing and unusable answers in the denominator.
Order disagreements include only pairs with two usable answers.

| Format | Control | Correct/planned | Missing | Unusable | Disagree/complete |
|---|---|---:|---:|---:|---:|
| letter | recipient_lookup | 8/8 | 0 | 0 | 0/4 |
| letter | quantity | 4/4 | 0 | 0 | 0/2 |
| letter | explicit_rule | 10/12 | 0 | 0 | 0/6 |
| recipient | recipient_lookup | 8/8 | 0 | 0 | 0/4 |
| recipient | quantity | 4/4 | 0 | 0 | 0/2 |
| recipient | explicit_rule | 6/12 | 0 | 0 | 0/6 |

## Controls by displayed option order

| Format | Control | Sam option position | Correct/planned | Usable/planned |
|---|---|---|---:|---:|
| letter | recipient_lookup | first | 4/4 | 4/4 |
| letter | recipient_lookup | second | 4/4 | 4/4 |
| letter | quantity | first | 2/2 | 2/2 |
| letter | quantity | second | 2/2 | 2/2 |
| letter | explicit_rule | first | 5/6 | 6/6 |
| letter | explicit_rule | second | 5/6 | 6/6 |
| recipient | recipient_lookup | first | 4/4 | 4/4 |
| recipient | recipient_lookup | second | 4/4 | 4/4 |
| recipient | quantity | first | 2/2 | 2/2 |
| recipient | quantity | second | 2/2 | 2/2 |
| recipient | explicit_rule | first | 3/6 | 6/6 |
| recipient | explicit_rule | second | 3/6 | 6/6 |

## Existing debug judgments (no correct answer assigned)

SAM/YOU denotes the payoff recipient in the predicted choice.

| Case | Format | Sam option first | Sam option second | Agreement |
|---|---|---|---|---|
| boxes_unable_0.1 | letter | YOU | YOU | True |
| boxes_unable_0.1 | recipient | YOU | SAM | False |
| boxes_unable_1 | letter | SAM | SAM | True |
| boxes_unable_1 | recipient | SAM | SAM | True |
| boxes_unwilling_0.1 | letter | YOU | SAM | False |
| boxes_unwilling_0.1 | recipient | YOU | SAM | False |
| boxes_unwilling_1 | letter | SAM | SAM | True |
| boxes_unwilling_1 | recipient | SAM | SAM | True |
| debug_numeric_high_0.5 | letter | SAM | SAM | True |
| debug_numeric_high_0.5 | recipient | SAM | SAM | True |
| debug_numeric_low_0.5 | letter | SAM | SAM | True |
| debug_numeric_low_0.5 | recipient | SAM | SAM | True |

## Candidate for full debug (not pilot approval)

- letter: not ready (22/24 correct controls; 6/6 complete debug pairs; 1 disagreements).
- recipient: not ready (18/24 correct controls; 6/6 complete debug pairs; 2 disagreements).

## Raw replies

- letter: {'{"answer": "A"}': 17, '{"answer": "B"}': 19}
- recipient: {'{"answer": "SAM"}': 13, '{"answer":"SAM"}': 3, '{"answer":"YOU"}': 5, '{"answer": "YOU"}': 15}

## Unusable responses


