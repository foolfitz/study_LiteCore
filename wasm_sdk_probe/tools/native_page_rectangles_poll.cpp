// Link batch item 2, Part N1, additional arm (not in the brief): when does
// getPartPageRectangles() start returning the new page, relative to the
// LOK_CALLBACK_DOCUMENT_SIZE_CHANGED that the page would key its re-read on?
//
// Same load / settle as tools/native_page_rectangles.cpp, then Edit A
// (.uno:GoToEndOfDoc, wait, .uno:InsertPagebreak) while the main thread polls
// getPartPageRectangles() (and getParts()) in a tight loop with a 1 ms sleep
// for kPollMs after the dispatch.  Only CHANGES of the count are recorded (plus
// the first and last sample and the number of samples), with their times
// relative to the dispatch; every callback is logged with its time relative to
// the same dispatch.  The polling takes the SolarMutex like any LOK call, so a
// sample can only observe a layout the LOK thread has finished with: this arm
// answers "is there a window where the callback has fired but the rectangles
// are still the old ones" for a re-read made AFTER the callback.
//
// Build:  g++ -std=c++17 -O2 -I<libreoffice-26-8>/include
//             tools/native_page_rectangles_poll.cpp -ldl -lpthread -o native-page-rectangles-poll
// Usage:  native-page-rectangles-poll INSTALL_PROGRAM_DIR PROFILE_URL DOC_URL LABEL ROUND
// (SAL_USE_VCLPLUGIN=svp in the environment.)  Payloads are redacted except for
// geometry types and the page number, as in the main tool (the owner's document).

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
constexpr int kQuietMs = 1500;
constexpr int kPollMs = 1500;

struct CallbackRecord {
  double tMs;
  int type;
  std::string payload;
};

std::mutex gMutex;
std::vector<CallbackRecord> gCallbacks;
Clock::time_point gEpoch = Clock::now();
Clock::time_point gLastCallback = Clock::now();

double msBetween(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}
double nowMs() { return msBetween(gEpoch, Clock::now()); }

bool payloadKept(int type, const std::string &p) {
  switch (type) {
  case LOK_CALLBACK_DOCUMENT_SIZE_CHANGED:
  case LOK_CALLBACK_INVALIDATE_TILES:
  case LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR:
  case LOK_CALLBACK_SET_PART:
    return true;
  case LOK_CALLBACK_STATE_CHANGED:
    return p.rfind(".uno:StatePageNumber=", 0) == 0 || p.rfind(".uno:PageStatus=", 0) == 0;
  default:
    return false;
  }
}

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  gLastCallback = Clock::now();
  std::string p = payload ? payload : "";
  if (!payloadKept(type, p))
    p = "<redacted " + std::to_string(p.size()) + " bytes>";
  gCallbacks.push_back({nowMs(), type, p});
}

void sleepMs(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

double waitQuiet() {
  const auto start = Clock::now();
  for (;;) {
    sleepMs(100);
    Clock::time_point last;
    {
      std::lock_guard<std::mutex> lock(gMutex);
      last = gLastCallback;
    }
    if (msBetween(last, Clock::now()) >= kQuietMs && msBetween(start, Clock::now()) >= kQuietMs)
      return msBetween(start, Clock::now());
    if (msBetween(start, Clock::now()) > 60000)
      return -1;
  }
}

std::string jsonEscape(const std::string &value) {
  std::string out;
  for (const char c : value) {
    if (c == '"') out += "\\\"";
    else if (c == '\\') out += "\\\\";
    else if (c == '\n') out += "\\n";
    else if (static_cast<unsigned char>(c) < 0x20) out += ' ';
    else out += c;
  }
  return out;
}

int countRects(const std::string &raw) {
  if (raw.empty())
    return 0;
  int n = 1;
  for (size_t i = 0; i + 1 < raw.size(); ++i)
    if (raw[i] == ';' && raw[i + 1] == ' ')
      ++n;
  return n;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 6) {
    std::cerr << "usage: native-page-rectangles-poll INSTALL PROFILE_URL DOC_URL LABEL ROUND\n";
    return 2;
  }
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit)
    return 1;
  gEpoch = Clock::now();
  LibreOfficeKitDocument *d = kit->pClass->documentLoad(kit, argv[3]);
  if (!d)
    return 1;
  d->pClass->initializeForRendering(d, "{}");
  d->pClass->registerCallback(d, onCallback, nullptr);
  std::string pixels(256 * 256 * 4, '\0');
  d->pClass->paintTile(d, reinterpret_cast<unsigned char *>(pixels.data()), 256, 256, 0, 0, 3840, 3840);
  std::cout << "{\"rec\":\"start\",\"doc\":\"" << jsonEscape(argv[4]) << "\",\"round\":" << argv[5] << "}" << std::endl;
  waitQuiet();
  char *raw0 = d->pClass->getPartPageRectangles(d);
  const int before = countRects(raw0 ? raw0 : "");
  std::free(raw0);
  std::cout << "{\"rec\":\"before\",\"count\":" << before << ",\"getParts\":" << d->pClass->getParts(d) << "}" << std::endl;

  d->pClass->postUnoCommand(d, ".uno:GoToEndOfDoc", nullptr, false);
  sleepMs(800);
  waitQuiet();

  const auto dispatch = Clock::now();
  const double dispatchMs = msBetween(gEpoch, dispatch);
  d->pClass->postUnoCommand(d, ".uno:InsertPagebreak", nullptr, false);
  struct Sample { double t; int count; int parts; };
  std::vector<Sample> changes;
  int lastCount = -1, lastParts = -1, samples = 0;
  double firstT = 0, lastT = 0;
  while (msBetween(dispatch, Clock::now()) < kPollMs) {
    const double t = msBetween(dispatch, Clock::now());
    char *raw = d->pClass->getPartPageRectangles(d);
    const int count = countRects(raw ? raw : "");
    std::free(raw);
    const int parts = d->pClass->getParts(d);
    if (samples == 0)
      firstT = t;
    lastT = t;
    ++samples;
    if (count != lastCount || parts != lastParts) {
      changes.push_back({t, count, parts});
      lastCount = count;
      lastParts = parts;
    }
    sleepMs(1);
  }
  std::cout << "{\"rec\":\"poll\",\"dispatchMsSinceStart\":" << dispatchMs << ",\"samples\":" << samples
            << ",\"firstSampleMs\":" << firstT << ",\"lastSampleMs\":" << lastT << ",\"changes\":[";
  for (size_t i = 0; i < changes.size(); ++i)
    std::cout << (i ? "," : "") << "{\"tMs\":" << changes[i].t << ",\"count\":" << changes[i].count
              << ",\"getParts\":" << changes[i].parts << "}";
  std::cout << "]}" << std::endl;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    for (const auto &c : gCallbacks)
      if (c.tMs >= dispatchMs - 5)
        std::cout << "{\"rec\":\"callback\",\"tMsAfterDispatch\":" << (c.tMs - dispatchMs) << ",\"type\":\""
                  << lokCallbackTypeToString(c.type) << "\",\"payload\":\"" << jsonEscape(c.payload) << "\"}" << std::endl;
  }
  std::cout << "{\"rec\":\"end\"}" << std::endl;
  d->pClass->destroy(d);
  sleepMs(200);
  return 0;
}
