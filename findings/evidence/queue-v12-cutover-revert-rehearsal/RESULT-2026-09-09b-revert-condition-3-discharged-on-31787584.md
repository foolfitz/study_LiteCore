# Revert condition 3, re-taken on `31787584…` (candidate `e2-editor-v13`): E-3's named instance is MET

**2026-09-09, second pass.** This completes what
`RESULT-2026-09-09-revert-condition-3-on-31787584-PARTIAL.md` (beside this file,
left unedited) recorded as owed. That pass met E-3's **universal clause** — every
plain shipped-page run reconciles — and could not take E-3's **named instance**,
the re-run of the revert rehearsal, because its commissioning constraints forbade
all four cutover steps. The owner authorised the drill explicitly (2026-09-09,
disposition **A** of that document's two options). It was taken here.

`RESULT-2026-09-07-revert-condition-3-discharged-on-9b29e39b.md` is the
immediately preceding *complete* take; everything bound to `9b29e39b…` died when
finding 093 option B was linked and the page moved to `31787584…`.

Script: `rehearse_revert_v50.sh` — `rehearse_revert_v49.sh` with only the identity
constants changed (`BASE_SHA` → the tree's current shipped sha `1ec7baf9…`,
`CAND_SHA` → `31787584…`, `NEWGEN` → v50, profile → `e2-editor-v13`,
`--frozen-date` → 2026-09-09, the repoint → `v49 v50`), `trap` intact.
Transcript: `rehearsal-2026-09-09.log`.

## Identity of the tree this was measured on

| | |
|---|---|
| shipping page (`web/` and `dist/`) before and after | `1ec7baf9fb53c808cf127476346d69d56cf93a802f6c72680fa84416f7599ecc` |
| shipped generation before and after | `e2/editor-shell-v2-bundle-v49.json`, digest `4f8494b6…` |
| candidate page written during the cutover | `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a` |
| generation frozen during the cutover | `e2/editor-shell-v2-bundle-v50.json`, digest `ea69984c…` |
| `tools/build_e2_c_shell_bundle.py` before and after | `0e07fda14e6a8d281d075ac7f7c1ed060a41fcded8bc9b469bd8bcf0a7e9e512` |

## The four steps, performed for real

1. `build_cutover_page.py --profile e2-editor-v13 --write --expect-sha256 31787584…`
   rewrote `web/e2-editor-app.js`; the pin moved `4a2710bba1ef07d9 -> 0fe25650bec1bac5`.
2. `cp web/e2-editor-app.js dist/e2-editor-app.js` — the served copy.
3. `build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v50.json
   --frozen-date 2026-09-09 --write` wrote the generation, `written: true`,
   `problems: []` (`freeze-v50.json`).
4. `MANIFEST` repointed v49 → v50 in `tools/build_e2_c_shell_bundle.py`.

The tree was genuinely in the cutover state between steps 4 and the revert: `git
status` carried `M tools/build_e2_c_shell_bundle.py`, `M web/e2-editor-app.js`,
`?? e2/editor-shell-v2-bundle-v50.json`. `dist/e2-editor-app.js` was **not** in
that listing — it is gitignored, which is the whole reason a rehearsal is needed
rather than a `git checkout`.

## E-3's criterion, term by term, on the post-revert run

`rerun50-after-revert.json` / `rerun50-reconcile-after-revert.json`.

| E-3 requires, on the **post-revert** run | measured |
|---|---|
| `check_usable_editor` `ok` | **true** |
| `reconciledFor.kind` | **`shipped-page`** |
| `servedShell.bundle` | **`e2/editor-shell-v2-bundle-v49.json`** |
| `declaredSha256 == servedSha256` | **true**, `4f8494b6b25736c6314d9cfb8772670009057313d5b0e6753c12b75771e3b9cd` |
| `servedShell.differingPaths` | **`[]`** (and `missing: []`, `differsOnlyInTheEntrypoint: false`) |
| `problems` | **`[]`** |

`restore()` runs `git checkout -- web/e2-editor-app.js tools/build_e2_c_shell_bundle.py`,
so the post-revert run could only declare **v49** because that freeze is
committed (`18eefcce`). The run itself is 41 checks, `complete: true`, **39 PASS
/ 2 NOT_ESTABLISHED, no FAIL**, the NE set exactly the fixed pair, and
`candidateCutover: null`. `startedAt` 2026-09-09T15:38:44+08:00, `completedAt`
2026-09-09T15:44:49+08:00.

## The cutover half, and E-4's positive control on a genuine cutover

`rerun50-after-cutover.json` (no `--candidate-profile`; the tree really was
repointed): bundle **v50**, `declaredSha256 == servedSha256 ==
ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`,
`differingPaths: []`, `differsOnlyInTheEntrypoint: false` — no difference at all,
which is what distinguishes a cutover from a candidate mirror.
`check_usable_editor` `ok: true`, `reconciledFor.kind: "shipped-page"`.

That digest `ea69984c…` is **exactly the value E-4 pins as `one-served-shell`**
and exactly what all six banked candidate runs served. Until now that value had
only ever appeared as the digest a `--candidate-profile e2-editor-v13` run
*serves*; here it appears as the `bundleSha256` a real cutover generation
*declares*. Obligation R6 — the cutover record quotes the cutover generation's
`bundleSha256` and E-4's pinned value side by side, equal — is satisfiable and
satisfied on this identity, and no longer rests on the recomputation argument in
`check_soak_bank.py`'s comment.

## The post-cutover run has no FAIL — a change from 2026-09-07, recorded

The 2026-09-07 take's post-cutover run was 37 PASS / 2 NE / **1 FAIL**
(`the-document-region-says-why-it-is-empty`), and that FAIL was its fourth
reproduction. On this identity the post-cutover run is **39 PASS / 2 NE / 0
FAIL**. Both the R-1 disposition (that check rewritten to verify the claim) and
finding 093 option B's link landed between the two takes, so this is not one
variable; it is recorded as an observation, not attributed.

## The tree afterwards — byte-identical on all thirteen bound paths

The bound list is derived from the live manifest's own `included` array, not
hand-typed. `diff` empty on both listings:

```
bound-sha-before-31787584-rehearsal.txt      bound-sha-after-31787584-rehearsal.txt
bound-sha-before-dist-31787584-rehearsal.txt bound-sha-after-dist-31787584-rehearsal.txt
```

Thirteen paths in the source tree, thirteen in the `dist/` mirror, twenty-six
comparisons, **zero differing**. `MANIFEST` back to v49, the bundle tool back to
its committed bytes, `git status --short` clean apart from this pass's untracked
evidence.

## The soak bank is untouched — and what that does and does not prove

`check_soak_bank.py` before and after the rehearsal: `cleanRuns: 6,
totalRuns: 6, every-run-clean: true, one-page-sha: true, ok: false`
(`count-reached` and `day-spread` false, as before — the count is 6 of 12 on one
UTC day). The two verdict JSONs are **byte-identical**
(`soak-bank-before-rehearsal.json`, `soak-bank-after-rehearsal.json`).

**Stated honestly, because the acceptance for this pass framed it as the strong
test:** this verdict is *report-local*. `DEFAULT_SHA`
(`check_soak_bank.py:111`), `DEFAULT_SERVED_SHELL` (`:303`), `EXPECTED_PASS` and
`EXPECTED_NE` are module constants, the six runs are banked JSON, and
`reconcile()` shells out to `check_usable_editor.py --report`, which the
2026-09-06 E-3 red-case note already records as report-local. So a byte moved in
`web/` or `dist/` and not put back would **not** turn those six red. The
identical verdict is a real guard against one thing — a stray write into
`findings/evidence/queue-v12-cutover-soak/` — and it is not the byte-for-byte
test. The byte-for-byte test is the twenty-six-path comparison above, and it is
the one that carries the claim.

## Supporting requirements — all met, after the revert

| requirement | measured |
|---|---|
| `make test-e2-c-static` | **exit 0** (`test-e2-c-static-2026-09-09-rehearsal.log`); also exit 0 immediately before the rehearsal |
| `make test-e2-c-reachability` | **exit 0** (`test-e2-c-reachability-2026-09-09-rehearsal.log`) |
| `python3 tools/build_e2_c_shell_bundle.py` (default manifest) | **exit 0**, `bundleSha256 4f8494b6…` (= v49's declared value), `problems: []` |
| `python3 -m unittest tests.test_e2_c_shell_bundle` | **12 of 12 OK** |
| anti-rewrite proof against the **past** generation | `--manifest e2/editor-shell-v2-bundle-v48.json` **still refuses**: *"refusing to rewrite … it exists with digest ecfb6866… and the tree now hashes 4f8494b6… A changed shell needs a NEW generation"*, exit 1 |

## Generation v50: frozen, then removed by the procedure's own `restore()`

`restore()` ends with `rm -f "$NEWGEN"`, as it has in every take
(v45, v49, and now v50). So **v50 does not remain in the tree**, and
`e2/editor-shell-v2-bundle-v50.json` is absent; the generation number stays
unclaimed and the next real cutover may take it.

This is worth naming rather than passing over, because a frozen generation is
*additive* — a new file, not a mutation — and could legitimately have been left.
Two things pull in opposite directions and the procedure resolves them one way:
leaving v50 behind would make the post-revert tree differ from its pre-rehearsal
state, and "the revert restores every byte" is the property being measured. The
removal is therefore part of the measurement, not tidying. **Nothing is lost:**
`freeze-v50.json` banked beside this file holds the full report the write
produced, `included` list and all, so v50 is reconstructible byte-for-byte
without re-running anything.

## Attempt 1 failed at step 3, the guard caught it, and the failure is banked

`rehearsal-2026-09-09-attempt1-REPOINT-GUARD-FIRED.log`. The first attempt
performed steps 1 and 2 for real and froze v50, then died at step 4 with

```
AssertionError: expected exactly 1 MANIFEST line, found 0
STEP 3 REPOINT FAILED
```

Cause: **drafting error in deriving the script**, not a tree or product defect.
The `sed` expression that was to rewrite the repoint arguments read
`s|repoint_manifest\.py v48 v49|…|`, and the line in the file is
`python3 "$SP/repoint_manifest.py" v48 v49` — the closing quote sits between
`.py` and the space, so the pattern never matched and the script asked to repoint
**v48 → v49** on a tree whose `MANIFEST` says v49. The diff of the derived script
against `rehearse_revert_v49.sh` was reviewed before running and this line simply
was not among the changed hunks; that was there to be seen and was not seen.

The assertion in `repoint_manifest.py` is the one added after 2026-08-17, whose
comment reads *"a string replace that did not match once left MANIFEST pointing
at the previous generation while `--write` regenerated it in place. Silence is
what made that expensive."* This is that guard firing on a live attempt, against
a real wrong-generation repoint, and it is the reason the failure cost one
transcript instead of a rewritten generation. The `trap` then restored
everything: `web/`, `dist/`, the tool and the removal of v50 all came back
before the second attempt started, and attempt 2's `=== BASELINE ===` block
shows the tree already at `1ec7baf9…` / v49.

Banked in full rather than discarded, per the 2026-08-27 practice of keeping the
version that went red.

## Chrome census

One Google Chrome browser root before (pid 211853, crashpad 211863 — the owner's)
and one after; 39 processes before, 35 after, all children of that one root. No
headless Chrome and no `serve_candidate_page.py` left behind. Nothing was killed.

## Count semantics

**Nothing here counts toward the soak and nothing here restarts it.** Both runs
are plain shipped-page runs written to the scratchpad and banked here, not in
`findings/evidence/queue-v12-cutover-soak/`; `run_e2_c_product_path.py` was not
modified and the clean predicate stands at 39 PASS / 2 NE. The count remains
**6 of 12**, all six on UTC day 2026-09-09.
