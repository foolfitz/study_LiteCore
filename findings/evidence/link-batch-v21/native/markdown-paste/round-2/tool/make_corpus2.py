#!/usr/bin/env python3
"""Write round 2's extra Markdown corpus (UTF-8 bytes) into OUT_DIR. Deterministic.

Usage: make_corpus2.py OUT_DIR

S-items are for T3 (the md4c pre-scan premise, spec section 9.3) and are also
pasted natively to see what Writer really does with them. Every URL points at
this host only:
  127.0.0.1:18765  the runner's logging HTTP listener (answers 404)
  localhost:18768  the runner's logging socket that closes at once (for https)
so no external host is contacted. The PNG in data: URLs is round 1's 4x3 PNG
(round-1 make_corpus.png, imported read-only).
"""

import base64
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True  # never write into round 1's tool/__pycache__
sys.path.insert(0, os.path.join(HERE, "..", "..", "tool"))
import make_corpus  # noqa: E402  (round 1, read only)

L = "http://127.0.0.1:18765"
DATA = "data:image/png;base64," + base64.b64encode(make_corpus.png(4, 3)).decode("ascii")

CORPUS = {
    # Controls: S01 MUST classify as a remote image, S08 MUST NOT (data: only).
    "S01-inline-http": "Before ![remote](%s/s01.png) after.\n" % L,
    "S02-https-hostname": "Before ![remote](https://localhost:18768/s02.png) after.\n",
    "S03-reference": "Before ![alt][r] after.\n\n[r]: %s/s03.png\n" % L,
    "S04-two-images": "![one](%s/s04a.png) and ![two](%s/s04b.png)\n" % (L, L),
    "S05-data-and-remote": "![d](%s) and ![r](%s/s05.png)\n" % (DATA, L),
    "S06-fenced-lookalike": "```\n![x](%s/s06.png)\n```\n" % L,
    "S07-inline-code-lookalike": "Text `![x](%s/s07.png)` end.\n" % L,
    "S08-data-only": "Before ![dot](%s) after.\n" % DATA,
    "S09-indented-code-lookalike": "    ![x](%s/s09.png)\n" % L,
    "S10-escaped-lookalike": "\\![x](%s/s10.png)\n" % L,
    "S11-autolink-png": "<%s/s11.png>\n" % L,
    "S12-image-in-link": "[![a](%s/s12.png)](https://example.org)\n" % L,
    "S13-bang-wikilink": "![[s13.png]]\n",
    "S14-empty-alt-data": "![](%s)\n" % DATA,
    "S15-uppercase-DATA": "![u](DATA:image/png;base64,%s)\n" % DATA.split(",", 1)[1],
    # Whitespace-only inputs, several kinds.
    "W1-spaces": "   ",
    "W2-tabs": "\t\t",
    "W3-ideographic-space": "\u3000\u3000",
    "W4-nbsp": "\u00a0",
    "W5-newlines": "\n\n\n",
    "W6-mixed-ascii-ws": " \t\n \n\t \n",
    # Raw HTML: md4c reports it as HTML (MD_BLOCK_HTML / MD_TEXT_HTML), never
    # MD_SPAN_IMG; Writer hands HTML blocks to its HTML import (swmd.cxx:591-603).
    "H1-comment-only": "<!-- just a comment -->\n",
    "H2-html-block-img": "<img src=\"%s/h2.png\">\n" % L,
    "H3-inline-html-img": "Before <img src=\"%s/h3.png\"> after.\n" % L,
    "H4-inline-img-then-block": "Before <img src=\"%s/h4.png\"> after.\n\n<div>block</div>\n" % L,
    "H5-html-block-img-sized": "<img src=\"%s/h5.png\" width=\"10\" height=\"10\">\n" % L,
    "H6-html-link-stylesheet": "<link rel=\"stylesheet\" href=\"%s/h6.css\">\n" % L,
    # Added after the dry run (H2 alone has no text, so the spec's no-text rule
    # would refuse it by accident): ordinary text plus an HTML-block image.
    "H7-text-then-html-block-img": "Intro text.\n\n<img src=\"%s/h7.png\">\n" % L,
    # No text at all, but not empty: a rule.
    "N1-rule-only": "---\n",
}


def main(argv):
    out = argv[1]
    os.makedirs(out, exist_ok=True)
    for name, text in CORPUS.items():
        with open(os.path.join(out, name + ".md"), "wb") as handle:
            handle.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
