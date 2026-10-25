# Actual Files range and autosave acceptance

The executable population is derived by `read_calc_range_autosave_host.required()` from the new driver plus its inherited setup and read-only routes. The initial population is 54 checks. Specification section 20 was committed before execution. This is one finite run containing Chrome and Firefox, each with an owned editable fixture and an owned read-only share. It does not restart the closed mirror/browser N=3 gates.

Run only after the coordinator has installed and verified the candidate through the existing guarded package procedure and recorded fresh `ddev-before.json`, `locks-before.txt`, and `owner-document-before.json` under `findings/evidence/host-0.2.37`. The driver does not start services, install packages, or change the lock table. It creates a temporary folder, user, share, and documents, and releases only its own document locks. Preserve the unrelated lock on file 24674 and document 24920.

From the repository root, obtain the exact build ID from the installed candidate's `release.json` and substitute it below. Do not pass the app version as the build ID.

```bash
python3 wasm_sdk_probe/tools/probe_calc_range_autosave_host.py \
  --out findings/evidence/host-0.2.37/range-autosave-host-01 \
  --build-id EXACT_RELEASE_BUILD_ID
```

Allow approximately 5–8 minutes, including browser startup, two real 30-second idle saves per browser, a 31-second unconfirmed draft interval, and normal Files reopen/leave. The native export is held once by a diagnostic promise while trusted input enters a new draft; the save still exports with the real native engine and writes through the actual host/WebDAV path. No synthetic successful host response is injected.

After the driver exits and its cleanup finishes, the coordinator records `ddev-after.json`, `locks-after.txt`, and `owner-document-after.json` with the same capture commands as the before files. Then run:

```bash
python3 wasm_sdk_probe/tools/read_calc_range_autosave_host.py \
  findings/evidence/host-0.2.37/range-autosave-host-01 \
  --release findings/evidence/host-0.2.37/release.json \
  --safety-dir findings/evidence/host-0.2.37 --red-cases
```

The reader independently opens all four server-downloaded ODS snapshots and resolves effective cell formatting through cell/parent, row and column defaults, and family defaults. It verifies content, B/I/U in Latin/Asian/complex script properties, the adjacent cell, an outside cell, and a second sheet. It also rechecks viewport artifacts, the exact case/browser/route/tool/package population, successful original-target autosave outcomes, complete owned-resource cleanup, and the external preservation snapshots. A normal pass cannot depend on fallback cleanup UNLOCK. Seven report mutations must be rejected.

Missing execution or any failed check leaves actual Files acceptance `NOT_ESTABLISHED`. Preserve failed reports and complete owned cleanup before investigating. Do not erase an attempt or describe a failed product interaction as a harness defect without direct causal evidence. A reader pass closes this finite actual Files scope; further concerns become findings rather than an open-ended extension.
