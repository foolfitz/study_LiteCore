#!/usr/bin/env python3
"""Validate R5 hashes, exports, cache policy, browser evidence, and regressions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


REVIEW_EXPORTS = {
    "_oxsdk_abi_version",
    "_oxsdk_capabilities",
    "_oxsdk_engine_start",
    "_oxsdk_document_open",
    "_oxsdk_document_paint",
    "_oxsdk_document_click",
    "_oxsdk_document_insert_text",
    "_oxsdk_document_save",
    "_oxsdk_document_close",
    "_oxsdk_document_search",
    "_oxsdk_document_get_selection",
    "_oxsdk_document_replace_selection",
    "_oxsdk_document_undo",
    "_oxsdk_document_add_comment",
    "_oxsdk_document_list_comments",
    "_oxsdk_document_set_track_changes",
    "_oxsdk_document_list_changes",
    "_oxsdk_request_cancel",
    "_oxsdk_buffer_alloc",
    "_oxsdk_buffer_free",
}
READER_EXPORTS = {
    "_oxsdk_abi_version",
    "_oxsdk_capabilities",
    "_oxsdk_engine_start",
    "_oxsdk_document_open",
    "_oxsdk_document_paint",
    "_oxsdk_document_save",
    "_oxsdk_document_close",
    "_oxsdk_document_search",
    "_oxsdk_request_cancel",
    "_oxsdk_buffer_alloc",
    "_oxsdk_buffer_free",
}
EXPECTED_CORE_STATUS = {
    " M desktop/CustomTarget_soffice_bin-emscripten-exports.mk",
    " M solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk",
    " M solenv/gbuild/platform/unxgcc.mk",
    " M static/CustomTarget_emscripten_fs_image.mk",
    " M vcl/qt5/QtFrame.cxx",
    "?? LibreOffice_VCL_Qt6_研究報告.md",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_hashed_file(path: Path) -> dict[str, Any]:
    digest = sha256(path)
    match = re.search(r"\.([0-9a-f]{12,64})\.[^.]+$", path.name)
    name_hash = match.group(1) if match else ""
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": digest,
        "filenameHash": name_hash,
        "pass": bool(name_hash) and digest.startswith(name_hash),
    }


def loader_exports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
    return set(re.findall(r'Module\["(_(?:oxsdk|probe)_[^"]+)"\]', source))


def head_cache(base_url: str, relative: str) -> dict[str, Any]:
    request = urllib.request.Request(base_url.rstrip("/") + "/" + relative.lstrip("/"), method="HEAD")
    with urllib.request.urlopen(request, timeout=30) as response:
        return {
            "path": relative,
            "status": response.status,
            "cacheControl": response.headers.get("Cache-Control", ""),
        }


def summarize_browser(path: Path) -> dict[str, Any]:
    data = load_json(path)
    runs = [sample["run"] for sample in data["samples"]]
    timing_keys = sorted({key for run in runs for key in run if key.startswith("t_")})
    return {
        "path": str(path),
        "browser": data["browser"],
        "browserVersion": data["browser_version"],
        "cache": data["cache"],
        "samples": len(runs),
        "passed": sum(run.get("pass") is True for run in runs),
        "medianMs": {
            key: round(statistics.median(run[key] for run in runs if run.get(key) is not None), 3)
            for key in timing_keys
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser.add_argument("--profiles", type=Path, default=project / "dist" / "profiles")
    parser.add_argument(
        "--evidence", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r5",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--core", type=Path, default=workspace / "libreoffice-26-8")
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "findings" / "evidence" / "sdk-r5" / "summary.json",
    )
    args = parser.parse_args()

    inventory = load_json(args.profiles / "r5-inventory.json")
    profile_inventory = {item["profile"]: item for item in inventory["profiles"]}
    manifests = {
        name: load_json(args.profiles / name / "sdk-manifest.json")
        for name in ("full-qa", "writer-review", "writer-reader")
    }

    hash_checks: list[dict[str, Any]] = []
    cache_paths: set[str] = set()
    for name, manifest in manifests.items():
        profile_dir = args.profiles / name
        for relative in manifest["artifactFiles"].values():
            path = (profile_dir / relative).resolve()
            hash_checks.append(check_hashed_file(path))
            cache_paths.add(path.relative_to(project / "dist").as_posix())
        for pack in manifest["resourcePacks"]:
            for key in ("data", "metadata"):
                path = (profile_dir / pack[key]).resolve()
                hash_checks.append(check_hashed_file(path))
                cache_paths.add(path.relative_to(project / "dist").as_posix())
            metadata = load_json((profile_dir / pack["metadata"]).resolve())
            data_path = (profile_dir / pack["data"]).resolve()
            ranges_ok = bool(metadata["files"]) and metadata["files"][0]["start"] == 0
            previous_end = 0
            for entry in metadata["files"]:
                ranges_ok = ranges_ok and entry["start"] == previous_end and entry["end"] > entry["start"]
                previous_end = entry["end"]
            ranges_ok = ranges_ok and previous_end == data_path.stat().st_size
            hash_checks.append({
                "path": str(data_path),
                "packIntegrity": True,
                "rangesContiguous": ranges_ok,
                "manifestHashMatches": sha256(data_path) == pack["sha256"] == metadata["sha256"],
                "pass": ranges_ok and sha256(data_path) == pack["sha256"] == metadata["sha256"],
            })

    export_checks = {}
    for name, expected in (("writer-review", REVIEW_EXPORTS), ("writer-reader", READER_EXPORTS)):
        manifest = manifests[name]
        loader = args.profiles / name / manifest["artifactFiles"]["probe.js"]
        actual = loader_exports(loader)
        export_checks[name] = {
            "expected": sorted(expected),
            "actual": sorted(actual),
            "noLegacyProbe": not any(symbol.startswith("_probe_") for symbol in actual),
            "pass": actual == expected and not any(symbol.startswith("_probe_") for symbol in actual),
        }

    full = profile_inventory["full-qa"]
    size_checks = {}
    for name in ("writer-review", "writer-reader"):
        profile = profile_inventory[name]
        size_checks[name] = {
            "wasmRawReductionBytes": full["wasm"]["rawBytes"] - profile["wasm"]["rawBytes"],
            "wasmGzipReductionBytes": full["wasm"]["gzip9Bytes"] - profile["wasm"]["gzip9Bytes"],
            "startupResourceReductionBytes": full["startupResourceBytes"] - profile["startupResourceBytes"],
        }
        size_checks[name]["pass"] = all(value > 0 for value in size_checks[name].values())

    cache_results = [head_cache(args.base_url, path) for path in sorted(cache_paths)]
    entry_cache_results = [
        head_cache(args.base_url, path)
        for path in (
            "r5-reader.html",
            "r5-reader-app.js",
            "profiles/writer-reader/sdk-worker.js",
            "profiles/writer-reader/sdk-manifest.json",
        )
    ]
    cache_pass = all("immutable" in item["cacheControl"] for item in cache_results)
    cache_pass = cache_pass and all(item["cacheControl"] == "no-cache" for item in entry_cache_results)

    browser_paths = [
        args.evidence / "browser-raw" / "review" / f"{browser}-t1-plain-zh-cold-summary.json"
        for browser in ("chrome", "firefox")
    ] + [
        args.evidence / "browser-raw" / "reader" / f"{browser}-t1-plain-zh-{cache}-summary.json"
        for browser in ("chrome", "firefox")
        for cache in ("cold", "hot")
    ]
    browser = [summarize_browser(path) for path in browser_paths]
    browser_pass = all(item["samples"] >= 3 and item["samples"] == item["passed"] for item in browser)

    conformance_paths = [
        args.evidence / "conformance" / "review" / f"{browser_name}-r4-conformance.json"
        for browser_name in ("chrome", "firefox")
    ]
    conformance = [load_json(path) for path in conformance_paths]
    conformance_pass = all(item["conformance"]["pass"] for item in conformance)
    regression_files = {
        "r2": args.evidence / "regression" / "r2" / "chrome-t1-plain-zh-r2-conformance.json",
        "r3Conformance": args.evidence / "regression" / "r3-conformance" / "chrome-r3-conformance.json",
        "r3Flow": args.evidence / "regression" / "r3-flow" / "chrome-t1-plain-zh-cold-summary.json",
        "r1Flow": args.evidence / "regression" / "r1" / "chrome-t1-plain-zh-cold-summary.json",
    }
    regression = {name: load_json(path) for name, path in regression_files.items()}
    regression_pass = (
        regression["r2"]["conformance"]["pass"]
        and regression["r3Conformance"]["conformance"]["pass"]
        and regression["r3Flow"]["samples"][-1]["run"]["pass"]
        and regression["r1Flow"]["samples"][-1]["run"]["pass"]
    )

    roundtrip = {
        "reader": load_json(args.evidence / "reader-roundtrip.json"),
        "review": load_json(args.evidence / "review-roundtrip.json"),
        "r3": load_json(args.evidence / "regression" / "r3-roundtrip.json"),
        "r1": load_json(args.evidence / "regression" / "r1-roundtrip.json"),
    }
    roundtrip_pass = all(value.get("pass", all(
        document.get("pass", False) for document in value.get("documents", [])
    )) for value in roundtrip.values())

    core_status_output = subprocess.run(
        ["git", "-c", "core.quotePath=false", "-C", str(args.core), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    core_status = {line for line in core_status_output.splitlines() if line}
    core_pass = core_status == EXPECTED_CORE_STATUS

    checks = {
        "resourceProof": all(inventory["proof"].values()),
        "artifactHashes": all(item["pass"] for item in hash_checks),
        "exports": all(item["pass"] for item in export_checks.values()),
        "sizeReduction": all(item["pass"] for item in size_checks.values()),
        "cachePolicy": cache_pass,
        "browserMatrix": browser_pass,
        "providerConformance": conformance_pass,
        "regressions": regression_pass,
        "roundtrip": roundtrip_pass,
        "coreUnchanged": core_pass,
        "automationNotShippable": inventory["writer-automation"]["status"] == "not-shippable"
        and inventory["writer-automation"]["binaryProduced"] is False,
    }
    result = {
        "schemaVersion": 1,
        "release": "R5",
        "decision": "GO" if all(checks.values()) else "STOP",
        "checks": checks,
        "size": size_checks,
        "browser": browser,
        "exports": export_checks,
        "hashChecks": hash_checks,
        "cache": {"hashed": cache_results, "entries": entry_cache_results},
        "coreStatus": sorted(core_status),
        "inventory": str(args.profiles / "r5-inventory.json"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"decision": result["decision"], "checks": checks}, ensure_ascii=False, indent=2))
    print(args.output)
    if result["decision"] != "GO":
        raise SystemExit("R5 validation failed")


if __name__ == "__main__":
    main()
