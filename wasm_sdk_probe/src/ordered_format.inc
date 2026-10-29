// Included in probe_engine.cpp's anonymous namespace, diagnostic v23 only.
// All LOK calls finish in this command. The owned transaction is judged after
// the next poll flush. Callback rectangles never determine read or restore.
// L-format-read-identity-by-content: equal paragraph text is indistinguishable;
// unavailable/unusable accessibility fingerprints remain explicitly declined.

// Native restore-v2 FORMAT: 40/40, five rounds, FORMAT-RESTORE-HOLDS.
// RESET alone clears the mark but leaves SelectText's selection mode active.
// The measured Q sequence clears that mode at the same recorded point. Do not
// insert a read, event-loop yield, or callback wait between these three calls.
void restoreOrderedFormatPoint() {
  if (!gFormatBarrier.restorePointValid)
    return;
  const int x = gFormatBarrier.restorePoint.x;
  const int y = gFormatBarrier.restorePoint.y +
                gFormatBarrier.restorePoint.height / 2;
  gState.document->pClass->setTextSelection(
      gState.document, LOK_SETTEXTSELECTION_RESET, x, y);
  gState.document->pClass->setTextSelection(
      gState.document, LOK_SETTEXTSELECTION_START, x, y);
  gState.document->pClass->setTextSelection(
      gState.document, LOK_SETTEXTSELECTION_RESET, x, y);
}

void finishOrderedFormatReadback() {
  auto refuse = [](const char *shape, const char *message) {
    gFormatBarrier.failureShape = shape;
    failFormatBarrier(kFormatMutationOutcomeUnknown, message);
  };
  if (!gFormatBarrier.selectionTypeReadable) {
    refuse(gFormatBarrier.selectionType == LOK_SELTYPE_NONE
               ? "select-text-returned-none" : "selection-type-not-readable",
           "the synchronous selection read did not provide readable text; "
           "the format mutation outcome is unknown");
    return;
  }
  const auto &readback = gFormatBarrier.readback;
  if (!readback.parsed || readback.footnoteApparatus || readback.unknownTag ||
      readback.malformedNesting) {
    refuse(readback.footnoteApparatus ? "footnote-apparatus-readback"
           : readback.unknownTag ? "unknown-structural-tag"
           : readback.malformedNesting ? "malformed-readback-nesting"
                                      : "block-extraction-failed",
           "the format readback does not provide a supported structural proof");
    return;
  }
  if (gFormatBarrier.route == FormatBarrierRoute::RangeCross) {
    if (!gFormatBarrier.crossChecked || !gFormatBarrier.crossIdentityHeld) {
      refuse(!gFormatBarrier.crossChecked ? "block-extraction-failed"
             : gFormatBarrier.postBlockTexts.size() !=
                       gFormatBarrier.preBlockTexts.size()
                 ? "block-count-changed" : "block-text-mismatch",
             "the format readback does not identify the original selected blocks");
      return;
    }
  } else {
    if (readback.multiBlock) {
      refuse("multi-block-readback", "the readback covers more than one paragraph");
      return;
    }
    gFormatBarrier.paragraphIdentityChecked =
        gFormatBarrier.dispatchParagraphKnown &&
        gFormatBarrier.readbackParagraphKnown &&
        gFormatBarrier.dispatchParagraphUsable &&
        gFormatBarrier.readbackParagraphUsable;
    gFormatBarrier.paragraphIdentityDeclined =
        gFormatBarrier.paragraphIdentityChecked ? ""
        : (!gFormatBarrier.dispatchParagraphKnown ||
           !gFormatBarrier.readbackParagraphKnown)
            ? "a paragraph read did not succeed"
            : "the reported list prefix consumed the whole paragraph, so the "
              "fingerprint is the empty-string constant and identifies nothing "
              "(finding 074)";
    if (gFormatBarrier.paragraphIdentityChecked &&
        gFormatBarrier.dispatchParagraphFingerprint !=
            gFormatBarrier.readbackParagraphFingerprint) {
      refuse("readback-is-a-different-paragraph",
             "the readback identifies a different paragraph from the dispatch");
      return;
    }
  }
  if (!gFormatBarrier.restoreConfirmed) {
    refuse("selection-not-restored",
           "the synchronous read did not confirm NONE after restoring the caret");
    return;
  }
  const bool satisfied = gFormatBarrier.route == FormatBarrierRoute::RangeCross
                             ? gFormatBarrier.crossStateHeld
                             : formatBarrierReadbackSatisfied();
  if (!satisfied) {
    gFormatBarrier.failureShape = "postcondition-not-met";
    failFormatBarrier("EDITOR_FORMAT_POSTCONDITION_FAILED",
                      "the document does not show the state this action asked for");
    return;
  }
  completeFormatBarrier();
}

void deferOrderedFormatReply(FormatStateBarrier barrier, bool dispatched,
                             const char *refusalCode = nullptr,
                             const char *refusalMessage = nullptr) {
  setOrderedReply([barrier, dispatched, refusalCode, refusalMessage]() mutable {
    // Legacy serializers only: no LOK reads or stage transitions at poll.
    gFormatBarrier = barrier;
#ifdef OXSDK_E2_V25_FORMAT_PROOF
    // Finding 171: the record carries what this command already knows.
    gFormatBarrier.dispatchRecorded = true;
    gFormatBarrier.dispatched = dispatched;
#endif
    if (refusalCode) {
      failFormatBarrier(refusalCode, refusalMessage);
      return;
    }
    std::string payload;
    gFormatBarrier.resultSeen =
        dispatched && orderedUnoResult(barrier.command, payload);
    if (gFormatBarrier.resultSeen) {
      gFormatBarrier.resultSuccess = commandResultSucceeded(payload.c_str());
      const char *modified = jsonFieldValue(payload.c_str(), "wasModified");
      gFormatBarrier.resultModified =
          modified && std::strncmp(modified, "true", 4) == 0;
    }
    const bool selects = barrier.route != FormatBarrierRoute::RangeCross;
    gFormatBarrier.selectionResultSeen =
        selects && orderedUnoResult(kFormatBarrierSelectCommand, payload);
    if (!gFormatBarrier.resultSeen ||
        (selects && !gFormatBarrier.selectionResultSeen)) {
      gFormatBarrier.failureShape =
          std::string("proof-absent-at-poll:UNO_COMMAND_RESULT:") +
          (!gFormatBarrier.resultSeen ? barrier.command
                                     : kFormatBarrierSelectCommand);
      failFormatBarrier(kFormatMutationOutcomeUnknown,
                        "the matching UNO command result was absent at the first poll");
      return;
    }
    finishOrderedFormatReadback();
  });
}

void startOrderedFormatAction(const Command &command, std::uint32_t action,
                              const char *name) {
  FormatStateBarrier barrier;
  barrier.action = name;

  switch (action) {
  case OXSDK_EDITOR_SET_LIST_UNORDERED:
    barrier.target = FormatBarrierTarget::ListBullet;
    barrier.expected = true;
    barrier.command = ".uno:DefaultBullet";
    barrier.arguments = kListOnArguments;
    barrier.expectedListTag = "ul";
    break;
  case OXSDK_EDITOR_SET_LIST_ORDERED:
    barrier.target = FormatBarrierTarget::ListNumber;
    barrier.expected = true;
    barrier.command = ".uno:DefaultNumbering";
    barrier.arguments = kListOnArguments;
    barrier.expectedListTag = "ol";
    break;
  case OXSDK_EDITOR_SET_LIST_NONE:
    barrier.target = FormatBarrierTarget::ListNone;
    barrier.expected = false;
    // Dispatched bare on purpose: FN_NUM_BULLET_OFF forwards to
    // FN_NUM_BULLET_ON with On=false and then calls DelNumRules, so it is
    // already a setter.  Finding 030 measured it landing on "no list" three
    // presses running, from both a bulleted and a numbered start.
    barrier.command = ".uno:RemoveBullets";
    barrier.expectedListTag = "none";
    break;
  case OXSDK_EDITOR_SET_PARAGRAPH_HEADING:
  case OXSDK_EDITOR_SET_PARAGRAPH_BODY: {
    const bool heading = action == OXSDK_EDITOR_SET_PARAGRAPH_HEADING;
    barrier.target = FormatBarrierTarget::ParagraphStyle;
    // Finding 019: .uno:Heading1ParaStyle and .uno:TextBodyParaStyle are UI
    // aliases with no dispatchable slot, so E1-A's mapping posted names that do
    // nothing.  The real command is StyleApply with fixed arguments; the enum
    // stays closed because neither the name nor the arguments cross the ABI.
    barrier.command = ".uno:StyleApply";
    barrier.arguments = styleApplyArguments(heading);
    barrier.expectedStyles = styleCandidates(heading);
    // SPEC E2-A 2.8, narrowing 2: the serialiser writes <p> for both "Text
    // body" and the default paragraph style, so this half of the postcondition
    // reads "is it a heading" and not "is it Text body".  The closed enum
    // promises two states, which this answers; it does not promise the style
    // name, and must not be reported as if it did.
    barrier.expectedBlockTag = heading ? "h1" : "p";
    break;
  }
  default:
    setOrderedReply([command]() {
      emitCommandError(command, "editor-action", "EDITOR_ACTION_UNSUPPORTED",
                       "closed editor action is unsupported");
    });
    return;
  }

  barrier.requestId = command.requestId;
  barrier.documentHandle = gState.documentHandle;
  barrier.beforeRevision = gState.revision;

  // Routing happens BEFORE the dispatch, and a refusal here is the cleanest
  // outcome this barrier can produce: nothing was sent, so the document is
  // provably untouched.  Both shapes are pre-dispatch refusals and must not
  // carry MUTATION_OUTCOME_UNKNOWN -- that code sends the host into recovery,
  // and there is nothing to recover from.
  {
    std::string refusal;
    if (!routeFormatBarrier(barrier, action, refusal)) {
      barrier.failureShape = refusal;

      if (refusal == "gesture-not-permitted") {
        deferOrderedFormatReply(barrier, false,
            "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
            "this action is not offered for this kind of selection in this "
            "profile, so nothing was dispatched and the document is unchanged");
      } else if (refusal == "routing-selection-not-observed") {
        // Its own branch, and not folded into the readback message below: an
        // action refused because core has not reported a selection YET is not
        // an action refused because the selection holds an image.  Telling the
        // host the second when the first happened is how a caller learns to
        // work around the wrong thing.  Same typed code and same wording as
        // the inherited actions' gate, because it is the same refusal.
        deferOrderedFormatReply(barrier, false,
            "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
            "no selection has been reported yet, so this action cannot be "
            "classified; nothing was dispatched and the document is unchanged");
      } else {
        deferOrderedFormatReply(barrier, false,
            "EDITOR_FORMAT_SELECTION_NOT_READABLE",
            "this selection holds an image or another object, and reading it "
            "back would stop this document responding, so nothing was "
            "dispatched and the document is unchanged");
      }
      return;
    }
  }
  barrier.beforeSequence = gEditorState.sourceSequence;
  barrier.dispatchSequence = gEditorState.sourceSequence;
  // Captured before the dispatch, because the dispatch can move the caret and
  // the read is going to move it again.  A restore aimed at where the caret
  // ended up would put it back to the wrong place and still look like success.
  barrier.restorePoint = gEditorState.caret;
  barrier.restorePointValid = gEditorState.caret.available;
  // Same instant, same reason (SPEC E2-A 10.14 narrowing 7).  Recorded here and
  // nowhere later: every later moment describes a selection the barrier itself
  // made.
  barrier.dispatchSelectionCollapsed = gEditorState.selectionRectangles.empty();
  barrier.dispatchSelectionObserved = gEditorState.selectionObserved;
  barrier.dispatchSelectionRectangles = gEditorState.selectionRectangles.size();
  // Finding 046.  Asked for at the dispatch, because from the next stage onward
  // every paragraph the engine can see is one the barrier's own selection
  // reached.
  barrier.dispatchParagraphKnown = refreshCaretParagraph();
  barrier.dispatchParagraphFingerprint = gEditorState.a11yContentHash;
  barrier.dispatchParagraphUsable = gEditorState.a11yFingerprintUsable;
#ifdef OXSDK_E2_V25_FORMAT_PROOF
  // Finding 171.  The legacy path leaves `idle` here (AwaitingResult, set just
  // before postUnoCommand), and the worker's projection still derives
  // `dispatched` from that for engines that do not send the field.  Nothing
  // compiled under the v23 define reads `stage`, and no deadline is armed.
  barrier.stage = FormatBarrierStage::AwaitingResult;
#endif
  // v23 callback routing must bypass all legacy barrier observers. This
  // temporary global lets existing pure/read helpers share the transaction;
  // no transaction survives here between this command and its reply.
  gFormatBarrier = barrier;
  expectOrderedUno(barrier.command);
  gState.document->pClass->postUnoCommand(
      gState.document, barrier.command.c_str(),
      barrier.arguments.empty() ? nullptr : barrier.arguments.c_str(), true);
  if (barrier.route == FormatBarrierRoute::RangeCross) {
    // Preserve the caller's entire range and compare every block by content.
    checkFormatBarrierCrossParagraph();
  } else {
    restoreOrderedFormatPoint();
    expectOrderedUno(kFormatBarrierSelectCommand);
    gState.document->pClass->postUnoCommand(
        gState.document, kFormatBarrierSelectCommand, nullptr, true);
    const SelectionReadback selected = readSelection();
    gFormatBarrier.selectionType = selected.type;
    // Capture 046 identity at the selected paragraph, before 037 permits HTML.
    gFormatBarrier.readbackParagraphKnown = refreshCaretParagraph();
    gFormatBarrier.readbackParagraphFingerprint = gEditorState.a11yContentHash;
    gFormatBarrier.readbackParagraphUsable = gEditorState.a11yFingerprintUsable;
    gFormatBarrier.selectionTypeReadable = selected.type == LOK_SELTYPE_TEXT;
    if (gFormatBarrier.selectionTypeReadable) {
      char *html = gState.document->pClass->getTextSelection(
          gState.document, "text/html", nullptr);
      const std::string markup = html ? std::string(html) : std::string();
      std::free(html);
      gFormatBarrier.readbackBytes = markup.size();
      gFormatBarrier.readbackHtml = markup.substr(0, FormatReadbackEvidenceLimit);
      gFormatBarrier.readback = parseFormatReadback(markup);
    }
  }
  restoreOrderedFormatPoint();
  gFormatBarrier.restoreConfirmed =
      gFormatBarrier.restorePointValid && readSelection().type == LOK_SELTYPE_NONE;
  barrier = gFormatBarrier;
  gFormatBarrier = FormatStateBarrier{};
  deferOrderedFormatReply(std::move(barrier), true);
}
