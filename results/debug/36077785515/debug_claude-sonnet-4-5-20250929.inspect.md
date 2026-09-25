# debug_claude-sonnet-4-5-20250929.jsonl  (196 responses; model=claude-sonnet-4-5-20250929)

## Response collection

Stop reasons: end_turn=196

- input_tokens: 27444 (metadata available for 196/196 responses)
- output_tokens: 784 (metadata available for 196/196 responses)
- cache_creation_input_tokens: 0 (metadata available for 196/196 responses)
- cache_read_input_tokens: 0 (metadata available for 196/196 responses)

| family | recorded | A | B | unparsed |
|---|---|---|---|---|
| attribution | 100 | 19 | 81 | 0 |
| aggregate | 96 | 4 | 92 | 0 |

## Unparsed responses: 0


## Inferred-WTR ladders (K = partner keeps own payoff, . = gives; shown as keyed-A then keyed-B at each rung)

| cell | pattern by rung | order disagreements / complete pairs | fit |
|---|---|---|---|
| aggregate / debug / high/t1 / original | 0.1:.K 0.2:.K 0.5:.K 1:KK 1.5:KK 2:.K | 4/6 | unidentified (viol 4) |
| aggregate / debug / high/t1 / swapped | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| aggregate / debug / high/t2 / original | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| aggregate / debug / high/t2 / swapped | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| aggregate / debug / low/t1 / original | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| aggregate / debug / low/t1 / swapped | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:KK 2:KK | 4/6 | unidentified (viol 4) |
| aggregate / debug / low/t2 / original | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| aggregate / debug / low/t2 / swapped | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| attribution / boxes / baseline | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| attribution / boxes / constrained | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| attribution / boxes / helped | 0.1:.K 0.2:.K 0.5:.K 1:KK 1.5:.K 2:.K | 5/6 | unidentified (viol 5) |
| attribution / boxes / unable | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |
| attribution / boxes / unwilling | 0.1:.K 0.2:.K 0.5:.K 1:.K 1.5:.K 2:.K | 6/6 | unidentified (viol 6) |

Only rungs with two parsed answers enter the option-order denominator. Missing responses can make a threshold fit look more precise by removing conflicting answers; inspect coverage, order effects and violations before interpreting any fitted bound.
