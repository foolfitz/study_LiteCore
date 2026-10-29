# F2: clear-format on plain text, four ok answers on v25 and red on v24 (2026-10-29)

Spec `specs/SPEC-M3-link-batch-v25.md` 6.3 F2 (R3), as corrected in section 15 item 7 before any evidence run. Local mirror, no DDEV. Tool `wasm_sdk_probe/tools/check_v25_clear_format_noop.py` (new); products from `wasm_sdk_probe/tools/v25_f_products.py` (v24 from its own bytes: page `b15a6d8e` from git, v24 archive profile, generation 77; v25 as `dist/` serves it, generation 78; identity checked file by file before use).

## The recipe correction (before any evidence run)

The first version of the tool pressed clear-format once, right after placing the caret in plain text, and judged that press. Its shakedown (`recipe-witness-shake-01/report.json`, Chrome, one run per product, scratch output) showed **v24 answering all four requests ok** -- `F2_RED` only because v24 sends no `witness`, i.e. the counterexample was not red for finding 172. v25's four witnesses were all `on-time-item`: on that first press LOK broadcasts all four state items inside the flush. Finding 172 needs a no-op request whose state item does **not** arrive, and LOK re-broadcasts only a state that changed. So the tool now presses clear-format twice on the same plain text and judges the second press (the first is a warm-up that must end in 已清除 and `ready`), and adds one clause: the judged press's `set-bold` witness must be `state-noop` (the press exercised the no-op proof rather than meeting a broadcast). A second shakedown (scratch, Chrome) confirmed the shape before run-01. Fixed-by-execution 1 (spec section 15 item 10).

## Rules (tool docstring)

A judged press PASSes when: exactly set-bold, set-italic, set-underline, set-strikethrough, each `enabled: false`; each answered ok with `changed: true`, `completion: "uno-command-result"`, a witness in {uno-success, on-time-item, state-noop} (the v25 worker forwards only those and turns a missing or unknown engine witness into null, so a non-null witness is the engine's own field -- spec 13 item 4); `set-bold`'s witness `state-noop`; toast starting 已清除; pill `ready`; warm-up held. A v24 run is the counterexample only when red **for 172**: warm-up held and the judged press's first reply `LOK_COMMAND_FAILED`. Exit 0 iff every v25 run passes and every v24 run is red for 172.

## run-01 (15:33:35-15:36:18 +0800; Chrome 156.0.8078.47, Firefox 157.0.1; 3 per browser per product): **F2_HOLDS**

| Product | Browser | Result | Judged press |
| --- | --- | --- | --- |
| v25 | Chrome | 3/3 PASS | four ok, witnesses `state-noop` x4, 已清除…, `ready` |
| v25 | Firefox | 3/3 PASS | the same |
| v24 | Chrome | 3/3 red for 172 | `set-bold` `LOK_COMMAND_FAILED`, the other three never sent, toast 清除格式：LOK_COMMAND_FAILED… |
| v24 | Firefox | 3/3 red for 172 | the same |

Every warm-up held in all twelve runs (v25 warm-up witnesses `on-time-item` x4; v24 none). Identities: v24 and v25 `ok`. Pre-run: no refusal, load 1.28.
