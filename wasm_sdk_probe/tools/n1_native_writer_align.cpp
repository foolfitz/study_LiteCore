// SPEC-P-demo-batch-3 N1: what does native Writer do with the four alignment commands, in the shapes the engine's ordered format
// path will see them?  Each arm: place the selection, dispatch, read the selection type and the HTML the barrier reads
// (.uno:SelectText on a caret, the caller's range otherwise), save, undo.  It emits observations, not verdicts.
//   n1-native-writer-align INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
namespace {
void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }
std::string escape(const char *value) {
  std::string out;
  for (const char *p = value ? value : ""; *p; ++p) {
    if (*p == '"' || *p == '\\') { out += '\\'; out += *p; }
    else if (*p == '\n') out += "\\n";
    else if (*p == '\r') out += "\\r";
    else if (*p == '\t') out += "\\t";
    else if (static_cast<unsigned char>(*p) < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", *p); out += b; }
    else out += *p;
  }
  return out;
}
void uno(LibreOfficeKitDocument *d, const char *command, const char *args = nullptr, bool notify = true, int ms = 350) {
  d->pClass->postUnoCommand(d, command, args, notify);
  drain(ms);
}
void search(LibreOfficeKitDocument *d, const std::string &needle) {
  uno(d, ".uno:GoToStartOfDoc");
  const std::string a = "{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"" + needle +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  uno(d, ".uno:ExecuteSearch", a.c_str(), false, 500);
}
std::string html(LibreOfficeKitDocument *d) {
  char *used = nullptr;
  char *raw = d->pClass->getTextSelection(d, "text/html", &used);
  const std::string out = raw ? raw : "";
  std::free(raw); std::free(used);
  const auto body = out.find("<body");
  return body == std::string::npos ? out : out.substr(body);
}
int counter = 0;
void arm(LibreOfficeKitDocument *d, const std::string &out, const std::string &label, const std::string &needle, const char *place,
         const char *command) {
  search(d, needle);
  for (const char *p = place; p && *p;) {
    const char *end = std::strchr(p, ',');
    const std::string step = end ? std::string(p, end - p) : std::string(p);
    uno(d, step.c_str());
    p = end ? end + 1 : nullptr;
  }
  const int before = d->pClass->getSelectionType(d);
  uno(d, command);
  bool collapsed = before == LOK_SELTYPE_NONE;
  if (collapsed) uno(d, ".uno:SelectText");
  const int type = d->pClass->getSelectionType(d);
  const std::string read = html(d);
  // The engine's v28 fallback: SelectText found nothing on an empty last paragraph.
  std::string fallback;
  if (type == LOK_SELTYPE_NONE) {
    uno(d, ".uno:CharLeftSel");
    fallback = html(d);
  }
  const std::string url = "file://" + out + "/arm-" + std::to_string(++counter) + ".odt";
  d->pClass->saveAs(d, url.c_str(), "odt", nullptr);
  drain(300);
  std::cout << "{\"arm\":\"" << label << "\",\"command\":\"" << command << "\",\"selectionBefore\":" << before
            << ",\"selectionAtRead\":" << type << ",\"saved\":\"" << url << "\",\"html\":\"" << escape(read.c_str()) << "\",\"fallbackHtml\":\""
            << escape(fallback.c_str()) << "\"}" << std::endl;
  uno(d, ".uno:Undo");
}
}  // namespace
int main(int argc, char **argv) {
  if (argc < 5) return 64;
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 2;
  LibreOfficeKitDocument *d = kit->pClass->documentLoad(kit, argv[3]);
  if (!d) return 3;
  d->pClass->initializeForRendering(d, "{}");
  drain(500);
  const char *const commands[] = {".uno:LeftPara", ".uno:CenterPara", ".uno:RightPara", ".uno:JustifyPara"};
  for (const char *c : commands) {
    arm(d, argv[4], "caret-plain", "BRAVO", ".uno:GoRight", c);
    arm(d, argv[4], "range-single", "plain paragraph two", nullptr, c);
    arm(d, argv[4], "range-cross", "BRAVO", ".uno:LineDownSel,.uno:LineDownSel", c);
    arm(d, argv[4], "caret-heading", "CHARLIE", ".uno:GoRight", c);
    arm(d, argv[4], "caret-list", "DELTA", ".uno:GoRight", c);
    arm(d, argv[4], "caret-already-centred", "ECHO", ".uno:GoRight", c);
    arm(d, argv[4], "caret-empty-mid", "ECHO", ".uno:GoRight,.uno:GoDown", c);
    arm(d, argv[4], "caret-empty-last", "FOXTROT", ".uno:GoRight,.uno:GoDown", c);
  }
  d->pClass->destroy(d);
  kit->pClass->destroy(kit);
  return 0;
}
