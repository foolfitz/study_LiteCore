# Native keyboard input after the Markdown dialog, Xvfb diagnostic

Run **2026-10-25 03:09:12-03:10:12 Asia/Taipei**, using `../native_xvfb_focus.py`. The source sha256 matches `report.json`. This is a non-counted automated diagnostic, not the owner's F3-hand report.

```bash
env -u WAYLAND_DISPLAY -u WAYLAND_SOCKET XDG_SESSION_TYPE=x11 xvfb-run -a -s '-screen 0 1600x1200x24 -nolisten tcp' python3 findings/evidence/host-0.2.33/count-preparation-2026-10-25/native_xvfb_focus.py
```

Three rounds, each with a fresh headed Chrome profile and its own generated ODT opened through the actual Nextcloud Files action. The tool reuses the existing headed launcher, with host-helper-compatible `LockChrome` dispatch. It records the full browser argv: **no `--headless=new`**. It focuses only the Chrome window belonging to its own process on the isolated X display. Text is injected with **libXtst / XTestFakeKeyEvent**, not CDP or DOM keyboard events; page records show the native keydowns as **trusted**.

## Observations

All **3/3** rounds recorded:

- Insert a paragraph through the Markdown dialog, then type `xvfbafterinsert`: the focus is back on `sink`, and the exact marker is present in the server-saved ODT.
- Open the dialog, type `discardedxvfb`, cancel, then type `xvfbaftercancel`: the focus is back on `sink`, the second marker is saved, and the cancelled dialog text is absent from the saved file.
- The inserted Markdown text `xvfbpasted` is also saved. The host reports save outcome `saved`, and the subsequent WebDAV GET is **200**.

`round-1.png` through `round-3.png` show the final product view. Round 1 was visually inspected: the typed markers appear in the document and the save notice is visible. Native keydown records, saved paragraph texts, focus and identity are in `report.json`. The self-created remote folder was deleted (**204**) after all three rounds, and all diagnostic browsers closed.

## Limits and correction history

This verifies the automated native **X11** keyboard path on host **0.2.33 / a67beefefebe57d6**, editor **e2-editor-v22 / f7a40bcc**, page **3b96cb16…**. It does not assert a latency criterion, subjective appearance acceptance, or the owner's personal desktop/IME experience. `report.json` explicitly keeps `ownerF3HandSatisfied: false`; v22 section 11.3 still requires the owner's report.

The first attempt incorrectly used the bare headed Chrome base with host helpers that dispatch on `LockChrome`. All three rounds failed at login with `AttributeError: ... has no attribute 'command'`, before any document interaction. Its exact source and outputs are retained in `../native_xvfb_focus-attempt-1.py`, `../xvfb-focus-attempt-1.log` and `../xvfb-focus-attempt-1/`. The correction is confined to this diagnostic's adapter; no shared launcher, product or acceptance judge changed. The successful retry above used fresh output and profiles.
