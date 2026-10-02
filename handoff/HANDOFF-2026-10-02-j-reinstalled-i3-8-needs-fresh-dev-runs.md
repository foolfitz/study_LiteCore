# Handoff, 2026-10-02 — J: 0.2.5 reinstalled on litecoreprobe, I3-8 cannot pass as written, replacement needs fresh dev runs

Entry points: this file, `findings/evidence/m3-install/review-2026-10-02-opus-i3-8-prime.md` (the
review, verbatim; DETAILS has a verified evidence line per item), `findings/evidence/m3-install/proposal-2026-10-02-i3-8-prime.md`
(the proposal; **not adopted as written**), `findings/evidence/m3-install/equivalence.json` (the
failing run), `findings/evidence/m3-install/install.json` (the 0.2.5 reinstall),
`specs/SPEC-M3-install-elsewhere.md` (§3.3, I3-7, I3-8, the 2026-10-02 revision row),
`wasm_sdk_probe/tools/check_m3_install_elsewhere.py`.

Picks up from `handoff/HANDOFF-2026-09-30-zstd-delivered.md`. Its "What is next" item 1 was J:
install the 0.2.5 release archive on `litecoreprobe` and redo install-elsewhere. The owner said on
2026-10-02 that no other ddev project was in use, and asked for J.

## Where J stands

**J is half done, and no 0.2.5 install-elsewhere window (shakedown or counted) has run.**

- Done: `litecoreprobe` has `litecore` 0.2.5 from archive `602fe6bb…`, enabled, binding clean.
- Blocked: the equivalence check (I3-8) is red, and I3-8 as written cannot be made green without
  re-pinning old reports to old bindings (machinery to keep an old claim alive; CLAUDE.md
  "驗收判準的形式" §4).
- Decided, **not implemented**: the replacement (below, "What is next" item 1). The first draft of
  it, I3-8′, went to an opus adversarial review before adoption and came back with a BLOCKING
  finding, so it is not adopted as proposed.
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
| `75553959` | **The review, verbatim:** `review-2026-10-02-opus-i3-8-prime.md` — 1 BLOCKING (browsers unbound, Firefox already drifted), 6 HEAVY, 5 LIGHT. Its recommended fix (option A) is the direction below. Its option B (keep the historical dev reports as the baseline) fails today on Firefox 156 ≠ 157, so it collapses into A. |

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
  locks `…174033`, host entry `2026-09-29T183110Z`) all ran Firefox 156.0. They stay as history;
  they will not be the comparison baseline.
- The machine rebooted between 09-30 and 10-02 (kernel 7.0.0-31 → 7.0.0-34). ddev: `litecore` and
  `litecoreprobe` were started 2026-10-02; `fgp-nc` and `nc-bridge` are running; the others are
  paused.

## What is next

1. **Implement the replacement for I3-8, then write the spec revision, both before any run.**
   Decided by the main session, **nothing below is implemented yet**. Clause IDs are not assigned;
   the revision row assigns them. Adopt the review's option A; I3-8′ is not adopted as proposed.
   - **Withdraw I3-8's PRE-era rows** (CLAUDE.md §4) and say so as a withdrawal plus new clauses,
     **not** "nothing relaxed". Append-only correction of the 2026-10-02 row's "判準條文不動",
     naming what it supersedes. **Decided: keep the transcription check unchanged** (old expressions
     found verbatim at PRE `9748b714`; True in the failing run) — it guards that the recording
     path is still the one the runners use, which the exact-equality clause below does not.
   - **Recording path:** the current dev recording path (`binding_fields(host_binding)`,
     `package_for`, `Instance.describe`), **extended with `release_record`**, must *exactly* equal
     what each fresh dev report recorded. No exemption for added fields (review item 4: Z0-1 and
     Z0-2 read exactly the `zst*` fields; Z4-1's release record was neither compared nor listed).
     Recursion: dicts recurse; lists, scalars and type changes are leaves compared for equality; a
     missing key is red.
   - **I3-7 extended to all four runners:** a fresh dev-instance counted run of assets, versions,
     locks and host entry, each started **after the re-run equivalence check** and finished before
     the window; each passed explicitly (like `--dev-host-entry`), bound by path and sha256 (and
     re-derived at scoring time, not stored as a boolean); filtered to the dev base URL; each
     reaches its required verdict; red cases re-run at scoring time; runner sha256 equal to the
     equivalence check's.
   - **New clause, browsers:** for each runner, the set of per-run `version` values in the
     `litecoreprobe` report equals the set in its dev report (`runs[i].version` in assets, versions,
     locks; `browsers/<b>/<arm>[i].version` in host entry). Red today by construction, which is
     what forces fresh dev runs.
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
     dev runs — a runner without a dev report, a dev report with another runner sha, one that
     re-scores red, one whose red cases stay green, one from `litecoreprobe`, one changed since the
     check; browsers — a differing version set; criteria — differing.
2. **Commit** (`wasm_sdk_probe/` must be clean: counted runners and the window refuse an
   uncommitted tree).
3. **Re-run `equivalence`** (the module sha and tree changed).
4. **Fresh dev counted runs, assets, versions, locks, host entry**, one at a time, as the Z3
   re-count did (09-29: assets 4.5 min, locks 47 min, versions 4 min, host entry 5 min, so about
   1 h). From `wasm_sdk_probe/tools`, as a background shell chain with stdout to the scratchpad:
   `for r in assets versions locks host_entry; do python3 check_m3_$r.py --label counted > $S/dev-$r.log 2>&1; done`
   (each refuses an uncommitted host tree and runs `make test-e2-c-static` itself). Then re-score
   and `--red-cases` each report by hand, as for Z3. **Check `firefox --version` before the chain**;
   the version-equality clause is what verifies it either way.
   *Owner action, optional, needs sudo (the owner runs it):* `sudo snap refresh --hold=72h firefox`
   keeps Firefox fixed through J.
5. **Shakedown window**, then `--strict --red-cases FILE` with **zero SKIP/GREEN** before counting.
6. **Counted window** (about 1 h). Then `RESULT.md` for 0.2.5, with the Firefox 157 qualifier
   written first, not buried; and a handoff.
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
  reports, which is machinery. The replacement binds the comparison baseline *in time* (fresh dev
  runs inside the bound span) instead of trusting historical reports.
- **Environment drift is invisible to tree and module bindings.** A snap auto-refresh moved Firefox
  between the dev runs and the window while every binding stayed green. Browsers need binding per
  run, and the check should be on the raw per-run `version` field, not on a statement about the
  machine.
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
- **New:** the Firefox snap may auto-refresh at any time — check `firefox --version` before any
  counted run.
