# Selection collector preparation 04 (uncounted): table census, export overflow

Uncounted Chrome preparation with the new preparation-only `--keep-going`, over the seven table-involved Shift members that preparation 03 had not measured. Receipt `runner.command.json` (exit 1 because four cells were nonpassing, 337 s). The executed runner is committed together with this directory; its hash is in `report.json` `config.instrumentSources`. `postConfig` equals `config`.

## Results against the preparation-03 prediction

| Member | Reader | Candidate (Shift) | Reference (plain) | Native (3/3 rounds) | Prediction |
| --- | --- | --- | --- | --- | --- |
| `shift-Down@cell-end` | S1 FAIL `moving endpoint differs from independent control`; S2 PASS | `A1 cell text\nA2 cell text\n`, caret (1418, 4896) | (2537, 4896) | same text, cursor (1418, 4894) | false, confirmed |
| `shift-Right@cell-end` | S1 FAIL `anchor/moving endpoints not uniquely witnessed`; S2 PASS | `A1 cell text\tB1 cell text\n`, caret (6403, 4620) | (6403, 4620) | same text, cursor (6403, 4618) | false, confirmed (different failing clause: the caret matches, but a whole-row table selection has no text anchor/moving pair) |
| `shift-Down@list-mid` | S1 FAIL `moving endpoint differs from independent control`; S2 PASS | jumps the table, caret (2584, 5172) | (2537, 4620), inside A1 | cursor (2584, 5170) | false, confirmed |
| `shift-Home@cell-end` | PASS | `A1 cell text` | | `A1 cell text` | holds, confirmed |
| `shift-End@cell-end` | PASS | `` | | `` | holds, confirmed |
| `shift-Left@cell-end` | PASS | `t` | | `t` | holds, confirmed |
| `shift-Up@doc-end` | instrument fatal (no page) | | | | not measured |

Together with preparation 03, four of the five predicted members are measured: in every one the product reproduces native Writer's table/cell selection, and the S1 premise "Shift endpoint = same-browser unshifted endpoint" is false. The three within-cell members hold. In all seven completed cells, S2 is clean. The S1 disposition remains an open decision; no criterion has been changed.

## The doc-end fatal: page export overflow

`chrome-shift-Up@doc-end.json` holds only `fatal`/`exportFailure`: `export_page` got no `length` because `JSON.stringify(window.__featureSelection)` failed in the page. The other cells' exports were 295–373 MB, and 99.8% of every cell is `paint` responses (each a full 900×1153 RGBA page bitmap, 4,150,800 bytes, about 65 per cell). Shift+Up from the document end selects the whole table, which plausibly triggers more paints and pushes the record past V8's single-string limit. The browser was closed before the record could be recovered, so that size is inferred, not measured.

At this size a 216-cell qualifying run would also need about 80 GB of raw files, against 63 GB free on this disk.

Disposition (next commit): the observer keeps each paint bitmap's length and SHA-256 instead of its bytes. No reader predicate reads bitmap content. Every other paint field is kept, as is every other message, including save bytes. The reader refuses a paint response whose digest is missing or incomplete. Raw cells here are stored as deterministic gzip (`.json.gz`, each equal before compression and after decompression).
