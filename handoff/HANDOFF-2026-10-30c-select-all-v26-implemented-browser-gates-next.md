# Handoff: select-all v26 + finding 174 implemented, in dist (unfrozen); browser gates S1/S2 next

Checkpoint **2026-10-30 ~03:30 +0800**. Supersedes `HANDOFF-2026-10-30b-select-all-measured-on-v25.md` as the
entry point (that file and `HANDOFF-2026-10-30-finding-173-fixed-host-0241-installed.md` still hold for what they say
that is not superseded). Study HEAD **284a85c18** plus the commit that adds this file. Tree clean except the
unrelated untracked `codex-claude-code-delegation.md` (preserve it). **Nothing is running.** The owner is using
DDEV from another session; nothing here touches DDEV until the 0.2.42 install (owner slot needed).

## Owner decisions this session (2026-10-30)

- Finding 173 hand test on host 0.2.41: bullet applied, no restart notice -> **173 confirmed fixed** on the host
  route. The toast was a red box with `MUTATION_OUTCOME_UNKNOWN` + English -> **finding 174** (`2c05017b0`).
- Select-all: **B** -- ship without a relink as manifest successor `e2-editor-v26` (overrides 10-29's "wait for
  v26 engine batch"; the next engine batch is renamed **v27**).
- Finding 174: **B** -- all three `review` toasts (059, 083/173, 046) become label + Chinese sentence, not error
  style; code and English to `console.warn`. Bundled with select-all into **generation 80 / host 0.2.42** (A).

## State

- Spec **`specs/SPEC-M3-select-all-v26.md`**, pinned `9f084bf06` (append-only). Draft got one adversarial review
  (opus); 10 of 12 items adopted after reading source (spec section 8). Section 7 is the order; steps 1-4 done.
- **Profile `e2-editor-v26`** assembled (Makefile rule `dist/profiles/e2-editor-v26/sdk-manifest.json`: python + cp,
  no link), archived `wasm_sdk_probe/build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae` (read-only).
  wasm/loader = v25 archive; worker `95d6e7ae…` = v25 worker + one comment line + `featureExtendPermitted` naming
  v26; manifest `835752a3…` = v25 + four values (`profile`, `sdkVersion`, `workerSha256`, `select-all` granted).
- **Shell**: client (`EDITOR_SELECT_ALL_ACTIONS`, `EDITOR_ACCEPTED_ACTIONS`, select-all = move class), session
  (allowlist reads the union; select-all in `BOUNDARY_CAPABLE_MOVES` = non-mutation), page (worker URL v26;
  `selectAllKey`/`selectAllResult`/`takeSelectAllKey` before the accel bail-out; 174 in `run()`'s review branch).
- **`dist/` now serves the generation-80 CANDIDATE** (page `e04e3fde…`, client `50f5a2ac…`, session `d037eaa4…`;
  `make e2-c-assets` = three cp, cmp equal). **Generation 80 is NOT frozen yet** (spec 5.8: only after S1 and S2).
  The v79-pinned tools are NE on the live tree by construction from here on (use V0' restores, spec 5.7).
- Evidence `findings/evidence/select-all-v26/`: `p1/` (P1_HOLDS dist+archive, 9 red cases each on its clause, v25
  control red; P1 fixed once by its own first run), `u1/`, `u2/`, `u3/` (red before / green after), `assets/`,
  `suite-after-page.txt` (shell suite 548/548). README lists two PRE-EXISTING python reds (verified at 9f084bf06).

## Next steps (spec section 7, from step 5)

1. **S2** (`tools/check_v80_blank_bullet.py`, derived from `check_v79_blank_bullet.py`, which is NOT edited):
   B1's procedure/products/counts with generation 79 as `before` and 80 as `after`; after adds: `#toast` has no
   `bad` class, no `MUTATION_OUTCOME_UNKNOWN`, no `selection read`; before is red for 174 (bad + code). `--self-test`.
2. **S1** (`tools/check_v26_select_all.py`, derived from `findings/evidence/select-all-v25/measure_select_all.py`,
   NOT edited): the page sends select-all on a REAL Ctrl+A; harness only reads. Products after/before/unoffered/
   fake/v25-worker; seven documents incl. a multi-page one; arms per spec 5.4 (11 arms); four counterexamples red
   for the right reason; `--self-test` with one mutation per PASS-clause id (tool-closed). Chrome + Firefox
   (`copy` Chrome only). Run counterexamples first.
3. Freeze generation 80 (three files vs 79; excluded list = v79's eight + `sdk/v26-select-all-worker.js`),
   Makefile bundle line -> v80 (red/green/red).
4. F3-80, F4-80 (derived tools; replace every pin listed in spec 5.6 and run the stale-value scan first), V0',
   E1-C intact.
5. Host 0.2.42 package (changed 3, added 4, removed 4), then an **owner slot** (they are on DDEV elsewhere -- ask),
   install, Files workflow, capture-after, owner hand test (spec 5.9 a-c).

## Cautions

All of 10-30's and 10-30b's, plus:
- `dist/` serves an unfrozen candidate. If anything in the shell must change before the freeze, change source,
  rerun `make e2-c-assets`, and redo the suite; after the freeze any change is generation 81.
- F3 check `a-format-that-worked-is-not-reported-as-failed` is DISARMED by 174 (it greps the toast for
  `LOK_COMMAND_FAILED`, which is no longer shown); its PASS on F3-80 must not be cited for finding 059 (spec 5.5).
- The page-slicing tests assemble functions from the page source; when the keydown handler gains a call, every
  test that evaluates the whole handler needs the callee in scope (`page-move-during-delete.test.mjs` uses
  `optional(...)` so old pages still assemble for V0').
- `featureExtendPermitted` binds the profile name; S1's `extend` arm (Shift+Down, a LINE move -- Shift+Right is a
  V1 move that bypasses it) with the `v25-worker` product as its red case is what guards that.

## Section 34.4 this round

Fixed-by-execution **1** (P1's population parser, before use). Fixed-by-review **10** (the spec draft, before
pinning; section 8 of the spec). Test-harness slips fixed while writing (not product): U1 default-parameter
sentinel; move-during-delete scope; a comment matched by `indexOf`.

## Language

Replies to the owner: Taiwan Traditional Chinese (A/B/C for options). Evidence, upstream text and `handoff/**`:
English. `devlog/`, `research/`, `specs/`: zh-TW (specs append-only once pinned).
