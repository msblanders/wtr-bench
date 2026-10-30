# Functional learning pilot

Data origin: anthropic_api.

Recorded 256/256 responses; valid 109; cost $3.511.

Positive contrasts favor the functional procedure. World-level bootstrap intervals are exploratory.

| Environment | Comparator minus functional | Complete worlds | Mean MSE advantage | 95% interval |
|---|---|---:|---:|---|
| shared | general minus functional | 8 | -0.03329686497471679 | [-0.11180324959109818, 0.007793208240901034] |
| shared | structured minus functional | 8 | 0.23621084279111884 | [0.11900439371051864, 0.3160596143777577] |
| shared | wrong_routing minus functional | 8 | -0.0010936322706970646 | [-0.0024634252508511957, 0.0006968535515214621] |
| context_specific | general minus functional | 8 | -0.0027862511117335807 | [-0.11897409571306898, 0.10780138178088366] |
| context_specific | structured minus functional | 8 | 0.18620725175977462 | [0.07443845551676838, 0.2959084140707381] |
| context_specific | wrong_routing minus functional | 8 | 0.034814339545566446 | [-0.0031809131655281785, 0.10725939182604266] |

Malformed outputs receive error 1 in the primary utility score; valid-only scores are in report.json.
Missing responses are not imputed. Incomplete runs do not establish the planned contrast.
This tests supplied procedures for using context, not training efficiency or evolved neural organization.

## Learning curves

| Environment | Evidence per partner | Procedure | Collected | Mean MSE | Transfer-choice MSE |
|---|---:|---|---:|---:|---:|
| shared | 0 | general | 8 | 0.07656855942528171 | 0.0646415726911791 |
| shared | 0 | structured | 8 | 0.07656855942528171 | 0.0646415726911791 |
| shared | 0 | functional | 8 | 0.07656855942528171 | 0.0646415726911791 |
| shared | 0 | wrong_routing | 8 | 0.07656855942528171 | 0.0646415726911791 |
| shared | 2 | general | 8 | 0.0751904908029252 | 0.06009966417006268 |
| shared | 2 | structured | 8 | 0.883713614100432 | 0.8823176098627202 |
| shared | 2 | functional | 8 | 0.17508108572707556 | 0.1639302030882408 |
| shared | 2 | wrong_routing | 8 | 0.17180018891498436 | 0.16027951263684198 |
| shared | 8 | general | 8 | 1.0 | 1.0 |
| shared | 8 | structured | 8 | 1.0 | 1.0 |
| shared | 8 | functional | 8 | 1.0 | 1.0 |
| shared | 8 | wrong_routing | 8 | 1.0 | 1.0 |
| shared | 24 | general | 8 | 1.0 | 1.0 |
| shared | 24 | structured | 8 | 1.0 | 1.0 |
| shared | 24 | functional | 8 | 1.0 | 1.0 |
| shared | 24 | wrong_routing | 8 | 1.0 | 1.0 |
| context_specific | 0 | general | 8 | 0.08487069889834793 | 0.07905263791513477 |
| context_specific | 0 | structured | 8 | 0.08487069889834793 | 0.07905263791513477 |
| context_specific | 0 | functional | 8 | 0.08487069889834793 | 0.07905263791513477 |
| context_specific | 0 | wrong_routing | 8 | 0.08487069889834793 | 0.07905263791513477 |
| context_specific | 2 | general | 8 | 0.2003626794937864 | 0.21756114953972255 |
| context_specific | 2 | structured | 8 | 0.7673431881083109 | 0.7797788107025024 |
| context_specific | 2 | functional | 8 | 0.20872143282898714 | 0.263088885230307 |
| context_specific | 2 | wrong_routing | 8 | 0.31316445146568644 | 0.36467242448639053 |
| context_specific | 8 | general | 8 | 1.0 | 1.0 |
| context_specific | 8 | structured | 8 | 1.0 | 1.0 |
| context_specific | 8 | functional | 8 | 1.0 | 1.0 |
| context_specific | 8 | wrong_routing | 8 | 1.0 | 1.0 |
| context_specific | 24 | general | 8 | 1.0 | 1.0 |
| context_specific | 24 | structured | 8 | 1.0 | 1.0 |
| context_specific | 24 | functional | 8 | 1.0 | 1.0 |
| context_specific | 24 | wrong_routing | 8 | 1.0 | 1.0 |
