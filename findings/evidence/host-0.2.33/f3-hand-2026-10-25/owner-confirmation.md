# Owner editor acceptance: F3-hand and carried manual checks

## Exact replies and their scope

The owner first replied:

> 測試完成

Translation: "Testing completed." This alone was not recorded as a passing result. The assistant then asked whether all four specified checks met expectations or any had a problem, naming Insert/A, Cancel/B, Home/End boundary deletion and dialog appearance, and offered:

- **A：四項都符合預期** — all four meet expectations.
- **B：有異常，我補充是哪一項及現象** — there is an issue; the owner will specify the item and behavior.

The owner's exact clarification was:

> A

The reply explicitly selects **all four meet expectations** for the procedure given in this slot. It is not merely inferred from "Testing completed."

## Accepted observations

1. **F3-hand, Insert:** after inserting a short paragraph through the Markdown dialog, real keyboard **A** appears in the document.
2. **F3-hand, Cancel:** after cancelling the dialog, real keyboard **B** appears in the document.
3. **Carried Home/End hand check:** Ctrl+Home then Backspace, and Ctrl+End then Delete, do not delete text at the respective document boundary.
4. **Carried dialog appearance check:** the open dialog is centred; after closing, no dialog obscures the document.

**F3-hand holds**, and the two separately registered Home/End and appearance owner follow-ups are now reported as meeting expectations. They are not new F3 criteria. The procedure specified the owner's normal **Chrome**, using admin and the actual Files action; no browser version was reported or inferred. No machine diagnostic replaced these owner observations.

## Candidate and fixture attribution

- Host **0.2.33**, clean source **4f7f870bb44e703e101148f143f174c7facee5c9**, package **a67beefefebe57d6**.
- Editor **e2-editor-v22**, wasm **f7a40bcce073d913e562245b96f32a1051766dda23da0da3911741f03934d49e**, page **3b96cb1661aba6de6add989c98c80ab393cd394307763bc6dc28c9440fba82e2**.
- Files fixture **LiteCore 手動驗收 2026-10-25/Markdown 焦點測試.odt**, fileId **24920**. Before owner edits: 1,518 bytes, sha256 **3d17d51266216f6e282a6785e902f19460cbd59ccfdbb4c09579624147291297**.
- Current container/app/fixture identity was directly read at **08:54:19 Asia/Taipei** before handoff to the owner (`container-identity.json`). The fixture's original hash describes the pre-edit source; it is not required to remain unchanged after this edit test.

This supersedes the pending editor owner status in the slot README, count-preparation handoff and v22 section 15. The existing machine F3 and native Xvfb results remain separate evidence. ODS H7 and V3-SEE were already accepted and were not retested.

Host **0.2.33 remains an uncounted candidate**. K was not scheduled, started or re-pinned by this acceptance reply; nominal shipped host remains **0.2.26**. No criterion, judge, product or binding changed. Section 34.4 **+0 / +0**, cumulative **47 / 27**.
