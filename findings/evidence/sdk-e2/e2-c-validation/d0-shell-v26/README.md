# D0, round two, re-run on shell v26 — 2026-08-22

Same artifact `29ec627b` as the 2026-08-21 round next door; **the artifact did
not move**. What moved is the shell: finding 066's fix touched
`web/e2-editor-app.js`, the bundle's entrypoint, so the bundle digest went
v25 (`07143f961d82c4b3…`) → v26 (`b25b6c29d1e74012…`) and the matrix's fifth
binding was re-stated with a `refreezeLog` entry.

## Result

| | Chrome | Firefox |
|---|---|---|
| `pass` | **true** | **true** |
| `problems` | `[]` | `[]` |

Judged by `tools/analyze_e2_c_d0.py` against `e2/validation-matrix-v2.json`, not
by reading the raw output.

## Why this is a separate directory, and why that is a question and not an answer

The tree's convention namespaces D0 evidence by **artifact**
(`e2-editor-v3-29ec627b`), and the README of the 2026-08-21 round says so
explicitly: "the namespaces are the artifact, so neither round can overwrite the
other." By that convention this run belongs in the same directory as that one,
written with `--overwrite`.

It was not put there, because `--overwrite` **discards a completed run** and the
run it would discard is the record of what round two was validated on before the
shell moved. Destroying a frozen record is not something to do unattended, and
the operator was away.

So this directory is a deliberate hedge, and it has a cost worth naming: the
canonical location now holds a run made on shell v25 while the matrix binds v26.
**Somebody should settle which of the two is the record**, and either fold this
run into the canonical directory or teach the layout to carry the shell
generation. Nothing measured on 2026-08-22 depends on the answer.
