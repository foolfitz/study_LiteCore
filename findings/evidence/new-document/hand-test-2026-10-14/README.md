# Owner hand test of host 0.2.19 "New document", 2026-10-14

The owner used `https://litecore.ddev.site:8443` with host 0.2.19 (`afbaf3c`), the uncounted candidate: Files, "+ New → 新文字文件", then typing, saving and reopening. The owner's verdict: 「應該是通過」. The owner downloaded the two saved files, one saved from Firefox and one from Chrome, and the main session read them from copies in its scratchpad.

**The documents are not committed.** They contain the owner's own interview notes, which name a person. Only the values below are recorded.

| | saved from Firefox | saved from Chrome |
|---|---|---|
| size | 24,617 bytes | 24,584 bytes |
| mimetype | `application/vnd.oasis.opendocument.text` | same |
| generator | `LibreOfficeDev/26.8.0.1.0$Emscripten_x86` (the WASM engine) | same |
| `styles.xml` sha256 (first 16) | `5addf7dcead9b62c` | `5addf7dcead9b62c`, **byte-identical** |
| default paragraph style: Western / Asian / Complex language | en-US / zh-TW / hi-IN | same |
| default paragraph style: fonts | Liberation Serif / Noto Sans CJK TC / Liberation Sans, 12pt | same |
| page | 8.2681in x 11.6929in (= 21.0 cm x 29.7 cm, **A4**) | same |
| text | the owner's Chinese text, saved and present after reopening | same |

These match `specs/SPEC-M3-new-document.md`'s expectation for a zh_TW user. They also match the counted run `runs/2026-10-14T035226Z.json`: across two browsers the saved `styles.xml` is byte-identical, so the browser language does not reach a new document. The page size is written in inches because the engine's measurement unit is en-US. The value is A4.
