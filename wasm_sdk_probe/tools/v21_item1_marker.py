#!/usr/bin/env python3
"""D1's marker reader on any container, and its four red cases (ARMS-item1.md §2.7).

The paragraph order is `d1-marker/tool/read_marker.py`'s `paragraphs()`, loaded by path and never
edited (it is committed evidence).  Containers go through the S-7 adapter (`v21_odt_adapter`), so an
.odt, a .fodt and a .fodt.gz are all one `office:document` before `paragraphs()` sees them.

  paragraphs_of(raw)           [(part, index, text)] for any container
  landing(raw)                 (part, index, text, offset) of the one `Z`; LandingError otherwise
  native_landing(arm)          the native D1 run's landing for `arm`, all three rounds required equal
  native_shapes(arm, round)    read_results.para_shapes of a native saved document (records)
  shapes_of(raw)               para_shapes of any container
  self_test()                  the four red cases; exit 1 if any is not red

  v21_item1_marker.py --self-test
  v21_item1_marker.py --landing FILE
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fodt_to_odt  # noqa: E402
import v21_odt_adapter as adapter  # noqa: E402

REPO = HERE.parent.parent
N142 = REPO / "findings/evidence/link-batch-v21/native/142-ctrl-home-end"
D1M = N142 / "d1-marker"
READ_MARKER = D1M / "tool/read_marker.py"
D1_POPULATION = D1M / "tool/d1_population.py"
READ_RESULTS = N142 / "tool/read_results.py"
FIXTURES = N142 / "fixtures"
MARKER = "Z"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


read_marker = _load(READ_MARKER, "read_marker")
d1_population = _load(D1_POPULATION, "d1_population")
read_results = _load(READ_RESULTS, "read_results")


class LandingError(ValueError):
    pass


def paragraphs_of(raw: bytes) -> list[tuple]:
    return read_marker.paragraphs(adapter.flat_document(raw))


def landing(raw: bytes) -> tuple:
    """The one marker's (part, index, paragraph text, offset).  Raises with the reason as payload."""
    try:
        paras = paragraphs_of(raw)
    except (adapter.AdapterError, ValueError) as error:
        raise LandingError(f"unreadable: {type(error).__name__}: {error}") from error
    hits = [(p, i, t, off) for p, i, t in paras for off in range(len(t)) if t[off] == MARKER]
    if len(hits) != 1:
        raise LandingError(f"{len(hits)} markers in the saved document: {hits[:4]}")
    return hits[0]


def shapes_of(raw: bytes) -> list[str]:
    return read_results.para_shapes(adapter.flat_document(raw))


def native_saved(arm: str, round_no: int) -> bytes:
    return (D1M / "out" / arm / f"r{round_no}.fodt.gz").read_bytes()


def native_landing(arm: str) -> tuple:
    found = {landing(native_saved(arm, r)) for r in (1, 2, 3)}
    if len(found) != 1:
        raise LandingError(f"native rounds of {arm} disagree: {sorted(found)}")
    return found.pop()


def native_shapes(arm: str, round_no: int = 1) -> list[str]:
    return read_results.para_shapes(gzip.decompress((N142 / "out" / arm / f"r{round_no}.fodt.gz").read_bytes()))


def population() -> dict:
    """d1_population.classify over the committed arms.json: the IN arms (with d1Script, noCtrlScript)."""
    arms = json.loads((N142 / "out/arms.json").read_text())
    ins, outs, errors = d1_population.classify(arms)
    if errors or not ins:
        raise SystemExit(f"population red: {errors or 'zero IN'}")
    return {"in": ins, "out": [{"name": n, "rules": r} for n, r in outs], "arms": arms}


# ------------------------------------------------------------------ red cases (§2.7)

def _rezip(odt: bytes, change) -> bytes:
    """A copy of `odt` with `change(members)` applied (members: name -> bytes, in order)."""
    with zipfile.ZipFile(io.BytesIO(odt)) as archive:
        members = {info.filename: archive.read(info.filename) for info in archive.infolist()}
    change(members)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data, zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


def _mutated_flat(kind: str):
    """Adapter mutations for red case 1."""
    import xml.etree.ElementTree as ET
    O = adapter.O

    def flat(raw: bytes) -> bytes:
        if not adapter.is_zip(raw if raw[:2] != b"\x1f\x8b" else gzip.decompress(raw)):
            return adapter.flat_document(raw)
        root = ET.fromstring(adapter.flat_document(raw))
        master, body = root.find(O + "master-styles"), root.find(O + "body")
        if kind == "drop-master" and master is not None:
            root.remove(master)
        elif kind == "master-into-body" and master is not None:
            root.remove(master)
            body.insert(0, master)
        elif kind == "content-only":
            members = adapter._members(raw)
            return members["content.xml"]
        return ET.tostring(root)
    return flat


def cross_container(flat=None) -> list[str]:
    """Red case 1 (and S-6 proof (i)): every fixture and every native saved document, converted by
    S-6, read through `flat` (the adapter, or a mutation), gives the paragraphs of the flat original."""
    flat = flat or adapter.flat_document
    sources = (sorted(FIXTURES.glob("*.fodt")) + sorted((D1M / "out").glob("*/r*.fodt.gz"))
               + sorted((N142 / "out").glob("*/r*.fodt.gz")))
    if not sources:
        return ["no sources found (directory moved?)"]
    problems = []
    for path in sources:
        raw = fodt_to_odt.read_flat(path)
        try:
            got = read_marker.paragraphs(flat(fodt_to_odt.convert(raw)))
        except Exception as error:  # noqa: BLE001 -- an error is a difference too
            problems.append(f"{path.name}: {type(error).__name__}: {error}")
            continue
        if got != read_marker.paragraphs(raw):
            problems.append(f"{path.relative_to(N142)}: paragraphs differ")
    return problems


def self_test(verbose: bool = True) -> int:
    results = []

    def check(name: str, red: bool, detail: str = "") -> None:
        results.append((name, red))
        if verbose:
            print(f"{'RED ok ' if red else 'NOT RED'}  {name}  {detail}")

    # 1. cross-container equality: green on the real adapter, red on each mutation
    green = cross_container()
    if verbose:
        print(f"green  cross-container on the real adapter: {len(green)} problem(s) {green[:2]}")
    for kind in ("drop-master", "master-into-body", "content-only"):
        found = cross_container(_mutated_flat(kind))
        check(f"1 cross-container, adapter mutated: {kind}", bool(found), f"{len(found)} difference(s)")
    # 2-4 on a WASM-shaped saved document: the native a1-home-mid r1 as an ODT
    odt = fodt_to_odt.convert(fodt_to_odt.read_flat(D1M / "out/a1-home-mid/r1.fodt.gz"))
    reference = native_landing("a1-home-mid")
    real = landing(odt)
    if verbose:
        print(f"green  the ODT's landing {real[:2]}+{real[3]} equals native {reference[:2]}+{reference[3]}: {real == reference}")
    if real != reference:
        results.append(("green landing on the real ODT", False))

    def shift(m):
        m["content.xml"] = m["content.xml"].replace(b"ZAlpha", b"AZlpha", 1)
    shifted = _rezip(odt, shift)
    try:
        check("2 marker shift", landing(shifted) != reference)
    except LandingError as error:
        check("2 marker shift", True, str(error))

    def duplicate(m):
        m["content.xml"] = m["content.xml"].replace(b"Bravo", b"BZravo", 1)
    try:
        landing(_rezip(odt, duplicate))
        check("3 duplicate marker", False)
    except LandingError as error:
        check("3 duplicate marker", "2 markers" in str(error), str(error)[:80])

    for label, change in (("no content.xml", lambda m: m.pop("content.xml")),
                          ("no styles.xml", lambda m: m.pop("styles.xml")),
                          ("content.xml cut short", lambda m: m.__setitem__("content.xml", m["content.xml"][:-200]))):
        try:
            landing(_rezip(odt, change))
            check(f"4 missing XML: {label}", False)
        except LandingError as error:
            check(f"4 missing XML: {label}", str(error).startswith("unreadable"), str(error)[:90])
    reds = [name for name, red in results if not red]
    print(f"self-test: {len(results) - len(reds)}/{len(results)} red as required" + (f"; NOT RED: {reds}" if reds else ""))
    return 1 if reds or green else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--landing")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.landing:
        print(landing(Path(args.landing).read_bytes()))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
