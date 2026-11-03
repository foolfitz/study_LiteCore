// Microsoft formats, native measurement M0 (specs/SPEC-P-ms-formats.md, draft 2026-11-03): one file through
// LibreOfficeKit on the native 26.8 core (build-native-26-8), the API the WASM engine uses.
//
//   msformat-native PROGRAM_DIR PROFILE_URL INPUT_PATH OUT_DIR FORMATS
//
// Loads INPUT_PATH, reports what type detection chose (the model's FilterName), the LOK document type, the part
// count and a content dump; saves the document in each comma-separated LOK format (saveAs with that format, as
// the engine's save does); then loads every output again in the same process and dumps it the same way, so a
// round trip is compared inside one build.  A format written `own.EXT` is saved instead through
// XStorable::storeToURL with the filter the document was LOADED with (what `.uno:Save` keeps, Collabora's save), to
// saved-own.EXT -- against `EXT`, which LOK's saveAs maps to its own filter for that suffix.  Prints one JSON object on stdout.  Observations, not verdicts: the
// comparison is the driver's (tools/run_msformat_native.py).
//
// The content dump is a text file per document in OUT_DIR:
//   text documents  -- the body walked in order: each paragraph's string, each table's cells by name;
//   spreadsheets    -- per sheet, its name, then every non-empty cell of the used area as `A1<TAB>formula`
//                      (XCell::getFormula: the formula, or the value, or the string), capped at 200000 cells.
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <com/sun/star/beans/PropertyValue.hpp>
#include <com/sun/star/container/XEnumeration.hpp>
#include <com/sun/star/container/XEnumerationAccess.hpp>
#include <com/sun/star/container/XIndexAccess.hpp>
#include <com/sun/star/container/XNamed.hpp>
#include <com/sun/star/frame/XModel.hpp>
#include <com/sun/star/frame/XStorable.hpp>
#include <com/sun/star/lang/XServiceInfo.hpp>
#include <com/sun/star/sheet/XCellRangeAddressable.hpp>
#include <com/sun/star/sheet/XSheetCellCursor.hpp>
#include <com/sun/star/sheet/XSpreadsheet.hpp>
#include <com/sun/star/sheet/XSpreadsheetDocument.hpp>
#include <com/sun/star/sheet/XUsedAreaCursor.hpp>
#include <com/sun/star/table/XCell.hpp>
#include <com/sun/star/text/XText.hpp>
#include <com/sun/star/text/XTextDocument.hpp>
#include <com/sun/star/text/XTextRange.hpp>
#include <com/sun/star/text/XTextTable.hpp>
#include <sfx2/lokhelper.hxx>
#include <sfx2/viewsh.hxx>
#include <vcl/svapp.hxx>

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>

#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <unistd.h>
#include <vector>

using namespace com::sun::star;
using boost::property_tree::ptree;
using uno::Reference;
using uno::UNO_QUERY;
using uno::UNO_QUERY_THROW;

namespace {

double since(std::chrono::steady_clock::time_point start) {
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
}

std::string utf8(const OUString &s) { return OUStringToOString(s, RTL_TEXTENCODING_UTF8).getStr(); }

std::string columnName(sal_Int32 column) {
  std::string name;
  for (++column; column > 0; column = (column - 1) / 26)
    name.insert(name.begin(), static_cast<char>('A' + (column - 1) % 26));
  return name;
}

Reference<frame::XModel> modelOf(LibreOfficeKitDocument *doc) {
  auto *shell = SfxLokHelper::getViewOfId(doc->pClass->getView(doc));
  return shell ? shell->GetCurrentDocument() : Reference<frame::XModel>();
}

std::string filterOf(const Reference<frame::XModel> &model) {
  for (const auto &arg : model->getArgs())
    if (arg.Name == "FilterName") {
      OUString name;
      arg.Value >>= name;
      return utf8(name);
    }
  return "";
}

void dumpText(const Reference<text::XTextDocument> &document, std::ostream &out, ptree &facts) {
  Reference<container::XEnumerationAccess> body(document->getText(), UNO_QUERY_THROW);
  auto paragraphs = body->createEnumeration();
  int paragraphCount = 0, tableCount = 0;
  while (paragraphs->hasMoreElements()) {
    Reference<lang::XServiceInfo> info(paragraphs->nextElement(), UNO_QUERY);
    if (!info.is()) continue;
    if (info->supportsService("com.sun.star.text.TextTable")) {
      Reference<text::XTextTable> table(info, UNO_QUERY_THROW);
      ++tableCount;
      out << "[table " << tableCount << "]\n";
      for (const auto &cellName : table->getCellNames()) {
        Reference<text::XText> cell(table->getCellByName(cellName), UNO_QUERY);
        out << utf8(cellName) << '\t' << (cell.is() ? utf8(cell->getString()) : std::string()) << '\n';
      }
    } else {
      Reference<text::XTextRange> paragraph(info, UNO_QUERY);
      ++paragraphCount;
      out << (paragraph.is() ? utf8(paragraph->getString()) : std::string()) << '\n';
    }
  }
  facts.put("paragraphs", paragraphCount);
  facts.put("tables", tableCount);
}

void dumpSheets(const Reference<sheet::XSpreadsheetDocument> &document, std::ostream &out, ptree &facts) {
  Reference<container::XIndexAccess> sheets(document->getSheets(), UNO_QUERY_THROW);
  long cells = 0;
  bool capped = false;
  ptree names;
  for (sal_Int32 i = 0; i < sheets->getCount(); ++i) {
    Reference<sheet::XSpreadsheet> sheet(sheets->getByIndex(i), UNO_QUERY_THROW);
    Reference<container::XNamed> named(sheet, UNO_QUERY_THROW);
    ptree name;
    name.put("", utf8(named->getName()));
    names.push_back({"", name});
    out << "[sheet " << utf8(named->getName()) << "]\n";
    Reference<sheet::XSheetCellCursor> cursor = sheet->createCursor();
    Reference<sheet::XUsedAreaCursor> used(cursor, UNO_QUERY_THROW);
    used->gotoStartOfUsedArea(false);
    used->gotoEndOfUsedArea(true);
    Reference<sheet::XCellRangeAddressable> address(cursor, UNO_QUERY_THROW);
    const auto area = address->getRangeAddress();
    for (sal_Int32 row = area.StartRow; row <= area.EndRow && !capped; ++row)
      for (sal_Int32 column = area.StartColumn; column <= area.EndColumn; ++column) {
        auto cell = sheet->getCellByPosition(column, row);
        const OUString formula = cell->getFormula();
        if (formula.isEmpty()) continue;
        out << columnName(column) << row + 1 << '\t' << utf8(formula) << '\n';
        if (++cells >= 200000) { capped = true; break; }
      }
  }
  facts.add_child("sheetNames", names);
  facts.put("cells", cells);
  facts.put("capped", capped);
}

// Everything about one loaded document; `label` names its dump file.
ptree describe(LibreOfficeKitDocument *doc, const std::string &dumpPath) {
  ptree facts;
  facts.put("documentType", doc->pClass->getDocumentType(doc));
  doc->pClass->initializeForRendering(doc, nullptr);
  facts.put("parts", doc->pClass->getParts(doc));
  long width = 0, height = 0;
  doc->pClass->getDocumentSize(doc, &width, &height);
  facts.put("widthTwips", width);
  facts.put("heightTwips", height);
  try {
    SolarMutexGuard guard;
    auto model = modelOf(doc);
    if (!model.is()) {
      facts.put("modelError", "no model for the LOK view");
      return facts;
    }
    facts.put("filter", filterOf(model));
    std::ofstream out(dumpPath, std::ios::binary | std::ios::trunc);
    if (Reference<text::XTextDocument> text{model, UNO_QUERY}; text.is())
      dumpText(text, out, facts);
    else if (Reference<sheet::XSpreadsheetDocument> sheets{model, UNO_QUERY}; sheets.is())
      dumpSheets(sheets, out, facts);
    facts.put("dump", dumpPath);
  } catch (const uno::Exception &e) {
    facts.put("modelError", utf8(e.Message));
  }
  return facts;
}

bool storeOwn(LibreOfficeKitDocument *doc, const std::string &url, ptree &save) {
  SolarMutexGuard guard;
  try {
    auto model = modelOf(doc);
    if (!model.is()) {
      save.put("error", "no model for the LOK view");
      return false;
    }
    const std::string filter = filterOf(model);
    save.put("filter", filter);
    Reference<frame::XStorable> storable(model, UNO_QUERY_THROW);
    beans::PropertyValue name;
    name.Name = "FilterName";
    name.Value <<= OUString::fromUtf8(filter);
    beans::PropertyValue overwrite;
    overwrite.Name = "Overwrite";
    overwrite.Value <<= true;
    storable->storeToURL(OUString::fromUtf8(url), {name, overwrite});
    return true;
  } catch (const uno::Exception &e) {
    save.put("error", utf8(e.Message));
    return false;
  }
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 6) {
    std::cerr << "usage: msformat-native PROGRAM_DIR PROFILE_URL INPUT_PATH OUT_DIR FORMATS\n";
    return 2;
  }
  const std::string outDir = argv[4];
  std::vector<std::string> formats;
  {
    std::stringstream list(argv[5]);
    for (std::string f; std::getline(list, f, ',');)
      if (!f.empty()) formats.push_back(f);
  }
  ptree report;
  auto started = std::chrono::steady_clock::now();
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  report.put("initMs", since(started));
  if (!kit) {
    report.put("error", "lok_init_2 failed");
    boost::property_tree::write_json(std::cout, report);
    _exit(3);
  }
  const std::string inputUrl = std::string("file://") + argv[3];
  started = std::chrono::steady_clock::now();
  LibreOfficeKitDocument *doc = kit->pClass->documentLoad(kit, inputUrl.c_str());
  ptree source;
  source.put("loadMs", since(started));
  source.put("ok", doc != nullptr);
  if (!doc) {
    char *error = kit->pClass->getError(kit);
    source.put("error", error ? error : "");
    report.add_child("source", source);
    boost::property_tree::write_json(std::cout, report);
    _exit(0);
  }
  for (auto &[k, v] : describe(doc, outDir + "/source.dump.txt")) source.add_child(k, v);
  report.add_child("source", source);

  ptree saves;
  std::vector<std::pair<std::string, std::string>> outputs;
  for (const auto &format : formats) {
    const bool own = format.rfind("own.", 0) == 0;
    const std::string path = own ? outDir + "/saved-" + format : outDir + "/saved." + format;
    ptree save;
    save.put("format", format);
    started = std::chrono::steady_clock::now();
    const bool ok = own ? storeOwn(doc, "file://" + path, save)
                        : doc->pClass->saveAs(doc, ("file://" + path).c_str(), format.c_str(), nullptr);
    save.put("saveMs", since(started));
    save.put("ok", ok);
    if (!ok) {
      if (!own) {
        char *error = kit->pClass->getError(kit);
        save.put("error", error ? error : "");
      }
    } else {
      std::ifstream in(path, std::ios::binary | std::ios::ate);
      save.put("bytes", static_cast<long>(in.tellg()));
      outputs.emplace_back(format, path);
    }
    saves.push_back({"", save});
  }
  report.add_child("saves", saves);
  doc->pClass->destroy(doc);

  ptree reloads;
  for (const auto &[format, path] : outputs) {
    ptree reload;
    reload.put("format", format);
    started = std::chrono::steady_clock::now();
    LibreOfficeKitDocument *again = kit->pClass->documentLoad(kit, ("file://" + path).c_str());
    reload.put("loadMs", since(started));
    reload.put("ok", again != nullptr);
    if (again) {
      const std::string base = path.substr(path.rfind('/') + 1);
      for (auto &[k, v] : describe(again, outDir + "/" + base + ".dump.txt")) reload.add_child(k, v);
      again->pClass->destroy(again);
    } else {
      char *error = kit->pClass->getError(kit);
      reload.put("error", error ? error : "");
    }
    reloads.push_back({"", reload});
  }
  report.add_child("reloads", reloads);
  boost::property_tree::write_json(std::cout, report);
  std::cout.flush();
  _exit(0); // kit->destroy can hang on a native core; the harness only needs its report
}
