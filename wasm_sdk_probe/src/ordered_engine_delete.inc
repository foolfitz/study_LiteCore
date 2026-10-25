// Headless candidate C: classify K1 at return; no stage, deadline or waiter.
// DELETE-Q-HOLDS (native restore-v2/delete/reader-result-01.json, 45 cells,
// N=5) authorizes ONLY the separator restore below. FORMAT has its own gate.
void emitOrderedDeleteError(const SelectionBarrierTransaction &transaction,
                            const char *code, const std::string &message,
                            const char *shape) {
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << transaction.requestId
       << ",\"documentHandle\":" << transaction.documentHandle
       << ",\"revision\":" << gState.revision
       << ",\"operation\":\"editor-action\",\"code\":\"" << code
       << "\",\"message\":\"" << jsonEscape(message.c_str())
       << "\",\"failureShape\":\"" << jsonEscape(shape) << "\"";
  appendCaretBefore(json, transaction);
  json << "}";
  emitJson(json.str());
}

void composeOrderedDelete(SelectionBarrierTransaction transaction,
                          const char *completion, bool changed,
                          const probe::merge::KeyJudgement &judgement = {}) {
  if (changed)
    advanceRevision();
  const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
      std::chrono::steady_clock::now() - transaction.startedAt).count();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-action-completed\",\"requestId\":" << transaction.requestId
       << ",\"documentHandle\":" << transaction.documentHandle
       << ",\"beforeRevision\":" << transaction.beforeRevision
       << ",\"revision\":" << gState.revision << ",\"action\":\""
       << jsonEscape(transaction.action.c_str()) << "\",\"option\":false,\"changed\":"
       << (changed ? "true" : "false") << ",\"completion\":\"" << completion
       << "\",\"callbackSequenceBefore\":" << transaction.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence;
  if (!changed) {
    json << ",\"boundaryNoop\":{\"waitedMs\":" << elapsed << "}";
  } else if (transaction.mergeKey) {
    const auto keyElapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - transaction.keyPostedAt).count();
    json << ",\"keyUndo\":{\"comment\":\"" << jsonEscape(judgement.after.topComment.c_str())
         << "\",\"actionsBefore\":" << judgement.before.actions
         << ",\"actionsAfter\":" << judgement.after.actions
         << ",\"restorePresses\":0,\"keyToUndoMs\":" << keyElapsed << ",\"codePoints\":[";
    for (std::size_t i = 0; i < transaction.selectedCodePoints.size(); ++i) {
      if (i) json << ',';
      json << transaction.selectedCodePoints[i];
    }
    json << "]}";
  } else {
    const auto uno = gOrderedProof.uno.find(transaction.command);
    const auto collapse = gOrderedProof.callbacks.find(LOK_CALLBACK_TEXT_SELECTION);
    const auto ackSequence = uno == gOrderedProof.uno.end() ? 0 : uno->second.sequence;
    const auto collapseSequence = collapse == gOrderedProof.callbacks.end() ? 0 : collapse->second;
    json << ",\"selectionBarrier\":{\"selectedText\":\""
         << jsonEscape(transaction.selectedText.c_str()) << "\",\"utf8Bytes\":"
         << transaction.selectedText.size() << ",\"transactionSerial\":" << transaction.transactionSerial
         << ",\"codePoints\":[";
    for (std::size_t i = 0; i < transaction.selectedCodePoints.size(); ++i) {
      if (i) json << ',';
      json << transaction.selectedCodePoints[i];
    }
    json << "],\"preselectionSequence\":" << transaction.preselectionSequence
         << ",\"dispatchSequence\":" << transaction.dispatchSequence
         << ",\"collapseSequence\":" << collapseSequence
         << ",\"acknowledgementSequence\":" << ackSequence
         << ",\"acknowledgementBeforeCollapse\":" << (ackSequence < collapseSequence ? "true" : "false") << "}";
  }
  json << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
}

void startOrderedCaretDelete(const Command &command, const char *action,
                             const char *unoCommand, bool backward) {
  const SelectionReadback initial = readSelection();
  if (initial.type != LOK_SELTYPE_NONE || initial.textMissing ||
      !gEditorState.selectionObserved || !gEditorState.selectionRectangles.empty()) {
    emitCommandError(command, "editor-action", "EDITOR_STATE_UNAVAILABLE",
                     "selection delete requires a callback-confirmed collapsed caret");
    return;
  }
  SelectionBarrierTransaction transaction;
  transaction.requestId = command.requestId;
  transaction.documentHandle = command.documentHandle;
  transaction.beforeRevision = gState.revision;
  transaction.beforeSequence = gEditorState.sourceSequence;
  transaction.transactionSerial = gNextSelectionBarrierSerial++;
  transaction.action = action;
  transaction.command = unoCommand;
  transaction.backward = backward;
  transaction.caretBefore = gEditorState.caret;
  transaction.caretBeforeSequence = gEditorState.sourceSequence;
  transaction.pStartRead = readMergeUndoPayload(transaction.pStart);
  transaction.startedAt = std::chrono::steady_clock::now();
  const int key = (backward ? com::sun::star::awt::Key::LEFT : com::sun::star::awt::Key::RIGHT)
                   | EditorShiftModifier;
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYINPUT, 0, key);
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYUP, 0, key);
  const SelectionReadback selected = readSelection();
  transaction.selectedText = selected.text;
  const bool decoded = decodeUtf8(selected.text, transaction.selectedCodePoints);
  const auto route = probe::ordereddelete::routeK1(selected.type, selected.textMissing,
      selected.text.size(), decoded, transaction.selectedCodePoints);
  if (route == probe::ordereddelete::Route::BoundaryNoop) {
    setOrderedReply([transaction] { composeOrderedDelete(transaction, "verified-boundary-noop", false); });
    return;
  }
  if (route == probe::ordereddelete::Route::Unsupported) {
    setOrderedReply([transaction] {
      emitOrderedDeleteError(transaction, "EDITOR_BOUNDARY_UNSUPPORTED",
                             "K1 did not select a supported text unit", "k1-unsupported");
    });
    return;
  }
  if (route == probe::ordereddelete::Route::DeleteUnit) {
    transaction.preselectionSequence = gEditorState.sourceSequence;
    transaction.dispatchSequence = gEditorState.sourceSequence;
    expectOrderedUno(transaction.command);
    gState.document->pClass->postUnoCommand(gState.document, unoCommand, nullptr, true);
    const SelectionReadback after = readSelection();
    const bool collapsed = after.type == LOK_SELTYPE_NONE && !after.textMissing;
    setOrderedReply([transaction, collapsed] {
      std::string payload;
      if (!orderedUnoResult(transaction.command, payload)) {
        emitOrderedDeleteError(transaction, "MUTATION_OUTCOME_UNKNOWN",
            "delete proof absent at first poll", "proof-absent-at-poll:UNO_COMMAND_RESULT");
      } else if (!commandResultSucceeded(payload.c_str())) {
        emitOrderedDeleteError(transaction, "LOK_COMMAND_FAILED", "fixed delete command failed", "delete-rejected");
      } else if (!collapsed) {
        emitOrderedDeleteError(transaction, "MUTATION_OUTCOME_UNKNOWN",
            "delete returned without a collapsed selection", "selection-not-collapsed");
      } else {
        composeOrderedDelete(transaction, "verified-selection-delete", true);
      }
    });
    return;
  }
  // Only after DELETE-Q-HOLDS. Three calls at the same recorded point, with
  // no read, pump or wait between them; the old single RESET remains rejected.
  if (!transaction.caretBefore.available) {
    setOrderedReply([transaction] {
      emitOrderedDeleteError(transaction, "MUTATION_OUTCOME_UNKNOWN", "no recorded caret for restore", "restore-point-absent");
    });
    return;
  }
  const int x = transaction.caretBefore.x;
  const int y = transaction.caretBefore.y + transaction.caretBefore.height / 2;
  gState.document->pClass->setTextSelection(gState.document, LOK_SETTEXTSELECTION_RESET, x, y);
  gState.document->pClass->setTextSelection(gState.document, LOK_SETTEXTSELECTION_START, x, y);
  gState.document->pClass->setTextSelection(gState.document, LOK_SETTEXTSELECTION_RESET, x, y);
  if (readSelection().type != LOK_SELTYPE_NONE) {
    setOrderedReply([transaction] {
      emitOrderedDeleteError(transaction, "MUTATION_OUTCOME_UNKNOWN", "Q did not restore a collapsed caret", "restore");
    });
    return;
  }
  const bool p0Read = readMergeUndoPayload(transaction.p0);
  const char *refusal = probe::merge::judgeBeforeKey(transaction.pStartRead, transaction.pStart, p0Read, transaction.p0);
  if (refusal) {
    setOrderedReply([transaction, refusal] {
      emitOrderedDeleteError(transaction, "MUTATION_OUTCOME_UNKNOWN", "restore undo proof failed", refusal);
    });
    return;
  }
  transaction.mergeKey = true;
  transaction.keyPostedAt = std::chrono::steady_clock::now();
  const int userKey = backward ? com::sun::star::awt::Key::BACKSPACE : com::sun::star::awt::Key::DELETE;
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYINPUT, 0, userKey);
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYUP, 0, userKey);
  std::string after;
  const bool read = readMergeUndoPayload(after);
  const auto judgement = probe::merge::judgeAfterKey(transaction.p0, read, after, false);
  setOrderedReply([transaction, judgement] {
    if (judgement.verdict == probe::merge::KeyVerdict::Verified)
      composeOrderedDelete(transaction, "verified-key-undo", true, judgement);
    else if (judgement.verdict == probe::merge::KeyVerdict::Pending)
      composeOrderedDelete(transaction, "verified-boundary-noop", false);
    else
      emitOrderedDeleteError(transaction, "MUTATION_OUTCOME_UNKNOWN", "key undo proof failed", judgement.stage);
  });
}
