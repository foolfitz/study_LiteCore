#!/usr/bin/env python3
"""Aggregate R1 artifact and browser evidence into metrics.json."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


TIMING_KEYS = (
    "t_ready_ms",
    "t_open_ms",
    "t_first_tile_ms",
    "t_insert_ms",
    "t_save_ms",
)


def compressed_size(command: list[str]) -> int:
    with tempfile.TemporaryFile() as output:
        subprocess.run(command, check=True, stdout=output)
        return int(output.tell())


def artifact_metrics(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "raw": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "gzip": compressed_size(["gzip", "-9", "-c", str(path)]),
    }
    brotli = shutil.which("brotli")
    result["brotli"] = (
        compressed_size([brotli, "-q", "11", "-c", str(path)])
        if brotli else None
    )
    return result


def percentile(values: list[float], probability: float) -> float | None:
    ordered = sorted(value for value in values if value is not None)
    if not ordered:
        return None
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def aggregate_runs(raw_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs: list[dict[str, Any]] = []
    memory: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*-summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        aggregate: dict[str, Any] = {
            "browser": summary["browser_version"],
            "browser_family": summary["browser"],
            "doc": summary["doc"],
            "cache": summary["cache"],
        }
        for key in TIMING_KEYS:
            aggregate[key] = []
        aggregate["insert_method"] = []

        for sample_index, sample in enumerate(summary["samples"]):
            run = sample["run"]
            for key in TIMING_KEYS:
                aggregate[key].append(run.get(key))
            aggregate["insert_method"].append(run.get("insert_method"))
            for measurement in sample.get("memory", []):
                item = dict(measurement)
                item.update({
                    "browser_family": summary["browser"],
                    "browser_version": summary["browser_version"],
                    "doc": summary["doc"],
                    "cache": summary["cache"],
                    "sample": sample_index + 1,
                })
                memory.append(item)
        aggregate["summary_ms"] = {
            key: {
                "p50": percentile(aggregate[key], 0.50),
                "p95": percentile(aggregate[key], 0.95),
            }
            for key in TIMING_KEYS
        }
        runs.append(aggregate)
    return runs, memory


def main() -> None:
    parser = argparse.ArgumentParser()
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser.add_argument("--dist", type=Path, default=project / "dist")
    parser.add_argument(
        "--raw-dir", type=Path,
        default=workspace / "findings" / "evidence" / "probe-r1" / "browser-raw",
    )
    parser.add_argument(
        "--memory-raw-dir", type=Path,
        default=workspace / "findings" / "evidence" / "probe-r1" / "memory-raw",
    )
    parser.add_argument(
        "--roundtrip", type=Path,
        default=workspace / "findings" / "evidence" / "probe-r1" / "roundtrip.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "probe-r1" / "metrics.json",
    )
    args = parser.parse_args()

    artifact_names = ("probe.wasm", "probe.js", "soffice.data")
    artifacts = {
        name: artifact_metrics(args.dist / name) for name in artifact_names
    }
    runs, memory = aggregate_runs(args.raw_dir)
    memory = [
        item for item in memory
        if not str(item.get("method", "")).startswith("skipped by memory=skip")
    ]
    if args.memory_raw_dir.is_dir():
        _, dedicated_memory = aggregate_runs(args.memory_raw_dir)
        memory.extend(dedicated_memory)
    roundtrip = []
    if args.roundtrip.is_file():
        roundtrip = json.loads(args.roundtrip.read_text(encoding="utf-8"))["documents"]

    core_commit = subprocess.run(
        ["git", "-C", str(workspace / "libreoffice-26-8"), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    emcc_line = subprocess.run(
        ["emcc", "--version"], check=True, capture_output=True, text=True,
    ).stdout.splitlines()[0]
    result = {
        "date": dt.date.today().isoformat(),
        "core_commit": core_commit,
        "emcc": "4.0.10",
        "emcc_version_line": emcc_line,
        "artifacts": artifacts,
        "compression_notes": {
            "brotli": "brotli executable unavailable; skipped"
            if not shutil.which("brotli") else "brotli -q 11",
            "gzip": "gzip -9",
        },
        "runs": runs,
        "memory": memory,
        "roundtrip": roundtrip,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)


if __name__ == "__main__":
    main()
