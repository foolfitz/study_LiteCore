#!/usr/bin/env python3
"""Deterministic corpora for the long-paragraph diagnosis (v21 shakedown, item 2 follow-up).

Every corpus is exactly `n` UTF-8 bytes and has no trailing newline.

  cjk(n)            one paragraph: "中" * floor(n/3) + "a" * (n mod 3)
                    == wasm_sdk_probe/tools/v21_item2_fixtures.py size_corpus(n) (checked by --check);
                    n = 65536 gives sha256 9ecdb239209da768...
  ascii(n)          one paragraph: "a" * n
  cjksplit<k>(n)    k paragraphs of "中", separated by one blank line ("\\n\\n"), as equal as the
                    bytes allow (the first paragraphs take the extra characters); the last paragraph
                    is padded with "a" to exactly n bytes
  cjkspace100(n)    one paragraph: groups of 100 "中" each followed by one ASCII space, then "中" to
                    fill, then "a" to exactly n bytes; never ends with a space

  corpora.py --check            compare cjk(65536) with the item-2 fixture generator and print sums
  corpora.py --write DIR NAME:N [NAME:N ...]   write DIR/NAME-N.md (refuses to overwrite)
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

CJK = "中"          # U+4E2D, three UTF-8 bytes


def cjk(n: int) -> bytes:
    return (CJK * (n // 3) + "a" * (n % 3)).encode("utf-8")


def ascii_(n: int) -> bytes:
    return b"a" * n


def cjksplit(k: int, n: int) -> bytes:
    sep = 2 * (k - 1)
    chars = (n - sep) // 3
    pad = (n - sep) - 3 * chars
    sizes = [chars // k + (1 if i < chars % k else 0) for i in range(k)]
    paras = [CJK * s for s in sizes]
    paras[-1] += "a" * pad
    return "\n\n".join(paras).encode("utf-8")


def cjkspace(every: int, n: int) -> bytes:
    group = CJK * every + " "
    gbytes = len(group.encode("utf-8"))
    groups = max(0, (n - 3) // gbytes)          # leave room for at least one "中" after the last space
    text = group * groups
    rest = n - len(text.encode("utf-8"))
    text += CJK * (rest // 3) + "a" * (rest % 3)
    return text.encode("utf-8")


def make(name: str, n: int) -> bytes:
    if name == "cjk":
        raw = cjk(n)
    elif name == "ascii":
        raw = ascii_(n)
    elif (m := re.fullmatch(r"cjksplit(\d+)", name)):
        raw = cjksplit(int(m.group(1)), n)
    elif (m := re.fullmatch(r"cjkspace(\d+)", name)):
        raw = cjkspace(int(m.group(1)), n)
    else:
        raise SystemExit(f"unknown corpus {name}")
    if len(raw) != n:
        raise SystemExit(f"{name}:{n} came out {len(raw)} bytes")
    return raw


def describe(raw: bytes) -> dict:
    text = raw.decode("utf-8")
    paras = [p for p in text.split("\n\n")]
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "utf16": len(text),
            "paragraphs": len(paras), "longestParagraphChars": max(len(p) for p in paras),
            "spaces": text.count(" ")}


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--check"]:
        tools = Path(__file__).resolve().parents[6] / "wasm_sdk_probe" / "tools"
        sys.path.insert(0, str(tools))
        import v21_item2_fixtures as fx  # noqa: E402
        same = fx.size_corpus(65536) == cjk(65536)
        print({"cjk(65536) == size_corpus(65536)": same, **describe(cjk(65536))})
        return 0 if same else 1
    if argv[1:2] == ["--write"]:
        out = Path(argv[2])
        out.mkdir(parents=True, exist_ok=True)
        for spec in argv[3:]:
            name, n = spec.split(":")
            path = out / f"{name}-{int(n)}.md"
            if path.exists():
                raise SystemExit(f"refusing to overwrite {path}")
            raw = make(name, int(n))
            path.write_bytes(raw)
            print(path.name, describe(raw))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
