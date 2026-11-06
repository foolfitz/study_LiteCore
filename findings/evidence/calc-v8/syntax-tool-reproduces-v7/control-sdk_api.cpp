#include "sdk_api.h"
#include "probe_engine.hpp"
#ifdef OXSDK_ODS_VIEWER
#include "ods_viewer.hpp"
#endif
#ifdef OXSDK_MS_FORMATS
#include "document_format.hpp"
#endif
#ifdef OXSDK_ODS_VIEWER_V2
#if !defined(OXSDK_ODS_VIEWER)
#error "OXSDK_ODS_VIEWER_V2 is added to the viewer's shape, never used alone"
#endif
// The core's own answer to "were the forms components built" (finding 158-B):
// config_host/config_features.h of the tree the rule compiles against.
#include <config_features.h>
#ifndef HAVE_FEATURE_DBCONNECTIVITY
#error "config_features.h does not define HAVE_FEATURE_DBCONNECTIVITY"
#endif
#endif

#if defined(OXSDK_ODS_EDITOR) && !defined(OXSDK_ODS_VIEWER_V2)
#error "OXSDK_ODS_EDITOR requires the v2 spreadsheet engine shape"
#endif

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
#if defined(OXSDK_ODS_VIEWER_V2)
  // SPEC-M4-viewer-v2 3.1: v1's bits plus part_info, plus form-controls when
  // the core has the forms components.  The manifest's expectedCapabilityBits
  // must equal this, so a manifest cannot claim forms this core lacks.
  return OXSDK_CAPABILITY_OPEN_ODT | OXSDK_CAPABILITY_RGBA_TILE |
         OXSDK_CAPABILITY_CANCEL_QUEUED | OXSDK_CAPABILITY_SEARCH |
         OXSDK_CAPABILITY_OPEN_ODS | OXSDK_CAPABILITY_PART_SWITCH |
         OXSDK_CAPABILITY_PART_TEXT | OXSDK_CAPABILITY_PART_INFO
#ifdef OXSDK_ODS_EDITOR
         | OXSDK_CAPABILITY_CELL_EDITING | OXSDK_CAPABILITY_SAVE_ODS
#ifdef OXSDK_ODS_RANGE
         | OXSDK_CAPABILITY_CELL_RANGE_FORMATTING
#endif
#ifdef OXSDK_ODS_STYLE
         | OXSDK_CAPABILITY_CELL_RANGE_STYLING
#endif
#ifdef OXSDK_ODS_HEADERS
         | OXSDK_CAPABILITY_CELL_HEADERS
#endif
#ifdef OXSDK_ODS_STRUCTURE
         | OXSDK_CAPABILITY_CELL_STRUCTURE
#endif
#ifdef OXSDK_ODS_COPY
#error positive control: the copy block is compiled
         | OXSDK_CAPABILITY_CELL_COPY
#endif
#ifdef OXSDK_ODS_COPY_HTML
         | OXSDK_CAPABILITY_CELL_COPY_HTML
#endif
#ifdef OXSDK_ODS_ZOOM
         | OXSDK_CAPABILITY_CELL_ZOOM
#endif
#ifdef OXSDK_ODS_UNDO
         // SPEC-P-calc-undo 4.2 E1: the engine's undo walk (probe_engine.cpp,
         // startOdsUndoWalk) and the two exports; redo rides on this bit.
         | OXSDK_CAPABILITY_UNDO
#endif
#ifdef OXSDK_MS_FORMATS
         | OXSDK_CAPABILITY_OPEN_XLSX | OXSDK_CAPABILITY_SAVE_XLSX
#endif
#endif
#if HAVE_FEATURE_DBCONNECTIVITY
         | OXSDK_CAPABILITY_FORM_CONTROLS
#endif
      ;
#elif defined(OXSDK_ODS_VIEWER)
  // SPEC-M4-ods-in-nextcloud 3.2: the reader's bits without save, plus the
  // viewer's three.  The manifest's expectedCapabilityBits must equal this.
  return OXSDK_CAPABILITY_OPEN_ODT | OXSDK_CAPABILITY_RGBA_TILE |
         OXSDK_CAPABILITY_CANCEL_QUEUED | OXSDK_CAPABILITY_SEARCH |
         OXSDK_CAPABILITY_OPEN_ODS | OXSDK_CAPABILITY_PART_SWITCH |
         OXSDK_CAPABILITY_PART_TEXT;
#elif defined(OXSDK_READER_PROFILE)
  return OXSDK_CAPABILITY_OPEN_ODT | OXSDK_CAPABILITY_RGBA_TILE |
         OXSDK_CAPABILITY_SAVE_ODT | OXSDK_CAPABILITY_CANCEL_QUEUED |
         OXSDK_CAPABILITY_SEARCH;
#else
  return OXSDK_CAPABILITY_OPEN_ODT | OXSDK_CAPABILITY_RGBA_TILE |
         OXSDK_CAPABILITY_INSERT_TEXT | OXSDK_CAPABILITY_SAVE_ODT |
         OXSDK_CAPABILITY_CANCEL_QUEUED | OXSDK_CAPABILITY_SEARCH |
         OXSDK_CAPABILITY_SELECTION_TEXT |
         OXSDK_CAPABILITY_REPLACE_SELECTION | OXSDK_CAPABILITY_UNDO |
         OXSDK_CAPABILITY_COMMENTS | OXSDK_CAPABILITY_TRACKED_CHANGES
#ifdef OXSDK_MS_FORMATS
         | OXSDK_CAPABILITY_OPEN_DOCX | OXSDK_CAPABILITY_SAVE_DOCX
#endif
         ;
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
#ifdef OXSDK_MS_FORMATS
    // SPEC-P-ms-formats 5.1 E1 (finding 013's narrow surface): the table, per build.
    if (probe::docformat::acceptedSuffix(probe::docformat::kThisBuild, name).empty())
      return probe::SubmitStatus::InvalidArgument;
#elif defined(OXSDK_ODS_VIEWER)
    // W7a (finding 013's allowlist): `.ods` beside `.odt`, either case.
    // Content detection still reads the zip's own `mimetype`.
    if (probe::odsviewer::acceptedSuffix(name).empty())
      return probe::SubmitStatus::InvalidArgument;
#else
    if (name.size() < 4 || name.substr(name.size() - 4) != ".odt")
      return probe::SubmitStatus::InvalidArgument;
#endif
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

// The viewer has no save (SPEC-M4 3.2, review M2): not in its export list and
// not compiled, because EMSCRIPTEN_KEEPALIVE exports a function whatever the
// list says -- the reader's click is kept out the same way.
#if !defined(OXSDK_ODS_VIEWER) || defined(OXSDK_ODS_EDITOR)
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_save(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    const char *formatUtf8, std::uint32_t formatLength) {
  if (!validRequest(requestId) || documentHandle == 0 || !formatUtf8 ||
      formatLength == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    const std::string format(formatUtf8, formatLength);
#ifdef OXSDK_MS_FORMATS
    if (!probe::docformat::savable(probe::docformat::kThisBuild, format))
#elif defined(OXSDK_ODS_EDITOR)
    if (format != "ods")
#else
    if (format != "odt")
#endif
      return probe::SubmitStatus::InvalidArgument;
    return probe::save(requestId, documentHandle, format);
  });
}
#endif

#ifdef OXSDK_ODS_EDITOR
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_cell(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::uint32_t expectedRevision, std::int32_t part, std::int32_t column,
    std::int32_t row, std::int32_t operation, const char *text,
    std::uint32_t textLength, std::uint32_t enabled) {
  constexpr int maxOperation =
#ifdef OXSDK_ODS_ZOOM
      16;
#elif defined(OXSDK_ODS_COPY)
      15;
#elif defined(OXSDK_ODS_STRUCTURE)
      14;
#elif defined(OXSDK_ODS_HEADERS)
      13;
#elif defined(OXSDK_ODS_STYLE)
      12;
#elif defined(OXSDK_ODS_RANGE)
      9;
#else
      5;
#endif
  if (!validRequest(requestId) || documentHandle == 0 || part < 0
      || column < 0 || row < 0 || operation < 0 || operation > maxOperation
      || enabled > 1 || (textLength > 0 && !text) || textLength > 131068)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::cell(requestId, documentHandle, expectedRevision, part,
        column, row, operation, std::string(text ? text : "", textLength), enabled != 0);
  });
}
#endif

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
#endif

// SPEC-P-calc-undo 4.2 E2 (Codex review 1): undo and redo are compiled for the
// Calc editor too when it carries OXSDK_ODS_UNDO; the rest of this reader-
// excluded block (selection, comments, tracked changes) stays Writer's.
#if !defined(OXSDK_READER_PROFILE) || defined(OXSDK_ODS_UNDO)
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
#endif

#ifndef OXSDK_READER_PROFILE
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

#ifdef OXSDK_E2_V20_LINK_BATCH
/*
 * SPEC-M3-link-batch 10.8 (S-11), the redo precedent: a document-level EXPORT
 * beside get_selection, never an editor action.  No wire id, no gesture; the
 * editor ABI stays 4.  A COMPILED export like redo, so the SDK gates the call
 * on the manifest's declaration before reaching for the symbol.  The export
 * list is the Makefile's per-profile `exports.txt` recipe; part 3 adds
 * `_oxsdk_document_page_rectangles` to v20's.
 */
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_page_rectangles(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::pageRectangles(requestId, documentHandle); });
}
#endif

#ifdef OXSDK_E2_V21_LINK_BATCH
/*
 * SPEC-M3-link-batch-v21 4.2: insert_text's shape and boundary checks.  The
 * content is judged on the engine thread (size included: the engine's reply
 * for over 65,536 bytes is INVALID_ARGUMENT with `dispatched: false`, so
 * 11.2 M3 can tell which layer refused); this boundary refuses only what
 * cannot be a request at all.  The Makefile's v21 export list adds
 * `_oxsdk_document_paste_markdown`.
 */
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_paste_markdown(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    const char *utf8, std::uint32_t utf8Length) {
  if (!validRequest(requestId) || documentHandle == 0 || !utf8 ||
      utf8Length == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::pasteMarkdown(requestId, documentHandle,
                                std::string(utf8, utf8Length));
  });
}
#endif

#ifdef OXSDK_E2_V24_TYPED_INSERT
/*
 * SPEC-M3-link-batch-v24 4.1 (finding 168): typed text through .uno:InsertText.
 * insert_text's shape and boundary checks; the content (UTF-8, NUL, line
 * breaks) is judged on the engine thread.  A document-level export like
 * page_rectangles and paste_markdown -- never an editor action, so the editor
 * ABI stays 6 (fable ruling 2) and the SDK gates the call on the manifest's
 * `typedInsert` declaration.  The Makefile's v24 export list adds
 * `_oxsdk_document_insert_typed_text`.
 */
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_insert_typed_text(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    const char *utf8, std::uint32_t utf8Length) {
  if (!validRequest(requestId) || documentHandle == 0 || !utf8 ||
      utf8Length == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus([&] {
    return probe::insertTypedText(requestId, documentHandle,
                                  std::string(utf8, utf8Length));
  });
}
#endif

#ifdef OXSDK_ODS_VIEWER
// SPEC-M4-ods-in-nextcloud 3.2.  A negative part cannot be a request; the
// upper bound needs the part count, which only the engine thread may read.
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_set_part(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::int32_t part) {
  if (!validRequest(requestId) || documentHandle == 0 || part < 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::setPart(requestId, documentHandle, part); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_current_part(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle) {
  if (!validRequest(requestId) || documentHandle == 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::currentPart(requestId, documentHandle); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_part_name(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::int32_t part) {
  if (!validRequest(requestId) || documentHandle == 0 || part < 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::partName(requestId, documentHandle, part); });
}

extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_part_text(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::int32_t part) {
  if (!validRequest(requestId) || documentHandle == 0 || part < 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::partText(requestId, documentHandle, part); });
}

#ifdef OXSDK_ODS_VIEWER_V2
extern "C" EMSCRIPTEN_KEEPALIVE int32_t oxsdk_document_part_info(
    oxsdk_request_id requestId, oxsdk_document_handle documentHandle,
    std::int32_t part) {
  if (!validRequest(requestId) || documentHandle == 0 || part < 0)
    return OXSDK_STATUS_INVALID_ARGUMENT;
  return safeStatus(
      [&] { return probe::partInfo(requestId, documentHandle, part); });
}
#endif
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
