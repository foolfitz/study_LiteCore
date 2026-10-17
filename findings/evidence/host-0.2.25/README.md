# Host 0.2.25 (2026-10-17)

Engine v21 (item 1 only) and shell generation v74, packaged into the `litecore` app after the v74 freeze (`4628c9d3`).
Handoff 10-17b "Next" step 2.

| what | value | file |
|---|---|---|
| host commit | `03970d0` (`appinfo/info.xml` 0.2.24 → 0.2.25 only) | |
| install | `ddev occ upgrade`, run by the owner (the auto-mode classifier refused it to the session); `app:list` 0.2.25, maintenance false, debug false | |
| engine package | buildId `f5f0df762e1855f2`, 22 files; profile `e2-editor-v21` (wasm `db3408f5…`, worker `0d55bcfa…`), page `605cf24b…` | `check-engine-decoded.txt` |
| differs from 0.2.24's (`d3cd39bb…`) | the profile (v20 → v21, 4 files) and 6 shell files: `e2-editor-app.js`, `e2-editor.html`, the client, the session, `paragraph-editor-client.js`, `document-sdk.js` | archive `ATTRIBUTION.md` |
| HTTP | entry 303 → address `f5f0df762e1855f2-90d7bc2c`; page, worker and wasm decode to the manifest's sha256 under gzip and zstd | `http-served.txt` (tool `http_served_page.py`) |
| HTTP red case | the same tool against 0.2.24's archived manifest: 7 lines red (run before the version bump, with the package already in place) | `http-served-red-against-0224-manifest.txt` |
| D2 host identity | `--page v21`: problems `[]` (version, page, S-1 shell digest `e35923a0…`, wasm); `--page 0224` refused on all four fields | `identity-*.json` |
| archive | `wasm_sdk_probe/build/archive/host-0.2.25-engine-f5f0df762e1855f2/` (untracked, read-only) | |

Rollback: copy `build/archive/host-0.2.24-engine-d3cd39bbc71ec311/` (without `ATTRIBUTION.md`) to the app's `engine/`, check out host `1479e56`, `ddev occ upgrade`.

**Between 15:40 and 16:36** the package was in place while `info.xml` still said 0.2.24 (the version bump waited for the owner). No measurement ran against the host in that window except the HTTP red case above.

The files `check-relink-queue-red-before-reanchor.txt` and `test-e2-c-static-after-freeze-v74*.txt` are the v74 freeze's witnesses (`4628c9d3`), filed here earlier.
