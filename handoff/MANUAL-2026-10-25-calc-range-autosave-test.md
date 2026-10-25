# Owner manual test fixture

This file was created on request to guide the owner through manual testing after host 0.2.37 installation. It is owner-controlled and must not be deleted, reset or restored by automated cleanup. Passing manual acceptance has not yet been reported.

```json
{
  "folder": "LiteCore Calc 手動驗收 2026-10-25 203756",
  "path": "LiteCore Calc 手動驗收 2026-10-25 203756/多格格式與自動儲存.ods",
  "fileId": 25391,
  "editorUrl": "https://litecore.ddev.site:8443/index.php/apps/litecore/r/ods-editor.html?fileId=25391",
  "initialSha256": "7210d8a664a82fd660db06feb004cb52c8f7dd57b0a7f7461b7d416e89d756b2",
  "ownership": "Owner manual test document. Preserve after owner edits; not an automated cleanup fixture."
}
```

Use the normal admin account. Cell B2:C2 is suitable for range B/I/U and B2 for confirmed-value autosave. A2 and the other sheet are preservation controls. Service was already running; no service lifecycle command was executed.

## Owner feedback

The owner reported the preceding functional tests passed on 2026-10-25. Their screenshot used a document named M4 檢視 測試 plain.ods; the exact manually used file is not inferred to be fixture25391. All owner documents, including25391, remain protected. A separate dark-host inline text contrast issue was reported and handled as a CSS-only correction.
