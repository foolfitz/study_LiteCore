# Handoff, 2026-10-03 — J done: `INSTALLS ELSEWHERE` on host 0.2.5

Entry points: this file, `findings/evidence/m3-install/RESULT-0.2.5.md` (the verdict, browser limitation first), `findings/evidence/m3-install/README.md` section "0.2.5 (J, 2026-10-02)", `specs/SPEC-M3-install-elsewhere.md` (§3.3 last bullet, §4 I3 items 8–14, the three 2026-10-02 revision rows), `findings/evidence/m3-install/review-2026-10-02-opus-i3-9-12.md` (second review, dispositions at its top).

Picks up from `handoff/HANDOFF-2026-10-02-j-reinstalled-owner-chose-b.md`. Its "What is next" items 1–6 are done; item 7 is unchanged and is now the head of the queue (below).

## Verdict

`findings/evidence/m3-install/runs/2026-10-02T162328+0000.json`: **`INSTALLS ELSEWHERE`**, 7,172 samples over 3653 s (16:23:36–17:24:29Z), no problem; re-scored from the stored report the same; red cases 153/153 at scoring. On litecoreprobe: assets `ASSETS DELIVERED` (Chrome 3/3, Firefox 3/3, Firefox-nozstd 3/3), versions `VERSIONS CORRECT` (3/3, 3/3), host entry `LANDS`, locks `LOCKS LAND` (52/52). **Every litecoreprobe run was on Firefox 157.0**; the dev baseline it is compared with ran on 156.0 (one host-entry baseline report on 157.0). Owner's decision B: a named limitation, not a criterion. The re-check commands in `RESULT-0.2.5.md` were run from a fresh worktree and reproduce (`INSTALLS ELSEWHERE`, 153/153).

## What changed in the criteria (all before any 0.2.5 window)

- **Withdrawn (§4 of "驗收判準的形式"):** I3-8's PRE-era rows (today's scorers re-score PRE-era reports as PRE's did) and the PRE-vs-now recording comparison (now registered: `recording.preDifferences`, 88 `zst*` fields). **Nothing checks the former any more**; the spec says so. The 0.2.1 verdict stays bound to its tools; `RESULT.md` has an appended re-check recipe at `71e0ac8e` (run: `INSTALLS ELSEWHERE`, 111/111).
- **Added:** I3-9 (dev recording path exactly equal to each judged dev baseline report), I3-10 (dev baseline selected by rule from the four `runs/`, re-scored, red-cased, once-committed blobs), I3-11 (since each dev report only the orchestrator changed under `wasm_sdk_probe/`; closure, `git grep` mentions, `devCommit`/`changed` re-derived from git while scoring), I3-12 (criteria equal), I3-13 (run shape and test document equal — host entry's own score does not pin its arms), I3-14 (no other counted dev run between the check and the window — I3-7 cannot be re-run until green). I3-8 gained: equivalence after install, `openssl` + `libssl3t64` package version in the tree binding. Additions to this gate close now that the 0.2.5 counted window has landed; later concerns are findings or post-work.
- I3-11 is deliberately stricter than the first review suggested: `make test-e2-c-static` reads far more than "closure + Makefile + tests + web" (`tools/check_e1_c_bundle_intact.py`, `tools/inventory_corpus_axes.py`, `test-docs/`, `tests/*.py`, `editor-shell/`, `e2/`), so only the orchestrator may change.

## Commits this session (`study_LiteCore`, `main`, not pushed)

| Commit | What |
|---|---|
| `f42d428e` | Spec (withdrawal + I3-9..I3-12, owner's decision B with the owner's words), tool, 0.2.1 RESULT re-check correction. |
| `e565d422` | Under `f42d428e`: equivalence (run twice on the same commit — the second by mistake, same result), I3-7 `2026-10-02T154130Z`, shakedown `154722` (135/135). **Superseded.** |
| `81856daa` | After the second review: I3-13, I3-14, the LIGHT items; review saved verbatim with dispositions. Red cases 135 → 153. |
| `2e1ef711` | Under `81856daa`: equivalence 16:06:54Z (5 baseline reports, 0 problems), I3-7 `2026-10-02T160707Z` (LANDS, 23/23), shakedown `161235` (`--strict --red-cases` 153/153). |
| `d695f798` | The counted window, `RESULT-0.2.5.md`, README. |

## State

- `study_LiteCore`: `main` at `d695f798` plus this handoff's commit, clean, not pushed.
- litecoreprobe runs `litecore` 0.2.5 from archive `602fe6bb…`; web container started 2026-10-02 14:16:50Z. `release.json` is the 0.2.5 record.
- Dev instance: `~/Projects/Nextcloud_Apps/litecore` at `7420418` (0.2.5).
- Firefox 157.0 (snap rev 8995), Chrome 151.0.7922.169, libssl3t64 3.5.5-1ubuntu3.7.

## What is next

1. **The owner's queue, unchanged from 09-30:** A (distribution channel — the owner's outward action), F (finding 105's Firefox-only repro), and the registered list (K0-5 at the a11y cutover, Chrome's gzip path, K2-2's `gzBytes` anchor, brotli, 106 / 108 / 094). Ask the owner which; do not pick an outward action yourself.
2. **Post-work on this gate (not criteria; the gate is closed):**
   - `transcription` (I3-8) now guards only the provenance of a registered comparison (review item 10). The owner asked on 2026-10-03 whether we are chasing verbatim text; this check is the one place in the gate that does. Proposal for the next tool change: register it or delete it. Do not change it in a way that re-scores the 0.2.5 window differently without saying so — the window's re-check is pinned to `d695f798`.
   - The gate's own machinery grew ~600 lines this round (two reviews, 111 → 153 red cases). Before adding anything else to it, ask whether the next install window will happen at all; if not, leave it.

## Things this round taught

- **A justification checked in one direction.** "The orchestrator is not on the runners' path" was proved by "no runner imports it" — true, and beside the point: it launches and judges them. The question to ask of an exempted component is every edge it has to the thing it is exempt from, not the one that was easy to check.
- **"Can proceed" from a reviewer is not "no holes".** The second review found two holes it judged unexercised and said proceed. Closing them before counting cost ~20 minutes (tool, equivalence, I3-7, shakedown); closing them after would have been impossible (§9).
- **Read the raw value once.** `dpkg-query -W -f='${Version}'` printed both architectures with no separator (`3.5.5-1ubuntu3.73.5.5-1ubuntu3.7`); seen in the dry run's output, not by any check.
- **A wrong label on a command is a wrong record.** I re-ran `equivalence` while the echo said "(not re-run)". The result was the same, but the message was false; it is recorded in the commit and here.

## Standing rules to carry

- Never run two M3 runners (or an M3 probe) at once — each clears the whole `oc_files_lock` table.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` version bump and `ddev occ upgrade`.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/` and findings' prose are zh-TW. Specs and gate documents are append-only.
- Don't start or restart other ddev projects during a counted run or an install window.
- `install --reinstall --was <previous record>` for an upgrade.
- Firefox snap may auto-refresh any time; owner's decision B: no re-measurement for a browser upgrade, note the version in each RESULT.
- **New:** a verdict's re-check is pinned to the commit that recorded it (worktree + `dist` symlink, as in both RESULT files); today's tools re-score old windows red by design.
- **New (owner, 2026-10-03):** byte-for-byte equality is for machine data (hashes, git blobs, JSON fields), not prose; don't spend effort matching sentences verbatim.
