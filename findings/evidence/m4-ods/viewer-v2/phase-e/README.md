# Phase E on ods-viewer-v2 `a6390eef` (the DB-connectivity core), 2026-10-22

Mirror only, no ddev. `run_ods_viewer_phase_e.py --profile ods-viewer-v2`.

| report | staged | result |
| --- | --- | --- |
| `report-2026-10-21T180920Z.json` | the ladder (9) + `fdo67682-2` (157) + `date-time-functions`, `functions` (159) + the five form-control files (158) | E1, E3, E4a, E5, E6, V2-157, V2-160 PASS; **E2 and V2-158B FAIL on all five form-control files** |
| `report-2026-10-21T181049Z.json` | the ladder controls + `tdf138507` (a form without a control; v1 opens and paints it) | **E2 FAIL on tdf138507** (a regression against v1); V2-158B has nothing staged |

What holds on this link:

- **157:** `fdo67682-2.ods`'s twelve hidden parts are `partVisible: false`, their tabs disabled, `showPart` refused `PART_HIDDEN` with 0 switches reaching the handle (V2-157, E5).
- **159:** E3 is green on `date-time-functions.ods` and `functions.ods` -- the add-in cells now match the native oracle.
- **160:** 49 reads, 0 unconfirmed, wait max 122 ms (p99 122), 0 late results.

What fails, and why (read in the source, SPEC-M4-viewer-v2 §7):

- The five form-control files and `tdf138507.ods` do not load: `loadComponentFromURL returned an empty reference`, with the engine's stderr showing `RuntimeException: unsatisfied query for interface of type com.sun.star.uno.XAggregation!` from the XML parser, then `SAX parse exception caught while importing`.
- `forms/source/component/DatabaseForm.cxx:358`: `ODatabaseForm`'s constructor aggregates `com.sun.star.sdb.RowSet` with `UNO_QUERY_THROW`. That service is dbaccess's (`dbaccess/util/dba.component`, `com_sun_star_comp_dba_ORowSet_get_implementation`), and dbaccess is stripped on wasm (`ENABLE_WASM_STRIP_DBACCESS`); the v2 core's constructor list has 0 `ORowSet`. Every `<form:form>` therefore throws during import. On v1's core the forms service did not exist at all, so the import skipped the form and the file loaded (and then could not paint a control: finding 158).
