# Host 0.2.34 — spreadsheet cell editor installed, H-write holds, stopped

Installed uncounted candidate: host **2f3ef60972b195096baa3e1dbddd1a70829a6626**, package **d308e0cc58958d85**, new **ods-editor-v1 / d5a081f8**. Writer v22 and readonly viewer v3 retain their previous identities. All **35** previous packaged file records (including compressed metadata) are unchanged; ten new paths add the cell editor. `release.json`, `manifest-diff-final.json` and `pre-stop-verification.json` record the actual identity. Full K remains deferred/batched; nominal shipped host is **0.2.26**.

## Read the existing acceptance artifacts

From the repository root, without a browser, build or service:

```bash
python3 wasm_sdk_probe/tools/read_calc_editor_acceptance.py --red-cases
```

`acceptance-reader.txt`: no problems; **171** native checks, **186** browser editing/download checks; host **23 admin + 2 readonly checks per browser**. Three reader controls turn red (empty native population, missing Firefox W-edit, real conflict-copy state red). The reader also reads downloaded/server ODS bytes and XML, and raw conditional PUT headers/status and preserved-original hashes. It does not launch K or replace its criteria.

The H-write evidence is deliberately split:

| Browser / completed arm | Report | Result |
| --- | --- | --- |
| Chrome writable + Writer | `host-write-03/report.json` | All 23 admin checks pass; the report's subsequent readonly arm fails and remains a failure |
| Chrome readonly share | `host-readonly-05/report.json` | Both Chrome readonly checks pass; its later Firefox certificate setup fails before a product page |
| Firefox writable + Writer + readonly | `host-firefox-07/report.json` | 27/27 including two setup checks; complete run clean |

Both browsers actually enter from Files. Positive locks are verified through DAV, and a second PUT without their held token gets **423**. Actual original PUT carries ODS MIME, **If-Match** and its lock condition. Server GET bytes, independent ODS XML and an actual Files reopen confirm text, formula calculation and B/I/U. An external write on the runner's own locked file uses its own token; saving preserves those external bytes and creates an ODS conflict copy. A later save updates the same copy while preserving the external original. A temporary user receives permission-1 sharing, opens the old viewer route, has no save entry, and creates no lock. Each browser also opens and saves a separate Writer fixture, checked in server XML.

`*-server-saved.ods`, `*-writer-saved.odt`, `*-conflict-copy.ods` and screenshots retain the files. The conflict-copy artifact is the final copy after its follow-up save (`After conflict <browser>`); initial local-copy text is retained in raw checks. These are owned disposable files, not owner documents.

## Preserved failures and corrections

- `host-write-01`: test reader returned a DOM node to CDP, causing object-chain serialization failure. Corrected to return a boolean.
- `host-write-02`: **real product red**. The host successfully created the right ODS copy, but the new session looked at `error.details.outcome`; the actual host uses `error.outcome`. Witness **a25eedb0**, red-first unit and fix **85ad4e33**. Copy success clears dirty while preserving the notice; stranded content stays dirty. The engine was not changed/relinked.
- First package **df7f6fe14e395638** is retained in its own immutable archive, `release-first-attempt.json`, first checksums/offline output. Corrected package changes exactly one new session asset (`manifest-diff-correction.json`). Both offline packages have zero problems and **22/22** red cases.
- `host-readonly-04`: **real routing red**. Files sent a permission-1 shared file into the editor, while the server correctly resolved it readonly and disabled mutation. Host **2f3ef60** redirects the readonly target to the viewer using the server-resolved permission. No engine/package change. Chrome readonly passed in 05; Firefox passed in 07. The old client permission mock is not used as evidence of real sharing permissions.
- 05's Firefox setup lacked the local development CA. 06's external Firefox profile was under `/tmp`, inaccessible to snap Firefox. The final runner uses an isolated build-directory profile with the existing mkcert development CA, deleted afterward. It changes no daily browser profile/trust store. The failed-constructor geckodriver was identified by its exact port and terminated (`firefox-constructor-cleanup.json`).
- The initial previous-package directory control referenced an already removed 0.2.33 worktree (`offline-package-control-old-path-error.txt`). `previous-manifest-control.txt` instead reads the real archived 0.2.33 manifest and rejects the missing editor page. Do not describe the failed path lookup as a package verdict.

## Installation, rollback and environment

Before mutation: isolated host commits, engine archive and checksums, offline package guards, guarded install and concrete functional rollback were prepared. The install fast-forwarded the host and `occ upgrade` completed 0.2.34 with maintenance disabled; all three unauthenticated routes returned 401. The later session package refresh and server routing correction were guarded against exact predecessor identities in the same feature slot. The expired-window control refuses before mutation. `rollback-package.sh` restores 0.2.33 source and engine, retaining the installed 0.2.34 version label; it was prepared but not executed.

Only litecore was started in the autonomous idle feature slot authorized by the owner and SPEC-M4-cell-editing-v1 section 3.5. This was not K/P5. **No global lock-table clearing** or root command occurred. Before/after lock file-id lists are both empty. Every temporary user/share/folder was removed and independently checked; normal page departure released the final runs' own locks. The early real dirty-state failure required one explicit UNLOCK for its own test file, recorded in run 02. The owner's edited fileId **24920** remains **31,008 B**, sha256 **a84629657cf01ea0adeb26991c6f62932e2df601637ecaee0b1fa6721afa6adb** (`owner-fixture-preserved.json`).

`cleanup.json` and raw ddev snapshots show all statuses restored: **litecore stopped**, fgp-nc and nc-bridge paused, all others stopped. Live source is clean. The isolated worktree was verified against the archive and removed; branch `host-0.2.34`, both package archives, the frozen profile and profile archive remain. No manual acceptance is newly pending. Prior owner F3-hand/Home-End/dialog/H7/V3-SEE observations remain accepted.

Section 34.4: **+0/+0**, cumulative **47/27**. New feature implementation, bindings and new tools; no existing judge was repaired. Full count pins/BINDING/chain were not moved. Manual save and whole-cell B/I/U are the v1 scope; existing ODS limitations remain. Native/browser details: [cell evidence](../m4-cell-editing/README.md).
