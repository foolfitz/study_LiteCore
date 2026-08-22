# D0, round two, re-run on shell v27 — 2026-08-22

Artifact `29ec627b` unchanged again; the shell moved because finding 067's fix
touched `web/e2-editor-app.js`, the bundle's entrypoint, for the second time in
one day. Bundle v26 (`b25b6c29d1e74012…`) → v27 (`55a91f837f210e8e…`), and the
matrix's fifth binding was re-stated with a third `refreezeLog` entry.

| | Chrome | Firefox |
|---|---|---|
| `pass` | **true** | **true** |
| `problems` | `[]` | `[]` |

Judged by `tools/analyze_e2_c_d0.py` against `e2/validation-matrix-v2.json`.

Same namespace question as `../d0-shell-v26/`, and the same answer: this is a
separate directory rather than an `--overwrite` of the canonical one, because
`--overwrite` discards a completed run. **There are now three D0 records for one
artifact** (v25's under `d0/`, v26's, and this one), which is a sign the layout
should carry the shell generation rather than accumulating siblings. That is a
decision for a person, and nothing measured today depends on it.
