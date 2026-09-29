# Leaving with unsaved edits (finding 107), 2026-09-29

Probe: `wasm_sdk_probe/tools/probe_m3_unsaved_leave.py`. Dev instance, host `litecore` `695d9ad`
(0.2.2) clean, page `fbfb59a4…`, Chrome only. A measurement, not a gate.

## Result: `2026-09-29T061218+0000.json`

Three rounds, each arm a fresh open from Files, one paragraph action (revision 0 -> 1), a trusted
CDP click on `#text` (user activation), then a renderer-initiated navigation to `/apps/files/`.

| Arm | Dialog | Tab ended at | Server file | Saves | Rounds |
| --- | --- | --- | --- | ---: | --- |
| control (the probe adds its own asking `beforeunload`) | `beforeunload`, dismissed | the editor | unchanged | 0 | 3/3 |
| unsaved | **none** | `/apps/files/files` | **unchanged: the edit is gone** | 0 | 3/3 |

The control shows the instrument sees a leave dialog and the page had the activation a dialog needs,
so "no dialog" in the unsaved arm is the page not asking. `check_m3_locks.py`'s K10 (stranded bytes
guard the leave) is a second, counted positive control.

## Limits

Chrome only; in-page navigation only (tab close, window close, reload not measured); download mode
(no host) not measured. The source has no listener on any of those paths (inference, not measured).

## Other files

- `shakedown/2026-09-29T061134+0000.json`: one round, same outcome.
