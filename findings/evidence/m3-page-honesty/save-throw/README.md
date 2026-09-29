# A lock lost while the save's PUT is on the wire (review BLOCKING 1, finding 108)

Probe: `wasm_sdk_probe/tools/probe_m3_save_throw.py` (sha256 `4771383b…`, unchanged across all four
reports). Chrome 151.0.7922.169, cold profile, dev instance `litecore.ddev.site`, file
`M3 骨架 測試.odt` reset before each run.

What the probe does: open from Files, one edit (heading, revision 0 → 1), press save; CDP `Fetch`
holds the save's PUT; the `oc_files_lock` row is deleted behind the host's back; every other request
is let through until the host records its lock `lost` by its own 60 s refresh; then the PUT is
released. Verdict KEPT = the bytes the page sent are on the original, or in a copy, or stranded with
leaving asked; else LOST.

## The three steps (predictions written in the 09-29g handoff before any run)

| Report | Host | Host script sha256 | Predicted | Measured | Attempts (status, withToken) | Where the bytes went | Leave asked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `2026-09-29T105616+0000.json` | `c740d2f` 0.2.3, clean | `bb41c944…` | LOST | **LOST** | (412, true) | nowhere: original unchanged (`3b6db004…`), no copy, not stranded | no — landed on `/apps/files/files` |
| `2026-09-29T105821+0000.json` | `c740d2f` + fix step `b` (catch-all), uncommitted, still 0.2.3 | `f6bff615…` | KEPT via stranded + leave asked | **KEPT** | (412, true) | stranded (`ccf1fe65…`, 10,232 bytes); download button shown | yes — `beforeunload` dialog, stayed on the editor after declining |
| `2026-09-29T110015+0000.json` | `c740d2f` + steps `b` and `a`, uncommitted, 0.2.4 after `ddev occ upgrade` | `cdaf63c3…` | KEPT on the original (or a copy) | **KEPT** | (412, true), (204, false) | original (`d6c84d75…` = sent) | no (nothing unsaved) |
| `2026-09-29T110220+0000.json` | `369e6ed` 0.2.4, **clean** (committed) | `33da187f…` | same as above | **KEPT** | (412, true), (204, false) | original (`71e6d7fd…` = sent) | no (nothing unsaved) |

The fourth report exists because the committed host differs from the third report's bytes: a
header-comment edit (the `save()` paragraph now says every save ends saved, copied or stranded) was
made after the third run. It is the one that binds host 0.2.4.

In every run the edit landed (`smoke.caret.revision` 0 → `smoke.acted.revision` 1, latency
「標題 …ms」), the lock was `held` when the PUT was held (`heldAt.lock.state`), and exactly one lock
row was deleted.

## Read from these reports

- **Step 1 is the data loss.** Page toast: `存回：Cannot read properties of null (reading 'replace')`;
  page line 「存回 失敗」; the host bar shows only the lock-lost notice, the download button is
  hidden; `host.stranded` is null and `host.error` is null (the throw came out of `save()`, not
  `run()`); the leave went through with no dialog. `tokenOnServer` is absent from the save record
  because the call threw before its result was assigned.
- **Step 2 shows the catch-all alone is enough to keep the bytes**, and that it is the same throw:
  `saves[0].unexpected` = `TypeError: Cannot read properties of null (reading 'replace')`,
  `outcome` = `stranded`. Page toast: `HOST_SAVE_FAILED：存回時發生未預期的錯誤：…`.
- **Step 3 shows asking about the token that was sent turns the loss into a normal save**:
  `tokenOnServer` false → `loseLock('save', 412)` (a no-op, the refresh already lost it) → the
  retry without the token is 204, because deleting the lock row does not move the ETag
  (`lockAfterDelete.etag` = the `If-Match` value). The retry waited out the 1.1 s spacing
  (`attempts[1].waited`) and its read-back matched.
- **The refresh against a deleted lock row answered 400, not 412** (`host.lock.refreshes[0].status`,
  all four runs). 400 is in the host's `LOST` list, so the trigger works; this is recorded because
  the 09-29g handoff expected "a LOST status" without naming one.

## Limits

- Chrome only, one run per step. The trigger is deterministic (the PUT is held until the refresh
  has already lost the lock), so the repeat count measures the host code path, not a race rate; the
  real-world rate of a refresh landing inside a PUT's round trip was not measured.
- The lock was lost by deleting its row, which answers 400. A lock lost by expiry or by an unlock
  from Files may answer another status (412/423); the host code treats all of `LOST` the same way.
- On the committed 0.2.4 the catch-all is not exercised by this probe (step `a` removes the throw).
  Its only measurement is step 2. It also covers, by construction and unmeasured, the §7.5-registered
  `.text()` throw in `tokenOnServer` and any throw in `saveCopy`.

## Files

- `host_fix_0_2_4.py` — the two fix steps as applied in steps 2 and 3 (sha256 `d371f4c1…`). The
  committed host adds only the header-comment edit on top.
