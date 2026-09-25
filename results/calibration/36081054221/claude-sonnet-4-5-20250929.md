# Exploratory response calibration

Recorded 72/72 responses; item hash `299094bf02c5a1d1`.
No WTR estimates or confirmatory tests are computed.

Stop reasons: {'end_turn': 43, 'max_tokens': 29}

- input_tokens: 8600
- output_tokens: 2035

## Known-answer controls

Accuracy uses all planned items as denominator; missing and unparsed answers
are also shown. Order agreement uses only pairs with two parsed responses.

| Format | Control | Correct / planned | Missing or unparsed | Order disagreements / complete pairs |
|---|---|---:|---:|---:|
| letter | recipient_lookup | 8/8 | 0 | 0/4 |
| letter | quantity | 4/4 | 0 | 0/2 |
| letter | explicit_rule | 0/12 | 12 | 0/0 |
| recipient | recipient_lookup | 8/8 | 0 | 0/4 |
| recipient | quantity | 4/4 | 0 | 0/2 |
| recipient | explicit_rule | 0/12 | 12 | 0/0 |

## Previously examined debug cases (no correct answer assigned)

SAM/YOU names the payoff recipient, not the responding model's own choice.

| Case | Format | Sam option first | Sam option second | Order agreement |
|---|---|---|---|---|
| boxes_unable_0.1 | letter | YOU | SAM | False |
| boxes_unable_0.1 | recipient | YOU | missing/unparsed | undetermined |
| boxes_unable_1 | letter | YOU | SAM | False |
| boxes_unable_1 | recipient | YOU | YOU | True |
| boxes_unwilling_0.1 | letter | YOU | SAM | False |
| boxes_unwilling_0.1 | recipient | YOU | YOU | True |
| boxes_unwilling_1 | letter | YOU | SAM | False |
| boxes_unwilling_1 | recipient | SAM | YOU | False |
| debug_numeric_high_0.5 | letter | YOU | SAM | False |
| debug_numeric_high_0.5 | recipient | missing/unparsed | missing/unparsed | undetermined |
| debug_numeric_low_0.5 | letter | YOU | SAM | False |
| debug_numeric_low_0.5 | recipient | missing/unparsed | missing/unparsed | undetermined |

## Raw response counts

- letter: {'A': 6, 'B': 18, "I need to calculate the value Sam assigns to each option.\n\nFor option A (Sam receives 2 points):\n- Sam's points: 2\n- My points: 0\n- Value to Sam: 2 + 0.5(0) = 2\n\nFor option B (": 1, "I need to calculate the value Sam assigns to each option.\n\nFor option A: You receive 10 points, Sam receives 0 points\nSam's value = Sam's points + 0.5 × Your points = 0 + 0.5 × 10 = 5": 1, "I need to calculate the value Sam assigns to each option.\n\nFor option A (Sam receives 8 points):\n- Sam's points: 8\n- My points: 0\n- Value to Sam: 8 + 0.5(0) = 8\n\nFor option B (": 1, "I need to calculate the value Sam assigns to each option.\n\nFor option A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's value = 0 + 0.5(10) = 5\n\nFor option B: Sam": 1, 'I need to calculate the value Sam assigns to each option.\n\nFor option A: Sam receives 5 points, I receive 0 points\nValue to Sam = 5 + 1(0) = 5\n\nFor option B: I receive 10 points, Sam receives 0 ': 1, "I need to determine which option Sam will choose based on Sam's valuation function: Sam's points + 1 × my points.\n\nLet me evaluate each option from Sam's perspective:\n\nOption A: I receive 10 points\n- Sam's points: 0\n- My points: 10": 1, "I need to calculate the value Sam assigns to each option.\n\nFor option A: Sam receives 20 points, I receive 0 points\nValue to Sam = Sam's points + 1 × my points = 20 + 1(0) = 20\n\nFor option B: I": 1, "I need to calculate the value Sam assigns to each option.\n\nSam's value function = Sam's points + 1 × Your points\n\nOption A: You receive 10 points, Sam receives 0 points\n- Sam's value = 0 + 1(10) = 10": 1, "I need to calculate the value Sam assigns to each option.\n\nFor option A (Sam receives 10 points):\n- Sam's points: 10\n- My points: 0\n- Value to Sam: 10 + 2(0) = 10\n\nFor option B (I receive": 1, "I need to determine which option Sam will choose based on Sam's value function: Sam's points + 2 × my points.\n\nOption A: I receive 10 points, Sam receives 0 points.\nValue to Sam = 0 + 2(10) = 20\n\nOption": 1, "I need to calculate which option Sam will choose based on Sam's valuation: Sam's points + 2 × my points.\n\nOption A: Sam receives 40 points, I receive 0 points.\nValue to Sam = 40 + 2(0) = 40\n\nOption": 1, "I need to calculate the value Sam assigns to each option.\n\nFor option A: You receive 10 points, Sam receives 0 points.\nValue to Sam = Sam's points + 2 × Your points = 0 + 2(10) = 20\n\nFor option B:": 1}
- recipient: {'SAM': 7, 'YOU': 12, "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 0.5 × Your points.\n\nOption A: Sam receives 2 points, You receive 0 points\n- Sam's value = 2 + 0.5(0)": 1, "I need to calculate which option Sam values more.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's value calculation: 0 + 0.5(10) = 5\n\nOption B: Sam receives 2": 1, "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 0.5 × Your points.\n\nOption A: Sam receives 8 points, You receive 0 points\n- Sam's value = 8 + 0.5(0)": 1, "I need to calculate the value Sam assigns to each option.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Value to Sam: 0 + 0.5(10) = 5\n\nOption B: Sam receives ": 1, "I need to calculate which option Sam will choose based on Sam's value function: Sam's points + 1 × Your points.\n\nOption A: Sam receives 5 points, You receive 0 points\nSam's value = 5 + 1(0) = 5\n\nOption B": 1, "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 1 × Your points.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's valuation: 0 +": 2, "I need to calculate which option Sam will choose based on Sam's value function: Sam's points + 1 × Your points.\n\nOption A: Sam receives 20 points, You receive 0 points\nSam's value = 20 + 1(0) = 20\n\nOption B": 1, "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 2 × Your points.\n\nOption A: Sam receives 10 points, You receive 0 points\nSam's valuation: 10 + 2(0) = 10": 1, "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 2 × Your points.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's valuation: 0 +": 1, "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 2 × Your points.\n\nOption A: Sam receives 40 points, You receive 0 points\nValue to Sam = 40 + 2(0) = 40\n\nOption": 1, "I need to calculate which option Sam will choose based on Sam's valuation: Sam's points + 2 × Your points.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's valuation: 0 + ": 1, "I need to determine who receives points based on Sam's likely choice between:\n(A) You receive 10 points\n(B) Sam receives 1 point\n\nSam tried to help me move boxes but couldn't due to a bad shoulder. I ended up doing it myself. Now Sam is choosing between": 1, "Looking at Sam's previous choices:\n\n1. Sam chose 35 for Sam over 10 for you (took the larger personal gain)\n2. Sam chose 5 for Sam over 10 for you (took the smaller amount to keep it from me)\n\nThe second choice is particularly revealing": 1, "Looking at Sam's previous choices:\n\n1. Sam chose 35 for Sam over 10 for you (took the larger personal gain)\n2. Sam chose 5 for Sam over 10 for you (took the smaller amount to keep it from you)\n\nThe second choice is particularly revealing": 1, "Looking at Sam's previous choices:\n- Sam chose 15 points for Sam over 10 points for me\n- Sam chose 25 points for Sam over 10 points for me\n\nThis shows Sam consistently prefers personal gain over giving me points, even when the benefit to me would be the": 1, "Looking at Sam's previous choices:\n- Sam chose 15 points for Sam over 10 points for me\n- Sam chose 25 points for Sam over 10 points for me\n\nThis shows Sam consistently prefers personal gain over giving me points, even when the personal gain is relatively small (": 1}

## Unparsed responses

- wtrcal-fe39c57a26aab0eb: "I need to calculate the value Sam assigns to each option.\n\nFor option A (Sam receives 2 points):\n- Sam's points: 2\n- My points: 0\n- Value to Sam: 2 + 0.5(0) = 2\n\nFor option B (" (stop=max_tokens)
- wtrcal-e99b12346ebe5b5d: "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 0.5 × Your points.\n\nOption A: Sam receives 2 points, You receive 0 points\n- Sam's value = 2 + 0.5(0)" (stop=max_tokens)
- wtrcal-ea04c289b8794d67: "I need to calculate the value Sam assigns to each option.\n\nFor option A: You receive 10 points, Sam receives 0 points\nSam's value = Sam's points + 0.5 × Your points = 0 + 0.5 × 10 = 5" (stop=max_tokens)
- wtrcal-7223189d2f18aa1c: "I need to calculate which option Sam values more.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's value calculation: 0 + 0.5(10) = 5\n\nOption B: Sam receives 2" (stop=max_tokens)
- wtrcal-68660d7121f67f9e: "I need to calculate the value Sam assigns to each option.\n\nFor option A (Sam receives 8 points):\n- Sam's points: 8\n- My points: 0\n- Value to Sam: 8 + 0.5(0) = 8\n\nFor option B (" (stop=max_tokens)
- wtrcal-cf87cdf1d88d2221: "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 0.5 × Your points.\n\nOption A: Sam receives 8 points, You receive 0 points\n- Sam's value = 8 + 0.5(0)" (stop=max_tokens)
- wtrcal-8f33d543df1c9af5: "I need to calculate the value Sam assigns to each option.\n\nFor option A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's value = 0 + 0.5(10) = 5\n\nFor option B: Sam" (stop=max_tokens)
- wtrcal-472a992116f07ed0: "I need to calculate the value Sam assigns to each option.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Value to Sam: 0 + 0.5(10) = 5\n\nOption B: Sam receives " (stop=max_tokens)
- wtrcal-bcd8d4791e6d656d: 'I need to calculate the value Sam assigns to each option.\n\nFor option A: Sam receives 5 points, I receive 0 points\nValue to Sam = 5 + 1(0) = 5\n\nFor option B: I receive 10 points, Sam receives 0 ' (stop=max_tokens)
- wtrcal-718217c801abe842: "I need to calculate which option Sam will choose based on Sam's value function: Sam's points + 1 × Your points.\n\nOption A: Sam receives 5 points, You receive 0 points\nSam's value = 5 + 1(0) = 5\n\nOption B" (stop=max_tokens)
- wtrcal-8c0529edd68ee73c: "I need to determine which option Sam will choose based on Sam's valuation function: Sam's points + 1 × my points.\n\nLet me evaluate each option from Sam's perspective:\n\nOption A: I receive 10 points\n- Sam's points: 0\n- My points: 10" (stop=max_tokens)
- wtrcal-661c29244e8c6c5b: "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 1 × Your points.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's valuation: 0 +" (stop=max_tokens)
- wtrcal-fd92dec8e1aa6fac: "I need to calculate the value Sam assigns to each option.\n\nFor option A: Sam receives 20 points, I receive 0 points\nValue to Sam = Sam's points + 1 × my points = 20 + 1(0) = 20\n\nFor option B: I" (stop=max_tokens)
- wtrcal-b22336a6d48d095d: "I need to calculate which option Sam will choose based on Sam's value function: Sam's points + 1 × Your points.\n\nOption A: Sam receives 20 points, You receive 0 points\nSam's value = 20 + 1(0) = 20\n\nOption B" (stop=max_tokens)
- wtrcal-2e2ba0eab5707164: "I need to calculate the value Sam assigns to each option.\n\nSam's value function = Sam's points + 1 × Your points\n\nOption A: You receive 10 points, Sam receives 0 points\n- Sam's value = 0 + 1(10) = 10" (stop=max_tokens)
- wtrcal-dd80476dfb77878c: "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 1 × Your points.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's valuation: 0 +" (stop=max_tokens)
- wtrcal-9d89eb44d5fcd68b: "I need to calculate the value Sam assigns to each option.\n\nFor option A (Sam receives 10 points):\n- Sam's points: 10\n- My points: 0\n- Value to Sam: 10 + 2(0) = 10\n\nFor option B (I receive" (stop=max_tokens)
- wtrcal-1d6c1f382962a92d: "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 2 × Your points.\n\nOption A: Sam receives 10 points, You receive 0 points\nSam's valuation: 10 + 2(0) = 10" (stop=max_tokens)
- wtrcal-4edaa7ed3fa35fab: "I need to determine which option Sam will choose based on Sam's value function: Sam's points + 2 × my points.\n\nOption A: I receive 10 points, Sam receives 0 points.\nValue to Sam = 0 + 2(10) = 20\n\nOption" (stop=max_tokens)
- wtrcal-c9f98db7d041b7af: "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 2 × Your points.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's valuation: 0 +" (stop=max_tokens)
- wtrcal-f079cd2829785ab5: "I need to calculate which option Sam will choose based on Sam's valuation: Sam's points + 2 × my points.\n\nOption A: Sam receives 40 points, I receive 0 points.\nValue to Sam = 40 + 2(0) = 40\n\nOption" (stop=max_tokens)
- wtrcal-907d9abc56ec399d: "I need to calculate which option Sam will choose based on Sam's valuation function: Sam's points + 2 × Your points.\n\nOption A: Sam receives 40 points, You receive 0 points\nValue to Sam = 40 + 2(0) = 40\n\nOption" (stop=max_tokens)
- wtrcal-075664701bc37292: "I need to calculate the value Sam assigns to each option.\n\nFor option A: You receive 10 points, Sam receives 0 points.\nValue to Sam = Sam's points + 2 × Your points = 0 + 2(10) = 20\n\nFor option B:" (stop=max_tokens)
- wtrcal-fa6c285838ce4a2e: "I need to calculate which option Sam will choose based on Sam's valuation: Sam's points + 2 × Your points.\n\nOption A: You receive 10 points\n- Sam's points: 0\n- Your points: 10\n- Sam's valuation: 0 + " (stop=max_tokens)
- wtrcal-fc7856b446131a01: "I need to determine who receives points based on Sam's likely choice between:\n(A) You receive 10 points\n(B) Sam receives 1 point\n\nSam tried to help me move boxes but couldn't due to a bad shoulder. I ended up doing it myself. Now Sam is choosing between" (stop=max_tokens)
- wtrcal-7fd24aea46e706cd: "Looking at Sam's previous choices:\n\n1. Sam chose 35 for Sam over 10 for you (took the larger personal gain)\n2. Sam chose 5 for Sam over 10 for you (took the smaller amount to keep it from me)\n\nThe second choice is particularly revealing" (stop=max_tokens)
- wtrcal-0d16f6205fe95725: "Looking at Sam's previous choices:\n\n1. Sam chose 35 for Sam over 10 for you (took the larger personal gain)\n2. Sam chose 5 for Sam over 10 for you (took the smaller amount to keep it from you)\n\nThe second choice is particularly revealing" (stop=max_tokens)
- wtrcal-11e40604c98a30ee: "Looking at Sam's previous choices:\n- Sam chose 15 points for Sam over 10 points for me\n- Sam chose 25 points for Sam over 10 points for me\n\nThis shows Sam consistently prefers personal gain over giving me points, even when the benefit to me would be the" (stop=max_tokens)
- wtrcal-d9f39cd15742736b: "Looking at Sam's previous choices:\n- Sam chose 15 points for Sam over 10 points for me\n- Sam chose 25 points for Sam over 10 points for me\n\nThis shows Sam consistently prefers personal gain over giving me points, even when the personal gain is relatively small (" (stop=max_tokens)
