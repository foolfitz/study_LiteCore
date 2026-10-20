# O3: the `ods-viewer-v1` rule, its builder, and the gates before the owner's link

Spec: `specs/SPEC-M4-ods-in-nextcloud.md` addendum 4. Runbook: `handoff/RUNBOOK-link-ods-viewer-v1.md`.
Nothing was linked and no make target that compiles was run; `make -n` (a dry run) and `make -k
test-e2-c-static` (a static target with no compile, checked by its own `make -n`) were.

## What landed

- **Makefile block `ods-viewer-v1`** (after e2-editor-v14's): objects `sdk_api`, `probe_engine`,
  `unoembind_stub` compiled with `$(E2_V5_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_READER_PROFILE
  -DOXSDK_ODS_VIEWER`; the export list from `$(E2_V5_CORE)`'s own core export list (byte-identical to
  the writer core's, `e9b54133`) plus the reader's symbols without save and the viewer's four, refused
  if it carries save or an editor symbol; v14's link line with the 1 MiB stack, guarded by
  `refuse_unasked_relink`; the packaging rule (worker pin `d1de2dfd…`, the builder's `--check`, the
  builder, and three greps on the wasm: `search-result` present as the positive control, `partBefore`
  present, the editor's `verified-caret-readback` absent; the manifest removed on failure).
- **`tools/build_ods_viewer_profile.py`**: the base pack (e2-editor-v14's `9901e9be` minus
  `35-lang-normalize.conf`, from `9901e9be`'s data and from the a11y core's original image by its
  offsets, the original first required to reproduce `9901e9be`; same sha both ways), the shipping
  `cjk-sub-e10` and `fallback-fonts-r5` by path, the reader-shaped manifest (capabilities and bits as
  `sdk_api.cpp` reports under the define; no editor contract), and checks on the export list.
- **The viewer's `#error`** now refuses `OXSDK_MERGE_KEY_UNDO` and `OXSDK_FINDING_016_SELECTION_BARRIER`
  as well (`syntax-checks.txt`).
- **`tools/check_merge_key_undo_scope.py`**: the compile guards per carrier (`guard_variants`), see below.

## The gates (each file here)

| gate | file | result |
| --- | --- | --- |
| link line vs v14's | `link-token-diff.txt` (from `make -n`, `make-n-ods-viewer-v1.txt`) | 4 differences: objects, stack token, export list path, output path |
| undefined symbols | `undefined-symbols.txt` | the viewer's objects (compiled to scratch with the rule's flags) need 3 symbols v14's link did not resolve from the core: `condition_variable::notify_all`, `to_string(int)`, `tolower` -- emscripten's libc++ / libc |
| syntax | `syntax-checks.txt` | the three units, viewer defines: exit 0, 0 warnings; adding B, the barrier, or dropping the reader define: refused by the viewer's `#error` |
| the builder | `builder-check.txt`, `builder-red-drop.txt` | `base-a11y-no35.6f7424a1c1427ad7.data`, 39,892,028 bytes, 1,488 files, same sha from the original image; dropping one more file is red in both reconciliation lines |
| the core provides Calc | `core-provides-calc-a11y-gate0.{txt,json}` | exit 0 on `build-a11y-gate0`; exit 1 on `build-headless-probe` (the negative control, not kept) |
| core link inputs not newer than v14's link | (printed) | `0` |
| `make -k test-e2-c-static` | `test-e2-c-static-red-viewer-not-declared.txt`, `test-e2-c-static-green.txt` | red before the viewer was declared (its two objects differ from `5d77dc84`); then red on the new guard (below); green, exit 0, after both fixes: 29 rules, 115 objects, 13 declared differences |
| the frozen set | `frozen-set-before.sha256` | 1,430 files under `dist/profiles/` and `build/archive/` |

Measured once, not a gate: the base pack compresses to 5,649,371 bytes with zstd -19 and 7,567,047 with
gzip -9 (the editor's `base-r5-no35`: 5,530,574 with zstd -19). The review's C1 had estimated about 6.5 MB.

## M1-1 and the viewer (a check changed, with its witness)

`test-e2-c-static` runs M1-1 (`check_merge_key_undo_scope.py --base 5d77dc84 --carrier …`): every object
of every `$(X_BUILD)/%.o` rule must preprocess as at `5d77dc84`, except the carriers' declared objects, and
each carrier's `probe_engine` must refuse two compile variants (B with the main-loop engine, B without the
selection barrier). The viewer's rule entered that population with the Makefile block.

1. **Undeclared**, the line was red on exactly the viewer's two objects (the witness,
   `test-e2-c-static-red-viewer-not-declared.txt`). Declaring it as a carrier is the precedent (v20, v21,
   v22 were declared the same way).
2. **Declared**, it was red on the second B guard: removing the selection barrier from a rule that never
   had it changes nothing. B's guards mean something only for a carrier of B.
3. **The change** (`guard_variants`): a carrier whose compile command defines `OXSDK_MERGE_KEY_UNDO` keeps
   both B guards; a carrier without it must refuse `-DOXSDK_MERGE_KEY_UNDO` (B cannot be compiled into it).
   A B carrier that loses its define falls in the second branch and is red there. Three offline tests in
   `tests/test_merge_key_undo_scope.py` (22/22).
4. **The new guard was red on the viewer**: B's own `#error` sits inside an editor `#ifdef`, so in the
   reader shape B was inert, not refused. The viewer's `#error` now names B and the barrier, and the line
   is green.

§34: one check changed because of execution, with the witness above; nothing because of review.
