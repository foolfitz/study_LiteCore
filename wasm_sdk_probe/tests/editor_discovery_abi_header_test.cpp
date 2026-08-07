#include "editor_discovery_api.h"

#include <cstdint>
#include <type_traits>

static_assert(OXSDK_EDITOR_DISCOVERY_ABI_VERSION == 1u);
static_assert(OXSDK_EDITOR_MOVE_CHARACTER_LEFT == 1);
static_assert(OXSDK_EDITOR_SET_LIST_ORDERED == 19);
static_assert(OXSDK_EDITOR_SELECTION_RESET == 3);
static_assert(std::is_same_v<
              decltype(oxsdk_editor_discovery_get_state(1, 1)), std::int32_t>);

int main() { return 0; }
