Adversarial code review. Reply in English, maximum300words, no tools. Only concrete bugs in new private diagnostic kind9. Existing unipoll dispatch executes on engine thread; setOrderedReply queues a composer for the next poll, before any next command. requireDocument validates matching open document. JSON emit routes through worker handleCEvent. Baseworker accept stores pending{operation,payload}; complete deletespending and posts success; fail deletespending and posts typed error. BasehandleCEvent forwards unknown types to diagnostic events. New immutable successor e2-editor-v23-diag-r2 preserves ABI5/public037guard and original artifact; no arbitraryMIME/key/UNO input. kind9 must call literal currentselection getTextSelection(text/html) on engine dispatch, emit attributed callentry/return includingactualHTML, captureownedHTML for postpollresponse, freeallocations. Shared olddiagnostic code changes do not alter frozenoldbinary; oldtail stillrejects9. Focus commandordering, lifetime, event/responseidentity, protocol errors, deadlocks. Don't request unrelatedservices/timing/generalization.

void emitOrderedControl(int kind, std::uint32_t requestId) {
  std::ostringstream json;
  json << "{\"type\":\"v23-control\",\"kind\":" << kind
       << ",\"requestId\":" << requestId << "}";
  emitJson(json.str());
}

#include "ordered_diagnostic_html.inc"

void handleOrderedDiagnostic(const Command &command) {
  const int kind = command.values[0];
  if (kind == 1) {
    emitOrderedControl(kind, command.requestId);
    std::mutex mutex;
    std::condition_variable condition;
    std::unique_lock<std::mutex> lock(mutex);
    condition.wait(lock, [] { return false; });
    return;
  }
  if (kind == 2) {
    emitOrderedControl(kind, command.requestId);
    setOrderedReply([command] {
      emitOrderedMissingProof(command, "v23Diagnostic", "UNO_COMMAND_RESULT");
    });
    return;
  }
  if (!requireDocument(command, "v23Diagnostic"))
    return;
  if (kind == 4 && readSelection().type != LOK_SELTYPE_TEXT) {
    emitCommandError(command, "v23Diagnostic", "INVALID_ARGUMENT",
                     "the private range-Left control requires a TEXT selection");
    return;
  }
  if (kind == 9) {
    startOrderedHtmlRead(command);
    return;
  }
  emitOrderedControl(kind, command.requestId);
  EditorPendingOperation pending;
  pending.requestId = command.requestId;
  pending.documentHandle = command.documentHandle;
  pending.beforeRevision = gState.revision;
  pending.beforeSequence = gEditorState.sourceSequence;
  pending.requiredCallback = kind == 4 ? EditorCaretOrSelectionCallback : LOK_CALLBACK_TEXT_SELECTION;
  pending.name = kind == 6 ? "move-character-right" : kind == 7 ? "move-line-end"
                 : kind == 8 ? "move-line-home" : "move-character-left";
  int key = kind == 6 ? com::sun::star::awt::Key::RIGHT
            : kind == 7 ? com::sun::star::awt::Key::END
            : kind == 8 ? com::sun::star::awt::Key::HOME : com::sun::star::awt::Key::LEFT;
  if (kind != 4)
    key |= EditorShiftModifier;
  dispatchOrderedKey(key, pending);
}
extern "C" int oxsdk_v23_diagnostic(int kind, int requestId) {
  if (kind < 1 || kind > 9 || requestId <= 0)
    return static_cast<int>(SubmitStatus::InvalidArgument);
  if (!gStarted.load(std::memory_order_acquire))
    return static_cast<int>(SubmitStatus::NotStarted);
  if (kind == 3) {
    // Deliberately the sole off-engine-thread LOK entrance, for the 040
    // negative control. An isolated harness invokes it with a settled doc.
    LibreOfficeKitDocument *document = nullptr;
    {
      std::lock_guard<std::mutex> lock(gState.mutex);
      if (!gCallbackDocumentHandle.load(std::memory_order_acquire) ||
          gState.executingRequest || !gState.commands.empty() ||
          !gState.asynchronousRequests.empty())
        return static_cast<int>(SubmitStatus::InvalidArgument);
      document = gState.document;
    }
    if (!document)
      return static_cast<int>(SubmitStatus::InvalidArgument);
    emitOrderedControl(kind, static_cast<std::uint32_t>(requestId));
    char *text = document->pClass->getTextSelection(document, "text/html", nullptr);
    std::free(text);
    emitSdkError(requestId, gCallbackDocumentHandle.load(), "v23Diagnostic",
                 "DIAGNOSTIC_CONTROL_RETURNED", "JS-thread LOK negative control returned");
    return static_cast<int>(SubmitStatus::Ok);
  }
  Command command{kind == 1 ? CommandType::DiagnosticNeverReturn
                           : kind == 2 ? CommandType::DiagnosticMissingProof
                           : kind == 9 ? CommandType::DiagnosticHtml
                                       : CommandType::DiagnosticKey};
  command.sdk = true;
  command.requestId = static_cast<std::uint32_t>(requestId);
  command.documentHandle = gCallbackDocumentHandle.load(std::memory_order_acquire);
  command.values[0] = kind;
  return static_cast<int>(submit(std::move(command)));
}
WORKER TAIL

// Concatenated only into e2-editor-v23-diag-r2's worker. No public SDK method,
// action id or capability is added. The harness uses Engine._request so the
// existing page-side SDK timeout (30 s default) and best-effort cancel apply.
// Cancellation does not stop a stuck synchronous LOK call. After a timeout,
// session recovery/disposal must terminate this worker before another trial.
const v23ProductHandleRequest = handleRequest;
handleRequest = function handleV23DiagnosticRequest(request) {
  if (request.operation !== "v23Diagnostic")
    return v23ProductHandleRequest(request);
  if (!moduleInstance || activeManifest?.profile !== "e2-editor-v23-diag-r2"
      || activeManifest?.editorContract?.abiVersion !== 5) {
    postResponse(request.requestId, false, {
      code: "UNSUPPORTED_OPERATION",
      message: "private v23 diagnostic requires the initialized diagnostic profile",
    });
    return;
  }
  // SDK ids range over uint32. This private int C entrance intentionally
  // accepts only positive int32 ids; diagnostic trials use fresh engines.
  const kind = request.payload?.kind;
  if (![1, 2, 3, 4, 5, 6, 7, 8, 9].includes(kind) || !Number.isInteger(request.requestId)
      || request.requestId <= 0 || request.requestId > 2147483647) {
    postResponse(request.requestId, false, {
      code: "INVALID_ARGUMENT", message: "invalid private v23 diagnostic request",
    });
    return;
  }
  // 1: never-return; 2: missing-proof; 3: direct JS-thread LOK.
  // 4: range-Left; 5/6: Shift+Left/Right; 7/8: Shift+End/Home.
  // 9: engine-thread literal current-selection HTML transfer (040).
  // These closed controls/observers are private W-D inputs only.
  // The engine checks that kind 3 has an open document. It may never return.
  accept(request, () => callStatus("oxsdk_v23_diagnostic",
    ["number", "number"], [kind, request.requestId]));
};


// Preserve the base worker's error projection and pending cleanup. Only this
// derived diagnostic worker exposes the engine's additional proof-failure
// string; it is neither a format-barrier failure nor a merge-key failure.
const v23ProductHandleCEvent = handleCEvent;
const v23ProductPostResponse = postResponse;
let v23ErrorProjection = null;
handleCEvent = function handleV23DiagnosticEvent(rawEvent) {
  let event;
  try {
    event = JSON.parse(rawEvent);
  } catch (_) {
    return v23ProductHandleCEvent(rawEvent);
  }
  if (activeManifest?.profile === "e2-editor-v23-diag-r2"
      && activeManifest?.editorContract?.abiVersion === 5 && event?.type === "v23-html-result") {
    const requestId = Number(event.requestId);
    const request = pending.get(requestId);
    if (request?.operation !== "v23Diagnostic" || request.payload.kind !== 9)
      return v23ProductHandleCEvent(rawEvent);
    if (typeof event.html !== "string" || event.bytes !== new TextEncoder().encode(event.html).length) {
      fail(requestId, "WORKER_PROTOCOL_ERROR", "invalid private HTML result");
      return;
    }
    complete(requestId, {html: event.html, bytes: event.bytes});
    return;
  }
  const previous = v23ErrorProjection;
  v23ErrorProjection = activeManifest?.profile === "e2-editor-v23-diag-r2"
    && activeManifest?.editorContract?.abiVersion === 5 && event?.type === "error"
    && typeof event.failureShape === "string" && Number(event.requestId) > 0
    ? {requestId: Number(event.requestId), failureShape: event.failureShape} : null;
  try {
    return v23ProductHandleCEvent(rawEvent);
  } finally {
    v23ErrorProjection = previous;
  }
};
postResponse = function postV23DiagnosticResponse(requestId, ok, value, transfer = []) {
  const projection = v23ErrorProjection;
  if (!ok && projection?.requestId === requestId)
    value = {...value, failureShape: projection.failureShape};
  return v23ProductPostResponse(requestId, ok, value, transfer);
};
