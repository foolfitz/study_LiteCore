# A correct caret moved the harness aim — and the first remedy did not fix it

`run_e2_c_product_path.py`, Chrome, 2026-08-22, on `e2-editor-v4`
(`f923cfa5…`, worker `e6ee92ca…`).

## The observation

| | `bandsAtInducer` | `stateAfterNextOperation` |
|---|---|---|
| v3 (`pp-after-redo.json`, finding 071's dir) | `[83,95] [106,120] [130,143] [1000,1018]` | `recoverable-error` |
| v4, before the remedy | `[83,121] [130,143] [1000,1018]` | `ready` |

The pre-inducer `bands` are **identical** in both. The document, the fixture
and the harness are the same. The two leading bands merge only at the moment
the inducer aims — after a marker has been typed onto that paragraph.

The extra ink in rows 96–105 is the caret. Finding 068's fix put it where it
belongs instead of a commit behind, and where it belongs is the gap between
those two lines. The harness derives its drag from these bands, so the aim
moved and the inducer stopped inducing.

## The remedy that failed

Drop runs narrower than 3px before the merge. Seven unit tests, all passing,
including one either side of the threshold.

`product-path-with-the-failed-remedy.json`:

- `bandsAtInducer` is **still** `[83,121]` — the thing it was for did not move
- `format-a-paragraph-changes-that-paragraph` and
  `ctrl-x-is-handled-by-the-product` fell from PASS to NOT_ESTABLISHED

**That second point was a wrong attribution and later runs overturned it.**
After the revert those two came back PASS in one round and fell again in the
next: they are INTERMITTENT, and the cause was a different change made in the
same batch -- `caret-follows-the-text-you-type` types 36 characters into the
fixture, and those two checks aim by BAND INDEX. `ctrl-x` saw 9 bands one round
and 8 the next, so its drag selected nothing and it reported
`CLIPBOARD_EMPTY_SELECTION`. The check has been moved to a point where nothing
downstream aims by band.

Two runs is one sample for an intermittent thing. This file is about an aim
that something else moved, and the attribution above made the other half of the
same mistake.

The revert stands on the first point alone, and that point is enough: **it did
not do what it was for.**

Reverted.

### Why it failed

The mechanism was right and the **detail** was wrong. It assumed the caret
forms a *separate run* that `BAND_MERGE_GAP` then bridges — so filtering it
before the merge would do. But a caret 16 rows tall spanning a 10-row gap makes
the ink **contiguous**: `counts[y] > 0` holds all the way from the first band's
bottom to the second band's top. There is no separate run to drop. The filter
was applied at the wrong step, and all it actually achieved was changing which
*other* runs survived and merged — which is how two unrelated checks lost their
aim.

### The part worth keeping

**The unit tests all passed and the remedy did nothing.** Those seven tests
checked that a thin standalone run is excluded. That behaviour is real and the
tests were correct about it. It simply was not what happens here. A test can
verify a behaviour perfectly and still be about the wrong thing — the run is
what said so.

## Next

The thing to filter is a **column**, not a run of rows: a caret is a vertical
line crossing many rows and one or two columns wide. That means removing such
columns from the scan *before* row counts are aggregated — and `scan` currently
exposes only `counts`/`firsts`/`lasts`, already aggregated per row. So it is a
change on the scanning side, not in `text_bands()`.

Until then `recovery-returns-what-the-product-promised` stays NOT_ESTABLISHED,
which is honest: the inducer did not induce, so the check can say nothing about
recovery, and it claims nothing.
