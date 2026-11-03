#!/usr/bin/env python3
"""SPEC-P-calc-undo section 2 (NU): how many engine undos each Calc page write takes, on the native bridge (build/calc-style-native).

Per arm, a fresh cell-editing.ods: save with no write (B), the arm's writes, a read and a save (U0), then up to five .uno:Undo, each followed
by an op 0 read of the target cell and a save (U_k).  Back = every cell of the first sheet has B's content (value type, value, formula, text) and B's resolved
automatic style (every attribute of the style element and of its property children, the name aside).  Steps = the least k whose U_k is back.
This script never compiles.
  probe_calc_undo_native.py --out DIR [--binary PATH]

--binary (SPEC-P-calc-undo 4.4, NU-3): another driver with calc_cell_native's protocol, such as build/calc-undo-native/{undo,control}/
calc-undo-native from build_calc_undo_native.py.  Without it the binary is build/calc-style-native/calc-cell-native, as for native-01.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import run_calc_cell_native as native
from create_calc_edit_fixture import create

NS = native.NAMES
T, O, S = (lambda k: lambda n: f"{{{NS[k]}}}{n}")("t"), (lambda k: lambda n: f"{{{NS[k]}}}{n}")("o"), (lambda k: lambda n: f"{{{NS[k]}}}{n}")("s")
TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
MAX_UNDO = 5
A1C2 = [0, 0, 2, 1]


def write(column, row, operation, text="", enabled=0):
    return dict(part=0, column=column, row=row, operation=operation, enabled=enabled, text=text)


def ranged(operation, value=None, enabled=0):
    c, r, ec, er = A1C2
    payload = dict(endColumn=ec, endRow=er)
    if value is not None:
        payload["value"] = value
    return dict(part=0, column=c, row=r, operation=operation, enabled=enabled, text=json.dumps(payload))


# (arm, writes, target cell (column, row))
ARMS = [
    ("zero", [], (5, 0)),
    ("two-inputs", [write(5, 0, 1, "ONE"), write(5, 1, 1, "TWO")], (5, 0)),
    ("input-text", [write(5, 0, 1, "UNDOME")], (5, 0)),
    ("input-number", [write(5, 1, 1, "123")], (5, 1)),
    ("input-formula", [write(5, 2, 1, "=B1+1")], (5, 2)),
    ("input-overwrite", [write(0, 1, 1, "新內容")], (0, 1)),
    ("input-clear", [write(2, 1, 1, "")], (2, 1)),
    ("cell-bold", [write(1, 1, 2, enabled=1)], (1, 1)),
    ("cell-italic", [write(1, 1, 3, enabled=1)], (1, 1)),
    ("cell-underline", [write(1, 1, 4, enabled=1)], (1, 1)),
    ("range-bold", [ranged(7, enabled=1)], (1, 1)),
    ("range-italic", [ranged(8, enabled=1)], (1, 1)),
    ("range-underline", [ranged(9, enabled=1)], (1, 1)),
    ("range-textColor", [ranged(10, "#c00000")], (1, 1)),
    ("range-backColor", [ranged(11, "#ffe599")], (1, 1)),
    ("range-align", [ranged(12, "center")], (1, 1)),
    ("draft-then-bold", [write(5, 0, 1, "DRAFT"), write(5, 0, 2, enabled=1)], (5, 0)),
]
READ_KEYS = ("input", "formula", "cellType", "bold", "boldAsian", "boldComplex", "italic", "italicAsian", "italicComplex", "underline",
             "textColor", "backColor", "horizontalAlign")


def sheet_state(path):
    """Every cell of the first sheet: content and its resolved automatic style, the style's name aside."""
    with zipfile.ZipFile(path) as z:
        content = ET.fromstring(z.read("content.xml"))
    styles = {}
    for style in content.iter(S("style")):
        attrs = {k: v for k, v in style.attrib.items() if k != S("name")}
        props = {child.tag: dict(child.attrib) for child in style}
        styles[style.get(S("name"))] = {"attrs": attrs, "props": props}
    table = content.find(".//" + T("table"))
    state, row = {}, 0
    for tr in table.iter(T("table-row")):
        rows = int(tr.get(T("number-rows-repeated"), "1"))
        col = 0
        for cell in tr:
            if cell.tag not in (T("table-cell"), T("covered-table-cell")):
                continue
            cols = int(cell.get(T("number-columns-repeated"), "1"))
            record = {"kind": cell.tag.rsplit("}", 1)[1], "type": cell.get(O("value-type")), "value": cell.get(O("value")),
                      "formula": cell.get(T("formula")), "text": "\n".join("".join(p.itertext()) for p in cell.findall(f"{{{TEXT}}}p")),
                      "style": styles.get(cell.get(T("style-name")))}
            if record["type"] or record["formula"] or record["text"] or record["style"]:
                for dr in range(min(rows, 50)):
                    for dc in range(min(cols, 50)):
                        state[f"{col + dc},{row + dr}"] = record
            col += cols
        row += rows
    return state


BINARY = None


def run_driver(out, name, file, requests):
    """run_calc_cell_native.run with the binary as a parameter; the same files, the same checks."""
    profile = out / f"profile-{name}"
    profile.mkdir()
    inputs = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests)
    (out / f"{name}-requests.jsonl").write_text(inputs)
    command = [str(BINARY), str(native.CORE / "instdir/program"), profile.as_uri(), file.as_uri()]
    with (out / f"{name}-stderr.txt").open("w") as err:
        result = subprocess.run(command, input=inputs, stdout=subprocess.PIPE, stderr=err, text=True, timeout=90,
                                env={**os.environ, "SAL_USE_VCLPLUGIN": "svp"})
    (out / f"{name}-observations.jsonl").write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"{name} driver exit {result.returncode}")
    # Successive JSON values, not lines: command-values for .uno:Undo comes back pretty-printed over several lines (NU-2, first run).
    observations, at, decoder = [], 0, json.JSONDecoder()
    while True:
        while at < len(result.stdout) and result.stdout[at].isspace():
            at += 1
        if at >= len(result.stdout):
            break
        value, at = decoder.raw_decode(result.stdout, at)
        observations.append(value)
    if len(observations) != len(requests):
        raise RuntimeError(f"{name}: {len(observations)} replies for {len(requests)} requests")
    return observations


def run_arm(out, fixture, name, writes, target):
    read = dict(part=0, column=target[0], row=target[1], operation=0, enabled=0, text="")
    saves = {"B": out / f"{name}-B.ods", "U0": out / f"{name}-U0.ods"}
    requests = [read, {"action": "save", "url": saves["B"].as_uri()}, *writes, read, {"action": "save", "url": saves["U0"].as_uri()}]
    for k in range(1, MAX_UNDO + 1):
        saves[f"U{k}"] = out / f"{name}-U{k}.ods"
        requests += [{"action": "uno", "command": ".uno:Undo"}, read, {"action": "save", "url": saves[f"U{k}"].as_uri()}]
    own = out / f"{name}-fixture.ods"  # a copy per arm: an aborted LOK run leaves .~lock and the next opens read-only
    shutil.copyfile(fixture, own)
    replies = run_driver(out, name, own, requests)
    base_read = {k: replies[0].get(k) for k in READ_KEYS}
    write_replies = replies[2:2 + len(writes)]
    after_write = {k: replies[2 + len(writes)].get(k) for k in READ_KEYS}
    base = sheet_state(saves["B"])
    steps = []
    for k in range(0, MAX_UNDO + 1):
        if k == 0:
            reading, saved_ok = after_write, replies[3 + len(writes)].get("saved") is True
        else:
            at = 2 + len(writes) + 2 + 3 * (k - 1)
            reading = {key: replies[at + 1].get(key) for key in READ_KEYS}
            saved_ok = replies[at + 2].get("saved") is True
        state = sheet_state(saves[f"U{k}"])
        differ = sorted(c for c in set(base) | set(state) if base.get(c) != state.get(c))
        steps.append({"k": k, "saved": saved_ok, "fileBack": saved_ok and not differ, "readBack": reading == base_read,
                      "differ": differ[:8], "read": reading})
    file_steps = next((s["k"] for s in steps if s["fileBack"]), None)
    read_steps = next((s["k"] for s in steps if s["readBack"]), None)
    return {"arm": name, "writes": writes, "target": list(target), "writeReplies": write_replies,
            "baseRead": base_read, "afterWrite": after_write, "steps": steps,
            "fileSteps": file_steps, "readSteps": read_steps,
            "agree": file_steps == read_steps,
            "bSha256": hashlib.sha256(saves["B"].read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    global BINARY
    binary = BINARY = (args.binary or native.ROOT / "wasm_sdk_probe/build/calc-style-native/calc-cell-native").resolve()
    if not binary.is_file():
        raise SystemExit(f"{binary} is missing; this script never compiles")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fixture = create(out / "fixture")
    report = {"toolSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "binary": str(binary), "binarySha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "maxUndo": MAX_UNDO, "arms": []}
    for name, writes, target in ARMS:
        report["arms"].append(run_arm(out, fixture, name, writes, target))
    by = {a["arm"]: a for a in report["arms"]}
    report["NU-0"] = by["zero"]["fileSteps"] == 0 and by["zero"]["readSteps"] == 0 and by["two-inputs"]["fileSteps"] == 2
    report["NU-1"] = {a["arm"]: ("agree" if a["agree"] else "NE") for a in report["arms"]}
    report["table"] = {a["arm"]: a["fileSteps"] if a["agree"] else "NE" for a in report["arms"]}
    (out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"NU-0": report["NU-0"], "table": report["table"]}, ensure_ascii=False))
    return 0 if report["NU-0"] and all(a["agree"] for a in report["arms"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
