# Adversarial review: v23 first-poll engine integration
Inspect only supplied source; no tools. Find concrete correctness/lifetime/order defects in this engine-thread unipoll patch. Keep response under500words. Corecalls are synchronous under candidateC, callbackflush precedes nextpoll. Allreplies must be composed at firstpostcommandpoll, raw callbacks onlyrecord state/proof (editor-state/lokeventsallowed). Pollonequeuedcommandmax, pendingreplyfirst, nonblocking, anyInput includesreply. Typedproofabsence mustrefuseatthatpoll; nooldtimerstaging. DiagnosticABI5currenthealdesscore; unitK1 safeTEXT path, separateDELETEQnative45passed beforecode; FORMAT40stillpending, don'tinferpass. This is source review, not link/readiness approval.


## ordered_engine_state.inc
```cpp
// Candidate C state: owned by the engine thread. No callback owns a reply.
struct OrderedUnoProof {
  bool seen = false;
  std::string payload;
  std::uint64_t sequence = 0;
};
struct OrderedCommandProof {
  std::map<std::string, OrderedUnoProof> uno;
  std::map<int, std::uint64_t> callbacks;
  std::unordered_set<std::string> stateItems;
  bool viewReady = false;
  int searchType = -1;
  std::string searchPayload;
  bool commentAdded = false;
  std::string commentPayload;
  bool missingReported = false;
};
OrderedCommandProof gOrderedProof;
Command gOrderedCommand{CommandType::EmitReady};
std::function<void()> gOrderedReply;
bool gOrderedDispatching = false;
bool gOrderedComposing = false;
void markAsynchronous(std::uint32_t requestId);
void emitJson(const std::string &json);

void setOrderedReply(std::function<void()> reply) {
  if (gOrderedReply)
    throw std::logic_error("one ordered command attempted to install two replies");
  gOrderedReply = std::move(reply);
  if (gOrderedCommand.requestId)
    markAsynchronous(gOrderedCommand.requestId);
}

void expectOrderedUno(const std::string &name) {
  // Inserting a second expectation must not erase an already observed proof.
  gOrderedProof.uno.emplace(name, OrderedUnoProof{});
}

void noteOrderedProofAbsent(const char *callback) {
  if (gOrderedProof.missingReported)
    return;
  gOrderedProof.missingReported = true;
#ifdef OXSDK_E2_V23_DIAGNOSTIC
  static std::uint64_t missing = 0;
  std::ostringstream json;
  json << "{\"type\":\"v23-proof-absent\",\"requestId\":"
       << gOrderedCommand.requestId << ",\"count\":" << ++missing
       << ",\"callback\":\"" << callback << "\"}";
  emitJson(json.str());
#else
  (void)callback;
#endif
}

bool orderedUnoResult(const std::string &name, std::string &payload) {
  const auto found = gOrderedProof.uno.find(name);
  if (found == gOrderedProof.uno.end() || !found->second.seen) {
    if (gOrderedComposing)
      noteOrderedProofAbsent("UNO_COMMAND_RESULT");
    return false;
  }
  payload = found->second.payload;
  return true;
}

```


## ordered_engine_poll.inc
```cpp
// Actual unipoll adapter. The pure runOnePoll helper supplies the same
// reply-first, one-command and nonblocking rules exercised by the unit tests.
struct OrderedPollEngine {
  probe::poll::Inputs pollInputs() {
    std::lock_guard<std::mutex> lock(gState.mutex);
    return {gState.commands.size(), static_cast<bool>(gOrderedReply)};
  }
  void recordPoll(const probe::poll::Inputs &in, probe::poll::Step step) {
#ifdef OXSDK_E2_V23_DIAGNOSTIC
    static std::uint64_t poll = 0;
    std::uint32_t requestId = 0;
    if (step == probe::poll::Step::SendReply)
      requestId = gOrderedCommand.requestId;
    else if (step == probe::poll::Step::DispatchOne) {
      std::lock_guard<std::mutex> lock(gState.mutex);
      requestId = gState.commands.front().requestId;
    }
    std::ostringstream json;
    json << "{\"type\":\"v23-poll\",\"poll\":" << ++poll
         << ",\"queued\":" << in.queued << ",\"drained\":"
         << (step == probe::poll::Step::DispatchOne ? 1 : 0)
         << ",\"replyPending\":" << (in.replyPending ? "true" : "false")
         << ",\"reply\":" << (step == probe::poll::Step::SendReply ? "true" : "false")
         << ",\"requestId\":" << requestId << "}";
    emitJson(json.str());
#else
    (void)in;
    (void)step;
#endif
  }
  void sendPendingReply() {
    auto reply = std::move(gOrderedReply);
    gOrderedReply = {};
    gOrderedComposing = true;
    try {
      reply();
    } catch (const std::exception &error) {
      emitSdkError(gOrderedCommand.requestId, gOrderedCommand.documentHandle,
                   "ordered-reply", "MUTATION_OUTCOME_UNKNOWN", error.what());
    } catch (...) {
      emitSdkError(gOrderedCommand.requestId, gOrderedCommand.documentHandle,
                   "ordered-reply", "MUTATION_OUTCOME_UNKNOWN", "reply composition failed");
    }
    gOrderedComposing = false;
    finishAsynchronous(gOrderedCommand.requestId);
    gEditorPending = EditorPendingOperation{};
    gOrderedProof = OrderedCommandProof{};
  }
  void dispatchOne() {
    Command command;
    bool cancelled = false;
    {
      std::lock_guard<std::mutex> lock(gState.mutex);
      command = std::move(gState.commands.front());
      gState.commands.pop_front();
      if (command.sdk) {
        gState.pendingRequests.erase(command.requestId);
        cancelled = gState.cancelledRequests.erase(command.requestId) != 0;
        if (!cancelled)
          gState.executingRequest = command.requestId;
      }
    }
    gOrderedCommand = command;
    gOrderedProof = OrderedCommandProof{};
    gOrderedDispatching = true;
    executeQueuedCommand(command, cancelled);
    gOrderedDispatching = false;
  }
};

int mainLoopPollCallbackImpl(void *, int) {
  static bool inOrderedPoll = false;
  OrderedPollEngine engine;
  return probe::poll::runOnePoll(engine, inOrderedPoll);
}

```


## ordered_engine_reply.inc
```cpp
// Reply composers run only at the first poll after dispatch. They never call
// LOK: dispatch reads are owned values, flush-dependent fields use live caches.
void emitOrderedMissingProof(const Command &command, const char *operation,
                             const char *callback, const char *code = "MUTATION_OUTCOME_UNKNOWN") {
  noteOrderedProofAbsent(callback);
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << command.documentHandle
       << ",\"revision\":" << gState.revision << ",\"operation\":\""
       << jsonEscape(operation) << "\",\"code\":\"" << code
       << "\",\"failureShape\":\"proof-absent-at-poll:" << callback
       << "\",\"message\":\"required proof was absent at the first post-command poll\"}";
  emitJson(json.str());
}

void composeOrderedEditorPending(EditorPendingOperation pending) {
  int matched = -1;
  for (int type : {LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR, LOK_CALLBACK_TEXT_SELECTION}) {
    const auto found = gOrderedProof.callbacks.find(type);
    if (found != gOrderedProof.callbacks.end() && found->second > pending.beforeSequence &&
        (pending.requiredCallback == type || pending.requiredCallback == EditorCaretOrSelectionCallback)) {
      matched = type;
      break;
    }
  }
  const char *completion = matched == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR
      ? "documented-callback-visible-cursor"
      : matched == LOK_CALLBACK_TEXT_SELECTION ? "documented-callback-text-selection"
      : pending.caret ? "verified-caret-readback"
      : pending.selection ? "verified-selection-readback" : "verified-move-readback";
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion << ",\"type\":\""
       << (pending.caret ? "editor-caret-placed" : pending.selection
           ? "editor-selection-completed" : "editor-action-completed")
       << "\",\"requestId\":" << pending.requestId
       << ",\"documentHandle\":" << pending.documentHandle
       << ",\"revision\":" << gState.revision;
  if (pending.selection)
    json << ",\"method\":\"" << jsonEscape(pending.name.c_str()) << "\"";
  else if (!pending.caret)
    json << ",\"beforeRevision\":" << pending.beforeRevision
         << ",\"action\":\"" << jsonEscape(pending.name.c_str())
         << "\",\"option\":" << (pending.option ? "true" : "false") << ",\"changed\":false";
  json << ",\"completion\":\"" << completion
       << "\",\"callbackSequenceBefore\":" << pending.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  gEditorPending = EditorPendingOperation{};
}

void composeOrderedUno(const Command &command, const std::string &operation,
                       const std::string &unoCommand, const std::string &action,
                       std::uint32_t beforeRevision, std::uint64_t beforeSequence,
                       bool option) {
  std::string payload;
  if (!orderedUnoResult(unoCommand, payload)) {
    emitOrderedMissingProof(command, operation.c_str(), "UNO_COMMAND_RESULT");
    return;
  }
  if (operation == "comment-added") {
    if (!gOrderedProof.commentAdded) {
      emitOrderedMissingProof(command, operation.c_str(), "COMMENT", "LOK_ERROR");
      return;
    }
    payload = gOrderedProof.commentPayload;
  }
  if (operation == "editor-action-completed") {
    // 059 uses only an on-time item observed in this command's own flush.
    if (!commandResultSucceeded(payload.c_str()) &&
        !inlineFormatArgumentResolved(unoCommand, option)) {
      emitSdkError(command.requestId, command.documentHandle, "editor-action",
                   "LOK_COMMAND_FAILED", "LibreOfficeKit rejected the fixed editor command");
      return;
    }
    advanceRevision();
    std::ostringstream json;
    json << "{\"schemaVersion\":" << ProtocolSchemaVersion
         << ",\"type\":\"editor-action-completed\",\"requestId\":" << command.requestId
         << ",\"documentHandle\":" << command.documentHandle
         << ",\"beforeRevision\":" << beforeRevision << ",\"revision\":" << gState.revision
         << ",\"action\":\"" << jsonEscape(action.c_str())
         << "\",\"option\":" << (option ? "true" : "false")
         << ",\"changed\":true,\"completion\":\"uno-command-result\""
         << ",\"callbackSequenceBefore\":" << beforeSequence
         << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence << ",\"state\":{";
    appendEditorState(json);
    json << "}}";
    emitJson(json.str());
    return;
  }
  // Undo/redo/track changes retain the existing void-command result policy.
  advanceRevision();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion << ",\"type\":\""
       << jsonEscape(operation.c_str()) << "\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << command.documentHandle
       << ",\"revision\":" << gState.revision << ",\"resultPayload\":\""
       << jsonEscape(payload.c_str()) << "\"}";
  emitJson(json.str());
}

```


## Callback implementation
```cpp
void onLokCallback(int type, const char *payload, void *) {
  const std::uint32_t documentHandle =
      gCallbackDocumentHandle.load(std::memory_order_acquire);
  const std::uint32_t revision =
      gCallbackRevision.load(std::memory_order_acquire);
  std::ostringstream json;
  json << "{\"type\":\"lok\",\"id\":" << type << ",\"payload\":\""
       << jsonEscape(payload) << "\",\"documentHandle\":" << documentHandle
       << ",\"revision\":" << revision << "}";
  emitJson(json.str());

#ifdef OXSDK_EDITOR_DISCOVERY
#if defined(OXSDK_MERGE_KEY_UNDO) && !defined(OXSDK_E2_V23_LINK_BATCH)
  feedMergeAttribution(type, payload);
#endif
  bool editorStateChanged = false;
  const char *editorSource = nullptr;
  switch (type) {
  case LOK_CALLBACK_INVALIDATE_TILES:
    editorStateChanged = true;
    editorSource = "invalidate-tiles";
    break;
  case LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR:
    editorStateChanged = parseEditorRectangle(payload, gEditorState.caret);
    editorSource = editorStateChanged ? "visible-cursor" : nullptr;
    break;
  case LOK_CALLBACK_TEXT_SELECTION:
    editorStateChanged = parseEditorSelectionRectangles(
        payload, gEditorState.selectionRectangles);
    if (editorStateChanged)
      gEditorState.selectionObserved = true;
    editorSource = editorStateChanged ? "selection-rectangles" : nullptr;
    break;
  case LOK_CALLBACK_TEXT_SELECTION_START:
    editorStateChanged =
        parseEditorRectangle(payload, gEditorState.selectionStart);
    editorSource = editorStateChanged ? "selection-start" : nullptr;
    break;
  case LOK_CALLBACK_TEXT_SELECTION_END:
    editorStateChanged = parseEditorRectangle(payload, gEditorState.selectionEnd);
    editorSource = editorStateChanged ? "selection-end" : nullptr;
    break;
  case LOK_CALLBACK_CURSOR_VISIBLE:
    if (payload && (std::strcmp(payload, "true") == 0 ||
                    std::strcmp(payload, "false") == 0)) {
      gEditorState.cursorVisible = std::strcmp(payload, "true") == 0;
      editorStateChanged = true;
      editorSource = "cursor-visible";
    }
    break;
  case LOK_CALLBACK_STATE_CHANGED:
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
    updateEditorSchedulerProbeState(payload);
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
    // Finding 021 attribution.  "No format state arrived" has two causes that
    // the parsed events alone cannot separate: core never sent one, or core
    // sent one this build failed to recognise.  Counting arrivals here -- the
    // count only, never the payload -- separates them without widening the
    // callback surface.
    ++gEditorState.stateChangedTotal;
#endif
    updateEditorFormatState(payload);
    break;
  case LOK_CALLBACK_A11Y_FOCUS_CHANGED: {
    // Only counted when the documented payload parses; a malformed payload
    // must not be recorded as an observed content change.
    EditorSemanticSnapshot snapshot;
    if (payload && parseEditorSemanticJson(std::string(payload), snapshot)) {
      gEditorState.a11yObserved = true;
      ++gEditorState.a11yChangeCount;
      gEditorState.a11yContentLength = snapshot.contentLength;
      gEditorState.a11yPosition = snapshot.position;
      gEditorState.a11yContentHash = snapshot.contentHash;
      gEditorState.a11yFingerprintUsable = snapshot.fingerprintUsable;
      gEditorState.a11yListPrefixLength = snapshot.listPrefixLength;
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
      gEditorState.a11yParagraphText = snapshot.content;
#endif
      editorStateChanged = true;
      editorSource = "a11y-paragraph-changed";
    } else {
      // Counted separately so that "no content change was reported" stays
      // distinguishable from "the callback arrived but could not be read".
      ++gEditorState.a11yUnparsedCount;
    }
    break;
  }
#ifdef OXSDK_E2_V20_LINK_BATCH
  case LOK_CALLBACK_DOCUMENT_SIZE_CHANGED:
    // SPEC-M3-link-batch 12.3: counted on every arrival, and the arrival
    // PUSHES editor-state by itself -- until this case the switch pushed
    // seven callback types and this was not one of them, so a page added by
    // typing announced nothing the page could re-read on.  The payload is
    // not parsed and not forwarded; the page re-reads `page-rectangles`.
    ++gEditorState.documentSizeChangedCount;
    editorStateChanged = true;
    editorSource = "document-size-changed";
    break;
#endif
  default:
    break;
  }
  if (editorStateChanged) {
    ++gEditorState.sourceSequence;
    if (type == LOK_CALLBACK_INVALIDATE_TILES)
      gEditorState.documentChangeSequence = gEditorState.sourceSequence;
    if (type == LOK_CALLBACK_A11Y_FOCUS_CHANGED)
      gEditorState.a11yLastSequence = gEditorState.sourceSequence;
#ifdef OXSDK_E2_FORMAT_BARRIER
    // Finding 021: the caret moved, so whatever paragraph format state is
    // cached now describes some *other* paragraph until a fresh payload
    // arrives.  Marking it here is what lets the precondition tell "known for
    // this paragraph" from "known for the previous one" -- without it, the
    // no-op check silently answers for the wrong paragraph.
    if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR ||
        type == LOK_CALLBACK_TEXT_SELECTION ||
        type == LOK_CALLBACK_TEXT_SELECTION_START ||
        type == LOK_CALLBACK_TEXT_SELECTION_END)
      gEditorState.formatStateStale = true;
#endif
    emitEditorStateEvent(editorSource);
#ifndef OXSDK_E2_V23_LINK_BATCH
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
    handleSelectionBarrierStateCallback(type);
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
    handleFormatBarrierStateCallback(type);
#endif
    completePendingEditorOperation(type);
#endif
  } else if (type >= LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR &&
             type <= LOK_CALLBACK_CURSOR_VISIBLE && editorSource == nullptr) {
    std::ostringstream parseError;
    parseError << "{\"schemaVersion\":" << ProtocolSchemaVersion
               << ",\"type\":\"editor-callback-parse-error\",\"requestId\":0"
               << ",\"documentHandle\":" << documentHandle
               << ",\"revision\":" << revision << ",\"callbackId\":"
               << type << "}";
    emitJson(parseError.str());
  }
#endif

#ifdef OXSDK_E2_V23_LINK_BATCH
  // Cache/evidence only. The pending command owns the first-poll composer.
  if (gOrderedDispatching || gOrderedReply) {
    gOrderedProof.callbacks[type] = gEditorState.sourceSequence;
    if (type == 70 && payload && std::strstr(payload, "afterCallbackRegistered invoked"))
      gOrderedProof.viewReady = true;
    if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
      for (auto &entry : gOrderedProof.uno) {
        if (commandResultMatches(payload, entry.first)) {
          entry.second = {true, payload ? payload : "", gEditorState.sourceSequence};
        }
      }
    }
    if (type == LOK_CALLBACK_SEARCH_RESULT_SELECTION || type == LOK_CALLBACK_SEARCH_NOT_FOUND) {
      gOrderedProof.searchType = type;
      gOrderedProof.searchPayload = payload ? payload : "";
    }
    if (type == LOK_CALLBACK_COMMENT && payload &&
        std::strstr(payload, "\"action\": \"Add\"")) {
      gOrderedProof.commentAdded = true;
      gOrderedProof.commentPayload = payload;
    }
  }
#else
  if (type == 70 && payload &&
      std::strstr(payload, "afterCallbackRegistered invoked")) {
    const std::uint32_t requestId =
        gOpenRequestId.exchange(0, std::memory_order_acq_rel);
    if (requestId != 0) {
      std::ostringstream ready;
      ready << "{\"schemaVersion\":" << ProtocolSchemaVersion
            << ",\"type\":\"view-ready\",\"requestId\":" << requestId
            << ",\"documentHandle\":" << documentHandle
            << ",\"revision\":" << revision << "}";
      emitJson(ready.str());
    }
  }

  if (type == LOK_CALLBACK_SEARCH_RESULT_SELECTION ||
      type == LOK_CALLBACK_SEARCH_NOT_FOUND) {
    const std::uint32_t requestId =
        gSearchRequestId.exchange(0, std::memory_order_acq_rel);
    if (requestId != 0) {
      const bool found = type == LOK_CALLBACK_SEARCH_RESULT_SELECTION;
#ifdef OXSDK_EDITOR_DISCOVERY
      // Search establishes a real Writer selection after the view has become
      // interactive.  Reattach here so the documented focused-paragraph
      // snapshot reflects that selection instead of an early empty focus.
#ifndef OXSDK_FINDING_016_SELECTION_BARRIER
      if (found)
        refreshEditorAccessibility();
#endif
#endif
      std::ostringstream result;
      result << "{\"schemaVersion\":" << ProtocolSchemaVersion
             << ",\"type\":\"search-result\",\"requestId\":" << requestId
             << ",\"documentHandle\":" << documentHandle
             << ",\"revision\":" << revision << ",\"found\":"
             << (found ? "true" : "false") << ",\"query\":\""
             << jsonEscape(gSearchQuery.c_str()) << "\",\"resultPayload\":\""
             << jsonEscape(payload) << "\"}";
      gSearchQuery.clear();
      emitJson(result.str());
      finishAsynchronous(requestId);
    }
  }

  if (type == LOK_CALLBACK_COMMENT &&
      gUnoOperation == "comment-added" && payload &&
      std::strstr(payload, "\"action\": \"Add\"") != nullptr) {
    const std::uint32_t requestId =
        gUnoRequestId.exchange(0, std::memory_order_acq_rel);
    if (requestId != 0) {
      gUnoOperation.clear();
      advanceRevision();
      std::ostringstream result;
      result << "{\"schemaVersion\":" << ProtocolSchemaVersion
             << ",\"type\":\"comment-added\",\"requestId\":" << requestId
             << ",\"documentHandle\":" << documentHandle
             << ",\"revision\":" << gState.revision
             << ",\"resultPayload\":\"" << jsonEscape(payload) << "\"}";
      emitJson(result.str());
      finishAsynchronous(requestId);
    }
  }

  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
#ifdef OXSDK_ODS_VIEWER
    notePartTextUnoResult(payload);
#endif
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
    if (handleSelectionBarrierUnoResult(payload))
      return;
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
    handleFormatBarrierUnoResult(payload);
#endif
    const std::uint32_t requestId =
        gUnoRequestId.load(std::memory_order_acquire);
    if (requestId != 0) {
#ifdef OXSDK_EDITOR_DISCOVERY
      if (gUnoOperation == "editor-action-completed") {
        gUnoRequestId.store(0, std::memory_order_release);
        gUnoOperation.clear();
        const std::string action = std::move(gEditorUnoAction);
        const std::string command = std::move(gEditorUnoCommand);
        gEditorUnoSemanticReadback = false;
        if (!commandResultMatches(payload, command)) {
          emitSdkError(requestId, documentHandle, "editor-action",
                       "LOK_RESULT_MISMATCH",
                       "fixed editor command returned an unexpected result");
          finishAsynchronous(requestId);
          return;
        }
        bool rejected = !commandResultSucceeded(payload);
#ifdef OXSDK_E2_FORMAT_BARRIER
        // Finding 059: for the four inline formats, `success` is not evidence
        // about the document.  Ask the document's own state instead, and only
        // fall back to reporting a failure when the state disagrees with what
        // was asked for.  Every other command keeps the old gate.
        if (rejected && inlineFormatArgumentResolved(command, gEditorUnoOption))
          rejected = false;
#endif
        if (rejected) {
          emitSdkError(requestId, documentHandle, "editor-action",
                       "LOK_COMMAND_FAILED",
                       "LibreOfficeKit rejected the fixed editor command");
          finishAsynchronous(requestId);
          return;
        }
        const bool manualObservation =
            gEditorUnoOption &&
            (action == "delete-backward" || action == "delete-forward");
        advanceRevision();
        std::ostringstream result;
        result << "{\"schemaVersion\":" << ProtocolSchemaVersion
               << ",\"type\":\"editor-action-completed\",\"requestId\":"
               << requestId << ",\"documentHandle\":" << documentHandle
               << ",\"beforeRevision\":" << gEditorUnoBeforeRevision
               << ",\"revision\":" << gState.revision << ",\"action\":\""
               << jsonEscape(action.c_str())
               << "\",\"option\":" << (gEditorUnoOption ? "true" : "false")
               << ",\"changed\":"
               << (manualObservation ? "null" : "true")
               << ",\"completion\":\""
               << (manualObservation
                       ? "uno-command-result-manual-observation"
                       : "uno-command-result")
               << "\"";
        if (manualObservation)
          result << ",\"manualVerificationRequired\":true";
        result
               << ",\"callbackSequenceBefore\":" << gEditorUnoBeforeSequence
               << ",\"callbackSequenceAfter\":"
               << gEditorState.sourceSequence << ",\"state\":{";
        appendEditorState(result);
        result << "}}";
        emitJson(result.str());
        finishAsynchronous(requestId);
        return;
      }
#endif
      if (gUnoOperation == "comment-added") {
        // InsertAnnotation enters comment edit mode. Commit it and wait for
        // LOK_CALLBACK_COMMENT Add before resolving the SDK operation.
        gState.document->pClass->postUnoCommand(gState.document, ".uno:Escape",
                                                nullptr, false);
        return;
      }
      gUnoRequestId.store(0, std::memory_order_release);
      const std::string operation = std::move(gUnoOperation);
      gUnoOperation.clear();
      // LOK reports success:false for several successful void commands.
      // Treat command-result as the completion barrier; semantic follow-up
      // queries verify undo and track-changes effects in the conformance flow.
      advanceRevision();
      std::ostringstream result;
      result << "{\"schemaVersion\":" << ProtocolSchemaVersion
             << ",\"type\":\"" << jsonEscape(operation.c_str())
             << "\",\"requestId\":" << requestId
             << ",\"documentHandle\":" << documentHandle
             << ",\"revision\":" << gState.revision
             << ",\"resultPayload\":\"" << jsonEscape(payload) << "\"}";
      emitJson(result.str());
      finishAsynchronous(requestId);
    }
  }
#endif
}

```
