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


def establishable(record: dict, paragraphs: list[dict]) -> tuple[bool, str | None]:
    """Whether placement i may be compared against fixture paragraph i.

    Ruling 2 of the 2026-09-05 amendment.  Two conditions, both about the
    mapping rather than about the product:

      * the run found as many bands as the fixture has paragraphs, so the
        bands ARE the paragraphs;
      * where the record says which band each placement came from, that band
        is the placement's own index -- the probe takes the first three bands
        over 40px, and a fixture whose first three tall bands were not its
        first three paragraphs would make the mapping quietly wrong.

    Records taken before `bandIndex` existed satisfy the second vacuously and
    are judged on the first, which is what they were banked under.
    """
    bands = record.get("bandsFound")
    if bands != len(paragraphs):
        return False, (f"bandsFound {bands!r} != {len(paragraphs)} fixture "
                       f"paragraphs: placement i is not paragraph i")
    for placement in record.get("placements") or []:
        band_index = placement.get("bandIndex")
        if band_index is not None and band_index != placement.get("index"):
            return False, (f"placement {placement.get('index')} came from band "
                           f"{band_index}: the mapping does not hold")
    return True, None


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
    #
    # AMENDED 2026-09-05 (Ruling 2).  Until then this asked whether the reading
    # matched ANY fixture paragraph, which a pointer aimed at the wrong
    # paragraph satisfies -- and the replay showed one does.  It now compares
    # placement i against fixture paragraph i, which is sound only while the
    # placements are the first bands in document order; `bandIndex` is checked
    # against the placement index for exactly that reason, and a record whose
    # band count does not match the fixture's paragraph count is
    # NOT_ESTABLISHED rather than compared against a paragraph nobody aimed at.
    focus_rows = []
    for record in candidates:
        readings = [r for r in (record.get("axReadings") or []) if r]
        placements = record.get("placements") or []
        established, why = establishable(record, paragraphs)
        matched = 0
        aimed = []
        for placement in placements:
            index = placement.get("index")
            reading = placement.get("axReading")
            expected = (paragraphs[index]["text"]
                        if isinstance(index, int) and index < len(paragraphs)
                        else None)
            hit = bool(established and reading and expected
                       and (expected in reading or reading in expected))
            matched += 1 if hit else 0
            aimed.append({"index": index, "expected": expected,
                          "reading": reading, "ok": hit})
        focus_rows.append({"placements": len(placements),
                           "readings": len(readings),
                           "distinct": len(set(readings)),
                           "established": established,
                           "notEstablishedBecause": why,
                           "matchedTheParagraphAimedAt": matched,
                           "aimed": aimed})
    ok4 = all(row["placements"] == 3 and row["distinct"] == 3
              and row["established"]
              and row["matchedTheParagraphAimedAt"] == 3
              for row in focus_rows) \
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

    # ---- term 8
    #
    # Judged on the AX side, not the DOM side. `aria-activedescendant` is only
    # a promise until the tree carries it: with the attribute set, Chrome marks
    # the DESCENDANT focused, and that is the node an AT announces -- measured
    # with Orca on 2026-09-03 (`findings/evidence/087/RESULT-mechanisms.md`),
    # where the same arrangement produced "heading 1" and "List with 2 items".
    # The DOM reading is recorded beside it and judged by nothing.
    structure = []
    for record in candidates:
        established8, why8 = establishable(record, paragraphs)
        for placement in record.get("placements") or []:
            reading = placement.get("axReading")
            # AMENDED 2026-09-05 (Ruling 2).  The expectation used to be taken
            # from the reading, so once the reading comes from the pointer the
            # term compared the pointer with ITSELF: redirecting placement 1's
            # pointer at the heading reddened nothing.  It now comes from the
            # fixture, keyed by the placement index like term 4's.
            index = placement.get("index")
            expected_role, expected_level = None, None
            para = (paragraphs[index]
                    if established8 and isinstance(index, int)
                    and index < len(paragraphs) else None)
            if para is not None and para["tag"] == "h":
                expected_role = "heading"
                expected_level = (int(para["outlineLevel"])
                                  if para["outlineLevel"] else 1)
            # FOCUSED **OR ACTIVE DESCENDANT OF FOCUSED** -- the ruling's own
            # wording, and the half that matters: Chrome keeps `focused` on the
            # textbox and expresses the pointer as a relation, visible only
            # through `getPartialAXTree`.
            caret = placement.get("axCaretNode") or {}
            target = caret.get("target") or {}
            got_role = (target.get("role")
                        if target.get("role") in ("heading", "listitem")
                        else None)
            got_level = target.get("level")
            structure.append({
                "reading": reading,
                "aimedAt": (para or {}).get("text"),
                "established": established8,
                "notEstablishedBecause": why8,
                "expectedRole": expected_role, "expectedLevel": expected_level,
                "focusedRole": got_role, "focusedLevel": got_level,
                "axFocused": caret.get("focused"),
                "activeDescendantRef": caret.get("activeDescendantRef"),
                "ok": (established8
                       and got_role == expected_role
                       and (expected_role != "heading"
                            or got_level == expected_level)),
                "domActiveDescendant": placement.get("domActiveDescendant"),
            })
    ok8 = bool(structure) and all(row["ok"] for row in structure)
    terms["8-structure-on-the-caret-path"] = {
        "ok": ok8, "placements": structure,
        "note": "the node the AX tree marks focused after each placement must "
                "carry the fixture's own role and level; a live region "
                "carrying the role as text does not satisfy this",
    }

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
