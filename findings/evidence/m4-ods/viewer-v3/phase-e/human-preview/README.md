# V3-SEE human preview, 2026-10-24

URL and exact identities: `preview.json`. Local server `127.0.0.1:8794`, mirror in `wasm_sdk_probe/build/ods/viewer-v3-human/root/`. The product page uses ods-viewer-v3 (ebb7e0cb); only the mirror's HTML adds a visible identity banner and a local load-only host for tdf134161.ods (101 controls). No ddev is used and no dist file is changed.

Before handing this URL to the owner, a fresh headless browser opened it: `page-state.json` confirms the v3 worker, exact fixture SHA256, ready spreadsheet state, opened event and drawn tiles. `preview.png` is that browser's screenshot. This is a preflight for the owner's observation, not a substitute for it.

**Human confirmation pending.** The owner was asked to inspect the document and report whether controls are visible. Record their exact answer and this page/profile identity before claiming V3-SEE. The automatically verified open/tiles do not settle that criterion.

The server PID is recorded in preview.json; stop only that server when the preview is no longer needed. Leaving this preview available does not occupy ddev.

## Owner confirmation, 2026-10-24 (supersedes pending statements above)

The owner confirmed both the green identity banner and the small box in the yellow cell. V3-SEE holds; the exact original answer and its translation are in `human-preview/owner-confirmation.md` (or `owner-confirmation.md` from the preview directory). All pinned Phase E requirements are now met with the existing Basic UDF limitation retained. Host 0.2.33 packaging is the next step; installation remains unperformed.
