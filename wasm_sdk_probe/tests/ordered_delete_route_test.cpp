#include "ordered_delete_route.hpp"

#include <cstdio>
#include <vector>

// A synthetic selection oracle for the three K1 branches required by 16.2,
// plus invalid/unsupported reads and both pre-existing byte bounds. There are
// no LOK calls here; neither RESET restoration nor engine routing is proved.
namespace {
using probe::ordereddelete::Route;
using probe::ordereddelete::routeK1;
int failures = 0;
void check(bool ok, const char *name) {
  if (!ok) {
    ++failures;
    std::printf("FAIL %s\n", name);
  }
}
} // namespace

int main() {
  check(routeK1(LOK_SELTYPE_NONE, false, 0, true, {}) == Route::BoundaryNoop,
        "NONE is immediate boundary noop");
  check(routeK1(LOK_SELTYPE_TEXT, false, 1, true, {'x'}) == Route::DeleteUnit,
        "one nonseparator unit uses synchronous UNO delete");
  for (const auto separator : std::vector<std::uint32_t>{'\n', '\r', 0x2028, 0x2029})
    check(routeK1(LOK_SELTYPE_TEXT, false, separator < 128 ? 1 : 3, true,
                  {static_cast<std::uint32_t>(separator)}) == Route::RestoreForMerge,
          "separator requires restoration before the user key");
  check(routeK1(LOK_SELTYPE_COMPLEX, false, 1, true, {'x'}) == Route::Unsupported,
        "non-TEXT refuses");
  check(routeK1(LOK_SELTYPE_LARGE_TEXT, false, 1, true, {'x'}) == Route::Unsupported,
        "large-text type refuses independently of payload size");
  check(routeK1(LOK_SELTYPE_TEXT, true, 1, true, {'x'}) == Route::Unsupported,
        "missing text refuses");
  check(routeK1(LOK_SELTYPE_TEXT, false, 0, true, {}) == Route::Unsupported,
        "empty TEXT is not NONE");
  check(routeK1(LOK_SELTYPE_TEXT, false, 1, false, {'x'}) == Route::Unsupported,
        "failed UTF-8 decode refuses even with a partial vector");
  check(routeK1(LOK_SELTYPE_TEXT, false, 1, true, {}) == Route::Unsupported,
        "empty decoded vector refuses");
  for (const auto other : std::vector<std::uint32_t>{'\t', 0xfffc})
    check(routeK1(LOK_SELTYPE_TEXT, false, other < 128 ? 1 : 3, true,
                  {static_cast<std::uint32_t>(other)}) == Route::Unsupported,
          "tab/object unit refuses");
  for (const std::size_t bytes : {128, 129, 4096, 4097}) {
    std::vector<std::uint32_t> plain(bytes, 'x');
    auto separator = plain;
    separator.back() = '\n';
    check(routeK1(LOK_SELTYPE_TEXT, false, bytes, true, plain) ==
              (bytes <= 128 ? Route::DeleteUnit : Route::Unsupported),
          "plain byte boundary");
    check(routeK1(LOK_SELTYPE_TEXT, false, bytes, true, separator) ==
              (bytes <= 4096 ? Route::RestoreForMerge : Route::Unsupported),
          "separator byte boundary precedes the 128-byte unit cap");
  }
  std::printf("ordered delete route: %d failures\n", failures);
  return failures ? 1 : 0;
}
