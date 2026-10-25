# Calc grid entry and rectangular selection — accepted finite shell batch

Final source acceptance: **378/378**, Chrome N=3 and Firefox N=3, `final-02/report.json`. Each round has 63 checks; fixture-defined selection and pending-entry populations are verified by the reader. Twelve post-input views contain **312 DOM tiles**, compared byte-for-byte with direct engine rendering. Actual downloaded ODS XML, reopen, neighbors and another sheet pass. Session/SDK/host contract units: **22/22**. Focused oversized/protected/failed-hit/old-draft validation: **8/8 per browser**, `pending-validation-05`.

```bash
python3 wasm_sdk_probe/tools/read_calc_input_range.py findings/evidence/calc-input-range/final-02 --red-cases
```

The reader derives literal checks from executable call sites and dynamic cases from the fixture manifest, checks source/tool identities, exact populations, snapshots and independent ODS XML. Empty runs, missing browser, empty checks, missing check, false check and wrong tool identity all turn red. `reader-empty-red.txt` precedes its clean final read.

## Delivered contract

Grid input starts a replacement draft; F2 preserves apostrophe-safe cell input. Enter commits and Escape cancels. Formula/address fields own their input. Pending cell selection keeps one actual textarea receiving text/composition, then transfers the buffer to the selected explicit target after the pointer pump finishes. Transfer validates complete length/writability before changing the session; failure retains the buffer and refuses Save. Cancelled/failed selections cannot redirect it. Escape also works after a refused Save moves focus to the toolbar.

Click collapses; drag, Shift-click and Shift-arrows extend a separate active/anchor/focus rectangle. Ordinary arrows move from focus to the next engine-visible cell and collapse, including top/left boundary collapse. Focus geometry drives scrolling; starting editing reveals active. Hidden indices have no invented dimensions. Endpoint merged extents are included, but interior/boundary merges do not recursively expand selection. This is an address rectangle, not full Calc merge closure. Each step uses a bounded SDK request independent of selected area. Read/hit cursor side effects never choose mutation targets.

Multi-cell B/I/U is refused through toolbar, shortcut and session, without revision changes. Starting input/F2 collapses to the active anchor. No range mutation, rich text, fill, multicell paste, drag autoscroll or autosave was added. Existing single-cell formatting remains supported; invalidate-before-emit is preserved. No native build/relink or frozen profile change was required.

## Preserved failures and review

- `browser-red-01`: real missing F2/direct-entry paths. `session-entry-red.txt` and `session-range-red.txt` preserve failing API witnesses; `browser-range-red-01` preserves missing Shift selection.
- `browser-entry-01`: Firefox F1/F2 runner code mix-up, retained and corrected; not a product failure.
- `full-attempt-01`: refused formatting lost grid focus. `full-attempt-02`: synthetic Firefox composition guard allowed a newline; corrected without blocking trusted IME default handling.
- `pending-entry-red`: delayed selection loses first input. `pending-entry-green-01`: Chrome buffer transferred before final pointer extension and was prematurely committed. Both retained.
- `full-attempt-04`: request-count judge incorrectly bounded an entire interpolated drag instead of one pointer step. The corrected runner records actual steps and SDK calls; selected area is not enumerated.
- `pending-validation-01` through `04`: Escape after refused Save went to the save button, leaving the retained buffer active. Event traces expose this; global pending Escape corrects it. `05` passes in both browsers.
- `final-01` could not acquire the browser lock because the focused validation was still running; no acceptance round ran. `final-02` is the six-round accepted artifact.

Astra `/root/astra_calc_scope` supplied scope and repeated source audits under owner-delegated authority. It identified concrete buffer validation/target/old-prefix issues and approved finite closure after corrections and tests. Claude protocol review 04 and source-excerpt review 05 completed; earlier long review attempts timed out or were terminated without verdict. Full work orders, original results and dispositions are in [review outcomes](review-outcomes.md). No failed attempt is counted as approval.

Firefox IME evidence is a synthetic composition lifecycle plus trusted Enter, not an OS/Firefox preedit claim. Chrome exercises trusted CDP preedit and commit, also not an OS input-method claim. Continuous keyboard reception while an ordinary cell commit disables the textarea remains a **pre-existing, unmeasured follow-up limitation**, explicitly retained by Astra's closure ruling. This does not imply arbitrary-latency continuous typing was established.

Actual Files installation/acceptance: [host 0.2.36](../host-0.2.36/README.md). Full K remains deferred; nominal shipped host is 0.2.26. Section 34.4 +0/+0, cumulative 47/27.
