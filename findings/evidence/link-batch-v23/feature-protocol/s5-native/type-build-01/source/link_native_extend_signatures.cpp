// Link batch, native step -- what does core broadcast after Shift+<arrow/Home/End>,
// and after a plain arrow pressed on a range?
//
// Brief: handoff/tasks/TASK-2026-10-13h-link-native-extend-signatures.md.
// Native LibreOffice (LOK) only; no browser, no profile.
//
// Why: the engine completes a pending move on the FIRST matching callback
// (probe_engine.cpp completePendingEditorOperation): a plain move on
// LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR or LOK_CALLBACK_TEXT_SELECTION, an
// extend on LOK_CALLBACK_TEXT_SELECTION only, and a deadline completes a move
// that gets nothing (finding 096).  Whether those completions report the state
// the key finally produced depends on which callbacks core emits, in what order,
// how many of each, and whether any arrives at all.  This tool records exactly
// that and decides nothing.
//
// What it records, per arm (every arm is a FRESH document load):
//   * every callback after the key's KEYINPUT post: numeric type, name, payload
//     (<= 400 bytes), tMs since the post (callbacks that arrived up to 500 ms
//     BEFORE the post are recorded with negative tMs, so a window contaminated
//     by earlier activity shows);
//   * before and after the 1500 ms window: getTextSelection(text/plain), and the
//     last payload of TEXT_SELECTION, INVALIDATE_VISIBLE_CURSOR,
//     TEXT_SELECTION_START, TEXT_SELECTION_END.
//
// Starting shapes are made the way the PRODUCT makes them: a caret by one click
// (postMouseEvent DOWN+UP, count 1, button 1, as the engine's place-caret does),
// a range by a mouse drag (DOWN at A, MOVE to B, UP at B, as
// OXSDK_EDITOR_SELECTION_MOUSE_DRAG does), plus one keyboard-made range.
// Coordinates are NOT hard-coded: a discovery pass at the start of each process
// walks the document with keys and stores the INVALIDATE_VISIBLE_CURSOR rectangle
// at each named offset; a click/drag point is (rect.x, rect.y + rect.h / 2).
// Every discovery row is printed ("discover-*" lines) with the text the same
// position selects with Shift+Home / Shift+End, so the offsets are checked
// against the fixture's text.
//
// Build:  g++ -std=c++17 -O2 -I<libreoffice-26-8>/include
//             tools/link_native_extend_signatures.cpp -ldl -lpthread -o link-native-extend-signatures
// Usage:  link-native-extend-signatures INSTALL_PROGRAM_DIR PROFILE_URL FIXTURE_URL ROUND [SETTLE_QUIET_MS [ARM_FILTER_SUBSTRING]]
//         link-native-extend-signatures --paragraphs     (prints the fixture paragraphs the tool expects)
// Output: one JSON line per arm on stdout.  SAL_USE_VCLPLUGIN=svp.

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <iostream>
#include <map>
#include <memory>
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

constexpr int kShift = 0x1000;  // KEY_SHIFT (the engine's EditorShiftModifier)
constexpr int kMod1 = 0x2000;   // KEY_MOD1 (Ctrl)
constexpr int kDown = 1024, kUp = 1025, kLeft = 1026, kRight = 1027, kHome = 1028,
              kEnd = 1029;  // css::awt::Key
constexpr int kWindowMs = 1500;

// ---- the fixture's paragraphs, in document order -------------------------------
// The runner compares this list with the fixture (gen_extend_signatures.py).
const char *const kParas[] = {
    /* 0  */ "P1 plain paragraph above",
    /* 1  */ "P2 ALPHA BETA GAMMA DELTA",
    /* 2  */ "P3 plain paragraph below",
    /* 3  */ "",
    /* 4  */ "W1 this paragraph is deliberately long so that it wraps onto several displayed lines "
             "because it keeps adding ordinary words one after another until the first line is full "
             "and then the second line is full as well and a third line is needed to hold the rest "
             "of the sentence which goes on for a little while longer before it finally stops here",
    /* 5  */ "中文段落測試，這是第二句。",
    /* 6  */ "Heading one for the test",
    /* 7  */ "List item one",
    /* 8  */ "A1 cell text",
    /* 9  */ "B1 cell text",
    /* 10 */ "A2 cell text",
    /* 11 */ "B2 cell text",
    /* 12 */ "Final paragraph ends the document.",
};
constexpr int kParaCount = sizeof(kParas) / sizeof(kParas[0]);
constexpr int kP1 = 0, kP2 = 1, kP3 = 2, kEmpty = 3, kWrap = 4, kCjk = 5, kHeading = 6, kList = 7,
              kCellA1 = 8, kFinal = 12;

// ---- callbacks -----------------------------------------------------------------
Clock::time_point gEpoch = Clock::now();
double msBetween(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}
double nowMs() { return msBetween(gEpoch, Clock::now()); }

struct Cb {
  double t;  // ms since process start
  int type;
  std::string payload;
};

// One context per document.  Never freed before exit: a callback that arrives
// after destroy() must still find its mutex.
struct Ctx {
  std::mutex m;
  std::vector<Cb> list;
  std::map<int, std::string> last;
  Clock::time_point lastAt = Clock::now();
};
std::deque<std::unique_ptr<Ctx>> gCtxs;

void onCallback(int type, const char *payload, void *data) {
  auto *c = static_cast<Ctx *>(data);
  std::lock_guard<std::mutex> lock(c->m);
  c->lastAt = Clock::now();
  std::string p = payload ? payload : "";
  c->list.push_back({nowMs(), type, p});
  c->last[type] = p;
}

struct Doc {
  LibreOfficeKitDocument *d = nullptr;
  Ctx *ctx = nullptr;
};

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

std::string lastOf(Doc &s, int type) {
  std::lock_guard<std::mutex> lock(s.ctx->m);
  auto it = s.ctx->last.find(type);
  return it == s.ctx->last.end() ? std::string() : it->second;
}

// Wait until no callback for quietMs (and at least quietMs in total); the cap
// ends the wait.  Returns the waited ms, negated if the cap ended it.
double settle(Doc &s, int quietMs, int capMs) {
  const auto start = Clock::now();
  for (;;) {
    drain(25);
    Clock::time_point lastAt;
    {
      std::lock_guard<std::mutex> lock(s.ctx->m);
      lastAt = s.ctx->lastAt;
    }
    const double sinceLast = msBetween(lastAt, Clock::now());
    const double waited = msBetween(start, Clock::now());
    if (sinceLast >= quietMs && waited >= quietMs)
      return waited;
    if (waited > capMs)
      return -waited;
  }
}

// ---- small helpers -------------------------------------------------------------
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

std::string utf8Trunc(const std::string &s, size_t n) {
  if (s.size() <= n)
    return s;
  size_t k = n;
  while (k > 0 && (static_cast<unsigned char>(s[k]) & 0xC0) == 0x80)
    --k;
  return s.substr(0, k);
}

std::string q(const std::string &s) { return "\"" + jsonEscape(s) + "\""; }

std::string selectedText(Doc &s) {
  char *used = nullptr;
  char *text = s.d->pClass->getTextSelection(s.d, "text/plain;charset=utf-8", &used);
  std::string out = text ? text : "";
  std::free(text);
  std::free(used);
  return out;
}

void keyPost(Doc &s, int code) {
  s.d->pClass->postKeyEvent(s.d, LOK_KEYEVENT_KEYINPUT, 0, code);
  s.d->pClass->postKeyEvent(s.d, LOK_KEYEVENT_KEYUP, 0, code);
}

// Shape-making key: post, then a short pause (as the f129 tools do).
void key(Doc &s, int code, int waitMs = 150) {
  keyPost(s, code);
  drain(waitMs);
}

// The engine's click and drag, as in src/probe_engine.cpp (handleClick,
// OXSDK_EDITOR_SELECTION_MOUSE_DRAG).
void engineClick(Doc &s, long x, long y) {
  s.d->pClass->postMouseEvent(s.d, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0);
  s.d->pClass->postMouseEvent(s.d, LOK_MOUSEEVENT_MOUSEBUTTONUP, x, y, 1, 1, 0);
}
void engineDrag(Doc &s, long x1, long y1, long x2, long y2) {
  s.d->pClass->postMouseEvent(s.d, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x1, y1, 1, 1, 0);
  s.d->pClass->postMouseEvent(s.d, LOK_MOUSEEVENT_MOUSEMOVE, x2, y2, 1, 1, 0);
  s.d->pClass->postMouseEvent(s.d, LOK_MOUSEEVENT_MOUSEBUTTONUP, x2, y2, 1, 1, 0);
}
// The engine's text-handles path (probe_engine.cpp ~5577): RESET + START at the
// first point, END at the second.
void engineTextHandles(Doc &s, long x1, long y1, long x2, long y2) {
  s.d->pClass->setTextSelection(s.d, LOK_SETTEXTSELECTION_RESET, x1, y1);
  s.d->pClass->setTextSelection(s.d, LOK_SETTEXTSELECTION_START, x1, y1);
  s.d->pClass->setTextSelection(s.d, LOK_SETTEXTSELECTION_END, x2, y2);
}

Doc openDoc(LibreOfficeKit *kit, const std::string &url) {
  Doc s;
  s.d = kit->pClass->documentLoad(kit, url.c_str());
  if (!s.d)
    return s;
  gCtxs.push_back(std::make_unique<Ctx>());
  s.ctx = gCtxs.back().get();
  s.d->pClass->initializeForRendering(s.d, "{}");
  s.d->pClass->registerCallback(s.d, onCallback, s.ctx);
  std::string pixels(256 * 256 * 4, '\0');
  s.d->pClass->paintTile(s.d, reinterpret_cast<unsigned char *>(pixels.data()), 256, 256, 0, 0, 3840, 3840);
  drain(500);
  return s;
}

void closeDoc(Doc &s) {
  if (!s.d)
    return;
  s.d->pClass->destroy(s.d);
  s.d = nullptr;
  drain(200);
}

// ---- points --------------------------------------------------------------------
struct Pt {
  bool ok = false;
  long rx = 0, ry = 0, rw = 0, rh = 0;
  long x = 0, y = 0;  // click point: (rx, ry + rh / 2)
  std::string rect;
};

Pt ptFromRect(const std::string &rect) {
  Pt p;
  p.rect = rect;
  if (std::sscanf(rect.c_str(), "%ld, %ld, %ld, %ld", &p.rx, &p.ry, &p.rw, &p.rh) == 4) {
    p.ok = true;
    p.x = p.rx;
    p.y = p.ry + p.rh / 2;
  }
  return p;
}

std::map<std::string, Pt> gPts;  // "p1.0", "p2.11", "w.l1end", ...

const Pt &pt(const std::string &name) {
  static const Pt none;
  auto it = gPts.find(name);
  return it == gPts.end() ? none : it->second;
}

std::string ptJson(const std::string &name) {
  const Pt &p = pt(name);
  std::ostringstream o;
  o << "{\"name\":" << q(name) << ",\"rect\":" << q(p.rect) << ",\"x\":" << p.x << ",\"y\":" << p.y << "}";
  return o.str();
}

std::string utf8Prefix(const std::string &s, int codepoints) {
  size_t i = 0;
  for (int n = 0; n < codepoints && i < s.size(); ++n) {
    ++i;
    while (i < s.size() && (static_cast<unsigned char>(s[i]) & 0xC0) == 0x80)
      ++i;
  }
  return s.substr(0, i);
}
std::string utf8Suffix(const std::string &s, int fromCodepoint) { return s.substr(utf8Prefix(s, fromCodepoint).size()); }

// ---- discovery -----------------------------------------------------------------
// One fresh load per paragraph: Ctrl+Down to the paragraph, then Right (or End)
// to each named offset, recording the cursor rectangle.  The load is ended by
// Shift+Home and Shift+End from the last position, whose selections are printed so
// the offset can be checked against the fixture text.
struct DiscoverSpec {
  int para;
  std::vector<int> offsets;  // ascending; reached with Right
  bool toEnd;                // then End -> "p<para>.end"
};

std::string pname(int para, const std::string &suffix) { return "p" + std::to_string(para) + "." + suffix; }

void discoverOne(LibreOfficeKit *kit, const std::string &url, int round, const DiscoverSpec &spec, int quiet) {
  Doc s = openDoc(kit, url);
  if (!s.d) {
    std::cout << "{\"arm\":\"discover-p" << spec.para << "\",\"round\":" << round << ",\"fatal\":\"documentLoad\"}"
              << std::endl;
    return;
  }
  settle(s, quiet, 8000);
  for (int i = 0; i < spec.para; ++i) {
    key(s, kDown | kMod1, 100);
    settle(s, 200, 3000);
  }
  std::ostringstream steps;
  int at = 0;
  bool first = true;
  std::string rect;
  auto record = [&](const std::string &name) {
    rect = lastOf(s, LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
    gPts[name] = ptFromRect(rect);
    steps << (first ? "" : ",") << ptJson(name);
    first = false;
  };
  for (int off : spec.offsets) {
    while (at < off) {
      key(s, kRight, 100);
      settle(s, 200, 3000);
      ++at;
    }
    record(pname(spec.para, std::to_string(off)));
  }
  if (spec.toEnd) {
    key(s, kEnd, 100);
    settle(s, 200, 3000);
    record(pname(spec.para, "end"));
  }
  key(s, kHome | kShift, 100);
  settle(s, 200, 3000);
  const std::string homeText = selectedText(s);
  key(s, kEnd | kShift, 100);
  settle(s, 200, 3000);
  const std::string endText = selectedText(s);
  std::cout << "{\"arm\":\"discover-p" << spec.para << "\",\"round\":" << round << ",\"steps\":[" << steps.str()
            << "],\"shiftHomeText\":" << q(homeText) << ",\"shiftEndText\":" << q(endText)
            << ",\"paraText\":" << q(kParas[spec.para]) << "}" << std::endl;
  closeDoc(s);
}

// The wrapped paragraph: End -> end of displayed line 1, Right -> start of line 2,
// End, Right -> start of line 3.  Proves the paragraph wraps at least twice.
void discoverWrap(LibreOfficeKit *kit, const std::string &url, int round, int quiet) {
  Doc s = openDoc(kit, url);
  if (!s.d)
    return;
  settle(s, quiet, 8000);
  for (int i = 0; i < kWrap; ++i) {
    key(s, kDown | kMod1, 100);
    settle(s, 200, 3000);
  }
  std::ostringstream steps;
  bool first = true;
  auto record = [&](const std::string &name) {
    gPts[name] = ptFromRect(lastOf(s, LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR));
    steps << (first ? "" : ",") << ptJson(name);
    first = false;
  };
  record("w.l1start");
  key(s, kEnd, 100);
  settle(s, 200, 3000);
  record("w.l1end");
  key(s, kRight, 100);
  settle(s, 200, 3000);
  record("w.l2start");
  key(s, kEnd, 100);
  settle(s, 200, 3000);
  record("w.l2end");
  key(s, kRight, 100);
  settle(s, 200, 3000);
  record("w.l3start");
  key(s, kEnd | kShift, 100);
  settle(s, 200, 3000);
  const std::string l3 = selectedText(s);
  std::cout << "{\"arm\":\"discover-wrap\",\"round\":" << round << ",\"steps\":[" << steps.str()
            << "],\"shiftEndTextAtLine3Start\":" << q(l3) << "}" << std::endl;
  closeDoc(s);
}

bool discoverAll(LibreOfficeKit *kit, const std::string &url, int round, int quiet) {
  const std::vector<DiscoverSpec> specs = {
      {kP1, {0}, false},
      {kP2, {0, 3, 8, 9, 10, 11, 14, 19, 20, 25}, false},
      {kP3, {10}, false},
      {kEmpty, {0}, false},
      {kWrap, {0}, false},
      {kCjk, {4}, false},
      {kHeading, {7}, false},
      {kList, {5}, false},
      {kCellA1, {0}, true},
      {kFinal, {0}, true},
  };
  for (const DiscoverSpec &sp : specs)
    discoverOne(kit, url, round, sp, quiet);
  discoverWrap(kit, url, round, quiet);
  const char *must[] = {"p0.0",  "p1.3",  "p1.8",  "p1.9",  "p1.10", "p1.11", "p1.14", "p1.19",
                        "p1.20", "p1.25", "p2.10", "p3.0",  "p5.4",  "p6.7",  "p7.5",  "p8.end",
                        "p12.end", "w.l1start", "w.l1end"};
  bool all = true;
  for (const char *n : must)
    if (!pt(n).ok) {
      std::cout << "{\"fatal\":\"missing discovery point\",\"point\":" << q(n) << ",\"round\":" << round << "}"
                << std::endl;
      all = false;
    }
  return all;
}

// ---- shapes --------------------------------------------------------------------
struct ShapeMade {
  std::string method;
  std::vector<std::string> points;
  std::string expectedSelection;  // "" for a caret
  bool expectRange = false;
  std::string expectedCursorPoint;  // name in gPts, "" if none
  bool haveExpectHomeEnd = false;
  std::string expectShiftHome, expectShiftEnd;  // selection after Shift+Home / Shift+End from this caret
  double settleMs = 0;
};

const std::vector<std::string> kShapes = {"caret-mid", "range-fwd",    "range-bwd",     "range-one",   "range-cross",
                                          "range-kbd", "doc-start",    "doc-end",       "empty-para",  "wrap-line-end",
                                          "cjk-mid",   "heading-mid",  "list-mid",      "cell-end"};
const std::vector<std::string> kRangeShapes = {"range-fwd", "range-bwd", "range-cross", "range-kbd"};

void clickAt(Doc &s, const std::string &name) {
  const Pt &p = pt(name);
  engineClick(s, p.x, p.y);
}
void dragBetween(Doc &s, const std::string &a, const std::string &b) {
  const Pt &pa = pt(a);
  const Pt &pb = pt(b);
  engineDrag(s, pa.x, pa.y, pb.x, pb.y);
}

ShapeMade makeShape(Doc &s, const std::string &shape, int quiet) {
  ShapeMade m;
  const std::string P2 = kParas[kP2];
  auto caretAt = [&](const std::string &point, const std::string &textBefore, const std::string &textAfter) {
    m.method = "click";
    m.points = {point};
    m.expectedCursorPoint = point;
    m.haveExpectHomeEnd = true;
    m.expectShiftHome = textBefore;
    m.expectShiftEnd = textAfter;
    clickAt(s, point);
  };
  if (shape == "caret-mid") {
    caretAt("p1.11", utf8Prefix(P2, 11), utf8Suffix(P2, 11));
  } else if (shape == "range-fwd") {
    m.method = "drag";
    m.points = {"p1.9", "p1.19"};
    m.expectedSelection = "BETA GAMMA";
    m.expectRange = true;
    m.expectedCursorPoint = "p1.19";
    dragBetween(s, "p1.9", "p1.19");
  } else if (shape == "range-bwd") {
    m.method = "drag";
    m.points = {"p1.19", "p1.9"};
    m.expectedSelection = "BETA GAMMA";
    m.expectRange = true;
    m.expectedCursorPoint = "p1.9";
    dragBetween(s, "p1.19", "p1.9");
  } else if (shape == "range-one") {
    m.method = "drag";
    m.points = {"p1.9", "p1.10"};
    m.expectedSelection = "B";
    m.expectRange = true;
    m.expectedCursorPoint = "p1.10";
    dragBetween(s, "p1.9", "p1.10");
  } else if (shape == "range-cross") {
    m.method = "drag";
    m.points = {"p1.11", "p2.10"};
    m.expectedSelection = utf8Suffix(P2, 11) + "\n" + utf8Prefix(kParas[kP3], 10);
    m.expectRange = true;
    m.expectedCursorPoint = "p2.10";
    dragBetween(s, "p1.11", "p2.10");
  } else if (shape == "range-kbd") {
    m.method = "click+Shift+Right x3";
    m.points = {"p1.11"};
    m.expectedSelection = "TA ";
    m.expectRange = true;
    m.expectedCursorPoint = "p1.14";
    clickAt(s, "p1.11");
    settle(s, quiet, 8000);
    for (int i = 0; i < 3; ++i)
      key(s, kRight | kShift, 150);
  } else if (shape == "doc-start") {
    caretAt("p0.0", "", kParas[kP1]);
  } else if (shape == "doc-end") {
    caretAt("p12.end", kParas[kFinal], "");
  } else if (shape == "empty-para") {
    m.method = "click";
    m.points = {"p3.0"};
    m.expectedCursorPoint = "p3.0";
    clickAt(s, "p3.0");
  } else if (shape == "wrap-line-end") {
    m.method = "click+End";
    m.points = {"w.l1start"};
    m.expectedCursorPoint = "w.l1end";
    clickAt(s, "w.l1start");
    settle(s, quiet, 8000);
    key(s, kEnd, 150);
  } else if (shape == "cjk-mid") {
    caretAt("p5.4", utf8Prefix(kParas[kCjk], 4), utf8Suffix(kParas[kCjk], 4));
  } else if (shape == "heading-mid") {
    caretAt("p6.7", utf8Prefix(kParas[kHeading], 7), utf8Suffix(kParas[kHeading], 7));
  } else if (shape == "list-mid") {
    caretAt("p7.5", utf8Prefix(kParas[kList], 5), utf8Suffix(kParas[kList], 5));
  } else if (shape == "cell-end") {
    caretAt("p8.end", kParas[kCellA1], "");
  }
  m.settleMs = settle(s, quiet, 8000);
  return m;
}

// ---- one measured arm ----------------------------------------------------------
struct KeyDef {
  const char *name;
  int code;
};
const KeyDef kKeys[] = {{"Left", kLeft}, {"Right", kRight}, {"Up", kUp},
                        {"Down", kDown}, {"Home", kHome},   {"End", kEnd}};

struct StateSnap {
  std::string selection, textSelection, cursor, selStart, selEnd;
};
StateSnap snap(Doc &s) {
  StateSnap x;
  x.selection = selectedText(s);
  x.textSelection = lastOf(s, LOK_CALLBACK_TEXT_SELECTION);
  x.cursor = lastOf(s, LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
  x.selStart = lastOf(s, LOK_CALLBACK_TEXT_SELECTION_START);
  x.selEnd = lastOf(s, LOK_CALLBACK_TEXT_SELECTION_END);
  return x;
}
std::string snapJson(const StateSnap &x) {
  return "{\"getTextSelection\":" + q(x.selection) + ",\"TEXT_SELECTION\":" + q(utf8Trunc(x.textSelection, 400)) +
         ",\"INVALIDATE_VISIBLE_CURSOR\":" + q(x.cursor) + ",\"TEXT_SELECTION_START\":" + q(utf8Trunc(x.selStart, 400)) +
         ",\"TEXT_SELECTION_END\":" + q(utf8Trunc(x.selEnd, 400)) + "}";
}

std::string callbacksJson(Doc &s, double t0, double fromRel) {
  std::vector<Cb> copy;
  {
    std::lock_guard<std::mutex> lock(s.ctx->m);
    copy = s.ctx->list;
  }
  std::ostringstream o;
  o << "[";
  bool first = true;
  for (const Cb &c : copy) {
    const double rel = c.t - t0;
    if (rel < fromRel)
      continue;
    o << (first ? "" : ",") << "{\"tMs\":" << rel << ",\"typeNum\":" << c.type << ",\"type\":"
      << q(lokCallbackTypeToString(c.type)) << ",\"payload\":" << q(utf8Trunc(c.payload, 400)) << "}";
    first = false;
  }
  o << "]";
  return o.str();
}

// kind: "shift" | "plain" | "control".  keyDef null for the control.
void measuredArm(LibreOfficeKit *kit, const std::string &url, int round, const std::string &shape, const KeyDef *keyDef,
                 bool shift, const std::string &kind, int quiet) {
  const std::string armId = kind == "control" ? "control-" + shape : (shift ? "shift-" : "plain-") + std::string(keyDef->name) + "@" + shape;
  Doc s = openDoc(kit, url);
  if (!s.d) {
    std::cout << "{\"arm\":" << q(armId) << ",\"round\":" << round << ",\"fatal\":\"documentLoad\"}" << std::endl;
    return;
  }
  settle(s, quiet, 8000);
  const ShapeMade made = makeShape(s, shape, quiet);
  drain(100);
  const StateSnap before = snap(s);
  const int keyCode = keyDef ? (keyDef->code | (shift ? kShift : 0)) : 0;
  const double t0 = nowMs();
  double postMs = 0;
  if (keyDef) {
    keyPost(s, keyCode);
    postMs = nowMs() - t0;
  }
  const double remaining = kWindowMs - (nowMs() - t0);
  if (remaining > 0)
    drain(static_cast<int>(remaining));
  const double windowEnd = nowMs() - t0;
  const StateSnap after = snap(s);
  std::cout << "{\"arm\":" << q(armId) << ",\"round\":" << round << ",\"kind\":" << q(kind) << ",\"shape\":" << q(shape)
            << ",\"key\":" << q(keyDef ? keyDef->name : "") << ",\"shift\":" << (shift ? "true" : "false")
            << ",\"shapeMake\":{\"method\":" << q(made.method) << ",\"points\":[";
  for (size_t i = 0; i < made.points.size(); ++i)
    std::cout << (i ? "," : "") << ptJson(made.points[i]);
  std::cout << "],\"expectedSelection\":" << q(made.expectedSelection)
            << ",\"expectRange\":" << (made.expectRange ? "true" : "false")
            << ",\"expectedCursorRect\":" << q(made.expectedCursorPoint.empty() ? "" : pt(made.expectedCursorPoint).rect)
            << ",\"expectedCursorPoint\":" << q(made.expectedCursorPoint)
            << ",\"haveExpectHomeEnd\":" << (made.haveExpectHomeEnd ? "true" : "false")
            << ",\"expectShiftHome\":" << q(made.expectShiftHome) << ",\"expectShiftEnd\":" << q(made.expectShiftEnd)
            << ",\"settleMs\":" << made.settleMs << "},\"before\":" << snapJson(before) << ",\"postReturnMs\":" << postMs
            << ",\"windowMs\":" << windowEnd << ",\"after\":" << snapJson(after)
            << ",\"callbacks\":" << callbacksJson(s, t0, -500) << "}" << std::endl;
  closeDoc(s);
}

// ---- interaction arms (question 7) ---------------------------------------------
// From caret-mid: Shift+<first key>, then one product action, then read the selection.
void interactionArm(LibreOfficeKit *kit, const std::string &url, int round, const KeyDef &first, char step, int quiet) {
  const std::string armId = std::string("inter-Shift+") + first.name + "-" + step;
  Doc s = openDoc(kit, url);
  if (!s.d) {
    std::cout << "{\"arm\":" << q(armId) << ",\"round\":" << round << ",\"fatal\":\"documentLoad\"}" << std::endl;
    return;
  }
  settle(s, quiet, 8000);
  const ShapeMade made = makeShape(s, "caret-mid", quiet);
  drain(100);
  const double tFirst = nowMs();
  keyPost(s, first.code | kShift);
  drain(800);
  settle(s, 300, 4000);
  const StateSnap afterFirst = snap(s);
  const double t1 = nowMs();
  std::string action, expectSel, expectCursorRect;
  std::vector<std::string> points;
  if (step == 'a') {
    action = "click at p2.10 (in P3)";
    points = {"p2.10"};
    expectSel = "";
    expectCursorRect = pt("p2.10").rect;
    clickAt(s, "p2.10");
  } else if (step == 'b') {
    action = "mouse drag over ALPHA (p1.3 -> p1.8)";
    points = {"p1.3", "p1.8"};
    expectSel = "ALPHA";
    dragBetween(s, "p1.3", "p1.8");
  } else {
    action = "setTextSelection RESET+START at p1.20, END at p1.25 (DELTA)";
    points = {"p1.20", "p1.25"};
    expectSel = "DELTA";
    engineTextHandles(s, pt("p1.20").x, pt("p1.20").y, pt("p1.25").x, pt("p1.25").y);
  }
  const double waited = settle(s, 500, 4000);
  const StateSnap afterStep = snap(s);
  const std::string cbStep = callbacksJson(s, t1, 0);  // before the extra Shift+Home below
  std::string shiftHomeText;
  if (step == 'a') {
    // Where is the caret?  Shift+Home from it selects back to the start of the line.
    key(s, kHome | kShift, 150);
    settle(s, 300, 3000);
    shiftHomeText = selectedText(s);
  }
  std::cout << "{\"arm\":" << q(armId) << ",\"round\":" << round << ",\"kind\":\"interaction\",\"firstKey\":"
            << q(std::string("Shift+") + first.name) << ",\"step\":" << q(std::string(1, step))
            << ",\"action\":" << q(action) << ",\"points\":[";
  for (size_t i = 0; i < points.size(); ++i)
    std::cout << (i ? "," : "") << ptJson(points[i]);
  std::cout << "],\"expectedSelection\":" << q(expectSel) << ",\"expectedCursorRect\":" << q(expectCursorRect)
            << ",\"caretMidSettleMs\":" << made.settleMs << ",\"afterFirstKey\":" << snapJson(afterFirst)
            << ",\"afterStep\":" << snapJson(afterStep) << ",\"settleAfterStepMs\":" << waited
            << ",\"shiftHomeAfterClick\":" << q(shiftHomeText) << ",\"expectedShiftHomeAfterClick\":"
            << q(step == 'a' ? utf8Prefix(kParas[kP3], 10) : "") << ",\"callbacksFirstKey\":"
            << callbacksJson(s, tFirst, -500) << ",\"callbacksStep\":" << cbStep << "}" << std::endl;
  closeDoc(s);
}

}  // namespace

int main(int argc, char **argv) {
  if (argc >= 2 && std::strcmp(argv[1], "--paragraphs") == 0) {
    for (int i = 0; i < kParaCount; ++i)
      std::cout << kParas[i] << "\n";
    return 0;
  }
  if (argc < 5) {
    std::cerr << "usage: link-native-extend-signatures INSTALL PROFILE_URL FIXTURE_URL ROUND [SETTLE_QUIET_MS [FILTER]]\n"
                 "       link-native-extend-signatures --paragraphs\n";
    return 2;
  }
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 failed\n";
    return 1;
  }
  const std::string url = argv[3];
  const int round = std::atoi(argv[4]);
  const int quiet = argc > 5 ? std::atoi(argv[5]) : 800;
  const std::string filter = argc > 6 ? argv[6] : "";
  auto wanted = [&](const std::string &id) { return filter.empty() || id.find(filter) != std::string::npos; };

  std::cout << "{\"arm\":\"meta\",\"round\":" << round << ",\"settleQuietMs\":" << quiet << ",\"windowMs\":" << kWindowMs
            << "}" << std::endl;
  if (!discoverAll(kit, url, round, quiet))
    return 3;

  // Controls: the window with NO key.
  for (const char *shape : {"caret-mid", "range-fwd", "range-kbd"}) {
    const std::string id = std::string("control-") + shape;
    if (wanted(id))
      measuredArm(kit, url, round, shape, nullptr, false, "control", quiet);
  }
  // Shift+key on every shape.
  for (const std::string &shape : kShapes)
    for (const KeyDef &k : kKeys) {
      const std::string id = std::string("shift-") + k.name + "@" + shape;
      if (wanted(id))
        measuredArm(kit, url, round, shape, &k, true, "shift", quiet);
    }
  // Plain key on the four range shapes.
  for (const std::string &shape : kRangeShapes)
    for (const KeyDef &k : kKeys) {
      const std::string id = std::string("plain-") + k.name + "@" + shape;
      if (wanted(id))
        measuredArm(kit, url, round, shape, &k, false, "plain", quiet);
    }
  // Interaction arms.
  const KeyDef *firsts[] = {&kKeys[1], &kKeys[3], &kKeys[5]};  // Right, Down, End
  for (const KeyDef *f : firsts)
    for (char step : {'a', 'b', 'c'}) {
      const std::string id = std::string("inter-Shift+") + f->name + "-" + step;
      if (wanted(id))
        interactionArm(kit, url, round, *f, step, quiet);
    }
  return 0;
}
