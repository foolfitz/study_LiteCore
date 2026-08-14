#!/usr/bin/env python3
"""Build finding 037's JS-only main-thread proxy trace profile.

The profile is derived from e2-preguard-diagnostic without relinking WASM.
Its loader records both sides of Emscripten main-thread proxy calls and mailbox
activity.  Pthread-side records are forwarded to the runtime worker before a
synchronous proxy can park that pthread, so the trace remains readable after
the wedge.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
from pathlib import Path


PROJECT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT / "dist" / "profiles" / "e2-preguard-diagnostic"
OUTPUT = PROJECT / "dist" / "profiles" / "e2-proxy-trace"
EXPECTED_WASM_SHA256 = (
    "ee185b3d5972cac761acbcbc19cbafe916962788822e7cbae87bfe771d62a566"
)
TRACE_LIMIT = 20_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_once(text: str, before: str, after: str, label: str) -> str:
    count = text.count(before)
    if count != 1:
        raise SystemExit(
            f"proxy trace patch {label!r} matched {count} times, expected 1"
        )
    return text.replace(before, after)


LOADER_ANCHOR = (
    "PThread.currentProxiedOperationCallerThread=0;return rtn};"
    "var __emscripten_runtime_keepalive_clear"
)

LOADER_TRACE = r'''PThread.currentProxiedOperationCallerThread=0;return rtn};
var __proxyTraceLimit=20000;
var __proxyTrace=globalThis.__proxyTrace=Array.isArray(globalThis.__proxyTrace)?globalThis.__proxyTrace:[];
var __proxyTraceDropped=Number(globalThis.__proxyTraceDropped||0);
var __proxyTraceSequence=0;
var __proxyTraceContext=ENVIRONMENT_IS_PTHREAD?"pthread":ENVIRONMENT_IS_WORKER?"runtime-worker":"main";
var __proxyTraceThread=()=>{try{return typeof _pthread_self==="function"?Number(_pthread_self()):null}catch(error){return null}};
var __proxyTracePush=(record,forward=true)=>{var entry={t:performance.now(),timeOrigin:performance.timeOrigin,sequence:++__proxyTraceSequence,context:__proxyTraceContext,thread:__proxyTraceThread(),...record};__proxyTrace.push(entry);if(__proxyTrace.length>__proxyTraceLimit){var remove=__proxyTrace.length-__proxyTraceLimit;__proxyTrace.splice(0,remove);__proxyTraceDropped+=remove}globalThis.__proxyTraceDropped=__proxyTraceDropped;Module["__proxyTrace"]=__proxyTrace;Module["__proxyTraceDropped"]=__proxyTraceDropped;if(forward&&ENVIRONMENT_IS_PTHREAD){try{postMessage({cmd:"callHandler",handler:"__proxyTraceFromPthread",args:[entry]})}catch(error){}}return entry};
Module["__proxyTraceFromPthread"]=entry=>__proxyTracePush({...entry,forwardedT:performance.now(),forwardedTimeOrigin:performance.timeOrigin},false);
Module["__proxyTrace"]=__proxyTrace;
Module["__proxyTraceDropped"]=__proxyTraceDropped;
Module["__proxyTraceSnapshot"]=globalThis.__proxyTraceSnapshot=()=>({capturedAt:performance.now(),timeOrigin:performance.timeOrigin,limit:__proxyTraceLimit,dropped:__proxyTraceDropped,entries:__proxyTrace.slice()});
var __proxyTraceOriginalProxyToMainThread=proxyToMainThread;
proxyToMainThread=(funcIndex,emAsmAddr,sync,...callArgs)=>{var callId=++__proxyTraceSequence;__proxyTracePush({phase:"proxy-enter",callId,index:funcIndex,emAsmAddr,argCount:callArgs.length,sync:Boolean(sync)});var completed=false;try{var rtn=__proxyTraceOriginalProxyToMainThread(funcIndex,emAsmAddr,sync,...callArgs);completed=true;return rtn}finally{__proxyTracePush({phase:"proxy-exit",callId,index:funcIndex,emAsmAddr,argCount:callArgs.length,sync:Boolean(sync),completed})}};
var __proxyTraceOriginalMailboxAwait=__emscripten_thread_mailbox_await;
__emscripten_thread_mailbox_await=pthread_ptr=>{__proxyTracePush({phase:"mailbox-await-enter",pthreadPtr:Number(pthread_ptr)});var completed=false;try{var rtn=__proxyTraceOriginalMailboxAwait(pthread_ptr);completed=true;return rtn}finally{__proxyTracePush({phase:"mailbox-await-exit",pthreadPtr:Number(pthread_ptr),completed})}};
var __proxyTraceOriginalCheckMailbox=checkMailbox;
checkMailbox=()=>{__proxyTracePush({phase:"check-mailbox-enter"});var completed=false;try{var rtn=__proxyTraceOriginalCheckMailbox();completed=true;return rtn}finally{__proxyTracePush({phase:"check-mailbox-exit",completed})}};
var __proxyTraceOriginalReceive=__emscripten_receive_on_main_thread_js;
__emscripten_receive_on_main_thread_js=(funcIndex,emAsmAddr,callingThread,numCallArgs,args)=>{var callId=++__proxyTraceSequence;var argCount=numCallArgs/2;__proxyTracePush({phase:"receive-enter",callId,index:funcIndex,emAsmAddr,callingThread:Number(callingThread),argCount});var completed=false;try{var rtn=__proxyTraceOriginalReceive(funcIndex,emAsmAddr,callingThread,numCallArgs,args);completed=true;return rtn}finally{__proxyTracePush({phase:"receive-exit",callId,index:funcIndex,emAsmAddr,callingThread:Number(callingThread),argCount,completed})}};
var __emscripten_runtime_keepalive_clear'''


WORKER_SNAPSHOT_ANCHOR = "function handleCancel(message) {"
WORKER_SNAPSHOT_PATCH = r'''function proxyTraceSnapshot() {
  const snapshot = moduleInstance?.__proxyTraceSnapshot?.() || {
    capturedAt: performance.now(),
    timeOrigin: performance.timeOrigin,
    limit: 20000,
    dropped: Number(moduleInstance?.__proxyTraceDropped || 0),
    entries: Array.isArray(moduleInstance?.__proxyTrace)
      ? moduleInstance.__proxyTrace.slice()
      : [],
  };
  return {
    ...snapshot,
    forwardedBy: "sdk-worker",
    forwardedAt: performance.now(),
  };
}

self.__sdkProxyTraceSnapshot = proxyTraceSnapshot;

function handleCancel(message) {'''

WORKER_REQUEST_ANCHOR = '''  else if (message.kind === "cancel")
    handleCancel(message);
});'''
WORKER_REQUEST_PATCH = '''  else if (message.kind === "cancel")
    handleCancel(message);
  else if (message.kind === "proxy-trace-request")
    self.postMessage({
      protocolVersion: PROTOCOL_VERSION,
      kind: "proxy-trace",
      requestId: message.requestId ?? null,
      snapshot: proxyTraceSnapshot(),
    });
});'''


def write_wasm() -> str:
    source = SOURCE / "probe.wasm"
    destination = OUTPUT / "probe.wasm"
    source_hash = sha256(source)
    if source_hash != EXPECTED_WASM_SHA256:
        raise SystemExit(
            f"source probe.wasm SHA-256 mismatch: {source_hash}"
        )
    if destination.exists():
        destination.unlink()
    try:
        os.link(source, destination)
        method = "hardlink"
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.copy2(source, destination)
        method = "copy-cross-device"
    output_hash = sha256(destination)
    if output_hash != EXPECTED_WASM_SHA256:
        raise SystemExit(
            f"output probe.wasm SHA-256 mismatch after {method}: {output_hash}"
        )
    return method


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wasm_method = write_wasm()

    loader = (SOURCE / "probe.js").read_text(encoding="utf-8")
    loader = replace_once(
        loader, LOADER_ANCHOR, LOADER_TRACE,
        "proxy-mailbox-receive-wrappers",
    )
    (OUTPUT / "probe.js").write_text(loader, encoding="utf-8")

    worker = (SOURCE / "sdk-worker.js").read_text(encoding="utf-8")
    worker = replace_once(
        worker, WORKER_SNAPSHOT_ANCHOR, WORKER_SNAPSHOT_PATCH,
        "snapshot-export",
    )
    worker = replace_once(
        worker, WORKER_REQUEST_ANCHOR, WORKER_REQUEST_PATCH,
        "snapshot-request-forwarding",
    )
    (OUTPUT / "sdk-worker.js").write_text(worker, encoding="utf-8")

    manifest = json.loads(
        (SOURCE / "sdk-manifest.json").read_text(encoding="utf-8")
    )
    manifest["profile"] = "e2-proxy-trace"
    manifest["sdkVersion"] = f'{manifest["sdkVersion"]}+proxy-trace'
    diagnostic = manifest["diagnostic"]
    if diagnostic.get("wasmSha256") != EXPECTED_WASM_SHA256:
        raise SystemExit("source manifest does not name the expected preguard WASM")
    diagnostic["loaderSha256"] = sha256(OUTPUT / "probe.js")
    diagnostic["workerSha256"] = sha256(OUTPUT / "sdk-worker.js")
    diagnostic["proxyTrace"] = {
        "jsOnly": True,
        "limit": TRACE_LIMIT,
        "droppedCountRecorded": True,
        "pthreadIssueForwardedToRuntimeWorker": True,
        "phases": [
            "proxy-enter", "proxy-exit",
            "receive-enter", "receive-exit",
            "mailbox-await-enter", "mailbox-await-exit",
            "check-mailbox-enter", "check-mailbox-exit",
        ],
        "snapshotRequestKind": "proxy-trace-request",
    }
    (OUTPUT / "sdk-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Final identity check is deliberately after every write.
    output_wasm_hash = sha256(OUTPUT / "probe.wasm")
    if output_wasm_hash != EXPECTED_WASM_SHA256:
        raise SystemExit(f"final probe.wasm SHA-256 mismatch: {output_wasm_hash}")
    print(json.dumps({
        "output": str(OUTPUT),
        "wasmLinkMethod": wasm_method,
        "wasmSha256": output_wasm_hash,
        "loaderSha256": diagnostic["loaderSha256"],
        "workerSha256": diagnostic["workerSha256"],
        "traceLimit": TRACE_LIMIT,
    }, indent=2))


if __name__ == "__main__":
    main()
