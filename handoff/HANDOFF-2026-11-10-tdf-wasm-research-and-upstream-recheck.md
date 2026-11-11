# Handoff: TDF WASM direction research; findings 001/002/003/040/114 re-checked upstream; 001 withdrawn

Checkpoint **2026-11-10 ~22:40**. One handoff for this session. This session was research and upstream-finding triage, not
product work. **The product line is unchanged** since `HANDOFF-2026-11-08-releases-0.2.60-0.2.61-zoom-anchor.md`: 0.2.61 is
installed and the owner's hand test is still pending. Read that handoff for the product state.

## Where things stand

1. **Documents written this session** (repo root, all uncommitted, zh-TW):
   - `RESEARCH-2026-11-10-tdf-wasm-direction-mailing-lists.md`: what the dev list, the TDF proposal and the core tree say about
     TDF's WASM direction. Includes a source-level WASM progress table per release cycle (25.2 to 26.8).
   - `RESEARCH-2026-11-10-industry-direction-client-side-office.md`: evidence for "client-side office" as an industry
     direction (TDF proposal, heise comparison, RGESN, NGI grants, vendors). Lists the arguments not to use.
   - `RESEARCH-2026-11-10-upstream-reportable-findings-wasm-qt.md`: inventory of WASM/Qt findings worth sending upstream, plus
     two appended re-check sections and a revision log.
   - Not written by this session (pre-existing, untracked): `RESEARCH-2026-11-10-tdf130857-qt-weld-commits.md`,
     `codex-claude-code-delegation.md`.
2. **Findings changes** (uncommitted). Five WASM builds, all tested with the unchanged `wasm-lite/tools/pw/probe.js` and the
   same Chromium 151 as on 2026-07-31:
   - **001 WITHDRAWN.** None of the five clean rebuilds crashes, including an exact replica of the July build at its own commit
     `671c848b` (same flags, same two fs-image patches, zh-TW, same toolchain; `soffice.data` byte-size identical).
     - The July crash tree had been configured with `--enable-lto` first and reconfigured without it. Stale LTO bitcode
       stayed in `liblocaledata_{others,euro,en,es}.a`: the log has 0 locale-data compiles and 10,262 `wasm-ld` signature-mismatch
       warnings. Every other build, July t2/t3 included, has 285 compiles and 0 warnings.
     - So the July t3 "only symbols differ" control was confounded.
     - The mixed state was **not** re-created on purpose; the causal link is inference.
     - Header and an appended 〈撤銷〉 section are in the finding. `drafts/001-bugzilla.txt` is voided, and the index row in
       `findings/README.md` is updated.
   - **002 reproduced at runtime** on master `2a2335cf` (stock build): `qt_vcldemo.html` never requests `soffice.data`, and the
     console shows `Bootstrap exception Cannot open uno ini`. It is now confirmed both statically and at runtime; only a
     Bugzilla draft is missing.
   - **003 race** hit 2 of 2 fresh build dirs on 26.8.2.2 at the first `make` (`dragonbox.version`), 0 of 2 on master. The rule
     at `UnpackedTarball.mk:170` is unchanged on master.
   - **040 and 114**: static re-check on 26.8.2.2 `9dea406a`, 26.8.3.1 `861effc5` and master `2a2335cf`; the cause code is
     unchanged. 114: LO now bundles fontconfig 2.18.3, whose `35-lang-normalize.conf` keeps all 258 old rules (+57 new). The
     census re-run with 2.18.3's rule file (2.18.2 library) still rewrites 66 tags, including `zh-tw -> tw`.
3. **Evidence created** (English):
   - `findings/evidence/001/`: `master-2a2335cf/`, `26.8.2.2-9dea406a/`, `671c848b-rebuild/`, `rebuild-2026-11-10/` (logs,
     `build.sh`, `run_probe.sh`, configure inputs, `config_host.mk` per build), `july-crash-build-stale-lto.txt`,
     `upstream-recheck-2026-11-10.txt`.
   - `findings/evidence/002/`: `master-2a2335cf/`, `upstream-recheck-2026-11-10.txt`.
   - `findings/evidence/003/make-error-26.8.2.2.txt`
   - `findings/evidence/040/upstream-recheck-2026-11-10.txt`
   - `findings/evidence/114/recheck-2026-11-10/` (census control and variant, 2.18.2-to-2.18.3 rule diff).

## Environment state

- **`~/LibreOffice/lo-submit`**:
  - Remote-tracking refs were fetched: `origin/master` is now `2a2335cf` (2026-11-10), and `libreoffice-26-8-2` and
    `libreoffice-26-8-3` were added, plus tags `libreoffice-26.8.2.2` and `libreoffice-26.8.3.1`. Its worktree and branch
    `table-style-sort` are untouched.
  - It is itself a worktree of `study_LiteCore/libreoffice-25-2/.git`, with `extensions.worktreeConfig=true`. It uses a
    per-worktree sparse checkout, and **new worktrees inherit it**. Run `git sparse-checkout disable` in the new worktree only.
    Avoid `git submodule deinit` there: per git's documentation it removes the `submodule.<name>` section from
    `.git/config`, which is the shared config (not tested this session; worktree removal with `--force` worked without it).
- **`wasm-lite/upstream-master/`** (worktrees and builds) was created, then fully deleted at the owner's request (option A).
  The three worktrees were removed with `git worktree remove --force`. The shared `.git/config` hash is unchanged
  (`8a859983…`). The kept core trees and the shared ccache were not touched. Disk is back to 101 GB free.
- **Gotchas met**:
  - `emsdk_env.sh` unsets short variable names such as `DIR`. Use distinct names and set them after sourcing.
  - `setsid`'s `$!` is a dead parent; find the PID with `ps`.
  - The rm safety check rejects variable-expanded `rm` targets; use literal absolute paths.

## Memories added

- `reading-tdf-and-freedesktop-sites`
- `reconfigure-keeps-stale-objects`

## Next session

1. Write the finding 002 Bugzilla draft (`findings/drafts/002-bugzilla.txt`), the easiest upstream report. Submissions stay
   on hold.
2. Commit this session's changes when the owner asks. Nothing is committed. Files touched (`git status --short`, excluding the
   pre-existing `*/profile/` dirs):
   - modified: `findings/001-…md`, `002-…md`, `003-…md`, `040-…md`, `114-wasm-…md`, `findings/README.md`,
     `findings/drafts/001-bugzilla.txt`;
   - new: the three RESEARCH files above, and the evidence paths listed above.
3. A 040 runtime re-check needs our probe linked against a newer core (owner `make`).
4. TDF Discourse topic 13729 (the proposal's discussion) is unread. Anubis denies headless Chrome; it needs the owner's browser
   or extension-mode Playwright.
5. Upstream submissions remain on hold since 2026-08-15; re-check duplicates before any send.

## Section 34.4

Checks changed because of review: 0.
