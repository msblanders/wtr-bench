# Neural update pilot: completed results

**The primary comparison favored the shared contextual update network. Independently parameterized update networks did not improve data efficiency in this pilot.**

[Completed run 41008849744](https://github.com/msblanders/wtr-bench/actions/runs/41008849744). Eight paired training replicates, three models per replicate, zero API calls. All models within a replicate received exactly the same training observations, verified by stream hashes. All 24 models completed the frozen training schedule; no outcome-driven changes or reruns were made.

## Prespecified primary result

Error is mean squared deviation from the exact Bayesian mixture's next-observation probability. The primary data-efficiency endpoint averages this error across 64, 256 and 1,024 training updates. Lower is better. Training uses observed next outcomes; family labels, latent states and oracle predictions are excluded.

| Model | Across training checkpoints | Final checkpoint | Longer histories at final checkpoint |
|---|---:|---:|---:|
| Shared contextual updater | 0.002577 | 0.001488 | 0.004825 |
| Two routed update networks | 0.003127 | 0.001333 | 0.004506 |
| Single dense recurrent network | 0.003259 | 0.001013 | 0.004043 |

The shared model's primary error was **17.6% lower** than the routed model's. The paired shared-minus-routed difference was **−0.000550**, with a bootstrap 95% interval **[−0.001193, −0.000042]** across eight complete training runs. Five of eight paired differences favored shared updates. This is an exploratory pilot interval; it should not be treated as a general architecture ranking.

The secondary dense-minus-routed primary-score difference was +0.000132, with interval [−0.000621, +0.000755]. At the final checkpoint the dense model had the lowest average error; this final ranking is descriptive, not the prespecified primary contrast.

## Where the advantage occurred

| Training updates | Dense | Routed | Shared contextual |
|---|---:|---:|---:|
| 64 | 0.006055 | 0.005606 | 0.003788 |
| 256 | 0.002709 | 0.002443 | 0.002457 |
| 1024 | 0.001013 | 0.001333 | 0.001488 |

The shared model's advantage was concentrated at the early checkpoint. It was not the best final model. All three had larger errors on positions 33–64 than on the 32-position training horizon; longer-history generalization remains imperfect.

## Resource accounting

| Model | Parameters | State values | Approx. forward matrix MACs/observation | Mean training seconds |
|---|---:|---:|---:|---:|
| dense | 1153 | 18 | 1044 | 6.78 |
| routed | 1156 | 24 | 1008 | 12.94 |
| shared | 1210 | 34 | 2142 | 9.03 |

The shared comparator was deliberately generous: about 4.7% more parameters, more memory state, and more recurrent matrix arithmetic than the routed model. The dense comparator was nearly parameter-matched. Data and optimizer-update counts match; total FLOPs do not. Matrix MAC estimates omit nonlinearities, elementwise operations and backpropagation. The result supports adequacy of this shared architecture, not a resource-isolated proof that sharing is intrinsically better.

## Secondary routing diagnostics

Expert-to-family assignments were chosen on a separate validation stream after training. Neither the routed nor shared two-bank model showed a held-out crossed expert preference in any of the eight runs: under forced-expert readouts, the assigned expert did not beat the other expert for both respective families. Uniform gating worsened average final error (routed: 0.018396; shared: 0.009953), showing reliance on the learned mixture, but not identifying task-specific expert algorithms.

These interventions can disrupt complementary predictions and coadapted readouts. Their failure to produce a clean dissociation is not proof that no internal functional specialization exists. The exact full-branch permutation symmetry was checked independently in development tests.

## Implication for the research program

The earlier finite-program selection result established that appropriate evidence gates and transfer settings can be selected in a specified search space. This stronger neural comparison does not support a blanket efficiency advantage for independently parameterized updates. A shared conditional update function can learn both stable-rate inference and changing-state tracking under these budgets.

Parameter sharing is compatible with conditional functional specialization inside a network. This experiment therefore does not settle the broader evolutionary-psychology claim or demonstrate one invariant computation. It narrows the engineering claim: separate update networks should not be assumed beneficial merely because the generating problems require different Bayesian computations. A subsequent test needs a specified source of computational conflict, interference or constrained memory, with predictions fixed before inspecting results.

## Files and provenance

Source/protocol were frozen at [29b0dacee664ac995bcf020f1acad2ec6d3693aa](https://github.com/msblanders/wtr-bench/tree/29b0dacee664ac995bcf020f1acad2ec6d3693aa/experiments/neural-update-v1); launch commit was cabfbbfd711289dfbc33c99f1dbf6cea4758744c. The eight development checks passed, including a Bayesian-reference comparison with exhaustive latent enumeration. Standard project CI also passed for the frozen source.

- `summary.json`: original aggregate results from the completed workflow.
- `replicate-results.json`: every model/checkpoint score, routing intervention, training trace, data hash and runtime for all eight paired runs.
- `manifest.json`: exact configuration, source hashes, dependency versions and seed plan.
- `diagnostics.json`: descriptive checkpoint means and validation-aligned forced-expert differences derived from the saved per-run metrics.
- `artifacts.json`: identities and SHA-256 digests of the original workflow artifacts. Per-seed artifacts contain every saved checkpoint weight file; the protocol artifact contains the frozen source.

All files here are synthetic experiment outputs. No API responses or private user data are included. This results interpretation was written after completion; it does not alter the frozen protocol.
