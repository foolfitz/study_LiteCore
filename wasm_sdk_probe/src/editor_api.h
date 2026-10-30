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
 * 3 as of 2026-08-15.  The action list was unchanged -- what changed was the
 * SEMANTICS of one field: `enabled` on the four inline format actions is now
 * sent to core instead of being stored and discarded (finding 045), so a
 * client that asks for `false` gets "off" rather than a toggle.  A caller
 * cannot tell those two builds apart by looking at the action list, which is
 * exactly why the version has to move: an allowlist's version is an identity,
 * and the identity now includes what the fields mean.
 *
 * 4 as of 2026-08-22.  A SUCCESSOR identity, not an edit: ids 1-15 are
 * inherited verbatim and the new ones start at 16, so a v3 caller's constants
 * still mean what they meant.  What makes appending safe here -- and unsafe in
 * place -- is that the runtime handshake is an EXACT match: a client built for
 * one version and a binary built for the other refuse each other at init
 * rather than agreeing about the first fifteen and disagreeing about the rest.
 *
 * What is new is a contract surface, not new behaviour: the engine has
 * dispatched line movement (arrow/Home/End key codes) since the E2-A discovery
 * ABI drove it, and the product ABI simply never named it -- `internalAction()`
 * returned 0 and the boundary refused. So 16-19 open a door the engine was
 * already standing behind. 20 is the exception and is genuinely new.
 *
 * 5 as of 2026-10-16, in the v21 link batch only (SPEC-M3-link-batch-v21
 * 4.1): a successor identity again.  Ids 1-21 inherited verbatim, 22 and 23
 * appended (move-document-start / -end, finding 142).  v8-v20 stay at 4: the
 * define keeps their preprocessed output what it was.
 *
 * 6 is selected only by OXSDK_E2_V23_FEATURE_ABI6: the same IDs 1-23,
 * with extend_selection accepted by character and line moves (1,2,16-19).
 * The feature manifest grants those six existing actions the three gesture
 * classes. Diagnostic v23 builds retain ABI 5; the Document SDK ABI is separate.
 */
#if defined(OXSDK_E2_V23_FEATURE_ABI6)
#if !defined(OXSDK_E2_V23_LINK_BATCH) || !defined(OXSDK_E2_V21_LINK_BATCH)
#error "ABI6 feature requires the ordered v23 engine and inherited v21 actions"
#endif
#ifdef OXSDK_E2_V23_DIAGNOSTIC
#error "ABI6 feature cannot be combined with diagnostic instrumentation"
#endif
#define OXSDK_EDITOR_ABI_VERSION 6u
/*
 * OXSDK_E2_V24_TYPED_INSERT (SPEC-M3-link-batch-v24) adds a document-level
 * export, not an action: no id, gesture, limit or field meaning changes, so
 * the version stays 6 (fable ruling 2).  It is an ABI6 successor only.
 */
#elif defined(OXSDK_E2_V24_TYPED_INSERT)
#error "the v24 typed insert requires the ABI6 feature engine"
#elif defined(OXSDK_E2_V21_LINK_BATCH)
#define OXSDK_EDITOR_ABI_VERSION 5u
#else
#define OXSDK_EDITOR_ABI_VERSION 4u
#endif
/*
 * OXSDK_E2_V25_FORMAT_PROOF (SPEC-M3-link-batch-v25) changes two ordered
 * format replies (findings 171, 172).  No export, action, gesture, limit or
 * field meaning changes, so it is a v24 successor at ABI 6 only.
 */
#if defined(OXSDK_E2_V25_FORMAT_PROOF) && !defined(OXSDK_E2_V24_TYPED_INSERT)
#error "the v25 format proof requires the v24 typed-insert engine"
#endif
/*
 * OXSDK_E2_V27_FIRST_BLOCK (SPEC-M3-v27-finding-176) lets the ordered collapsed
 * route judge a two-paragraph readback by its first block, and records the undo
 * stack around a format action.  No export, action, gesture, limit or field
 * meaning changes: a v25/v26 successor at ABI 6.
 */
#if defined(OXSDK_E2_V27_FIRST_BLOCK) && !defined(OXSDK_E2_V25_FORMAT_PROOF)
#error "the v27 first-block read requires the v25 format-proof engine"
#endif
/*
 * OXSDK_E2_V28_LAST_BLOCK (SPEC-M3-v28-last-line-fallback) lets the ordered
 * collapsed route, when `.uno:SelectText` selects nothing, select one position
 * back and judge that readback by its LAST block.  No export, action, gesture,
 * limit or field meaning changes: a v27 successor at ABI 6.
 */
#if defined(OXSDK_E2_V28_LAST_BLOCK) && !defined(OXSDK_E2_V27_FIRST_BLOCK)
#error "the v28 last-block fallback requires the v27 first-block engine"
#endif

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
 * Neither flag is accepted by any of these: extend_selection is for movement
 * actions admitted by the selected ABI and enabled is for the four inline format actions, so both
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
 * v3 (ABI 4) appends five.  A separate enum again, for the reason v2 gave: the
 * enums above are pinned verbatim by tests/editor_abi_header_test.cpp, and
 * editing a test that exists to pin an earlier version is how a freeze test
 * turns into something that follows the implementation around.
 *
 * MOVE_LINE_* are the caret movements the engine has always had and the product
 * ABI never named. They take the same shape as the two character movements and
 * retain the legacy ABI 4/5 rule: `extend_selection` is accepted ONLY by
 * the two character movements, NOT by these four. That is deliberate and it is
 * a narrowing, not an oversight -- a shift-selected line movement is a
 * selection this build has never classified, and granting it here would let a
 * caller build a range the gesture router cannot describe. It can be added
 * by ABI 6 under the feature-only selector, after its protocol boundary.
 *
 * DELETE_SELECTION is the one genuinely new behaviour. It exists because
 * `delete-backward` is characterised caret-only and cut runs on a range by
 * definition, so cut could not remove text at all
 * (queue-cut-cannot-remove-text). It is NOT a widened delete-backward:
 * widening that one would discard its measured caret-only characterisation,
 * and a distinct action can declare its own gestures natively and refuse at a
 * collapsed caret rather than silently doing nothing.
 */
typedef enum oxsdk_editor_v3_action {
  OXSDK_EDITOR_V3_MOVE_LINE_UP = 16,
  OXSDK_EDITOR_V3_MOVE_LINE_DOWN = 17,
  OXSDK_EDITOR_V3_MOVE_LINE_HOME = 18,
  OXSDK_EDITOR_V3_MOVE_LINE_END = 19,
  OXSDK_EDITOR_V3_DELETE_SELECTION = 20,
  /*
   * SELECT_ALL is in the contract and WITHHELD BY THE MANIFEST on the v4
   * profile: the binary implements it, the manifest grants it no gesture, and
   * the mask is narrowing-only so a manifest can never widen that back.
   *
   * That asymmetry is the whole point. A capability can ship dark and be
   * granted later by a MEASUREMENT rather than another relink -- but only in
   * that direction, so shipping it dark costs nothing and claims nothing.
   * Its postcondition is uncharacterised, which is exactly why it is dark.
   */
  OXSDK_EDITOR_V3_SELECT_ALL = 21
} oxsdk_editor_v3_action;

#ifdef OXSDK_E2_V21_LINK_BATCH
/*
 * v4 (ABI 5) appends two, in a separate enum for the reason v2 and v3 gave:
 * the enums above are pinned verbatim by tests/editor_abi_header_test.cpp.
 *
 * Ctrl+Home / Ctrl+End (finding 142).  Caret moves like 1-2 and 16-19 --
 * revision unchanged, `changed: false`, completed by a caret callback or by
 * `verified-move-readback` -- and they take NO extend_selection in every ABI:
 * Ctrl+Shift+Home/End is a selection this build has never classified.  Inside
 * a table, a header or a section Writer goes up one level per press
 * (L-142-steps); nothing here merges the presses.
 */
typedef enum oxsdk_editor_v4_action {
  OXSDK_EDITOR_V4_MOVE_DOCUMENT_START = 22,
  OXSDK_EDITOR_V4_MOVE_DOCUMENT_END = 23
} oxsdk_editor_v4_action;
#endif

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
 * extend_selection is accepted by character moves (1,2) in every ABI, and
 * additionally by line moves (16-19) only in the ABI 6 feature build.
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
