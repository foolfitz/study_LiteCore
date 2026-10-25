
// Concatenated only into e2-editor-v23-diag's worker. No public SDK method,
// action id or capability is added. The harness uses Engine._request so the
// existing page-side SDK timeout (30 s default) and best-effort cancel apply.
// Cancellation does not stop a stuck synchronous LOK call. After a timeout,
// session recovery/disposal must terminate this worker before another trial.
const v23ProductHandleRequest = handleRequest;
handleRequest = function handleV23DiagnosticRequest(request) {
  if (request.operation !== "v23Diagnostic")
    return v23ProductHandleRequest(request);
  if (!moduleInstance || activeManifest?.profile !== "e2-editor-v23-diag"
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
  if (![1, 2, 3].includes(kind) || !Number.isInteger(request.requestId)
      || request.requestId <= 0 || request.requestId > 2147483647) {
    postResponse(request.requestId, false, {
      code: "INVALID_ARGUMENT", message: "invalid private v23 diagnostic request",
    });
    return;
  }
  // 1: queued never-return; 2: queued missing-proof; 3: direct JS-thread LOK.
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
  const previous = v23ErrorProjection;
  v23ErrorProjection = activeManifest?.profile === "e2-editor-v23-diag"
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
