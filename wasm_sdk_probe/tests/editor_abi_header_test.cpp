#include "editor_api.h"

#include <cstdint>
#include <type_traits>

/*
 * 2 since SPEC E2-B.  The v1 action assertions below are deliberately NOT
 * touched: 1-10 keep their wire ids in v2, so a test that pins them still
 * pins them.  Editing those to accommodate v2 would be the move this file
 * exists to prevent.
 */
static_assert(OXSDK_EDITOR_ABI_VERSION == 2u);
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
