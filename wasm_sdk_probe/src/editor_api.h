#ifndef OXOFFICE_EDITOR_API_H
#define OXOFFICE_EDITOR_API_H

#include "sdk_api.h"

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Narrow ODT editor ABI. Versioned independently from the Document SDK ABI.
 *
 * Flat integer, and the runtime requires an EXACT match (SPEC E2-B 5.4).  The
 * Document SDK's own version is a packed major/minor with a compatibility
 * range, and copying that here was considered and rejected: this contract is an
 * allowlist, and an allowlist's version is an identity, not a range.  Range
 * semantics are what let E1-C extend v1 in place while the freeze test kept
 * pinning only eight of the ten actions.
 *
 * 3 as of 2026-08-15.  The action list is unchanged -- what changed is the
 * SEMANTICS of one field: `enabled` on the four inline format actions is now
 * sent to core instead of being stored and discarded (finding 045), so a
 * client that asks for `false` gets "off" rather than a toggle.  A caller
 * cannot tell those two builds apart by looking at the action list, which is
 * exactly why the version has to move: an allowlist's version is an identity,
 * and the identity now includes what the fields mean.
 */
#define OXSDK_EDITOR_ABI_VERSION 3u

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
 * v2 adds five paragraph-level actions.  Wire IDs 1-10 are unchanged, so a v2
 * caller sends the v1 constants for those -- which is why this is a separate
 * enum rather than five more entries in the one above: the enum above is
 * pinned, verbatim, by tests/editor_abi_header_test.cpp, and editing a test
 * that exists to pin v1 is how a freeze test turns into something that follows
 * the implementation around.
 *
 * Neither flag is accepted by any of these: extend_selection is for the two
 * movement actions and enabled is for the four inline format actions, so both
 * must be strictly 0 here (SPEC E2-B 5.11, negative matrix N7).
 *
 * set_paragraph_heading takes no level: narrowing 2 promises H1 only, so the
 * level is implied.  Supporting H2-H6 later is a breaking change that adds a
 * parameter -- not a spare field left here untested today.
 */
typedef enum oxsdk_editor_v2_action {
  OXSDK_EDITOR_V2_SET_LIST_NONE = 11,
  OXSDK_EDITOR_V2_SET_LIST_UNORDERED = 12,
  OXSDK_EDITOR_V2_SET_LIST_ORDERED = 13,
  OXSDK_EDITOR_V2_SET_PARAGRAPH_HEADING = 14,
  OXSDK_EDITOR_V2_SET_PARAGRAPH_BODY = 15
} oxsdk_editor_v2_action;

/*
 * Which selection shapes an action may be dispatched on.  The classes are the
 * engine's own routing boundary (SPEC E2-B 9.9), not a separate taxonomy:
 * COLLAPSED is a caret, RANGE_SINGLE is a range whose pre-dispatch html
 * readback holds one block, RANGE_CROSS is one that holds more.
 */
#define OXSDK_EDITOR_GESTURE_COLLAPSED 1u
#define OXSDK_EDITOR_GESTURE_RANGE_SINGLE 2u
#define OXSDK_EDITOR_GESTURE_RANGE_CROSS 4u

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
 * The editor ABI version this BINARY implements.
 *
 * The manifest also carries an abiVersion, but a manifest is a claim and a
 * binary is a fact, and findings 027/036 are about those two coming apart: a
 * profile is assembled, the hash is not a function of the source, and a stale
 * wasm beside a fresh manifest runs today with nobody the wiser.  The worker
 * calls this at init and refuses on mismatch -- the same shape as
 * oxsdk_abi_version() for the Document SDK.
 */
uint32_t oxsdk_editor_abi_version(void);

/*
 * Restrict one action to a set of gesture classes.  Called by the worker at
 * init, once per action, from the profile manifest.
 *
 * This exists because the engine reads no manifest -- there are zero references
 * to one in probe_engine.cpp or editor_api.cpp -- and the mask cannot ride on
 * the per-dispatch options either, since both option flags must be 0 for
 * actions 11-15.  Without it a partial GO that restricts a gesture is
 * expressible in the manifest and unenforceable at runtime, which is precisely
 * the "manifest describes but does not constrain" defect SPEC E2-B 5.7 exists
 * to remove.
 *
 * Narrowing only: the mask can withhold a gesture the binary implements, never
 * grant one it does not. A tampered manifest therefore cannot widen the ABI.
 * The default is every class the binary supports.
 */
int32_t oxsdk_editor_set_action_gestures(uint32_t action, uint32_t gesture_mask);

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
/*
 * Place the caret at a point and ANSWER with where it went.
 *
 * queue-verify-caret-by-block-identity.  The existing click entry point replies
 * before core has processed anything and says nothing about the outcome, so
 * every caller had to invert the mapping -- post a pixel, then guess from a
 * rectangle.  Findings 048, 051 and 052 are that inversion's three shapes.
 *
 * The reply carries the caret rectangle, the caret paragraph's FINGERPRINT and
 * the offset within it.  A fingerprint, not an index: four native rounds
 * established that LOK carries no paragraph index anywhere, and not the text
 * itself, because this ABI does not hand the document's contents to the host
 * through the state channel.  Two paragraphs with the same text are therefore
 * indistinguishable -- the named limit, not a hidden one.
 */
int32_t oxsdk_editor_place_caret(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    int32_t x_twips, int32_t y_twips);

int32_t oxsdk_editor_select_range(
    oxsdk_request_id request_id, oxsdk_document_handle document_handle,
    int32_t start_x_twips, int32_t start_y_twips,
    int32_t end_x_twips, int32_t end_y_twips);

#ifdef __cplusplus
}
#endif

#endif
