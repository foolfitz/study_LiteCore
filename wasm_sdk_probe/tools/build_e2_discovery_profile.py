#!/usr/bin/env python3
"""Assemble the isolated E2-A paragraph format discovery profile."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from e1_support import sha256, write_json

# The Worker gates every editorDiscovery* operation on one hardcoded diagnostic
# scope.  E2 needs the same operations under its own scope, but editing
# sdk/sdk-worker.js in place would change the bytes every other profile copies,
# so e1-editor-v1 and e1-editor-discovery could no longer be rebuilt to the
# hashes E1-C recorded.  Instead the divergence is applied to this profile's
# copy only -- the JS counterpart of the OXSDK_E2_FORMAT_BARRIER #ifdef that
# keeps the shared C++ translation unit byte-identical for non-E2 builds.
#
# Substitution is exact and must match exactly once.  A silent no-op here would
# produce a profile whose Worker rejects the very operations E2-A is measuring,
# and the failure would look like a missing capability rather than a build bug.
WORKER_GATE_BEFORE = """function editorDiscoveryEnabled() {
  return activeManifest?.diagnostic?.scope === "e1-odt-editing-discovery"
    && activeManifest?.capabilities?.includes("editor-discovery-closed-actions");
}"""

WORKER_GATE_AFTER = """function editorDiscoveryEnabled() {
  return (activeManifest?.diagnostic?.scope === "e1-odt-editing-discovery"
      || activeManifest?.diagnostic?.scope === "e2-paragraph-format-discovery"
      || activeManifest?.diagnostic?.scope === "e2-scheduler-attribution"
      || activeManifest?.diagnostic?.scope === "e2-mainloop-attribution"
      || activeManifest?.diagnostic?.scope === "e2-mainloop-pei-attribution"
      || activeManifest?.diagnostic?.scope === "e2-locale-attribution")
    && activeManifest?.capabilities?.includes("editor-discovery-closed-actions");
}"""

WORKER_MESSAGE_BEFORE = (
    '      message: "editor discovery operations require the isolated E1 diagnostic profile",'
)
WORKER_MESSAGE_AFTER = (
    '      message: "editor discovery operations require an isolated diagnostic profile",'
)

# The engine reports crosstalkCount and earlyStateCount so that "the barrier did
# not accept an unattributed state" is provable from evidence instead of
# asserted.  The shared Worker forwards a fixed field set that drops them, which
# left both counters reading null in the first A2-wasm evidence.  Diagnostic
# profiles get them through; the product path is untouched.
WORKER_BARRIER_BEFORE = """        if (operation !== "editorActionV1")
          result.selectionBarrier = event.selectionBarrier;"""

WORKER_BARRIER_AFTER = """        if (operation !== "editorActionV1") {
          result.selectionBarrier = event.selectionBarrier;
          result.formatBarrier = event.formatBarrier;
        }"""

# A failed postcondition is only auditable if the markup it judged survives the
# trip.  The engine already puts the whole readback -- tags, restore flag and up
# to 2048 bytes of raw markup -- into the error payload, and the shared worker
# forwards a fixed five fields and drops it.  The frozen matrix promises the
# opposite ("carries the observed tags and the raw markup"), so this is the
# pipeline breaking a contract the engine keeps.
#
# Patched on the E2 copy rather than in sdk/sdk-worker.js: the shared file is
# what the frozen E1 profiles are built from, and E2 must diverge on its own
# copy only.
WORKER_ERROR_BEFORE = """          expectedRevision: event.expectedRevision,
          currentRevision: event.currentRevision,
        });"""

WORKER_ERROR_AFTER = """          expectedRevision: event.expectedRevision,
          currentRevision: event.currentRevision,
          formatBarrier: event.formatBarrier,
        });"""

# The drain result now carries which pump actually did anything; without this
# the attribution run cannot tell a working pump from a silent no-op.
WORKER_DRAIN_BEFORE = """          before: event.before,
          after: event.after,
          delta: event.delta,"""

WORKER_DRAIN_AFTER = """          before: event.before,
          after: event.after,
          delta: event.delta,
          pump: event.pump,"""


def write_e2_worker(source: Path, destination: Path) -> dict[str, object]:
    text = source.read_text(encoding="utf-8")
    edits = []
    for name, before, after in (
        ("discovery-scope-gate", WORKER_GATE_BEFORE, WORKER_GATE_AFTER),
        ("discovery-gate-message", WORKER_MESSAGE_BEFORE, WORKER_MESSAGE_AFTER),
        ("format-barrier-counters", WORKER_BARRIER_BEFORE, WORKER_BARRIER_AFTER),
        ("scheduler-drain-pump", WORKER_DRAIN_BEFORE, WORKER_DRAIN_AFTER),
        ("format-barrier-error-details", WORKER_ERROR_BEFORE, WORKER_ERROR_AFTER),
    ):
        occurrences = text.count(before)
        if occurrences != 1:
            raise SystemExit(
                f"E2 worker patch {name!r} matched {occurrences} times, expected exactly 1; "
                "sdk/sdk-worker.js changed and the patch must be re-derived"
            )
        text = text.replace(before, after)
        edits.append({"name": name, "occurrences": occurrences})
    destination.write_text(text, encoding="utf-8")
    return {
        "sourceSha256": sha256(source),
        "edits": edits,
        "sharedWorkerModified": False,
    }


def build_profile(source_manifest: Path, loader: Path, wasm: Path, worker: Path,
                  output: Path, profile_name: str = "e2-format-discovery",
                  scope: str = "e2-paragraph-format-discovery",
                  extra_capabilities: list[str] | None = None,
                  ui_language: str | None = None) -> dict[str, object]:
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loader, output / "probe.js")
    shutil.copy2(wasm, output / "probe.wasm")
    worker_patch = write_e2_worker(worker, output / "sdk-worker.js")
    manifest["profile"] = profile_name
    manifest["sdkVersion"] = f'{manifest["sdkVersion"]}+{profile_name}'
    manifest["artifactFiles"] = {
        **manifest["artifactFiles"],
        "probe.js": "./probe.js",
        "probe.wasm": "./probe.wasm",
    }
    capabilities = list(manifest.get("capabilities", []))
    capabilities.extend([
        "editor-discovery-closed-actions",
        "verified-selection-delete",
        "verified-format-state",
    ])
    capabilities.extend(extra_capabilities or [])
    manifest["capabilities"] = capabilities
    manifest["diagnostic"] = {
        "scope": scope,
        "contract": "closed-actions-v1-candidate-not-product-abi",
        "loaderSha256": sha256(output / "probe.js"),
        "wasmSha256": sha256(output / "probe.wasm"),
        "workerSha256": sha256(output / "sdk-worker.js"),
        "productionArtifactReplaced": False,
        "rawCallbackExposed": False,
        "arbitraryKeyCodeAccepted": False,
        "arbitraryUnoCommandAccepted": False,
        "automaticRetry": False,
        "selectionBarrier": "verified-single-writer-unit-v1",
        "formatBarrier": "verified-format-state-v1",
        # Finding 020: the result's own verdict fields contradict the document
        # for two of the list commands, so completion never consults them.
        "formatCompletionRequiresCommandResultAndState": True,
        "formatResultVerdictFieldsUsedForCompletion": False,
        "stateWordCountUsedForCompletion": False,
        "boundaryReadbackDeadlineMs": 250,
        "deadlineCanDeclareMutationSuccess": False,
        "boundaryRejectionRequiresFreshWorker": True,
        # Finding 021 candidate 1.  "lok-runloop-unipoll" means the engine has
        # no blocking command loop: commands dispatch from the unipoll poll
        # callback and the VCL scheduler is pumped by the upstream emscripten
        # main loop entered through the public LOK runLoop API.  No unit-test
        # pump is linked in that build.
        "engineLoop": ("lok-runloop-unipoll"
                       if profile_name.startswith("e2-mainloop")
                       else "blocking-command-loop"),
        # Finding 031.  null means the engine calls documentLoad with no
        # options, which is every profile but the locale measurement one.  The
        # value is compiled into the WASM, so recording it here is a claim the
        # evidence can be checked against rather than the thing that sets it.
        "uiLanguage": ui_language,
        "workerPatch": worker_patch,
    }
    write_json(output / "sdk-manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--loader", type=Path, required=True)
    parser.add_argument("--wasm", type=Path, required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-name", default="e2-format-discovery")
    parser.add_argument("--scope", default="e2-paragraph-format-discovery")
    parser.add_argument("--extra-capability", action="append", default=[])
    parser.add_argument("--ui-language", default=None)
    args = parser.parse_args()
    build_profile(args.source_manifest, args.loader, args.wasm, args.worker,
                  args.output, args.profile_name, args.scope,
                  args.extra_capability, args.ui_language)


if __name__ == "__main__":
    main()
