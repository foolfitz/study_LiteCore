#!/usr/bin/env python3
"""Judge gate condition 4a from `probe_aria_projection.py` records.

The probe reports; this judges.  They are separate because the probe predates
any threshold -- it says so in its own docstring -- and 4a's terms were fixed
on 2026-08-29, before any run that would satisfy them
(`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, addendum part 1 §A-1).

Terms, verbatim from the plan:

  1 Identity      built via `repointed_page()` with `--candidate-profile`; the
                  report carries a pageSha256 equal to the soak reports'.
  2 Text          all 9 paragraphs of `list-contexts.odt` appear in the AX
                  tree, compared IN CODE against the fixture's content.xml.
  3 Structure     the heading carries AX `level: 1` matching the ODT
                  outline-level; 4 `listitem` nodes inside 2 `list` containers.
  4 Focus         three placements, three distinct readings, each the paragraph
                  targeted, compared in code.
  5 Repetition    three runs, identical on terms 2-4.
  7 Delta         the same instrument on the shipped v8 page shows
                  `documentTextInTree: false` and the region carrying its
                  reason sentence.

Term 6 (the mutation) is a product-path run, not an AX-tree run, and is judged
where it is produced.

Usage:
  check_4a.py --candidate R1.json R2.json R3.json --control V8.json \
              --expect-page-sha256 <sha>
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
FIXTURE = PROJECT / "dist" / "e1-fixtures" / "list-contexts.odt"
OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
TEXTNS = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def fixture_paragraphs() -> list[dict]:
    """The fixture's own paragraphs, read from its content.xml.

    IN CODE, per term 2: a reading compared by eye is a reading nobody can
    re-check, and three different strings would also be produced by a counter.
    """
    with zipfile.ZipFile(FIXTURE) as archive:
        root = ET.fromstring(archive.read("content.xml"))
    body = root.find(f".//{OFFICE}text")
    out = []
    for element in body.iter():
        tag = element.tag.split("}")[-1]
        if tag in ("p", "h"):
            out.append({
                "tag": tag,
                "outlineLevel": element.get(f"{TEXTNS}outline-level"),
                "text": "".join(element.itertext()),
            })
    return out


def names(record: dict) -> list[str]:
    values = []
    for node in record.get("nodes") or []:
        for key in ("name", "value"):
            text = node.get(key)
            if isinstance(text, str) and text:
                values.append(text)
    return values


def judge(candidates: list[dict], control: dict, expect_sha: str | None) -> dict:
    terms: dict[str, dict] = {}
    paragraphs = fixture_paragraphs()

    # ---- term 1
    identity = []
    for record in candidates:
        mirror = record.get("mirror") or {}
        identity.append({
            "kind": record.get("kind"),
            "profile": record.get("profile"),
            "pageSha256": mirror.get("pageSha256"),
            "shim": mirror.get("shim", "unknown"),
        })
    ok1 = all(row["kind"] == "candidate" and row["shim"] is None
              and (expect_sha is None or row["pageSha256"] == expect_sha)
              for row in identity) and bool(identity)
    terms["1-identity"] = {"ok": ok1, "expected": expect_sha, "runs": identity}

    # ---- term 2
    text_rows = []
    for record in candidates:
        present = names(record)
        missing = [p["text"] for p in paragraphs
                   if not any(p["text"] in value for value in present)]
        text_rows.append({"found": len(paragraphs) - len(missing),
                          "of": len(paragraphs), "missing": missing})
    ok2 = all(row["found"] == row["of"] for row in text_rows) and bool(text_rows)
    terms["2-text"] = {"ok": ok2, "runs": text_rows}

    # ---- term 3
    heading = next(p for p in paragraphs if p["tag"] == "h")
    structure_rows = []
    for record in candidates:
        nodes = record.get("nodes") or []
        heading_nodes = [n for n in nodes
                         if str(n.get("role")) == "heading"
                         and heading["text"] in str(n.get("name") or "")]
        levels = [n.get("level") for n in heading_nodes]
        structure_rows.append({
            "headingNodes": len(heading_nodes),
            "headingLevels": levels,
            "levelMatchesOdt": levels == [int(heading["outlineLevel"])] * len(levels)
                               and len(levels) == 1,
            "listContainers": sum(1 for n in nodes if str(n.get("role")) == "list"),
            "listItems": sum(1 for n in nodes if str(n.get("role")) == "listitem"),
        })
    ok3 = all(row["levelMatchesOdt"] and row["listContainers"] == 2
              and row["listItems"] == 4 for row in structure_rows) \
        and bool(structure_rows)
    terms["3-structure"] = {"ok": ok3, "odtOutlineLevel": heading["outlineLevel"],
                            "runs": structure_rows}

    # ---- term 4
    focus_rows = []
    for record in candidates:
        readings = [r for r in (record.get("axReadings") or []) if r]
        placements = record.get("placements") or []
        matched = 0
        for placement in placements:
            reading = placement.get("axReading")
            if reading and any(p["text"] in reading or reading in p["text"]
                               for p in paragraphs):
                matched += 1
        focus_rows.append({"placements": len(placements),
                           "readings": len(readings),
                           "distinct": len(set(readings)),
                           "matchedAFixtureParagraph": matched})
    ok4 = all(row["placements"] == 3 and row["distinct"] == 3
              and row["matchedAFixtureParagraph"] == 3 for row in focus_rows) \
        and bool(focus_rows)
    terms["4-focus"] = {"ok": ok4, "runs": focus_rows}

    # ---- term 5
    signatures = []
    for record in candidates:
        signatures.append(json.dumps({
            "text": sorted(set(names(record))),
            "readings": record.get("axReadings"),
        }, ensure_ascii=False, sort_keys=True))
    ok5 = len(candidates) == 3 and len(set(signatures)) == 1
    terms["5-repetition"] = {"ok": ok5, "runs": len(candidates),
                             "distinctSignatures": len(set(signatures))}

    # ---- term 7
    region = (control or {}).get("regionAtLoad") or {}
    ok7 = (control.get("documentTextInTree") is False
           and isinstance(region.get("text"), str) and bool(region.get("text"))
           and region.get("reason") is not None)
    terms["7-delta"] = {"ok": ok7, "profile": (control or {}).get("profile"),
                        "documentTextInTree": (control or {}).get("documentTextInTree"),
                        "region": region}

    return {"criterion": "gate condition 4a",
            "terms": terms,
            "ok": all(term["ok"] for term in terms.values())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", nargs="+", required=True)
    parser.add_argument("--control", required=True)
    parser.add_argument("--expect-page-sha256", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    candidates = [json.loads(Path(p).read_text(encoding="utf-8"))
                  for p in args.candidate]
    control = json.loads(Path(args.control).read_text(encoding="utf-8"))
    verdict = judge(candidates, control, args.expect_page_sha256)
    text = json.dumps(verdict, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if verdict["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
