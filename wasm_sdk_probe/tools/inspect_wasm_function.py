#!/usr/bin/env python3
"""What is wasm-function[N]?  Answered from the binary, with no rebuild.

Finding 037 left one thread parked and three threads at 100% in a single
function index.  The shipped artifacts are linked without --profiling-funcs, so
they carry no name section and a profile can only say "36295".

The index is still answerable though: **imports keep their names even when
nothing else does**.  Decoding the function's body and resolving every call it
makes to an import says what the function is made of, which for a wait or a
spin is usually enough to name it.

Usage:
  inspect_wasm_function.py --wasm dist/profiles/.../probe.wasm --function 36295
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SECTION_NAMES = {
    0: "custom", 1: "type", 2: "import", 3: "function", 4: "table",
    5: "memory", 6: "global", 7: "export", 8: "start", 9: "element",
    10: "code", 11: "data", 12: "datacount", 13: "tag",
}

# The instructions this cares about: calls (who does it reach) and the atomic
# waits (is it a wait at all).  Everything else is skipped by length.
CALL = 0x10
CALL_INDIRECT = 0x11
ATOMIC_PREFIX = 0xFE
MEMORY_ATOMIC_WAIT32 = 0x01
MEMORY_ATOMIC_WAIT64 = 0x02
MEMORY_ATOMIC_NOTIFY = 0x00


def leb(data: bytes, i: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = data[i]
        i += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, i
        shift += 7


def sleb(data: bytes, i: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = data[i]
        i += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            if shift < 64 and byte & 0x40:
                result -= 1 << shift
            return result, i


def name(data: bytes, i: int) -> tuple[str, int]:
    length, i = leb(data, i)
    return data[i:i + length].decode("utf-8", "replace"), i + length


def parse(data: bytes) -> dict:
    imports: list[str] = []
    exports: dict[int, str] = {}
    code_entries: list[tuple[int, int]] = []  # (start, end) of each body
    i = 8
    while i < len(data):
        section_id = data[i]
        i += 1
        size, i = leb(data, i)
        end = i + size
        if section_id == 2:
            count, j = leb(data, i)
            for _ in range(count):
                module, j = name(data, j)
                field, j = name(data, j)
                kind = data[j]
                j += 1
                if kind == 0:  # function import
                    _, j = leb(data, j)
                    imports.append(f"{module}.{field}")
                elif kind == 1:  # table
                    j += 1
                    limits = data[j]
                    j += 1
                    _, j = leb(data, j)
                    if limits & 1:
                        _, j = leb(data, j)
                elif kind == 2:  # memory
                    limits = data[j]
                    j += 1
                    _, j = leb(data, j)
                    if limits & 1:
                        _, j = leb(data, j)
                elif kind == 3:  # global
                    j += 2
                elif kind == 4:  # tag
                    j += 1
                    _, j = leb(data, j)
        elif section_id == 7:
            # Exports keep their names too, and there are far more of them than
            # imports.  For a stripped build this is the only other name source.
            count, j = leb(data, i)
            for _ in range(count):
                export_name, j = name(data, j)
                kind = data[j]
                j += 1
                index, j = leb(data, j)
                if kind == 0:
                    exports.setdefault(index, export_name)
        elif section_id == 10:
            count, j = leb(data, i)
            for _ in range(count):
                body_size, j = leb(data, j)
                code_entries.append((j, j + body_size))
                j += body_size
        i = end
    return {"imports": imports, "exports": exports, "code": code_entries}


def scan_body(data: bytes, start: int, end: int) -> dict:
    """Walk the body far enough to collect calls and atomic waits.

    Not a full decoder: immediates are skipped by opcode class, which is
    enough for call targets and the atomic opcodes and wrong for nothing that
    is asked about here.  A miscount would show up as call targets far outside
    the function space, so the caller checks that.
    """
    calls: list[int] = []
    atomics: list[str] = []
    i = start
    while i < end:
        op = data[i]
        i += 1
        if op == CALL:
            target, i = leb(data, i)
            calls.append(target)
        elif op == CALL_INDIRECT:
            _, i = leb(data, i)
            _, i = leb(data, i)
        elif op == ATOMIC_PREFIX:
            sub, i = leb(data, i)
            if sub == MEMORY_ATOMIC_WAIT32:
                atomics.append("memory.atomic.wait32")
            elif sub == MEMORY_ATOMIC_WAIT64:
                atomics.append("memory.atomic.wait64")
            elif sub == MEMORY_ATOMIC_NOTIFY:
                atomics.append("memory.atomic.notify")
            if sub not in (0x03,):  # most atomics carry align+offset
                _, i = leb(data, i)
                _, i = leb(data, i)
        elif op in (0x02, 0x03, 0x04, 0x06):  # block/loop/if/try: blocktype
            if data[i] == 0x40 or 0x7B <= data[i] <= 0x7F:
                i += 1
            else:
                _, i = sleb(data, i)
        elif op in (0x0C, 0x0D, 0x07, 0x08, 0x09, 0x25, 0x26):  # br etc
            _, i = leb(data, i)
        elif op == 0x0E:  # br_table
            count, i = leb(data, i)
            for _ in range(count + 1):
                _, i = leb(data, i)
        elif op in (0x20, 0x21, 0x22, 0x23, 0x24, 0x3F, 0x40, 0xD2):
            _, i = leb(data, i)
        elif op == 0x41:
            _, i = sleb(data, i)
        elif op == 0x42:
            _, i = sleb(data, i)
        elif op == 0x43:
            i += 4
        elif op == 0x44:
            i += 8
        elif 0x28 <= op <= 0x3E:  # loads and stores: align + offset
            _, i = leb(data, i)
            _, i = leb(data, i)
        elif op == 0xFC:
            sub, i = leb(data, i)
            if sub in (8, 11):
                _, i = leb(data, i)
                _, i = leb(data, i)
            elif sub in (9, 10, 12, 13, 14, 15, 16, 17):
                _, i = leb(data, i)
                if sub in (10, 14):
                    _, i = leb(data, i)
    return {"calls": calls, "atomics": atomics}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--function", type=int, action="append", required=True)
    args = parser.parse_args()

    data = args.wasm.read_bytes()
    module = parse(data)
    imports = module["imports"]
    exports = module["exports"]
    code = module["code"]
    total = len(imports) + len(code)
    report = {
        "wasm": str(args.wasm),
        "importedFunctions": len(imports),
        "definedFunctions": len(code),
        "totalFunctions": total,
        "functions": [],
    }

    def label(index: int) -> str:
        if index < len(imports):
            return f"import:{imports[index]}"
        if index in exports:
            return f"export:{exports[index]}[{index}]"
        return f"wasm-function[{index}]"

    def body_of(index: int):
        if index < len(imports) or index - len(imports) >= len(code):
            return None
        return code[index - len(imports)]

    def nearest_named(root: int, max_depth: int = 4, budget: int = 4000):
        """Breadth-first outward until the call graph reaches named functions."""
        seen = {root}
        frontier = [root]
        found: list[tuple[int, str, int]] = []
        for depth in range(1, max_depth + 1):
            nxt = []
            for index in frontier:
                span = body_of(index)
                if not span or len(seen) > budget:
                    continue
                for target in scan_body(data, span[0], span[1])["calls"]:
                    if target >= total or target in seen:
                        continue
                    seen.add(target)
                    tag = label(target)
                    if tag.startswith(("import:", "export:")):
                        found.append((depth, tag, target))
                    else:
                        nxt.append(target)
            frontier = nxt
            if found:
                break
        return sorted(set(found))[:25]

    for index in args.function:
        entry: dict = {"index": index, "name": label(index)}
        if index < len(imports):
            report["functions"].append(entry)
            continue
        start, end = code[index - len(imports)]
        body = scan_body(data, start, end)
        entry["bodyBytes"] = end - start
        entry["atomics"] = sorted(set(body["atomics"]))
        counts: dict[str, int] = {}
        suspicious = 0
        for target in body["calls"]:
            if target >= total:
                suspicious += 1
                continue
            counts[label(target)] = counts.get(label(target), 0) + 1
        entry["calls"] = sorted(counts.items(), key=lambda kv: -kv[1])[:20]
        entry["callTargetsOutOfRange"] = suspicious
        entry["isExported"] = exports.get(index)
        entry["nearestNamed"] = [
            {"depth": d, "name": n} for d, n, _ in nearest_named(index)]
        report["functions"].append(entry)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
