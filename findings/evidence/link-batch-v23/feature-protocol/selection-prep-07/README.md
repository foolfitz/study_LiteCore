# Selection collector preparation 07 (uncounted): first Firefox execution

The first Firefox execution of tonight's selection instrument: the place-caret route reader, paint digests and their export wait under WebDriver, the shared drag witness, the collapsed-shape anchor, A′ table selection and S4. It is uncounted, uses `--keep-going` and runs 13 cells covering every path. Receipt `runner.command.json` (exit 0, 448 s, about 34 s per cell). The foreign CPU guard passed; `postConfig` equals `config`; the user agent is Firefox.

All 13 PASS:

- S1/S2: `shift-Right@caret-mid`, `shift-Down@caret-mid`, `shift-End@wrap-line-end` (also S3), the drag `shift-Right@range-bwd`, `shift-Right@empty-para`, `shift-Left@cjk-mid` and `shift-Home@doc-start` (also S3).
- S2 only: the keyboard range `plain-Down@range-kbd`.
- Table-selection members: `shift-Up@cell-end` and `shift-Down@list-mid`. Firefox's selected text equals the three agreeing native rounds, including the table jump that ends mid `Final paragr`.
- S4: click with Shift+Home, drag, and public range selection.

Cells are 0.5–1.7 MB with paint digests. Raw cells are stored as deterministic `.json.gz`. This preparation establishes no group; it is the reviewer's recommended Firefox check before the first counted run.
