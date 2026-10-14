# N7(b)'s red case: a blank document whose manifest is missing is refused, and leaves no file

Taken 2026-10-14 03:19Z by `wasm_sdk_probe/tools/check_m3_new_document.py --red-corrupt` on host 0.2.19
(afbaf3c) on the dev instance `litecore`, as admin (language zh_TW, no locale).

What it did, in order:

1. `DELETE` any earlier `新文件 紅案-壞範本.odt`; PROPFIND confirms absence.
2. Renamed `blank/MANIFEST.json` in the host repo (the instance serves the repo through `nc-link` symlinks,
   so the app saw it vanish at once).
3. `POST /ocs/v2.php/apps/files/api/v1/templates/create` with `templatePath ""` (a blank document).
   Answer: **403**, message `無法從範本建立檔案` (core's own "Failed to create file from template").
4. PROPFIND of the name: **no file** (`fileid` null); a Depth-1 listing of the root shows no `新文件 紅案*`.
   The listener removed the empty file core had created before rethrowing (`FileCreatedFromTemplateListener`).
5. Restored the manifest (sha256 equal to the recorded `e5cdb8e2…`); `git status` clean.
6. Positive control right after: the same request answers 200 and the created file is byte-identical to
   `en-US_zh-TW_A4.odt` (3,940 bytes, sha256 `7e6221b6…`), then deleted.

Files: one JSON per take; `red: true` means refused AND no file AND manifest restored.
