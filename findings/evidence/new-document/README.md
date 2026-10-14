# new-document: "+ New -> New document" in Files, with a blank document that states its defaults

Spec: `specs/SPEC-M3-new-document.md` (zh-TW). Task: `handoff/tasks/TASK-2026-10-14d-new-document.md`. Host: `~/Projects/Nextcloud_Apps/litecore` 0.2.19 (`afbaf3c`).

| path | what |
| --- | --- |
| `brief-1-default-language-and-fonts.md`, `analysis-1.md` | the question and fable's analysis (2026-10-14): a style-less ODT is Letter, browser-dependent Asian language, `Noto Sans CJK KR`; option A chosen by the owner |
| `probe-1-native-defaults/` | the analysis' seven native arms (LibreOfficeKit load + save of richdocuments' style-less template) |
| `native-roundtrip/` | **N11**: native 26.8 round trip of four generated templates under `LANG=en_US` and `zh_TW`, 8/8 keep every stated default; the richdocuments control shows the zh-CN/zh-TW leak |
| `control-0.2.18/` | **N1's red case**: the creator list on the installed 0.2.18, taken before the upgrade -- no `litecore` creator |
| `red-corrupt/` | **N7(b)'s red case**: with `blank/MANIFEST.json` hidden, creating a blank document is refused (403) and leaves no file; manifest restored; positive control 200 |
| `shakedown/` | the runner's shakedowns (do not count); the first full one (`…032312Z`) is where the two instrument faults recorded in the spec's section 4 were found |
| `runs/` | the counted run(s) of `wasm_sdk_probe/tools/check_m3_new_document.py --label counted` |

The generator is `wasm_sdk_probe/tools/make_new_document_templates.py`; the templates it made are the host's `blank/` (30 files, `MANIFEST.json` sha256 `e5cdb8e2…`). `--check` regenerates in memory and compares byte for byte; `--validate` runs odfvalidator on the set (30/30 pass; richdocuments' template fails on the mimetype entry's extra field). `check_new_document_choice.py` is N12 (the host's `BlankDocument::choose()` called through `php -r`, 174 inputs, closed both ways).

## Review before the count (2026-10-14, §34.3), appended

`review/`: the brief (`../REVIEW-BRIEF.md`), the two seats (`opus-review.md` with `opus-experiments/`, `codex-review.md`), the disposition (`DISPOSITION.md`, one row per seat item) and the red demos (`demos-before-after.py` → `demos-before-after.txt`: each mutation scored by the tool at `3b818514` and by the tree's tool; then every committed report by both, no verdict moved). Ruled by fable on the owner's behalf (task 10-14j, part J2). This was the tool's one review; §34.4: repaired because of review = 1 tool / 10 fixes, because of execution = 0.

What changed in `wasm_sdk_probe/tools/check_m3_new_document.py` (unit tests: `wasm_sdk_probe/tests/test_check_m3_new_document.py`, 19; red cases 30 → 39, each must go red on the rule its name starts with):

- N4: the saved paragraph sequence is exactly `["zqx"]` (was: contains it once); both generations must have been read.
- N5: the reopen lands on N2's fileid; `data-offers` must be `"0"` or `"1"`, anything else is "not read", not `NOT_OFFERED`.
- N8: the other user's share permissions carry no `CK`.
- No mode prints `WORKS` with zero runs or a `stopped` run.
- Settings: a setting that cannot be read refuses the run (exit 2) instead of being taken as "not set" and deleted at the restore; the restore's `ok` needs occ exit 0, a successful readback and equality, both keys are always attempted, SIGTERM reaches the restore; the runner waits for other runners (including another instance of itself) before reading the owner's settings.
- N9 for the count: the "0.2.19 changed only the host" clauses (engine and page equal to 0.2.18's, host diff within the allowed paths) run only on a report whose host is 0.2.19 and are frozen there; the count binds the candidate (`ENGINE_BUILD_ID`, `PAGE_SHA256`, `None` until the binding step writes them, so an unbound count reads "binding not written"). `--red-corrupt` records `hostCommit`; N7(b) is inherited while `lib/Listener/`, `lib/Template/`, `blank/` are unchanged since it.

Corrections to what the 0.2.19 acceptance measured (spec §7.5): `servedPage` is the manifest's declared hash, not an HTTP read; `engineFiles` was recorded, not compared; the host's `engine/` is gitignored; N5's byte half shows the host handed the marked bytes to the page, not what the engine loaded; the red-case count in §7.1 was 30, not 29.
