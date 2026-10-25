#ifndef OXOFFICE_ORDERED_DELETE_ROUTE_HPP
#define OXOFFICE_ORDERED_DELETE_ROUTE_HPP

// Spec 16.2, clarified by the resumed diagnostic ruling: classify the
// synchronous K1 read, before any document mutation. This does not implement
// the RESET restoration: that engine branch still requires RESET-HOLDS.
// Like probe_engine.cpp, the translation unit opts into LOK_USE_UNSTABLE_API.
#include "merge_key_undo.hpp"
#include <LibreOfficeKit/LibreOfficeKitEnums.h>

namespace probe {
namespace ordereddelete {

enum class Route { BoundaryNoop, DeleteUnit, RestoreForMerge, Unsupported };

// byteCount and decoded come from the same readSelection() text. A failed
// UTF-8 decode is explicitly refused, never classified from a partial vector.
inline Route routeK1(int selectionType, bool textMissing, std::size_t byteCount,
                     bool utf8Valid, const std::vector<std::uint32_t> &decoded) {
  if (selectionType == LOK_SELTYPE_NONE)
    return Route::BoundaryNoop;
  if (selectionType != LOK_SELTYPE_TEXT || textMissing || byteCount == 0 ||
      byteCount > 4096 || !utf8Valid || decoded.empty())
    return Route::Unsupported;
  const auto unit = merge::classifyUnit(decoded);
  if (unit == merge::UnitClass::MergeKey)
    return Route::RestoreForMerge;
  if (byteCount <= 128 && unit == merge::UnitClass::Barrier)
    return Route::DeleteUnit;
  return Route::Unsupported;
}

} // namespace ordereddelete
} // namespace probe

#endif
