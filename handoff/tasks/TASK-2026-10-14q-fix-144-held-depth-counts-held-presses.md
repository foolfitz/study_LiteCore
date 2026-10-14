# Task 2026-10-14q: fix finding 144 for host 0.2.22 (132's depth rule must count the presses 141 holds)

**Authority.** The owner chose **A**: fix it now and release 0.2.22. You rule the details on the owner's behalf. Append a zh-TW 裁決 section to `findings/144-…md` and to `findings/141-…md` (the 141 fix is what broke it), and add an English section to `findings/evidence/host-0.2.21/README.md` or a new `findings/evidence/host-0.2.22/` directory.

**The defect** (`findings/144-…md`; the main session checked the source):
- Since 141, a second same-key press made while the first delete is unanswered is held on the page (`web/e2-editor-app.js:2603`, `heldDeletes.count`). So `deletesInFlight` never exceeds 1.
- 132's depth rule (`dropsHeldRepeat`, `:2834–2837`) drops a flagged repeat only at `deletesInFlight >= HELD_DELETE_DEPTH` (2), so it never fires.
- Every repeat of a held key is held and then released one by one. On 0.2.21, K3c (132-B, `findings/evidence/host-0.2.21/k3/`) measured 27–29 deletes after release (0.2.18: 1–2), the last at 1.78–1.85 s, and 52 characters per hold (0.2.18: 25/26). Same in both browsers, 12/12 holds.

**The direction the main session sees** (check it, do not assume it): count the held presses in the depth, e.g. `deletesInFlight + heldDeletes.count >= HELD_DELETE_DEPTH` at the keydown. After release this should leave at most one in flight plus one held, which is 132's 「放開之後最多再刪 2 字」. Finding 141's boundary behaviour must not regress: a burst of unflagged presses at a C boundary still gives exactly 1 request. Finding 131's press-for-press for unflagged presses inside text must stay.

## Criteria, written before any run (the default if never met: 0.2.22 is not released, 0.2.21 stays installed with the owner told not to hold delete keys inside text)

- **U1 (red first on `2d6c4580…`).** Flagged repeats (`repeat: true`) of Backspace while one delete is unanswered and one press is held are dropped at keydown (no `beforeinput`). A hold of N flagged repeats leaves ≤ 2 deletes after the key-up. On today's bytes this must be red.
- **U2.** 141's tests (`editor-shell-v2/tests/page-held-deletes.test.mjs`) and 131/132's existing tests stay green unchanged, or say exactly why one must change.
- **U3.** The `editor-shell-v2` suite stays green, and `check_e1_c_bundle_intact.py` prints `intact: true`.
- **N1 (no host, `dist/` mirror on v20, your page, never `--write`, Firefox and Chrome):**
  - 10-14o's `burst-1s` at the document start: exactly 1 engine request, ready < 2.5 s;
  - the in-text control burst (unflagged): every press deletes.
  - If you can drive a **flagged** hold inside text on the mirror, i.e. WebDriver/CDP repeats with `repeat: true`, record its deletes-after-release, which must be ≤ 2. If not, say so; the host-side 132-B (H1) is the binding check.
- **H1 (host, after the main session installs 0.2.22; run by a later task):**
  - 132-B as K3c ran it: `132-B PASS`, with (a) ≤ 2 deletes after release in 12/12 holds;
  - K3a and K3b as in task 10-14p.

Run U1–U3 and N1. Report when the page bytes are ready for the v71 freeze.

## Limits

- **Edit only:**
  - `web/e2-editor-app.js`;
  - `editor-shell-v2/tests/` (new or adapted tests, with reasons);
  - `findings/144-*`, `findings/141-*` (append only);
  - `findings/evidence/host-0.2.22/` (new).
- Do not touch the host. Do not freeze, package, run `occ upgrade` or link, and never `--write`. The only `make` is `e2-c-assets`.
- Owner's-instance desk rules as in 10-14o. N1 is no-host, so the instance is not needed.
- Commit only your own paths (`git commit -- <paths>`). If `.git/index.lock` exists, wait and retry. End messages with your model's `Co-Authored-By` line; never a `Claude-Session` line; no push.

## Output

A `## SUMMARY` of at most 20 lines:
- the change in one or two sentences;
- U1 red, then green;
- U2 and U3 counts;
- the N1 numbers;
- the page sha256 now in `dist/`;
- anything the freeze must know, including any product-path mutation anchor the change moves (`tests/test_product_path_mutations.py` will say).
