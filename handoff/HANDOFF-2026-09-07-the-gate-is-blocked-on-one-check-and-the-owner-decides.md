# Handoff, 2026-09-07 — the gate is blocked on one check, and the owner decides

Written for the next agent (or the owner) after the T2 follow-up
(`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "T2 came back red;
the schedule is stopped"). Everything here is checkable in the tree; where it
is not, it says so.

## Read this first: the tree is consistent

| | value | source |
|---|---|---|
| candidate page (`build_cutover_page.py --profile e2-editor-v12`, no `--write`) | `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c` | re-measured tonight, matches every banked report |
| shell (`web/` and `dist/`, byte-identical) | `df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143` (`e2-editor-app.js`) | `sha256sum` |
| shell bundle currently declared, `MANIFEST` | `e2/editor-shell-v2-bundle-v48.json`, `bundleSha256 ecfb6866117673c21a7c21995f7ea76fe60beb9f94a73c222053a18cc573a6ef` | `tools/build_e2_c_shell_bundle.py:448` |
| cutover generation (frozen on cut-over bytes, kept as the record of the mistake) | v47, `bundleSha256 cf7f923391a059943366b46bde8f25c7a618da57752e592ffaa13398e78161e4` | `e2/editor-shell-v2-bundle-v47.json` |
| shipped profile / pin (tree currently ships) | `e2-editor-v8` / `4a2710bba1ef07d9` | `web/e2-editor-app.js:49,1425` |
| candidate profile / pin (what the cutover would ship) | `e2-editor-v12` / `4ec1e389aaab3b03` | banked `candidateCutover` stamps |
| `check_soak_bank.py` `DEFAULT_SHA` | `9b29e39b…` | line 108 |
| `check_soak_bank.py` `DEFAULT_SERVED_SHELL` | `cf7f9233…` (v47 — the CUTOVER generation's digest, not the tree's shipping generation) | line 247, corrected tonight |
| `check_caret_diagnostics.py` `DEFAULT_SHA` | `9b29e39b…` | line 50 |
| soak bank | 2 runs banked, both FAIL on one check (see below); 0 diagnostics or ODT/revert runs stored there | `findings/evidence/queue-v12-cutover-soak/` |
| soak count | **0 of 12** | `check_soak_bank.py`, unchanged all night |
| unpushed commits | **581**, `main` has no upstream | `git rev-list --count HEAD`; pushing is the owner's step |

`git status` is clean as of this commit.

## What is discharged on this page

All of the following are re-earned on `9b29e39b…` / shell v48, by the existing
judges, not by this session's reading:

* **4a, all eight terms.** `findings/evidence/gate-4a-on-9b29e39b/RESULT-4a.md`:
  terms 1, 2, 3, 4, 5, 7, 8 were `check_4a.py`-verified `ok: true` earlier
  tonight; term 6 (the mutation) could not even be applied then (R-3, below)
  and is now measured for the first time — the re-anchored mutation reddens
  exactly `the-document-region-says-why-it-is-empty` and nothing else, proven
  by a real browser run, with `web/`/`dist/` verified byte-identical
  (`df5f3b6c…`) before and after by sha256.
* **Condition 2** (caret diagnostics): `check_caret_diagnostics.py`, four
  clauses, `ok: true` (commit `25670d0e`).
* **ODT round trip**: both directions pass (commit `d450f6ff`).
* **Revert condition 3**: ruling E-3's five terms all met, the tree left
  exactly as the rehearsal found it, verified by sha256 over all thirteen
  bound paths in both `web/` and `dist/` (commit `dbabc3c9`).
* **4b's mechanical half**: `findings/evidence/manual-round-v12d-9b29e39b/`
  — ten paragraphs reach the Orca log, headings are announced with level, the
  second-heading residue is absent, agent-driven under the consent on file.
  Ruled discharged on this exact page in
  `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, "The page is final:
  `9b29e39b…` on shell generation v48".

## What blocks

**R-1**: the product-path check `the-document-region-says-why-it-is-empty`
FAILs on every v12-pinned run whose focused paragraph is currently named by
the structure projection — by design, not by regression. `findings/092-*.md`
has the full mechanism: the check's own probe
(`READ_A11Y_REGION` in `tools/run_e2_c_product_path.py`) reads only the live
region's `textContent`/`dataset.reason` and `dataset.offers`; it never reads
`dataset.deferredToStructure`, the attribute finding 088's fix added
specifically so a probe could tell "silent because the structure channel
already said it" from "silent because there is nothing to say". Reproduced
6/6 on `e2-editor-v12`, 0/0 on the shipped `e2-editor-v8` control (which has no
structure projection to defer to). None of the ten pre-088 `20f09cc9…` soak
runs ever exercised this interaction, so tonight is the first time it has been
measured at all — this is not something v46 broke.

Finding 092 lists three dispositions, recommendation **A**: change the check
to accept either channel (the live region, or the structure channel's active
descendant with a non-empty focused-node text when
`data-deferred-to-structure="1"`) as "something to read". This is a test
change (`AGENTS.md` §4 permits it — the premise the check was written on, "the
live region is the only channel", was falsified by findings 087/088), needs a
red case (both channels silent must still FAIL), and zeroes the soak count
under `AGENTS.md` §9's count semantics (no cost: the count is already 0). **B**
reverts 088's fix to make the check pass again — the owner already rejected
that behaviour by ear once. **C** leaves the check as-is — the soak can never
reach 12 while `e2-editor-v12` ships a structure projection. This is the
owner's call: it changes what "clean" means for the gate.

**Residual risk, either way**: a screen reader that reads only the live
region and does not follow `aria-activedescendant` gets nothing at all on
`e2-editor-v12` when the structure channel has taken over. Orca (which does
follow it) has been measured clean; this combination has not been measured at
all. If it is never measured, the default conclusion is "known but
unmeasured gap", not "checked and fine".

## What was corrected tonight

* **R-2** (`53961163`): `check_soak_bank.py`'s `DEFAULT_SERVED_SHELL` pinned
  v48's digest (the shell as the tree ships it) instead of the digest a
  `--candidate-profile e2-editor-v12` run actually serves — which is, by
  construction, the digest of the cut-over shell, i.e. v47 (the generation
  frozen by mistake, see next section). Verified two ways: read from
  `e2-editor-shell-v2-bundle-v47.json`, and read `servedShell.servedSha256`
  from both banked soak reports — both equal `cf7f9233…`. After the fix,
  `one-served-shell: true` on both banked runs; `every-run-clean` is still
  `false` (R-1) and the count is still 0 of 12 — this removed one false
  negative, it did not manufacture a clean run.
  `check_soak_bank.py --self-test` still declines with the same message it
  gave before this fix, verbatim: `RED 11's run must fail on one-served-shell
  and NOTHING else; other false clauses: ['run-ok', 'pass-count']` — that
  self-test case reads the real bank, and the real bank's two runs already
  carry `run-ok: false` / `pass-count: false` from R-1, not from anything R-2
  touched.
* **R-3** (`c668b812`): the 4a term-6 mutation's `find` pattern was anchored
  on the pre-v45 call site (`projectFocusedParagraph(snapshot);`, 0
  occurrences after 78f1cb3a gave the function a second parameter). Re-anchored
  on the current call site (`projectFocusedParagraph(snapshot,
  structureSpeaks);`, exactly one occurrence), same semantic mutation. Static
  test (`tests.test_product_path_mutations`) passes; the red case was proven
  for real — the mutation reddens exactly its target check and nothing else,
  and `web/`/`dist/` were verified byte-identical (`df5f3b6c…`) before and
  after. `make test-e2-c-static` now exits 0 (was exit 2 on the committed
  tree, per `queue-v12-cutover-revert-rehearsal/RESULT-2026-09-07-revert-condition-3-discharged-on-9b29e39b.md`).
* **Finding 092 drafted** (`17b7740b`): R-1's mechanism, evidence and
  disposition options, so the owner's decision has a document to decide
  against rather than a paragraph in a plan.

## The T1d overshoot and its correction (from the plan, not re-verified further here)

Commit `000a57e2` landed the v46 hunk, froze generation v47, **and** performed
the actual cutover (`build_cutover_page.py --write`), repointing
`web/e2-editor-app.js` to `PINNED_WASM_SHA256 4ec1e389aaab3b03` /
`workerUrl …/e2-editor-v12/…` — before the gate had passed. `2d319677`
corrected this without rewriting history: it restored the shipping lines
(`e2-editor-v8` / `4a2710bba1ef07d9`), kept the v46 hunk, brought `dist/` back
to identity, and froze **v48** on that shell; v47 stays in the tree as the
record of the mistake. The candidate page sha was re-measured (without
`--write`) and confirmed unchanged at `9b29e39b…` — the page T1c had measured
— because `build_cutover_page.py`'s repoint fully substitutes the two lines
regardless of what the source already carried. The lesson recorded in the
plan: a measurement build needs to be named as one ("never `--write`") because
"build the candidate page and hash it" was read as the tool's default landing
path.

## Schedule state: stopped

T3's four scheduled wake-ups (soak sessions for 2026-09-07 08:17/15:47 and
2026-09-08 08:17/15:47 CST) are deleted — R-1 is not the named known
intermittent (`clear-format-removes-every-inline-format`), so per the FAIL
policy written before the schedule started, anything else stops it and the
main session does not decide a fix, because a fix moves the page.

**To restart**, once R-1 has a disposition and (if disposition A) the check
change has landed and its own red case is proven: re-open T3 per the plan's
schedule section — two sonnet sessions per UTC day (not one), because the
three-day spread exists for defects that depend on machine state and elapsed
time; the soak needs >= 12 clean runs across >= 3 UTC days with >= 2 clean
runs each; each session runs the shell bundle test before every run,
`--candidate-profile e2-editor-v12`, banks per `RUNS.md`'s conventions, and is
judged by `check_soak_bank.py`.

## What only the owner can do

1. **Decide R-1's disposition** (A/B/C in finding 092) — it changes what
   "clean" means for this gate, which `AGENTS.md` §9 does not let a drafting
   session decide for itself.
2. **T4**: condition 3's six manual cells (open, type with an IME commit,
   paragraph format, inline format on a selection, undo/redo, save and
   reopen — the gate says these are *"not substitutable by more
   automation"*) and 4b's judgement half (order, verbosity, what it sounded
   like) — both identity-bound to `9b29e39b…`/v48, both still owed.
3. **The cutover itself**, once the soak closes.
4. **Pushing the 581 unpushed commits.**

---

## Correction appended by the main session (2026-09-07 ~05:00 CST)

Where this document says condition 4a is discharged on all eight terms: it
is **seven of eight**. Term 6's mutation run reddens exactly the check it
targets — but that check is red on this page **without** the mutation (R-1),
so the run cannot show that the mutation was caught; its composition equals
the baseline's. Term 6 is NOT_ESTABLISHED pending R-1's disposition and a
green baseline run, then re-taken. The re-anchored pattern, the static
mutation tests and `make test-e2-c-static` (exit 0) stand. Ruling and
reasoning: `PLAN-2026-09-06-after-the-page-moved-twice.md`, section "The
follow-up landed, with one downgrade".
