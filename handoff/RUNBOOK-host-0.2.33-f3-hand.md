# Remaining editor owner observation: Markdown Insert/Cancel focus

Criterion: `specs/SPEC-M3-link-batch-v22.md` section 11.3, **F3-hand**. This is separate from the completed ODS H7 and V3-SEE. No repeat of those ODS tests is needed.

The autonomous Xvfb diagnostic already verified native X11 typing and server-saved content in **3/3** rounds (`findings/evidence/host-0.2.33/count-preparation-2026-10-25/xvfb-focus/`). It is not the owner's report on their actual desktop/browser. Do not mark F3-hand complete from that diagnostic.

## Prepare the next owner slot

Re-read `ddev list --json-output`. Use the owner's next available slot; if another project is running, preserve it and wait. Start only litecore if stopped, recording that it was the agent's start. The previous autonomous preparation slot is closed; its service states are recorded separately.

Expected installed candidate: host **0.2.33 / 4f7f870**, package **a67beefefebe57d6**, editor **e2-editor-v22 / f7a40bcc**, page **3b96cb16…**. No installation, package rebuild, relink or new shell generation is needed.

The dedicated fixture is **LiteCore 手動驗收 2026-10-25/Markdown 焦點測試.odt**. Its upload/read-back identity is recorded in `findings/evidence/host-0.2.33/count-preparation-2026-10-25/manual-fixture.json`; the original generated ODT is retained next to it. Use this fixture so the owner need not alter a personal document.

Recorded fixture identity: fileId **24920**, **1,518 bytes**, sha256 **3d17d51266216f6e282a6785e902f19460cbd59ccfdbb4c09579624147291297**. The upload was 201 and read-back 200, byte-equal to the retained source. This identity is before any owner edits.

## Owner action, about one minute

1. In the owner's normal **Chrome**, log in as the existing test admin and enter **https://litecore.ddev.site:8443/index.php/apps/files/**.
2. Open **LiteCore 手動驗收 2026-10-25/Markdown 焦點測試.odt** through Files. Click inside the document to place the caret.
3. Click **貼上為 Markdown…**, enter a short paragraph, click **插入**, then type **A** on the real keyboard. Confirm that A appears in the document.
4. Open the same dialog again, click **取消**, then type **B** on the real keyboard. Confirm that B appears in the document.
5. Report what happened after each button. Save and close this test document when finished so the next task can read its lock state.

Use ordinary keyboard typing after each button. The existing defect can be masked by the toolbar's text insertion field, pasting, or CDP `Input.insertText`; those are not the requested owner path. Record the exact report and the actual browser; do not infer a result.

The older owner follow-ups for Ctrl/Cmd+Home/End and dialog appearance remain as recorded in `RELEASE-TEXT-DRAFT-0.2.27-0.2.28.md` section 6. They are separate from this F3-hand criterion and must not be silently marked complete.

## After the report

- A passing report satisfies the existing human half; save exact words and identity in English evidence, preserving the quotation as data, then append the v22 spec. A problem is recorded before choosing a fix; do not rerun the machine diagnostic to replace the report.
- Stop litecore if the agent started it unless the owner requests that it remain running, and verify all other project states.
- K is still unrun. Do not use the old 0.2.26 chain unchanged. The remaining work is final identity re-pins, merge BINDING, a new chain/reader on 0.2.33, existing preflights and the owner's K window/no-site agreement. Once that agreement is given, retain it instead of asking again.
- `make test-e2-c-static` contains a **C++ model compilation**, despite its name. The owner has not asked the agent to build; do not run that target unattended. The autonomous preparation used the focused Python tests, existing red cases and actual browser arms instead. Handle any required compiling target under the owner's standing build rule.

## Completed, 2026-10-25

The owner explicitly selected A (all four listed observations meet expectations) after this procedure. F3-hand, the carried Home/End hand check and dialog appearance report are complete; see `findings/evidence/host-0.2.33/f3-hand-2026-10-25/owner-confirmation.md`. Do not request them again for this candidate. The document is now edited; its original hash above describes only the pre-test source. It was preserved with the owner's changes. litecore was stopped and all ddev project states restored. K remains unrun.
