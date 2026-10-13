# Ruling-3 acceptance (conditions 3 and 4, addenda 4–6) on host 0.2.18, page `b24d754a…`

- **Probes and judge:** the probes as of `becd0370`; the judge as of `60655ab5`, which includes S1, N1 and addendum 6.
- **Runs:** all arms, default rounds, Chrome then Firefox, one job at a time, 2026-10-13. Held ran 02:27–02:36Z, table 02:36–02:45Z. Probe exit 0 both, no fatal round.
- **Static:** before = after in both reports: host 0.2.18 (`f5b34f0`, info.xml uncommitted on purpose), buildId `d6d04880f56e31da`, served page = dist page = `b24d754a…`.

| probe | judge | rounds |
|---|---|---|
| `held/` | **exit 0, PASS** (`judge-output.txt`) | start-press 1, start-hold 2, end-hold 2, end-press-type 1 per browser: all PASS |
| `table/` | **exit 0, PASS** (`judge-output.txt`) | before-table-press-type, before-table-hold, cell-press-type, cell-hold 1 each; cell-start-hold 2 per browser: all PASS |

**Raw inputs worth naming:**

- **`scrollTop` on the end arms:** every sample from the refusal to the end of the log is ≥ `pre`. Chrome: `pre` 21477, series [21477] or [21477, 21596]. Firefox: `pre` 21463, series [21463] or [21463, 21582]. No sample at 0. On `6470dec0` the same arms had `21477 → 0 → 21477`.
- **`start-hold`:** `wvy` at the start of paragraph 0 on 4/4 rounds. On `aebef525` it FAILed 4/4.
- **`cell-start-hold`:** the stage is `nothing-selected` on 4/4 rounds, and paragraph 1 is exactly `wvy` followed by the original A1 (`paragraph1IsAfterThenOriginal` true). On `aebef525` `wvy` was one character in.
- **`cell-press-type`:** `kjzqx` is contiguous in paragraph 1. **`cell-hold`:** `wvy` is at the end of paragraph 1. On `6470dec0` both had their mark in B1.
