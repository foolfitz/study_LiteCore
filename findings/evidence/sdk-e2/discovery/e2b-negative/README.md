# SPEC E2-B 5.10: the negative matrix

**Date** 2026-08-15. Artifact `572035ac…` (product v2), both browsers, one round
each — negative rows are deterministic refusals, so 5.10/7.1 registers one round
per browser rather than three.

## Verdict: 12 rows, both criteria, both browsers

Every row must satisfy **two** things, and the second is the one with teeth:

1. the refusal carried a code the row registered **in advance**, and
2. **the document did not change** — `<office:body>` compared **byte for byte**
   between a save taken before the attempt and one taken after.

A row that only checked the code would pass just as happily if the engine had
refused loudly and mutated anyway.

| row | what one thing was changed | refused with |
|---|---|---|
| **N1** | manifest no longer lists `set-list-ordered` | `UNSUPPORTED_OPERATION` |
| **N2** | capability `narrow-editor-v2` withheld | `UNSUPPORTED_OPERATION` |
| **N3** | `editorContract.version` set to 1 | `UNSUPPORTED_OPERATION` |
| **N4** | `abiVersion` says 3, the binary reports 2 | `INCOMPATIBLE_ABI` |
| **N5** | a v2 action id sent to the **v1** profile | `INVALID_ARGUMENT` |
| **N6** | an action name outside the closed set | `EDITOR_ACTION_UNSUPPORTED` |
| **N7** | `extendSelection: true` on a paragraph action | `INVALID_ARGUMENT` |
| **N8** | a stale `expectedRevision` | `STALE_REVISION` |
| **N9a/b/c** | `unoCommand` / `keyCode` / `command`, one at a time | `INVALID_ARGUMENT` |
| **N11** | manifest withholds the crossing gesture | `EDITOR_FORMAT_GESTURE_UNSUPPORTED` |

Chrome and Firefox identical. Zero mutation proven on bytes for every row that
opened a document; N4 never opens one, and that is recorded as its reason rather
than left implicit.

## The three rows that are new, and why they matter

**N1 proves the manifest constrains rather than describes.** Before this
contract the worker dispatched from its own hard-coded map and never read
`editorContract.actions`, so removing an action from a manifest changed nothing.
The freeze condition "withhold a capability and prove zero mutation" was
unsatisfiable by construction.

**N4 proves a manifest cannot lie about its binary.** The editor ABI had no
runtime consumer at all: a profile could claim any `abiVersion` and a stale wasm
beside a fresh manifest would run with nobody the wiser — which is findings
027/036's failure mode, made unreachable by one exported symbol.

**N11 is the only row in the matrix that tests a gesture limit**, and without it
a partial GO that restricts a gesture would be expressible in the manifest and
unenforceable at runtime. It is also the row that exercises **disposition A**:
the refusal branch and the B' branch are the same mechanism, and this is the
evidence that the refusal half works.

## Two design faults this run found in its own rows

**N5 did not test what it claimed.** Aimed at the v2 profile it observed
`UNSUPPORTED_OPERATION` — correctly, because a v2 profile does not declare
`narrow-editor-v1`, so the capability gate refused before the action map was
consulted. That is a true refusal, but it is N3's refusal. The row was re-aimed
at the **v1** profile, which is the only place "a v1 build rejects a v2 action
id" can be shown.

**The attribution check then fired on N5**, because it drives a different
profile from the one the runner hashed. That is the check doing its job
(finding 027: evidence filed under an artifact that never ran it). Rather than
loosening it, the row now **declares** `crossProfile: true` and only undeclared
mismatches are flagged — a check that cries wolf on a legitimate row is a check
people learn to ignore, and then a real misattribution walks through.

## The judge can fail

Mutation control: replacing one passing row's *after* document with a different
one makes the analyzer report
`N1: the document CHANGED despite the refusal` and exit non-zero; restoring it
returns exit 0.
