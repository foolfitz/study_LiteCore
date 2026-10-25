Reply in English. No tools. Review the fullnewkind9helper and worker below for concretebugs, not conditionalpossibilities; maximum250words. Context verified: accept pending.set({operation,payload}) BEFOREinvoke; everypoll prioritizespendingreply then drainsatmost1command, provedactual2browserN3; requireDocument validatesopenhandle beforecallinghelper; setOrderedReply slot never overwritten sincecommands waitpendingreply; baseeventhandler resolvesoverride byname atcalltime (actualVMtested). jsonEscape handles allASCIIcontrolbytes<32 includingtab,newline,CR,quotes,backslashes. LOKAPIreturnsNULterminated UTF8 text, malloc/free ownership. Protocol rejects malformedUTF8 bytecount instead of changingevidence. Reader separately requiresnonempty HTMLwithselectedIMG and exact fixture/COMPLEXprecondition; null/empty cannotmakegatePASS. Private diagnostic events intentionallypreserveactualHTML evidence; nopublicAPI/gesture widening. Frozenoldcandidateunchanged. Focus on concrete deviationsfromengine-thread literalcall, ownership, cachedpostpollreply, exactprofile+requestmatching. Ifnone, say no concretefinding; do notrepeat already resolvedconditionalclaims.

HELPER
// Private r2 diagnostic only; included under OXSDK_E2_V23_DIAGNOSTIC.
void emitOrderedHtml(const char *type, std::uint32_t requestId, const std::string &html) {
  std::ostringstream json;
  json << "{\"type\":\"" << type << "\",\"requestId\":" << requestId
       << ",\"html\":\"" << jsonEscape(html.c_str()) << "\",\"bytes\":" << html.size() << "}";
  emitJson(json.str());
}

void startOrderedHtmlRead(const Command &command) {
  emitOrderedControl(9, command.requestId);
  // Ruling 2026-10-26 / spec20: literal 040 transfer, engine dispatch only.
  // The reply captures owned HTML; it never calls LOK at the next poll.
  std::unique_ptr<char, decltype(&std::free)> text(
      gState.document->pClass->getTextSelection(gState.document, "text/html", nullptr), &std::free);
  const std::string html = text ? text.get() : "";
  emitOrderedHtml("v23-html-return", command.requestId, html);
  setOrderedReply([requestId = command.requestId, html] {
    emitOrderedHtml("v23-html-result", requestId, html);
  });
}

R2 TAIL

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
