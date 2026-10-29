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

#ifdef OXSDK_E2_V25_FORMAT_PROOF
// Finding 172, SPEC-M3-ordered-commands section 23.  What makes an inline-format
// request true, given that core answers `success:false` when it honours the
// parameterised form (finding 059):
//   uno-success   the result itself says so;
//   on-time-item  this flush carries the state item and it equals the request;
//   state-noop    this flush carries NO item, the item is on the measured
//                 on-time list (core broadcasts a change in the command's own
//                 flush, 5/5), and the known state already equals the request:
//                 nothing changed because nothing had to.  Without this case a
//                 request for the current state -- clear-format's first press
//                 on plain text -- answers LOK_COMMAND_FAILED.
// Named limit L-noop-trusts-last-state-item: a stale cache plus a refused
// dispatch passes here, exactly as it did on v22.
bool orderedInlineFormatStateEquals(const std::string &unoCommand, bool requested) {
  if (unoCommand == ".uno:Bold")
    return gEditorState.boldKnown && gEditorState.bold == requested;
  if (unoCommand == ".uno:Italic")
    return gEditorState.italicKnown && gEditorState.italic == requested;
  if (unoCommand == ".uno:Underline")
    return gEditorState.underlineKnown && gEditorState.underline == requested;
  if (unoCommand == ".uno:Strikeout")
    return gEditorState.strikeoutKnown && gEditorState.strikeout == requested;
  return false;
}

const char *orderedInlineFormatWitness(const std::string &unoCommand, bool requested,
                                       const std::string &payload) {
  if (commandResultSucceeded(payload.c_str()))
    return "uno-success";
  for (const auto &read : probe::replystate::kReads) {
    if (unoCommand != read.unoCommand)
      continue;
    if (gOrderedProof.stateItems.count(read.stateKey))
      return orderedInlineFormatStateEquals(unoCommand, requested) ? "on-time-item" : nullptr;
    return orderedInlineFormatStateEquals(unoCommand, requested) ? "state-noop" : nullptr;
  }
  return nullptr;
}
#endif

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
#ifdef OXSDK_E2_V25_FORMAT_PROOF
    const char *witness = orderedInlineFormatWitness(unoCommand, option, payload);
    if (!witness) {
      emitSdkError(command.requestId, command.documentHandle, "editor-action",
                   "LOK_COMMAND_FAILED", "LibreOfficeKit rejected the fixed editor command");
      return;
    }
#else
    // 059 uses only an on-time item observed in this command's own flush.
    if (!commandResultSucceeded(payload.c_str()) &&
        !inlineFormatArgumentResolved(unoCommand, option)) {
      emitSdkError(command.requestId, command.documentHandle, "editor-action",
                   "LOK_COMMAND_FAILED", "LibreOfficeKit rejected the fixed editor command");
      return;
    }
#endif
    advanceRevision();
    std::ostringstream json;
    json << "{\"schemaVersion\":" << ProtocolSchemaVersion
         << ",\"type\":\"editor-action-completed\",\"requestId\":" << command.requestId
         << ",\"documentHandle\":" << command.documentHandle
         << ",\"beforeRevision\":" << beforeRevision << ",\"revision\":" << gState.revision
         << ",\"action\":\"" << jsonEscape(action.c_str())
         << "\",\"option\":" << (option ? "true" : "false")
         << ",\"changed\":true,\"completion\":\"uno-command-result\""
#ifdef OXSDK_E2_V25_FORMAT_PROOF
         << ",\"witness\":\"" << witness << "\""
#endif
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
