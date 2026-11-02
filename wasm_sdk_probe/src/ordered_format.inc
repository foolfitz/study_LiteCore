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
#ifdef OXSDK_E2_V28_LAST_BLOCK
  // SPEC-M3-v28-last-line-fallback 4.1 item 8.  Before the NONE refusal below,
  // which is the first check today.  A fallback that also read NONE (the blank
  // document) falls through to it unchanged: same shape, same message.
  if (gFormatBarrier.fallbackRan &&
      gFormatBarrier.fallbackSelectionType != LOK_SELTYPE_NONE) {
    auto refuseFallback = [](const char *reason) {
      gFormatBarrier.fallbackRefusal = reason;
      gFormatBarrier.failureShape = "fallback-readback-refused";
      failFormatBarrier(kFormatMutationOutcomeUnknown,
                        "the fallback selection's readback does not provide a "
                        "supported structural proof; the format mutation outcome "
                        "is unknown");
    };
    // v28: the restore before the structural refusals
    if (!gFormatBarrier.restoreConfirmed) {
      // A refused fallback is review with the queue open: a selection the
      // restore did not clear must not survive into the user's next key.
      gFormatBarrier.failureShape = "selection-not-restored";
      failFormatBarrier(kFormatMutationOutcomeUnknown,
                        "the synchronous read did not confirm NONE after restoring the caret");
      return;
    }
    const FormatReadback &fallback = gFormatBarrier.fallbackReadback;
    if (!gFormatBarrier.fallbackReadable) {
      refuseFallback("selection-type-not-readable");
      return;
    }
    if (!fallback.parsed || fallback.footnoteApparatus || fallback.unknownTag ||
        fallback.malformedNesting) {
      refuseFallback(fallback.footnoteApparatus ? "footnote-apparatus-readback"
                     : fallback.unknownTag ? "unknown-structural-tag"
                     : fallback.malformedNesting ? "malformed-readback-nesting"
                                                 : "block-extraction-failed");
      return;
    }
    // One position back from an empty paragraph crosses exactly one paragraph
    // break: the previous paragraph's tail and the dispatch paragraph.
    if (gFormatBarrier.fallbackReadback.blockCount != 2) {
      refuseFallback("unexpected-block-count");
      return;
    }
    // Finding 046's identity read, as on the primary route (declined on an empty
    // paragraph: its fingerprint is the empty-string constant, finding 074).
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
    if (!formatBarrierFallbackReadbackSatisfied()) {
      gFormatBarrier.failureShape = "postcondition-not-met";
      failFormatBarrier("EDITOR_FORMAT_POSTCONDITION_FAILED",
                        "the document does not show the state this action asked for");
      return;
    }
    completeFormatBarrier();
    return;
  }
#endif
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
#ifdef OXSDK_E2_V27_FIRST_BLOCK
    // Finding 176 (SPEC-M3-v27-finding-176 4.1 item 2; fable ruling 3 Q1).  On
    // the collapsed route `.uno:SelectText` is FN_SELECT_PARA: it selects from
    // the start of the paragraph holding the cursor and, on an EMPTY paragraph
    // only, runs on to the end of the NEXT one (textsh1.cxx:1975, GoCurrPara
    // pam.cxx:1238) -- never upward.  So the first block IS the dispatch
    // paragraph, and the predicate below already reads only the first block:
    // judge it, in both directions, instead of refusing.  RangeSingle keeps
    // the refusal (not measured under this read).
    if (readback.multiBlock &&
        gFormatBarrier.route != FormatBarrierRoute::Collapsed) {
      refuse("multi-block-readback", "the readback covers more than one paragraph");
      return;
    }
#else
    if (readback.multiBlock) {
      refuse("multi-block-readback", "the readback covers more than one paragraph");
      return;
    }
#endif
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

#ifdef OXSDK_E2_V31_ALIGNMENT
// SPEC-P-demo-batch-3 append 2.  An alignment moves the text sideways under the
// caret, so a restore aimed at the rectangle from before the dispatch lands on
// another character: N2 measured 16 of 33 places wrong, and the next key typed
// there goes in the wrong place.  This read needs no coordinates.  It extends
// one character from the caret, reads, and moves back from the point, which
// drops the selection (finding 129) at the character it started on: 33 of 33.
// On a range the caller's selection is read where it stands and stays there, as
// in Writer.  One command, no read, yield or callback wait between the calls.
void readOrderedAlignCaret() {
  gFormatBarrier.alignCaretRead = true;
  expectOrderedUno(kFormatBarrierFallbackCommand);
  gState.document->pClass->postUnoCommand(
      gState.document, kFormatBarrierFallbackCommand, nullptr, true);
  SelectionReadback selected = readSelection();
  if (selected.type != LOK_SELTYPE_TEXT) {
    // The start of the document: there is nothing to step back over.
    gFormatBarrier.alignReadBack = false;
    expectOrderedUno(".uno:CharRightSel");
    gState.document->pClass->postUnoCommand(gState.document, ".uno:CharRightSel",
                                            nullptr, true);
    selected = readSelection();
  }
  gFormatBarrier.selectionType = selected.type;
  const bool readable = LOK_SELTYPE_TEXT == selected.type;
  gFormatBarrier.selectionTypeReadable = readable;
  if (!readable) {
    // Neither way: a document holding one empty paragraph.  Nothing was
    // selected, so there is nothing to move back from.
    gFormatBarrier.restoreConfirmed = selected.type == LOK_SELTYPE_NONE;
    return;
  }
  char *html = gState.document->pClass->getTextSelection(
      gState.document, "text/html", nullptr);
  const std::string markup = html ? std::string(html) : std::string();
  std::free(html);
  gFormatBarrier.readbackBytes = markup.size();
  gFormatBarrier.readbackHtml = markup.substr(0, FormatReadbackEvidenceLimit);
  gFormatBarrier.readback = parseFormatReadback(markup);
  const char *back = gFormatBarrier.alignReadBack ? ".uno:GoRight" : ".uno:GoLeft";
  expectOrderedUno(back);
  gState.document->pClass->postUnoCommand(gState.document, back, nullptr, true);
  gFormatBarrier.restoreConfirmed = readSelection().type == LOK_SELTYPE_NONE;
}

void finishOrderedAlignCaretRead() {
  auto refuse = [](const char *shape, const char *message) {
    gFormatBarrier.failureShape = shape;
    failFormatBarrier(kFormatMutationOutcomeUnknown, message);
  };
  if (!gFormatBarrier.restoreConfirmed) {
    refuse("selection-not-restored",
           "the synchronous read did not confirm NONE after moving back to the caret");
    return;
  }
  if (!gFormatBarrier.selectionTypeReadable) {
    // L-align-blank-document: a document of one empty paragraph has nothing to
    // select, so the answer rests on the undo stack being readable and the
    // command having answered; N2's blank arms saved the alignment.
    if (gFormatBarrier.resultSeen && gFormatBarrier.undoRead) {
      completeFormatBarrier();
      return;
    }
    refuse("select-text-returned-none",
           "the document has nothing to select and the undo stack could not be read");
    return;
  }
  const FormatReadback &readback = gFormatBarrier.readback;
  if (!readback.parsed || readback.footnoteApparatus || readback.unknownTag ||
      readback.malformedNesting) {
    refuse(readback.footnoteApparatus ? "footnote-apparatus-readback"
           : readback.unknownTag ? "unknown-structural-tag"
           : readback.malformedNesting ? "malformed-readback-nesting"
                                      : "block-extraction-failed",
           "the format readback does not provide a supported structural proof");
    return;
  }
  if (!formatBarrierAlignCaretReadSatisfied()) {
    gFormatBarrier.failureShape = "postcondition-not-met";
    failFormatBarrier("EDITOR_FORMAT_POSTCONDITION_FAILED",
                      "the document does not show the state this action asked for");
    return;
  }
  completeFormatBarrier();
}
#endif

#ifdef OXSDK_E2_V32_PARAGRAPH_READ
// SPEC-P-demo-batch-4 (finding 180).  Every paragraph action on all three routes:
// the document says what the caret or the selection covers, before and after, and
// nothing selects, moves or restores.  The reply only reads what the command found.
void finishOrderedParagraphRead() {
  auto refuse = [](const char *shape, const char *message) {
    gFormatBarrier.failureShape = shape;
    failFormatBarrier(kFormatMutationOutcomeUnknown, message);
  };
  if (!gFormatBarrier.paragraphReadAfter) {
    refuse("paragraph-read-failed",
           "the paragraphs could not be read after the dispatch; the format "
           "mutation outcome is unknown");
    return;
  }
  if (!gFormatBarrier.crossIdentityHeld) {
    refuse(gFormatBarrier.postBlockTexts.size() != gFormatBarrier.preBlockTexts.size()
               ? "block-count-changed" : "block-text-mismatch",
           "the paragraphs read after the dispatch are not the ones it was sent to");
    return;
  }
  if (!gFormatBarrier.crossStateHeld) {
    gFormatBarrier.failureShape = "postcondition-not-met";
    failFormatBarrier("EDITOR_FORMAT_POSTCONDITION_FAILED",
                      "the document does not show the state this action asked for");
    return;
  }
  completeFormatBarrier();
}

#endif
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
#ifdef OXSDK_E2_V32_PARAGRAPH_READ
    const bool selects = false;  // nothing the verdict rests on selected anything
#elif defined(OXSDK_E2_V31_ALIGNMENT)
    const bool selects = barrier.route != FormatBarrierRoute::RangeCross &&
                         !barrier.alignCaretRead;
#else
    const bool selects = barrier.route != FormatBarrierRoute::RangeCross;
#endif
    gFormatBarrier.selectionResultSeen =
        selects && orderedUnoResult(kFormatBarrierSelectCommand, payload);
#ifdef OXSDK_E2_V28_LAST_BLOCK
    // 4.1 item 7.  Recorded, never a verdict input: the command answers success
    // whether or not anything was selected.  Read from the proof map directly,
    // because its absence is not an event here.
    if (gFormatBarrier.fallbackRan) {
      const auto found = gOrderedProof.uno.find(kFormatBarrierFallbackCommand);
      gFormatBarrier.fallbackResultSeen =
          found != gOrderedProof.uno.end() && found->second.seen;
    }
#endif
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
#ifdef OXSDK_E2_V32_PARAGRAPH_READ
    if (gFormatBarrier.paragraphRead) {
      finishOrderedParagraphRead();
      return;
    }
#endif
#ifdef OXSDK_E2_V31_ALIGNMENT
    if (gFormatBarrier.alignCaretRead) {
      finishOrderedAlignCaretRead();
      return;
    }
#endif
    finishOrderedFormatReadback();
  });
}

#ifdef OXSDK_E2_V32_PARAGRAPH_READ
void setOrderedListTarget(FormatStateBarrier &barrier, const char *tag) {
  const bool off = !tag;
  barrier.target = off ? FormatBarrierTarget::ListNone
                   : tag[0] == 'u' ? FormatBarrierTarget::ListBullet
                                   : FormatBarrierTarget::ListNumber;
  barrier.expected = !off;
  barrier.expectedListTag = off ? "none" : tag;
  // The same three commands and arguments as the set-list actions below: finding
  // 030 measured them as setters, and a toggle here is only the choice between them.
  barrier.command = off ? ".uno:RemoveBullets"
                    : tag[0] == 'u' ? ".uno:DefaultBullet" : ".uno:DefaultNumbering";
  barrier.arguments = off ? "" : kListOnArguments;
}

void setOrderedStyleTarget(FormatStateBarrier &barrier, int level) {
  barrier.target = FormatBarrierTarget::ParagraphStyle;
  barrier.command = ".uno:StyleApply";
  barrier.arguments = level ? headingApplyArguments(level) : styleApplyArguments(false);
  barrier.expectedBlockTag = level ? "h" + std::to_string(level) : "p";
}

// Which way the press goes is the document's answer, read here and nowhere else.
void resolveOrderedToggle(FormatStateBarrier &barrier, std::uint32_t action,
                          const std::vector<WriterParagraphRead> &before) {
  if (action == OXSDK_EDITOR_TOGGLE_LIST_UNORDERED ||
      action == OXSDK_EDITOR_TOGGLE_LIST_ORDERED) {
    const char *tag = action == OXSDK_EDITOR_TOGGLE_LIST_UNORDERED ? "ul" : "ol";
    setOrderedListTarget(barrier, toggleTakesOff(before, tag, "") ? nullptr : tag);
    return;
  }
  const int level = static_cast<int>(action - OXSDK_EDITOR_TOGGLE_HEADING_1) + 1;
  setOrderedStyleTarget(barrier,
                        toggleTakesOff(before, "", "h" + std::to_string(level)) ? 0 : level);
}

void startOrderedParagraphRead(FormatStateBarrier barrier, std::uint32_t action) {
  barrier.paragraphRead = true;
  // `selectionObserved` for the reason routeFormatBarrier gives: before core has
  // reported a selection, "no rectangles" means nobody has said yet.
  if (!gEditorState.selectionObserved) {
    barrier.failureShape = "routing-selection-not-observed";
    deferOrderedFormatReply(barrier, false, "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
        "no selection has been reported yet, so this action cannot be "
        "classified; nothing was dispatched and the document is unchanged");
    return;
  }
  std::vector<WriterParagraphRead> before;
  if (!writerSelectionParagraphs(gState.document, before, barrier.paragraphReadReason)) {
    barrier.failureShape = "routing-selection-not-readable";
    deferOrderedFormatReply(barrier, false, "EDITOR_FORMAT_SELECTION_NOT_READABLE",
        "this selection holds something other than paragraphs, so nothing was "
        "dispatched and the document is unchanged");
    return;
  }
  barrier.route = gEditorState.selectionRectangles.empty() ? FormatBarrierRoute::Collapsed
                  : before.size() >= 2 ? FormatBarrierRoute::RangeCross
                                       : FormatBarrierRoute::RangeSingle;
  const std::uint32_t gesture =
      barrier.route == FormatBarrierRoute::Collapsed     ? kGestureCollapsed
      : barrier.route == FormatBarrierRoute::RangeSingle ? kGestureRangeSingle
                                                         : kGestureRangeCross;
  if (!editorGesturePermitted(action, gesture)) {
    barrier.failureShape = "gesture-not-permitted";
    deferOrderedFormatReply(barrier, false, "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
        "this action is not offered for this kind of selection in this "
        "profile, so nothing was dispatched and the document is unchanged");
    return;
  }
  if (action == OXSDK_EDITOR_TOGGLE_LIST_ORDERED && !toggleTakesOff(before, "ol", "") &&
      numberingHasNoEffect(before)) {
    barrier.failureShape = "numbering-on-heading";
    deferOrderedFormatReply(barrier, false, "EDITOR_FORMAT_NUMBERING_ON_HEADING",
        "a heading takes no numbering here, so nothing was dispatched and the "
        "document is unchanged");
    return;
  }
  if (action >= OXSDK_EDITOR_TOGGLE_HEADING_1 && action <= OXSDK_EDITOR_TOGGLE_LIST_ORDERED)
    resolveOrderedToggle(barrier, action, before);
  barrier.beforeSequence = gEditorState.sourceSequence;
  barrier.dispatchSequence = gEditorState.sourceSequence;
  barrier.dispatchSelectionCollapsed = gEditorState.selectionRectangles.empty();
  barrier.dispatchSelectionObserved = gEditorState.selectionObserved;
  barrier.dispatchSelectionRectangles = gEditorState.selectionRectangles.size();
  barrier.stage = FormatBarrierStage::AwaitingResult;
  std::string undoBefore;
  const bool undoBeforeRead = readMergeUndoPayload(undoBefore);
  gFormatBarrier = barrier;
  // A paragraph style on the leading part of one paragraph makes core build an
  // inline heading frame (SwDocShell::MakeInlineHeading) instead of styling the
  // paragraph.  These buttons style paragraphs, so the selection widens to the
  // paragraph first, and stays there.  N5 measured it.
  if (barrier.route == FormatBarrierRoute::RangeSingle &&
      barrier.target == FormatBarrierTarget::ParagraphStyle) {
    expectOrderedUno(kFormatBarrierSelectCommand);
    gState.document->pClass->postUnoCommand(
        gState.document, kFormatBarrierSelectCommand, nullptr, true);
    if (!writerSelectionParagraphs(gState.document, before,
                                   gFormatBarrier.paragraphReadReason) ||
        before.size() != 1) {
      barrier = gFormatBarrier;
      barrier.failureShape = "routing-selection-not-readable";
      gFormatBarrier = FormatStateBarrier{};
      deferOrderedFormatReply(barrier, false, "EDITOR_FORMAT_SELECTION_NOT_READABLE",
          "this selection holds something other than paragraphs, so nothing was "
          "dispatched and the document is unchanged");
      return;
    }
  }
  gFormatBarrier.preBlockCount = static_cast<std::uint32_t>(before.size());
  gFormatBarrier.preBlockCountObserved = true;
  gFormatBarrier.preBlockTexts.clear();
  for (const WriterParagraphRead &row : before)
    gFormatBarrier.preBlockTexts.push_back(row.text);
  expectOrderedUno(gFormatBarrier.command);
  gState.document->pClass->postUnoCommand(
      gState.document, gFormatBarrier.command.c_str(),
      gFormatBarrier.arguments.empty() ? nullptr : gFormatBarrier.arguments.c_str(), true);
  std::vector<WriterParagraphRead> after;
  gFormatBarrier.paragraphReadAfter =
      writerSelectionParagraphs(gState.document, after, gFormatBarrier.paragraphReadReason);
  gFormatBarrier.crossChecked = gFormatBarrier.paragraphReadAfter;
  gFormatBarrier.postBlockCount = static_cast<std::uint32_t>(after.size());
  gFormatBarrier.postBlockCountObserved = gFormatBarrier.paragraphReadAfter;
  for (const WriterParagraphRead &row : after)
    gFormatBarrier.postBlockTexts.push_back(row.text);
  gFormatBarrier.crossIdentityHeld =
      gFormatBarrier.postBlockTexts == gFormatBarrier.preBlockTexts;
  gFormatBarrier.crossStateHeld = everyParagraphMeets(
      after, gFormatBarrier.expectedListTag, gFormatBarrier.expectedBlockTag,
      gFormatBarrier.expectedAlign);
  // Nothing here moved the caret or the selection, so there is nothing to confirm.
  gFormatBarrier.restoreConfirmed = true;
  {
    std::string undoAfter;
    const bool undoAfterRead = readMergeUndoPayload(undoAfter);
    const probe::merge::UndoSummary summaryBefore = probe::merge::summarizeUndoPayload(undoBefore);
    const probe::merge::UndoSummary summaryAfter = probe::merge::summarizeUndoPayload(undoAfter);
    gFormatBarrier.undoAttempted = true;
    gFormatBarrier.undoRead =
        undoBeforeRead && undoAfterRead && summaryBefore.ok && summaryAfter.ok;
    if (gFormatBarrier.undoRead) {
      gFormatBarrier.undoChanged = undoBefore != undoAfter;
      gFormatBarrier.undoActionsBefore = summaryBefore.actions;
      gFormatBarrier.undoActionsAfter = summaryAfter.actions;
      gFormatBarrier.undoTop = summaryAfter.topComment;
    }
  }
  barrier = gFormatBarrier;
  gFormatBarrier = FormatStateBarrier{};
  deferOrderedFormatReply(std::move(barrier), true);
}

#endif
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
#ifdef OXSDK_E2_V31_ALIGNMENT
  // SPEC-P-demo-batch-3 3.2.  These four set, they do not toggle: the same
  // press twice leaves the same value (N1, caret-already-centred).  The
  // postcondition is the align attribute the HTML read carries on the block.
  case OXSDK_EDITOR_SET_ALIGN_LEFT:
  case OXSDK_EDITOR_SET_ALIGN_CENTER:
  case OXSDK_EDITOR_SET_ALIGN_RIGHT:
  case OXSDK_EDITOR_SET_ALIGN_JUSTIFY:
    barrier.target = FormatBarrierTarget::ParagraphAlign;
    barrier.command = action == OXSDK_EDITOR_SET_ALIGN_LEFT ? ".uno:LeftPara"
                      : action == OXSDK_EDITOR_SET_ALIGN_CENTER ? ".uno:CenterPara"
                      : action == OXSDK_EDITOR_SET_ALIGN_RIGHT ? ".uno:RightPara"
                                                               : ".uno:JustifyPara";
    barrier.expectedAlign = action == OXSDK_EDITOR_SET_ALIGN_LEFT ? "left"
                            : action == OXSDK_EDITOR_SET_ALIGN_CENTER ? "center"
                            : action == OXSDK_EDITOR_SET_ALIGN_RIGHT ? "right"
                                                                     : "justify";
    break;
#endif
#ifdef OXSDK_E2_V32_PARAGRAPH_READ
  // SPEC-P-demo-batch-4.  Set from the document in resolveOrderedToggle, below.
  case OXSDK_EDITOR_TOGGLE_HEADING_1:
  case OXSDK_EDITOR_TOGGLE_HEADING_2:
  case OXSDK_EDITOR_TOGGLE_HEADING_3:
  case OXSDK_EDITOR_TOGGLE_HEADING_4:
  case OXSDK_EDITOR_TOGGLE_LIST_UNORDERED:
  case OXSDK_EDITOR_TOGGLE_LIST_ORDERED:
    break;
#endif
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
#ifdef OXSDK_E2_V32_PARAGRAPH_READ
  startOrderedParagraphRead(std::move(barrier), action);
  return;
#endif

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
#ifdef OXSDK_E2_V31_ALIGNMENT
  // Append 2: a range of one paragraph is read like a range of several, from
  // the selection the caller made.  The route's other gift is that nothing
  // collapses it.
  const bool aligning = barrier.target == FormatBarrierTarget::ParagraphAlign;
  if (aligning && barrier.route == FormatBarrierRoute::RangeSingle)
    barrier.route = FormatBarrierRoute::RangeCross;
#endif
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
#ifdef OXSDK_E2_V27_FIRST_BLOCK
  // Finding 176 (4.1 item 4): recorded, never a verdict input.  Read here,
  // after routing (a pre-dispatch refusal never reads it), before the post.
  std::string undoBefore;
  const bool undoBeforeRead = readMergeUndoPayload(undoBefore);
#endif
  // v23 callback routing must bypass all legacy barrier observers. This
  // temporary global lets existing pure/read helpers share the transaction;
  // no transaction survives here between this command and its reply.
  gFormatBarrier = barrier;
  expectOrderedUno(barrier.command);
  gState.document->pClass->postUnoCommand(
      gState.document, barrier.command.c_str(),
      barrier.arguments.empty() ? nullptr : barrier.arguments.c_str(), true);
#ifdef OXSDK_E2_V31_ALIGNMENT
  if (aligning && barrier.route == FormatBarrierRoute::Collapsed) {
    readOrderedAlignCaret();
  } else
#endif
  if (barrier.route == FormatBarrierRoute::RangeCross) {
    // Preserve the caller's entire range and compare every block by content.
    checkFormatBarrierCrossParagraph();
  } else {
#ifdef OXSDK_E2_V27_FIRST_BLOCK
    // Finding 176 (4.1 item 1; fable ruling 3 Q2): on the collapsed route the
    // select runs from where the dispatch left the cursor -- the dispatch
    // paragraph -- rather than from a point captured before the action changed
    // that paragraph's geometry.  RangeSingle keeps the restore: it collapses
    // the caller's range first.
    if (barrier.route != FormatBarrierRoute::Collapsed)
      restoreOrderedFormatPoint();
#else
    restoreOrderedFormatPoint();
#endif
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
#ifdef OXSDK_E2_V28_LAST_BLOCK
    // SPEC-M3-v28-last-line-fallback 4.1 item 6.  `.uno:SelectText` selects
    // nothing on an empty paragraph with no next content node (finding 083's
    // path): select one position back, across the paragraph break, so that the
    // dispatch paragraph is the LAST block of the readback.  Collapsed only, and
    // only with a restore point -- without one the restore below is a no-op and
    // this selection would be left for the user's next key.  No read, yield or
    // callback wait between these calls and the restore.
    if (barrier.route == FormatBarrierRoute::Collapsed &&
        selected.type == LOK_SELTYPE_NONE && barrier.restorePointValid) {
      expectOrderedUno(kFormatBarrierFallbackCommand);
      gState.document->pClass->postUnoCommand(
          gState.document, kFormatBarrierFallbackCommand, nullptr, true);
      const SelectionReadback stepBack = readSelection();
      gFormatBarrier.fallbackSelectionType = stepBack.type;
      gFormatBarrier.fallbackReadable = stepBack.type == LOK_SELTYPE_TEXT;
      if (gFormatBarrier.fallbackReadable) {
        char *html = gState.document->pClass->getTextSelection(
            gState.document, "text/html", nullptr);
        const std::string markup = html ? std::string(html) : std::string();
        std::free(html);
        gFormatBarrier.fallbackReadbackBytes = markup.size();
        gFormatBarrier.fallbackReadbackHtml =
            markup.substr(0, FormatReadbackEvidenceLimit);
        gFormatBarrier.fallbackReadback = parseFormatReadback(markup);
      }
    }
    // Set from the read (the type starts at -1), as the group's last statement:
    // a group that ended in a bare `}` preprocessed identically to the line
    // before it, which the L reader's line alignment could not tell apart.
    gFormatBarrier.fallbackRan = gFormatBarrier.fallbackSelectionType >= 0;
#endif
  }
#ifdef OXSDK_E2_V31_ALIGNMENT
  if (aligning) {
    // The caret read confirmed its own return; the range stays selected.
    if (barrier.route != FormatBarrierRoute::Collapsed)
      gFormatBarrier.restoreConfirmed = readSelection().type == LOK_SELTYPE_TEXT;
  } else {
#endif
  restoreOrderedFormatPoint();
  gFormatBarrier.restoreConfirmed =
      gFormatBarrier.restorePointValid && readSelection().type == LOK_SELTYPE_NONE;
#ifdef OXSDK_E2_V31_ALIGNMENT
  }
#endif
#ifdef OXSDK_E2_V27_FIRST_BLOCK
  {
    std::string undoAfter;
    const bool undoAfterRead = readMergeUndoPayload(undoAfter);
    const probe::merge::UndoSummary before = probe::merge::summarizeUndoPayload(undoBefore);
    const probe::merge::UndoSummary after = probe::merge::summarizeUndoPayload(undoAfter);
    gFormatBarrier.undoAttempted = true;
    gFormatBarrier.undoRead = undoBeforeRead && undoAfterRead && before.ok && after.ok;
    if (gFormatBarrier.undoRead) {
      gFormatBarrier.undoChanged = undoBefore != undoAfter;
      gFormatBarrier.undoActionsBefore = before.actions;
      gFormatBarrier.undoActionsAfter = after.actions;
      gFormatBarrier.undoTop = after.topComment;
    }
  }
#endif
  barrier = gFormatBarrier;
  gFormatBarrier = FormatStateBarrier{};
  deferOrderedFormatReply(std::move(barrier), true);
}
