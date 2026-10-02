# Handoff, 2026-10-02 — J: 0.2.5 reinstalled on litecoreprobe, I3-8 cannot pass as written; owner chose B (no re-measurement for the Firefox upgrade)

Entry points: this file, `findings/evidence/m3-install/review-2026-10-02-opus-i3-8-prime.md` (the
review, verbatim; DETAILS has a verified evidence line per item), `findings/evidence/m3-install/proposal-2026-10-02-i3-8-prime.md`
(the proposal; **not adopted as written**), `findings/evidence/m3-install/equivalence.json` (the
failing run), `findings/evidence/m3-install/install.json` (the 0.2.5 reinstall),
`specs/SPEC-M3-install-elsewhere.md` (§3.3, I3-7, I3-8, the 2026-10-02 revision row),
`wasm_sdk_probe/tools/check_m3_install_elsewhere.py`.

Picks up from `handoff/HANDOFF-2026-09-30-zstd-delivered.md`. Its "What is next" item 1 was J:
install the 0.2.5 release archive on `litecoreprobe` and redo install-elsewhere. The owner said on
2026-10-02 that no other ddev project was in use, and asked for J.

## Owner decision, 2026-10-02 (after the first draft of this handoff): **B — no re-measurement because of Firefox**

The main session first chose the review's option A (fresh dev-instance counted runs of all four
runners on Firefox 157, plus a browser-version equality clause). The owner declined: **"我不想因為
firefox升級的關係重新量測"**, and chose B from these two:

- A (not chosen): `sudo snap revert firefox` back to 156 and hold, keep the 09-29 dev reports as
  the baseline.
- **B (chosen): run J on whatever Firefox is installed (157 today), keep the 09-29 dev reports
  (Firefox 156) as the baseline, no fresh dev runs for the browser's sake, and no browser criterion.
  The browser difference is written into the 0.2.5 RESULT as a named limitation, first, not buried:
  "dev verdicts on Firefox 156.0, litecoreprobe window on Firefox 157.0 (Chrome 151.0.7922.169 on
  both); if any window cell is red, the browser difference is an unexcluded explanation."**

Also stated by the main session to the owner and agreed: **no existing counted verdict is re-run
because of the upgrade**; they stand as measured on Firefox 156. Future counted runs use whatever is
installed. Write this decision, with the quote, into the spec revision row.

The plan in "What is next" below is the B version (rewritten after the decision). The review's
option B fixes (its findings 2, 3, 4, 9) are what replace I3-8.

## Where J stands

**J is half done, and no 0.2.5 install-elsewhere window (shakedown or counted) has run.**

- Done: `litecoreprobe` has `litecore` 0.2.5 from archive `602fe6bb…`, enabled, binding clean.
- Blocked: the equivalence check (I3-8) is red, and I3-8 as written cannot be made green without
  re-pinning old reports to old bindings (machinery to keep an old claim alive; CLAUDE.md
  "驗收判準的形式" §4).
- Decided, **not implemented**: the replacement (below, "What is next" item 1). The first draft of
  it, I3-8′, went to an opus adversarial review before adoption and came back with a BLOCKING
  finding (Firefox drift), so it is not adopted as proposed; the owner then chose B (above).
- **If the replacement is never implemented, the default conclusion is: there is no
  `INSTALLS ELSEWHERE` on 0.2.5.** The 0.2.1 verdict
  (`runs/2026-09-29T012339+0000.json`) stays exactly what it was: bound to host 0.2.1 and to the
  tools and browsers of that day.

**What this does to the existing verdicts.** The review's BLOCKING item: Firefox was auto-refreshed
by snap from 156.0 to 157.0 on 2026-10-01 10:42 CST (`snap list --all firefox`: 156.0-1 rev 8929
disabled, 157.0-1 rev 8995 active; `firefox --version` = 157.0). Chrome is unchanged at
151.0.7922.169; geckodriver 0.37.1. Every counted report under the `runs/` directories of
`m3-assets`, `m3-versions`, `m3-locks`, `m3-host-entry`, `m3-page-honesty`, `m3-same-second`,
`m3-skeleton` and `m3-gate-0` records Firefox 156.0 (a grep of their `"version"` fields, this
session). Any counted run from now on is on 157.0 or later. **The first counted runs on 157 are
themselves the measurement; no claim of regression or of non-regression exists yet.**

## What happened this session (`study_LiteCore`, `main`, not pushed)

| Commit | What |
|---|---|
| `3c99e400` | **J bindings, before any 0.2.5 run.** `findings/evidence/m3-install/release.json` rewritten to 0.2.5 (archive `602fe6bb…`, 111,711,969 bytes, 52 members, built twice byte-identical by `build_m3_release.py`); the 0.2.1 record kept as `release-0.2.1.json`; a revision row appended to `specs/SPEC-M3-install-elsewhere.md`. **That row says "判準條文不動" (criteria text unchanged); the review says this now needs an append-only correction** (item 6), because withdrawing I3-8's rows is a change to a criterion. |
| `c129724d` | `check_m3_install_elsewhere.py install --reinstall --was RECORD`. The first upgrade-reinstall was refused: `--reinstall` compared the existing 0.2.1 install against `release.json`, which was already 0.2.5 — 28 differences. **The guard was right; the comparison target was wrong.** `--was` names the record the existing install must match; new helper `differs_from()` applies the same rules as `host_binding()` but lives in install-elsewhere, so the shared module's identity is unchanged; the record compared goes into `install.json` `removedFirst.verifiedAgainst`. Checked: 0 differences against `release-0.2.1.json`, 28 against `release.json` (same as `host_binding`). |
| `bf9bcfb9` | **Reinstall done:** 0.2.1 verified against its own record, then removed, app config deleted, 0.2.5 extracted from the archive and enabled (`litecore 0.2.5 enabled`, 52 files, binding clean, baseline 236 samples). Then `equivalence` (I3-8) went red: `1/6 reports score and red-case the same; recording paths equal: False; old expressions found in 9748b714: True`. Cause: the six 09-28 counted reports (the rows, scored under the tools at PRE `9748b714` and now) differ because of **deliberate later changes** — page and host pins moved; the asset runner's K2 pre-leave-save instrument clauses; the locks runner's K9′/K10′ readonly and nowhere arms (SPEC-M3-page-honesty §7.4). Recording path: every field PRE records is equal now; only the `zst*` fields (Z0) were added. The proposal I3-8′ (`proposal-2026-10-02-i3-8-prime.md`) was written and, at the owner's choice, sent to review. **The equivalence run overwrote `equivalence.json` and `install.json`**; the 0.2.1 counted window report embeds both originals, so nothing is lost. |
| `75553959` | **The review, verbatim:** `review-2026-10-02-opus-i3-8-prime.md` — 1 BLOCKING (browsers unbound, Firefox already drifted), 6 HEAVY, 5 LIGHT. It recommended option A (fresh dev runs); it judged option B (the historical dev reports as baseline) to collapse into A only because of Firefox 156 ≠ 157. **The owner then chose B with the browser difference as a named limitation instead of a criterion** (section above). |

## State

- `study_LiteCore`: `main` at `75553959` plus this handoff's commit, clean, not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `7420418` (0.2.5), clean, not pushed; the dev instance is
  running 0.2.5.
- `litecoreprobe`: `litecore` 0.2.5 installed from archive `602fe6bb…` on 2026-10-02 (`install.json`,
  `startedAt` 14:18:42Z, `webStartedAt` 14:16:50Z). **A container restart invalidates
  `install.json`'s baseline (I4-1b)** and needs `install --reinstall` — now with no `--was`,
  because `release.json` matches the installed version. **Decided (main session): if the probe's
  web container restarts at any point before the counted window ends, `install --reinstall`, then
  redo everything from step 3 below** (equivalence → dev runs → shakedown → counted): the baseline,
  the equivalence check, the dev runs and both windows must sit in one container lifetime. Write
  this order into the revision row.
- `equivalence.json` holds the **failing** run (at 2026-10-02T14:21:12Z); it must be re-run after the
  tool change below. `install.json` holds the 0.2.5 reinstall.
- The four dev-instance 0.2.5 counted reports (assets `2026-09-29T163517`, versions `…182723`,
  locks `…174033`, host entry `2026-09-29T183110Z`) all ran Firefox 156.0. **Under decision B they
  are the comparison baseline.** The reviewer verified (read-only, in-process) that today's dev
  recording path equals what they recorded, `zst*` included, and that their runner shas equal the
  current runner files.
- The machine rebooted between 09-30 and 10-02 (kernel 7.0.0-31 → 7.0.0-34). ddev: `litecore` and
  `litecoreprobe` were started 2026-10-02; `fgp-nc` and `nc-bridge` are running; the others are
  paused.

## What is next

1. **Implement the replacement for I3-8, then write the spec revision, both before any run.**
   Decided (owner: B; details: main session), **nothing below is implemented yet**. Clause IDs are
   not assigned; the revision row assigns them. I3-8′ is not adopted as proposed; this is the
   review's option B with its fixes.
   - **Withdraw I3-8's PRE-era rows** (CLAUDE.md §4) and say so as a withdrawal plus new clauses,
     **not** "nothing relaxed". Append-only correction of the 2026-10-02 row's "判準條文不動",
     naming what it supersedes. **Decided: keep the transcription check unchanged** (old expressions
     found verbatim at PRE `9748b714`; True in the failing run) — it guards that the recording
     path is still the one the runners use, which the exact-equality clause below does not.
   - **Recording path:** the current dev recording path (`binding_fields(host_binding)`,
     `package_for`, `Instance.describe`), **extended with `release_record`**, must *exactly* equal
     what each selected 09-29 dev report recorded. No exemption for added fields (review item 4: Z0-1 and
     Z0-2 read exactly the `zst*` fields; Z4-1's release record was neither compared nor listed).
     Recursion: dicts recurse; lists, scalars and type changes are leaves compared for equality; a
     missing key is red.
   - **Dev baseline = the 09-29 reports on the release commit (review option B, its item 3):**
     selected by the tool, not listed by hand — counted reports in each runner's `runs/` whose
     base URL is the dev instance's (top-level for versions and locks, `instance.baseUrl` for
     assets and host entry; `runs/` also holds litecoreprobe's own reports), whose bound host
     commit starts with `release.json`'s `commit`, and whose `startedAt` is before the equivalence
     check. ≥ 1 per runner recorded by the current runner sha256; **all** of those reach the
     required verdict (no cherry-picking); reports with other shas are listed, not judged. Each
     re-scored and red-cased at scoring time; each bound to its committed git blob
     (`git diff --quiet HEAD -- <path>`) with its sha256 in `equivalence.json`; `score()`
     re-derives, never trusts a stored boolean. Today this selects exactly the four reports named
     in "State".
   - **Shared-module drift (review item 2, option B):** for each selected dev report, take the last
     `wasm_sdk_probe/` commit at or before its `startedAt`; `git diff --name-only <that>
     <equivalence HEAD> -- wasm_sdk_probe/` must not touch any file in the runners' transitive
     import closure (computed by the tool, e.g. `modulefinder` over the four runners — form 2, not
     a hand list), the Makefile, `editor-shell-v2/tests/` or `web/`. The reviewer measured no such
     drift today (only `check_m3_install_elsewhere.py` changed, which no runner imports). The
     working-tree state during the 09-29 dev runs was not recorded: name it as a limit.
   - **Browsers: no criterion (owner decision B).** Record, in `equivalence.json` and the window
     report, the per-run `version` set of each dev report and of each litecoreprobe report
     (`runs[i].version`; host entry `browsers/<b>/<arm>[i].version`), so RESULT's limitation line
     quotes raw fields.
   - **I3-7 stays as written**: a counted host-entry run on the **dev** instance, started after the
     re-run equivalence check and finished before the window (about 5 min). That is the existing
     protocol from the 0.2.1 window, not a re-measurement for the browser's sake; it will run on
     Firefox 157, and that is fine under B.
   - **LIGHT items:** the assets `criteria` equal between dev and probe report (it decides whether
     Z0–Z2 are scored at all, `check_m3_assets.py:732`); record `ssl.OPENSSL_VERSION` in the tree
     binding or name it as a limit (libssl3 was upgraded 2026-10-02 09:24, after the dev reports);
     pin the **0.2.1** `RESULT.md` "Re-check" commands to tools at `b30b58b7` (current tools
     re-score that window's runner reports red: assets NOT DELIVERED, versions NOT CORRECT, locks
     DO NOT LAND); pin the 0.2.5 result's re-check the same way; any row attribution kept anywhere
     is generated by a tool, not narrated.
   - **Red cases:** the four I3-8 row-pinned cases ("a report scoring differently", "a report whose
     red cases now pass", "equivalence missing a runner", "an equivalence row without its red-case
     exit") must be replaced, or they FAIL as "mutation does not apply" and break the zero
     SKIP/GREEN gate; and `score()` hard-requires rows covering every runner
     (`check_m3_install_elsewhere.py` around `:1154-1157`). New pinned red cases for each new clause;
     the review's list (item 7): recording — a PRE field changed, a PRE field missing, a nested
     `package/files` field changed, plus a unit check that a changed only-now field does not pass;
     dev baseline — a runner without a dev report, a dev report with another runner sha, one that
     re-scores red, one whose red cases stay green, one from `litecoreprobe`, one started after the
     check, one changed since it was committed; module drift — a closure file changed after a dev
     report; criteria — differing.
2. **Commit** (`wasm_sdk_probe/` must be clean: counted runners and the window refuse an
   uncommitted tree).
3. **Re-run `equivalence`** (the module sha and tree changed).
4. **I3-7: the dev host-entry counted run** (about 5 min), after the re-run equivalence check:
   from `wasm_sdk_probe/tools`, `python3 check_m3_host_entry.py --label counted`, then re-score and
   `--red-cases` it by hand. **No fresh dev runs of assets, versions or locks** (owner decision B).
   Note `firefox --version` in the RESULT; do not stop on a version change.
5. **Shakedown window**, then `--strict --red-cases FILE` with **zero SKIP/GREEN** before counting.
6. **Counted window** (about 1 h), passing `--dev-host-entry <the step-4 report>`. Then `RESULT.md`
   for 0.2.5, with the browser limitation (owner decision B, wording above) written first, not
   buried; and a handoff.
7. Unchanged from the 09-30 handoff: A (distribution channel, owner's outward action), F (finding
   105's Firefox-only repro), the registered list (K0-5 at the a11y cutover, Chrome's gzip path,
   K2-2's `gzBytes` anchor, brotli, 106 / 108 / 094).

## Things this round taught

- **A guard that refuses to remove an install can be right and still block the first upgrade.** It
  compared the existing 0.2.1 install against the new release's record and found 28 differences.
  Upgrade paths need the previous record named (`--was`), and the record compared should be written
  down.
- **A criterion written to show one refactor neutral becomes unsatisfiable once the scorers change
  on purpose.** I3-8 was met in the 0.2.1 window; keeping it alive would mean re-pinning old
  reports, which is machinery. The replacement keeps the historical dev reports as the baseline but binds them by tool: selection by
  raw fields, committed blobs, runner shas, and no shared-module drift since they ran.
- **Environment drift is invisible to tree and module bindings.** A snap auto-refresh moved Firefox
  between the dev runs and the window while every binding stayed green. Whether to make it a
  criterion is a cost decision the owner made (B: record it as a named limitation, no re-runs); the
  per-run `version` fields are what make the limitation statable from raw data.
- **The drafter's narration of why rows differed was wrong once.** The proposal attributed the
  locks rows to §7.11 / finding 108; they come from §7.4 (K9′ readonly, K10′ nowhere), and readonly
  was omitted. Attribution should come from a tool (the scorer's per-arm problems plus `git log -S`
  on the changed line), not from the author.

## Standing rules to carry

- Never run two M3 runners (or an M3 probe) at once — each clears the whole `oc_files_lock` table.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` version bump
  and `ddev occ upgrade`.
- After changing `dist/`, re-run `package_m3_engine.py` (about 50 s: zstd level 19).
- `build_m3_release.py` rewrites `release.json` unless given `--record <elsewhere>`.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/`, and
  findings' prose are zh-TW. Specs and gate documents are append-only.
- Don't start or restart other ddev projects during a counted run or an install window.
- **New:** `install --reinstall --was <previous record>` for an upgrade; without `--was` it compares
  against `release.json`.
- **New:** the Firefox snap may auto-refresh at any time. Owner decision B (2026-10-02): no
  re-measurement because of a browser upgrade; existing verdicts stand as measured; note the
  version in each RESULT.
