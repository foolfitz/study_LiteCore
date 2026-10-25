#!/usr/bin/env python3
"""Build the small native bridge/driver and verify real saved ODS files (no core build)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

from create_calc_edit_fixture import create

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "build-native-26-8"
BUILD = ROOT / "wasm_sdk_probe/build/calc-cell-native"
NAMES = {"t": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
         "o": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
         "s": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
         "f": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"}


def build(out):
    BUILD.mkdir(parents=True, exist_ok=True)
    load = subprocess.check_output(["uptime"], text=True)
    makes = subprocess.run(["pgrep", "-a", "make"], capture_output=True, text=True)
    (out / "build-environment.txt").write_text(load + makes.stdout)
    if makes.returncode == 0:
        raise RuntimeError("another make exists; do not compile until the owner resolves it")
    include = [ROOT / "libreoffice-26-8/include", CORE / "config_host",
               CORE / "workdir/UnoApiHeadersTarget/udkapi/comprehensive",
               CORE / "workdir/UnoApiHeadersTarget/offapi/comprehensive",
               CORE / "workdir/UnpackedTarball/boost"]
    install = CORE / "instdir/program"
    commands = [
        ["g++", "-std=c++20", "-O2", "-fPIC", "-DLIBO_INTERNAL_ONLY", "-DCPPU_ENV=gcc3",
         "-DUNX", "-DLINUX", "-DX86_64", *[f"-I{p}" for p in include], "-c",
         str(ROOT / "wasm_sdk_probe/src/calc_cell_bridge.cpp"), "-o", str(BUILD / "bridge.o")],
        ["g++", "-std=c++17", "-O2", f"-I{include[0]}", f"-I{include[-1]}",
         str(ROOT / "wasm_sdk_probe/tools/calc_cell_native.cpp"), str(BUILD / "bridge.o"),
         f"-L{install}", "-lsfxlo", "-lvcllo", "-lcomphelper", "-ltllo",
         *[str(install / name) for name in ("libuno_sal.so.3", "libuno_cppu.so.3", "libuno_cppuhelpergcc3.so.3")],
         f"-Wl,-rpath,{install}", "-ldl", "-o", str(BUILD / "calc-cell-native")],
    ]
    (out / "build-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    for i, command in enumerate(commands):
        with (out / f"compile-{i}.txt").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)


def run(out, name, file, requests):
    profile = out / f"profile-{name}"
    profile.mkdir()
    inputs = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests)
    (out / f"{name}-requests.jsonl").write_text(inputs)
    command = [str(BUILD / "calc-cell-native"), str(CORE / "instdir/program"),
               profile.as_uri(), file.as_uri()]
    with (out / f"{name}-stderr.txt").open("w") as err:
        result = subprocess.run(command, input=inputs, capture_output=False, stdout=subprocess.PIPE,
                                stderr=err, text=True, timeout=90,
                                env={**os.environ, "SAL_USE_VCLPLUGIN": "svp"})
    (out / f"{name}-observations.jsonl").write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"{name} driver exit {result.returncode}")
    observations = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    if len(observations) != len(requests):
        raise RuntimeError(f"{name}: {len(observations)} replies for {len(requests)} requests")
    return observations


def address(col, row):
    letters = ""
    while col >= 0:
        letters = chr(65 + col % 26) + letters
        col = col // 26 - 1
    return letters + str(row + 1)


def cursor_matches(geometry, raw):
    try:
        cursor = [int(x.strip()) for x in raw.split(",")]
        return (len(cursor) == 6
                and cursor[4:6] == [int(geometry["column"]), int(geometry["row"])]
                and all(abs(a - int(geometry[k])) <= 20 for a, k in zip(
                    cursor[:4], ("xTwips", "yTwips", "widthTwips", "heightTwips"))))
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def reader_controls():
    geometry = dict(column=1, row=2, xTwips=100, yTwips=200, widthTwips=300, heightTwips=400)
    assert cursor_matches(geometry, "100,200,300,400,1,2")
    assert not cursor_matches(geometry, "100,200,300,400,2,2"), "one-column-off control must be red"
    assert not cursor_matches(geometry, "100,200,330,400,1,2"), "wrong geometry must be red"
    assert not cursor_matches(geometry, "EMPTY"), "missing cell must be red"
    return {"green": 1, "red": 3, "pass": True}


def cells_from_xml(path):
    with zipfile.ZipFile(path) as z:
        content = ET.fromstring(z.read("content.xml"))
    cells = {}
    for part, table in enumerate(content.findall(".//t:table", NAMES)):
        row = 0
        for tr in table.findall("t:table-row", NAMES):
            repeats = int(tr.get(f"{{{NAMES['t']}}}number-rows-repeated", "1"))
            col = 0
            for cell in tr:
                if cell.tag not in (f"{{{NAMES['t']}}}table-cell", f"{{{NAMES['t']}}}covered-table-cell"):
                    continue
                n = int(cell.get(f"{{{NAMES['t']}}}number-columns-repeated", "1"))
                if row < 10 and col < 10:
                    cells[(part, col, row)] = cell
                col += n
            row += repeats
    return content, cells


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "reader-controls.json").write_text(json.dumps(reader_controls(), indent=2) + "\n")
    if not args.skip_build:
        build(out)
    fixture = create(out / "fixture")
    manifest = json.loads((out / "fixture/manifest.json").read_text())
    context = {"criterion": "SPEC-M4-cell-editing-v1 N-model/N-format/N-geometry", "rounds": 3,
               "coreCommit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT / "libreoffice-26-8", text=True).strip(),
               "fixtureSha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
               "sources": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                           ("wasm_sdk_probe/src/calc_cell_bridge.cpp", "wasm_sdk_probe/tools/calc_cell_native.cpp", __file__)}}
    (out / "context.json").write_text(json.dumps(context, indent=2) + "\n")
    checks = []

    def check(name, ok, actual):
        checks.append({"id": name, "pass": bool(ok), "actual": actual})

    for number in range(1, 4):
        requests = []
        tags = []

        def add(tag, **request):
            tags.append(tag)
            requests.append(request)

        for item in manifest["geometry"]:
            add(("geometry", item), **item)
            add(("cursor", item), action="lok-select", address=address(item["column"], item["row"]))
        for case in manifest["cases"]:
            add(("edit", case), column=case["column"], row=case["row"], operation=1, text=case["input"])
        for index, key in enumerate(manifest["formats"], 2):
            for enabled in (1, 0, 1):
                add(("format", key, enabled), column=1, row=1, operation=index, enabled=enabled)
        for item in manifest["preserved"]:
            add(("preserved", item), **{k: v for k, v in item.items() if k != "formula"})
        add(("recalculated",), column=2, row=0)
        add(("protected",), part=2, column=0, row=0, operation=1, text="must refuse")
        add(("protected-unchanged",), part=2, column=0, row=0)
        add(("unlocked",), part=2, column=1, row=0, operation=1, text="Unlocked updated")
        add(("long",), column=0, row=0, operation=1, text="a" * 32768)
        add(("long-unchanged",), column=0, row=0)
        add(("invalid",), part=999, column=0, row=0)
        saved = out / f"saved-r{number}.ods"
        add(("saved",), action="save", url=saved.as_uri())
        observations = run(out, f"r{number}", fixture, requests)
        geometry = None
        for tag, actual in zip(tags, observations):
            label = f"r{number}/{tag[0]}/{len(checks)}"
            if tag[0] == "geometry":
                geometry = actual
                check(label, actual.get("ok") == "true", actual)
            elif tag[0] == "cursor":
                raw = actual.get("cursor", {}).get("commandValues", "")
                match = cursor_matches(geometry, raw)
                check(label, match, {"cursor": actual, "model": geometry})
                if geometry.get("ok") == "true":
                    hit = {"operation": 5, "column": int(geometry["xTwips"]) + max(1, int(geometry["widthTwips"]) // 2),
                           "row": int(geometry["yTwips"]) + max(1, int(geometry["heightTwips"]) // 2)}
                    reply = run(out, f"hit-r{number}-{len(checks)}", fixture, [hit])[0]
                    check(label + "/hit", (reply.get("column"), reply.get("row")) == (geometry["column"], geometry["row"]), reply)
            elif tag[0] == "edit":
                expected = tag[1]["input"]
                check(label, actual.get("ok") == "true" and actual.get("input") == expected, actual)
            elif tag[0] == "format":
                keys = [tag[1]] + ([tag[1] + s for s in ("Asian", "Complex")] if tag[1] != "underline" else [])
                check(label, all(actual.get(k) == ("true" if tag[2] else "false") for k in keys), actual)
            elif tag[0] == "preserved":
                check(label, actual.get("formula") == tag[1]["formula"], actual)
            elif tag[0] == "recalculated":
                check(label, float(actual.get("value", -1)) == 63, actual)
            elif tag[0] == "protected":
                check(label, actual.get("code") == "READ_ONLY", actual)
            elif tag[0] == "protected-unchanged":
                check(label, actual.get("formula") == "鎖定內容", actual)
            elif tag[0] == "unlocked":
                check(label, actual.get("ok") == "true" and actual.get("formula") == "Unlocked updated", actual)
            elif tag[0] == "long":
                check(label, actual.get("code") == "CELL_TEXT_TOO_LONG", actual)
            elif tag[0] == "long-unchanged":
                check(label, actual.get("formula") == manifest["cases"][0]["input"], actual)
            elif tag[0] == "invalid":
                check(label, actual.get("code") == "INVALID_ARGUMENT", actual)
            else:
                check(label, actual.get("saved") is True, actual)

        read_requests = [{"column": c["column"], "row": c["row"]} for c in manifest["cases"]]
        read_requests += [{"column": 1, "row": 1}]
        reopened = run(out, f"reopen-r{number}", saved, read_requests)
        for case, actual in zip(manifest["cases"], reopened):
            check(f"r{number}/reopen/{case['id']}", actual.get("input") == case["input"], actual)
        check(f"r{number}/reopen/formats", all(reopened[-1].get(key) == "true" for key in manifest["formats"]), reopened[-1])
        content, cells = cells_from_xml(saved)
        cell = cells[(0, 2, 0)]
        check(f"r{number}/xml/formula", cell.get(f"{{{NAMES['t']}}}formula") == "of:=[.B1]*3" and float(cell.get(f"{{{NAMES['o']}}}value", -1)) == 63, ET.tostring(cell, encoding="unicode"))
        styled = cells[(0, 1, 1)]
        style = styled.get(f"{{{NAMES['t']}}}style-name")
        attributes = content.find(f".//s:style[@s:name='{style}']/s:text-properties", NAMES)
        check(f"r{number}/xml/formats", attributes is not None and attributes.get(f"{{{NAMES['f']}}}font-weight") == "bold" and attributes.get(f"{{{NAMES['f']}}}font-style") == "italic" and attributes.get(f"{{{NAMES['s']}}}text-underline-style") == "solid", attributes.attrib if attributes is not None else None)

    failures = [c for c in checks if not c["pass"]]
    report = {"checks": checks, "failures": len(failures), "pass": not failures}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(checks) - len(failures)}/{len(checks)} checks pass")
    for failure in failures:
        print(json.dumps(failure, ensure_ascii=False))
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
