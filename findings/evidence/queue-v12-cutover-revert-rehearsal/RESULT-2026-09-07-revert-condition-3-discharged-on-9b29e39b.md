# Revert condition 3, re-taken on `9b29e39b…` (shell generation v48): the post-revert run reconciles again

Task T2, item 5, of `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`.
Ruling **E-3** of the 2026-09-06 adjudication
(`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, "E-3 — Acceptance
criterion for E-1") is the criterion; `RESULT-2026-09-06b-revert-condition-3-discharged.md`
(beside this file, on `20f09cc9…` / v44) is the immediately preceding take.
That page moved twice more since (finding 088's second fix, then the T1d
mistake and its v48 correction), so the rehearsal is re-earned here on the
final page, `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`.

Script: `rehearse_revert_v49.sh` — `rehearse_revert_v45.sh` with only the
identity constants changed (`BASE_SHA` → the tree's current shipped sha
`df5f3b6c…`, `CAND_SHA` → `9b29e39b…`, `NEWGEN` → v49, since v48 is now the
live shipped generation), `trap` intact. Transcript: `rehearsal-2026-09-07.log`.

## The criterion, term by term

| E-3 requires, on the **post-revert** run | measured |
|---|---|
| `check_usable_editor` `ok` | **true** |
| `reconciledFor.kind` | **`shipped-page`** |
| `servedShell.bundle` | **`e2/editor-shell-v2-bundle-v48.json`** |
| `declaredSha256 == servedSha256` | **true**, `ecfb6866117673c21a7c21995f7ea76fe60beb9f94a73c222053a18cc573a6ef` |
| `servedShell.differingPaths` | **`[]`** |

`restore()` runs `git checkout -- web/e2-editor-app.js tools/build_e2_c_shell_bundle.py`,
so the post-revert run could only declare v48 because that freeze is
**committed** (`2d319677`). The post-revert raw report is also **38 PASS / 2
NE, `ok: true`** — clean, with no FAIL, unlike every other run of this page in
this task (see below).

## The cutover half, and E-4's positive control

The post-cutover run (no `--candidate-profile`, tree genuinely repointed to
`e2-editor-v12` by step 1): bundle **v49**
(`bundleSha256 cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4`
— identical to v47's frozen value, expected: v47, v48 and v49 differ from each
other only in the entrypoint file, and v49's entrypoint is the same
`9b29e39b…` bytes v47 was frozen on), `declaredSha256 == servedSha256`,
`differingPaths: []`, `differsOnlyInTheEntrypoint: false` (there is no
difference at all here — a real cutover, not a candidate-profile override).
`check_usable_editor` reconciles `ok: true`, `reconciledFor.kind: "shipped-page"`
— the run genuinely ships `e2-editor-v12` for this reconciliation, which is
what "cutover" means.

That servedSha256 (`cf7f9233…`) is the value E-4's positive control names for
the *candidate* side; here it appears as the *declared* value of a real
cutover, which is the same identity by a different route — the freeze
mechanism does not care whether the bytes arrived by `--write` or by
`--candidate-profile`.

## The post-cutover run is 37 PASS / 2 NE / 1 FAIL — the same defect items 1-3 already recorded, now on a genuine shipped-page run

```
the-document-region-says-why-it-is-empty   FAIL
```

identical id and shape to the FAIL recorded in
`findings/evidence/queue-v12-cutover-soak/RUNS.md` ("Re-taken on `9b29e39b…` /
v48") and `../gate-4a-on-9b29e39b/RESULT-4a.md`. Those were `--candidate-profile`
runs; **this one is not** — step 1 of the rehearsal genuinely repointed
`web/e2-editor-app.js` and `dist/e2-editor-app.js` to `e2-editor-v12`, and the
run that followed carries no `candidateCutover` stamp at all. This is the
fourth reproduction of the same FAIL and the first on bytes that are not
merely a measurement mirror — it is what a real cutover to `e2-editor-v12`
would ship today. Not fixed here, per this task's role; recorded because it
bears directly on whether this gate should close.

## `make test-e2-c-static` FAILs on the current tree, same root cause as condition 4a's term 6

Run after the rehearsal, on the tree fully restored to `9b29e39b…`'s shipped
state (i.e. this is not an effect of the rehearsal — it is the state of the
already-committed tree):

```
AssertionError: 0 != 1 : projection-not-wired expects one occurrence of its
pattern in dist/e2-editor-app.js and found 0. The tree moved under the
mutation; fix the pattern, not the count.
FAILED (failures=1)
make: *** [Makefile:2801: test-e2-c-static] Error 1
```
exit code 2. Full log: `test-e2-c-static-2026-09-07.log`. This is the exact
same stale-pattern break recorded in `../gate-4a-on-9b29e39b/RESULT-4a.md`'s
term 6 section: the `projection-not-wired` mutation's fixed string was written
against the pre-v46 source and no longer matches after the v46 hunk. Not fixed
here. `make test-e2-c-reachability` is unaffected: exit 0, full log
`test-e2-c-reachability-2026-09-07.log`.

Also required and unaffected: `python3 tools/build_e2_c_shell_bundle.py`
(default manifest) exits 0, `bundleSha256 ecfb6866…`, `problems: []`;
`python3 -m unittest tests.test_e2_c_shell_bundle` 12/12; and
`python3 tools/build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v43.json`
still refuses: *"manifest is out of date … refusing to rewrite
e2/editor-shell-v2-bundle-v43.json … a changed shell needs a NEW generation"* —
the anti-rewrite proof that `tools/build_e2_c_shell_bundle.py` was genuinely
restored to its committed state, not left pointed at v49.

## The tree afterwards — exactly as it found it

`git status --short` empty both immediately after the script's own restore and
after the trap's second (redundant, harmless) firing at script exit.
`web/e2-editor-app.js` and `dist/e2-editor-app.js` both
`df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143`, `MANIFEST`
back to `e2/editor-shell-v2-bundle-v48.json`, `e2/editor-shell-v2-bundle-v49.json`
removed.

**All thirteen bound paths, sha256 before and after, identical — both the
source tree and the `dist/` mirror:**

```
$ diff bound-sha-before-9b29e39b.txt bound-sha-after-9b29e39b.txt
(no output)
$ diff bound-sha-before-dist-9b29e39b.txt bound-sha-after-dist-9b29e39b.txt
(no output)
```

Full listings banked beside this file: `bound-sha-before-9b29e39b.txt`,
`bound-sha-after-9b29e39b.txt`, `bound-sha-before-dist-9b29e39b.txt`,
`bound-sha-after-dist-9b29e39b.txt`.

## No kills this time

Unlike the 2026-09-06 take (two attempts killed by the harness for a low-memory
threshold before a clean third), this run completed on the first attempt —
`REHEARSAL SCRIPT DONE` printed once, no `Killed` line in the transcript.
