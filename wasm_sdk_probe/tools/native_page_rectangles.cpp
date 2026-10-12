// Link batch, item 2 (the page number, Collabora's way): what does native
// LibreOffice's getPartPageRectangles() return, what does it cost, and does it
// follow an edit that adds a page?
//
// Brief: handoff/tasks/TASK-2026-10-12c-native-page-rectangles-and-129-shapes.md
// (Part N1).  Plan: handoff/PLAN-2026-10-12-link-batch-shift-selection-and-page-number.md.
//
// One invocation = ONE fresh load of ONE document (the run script starts a
// fresh process per round).  Sequence:
//
//   load -> (initializeForRendering + one paintTile) -> wait until the
//   callbacks have been quiet for kQuietMs -> read the cheap page-count
//   sources (getParts, getDocumentSize, no rectangles yet, so that the first
//   rectangle call below is a cold call) -> 10 consecutive timed
//   getPartPageRectangles() calls -> 1 more call after a further quiet wait
//   (stability, not part of the timing)
//   -> Edit A: .uno:GoToEndOfDoc, .uno:InsertPagebreak -> quiet -> read
//   -> Edit B: .uno:GoToStartOfDoc, type one character -> quiet -> read
//
// Every callback is logged with its time relative to the previous edit
// (type name, payload).  With --redact the payloads of types that can carry
// document text are replaced by their length (the owner's document).
//
// Output: one JSON object per line on stdout; strings verbatim (escaped).
// Nothing here is parsed or judged: the analysis is a separate script that
// reads this raw file (tools/analyze_native_page_rectangles.py).
//
// Build:  g++ -std=c++17 -O2 -I<libreoffice-26-8>/include \
//             tools/native_page_rectangles.cpp -ldl -lpthread -o native-page-rectangles
// Usage:  native-page-rectangles INSTALL_PROGRAM_DIR PROFILE_URL DOC_URL LABEL ROUND [--redact]
// (SAL_USE_VCLPLUGIN=svp in the environment.)

#include <algorithm>
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

using Clock = std::chrono::steady_clock;

constexpr int kQuietMs = 1500;      // no callback for this long == quiet
constexpr int kQuietCapMs = 60000;  // give up waiting after this long

struct CallbackRecord {
  double tMs;  // relative to gEpoch
  int type;
  std::string payload;
};

std::mutex gMutex;
std::vector<CallbackRecord> gCallbacks;
Clock::time_point gEpoch = Clock::now();
Clock::time_point gLastCallback = Clock::now();
bool gRedact = false;

double msSince(Clock::time_point t) {
  return std::chrono::duration<double, std::milli>(Clock::now() - t).count();
}
double msBetween(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
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

// Types whose payload is geometry or a bare notice (kept even under --redact).
bool payloadIsGeometry(int type) {
  switch (type) {
  case LOK_CALLBACK_DOCUMENT_SIZE_CHANGED:
  case LOK_CALLBACK_INVALIDATE_TILES:
  case LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR:
  case LOK_CALLBACK_INVALIDATE_VIEW_CURSOR:
  case LOK_CALLBACK_CURSOR_VISIBLE:
  case LOK_CALLBACK_VIEW_CURSOR_VISIBLE:
  case LOK_CALLBACK_SET_PART:
    return true;
  default:
    return false;
  }
}

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  gLastCallback = Clock::now();
  std::string p = payload ? payload : "";
  if (gRedact && !payloadIsGeometry(type)) {
    // STATE_CHANGED carries "name=value"; keep only the command name and the
    // PageStatus value (a page count is not document text).
    if (type == LOK_CALLBACK_STATE_CHANGED) {
      const auto eq = p.find('=');
      const std::string name = eq == std::string::npos ? p : p.substr(0, eq);
      if (name == ".uno:PageStatus" || name == ".uno:StatePageNumber") {
        // keep as is
      } else {
        p = name + "=<redacted " + std::to_string(p.size() - name.size()) + " bytes>";
      }
    } else {
      p = "<redacted " + std::to_string(p.size()) + " bytes>";
    }
  }
  gCallbacks.push_back({msBetween(gEpoch, Clock::now()), type, p});
}

void sleepMs(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

// Wait until no callback has arrived for kQuietMs.  Returns the waited time.
double waitQuiet() {
  const auto start = Clock::now();
  for (;;) {
    sleepMs(100);
    Clock::time_point last;
    {
      std::lock_guard<std::mutex> lock(gMutex);
      last = gLastCallback;
    }
    if (msSince(last) >= kQuietMs && msSince(start) >= kQuietMs)
      return msSince(start);
    if (msSince(start) > kQuietCapMs)
      return -msSince(start);  // negative: never went quiet
  }
}

std::string rectangles(LibreOfficeKitDocument *d, double &ms) {
  const auto t0 = Clock::now();
  char *raw = d->pClass->getPartPageRectangles(d);
  const auto t1 = Clock::now();
  ms = msBetween(t0, t1);
  std::string out = raw ? raw : "<null>";
  std::free(raw);
  return out;
}

void emitCallbacksSince(double fromMs, const char *phase) {
  std::lock_guard<std::mutex> lock(gMutex);
  for (const auto &c : gCallbacks) {
    if (c.tMs < fromMs)
      continue;
    std::cout << "{\"rec\":\"callback\",\"phase\":\"" << phase << "\",\"tMs\":" << c.tMs
              << ",\"type\":\"" << lokCallbackTypeToString(c.type) << "\",\"payload\":\""
              << jsonEscape(c.payload) << "\"}" << std::endl;
  }
}

void emitPageCountSources(LibreOfficeKitDocument *d, const char *phase) {
  long w = 0, h = 0;
  d->pClass->getDocumentSize(d, &w, &h);
  const int parts = d->pClass->getParts(d);
  std::cout << "{\"rec\":\"sources\",\"phase\":\"" << phase << "\",\"getParts\":" << parts
            << ",\"docWidthTwips\":" << w << ",\"docHeightTwips\":" << h << "}" << std::endl;
}

void emitRects(LibreOfficeKitDocument *d, const char *phase, int index) {
  double ms = 0;
  const std::string raw = rectangles(d, ms);
  std::cout << "{\"rec\":\"rects\",\"phase\":\"" << phase << "\",\"index\":" << index
            << ",\"ms\":" << ms << ",\"raw\":\"" << jsonEscape(raw) << "\"}" << std::endl;
}

void uno(LibreOfficeKitDocument *d, const char *command) {
  d->pClass->postUnoCommand(d, command, nullptr, false);
}

void typeChar(LibreOfficeKitDocument *d, char c) {
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYINPUT, c, 0);
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYUP, c, 0);
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 6) {
    std::cerr << "usage: native-page-rectangles INSTALL_PROGRAM_DIR PROFILE_URL DOC_URL LABEL ROUND [--redact]\n";
    return 2;
  }
  const std::string label = argv[4];
  const std::string round = argv[5];
  gRedact = argc > 6 && std::strcmp(argv[6], "--redact") == 0;

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 failed\n";
    return 1;
  }
  gEpoch = Clock::now();
  std::cout << "{\"rec\":\"start\",\"doc\":\"" << jsonEscape(label) << "\",\"round\":" << round
            << ",\"redact\":" << (gRedact ? "true" : "false") << "}" << std::endl;

  const auto loadStart = Clock::now();
  LibreOfficeKitDocument *d = kit->pClass->documentLoad(kit, argv[3]);
  if (!d) {
    std::cout << "{\"rec\":\"fatal\",\"what\":\"documentLoad\"}" << std::endl;
    return 1;
  }
  const double loadMs = msSince(loadStart);
  d->pClass->initializeForRendering(d, "{}");
  d->pClass->registerCallback(d, onCallback, nullptr);
  std::string pixels(256 * 256 * 4, '\0');
  d->pClass->paintTile(d, reinterpret_cast<unsigned char *>(pixels.data()), 256, 256, 0, 0, 3840, 3840);
  std::cout << "{\"rec\":\"load\",\"loadMs\":" << loadMs << "}" << std::endl;

  // ---- settle -----------------------------------------------------------
  emitPageCountSources(d, "right-after-load");
  const double settleMs = waitQuiet();
  std::cout << "{\"rec\":\"quiet\",\"phase\":\"settle\",\"waitedMs\":" << settleMs << "}" << std::endl;
  emitCallbacksSince(0, "settle");
  emitPageCountSources(d, "settled");

  // ---- ten consecutive timed calls, then one after a further quiet wait ----
  for (int i = 0; i < 10; ++i)
    emitRects(d, "timed", i);
  sleepMs(2000);
  emitRects(d, "stability-after-2s", 0);
  emitPageCountSources(d, "after-timed");

  // ---- Edit A: add a page --------------------------------------------------
  const double editA = msBetween(gEpoch, Clock::now());
  std::cout << "{\"rec\":\"edit\",\"edit\":\"A\",\"what\":\".uno:GoToEndOfDoc then .uno:InsertPagebreak\",\"tMs\":" << editA << "}" << std::endl;
  uno(d, ".uno:GoToEndOfDoc");
  sleepMs(800);
  std::cout << "{\"rec\":\"edit\",\"edit\":\"A2\",\"what\":\".uno:InsertPagebreak dispatched\",\"tMs\":" << msBetween(gEpoch, Clock::now()) << "}" << std::endl;
  uno(d, ".uno:InsertPagebreak");
  const double quietA = waitQuiet();
  std::cout << "{\"rec\":\"quiet\",\"phase\":\"after-A\",\"waitedMs\":" << quietA << "}" << std::endl;
  emitCallbacksSince(editA, "after-A");
  emitPageCountSources(d, "after-A");
  emitRects(d, "after-A", 0);
  emitRects(d, "after-A", 1);

  // ---- Edit B: one character in the first paragraph --------------------------
  const double editB = msBetween(gEpoch, Clock::now());
  std::cout << "{\"rec\":\"edit\",\"edit\":\"B\",\"what\":\".uno:GoToStartOfDoc then type 'Q'\",\"tMs\":" << editB << "}" << std::endl;
  uno(d, ".uno:GoToStartOfDoc");
  sleepMs(800);
  typeChar(d, 'Q');
  const double quietB = waitQuiet();
  std::cout << "{\"rec\":\"quiet\",\"phase\":\"after-B\",\"waitedMs\":" << quietB << "}" << std::endl;
  emitCallbacksSince(editB, "after-B");
  emitPageCountSources(d, "after-B");
  emitRects(d, "after-B", 0);
  emitRects(d, "after-B", 1);

  std::cout << "{\"rec\":\"end\"}" << std::endl;
  d->pClass->destroy(d);
  sleepMs(200);
  return 0;
}
