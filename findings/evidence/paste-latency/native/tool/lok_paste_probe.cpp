// Native control for task 2026-10-14f: how long does LibreOfficeKit 26.8 take
// to paste a text through the same entry point the WASM engine uses
// (doc->pClass->paste("text/plain;charset=utf-8", ...), probe_engine.cpp:3239),
// and what does it cost to type the same text key by key instead?
//
// Usage: lok_paste_probe <install-dir> <profile-url> <in-url> <text-path> <paste|keys> [out-path]
//
// The document is opened the way the engine opens it (documentLoad,
// initializeForRendering("{}"), registerCallback), callbacks are counted by
// type, then the text is inserted and the wall time of the insert printed,
// followed by one small paintTile (forces the layout the engine's getState and
// paint would) and a saveAs so the paragraph count can be read.
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

static std::map<int, int> gCallbacks;
static int gTotal = 0;
static std::chrono::steady_clock::time_point gLast;

static void onCallback(int type, const char * /*payload*/, void * /*data*/) {
  gCallbacks[type] += 1;
  gTotal += 1;
  gLast = std::chrono::steady_clock::now();
}

static double ms(std::chrono::steady_clock::time_point a, std::chrono::steady_clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}

static bool decodeUtf8(const std::string &text, std::vector<unsigned int> &out) {
  size_t i = 0;
  while (i < text.size()) {
    unsigned char c = text[i];
    unsigned int cp; int n;
    if (c < 0x80) { cp = c; n = 1; }
    else if ((c >> 5) == 0x6) { cp = c & 0x1F; n = 2; }
    else if ((c >> 4) == 0xE) { cp = c & 0x0F; n = 3; }
    else if ((c >> 3) == 0x1E) { cp = c & 0x07; n = 4; }
    else return false;
    if (i + n > text.size()) return false;
    for (int k = 1; k < n; ++k) cp = (cp << 6) | (text[i + k] & 0x3F);
    out.push_back(cp);
    i += n;
  }
  return true;
}

int main(int argc, char **argv) {
  setvbuf(stdout, nullptr, _IONBF, 0);
  if (argc < 6) { std::fprintf(stderr, "usage: %s <install-dir> <profile-url> <in-url> <text-path> <paste|keys> [out-path]\n", argv[0]); return 2; }
  const char *install = argv[1], *profile = argv[2], *inUrl = argv[3], *textPath = argv[4], *mode = argv[5];
  const char *outPath = argc > 6 ? argv[6] : nullptr;
  std::ifstream in(textPath, std::ios::binary);
  std::stringstream buffer; buffer << in.rdbuf();
  const std::string text = buffer.str();
  std::printf("text bytes=%zu newlines=%zu mode=%s\n", text.size(), (size_t)std::count(text.begin(), text.end(), '\n'), mode);

  auto t0 = std::chrono::steady_clock::now();
  LibreOfficeKit *kit = lok_init_2(install, profile);
  if (!kit) { std::fprintf(stderr, "lok_init_2 failed\n"); return 1; }
  auto t1 = std::chrono::steady_clock::now();
  LibreOfficeKitDocument *doc = kit->pClass->documentLoad(kit, inUrl);
  if (!doc) { char *e = kit->pClass->getError(kit); std::fprintf(stderr, "load failed: %s\n", e ? e : "?"); return 1; }
  auto t2 = std::chrono::steady_clock::now();
  doc->pClass->initializeForRendering(doc, "{}");
  doc->pClass->registerCallback(doc, onCallback, nullptr);
  long w = 0, h = 0;
  doc->pClass->getDocumentSize(doc, &w, &h);
  auto t3 = std::chrono::steady_clock::now();
  std::printf("init=%.1f ms load=%.1f ms initializeForRendering+size=%.1f ms size=%ldx%ld twips\n",
              ms(t0, t1), ms(t1, t2), ms(t2, t3), w, h);
  // A small paint first, so the first layout is not charged to the insert.
  std::vector<unsigned char> pixels(256 * 256 * 4);
  doc->pClass->paintTile(doc, pixels.data(), 256, 256, 0, 0, 3840, 3840);
  auto t4 = std::chrono::steady_clock::now();
  std::printf("first paintTile=%.1f ms callbacksSoFar=%d\n", ms(t3, t4), gTotal);
  const int callbacksBefore = gTotal;
  std::map<int, int> before = gCallbacks;

  auto t5 = std::chrono::steady_clock::now();
  bool ok = true;
  if (std::strcmp(mode, "paste") == 0) {
    ok = doc->pClass->paste(doc, "text/plain;charset=utf-8", text.data(), text.size());
  } else {
    std::vector<unsigned int> cps;
    if (!decodeUtf8(text, cps)) { std::fprintf(stderr, "bad utf8\n"); return 1; }
    for (unsigned int cp : cps) {
      if (cp == '\n') {
        doc->pClass->postKeyEvent(doc, LOK_KEYEVENT_KEYINPUT, 13, 1280);
        doc->pClass->postKeyEvent(doc, LOK_KEYEVENT_KEYUP, 13, 1280);
      } else {
        doc->pClass->postKeyEvent(doc, LOK_KEYEVENT_KEYINPUT, (int)cp, 0);
        doc->pClass->postKeyEvent(doc, LOK_KEYEVENT_KEYUP, (int)cp, 0);
      }
    }
  }
  auto t6 = std::chrono::steady_clock::now();
  std::printf("insert(%s) ok=%d wall=%.1f ms callbacksDuring=%d\n", mode, ok ? 1 : 0, ms(t5, t6), gTotal - callbacksBefore);
  doc->pClass->getDocumentSize(doc, &w, &h);
  auto t7 = std::chrono::steady_clock::now();
  doc->pClass->paintTile(doc, pixels.data(), 256, 256, 0, 0, 3840, 3840);
  auto t8 = std::chrono::steady_clock::now();
  std::printf("after insert: getDocumentSize=%.1f ms (%ldx%ld) paintTile=%.1f ms callbacksTotal=%d\n", ms(t6, t7), w, h, ms(t7, t8), gTotal);
  std::printf("callbacks by type (during insert and after):");
  for (auto &kv : gCallbacks) {
    int d = kv.second - before[kv.first];
    if (d) std::printf(" %d:%d", kv.first, d);
  }
  std::printf("\n");
  if (outPath) {
    std::string outUrl = std::string("file://") + outPath;
    auto t9 = std::chrono::steady_clock::now();
    if (!doc->pClass->saveAs(doc, outUrl.c_str(), "odt", nullptr)) { std::fprintf(stderr, "saveAs failed\n"); return 1; }
    std::printf("saveAs=%.1f ms -> %s\n", ms(t9, std::chrono::steady_clock::now()), outPath);
  }
  doc->pClass->destroy(doc);
  kit->pClass->destroy(kit);
  return 0;
}
