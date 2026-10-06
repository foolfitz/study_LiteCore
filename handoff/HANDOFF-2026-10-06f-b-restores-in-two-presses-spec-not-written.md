# Handoff, 2026-10-06f — rounds five and six run: B's proof holds at the undo limit, and B's restore reaches every labelled boundary in two presses; the spec is still not written

Entry points: this file; `findings/evidence/merge-native/README.md` (sections "Fifth round" and "Sixth round" are this session's); `PREDICTION-5.md`, `PREDICTION-6.md` (each committed before its round). Picks up from `HANDOFF-2026-10-06e-option-b-is-feasible-natively.md` — read its "B as worked out", "What the relink would ship" and "Standing rules" first; they all still hold except where this file corrects them. Session stopped early at the owner's request (they had to close it). Nothing is running. No engine, shell, page, host or runner byte changed.

## Commits

| Commit | What |
|---|---|
| `b3eaf3b4` | Round five instruments + `PREDICTION-5.md`: payload shape and default limit read from source; fixture `undo-limit-same.fodt` (H02); reader reports count-only agreement and timestamp-only changes, fails if the count never reached the limit (red case run) |
| `fb1fda41` | Round five results (`limit/`) |
| `af26cd61` | Round six instruments + `PREDICTION-6.md`: probe `MERGE_RESTORE_PRESSES`, reader shows restore press count, runner records the setting |
| `56ffd283` | 6b appended to `PREDICTION-6.md` before 6b ran; `round-i-tables.cases.tsv` |
| `1e9037eb`, `0a61de2c` | Round six results (`restore/`); README totals listed case by case |

## What was measured

- **Round five, undo limit 3** (`limit/round-20261006T085152Z`, `…085306Z`): the count stops at the limit (count-only comparison wrong 36 times: 21 + 15); the **whole `.uno:Undo` payload changed on every press that changed `content.xml` and on no other** (72 presses, 0 disagreements, including two no-ops with the stack full). With identical comments (H02) presses 4–8 changed the payload **only in the newest action's `dateTime`** (15 presses). Default limit is **100** (`Common.xcs`, read). Native timestamps are nanoseconds; **WASM's are whole milliseconds** (`std::chrono::system_clock` → WASI `clock_time_get` → `Date.now()`, `wasm-lite/tools/emsdk/upstream/emscripten/src/lib/libwasi.js:162–170`, read not measured).
- **Round six** (`restore/`): Delete at a paragraph's end when the **next paragraph has a visible label** (numbered heading, bullet or numbered item — I02, C08, C10, I03, I01; PMPC P27, E13, P62, P63): the first unshifted Left only sets Writer's in-front-of-label flag (`SwCursorShell::LeftRight`, `crsrsh.cxx:326–380`, case 2); **the second Left reaches the placed caret, and the key then gives `content.xml` byte-identical to Writer's own key, 3/3 each**. Unlabelled next paragraphs and all Backspace cases (C11–C14, E15) need one press. **C08 is no longer a refusal; P62 cannot be the production-UI runner's refusal arm.** 6b: at tables (C15, C16) neither press comes back and the probe's key then deleted a character inside a cell — the engine must refuse, pressing nothing (6b is that check's red case); C17 comes back in one press and the key does nothing; C29/C30 nothing selected. 183 presses this round, 0 stack-vs-content disagreements.
- Totals for B (rounds four to six): Writer's key equalled at 19 fixture cases and 11 PMPC cases, 3/3 each (listed in the README).

## Design decided this session (for the spec; not yet reviewed)

Engine, behind a **new macro `OXSDK_MERGE_KEY_UNDO` defined only for v15's object** (so v8/v14 preprocessed sources are unchanged by B — make that a criterion via `what_the_link_ships.py`-style preprocessing):

1. Unit with no separator → today's barrier delete (`verified-selection-delete`). Nothing selected at 250 ms → today's refusal (add a `mergeKey.stage: "nothing-selected"` field so the page can word it).
2. **B is entered only if the unit contains a paragraph/line separator (10, 13, U+2028, U+2029).** Units whose only separators are `\t` or U+FFFC stay refused as today (unmeasured scope: inline objects, tabs).
3. Restore: the opposite arrow without Shift; evaluate only callbacks after that press (cursor callback + collapsed typed selection); caret = pre-selection caret → go on; else press once more; **at most two presses**; not back → `EDITOR_BOUNDARY_UNSUPPORTED`, view recovery, `mergeKey{keyPosted:false, stage:"restore"}`. Per-press wait cap (2000 ms proposed). Risk to watch: a late cursor callback from the Shift+arrow read as the restore's → an extra press → false refusal (safe direction; the WASM criterion catches it).
4. Read `.uno:Undo` payload P0 (unreadable → refuse, keyPosted false). **Clock guard:** post the key only once the wall clock's millisecond is later than the one in which P0 was read — makes "a new action changes the newest `dateTime`" a guarantee on WASM, not a likelihood.
5. Post the user's key (KEYINPUT+KEYUP, charCode 0, same codes as the native probe). Re-read the payload on later callbacks (coalesced, non-reentrant step). Changed → completion **`verified-key-undo`**, `changed:true`, revision+1, `keyUndo{comment, actionsBefore, actionsAfter, restorePresses, keyToUndoMs, clockWaitMs, topDateTimeBefore, topDateTimeAfter, codePoints}`.
6. Deadline after the key (2000 ms proposed) with P unchanged → **`EDITOR_BOUNDARY_UNSUPPORTED` with `mergeKey{keyPosted:true, stage:"key-deadline"}`**, never `changed:false`. Chosen over `MUTATION_OUTCOME_UNKNOWN` because that code maps to `rollback` → `recoverable-error` → 「回到檢查點」 opens an older checkpoint and loses unsaved typing (109's shape again); the boundary code takes 109's path: checkpoint of whatever the document is at that moment, then reopen — honest.

Worker (`sdk/sdk-worker.js:843–870`, `:1060–1075`): forward `keyUndo` on completions and `mergeKey` on errors for product operations (today only `formatBarrier` is forwarded). Shell (`editor-shell-v2/narrow-editor-v2-client.js:276`): `DELETE_ACTIONS` accept `verified-key-undo` with `changed:true`, revision+1, non-empty `keyUndo.comment` → new shell generation. Page (`web/e2-editor-app.js`): `workerUrl` **and** `PINNED_WASM_SHA256` move to v15 (both lines, as at the v8 cutover, `:1881–1916`) — so the page commit follows the link; `BOUNDARY_TEXT` (`:1019`, "文件沒有被改動") must not be shown when `mergeKey.keyPosted`; the remaining-refusal wording should no longer say paragraph boundaries cannot be deleted.

## Criteria drafted (write into the spec with form and "if never done" default)

- M1-1 B only in v15 (preprocess every other profile's defines before/after: identical). M1-2 shell unit tests + red cases. M1-3 page text choice unit test + red case.
- **M2-1** (core): standalone page + fake host, Chrome and Firefox, real keys, 3/3 per browser per case; **the case list is generated by a tool from a native reference round R0** run on the very `.odt` bytes WASM loads (all cases, `MERGE_RESTORE_PRESSES=2`) — tool-closed, not hand-listed; a case where arm b ≠ key stops everything rather than being dropped. Per case: `verified-key-undo`, comment = native's, no reopen, saved `content.xml` = native key arm's. Control first: zero-edit load+save `content.xml` WASM = native; if not, a reduction may be appended only from that diff, before counting. Red: same runner on v8 for three cases per browser.
- M2-2 `keyToUndoMs` max < deadline/2. M2-3 refusals (C15, C16 before the key; C17 key-deadline; C29, C30 nothing selected) with an unsaved marker: marker survives the reopen; keyPosted never gets the "unchanged" text. M2-4 undo limit on WASM: ≥105 same-comment joins through the page, all `verified-key-undo`, `actionsAfter` reaches 100 (non-vacuity), `topDateTime` strictly increases every press. M2-5 product-path net v15 = v8 cell by cell.
- **R**: host release (0.2.8) packaging v15 + new page; six M3 runners re-bound; production-UI runner re-pinned: its Bdel/Bbs points (heading end, paragraph start) now become **merge/key arms on the host** (verified-key-undo, no reopen, marker on server), and B3x / a refusal arm move to the document start Backspace (C29 shape; 250 ms refusal). A Delete refusal arm on PMPC needs a native measurement first (document end or a protected TOC entry — the latter needs a TSV escape for the tab in entry text).
- Placement on WASM is the runner's choice and must be recorded; for merge cases the content comparison is itself the placement check (a wrong boundary gives a different document → red, not green).

## Registered, not this round

Enter / Tab via B (each its own measured step); document ends still refuse+reopen (now the commonest remaining refusal — could become a no-restart "nothing to delete" at the session layer); a caret already in front of a label (user pressed Left at an item's start) — the probe supports a negative `offset` but the TSV couples placement edge and key, so it is unmeasured; nested lists, tracked changes, fields, footnotes, RTL, picture labels; the shipped barrier's proof on a protected index-entry no-op (finding candidate, first attempt only); v14 does not get B; finding 111 open; performance / main-loop model has no measurement and was never registered — register it in the spec.

## What is next

1. **Write `specs/SPEC-M3-paragraph-merge.md`** (zh-TW, append-only) from the two sections above; then opus adversarial review of the spec before any code (codex MCP failed to connect this session; `codex exec -s read-only` may still work).
2. Native reference round R0 on the `.odt` inputs (instruments + predictions first; convert the fixtures once and record their sha256).
3. Engine/worker/shell/page code + unit tests + red cases; `RUNBOOK-relink-v15` (Makefile rules copied from v8 + the new define; confirm `c41e8582` as v8's link commit — the log says "076 的連結備妥", consistent but still to check against the archived v8); owner links (archive first).
4. WASM dev shakedown, bindings appended, counted runs, host 0.2.8, R.

## Things this round taught

- **"Feasible" from one round hid a coverage hole.** Round four's single C08 failure looked like an edge case; reading `LeftRight` showed it was every Delete before a labelled paragraph — in the owner's document, 11 list openings plus every non-last item. Ask what a single failing case is an instance of before calling it an edge.
- **A second press is safe only because it is conditional and checked**: it is pressed only when the first did not come back, and the key is pressed only when the caret is back. 6b shows what an unconditional sequence would do (a character deleted inside a table cell).
- The count-only proof is wrong even below any limit: 15 of round four's presses were in-paragraph deletes folded into the previous action.
