#!/usr/bin/env python3
"""The fixture for the block-identity measurement, written to wherever the run
asks for it.

Deliberately NOT a new entry in `create_e1_corpus.py`.  That corpus is frozen:
every fixture's sha256 is recorded in E1-A's list and in the evidence of every
run that used one, and adding a fixture there rewrites `manifest.json`, which is
one of the hash-bound files this tree has already been bitten by
(SPEC E2-B's lesson: a hash-bound file cannot be edited and cannot be added to
either).  This measurement needs a document with four shapes in it and does not
need it to be part of anyone's corpus, so it makes its own and records the
sha256 in the run's context.

The shapes, and which prediction each one is for
(findings/evidence/queue-block-identity/native/PREDICTION.md):

  BI-ANCHOR-ONE      the control: unique text, so an empty payload is a
                     measurement rather than accessibility never being enabled
  (empty paragraph)  P-BI-1, finding 046's cell
  BI-AFTER-EMPTY     the paragraph the overshoot reaches
  BI-TWIN x2         P-BI-4: two paragraphs whose text is identical
  BI-LONG-START ... BI-LONG-END
                     P-BI-3: one line, two clickable x positions, each with its
                     own searchable anchor so neither x is guessed from a width
  BI-LAST            the last line; everything below it is blank page, which is
                     where P-BI-2a and P-BI-2b click

Usage: create_block_identity_fixture.py OUTPUT.odt
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_e1_corpus import create_odt  # noqa: E402

# The long line stays short enough to fit one line on a default A4 text width
# (about 17 cm, so roughly 80 characters at the default size).  If it ever
# wrapped, the two x anchors would be on different lines and P-BI-3 would be
# measuring something else -- so the probe checks that their y matches and says
# so rather than assuming.
BODY = """
 <text:p>BI-ANCHOR-ONE</text:p>
 <text:p/>
 <text:p>BI-AFTER-EMPTY</text:p>
 <text:p>BI-TWIN</text:p>
 <text:p>BI-TWIN</text:p>
 <text:p>BI-LONG-START wwww wwww wwww wwww BI-LONG-END</text:p>
 <text:p>BI-LAST</text:p>
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: create_block_identity_fixture.py OUTPUT.odt",
              file=sys.stderr)
        return 64
    path = Path(sys.argv[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    create_odt(path, BODY)
    print(hashlib.sha256(path.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
