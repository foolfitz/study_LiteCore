# The 083 path, ruling 3 Q5.2: native arm for a second selection after `select-text-returned-none`

Registered 2026-10-30 ~17:20 +0800, before `tool/f083_native.cpp` was compiled.

**Authority.** The owner, 2026-10-30 ~17:05 +0800, answering the main session's A/B/C/D question after handoff 10-30i: 「A. 量 083 那格」. The ruling is `../RULING-fable-2026-10-30-c.md` Q5.2: candidates "to measure, not prescriptions"; "native arm first: a5, a4, a sham on a5, a document with a table/section before the last paragraph, and the Q sequence confirmed to clear SelectAll's selection."

**If this is never run:** ruling 3 section 4 and spec v27's `L-083-stays-a-toast` stand. The 083 sentence stays on every bullet pressed on a last empty paragraph.

## The question

On the ordered engine's collapsed route, v27's `.uno:SelectText` selects nothing when the empty paragraph is the last one. That is the 083 path (`select-text-returned-none`; a4 and a5 10/10 in `../native/`). The question has three parts:

1. Is there a second selection, made in the same command, whose `text/html` readback lets the existing predicate judge the dispatch paragraph? If not, does a minimally extended one?
2. Does it judge correctly in both directions?
3. Does the existing Q restore clear it?

## Candidates

- **SA: `.uno:SelectAll`.** This is `SID_SELECTALL`, handled by `SwWrtShell::SelAll` (`sw/source/uibase/wrtsh/select.cxx:131`).
  - On a one-paragraph document it should select exactly that paragraph. One block means the existing parser and `formatBarrierReadbackSatisfied` apply unchanged: rule ONE below.
  - On a multi-paragraph document it selects everything, so the readback is multi-block and rule ONE refuses (fail closed). Judging it needs a LAST-block field: rule LAST.
  - Read in the source, not measured:
    - With the caret inside a section, the first SelAll selects the current section only (`GoStart(..., !bIsFullSel)`, select.cxx:150-167).
    - A body that starts or ends with a table or section takes `ExtendedSelectAll` (select.cxx:186-201; `StartsWith_`, `sw/source/core/crsr/crsrsh.cxx:910`).
- **CL: `.uno:CharLeftSel`.** This is `FN_CHAR_LEFT_SEL` (`sw/sdi/swriter.sdi:577`), i.e. Shift+Left.
  - From the start of the empty last paragraph it goes one position back, across the paragraph break. That selects from the end of the previous paragraph to the dispatch paragraph, so the dispatch paragraph is the LAST block, and the cost does not grow with the document. Judged by rule LAST.
  - On a one-paragraph document it cannot move, so it predicts NONE.
  - This is the narrowest instance of the ruling's general wording: "a selection that reaches the paragraph from before it so that it is the LAST block".

## The harness

`tool/f083_native.cpp` is `../native/tool/f176_native.cpp` (sha256 `cb4d9f41...`) with one marked addition.

**Addition 5: op `H<.uno:Cmd>[|<json>]~<.uno:Fallback>`.** It runs G (v27's collapsed order), then the fallback only on the 083 path:
1. The dispatch.
2. No restore before the select.
3. `.uno:SelectText` and the synchronous read; `text/html` if TEXT.
4. **Only if that read is NONE:**
   - `postUnoCommand(<Fallback>, null, true)`;
   - the synchronous read;
   - `text/html` if TEXT: the full markup up to 1 MiB, its byte count, and the wall times of the post and of the html call.
5. The Q restore: RESET, START, RESET at the point captured before the dispatch.
6. The read again.

Everything G records is kept.

**Runner.** `../native/tool/run_cells.py` (sha256 `e00ae2cd...`), unedited, as Q6.3 used it:
- mode `uni1ai`, 5 rounds, one process per (cell, round), run-major;
- `nice -n 10`, a fresh profile, `SAL_USE_VCLPLUGIN=svp`, `SAL_LOK_OPTIONS=unipoll`.

Its cell table is replaced by `tool/run_cells_q52.py`. The script per cell is `<setup>,X<name>@<trigger>=<op>,L,S`: Q6.3's form, the locator after the measured step, then the save.

**Core.** `native-lok-26-8/build/instdir/program`, buildid 671c848b, the N1 and 176 core.

## Fixtures

`tool/make_fixtures_q52.py` imports 176's `doc`, `p`, `item` and `EMPTY`. Two fixtures are byte copies of `../native/fixtures/`: `empty-last.fodt` and `two-plain.fodt`. `blank-one.odt` is the host's blank template (sha256 `7e6221b6...`), copied after its hash is checked.

| fixture | body, in order |
|---|---|
| `blank-one.odt` | the host's blank template: one empty paragraph |
| `bulleted-only` | one empty bulleted paragraph |
| `heading-only` | one empty Heading 1 |
| `empty-last` | `Plain first`, empty |
| `two-plain` | `Plain first`, `E1-EMPTY-AFTER` |
| `bullet-then-empty-last` | a bullet item `Bullet before`, empty |
| `table-then-empty-last` | `Plain first`, a 1x1 table `Cell text`, empty |
| `table-first-empty-last` | a 1x1 table `Cell text`, empty |
| `section-then-empty-last` | `Plain first`, a section holding `Section text`, empty |
| `empty-last-in-section` | `Plain first`, a section holding an empty paragraph |
| `long-then-empty-last` | 300 paragraphs `Line NNN ...`, empty |

**The target** in every cell is the LAST `text:p`/`text:h` of the body in document order.

## Cells (27 x 5 rounds = 135 processes)

**How the caret reaches the last paragraph:**
- `k DOWN` in the fixtures where 176 used it (two paragraphs, or a list item then the empty one);
- Ctrl+End twice (`k9221`) where a table or section sits in between, and for the long document;
- nothing on the one-paragraph documents.

**Trigger:** END (a no-op at the end of an empty paragraph, 176's form). The exception is the Enter cell: `DOWN, END`, then RETURN as the trigger.

| cell | class | fixture | action | group |
|---|---|---|---|---|
| sa-a5-blank-one | A | blank-one | bullet | SA-1, SA-5 |
| sa-n5-sham-blank-one | N | blank-one | bullet `On:false` | SA-1 |
| sa-num-blank-one | S | blank-one | number | SA-5 |
| sa-head-blank-one | S | blank-one | heading | SA-5 |
| sa-none-bulleted-only | S | bulleted-only | none | SA-5 |
| sa-body-heading-only | S | heading-only | body (`Text body`) | SA-5 |
| sa-a4-empty-last | A | empty-last | bullet | SA-M |
| sa-a7-enter-last | A | two-plain (End, Enter) | bullet | SA-M |
| sa-a8-after-bullet | A | bullet-then-empty-last | bullet | SA-M |
| sa-n4-sham-empty-last | N | empty-last | sham | SA-M |
| sa-n8-sham-after-bullet | N | bullet-then-empty-last | sham | SA-M |
| sa-t1-table-then-empty-last | A | table-then-empty-last | bullet | SA-M |
| sa-t2-table-first-empty-last | A | table-first-empty-last | bullet | SA-M |
| sa-s1-section-then-empty-last | A | section-then-empty-last | bullet | SA-M |
| sa-s2-empty-last-in-section | A | empty-last-in-section | bullet | SA-M |
| sa-ns2-sham-empty-last-in-section | N | empty-last-in-section | sham | SA-M |
| cl-a4, cl-a7, cl-a8, cl-n4, cl-n8, cl-t1, cl-s1, cl-s2 | as SA's twins | as SA's twins | as SA's twins | CL |
| cl-a5-blank-one | R | blank-one | bullet | recorded (predicted NONE) |
| sa-r1-noop-bulleted-only | R | bulleted-only | bullet (already a bullet) | recorded |
| sa-long-300 | R | long-then-empty-last | bullet | recorded (cost) |

Notes on two cells:
- In `sa-n8`, the first block of the readback is the bullet item. A first-block reading says `ul` there, and the target is not in a list. It is the trap rule LAST must not fall into.
- In `sa-s2` and `sa-ns2`, SelAll inside a section is predicted (read, above) to select only the section. That is one block even in a two-paragraph document.

## Derivations (`tool/read_q52.py`, from the records only)

**A clean round** is 176's definition:
- exit 0, a `done` record;
- env `unipoll` + `uni1ai`, anyInput registered;
- not capped, saved ok.

Plus three conditions of its own:
- the op is H, and its format record carries `fallback`;
- the fallback markup was not truncated;
- there is a `locate` record.

**The fallback markup** is read by a port of `parseFormatReadback` (`wasm_sdk_probe/src/probe_engine.cpp:831`):
- `parsed`, `unknownTag` (and its name), `malformedNesting`, `footnoteApparatus`;
- `listTag`, `blockTag`, `blockCount`, `itemCount`, `multiBlock`.

To these it adds two LAST-block fields:
- `lastListTag`: the innermost open `ul`/`ol` when the last block-level tag opens (`none` if there is none);
- `lastBlockTag`: that tag.

**Expected per action** (`ordered_format.inc:160-202`):

| action | expected |
|---|---|
| bullet | list `ul` |
| number | list `ol` |
| none | list `none` |
| heading | block `h1` |
| body | block `p` |

**Rules:**
- **ONE.** Refused if any of these holds:
  - the fallback type is not TEXT;
  - `!parsed`, `unknownTag`, `malformedNesting` or `footnoteApparatus`;
  - `multiBlock`.

  Otherwise satisfied iff the expected list matches `listTag` (or `none`) and the expected block matches `blockTag`. This is the existing parser and predicate, unchanged, with multi-block refused as on v25.
- **LAST.** Refused as ONE, without the multi-block refusal. Satisfied iff the last-block fields match.
- **FIRST.** Recorded only: ONE without the multi-block refusal, i.e. what the existing predicate says about the first block.

**Ground truth** is the saved FODT's last paragraph: in a list or not, the list's kind (bullet or number, through its list style), heading or not. It "matches the action" as follows:

| action | matches when |
|---|---|
| bullet | in a list, bullet |
| number | in a list, number |
| none | not in a list |
| heading | `text:h` |
| body | `text:p` |

**P3 (the restore).** Both must hold:
- `restoredType` is 0 (NONE);
- the locate record's suffix and prefix are both empty. In every fixture the only empty paragraph is the last one, so this puts the caret in it.

**P0 (the 083 path).** The H op's `.uno:SelectText` read is NONE, so the fallback ran. A deciding cell that fails P0 in a clean round is NOT-ESTABLISHED for its verdict.

## Verdicts

### V1: SA, rule ONE, the one-paragraph document (`sa-a5`, `sa-n5`)

Judged in this order; the first that applies is the verdict.

1. **`ONE-BLOCK-UNSAFE`**: in any clean round of **any** cell of this run, rule ONE is satisfied while the saved last paragraph does not match the action. This is a per-instance property, checked across every cell, not only the two deciding ones.
2. **`NOT-ESTABLISHED`**: fewer than 5 clean rounds, or P0 fails, in `sa-a5` or `sa-n5`.
3. **`ONE-BLOCK-DOES-NOT-VERIFY`**: some clean round of `sa-a5` does not hold every one of the following:
   - fallback TEXT, `blockCount` 1;
   - rule ONE satisfied;
   - saved as a bullet;
   - P3.

   It is fail closed: the toast stays. The same applies if some clean round of `sa-n5` does not hold:
   - rule ONE not satisfied;
   - saved not in a list;
   - P3.
4. **`ONE-BLOCK-HOLDS`**: otherwise.

### Action scope (SA-5)

Read only when V1 holds. For each action:
- **IN-SCOPE**: 5 clean rounds, and in every round P0, rule ONE satisfied, the saved paragraph matching, and P3;
- **OUT-OF-SCOPE**: a clean round that does not;
- **NOT-ESTABLISHED**: fewer than 5 clean rounds, or P0 fails.

### V2: SA, rule LAST, the SA-M cells

1. **`LAST-UNSAFE`**: rule LAST is satisfied while the saved paragraph does not match, in any clean round of any SA cell.
2. **`NOT-ESTABLISHED`**: a cell with fewer than 5 clean rounds or a P0 failure.
3. Otherwise each cell is classified.
   - An A cell is one of:
     - **COVERED**: every round satisfied, with P3;
     - **REFUSED**: every round refused (fail closed);
     - **PARTIAL**: anything else.
   - An N cell is **SAFE** when it is never satisfied and is saved out of a list.
4. **`LAST-HOLDS`**: every N cell is SAFE, every A cell is COVERED or REFUSED, and P3 holds in every clean round. The covered list is reported with it.
5. **`LAST-PARTIAL`**: otherwise.

### V3: CL, rule LAST, the CL cells

The same as V2. `LAST-UNSAFE` is checked over the CL cells.

## Recorded, deciding nothing

- rule FIRST on every cell (predicted: `sa-n8` and `cl-n8` FIRST-satisfied, the first-block trap);
- selection types, the fallback's selected text, markup bytes and wall times (native, not WASM);
- the fallback's `UNO_COMMAND_RESULT`, if one arrives in the window;
- `sa-r1`, `sa-long-300`, `cl-a5`;
- the undo stacks.

## Not measured here (named)

- **WASM and the product path.** That includes the a11y paragraph-identity check: the native harness has no a11y. On the product, an empty paragraph's dispatch and readback fingerprints are the empty-string constant (finding 074), so that check is declined there, as it is today.
- **Images and frames.** On v25 WASM, a select-all over an as-char frame copied back `complex` (`specs/SPEC-M3-select-all-v26.md` section 1). The collapsed route reads that as not TEXT, i.e. fail closed. It is not re-measured natively.
- **Findings 037 and 038** (an inline image or a frame in a footnote wedging the handle on a selection read). A whole-document read reaches every such paragraph. This cannot be measured natively.
- **Other caret positions:** the caret in a table cell, a frame or a footnote; hidden tracked changes.
- **Time on WASM.**

## Amendment 1 (2026-10-30 ~17:25 +0800, after the smoke, before the counted run): nothing changes

**The smoke** is in `smoke/`: one round each of `sa-a5`, `sa-n5`, `sa-a4`, `sa-t2`, `sa-s2` and `cl-a4`, with binary `build-01` (sha256 `b3b4d293...`).

- **The blank template.** In `sa-a5` and `sa-n5`, `.uno:SelectAll` reads **NONE**: the type is 0, the text is empty, and there is no markup.
  - A document whose only paragraph is empty has no non-collapsed selection. The ruling's premise, "`.uno:SelectAll` on a one-paragraph document yields exactly one block", does not hold for the empty one.
  - That predicts V1 = `ONE-BLOCK-DOES-NOT-VERIFY`, i.e. fail closed.
- **The multi-paragraph cells** read TEXT:
  - `sa-a4`: `<p>Plain first</p><ul><li><p></p></li></ul>`;
  - `cl-a4`: `<p><br/></p><ul><li><p></p></li></ul>`;
  - `sa-t2`: a body-level `<table>` before the list, which the engine's parser refuses as an unknown tag;
  - `sa-s2`: the whole document, with no section markup. The read "SelAll in a section selects the section only" did not show. By source, an empty paragraph that is the section's only content is already at both section ends, so `bIsFullSel` is true.

**The criteria, the cells and the binary are not changed.** The counted run judges them as registered.

**Read, not measured.** `getTextSelection` on a collapsed selection is not a candidate. `SwTransferable::GetData` copies the (empty) selection into a fresh document (`lclOverWriteDoc`, `sw/source/uibase/dochdl/swdtflvr.cxx:530`), so its markup would describe that document's default paragraph, not the dispatch paragraph. Writer's `getCommandValues` set (`sw/source/uibase/uno/loktxdoc.cxx:1183`) has no paragraph or list state read.

## Amendment 2 (2026-10-30 ~18:10 +0800, after the counted run, before these cells ran): the four other paragraph actions on the multi-paragraph last line

**Why.** The owner chose 「A. 做多段文件最後一行」 (~18:05): build the multi-paragraph last line, with the design going to fable first. That means a `.uno:CharLeftSel` fallback and a last-block field. The counted run measured only the bullet on multi-paragraph documents (V3). Ruling 3's precedent (Q6.3) is native cells before the scope is pinned. This amendment adds cells only. **V1-V3 and their results are not touched.**

**The cells.** All use CL (`H<cmd>~.uno:CharLeftSel`), 5 rounds, the same binary (`build-01`), the same runner (`../native/tool/run_cells.py`, imported unedited), and the cell table in `tool/run_cells_q52_actions.py`. Fixtures are made by `tool/make_fixtures_q52_actions.py`, into a new directory.

| cell | class | fixture (body) | dispatch | judged as |
|---|---|---|---|---|
| cl-num-empty-last | A | `Plain first`, empty | `.uno:DefaultNumbering` On:true | number (`ol`; saved in a number list) |
| cl-none-bulleted-last | A | `Plain first`, an empty bullet item | `.uno:RemoveBullets` | none (`none`; saved not in a list) |
| cl-head-empty-last | A | `Plain first`, empty | `.uno:StyleApply` Heading 1 | heading (`h1`; saved `text:h`) |
| cl-body-heading-last | A | `Plain first`, an empty Heading 1 | `.uno:StyleApply` Text body | body (`p`; saved `text:p`) |
| cl-nnum-after-number | N | a number item `Numbered before`, empty | `.uno:DefaultNumbering` On:false | number (the trap: the previous block is `ol`) |
| cl-nhead-after-heading | N | a Heading 1 `Heading before`, empty | `.uno:StyleApply` of a style that does not exist | heading (the trap: the previous block is `h1`) |
| cl-nnone-noop-bulleted-last | N | `Plain first`, an empty bullet item | `.uno:DefaultBullet` On:true (a no-op there) | none |
| cl-nbody-sham-heading-last | N | `Plain first`, an empty Heading 1 | `.uno:StyleApply` of a style that does not exist | body |

**How the caret is reached:** `k DOWN`, then the trigger END, as `cl-a4` did.

**How an N cell is judged.** It takes the expectation of the action in its last column. "The saved paragraph matches" means the saved paragraph is in that action's target state, which an N cell's must not be. The style that does not exist is `"LiteCore No Such Style"` (ParagraphStyles).

**Verdict V4 (scope of rule LAST + CL on the multi-paragraph last line), by `tool/read_q52_actions.py`:**
- **`LAST-UNSAFE`**: in any clean round of these eight cells, rule LAST is satisfied while the saved paragraph matches the action's target state for an N cell, or does not match it for an A cell.
- Otherwise, per action:
  - **IN-SCOPE**: its A cell has 5 clean rounds, each with P0, LAST satisfied, the saved paragraph matching, and P3; **and** its N cell has 5 clean rounds, each with P0, LAST not satisfied, the saved paragraph not in the target state, and P3;
  - **NOT-ESTABLISHED**: either cell has fewer than 5 clean rounds or a P0 failure;
  - **OUT-OF-SCOPE**: anything else.
- The bullet's scope is V3 (`cl-a4`, `cl-a7`, `cl-a8`, `cl-n4`, `cl-n8`), already `LAST-HOLDS`.

**Recorded only:** rule FIRST (predicted fooled on both traps), the undo stack, bytes and times.

**If never run:** the v28 spec could pin only the bullet on this path.

### Amendment 2, correction 1 (~18:22 +0800, while the cells ran, before any of their records was read)

**The error.** Amendment 2's `LAST-UNSAFE` clause reads "satisfied while the saved paragraph matches the action's target state for an N cell". That is inverted. It contradicts two things:
- the definition of UNSAFE used in V1-V3 (a rule satisfied while the saved paragraph does **not** match the action);
- the same amendment's N-cell condition.

It was found while writing `tool/read_q52_actions.py`.

**It reads instead:** `LAST-UNSAFE` = in any clean round of these eight cells, rule LAST is satisfied while the saved paragraph is **not** in the target state of the action the cell is judged as.

An N cell whose dispatch did apply (saved in the target state) is not unsafe. It fails its own condition ("the saved paragraph not in the target state"), so its action is OUT-OF-SCOPE. Nothing else changes.

## Amendment 3 (2026-10-30 ~18:40 +0800, after amendment 2's result and a one-round smoke, before these cells' counted run): real Heading 1 paragraphs

**Amendment 2's result, as registered.** V4 = **`LAST-UNSAFE`**: `cl-nbody-sham-heading-last` was satisfied for body in 5/5 while its saved last paragraph is `text:h`. That verdict stands.

**What it was, measured.** 176's heading markup (`<text:h text:style-name="Heading_20_1" text:outline-level="1"/>` in a document with no `office:styles`) loads as an automatic style `P1` with parent **Standard** and a direct outline level 1. LibreOffice saves it back that way: `out-actions/cl-nbody-sham-heading-last/r1.fodt.gz`, and the same in `cl-nhead-after-heading`. So it is a `text:h` (the ground truth's heading) that is not a Heading 1 paragraph (the engine's heading: the HTML tag the export derives from the style), and the HTML export writes it as `<p>` (both cells' readbacks).

Two consequences:
- The negative cells for heading and body did not test what they were registered to test.
- 176's Q6.3 cell b1 used the same markup (`empty-heading-mid`). Its "body on an empty heading" started from this pseudo-heading, not from a Heading 1.

**The smoke** (`smoke-headings/`, one round each of the cells below; recorded, judging nothing):
- the real fixtures save back as `Heading_20_1`;
- the untouched empty Heading 1 reads `<h1>` (CL last block, SelectText first block);
- the pseudo-heading with text reads `<p>`.

**Cells** (5 rounds; `tool/run_cells_q52_headings.py`, fixtures `tool/make_fixtures_q52_headings.py`). "Real" means `Heading_20_1` defined in `office:styles` (display name "Heading 1", default outline level 1). Every cell is op H with the CL fallback; on a paragraph `.uno:SelectText` can read, H is G and the fallback does not run.

| cell | class | route | fixture | dispatch | judged as |
|---|---|---|---|---|---|
| cl-nhead-after-realheading | N | 083 | a real Heading 1 `Heading before`, empty | the style that does not exist | heading |
| cl-body-realheading-last | A | 083 | `Plain first`, a real empty Heading 1 | `Text body` | body |
| cl-nbody-realheading-last | N | 083 | the same | the style that does not exist | body |
| g-body-real-empty-heading-mid | R | v27 collapsed | `Plain first`, a real empty Heading 1, `E1-EMPTY-AFTER` | `Text body` | body |
| g-nbody-real-empty-heading-mid | R | v27 collapsed | the same | the style that does not exist | body |
| g-nbody-pseudo-heading-text-mid | R | v27 collapsed | `Plain first`, the pseudo-heading with text `Pseudo heading`, `E1-TEXT-AFTER` | the style that does not exist | body |

**Precondition (fixture validity).** The untouched real Heading 1 reads `<h1>` in every clean round in both places:
- `cl-nbody-realheading-last`: the CL last block;
- `g-nbody-real-empty-heading-mid`: the SelectText first block.

Otherwise V5 is NOT-ESTABLISHED.

**V5 (by `tool/read_q52_headings.py`), the 083 path with real headings, rule LAST + CL:**
- **`LAST-UNSAFE`**: in any clean round of the three 083 cells, LAST is satisfied while the saved paragraph is not in the target state.
- Otherwise, per action:
  - **heading**: the A cell is `cl-head-empty-last` from amendment 2. Its Heading 1 was applied by the dispatch, so it is valid as it stands. The N cell is `cl-nhead-after-realheading`.
  - **body**: the A cell is `cl-body-realheading-last`, the N cell `cl-nbody-realheading-last`.
  - Each action is IN-SCOPE / OUT-OF-SCOPE / NOT-ESTABLISHED by amendment 2's per-action rule.

**Recorded** (the v27 route, rule FIRST on the SelectText readback, as v27 judges it):
- the two real mid-document cells;
- the pseudo-heading with text: predicted satisfied for body while saved `text:h`. That is a limitation of the heading/body postcondition that predates v28: the HTML heading is the style's, an outline level alone does not make one.

Number and none keep their amendment 2 status; their fixtures have no heading.

**If never run:** heading and body are not pinned on this path.

## Amendment 4 (2026-10-30 ~19:25 +0800, before these cells ran): ruling 4's native cells before the v28 spec

**Authority.** Fable ruling 4 (`../RULING-fable-2026-10-30-d.md`), Q4.3-4.5 and section 4 item 6. Same binary (`build-01`), same runner (`../native/tool/run_cells.py`, imported unedited), mode uni1ai, 5 rounds. The cell table is `tool/run_cells_q52_v6.py`, the fixtures `tool/make_fixtures_q52_v6.py` (byte copies of `fixtures-actions/` and `fixtures/` files, plus one new fixture). Output goes to `out-v6/`.

**Stated plainly (ruling 4 Q4.3).** Amendment 2's records of the four number/none cells were read before this amendment: the README table "the per-action rule applied to the other cells". This re-run exists so that a run counted under a registered criterion post-dates that reading. The earlier records are not re-used for V6.

| cell | class | fixture | dispatch | judged as | group |
|---|---|---|---|---|---|
| cl-num-empty-last | A | empty-last | `.uno:DefaultNumbering` On:true | number | V6 |
| cl-nnum-after-number | N | number-then-empty-last | `.uno:DefaultNumbering` On:false | number | V6 |
| cl-none-bulleted-last | A | bulleted-last | `.uno:RemoveBullets` | none | V6 |
| cl-nnone-noop-bulleted-last | N | bulleted-last | `.uno:DefaultBullet` On:true | none | V6 |
| cl-long-300 | A | long-then-empty-last (300 lines, then empty) | `.uno:DefaultBullet` On:true | bullet | V7 |
| cl-a6-end | A | empty-empty-last (`Plain first`, empty, empty) | `.uno:DefaultBullet` On:true | bullet | V7 |
| cl-n6-end | N | empty-empty-last | `.uno:DefaultBullet` On:false | bullet | V7 |

The first four rows are the same cells as amendment 2, by name and table entry. How the caret is reached:
- V6: `k DOWN`, then END (as amendment 2);
- `cl-long-300` and the a6/n6 cells: Ctrl+End twice, then END.

The ruling's user path is "type, Enter, Enter, bullet"; Ctrl+End reaches the same last empty paragraph.

### V6: number and none, by `tool/read_q52_v6.py`

Amendment 2's per-action rule with correction 1, over these four cells:
- **`LAST-UNSAFE`** if LAST is satisfied in any clean round while the saved paragraph is not in the target state.
- Otherwise each action is **IN-SCOPE** iff:
  - its A cell has 5 clean rounds, each with P0, LAST satisfied, the saved last paragraph matching, and P3;
  - and its N cell has 5 clean rounds, each with P0, LAST not satisfied, the saved last paragraph not matching, and P3.
- **NOT-ESTABLISHED** if either cell has fewer than 5 clean rounds or a P0 failure.
- **OUT-OF-SCOPE** otherwise.

### V7: the long document and two empties at the end

- **`cl-long-300` COVERED** iff 5 clean rounds and, in each:
  - P0;
  - the fallback reads TEXT;
  - `blockCount == 2` (ruling 4's rule iii);
  - LAST satisfied, the saved last paragraph a bullet, P3.

  Recorded: the fallback markup's bytes, against the 561-581 of the short documents. This is the measurement behind "constant cost" (ruling 4 Q1.4).
- **`cl-a6-end` COVERED** iff 5 clean rounds and, in each:
  - P0, TEXT, `blockCount == 2`;
  - LAST satisfied, the saved last paragraph a bullet;
  - **the saved second-to-last paragraph not in a list** (the bullet went to the paragraph the caret was in);
  - `restoredType == 0`.

  The locator half of P3 does not discriminate here: two empty paragraphs give the same empty suffix and prefix. It is recorded, not judged.
- **`cl-n6-end` SAFE** iff 5 clean rounds, each with P0, LAST not satisfied, the saved last two paragraphs not in a list, and `restoredType == 0`.
- **`V7-UNSAFE`**: LAST satisfied while the saved last paragraph is not a bullet, in any clean round of the three cells.
- **Verdict:**
  - `V7-HOLDS` when all three hold;
  - `V7-UNSAFE` as above;
  - `NOT-ESTABLISHED` for fewer than 5 clean rounds or a P0 failure;
  - `V7-PARTIAL` otherwise.

**Stop rule** (ruling 4 Q4.5): a round where a rule is satisfied while the saved paragraph does not match takes that action out of scope and is a finding.

**If never run:** ruling 4 section 5. The v28 spec may not cite number/none, CL's constant cost, or the two-empties path as measured.
