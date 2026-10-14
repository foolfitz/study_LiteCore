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
