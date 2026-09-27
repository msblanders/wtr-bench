# Public data record for the social-inference research note

Archived 2026-09-27. This index accompanies the [research note](research-note-v1.md)
and the [mechanism proposal](irv-mechanism-proposal-v0.2.md). The proposal is future
work; the records below contain behavioral measurements, not activation interventions.

## Original collection archives

These are byte-for-byte copies of the original GitHub Actions ZIP artifacts, committed
to the repository so access does not depend on Actions retention or sign-in. Each ZIP's
SHA-256 and byte count matched GitHub's artifact metadata when archived. No model was
called again and no response was edited. Source revisions, artifact IDs, archive hashes,
and hashes of the item and response files are in the [manifest](../results/archive/manifest.json).

| Collection | Original ZIP | Recorded social/validation responses | Original run |
|---|---|---:|---|
| Numerical paired validation, v2 | [Download](../results/archive/paired-ordinal-v2-36190042216-1.zip?raw=true) | 240 | [36190042216](https://github.com/msblanders/wtr-bench/actions/runs/36190042216) |
| Natural-language validation, v3.2 | [Download](../results/archive/paired-natural-v3.2-36200022149-1.zip?raw=true) | 280, including 40 exploratory items | [36200022149](https://github.com/msblanders/wtr-bench/actions/runs/36200022149) |
| Sonnet 4.5 social pilot | [Download](../results/archive/paired-pilot-v1-36216737006-1.zip?raw=true) | 144 | [36216737006](https://github.com/msblanders/wtr-bench/actions/runs/36216737006) |
| Qwen3-14B, non-thinking, unsuccessful attempt | [Download](../results/archive/paired-open-v1-36274679302-1.zip?raw=true) | 0 answers; one HTTP 402 error record | [36274679302](https://github.com/msblanders/wtr-bench/actions/runs/36274679302) |
| Qwen3-14B, non-thinking, completed replication | [Download](../results/archive/paired-open-v1-36278388351-1.zip?raw=true) | 144 | [36278388351](https://github.com/msblanders/wtr-bench/actions/runs/36278388351) |
| Qwen3-14B, thinking | [Download](../results/archive/paired-reasoning-v1-14b-thinking-36281301593-1.zip?raw=true) | 144, plus a separately recorded canary | [36281301593](https://github.com/msblanders/wtr-bench/actions/runs/36281301593) |
| Qwen3-32B, thinking | [Download](../results/archive/paired-reasoning-v1-32b-thinking-36281301593-1.zip?raw=true) | 144, plus a separately recorded canary | [36281301593](https://github.com/msblanders/wtr-bench/actions/runs/36281301593) |

Each archive includes `items.jsonl`, `responses.jsonl`, the collection-start record,
and its original reports and metadata. The later archives also include frozen source
snapshots and provider request records; the exact contents differ by protocol version.
Model-written explanations and, where returned, reasoning traces are outputs to audit,
not privileged evidence about internal computation. The failed funding attempt is
preserved separately from the completed non-thinking replication.

All five social-collection ZIPs, including the unsuccessful attempt, contain the same
144-line `items.jsonl`, with SHA-256
`8544ce8f81447f4074e21efa8b8af013409c11eba4940640765f03f608a1890e`.
The two validation collections use their own item streams. Repeated presentations do
not increase the number of independent social scenarios beyond six.

To verify the downloaded archives, put them beside [SHA256SUMS](../results/archive/SHA256SUMS)
and run `sha256sum -c SHA256SUMS`. Extract archives into separate directories to avoid
overwriting files with the same names. Consult the original plans and the
[thinking-extension audit](thinking-36281301593-review.md) for scoring and scope.

## Earlier instrument-development records

These raw records were already committed before this archive was added. The links
retain failed instruments and diagnostic runs rather than selecting positive results.

| Evidence in the essay | Raw records | Audit |
|---|---|---|
| Sonnet's 151/156 second-option valuation answers | [36077785515](../results/debug/36077785515/) | [Review](debug-36077785515-review.md) |
| Explanations and remaining order sensitivity | [36095971330](../results/debug/36095971330/) | [Review](debug-36095971330-review.md) |
| Wider payoff ladder and censoring | [36099597085](../results/diagnostics/36099597085/) | [Review](measurement-36099597085-review.md) |
| Supplied-weight and history-derived recovery | [36111049496](../results/diagnostics/36111049496/) | [Review](recovery-36111049496-review.md) |
| Payoff-display diagnostic | [36115733552](../results/diagnostics/36115733552/) | [Review](presentation-36115733552-review.md) |

Other historical diagnostics remain under [results](../results/), with their associated
review documents in [docs](./). The archive does not add a new experiment or replace
any frozen plan.

## Citing a stable snapshot

Use GitHub's **Copy permalink** on this file, the research note, or the proposal when
citing a fixed version. A URL containing a commit SHA fixes the content; a `main` URL
follows later revisions. Relative links from a commit-pinned copy of this index point
to the same snapshot. These committed files do not have Actions artifact expiry.
This is a repository archive, not a DOI deposit or a promise of preservation if the
repository itself is removed.
