// Review 6 (link batch, engine code), Q1 arm: what does the barrier's K1
// (Shift+arrow, posted exactly as startSelectionBarrierDelete posts it) do at a
// few positions, and what does the user's own key do there?  Native 26.8, one
// fresh process per arm.  Scratch only; nothing here is part of the tree.
//
// Usage: k1probe INSTALL PROFILE_URL DOC_URL PLACEMENT ARM OUT_URL
//   PLACEMENT  comma list of steps: "uno:<cmd>" or "key:<code>"
//   ARM        "k1-left" | "k1-right"   : post K1, wait, read, then paste "Z", save
//              "key-1283" | "key-1286"  : post the user's key (Backspace|Delete), save
//   OUT_URL    where the document is saved (fodt) at the end
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
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
std::mutex gMutex;
struct Rec { double t; int type; std::string payload; };
std::vector<Rec> gRecs;
Clock::time_point gEpoch = Clock::now();
Clock::time_point gLast = Clock::now();

double ms(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}
std::string esc(const std::string &v) {
  std::string o;
  for (char c : v) {
    if (c == '"' || c == '\\') { o += '\\'; o += c; }
    else if (c == '\n') o += "\\n";
    else if (static_cast<unsigned char>(c) < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", (unsigned char)c); o += b; }
    else o += c;
  }
  return o;
}
void cb(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> l(gMutex);
  gLast = Clock::now();
  gRecs.push_back({ms(gEpoch, Clock::now()), type, payload ? payload : ""});
}
void sleepMs(int m) { std::this_thread::sleep_for(std::chrono::milliseconds(m)); }
void quiet(int quietMs = 1200) {
  const auto s = Clock::now();
  for (;;) {
    sleepMs(50);
    Clock::time_point last;
    { std::lock_guard<std::mutex> l(gMutex); last = gLast; }
    if (ms(last, Clock::now()) >= quietMs && ms(s, Clock::now()) >= quietMs) return;
    if (ms(s, Clock::now()) > 30000) return;
  }
}
void dump(double from, const char *phase) {
  std::lock_guard<std::mutex> l(gMutex);
  for (auto &r : gRecs) {
    if (r.t < from) continue;
    if (r.type == LOK_CALLBACK_STATE_CHANGED) continue;  // noise
    std::cout << "{\"rec\":\"cb\",\"phase\":\"" << phase << "\",\"t\":" << (r.t - from)
              << ",\"type\":\"" << lokCallbackTypeToString(r.type) << "\",\"payload\":\"" << esc(r.payload) << "\"}\n";
  }
}
void key(LibreOfficeKitDocument *d, int code) {
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYINPUT, 0, code);
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYUP, 0, code);
}
std::string undo(LibreOfficeKitDocument *d) {
  char *v = d->pClass->getCommandValues(d, ".uno:Undo");
  std::string s = v ? v : "<null>";
  std::free(v);
  return s;
}
void readSel(LibreOfficeKitDocument *d, const char *phase) {
  char *text = nullptr;
  const int t = d->pClass->getSelectionTypeAndText(d, "text/plain;charset=utf-8", &text, nullptr);
  std::cout << "{\"rec\":\"readSelection\",\"phase\":\"" << phase << "\",\"type\":" << t
            << ",\"text\":\"" << esc(text ? text : "") << "\"}\n";
  std::free(text);
}
}  // namespace

int main(int argc, char **argv) {
  if (argc < 7) { std::cerr << "usage\n"; return 2; }
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) { std::cerr << "init failed\n"; return 1; }
  LibreOfficeKitDocument *d = kit->pClass->documentLoad(kit, argv[3]);
  if (!d) { std::cerr << "load failed\n"; return 1; }
  d->pClass->initializeForRendering(d, "{}");
  d->pClass->registerCallback(d, cb, nullptr);
  std::string px(256 * 256 * 4, '\0');
  d->pClass->paintTile(d, reinterpret_cast<unsigned char *>(px.data()), 256, 256, 0, 0, 3840, 3840);
  quiet();

  // placement
  std::stringstream steps(argv[4]);
  std::string step;
  while (std::getline(steps, step, ',')) {
    if (step.rfind("uno:", 0) == 0) d->pClass->postUnoCommand(d, step.substr(4).c_str(), nullptr, false);
    else if (step.rfind("key:", 0) == 0) key(d, std::atoi(step.c_str() + 4));
    quiet(600);
  }
  quiet();
  const double placed = ms(gEpoch, Clock::now());
  dump(0, "load+placement");
  readSel(d, "after-placement");
  const std::string u0 = undo(d);
  std::cout << "{\"rec\":\"undo\",\"phase\":\"before\",\"payload\":\"" << esc(u0) << "\"}\n";

  const std::string arm = argv[5];
  const double t0 = ms(gEpoch, Clock::now());
  if (arm == "k1-left" || arm == "k1-right") {
    key(d, (arm == "k1-left" ? 1026 : 1027) | 0x1000);
    sleepMs(250);
    readSel(d, "k1+250ms");
    sleepMs(2000);
    readSel(d, "k1+2250ms");
    quiet();
    dump(t0, "k1");
    const std::string u1 = undo(d);
    std::cout << "{\"rec\":\"undo\",\"phase\":\"after-k1\",\"changed\":" << (u1 != u0 ? "true" : "false") << ",\"payload\":\"" << esc(u1) << "\"}\n";
    // what the next typed character does (the product types with paste)
    const double t1 = ms(gEpoch, Clock::now());
    const bool ok = d->pClass->paste(d, "text/plain;charset=utf-8", "Z", 1);
    quiet();
    dump(t1, "paste-Z");
    std::cout << "{\"rec\":\"paste\",\"ok\":" << (ok ? "true" : "false") << "}\n";
  } else {
    key(d, std::atoi(arm.c_str() + 4));
    quiet();
    dump(t0, "key");
    const std::string u1 = undo(d);
    std::cout << "{\"rec\":\"undo\",\"phase\":\"after-key\",\"changed\":" << (u1 != u0 ? "true" : "false") << ",\"payload\":\"" << esc(u1) << "\"}\n";
  }
  (void)placed;
  const bool saved = d->pClass->saveAs(d, argv[6], "fodt", nullptr);
  std::cout << "{\"rec\":\"saved\",\"ok\":" << (saved ? "true" : "false") << "}\n";
  std::cout.flush();
  d->pClass->destroy(d);
  sleepMs(200);
  std::_Exit(0);
}
