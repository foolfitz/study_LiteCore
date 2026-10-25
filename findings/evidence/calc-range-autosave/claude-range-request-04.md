Read-only adversarial review of the supplied new native Calc range bridge. At most3 concrete bugs, <=300words. Entry validates nonnegative part/start/operation, visible existing sheet, operation6..9, enabled0or1, and expectedrevision beforemutations7..9. One explicit UNO rectangle max65536cells; hiddenincluded; crossingmerge refused, wholemergeallowed; protectedsheet must have uniformunlockedprotection. One XMultiPropertySet operation allscripts; aftermutation exceptions markuncertain andblockwrites, no crashrollbackclaimed. Core setPropertyValues collectsfontitems into oneApplyAttributes withselectioneditabilitypreflight. Caller serializes operations andincrementsrevisiononlychanged oruncertain. Uncompiledpendingownerbuild; identify actual semantic/partialwrite/mixedtoggle bugs, notgeneric testrequests.
#ifdef OXSDK_ODS_RANGE
// A bounded, explicit rectangle. UNO collects the three script-family items
// into one pattern and calls ApplyAttributes once; never issue per-cell writes.
constexpr std::uint64_t kRangeCellLimit = 65536;

std::string rangeFormat(const Reference<beans::XPropertySet> &props,
                        const Reference<beans::XPropertyState> &states, int format) {
  const std::vector<OUString> names = format == 7
      ? std::vector<OUString>{u"CharWeight"_ustr, u"CharWeightAsian"_ustr, u"CharWeightComplex"_ustr}
      : format == 8
      ? std::vector<OUString>{u"CharPosture"_ustr, u"CharPostureAsian"_ustr, u"CharPostureComplex"_ustr}
      : std::vector<OUString>{u"CharUnderline"_ustr};
  int previous = -1;
  for (const auto &name : names) {
    if (states->getPropertyState(name) == beans::PropertyState_AMBIGUOUS_VALUE)
      return "mixed";
    const bool on = format == 7 ? property<float>(props, name) >= awt::FontWeight::BOLD
        : format == 8 ? property<awt::FontSlant>(props, name) != awt::FontSlant_NONE
        : property<sal_Int16>(props, name) != awt::FontUnderline::NONE;
    if (previous >= 0 && previous != static_cast<int>(on)) return "mixed";
    previous = on;
  }
  return previous == 1 ? "on" : "off";
}

ptree accessRange(const Reference<sheet::XSpreadsheet> &sheet,
                  const Reference<frame::XModel> &model, int part, int column, int row,
                  int columns, int rows, int operation, const char *text, int textLength,
                  int enabled, bool &mutationAttempted) {
  if (!text || textLength <= 0)
    throw Refusal("INVALID_ARGUMENT", "range endpoint payload is required");
  ptree request;
  std::istringstream input(std::string(text, textLength));
  boost::property_tree::read_json(input, request);
  const int endColumn = request.get<int>("endColumn"), endRow = request.get<int>("endRow");
  if (endColumn < column || endRow < row || endColumn >= columns || endRow >= rows)
    throw Refusal("INVALID_ARGUMENT", "invalid range endpoints");
  const auto area = static_cast<std::uint64_t>(endColumn - column + 1)
      * static_cast<std::uint64_t>(endRow - row + 1);
  if (area > kRangeCellLimit)
    throw Refusal("RANGE_TOO_LARGE", "range exceeds 65536 logical cells");
  auto range = sheet->getCellRangeByPosition(column, row, endColumn, endRow);
  auto cursor = sheet->createCursorByRange(
      Reference<sheet::XSheetCellRange>(range, uno::UNO_QUERY_THROW));
  cursor->collapseToMergedArea();
  Reference<sheet::XCellRangeAddressable> addressed(cursor, uno::UNO_QUERY_THROW);
  const auto merged = addressed->getRangeAddress();
  const bool crossesMerge = merged.StartColumn != column || merged.StartRow != row
      || merged.EndColumn != endColumn || merged.EndRow != endRow;
  Reference<beans::XPropertySet> props(range, uno::UNO_QUERY_THROW);
  Reference<beans::XPropertyState> states(range, uno::UNO_QUERY_THROW);
  Reference<util::XProtectable> protection(sheet, uno::UNO_QUERY_THROW);
  Reference<frame::XStorable> storable(model, uno::UNO_QUERY_THROW);
  std::string refusal;
  if (storable->isReadonly()) refusal = "READ_ONLY";
  else if (crossesMerge) refusal = "RANGE_MERGE_BOUNDARY";
  else if (protection->isProtected()) {
    // An ambiguous protection struct is not proof that every cell is unlocked.
    if (states->getPropertyState(u"CellProtection"_ustr) == beans::PropertyState_AMBIGUOUS_VALUE
        || property<util::CellProtection>(props, u"CellProtection"_ustr).IsLocked)
      refusal = "READ_ONLY";
  }
  const auto before = operation == 6 ? std::string() : rangeFormat(props, states, operation);
  bool changed = false;
  if (operation != 6) {
    if (!refusal.empty()) throw Refusal(refusal.c_str(), "the entire range is refused before mutation");
    if (before != (enabled ? "on" : "off")) {
      Reference<beans::XMultiPropertySet> multi(range, uno::UNO_QUERY_THROW);
      uno::Sequence<OUString> names;
      uno::Sequence<uno::Any> values;
      if (operation == 7) {
        names = {u"CharWeight"_ustr, u"CharWeightAsian"_ustr, u"CharWeightComplex"_ustr};
        const uno::Any value(enabled ? awt::FontWeight::BOLD : awt::FontWeight::NORMAL);
        values = {value, value, value};
      } else if (operation == 8) {
        names = {u"CharPosture"_ustr, u"CharPostureAsian"_ustr, u"CharPostureComplex"_ustr};
        const uno::Any value(enabled ? awt::FontSlant_ITALIC : awt::FontSlant_NONE);
        values = {value, value, value};
      } else {
        names = {u"CharUnderline"_ustr};
        values = {uno::Any(static_cast<sal_Int16>(enabled ? awt::FontUnderline::SINGLE : awt::FontUnderline::NONE))};
      }
      mutationAttempted = true;
      multi->setPropertyValues(names, values);
      if (rangeFormat(props, states, operation) != (enabled ? "on" : "off"))
        throw Refusal("RANGE_POSTCONDITION_FAILED", "native range format did not reach the requested state");
      changed = true;
    }
  }
  ptree result;
  result.put("ok", true); result.put("part", part);
  result.put("column", column); result.put("row", row);
  result.put("endColumn", endColumn); result.put("endRow", endRow);
  result.put("writable", refusal.empty()); result.put("refusalCode", refusal);
  result.put("bold", rangeFormat(props, states, 7));
  result.put("italic", rangeFormat(props, states, 8));
  result.put("underline", rangeFormat(props, states, 9));
  result.put("changed", changed);
  return result;
}
#endif