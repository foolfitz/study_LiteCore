# Autonomous count preparation: modal census fixed, native Xvfb typing observed

Spec: `specs/SPEC-M3-host-0233-count-preparation.md`. The owner requested autonomous continuation while asleep, suggested Xvfb, and asked to stop at necessary human verification. A fresh idle slot was recorded before starting only litecore (`slot.json`, `ddev-before.json`). **This is preparation, not a K count.**

## Page-honesty witness and existing v22 prescription

Unchanged runner **3eab7432…**, host **0.2.33 / 4f7f870**, package **a67beefefebe57d6**, page **3b96cb16…**: Vrw/Chrome failed only on `V2 control: paste-markdown did not advance ('存回 87 ms')`. Raw report **`findings/evidence/m3-page-honesty/shakedown/2026-10-24T190507+0000.json`**, receipt `page-honesty-witness.json`, committed first in **21d7b46c**.

Commit **e704efee** applies the existing v22 section 11.6 prescription: exclude the named modal entry from the toolbar edit census, as for open-file. The entry opens a dialog; its inner Insert performs the mutation. Other controls' coverage/mutation checks and all V7 read-only disabling checks remain. No product byte, count identity pin or merge BINDING moved.

- **Red first:** five focused tests on real reports; two failed under the old judge for the intended reasons (`modal-census-red-tests.txt`).
- After repair: **5/5 tests**, witness re-score **clean**, **158/158 existing red cases remain red**. The tests also check a future edit button, another omitted button and an enabled read-only Markdown entry.
- Actual repaired driver, **03:10:43-03:22:36 Asia/Taipei**: Vrw/Vro x Chrome/Firefox, **1/1 in all four cells**, exit **0**, **VERDICT clean**. Raw report **`findings/evidence/m3-page-honesty/shakedown/2026-10-24T191043+0000.json`**, `page-honesty-fixed-live.log`, reader output `page-honesty-fixed-live-score.txt`.
- Every cell's page-derived control set minus the two named entries equals its driven button rows: 22 listed, 20 driven in this run. These are observed sizes, not a fixed future count.

To re-read the completed report without a browser:

```bash
python3 wasm_sdk_probe/tools/check_m3_page_honesty.py --score findings/evidence/m3-page-honesty/shakedown/2026-10-24T191043+0000.json
```

Section 34.4: **execution +1 / review +0**, cumulative **47 / 27**, for the deferred witnessed judge repair.

## Headed Chrome and native X11 keys under Xvfb

`xvfb-focus/README.md` and its raw report/screenshots record **3/3** fresh headed Chrome rounds on the actual Files/host path: native **XTestFakeKeyEvent** typing after Markdown Insert and Cancel, trusted keydowns, both markers present in the server-saved ODT, cancelled dialog text absent, GET **200**, focus back on `sink`. The diagnostic folder was deleted (**204**); all diagnostic browsers closed.

The first attempt used a bare headed base class with host helpers that dispatch on LockChrome: three login adapter errors before document interaction. Exact first-attempt source/output are preserved. The correction is diagnostic-only; no shared launcher changed.

## Human remainder and next entry

The earlier H7 handoff's "no human acceptance item remains" referred to **ODS Phase H**. The inherited **editor F3-hand** in v22 section 11.3 still requires the owner's normal Chrome desktop report after Insert and Cancel. Xvfb machine evidence is not substituted for that report. The older Ctrl/Cmd+Home/End and dialog appearance owner follow-ups also remain unreported.

Dedicated fixture: **LiteCore 手動驗收 2026-10-25/Markdown 焦點測試.odt**, fileId **24920**, **1,518 bytes**, sha256 **3d17d51266216f6e282a6785e902f19460cbd59ccfdbb4c09579624147291297**. Upload **201**, read-back **200**, byte-equal to `manual-fixture.odt`; current container app/manifest/editor identity checked again (`manual-fixture.json`). It is not yet owner-accepted. Runbook: **`handoff/RUNBOOK-host-0.2.33-f3-hand.md`**, about one minute in the next available slot.

`binding-inventory.json` snapshots the old `repin_0226.py` template's participants plus merge BINDING. It is not an exhaustive census of all current/future pins. The old 0.2.26/v21 pins remain; `check_m3_assets.BUILD_ID` already names the new package. No re-pin or new chain was applied. The separate J-a P5 K window/no-site agreement was not fabricated from the sleeping instruction.

The full `make test-e2-c-static` was not invoked: its recipe includes an unconditional C++ model compilation, and the owner has not asked the agent to build. Verification here is the focused Python tests, existing red cases and actual browser arms; no full-static-pass claim is made.

## Cleanup and limits

**03:24:13-03:24:15 Asia/Taipei:** stopping the agent-started litecore exited **0**. `cleanup.json` and raw snapshots show every ddev project state matches the slot start: litecore stopped; fgp-nc and nc-bridge paused; all others stopped. Host source is clean at **4f7f870**. The new manual fixture and prior H7 fixture remain; package and archives did not change.

Before the first witness, a read-only query returned **22** app lock rows. The existing unmodified runner clears that table in its normal setup; the rows' owners/expiry were not captured before starting it. Do not claim all were expired or agent-owned. After all tests it reads **0** (`locks-after-tests.txt`). Restored-state claims above concern ddev project status, not database row equality.

The manual-fixture preflight initially expected DAV to return 404; the helper instead raises HTTPError. The read failed before creation. Handling that expected exception allowed a subsequent fresh MKCOL/PUT/read-back; no existing file was overwritten.

**Stop at the F3-hand owner remainder.** ODS H7 and V3-SEE already hold. Host **0.2.33 remains installed and uncounted**; K is batched/unrun, nominal shipped host **0.2.26**. No core compilation, relink, package rebuild, install/upgrade, Phase E/H repetition or corpus sweep was performed.
