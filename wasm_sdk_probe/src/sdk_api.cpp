#include "sdk_api.h"
#include "probe_engine.hpp"

#include <emscripten/emscripten.h>

#include <cstdlib>
#include <string>
#include <vector>

static_assert(sizeof(std::uint32_t) == 4, "R2 ABI requires 32-bit uint32_t");
static_assert(sizeof(oxsdk_request_id) == 4, "request ids must be 32-bit");
static_assert(sizeof(oxsdk_document_handle) == 4,
              "document handles must be 32-bit");
static_assert(OXSDK_ABI_VERSION == 0x00010001u,
              "unexpected ABI version encoding");

namespace {
bool validRequest(oxsdk_request_id requestId) { return requestId != 0; }

int32_t status(probe::SubmitStatus value) {
  return static_cast<int32_t>(value);
}

template <typename Function> int32_t safeStatus(Function &&function) noexcept {
  try {
    return status(function());
  } catch (...) {
    return OXSDK_STATUS_INTERNAL_ERROR;
  }
}

bool compatibleVersion(std::uint32_t requested) {
  const std::uint32_t major = requested >> 16;
  const std::uint32_t minor = requested & 0xffffu;
  return major == OXSDK_ABI_VERSION_MAJOR && minor <= OXSDK_ABI_VERSION_MINOR;
}
} // namespace

extern "C" EMSCRIPTEN_KEEPALIVE std::uint32_t oxsdk_abi_version(void) {
  return OXSDK_ABI_VERSION;
}

extern "C" EMSCRIPTEN_KEEPALIVE std::uint32_t oxsdk_capabilities(void) {
#ifdef OXSDK_READER_PROFILE
  return OXSDK_CAPABILITY_OPEN_ODT | OXSDK_CAPABILITY_RGBA_TILE |
         OXSDK_CAPABILITY_SAVE_ODT | OXSDK_CAPABILITY_CANCEL_QUEUED |
         OXSDK_CAPABILITY_SEARCH;
#else
  return OXSDK_CAPABILITY_OPEN_ODT | OXSDK_CAPABILITY_RGBA_TILE |
         OXSDK_CAPABILITY_INSERT_TEXT | OXSDK_CAPABILITY_SAVE_ODT |
         OXSDK_CAPABILITY_CANCEL_QUEUED | OXSDK_CAPABILITY_SEARCH |
         OXSDK_CAPABILITY_SELECTION_TEXT |
         OXSDK_CAPABILITY_REPLACE_SELECTION | OXSDK_CAPABILITY_UNDO |
         OXSDK_CAPABILITY_COMMENTS | OXSDK_CAPABILITY_TRACKED_CHANGES;
#endif
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_engine_start(
    std::uint32_t requestedAbiVersion, oxsdk_request_id requestId) {
  if (!validRequest(requestId))
    return OXSDK_STATUS_INVALID_ARGUMENT;
  if (!compatibleVersion(requestedAbiVersion))
    return OXSDK_STATUS_INCOMPATIBLE_ABI;
  return safeStatus([&] { return probe::start(requestId); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_open(
    oxsdk_request_id requestId, const std::uint8_t *bytes,
    std::uint32_t byteLength, const char *nameUtf8, std::uint32_t nameLength) {
  if (!validRequest(requestId) || !bytes || byteLength == 0 || !nameUtf8 ||
      nameLength == 0 || nameLength > 255) {
    return OXSDK_STATUS_INVALID_ARGUMENT;
  }

  return safeStatus([&] {
    std::string name(nameUtf8, nameLength);
    if (name.size() < 4 || name.substr(name.size() - 4) != ".odt")
      return probe::SubmitStatus::InvalidArgument;
    return probe::openBytes(
        requestId, std::vector<std::uint8_t>(bytes, bytes + byteLength),
        std::move(name));
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_paint(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::int32_t xTwips, std::int32_t yTwips, std::int32_t widthTwips,
    std::int32_t heightTwips, std::int32_t canvasWidthPx,
    std::int32_t canvasHeightPx) {
  if (!validRequest(requestId) || documentHandle == 0 || xTwips < 0 ||
      yTwips < 0 || widthTwips <= 0 || heightTwips <= 0 || canvasWidthPx <= 0 ||
      canvasHeightPx <= 0) {
    return OXSDK_STATUS_INVALID_ARGUMENT;
  }
  return safeStatus([&] {
    return probe::paintTile(requestId, documentHandle, xTwips, yTwips,
                            widthTwips, heightTwips, canvasWidthPx,
                            canvasHeightPx);
  });
}

#ifndef OXSDK_READER_PROFILE
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_click(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::int32_t xTwips, std::int32_t yTwips) {
  if (!validRequest(requestId) || documentHandle == 0 || xTwips < 0 ||
      yTwips < 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::click(requestId, documentHandle, xTwips, yTwips); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_insert_text(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    const char *utf8, std::uint32_t utf8Length) {
  if (!validRequest(requestId) || documentHandle == 0 || !utf8 ||
      utf8Length == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::insertText(requestId, documentHandle,
                             std::string(utf8, utf8Length));
  });
}
#endif

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_save(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    const char *formatUtf8, std::uint32_t formatLength) {
  if (!validRequest(requestId) || documentHandle == 0 || !formatUtf8 ||
      formatLength == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    const std::string format(formatUtf8, formatLength);
    if (format != "odt")
      return probe::SubmitStatus::InvalidArgument;
    return probe::save(requestId, documentHandle, format);
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_close(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] { return probe::close(requestId, documentHandle); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_search(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    const char *queryUtf8, std::uint32_t queryLength, std::uint32_t backward) {
  if (!validRequest(requestId) || documentHandle == 0 || !queryUtf8 ||
      queryLength == 0 || backward > 1)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::search(requestId, documentHandle,
                         std::string(queryUtf8, queryLength), backward != 0);
  });
}

#ifndef OXSDK_READER_PROFILE
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_get_selection(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::getSelection(requestId, documentHandle); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_replace_selection(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision, const char *utf8,
    std::uint32_t utf8Length) {
  if (!validRequest(requestId) || documentHandle == 0 || !utf8 ||
      utf8Length == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::replaceSelection(requestId, documentHandle, expectedRevision,
                                   std::string(utf8, utf8Length));
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_undo(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::undo(requestId, documentHandle, expectedRevision);
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_redo(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::redo(requestId, documentHandle, expectedRevision);
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_add_comment(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision, const char *textUtf8,
    std::uint32_t textLength, const char *authorUtf8,
    std::uint32_t authorLength) {
  if (!validRequest(requestId) || documentHandle == 0 || !textUtf8 ||
      textLength == 0 || !authorUtf8 || authorLength == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::addComment(requestId, documentHandle, expectedRevision,
                             std::string(textUtf8, textLength),
                             std::string(authorUtf8, authorLength));
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_list_comments(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::listComments(requestId, documentHandle); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_set_track_changes(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision, std::uint32_t enabled) {
  if (!validRequest(requestId) || documentHandle == 0 || enabled > 1)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::setTrackChanges(requestId, documentHandle, expectedRevision,
                                  enabled != 0);
  });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_list_changes(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::listChanges(requestId, documentHandle); });
}
#endif

extern "C" EMSCRIPTEN_KEEPALIVE int32_t
oxsdk_request_cancel(oxsdk_request_id requestId) {
  if (!validRequest(requestId))
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] { return probe::cancel(requestId); });
}

extern "C" EMSCRIPTEN_KEEPALIVE void *
oxsdk_buffer_alloc(std::uint32_t byteLength) {
  return byteLength == 0 ? nullptr : std::malloc(byteLength);
}

extern "C" EMSCRIPTEN_KEEPALIVE void oxsdk_buffer_free(void *pointer) {
  std::free(pointer);
}
