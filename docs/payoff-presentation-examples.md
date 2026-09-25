# Matched prompt examples

## original

```text
Sam is an acquaintance. In this constructed example, Sam's value for an outcome is Sam's points plus a fixed nonnegative weight times your points. Sam always chooses the strictly greater value. The same unknown weight holds for all the following decisions. There are no ties. Recently Sam made these two decisions. The choice was 5 points for Sam or 20 points for you; Sam chose the 20 points for you. The choice was 8 points for Sam or 20 points for you; Sam chose the 8 points for Sam. The recipient not named in an option receives 0 points.

Now Sam must choose exactly one option:
(A) Sam receives 2 points.
(B) You receive 10 points.
Which option will Sam choose? Return a JSON object with exactly two fields in this order: "brief_basis", a brief explanation (one or two sentences) for your answer using the supplied information; then "answer", whose value is A or B. Do not include other fields.
```

## explicit_payoffs

```text
Sam is an acquaintance. In this constructed example, Sam's value for an outcome is Sam's points plus a fixed nonnegative weight times your points. Sam always chooses the strictly greater value. The same unknown weight holds for all the following decisions. There are no ties. Recently Sam made these two decisions.

The available outcomes in this decision were:
| Outcome | Points for Sam | Points for you |
|---|---:|---:|
| 1 | 5 | 0 |
| 2 | 0 | 20 |
Sam chose outcome 2.

The available outcomes in this decision were:
| Outcome | Points for Sam | Points for you |
|---|---:|---:|
| 1 | 8 | 0 |
| 2 | 0 | 20 |
Sam chose outcome 1. The recipient not named in an option receives 0 points.

Now Sam must choose exactly one option:
| Option | Points for Sam | Points for you |
|---|---:|---:|
| A | 2 | 0 |
| B | 0 | 10 |
Which option will Sam choose? Return a JSON object with exactly two fields in this order: "brief_basis", a brief explanation (one or two sentences) for your answer using the supplied information; then "answer", whose value is A or B. Do not include other fields.
```
