#ifndef OXOFFICE_EDITOR_API_H
#define OXOFFICE_EDITOR_API_H

#include "sdk_api.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Narrow ODT editor ABI. Versioned independently from the Document SDK ABI. */
#define OXSDK_EDITOR_ABI_VERSION 1u

typedef enum oxsdk_editor_v1_action {
  OXSDK_EDITOR_V1_MOVE_CHARACTER_LEFT = 1,
  OXSDK_EDITOR_V1_MOVE_CHARACTER_RIGHT = 2,
  OXSDK_EDITOR_V1_DELETE_BACKWARD = 3,
  OXSDK_EDITOR_V1_DELETE_FORWARD = 4,
  OXSDK_EDITOR_V1_INSERT_PARAGRAPH_BREAK = 5,
  OXSDK_EDITOR_V1_INSERT_LINE_BREAK = 6,
  OXSDK_EDITOR_V1_SET_BOLD = 7,
  OXSDK_EDITOR_V1_SET_ITALIC = 8,
  OXSDK_EDITOR_V1_SET_UNDERLINE = 9,
  OXSDK_EDITOR_V1_SET_STRIKETHROUGH = 10
} oxsdk_editor_v1_action;

/*
 * extend_selection is accepted only by the two movement actions.
 * enabled is accepted only by the inline format actions
 * (SET_BOLD, SET_ITALIC, SET_UNDERLINE, SET_STRIKETHROUGH).
 * Both flags are strict 0/1 values. Mutations are revision guarded.
 */
int32_t oxsdk_editor_action(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    uint32_t expected_revision, uint32_t action, uint32_t extend_selection,
    uint32_t enabled);

int32_t oxsdk_editor_get_state(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle);

/*
 * Range selection (SPEC E1-D).  Selects from one document point to another.
 *
 * The method is fixed at this boundary and is NOT a parameter: only the
 * setTextSelection API path is reachable.  The gate recorded in SPEC E1-D
 * section 2.1 found that the synthesised-mouse-event path reports a completed
 * selection while selecting nothing at all -- the finding 022 defect shape --
 * so it must stay out of the product ABI, not merely default to off.
 *
 * A range that selects nothing is a legitimate outcome, not an error: callers
 * judge the result by reading the selection back (oxsdk_editor_get_state),
 * never by the fact that this call completed.
 */
int32_t oxsdk_editor_select_range(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    int32_t start_x_twips, int32_t start_y_twips,
    int32_t end_x_twips, int32_t end_y_twips);

#ifdef __cplusplus
}
#endif

#endif
