# Host 0.2.33 H7 slot opened, awaiting the owner

This continues `handoff/RUNBOOK-host-0.2.33-h7.md`. It supersedes the occupied-slot observation in `h7-preparation-2026-10-25/` for this attempt. **H7 remains pending; this is readiness evidence, not the owner's acceptance.**

## Authorization and service state

The owner's exact instruction was:

> 我把fgp容器停掉了，請繼續

Translation: "I have stopped the fgp container; please continue."

At **02:50:35 Asia/Taipei on 2026-10-25**, the fresh `ddev list --json-output` observation showed no running project: fgp-nc and nc-bridge were paused; litecore and all other projects were stopped. `slot.json` records the instruction, observed state and H7-only boundary before the service mutation. This is a new slot, not reuse of the expired overnight window.

The agent ran `ddev start` from `/home/jiajun/Projects/Nextcloud_Apps/litecore`; it completed with exit 0 and "Successfully started litecore". The project start built its routine container images and ran its existing app-link hook; no LibreOffice/SDK compilation, relink, package rebuild or app installation/upgrade command was run. The actual **02:51:35** snapshot in `ddev-after-start.json` confirms that **only litecore changed, stopped -> running**. fgp-nc and nc-bridge remained paused, and all other projects remained stopped.

litecore is being kept running for the owner's pending observation. After that observation or cancellation, stop the agent-started project and record the states unless the owner asks to keep it running.

## Current installed candidate and retained fixture

The host checkout was clean at **4f7f870 / 0.2.33** before starting. At **02:52:02**, a read-only PHP request in the web container read the installed app configuration, the served app's manifest through `OCP\App\IAppManager`, and the retained file through `OCP\Files\IRootFolder` (`container-identity.json`, raw output in `container-identity.txt`):

- Installed app version **0.2.33**; maintenance **false**.
- Package **a67beefefebe57d6**, manifest sha256 **df00baa21ffb760f1f0fe30bd9e04592a11946ae3f8a73b0c787b8fe7ea9c291**, matching the release record.
- Manifest viewer entry **ods-viewer-v3**, wasm **ebb7e0cb9f886185c0b0e53eb68f137eb9c5df07af2e83cdb09255c07477d82a**, and the full viewer entry equal to `release.json`.
- Retained file **M4 phase-h/M4 檢視 測試 plain.ods**, fileId **24674**, **7,537 bytes**, sha256 **0402e52724cb5bbd3046461a5fb1c40b9431b33f20834136a835a68f3123e750**. Name, id, size and content hash all match the prior machine H2/H3 report `findings/evidence/m4-ods/phase-h/shakedown/2026-10-23T171515+0000.json`.

This directly reads the current container configuration, manifest and fixture. It does not rehash every engine payload or repeat the previous browser run.

The first readout attempt used removed `OC_App::getAppPath()` and failed before producing an identity result (`container-identity-attempt-1.txt`). The local public interface was read and the command corrected to `OCP\App\IAppManager::getAppPath()`. No product, test runner, criterion or package binding was changed.

## Browser entry and pending observation

The Files URL is **https://litecore.ddev.site:8443/index.php/apps/files/**. An unauthenticated curl request with `Accept: text/html` reached the login page with HTTP **200** (`files-entry-browser-accept.txt`). With curl's default accept header, it returned **401** (`files-entry.txt`); neither request logged in or opened the document.

The owner has been asked to use **admin**, enter **M4 phase-h**, click **M4 檢視 測試 plain.ods** in Files, and switch **Alpha / Beta / Gamma**, then report the actual result. No owner observation has yet been recorded. Do not substitute the completed V3-SEE or the earlier 0.2.32 H7.

No Phase E/H or corpus sweep was repeated. K remains batched and was not started or re-pinned; nominal shipped host remains 0.2.26. Section 34.4 **+0 / +0**, cumulative **46 / 27**.
