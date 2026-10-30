# Fixed-evidence search-budget pilot

Eight paired runs; 48 training trajectories; 96 budget-selected models; no API calls.

| Suite | Steps | Readout | Evolution | Random search | Matched gradient |
|---|---:|---|---:|---:|---:|
| canonical_seen | 512 | interaction | 0.229914 | 0.244306 | 0.227990 |
| canonical_seen | 512 | wide_control | 0.228790 | 0.243329 | 0.230862 |
| canonical_seen | 2048 | interaction | 0.227102 | 0.243412 | 0.224984 |
| canonical_seen | 2048 | wide_control | 0.227442 | 0.241132 | 0.227721 |
| canonical_heldout | 512 | interaction | 0.230145 | 0.244180 | 0.227769 |
| canonical_heldout | 512 | wide_control | 0.228743 | 0.243749 | 0.230546 |
| canonical_heldout | 2048 | interaction | 0.227469 | 0.243482 | 0.224880 |
| canonical_heldout | 2048 | wide_control | 0.227655 | 0.241559 | 0.227576 |
| shifted | 512 | interaction | 0.225865 | 0.261911 | 0.220818 |
| shifted | 512 | wide_control | 0.220682 | 0.255275 | 0.225864 |
| shifted | 2048 | interaction | 0.219858 | 0.252823 | 0.217549 |
| shifted | 2048 | wide_control | 0.219434 | 0.260532 | 0.218401 |
| external_games | 512 | interaction | 0.315270 | 0.339996 | 0.315307 |
| external_games | 512 | wide_control | 0.324329 | 0.342062 | 0.322987 |
| external_games | 2048 | interaction | 0.314994 | 0.360864 | 0.302202 |
| external_games | 2048 | wide_control | 0.326172 | 0.342205 | 0.322302 |

Joint primary criteria satisfied: False

The longer budget replays the same training evidence. Each budget selects among 512 development candidates plus the initial model. External benchmarks and architecture-superiority checks are secondary.
