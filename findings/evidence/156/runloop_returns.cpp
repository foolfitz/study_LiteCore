// Finding 156: does LibreOfficeKit's runLoop (unipoll) run the main loop?
//
// A minimal native LOK client on a stock build:
//   1. SAL_LOK_OPTIONS=unipoll (set by the caller), lok_init_2;
//   2. runLoop(poll, wake, &state): the poll callback counts its calls and
//      returns -1 (quit) on the 50th, so a working runLoop returns after 50
//      polls;
//   3. prints how long runLoop took and how many polls ran;
//   4. with "load DOC_URL" as the third argument, then calls documentLoad, the
//      first thing a client does after its loop has run (a crash here is the
//      consequence, not the finding).
//
// Usage: runloop-returns INSTALL_PROGRAM_DIR PROFILE_URL [load DOC_URL]
// Build: g++ -std=c++17 -O2 -Wall -I<libreoffice-26-8>/include runloop_returns.cpp -ldl -o runloop-returns

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

namespace {
int gPolls = 0;
int poll(void *, int) { return ++gPolls >= 50 ? -1 : 0; }
void wake(void *) {}
double ms(std::chrono::steady_clock::time_point a) {
  return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - a).count();
}
}  // namespace

int main(int argc, char **argv) {
  if (argc != 3 && argc != 5) {
    std::fprintf(stderr, "usage: runloop-returns INSTALL PROFILE_URL [load DOC_URL]\n");
    return 64;
  }
  const char *opt = std::getenv("SAL_LOK_OPTIONS");
  std::printf("{\"rec\":\"env\",\"SAL_LOK_OPTIONS\":\"%s\"}\n", opt ? opt : "");
  std::fflush(stdout);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::printf("{\"rec\":\"fatal\",\"what\":\"lok_init_2\"}\n");
    return 2;
  }
  const auto t0 = std::chrono::steady_clock::now();
  kit->pClass->runLoop(kit, poll, wake, &gPolls);
  std::printf("{\"rec\":\"runLoop-returned\",\"ms\":%.3f,\"polls\":%d}\n", ms(t0), gPolls);
  std::fflush(stdout);
  if (argc == 5 && std::strcmp(argv[3], "load") == 0) {
    LibreOfficeKitDocument *doc = kit->pClass->documentLoad(kit, argv[4]);
    std::printf("{\"rec\":\"documentLoad-returned\",\"doc\":%s}\n", doc ? "true" : "false");
    std::fflush(stdout);
  }
  std::_Exit(0);
}
