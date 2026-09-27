# Does a relational valuation representation causally coordinate social judgments?

**Mechanism study proposal, v0.2 — draft, not a frozen confirmatory protocol.**
Mitchell Landers. Companion to the [behavioral note](research-note-v1.md).
This develops the September 22 Study 1 IRV mechanism-recovery draft. It preserves the strong
full-history alternative and corrects an ambiguity: physical separation is not sufficient
evidence that a shared abstract causal variable is absent. No mechanism experiments are
reported as completed here.

## Research question and intended contribution

When a language model predicts several actions by person A toward person B, are those
judgments causally coordinated by a representation of A's regard for B, or produced by more
task-specific computations? The target is an **inferred directed relationship**, A→B. It is
not the model's own preference, global niceness, ability, or the numerical magnitude of a WTR.
A scalar IRV/WTR is one candidate abstraction; a low-dimensional or context-dependent state
is an alternative, and the experiment must permit that result.

The behavioral pilot provides a starting phenomenon: in two tested configurations, a person
who tries but fails is favored on giving, while a capable refuser is favored on same-task
ability. Separate semantic rules can explain this. The proposed contribution is to calibrate
an intervention diagnostic on constructed systems, then test selective transfer for a directed
social relation in an inspectable language model. Decoding and steering belief representations,
distributed causal alignment and explicit/implicit mental-state gaps already have precedents.
We do not claim the first social representation, first causal probe, or first interchange
intervention. A broader literature review is required before asserting novelty.

## Work packages and decisions

| Package | Concrete output | What it can establish | Decision before proceeding |
|---|---|---|---|
| 0. Local behavioral bridge | Pinned Qwen3-32B run, 145 recorded generations, public audit | Behavior occurs in the inspectable implementation | If the fixed primary pattern fails, report it; do not select interventions on a behavior the checkpoint lacks |
| 1. Constructed world and learners | Seeded simulator, causal graphs, train/development/test splits, competence-matched families | Ground truth within explicitly defined synthetic systems | Match canonical competence without tuning on diagnostic test results |
| 2. Diagnostic recovery/calibration | Held-out recovery and false-positive estimates across whole learners and nuisance regimes | Whether the proposed test distinguishes the specified causal organizations | If it cannot, revise/calibrate before treating an LLM result as mechanism evidence |
| 3. LLM causal transfer | Frozen intervention sites/subspaces and held-out donor/recipient tests with controls | Evidence for or against the tested relational causal abstraction | Judge selectivity and held-out transfer, not decoding accuracy alone |

Packages 1–2 use small networks on CPU and can start while the bridge is being run. Package 3
requires an exhibited target behavior, activation access, and calibration. The bridge itself
is **not the mechanism study**. The hosted thinking extensions are also behavioral studies.
A proposal for Packages 1–3 can accompany the current note before any mechanism result exists.

## Package 1: world with independently manipulable causes

Construct a finite social world with several named agents and directed relationships. Define
latent regard q(A→B), task ability a(A,k), personal cost c, benefit to the recipient b, and
opportunity o separately. Independently randomize these causes rather than using helpfulness
as a proxy for both regard and competence. Include relational histories, failures, refusals,
missing opportunities and nuisance cues such as name, presentation order and neutral wording.

An initial, explicitly synthetic generator for voluntary action is:

`P(attempt A→B) = o × sigmoid((q(A→B) × b − c) / tau)`

and for task success conditional on an attempt:

`P(success | attempt) = a(A,k)`.

These equations define the constructed world's ground truth; they are not fitted claims about
human psychology. Allocation, costly support and harm avoidance need separately specified
utility/readout equations sharing q but preserving task-specific inputs. Histories are sampled
from the world; learners see histories and current circumstances, not a privileged q label.
Ambiguous evidence must imply uncertainty. An oracle posterior over the finite latent grid can
supply reference predictions without assuming learners recover the exact latent magnitude.

Before confirmatory training, freeze q/ability grids, cost/benefit ranges, noise tau, history
lengths, opportunity missingness, target equations and sample counts. Include matched histories
where aggregate good/bad outcomes agree but their causal explanations differ. Include A→B,
A→C, and C→B so relation identity can be separated from actor and recipient identity.

Split by full world/relationship history and random seed into training, canonical competence
assessment, diagnostic development and untouched diagnostic test sets. Reserve changes in cue
reliability, noise, task cost, and combinations of familiar causes as distribution shifts.
Do not place paraphrases or samples from the same history on both sides of a split.

### Learner families and honest ground truth

1. **Shared bottleneck:** a history encoder yields a relational state z(A→B); four judgment
   heads use that state plus the same permitted task context. The stipulated graph has a
   common mediator, and interventions on that mediator supply known causal tests.
2. **Independent full-history learners:** four separately parameterized predictors each receive
   the entire same history and permitted task context. No shared activations or parameters are
   required, but each can independently learn a q-like representation. This is the strong
   alternative, not an evidence-deprived straw model.
3. **Secondary controls:** evidence-isolated task systems, irrelevant shared bottlenecks,
   distributed/reparameterized shared systems, and duplicated q encodings. These characterize
   easy discrimination, lexical/nuisance shortcuts, and the distinction between anatomical
   sharing and an abstract variable implemented at several sites.

A shared encoder with disjoint readouts is not an adequate “no shared variable” control: the
encoder can copy the relevant state into each readout. Similarly, independent full-history
networks cannot simply be labeled “no abstract valuation.” Their lack of a single shared node
is an architectural fact; whether an allowed distributed intervention realizes the same
high-level causal abstraction is a separate empirical question.

Match canonical predictive competence, training data, training budget and approximate parameter
count using declared tolerances. Report residual mismatches and learning curves. Do not match
on held-out diagnostic performance or exclude awkward seeds after viewing it. Use pilot seeds
only to set tolerances and network widths, then retire them from confirmatory evaluation.
The old draft's 40 instances per family remains provisional; select confirmatory instance counts
from a simulation-based precision/power analysis after development, not as a settled requirement.

## Package 2: recover mechanisms before trusting the diagnostic

Behavioral diagnostics include transfer of a latent predictor trained on two judgments to the
other two, rank stability, coherent responses to cue interventions, nuisance crossovers, and
novel-context transfer. These tests are not mechanism identification by themselves. First ask
how often they distinguish the constructed families on unseen learner instances and shifts.

For causal recovery, intervene on known z, irrelevant state, task-specific state, and controlled
distributed copies. Compare an intervention's output vector with the counterfactual vector
predicted by the constructed world's relational intervention. Include the direct oracle
intervention as a positive control. Use identical intervention budgets and search capacity
across families. Declare whether multi-site joint interventions are allowed; an unrestricted
search can manufacture an apparent shared variable by coordinating independent computations.

Use development learners to fix the diagnostic, site/subspace search, dimensionality, control
set and decision threshold. On untouched learners, report sensitivity, specificity, false-positive
rate, held-out predictive fit, and uncertainty. Any classifier must be low capacity, with whole
learner instances and nuisance regimes held out. Include a canonical-competence-only classifier
as a negative control for architecture/capacity confounding. Bootstrap learners, not individual
responses from the same learner.

**Calibration gate:** predeclare a tolerable false-positive rate, minimum sensitivity and
interval precision before the untouched calibration test. Choose the sample size to evaluate
those bounds. Do not claim the gate has been specified numerically in this draft. If duplicated
or distributed task-specific systems reliably pass, characterize that ambiguity and restrict
the eventual claim to the identifiable causal abstraction. Failure to distinguish them is a
substantive result about the diagnostic, not a reason to rename the controls.

## Package 3: selective causal transfer in Qwen

After the local bridge, build a new, independently frozen stimulus set. The original six
stories established feasibility; they cannot be reused indefinitely for discovery and final
confirmation. Independently vary regard evidence, ability, cost and opportunity with explicit
story constraints and held-out relations, names, tasks and templates. Validate that the new
items produce the intended behavioral contrasts before interpreting activation interventions.

Use a context-only history prefix followed by several possible questions. A candidate “maintained
state” should be accessible after reading the relationship evidence and before seeing which
judgment will be requested. Hold prompt length/token boundaries stable within donor–recipient
pairs where practicable, and record the exact intervention positions. Behavior found only after
a task-specific answer has already formed supports a different, weaker interpretation.

Develop candidate layers and low-dimensional subspaces on a discovery split. Linear decoding
is a screening tool, not the causal result. Start with clean donor/recipient contrasts that
change regard evidence while holding actor ability, task demands, costs and opportunity fixed.
Interchange only the candidate relational component; compare held-out outputs with the
counterfactual relation change. Freeze search choices before the confirmatory split.

The primary target is **selective cross-task counterfactual agreement**: a regard intervention
should shift judgments about that same A→B relation across held-out giving/helping/costly-support
or harm-avoidance tasks in the predicted direction. Controls should show materially smaller
changes, using equivalence bounds rather than treating a nonsignificant difference as invariance.
Predefine the numerical effect and selectivity bounds after synthetic calibration and development.

Required controls include:

- **Ability:** an ability intervention changes competence judgments; a regard intervention
  should not simply substitute competence, particularly when effort is stipulated.
- **Relation identity:** compare A→B with A→C and C→B; the effect must not be a global actor
  or recipient positivity shift. Counterbalance names and answer labels.
- **General valence and wording:** positive/negative but non-relational descriptions, sentiment
  directions, norm-matched random subspaces and sham/no-op patches.
- **Output coding:** alternate response mappings, held-out tasks and prefixes before the task
  question, so transplanting an A/B preference or an answer representation cannot suffice.
- **Intervention integrity:** donor/recipient similarity, patch magnitude, general language
  competence checks and comparison against relevant task-specific interventions.

Report all frozen controls and effect distributions, including failed donor pairs. Resample
independent relationship/world instances for uncertainty; do not count token positions as
independent observations. Separate discovery, validation and confirmation in both code and
reporting. Test dose/magnitude sensitivity and off-manifold effects as declared robustness
analyses, not a search for the most favorable patch.

A positive result would support a specified relational causal abstraction under these
interventions and contexts. It would not establish a unique neuron, biological homology,
innateness, consciousness, human-like motives, or a universal WTR. A null result could reflect
a wrong site/subspace, nonlinear/distributed encoding, unstable behavior, inadequate power,
or absence of the proposed organization; report which alternatives the controls can resolve.

## Resources, milestones and application framing

The present repository supplies frozen behavioral items, strict scoring, provenance checks and
the local bridge runner. The synthetic generator, learner training and intervention pipeline
are **proposed work, not implemented deliverables of this version**.

A practical first ask is mentorship in causal representation analysis, CPU time for recovery
experiments, and a modest allocation of 80 GB GPU time for the bridge and initial Qwen work.
Fine-tuning a 32B model is not part of this first plan. Activation-only workflows may fit one
80 GB GPU for selected sites; gradient-based alignment and long traces require a measured
memory/compute budget before allocation. Ordinary hosted API access cannot supply the needed
activations. The bridge's few dollars or hours of rental cannot be inferred from the earlier
six-cent API bill; obtain an actual host quote and measure throughput before estimating costs.

Milestones are (1) local audited result; (2) frozen synthetic generator and competent learners;
(3) held-out calibration report; (4) frozen LLM intervention protocol; (5) a complete causal
transfer report, whether positive, negative or diagnostically inconclusive. This is a multi-stage
research project, not a promised two-week mechanism result.

For a fellowship or research conversation, the completed note demonstrates execution and
measurement judgment. This proposal explains the next question, the failure conditions and
the support required. It is useful to submit the note and proposal together; there is no need
to portray the unfinished mechanism project as a prerequisite already fulfilled.

## Related work to anchor the proposal

- [Geiger et al. (2024), Finding Alignments Between Interpretable Causal Variables and Distributed Neural Representations](https://proceedings.mlr.press/v236/geiger24a.html): distributed alignment/interchange framework.
- [Zhu, Zhang & Wang (2024), Language Models Represent Beliefs of Self and Others](https://arxiv.org/abs/2402.18496): decoding and interventions on belief representations.
- [SimpleToM](https://arxiv.org/abs/2410.13648): explicit mental-state inference can diverge from its application to judgments.

These examples establish precedent, not an exhaustive novelty review. The contribution must be
judged against the broader current literature before a submission claims priority.
