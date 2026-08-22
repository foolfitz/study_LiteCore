#!/usr/bin/env python3
"""Can a paragraph FINGERPRINT locate a paragraph?  Counted, over the corpus.

Written 2026-08-23 to settle roadmap 3.4's structure fork.  The proposal was to
build the document skeleton in the shell (from the ODT it already holds) and
join it to the engine's focused paragraph by recomputing the engine's own
FNV-1a fingerprint.  The join is only as good as the fingerprint's uniqueness,
and 08-16g's block-identity rounds already concluded that paragraph text is a
FINGERPRINT, not an IDENTITY.  This counts what that costs on real documents.

Measured (2026-08-23):

  dist/e1-fixtures   15 docs   3 with a collision (20%)     6 / 121 paragraphs
  test-docs/r7-compat 12 docs  5 with a collision (42%)   182 / 821 paragraphs

  worst: l0-t3-long.odt -- 133 paragraphs, 28 distinct fingerprints,
         110 paragraphs sitting in a collision

So on the realistic corpus roughly a fifth of all paragraphs cannot be told
apart by fingerprint, and one document collapses 133 paragraphs onto 28
identities.  A join built on it cannot answer "which node is focused".

AND THESE NUMBERS ARE THE OPTIMISTIC CASE.  The engine fingerprints the body
AFTER stripping `listPrefixLength`, which this cannot derive from the XML the
way LOK derives it, so it uses prefix 0 -- the whole paragraph text.  Stripping
a prefix maps MORE distinct paragraphs onto FEWER distinct bodies, so the
engine's own collision counts can only be worse.  `emptyStringHashCount` is
reported per document because empty paragraphs all share the FNV-1a offset
basis, and the known heading defect
(`queue-a11y-prefix-swallows-the-paragraph`) folds headings into that same
bucket -- the one class 1.3.1 most needs told apart.

Usage:
  measure_paragraph_fingerprint_collisions.py 'test-docs/r7-compat/*.odt'

FNV-1a 64 over the paragraph body, the same rule probe_engine.cpp uses.  The
list prefix cannot be derived from the XML the way LOK derives it, so this
counts the OPTIMISTIC case: prefix 0, i.e. the whole paragraph text.  The
engine's own numbers can only be WORSE, because stripping a prefix maps more
distinct paragraphs onto fewer distinct bodies.
"""
import collections, glob, json, sys, zipfile
from xml.etree import ElementTree as ET

NS = {'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'}

def fnv(s: str) -> str:
    h = 14695981039346656037
    for b in s.encode('utf-8'):
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return format(h, 'x')

EMPTY = fnv("")
rows = []
for path in sorted(glob.glob(sys.argv[1])):
    try:
        root = ET.fromstring(zipfile.ZipFile(path).read('content.xml').decode('utf-8'))
        body = root.find('office:body/office:text', NS)
        if body is None:
            continue
        paras = [''.join(e.itertext()) for e in body.iter()
                 if e.tag.split('}')[-1] in ('p', 'h')]
    except Exception as error:
        rows.append({"doc": path.split('/')[-1], "error": str(error)[:60]})
        continue
    counts = collections.Counter(fnv(t) for t in paras)
    collided = {f: c for f, c in counts.items() if c > 1}
    rows.append({
        "doc": path.split('/')[-1],
        "paragraphs": len(paras),
        "distinctFingerprints": len(counts),
        "collidingFingerprints": len(collided),
        "paragraphsInACollision": sum(collided.values()),
        "emptyStringHashCount": counts.get(EMPTY, 0),
    })
usable = [r for r in rows if "paragraphs" in r]
bad = [r for r in usable if r["collidingFingerprints"] > 0]
print(json.dumps(rows, indent=2, ensure_ascii=False))
print(f"\ndocuments read: {len(usable)}")
print(f"documents with AT LEAST ONE collision: {len(bad)}"
      f"  ({round(100*len(bad)/max(1,len(usable)))}%)")
print("paragraphs sitting in a collision:",
      sum(r["paragraphsInACollision"] for r in usable),
      "of", sum(r["paragraphs"] for r in usable))
