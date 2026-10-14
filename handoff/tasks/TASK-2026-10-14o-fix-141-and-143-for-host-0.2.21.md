# Task 2026-10-14o: fix finding 141 (page) and finding 143 (host CSS) for host 0.2.21

**Authority.** After reading the 10-14n diagnosis, the owner chose **A**: fix 141 and 143 now as host 0.2.21. Finding 142 (Ctrl+Home/End) goes to the next link batch as an engine action and is only registered here. You design the details on the owner's behalf; write the reasons into each finding (zh-TW, an appended 裁決 section) and into the evidence README (English).

**Read first:**
- `findings/141-…md`, `findings/143-…md`;
- `findings/evidence/host-0.2.20-hand-test/README.md` (your own diagnosis);
- findings 131 and 132, with the H2 depth rule in `web/e2-editor-app.js` around `:2600–2760`;
- `specs/SPEC-M3-link-batch.md` §10.5.

## Part 1, finding 141 (page)

- **The fix:** while a same-key delete is in flight, hold further presses of that key. If the in-flight one returns `verified-boundary-noop` with unchanged state, drop the held presses; otherwise release them in order. Finding 131's rule (every press is sent when it can change the document) is kept. Refine this if reading the code argues for it, and say why.
- **Where.** `web/e2-editor-app.js`, or `editor-shell-v2/` if the queue is the better place. Never `editor-shell/`, which is E1-C-bound.
- **Cost.** The page's sha256 moves. The freeze (v70), the re-pins and the packaging are the main session's; do not do them.
- **Tests, red first on today's bytes (page `53019168…`, session `f47c80ec…`):**
  - **T1.** Fake engine answering a no-op at 2,250 ms; 18 keydowns 30 ms apart → exactly 1 delete request, and the page is ready < 2.5 s after the first press. Today: 18 requests, about 40.6 s.
  - **T2 (control).** A real delete inside text; 18 presses → 18 requests, as finding 131 requires.
  - **T3 (control).** A press after the caret moved is sent.
  - **T4.** Flagged repeats (`repeat: true`) still obey H2.
  - **T5.** The `editor-shell-v2` suite and `check_e1_c_bundle_intact.py` stay green.

## Part 2, finding 143 (host)

- In `~/Projects/Nextcloud_Apps/litecore/templates/editor.php`:
  - make the editor root fit Nextcloud's `#content`, so nothing sits under its clip;
  - give `#page-status` legible styling on the host (≥ 13 px and contrast ≥ 4.5:1), or place it where it is seen, e.g. the title bar.
- Prefer host-side CSS that overrides the page, so the page and shell bytes do not change for 143.
- This file is live on the owner's instance the moment you save it, and that is accepted: it is CSS only.
- Do not bump the version and do not commit the host. The host commit is the 0.2.21 release, which is the main session's.

## Criteria, written before any run (the default if never met: 0.2.21 is not released; 0.2.20 stays installed)

- **K1 — unit:** T1–T5 as above; T1 is red on today's bytes and green on yours.
- **K2 — no host:** the `dist/` mirror on v20 with your page (`--out` mirror pattern, never `--write`), Firefox and Chrome. Your 10-14n `burst-1s` arm at the document start of the 60-page fixture:
  - exactly 1 engine delete request;
  - 處理中 ends < 2.5 s after the first keydown;
  - generation `1`, document unchanged, no toast.

  The control arm, the same burst inside text: every press deletes, as today.
- **K3 — host, after the main session installs 0.2.21; run by a later task:**
  - 10-14l's three probes judged by the C-aware judge (`269cbc6d`): `verdict PASS` in held and table, and restore-window recognised as a void C-profile run;
  - your `burst-1s` and `page-number` arms on the 60-page fixture in Firefox and Chrome:
    - burst as in K2;
    - the page-number text's bottom edge ≤ `#content`'s bottom edge;
    - font ≥ 13 px and contrast ≥ 4.5:1;
    - the text follows the wheel as in 10-14n.
- **K4 — 143 now:** your `page-number` arm on the **current** host with your CSS (0.2.20 bytes plus the template change), both browsers, meets K3's geometry and contrast clauses. Its red is today's 990 > 986 and 4.31 / 12 px.

Run K1, K2 and K4. Report when the page bytes are ready for the v70 freeze.

## Limits

- **Edit only:**
  - `web/e2-editor-app.js` (and `web/e2-editor.html` only if the fix needs it);
  - `editor-shell-v2/`;
  - new tests;
  - `templates/editor.php` in the host;
  - `findings/141-*`, `findings/143-*` (append only);
  - a new `findings/evidence/host-0.2.21/` directory.
- No make except `e2-c-assets`. No freeze, no `--write`, no packaging, no `ddev occ upgrade`, no host commit, no version bump, no link.
- The owner's instance: test files go only in folders you create, and you delete them afterwards. Never touch the owner's files or windows. Before each browser run:
  - the KWallet `Locked` property must not be `b true`;
  - record `pgrep -c chrome`;
  - check that nothing of ours is running.

  One browser job at a time.
- Commit only your own study_LiteCore paths (`git commit -- <paths>`). Leave the host template uncommitted and list its diff in the README. End commit messages with your model's `Co-Authored-By` line; never a `Claude-Session` line; no push.

## Output

- `## SUMMARY`, at most 25 lines:
  - the design of each fix in two sentences;
  - K1 (red, then green);
  - K2 and K4 numbers;
  - the page sha256 now in `dist/`;
  - the host template diff;
  - anything the freeze or release must know.
