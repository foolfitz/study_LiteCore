# ods-viewer-v3 pre-link preparation, 2026-10-24

Spec: `specs/SPEC-M4-viewer-v3.md` sections 4, 8-9. The owner built the core (K3 green); **the v3 SDK profile has not been linked yet**. Nothing here establishes that form controls can be painted.

## Base pack (E8-prime, read before handing over the link)

`base-pack-check.json`: base `21bec646…`, 39,934,615 B, 1,488 files. The classify() procedure reproduces 9901e9be on gate0 and removes exactly one 35-lang-normalize.conf. Against v1: 0 added, 0 removed, 9 changed, 1,479 unchanged.

`base-pack-reading.json` reads the actual pack/file slices. Against the DB-connectivity diagnostic profile a6390eef, **only `/instdir/program/services/services.rdb` changes**, adding exactly the `libdbalo.a` component with its eight implementations; no old component changes or disappears. Against v1, the other eight differences are the same ones read in SPEC-M4-viewer-v2 section 5.2:

| File | Delta against v1 | Reading |
| --- | ---: | --- |
| services.rdb | +24,954 B | Existing DB-connectivity registrations plus dba (+2,051 B against a6390eef) |
| main.xcd | +11,045 B | The DB-connectivity driver configuration already read in v2 section 5.2; byte-identical to a6390eef |
| calc.xcd / writer.xcd | +1,216 / +1,217 B | Same driver configuration as a6390eef |
| registry_en-US / qtz / zh-TW.xcd | +715 / +1,736 / +1,704 B | Same localized driver configuration as a6390eef |
| mytexts.bau / images_colibre.zip | 0 B | Every contained entry's SHA256 equals v1's; ZIP container differences only |

No font/fontconfig or other file changed. Reading: the base carries the intended DB-connectivity/dba registrations, with no unexpected payload difference.

Controls: `base-gate0-control.json` reproduces v1's 6f7424a1 base with 0/0/0 differences; `base-red-drop.json` deliberately removes main.xcd and the removed list shows exactly that extra file (exit 0 means the *red-case detection* worked).

## New profile identity and rules

- `builder-controls.json`: **synthetic loader/wasm**, packaging only, not an engine. The output identity is ods-viewer-v3, distinct base stem, part-info + form-controls, bits 63539. Wrong worker pin, missing part-info export, and a form-free gate0 core are rejected before creating the output directory.
- `link-token-comparison.json`: Makefile-expanded v2/v3 compile and link commands are identical after normalizing only core/object/export/output paths. Defines and link flags are identical.
- `syntax-v3.json`: all three Makefile-expanded compilation commands pass `-fsyntax-only` against the new core's headers; no object files written.
- `carrier-red-without-v3.{json,txt}`: without the new carrier declaration, the existing check fails on exactly v3's sdk_api/probe_engine objects. The Makefile now declares those two; the checker itself is unchanged. This is an additional profile binding, not a repaired check.
- `test-e2-c-static.txt`: `make -k test-e2-c-static` exit 0. Includes 490 + 5 Node tests, the 31-rule/121-object scope census and its guard controls, existing Python tests, and the read-only E1-C check. The reported unbuildable finding-012 diagnostic variant is pre-existing and accepted by that check.
- `viewer-unit-tests.txt`: session, SDK and worker tests, **57/57** pass.
- `core-provides-calc.txt`: existing core-capability check passes for this core.
- `gzip-recipe-control.txt`: the exact new Makefile gzip recipe runs successfully against the old v2 wasm by replacing only its input path, measuring 47,971,896 B. This checks the quoting of the closing command; it is not v3's measured size.

The engine source tree is byte-identical to source revision 2430916d recorded in the aa576ce7 archive. No engine or shell source was changed for this link.

## Frozen artifacts and next step

`archive-before-link.json` identifies the fresh backup in `wasm_sdk_probe/build/archive/before-ods-viewer-v3-…/`: all local files of editor e2-editor-v22 and viewer ods-viewer-v2, plus all manifest-referenced artifacts/resource packs (16 files, 388,892,439 B), preserving paths. Every copy was hashed against its source, then `sha256sum -c SHA256SUMS` was run; output is `archive-verification.txt`.

`frozen-set-before.sha256` records all current `dist/profiles` and `build/archive` files, including the backup. After linking, every listed file must still hash identically; v3 may add its own files. The manifest did not yet exist at this snapshot. `pre-link-summary.json` records the file count and completed checks.

Owner: `bash handoff/ods-viewer-v3/link.sh` from the repo root (a few minutes). Runbook: `handoff/RUNBOOK-link-ods-viewer-v3.md`. Stop on a failure or actual viewer gzip above 52,428,800 B. Then Codex verifies and archives the new identity and proceeds to the pinned Phase E, always with an explicit output directory. The installed host/package and ddev remain untouched.

Section 34.4: +0 / +0 (because of execution / because of review), cumulative 46 / 27. No existing checker was changed.
