#ifndef OXOFFICE_DOCUMENT_SDK_API_H
#define OXOFFICE_DOCUMENT_SDK_API_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define OXSDK_ABI_VERSION_MAJOR 1u
#define OXSDK_ABI_VERSION_MINOR 1u
#define OXSDK_ABI_VERSION                                                      \
  ((OXSDK_ABI_VERSION_MAJOR << 16) | OXSDK_ABI_VERSION_MINOR)

typedef uint32_t oxsdk_request_id;
typedef uint32_t oxsdk_document_handle;

typedef enum oxsdk_status {
  OXSDK_STATUS_OK = 0,
  OXSDK_STATUS_INVALID_ARGUMENT = 1,
  OXSDK_STATUS_INCOMPATIBLE_ABI = 2,
  OXSDK_STATUS_NOT_STARTED = 3,
  OXSDK_STATUS_DUPLICATE_REQUEST = 4,
  OXSDK_STATUS_REQUEST_NOT_FOUND = 5,
  OXSDK_STATUS_NOT_CANCELLABLE = 6,
  OXSDK_STATUS_INTERNAL_ERROR = 7
} oxsdk_status;

typedef enum oxsdk_capability {
  OXSDK_CAPABILITY_OPEN_ODT = 1u << 0,
  OXSDK_CAPABILITY_RGBA_TILE = 1u << 1,
  OXSDK_CAPABILITY_INSERT_TEXT = 1u << 2,
  OXSDK_CAPABILITY_SAVE_ODT = 1u << 3,
  OXSDK_CAPABILITY_CANCEL_QUEUED = 1u << 4,
  OXSDK_CAPABILITY_SEARCH = 1u << 5,
  OXSDK_CAPABILITY_SELECTION_TEXT = 1u << 6,
  OXSDK_CAPABILITY_REPLACE_SELECTION = 1u << 7,
  OXSDK_CAPABILITY_UNDO = 1u << 8,
  OXSDK_CAPABILITY_COMMENTS = 1u << 9,
  OXSDK_CAPABILITY_TRACKED_CHANGES = 1u << 10
#ifdef OXSDK_ODS_VIEWER
  ,
  /* SPEC-M4-ods-in-nextcloud 3.2: the read-only spreadsheet viewer only. */
  OXSDK_CAPABILITY_OPEN_ODS = 1u << 11,
  OXSDK_CAPABILITY_PART_SWITCH = 1u << 12,
  OXSDK_CAPABILITY_PART_TEXT = 1u << 13
#ifdef OXSDK_ODS_VIEWER_V2
  ,
  /* SPEC-M4-viewer-v2 3.1: part_info (finding 157), and whether the core this
     engine was compiled against has the forms components (finding 158-B; read
     from the core's own HAVE_FEATURE_DBCONNECTIVITY, never asserted). */
  OXSDK_CAPABILITY_PART_INFO = 1u << 14,
  OXSDK_CAPABILITY_FORM_CONTROLS = 1u << 15
#endif
#endif
} oxsdk_capability;

uint32_t oxsdk_abi_version(void);
uint32_t oxsdk_capabilities(void);

int32_t oxsdk_engine_start(uint32_t requested_abi_version,
                           oxsdk_request_id request_id);

/* Input bytes and UTF-8 names are borrowed only for the duration of this call.
 */
int32_t oxsdk_document_open(oxsdk_request_id request_id, const uint8_t *bytes,
                            uint32_t byte_length, const char *name_utf8,
                            uint32_t name_length);
int32_t oxsdk_document_paint(oxsdk_request_id request_id,
                             oxsdk_document_handle document_handle,
                             int32_t x_twips, int32_t y_twips,
                             int32_t width_twips, int32_t height_twips,
                             int32_t canvas_width_px, int32_t canvas_height_px);
int32_t oxsdk_document_click(oxsdk_request_id request_id,
                             oxsdk_document_handle document_handle,
                             int32_t x_twips, int32_t y_twips);
int32_t oxsdk_document_insert_text(oxsdk_request_id request_id,
                                   oxsdk_document_handle document_handle,
                                   const char *utf8, uint32_t utf8_length);
int32_t oxsdk_document_save(oxsdk_request_id request_id,
                            oxsdk_document_handle document_handle,
                            const char *format_utf8, uint32_t format_length);
int32_t oxsdk_document_close(oxsdk_request_id request_id,
                             oxsdk_document_handle document_handle);
int32_t oxsdk_document_search(oxsdk_request_id request_id,
                              oxsdk_document_handle document_handle,
                              const char *query_utf8, uint32_t query_length,
                              uint32_t backward);
int32_t oxsdk_document_get_selection(oxsdk_request_id request_id,
                                     oxsdk_document_handle document_handle);
int32_t oxsdk_document_replace_selection(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    uint32_t expected_revision, const char *utf8, uint32_t utf8_length);
int32_t oxsdk_document_undo(oxsdk_request_id request_id,
                            oxsdk_document_handle document_handle,
                            uint32_t expected_revision);
/*
 * Redo, added 2026-08-22 beside undo rather than as an editor action.
 * queue-redo-and-line-movement-need-wire-ids asked for a wire id and the answer
 * is that it needs none: the narrow editor ABI is an allowlist of the actions a
 * NARROWED product exposes, and undo was never in it either.
 */
int32_t oxsdk_document_redo(oxsdk_request_id request_id,
                            oxsdk_document_handle document_handle,
                            uint32_t expected_revision);
int32_t oxsdk_document_add_comment(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    uint32_t expected_revision, const char *text_utf8, uint32_t text_length,
    const char *author_utf8, uint32_t author_length);
int32_t oxsdk_document_list_comments(oxsdk_request_id request_id,
                                     oxsdk_document_handle document_handle);
int32_t oxsdk_document_set_track_changes(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    uint32_t expected_revision, uint32_t enabled);
int32_t oxsdk_document_list_changes(oxsdk_request_id request_id,
                                    oxsdk_document_handle document_handle);
#ifdef OXSDK_E2_V20_LINK_BATCH
/*
 * SPEC-M3-link-batch 10.8: the raw `getPartPageRectangles()` string, the
 * document size and `getParts()`, in one reply.  A document-level export like
 * redo, never an editor action.
 */
int32_t oxsdk_document_page_rectangles(oxsdk_request_id request_id,
                                       oxsdk_document_handle document_handle);
#endif
#ifdef OXSDK_E2_V21_LINK_BATCH
/*
 * SPEC-M3-link-batch-v21 4.2: paste `utf8` as Markdown at the caret.  The
 * shape of oxsdk_document_insert_text; the MIME type is fixed in the engine.
 * The bytes are judged before anything is dispatched (md4c's scan, NUL, UTF-8,
 * 65,536 bytes, the thread encoding, a collapsed caret, the undo read): every
 * such refusal is an error event with `dispatched: false`.  Completion is
 * `markdown-pasted` with the revision advanced by one, or
 * MUTATION_OUTCOME_UNKNOWN (`dispatched: true`) when the undo stack does not
 * prove the paste.  A document-level export like page_rectangles: no wire id,
 * no gesture, the editor ABI does not move for it.
 */
int32_t oxsdk_document_paste_markdown(oxsdk_request_id request_id,
                                      oxsdk_document_handle document_handle,
                                      const char *utf8, uint32_t utf8_length);
#endif

#ifdef OXSDK_ODS_VIEWER
/*
 * SPEC-M4-ods-in-nextcloud 3.2, the read-only spreadsheet viewer.  Document-
 * level queries like get_selection: no wire id, no gesture.  A part outside
 * 0..parts-1 is an error event with INVALID_ARGUMENT from the engine thread.
 *
 *   set_part      switch the view to `part`; replies `part-set` with the part
 *                 READ BACK and the new part's document size
 *   current_part  replies `current-part` with the view's part
 *   part_name     replies `part-name` with the sheet's name
 *   part_text     replies `part-text` with the part's text as text/plain:
 *                 switch, select all, read, deselect, switch back, all on the
 *                 engine thread; `partAfter` is read, not assumed
 *
 * `oxsdk_document_open` accepts `.ods` beside `.odt` (either case), and the
 * viewer has no save.
 */
int32_t oxsdk_document_set_part(oxsdk_request_id request_id,
                                oxsdk_document_handle document_handle,
                                int32_t part);
int32_t oxsdk_document_current_part(oxsdk_request_id request_id,
                                    oxsdk_document_handle document_handle);
int32_t oxsdk_document_part_name(oxsdk_request_id request_id,
                                 oxsdk_document_handle document_handle,
                                 int32_t part);
int32_t oxsdk_document_part_text(oxsdk_request_id request_id,
                                 oxsdk_document_handle document_handle,
                                 int32_t part);
#ifdef OXSDK_ODS_VIEWER_V2
/*
 * SPEC-M4-viewer-v2 3.1 (finding 157).
 *
 *   part_info     replies `part-info` with LOK's getPartInfo JSON for `part`,
 *                 as a string (`info`); the SDK parses it.  Its `visible` is
 *                 what a tab needs: core has no page for a hidden sheet, so
 *                 set_part to one stays where it was.
 */
int32_t oxsdk_document_part_info(oxsdk_request_id request_id,
                                 oxsdk_document_handle document_handle,
                                 int32_t part);
#endif
#endif

/* Cancels only a request that has not begun executing on the engine thread. */
int32_t oxsdk_request_cancel(oxsdk_request_id request_id);

/* Event-owned output pointers must be released exactly once with this API. */
void *oxsdk_buffer_alloc(uint32_t byte_length);
void oxsdk_buffer_free(void *pointer);

#ifdef __cplusplus
}
#endif

#endif
