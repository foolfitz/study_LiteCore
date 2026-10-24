# Resume host 0.2.33 at the owner's Files-path H7

Canonical criteria: `specs/SPEC-M4-ods-in-nextcloud.md` section 4 and `specs/SPEC-M4-viewer-v3.md` sections 16 and 19. Machine Phase H already holds. The only remaining human acceptance item for this candidate is H7. K requires a separate explicit schedule.

## Slot entry

The 2026-10-24 overnight window expired. Use a new owner-authorized ddev slot. The 2026-10-25 preparation observed **fgp-nc running and litecore stopped**; see `findings/evidence/host-0.2.33/h7-preparation-2026-10-25/`. Re-read the running set immediately before any start:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
ddev list --json-output
```

If another project is running, do not stop it or start litecore; report the occupied slot. When the slot is available, record its authorization/boundary and the actual project states. If litecore is stopped, the agent starts only litecore:

```bash
cd /home/jiajun/Projects/Nextcloud_Apps/litecore
ddev start
```

This is a service start, normally about 1-2 minutes; it does not compile or reinstall the candidate. Record whether the agent started it. If litecore was already running, preserve that ownership/state when finishing. Do not run the installation script again.

Before handing the browser entry to the owner, read the installed app version and on-disk manifest. Expected host **0.2.33 / 4f7f870**, package **a67beefefebe57d6**, viewer **ods-viewer-v3 / ebb7e0cb**. A different identity requires recording and investigation before attributing an observation to this candidate.

## Owner's observation

1. Open **https://litecore.ddev.site:8443/index.php/apps/files/** as the existing test **admin**.
2. Enter **M4 phase-h**, then click **M4 檢視 測試 plain.ods** in Files (fileId **24674**). Follow the Files action into the viewer.
3. Confirm that **Alpha / Beta / Gamma** are visible and switch among the sheets to see their contents.
4. Record the owner's exact report. Record the browser only if known; do not infer it.

Use the actual Files entry. The local mirror's completed V3-SEE and the previous 0.2.32 H7 are separate observations. The stopped 8794 preview URL is not an entry point for this test.

The machine half already exists in `findings/evidence/m4-ods/phase-h/shakedown/2026-10-23T171515+0000.json`: H2/H3 on this package and fixture, with read-back tab switching. Follow the recorded v2 H7 precedent (`specs/SPEC-M4-viewer-v2.md` section 10.5) when linking that evidence to the owner's report. Do not repeat Phase E/H or the corpus sweep to fill the human half. If the candidate or fixture identity differs, do not silently reuse that attribution.

## Record and finish

- Save the owner's exact words and the observation identity in a new English evidence Markdown file. Preserve quotations verbatim as data; distinguish current observations from historical machine evidence.
- Append the result to `specs/SPEC-M4-viewer-v3.md` in zh-TW. The spec is append-only. Update the current H7 status in the host evidence/release records with a pointer to the new observation; preserve earlier timestamped reports.
- If the observation does not happen, **H7 stays pending and 0.2.33 stays an uncounted candidate**. If the owner reports a problem, record it before choosing a fix or rollback; an absent confirmation is not a failure observation.
- After successful H7, leave the installed candidate in place. Full K remains batched and nominal shipped host remains 0.2.26 until the owner explicitly schedules K and its criteria are satisfied.
- Stop litecore if the agent started it for this slot, unless the owner asks to keep it running. Re-read all project states and record the outcome. Preserve the H7 fixture folder unless cleanup is within the owner's authorized scope.
- Keep cohesive English commits with `Co-Authored-By: Codex <noreply@openai.com>`. No compilation, new acceptance criterion, checker change, or package re-pin is needed for this work unit.
