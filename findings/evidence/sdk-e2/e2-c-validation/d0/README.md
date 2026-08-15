# E2-C phase D0 — entry inventory and surface

**Artifact**: `e2-editor-v2`, wasm `572035ac…`, loader `cdb7c843…`, worker `c01f1f2f…`,
shell bundle `b01d77da…` (`e2/editor-shell-v2-bundle-v1.json`).
**Criteria**: `e2/validation-matrix-v1.json`, frozen 2026-08-15 **before this ran**.
**Date**: 2026-08-15. **Browsers**: Chrome and Firefox, one round each.

## Result

**Both browsers pass all nine D0 cells, and their projections are identical
for all fifteen actions.**

| cell | Chrome | Firefox |
|---|---|---|
| `d0-inventory` | pass | pass |
| `d0-reachability-single-client` | **15/15** | **15/15** |
| `d0-reachability-control-undeclared` | pass | pass |
| `d0-session-opens` | pass (`ready`, 1 client replacement) | pass |
| `d0-no-diagnostic-surface` | pass (`editorActionV1` → `UNSUPPORTED_OPERATION`) | pass |
| `d0-forbidden-keycode` | pass (`INVALID_ARGUMENT`, body unchanged) | pass |
| `d0-forbidden-unocommand` | pass | pass |
| `d0-forbidden-command` | pass | pass |
| `d0-unknown-action` | pass (`EDITOR_ACTION_UNSUPPORTED`, 0 dispatched) | pass |

## What "15/15" means here, precisely

It is **one client** — `editor-shell-v2/narrow-editor-v2-client.js` — reaching every
action the manifest declares, on the real engine, through the worker. Not the union
of the shells in the tree: that union is what hid the gap for a whole release
(SPEC E2-C 2.2), and it is why this cell is specified as a single client.

For every action the analyzer checks the **whole request envelope**, not that a
request went out:

* the operation is `editorActionV2`;
* `action` matches what was asked for;
* `expectedRevision` equals the `beforeRevision` the result reports;
* `extendSelection` is false, and `enabled` is true for exactly the four inline
  formats and false for everything else;
* no `keyCode`, `unoCommand`, `command` or `method` field is present.

and the **typed postcondition per action class**, which is where the two contracts
stay separate:

| class | completion | `changed` | revision |
|---|---|---|---|
| character movement | `documented-callback-*` | `false` | unchanged |
| delete | `verified-selection-delete` | `true` | +1 |
| break, inline format | `uno-command-result` | `true` | +1 |
| the five paragraph actions | `verified-format-readback` | `null` | +1 |

A wrong `enabled` is a bold button that unbolds, and a delete accepting route C's
shape is finding 022's silent no-op coming back through the new door. Both would
look like "a request went out".

## Zero mutation is judged on bytes, not on the refusal code

The four refusal cells save the document before and after the attempt, and the
analyzer compares `<office:body>` byte for byte (not `content.xml`: automatic
styles renumber and meta carries timestamps). A cell that only checked the code
would pass just as happily if the engine had refused loudly and mutated anyway.
Same criterion the E2-B negative matrix used.

## The analyzer says no when it should

`python3 tools/analyze_e2_c_d0.py --self-test <evidence>` applies **11 mutations**
to a passing result and requires every one to turn the verdict red: a wrong wasm
hash, a missing action, a wrong `enabled` flag, a v1 completion on a paragraph
action, route C's shape on a delete, an accepted undeclared action, an accepted
`editorActionV1`, a session that did not open, an accepted forbidden field, a
dispatch hiding behind a refusal, and a broken attribution. 11/11 go red.

## Files

```
<profile>-<wasm prefix>/<browser>/result.json   the observations, as the page recorded them
<profile>-<wasm prefix>/<browser>/page.log      the page's own log, line per step
<profile>-<wasm prefix>/<browser>/saved/*.odt   eight saves: before and after each refusal cell
```

`result.json` carries `attribution`, which compares the hashes the page read out
of the manifest against the hashes the runner computed from the profile on disk.
Both browsers: consistent. Evidence filed under an artifact that never ran it is
finding 027's failure mode.

## What D0 does not say

D0 is reachability and surface. It does **not** show that any action put the right
thing in the document — that is D1, which checks each action against its own anchor
in the saved ODT, because all four inline formats return the same completion and a
mapping error would report the action name it was asked for.
