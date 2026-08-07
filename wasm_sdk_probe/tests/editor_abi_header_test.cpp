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

using EditorAction = std::int32_t (*)(
    oxsdk_request_id, oxsdk_document_handle, std::uint32_t, std::uint32_t,
    std::uint32_t, std::uint32_t);
using EditorGetState = std::int32_t (*)(oxsdk_request_id,
                                        oxsdk_document_handle);

static_assert(std::is_same_v<decltype(&oxsdk_editor_action), EditorAction>);
static_assert(
    std::is_same_v<decltype(&oxsdk_editor_get_state), EditorGetState>);

int main() { return 0; }
