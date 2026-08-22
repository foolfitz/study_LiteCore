#ifndef OXOFFICE_EDITOR_DISCOVERY_API_H
#define OXOFFICE_EDITOR_DISCOVERY_API_H

#include "sdk_api.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* E1-A diagnostic-only ABI. This is not part of the Document SDK ABI. */
#define OXSDK_EDITOR_DISCOVERY_ABI_VERSION 1u

typedef enum oxsdk_editor_action {
  OXSDK_EDITOR_MOVE_CHARACTER_LEFT = 1,
  OXSDK_EDITOR_MOVE_CHARACTER_RIGHT = 2,
  OXSDK_EDITOR_MOVE_LINE_UP = 3,
  OXSDK_EDITOR_MOVE_LINE_DOWN = 4,
  OXSDK_EDITOR_MOVE_LINE_HOME = 5,
  OXSDK_EDITOR_MOVE_LINE_END = 6,
  OXSDK_EDITOR_DELETE_BACKWARD = 7,
  OXSDK_EDITOR_DELETE_FORWARD = 8,
  OXSDK_EDITOR_INSERT_PARAGRAPH_BREAK = 9,
  OXSDK_EDITOR_INSERT_LINE_BREAK = 10,
  OXSDK_EDITOR_UNDO = 11,
  OXSDK_EDITOR_REDO = 12,
  OXSDK_EDITOR_SET_BOLD = 13,
  OXSDK_EDITOR_SET_ITALIC = 14,
  OXSDK_EDITOR_SET_PARAGRAPH_BODY = 15,
  OXSDK_EDITOR_SET_PARAGRAPH_HEADING = 16,
  OXSDK_EDITOR_SET_LIST_NONE = 17,
  OXSDK_EDITOR_SET_LIST_UNORDERED = 18,
  OXSDK_EDITOR_SET_LIST_ORDERED = 19,
  OXSDK_EDITOR_SET_UNDERLINE = 20,
  OXSDK_EDITOR_SET_STRIKETHROUGH = 21,
  /*
   * Added with the product ABI's version 4.  These are the engine's INTERNAL
   * numbers -- the product contract calls this one 20, and editor_api.cpp is
   * the only thing that converts between the two lists.
   *
   * Deleting a range that the caller already selected. Distinct from
   * DELETE_BACKWARD/DELETE_FORWARD, which the selection barrier characterises
   * as caret-only: those refuse a pre-existing selection on purpose and make
   * their own one-unit one. This is the opposite gesture and needs the
   * opposite treatment, so it dispatches on the selection that is there.
   */
  OXSDK_EDITOR_DELETE_SELECTION = 22
} oxsdk_editor_action;

typedef enum oxsdk_editor_selection_method {
  OXSDK_EDITOR_SELECTION_MOUSE_DRAG = 1,
  OXSDK_EDITOR_SELECTION_TEXT_HANDLES = 2,
  OXSDK_EDITOR_SELECTION_RESET = 3
} oxsdk_editor_selection_method;

int32_t oxsdk_editor_discovery_action(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    uint32_t expected_revision, uint32_t action, uint32_t extend_selection,
    uint32_t option);

int32_t oxsdk_editor_discovery_select(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    uint32_t method, int32_t start_x_twips, int32_t start_y_twips,
    int32_t end_x_twips, int32_t end_y_twips);

int32_t oxsdk_editor_discovery_get_state(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle);

#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
/* Finding 016 isolated diagnostic ABI; never exported by the normal E1 profile. */
int32_t oxsdk_editor_discovery_drain_scheduler(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle);
#endif

#ifdef __cplusplus
}
#endif

#endif
