#include "sdk_api.h"

#include <cstdint>
#include <type_traits>

static_assert(OXSDK_ABI_VERSION == 0x00010001u);
static_assert(OXSDK_ABI_VERSION_MAJOR == 1u);
static_assert(OXSDK_ABI_VERSION_MINOR == 1u);
static_assert(sizeof(oxsdk_request_id) == sizeof(std::uint32_t));
static_assert(sizeof(oxsdk_document_handle) == sizeof(std::uint32_t));
static_assert(std::is_same_v<decltype(oxsdk_abi_version()), std::uint32_t>);
static_assert(OXSDK_STATUS_OK == 0);
static_assert(OXSDK_CAPABILITY_CANCEL_QUEUED == (1u << 4));
static_assert(OXSDK_CAPABILITY_SEARCH == (1u << 5));
static_assert(OXSDK_CAPABILITY_TRACKED_CHANGES == (1u << 10));

int main()
{
    return 0;
}
