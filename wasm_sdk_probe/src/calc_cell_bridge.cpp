// SPEC-M4-cell-editing-v1: synchronous cell model access, independent of
// CELL_FORMULA/STATE_CHANGED callback timing. Only this TU uses internal headers.
#include "calc_cell_bridge.h"
#ifndef LOK_USE_UNSTABLE_API
#define LOK_USE_UNSTABLE_API
#endif
#include <LibreOfficeKit/LibreOfficeKit.h>

#include <sfx2/lokhelper.hxx>
#include <sfx2/viewsh.hxx>
#include <vcl/svapp.hxx>
#include <com/sun/star/awt/FontSlant.hpp>
#include <com/sun/star/awt/FontUnderline.hpp>
#include <com/sun/star/awt/FontWeight.hpp>
#include <com/sun/star/beans/XPropertySet.hpp>
#include <com/sun/star/beans/XPropertyState.hpp>
#include <com/sun/star/beans/XMultiPropertySet.hpp>
#include <com/sun/star/container/XIndexAccess.hpp>
#include <com/sun/star/frame/XModel.hpp>
#include <com/sun/star/frame/XStorable.hpp>
#include <com/sun/star/util/CellProtection.hpp>
#include <com/sun/star/sheet/XCellRangeAddressable.hpp>
#include <com/sun/star/table/XColumnRowRange.hpp>
#ifdef OXSDK_ODS_STYLE
#include <com/sun/star/table/CellHoriJustify.hpp>
#endif
#include <com/sun/star/sheet/XSpreadsheet.hpp>
#include <com/sun/star/sheet/XSpreadsheetDocument.hpp>
#include <com/sun/star/sheet/XSheetCellCursor.hpp>
#include <com/sun/star/sheet/XSheetCellRange.hpp>
#include <com/sun/star/sheet/XSpreadsheetView.hpp>
#include <com/sun/star/view/XSelectionSupplier.hpp>
#include <com/sun/star/util/XProtectable.hpp>
#include <com/sun/star/text/XTextRange.hpp>
#include <rtl/ustring.hxx>

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#ifdef OXSDK_ODS_STYLE
#include <cstdio>
#endif
#include <sstream>
#include <stdexcept>
#ifdef OXSDK_ODS_STYLE
#include <utility>
#endif
#include <vector>

namespace {
using namespace com::sun::star;
using uno::Reference;
using boost::property_tree::ptree;

struct Refusal : std::runtime_error {
  std::string code;
  Refusal(const char *c, const char *message) : std::runtime_error(message), code(c) {}
};

template<typename T> T property(const Reference<beans::XPropertySet> &p,
                                const OUString &name) {
  T value{};
  if (!(p->getPropertyValue(name) >>= value))
    throw Refusal("CELL_STATE_UNAVAILABLE", "cell property has no scalar value");
  return value;
}

ptree commandValues(LibreOfficeKitDocument *doc, const std::string &command) {
  char *raw = doc->pClass->getCommandValues(doc, command.c_str());
  if (!raw)
    throw Refusal("CELL_GEOMETRY_UNAVAILABLE", "LOK returned no command values");
  const std::string json(raw);
  std::free(raw);
  std::istringstream stream(json);
  ptree values;
  boost::property_tree::read_json(stream, values);
  return values;
}

int headerIndex(const ptree &headers, int coordinate, bool columns) {
  int previousIndex = -1;
  double previousSize = 0;
  bool first = true;
  const double pixel = coordinate / 15.0;
  for (const auto &item : headers) {
    const auto label = item.second.get<std::string>("text");
    int lastIndex = 0;
    if (columns && !label.empty() && label[0] >= 'A' && label[0] <= 'Z') {
      for (char c : label) lastIndex = lastIndex * 26 + c - 'A' + 1;
      --lastIndex;
    } else {
      lastIndex = std::stoi(label) - 1;
    }
    const double size = item.second.get<double>("size");
    if (!first && size > previousSize && pixel >= previousSize && pixel < size) {
      const int count = lastIndex - previousIndex;
      if (count <= 0) break;
      return previousIndex + 1 + static_cast<int>(
          (pixel - previousSize) * count / (size - previousSize));
    }
    first = false;
    previousSize = size;
    previousIndex = lastIndex;
  }
  throw Refusal("CELL_GEOMETRY_UNAVAILABLE", "point is outside the returned cell headers");
}

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

#ifdef OXSDK_ODS_STYLE
// SPEC-P-demo-batch-3 3.1.  Colours cross as text: write_json turns every number
// into a string anyway, and -1 is not a colour, it is "automatic" (CharColor) or
// "no fill" (CellBackColor).
constexpr sal_Int32 kNoColor = -1;

const char *styleProperty(int operation) {
  return operation == 10 ? "CharColor" : operation == 11 ? "CellBackColor" : "HoriJustify";
}

std::string colorName(sal_Int32 value, const char *none) {
  if (value == kNoColor) return none;
  char text[8];
  std::snprintf(text, sizeof text, "#%06x", static_cast<unsigned>(value) & 0xffffffu);
  return text;
}

const std::vector<std::pair<const char *, table::CellHoriJustify>> &horizontalAligns() {
  static const std::vector<std::pair<const char *, table::CellHoriJustify>> names{
      {"standard", table::CellHoriJustify_STANDARD}, {"left", table::CellHoriJustify_LEFT},
      {"center", table::CellHoriJustify_CENTER}, {"right", table::CellHoriJustify_RIGHT},
      {"block", table::CellHoriJustify_BLOCK}};
  return names;
}

// What the document says.  A value outside the closed list (REPEAT, set by a
// desktop application) is reported rather than folded into a neighbour.
std::string alignName(table::CellHoriJustify value) {
  for (const auto &entry : horizontalAligns())
    if (entry.second == value) return entry.first;
  return "other";
}

std::string rangeStyle(const Reference<beans::XPropertySet> &props,
                       const Reference<beans::XPropertyState> &states, int operation) {
  const OUString name = OUString::createFromAscii(styleProperty(operation));
  if (states->getPropertyState(name) == beans::PropertyState_AMBIGUOUS_VALUE)
    return "mixed";
  if (operation == 12) return alignName(property<table::CellHoriJustify>(props, name));
  return colorName(property<sal_Int32>(props, name), operation == 10 ? "auto" : "none");
}

// The closed spelling of a requested value, or a refusal before any mutation.
uno::Any styleValue(int operation, const std::string &value) {
  if (operation == 12) {
    for (const auto &entry : horizontalAligns())
      if (value == entry.first) return uno::Any(entry.second);
    throw Refusal("INVALID_ARGUMENT", "unknown horizontal alignment");
  }
  if (value == (operation == 10 ? "auto" : "none")) return uno::Any(kNoColor);
  if (value.size() != 7 || value[0] != '#')
    throw Refusal("INVALID_ARGUMENT", "a colour is #rrggbb");
  sal_Int32 rgb = 0;
  for (std::size_t index = 1; index < 7; ++index) {
    const char c = value[index];
    const int digit = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : -1;
    if (digit < 0) throw Refusal("INVALID_ARGUMENT", "a colour is #rrggbb in lower case");
    rgb = rgb * 16 + digit;
  }
  return uno::Any(rgb);
}
#endif

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
#ifdef OXSDK_ODS_STYLE
  const bool styling = operation >= 10;
  const auto before = operation == 6 || styling ? std::string() : rangeFormat(props, states, operation);
#else
  const auto before = operation == 6 ? std::string() : rangeFormat(props, states, operation);
#endif
  bool changed = false;
#ifdef OXSDK_ODS_STYLE
  if (styling) {
    const std::string wanted = request.get<std::string>("value", "");
    const uno::Any value = styleValue(operation, wanted);
    if (!refusal.empty()) throw Refusal(refusal.c_str(), "the entire range is refused before mutation");
    if (rangeStyle(props, states, operation) != wanted) {
      Reference<beans::XMultiPropertySet> multi(range, uno::UNO_QUERY_THROW);
      mutationAttempted = true;
      multi->setPropertyValues({OUString::createFromAscii(styleProperty(operation))}, {value});
      if (rangeStyle(props, states, operation) != wanted)
        throw Refusal("RANGE_POSTCONDITION_FAILED", "native range style did not reach the requested state");
      changed = true;
    }
  }
  if (operation != 6 && !styling) {
#else
  if (operation != 6) {
#endif
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
#ifdef OXSDK_ODS_STYLE
  result.put("textColor", rangeStyle(props, states, 10));
  result.put("backColor", rangeStyle(props, states, 11));
  result.put("horizontalAlign", rangeStyle(props, states, 12));
#endif
  result.put("changed", changed);
  return result;
}
#endif

ptree access(LibreOfficeKitDocument *doc, int part, int column, int row, int operation,
             const char *text, int textLength, int enabled, bool &mutationAttempted) {
  SolarMutexGuard guard;
  constexpr int maxOperation =
#ifdef OXSDK_ODS_STYLE
      12;
#elif defined(OXSDK_ODS_RANGE)
      9;
#else
      5;
#endif
  if (part < 0 || column < 0 || row < 0 || operation < 0 || operation > maxOperation)
    throw Refusal("INVALID_ARGUMENT", "invalid cell address or operation");
  if (!doc)
    throw Refusal("CELL_MODEL_UNAVAILABLE", "no LOK document");
  auto *shell = SfxLokHelper::getViewOfId(doc->pClass->getView(doc));
  if (!shell)
    throw Refusal("CELL_MODEL_UNAVAILABLE", "no document view for this handle");
  auto model = shell->GetCurrentDocument();
  if (!model.is())
    throw Refusal("CELL_MODEL_UNAVAILABLE", "document view has no model");
  Reference<sheet::XSpreadsheetDocument> document(model, uno::UNO_QUERY);
  if (!document.is())
    throw Refusal("DOCUMENT_TYPE_REFUSED", "cell editing requires a spreadsheet");
  Reference<container::XIndexAccess> sheets(document->getSheets(), uno::UNO_QUERY_THROW);
  if (part >= sheets->getCount())
    throw Refusal("INVALID_ARGUMENT", "sheet index is out of range");
  Reference<sheet::XSpreadsheet> sheet(sheets->getByIndex(part), uno::UNO_QUERY_THROW);
  Reference<beans::XPropertySet> sheetProperties(sheet, uno::UNO_QUERY_THROW);
  if (!property<bool>(sheetProperties, u"IsVisible"_ustr))
    throw Refusal("PART_HIDDEN", "hidden sheets cannot be edited");
  Reference<table::XColumnRowRange> dimensions(sheet, uno::UNO_QUERY_THROW);
  const int columns = dimensions->getColumns()->getCount();
  const int rows = dimensions->getRows()->getCount();
#ifdef OXSDK_ODS_RANGE
  if (operation >= 6)
    return accessRange(sheet, model, part, column, row, columns, rows, operation,
                       text, textLength, enabled, mutationAttempted);
#endif
  Reference<sheet::XSpreadsheetView> view(model->getCurrentController(), uno::UNO_QUERY_THROW);
  view->setActiveSheet(sheet);
  // Match the page's fixed 1 CSS px = 15 twips; screen-aligned row heights
  // accumulate rounding and cannot be reconstructed from UNO millimetres.
  doc->pClass->setClientZoom(doc, 256, 256, 3840, 3840);
  if (operation == 5) {
    const auto headers = commandValues(doc, ".uno:ViewRowColumnHeaders?x="
        + std::to_string(column) + "&y=" + std::to_string(row) + "&width=60&height=60");
    column = headerIndex(headers.get_child("columns"), column, true);
    row = headerIndex(headers.get_child("rows"), row, false);
  }
  if (column >= columns || row >= rows)
    throw Refusal("INVALID_ARGUMENT", "cell index is out of range");

  auto range = sheet->getCellRangeByPosition(column, row, column, row);
  auto cursor = sheet->createCursorByRange(
      Reference<sheet::XSheetCellRange>(range, uno::UNO_QUERY_THROW));
  cursor->collapseToMergedArea();
  Reference<sheet::XCellRangeAddressable> addressed(cursor, uno::UNO_QUERY_THROW);
  const auto address = addressed->getRangeAddress();
  const auto cell = sheet->getCellByPosition(address.StartColumn, address.StartRow);
  Reference<beans::XPropertySet> props(cell, uno::UNO_QUERY_THROW);
  Reference<beans::XPropertySet> rangeProps(cursor, uno::UNO_QUERY_THROW);
  Reference<util::XProtectable> protection(sheet, uno::UNO_QUERY_THROW);
  const auto cellProtection = property<util::CellProtection>(props, u"CellProtection"_ustr);
  Reference<frame::XStorable> storable(model, uno::UNO_QUERY_THROW);
  const bool writable = !storable->isReadonly()
      && !(protection->isProtected() && cellProtection.IsLocked);

  Reference<view::XSelectionSupplier> selection(model->getCurrentController(), uno::UNO_QUERY_THROW);
  selection->select(uno::Any(cell));
  const auto geometry = commandValues(doc, ".uno:CellCursor").get<std::string>("commandValues");
  int x, y, width, height, selectedColumn, selectedRow;
  char comma;
  std::istringstream rectangle(geometry);
  if (!(rectangle >> x >> comma >> y >> comma >> width >> comma >> height
          >> comma >> selectedColumn >> comma >> selectedRow)
      || selectedColumn != address.StartColumn || selectedRow != address.StartRow
      || width <= 0 || height <= 0)
    throw Refusal("CELL_GEOMETRY_UNAVAILABLE", "LOK cursor does not match the selected cell");

  const OUString before = cell->getFormula();
  bool changed = false;
  if (operation >= 1 && operation <= 4) {
    if (!writable)
      throw Refusal("READ_ONLY", "this cell is protected or the document is read-only");
    if (operation == 1) {
      if (textLength < 0 || (textLength > 0 && !text))
        throw Refusal("INVALID_ARGUMENT", "invalid cell text buffer");
      const OUString input = OUString::fromUtf8(std::string_view(text ? text : "", textLength));
      if (input.getLength() > 32767)
        throw Refusal("CELL_TEXT_TOO_LONG", "cell input exceeds 32767 UTF-16 code units");
      if (before != input) {
        mutationAttempted = true;
        cell->setFormula(input);
        changed = true;
      }
    } else {
      const bool on = enabled != 0;
#ifdef OXSDK_ODS_UNDO
      // SPEC-P-calc-undo 4.2 E3.  One setPropertyValue per script was one undo
      // action each: a single-cell bold took three undos (NU, native-01).  The
      // properties that differ are written in ONE setPropertyValues, the way
      // op 7 and 8 write a range, so the cell's bold or italic is one undo.
      if (operation == 2 || operation == 3) {
        const auto weight = on ? awt::FontWeight::BOLD : awt::FontWeight::NORMAL;
        const auto slant = on ? awt::FontSlant_ITALIC : awt::FontSlant_NONE;
        std::vector<OUString> names;
        std::vector<uno::Any> values;
        for (const auto &key : operation == 2
                 ? std::vector<OUString>{u"CharWeight"_ustr, u"CharWeightAsian"_ustr, u"CharWeightComplex"_ustr}
                 : std::vector<OUString>{u"CharPosture"_ustr, u"CharPostureAsian"_ustr, u"CharPostureComplex"_ustr}) {
          const bool differs = operation == 2 ? property<float>(props, key) != weight
                                              : property<awt::FontSlant>(props, key) != slant;
          if (differs) {
            names.push_back(key);
            values.push_back(operation == 2 ? uno::Any(weight) : uno::Any(slant));
          }
        }
        if (!names.empty()) {
          mutationAttempted = changed = true;
          Reference<beans::XMultiPropertySet> multi(cursor, uno::UNO_QUERY_THROW);
          multi->setPropertyValues(uno::Sequence<OUString>(names.data(), names.size()),
                                   uno::Sequence<uno::Any>(values.data(), values.size()));
        }
      } else
#endif
      if (operation == 2) {
        const float value = on ? awt::FontWeight::BOLD : awt::FontWeight::NORMAL;
        for (const auto &key : {u"CharWeight"_ustr, u"CharWeightAsian"_ustr, u"CharWeightComplex"_ustr}) {
          if (property<float>(props, key) != value) {
            mutationAttempted = changed = true;
            rangeProps->setPropertyValue(key, uno::Any(value));
          }
        }
      } else if (operation == 3) {
        const auto value = on ? awt::FontSlant_ITALIC : awt::FontSlant_NONE;
        for (const auto &key : {u"CharPosture"_ustr, u"CharPostureAsian"_ustr, u"CharPostureComplex"_ustr}) {
          if (property<awt::FontSlant>(props, key) != value) {
            mutationAttempted = changed = true;
            rangeProps->setPropertyValue(key, uno::Any(value));
          }
        }
      } else {
        const sal_Int16 value = on ? awt::FontUnderline::SINGLE : awt::FontUnderline::NONE;
        changed = property<sal_Int16>(props, u"CharUnderline"_ustr) != value;
        if (changed) {
          mutationAttempted = true;
          rangeProps->setPropertyValue(u"CharUnderline"_ustr, uno::Any(value));
        }
      }
    }
  }

  ptree out;
  out.put("ok", true);
  out.put("part", address.Sheet);
  out.put("column", address.StartColumn);
  out.put("row", address.StartRow);
  out.put("endColumn", address.EndColumn);
  out.put("endRow", address.EndRow);
  out.put("formula", cell->getFormula().toUtf8().getStr());
  OUString editable = cell->getFormula();
  if (cell->getType() == table::CellContentType_TEXT
      && (editable.startsWith("=") || editable.startsWith("+") || editable.startsWith("-")))
    editable = "'" + editable;
  out.put("input", editable.toUtf8().getStr());
  Reference<text::XTextRange> cellText(cell, uno::UNO_QUERY_THROW);
  out.put("text", cellText->getString().toUtf8().getStr());
  out.put("value", cell->getValue());
  out.put("cellType", static_cast<int>(cell->getType()));
  out.put("writable", writable);
  out.put("changed", changed);
  out.put("xTwips", x);
  out.put("yTwips", y);
  out.put("widthTwips", width);
  out.put("heightTwips", height);
  out.put("bold", property<float>(props, u"CharWeight"_ustr) >= awt::FontWeight::BOLD);
  out.put("boldAsian", property<float>(props, u"CharWeightAsian"_ustr) >= awt::FontWeight::BOLD);
  out.put("boldComplex", property<float>(props, u"CharWeightComplex"_ustr) >= awt::FontWeight::BOLD);
  out.put("italic", property<awt::FontSlant>(props, u"CharPosture"_ustr) != awt::FontSlant_NONE);
  out.put("italicAsian", property<awt::FontSlant>(props, u"CharPostureAsian"_ustr) != awt::FontSlant_NONE);
  out.put("italicComplex", property<awt::FontSlant>(props, u"CharPostureComplex"_ustr) != awt::FontSlant_NONE);
  out.put("underline", property<sal_Int16>(props, u"CharUnderline"_ustr) != awt::FontUnderline::NONE);
#ifdef OXSDK_ODS_STYLE
  out.put("textColor", colorName(property<sal_Int32>(props, u"CharColor"_ustr), "auto"));
  out.put("backColor", colorName(property<sal_Int32>(props, u"CellBackColor"_ustr), "none"));
  out.put("horizontalAlign", alignName(property<table::CellHoriJustify>(props, u"HoriJustify"_ustr)));
#endif
  return out;
}
} // namespace

extern "C" char *oxsdk_calc_cell_model(void *lokDocument, int part, int column,
                                      int row, int operation, const char *text,
                                      int textLength, int enabled) {
  ptree result;
  bool mutationAttempted = false;
  try {
    result = access(static_cast<LibreOfficeKitDocument *>(lokDocument), part, column,
                    row, operation, text, textLength, enabled, mutationAttempted);
  } catch (const Refusal &e) {
    result.put("ok", false); result.put("code", e.code); result.put("message", e.what());
  } catch (const com::sun::star::uno::Exception &e) {
    result.put("ok", false); result.put("code", "CELL_MODEL_ERROR");
    result.put("message", e.Message.toUtf8().getStr());
  } catch (const std::exception &e) {
    result.put("ok", false); result.put("code", "CELL_MODEL_ERROR"); result.put("message", e.what());
  }
  result.put("mutationAttempted", mutationAttempted);
  std::ostringstream stream;
  boost::property_tree::write_json(stream, result, false);
  const auto json = stream.str();
  char *copy = static_cast<char *>(std::malloc(json.size() + 1));
  if (copy) std::memcpy(copy, json.c_str(), json.size() + 1);
  return copy;
}
