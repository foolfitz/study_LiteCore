# SPEC-M3-autosave §4 M3 — two saves after a conflict, on host 0.2.12 (2026-10-12)

`wasm_sdk_probe/tools/probe_autosave_m3.py` (hash in `probe.sha256`). Host 0.2.12 `b245ae7`, served page `8909564e…`, engine v19. Fixture `dist/e1-fixtures/multi-paragraph.odt` (sha256 `3b6db004…`) uploaded as `probe-autosave-m3.odt`; intruder bytes `dist/e1-fixtures/list-contexts.odt` (`bf10a4b0…`). Not a counted runner; no product byte touched.

## What it does

The locks runner's K6 shape (`check_m3_locks.py` arm `broken-then-written`): open the file from Files (the host takes its token lock), then the owner removes that lock through files_lock's OCS route (200) and writes the intruder's bytes over the file (204). Our token is dead and our ETag stale. Then edit 1 (`set-paragraph-heading` at (0.35, 0.28)) → save 1 (toolbar button); edit 2 (insert the text `LC2` through the insert field) → save 2. The server is then read: the original's hash, every copy next to it (hash, and whether its `content.xml` holds `LC2`), the host's record, the host bar and the title bar.

## Result (`run-1/report.json`; Chrome 151 and Firefox 157, two rounds each; `shakedown/` is one earlier Chrome round, same result)

| | Chrome #1 | Firefox #1 | Chrome #2 | Firefox #2 |
|---|---|---|---|---|
| save 1 attempts (status, with token) | (412, yes), (412, no) | same | same | same |
| save 1 outcome | copy | copy | copy | copy |
| save 2 attempts | (412, no) | same | same | same |
| save 2 outcome | copy | copy | copy | copy |
| copies on the server | 2 | 2 | 2 | 2 |
| copy n's hash = save n's bytes | yes, yes | yes, yes | yes, yes | yes, yes |
| copy holds `LC2` | no, yes | no, yes | no, yes | no, yes |
| original = intruder's bytes | yes | yes | yes | yes |

In every round, after save 2: the host bar shows only `鎖已失效：別人現在可以寫這個檔案；存檔前仍會確認檔案沒被別人改過。` (the lost-lock notice from save 1's retry); nothing on the bar says where the content went. The title bar still reads `probe-autosave-m3.odt` and `尚未儲存` is hidden (the session is clean: `dirty` was cleared when the engine produced the bytes). The page's latency line reads `存回 失敗`; the only statement of the copy's name was the 4-second toast.

## Prediction record

Written in the probe's docstring before the first run, from `litecore-editor.js` 0.2.12: save 1 (412 with token, 412 without) → copy; save 2 (412 without) → copy; 2 copies; first copy = save 1's bytes; second holds the marker; original keeps the intruder's bytes; the bar shows the lost-lock notice, not where the content went. **Held in all 5 rounds (shakedown included).**

## What this settles

SPEC-M3-autosave §2.1's inference ("after a copy the host keeps its ETag and hash, so every later save meets the same conflict and writes one more copy") is now observed, in both browsers. With autosave on and this behaviour unchanged, every idle stretch after a conflict would add one copy. The owner chose O1 = B on 2026-10-12 (spec §8.2): after a copy, the session saves to that copy. This report is the red case for that change: on 0.2.12, two saves after a conflict leave **2** copies; under B they must leave **1**, holding the second edit.
