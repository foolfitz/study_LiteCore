// Finding 078 -- what does NATIVE LibreOffice write when bold is applied to a
// selection that covers a whole paragraph?
//
// The WASM engine expresses it as PARAGRAPH-level formatting: the fully
// selected paragraph comes back with a paragraph automatic style carrying
// fo:font-weight="bold", not a <text:span>. A partially selected paragraph
// comes back as a span. The extent is right either way -- measured, all four
// inline formats, findings/evidence/f078-inline-format-on-a-selection/ -- so
// the open question is about SHAPE, and shape is only answerable against the
// same core doing the same thing outside the browser.
//
// It is a blocker rather than a curiosity because the manifest is about to
// grant the gesture, and a manifest that grants it signs for what it produces.
// Divergence from native is a limitation to name; a different EXTENT would be a
// defect and would stop the grant.
//
// Two arms, one mechanism. `.uno:ExecuteSearch` leaves its hit SELECTED, so
// searching a paragraph's full text selects exactly that paragraph, and
// searching part of it selects part. The control is what makes the answer
// readable: if both arms produce the same shape, the shape is not about
// coverage at all.
//
// Usage: f078-native-range-format INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>

#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

namespace {

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

std::string jsonEscape(const char *value) {
  std::string out;
  for (const char *p = value ? value : ""; *p; ++p) {
    switch (*p) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': out += "\\r"; break;
    case '\t': out += "\\t"; break;
    default:
      if (static_cast<unsigned char>(*p) < 0x20) {
        char buffer[8];
        std::snprintf(buffer, sizeof buffer, "\\u%04x", *p);
        out += buffer;
      } else {
        out += *p;
      }
    }
  }
  return out;
}

// Selects the hit, which is the whole point: ExecuteSearch leaves its match
// selected, so the search string IS the selection.
void selectByText(LibreOfficeKitDocument *document, const std::string &needle) {
  const std::string arguments =
      "{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"" +
      needle +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(900);
}

void arm(LibreOfficeKitDocument *document, const std::string &outDir,
         const std::string &label, const std::string &needle) {
  selectByText(document, needle);
  const int selectionType = document->pClass->getSelectionType(document);
  char *used = nullptr;
  char *selected =
      document->pClass->getTextSelection(document, "text/plain;charset=utf-8",
                                         &used);
  document->pClass->postUnoCommand(document, ".uno:Bold", nullptr, true);
  drain(900);
  const std::string url = "file://" + outDir + "/native-" + label + ".odt";
  document->pClass->saveAs(document, url.c_str(), "odt", nullptr);
  drain(900);
  std::cout << "{\"arm\":\"" << label << "\",\"needle\":\"" << needle
            << "\",\"selectionType\":" << selectionType
            << ",\"selectedText\":\"" << jsonEscape(selected)
            << "\",\"saved\":\"" << url << "\"}" << std::endl;
  if (selected) std::free(selected);
  if (used) std::free(used);
  // Undo, so the second arm starts from the document the first one found.
  document->pClass->postUnoCommand(document, ".uno:Undo", nullptr, true);
  drain(700);
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 5) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    const char *error =
        kit->pClass->getError ? kit->pClass->getError(kit) : nullptr;
    std::cerr << (error ? error : "documentLoad returned null") << '\n';
    kit->pClass->destroy(kit);
    return 3;
  }
  document->pClass->initializeForRendering(document, "{}");
  drain(400);

  // THE WHOLE PARAGRAPH, then PART of one. The second is the control: if both
  // come back the same shape, coverage is not what decides the shape.
  arm(document, argv[4], "whole-paragraph", "E1-LC-END");
  arm(document, argv[4], "part-of-paragraph", "LC-ISOLATED");

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
