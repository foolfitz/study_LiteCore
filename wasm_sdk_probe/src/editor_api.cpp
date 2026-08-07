#include "editor_api.h"

#include "probe_engine.hpp"

#include <emscripten/emscripten.h>

#include <cstdint>

namespace {
enum InternalEditorAction : std::uint32_t {
  InternalMoveCharacterLeft = 1,
  InternalMoveCharacterRight = 2,
  InternalDeleteBackward = 7,
  InternalDeleteForward = 8,
  InternalInsertParagraphBreak = 9,
  InternalInsertLineBreak = 10,
  InternalSetBold = 13,
  InternalSetItalic = 14,
  InternalSetUnderline = 20,
  InternalSetStrikethrough = 21,
};

// The engine's selection methods, of which the narrow ABI exposes exactly one.
// Mirrors oxsdk_editor_selection_method in editor_discovery_api.h; that header
// is the diagnostic ABI and is deliberately not included here, so the one value
// the product uses is named locally rather than pulling the diagnostic surface
// into the product translation unit.
enum InternalSelectionMethod : std::uint32_t {
  InternalSelectionTextHandles = 2,
};

bool validRequest(oxsdk_request_id requestId) { return requestId != 0; }

bool isMove(std::uint32_t action) {
  return action == OXSDK_EDITOR_V1_MOVE_CHARACTER_LEFT ||
         action == OXSDK_EDITOR_V1_MOVE_CHARACTER_RIGHT;
}

bool isFormat(std::uint32_t action) {
  return action == OXSDK_EDITOR_V1_SET_BOLD ||
         action == OXSDK_EDITOR_V1_SET_ITALIC ||
         action == OXSDK_EDITOR_V1_SET_UNDERLINE ||
         action == OXSDK_EDITOR_V1_SET_STRIKETHROUGH;
}

std::uint32_t internalAction(std::uint32_t action) {
  switch (action) {
  case OXSDK_EDITOR_V1_MOVE_CHARACTER_LEFT:
    return InternalMoveCharacterLeft;
  case OXSDK_EDITOR_V1_MOVE_CHARACTER_RIGHT:
    return InternalMoveCharacterRight;
  case OXSDK_EDITOR_V1_DELETE_BACKWARD:
    return InternalDeleteBackward;
  case OXSDK_EDITOR_V1_DELETE_FORWARD:
    return InternalDeleteForward;
  case OXSDK_EDITOR_V1_INSERT_PARAGRAPH_BREAK:
    return InternalInsertParagraphBreak;
  case OXSDK_EDITOR_V1_INSERT_LINE_BREAK:
    return InternalInsertLineBreak;
  case OXSDK_EDITOR_V1_SET_BOLD:
    return InternalSetBold;
  case OXSDK_EDITOR_V1_SET_ITALIC:
    return InternalSetItalic;
  case OXSDK_EDITOR_V1_SET_UNDERLINE:
    return InternalSetUnderline;
  case OXSDK_EDITOR_V1_SET_STRIKETHROUGH:
    return InternalSetStrikethrough;
  default:
    return 0;
  }
}

int32_t status(probe::SubmitStatus value) {
  return static_cast<std::int32_t>(value);
}

template <typename Function> int32_t safeStatus(Function &&function) noexcept {
  try {
    return status(function());
  } catch (...) {
    return OXSDK_STATUS_INTERNAL_ERROR;
  }
}
} // namespace

extern "C" EMSCRIPTEN_KEEPALIVE std::int32_t oxsdk_editor_action(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision, std::uint32_t action,
    std::uint32_t extendSelection, std::uint32_t enabled) {
  const std::uint32_t mapped = internalAction(action);
  if (!validRequest(requestId) || documentHandle == 0 || mapped == 0 ||
      extendSelection > 1 || enabled > 1 ||
      (!isMove(action) && extendSelection != 0) ||
      (!isFormat(action) && enabled != 0)) {
    return OXSDK_STATUS_INVALID_ARGUMENT;
  }
  return safeStatus([&] {
    return probe::editorAction(requestId, documentHandle, expectedRevision,
                               mapped, extendSelection != 0, enabled != 0);
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE std::int32_t oxsdk_editor_get_state(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::editorGetState(requestId, documentHandle); });
}

extern "C" EMSCRIPTEN_KEEPALIVE std::int32_t oxsdk_editor_select_range(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::int32_t startXTwips, std::int32_t startYTwips,
    std::int32_t endXTwips, std::int32_t endYTwips) {
  if (!validRequest(requestId) || documentHandle == 0 || startXTwips < 0 ||
      startYTwips < 0 || endXTwips < 0 || endYTwips < 0) {
    return OXSDK_STATUS_INVALID_ARGUMENT;
  }
  return safeStatus([&] {
    return probe::editorSelect(requestId, documentHandle,
                               InternalSelectionTextHandles, startXTwips,
                               startYTwips, endXTwips, endYTwips,
                               /*boundedReadback=*/true);
  });
}
