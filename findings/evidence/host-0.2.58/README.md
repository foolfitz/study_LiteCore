# Host 0.2.58: Calc headers, Calc insert/delete rows and columns, Writer key bursts

Released for the hand-test slot the owner named on 2026-11-05 (option A; CLAUDE.md, the section on cadence, item 1). This is an
uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-05 12:19 +0800.

- The host commit is `0bf488a` (version bump only) on `f56a66e` (0.2.57), branch `host-0.2.58`. The engine is `9e9310e329d23db4`,
  archived in `build/archive/host-0.2.58-engine-9e9310e329d23db4` (not in git).
- Writer runs on `e2-editor-v33` (wasm `444519df`, unchanged) with **shell generation 91**: generation 90 plus the session's
  typed-text merge (`../release-0.2.58/gen-91/`).
- Calc moves from `ods-editor-v5` to **`ods-editor-v6`** (wasm `47e3792c`), and the page now has headers and structure.
- The served delta was measured with the packager's closure before the inputs were written: **5 changed** (the Writer session,
  `ods-editor-app.js`, `ods-editor.html`, the two Calc shell files), 6 added and 6 removed (v5 -> v6), 35 the same.
- The Writer page record is unchanged (same module, same profile). `writerIdentity` generation 91 binds the shell file.

| Read | Result |
|---|---|
| `../release-0.2.58/` (freeze, V0', units, release regression) | generation 91 frozen, `V0_PRIME_HOLDS`, v6 three copies equal; Writer P5/P4/S1/P1/Z/KB hold, F4 24/24, F3 equal; Calc C/CU/cell/range/autosave/P2 and both new P's hold, both browsers |
| `gate` | 39 of 39 (the features' first measurements and reds, and the release regression) |
| `package-run-01`, `delta`, `offline` | packaged in 149 s; `DELTA_HOLDS` with 7 red cases; `PACKAGE_HOLDS` |
| `offline-install-preflight`, `live-preflight`, `install` | `OFFLINE_INSTALL_READY`, `LIVE_PREFLIGHT_READY`, `CANDIDATE_INSTALLED`; documents and locks preserved; unauthenticated routes 401 |
| `files-workflow-01/` | 52/52, both browsers and the read-only user; no owned unlocks, share and user removed, folder 204 |
| `capture-after` | `holds: true`: host `0bf488a` clean, installed 0.2.58, buildId `9e9310e3` in every entry, engine equals the archive, protected documents and lock rows equal the installer's after-state, owned folder 404, temporary user absent |
| `calc-host-arm/run-02` read by `calc-host-arm/read_run.py` | **the new arm, on the user's path**: `H_CALC_HOLDS_PENDING_UNOBSERVED`. Headers 135/135 (Chrome) and 125/125 (Firefox); structure 18/18 in each |

## The new arm (`calc-host-arm/`)

The host does not frame the page. `EditorController.php` scopes the page's `<style>` with `@scope` and puts the page's body inside
Nextcloud's document, so Nextcloud's global CSS reaches the new DOM header buttons and the context menu. The mirror cannot see
that. `calc_host_arm.py` runs `check_calc_headers.scenario` and `check_calc_structure.scenario` unchanged. The page is opened the
owner's way: admin logs in, the tool's own fixture is PUT into an owned folder, its row in Files is clicked, and the host route
opens it with its lock. Each browser and each arm get a fresh copy. Before leaving, the page's own save is pressed.

- `run-01` is red on the instrument. The readiness wait read `window.__calcEditor.state` without `?.` and threw before the page
  module had run (the screenshot shows the shell with "尚未開啟"). The fix was one line; only this arm was re-run (cadence item 4).
- In `run-02`, P-H1 (every drawn header against the engine's cell geometry, within 0.6 px) holds on the host in both browsers:
  Nextcloud's button CSS does not move or resize the headers. The count differs from the mirror's 145/121 because the host
  viewport shows fewer headers.
- `run-02` P-H5 is red as written in both browsers, on one clause only. `pending` reads `window.__calcEditor.inputState`, which
  the page exposes only with `?diagnostics=1`, and the host route never passes that. The keys did what P-H5 asks: the whole
  column or row is selected, no edit began, and B2 is unchanged. `read_run.py` holds a P-H5 check only when those three clauses
  hold and `pending` is exactly `'no-diagnostics'`. Its red cases: run-01 is red; a copy of run-02 with a real pending entry in
  one cell is red (`H_CALC_RED`). This is a named limit of the host route, not a product reading.
- The arm was not run red first on 0.2.57: that page has no headers, so `headersSupported` never becomes true and the arm would
  time out. The discriminating reds are the mirror tools' own (`../calc-headers/p-red-*`, `../calc-structure/p-red-*`).

Rollback: `host_release.py rollback findings/evidence/host-0.2.58`, with `host-stack/bin` first on PATH, restores 0.2.57's engine
bytes (Calc on v5, generation 90). The host label stays 0.2.58.
