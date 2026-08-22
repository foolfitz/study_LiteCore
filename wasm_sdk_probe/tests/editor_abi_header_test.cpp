#include "editor_api.h"

#include <cstdint>
#include <type_traits>

/*
 * 2 since SPEC E2-B.  The v1 action assertions below are deliberately NOT
 * touched: 1-10 keep their wire ids in v2, so a test that pins them still
 * pins them.  Editing those to accommodate v2 would be the move this file
 * exists to prevent.
 */
// 3 since 2026-08-15: the action list did not change, the meaning of
// `enabled` did (finding 045).  Pinned here so the bump is a deliberate
// edit in two places rather than a silent drift in one.
//
// 4 since 2026-08-22, and the bump behaved: this assertion is what failed
// first when the header moved, before anything was built.  Ids 1-15 below are
// untouched, which is the whole claim v4 makes -- a successor identity that
// inherits verbatim rather than an edit to what v3 callers were told.
static_assert(OXSDK_EDITOR_ABI_VERSION == 4u);
static_assert(OXSDK_EDITOR_V1_MOVE_CHARACTER_LEFT == 1);
static_assert(OXSDK_EDITOR_V1_MOVE_CHARACTER_RIGHT == 2);
static_assert(OXSDK_EDITOR_V1_DELETE_BACKWARD == 3);
static_assert(OXSDK_EDITOR_V1_DELETE_FORWARD == 4);
static_assert(OXSDK_EDITOR_V1_INSERT_PARAGRAPH_BREAK == 5);
static_assert(OXSDK_EDITOR_V1_INSERT_LINE_BREAK == 6);
static_assert(OXSDK_EDITOR_V1_SET_BOLD == 7);
static_assert(OXSDK_EDITOR_V1_SET_ITALIC == 8);
/*
 * 9 and 10 were missing until 2026-08-15.  E1-C extended the frozen v1
 * contract with underline and strikethrough and rebound the verdict, and the
 * header grew both -- but the test that exists to pin the header did not, so
 * for two shipped artifacts the freeze test froze eight of the ten actions.
 * Found while auditing SPEC E2-B section 5 item 14; the JS declaration had
 * drifted the same way, and editor-shell/tests/declaration-drift.test.mjs now
 * catches that half automatically.
 */
static_assert(OXSDK_EDITOR_V1_SET_UNDERLINE == 9);
static_assert(OXSDK_EDITOR_V1_SET_STRIKETHROUGH == 10);
/* v2 adds five, and they are pinned the same way. */
static_assert(OXSDK_EDITOR_V2_SET_LIST_NONE == 11);
static_assert(OXSDK_EDITOR_V2_SET_LIST_UNORDERED == 12);
static_assert(OXSDK_EDITOR_V2_SET_LIST_ORDERED == 13);
static_assert(OXSDK_EDITOR_V2_SET_PARAGRAPH_HEADING == 14);
static_assert(OXSDK_EDITOR_V2_SET_PARAGRAPH_BODY == 15);
/*
 * v3 (ABI 4) appends five, pinned the same way and for the same reason.
 *
 * 16-19 are a contract surface over behaviour the engine already had; 20 is
 * the one new action.  Pinning them here now means the NEXT version cannot
 * quietly renumber them either -- which is the failure this file caught in
 * 2026-08-15, when two shipped artifacts had a freeze test that froze eight of
 * ten actions because the header grew and the test did not.
 */
static_assert(OXSDK_EDITOR_V3_MOVE_LINE_UP == 16);
static_assert(OXSDK_EDITOR_V3_MOVE_LINE_DOWN == 17);
static_assert(OXSDK_EDITOR_V3_MOVE_LINE_HOME == 18);
static_assert(OXSDK_EDITOR_V3_MOVE_LINE_END == 19);
static_assert(OXSDK_EDITOR_V3_DELETE_SELECTION == 20);
/* The gesture mask bits are ABI too -- the worker writes them from the manifest. */
static_assert(OXSDK_EDITOR_GESTURE_COLLAPSED == 1u);
static_assert(OXSDK_EDITOR_GESTURE_RANGE_SINGLE == 2u);
static_assert(OXSDK_EDITOR_GESTURE_RANGE_CROSS == 4u);

using EditorAction = std::int32_t (*)(
    oxsdk_request_id, oxsdk_document_handle, std::uint32_t, std::uint32_t,
    std::uint32_t, std::uint32_t);
using EditorGetState = std::int32_t (*)(oxsdk_request_id,
                                        oxsdk_document_handle);
/* Range selection is part of the same frozen surface (SPEC E1-D). */
using EditorSelectRange = std::int32_t (*)(
    oxsdk_request_id, oxsdk_document_handle, std::int32_t, std::int32_t,
    std::int32_t, std::int32_t);

static_assert(std::is_same_v<decltype(&oxsdk_editor_action), EditorAction>);
static_assert(
    std::is_same_v<decltype(&oxsdk_editor_get_state), EditorGetState>);
static_assert(
    std::is_same_v<decltype(&oxsdk_editor_select_range), EditorSelectRange>);

using EditorAbiVersion = std::uint32_t (*)();
using EditorSetActionGestures = std::int32_t (*)(std::uint32_t, std::uint32_t);
static_assert(
    std::is_same_v<decltype(&oxsdk_editor_abi_version), EditorAbiVersion>);
static_assert(std::is_same_v<decltype(&oxsdk_editor_set_action_gestures),
                             EditorSetActionGestures>);

int main() { return 0; }
