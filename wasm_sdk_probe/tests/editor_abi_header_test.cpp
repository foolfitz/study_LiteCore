#include "editor_api.h"

#include <cstdint>
#include <type_traits>

static_assert(OXSDK_EDITOR_ABI_VERSION == 1u);
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

int main() { return 0; }
