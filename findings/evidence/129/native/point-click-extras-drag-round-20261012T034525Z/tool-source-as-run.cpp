// Finding 129 -- does "click at the point's cursor rectangle, then the key"
// land where Writer's own key handling lands?
//
// Context: tools/f129_native_arrow_on_selection.cpp showed that, on a selection,
// Writer moves FROM THE POINT by the key's unit and drops the selection.  The
// engine refuses the six moves on a range, so the page fix planned for release
// 0.2.13 (specs/SPEC-M3-autosave.md 3.7, 8.1 Q5) first CLICKS at the point
// (x = the cursor rectangle's x, y = its y + height / 2) to collapse the
// selection there, then sends the ordinary collapsed move.  The engine's click
// is postMouseEvent(DOWN, x, y, 1, 1, 0) then (UP, x, y, 1, 1, 0)
// (src/probe_engine.cpp handleClick).  This tool measures the emulation against
// Writer's own behaviour.
//
// Brief: handoff/tasks/TASK-2026-10-12c-native-page-rectangles-and-129-shapes.md
// (Part N2).  The existing tool is NOT changed; this one reimplements the same
// procedure for its `ref` arms so ref and emu are paired in one process, and
// the old 12 arms' `ref` text is compared with round-20261012T020528Z by the
// analysis script.
//
// Shapes (every selection is made on a FRESH load):
//   old fixture  test-docs/f129/arrow-selection.fodt
//     p2-forward   "BETA GAMMA" of P2 (offsets 9..19), Shift+Right x10 (point at 19)
//     p2-backward  the same range, Shift+Left x10 from 19 (point at 9)
//   shapes fixture test-docs/f129/arrow-selection-shapes.fodt
//     s1  soft wrap: the 10 characters before the first wrap offset W, FORWARD
//         (point at W); W is found by `discover` (the y of the cursor rectangle
//         changes when Right crosses it)
//     s2  hard break: "visual line" of the first visual line, FORWARD (the
//         point right before <text:line-break/>)
//     s3  "paragraph" + the paragraph break, FORWARD (point in the empty paragraph)
//     s4  "cell A1" inside the text of table cell A1, FORWARD
//     s5  "text" of A1 + one more Shift+Right across the cell boundary into B1
// Navigation to s2..s5 uses Ctrl+Down (next paragraph); `made` (the selected
// text read back) is checked against the expectation and reported.
//
// For each shape x key in {Left,Right,Up,Down,Home,End}:
//   ref-<shape>-<key>   the key with the selection in place, then '#', then read
//   emu-<shape>-<key>   quiet; read the latest INVALIDATE_VISIBLE_CURSOR rect;
//                       click at (x, y + h/2); wait quiet; the (unshifted) key;
//                       '#'; read
// and once per shape  click-only-<shape>   the click alone, then '#', read.
// For emu / click-only the callbacks after the click (type, payload, time
// relative to the click) are logged.
//
// Extras (added after the first evidence round; see the README): with the
// environment variable F129_EXTRAS=only and F129_WRAP_FIXTURE_URL set, only
//   s1e  the S1 paragraph, the 10 characters before the wrap offset W, made
//        with Shift+End from inside line 1 (the point at the END of line 1)
//   m1r  test-docs/f129/arrow-selection-wrap.fodt, an unbroken 330-letter token
//        whose first line breaks MID-WORD at offset B (found by discover), the
//        10 characters before B with Shift+Right x10 (the point at B, which
//        Right displays at the START of line 2)
//   m1e  the same range made with Shift+End (the point at B displayed at the
//        END of line 1)
// are run.  F129_EXTRAS=drag runs instead
//   s1d, m1d  the same two paragraphs, the selection made with the product's own
//             mouse drag from inside the last characters of line 1 to a point to
//             the right of the end of line 1
// Without the variable the arm list is exactly the original one.
//
// Build:  g++ -std=c++17 -O2 -I<libreoffice-26-8>/include
//             tools/f129_native_point_click.cpp -ldl -lpthread -o f129-native-point-click
// Usage:  f129-native-point-click INSTALL_PROGRAM_DIR PROFILE_URL OLD_FIXTURE_URL SHAPES_FIXTURE_URL ROUNDS [ARM_FILTER_SUBSTRING [ROUND_LABEL_OFFSET]]
// Output: one JSON line per arm on stdout.  SAL_USE_VCLPLUGIN=svp.

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

namespace {

using Clock = std::chrono::steady_clock;

constexpr int kShift = 0x1000;  // KEY_SHIFT
constexpr int kMod1 = 0x2000;   // KEY_MOD1 (Ctrl)
constexpr int kDown = 1024, kUp = 1025, kLeft = 1026, kRight = 1027,
              kHome = 1028, kEnd = 1029;  // css::awt::Key

struct CallbackRecord {
  double tMs;  // since process start
  int type;
  std::string payload;
};

std::mutex gMutex;
std::vector<CallbackRecord> gCallbacks;
std::map<int, std::string> gLastByType;  // last payload per callback type
Clock::time_point gEpoch = Clock::now();
Clock::time_point gLastCallback = Clock::now();

double msBetween(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}
double nowMs() { return msBetween(gEpoch, Clock::now()); }

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  gLastCallback = Clock::now();
  const std::string p = payload ? payload : "";
  gCallbacks.push_back({nowMs(), type, p});
  gLastByType[type] = p;
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

// Wait until no callback for `quietMs` (and at least `quietMs` in total), at
// most capMs.  Returns the waited ms.
double waitQuiet(int quietMs, int capMs) {
  const auto start = Clock::now();
  for (;;) {
    drain(25);
    Clock::time_point last;
    {
      std::lock_guard<std::mutex> lock(gMutex);
      last = gLastCallback;
    }
    const double sinceLast = msBetween(last, Clock::now());
    const double waited = msBetween(start, Clock::now());
    if (sinceLast >= quietMs && waited >= quietMs)
      return waited;
    if (waited > capMs)
      return -waited;
  }
}

std::string jsonEscape(const std::string &value) {
  std::string out;
  for (const char c : value) {
    switch (c) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': out += "\\r"; break;
    case '\t': out += "\\t"; break;
    default:
      if (static_cast<unsigned char>(c) < 0x20) {
        char b[8];
        std::snprintf(b, sizeof b, "\\u%04x", static_cast<unsigned char>(c));
        out += b;
      } else {
        out += c;
      }
    }
  }
  return out;
}

void key(LibreOfficeKitDocument *d, int code) {
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYINPUT, 0, code);
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYUP, 0, code);
  drain(150);
}

void typeChar(LibreOfficeKitDocument *d, char c) {
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYINPUT, c, 0);
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYUP, c, 0);
  drain(300);
}

std::string selectedText(LibreOfficeKitDocument *d) {
  char *used = nullptr;
  char *text = d->pClass->getTextSelection(d, "text/plain;charset=utf-8", &used);
  std::string out = text ? text : "";
  std::free(text);
  std::free(used);
  return out;
}

void unoCommand(LibreOfficeKitDocument *d, const char *command) {
  d->pClass->postUnoCommand(d, command, nullptr, false);
  drain(400);
}

// Read the whole document's text.  One .uno:SelectAll is enough in a plain
// paragraph, but inside a table cell the first SelectAll selects only the cell
// (second: the table, third: the document -- measured by the first debug run of
// this tool, where the table arms read back one cell), so SelectAll is repeated
// until the text no longer changes (at most four passes).  `passes` receives the
// length after each pass.
std::string readWholeText(LibreOfficeKitDocument *d, std::vector<size_t> &passes) {
  std::string previous;
  for (int i = 0; i < 4; ++i) {
    unoCommand(d, ".uno:SelectAll");
    const std::string t = selectedText(d);
    passes.push_back(t.size());
    if (i > 0 && t == previous)
      return t;
    previous = t;
  }
  return previous;
}

// The engine's click (src/probe_engine.cpp handleClick), verbatim.
void engineClick(LibreOfficeKitDocument *d, long x, long y) {
  d->pClass->postMouseEvent(d, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0);
  d->pClass->postMouseEvent(d, LOK_MOUSEEVENT_MOUSEBUTTONUP, x, y, 1, 1, 0);
}

bool parseRect(const std::string &s, long &x, long &y, long &w, long &h) {
  return std::sscanf(s.c_str(), "%ld, %ld, %ld, %ld", &x, &y, &w, &h) == 4;
}

std::string lastOf(int type) {
  std::lock_guard<std::mutex> lock(gMutex);
  auto it = gLastByType.find(type);
  return it == gLastByType.end() ? std::string() : it->second;
}

struct Shape {
  std::string id;
  int fixture;                 // 0 old, 1 shapes
  std::vector<int> nav;        // keys from a fresh load
  int rightsBefore;            // plain Right presses after nav
  int selCount;                // Shift+<selKey> presses
  int selKey;                  // kRight or kLeft
  std::string expectedMade;    // what getTextSelection should return after the selection
  // When dragX2 != 0 the selection is made with the product's own mouse drag
  // (src/probe_engine.cpp, OXSDK_EDITOR_SELECTION_MOUSE_DRAG: DOWN at (x1, y1),
  // MOVE to (x2, y2), UP at (x2, y2), each with count 1, buttons 1) instead of
  // the Right / Shift+key presses.
  int dragX1 = 0, dragY1 = 0, dragX2 = 0, dragY2 = 0;
};

struct Key {
  const char *name;
  int code;
};
const Key kKeys[] = {{"Left", kLeft}, {"Right", kRight}, {"Up", kUp},
                     {"Down", kDown}, {"Home", kHome},   {"End", kEnd}};

const std::string kS1 =
    "S1 alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike "
    "november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee "
    "zulu one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone twentytwo "
    "twentythree twentyfour twentyfive twentysix twentyseven twentyeight twentynine "
    "thirty thirtyone thirtytwo thirtythree thirtyfour thirtyfive end1";

// ---- one arm -----------------------------------------------------------------
struct Result {
  std::string json;
};

void emitArm(const std::string &armId, int round, const Shape &shape, const std::string &kind,
             const char *keyName, LibreOfficeKit *kit, const std::string &fixtureUrl) {
  LibreOfficeKitDocument *d = kit->pClass->documentLoad(kit, fixtureUrl.c_str());
  if (!d) {
    std::cout << "{\"arm\":\"" << armId << "\",\"round\":" << round << ",\"fatal\":\"documentLoad\"}" << std::endl;
    return;
  }
  d->pClass->initializeForRendering(d, "{}");
  {
    std::lock_guard<std::mutex> lock(gMutex);
    gLastByType.clear();  // nothing from the previous document survives
  }
  d->pClass->registerCallback(d, onCallback, nullptr);
  std::string pixels(256 * 256 * 4, '\0');
  d->pClass->paintTile(d, reinterpret_cast<unsigned char *>(pixels.data()), 256, 256, 0, 0, 3840, 3840);
  drain(500);

  for (int k : shape.nav)
    key(d, k);
  drain(300);
  if (shape.dragX2 != 0) {
    d->pClass->postMouseEvent(d, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, shape.dragX1, shape.dragY1, 1, 1, 0);
    d->pClass->postMouseEvent(d, LOK_MOUSEEVENT_MOUSEMOVE, shape.dragX2, shape.dragY2, 1, 1, 0);
    d->pClass->postMouseEvent(d, LOK_MOUSEEVENT_MOUSEBUTTONUP, shape.dragX2, shape.dragY2, 1, 1, 0);
    drain(500);
  } else {
    for (int i = 0; i < shape.rightsBefore; ++i)
      key(d, kRight);
    for (int i = 0; i < shape.selCount; ++i)
      key(d, shape.selKey | kShift);
  }
  const std::string made = selectedText(d);

  // Selection-state callbacks as the selection stands.
  std::map<std::string, std::string> state;
  state["INVALIDATE_VISIBLE_CURSOR"] = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
  state["TEXT_SELECTION"] = lastOf(LOK_CALLBACK_TEXT_SELECTION);
  state["TEXT_SELECTION_START"] = lastOf(LOK_CALLBACK_TEXT_SELECTION_START);
  state["TEXT_SELECTION_END"] = lastOf(LOK_CALLBACK_TEXT_SELECTION_END);
  state["TABLE_SELECTED"] = lastOf(LOK_CALLBACK_TABLE_SELECTED);

  const bool emulate = kind == "emu" || kind == "click-only";
  long cx = -1, cy = -1;
  long rx = 0, ry = 0, rw = 0, rh = 0;
  bool haveRect = false;
  double quietBeforeMs = 0, clickMs = 0, quietAfterMs = 0;
  std::vector<CallbackRecord> afterClick;
  std::string selectedAfterClick;
  std::string cursorAtClick = state["INVALIDATE_VISIBLE_CURSOR"];
  if (emulate) {
    quietBeforeMs = waitQuiet(500, 4000);
    // The latest rectangle while the selection exists (after the quiet wait,
    // in case a late cursor callback arrives).
    cursorAtClick = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
    haveRect = parseRect(cursorAtClick, rx, ry, rw, rh);
    if (haveRect) {
      cx = rx;
      cy = ry + rh / 2;
      size_t from;
      {
        std::lock_guard<std::mutex> lock(gMutex);
        from = gCallbacks.size();
      }
      clickMs = nowMs();
      engineClick(d, cx, cy);
      quietAfterMs = waitQuiet(500, 4000);
      {
        std::lock_guard<std::mutex> lock(gMutex);
        for (size_t i = from; i < gCallbacks.size(); ++i)
          afterClick.push_back(gCallbacks[i]);
      }
      selectedAfterClick = selectedText(d);
    }
  }

  std::string afterKey;
  if (kind == "ref" || kind == "emu") {
    if (!(emulate && !haveRect)) {
      for (const Key &k : kKeys)
        if (keyName && std::strcmp(k.name, keyName) == 0)
          key(d, k.code);
      drain(300);
      afterKey = selectedText(d);
    }
  }
  const std::string cursorAfter = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
  typeChar(d, '#');
  std::vector<size_t> readPasses;
  const std::string text = readWholeText(d, readPasses);

  std::cout << "{\"arm\":\"" << armId << "\",\"round\":" << round << ",\"kind\":\"" << kind
            << "\",\"shape\":\"" << shape.id << "\",\"key\":\"" << (keyName ? keyName : "")
            << "\",\"made\":\"" << jsonEscape(made) << "\",\"madeExpected\":\""
            << jsonEscape(shape.expectedMade) << "\",\"madeOk\":" << (made == shape.expectedMade ? "true" : "false")
            << ",\"selectionState\":{";
  bool first = true;
  for (const auto &kv : state) {
    std::cout << (first ? "" : ",") << "\"" << kv.first << "\":\"" << jsonEscape(kv.second) << "\"";
    first = false;
  }
  std::cout << "}";
  if (emulate) {
    std::cout << ",\"cursorAtClick\":\"" << jsonEscape(cursorAtClick) << "\",\"haveRect\":"
              << (haveRect ? "true" : "false") << ",\"click\":{\"x\":" << cx << ",\"y\":" << cy
              << "},\"quietBeforeMs\":" << quietBeforeMs << ",\"quietAfterClickMs\":" << quietAfterMs
              << ",\"selectedAfterClick\":\"" << jsonEscape(selectedAfterClick) << "\",\"callbacksAfterClick\":[";
    for (size_t i = 0; i < afterClick.size(); ++i) {
      std::cout << (i ? "," : "") << "{\"tMs\":" << (afterClick[i].tMs - clickMs) << ",\"type\":\""
                << lokCallbackTypeToString(afterClick[i].type) << "\",\"payload\":\""
                << jsonEscape(afterClick[i].payload.substr(0, 240)) << "\"}";
    }
    std::cout << "]";
  }
  if (kind == "ref" || kind == "emu")
    std::cout << ",\"selectedAfterKey\":\"" << jsonEscape(afterKey) << "\"";
  std::cout << ",\"cursorAfter\":\"" << jsonEscape(cursorAfter) << "\",\"readPasses\":[";
  for (size_t i = 0; i < readPasses.size(); ++i)
    std::cout << (i ? "," : "") << readPasses[i];
  std::cout << "],\"text\":\"" << jsonEscape(text) << "\"}" << std::endl;
  d->pClass->destroy(d);
  drain(200);
}

// s1: where does line 2 start?  Right from the document start until the y of
// the cursor rectangle changes.
int discoverWrap(LibreOfficeKit *kit, const std::string &fixtureUrl, int round, const std::string &name,
                 const std::string &paragraphText) {
  LibreOfficeKitDocument *d = kit->pClass->documentLoad(kit, fixtureUrl.c_str());
  if (!d) {
    std::cout << "{\"arm\":\"discover-" << name << "\",\"round\":" << round << ",\"fatal\":\"documentLoad\"}" << std::endl;
    return -1;
  }
  d->pClass->initializeForRendering(d, "{}");
  {
    std::lock_guard<std::mutex> lock(gMutex);
    gLastByType.clear();
  }
  d->pClass->registerCallback(d, onCallback, nullptr);
  std::string pixels(256 * 256 * 4, '\0');
  d->pClass->paintTile(d, reinterpret_cast<unsigned char *>(pixels.data()), 256, 256, 0, 0, 3840, 3840);
  drain(500);
  long x0 = 0, y0 = 0, w0 = 0, h0 = 0;
  parseRect(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR), x0, y0, w0, h0);
  std::cout << "{\"arm\":\"discover-" << name << "\",\"round\":" << round << ",\"start\":\""
            << jsonEscape(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)) << "\",\"steps\":[";
  int wrap = -1;
  std::string prev = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
  for (int i = 1; i <= 200; ++i) {
    key(d, kRight);
    const std::string cur = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
    long x = 0, y = 0, w = 0, h = 0;
    parseRect(cur, x, y, w, h);
    std::cout << (i > 1 ? "," : "") << "{\"after\":" << i << ",\"cursor\":\"" << jsonEscape(cur) << "\"}";
    if (wrap < 0 && y != y0) {
      wrap = i;
      break;
    }
  }
  std::cout << "],\"wrapOffset\":" << wrap << ",\"line1Text\":\""
            << jsonEscape(wrap > 0 && static_cast<size_t>(wrap) <= paragraphText.size() ? paragraphText.substr(0, wrap) : "")
            << "\"}" << std::endl;
  d->pClass->destroy(d);
  drain(200);
  return wrap;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 6) {
    std::cerr << "usage: f129-native-point-click INSTALL PROFILE_URL OLD_FIXTURE_URL SHAPES_FIXTURE_URL ROUNDS [FILTER]\n";
    return 2;
  }
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 failed\n";
    return 1;
  }
  const std::string oldUrl = argv[3], shapesUrl = argv[4];
  const int rounds = std::atoi(argv[5]);
  const std::string filter = argc > 6 ? argv[6] : "";
  const int roundOffset = argc > 7 ? std::atoi(argv[7]) : 0;

  const char *extrasEnv = std::getenv("F129_EXTRAS");
  const bool extrasOnly = extrasEnv && (std::strcmp(extrasEnv, "only") == 0 || std::strcmp(extrasEnv, "drag") == 0);
  const bool extrasDrag = extrasEnv && std::strcmp(extrasEnv, "drag") == 0;
  const char *wrapEnv = std::getenv("F129_WRAP_FIXTURE_URL");
  for (int roundIndex = 1; roundIndex <= rounds; ++roundIndex) {
    const int round = roundIndex + roundOffset;
    if (extrasOnly) {
      if (!wrapEnv) {
        std::cout << "{\"fatal\":\"F129_WRAP_FIXTURE_URL not set\"}" << std::endl;
        return 2;
      }
      const std::string wrapUrl = wrapEnv;
      const int w1 = discoverWrap(kit, shapesUrl, round, "s1", kS1);
      const int bm = discoverWrap(kit, wrapUrl, round, "m1", "");
      if (w1 <= 10 || bm <= 10) {
        std::cout << "{\"fatal\":\"wrap offset not found\",\"round\":" << round << "}" << std::endl;
        continue;
      }
      std::vector<std::pair<Shape, std::string>> extra;
      if (extrasDrag) {
        // Drag from inside the last 10 characters of line 1 (x from the selection
        // rectangles of the s1e / m1r arms in point-click-extras-round-*: offset 91
        // of S1 starts at x 10062, offset 79 of the token at x 10136) to a point to
        // the right of the end of line 1, at the height of line 1 (y 1418 + 138).
        extra.push_back({{"s1d", 1, {}, 0, 0, 0, "?", 10100, 1556, 11400, 1556}, shapesUrl});
        extra.push_back({{"m1d", 1, {}, 0, 0, 0, "?", 10180, 1556, 11700, 1556}, wrapUrl});
      } else {
        extra.push_back({{"s1e", 1, {}, w1 - 10, 1, kEnd, "?"}, shapesUrl});
        extra.push_back({{"m1r", 1, {}, bm - 10, 10, kRight, "?"}, wrapUrl});
        extra.push_back({{"m1e", 1, {}, bm - 10, 1, kEnd, "?"}, wrapUrl});
      }
      for (const auto &sh : extra) {
        for (const char *kind : {"ref", "emu"}) {
          for (const Key &k : kKeys) {
            const std::string id = std::string(kind) + "-" + sh.first.id + "-" + k.name;
            if (!filter.empty() && id.find(filter) == std::string::npos)
              continue;
            emitArm(id, round, sh.first, kind, k.name, kit, sh.second);
          }
        }
        const std::string id = "click-only-" + sh.first.id;
        if (filter.empty() || id.find(filter) != std::string::npos)
          emitArm(id, round, sh.first, "click-only", nullptr, kit, sh.second);
      }
      continue;
    }
    const int wrap = discoverWrap(kit, shapesUrl, round, "s1", kS1);
    if (wrap <= 10) {
      std::cout << "{\"fatal\":\"wrap offset not found\",\"round\":" << round << "}" << std::endl;
      continue;
    }
    std::vector<Shape> shapes;
    // P2 = "P2 ALPHA BETA GAMMA DELTA": "BETA GAMMA" is offsets 9..19.  nav = Down, Home as in the old tool.
    shapes.push_back({"p2-forward", 0, {kDown, kHome}, 9, 10, kRight, "BETA GAMMA"});
    shapes.push_back({"p2-backward", 0, {kDown, kHome}, 19, 10, kLeft, "BETA GAMMA"});
    shapes.push_back({"s1", 1, {}, wrap - 10, 10, kRight, kS1.substr(wrap - 10, 10)});
    shapes.push_back({"s2", 1, {kDown | kMod1}, 9, 11, kRight, "visual line"});
    shapes.push_back({"s3", 1, {kDown | kMod1, kDown | kMod1}, 25, 10, kRight, "paragraph\n"});
    shapes.push_back({"s4", 1, {kDown | kMod1, kDown | kMod1, kDown | kMod1, kDown | kMod1, kDown | kMod1}, 3, 7, kRight, "cell A1"});
    shapes.push_back({"s5", 1, {kDown | kMod1, kDown | kMod1, kDown | kMod1, kDown | kMod1, kDown | kMod1}, 11, 5, kRight, ""});
    for (const Shape &shape : shapes) {
      const std::string &url = shape.fixture == 0 ? oldUrl : shapesUrl;
      for (const char *kind : {"ref", "emu"}) {
        for (const Key &k : kKeys) {
          const std::string id = std::string(kind) + "-" + shape.id + "-" + k.name;
          if (!filter.empty() && id.find(filter) == std::string::npos)
            continue;
          emitArm(id, round, shape, kind, k.name, kit, url);
        }
      }
      const std::string id = "click-only-" + shape.id;
      if (filter.empty() || id.find(filter) != std::string::npos)
        emitArm(id, round, shape, "click-only", nullptr, kit, url);
    }
  }
  return 0;
}
