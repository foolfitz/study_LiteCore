// SPEC-P-demo-batch-3 N2: where does the caret end up after an alignment and the read the engine does to verify it?
// Three routes on the same caret, each on a fresh document; each inserts X afterwards and saves, so the document says where the
// caret was.  truth: dispatch only.  coordinates: the shipped restore (SelectText, then RESET/START/RESET at the pre-dispatch caret
// rectangle).  sel: extend one character, read, move back from the point.  Observations, not verdicts.
//   n2-native-writer-align-caret INSTALL_PATH PROFILE_URL CARET_DOC_URL BLANK_DOC_URL OUTDIR
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
namespace {
std::mutex gLock;
std::string gCursor;
void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }
void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR && payload) { std::lock_guard<std::mutex> g(gLock); gCursor = payload; }
}
std::string cursor() { std::lock_guard<std::mutex> g(gLock); return gCursor; }
std::string escape(const char *value) {
  std::string out;
  for (const char *p = value ? value : ""; *p; ++p) {
    if (*p == '"' || *p == '\\') { out += '\\'; out += *p; }
    else if (*p == '\n') out += "\\n"; else if (*p == '\r') out += "\\r"; else if (*p == '\t') out += "\\t";
    else if (static_cast<unsigned char>(*p) < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", *p); out += b; }
    else out += *p;
  }
  return out;
}
void uno(LibreOfficeKitDocument *d, const char *command, const char *args = nullptr, bool notify = true, int ms = 220) {
  d->pClass->postUnoCommand(d, command, args, notify);
  drain(ms);
}
bool rectOf(const std::string &payload, int &x, int &y, int &h) {
  // {"viewId":"0","rectangle":"x, y, w, h",...} or the bare rectangle
  const auto at = payload.find("\"rectangle\":\"");
  const char *text = payload.c_str() + (at == std::string::npos ? 0 : at + 13);
  int w = 0;
  return std::sscanf(text, "%d, %d, %d, %d", &x, &y, &w, &h) == 4;
}
std::string html(LibreOfficeKitDocument *d) {
  char *used = nullptr;
  char *raw = d->pClass->getTextSelection(d, "text/html", &used);
  std::string out = raw ? raw : "";
  std::free(raw); std::free(used);
  const auto body = out.find("<body");
  return body == std::string::npos ? out : out.substr(body);
}
struct Place { const char *name, *needle; std::vector<const char *> steps; };
LibreOfficeKitDocument *gOpen = nullptr;
void run(LibreOfficeKit *kit, const std::string &url, const std::string &out, const Place &place, const char *route, const char *command, int &counter) {
  auto *d = kit->pClass->documentLoad(kit, url.c_str());
  if (!d) { std::cerr << "load failed\n"; std::exit(3); }
  d->pClass->initializeForRendering(d, "{}");
  d->pClass->registerCallback(d, onCallback, nullptr);
  drain(350);
  uno(d, ".uno:GoToStartOfDoc");
  if (place.needle && *place.needle) {
    const std::string a = std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"") + place.needle +
        "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
    uno(d, ".uno:ExecuteSearch", a.c_str(), false, 450);
  }
  for (const char *step : place.steps) uno(d, step);
  drain(250);
  const std::string caret = cursor();
  uno(d, command);
  std::string read, how = "none";
  int typeAtRead = -1;
  if (!std::strcmp(route, "coordinates")) {
    uno(d, ".uno:SelectText");
    typeAtRead = d->pClass->getSelectionType(d);
    read = html(d);
    int x = 0, y = 0, h = 0;
    if (rectOf(caret, x, y, h)) {
      y += h / 2;
      d->pClass->setTextSelection(d, LOK_SETTEXTSELECTION_RESET, x, y);
      d->pClass->setTextSelection(d, LOK_SETTEXTSELECTION_START, x, y);
      d->pClass->setTextSelection(d, LOK_SETTEXTSELECTION_RESET, x, y);
      drain(220);
    }
  } else if (!std::strcmp(route, "sel")) {
    uno(d, ".uno:CharLeftSel");
    typeAtRead = d->pClass->getSelectionType(d);
    how = "left";
    if (typeAtRead == LOK_SELTYPE_TEXT) {
      read = html(d);
      uno(d, ".uno:GoRight");
    } else {
      uno(d, ".uno:CharRightSel");
      typeAtRead = d->pClass->getSelectionType(d);
      how = "right";
      if (typeAtRead == LOK_SELTYPE_TEXT) {
        read = html(d);
        uno(d, ".uno:GoLeft");
      } else how = "blank";
    }
  }
  const int typeAfter = d->pClass->getSelectionType(d);
  uno(d, ".uno:InsertText", "{\"Text\":{\"type\":\"string\",\"value\":\"X\"}}");
  const std::string saved = "file://" + out + "/n2-" + std::to_string(++counter) + ".odt";
  d->pClass->saveAs(d, saved.c_str(), "odt", nullptr);
  drain(200);
  std::cout << "{\"place\":\"" << place.name << "\",\"route\":\"" << route << "\",\"command\":\"" << command << "\",\"how\":\"" << how
            << "\",\"typeAtRead\":" << typeAtRead << ",\"typeAfter\":" << typeAfter << ",\"caretBefore\":\"" << escape(caret.c_str())
            << "\",\"saved\":\"" << saved << "\",\"html\":\"" << escape(read.c_str()) << "\"}" << std::endl;
  d->pClass->registerCallback(d, nullptr, nullptr);
  d->pClass->destroy(d);
  drain(150);
}
}  // namespace
int main(int argc, char **argv) {
  if (argc < 6) return 64;
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 2;
  const std::vector<Place> places{
      {"doc-start", "", {}},
      {"first-para-mid", "ALPHA", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight", ".uno:GoRight"}},
      {"para-start", "BRAVO", {".uno:GoLeft"}},
      {"para-mid", "BRAVO", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}},
      {"para-end", "BRAVO", {".uno:GoToEndOfPara"}},
      {"heading-mid", "CHARLIE", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}},
      {"list-start", "DELTA", {".uno:GoLeft"}},
      {"list-mid", "DELTA", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}},
      {"wrapped-mid", "word060", {".uno:GoLeft"}},
      {"empty-mid", "GOLF", {".uno:GoLeft", ".uno:GoUp"}},
      {"empty-last", "GOLF", {".uno:GoToEndOfDoc"}},
  };
  int counter = argc > 6 ? std::atoi(argv[6]) : 0;
  const char *part = argc > 7 ? argv[7] : "align";
  if (!std::strcmp(part, "align")) {
    for (const char *command : {".uno:RightPara", ".uno:CenterPara", ".uno:LeftPara"})
      for (const auto &place : places)
        for (const char *route : {"truth", "coordinates", "sel"})
          run(kit, argv[3], argv[5], place, route, command, counter);
  } else if (!std::strcmp(part, "blank")) {
    const Place blank{"blank-doc", "", {}};
    for (const char *route : {"truth", "coordinates", "sel"})
      run(kit, argv[4], argv[5], blank, route, ".uno:CenterPara", counter);
    // Pressed twice: the second press changes nothing.
    for (const char *route : {"truth", "sel"}) {
      const Place twice{"blank-doc-second-press", "", {".uno:CenterPara"}};
      run(kit, argv[4], argv[5], twice, route, ".uno:CenterPara", counter);
    }
  } else {
    // The shipped paragraph actions on the shipped restore: a neighbour, measured once (not this batch's to change).
    for (const auto &place : places)
      if (!std::strcmp(place.name, "para-mid") || !std::strcmp(place.name, "list-mid") || !std::strcmp(place.name, "wrapped-mid"))
        for (const char *route : {"truth", "coordinates"}) {
          run(kit, argv[3], argv[5], place, route, ".uno:DefaultBullet", counter);
          run(kit, argv[3], argv[5], place, route, ".uno:DefaultNumbering", counter);
        }
  }
  kit->pClass->destroy(kit);
  return 0;
}
