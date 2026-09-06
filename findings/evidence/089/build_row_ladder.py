#!/usr/bin/env python3
"""Build the finding 089 scaling ladder: the two named ranges shortened to
A2:A<n>, and nothing else touched.

The 2026-09-05 bisect showed `table:named-expressions` is the switch: remove the
three `table:named-range` entries and the file opens in 1.6 s; put them back and
it times out.  This shortens the two that the 99 `IF(COUNTIF(Index2;Index);...)`
cells resolve through, so the cost can be measured as a function of n instead of
observed at one point.

`Farben` (`$B$2:.B100`) is NOT touched: it is a range the array formulas do not
resolve through, and leaving it identical keeps the variable single.

WHY THIS FILE EXISTS AT ALL.  `tdf149752-rows20.ods` and `-rows50.ods` were
built ad hoc in a scratchpad that is gone, so two banked fixtures had no
reproducible provenance.  `--verify` re-derives them and compares, which is the
check that this script is the thing that made them and not merely something that
makes files of the same shape.

  python3 build_row_ladder.py --verify          # reproduce rows20/rows50
  python3 build_row_ladder.py --rows 25 30 35 40
"""
import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "wasm_sdk_probe/test-docs/ods/upstream/tdf149752.ods"
OUT_DIR = Path(__file__).resolve().parent

OPEN_TAG = "<table:named-expressions>"
CLOSE_TAG = "</table:named-expressions>"
FULL = "$A$2:.$A$100"


def rewrite(content: str, rows: int) -> str:
    """Shorten A2:A100 to A2:A<rows>, INSIDE the named-expressions block only.

    Scoping matters: the document also holds 99 `SMALL([.$A$2:.$A$100];ROW())`
    formulas, and a blanket replace hits 200 sites instead of 2 -- which is a
    mistake this tree has already made once on this document.
    """
    start = content.index(OPEN_TAG)
    end = content.index(CLOSE_TAG) + len(CLOSE_TAG)
    block = content[start:end]
    assert block.count(FULL) == 2, f"expected 2 sites in the block, got {block.count(FULL)}"
    shrunk = block.replace(FULL, f"$A$2:.$A${rows}")
    assert shrunk.count(FULL) == 0
    out = content[:start] + shrunk + content[end:]
    # And the 99 array formulas outside the block are untouched.
    assert out.count(FULL) == content.count(FULL) - 2
    return out


def build(rows: int, dest: Path) -> Path:
    with zipfile.ZipFile(SOURCE) as src:
        names = src.namelist()
        content = src.read("content.xml").decode("utf-8")
        new_content = rewrite(content, rows).encode("utf-8")
        with zipfile.ZipFile(dest, "w") as out:
            for info in src.infolist():
                data = new_content if info.filename == "content.xml" else src.read(info.filename)
                out.writestr(info, data)
    assert len(names) == len(zipfile.ZipFile(dest).namelist())
    return dest


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_of(path: Path) -> bytes:
    with zipfile.ZipFile(path) as z:
        return z.read("content.xml")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, nargs="*", default=[])
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    rc = 0
    if args.verify:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for rows in (20, 50):
                banked = OUT_DIR / f"tdf149752-rows{rows}.ods"
                if not banked.is_file():
                    print(f"  MISSING  {banked.name}")
                    rc = 1
                    continue
                fresh = build(rows, Path(tmp) / banked.name)
                same_zip = sha(fresh) == sha(banked)
                same_xml = content_of(fresh) == content_of(banked)
                print(f"  rows{rows}: content.xml identical={same_xml}  "
                      f"whole-zip identical={same_zip}")
                if not same_xml:
                    rc = 1
        if rc == 0:
            print("verify: the banked fixtures are what this script produces")
        else:
            print("verify: FAILED -- the banked fixtures are not reproduced here")

    for rows in args.rows:
        dest = OUT_DIR / f"tdf149752-rows{rows}.ods"
        build(rows, dest)
        print(f"  wrote {dest.name}  {dest.stat().st_size} bytes  sha256={sha(dest)[:16]}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
