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
# Imported, not retyped: two copies of the closed action set would be free to
# drift, and the whole point of the combination profile is that its product half
# is the same contract the product ships.
from build_e1_b_profile import EDITOR_ACTIONS as E1_EDITOR_ACTIONS  # noqa: E402

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
# RE-DERIVED 2026-08-16.  The old anchor was
#     if (operation !== "editorActionV1")
#       result.selectionBarrier = event.selectionBarrier;
# and it stopped matching on 2026-08-15 (8879d71 and the commits around it),
# when the worker replaced the suffix comparison with an operation table and
# started forwarding a NAMED PROJECTION of the barrier to the product.  The
# builder failed loudly, exactly as designed -- but `test-e2-a-static` is what
# runs that check, and nobody ran it for a day, so what the loud failure
# actually bought was a diagnostic profile that could not be built and a static
# target that was red without anyone noticing.
#
# What the patch is for has not changed: a diagnostic profile needs the WHOLE
# barrier record -- crosstalkCount, earlyStateCount, the raw readback markup --
# and productFormatBarrier() drops all of it on purpose (those fields are not
# product promises).  So the patch now swaps the projection for the raw event
# instead of adding a forward that the product path already does.
WORKER_BARRIER_BEFORE = """        if (event.formatBarrier)
          result.formatBarrier = productFormatBarrier(event.formatBarrier);"""

WORKER_BARRIER_AFTER = """        if (event.formatBarrier)
          result.formatBarrier = event.formatBarrier;"""

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
# RE-DERIVED 2026-08-16, same cause as the counters patch above: the error path
# now forwards the named projection, which drops the raw readback markup this
# patch exists to preserve.  The swap keeps the diagnostic profile's promise
# ("carries the observed tags and the raw markup") without touching the product
# path, which keeps its projection.
WORKER_ERROR_BEFORE = """          formatBarrier: event.formatBarrier
            ? productFormatBarrier(event.formatBarrier) : undefined,"""

WORKER_ERROR_AFTER = """          formatBarrier: event.formatBarrier,"""

# The drain result now carries which pump actually did anything; without this
# the attribution run cannot tell a working pump from a silent no-op.
WORKER_DRAIN_BEFORE = """          before: event.before,
          after: event.after,
          delta: event.delta,"""

WORKER_DRAIN_AFTER = """          before: event.before,
          after: event.after,
          delta: event.delta,
          pump: event.pump,"""

# Finding 037 only, and only when --lok-trace is passed.
#
# The engine emits every LOK callback as a {"type":"lok"} event before it
# handles it (probe_engine.cpp onLokCallback), so the callback stream is
# already there; the shared worker forwards two ids as document-invalidated and
# six more only under debug, and drops the rest.  A barrier that never returns
# writes no evidence of its own, so this stream is the only record of how far
# the engine got before it stopped -- and it costs no rebuild, which means the
# run stays bound to the same artifact as the run it is explaining.
#
# Additive: the existing document-invalidated and lok-review paths are left
# exactly as they are, so a traced profile differs from an untraced one by what
# it reports and not by what it does.
WORKER_LOK_TRACE_BEFORE = """    case "lok":
      if (event.id === 0 || event.id === 1) {"""

WORKER_LOK_TRACE_AFTER = """    case "lok":
      if (debugEnabled)
        postEvent("diagnostic", { level: "lok-trace", detail: event });
      if (event.id === 0 || event.id === 1) {"""


def write_e2_worker(source: Path, destination: Path,
                    lok_trace: bool = False) -> dict[str, object]:
    text = source.read_text(encoding="utf-8")
    patches = [
        ("discovery-scope-gate", WORKER_GATE_BEFORE, WORKER_GATE_AFTER),
        ("discovery-gate-message", WORKER_MESSAGE_BEFORE, WORKER_MESSAGE_AFTER),
        ("format-barrier-counters", WORKER_BARRIER_BEFORE, WORKER_BARRIER_AFTER),
        ("scheduler-drain-pump", WORKER_DRAIN_BEFORE, WORKER_DRAIN_AFTER),
        ("format-barrier-error-details", WORKER_ERROR_BEFORE, WORKER_ERROR_AFTER),
    ]
    if lok_trace:
        patches.append(
            ("lok-callback-trace", WORKER_LOK_TRACE_BEFORE, WORKER_LOK_TRACE_AFTER))
    edits = []
    for name, before, after in patches:
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
        "lokCallbackTrace": lok_trace,
    }


def build_profile(source_manifest: Path, loader: Path, wasm: Path, worker: Path,
                  output: Path, profile_name: str = "e2-format-discovery",
                  scope: str = "e2-paragraph-format-discovery",
                  extra_capabilities: list[str] | None = None,
                  ui_language: str | None = None,
                  lok_trace: bool = False) -> dict[str, object]:
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(loader, output / "probe.js")
    shutil.copy2(wasm, output / "probe.wasm")
    worker_patch = write_e2_worker(worker, output / "sdk-worker.js", lok_trace)
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

    # Task #47.  Declaring narrow-editor-v1 is not enough to make the product
    # ABI reachable: sdk-worker.js gates it on capability AND
    # editorContract.version === 1 (sdk-worker.js:98-101), and this builder
    # never emitted an editorContract at all.  The first combination profile
    # therefore came out with the capability listed and every product method
    # refused at 0 ms with "editor v1 operations require the isolated narrow
    # editor profile" -- a failure that reads like a missing capability while
    # the capability is right there.
    #
    # Only emitted when the caller actually asked for that capability, so every
    # other diagnostic profile's manifest stays byte-identical.
    if "narrow-editor-v1" in (extra_capabilities or []):
        manifest["editorContract"] = {
            "version": 1,
            "abiVersion": 1,
            "actions": E1_EDITOR_ACTIONS,
            "textCommit": "document-sdk-insert-text",
            "undo": "document-sdk-undo",
            "state": "typed-editor-state-v1",
            "selectionBarrier": "verified-single-writer-unit-v1",
            "boundaryRejectionRequiresFreshWorker": True,
            "automaticRetry": False,
            "rawCallbackExposed": False,
            "arbitraryKeyCodeAccepted": False,
            "arbitraryUnoCommandAccepted": False,
            "diagnosticOperationsExposed": False,
            "loaderSha256": sha256(output / "probe.js"),
            "wasmSha256": sha256(output / "probe.wasm"),
            "workerSha256": sha256(output / "sdk-worker.js"),
        }
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
    parser.add_argument(
        "--lok-trace",
        action="store_true",
        help="forward every LOK callback as a diagnostic event (finding 037)",
    )
    args = parser.parse_args()
    build_profile(args.source_manifest, args.loader, args.wasm, args.worker,
                  args.output, args.profile_name, args.scope,
                  args.extra_capability, args.ui_language, args.lok_trace)


if __name__ == "__main__":
    main()
