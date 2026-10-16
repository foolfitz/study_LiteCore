# Plan, 2026-10-16: the next link (v21) and the seven queued engine items

The owner's words (2026-10-16): 「我已經讀完發佈說明，前個session說可以開始連結」 and 「如果會跑很久的話可以交給我執行」. The 0.2.24 release text is final (`338b8ddb`).

**Status.** This file is a plan, not a spec. Nothing in it is a criterion yet. No product bytes change until a spec is written and reviewed. The link itself is the owner's step (global rule since 2026-10-15).

**Inputs.** There are three fact sheets in `handoff/link-batch-v21/`. They were read-only gatherings by three opus subagents. Every claim carries a path:line and a label: source, doc, bytes, or inference.

- `facts-caret-boundary.md`: placeCaret on `TEXT_SELECTION`, the immediate boundary answer, and 142.
- `facts-markdown-cfield.md`: Markdown paste and the C manifest field.
- `facts-language-d12.md`: `Language=` (with 031 and the pins) and D12.

The main session re-read these citations against source:

- `probe_engine.cpp`: `:2966-2996`, `:3236-3242`, `:5905-5925`, `:7060-7075`;
- `editor_api.cpp:60-70`;
- `web/e2-editor-app.js:2944-2955`;
- `build_e2_editor_v4_profile.py:192-202`;
- core `init.cxx`: `:2843-2870`, `:6165-6192`, `:8343-8348`;
- `langselect.cxx:120-142`;
- `lokclipboard.cxx:176-192`;
- `transfer.cxx:1510-1523`.

All of them hold.

## 1. What any link costs, once

All of these are paid once per link, whatever the link carries:

- a new profile `e2-editor-v21` with its own Makefile block and define;
- the v20 profile archived first. The v20 `.o` files are already stale (handoff 10-16), so `make -n` will show recompiles;
- the owner runs `make`;
- X1 with declared deltas, M1-1, and `what_the_link_ships`;
- a new worker pin;
- a shell generation (v74) for any SDK, client or page change;
- every runner's page pin moved;
- host 0.2.25, then `BINDING`;
- the full count chain (about 8 h, in the owner's window).

So the batch should carry everything that is ready. But **an item whose design is not settled holds the whole link back.** Readiness, not the queue, decides the scope.

## 2. The seven items, by readiness

### 2.1 Finding 142: `move-document-start` / `move-document-end` (ready to specify)

- **Value.** Data damage, observed. After Ctrl+Home a Backspace deletes where the caret really is: one character of 「LD-PAGE-01」 in arm `press-after-ctrl-home`.
- **Design direction.** Use the key path, `Key::HOME|Mod1` / `Key::END|Mod1`, as select-all already does with `Key::A|Mod1` (`probe_engine.cpp:5674-5691`).
  - It is not `.uno:GoToStartOfDoc`. That is the mutation route (finding 067's engine half), and a UNO dispatch jumps keys still queued in core, which is finding 137's class. The hand-test README's "`.uno:` through the existing move machinery" contradicts itself.
- **Identity work** (fact sheet item 3(d)):
  - wire ids 22/23 and internal ids 24/25;
  - **both bounds move**: `kMaxInternalEditorAction` 23→25 and `kMaxExternalAction` 21→23. This is CLAUDE.md's silent-total-refusal rule;
  - by `editor_api.h:30-35`, ABI 4→5;
  - the builder hard-codes `ABI_VERSION = 4` and ids `1..21`;
  - X1 has no flag for a *changed* leaf (`abiVersion`). Adding one is a new use of X1, as its declared-delta flags were (§15.3);
  - the worker id table, the client and session sets (`BOUNDARY_CAPABLE_MOVES`?), the page `KEY_ACTIONS` (before `if (accel) return;`, `:2950`), and `ACTION_LABELS`.
- **Open.** A spec settles these after native arms:
  - the gestures: `collapsed` only, so on a range the page clicks first through `moveFromPoint`; or range gestures, which would need native characterisation;
  - Writer's behaviour inside a table cell, in a document that starts with a table, and in a header or footer;
  - whether the move verifies its target. Today no move does.

### 2.2 Markdown paste, the owner's A (needs native arms, then a spec)

- **Value.** A feature the owner asked for.
- **Design direction.** LOK `paste(doc, "text/markdown;charset=utf-8", …)`. This is exactly Collabora's AI-sidebar call (`kit/ChildSession.cpp:1896`).
  - The LOK clipboard never synthesises a Markdown flavour (`lokclipboard.cxx:176-190`), so plain Ctrl+V stays plain by construction.
  - Shape: a document-level export gated by a manifest declaration, as `redo` and `pageRectangles` are. Then there is no editor-ABI change and no capability change.
- **Risks to measure natively first** (all inference until measured):
  - **CJK decoding.** The byte flavour is decoded with `osl_getThreadTextEncoding()` (`transfer.cxx:1517`), and the WASM codeset is unmeasured.
  - A remote image URL (`swmd.cxx:691`).
  - A modal error dialog on a read error (`swdtflvr.cxx:2310`).
  - Wiki links that use the app language.
  - How many Undo steps one paste makes.
  - What happens on a range.
  - The postcondition: `doc_paste` returns true whatever the import did (`init.cxx:6165-6192`), so the engine needs its own check.
- **Page.** Where the entry point goes, and how the text is read: `navigator.clipboard.readText()` with its permission prompts, which are measured per browser on the host route, or "arm, then Ctrl+V". The E1-C-bound adapters (`187706b2…`) cannot carry it, so the new path lives in `editor-shell-v2/` and the page.
- **The first WASM run happens only after a link.** The engine hard-codes the MIME. A diagnostic profile would move that run before the spec; see §4 step 1d.
- **Correction to the research note.** Its 「Collabora Online 也走這條路」 is overstated. cool#15535 is core import fixes, not a Paste Special UI.

### 2.3 A manifest field that declares C (small; depends on 2.5)

- **Value.** Tools are honest about C. **Four** tools key on the wasm string today, not two:
  - the merge runner;
  - `judge_held_into_refusal.py`, which keeps its own copy of the constant;
  - `judge_counted_m2.py`;
  - `check_m3_production_ui.py`.
- **Design direction.** A flag the builder is told, like `--page-rectangles`.
- **Open:**
  - the name and value. It must tell window-C from an immediate-answer C if 2.5 lands;
  - what the builder checks before it declares;
  - the rule for v20 (fragment present, field never present);
  - whether product code consumes the field;
  - which §34.4 category the four tool edits fall in. The byte keying already judges a v21 correctly, so there is no execution witness. That needs a ruling.

### 2.4 `handleEditorPlaceCaret` completing on `TEXT_SELECTION` (recommend: not in v21)

- **No product effect alone.**
  - The session sends open-range clicks down the v67 polling path (`narrow-editor-v2-session.js:723`), which never asks the engine.
  - Collapsed clicks never produce a `TEXT_SELECTION`.
  - The gain ("one path instead of two") needs a session change too.
- **Design trap.** In 54/54 native moving clicks, `TEXT_SELECTION` arrives *before* the cursor callback (a subagent's tally of `findings/evidence/129/native`, fact sheet item 1(b); not re-tallied by the main session). Completing on the first one would reply with the pre-click caret. That is the defect §9 found for moves on a range. §10.1's transition rule avoids it but gains nothing for the 252/306 own-point clicks.
- The blank-page click (about 405 ms) is untouched either way.
- This is the same completion question the ordered-commands spec has to answer. Re-raise it there.

### 2.5 An immediate answer at the document start or end (recommend: not in v21 as specified; see A/B below)

- **Value.** Today the first press costs 2.25 s at the document start. **The 0.2.24 release text promises this for "the next link"** (§3.4 and the §4 list).
- **No clean signal exists.** Today's no-op is verified only as "K1 selected nothing for 2.25 s". Public LOK has no "caret at the document start" query.
- **The designs and their costs:**
  - **(a) A pre-check before K1.** It needs an internal-API translation unit; the precedent is compiled only for the a11y core. It runs ahead of keys still queued in core, which is finding 137's class: a press can be lost silently. It must also exclude the L-C-number-or-indent positions (ii) and (iii), and nothing can see those.
  - **(b) A FIFO marker after K1.** This is the ordered-commands spec's candidate B, and it does not exist yet.
  - **(c) A shorter window, from a measured K1 latency.** This widens L-C-late-K1: a K1 that arrives late leaves a selection, and the next typed character replaces it. That is data damage, rare.
  - **(d) Remember a standing no-op.** It does nothing for the first press, and the page already holds presses (141).
- **Side effect.** Any of these removes §17.4's only positive control for Rbs and Rdel (the busy period of at least 2,000 ms). The count reading would need a new one.

### 2.6–2.7 `Language=` (with 031's fix and the pins) and D12 (recommend: native arms now, decide after)

- **Value is smaller than when it was queued.**
  - New documents already get their languages, paper and fonts from the 30 templates (D5, hand-tested 10-14).
  - `Language=` affects style-less documents and the number and date locale. It does not fix fonts.
- **The design is large:**
  - `oxsdk_document_open` has no options slot, so the SDK ABI changes;
  - the tag is per user and computed by the host (`data-locale` comes from `findLocale`, which D3 rejects);
  - the three fallback pins need core-internal setters, through a bridge TU with `LIBO_INTERNAL_ONLY`;
  - the option must reach `_openFresh` and every recovery reopen without editing the E1-C-bound `editor-shell/editor-session.js`.
- **"031's fix" is not defined.** The finding lists four directions and chose none. Since 030 the barrier reads HTML tags, not localized names. The 031 tripwire watches the build image, not the shipped `base-r5-no35` pack.
- **D12 is only a choice of tag mapping.** By source reading, bare `en` gives A4 (it agrees with the template) and `en-US` gives Letter (`paper.cxx:231`, `:362-368`). Not measured.
- **analysis-1 is probably wrong about the Western slot.** `langselect.cxx:139-141` overwrites it with en-US, so the browser leaks only into the Asian and Complex slots. A native arm with `LANG=de_DE` and `Language=zh-TW` decides it.

## 3. Scope: the owner's choice

- **A (recommended): v21 = 142 + Markdown paste + the C field.**
  - 2.4 and 2.5 move to the ordered-commands batch, where their completion and FIFO questions belong.
  - 2.6–2.7 get native arms now, and a decision after.
  - The release text gets one appended correction: the boundary promise moves to the ordered-commands batch.
- **B: A, plus 2.5 by option (c), a measured shorter window.**
  - It keeps the release-text promise.
  - It trades a rarer, sooner data-damage residual for the 2.25 s. That is a risk decision; the main session would offer it to fable with the measured K1 latencies.
  - It first needs a census of K1 arrival times from existing logs, if they record them. Not yet checked.
- **C: all seven in v21.** The link waits for the host-side `Language=` design and for a design for 2.5 that does not yet exist. Slowest.

## 4. Order of work under A (no link until step 6)

1. **Native arms** (no link; small single-file `c++` compiles against `build-native-26-8`, not `make`):
   - **a.** 142: Ctrl+Home and Ctrl+End from these starting shapes: mid-text, the document start, the end, the first and a middle table cell, a document that starts with a table, a header, a single-paragraph range and a cross-paragraph range. Record the callbacks, the caret, and the `.uno:Undo` top.
   - **b.** Markdown corpus through `paste("text/markdown;charset=utf-8")`:
     - positions: an empty document, a template-made new document, the start of a paragraph with text, inside a bulleted paragraph, and on a range;
     - CJK and CTL text, a remote image, and an input that fails (does a dialog block?);
     - Undo count; keep `content.xml`.
   - **c.** For later: the `Language=` arms on analysis-1's probe (it already takes an options argument).
   - **d. Optional, the owner's `make`:** a diagnostic profile that carries only a Markdown paste path, so the first WASM run (encoding!) comes before the spec is final. Precedent: `e2-locale-attribution`.
2. **Spec** `specs/SPEC-M3-link-batch-v21.md` (zh-TW). Criteria are written before any implementation: ABI 5, the X1 changed-leaf flag, the C field's semantics and its v20 rule, Markdown's postcondition and limits.
3. **Two-seat review**: opus plus `codex exec -s read-only`. The codex MCP failed to connect this session.
4. **Implementation**: engine, worker, builder, X1, shell and page; red cases first; model and unit tests.
5. **Witness** on the no-host page, then freeze shell generation v74.
6. **Archive v20.** The owner links v21 (v20's link took about 2 minutes). Post-link checks, then archive v21.
7. **WASM shakedown**, which is Markdown's first WASM run unless 1d was done. Then host 0.2.25 (ask the owner before installing), bind, and the count chain in the owner's window.

## 5. Not in this link (unchanged)

- ODS and Calc (a separate core step).
- Shift+Arrow and moves on a range: the ordered-commands spec.
- Block identity.

## 6. Decision (2026-10-16; append only)

- The owner was asked to choose A, B or C. The answer was 「好，請開始」. It is taken as **A, the recommended scope**: 142, Markdown paste and the C field. If the owner meant otherwise, the correction goes here.
- **The release text is corrected in place, with a revision-log row.** Its two "next link" promises now say "not in v21":
  - `Language=` waits for native arms and a decision;
  - the boundary answer moves to the ordered-commands batch.
- **§4 step 1 starts now.** The native arms are 1a (142), 1b (Markdown) and 1c (`Language=`). Step 1d (a diagnostic profile, which needs the owner's `make`) is not started; it is offered after 1b reads.
- **Later the same day: review 1 and three owner answers.** Review 1 had two seats (`handoff/link-batch-v21/review-1-*.md`), and the dispositions are in spec §9. The owner then chose A three times (spec §9.13):
  - the Markdown entry is a dialog with a text box;
  - the Ctrl+Home/End readback stays at 250 ms;
  - **the C declaration is withdrawn from v21**. Nothing in this batch reads it, so it ships with its first reader in the ordered-commands batch.
  
  v21 is now 142 plus Markdown paste.
