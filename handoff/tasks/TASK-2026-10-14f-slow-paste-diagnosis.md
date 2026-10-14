# Task 2026-10-14f: diagnose a slow paste (the owner's hand test of 0.2.19)

**The report.** The owner hand-tested host 0.2.19 on `https://litecore.ddev.site:8443`. They created a new document and pasted a Markdown text with Ctrl+V, in Chrome and in Firefox. In their words: 「他過好久才跑完，為什麼那麼久？」

The pasted text is small: **40 lines, about 540 characters** (349 CJK), 8 of them Markdown-looking. It is extracted, locally only, to `wasm_sdk_probe/build/paste-repro/owner-paste.txt`. `build/` is git-ignored. **Never commit this text or copy it into evidence**: it is the owner's personal content and names a person. Evidence may record its shape (line count, character count, sha256), not its words.

The main session has not yet heard the owner's answers to three questions: how many seconds, whether both browsers were slow, and what the screen showed while waiting (the 處理中 pill, text appearing in pieces, or a frozen page). If they arrive, they will be sent to you.

**What the main session read (claims to check):**

- The page has no paste handler (`web/e2-editor-app.js:2392`). The paste arrives as `beforeinput` `insertFromPaste`, the input adapter commits it as **one** `commitText`, and that becomes one `document.insertText` (`editor-shell/editor-session.js:510-511`). The engine then makes **one** `paste(document, "text/plain;charset=utf-8", …)` call (`src/probe_engine.cpp:3239`). There is no chunking anywhere.
- So the time goes somewhere between that paste and the page settling. The candidates:
  - engine-side layout of 40 new paragraphs on WASM;
  - the callbacks and editor-state traffic that follows;
  - the page's repaint (C′ canvas, finding 122's per-commit paint path);
  - autosave (0.2.13+) or the checkpoint and save path;
  - finding 111's `_afterTyped` holding;
  - something else.

**Diagnose.**
- Reproduce on the owner's path: the ddev host 0.2.19, Files, "+ New → 新文字文件", then a real clipboard Ctrl+V into the editor. Use a real clipboard if the browser allows it: Chrome through CDP `Browser.grantPermissions` plus `navigator.clipboard.writeText` and a trusted Ctrl+V. The harness path and the user's path must be the same (the repo's lesson); if you cannot drive a real paste in one browser, say so rather than substitute a synthetic `insertText`.
- Break the time into phases, from page timestamps and the worker's or engine's own log:
  - key, then `beforeinput`;
  - `commitText` enqueued;
  - engine paste start and end;
  - the first editor-state push;
  - the page's pill or state returning to idle;
  - the last paint;
  - any save or autosave PUT.
- Controls:
  - the same text as a single line (no newlines);
  - 40 lines of ASCII only;
  - the owner's text pasted into the plain e2-editor page on `dist/` (v19 profile, no host).

  These separate per-paragraph cost, CJK shaping, and host or autosave involvement.
- Each phase claim must name its timestamps. "It is layout" without a measured phase is a hypothesis, not a finding.
- Optionally measure the native 26.8 paste time of the same text through LOK (the probes under `findings/evidence/new-document/probe-1-native-defaults/tool/` show the pattern).

**Output.**
- `findings/evidence/paste-latency/README.md` (English), with the phase table per browser, the controls, and the raw timing files (no pasted text).
- A one-paragraph conclusion: which phase dominates, and whether it is a known finding (122, 111, autosave) or a new one. If it is a new one, give a short candidate description; the main session registers findings.
- No product code changes. Report what a fix would touch; do not make it.

**Limits.**
- No make, no link, no `--write`, no freeze.
- Do not edit `web/`, `editor-shell*/`, `sdk/`, `src/`, the `Makefile` or `dist/profiles/*`. Do not change the host app.
- On the ddev instance, create test files only in a folder you create, and delete them afterwards. Do not touch the owner's other files.
- Before each browser run:
  - check that the KWallet `Locked` property is not `b true`;
  - record `pgrep -c chrome`;
  - check that `pgrep -af "probe_|check_m3|run_e2_c|run_merge|run_v20"` shows nothing of ours.
- Commit only your own paths (`git commit -- <paths>`) with your model's `Co-Authored-By` line.
- Report a `## SUMMARY` of at most 25 lines.
