# Brief for fable: adversarial review of the plan "clicking an `.ods` in Nextcloud opens it"

**Authority.** The owner, in the conversation on 2026-10-20 (~18:50): 「Nextcloud 裡點 .ods 就能開。請規劃，然後送給fable 做對抗性審查」. The owner is present and will read §1 of your review.

**What to review:** `R/handoff/PLAN-2026-10-20-nextcloud-opens-ods.md`, committed together with this brief. Its §6 lists the questions the main session wants attacked. Do not stop there: attack anything the plan assumes.

**Your stance.** Adversarial. The useful output is a defect the main session did not see, backed by a line you read, or a cheaper first step that could falsify the plan before the owner's link. Agreement is not useful unless it rests on something you checked yourself. CLAUDE.md §5 applies: look for "a change that would turn nothing red", and census rather than sample where a population is claimed.

**Constraints:**
- Read-only. No ddev, no browser, no make, no native LibreOffice run. Write nothing under the repository or under the Nextcloud app.
- Searches are allowed; no measurement is running on this machine. Never `cd` into `libreoffice-26-8/`. Use absolute paths.
- `R` = `/home/jiajun/LibreOffice/study_LiteCore`; `wsp` = `R/wasm_sdk_probe`; `app` = `/home/jiajun/Projects/Nextcloud_Apps/litecore` (the host, installed version 0.2.28 = `0870695`); `lo/` = `R/libreoffice-26-8/`.

**Inputs worth reading:**
- the plan;
- `R/handoff/PLAN-2026-09-03-ods-reading.md` (the earlier ODS milestone, with its amendments);
- `R/findings/089-*.md`;
- `R/findings/evidence/m4-ods/`;
- `wsp/viewer-shell/`, `wsp/web/ods-viewer*.{html,js}`, `wsp/tools/run_ods_viewer_draft_smoke.py`;
- `wsp/src/sdk_api.cpp`, `wsp/src/probe_engine.cpp`, `wsp/sdk/sdk-worker.js`, `wsp/sdk/document-sdk.js`;
- `wsp/Makefile` (the R5 reader rule; `E2_V5_*`; the v14 rules; `link_product_stack_1m`);
- `wsp/tools/package_m3_engine.py`, `wsp/tools/probe_m3_assets.py`;
- `R/specs/SPEC-M3-zstd.md`, `R/specs/SPEC-M3-host-entry.md` and whatever the host specs cite;
- `app/src/files.js`, `app/lib/Controller/EditorController.php`, `app/templates/editor.php`, `app/js/litecore-editor.js`, `app/appinfo/info.xml`;
- `R/CLAUDE.md` (the criteria rules, §1–§11);
- the memory notes the plan cites (`ddev-is-shared`, `release-count-batched`) are summarised in the plan; do not look for them.

**What to return** (nothing written; your final message is the review, saved verbatim by the main session as `R/handoff/REVIEW-2026-10-20-fable-ods-in-nextcloud.md`):
- **§1, in zh-TW, plain language, for the owner:**
  - the verdict: the plan holds, holds with the changes you list, or does not hold;
  - the two or three findings that matter most;
  - A/B/C labels for any options, never 甲乙丙.
- **§2, in English, the findings.** One entry each with:
  - severity (blocks / changes the plan / minor);
  - the claim in the plan it attacks, cited by section;
  - your evidence, as file:line you read;
  - the consequence;
  - the fix you propose.
  - Mark anything you inferred rather than read.
- **§3, in English, your answers to the plan's §6 questions**, one by one.
- **§4, in English, a cheaper first step**, if you see one.
