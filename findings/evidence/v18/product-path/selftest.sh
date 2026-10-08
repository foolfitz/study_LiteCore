#!/bin/bash
# Page red case for the product-path reader (../../v17/product-path/judge.py), unfiltered (opus review item 15:
# selftest-output.txt, committed in 15eca506, kept only grep'd lines and its "P2 notes:" line lost its payload).
# A: v17's 12 reports under v17's own label and page, expected P1-P3 HIT.  B: the same reports with v18's page
# cfc8ba1d as the candidate page, expected P2 MISS with the differing pages in its notes.
# Note: this reader exits 0 on a MISS too (measured here, case B); its verdict is the SUMMARY line, not the exit code.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
J=$HERE/../../v17/product-path/judge.py
D=$HERE/../../v17/product-path
echo "### A. v17's reports, v17's page (expect P1-P3 HIT)"
python3 -I "$J" --dir "$D"; echo "exit $?"
echo; echo "### B. v17's reports, v18's page cfc8ba1d (expect P2 MISS)"
python3 -I "$J" --dir "$D" --candidate v17 --candidate-page cfc8ba1d54dc4bef52baebc34f9d5f60ffe9cc4af9bee8c7a326bb02b2221cda; echo "exit $?"
