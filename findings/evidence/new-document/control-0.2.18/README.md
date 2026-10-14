# N1's red case: the creator list on the installed host 0.2.18 (SPEC-M3-new-document N1 紅案)

Taken 2026-10-14 03:18Z by `wasm_sdk_probe/tools/check_m3_new_document.py --control`, BEFORE the upgrade to
0.2.19, on the real 0.2.18: the host repo checked out at `96a87d8` (clean), the dev instance `litecore`
reporting `installed_version` 0.2.18.

`GET /ocs/v2.php/apps/files/api/v1/templates` as admin listed one creator, the `text` app's
(`文字文件`, `.md`, 3 user templates) and **no creator with `app === "litecore"`**. So on 0.2.18 Files'
"+ New" menu has no "New document" entry, which is what the owner reported on 2026-10-13.

The same listing on 0.2.19 (afbaf3c, after `occ upgrade`) adds
`{"app": "litecore", "label": "新文字文件", "extension": ".odt", "mimetypes": ["application/vnd.oasis.opendocument.text"], "templates": 11}`
(the 11 are the admin's own `.odt` files in their Templates folder; see the shakedown reports).

Files: one JSON per take, `red: true` means "no litecore creator".
