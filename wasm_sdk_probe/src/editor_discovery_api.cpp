#include "editor_discovery_api.h"
#include "probe_engine.hpp"

#include <emscripten/emscripten.h>

#include <cstdint>

namespace {
bool validRequest(oxsdk_request_id requestId) { return requestId != 0; }

bool validAction(std::uint32_t action) {
  return action >= OXSDK_EDITOR_MOVE_CHARACTER_LEFT &&
         action <= OXSDK_EDITOR_SET_LIST_ORDERED;
}

bool validSelectionMethod(std::uint32_t method) {
  return method >= OXSDK_EDITOR_SELECTION_MOUSE_DRAG &&
         method <= OXSDK_EDITOR_SELECTION_RESET;
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

extern "C" EMSCRIPTEN_KEEPALIVE std::int32_t oxsdk_editor_discovery_action(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision, std::uint32_t action,
    std::uint32_t extendSelection, std::uint32_t option) {
  if (!validRequest(requestId) || documentHandle == 0 || !validAction(action) ||
      extendSelection > 1 || option > 1) {
    return OXSDK_STATUS_INVALID_ARGUMENT;
  }
  return safeStatus([&] {
    return probe::editorAction(requestId, documentHandle, expectedRevision,
                               action, extendSelection != 0, option != 0);
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE std::int32_t oxsdk_editor_discovery_select(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t method, std::int32_t startXTwips,
    std::int32_t startYTwips, std::int32_t endXTwips,
    std::int32_t endYTwips) {
  if (!validRequest(requestId) || documentHandle == 0 ||
      !validSelectionMethod(method) || startXTwips < 0 || startYTwips < 0 ||
      endXTwips < 0 || endYTwips < 0) {
    return OXSDK_STATUS_INVALID_ARGUMENT;
  }
  return safeStatus([&] {
    return probe::editorSelect(requestId, documentHandle, method, startXTwips,
                               startYTwips, endXTwips, endYTwips);
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE std::int32_t
oxsdk_editor_discovery_get_state(oxsdk_request_id requestId,
                                 oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::editorGetState(requestId, documentHandle); });
}

#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
extern "C" EMSCRIPTEN_KEEPALIVE std::int32_t
oxsdk_editor_discovery_drain_scheduler(oxsdk_request_id requestId,
                                       oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::editorDrainScheduler(requestId, documentHandle); });
}
#endif
