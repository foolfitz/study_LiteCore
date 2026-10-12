# SPEC-M3-autosave §4 M2 — one save, end to end, in two segments, host 0.2.12 (2026-10-12)

`wasm_sdk_probe/tools/probe_autosave_m1.py --mode m2` (hash in `probe.sha256`, the same file as `../../130/m1b/probe.sha256`). Host 0.2.12 `b245ae7`, served page `8909564e…`, engine v19, the owner's document (563 KB) uploaded as `probe-autosave-m1.odt`. Per browser and round one session: five times, type one letter, 0.5 s, press save, wait until the host has settled it, 2.5 s. `run-1/report.json` (03:35:30–03:38:52 UTC, 2 rounds × Chrome 151 / Firefox 157); `shakedown/report.json` (one Chrome round at 03:06 UTC).

The segments:
- **engine** — the page's latency line `儲存 N ms`: `run("儲存", () => session.save())`, the part that runs in the session's queue (input waits behind it; see `../../130/m1b/`).
- **host, as the page sees it** — `存回 N ms`: `run("存回", () => HOST.save(...))`; the host's `fetch` calls are outside the session's queue (read from `web/e2-editor-app.js` `saveOnce` and `run()`: neither gates the input adapter; not measured here by typing).
- from the host's own record (`data-litecore` `saves[n].attempts[0]`): `waited` (the 1.1 s spacing), `check.ms` (the read-back GET and its hash), PUT (`respondedAt − at`).

## Result (ms)

| | save 1 (first after open) | saves 2–5 |
|---|---|---|
| engine, Chrome (r1, r2; shakedown) | 616, 663; 673 | 158–181; 154–209 |
| engine, Firefox (r1, r2) | 735, 684 | 276–301 |
| host as the page sees it, all | 85–100 | 83–105 (shakedown 78–92) |
| spacing wait | 0 | 0 |
| read-back GET + hash | 27–35 | 27–39 |
| PUT | 57–67 | 54–67 |

Every save's outcome `saved`, one attempt each. Load average 0.6–0.9 for the shakedown, 1.8–2.2 for run-1 (the native measurements of task 2026-10-12c were running); the two sets agree within ~60 ms on the engine segment and ~20 ms on the host segment.

## Prediction record (in the probe's docstring, written before the first m2 run)

- first save's engine segment 590–720 ms — 4 of 5 inside; **Firefox r1 735 ms outside** by 15 ms.
- the others 160–310 ms — Chrome's 154 and 158 (shakedown, r1) **below** by 2–6 ms; the rest inside.
- host segment 100–400 ms — **missed low**: 78–105 ms. A local ddev instance; a real server's round trips will be longer.
- no spacing wait (saves 2.5 s apart) — **held**.

## What this settles for the spec

An autosave blocks input for the engine segment only: about 0.6–0.75 s for the first save after open, 0.15–0.3 s after that, on the owner's document. The host's part (≈ 0.1 s here) does not hold the session's queue. Combined with `../../130/m1b/`: at typing speed nothing is lost even during the first save; a held key is, and that is where finding 130's notice has to speak.
