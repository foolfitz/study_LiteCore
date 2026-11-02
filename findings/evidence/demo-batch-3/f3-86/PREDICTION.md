# Prediction before the clear-wait runs (2026-11-02)

F3-86 moved one cell: Firefox `every-inline-format-reaches-the-document`, PASS to NOT_ESTABLISHED, arm `MKSTROFF`. Written before `diag_clear_wait.py` ran on generation 86.

**Claim.** This is the race finding 178 names and left open, not a v31 defect. The runner waits for the 清除格式 label, which the first of the clear loop's four steps writes. It presses S during the loop; the loop's last step sets strikethrough off and takes the press back. Strike is the last step, which is why only `MKSTROFF` is hit.

**What would refute it.** `diag_clear_wait.py` changes one thing in memory: the two waits go to the toast 「已清除…」, written once after the fourth step. Firefox three times, Chrome once.

- If the claim holds: every run PASS on this cell, `preconditionEstablished` true on `MKSTROFF`, and `read_v83_f3_equal.py` on `firefox-1`, `chrome-1` gives `F3_83_EQUAL`, 46/46.
- If any run still shows `MKSTROFF` unestablished, the claim is wrong and F3-86 stays open: no host 0.2.51 on this reading.

**Separate read.** `rerun/`, the unchanged runner three more times, gives the rate on these bytes. Finding 178 measured 2/120 presses on v29 in Firefox. A rate near 4/4 runs is a change of timing and has to be said, not hidden under "known race".
