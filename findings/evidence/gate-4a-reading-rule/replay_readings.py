#!/usr/bin/env python3
"""Offline replay of three candidate definitions of `axReading` over the 4a
records the tree already holds.  No browser; this reads recorded AX trees.

  A  current rule: name of the first AX node (full-tree order) carrying E1-LC
  B  pure pointer: text of the node the sink's activedescendant names
  C  disjunction: B if the tree carries the relation, else A

For each record and definition: term 4 (3 placements, 3 distinct readings,
each matching a fixture paragraph) and term 8 with its expectation keyed off
the reading, as check_4a.py does today.

Plus two record mutations:
  reorder   -- structure subtree placed BEFORE the live region (DOM-order swap;
               product focus unchanged)
  mispoint  -- placement 1's pointer redirected to node-0 (the heading)
"""
import json, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("/home/jiajun/LibreOffice/study_LiteCore")
FIXTURE = ROOT / "wasm_sdk_probe/dist/e1-fixtures/list-contexts.odt"
OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
TEXTNS = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"

def fixture():
    with zipfile.ZipFile(FIXTURE) as z:
        root = ET.fromstring(z.read("content.xml"))
    out = []
    for e in root.find(f".//{OFFICE}text").iter():
        tag = e.tag.split("}")[-1]
        if tag in ("p", "h"):
            out.append({"tag": tag, "level": e.get(f"{TEXTNS}outline-level"),
                        "text": "".join(e.itertext())})
    return out

PARAS = fixture()

def subtree_text(nodes, nid):
    n = nodes[nid]
    parts = []
    if n["role"] in ("StaticText",) and n.get("name"):
        parts.append(n["name"])
    for c in n["childIds"]:
        if c in nodes:
            parts.append(subtree_text(nodes, c))
    return "".join(parts)

def structure_leaves(nodes):
    """a11y-node-i <-> i-th heading/paragraph/listitem under #a11y-structure,
    in tree order (the page assigns ids in that order)."""
    group = next(n for n in nodes.values() if n["role"] == "group" and n.get("name") == "文件內容")
    kids = [nodes[c] for c in group["childIds"] if c in nodes]
    structure = kids[-1]  # generic after the live paragraph
    leaves = []
    def walk(n):
        if n["role"] in ("heading", "paragraph", "listitem"):
            leaves.append(n)
        for c in n["childIds"]:
            if c in nodes:
                walk(nodes[c])
    walk(structure)
    return leaves

def marker_first(nodes_in_order):
    for n in nodes_in_order:
        for k in ("name", "value"):
            if isinstance(n.get(k), str) and "E1-LC" in n[k]:
                return n[k]
    return None

def readings(record, definition, reorder=False, mispoint=False):
    nodes = {n["nodeId"]: n for n in record["nodes"]}
    order = list(record["nodes"])
    if reorder:
        group = next(n for n in order if n["role"] == "group" and n.get("name") == "文件內容")
        kids = [nodes[c] for c in group["childIds"]]
        structure_ids = set()
        def collect(n):
            structure_ids.add(n["nodeId"])
            for c in n["childIds"]:
                if c in nodes: collect(nodes[c])
        collect(kids[-1])
        order = [n for n in order if n["nodeId"] in structure_ids] + \
                [n for n in order if n["nodeId"] not in structure_ids]
    leaves = structure_leaves(nodes)
    out = []
    for p in record["placements"]:
        placed_nodes = p["axNodesCarryingText"]  # recorded after the placement
        # for the reorder mutation, use the recorded per-placement list but
        # with structure-subtree nodes first: the heading node has role
        # 'heading'; live-region text is a StaticText outside the structure.
        if reorder:
            # after placement, carried[] is in full-tree order: live StaticText,
            # then the structure heading, ... .  Reordering puts the structure
            # nodes first -> the first marker node is the structure heading.
            a = next((n.get("name") for n in placed_nodes if n["role"] == "heading"), None)
        else:
            a = p["axReading"]
        caret = p.get("axCaretNode") or {}
        ref = caret.get("activeDescendantRef")
        if mispoint and p["index"] == 1:
            ref = "a11y-node-0"
        b = None
        if ref:
            i = int(ref.rsplit("-", 1)[1])
            b = subtree_text(nodes, leaves[i]["nodeId"]) if i < len(leaves) else None
        c = b if ref else a
        out.append({"A": a, "B": b, "C": c, "ref": ref,
                    "targetRole": (leaves[int(ref.rsplit('-',1)[1])]["role"] if ref else None),
                    "targetLevel": (leaves[int(ref.rsplit('-',1)[1])].get("level") if ref else None),
                    "axName": (caret.get("target") or {}).get("name")})
    return out

def term4(rs):
    ok = len(rs) == 3 and len(set(r for r in rs if r)) == 3 and \
        all(r and any(p["text"] in r or r in p["text"] for p in PARAS) for r in rs)
    return ok

def term8(rows, key):
    oks = []
    for r in rows:
        reading = r[key]
        exp_role, exp_level = None, None
        for p in PARAS:
            if p["text"] and p["text"] == reading:
                if p["tag"] == "h":
                    exp_role, exp_level = "heading", int(p["level"] or 1)
                break
        got_role = r["targetRole"] if r["targetRole"] in ("heading", "listitem") else None
        oks.append(got_role == exp_role and (exp_role != "heading" or r["targetLevel"] == exp_level))
    return bool(rows) and all(oks)

files = {
 "3dfdcfef term8-RED (pre-087, no pointer)": "findings/evidence/087/4a-term8-RED-before-the-fix.json",
 "88adb453 run1 (087 fixed)": "findings/evidence/087/4a-eight-terms-run1.json",
 "20f09cc9 run1 (088 fixed)": "findings/evidence/088/4a-eight-terms-run1.json",
 "20f09cc9 run2": "findings/evidence/088/4a-eight-terms-run2.json",
 "20f09cc9 run3": "findings/evidence/088/4a-eight-terms-run3.json",
 "cf824c3f live region silenced (RED)": "findings/evidence/088/4a-with-live-region-silenced-TERM4-AND-8-RED.json",
}
for label, rel in files.items():
    rec = json.load(open(ROOT / rel))
    print("=" * 8, label)
    for mut in ("none", "reorder", "mispoint"):
        rows = readings(rec, None, reorder=(mut == "reorder"), mispoint=(mut == "mispoint"))
        line = f"  [{mut:8}] "
        for key in ("A", "B", "C"):
            rs = [r[key] for r in rows]
            line += f"{key}: t4={'G' if term4(rs) else 'R'} t8={'G' if term8(rows, key) else 'R'}  "
        print(line)
        if mut == "none":
            print("    readings A:", [r["A"] for r in rows])
            print("    readings B:", [r["B"] for r in rows])
            print("    AX name of pointer target:", [r["axName"] for r in rows])
