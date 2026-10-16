// Markdown paste through LibreOfficeKit, characterised natively (link batch v21,
// plan step 1b). One process = one fresh profile = one document = one paste.
//
// The product would call exactly this:
//   pClass->paste(doc, "text/markdown;charset=utf-8", bytes, len)
// which is what Collabora's kit does for its AI sidebar
// (cool-26-04 kit/ChildSession.cpp:1896).  This probe makes that call at a
// chosen caret position and records:
//   - paste()'s return value and the wall time of the call;
//   - every LOK callback from the moment paste() is called until 1.5 s after it
//     returned (type, ms since the call, whether it arrived during the call,
//     a short payload);
//   - the undo stack before and after (".uno:UndoCount", ".uno:Undo" JSON);
//   - the document saved as flat ODT before the paste, after it, and after each
//     .uno:Undo until the undo stack is back at its pre-paste depth;
//   - osl_getThreadTextEncoding() of the calling thread (the encoding
//     TransferableDataHelper::GetString decodes a byte flavour with,
//     vcl/source/treelist/transfer.cxx:1517) -- read through dlsym, so it is
//     the value of the thread that makes the paste call.
//
// A watchdog guards paste(), each .uno:Undo and each save: if a step has not
// returned within WATCHDOG seconds, the probe prints {"probe":"blocked",...}
// with every callback seen so far and _exit(124)s.  (A modal error dialog --
// sw/source/uibase/dochdl/swdtflvr.cxx:2310-2316 -- may block in LOK.)
//
// It says nothing about WASM.
//
// Usage:
//   md-paste-probe INSTALL PROFILE_URL DOC_URL OUT_DIR MIME PAYLOAD_FILE POSITION [WATCHDOG_S]
// POSITION: doc-start | para-start | para-middle | bullet-start | range-single | range-cross
// Fixture layout the positions assume (tool/inputs/positions.fodt):
//   1 "Start"  2 "Alpha Beta Gamma"  3 "Delta Epsilon"
//   4 * "Item one"  5 * "Item two"  6 "End"

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
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace {

constexpr int kShift = 0x1000;  // KEY_SHIFT
constexpr int kMod1 = 0x2000;   // KEY_MOD1
constexpr int kDown = 1024;
constexpr int kRight = 1027;
constexpr int kHome = 1028;
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

// Cut at a UTF-8 boundary so the JSON stays valid.
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
  double ms;  // since the paste call started (negative: before it)
  bool duringCall;
  std::string payload;
};

std::mutex gMutex;
std::vector<CallbackRecord> gCallbacks;
std::vector<std::string> gUnoResults;
std::string gLastUndoState;
Clock::time_point gPasteStart;
std::atomic<bool> gPasteStarted{false};
std::atomic<bool> gInCall{false};
long gCoreLogCount = 0;
double gCoreLogFirstMs = 0;
double gCoreLogLastMs = 0;

double msSince(Clock::time_point start) {
  return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  const std::string text = payload ? payload : "";
  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT)
    gUnoResults.push_back(text);
  if (type == LOK_CALLBACK_STATE_CHANGED && text.rfind(".uno:Undo=", 0) == 0)
    gLastUndoState = text;
  if (!gPasteStarted.load())
    return;
  // LOK_CALLBACK_CORE_LOG: LOK_INFO lines from the accessibility listener
  // (sfx2/source/view/viewsh.cxx, include/sfx2/lokhelper.hxx:35-54); tens of
  // thousands on a large paste. Counted, and only the first three kept.
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

std::string coreLogJson() {
  std::lock_guard<std::mutex> lock(gMutex);
  char buffer[160];
  std::snprintf(buffer, sizeof(buffer),
                "{\"count\":%ld,\"firstMs\":%.1f,\"lastMs\":%.1f,\"kept\":%ld}",
                gCoreLogCount, gCoreLogFirstMs, gCoreLogLastMs,
                gCoreLogCount < 3 ? gCoreLogCount : 3L);
  return buffer;
}

std::string callbacksJson() {
  std::lock_guard<std::mutex> lock(gMutex);
  std::string out = "[";
  for (std::size_t i = 0; i < gCallbacks.size(); ++i) {
    const CallbackRecord &r = gCallbacks[i];
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

// One watchdog for the whole process; armed around each blocking step.
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
      // Still armed past the deadline: the step is blocked.
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

void key(LibreOfficeKitDocument *document, int code) {
  document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT, 0, code);
  document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYUP, 0, code);
  drain(80);
}

void keys(LibreOfficeKitDocument *document, int code, int count) {
  for (int i = 0; i < count; ++i)
    key(document, code);
}

std::string commandValues(LibreOfficeKitDocument *document, const char *command) {
  char *values = document->pClass->getCommandValues(document, command);
  std::string out = values ? values : "";
  std::free(values);
  return out;
}

std::string undoJson(LibreOfficeKitDocument *document) {
  std::string state;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    state = gLastUndoState;
  }
  return "{\"count\":\"" + jsonEscape(commandValues(document, ".uno:UndoCount")) +
         "\",\"actions\":\"" + jsonEscape(commandValues(document, ".uno:Undo")) +
         "\",\"lastStateChanged\":\"" + jsonEscape(state) + "\"}";
}

int undoCount(LibreOfficeKitDocument *document) {
  return std::atoi(commandValues(document, ".uno:UndoCount").c_str());
}

std::string selectionText(LibreOfficeKitDocument *document) {
  char *text = document->pClass->getTextSelection(document, "text/plain;charset=utf-8", nullptr);
  std::string out = text ? text : "";
  std::free(text);
  return out;
}

std::string dispatch(LibreOfficeKitDocument *document, const char *command,
                     int timeoutMs = 8000) {
  std::size_t before;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    before = gUnoResults.size();
  }
  document->pClass->postUnoCommand(document, command, nullptr, true);
  for (int waited = 0; waited < timeoutMs; waited += 25) {
    drain(25);
    std::lock_guard<std::mutex> lock(gMutex);
    for (std::size_t i = before; i < gUnoResults.size(); ++i)
      if (gUnoResults[i].find(command) != std::string::npos)
        return gUnoResults[i];
  }
  return "";
}

bool saveFlat(LibreOfficeKitDocument *document, const std::string &path) {
  const std::string url = "file://" + path;
  return document->pClass->saveAs(document, url.c_str(), "fodt", nullptr) != 0;
}

void paint(LibreOfficeKitDocument *document) {
  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              canvas, canvas, 0, 0, 3840, 3840);
}

// The key sequence that puts the caret (or selection) at POSITION.
void place(LibreOfficeKitDocument *document, const std::string &position) {
  key(document, kHome | kMod1);
  if (position == "doc-start")
    return;
  if (position == "bullet-start") {
    keys(document, kDown, 3);
    key(document, kHome);
    return;
  }
  key(document, kDown);
  key(document, kHome);
  if (position == "para-start")
    return;
  keys(document, kRight, 6);  // after "Alpha "
  if (position == "para-middle")
    return;
  if (position == "range-single") {
    keys(document, kRight | kShift, 4);  // "Beta"
    return;
  }
  if (position == "range-cross") {
    keys(document, kRight | kShift, 16);  // "Beta Gamma" + break + "Delta"
    return;
  }
  emit("{\"probe\":\"error\",\"what\":\"unknown position " + jsonEscape(position) + "\"}");
  _exit(64);
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
  if (argc < 8) {
    std::cerr << "usage: md-paste-probe INSTALL PROFILE_URL DOC_URL OUT_DIR MIME "
                 "PAYLOAD_FILE POSITION [WATCHDOG_S]\n";
    return 64;
  }
  const std::string install = argv[1];
  const char *profileUrl = argv[2];
  const char *docUrl = argv[3];
  const std::string outDir = argv[4];
  const std::string mime = argv[5];
  const std::string payloadFile = argv[6];
  const std::string position = argv[7];
  const int watchdogSeconds = argc > 8 ? std::atoi(argv[8]) : 20;

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
       std::to_string(payload.size()) + ",\"position\":\"" + position +
       "\",\"watchdogSeconds\":" + std::to_string(watchdogSeconds) + "}");

  Watchdog watchdog(watchdogSeconds);
  watchdog.detach();

  const auto initStart = Clock::now();
  watchdog.arm("lok_init_2");
  LibreOfficeKit *kit = lok_init_2(install.c_str(), profileUrl);
  watchdog.disarm();
  if (!kit) { emit("{\"probe\":\"error\",\"what\":\"lok_init_2 null\"}"); return 2; }
  watchdog.arm("documentLoad");
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, docUrl);
  watchdog.disarm();
  if (!document) {
    char *e = kit->pClass->getError(kit);
    emit(std::string("{\"probe\":\"error\",\"what\":\"documentLoad null: ") +
         jsonEscape(e ? e : "?") + "\"}");
    return 3;
  }
  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  // The product asks for accessibility at open (probe_engine.cpp, open path).
  bool a11y = false;
  if (LIBREOFFICEKIT_DOCUMENT_HAS(document, setAccessibilityState)) {
    document->pClass->setAccessibilityState(document, document->pClass->getView(document), true);
    a11y = true;
  }
  paint(document);
  drain(500);
  emit("{\"probe\":\"opened\",\"ms\":" + std::to_string(static_cast<long>(msSince(initStart))) +
       ",\"accessibility\":" + (a11y ? "true" : "false") +
       ",\"threadTextEncoding\":" + std::to_string(threadTextEncoding(install)) + "}");

  // Ask the state: place, read back what Shift+End (collapsed) or the selection
  // (range) covers, then place again from scratch for the paste.
  const bool range = position.rfind("range-", 0) == 0;
  place(document, position);
  drain(300);
  std::string readback;
  if (range) {
    readback = selectionText(document);
  } else {
    key(document, kEnd | kShift);
    drain(300);
    readback = selectionText(document);
    place(document, position);
    drain(300);
  }
  emit("{\"probe\":\"position\",\"position\":\"" + position + "\",\"range\":" +
       (range ? "true" : "false") + ",\"readback\":\"" + jsonEscape(readback) +
       "\",\"readbackIs\":\"" + (range ? "selection" : "Shift+End from the caret") +
       "\",\"selectionAtPaste\":\"" + jsonEscape(selectionText(document)) + "\"}");

  watchdog.arm("save-before");
  const bool savedBefore = saveFlat(document, outDir + "/before.fodt");
  watchdog.disarm();
  drain(200);
  const int countBefore = undoCount(document);
  emit("{\"probe\":\"undo-before\",\"saved\":" + std::string(savedBefore ? "true" : "false") +
       ",\"undo\":" + undoJson(document) + "}");

  // The call under test.
  watchdog.arm("paste");
  gPasteStart = Clock::now();
  gPasteStarted = true;
  gInCall = true;
  const bool returned = document->pClass->paste(document, mime.c_str(), payload.data(),
                                                payload.size());
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
  emit(std::string("{\"probe\":\"paste\",\"returned\":") + (returned ? "true" : "false") +
       ",\"callMs\":" + callMsText + ",\"getError\":\"" + jsonEscape(lastError) + "\"}");
  drain(1500);
  emit("{\"probe\":\"callbacks\",\"coreLog\":" + coreLogJson() + ",\"list\":" +
       callbacksJson() + "}");
  gPasteStarted = false;

  const int countAfter = undoCount(document);
  emit("{\"probe\":\"undo-after\",\"undo\":" + undoJson(document) + "}");

  watchdog.arm("paint");
  const auto paintStart = Clock::now();
  paint(document);
  const double paintMs = msSince(paintStart);
  watchdog.disarm();
  char paintText[32];
  std::snprintf(paintText, sizeof(paintText), "%.1f", paintMs);
  emit(std::string("{\"probe\":\"paint\",\"ms\":") + paintText + "}");

  watchdog.arm("save-after");
  const bool savedAfter = saveFlat(document, outDir + "/after.fodt");
  watchdog.disarm();
  emit(std::string("{\"probe\":\"save\",\"which\":\"after\",\"saved\":") +
       (savedAfter ? "true" : "false") + "}");

  // Undo until the stack is back at its pre-paste depth (at most 12 steps).
  int step = 0;
  int count = countAfter;
  while (count > countBefore && step < 12) {
    ++step;
    watchdog.arm("undo-" + std::to_string(step));
    const std::string result = dispatch(document, ".uno:Undo");
    drain(300);
    const std::string path = outDir + "/undo-" + std::to_string(step) + ".fodt";
    const bool saved = saveFlat(document, path);
    watchdog.disarm();
    count = undoCount(document);
    emit("{\"probe\":\"undo\",\"step\":" + std::to_string(step) + ",\"result\":\"" +
         jsonEscape(result) + "\",\"countAfterStep\":" + std::to_string(count) +
         ",\"saved\":" + (saved ? "true" : "false") + "}");
  }
  emit("{\"probe\":\"done\",\"undoSteps\":" + std::to_string(step) +
       ",\"countBefore\":" + std::to_string(countBefore) +
       ",\"countAfter\":" + std::to_string(countAfter) + "}");

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  std::fflush(nullptr);
  _exit(0);  // skip static teardown; everything is flushed above
}
