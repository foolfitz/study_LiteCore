#!/usr/bin/env python3
"""Validate the frozen E1-C product editor matrix and decide the E1 gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from build_e1_b_profile import EDITOR_ACTIONS
from e1_support import inspect_odt, sha256, write_json
from r7_support import desktop_pdf_roundtrip


PHASE_PATHS = {
    "integration": "browser",
    "recovery": "recovery",
    "corpus": "corpus",
    "lifecycle": "lifecycle",
}
EXPECTED_CASES = {
    "integration": [f"integration-{index:02d}" for index in range(1, 4)],
    "recovery": [
        "boundary-start", "boundary-table", "crash-preedit", "crash-queued",
        "crash-unsaved", "crash-saved", "crash-after-checkpoint",
    ],
    "corpus": ["l0-t1", "l0-t2", "l0-t3", "l1-review-odt", "l4-stress-100"],
    "lifecycle": [f"cycle-{index:02d}" for index in range(1, 11)],
}
FIXTURE_ANCHORS = {
    "plain-grapheme": [
        "E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme",
        "combining é boundary", "E1-PLAIN-END",
    ],
    "table-boundary": [
        "E1-TABLE-BEFORE", "E1-CELL-A1", "E1-CELL-B2", "E1-TABLE-AFTER",
    ],
    "l0-t1": ["Final line：ODT round-trip 完整性檢查。"],
    "l0-t2": ["文件結尾：請確認表格、圖片、註解與標題樣式均保留。"],
    "l0-t3": [
        "第 1 頁：長文件記憶體與效能測試",
        "第 22 頁：長文件記憶體與效能測試",
    ],
    "l1-review-odt": ["Lorem ipsum"],
    "l4-stress-100": [
        "R7 stress page 001 頁面錨點",
        "R7 stress page 050 頁面錨點",
        "R7 stress page 100 頁面錨點",
    ],
}
BASE_ARTIFACT_HASH_KEYS = ("loaderSha256", "wasmSha256", "workerSha256")
SHELL_BUNDLE_HASH_KEY = "shellBundleSha256"
SHELL_BUNDLE_MANIFEST = Path("e1/editor-shell-bundle-v2.json")
DEFAULT_MATRIX = Path("e1/validation-matrix-v1.json")
CORE_BASELINE_HEAD = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
CORE_BASELINE_STATUS = [
    " M desktop/CustomTarget_soffice_bin-emscripten-exports.mk",
    " M solenv/gbuild/platform/EMSCRIPTEN_INTEL_GCC.mk",
    " M solenv/gbuild/platform/unxgcc.mk",
    " M static/CustomTarget_emscripten_fs_image.mk",
    " M vcl/qt5/QtFrame.cxx",
    "?? LibreOffice_VCL_Qt6_研究報告.md",
]


def latest_directory(base: Path) -> Path:
    attempts = sorted(path for path in base.glob("attempt-*") if path.is_dir())
    return attempts[-1] if attempts else base


def load_json(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def artifact_hash_keys(matrix: dict[str, Any] | None = None) -> tuple[str, ...]:
    baseline = (matrix or {}).get("baseline") or {}
    if baseline.get(SHELL_BUNDLE_HASH_KEY):
        return (*BASE_ARTIFACT_HASH_KEYS, SHELL_BUNDLE_HASH_KEY)
    return BASE_ARTIFACT_HASH_KEYS


def evidence_artifact(
    value: dict[str, Any], keys: tuple[str, ...] = BASE_ARTIFACT_HASH_KEYS,
) -> dict[str, Any]:
    """The artifact hashes a run recorded about itself, or Nones if it recorded none."""
    artifact = value.get("artifact") or {}
    contract = ((value.get("artifact") or {}).get("editorContract")) or {}
    return {
        key: artifact.get(key) if key == SHELL_BUNDLE_HASH_KEY else contract.get(key)
        for key in keys
    }


IMPORT_PATTERN = re.compile(r'^\s*import(?:[\s\S]*?from\s*)?["\']([^"\']+)["\'];?', re.MULTILINE)


def loaded_shell_modules(project: Path) -> list[str]:
    """Follow local JS imports and return shell/input modules loaded by E1-C."""
    entry = project / "web" / "e1-editor-validation-app.js"
    pending = [entry]
    visited: set[Path] = set()
    loaded: set[str] = set()
    while pending:
        path = pending.pop()
        resolved = path.resolve()
        if resolved in visited or not path.is_file():
            continue
        visited.add(resolved)
        text = path.read_text(encoding="utf-8")
        # The source entrypoint lives under web/ but is copied to dist/ root;
        # its relative imports therefore resolve from the project/dist root.
        # All dependencies retain their source-relative directory structure.
        import_base = project if path == entry else path.parent
        for specifier in IMPORT_PATTERN.findall(text):
            if not specifier.startswith("."):
                continue
            dependency = (import_base / specifier).resolve()
            try:
                relative = dependency.relative_to(project.resolve())
            except ValueError:
                continue
            pending.append(dependency)
            relative_text = relative.as_posix()
            if relative.parts[0] in {"editor-shell", "input"}:
                loaded.add(relative_text)
    return sorted(loaded)


def shell_bundle_digest(hashes: dict[str, str | None]) -> str | None:
    if not hashes or any(not value for value in hashes.values()):
        return None
    payload = "".join(
        f"{path}\0{hashes[path]}\n" for path in sorted(hashes)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def shell_bundle_inventory(project: Path) -> dict[str, Any]:
    manifest_path = project / SHELL_BUNDLE_MANIFEST
    manifest = load_json(manifest_path, {})
    included = manifest.get("included") or []
    excluded = manifest.get("excluded") or []
    loaded = loaded_shell_modules(project)
    available = sorted(
        path.relative_to(project).as_posix()
        for directory in (project / "editor-shell", project / "input")
        for path in directory.glob("*.js")
    )
    included_paths = [str(item.get("path")) for item in included]
    excluded_paths = [str(item.get("path")) for item in excluded]
    expected_hashes = {
        str(item.get("path")): item.get("sha256") for item in included
    }
    source_hashes: dict[str, str | None] = {}
    dist_hashes: dict[str, str | None] = {}
    files = []
    differences = []
    for path, expected in expected_hashes.items():
        source_path = project / path
        dist_path = project / "dist" / path
        source_hash = sha256(source_path) if source_path.is_file() else None
        dist_hash = sha256(dist_path) if dist_path.is_file() else None
        source_hashes[path] = source_hash
        dist_hashes[path] = dist_hash
        if source_hash != expected:
            differences.append({
                "path": path, "side": "source", "observed": source_hash,
                "expected": expected,
            })
        if dist_hash != expected:
            differences.append({
                "path": path, "side": "dist", "observed": dist_hash,
                "expected": expected,
            })
        files.append({
            "path": path,
            "expectedSha256": expected,
            "sourceSha256": source_hash,
            "distSha256": dist_hash,
            "sourcePass": source_hash == expected,
            "distPass": dist_hash == expected,
        })
    source_bundle = shell_bundle_digest(source_hashes)
    dist_bundle = shell_bundle_digest(dist_hashes)
    expected_bundle = manifest.get("bundleSha256")
    unaccounted = sorted(set(available) - set(included_paths) - set(excluded_paths))
    missing = sorted((set(included_paths) | set(excluded_paths)) - set(available))
    exclusions_have_reasons = all(
        item.get("path") and str(item.get("reason", "")).strip() for item in excluded
    )
    passed = (
        manifest.get("schemaVersion") == 1
        and manifest.get("release") == "E1-C-editor-shell-bundle"
        and included_paths == loaded
        and sorted(excluded_paths) == sorted(set(available) - set(loaded))
        and len(included_paths) == len(set(included_paths))
        and len(excluded_paths) == len(set(excluded_paths))
        and exclusions_have_reasons
        and not unaccounted
        and not missing
        and not differences
        and source_bundle == expected_bundle
        and dist_bundle == expected_bundle
    )
    return {
        "manifest": str(manifest_path),
        "algorithm": manifest.get("algorithm"),
        "loadedModules": loaded,
        "availableModules": available,
        "included": files,
        "excluded": excluded,
        "unaccountedModules": unaccounted,
        "missingModules": missing,
        "differences": differences,
        "sourceBundleSha256": source_bundle,
        "distBundleSha256": dist_bundle,
        "expectedBundleSha256": expected_bundle,
        "pass": passed,
    }


def profile_inventory(project: Path) -> dict[str, Any]:
    profile = project / "dist" / "profiles" / "e1-editor-v1"
    manifest_path = profile / "sdk-manifest.json"
    exports_path = project / "build" / "e1" / "editor-v1" / "exports.txt"
    manifest = load_json(manifest_path, {})
    exports = exports_path.read_text(encoding="utf-8").splitlines() if exports_path.is_file() else []
    contract = manifest.get("editorContract") or {}
    forbidden_exports = [entry for entry in exports if "editor_discovery" in entry]
    passed = (
        manifest.get("profile") == "e1-editor-v1"
        and "narrow-editor-v1" in manifest.get("capabilities", [])
        and "diagnostic" not in manifest
        and contract.get("version") == 1
        and contract.get("actions") == EDITOR_ACTIONS
        and contract.get("automaticRetry") is False
        and contract.get("rawCallbackExposed") is False
        and contract.get("arbitraryKeyCodeAccepted") is False
        and contract.get("arbitraryUnoCommandAccepted") is False
        and "_oxsdk_editor_action" in exports
        and "_oxsdk_editor_get_state" in exports
        and not forbidden_exports
    )
    shell_bundle = shell_bundle_inventory(project)
    return {
        "manifest": str(manifest_path),
        "exports": str(exports_path),
        "loaderSha256": sha256(profile / "probe.js") if (profile / "probe.js").is_file() else None,
        "wasmSha256": sha256(profile / "probe.wasm") if (profile / "probe.wasm").is_file() else None,
        "workerSha256": sha256(profile / "sdk-worker.js") if (profile / "sdk-worker.js").is_file() else None,
        "shellBundleSha256": shell_bundle.get("distBundleSha256"),
        "shellBundle": shell_bundle,
        "actions": contract.get("actions"),
        "forbiddenExports": forbidden_exports,
        "pass": passed,
    }


def command_version(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=30,
        )
        return {
            "command": command,
            "available": completed.returncode == 0,
            "returnCode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "command": command,
            "available": False,
            "error": {"name": type(error).__name__, "message": str(error)},
        }


def workspace_preflight(
    project: Path, root: Path, matrix: dict[str, Any], phase: str,
) -> dict[str, Any]:
    core = project.parent / "libreoffice-26-8"
    preserved = root / "baseline" / "core-status-before.txt"
    if phase == "before" and preserved.is_file():
        lines = preserved.read_text(encoding="utf-8").splitlines()
        head = lines[0] if lines else None
        status = lines[1:]
        capture = "preserved-entry-baseline"
    else:
        head_result = subprocess.run(
            ["git", "-C", str(core), "rev-parse", "HEAD"],
            check=False, capture_output=True, text=True, timeout=30,
        )
        status_result = subprocess.run(
            ["git", "-c", "core.quotepath=false", "-C", str(core), "status", "--short"],
            check=False, capture_output=True, text=True, timeout=30,
        )
        head = head_result.stdout.strip()
        status = status_result.stdout.splitlines()
        capture = "live-workspace"
    profile = profile_inventory(project)
    baseline = matrix.get("baseline", {})
    artifact_checks = {
        "loader": {
            "observed": profile.get("loaderSha256"),
            "expected": baseline.get("loaderSha256"),
        },
        "wasm": {
            "observed": profile.get("wasmSha256"),
            "expected": baseline.get("wasmSha256"),
        },
        "worker": {
            "observed": profile.get("workerSha256"),
            "expected": baseline.get("workerSha256"),
        },
    }
    shell_required = bool(baseline.get(SHELL_BUNDLE_HASH_KEY))
    if shell_required:
        artifact_checks["shellBundle"] = {
            "observed": profile.get(SHELL_BUNDLE_HASH_KEY),
            "expected": baseline.get(SHELL_BUNDLE_HASH_KEY),
        }
    for value in artifact_checks.values():
        value["pass"] = value["observed"] == value["expected"]
    environment = {
        "chrome": command_version(["/usr/bin/google-chrome", "--version"]),
        "firefox": command_version(["/usr/bin/firefox", "--version"]),
        "geckodriver": command_version(["/snap/bin/geckodriver", "--version"]),
        "node": command_version(["node", "--version"]),
        "python": command_version(["python3", "--version"]),
        "soffice": command_version(["/usr/bin/soffice", "--version"]),
    }
    # The matrix carries its own baseline.coreCommit, and until 2026-08-10 nobody
    # read it: this gate compared the measured HEAD against the module constant
    # and never noticed if the frozen matrix disagreed with it.  An unread claim
    # is what finding 029 was about, so compare the two copies as well -- E1's
    # matrix against E1's constant.  This is deliberately within one release; the
    # frozen baselines of E1/R6/R7/R8 are allowed to differ from each other.
    matrix_commit_pass = baseline.get("coreCommit") == CORE_BASELINE_HEAD
    core_pass = (head == CORE_BASELINE_HEAD and status == CORE_BASELINE_STATUS
                 and matrix_commit_pass)
    result = {
        "schemaVersion": 1,
        "release": "E1-C-editor-validation",
        "phase": phase,
        "capture": capture,
        "core": {
            "head": head,
            "expectedHead": CORE_BASELINE_HEAD,
            "status": status,
            "expectedStatus": CORE_BASELINE_STATUS,
            "matrixCommit": baseline.get("coreCommit"),
            "matrixCommitPass": matrix_commit_pass,
            "pass": core_pass,
        },
        "profile": {
            "name": baseline.get("profile"),
            "surfacePass": profile.get("pass") is True,
            "artifacts": artifact_checks,
            "shellBundle": profile.get("shellBundle"),
            "shellConsistencyRequired": shell_required,
            "pass": profile.get("pass") is True
            and all(value["pass"] for value in artifact_checks.values())
            and (not shell_required or profile.get("shellBundle", {}).get("pass") is True),
        },
        "environment": environment,
    }
    result["pass"] = (
        result["core"]["pass"]
        and result["profile"]["pass"]
        and all(value.get("available") is True for value in environment.values())
    )
    return result


def expected_cases_for_matrix(matrix: dict[str, Any]) -> dict[str, list[str]]:
    if matrix.get("schemaVersion") == 1:
        return {
            **EXPECTED_CASES,
            "recovery": [
                value for value in EXPECTED_CASES["recovery"]
                if value != "crash-after-checkpoint"
            ],
        }
    return EXPECTED_CASES


def collect_cases(
    root: Path, matrix: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_cases = expected_cases_for_matrix(matrix or {"schemaVersion": 2})
    cases: list[dict[str, Any]] = []
    phases: dict[str, Any] = {}
    for phase, category in PHASE_PATHS.items():
        phase_results = []
        for browser in ("chrome", "firefox"):
            summary_path = root / category / browser / "summary.json"
            summary = load_json(summary_path, {"pass": False, "error": "missing summary"})
            phases[f"{phase}:{browser}"] = {
                "path": str(summary_path),
                "pass": summary.get("pass") is True,
                "expectedCases": summary.get("expectedCases"),
                "completedCases": summary.get("completedCases"),
                "memory": summary.get("memory"),
            }
            for case_name in expected_cases[phase]:
                directory = latest_directory(root / category / browser / case_name)
                result_path = directory / "result.json"
                result = load_json(result_path, {})
                entry = {
                    "phase": phase,
                    "browser": browser,
                    "case": case_name,
                    "directory": str(directory),
                    "resultPath": str(result_path),
                    "result": result,
                    "pass": result.get("pass") is True,
                }
                cases.append(entry)
                phase_results.append(entry)
        phases[phase] = {
            "expectedCases": len(expected_cases[phase]) * 2,
            "observedCases": len([item for item in phase_results if item["result"]]),
            "pass": len(phase_results) == len(expected_cases[phase]) * 2
            and all(item["pass"] for item in phase_results),
        }
    return cases, phases


def artifact_binding(
    cases: list[dict[str, Any]], project: Path,
    matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind every automatic phase result to the artifact that is in dist/ right now.

    The manual gate has compared the hashes a run recorded against the profile on
    disk since E1-C was frozen (see manual_gate); the automatic phases did not.
    That asymmetry was found on 2026-08-07: the E1-D and underline/strikethrough
    relinks invalidated the manual round by construction while leaving 48 browser
    cases silently alive, so the gate could reach PARTIAL_GO carrying evidence
    that described a binary no longer shipped.  A rebuild invalidates *all* of
    E1-C's evidence, not the trusted-input half of it.

    Evidence that does not name the artifact it ran against does not bind either;
    an unattributable pass is not weaker proof than a stale one, it is none.
    """
    profile = profile_inventory(project)
    keys = artifact_hash_keys(matrix)
    expected = {key: profile.get(key) for key in keys}
    results = []
    for entry in cases:
        observed = evidence_artifact(entry["result"], keys)
        if not any(observed.values()):
            reason = "result does not record the artifact it ran against"
        elif observed != expected:
            reason = "result was produced by a superseded artifact"
        else:
            reason = None
        results.append({
            "phase": entry["phase"],
            "browser": entry["browser"],
            "case": entry["case"],
            "resultPath": entry["resultPath"],
            "observed": observed,
            "pass": reason is None,
            "reason": reason,
        })
    counted = lambda reason: sum(1 for item in results if item["reason"] == reason)  # noqa: E731
    return {
        "schemaVersion": 1,
        "release": "E1-C-editor-validation",
        "expected": expected,
        "results": results,
        "boundCases": sum(1 for item in results if item["pass"]),
        "supersededCases": counted("result was produced by a superseded artifact"),
        "unattributableCases": counted("result does not record the artifact it ran against"),
        "pass": bool(results) and all(item["pass"] for item in results),
    }


def text_expectations(entry: dict[str, Any]) -> tuple[list[str], list[str]]:
    result = entry["result"]
    case = result.get("case") or {}
    scenario = case.get("scenario")
    fixture = case.get("fixture")
    required: list[str] = []
    forbidden: list[str] = []
    if scenario == "integration":
        required = [
            "E1-PLAIN-START",
            "emoji 😀 grapheme",
            "combining é boundary",
            "E1C-COMMIT-臺灣😀",
            "E1C-AFTER-MOVE",
            "臺灣中文游標測E1C-REPLACE",
            "012345678E1C-PASTE-臺灣😀",
            "E1C-PARAGRAPH",
            "E1C-LINE",
        ]
        forbidden = ["E1C-CANCEL", "E1C-UNDO", "<b>forbidden</b>"]
    elif str(scenario).startswith("boundary-"):
        required = FIXTURE_ANCHORS.get(fixture, [])
        forbidden = ["E1C-BOUNDARY-QUEUED-MUST-NOT-REPLAY"]
    elif scenario == "crash-after-checkpoint":
        required = [
            *FIXTURE_ANCHORS["plain-grapheme"],
            "E1C-CKPT-MUST-SURVIVE",
        ]
        forbidden = [
            "E1C-CKPT-MUST-NOT-RETURN",
            "E1C-CKPT-PREEDIT-FORBIDDEN",
            "E1C-CKPT-QUEUED",
        ]
    elif str(scenario).startswith("crash-"):
        marker = f"E1C-{str(scenario).upper()}-MUST-"
        if scenario == "crash-saved":
            required = [f"{marker}SURVIVE"]
        else:
            forbidden = [f"{marker}NOT-REPLAY"]
        forbidden.extend([f"{marker}NOT-REPLAY-FIRST", f"{marker}NOT-REPLAY-QUEUED"])
        required.extend(FIXTURE_ANCHORS["plain-grapheme"])
    elif scenario == "corpus":
        required = [*FIXTURE_ANCHORS.get(fixture, []), f"E1C-{fixture}-臺灣😀"]
    elif scenario == "lifecycle":
        required = [
            *FIXTURE_ANCHORS["plain-grapheme"],
            f"E1C-LIFECYCLE-{int(case.get('repetition', 0)):02d}",
        ]
    return required, forbidden


def desktop_required(entry: dict[str, Any]) -> bool:
    result = entry["result"]
    case = result.get("case") or {}
    phase = case.get("phase")
    if phase == "corpus":
        return True
    if phase == "integration" and case.get("repetition") == 3:
        return True
    if case.get("scenario") in {"crash-saved", "crash-after-checkpoint"}:
        return True
    if phase == "lifecycle" and case.get("repetition") == 10:
        return True
    return False


def recorded_roundtrips(previous: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Index a previous roundtrip summary by case identity."""
    return {
        (item.get("phase"), item.get("browser"), item.get("case")): item
        for item in previous.get("documents", [])
        if item.get("phase") and item.get("browser") and item.get("case")
    }


def validate_outputs(cases: list[dict[str, Any]], skip_desktop: bool,
                     previous: dict[str, Any] | None = None,
                     refresh_desktop: bool = False) -> dict[str, Any]:
    recorded = recorded_roundtrips(previous or {})
    reused_count = 0
    documents = []
    for entry in cases:
        directory = Path(entry["directory"])
        source = directory / "output.odt"
        inspected = inspect_odt(source)
        required, forbidden = text_expectations(entry)
        text = inspected.get("text", "")
        required_results = [
            {"text": value, "count": text.count(value), "pass": text.count(value) >= 1}
            for value in required
        ]
        forbidden_results = [
            {"text": value, "count": text.count(value), "pass": text.count(value) == 0}
            for value in forbidden
        ]
        need_desktop = desktop_required(entry)
        # Reuse a recorded round-trip when the input ODT is byte-identical to
        # the one it was recorded from.  Re-running rewrites desktop.pdf, and
        # LibreOffice stamps a fresh CreationDate into every export, so the run
        # can never reproduce the recorded pdfSha256 anyway -- validating was
        # silently mutating the evidence it was validating, every single time.
        source_sha = sha256(source) if source.is_file() else None
        prior = recorded.get((entry["phase"], entry["browser"], entry["case"]))
        prior_desktop = (prior or {}).get("desktop") or {}
        can_reuse = (
            not refresh_desktop
            and prior is not None
            and source_sha is not None
            and prior.get("sha256") == source_sha
            and prior_desktop.get("pass") is True
            and prior_desktop.get("skipped") is not True
            and (directory / "desktop.pdf").is_file()
        )
        if need_desktop and can_reuse:
            desktop = {**prior_desktop, "reused": True}
            reused_count += 1
        elif need_desktop and not skip_desktop:
            desktop = desktop_pdf_roundtrip(source, directory / "desktop.pdf")
        elif need_desktop:
            # Skipping a required check means it was not measured, and not
            # measured has to fail: until 2026-08-08 this recorded pass=True,
            # so --skip-desktop could carry a run all the way to
            # E1_GO_ODT_EDITOR without a single desktop round-trip ever having
            # run.  The flag still works -- it just can no longer launder an
            # absent measurement into a passing one.
            desktop = {"pass": False, "skipped": True}
        else:
            desktop = {"pass": True, "required": False}
        passed = (
            entry["pass"]
            and inspected.get("exists") is True
            and inspected.get("zip") is True
            and inspected.get("crc") is True
            and inspected.get("xml") is True
            and all(item["pass"] for item in required_results + forbidden_results)
            and desktop.get("pass") is True
        )
        documents.append({
            "phase": entry["phase"],
            "browser": entry["browser"],
            "case": entry["case"],
            "path": str(source),
            "bytes": source.stat().st_size if source.is_file() else None,
            "sha256": source_sha,
            "inspection": {
                key: inspected.get(key)
                for key in ("exists", "zip", "crc", "xml", "paragraphs", "headings", "lists", "tables")
            },
            "required": required_results,
            "forbidden": forbidden_results,
            "desktop": desktop,
            "pass": passed,
        })
    return {
        "schemaVersion": 1,
        "release": "E1-C-editor-validation",
        "documents": documents,
        "desktopRequired": sum(desktop_required(item) for item in cases),
        "desktopReused": reused_count,
        "desktopSkipped": sum(
            1 for item in documents if (item.get("desktop") or {}).get("skipped") is True
        ),
        "pass": bool(documents) and all(item["pass"] for item in documents),
    }


def manual_gate(
    root: Path, project: Path, matrix: dict[str, Any] | None = None,
    refresh_desktop: bool = False,
) -> dict[str, Any]:
    profile = profile_inventory(project)
    keys = artifact_hash_keys(matrix)
    results = []
    for browser in ("chrome", "firefox"):
        path = root / "manual" / f"{browser}-chewing.json"
        value = load_json(path, {})
        manual = value.get("manualEvidence", {})
        output_path = Path((value.get("savedOutput") or {}).get("path", ""))
        inspected = inspect_odt(output_path)
        text = inspected.get("text", "")
        required = [
            "E1C人工第一筆中文輸入",
            "E1C人工選取替換",
            "E1C人工原生貼上臺灣😀",
            "E1C人工剪貼簿臺灣😀",
        ]
        content = {
            "required": [
                # SPEC-E1-C section 6 item 5 says "exact anchor count", and this
                # said ">= 1" until 2026-08-14: a duplicated commit landing the
                # same anchor twice would have passed, which is exactly the
                # exactly-once property the whole milestone is about.  Both
                # browsers measure 1 for all four, so tightening costs nothing
                # and is not a moved goalpost (SPEC-E1-C v9).
                {"text": item, "count": text.count(item), "pass": text.count(item) == 1}
                for item in required
            ],
            "cancelledCount": text.count("E1C人工取消不得出現"),
        }
        content["pass"] = (
            all(item["pass"] for item in content["required"])
            and content["cancelledCount"] == 0
        )
        observed = evidence_artifact(value, keys)
        artifact_pass = (
            (value.get("artifact") or {}).get("profile") == "e1-editor-v1"
            and any(observed.values())
            and observed == {key: profile.get(key) for key in keys}
        )
        # Section 6 item 5 asks for a desktop reopen of the manual output, and
        # until 2026-08-14 no gate ever performed one: the manual ODT is not in
        # the roundtrip phase, and this gate stopped at zip/crc/xml plus anchor
        # counts.  That literal gap was present in every previous GO.  One
        # soffice invocation per browser, no operator cost (SPEC-E1-C v9).
        # A recorded `*.desktop.pdf` is never overwritten by a run that is only
        # reading.  Measured on 2026-08-16: running this validator to READ a
        # verdict rewrote both browsers' desktop PDFs in the namespace of an
        # operator round from 2026-08-07, because this phase -- added on
        # 2026-08-14 -- never got the guard the round-trip phase has had since
        # the same day, one function above.
        #
        # It re-exports either way, because the export succeeding IS the
        # measurement (SPEC-E1-C section 6 item 5).  What changes is where the
        # bytes land: to a scratch path when a record already exists, so the
        # round keeps the file it was judged with.  LibreOffice stamps a fresh
        # CreationDate into every export, so a re-export can never reproduce the
        # recorded bytes and "unchanged" is not available as a test.
        desktop_path = output_path.with_suffix(".desktop.pdf")
        if inspected.get("exists") is not True:
            desktop = {"pass": False, "reason": "manual output missing"}
        elif desktop_path.is_file() and not refresh_desktop:
            with tempfile.TemporaryDirectory() as scratch:
                desktop = desktop_pdf_roundtrip(
                    output_path, Path(scratch) / desktop_path.name)
            desktop["recordPreserved"] = str(desktop_path)
        else:
            desktop = desktop_pdf_roundtrip(output_path, desktop_path)
        content["desktop"] = desktop
        output_pass = all(
            inspected.get(key) is True for key in ("exists", "zip", "crc", "xml")
        ) and content["pass"] and desktop.get("pass") is True
        checks = {
            "operatorConfirmedChewing": manual.get("operatorInputMethod")
            == "Fcitx5 Chewing (operator-confirmed)",
            "trustedComposition": manual.get("trustedComposition") is True,
            "trustedNativeCopy": manual.get("nativeCopy", {}).get("isTrusted") is True,
            "trustedPaste": manual.get("trustedPaste") is True,
            "cancel": manual.get("cancelProbe", {}).get("pass") is True,
            "clipboardWrite": manual.get("clipboardWrite", {}).get("status") == "passed",
            "clipboardRead": manual.get("clipboardRead", {}).get("status") == "passed"
            and manual.get("clipboardRead", {}).get("found") is True,
            "artifact": artifact_pass,
            "output": output_pass,
        }
        results.append({
            "browser": browser,
            "path": str(path),
            "present": bool(value),
            "savedOutput": str(output_path) if str(output_path) else None,
            "checks": checks,
            "content": content,
            "pass": value.get("pass") is True and all(checks.values()),
        })
    return {
        "requiredBrowsers": 2,
        "results": results,
        "complete": all(item["present"] for item in results),
        "pass": all(item["pass"] for item in results),
    }


def run_regression(project: Path, root: Path) -> dict[str, Any]:
    command = [
        "make",
        "test-r6-release",
        "test-r7-b-static",
        "test-r7-c-static",
        "test-r7-d-static",
        "test-r8-d-static",
        "test-e1-a-static",
        "test-e1-b-static",
        "test-e1-c-static",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=project,
            check=False,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        result = {
            "command": command,
            "returnCode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "pass": completed.returncode == 0,
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        result = {
            "command": command,
            "error": {"name": type(error).__name__, "message": str(error)},
            "pass": False,
        }
    write_json(root / "regression" / "summary.json", result)
    return result


def decide(
    profile_safe: bool,
    binding_safe: bool,
    phases_safe: bool,
    outputs_safe: bool,
    lifecycle_safe: bool,
    regression_safe: bool,
    preflight_safe: bool,
    manual: dict[str, Any],
) -> dict[str, Any]:
    automatic = all((
        profile_safe,
        binding_safe,
        phases_safe,
        outputs_safe,
        lifecycle_safe,
        regression_safe,
        preflight_safe,
    ))
    if automatic and manual.get("pass") is True:
        decision = "E1_GO_ODT_EDITOR"
        complete = True
    elif automatic and manual.get("complete") is not True:
        decision = "E1_AUTOMATIC_GO_MANUAL_PENDING"
        complete = False
    elif automatic:
        decision = "E1_PARTIAL_GO_ODT_EDITOR"
        complete = True
    else:
        decision = "E1_STOP_OR_RESCOPE"
        complete = True
    return {"automaticPass": automatic, "decision": decision, "complete": complete}


def resolve_matrix_path(project: Path, value: Path) -> Path:
    if value.is_absolute():
        return value
    if value.parent == Path("."):
        return project / "e1" / value
    return project / value


def matrix_contract(matrix: dict[str, Any]) -> dict[str, Any]:
    schema = matrix.get("schemaVersion")
    expected_release = {
        1: "E1-C-editor-validation",
        2: "E1-C-editor-validation-next",
    }.get(schema)
    crash_scenarios = [
        value for value in matrix.get("recoveryScenarios", [])
        if str(value).startswith("crash-")
    ]
    crash_barriers = (matrix.get("thresholds") or {}).get("crashBarriersPerBrowser")
    checks = {
        "knownSchema": expected_release is not None,
        "release": matrix.get("release") == expected_release,
        "crashBarrierCount": crash_barriers == len(crash_scenarios),
    }
    if schema == 2:
        activation = matrix.get("activation") or {}
        # The activation block has two legal states and they are checked
        # against each other, not against a fixed answer.  Before the
        # rebinding, v2 is planned and v1 is the decision basis; after it
        # (2026-08-16), v2 IS the decision basis and says when it became one.
        # Half a transition -- activatedOn set while currentDecisionMatrix
        # still names v1, or the reverse -- fails, which is the case a fixed
        # assertion could not express.
        activated = bool(activation.get("activatedOn"))
        current = activation.get("currentDecisionMatrix")
        checks.update({
            "nextRebinding": activation.get("effectiveAt") == "next-rebinding",
            "activationConsistent": (
                current == "validation-matrix-v2.json" if activated
                else current == "validation-matrix-v1.json"),
            "shellBundleBaseline": bool(
                (matrix.get("baseline") or {}).get(SHELL_BUNDLE_HASH_KEY)
            ),
        })
    return {
        "schemaVersion": schema,
        "expectedRelease": expected_release,
        "crashScenarios": crash_scenarios,
        "crashBarriersPerBrowser": crash_barriers,
        "checks": checks,
        "pass": all(checks.values()),
    }


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=workspace / "findings" / "evidence" / "sdk-e1" / "editor-validation",
    )
    parser.add_argument("--skip-desktop", action="store_true")
    parser.add_argument(
        "--refresh-desktop", action="store_true",
        help="re-run every desktop round-trip even when the input ODT is "
        "unchanged, overwriting the recorded desktop.pdf files.  Off by "
        "default so validating does not mutate the evidence it validates",
    )
    parser.add_argument("--run-regression", action="store_true")
    parser.add_argument("--write-preflight", choices=("before", "after"))
    parser.add_argument(
        "--matrix", type=Path, default=DEFAULT_MATRIX,
        help="matrix path relative to the project (a bare name resolves under e1/)",
    )
    args = parser.parse_args()
    root = args.evidence_root.resolve()

    matrix_path = resolve_matrix_path(project, args.matrix)
    matrix = load_json(matrix_path, {})
    if args.write_preflight:
        preflight = workspace_preflight(project, root, matrix, args.write_preflight)
        output = root / "baseline" / f"preflight-{args.write_preflight}.json"
        write_json(output, preflight)
        print(json.dumps({
            "output": str(output), "phase": args.write_preflight,
            "pass": preflight["pass"],
        }, ensure_ascii=False))
        if not preflight["pass"]:
            raise SystemExit(1)
        return
    profile = profile_inventory(project)
    write_json(root / "inventory" / "profile.json", profile)
    cases, phases = collect_cases(root, matrix)
    binding = artifact_binding(cases, project, matrix)
    write_json(root / "inventory" / "artifact-binding.json", binding)
    outputs = validate_outputs(
        cases, args.skip_desktop,
        previous=load_json(root / "roundtrip" / "summary.json", {}),
        refresh_desktop=args.refresh_desktop,
    )
    write_json(root / "roundtrip" / "summary.json", outputs)
    manual = manual_gate(root, project, matrix,
                         refresh_desktop=args.refresh_desktop)
    regression = run_regression(project, root) if args.run_regression else load_json(
        root / "regression" / "summary.json", {"pass": False, "error": "missing regression"}
    )
    before = load_json(root / "baseline" / "preflight-before.json", {})
    after = load_json(root / "baseline" / "preflight-after.json", {})
    preflight_safe = before.get("pass") is True and after.get("pass") is True
    lifecycle_safe = all(
        phases.get(f"lifecycle:{browser}", {}).get("memory", {}).get("pass") is True
        for browser in ("chrome", "firefox")
    )
    phases_safe = all(phases.get(phase, {}).get("pass") is True for phase in PHASE_PATHS)
    result = {
        "schemaVersion": 1,
        "release": "E1-C-editor-validation",
        "matrix": {
            "path": str(matrix_path),
            "status": matrix.get("status"),
            "corpusCount": len(matrix.get("corpus", [])),
            **matrix_contract(matrix),
        },
        "profile": profile,
        "artifactBinding": binding,
        "phases": phases,
        "caseCount": len(cases),
        "roundtrip": outputs,
        "manual": manual,
        "regression": regression,
        "preflight": {
            "before": str(root / "baseline" / "preflight-before.json"),
            "after": str(root / "baseline" / "preflight-after.json"),
            "pass": preflight_safe,
        },
        "properties": {
            "profileFailClosed": profile["pass"],
            "evidenceArtifactBinding": binding["pass"],
            "browserPhases": phases_safe,
            "odtRoundtrip": outputs["pass"],
            "boundedLifecycle": lifecycle_safe,
            "regression": regression.get("pass") is True,
            "workspaceBaseline": preflight_safe,
            "trustedManualDelta": manual["pass"],
        },
        **decide(
            profile["pass"], binding["pass"], phases_safe, outputs["pass"],
            lifecycle_safe, regression.get("pass") is True, preflight_safe, manual,
        ),
    }
    write_json(root / "summary.json", result)
    print(json.dumps({
        "output": str(root / "summary.json"),
        "automaticPass": result["automaticPass"],
        "complete": result["complete"],
        "decision": result["decision"],
        "failedProperties": [
            name for name, value in result["properties"].items() if value is not True
        ],
        "artifactBinding": {
            key: binding[key]
            for key in ("boundCases", "supersededCases", "unattributableCases")
        },
    }, ensure_ascii=False))
    if result["decision"] == "E1_STOP_OR_RESCOPE":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
