#!/usr/bin/env python3
"""The merge table an engine is judged by (SPEC-M3-K-0.2.44 append 2; ruling findings/evidence/k-0.2.44/merge-keying/RULING.md).

`run_merge_wasm_shakedown.py` and `judge_counted_m2.py` are bound and are not edited.  Both key C on a literal in the wasm
bytes, and the ordered engine (v23 on) composes that string at run time, so they read v28 as an engine without C and hold
it to refusals it no longer makes, by design (SPEC-M3-ordered-commands A4, A5, section 16.2).  The K wrappers replace, in
process, the keying and the table, and record what they read:

  table "ordered-abi6"  manifest editorContract.abiVersion >= 6, and editorContract.wasmSha256 equal to the sha256 of the
                        wasm served and to the bound wasm: `nothing-selected`, `key-noop`, `refused-k1-*` expect the no-op
  table "c"             the literal is in the bytes (v20-v22): the runner's own C row, unchanged
  table "refusal"       neither: the runner's own refusals, unchanged

A claim of ABI >= 6 whose manifest does not name the served wasm does not get the ordered table.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

ORDERED = "ordered-abi6"
MOVED = ("key-noop",)                  # plus every `refused-k1-*`; `nothing-selected` is C's own row


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_of(key: dict[str, Any], bound_wasm: str | None) -> str:
    abi = key.get("abiVersion")
    if isinstance(abi, int) and abi >= 6 and key.get("manifestWasmSha256") == key.get("servedWasmSha256") == bound_wasm:
        return ORDERED
    return "c" if key.get("fragmentInBytes") else "refusal"


def read_key(wasm: Path, fragment: bytes, bound_wasm: str | None) -> dict[str, Any]:
    """What the table is decided from, read from the wasm and the manifest beside it."""
    data = wasm.read_bytes()
    beside = wasm.with_name("sdk-manifest.json")
    contract = (json.loads(beside.read_text()).get("editorContract") or {}) if beside.is_file() else {}
    key = {"fragmentInBytes": fragment in data, "abiVersion": contract.get("abiVersion"),
           "manifestWasmSha256": contract.get("wasmSha256"), "servedWasmSha256": hashlib.sha256(data).hexdigest(),
           "boundWasmSha256": bound_wasm}
    return {**key, "table": table_of(key, bound_wasm), "applied": True}


def require_ordered(key: dict[str, Any]) -> None:
    """The K wrapper's refusal, before any browser: a count on this table or none."""
    if key.get("table") != ORDERED:
        raise SystemExit(f"not the ordered table: {key}; the merge count of K runs on the bound v28 wasm only")


def install(runner: Any, owner: Any, key: dict[str, Any]) -> None:
    """Replace `runner.boundary_noop_declared` and `owner.expectation` in process.  `owner` is the runner when running and
    the judge when judging: each has its own `expectation`, with its own return shape, so a moved decision is handed to
    the original under C's row.  A caller passing no keying (`tool_cases(frame_cell=False)`, the case order) still gets
    the refusal table."""
    ordered = key["table"] == ORDERED
    keyed_on_bytes: Callable[[Path], bool] = runner.boundary_noop_declared
    original = owner.expectation

    def declared(wasm: Path) -> bool:
        return (ordered and sha256(wasm) == key["servedWasmSha256"]) or keyed_on_bytes(wasm)

    def expectation(decision, boundary_noop=False):
        if ordered and boundary_noop and decision and (decision in MOVED or decision.startswith("refused-k1-")):
            decision = "nothing-selected"
        return original(decision, boundary_noop)

    runner.boundary_noop_declared = declared
    owner.expectation = expectation
