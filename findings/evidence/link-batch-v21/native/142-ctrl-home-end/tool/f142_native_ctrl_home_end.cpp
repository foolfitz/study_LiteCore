// Finding 142, link batch v21, plan step 1a: what does native Writer do when
// the engine posts Ctrl+Home / Ctrl+End on the KEY path?
//
// Native LibreOfficeKit only (no browser, no WASM). One document per process.
// Starts from k1probe.cpp (review 6) and link_native_extend_signatures.cpp.
//
// KEY SHAPE. Every key is posted exactly as wasm_sdk_probe/src/probe_engine.cpp
// handleEditorAction posts a key-path action (:5740-5743): KEYINPUT then KEYUP,
// charCode 0, keyCode = css::awt::Key code | modifier bits, Mod1 = 0x2000
// (:1094), Shift = 0x1000 (:1091). Select-all is Key::A | Mod1 (:5691), so
// Ctrl+Home is 1028 | 0x2000 and Ctrl+End is 1029 | 0x2000. The user's own
// Backspace/Delete are posted the same way (postMergeKeyEvents, :3757-3762) and
// K1 is Shift+Left (startSelectionBarrierDelete, :4239-4246).
//
// Usage: f142-native INSTALL_PROGRAM_DIR PROFILE_URL DOC_URL SCRIPT OUT_URL
//
// SCRIPT is a comma-separated list of steps, run in order:
//   k<code>[x<n>]      setup key (posted as above), n times; settle after each
//   u<.uno:Cmd>        setup UNO command (postUnoCommand, no notify); settle
//   r<name>            record the last INVALIDATE_VISIBLE_CURSOR rect as a point
//   c<name>            setup click at a point: DOWN+UP, count 1, button 1, as the
//                      engine's place-caret / handleClick post it
//   s<a>:<b>           setup range by the engine's text-handles path (what
//                      oxsdk_editor_select_range uses, editor_api.cpp:219-222;
//                      probe_engine.cpp:5810-5853): RESET+START at a, END at b
//   M<label>=<code>    MEASURED press of one key
//   B<label>=<c1>+<c2> MEASURED: two keys posted back-to-back with no wait
//   K<label>           MEASURED K1 for Backspace (Shift+Left), selection read at
//                      +250 ms and +2250 ms, as k1probe.cpp reads it
//   J<label>           MEASURED K1 for Delete (Shift+Right), same reads
//   L                  locator: Shift+End, read selection; Shift+Home, read
//                      selection (prefix/suffix of the caret's line). Changes
//                      the selection, so it only ever comes last.
//   S                  saveAs(OUT_URL, "fodt")
//
// Output: JSON lines on stdout. A measured press records every callback that
// arrives after its first post (type, payload <= 600 bytes, ms since the post),
// the selection / caret / TEXT_SELECTION / .uno:Undo before and after, and how
// long the window stayed quiet after its last callback.
//
// Build: g++ -std=c++17 -O2 -I<libreoffice-26-8>/include f142_native_ctrl_home_end.cpp -ldl -lpthread -o f142-native

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

namespace {

using Clock = std::chrono::steady_clock;

constexpr int kShift = 0x1000;
constexpr int kLeft = 1026, kRight = 1027, kHome = 1028, kEnd = 1029;

constexpr int kSetupQuietMs = 600;
constexpr int kPreMeasureQuietMs = 1500;
constexpr int kMeasureQuietMs = 2000;
constexpr int kMeasureCapMs = 15000;

const Clock::time_point gEpoch = Clock::now();
std::mutex gMutex;
struct Cb {
  double t;  // ms since process start
  int type;
  std::string payload;
};
std::vector<Cb> gCbs;
std::map<int, std::string> gLast;
Clock::time_point gLastAt = Clock::now();

double msBetween(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}
double nowMs() { return msBetween(gEpoch, Clock::now()); }
void sleepMs(int m) { std::this_thread::sleep_for(std::chrono::milliseconds(m)); }

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  gLastAt = Clock::now();
  std::string p = payload ? payload : "";
  gCbs.push_back({msBetween(gEpoch, gLastAt), type, p});
  gLast[type] = p;
}

std::string esc(const std::string &v) {
  std::string o;
  for (const char c : v) {
    switch (c) {
    case '"': o += "\\\""; break;
    case '\\': o += "\\\\"; break;
    case '\n': o += "\\n"; break;
    case '\r': o += "\\r"; break;
    case '\t': o += "\\t"; break;
    default:
      if (static_cast<unsigned char>(c) < 0x20) {
        char b[8];
        std::snprintf(b, sizeof b, "\\u%04x", static_cast<unsigned char>(c));
        o += b;
      } else {
        o += c;
      }
    }
  }
  return o;
}
std::string utf8Trunc(const std::string &s, size_t n) {
  if (s.size() <= n) return s;
  size_t k = n;
  while (k > 0 && (static_cast<unsigned char>(s[k]) & 0xC0) == 0x80) --k;
  return s.substr(0, k);
}
std::string q(const std::string &s) { return "\"" + esc(s) + "\""; }

// Wait until no callback for quietMs (and at least quietMs in total). Returns
// the ms waited, negated if the cap ended it.
double settle(int quietMs, int capMs) {
  const auto start = Clock::now();
  for (;;) {
    sleepMs(20);
    Clock::time_point last;
    {
      std::lock_guard<std::mutex> lock(gMutex);
      last = gLastAt;
    }
    const auto now = Clock::now();
    const double waited = msBetween(start, now);
    if (msBetween(last, now) >= quietMs && waited >= quietMs) return waited;
    if (waited > capMs) return -waited;
  }
}

std::string lastOf(int type) {
  std::lock_guard<std::mutex> lock(gMutex);
  auto it = gLast.find(type);
  return it == gLast.end() ? std::string() : it->second;
}
size_t cbCount() {
  std::lock_guard<std::mutex> lock(gMutex);
  return gCbs.size();
}

LibreOfficeKitDocument *gDoc = nullptr;

void post(int code) {
  gDoc->pClass->postKeyEvent(gDoc, LOK_KEYEVENT_KEYINPUT, 0, code);
  gDoc->pClass->postKeyEvent(gDoc, LOK_KEYEVENT_KEYUP, 0, code);
}

struct Sel {
  int type = -1;
  std::string text;
};
Sel readSel() {
  Sel s;
  char *text = nullptr;
  s.type = gDoc->pClass->getSelectionTypeAndText(gDoc, "text/plain;charset=utf-8", &text, nullptr);
  s.text = text ? text : "";
  std::free(text);
  return s;
}
std::string undoValues() {
  char *v = gDoc->pClass->getCommandValues(gDoc, ".uno:Undo");
  std::string s = v ? v : "<null>";
  std::free(v);
  return s;
}

struct Snap {
  Sel sel;
  std::string cursor, textSelection, undo;
};
Snap snap() {
  Snap s;
  s.sel = readSel();
  s.cursor = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
  s.textSelection = lastOf(LOK_CALLBACK_TEXT_SELECTION);
  s.undo = undoValues();
  return s;
}
std::string snapJson(const Snap &s) {
  std::ostringstream o;
  o << "{\"selType\":" << s.sel.type << ",\"selText\":" << q(s.sel.text) << ",\"cursor\":" << q(s.cursor)
    << ",\"textSelection\":" << q(utf8Trunc(s.textSelection, 600)) << ",\"undo\":" << q(s.undo) << "}";
  return o.str();
}

// Callbacks with index >= from, times relative to t0Ms.
std::string callbacksSince(size_t from, double t0Ms, double *firstMs, double *lastMs, int *n) {
  std::vector<Cb> copy;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    copy.assign(gCbs.begin() + static_cast<long>(from), gCbs.end());
  }
  std::ostringstream o;
  o << "[";
  *n = static_cast<int>(copy.size());
  *firstMs = *lastMs = -1;
  for (size_t i = 0; i < copy.size(); ++i) {
    const double rel = copy[i].t - t0Ms;
    if (i == 0) *firstMs = rel;
    *lastMs = rel;
    o << (i ? "," : "") << "{\"t\":" << rel << ",\"typeNum\":" << copy[i].type << ",\"type\":"
      << q(lokCallbackTypeToString(copy[i].type)) << ",\"payload\":" << q(utf8Trunc(copy[i].payload, 600)) << "}";
  }
  o << "]";
  return o.str();
}

std::map<std::string, std::string> gPoints;  // name -> rect payload

bool parseRect(const std::string &payload, long &x, long &y, long &w, long &h) {
  std::string s = payload;
  const auto r = payload.find("\"rectangle\"");
  if (r != std::string::npos) {
    const auto qs = payload.find('"', payload.find(':', r) + 1);
    const auto qe = payload.find('"', qs + 1);
    if (qs != std::string::npos && qe != std::string::npos) s = payload.substr(qs + 1, qe - qs - 1);
  }
  return std::sscanf(s.c_str(), "%ld, %ld, %ld, %ld", &x, &y, &w, &h) == 4;
}
bool pointOf(const std::string &name, long &px, long &py) {
  auto it = gPoints.find(name);
  if (it == gPoints.end()) return false;
  long x, y, w, h;
  if (!parseRect(it->second, x, y, w, h)) return false;
  px = x;
  py = y + h / 2;
  return true;
}

void emitSetup(const std::string &step, double settled, const std::string &extra = "") {
  std::cout << "{\"rec\":\"setup\",\"step\":" << q(step) << ",\"settleMs\":" << settled
            << ",\"cursor\":" << q(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)) << extra << "}" << std::endl;
}

void measured(const std::string &kind, const std::string &label, const std::vector<int> &codes) {
  const double preQuiet = settle(kPreMeasureQuietMs, 10000);
  const Snap before = snap();
  const size_t from = cbCount();
  const double t0 = nowMs();
  for (int c : codes) post(c);
  const double postReturned = nowMs() - t0;
  const double waited = settle(kMeasureQuietMs, kMeasureCapMs);
  const double windowEnd = nowMs() - t0;
  const Snap after = snap();
  double first, last;
  int n;
  const std::string cbs = callbacksSince(from, t0, &first, &last, &n);
  std::ostringstream codesJson;
  for (size_t i = 0; i < codes.size(); ++i) codesJson << (i ? "," : "") << codes[i];
  std::cout << "{\"rec\":\"press\",\"kind\":" << q(kind) << ",\"label\":" << q(label) << ",\"codes\":["
            << codesJson.str() << "],\"preQuietMs\":" << preQuiet << ",\"postReturnedMs\":" << postReturned
            << ",\"capped\":" << (waited < 0 ? "true" : "false") << ",\"windowMs\":" << windowEnd
            << ",\"nCallbacks\":" << n << ",\"firstCbMs\":" << first << ",\"lastCbMs\":" << last
            << ",\"quietAfterLastMs\":" << (n ? windowEnd - last : windowEnd)
            << ",\"undoChanged\":" << (after.undo != before.undo ? "true" : "false")
            << ",\"before\":" << snapJson(before) << ",\"after\":" << snapJson(after) << ",\"callbacks\":" << cbs
            << "}" << std::endl;
}

void measuredK1(const std::string &label, int k1) {
  const double preQuiet = settle(kPreMeasureQuietMs, 10000);
  const Snap before = snap();
  const size_t from = cbCount();
  const double t0 = nowMs();
  post(k1);
  sleepMs(250);
  const Sel s250 = readSel();
  sleepMs(2000);
  const Sel s2250 = readSel();
  const double waited = settle(kMeasureQuietMs, kMeasureCapMs);
  const double windowEnd = nowMs() - t0;
  const Snap after = snap();
  double first, last;
  int n;
  const std::string cbs = callbacksSince(from, t0, &first, &last, &n);
  std::cout << "{\"rec\":\"press\",\"kind\":\"K1\",\"label\":" << q(label) << ",\"codes\":[" << k1
            << "],\"preQuietMs\":" << preQuiet << ",\"capped\":" << (waited < 0 ? "true" : "false")
            << ",\"windowMs\":" << windowEnd << ",\"nCallbacks\":" << n << ",\"firstCbMs\":" << first
            << ",\"lastCbMs\":" << last << ",\"quietAfterLastMs\":" << (n ? windowEnd - last : windowEnd)
            << ",\"sel250\":{\"type\":" << s250.type << ",\"text\":" << q(s250.text) << "}"
            << ",\"sel2250\":{\"type\":" << s2250.type << ",\"text\":" << q(s2250.text) << "}"
            << ",\"undoChanged\":" << (after.undo != before.undo ? "true" : "false")
            << ",\"before\":" << snapJson(before) << ",\"after\":" << snapJson(after) << ",\"callbacks\":" << cbs
            << "}" << std::endl;
}

void locate() {
  settle(kPreMeasureQuietMs, 10000);
  const Sel atStart = readSel();
  post(kEnd | kShift);
  settle(kSetupQuietMs, 5000);
  const Sel suffix = readSel();
  post(kHome | kShift);
  settle(kSetupQuietMs, 5000);
  const Sel prefix = readSel();
  std::cout << "{\"rec\":\"locate\",\"selBefore\":" << q(atStart.text) << ",\"suffix\":" << q(suffix.text)
            << ",\"prefix\":" << q(prefix.text) << "}" << std::endl;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc != 6) {
    std::cerr << "usage: f142-native INSTALL PROFILE_URL DOC_URL SCRIPT OUT_URL\n";
    return 64;
  }
  const char *envs[] = {"SAL_USE_VCLPLUGIN", "SAL_LOK_OPTIONS", "LANG", "LC_ALL", "LANGUAGE", "SAL_LOG"};
  std::cout << "{\"rec\":\"env\",\"install\":" << q(argv[1]) << ",\"profile\":" << q(argv[2])
            << ",\"doc\":" << q(argv[3]) << ",\"script\":" << q(argv[4]) << ",\"out\":" << q(argv[5]);
  for (const char *e : envs) {
    const char *v = std::getenv(e);
    std::cout << ",\"" << e << "\":" << (v ? q(v) : std::string("null"));
  }
  std::cout << "}" << std::endl;

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cout << "{\"rec\":\"fatal\",\"what\":\"lok_init_2\"}" << std::endl;
    return 2;
  }
  const double tLoad = nowMs();
  gDoc = kit->pClass->documentLoad(kit, argv[3]);
  if (!gDoc) {
    std::cout << "{\"rec\":\"fatal\",\"what\":\"documentLoad\"}" << std::endl;
    std::_Exit(3);
  }
  gDoc->pClass->initializeForRendering(gDoc, "{}");
  gDoc->pClass->registerCallback(gDoc, onCallback, nullptr);
  std::string px(256 * 256 * 4, '\0');
  gDoc->pClass->paintTile(gDoc, reinterpret_cast<unsigned char *>(px.data()), 256, 256, 0, 0, 3840, 3840);
  const double settled = settle(kPreMeasureQuietMs, 10000);
  std::cout << "{\"rec\":\"load\",\"loadMs\":" << (nowMs() - tLoad) << ",\"settleMs\":" << settled
            << ",\"callbacks\":" << cbCount() << ",\"cursor\":" << q(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR))
            << ",\"undo\":" << q(undoValues()) << "}" << std::endl;

  std::stringstream steps(argv[4]);
  std::string step;
  while (std::getline(steps, step, ',')) {
    if (step.empty()) continue;
    const char op = step[0];
    const std::string arg = step.substr(1);
    if (op == 'k') {
      int code = 0, times = 1;
      const auto x = arg.find('x');
      code = std::atoi(arg.substr(0, x).c_str());
      if (x != std::string::npos) times = std::atoi(arg.substr(x + 1).c_str());
      double s = 0;
      for (int i = 0; i < times; ++i) {
        post(code);
        s = settle(kSetupQuietMs, 5000);
      }
      emitSetup(step, s);
    } else if (op == 'u') {
      gDoc->pClass->postUnoCommand(gDoc, arg.c_str(), nullptr, false);
      emitSetup(step, settle(kSetupQuietMs, 5000));
    } else if (op == 'r') {
      settle(kSetupQuietMs, 5000);
      gPoints[arg] = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
      std::cout << "{\"rec\":\"point\",\"name\":" << q(arg) << ",\"rect\":" << q(gPoints[arg]) << "}" << std::endl;
    } else if (op == 'c') {
      long x, y;
      if (!pointOf(arg, x, y)) {
        std::cout << "{\"rec\":\"fatal\",\"what\":\"no point\",\"name\":" << q(arg) << "}" << std::endl;
        std::_Exit(4);
      }
      gDoc->pClass->postMouseEvent(gDoc, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0);
      gDoc->pClass->postMouseEvent(gDoc, LOK_MOUSEEVENT_MOUSEBUTTONUP, x, y, 1, 1, 0);
      emitSetup(step, settle(kSetupQuietMs, 5000),
                ",\"x\":" + std::to_string(x) + ",\"y\":" + std::to_string(y));
    } else if (op == 's') {
      const auto colon = arg.find(':');
      long x1, y1, x2, y2;
      if (colon == std::string::npos || !pointOf(arg.substr(0, colon), x1, y1) ||
          !pointOf(arg.substr(colon + 1), x2, y2)) {
        std::cout << "{\"rec\":\"fatal\",\"what\":\"no point\",\"step\":" << q(step) << "}" << std::endl;
        std::_Exit(4);
      }
      gDoc->pClass->setTextSelection(gDoc, LOK_SETTEXTSELECTION_RESET, x1, y1);
      gDoc->pClass->setTextSelection(gDoc, LOK_SETTEXTSELECTION_START, x1, y1);
      gDoc->pClass->setTextSelection(gDoc, LOK_SETTEXTSELECTION_END, x2, y2);
      const double s = settle(kSetupQuietMs, 5000);
      const Sel sel = readSel();
      emitSetup(step, s, ",\"selType\":" + std::to_string(sel.type) + ",\"selText\":" + q(sel.text));
    } else if (op == 'M') {
      const auto eq = arg.find('=');
      measured("key", arg.substr(0, eq), {std::atoi(arg.substr(eq + 1).c_str())});
    } else if (op == 'B') {
      const auto eq = arg.find('=');
      const auto plus = arg.find('+', eq);
      measured("back-to-back", arg.substr(0, eq),
               {std::atoi(arg.substr(eq + 1, plus - eq - 1).c_str()), std::atoi(arg.substr(plus + 1).c_str())});
    } else if (op == 'K') {
      measuredK1(arg, kLeft | kShift);
    } else if (op == 'J') {
      measuredK1(arg, kRight | kShift);
    } else if (op == 'L') {
      locate();
    } else if (op == 'S') {
      settle(kSetupQuietMs, 5000);
      const bool ok = gDoc->pClass->saveAs(gDoc, argv[5], "fodt", nullptr);
      std::cout << "{\"rec\":\"saved\",\"ok\":" << (ok ? "true" : "false") << "}" << std::endl;
    } else {
      std::cout << "{\"rec\":\"fatal\",\"what\":\"unknown step\",\"step\":" << q(step) << "}" << std::endl;
      std::_Exit(5);
    }
  }
  std::cout << "{\"rec\":\"done\",\"ms\":" << nowMs() << "}" << std::endl;
  std::cout.flush();
  gDoc->pClass->destroy(gDoc);
  sleepMs(200);
  std::_Exit(0);
}
