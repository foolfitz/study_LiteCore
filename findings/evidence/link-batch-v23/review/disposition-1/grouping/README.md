# Undo grouping hides a real deletion from the at-return undo proof (measured natively, 2026-10-20)

This settles the opus seat's Q6(2)/Q7.1 (`../../opus-review-1.md`). The seat inferred the problem from source and checked it on a re-implementation of two functions, not on LibreOffice. This is the measurement on LibreOffice.

## What ran

| item | value |
|---|---|
| harness | `../../../native/ordered-commands/tool/oc_native.cpp` at HEAD, source sha256 `c722de38…`; the commit-time build line of `smoke-n1/build.txt`, with absolute paths |
| binary | sha256 `3fda8963…`, byte-identical to the N1 binary |
| core | `native-lok-26-8/build/instdir/program` (671c848b) |
| fixture | `underscores.fodt`: `../../../native/ordered-commands/fixtures/abcd.fodt` with its paragraph replaced by `Name: ` followed by 30 `_` |
| rounds | one round per cell; 4 processes, all exit 0 |

The arms:
- **g1**: trigger End (the caret goes to the paragraph's end), then 25 × Backspace (`K1283`).
- **g2**: setup Home and Right ×5, trigger Right (the caret goes after `Name: `), then 25 × Delete (`K1286`).
- Each arm ran in two modes:
  - `uni1`: unipoll, one op per poll, which is candidate C's drive;
  - `seq`: threaded, each op settled, which is Writer's own order.

At each op's return the harness reads the whole `.uno:Undo` payload (`atReturn.undo`). `read_grouping.py` compares each read with the one before it. Its output is `reader-output.txt`.

## Result

- In every cell, all 25 presses deleted a character: the saved paragraph is `Name: _____`, so 25 of the 30 underscores are gone.
- **`uni1`, both arms:** ops 20–25 return an undo payload that is byte-identical to the previous op's, although each of those ops deleted a character. Writer merged them into one `SwUndoDelete`, whose top comment had saturated at `Delete “________..._______”`. That is 6 of 25 presses.
- **`seq`:** the same, one op later (ops 21–25). In the threaded mode the at-return read can come before the posted key has run.
- **g2 is the case that gives the wrong meaning under spec §5.4/§5.5:**
  - forward Delete moves neither the caret nor the selection;
  - after op 20, "undo, caret and selection unchanged" holds while a character was deleted;
  - the spec then answers `verified-boundary-noop`, `changed:false`, revision unchanged;
  - the frozen client accepts that (`narrow-editor-v2-client.js:372-374`), so the page's model of the document is now stale.
- **g1** (Backspace moves the caret) falls through §5.4/§5.5: neither named outcome applies.

The source lines (read again by the main session):
- the merge: `sw/source/core/doc/DocumentContentOperationsManager.cxx:4648-4666`;
- the comment: `undel.cxx:842` → `ShortenString(…, nUndoStringLength, …)`, `undobj.cxx:1626-1643`;
- the payload fields: `index`, `comment`, `viewId`, `dateTime` (`svl/source/undo/undo.cxx:1310-1318`).

The seat predicted the payload would stop changing at press 22; it stops at 20. The mechanism is the same.

## What this does and does not show

- It shows that "the `.uno:Undo` payload is unchanged" does not imply "the key did nothing". It holds for a run of 20 or more equal characters deleted in one direction within one paragraph.
- It shows nothing about whether a different witness would be sound. That is a design question for the ruling (`../DISPOSITION.md`).
- Today's product does not reach this. Mid-text caret deletes complete through the barrier (`verified-selection-delete`), not through the undo proof. §5.4 moves every caret delete to the undo proof, and that move is what makes this reachable.
