# Host 0.2.26 (2026-10-17)

Host 0.2.25 plus one CSS rule for finding 154 (fable ruling 3, spec §12.5). The engine package is the one 0.2.25 carried: engine v21 (item 1 only) and shell generation v74.

| what | value | file |
|---|---|---|
| host commit | `3c01876`: `appinfo/info.xml` 0.2.25 → 0.2.26, and `templates/editor.php` `#litecore-editor-root dialog:not([open]) { display: none; }` in the host's own `<style>`, with its comment | |
| install | `ddev occ upgrade` (run by the session on the owner's typed command); `app:list` 0.2.26, `needsDbUpgrade` false, debug false | `package-unchanged.txt` |
| engine package | unchanged: `engine/MANIFEST.json` sha256 `54bebc4de343526b…`, `diff -rq` equal to `build/archive/host-0.2.25-engine-f5f0df762e1855f2/` (ATTRIBUTION.md only); buildId `f5f0df762e1855f2` | `package-unchanged.txt`, `check-engine-decoded.txt` |
| HTTP | entry 303 → address `f5f0df762e1855f2-90d7bc2c` (as on 0.2.25; the app version is not part of the address); page `605cf24b…`, worker `0d55bcfa…`, wasm `db3408f5…` decode to the manifest's under gzip and zstd | `http-served.txt` (tool `../host-0.2.25/http_served_page.py`) |
| the fix | acceptance met in both browsers (spec §12.5 (c′)) | `../154/0226/` |
| D2 | PASS 6/6 (spec §12.5 results) | shakedown README §5.10 |

No separate archive: the package is byte-equal to the 0.2.25 archive. Rollback to 0.2.25 = host `03970d0` + `ddev occ upgrade`; to 0.2.24 = see `../host-0.2.25/README.md`.
