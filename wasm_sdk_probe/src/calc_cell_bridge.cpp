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
#include <com/sun/star/container/XIndexAccess.hpp>
#include <com/sun/star/frame/XModel.hpp>
#include <com/sun/star/frame/XStorable.hpp>
#include <com/sun/star/util/CellProtection.hpp>
#include <com/sun/star/sheet/XCellRangeAddressable.hpp>
#include <com/sun/star/table/XColumnRowRange.hpp>
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
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <stdexcept>

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

ptree access(LibreOfficeKitDocument *doc, int part, int column, int row, int operation,
             const char *text, int textLength, int enabled, bool &mutationAttempted) {
  SolarMutexGuard guard;
  if (part < 0 || column < 0 || row < 0 || operation < 0 || operation > 5)
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
