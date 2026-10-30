// THE 083 PATH (fable ruling 3 Q5.2, findings/evidence/176/native-q52/PREDICTION.md): a second
// selection after `.uno:SelectText` returns NONE.  Derived from findings/evidence/176/native/tool/
// f176_native.cpp (sha256 cb4d9f410813188176ab74f66ec01974d63c6ec6db9804ee782fcb4ff73bf7cb) with
// exactly one addition, everything else unchanged:
//   5. op H<.uno:Cmd>[|<json>]~<.uno:Fallback>: G (v27's collapsed order: no restore before the
//      select), then, ONLY if the synchronous read after .uno:SelectText is NONE (the 083 path):
//      postUnoCommand(<Fallback>, null, true); the synchronous read; getTextSelection("text/html")
//      if TEXT; then G's restore and read.  The format record gains "fallback": the command,
//      whether it ran, the read, the full markup (up to 1 MiB) with its byte count, and the wall
//      times of the post and of the html call.
//
// FINDING 176, engine item C (fable ruling 2026-10-30 §3.3 step 1): the native arm.
// Derived from findings/evidence/link-batch-v23/native/ordered-commands/tool/oc_native.cpp
// (sha256 6e6b22d973375d681a3035fd3d6da742b78af4fdb6f7cfdb581e1daf3fa13723) with exactly these
// additions, everything else unchanged:
//   1. op F<.uno:Cmd>[|<json>]: the engine's ordered format action at a collapsed caret, in ONE call,
//      in the order of wasm_sdk_probe/src/ordered_format.inc startOrderedFormatAction (non-cross
//      route): the caret point captured before the dispatch (the last INVALIDATE_VISIBLE_CURSOR
//      rectangle, x and y + h/2, as restoreOrderedFormatPoint); postUnoCommand(cmd, json, true);
//      RESET, START, RESET at that point; postUnoCommand(.uno:SelectText, null, true); the
//      synchronous selection read (getSelectionTypeAndText); getTextSelection("text/html") if TEXT;
//      RESET, START, RESET again; the synchronous selection read again (the restore confirmation).
//      The record carries the point, both reads and the markup (first 4000 bytes).
//   2. every op record carries cbIndexAtStart and cbIndexAtReturn, so a reader can split the op's
//      callbacks into during-the-call, before-the-first-poll and late by index, not by clock.
//   3. (amendment 1, after the smoke, before the counted run) an F or G op also records the whole .uno:Undo
//      payload immediately before its first call ("undoAtStart"), as OC_A11Y does without switching
//      accessibility on.
//   4. (amendment 1) op G<.uno:Cmd>[|<json>]: F without the restore BEFORE .uno:SelectText -- the select
//      runs from wherever the dispatch left the cursor; the restore after the read is kept.
// The question (findings/evidence/176/native/PREDICTION.md): is there a caret-paragraph-scoped
// observable, delivered before the first poll after the command returns, that says whether a list
// action applied to the paragraph it was dispatched to -- without the selection readback?
//
// Ordered commands (engine v23), fable ruling 1 §2.6: does LOK apply the
// engine's command sequences in Writer's order under unipoll (candidate C)?
//
// Native LibreOfficeKit only (no browser, no WASM, no engine build). One
// document per process. Grown from findings/evidence/link-batch-v21/native/
// 142-ctrl-home-end/tool/f142_native_queued_pair.cpp (the queued-in-callback
// form) and f142_native_ctrl_home_end.cpp (records, settle, save).
//
// Usage: oc-native MODE INSTALL_PROGRAM_DIR PROFILE_URL DOC_URL SCRIPT OUT_URL
//
// MODE (how the measured sequence of an X step is issued):
//   seq      threaded LOK (as the product today). Each op of the sequence runs
//            from the driver thread and is left to settle (600 ms quiet) before
//            the next: Writer's own order, measured rather than written down.
//   q        threaded LOK. The trigger key is posted; inside its first
//            INVALIDATE_VISIBLE_CURSOR callback (the LOK main thread, busy) the
//            ops run back to back, so a posted op is still queued when the next
//            op is issued. The positive control: it must reorder.
//   unipoll  SAL_LOK_OPTIONS=unipoll (set by the runner, recorded in the env
//            record). lok_init_2 runs InitVCL on this thread
//            (desktop/source/lib/init.cxx:8378-8387). The harness then does what
//            lo_runLoop does (init.cxx:7722-7743) except soffice_main:
//            vcl::lok::registerPollCallbacks, SfxLokHelper::registerViewCallbacks
//            and Application::UpdateMainThread, resolved by dlsym from
//            libmergedlo.so. NATIVE ONLY: soffice_main would return at once
//            (ImplSVMain's IsVCLInit early return, vcl/source/app/svmain.cxx:196)
//            and destroy its stack Desktop on the way out; ~Application runs
//            ImplDeInitSVData and clears mpApp (vcl/source/app/svapp.cxx:165-168),
//            so the first window crashed in ImplUpdateGlobalSettings (smoke
//            1, 2026-10-20). On Emscripten soffice_main leaks the Desktop instead
//            (desktop/source/app/sofficemain.cxx:78-92), which is why the engine's
//            mainloop profile can call runLoop. Here the application object is
//            InitVCL's bare Application, and Desktop::Main never runs, so the
//            harness also calls SfxApplication::GetOrCreate(), the one line iOS's
//            LOK init adds for the same reason (init.cxx:8294; without it the
//            load crashed in SfxApplication::GetFilterMatcher, smoke 2). Upstream
//            caa4036188ed (2026-02-27) made ImplSVMain return early when VCL is
//            initialised; Collabora's co-26.04 core still runs mpApp->Main()
//            there. The harness then enters
//            Application::Execute itself, as the engine's mainloop profile does
//            (wasm_sdk_probe/src/probe_engine.cpp, OXSDK_MAINLOOP_ENGINE). Every step runs from
//            the poll callback, which ImplYield calls only when no user event
//            is pending (vcl/headless/svpinst.cxx:442-481); the trigger and the
//            ops of an X step run back to back inside one poll call.
//   uni1     unipoll, ONE op per poll (SPEC-M3-ordered-commands §5.2), for N1
//            (§9.1). After each op returns, the next poll call is "the first poll
//            after return": its time and the callback count are recorded, then
//            the harness idles for 1500 ms (polls that do nothing) and records
//            every callback that arrived after the first poll (N1a/N1b). No
//            anyInput callback is registered.
//   uni1ai   as uni1, with an anyInput callback that answers "a reply is
//            pending" from an op's return until its first poll (the spec's
//            §5.2 rule without the queued-command term: the page sends one
//            command at a time). N1c compares uni1 and uni1ai.
//   uni1f    unipoll, ONE op per poll and the next op at the next poll, with no idle and no late-callback
//            window: the page's cadence (SPEC-M3-ordered-commands §15.3, the object-click arm of
//            L-object-click-shell-switch; fable ruling 2 §2.3).
//
// KEY SHAPE: as the engine posts a key-path action (probe_engine.cpp
// handleEditorAction): KEYINPUT then KEYUP, charCode 0, keyCode = awt Key code
// | Shift 0x1000 | Mod1 0x2000.
//
// SCRIPT is a comma-separated list of steps:
//   k<code>[x<n>]   setup key, n times; settle 600 ms after each
//   r<name>         record the last INVALIDATE_VISIBLE_CURSOR rect as a point
//   X<label>@<trigger>=<op>;<op>;...
//                   MEASURED. Settle 1500 ms, snapshot, post the trigger key,
//                   then the ops as MODE says; settle 2000 ms (cap 15 s),
//                   snapshot. Ops:
//                     K<code>          posted key (KEYINPUT+KEYUP)
//                     U<.uno:Cmd>[|<json>]  postUnoCommand(cmd, json, true)
//                                      (a ` in json stands for a comma):
//                                      the engine's form, synchronous
//                                      (a result listener forces SYNCHRON)
//                     P<text>          paste("text/plain;charset=utf-8")
//                     C<point>[+<dx>]  click DOWN+UP at a recorded point, dx twips to its right
//                     R<point>        synchronous setTextSelection(RESET) at a recorded caret point
//                     I<ms>            idle: seq settles as after any op; uni1f polls doing nothing for
//                                      <ms> (VCL timers run); not a LOK call, no record
//                   After every op returns: the selection type and text and the
//                   whole .uno:Undo payload, read at once ("atReturn").
//   S               saveAs(OUT_URL, "fodt")
//   L               locator: Shift+End then Shift+Home from the caret; last only
//
// Output: JSON lines on stdout ("env", "init", "load", "setup", "point",
// "measured", "saved", "locate", "done"; "fatal" on any failure).
//
// OC_A11Y=1 (SPEC-M3-ordered-commands §15.1, fable ruling 2 §2.1 item 5; opt-in, so the earlier arms'
// output is unchanged when it is unset): after load, setAccessibilityState(view, true), as the engine does
// (probe_engine.cpp ~2205); every op then also reads .uno:Undo and getA11yFocusedParagraph immediately
// before its call ("atStart") and adds the a11y read to "atReturn" -- the caret-delete decider's inputs,
// read in the same poll as the key with no yield between; snapshots and the env/load records carry it too.
//
// Build: g++ -std=c++17 -O2 -Wall -I<libreoffice-26-8>/include oc_native.cpp -ldl -lpthread -o oc-native

#include <dlfcn.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
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

constexpr int kShift = 0x1000;
constexpr int kHome = 1028, kEnd = 1029;
constexpr int kSetupQuietMs = 600;
constexpr int kPreMeasureQuietMs = 1500;
constexpr int kMeasureQuietMs = 2000;
constexpr int kMeasureCapMs = 15000;

enum class Mode { Seq, Queued, Unipoll, Uni1, Uni1Ai, Uni1F };
Mode gMode = Mode::Seq;
const char *modeName() {
  switch (gMode) {
  case Mode::Seq: return "seq";
  case Mode::Queued: return "q";
  case Mode::Unipoll: return "unipoll";
  case Mode::Uni1: return "uni1";
  case Mode::Uni1Ai: return "uni1ai";
  case Mode::Uni1F: return "uni1f";
  }
  return "?";
}
bool unipollMode() {
  return gMode == Mode::Unipoll || gMode == Mode::Uni1 || gMode == Mode::Uni1Ai || gMode == Mode::Uni1F;
}
bool onePerPoll() { return gMode == Mode::Uni1 || gMode == Mode::Uni1Ai; }
bool gReplyPending = false;  // uni1ai's anyInput answer
bool anyInputCallback(void *, int) { return gReplyPending; }

const Clock::time_point gEpoch = Clock::now();
std::mutex gMutex;
struct Cb {
  double t;
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
[[noreturn]] void fatal(const std::string &what, const std::string &extra = "") {
  std::cout << "{\"rec\":\"fatal\",\"what\":" << q(what) << extra << "}" << std::endl;
  std::cout.flush();
  std::_Exit(4);
}

LibreOfficeKit *gKit = nullptr;
LibreOfficeKitDocument *gDoc = nullptr;
std::string gOutUrl;

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
bool gA11y = false;
std::string a11yRead() {
  char *v = gDoc->pClass->getA11yFocusedParagraph(gDoc);
  std::string s = v ? v : "<null>";
  std::free(v);
  return s;
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

struct Snap {
  Sel sel;
  std::string cursor, undo, a11y;
};
Snap snap() {
  return {readSel(), lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR), undoValues(), gA11y ? a11yRead() : ""};
}
std::string snapJson(const Snap &s) {
  std::ostringstream o;
  o << "{\"selType\":" << s.sel.type << ",\"selText\":" << q(s.sel.text) << ",\"cursor\":" << q(s.cursor)
    << ",\"undo\":" << q(s.undo);
  if (gA11y) o << ",\"a11y\":" << q(s.a11y);
  o << "}";
  return o.str();
}

std::string callbacksSince(size_t from, double t0Ms, int *n) {
  std::vector<Cb> copy;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    copy.assign(gCbs.begin() + static_cast<long>(from), gCbs.end());
  }
  std::ostringstream o;
  o << "[";
  *n = static_cast<int>(copy.size());
  for (size_t i = 0; i < copy.size(); ++i)
    o << (i ? "," : "") << "{\"t\":" << (copy[i].t - t0Ms) << ",\"type\":"
      << q(lokCallbackTypeToString(copy[i].type)) << ",\"payload\":" << q(utf8Trunc(copy[i].payload, 400)) << "}";
  o << "]";
  return o.str();
}

std::map<std::string, std::string> gPoints;
bool pointOf(const std::string &spec, long &px, long &py) {
  const auto plus = spec.find('+');
  const std::string name = spec.substr(0, plus);
  const long dx = plus == std::string::npos ? 0 : std::atol(spec.substr(plus + 1).c_str());
  auto it = gPoints.find(name);
  if (it == gPoints.end()) return false;
  long x, y, w, h;
  if (std::sscanf(it->second.c_str(), "%ld, %ld, %ld, %ld", &x, &y, &w, &h) != 4) return false;
  px = x + dx;
  py = y + h / 2;
  return true;
}

// ---- the ops of a measured sequence ------------------------------------------------

struct Op {
  char kind;  // K U P C R I F G H
  std::string arg, json;
  std::string fallback;  // 083 addition 5: H only
};
std::vector<Op> parseOps(const std::string &s) {
  std::vector<Op> ops;
  std::stringstream ss(s);
  std::string one;
  while (std::getline(ss, one, ';')) {
    if (one.empty()) continue;
    Op op{one[0], one.substr(1), ""};
    if (op.kind == 'H') {  // 083 addition 5
      const auto tilde = op.arg.rfind('~');
      if (tilde == std::string::npos) fatal("H needs ~<fallback>", ",\"op\":" + q(one));
      op.fallback = op.arg.substr(tilde + 1);
      op.arg = op.arg.substr(0, tilde);
    }
    if (op.kind == 'U' || op.kind == 'F' || op.kind == 'G' || op.kind == 'H') {
      const auto bar = op.arg.find('|');
      if (bar != std::string::npos) {
        op.json = op.arg.substr(bar + 1);
        op.arg = op.arg.substr(0, bar);
        for (char &c : op.json)
          if (c == '`') c = ',';
      }
    }
    if (std::string("KUPCRIFGH").find(op.kind) == std::string::npos) fatal("unknown op", ",\"op\":" + q(one));
    ops.push_back(op);
  }
  return ops;
}

// Runs one op and returns its record, with the state read the moment the call returned.
std::string runOp(const Op &op, double t0) {
  // OC_A11Y: the decider's "before" inputs, read just before the call, nothing in between
  const std::string undoAtStart = gA11y ? undoValues() : "", a11yAtStart = gA11y ? a11yRead() : "";
  const size_t cbAtStart = cbCount();
  std::string formatRecord;
  const bool format = op.kind == 'F' || op.kind == 'G' || op.kind == 'H';
  const std::string undoBeforeFormat = format ? undoValues() : "";
  const double tStart = nowMs();
  if (op.kind == 'K') {
    post(std::atoi(op.arg.c_str()));
  } else if (op.kind == 'U') {
    gDoc->pClass->postUnoCommand(gDoc, op.arg.c_str(), op.json.empty() ? nullptr : op.json.c_str(), true);
  } else if (op.kind == 'P') {
    gDoc->pClass->paste(gDoc, "text/plain;charset=utf-8", op.arg.c_str(), op.arg.size());
  } else if (op.kind == 'I') {
    // idle: only seq and uni1f give it a meaning (a settle); elsewhere it is a no-op
  } else if (op.kind == 'C') {
    long x, y;
    if (!pointOf(op.arg, x, y)) fatal("no point", ",\"name\":" + q(op.arg));
    gDoc->pClass->postMouseEvent(gDoc, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0);
    gDoc->pClass->postMouseEvent(gDoc, LOK_MOUSEEVENT_MOUSEBUTTONUP, x, y, 1, 1, 0);
  } else if (format) {
    // 176 addition 1: ordered_format.inc's collapsed-caret sequence, no read or yield inserted.
    const std::string caret = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
    long x = 0, y = 0, w = 0, h = 0;
    const bool pointValid = std::sscanf(caret.c_str(), "%ld, %ld, %ld, %ld", &x, &y, &w, &h) == 4;
    const long py = y + h / 2;
    auto restore = [&] {
      if (!pointValid) return;
      gDoc->pClass->setTextSelection(gDoc, LOK_SETTEXTSELECTION_RESET, x, py);
      gDoc->pClass->setTextSelection(gDoc, LOK_SETTEXTSELECTION_START, x, py);
      gDoc->pClass->setTextSelection(gDoc, LOK_SETTEXTSELECTION_RESET, x, py);
    };
    gDoc->pClass->postUnoCommand(gDoc, op.arg.c_str(), op.json.empty() ? nullptr : op.json.c_str(), true);
    const size_t cbAfterDispatch = cbCount();
    if (op.kind == 'F') restore();
    gDoc->pClass->postUnoCommand(gDoc, ".uno:SelectText", nullptr, true);
    const Sel selected = readSel();
    std::string html;
    if (selected.type == LOK_SELTYPE_TEXT) {
      char *markup = gDoc->pClass->getTextSelection(gDoc, "text/html", nullptr);
      html = markup ? markup : "";
      std::free(markup);
    }
    // 083 addition 5: on the 083 path only, the fallback selection and its read; no read or yield
    // inserted between the select's read and the fallback, nor between the fallback and the restore.
    bool fallbackRan = false;
    Sel fallbackSel;
    std::string fallbackHtml;
    double fallbackPostMs = -1, fallbackHtmlMs = -1;
    size_t cbBeforeFallback = 0;
    if (op.kind == 'H' && selected.type == LOK_SELTYPE_NONE) {
      fallbackRan = true;
      cbBeforeFallback = cbCount();
      const double posted = nowMs();
      gDoc->pClass->postUnoCommand(gDoc, op.fallback.c_str(), nullptr, true);
      fallbackPostMs = nowMs() - posted;
      fallbackSel = readSel();
      if (fallbackSel.type == LOK_SELTYPE_TEXT) {
        const double asked = nowMs();
        char *markup = gDoc->pClass->getTextSelection(gDoc, "text/html", nullptr);
        fallbackHtmlMs = nowMs() - asked;
        fallbackHtml = markup ? markup : "";
        std::free(markup);
      }
    }
    restore();
    const Sel restored = readSel();
    std::ostringstream f;
    f << ",\"format\":{\"caret\":" << q(caret) << ",\"pointValid\":" << (pointValid ? "true" : "false")
      << ",\"x\":" << x << ",\"y\":" << py << ",\"cbIndexAfterDispatch\":" << cbAfterDispatch
      << ",\"selectedType\":" << selected.type << ",\"selectedText\":" << q(selected.text)
      << ",\"htmlBytes\":" << html.size() << ",\"html\":" << q(utf8Trunc(html, 4000))
      << ",\"restoredType\":" << restored.type << ",\"undoAtStart\":" << q(undoBeforeFormat)
      << ",\"restoreBeforeSelect\":" << (op.kind == 'F' ? "true" : "false");
    if (op.kind == 'H')
      f << ",\"fallback\":{\"command\":" << q(op.fallback) << ",\"ran\":" << (fallbackRan ? "true" : "false")
        << ",\"cbIndexBefore\":" << cbBeforeFallback << ",\"postMs\":" << fallbackPostMs
        << ",\"type\":" << fallbackSel.type << ",\"textBytes\":" << fallbackSel.text.size()
        << ",\"text\":" << q(utf8Trunc(fallbackSel.text, 4000)) << ",\"htmlMs\":" << fallbackHtmlMs
        << ",\"htmlBytes\":" << fallbackHtml.size() << ",\"html\":" << q(utf8Trunc(fallbackHtml, 1 << 20))
        << "}";
    f << "}";
    formatRecord = f.str();
  } else if (op.kind == 'R') {
    long x, y;
    if (!pointOf(op.arg, x, y)) fatal("no reset point", ",\"name\":" + q(op.arg));
    gDoc->pClass->setTextSelection(gDoc, LOK_SETTEXTSELECTION_RESET, x, y);
  }
  const double tReturned = nowMs();
  const size_t cbAtReturn = cbCount();
  const Sel s = readSel();
  const std::string undo = undoValues();
  const std::string a11y = gA11y ? a11yRead() : "";
  std::ostringstream o;
  o << "{\"op\":" << q(std::string(1, op.kind) + op.arg) << ",\"startMs\":" << (tStart - t0)
    << ",\"returnedMs\":" << (tReturned - t0)
    << ",\"cbIndexAtStart\":" << cbAtStart << ",\"cbIndexAtReturn\":" << cbAtReturn << formatRecord;
  if (gA11y) o << ",\"atStart\":{\"undo\":" << q(undoAtStart) << ",\"a11y\":" << q(a11yAtStart) << "}";
  o << ",\"atReturn\":{\"selType\":" << s.type << ",\"selText\":" << q(s.text) << ",\"undo\":" << q(undo);
  if (gA11y) o << ",\"a11y\":" << q(a11y);
  o << "}}";
  return o.str();
}

// ---- q mode: the ops fire inside the trigger's first cursor callback ----------------

std::vector<Op> gArmedOps;
bool gArmed = false, gFired = false;
double gFiredMs = -1, gArmT0 = 0;
std::vector<std::string> gFiredRecords;

void onCallback(int type, const char *payload, void *) {
  bool fire = false;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    gLastAt = Clock::now();
    std::string p = payload ? payload : "";
    gCbs.push_back({msBetween(gEpoch, gLastAt), type, p});
    gLast[type] = p;
    if (gArmed && type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR) {
      gArmed = false;
      fire = true;
      gFiredMs = nowMs();
    }
  }
  if (fire) {
    std::vector<std::string> recs;
    for (const Op &op : gArmedOps) recs.push_back(runOp(op, gArmT0));
    std::lock_guard<std::mutex> lock(gMutex);
    gFiredRecords = recs;
    gFired = true;
  }
}

// ---- steps ------------------------------------------------------------------------

// A step does its LOK calls and then asks for a quiet window (0 = none).
struct Settle {
  int quietMs = 0, capMs = 0;
  int fixedMs = 0;  // uni1/uni1ai: wait this long whatever arrives
};
struct Step {
  std::string text;
  std::function<Settle()> run;
};
std::vector<Step> gSteps;
double gLastSettleMs = 0;  // filled by the executor after each settle

void emitSetup(const std::string &step, const std::string &extra = "") {
  std::cout << "{\"rec\":\"setup\",\"step\":" << q(step) << ",\"settleMs\":" << gLastSettleMs
            << ",\"cursor\":" << q(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)) << extra << "}" << std::endl;
}

// Measured-step state shared by its micro-steps.
struct Measured {
  std::string label;
  int trigger = 0;
  std::vector<Op> ops;
  Snap before;
  size_t from = 0;
  double t0 = 0, preQuietMs = 0;
  std::vector<std::string> opRecords;
  bool fired = true;
  // uni1/uni1ai, per op being measured
  double opReturnedMs = 0, firstPollMs = 0;
  size_t firstPollIndex = 0;
  std::string pendingOp;
};

void settleBlocking(const Settle &s) {
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
    if (msBetween(last, now) >= s.quietMs && waited >= s.quietMs) {
      gLastSettleMs = waited;
      return;
    }
    if (waited > s.capMs) {
      gLastSettleMs = -waited;
      return;
    }
  }
}

void addSteps(const std::string &script) {
  std::stringstream steps(script);
  std::string step;
  while (std::getline(steps, step, ',')) {
    if (step.empty()) continue;
    const char op = step[0];
    const std::string arg = step.substr(1);
    if (op == 'k') {
      const auto x = arg.find('x');
      const int code = std::atoi(arg.substr(0, x).c_str());
      const int times = x == std::string::npos ? 1 : std::atoi(arg.substr(x + 1).c_str());
      for (int i = 0; i < times; ++i)
        gSteps.push_back({step, [code] { post(code); return Settle{kSetupQuietMs, 5000}; }});
      gSteps.push_back({step, [step] { emitSetup(step); return Settle{}; }});
    } else if (op == 'r') {
      gSteps.push_back({step, [] { return Settle{kSetupQuietMs, 5000}; }});
      gSteps.push_back({step, [arg] {
                          gPoints[arg] = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
                          std::cout << "{\"rec\":\"point\",\"name\":" << q(arg) << ",\"rect\":" << q(gPoints[arg])
                                    << "}" << std::endl;
                          return Settle{};
                        }});
    } else if (op == 'X') {
      const auto at = arg.find('@'), eq = arg.find('=');
      if (at == std::string::npos || eq == std::string::npos || eq < at) fatal("bad X step", ",\"step\":" + q(step));
      auto m = std::make_shared<Measured>();
      m->label = arg.substr(0, at);
      m->trigger = std::atoi(arg.substr(at + 1, eq - at - 1).c_str());
      m->ops = parseOps(arg.substr(eq + 1));
      gSteps.push_back({step, [] { return Settle{kPreMeasureQuietMs, 10000}; }});
      gSteps.push_back({step, [m] {
                          m->preQuietMs = gLastSettleMs;
                          m->before = snap();
                          m->from = cbCount();
                          m->t0 = nowMs();
                          if (gMode == Mode::Queued) {
                            {
                              std::lock_guard<std::mutex> lock(gMutex);
                              gArmedOps = m->ops;
                              gArmT0 = m->t0;
                              gFired = false;
                              gArmed = true;
                            }
                            post(m->trigger);
                            bool fired = false;
                            for (int i = 0; i < 250 && !fired; ++i) {
                              sleepMs(20);
                              std::lock_guard<std::mutex> lock(gMutex);
                              fired = gFired;
                            }
                            std::lock_guard<std::mutex> lock(gMutex);
                            gArmed = false;
                            m->fired = fired;
                            m->opRecords = gFiredRecords;
                            return Settle{kMeasureQuietMs, kMeasureCapMs};
                          }
                          post(m->trigger);
                          if (onePerPoll() || gMode == Mode::Uni1F) return Settle{kSetupQuietMs, 5000};
                          if (gMode == Mode::Unipoll) {
                            for (const Op &op : m->ops) m->opRecords.push_back(runOp(op, m->t0));
                            return Settle{kMeasureQuietMs, kMeasureCapMs};
                          }
                          return Settle{kSetupQuietMs, 5000};  // seq: the trigger settles first
                        }});
      {
        // seq: one op per step, each settled before the next. Other modes: no-ops.
        for (size_t i = 0; i < m->ops.size(); ++i)
          gSteps.push_back({step, [m, i] {
                              if (gMode != Mode::Seq) return Settle{};
                              if (m->ops[i].kind == 'I')  // seq: an idle is one more settle
                                return i + 1 == m->ops.size() ? Settle{kMeasureQuietMs, kMeasureCapMs}
                                                              : Settle{kSetupQuietMs, 5000};
                              m->opRecords.push_back(runOp(m->ops[i], m->t0));
                              return i + 1 == m->ops.size() ? Settle{kMeasureQuietMs, kMeasureCapMs}
                                                            : Settle{kSetupQuietMs, 5000};
                            }});
        // uni1/uni1ai: the op in its own poll; the next poll is its first poll after
        // return; then a fixed 1500 ms idle; then its late callbacks are recorded.
        for (size_t i = 0; i < m->ops.size(); ++i) {
          gSteps.push_back({step, [m, i] {
                              if (!onePerPoll()) return Settle{};
                              m->pendingOp = runOp(m->ops[i], m->t0);
                              m->opReturnedMs = nowMs();
                              if (gMode == Mode::Uni1Ai) gReplyPending = true;
                              return Settle{};
                            }});
          gSteps.push_back({step, [m] {
                              if (!onePerPoll()) return Settle{};
                              m->firstPollMs = nowMs();
                              m->firstPollIndex = cbCount();
                              gReplyPending = false;
                              Settle s;
                              s.fixedMs = 1500;
                              return s;
                            }});
          gSteps.push_back({step, [m, i] {
                              if (!onePerPoll()) return Settle{};
                              int nLate = 0;
                              const std::string late = callbacksSince(m->firstPollIndex, m->firstPollMs, &nLate);
                              std::string rec = m->pendingOp;
                              rec.pop_back();
                              std::ostringstream o;
                              o << rec << ",\"firstPollAfterReturnMs\":" << (m->firstPollMs - m->opReturnedMs)
                                << ",\"cbIndexAtFirstPoll\":" << m->firstPollIndex
                                << ",\"lateCallbacks\":" << late << "}";
                              m->opRecords.push_back(o.str());
                              return i + 1 == m->ops.size() ? Settle{kMeasureQuietMs, kMeasureCapMs} : Settle{};
                            }});
        }
        // uni1f: the op in its own poll, the next op at the next poll; I<ms> polls doing nothing.
        for (size_t i = 0; i < m->ops.size(); ++i)
          gSteps.push_back({step, [m, i] {
                              if (gMode != Mode::Uni1F) return Settle{};
                              const bool last = i + 1 == m->ops.size();
                              if (m->ops[i].kind == 'I') {
                                if (last) return Settle{kMeasureQuietMs, kMeasureCapMs};
                                Settle s;
                                s.fixedMs = std::atoi(m->ops[i].arg.c_str());
                                return s;
                              }
                              m->opRecords.push_back(runOp(m->ops[i], m->t0));
                              return last ? Settle{kMeasureQuietMs, kMeasureCapMs} : Settle{};
                            }});
      }
      gSteps.push_back({step, [m] {
                          const double windowMs = nowMs() - m->t0;
                          const Snap after = snap();
                          int n = 0;
                          const std::string cbs = callbacksSince(m->from, m->t0, &n);
                          std::ostringstream ops;
                          for (size_t i = 0; i < m->opRecords.size(); ++i) ops << (i ? "," : "") << m->opRecords[i];
                          std::cout << "{\"rec\":\"measured\",\"label\":" << q(m->label) << ",\"mode\":"
                                    << q(modeName()) << ",\"trigger\":" << m->trigger << ",\"fired\":"
                                    << (m->fired ? "true" : "false") << ",\"preQuietMs\":" << m->preQuietMs
                                    << ",\"settleMs\":" << gLastSettleMs << ",\"capped\":"
                                    << (gLastSettleMs < 0 ? "true" : "false") << ",\"windowMs\":" << windowMs
                                    << ",\"ops\":[" << ops.str() << "],\"before\":" << snapJson(m->before)
                                    << ",\"after\":" << snapJson(after) << ",\"nCallbacks\":" << n
                                    << ",\"callbacks\":" << cbs << "}" << std::endl;
                          return Settle{};
                        }});
    } else if (op == 'S') {
      gSteps.push_back({step, [] { return Settle{kSetupQuietMs, 5000}; }});
      gSteps.push_back({step, [] {
                          const bool ok = gDoc->pClass->saveAs(gDoc, gOutUrl.c_str(), "fodt", nullptr);
                          std::cout << "{\"rec\":\"saved\",\"ok\":" << (ok ? "true" : "false") << "}" << std::endl;
                          return Settle{};
                        }});
    } else if (op == 'L') {
      auto sel = std::make_shared<std::vector<std::string>>();
      gSteps.push_back({step, [] { return Settle{kPreMeasureQuietMs, 10000}; }});
      gSteps.push_back({step, [sel] { sel->push_back(readSel().text); post(kEnd | kShift); return Settle{kSetupQuietMs, 5000}; }});
      gSteps.push_back({step, [sel] { sel->push_back(readSel().text); post(kHome | kShift); return Settle{kSetupQuietMs, 5000}; }});
      gSteps.push_back({step, [sel] {
                          std::cout << "{\"rec\":\"locate\",\"selBefore\":" << q((*sel)[0]) << ",\"suffix\":"
                                    << q((*sel)[1]) << ",\"prefix\":" << q(readSel().text) << "}" << std::endl;
                          return Settle{};
                        }});
    } else {
      fatal("unknown step", ",\"step\":" + q(step));
    }
  }
}

void finish() {
  std::cout << "{\"rec\":\"done\",\"ms\":" << nowMs() << "}" << std::endl;
  std::cout.flush();
  std::_Exit(0);
}

// ---- the document, loaded by either executor ----------------------------------------

std::string gDocUrl;
void loadDocument() {
  const double tLoad = nowMs();
  gDoc = gKit->pClass->documentLoad(gKit, gDocUrl.c_str());
  if (!gDoc) fatal("documentLoad");
  gDoc->pClass->initializeForRendering(gDoc, "{}");
  gDoc->pClass->registerCallback(gDoc, onCallback, nullptr);
  if (gA11y) gDoc->pClass->setAccessibilityState(gDoc, gDoc->pClass->getView(gDoc), true);
  std::string px(256 * 256 * 4, '\0');
  gDoc->pClass->paintTile(gDoc, reinterpret_cast<unsigned char *>(px.data()), 256, 256, 0, 0, 3840, 3840);
  std::cout << "{\"rec\":\"load\",\"loadMs\":" << (nowMs() - tLoad) << ",\"undo\":" << q(undoValues());
  if (gA11y) std::cout << ",\"a11y\":" << q(a11yRead());
  std::cout << "}" << std::endl;
}

// ---- unipoll executor: one micro-step per poll call ---------------------------------

size_t gNext = 0;
bool gLoaded = false, gWaiting = false;
Settle gWait;
Clock::time_point gWaitStart;
long gPolls = 0;

int pollCallback(void *, int timeoutUs) {
  ++gPolls;
  if (!gLoaded) {
    gLoaded = true;
    loadDocument();
    gWaiting = true;
    gWait = Settle{kPreMeasureQuietMs, 10000};
    gWaitStart = Clock::now();
    return 1;
  }
  if (gWaiting) {
    Clock::time_point last;
    {
      std::lock_guard<std::mutex> lock(gMutex);
      last = gLastAt;
    }
    const auto now = Clock::now();
    const double waited = msBetween(gWaitStart, now);
    const bool quiet = gWait.fixedMs > 0 ? waited >= gWait.fixedMs
                                         : msBetween(last, now) >= gWait.quietMs && waited >= gWait.quietMs;
    if (!quiet && (gWait.fixedMs > 0 || waited <= gWait.capMs)) {
      int sleep = 5;
      if (timeoutUs >= 0 && timeoutUs / 1000 < sleep) sleep = timeoutUs / 1000;
      if (sleep > 0) sleepMs(sleep);
      return 0;
    }
    gLastSettleMs = quiet ? waited : -waited;
    gWaiting = false;
  }
  if (gNext >= gSteps.size()) finish();
  const Settle s = gSteps[gNext++].run();
  if (s.quietMs > 0 || s.fixedMs > 0) {
    gWaiting = true;
    gWait = s;
    gWaitStart = Clock::now();
  }
  return 1;
}
void wakeCallback(void *) {}

}  // namespace

int main(int argc, char **argv) {
  if (argc != 7) {
    std::cerr << "usage: oc-native seq|q|unipoll|uni1|uni1ai INSTALL PROFILE_URL DOC_URL SCRIPT OUT_URL\n";
    return 64;
  }
  const std::string mode = argv[1];
  if (mode == "seq") gMode = Mode::Seq;
  else if (mode == "q") gMode = Mode::Queued;
  else if (mode == "unipoll") gMode = Mode::Unipoll;
  else if (mode == "uni1") gMode = Mode::Uni1;
  else if (mode == "uni1ai") gMode = Mode::Uni1Ai;
  else if (mode == "uni1f") gMode = Mode::Uni1F;
  else {
    std::cerr << "unknown mode " << mode << "\n";
    return 64;
  }
  gDocUrl = argv[4];
  gOutUrl = argv[6];
  const char *envs[] = {"SAL_USE_VCLPLUGIN", "SAL_LOK_OPTIONS", "LANG", "LC_ALL", "LANGUAGE", "SAL_LOG"};
  std::cout << "{\"rec\":\"env\",\"mode\":" << q(mode) << ",\"install\":" << q(argv[2]) << ",\"profile\":"
            << q(argv[3]) << ",\"doc\":" << q(argv[4]) << ",\"script\":" << q(argv[5]) << ",\"out\":" << q(argv[6]);
  for (const char *e : envs) {
    const char *v = std::getenv(e);
    std::cout << ",\"" << e << "\":" << (v ? q(v) : std::string("null"));
  }
  gA11y = std::getenv("OC_A11Y") && std::string(std::getenv("OC_A11Y")) == "1";
  if (gA11y) std::cout << ",\"OC_A11Y\":\"1\"";
  std::cout << "}" << std::endl;
  addSteps(argv[5]);

  gKit = lok_init_2(argv[2], argv[3]);
  if (!gKit) fatal("lok_init_2");

  if (!unipollMode()) {
    loadDocument();
    settleBlocking({kPreMeasureQuietMs, 10000});
    for (Step &s : gSteps) {
      const Settle w = s.run();
      if (w.quietMs > 0) settleBlocking(w);
    }
    finish();
  }

  // unipoll: lo_runLoop's registrations without its soffice_main (see the
  // header), then enter the VCL loop ourselves. This thread holds the
  // SolarMutex from InitVCL (vcl/source/app/svmain.cxx:308), as lo_runLoop's
  // guard would.
  const std::string lib = std::string(argv[2]) + "/libmergedlo.so";
  void *h = dlopen(lib.c_str(), RTLD_NOW | RTLD_NOLOAD);
  if (!h) fatal("libmergedlo.so not loaded", ",\"lib\":" + q(lib));
  using Reg = void (*)(int (*)(void *, int), void (*)(void *), void *);
  auto reg = reinterpret_cast<Reg>(dlsym(h, "_ZN3vcl3lok21registerPollCallbacksEPFiPviEPFvS1_ES1_"));
  auto views = reinterpret_cast<void (*)()>(dlsym(h, "_ZN12SfxLokHelper21registerViewCallbacksEv"));
  auto mainThread = reinterpret_cast<void (*)()>(dlsym(h, "_ZN11Application16UpdateMainThreadEv"));
  auto execute = reinterpret_cast<void (*)()>(dlsym(h, "_ZN11Application7ExecuteEv"));
  auto sfxApp = reinterpret_cast<void *(*)()>(dlsym(h, "_ZN14SfxApplication11GetOrCreateEv"));
  std::cout << "{\"rec\":\"init\",\"registerPollCallbacks\":" << (reg ? "true" : "false")
            << ",\"registerViewCallbacks\":" << (views ? "true" : "false") << ",\"updateMainThread\":"
            << (mainThread ? "true" : "false") << ",\"execute\":" << (execute ? "true" : "false")
            << ",\"sfxApplicationGetOrCreate\":" << (sfxApp ? "true" : "false")
            << ",\"anyInputRegistered\":" << (gMode == Mode::Uni1Ai ? "true" : "false")
            << ",\"sofficeMainSkipped\":true}" << std::endl;
  if (!reg || !views || !mainThread || !execute || !sfxApp) fatal("a registration symbol is missing");
  reg(pollCallback, wakeCallback, &gPolls);
  if (gMode == Mode::Uni1Ai) gKit->pClass->registerAnyInputCallback(gKit, anyInputCallback, &gPolls);
  views();
  mainThread();
  sfxApp();
  execute();
  fatal("Application::Execute returned");
}
