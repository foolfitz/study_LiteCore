# Ruling brief — two questions the owner handed to fable before shell generation v62 is frozen (2026-10-12)

The owner chose 「交 fable 裁決」 for both questions below (AskUserQuestion, 2026-10-12). You rule; the main session executes the ruling and checks every number in it against the raw files. Work READ-ONLY in `/home/jiajun/LibreOffice/study_LiteCore` and `~/Projects/Nextcloud_Apps/litecore` (scratch copies under /tmp are fine; no browsers, ddev, builds or network). Answer in English to stdout; the main session saves it as `findings/evidence/128/ruling/fable-ruling.md`. Specs are zh-TW.

## Where the release stands

Release 0.2.13 = autosave (finding 127) + fixes for 128 (a deleted character stays drawn ~120 ms after the caret moved), 129 (an unshifted arrow on a range was refused), 130 (the input-failure toast never fired). Spec `specs/SPEC-M3-autosave.md` §9 (frozen, append-only; §9.4 criteria, §9.10 implementation-time corrections). The page `wasm_sdk_probe/web/e2-editor-app.js` = `dist/` = `c7f904fa…` is packaged into host 0.2.13 (not committed, not counted, shell generation v62 NOT frozen; the release rule is: browser criteria hold on `dist/` first, then freeze, then the count chain).

Already measured on this page: the new autosave runner's full shakedown passes after two reader fixes (`findings/evidence/m3-autosave/shakedown/README.md`) and its dual review is dispositioned (`findings/evidence/m3-autosave/review/DISPOSITION.md`); 129-B holds (`findings/evidence/129/final/README.md`); 130-U holds (`findings/evidence/130/replay-output-0.2.13.txt`); 128-B single keys hold (every key ≤ 40 ms: Chrome 13.8–29.7, Firefox 19.5–34 ms) and its host-segment cell holds with a discriminating red control (`findings/evidence/128/final-0.2.13/hostseg-rejudged.txt`).

## Question 1 — a burst of Backspaces is sometimes refused as delete-selection (proposed finding 131)

Evidence: `findings/evidence/128/final-0.2.13/report.json` (first seen: 3 of 4 rapid arms) and the A/B `findings/evidence/128/rapid-ab/README.md` + both `report.json`. Same instrument, same document, 20 real Backspaces 50 ms apart, two bursts per browser: **0.2.12's page 4/80 refused, 0.2.13's page 19/80**. Delete action time under the burst (latency line): 0.2.12 median 46–49 ms / p90 50–57; 0.2.13 median 63.5–67 / p90 120–133.

Mechanism, read from the log and the page (main session; check it): `el.sink.addEventListener("beforeinput", …)` near `deleteActionFor` (web/e2-editor-app.js, search 「FINDING 121」) takes the shape from `session.state.snapshot.editorState` (finding 121's fix: the engine's selection, not the page's belief). A delete goes through the engine's selection barrier (select one unit backwards, verify, delete — `findings/evidence/128/README.md` cause section, and finding 119's analysis). A Backspace whose `beforeinput` comes while the previous delete is out reads that one-unit RANGE, goes out as `delete-selection`, and when it is dispatched the caret is collapsed again: the gesture gate refuses it, the developer toast 「刪除選取：EDITOR_FORMAT_GESTURE_UNSUPPORTED…」 shows, the character stays. No data is lost. Why 0.2.13 makes it more frequent is **inferred, not measured**: 128's remedy B (§9.10: a repaint that meets BUSY while an `editorAction` is out gives up, and the action's end repaints at once — `engineActionsOut`, `busyLeftToAction`, `editorAction`, `renderDocument`'s BUSY branch) puts paint requests in the Worker ahead of the next delete, so each delete is out longer and the next key lands inside its barrier more often.

Options the owner was shown (you may rule otherwise):
- **A** Fix before freezing: the page does not take the engine's range for the user's selection while one of its own deletes is out (send delete-backward/forward), which also removes 0.2.12's 5 %. Then spec addendum, re-measure, re-shakedown; the chain moves later by some hours.
- **B** Ship 0.2.13 as is; register 131 with the 5 % → 24 % numbers as a named limit.
- **C** Revert 128's remedy B (back to 0.2.12's repaint): refusals back to ~5 %, 128's ~120 ms ghost back, 128 not shipped.

The main session's leaning: **A**, because the refusal is a correctness defect with a developer's sentence in front of the user, its trigger is a page decision (not the engine), 0.2.13 makes it five times more likely, and the owner's hand test of 0.2.12 already flagged delete behaviour. Constraints that bind any page change: the product-path runner's 41 page-mutation anchors and 2 diagnostic anchors must each still match exactly once (`run_e2_c_product_path.py`; §9.10 records why 128 took remedy B to keep `edit-arrows-swapped`'s anchor); E1-C's bundle check; the unit tests (`node --test editor-shell-v2/tests/*.test.mjs`, 213/213); §34 (no new checks of checks; the 128 probe is an instrument, not a counted check).

## Question 2 — 128-B's rapid-key clause is not met

§9.4 128-B says (via §5): single keys each ≤ 40 ms, rapid keys (50 ms apart) at most ≤ 60 ms, red case 0.2.12's page. Measured on 0.2.13 (`final-0.2.13/report.json`, `rapid` per arm, stale-after-caret): Chrome high 13.8–17.2 (one key unread), Chrome low up to 90.5, Firefox high 10.9–84.6, Firefox low up to 96.4. 0.2.12's page (`findings/evidence/128/README.md`): 125–283 ms. Note the rapid arms of the first run also contain the refused keys of Question 1, which disturb the per-key reading of the key after them; Firefox high had no refusal and still read 73.8–84.6 ms. §9.4 writes no "if never done" default for 128-B.

Options: **A** register the rapid clause as a named limit for this release (128: single keys fixed, host-segment cell holds, rapid improved from 125–283 to 77–96 ms but over 60); **B** keep working until ≤ 60 ms before freezing (cause not measured; the remedy-B paint ordering of Question 1 is the leading guess). Main session's leaning: **A**, unless your ruling on Question 1 changes the paint ordering, in which case the rapid clause is re-measured with the fix and judged then.

## What to rule

1. Question 1: which option, and if A, the exact rule the page should follow (where, and what it must not break: a real range the user made with the pointer and then deletes must still go out as delete-selection — finding 121), the criterion and red case that will judge it (written before any run), and how many bursts per browser.
2. Question 2: which option, and whether it depends on your answer to 1.
3. Anything in the mechanism above that you find wrong when you read the code — say so with file:line.
4. The release steps that follow from your ruling, in order, with what each needs before the next may start.

≤ 80 lines. Plain reasons the owner can read are welcome next to the technical rule.
