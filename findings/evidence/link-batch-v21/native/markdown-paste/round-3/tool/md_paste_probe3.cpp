// Round 3 (link batch v21 shakedown, ARMS-item2.md DM-5 and DM-17 C): round 2's
// md_paste_probe2.cpp with two additions and nothing else changed:
//   - every callback that arrives while PLACE runs (and its settle) is kept and
//     printed as {"probe":"place-callbacks",...}: does a click on an image or a
//     frame send TEXT_SELECTION (with rectangles or empty), GRAPHIC_SELECTION, a
//     cursor? (the WASM engine's "collapsed" cache reads TEXT_SELECTION only);
//   - the position line also carries getSelectionTypeAndText() (type, whether
//     the text came back, the text) -- the call the WASM engine's readSelection()
//     makes -- and the last TEXT_SELECTION / GRAPHIC_SELECTION payloads.
// Below is round 2's header, unchanged.
//
// Markdown paste through LibreOfficeKit, round 2 (link batch v21): positions
// round 1 did not measure (table cells, a page header, a range over two cells)
// and pastes that may add no undo action (protected content, read-only views).
// One process = one fresh profile = one document = one paste.
//
// Starts from round 1's md_paste_probe.cpp (same paste call, callback record,
// undo walk, saves, watchdog). What is new:
//   - the caret is placed by two step scripts instead of a fixed position name:
//     SETUP runs once after load (it may record caret rectangles as points),
//     PLACE runs before the read-back and again before the paste, so it must
//     reach the same place from any state (it starts from an absolute anchor:
//     Ctrl+Home pressed until the document start, or a click at a recorded
//     point). Steps, comma separated:
//       k<code>[x<n>]   key, KEYINPUT+KEYUP as probe_engine.cpp posts it; 80 ms
//                       after each (round 1's spacing); a Mod1 key also waits
//                       for 400 ms of callback quiet (finding 142: Ctrl+Home is
//                       not FIFO with keys Writer handles itself)
//       u<.uno:Cmd>     postUnoCommand without notification, then quiet 600 ms
//       r<name>         record the last INVALIDATE_VISIBLE_CURSOR rect as a point
//       c<name>         click DOWN+UP (count 1, button 1) at the point (x, y+h/2),
//                       as finding 142's probe does; then quiet 600 ms
//       a<x>:<y>        the same click at absolute twips
//   - READBACK: "end" = Shift+End and read the selection, then PLACE again;
//     "sel" = read the selection as placed (ranges); "none".
//   - FLAGS (comma list, or "-"): "viewro" = setViewReadOnly(view, true) after
//     the read-back and before the paste (Collabora's read-only viewer);
//     "typekey" = a CONTROL: instead of paste(), post one typed "x" (KEYINPUT +
//     KEYUP, charCode 'x', keyCode css::awt::Key::X = 535) -- used to show
//     whether a read-only view refuses ordinary typing at all.
//   - Before and after the paste it prints the raw getCommandValues(".uno:Undo")
//     and (".uno:ReadOnly") strings, the selection type and text, the caret
//     rectangle and the last ".uno:Paste" state callback, so the runner can say
//     whether the undo payload changed at all.
//
// Usage:
//   md-paste-probe2 INSTALL PROFILE_URL DOC_URL OUT_DIR MIME PAYLOAD_FILE SETUP PLACE READBACK FLAGS [WATCHDOG_S]
//
// It says nothing about WASM.

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <dlfcn.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace {

constexpr int kShift = 0x1000;  // KEY_SHIFT
constexpr int kMod1 = 0x2000;   // KEY_MOD1
constexpr int kEnd = 1029;

using Clock = std::chrono::steady_clock;

std::string jsonEscape(const std::string &value) {
  std::string out;
  for (const char character : value) {
    switch (character) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': out += "\\r"; break;
    case '\t': out += "\\t"; break;
    default:
      if (static_cast<unsigned char>(character) < 0x20) {
        char buffer[8];
        std::snprintf(buffer, sizeof(buffer), "\\u%04x",
                      static_cast<unsigned char>(character));
        out += buffer;
      } else {
        out += character;
      }
    }
  }
  return out;
}

std::string shortPayload(const std::string &payload, std::size_t limit = 160) {
  if (payload.size() <= limit)
    return payload;
  std::size_t cut = limit;
  while (cut > 0 && (static_cast<unsigned char>(payload[cut]) & 0xc0) == 0x80)
    --cut;
  return payload.substr(0, cut) + "...(" + std::to_string(payload.size()) + "B)";
}

struct CallbackRecord {
  int type;
  double ms;
  bool duringCall;
  std::string payload;
};

std::mutex gMutex;
std::vector<CallbackRecord> gCallbacks;
std::vector<std::string> gUnoResults;
std::map<int, std::string> gLastByType;
std::string gLastUndoState;
std::string gLastPasteState;
Clock::time_point gLastAt = Clock::now();
Clock::time_point gPasteStart;
std::atomic<bool> gPasteStarted{false};
std::atomic<bool> gInCall{false};
long gCoreLogCount = 0;
double gCoreLogFirstMs = 0;
double gCoreLogLastMs = 0;
std::map<std::string, std::string> gPoints;
std::atomic<bool> gPlaceCapture{false};
std::vector<CallbackRecord> gPlaceCallbacks;
Clock::time_point gPlaceStart;

double msSince(Clock::time_point start) {
  return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  const std::string text = payload ? payload : "";
  gLastAt = Clock::now();
  if (type != LOK_CALLBACK_CORE_LOG)
    gLastByType[type] = text;
  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT)
    gUnoResults.push_back(text);
  if (type == LOK_CALLBACK_STATE_CHANGED && text.rfind(".uno:Undo=", 0) == 0)
    gLastUndoState = text;
  if (type == LOK_CALLBACK_STATE_CHANGED && text.rfind(".uno:Paste=", 0) == 0)
    gLastPasteState = text;
  if (gPlaceCapture.load() && type != LOK_CALLBACK_CORE_LOG && gPlaceCallbacks.size() < 400)
    gPlaceCallbacks.push_back({type, msSince(gPlaceStart), false, text});
  if (!gPasteStarted.load())
    return;
  if (type == LOK_CALLBACK_CORE_LOG) {
    const double ms = msSince(gPasteStart);
    if (gCoreLogCount == 0)
      gCoreLogFirstMs = ms;
    gCoreLogLastMs = ms;
    if (gCoreLogCount < 3)
      gCallbacks.push_back({type, ms, gInCall.load(), text});
    ++gCoreLogCount;
    return;
  }
  gCallbacks.push_back({type, msSince(gPasteStart), gInCall.load(), text});
}

std::string lastOf(int type) {
  std::lock_guard<std::mutex> lock(gMutex);
  auto it = gLastByType.find(type);
  return it == gLastByType.end() ? std::string() : it->second;
}

std::string coreLogJson() {
  std::lock_guard<std::mutex> lock(gMutex);
  char buffer[160];
  std::snprintf(buffer, sizeof(buffer),
                "{\"count\":%ld,\"firstMs\":%.1f,\"lastMs\":%.1f,\"kept\":%ld}",
                gCoreLogCount, gCoreLogFirstMs, gCoreLogLastMs,
                gCoreLogCount < 3 ? gCoreLogCount : 3L);
  return buffer;
}

std::string callbacksJson(const std::vector<CallbackRecord> *list = nullptr) {
  std::lock_guard<std::mutex> lock(gMutex);
  const std::vector<CallbackRecord> &records = list ? *list : gCallbacks;
  std::string out = "[";
  for (std::size_t i = 0; i < records.size(); ++i) {
    const CallbackRecord &r = records[i];
    char ms[32];
    std::snprintf(ms, sizeof(ms), "%.1f", r.ms);
    out += (i ? "," : "") + std::string("{\"type\":") + std::to_string(r.type) +
           ",\"name\":\"" + lokCallbackTypeToString(r.type) + "\",\"ms\":" + ms +
           ",\"duringCall\":" + (r.duringCall ? "true" : "false") +
           ",\"payload\":\"" + jsonEscape(shortPayload(r.payload)) + "\"}";
  }
  return out + "]";
}

void emit(const std::string &line) {
  std::cout << line << "\n";
  std::cout.flush();
}

class Watchdog {
public:
  explicit Watchdog(int seconds) : mSeconds(seconds), mThread([this] { run(); }) {}
  void arm(const std::string &label) {
    std::lock_guard<std::mutex> lock(mMutex);
    mLabel = label;
    mArmedAt = Clock::now();
    mArmed = true;
    mCv.notify_all();
  }
  void disarm() {
    std::lock_guard<std::mutex> lock(mMutex);
    mArmed = false;
    mCv.notify_all();
  }
  void detach() { mThread.detach(); }

private:
  void run() {
    std::unique_lock<std::mutex> lock(mMutex);
    for (;;) {
      mCv.wait(lock, [this] { return mArmed; });
      const auto deadline = mArmedAt + std::chrono::seconds(mSeconds);
      const auto armedAt = mArmedAt;
      if (mCv.wait_until(lock, deadline, [this, armedAt] {
            return !mArmed || mArmedAt != armedAt;
          }))
        continue;
      const std::string label = mLabel;
      lock.unlock();
      emit("{\"probe\":\"blocked\",\"step\":\"" + label + "\",\"afterMs\":" +
           std::to_string(static_cast<long>(msSince(armedAt))) +
           ",\"callbacks\":" + callbacksJson() + "}");
      std::fflush(nullptr);
      _exit(124);
    }
  }
  int mSeconds;
  std::mutex mMutex;
  std::condition_variable mCv;
  std::string mLabel;
  Clock::time_point mArmedAt;
  bool mArmed = false;
  std::thread mThread;
};

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

// Wait until no callback for quietMs (and at least quietMs in total), cap capMs.
double settle(int quietMs, int capMs) {
  const auto start = Clock::now();
  for (;;) {
    drain(20);
    Clock::time_point last;
    {
      std::lock_guard<std::mutex> lock(gMutex);
      last = gLastAt;
    }
    const double waited = msSince(start);
    if (std::chrono::duration<double, std::milli>(Clock::now() - last).count() >= quietMs &&
        waited >= quietMs)
      return waited;
    if (waited > capMs)
      return -waited;
  }
}

LibreOfficeKitDocument *gDoc = nullptr;

void key(int code) {
  gDoc->pClass->postKeyEvent(gDoc, LOK_KEYEVENT_KEYINPUT, 0, code);
  gDoc->pClass->postKeyEvent(gDoc, LOK_KEYEVENT_KEYUP, 0, code);
  drain(80);
  if (code & kMod1)
    settle(400, 5000);
}

bool parseRect(const std::string &rect, long &x, long &y, long &w, long &h) {
  return std::sscanf(rect.c_str(), "%ld, %ld, %ld, %ld", &x, &y, &w, &h) == 4;
}

void click(long x, long y) {
  gDoc->pClass->postMouseEvent(gDoc, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, x, y, 1, 1, 0);
  gDoc->pClass->postMouseEvent(gDoc, LOK_MOUSEEVENT_MOUSEBUTTONUP, x, y, 1, 1, 0);
  settle(600, 5000);
}

// Runs a step script; returns a JSON array describing what each step did.
std::string runScript(const std::string &script, const std::string &label) {
  std::string out = "[";
  if (script.empty() || script == "-")
    return "[]";
  std::stringstream steps(script);
  std::string step;
  bool first = true;
  while (std::getline(steps, step, ',')) {
    if (step.empty())
      continue;
    const char op = step[0];
    const std::string arg = step.substr(1);
    std::string extra;
    if (op == 'k') {
      int times = 1;
      const auto x = arg.find('x');
      const int code = std::atoi(arg.substr(0, x).c_str());
      if (x != std::string::npos)
        times = std::atoi(arg.substr(x + 1).c_str());
      for (int i = 0; i < times; ++i)
        key(code);
    } else if (op == 'u') {
      gDoc->pClass->postUnoCommand(gDoc, arg.c_str(), nullptr, false);
      settle(600, 5000);
    } else if (op == 'r') {
      settle(300, 5000);
      gPoints[arg] = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
      extra = ",\"rect\":\"" + jsonEscape(gPoints[arg]) + "\"";
    } else if (op == 'c') {
      long x, y, w, h;
      if (!parseRect(gPoints[arg], x, y, w, h)) {
        emit("{\"probe\":\"error\",\"what\":\"no point " + jsonEscape(arg) + "\"}");
        _exit(66);
      }
      click(x, y + h / 2);
      extra = ",\"x\":" + std::to_string(x) + ",\"y\":" + std::to_string(y + h / 2);
    } else if (op == 'a') {
      long x = 0, y = 0;
      if (std::sscanf(arg.c_str(), "%ld:%ld", &x, &y) != 2) {
        emit("{\"probe\":\"error\",\"what\":\"bad absolute point " + jsonEscape(arg) + "\"}");
        _exit(66);
      }
      click(x, y);
    } else {
      emit("{\"probe\":\"error\",\"what\":\"unknown step " + jsonEscape(step) + "\"}");
      _exit(64);
    }
    out += (first ? "" : ",") + std::string("{\"step\":\"") + jsonEscape(step) +
           "\",\"cursor\":\"" + jsonEscape(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)) + "\"" +
           extra + "}";
    first = false;
  }
  (void)label;
  return out + "]";
}

std::string commandValues(const char *command) {
  char *values = gDoc->pClass->getCommandValues(gDoc, command);
  std::string out = values ? values : "";
  std::free(values);
  return out;
}

int undoCount() { return std::atoi(commandValues(".uno:UndoCount").c_str()); }

std::string selectionText() {
  char *text = gDoc->pClass->getTextSelection(gDoc, "text/plain;charset=utf-8", nullptr);
  std::string out = text ? text : "";
  std::free(text);
  return out;
}

int selectionType() {
  return gDoc->pClass->getSelectionType(gDoc);
}

// What the WASM engine's readSelection() asks (probe_engine.cpp readSelection).
std::string selectionTypeAndTextJson() {
  if (!LIBREOFFICEKIT_DOCUMENT_HAS(gDoc, getSelectionTypeAndText))
    return "{\"available\":false}";
  char *text = nullptr;
  const int type = gDoc->pClass->getSelectionTypeAndText(gDoc, "text/plain;charset=utf-8", &text, nullptr);
  const std::string out = "{\"available\":true,\"type\":" + std::to_string(type) +
                          ",\"textReturned\":" + (text ? "true" : "false") +
                          ",\"text\":\"" + jsonEscape(text ? text : "") + "\"}";
  std::free(text);
  return out;
}

// Everything the runner needs to say whether the paste left a trace.
std::string stateJson() {
  std::string undoState, pasteState;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    undoState = gLastUndoState;
    pasteState = gLastPasteState;
  }
  return "{\"undoCount\":\"" + jsonEscape(commandValues(".uno:UndoCount")) +
         "\",\"undoPayload\":\"" + jsonEscape(commandValues(".uno:Undo")) +
         "\",\"readOnly\":\"" + jsonEscape(commandValues(".uno:ReadOnly")) +
         "\",\"selectionType\":" + std::to_string(selectionType()) +
         ",\"selection\":\"" + jsonEscape(selectionText()) +
         "\",\"cursor\":\"" + jsonEscape(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)) +
         "\",\"lastUndoState\":\"" + jsonEscape(undoState) +
         "\",\"lastPasteState\":\"" + jsonEscape(pasteState) + "\"}";
}

std::string dispatch(const char *command, int timeoutMs = 8000) {
  std::size_t before;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    before = gUnoResults.size();
  }
  gDoc->pClass->postUnoCommand(gDoc, command, nullptr, true);
  for (int waited = 0; waited < timeoutMs; waited += 25) {
    drain(25);
    std::lock_guard<std::mutex> lock(gMutex);
    for (std::size_t i = before; i < gUnoResults.size(); ++i)
      if (gUnoResults[i].find(command) != std::string::npos)
        return gUnoResults[i];
  }
  return "";
}

bool saveFlat(const std::string &path) {
  const std::string url = "file://" + path;
  return gDoc->pClass->saveAs(gDoc, url.c_str(), "fodt", nullptr) != 0;
}

void paint() {
  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  gDoc->pClass->paintTile(gDoc, reinterpret_cast<unsigned char *>(pixels.data()), canvas,
                          canvas, 0, 0, 3840, 3840);
}

int threadTextEncoding(const std::string &install) {
  const std::string path = install + "/libuno_sal.so.3";
  void *handle = dlopen(path.c_str(), RTLD_NOW | RTLD_NOLOAD);
  if (!handle)
    return -1;
  using Fn = unsigned short (*)();
  auto fn = reinterpret_cast<Fn>(dlsym(handle, "osl_getThreadTextEncoding"));
  return fn ? static_cast<int>(fn()) : -2;
}

const char *envOr(const char *name) {
  const char *value = std::getenv(name);
  return value ? value : "(unset)";
}

std::string readFile(const std::string &path, bool &ok) {
  std::ifstream in(path, std::ios::binary);
  ok = static_cast<bool>(in);
  std::ostringstream buffer;
  buffer << in.rdbuf();
  return buffer.str();
}

} // namespace

int main(int argc, char **argv) {
  if (argc < 11) {
    std::cerr << "usage: md-paste-probe3 INSTALL PROFILE_URL DOC_URL OUT_DIR MIME "
                 "PAYLOAD_FILE SETUP PLACE READBACK FLAGS [WATCHDOG_S]\n";
    return 64;
  }
  const std::string install = argv[1];
  const char *profileUrl = argv[2];
  const char *docUrl = argv[3];
  const std::string outDir = argv[4];
  const std::string mime = argv[5];
  const std::string payloadFile = argv[6];
  const std::string setup = argv[7];
  const std::string place = argv[8];
  const std::string readbackMode = argv[9];
  const std::string flags = argv[10];
  const int watchdogSeconds = argc > 11 ? std::atoi(argv[11]) : 20;
  const bool viewReadOnly = flags.find("viewro") != std::string::npos;
  const bool typeKey = flags.find("typekey") != std::string::npos;

  bool ok = false;
  const std::string payload = readFile(payloadFile, ok);
  if (!ok) {
    std::cerr << "cannot read payload " << payloadFile << "\n";
    return 65;
  }

  emit(std::string("{\"probe\":\"env\",\"LANG\":\"") + envOr("LANG") +
       "\",\"LC_ALL\":\"" + envOr("LC_ALL") + "\",\"LC_CTYPE\":\"" + envOr("LC_CTYPE") +
       "\",\"SAL_USE_VCLPLUGIN\":\"" + envOr("SAL_USE_VCLPLUGIN") +
       "\",\"mime\":\"" + jsonEscape(mime) + "\",\"payloadBytes\":" +
       std::to_string(payload.size()) + ",\"setup\":\"" + jsonEscape(setup) +
       "\",\"place\":\"" + jsonEscape(place) + "\",\"readback\":\"" + jsonEscape(readbackMode) +
       "\",\"flags\":\"" + jsonEscape(flags) +
       "\",\"watchdogSeconds\":" + std::to_string(watchdogSeconds) + "}");

  Watchdog watchdog(watchdogSeconds);
  watchdog.detach();

  const auto initStart = Clock::now();
  watchdog.arm("lok_init_2");
  LibreOfficeKit *kit = lok_init_2(install.c_str(), profileUrl);
  watchdog.disarm();
  if (!kit) { emit("{\"probe\":\"error\",\"what\":\"lok_init_2 null\"}"); return 2; }
  watchdog.arm("documentLoad");
  gDoc = kit->pClass->documentLoad(kit, docUrl);
  watchdog.disarm();
  if (!gDoc) {
    char *e = kit->pClass->getError(kit);
    emit(std::string("{\"probe\":\"error\",\"what\":\"documentLoad null: ") +
         jsonEscape(e ? e : "?") + "\"}");
    return 3;
  }
  gDoc->pClass->initializeForRendering(gDoc, "{}");
  gDoc->pClass->registerCallback(gDoc, onCallback, nullptr);
  bool a11y = false;
  if (LIBREOFFICEKIT_DOCUMENT_HAS(gDoc, setAccessibilityState)) {
    gDoc->pClass->setAccessibilityState(gDoc, gDoc->pClass->getView(gDoc), true);
    a11y = true;
  }
  paint();
  drain(500);
  emit("{\"probe\":\"opened\",\"ms\":" + std::to_string(static_cast<long>(msSince(initStart))) +
       ",\"accessibility\":" + (a11y ? "true" : "false") +
       ",\"threadTextEncoding\":" + std::to_string(threadTextEncoding(install)) +
       ",\"readOnly\":\"" + jsonEscape(commandValues(".uno:ReadOnly")) + "\"}");

  watchdog.arm("setup");
  const std::string setupLog = runScript(setup, "setup");
  watchdog.disarm();
  emit("{\"probe\":\"setup\",\"steps\":" + setupLog + "}");

  // Ask the state: place, read back, (place again), then paste.
  watchdog.arm("place");
  {
    std::lock_guard<std::mutex> lock(gMutex);
    gPlaceCallbacks.clear();
    gPlaceStart = Clock::now();
  }
  gPlaceCapture = true;
  std::string placeLog = runScript(place, "place");
  settle(300, 5000);
  gPlaceCapture = false;
  emit("{\"probe\":\"place-callbacks\",\"list\":" + callbacksJson(&gPlaceCallbacks) + "}");
  const std::string typeAndTextAtPlace = selectionTypeAndTextJson();
  std::string readback;
  std::string placeAgainLog = "[]";
  const std::string cursorAtReadback = lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR);
  if (readbackMode == "sel") {
    readback = selectionText();
  } else if (readbackMode == "end") {
    key(kEnd | kShift);
    settle(300, 5000);
    readback = selectionText();
    placeAgainLog = runScript(place, "place-again");
    settle(300, 5000);
  }
  watchdog.disarm();
  emit("{\"probe\":\"position\",\"readbackMode\":\"" + readbackMode + "\",\"readback\":\"" +
       jsonEscape(readback) + "\",\"cursorAtReadback\":\"" + jsonEscape(cursorAtReadback) +
       "\",\"cursorAtPaste\":\"" + jsonEscape(lastOf(LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)) +
       "\",\"selectionAtPaste\":\"" + jsonEscape(selectionText()) +
       "\",\"selectionTypeAtPaste\":" + std::to_string(selectionType()) +
       ",\"selectionTypeAndTextAtPlace\":" + typeAndTextAtPlace +
       ",\"selectionTypeAndTextAtPaste\":" + selectionTypeAndTextJson() +
       ",\"lastTextSelection\":\"" + jsonEscape(lastOf(LOK_CALLBACK_TEXT_SELECTION)) +
       "\",\"lastGraphicSelection\":\"" + jsonEscape(lastOf(LOK_CALLBACK_GRAPHIC_SELECTION)) +
       "\",\"place\":" + placeLog + ",\"placeAgain\":" + placeAgainLog + "}");

  if (viewReadOnly) {
    const int view = gDoc->pClass->getView(gDoc);
    gDoc->pClass->setViewReadOnly(gDoc, view, true);
    settle(300, 5000);
    emit("{\"probe\":\"view-read-only\",\"view\":" + std::to_string(view) + "}");
  }

  watchdog.arm("save-before");
  const bool savedBefore = saveFlat(outDir + "/before.fodt");
  watchdog.disarm();
  drain(200);
  const int countBefore = undoCount();
  emit("{\"probe\":\"state-before\",\"saved\":" + std::string(savedBefore ? "true" : "false") +
       ",\"state\":" + stateJson() + "}");

  // The call under test.
  watchdog.arm("paste");
  gPasteStart = Clock::now();
  gPasteStarted = true;
  gInCall = true;
  bool returned = true;
  if (typeKey) {
    gDoc->pClass->postKeyEvent(gDoc, LOK_KEYEVENT_KEYINPUT, 'x', 535);
    gDoc->pClass->postKeyEvent(gDoc, LOK_KEYEVENT_KEYUP, 'x', 535);
  } else {
    returned = gDoc->pClass->paste(gDoc, mime.c_str(), payload.data(), payload.size());
  }
  gInCall = false;
  const double callMs = msSince(gPasteStart);
  watchdog.disarm();
  std::string lastError;
  if (!returned) {
    char *e = kit->pClass->getError(kit);
    lastError = e ? e : "";
  }
  char callMsText[32];
  std::snprintf(callMsText, sizeof(callMsText), "%.1f", callMs);
  emit(std::string("{\"probe\":\"paste\",\"call\":\"") + (typeKey ? "typekey" : "paste") +
       "\",\"returned\":" + (returned ? "true" : "false") +
       ",\"callMs\":" + callMsText + ",\"getError\":\"" + jsonEscape(lastError) + "\"}");
  drain(1500);
  emit("{\"probe\":\"callbacks\",\"coreLog\":" + coreLogJson() + ",\"list\":" +
       callbacksJson() + "}");
  gPasteStarted = false;

  const int countAfter = undoCount();
  emit("{\"probe\":\"state-after\",\"state\":" + stateJson() + "}");

  watchdog.arm("paint");
  const auto paintStart = Clock::now();
  paint();
  const double paintMs = msSince(paintStart);
  watchdog.disarm();
  char paintText[32];
  std::snprintf(paintText, sizeof(paintText), "%.1f", paintMs);
  emit(std::string("{\"probe\":\"paint\",\"ms\":") + paintText + "}");

  watchdog.arm("save-after");
  const bool savedAfter = saveFlat(outDir + "/after.fodt");
  watchdog.disarm();
  emit(std::string("{\"probe\":\"save\",\"which\":\"after\",\"saved\":") +
       (savedAfter ? "true" : "false") + "}");

  int step = 0;
  int count = countAfter;
  while (count > countBefore && step < 12) {
    ++step;
    watchdog.arm("undo-" + std::to_string(step));
    const std::string result = dispatch(".uno:Undo");
    drain(300);
    const std::string path = outDir + "/undo-" + std::to_string(step) + ".fodt";
    const bool saved = saveFlat(path);
    watchdog.disarm();
    count = undoCount();
    emit("{\"probe\":\"undo\",\"step\":" + std::to_string(step) + ",\"result\":\"" +
         jsonEscape(result) + "\",\"countAfterStep\":" + std::to_string(count) +
         ",\"saved\":" + (saved ? "true" : "false") + "}");
  }
  emit("{\"probe\":\"done\",\"undoSteps\":" + std::to_string(step) +
       ",\"countBefore\":" + std::to_string(countBefore) +
       ",\"countAfter\":" + std::to_string(countAfter) + "}");

  gDoc->pClass->destroy(gDoc);
  kit->pClass->destroy(kit);
  std::fflush(nullptr);
  _exit(0);
}
