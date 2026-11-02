# F3-84 (2026-11-02)

`tools/run_v84_f3_clipboard.py` (one press per format arm, finding 178) per browser. Read by `tools/read_v83_f3_equal.py --baseline baseline-f3-83`, whose two entries are links to F3-83's `diag-single-press/{chrome-1,firefox-1}`.

Verdict `F3_83_EQUAL`: every check's outcome equals F3-83's on both browsers, with no declared move. Self-test `ALL_RED`, 8 mutations. The verdict's name is the reader's; the reader is not derived because it takes `--baseline`.

Both runs exit 1. That is the runner's own `ok`, false on F3-83 too, and the reader compares it with the baseline.
