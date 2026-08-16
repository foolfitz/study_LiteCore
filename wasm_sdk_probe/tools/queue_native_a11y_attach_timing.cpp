// When does getA11yFocusedParagraph() start returning a real paragraph?
//
// The v3 link (first attempt) shipped with accessibility never switched on.
// The second attempt switches it on AT DOCUMENT OPEN -- and the paragraph still
// comes back empty for every caret position, while the engine now correctly
// reports `enabled: true, fresh: true`.
//
// The tree's own comment names the suspect (probe_engine.cpp, the discovery
// build's search path): "Reattach here so the documented focused-paragraph
// snapshot reflects that selection instead of an early empty focus."  So
// enabling early may attach a listener to a view that has no caret yet, and it
// may never fill in afterwards.
//
// This probe decides that BEFORE a third link is spent, which is the step
// skipped before the second one.  One document, four reads:
//
//   1. enabled at open, before any caret exists  -> read
//   2. after a click that puts a caret somewhere -> read
//   3. after RE-ATTACHING (off, then on)         -> read
//   4. after a second click                      -> read
//
// If 2 is empty and 3 is not, the fix is "re-attach once the view is
// interactive" and the shape is measured rather than guessed.
//
// Usage: queue-native-a11y-attach-timing INSTALL_PATH PROFILE_URL DOCUMENT_URL

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

namespace {

std::string jsonEscape(const char *value) {
  std::string out;
  if (!value)
    return out;
  for (const char *it = value; *it; ++it) {
    switch (*it) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': out += "\\r"; break;
    case '\t': out += "\\t"; break;
    default:
      if (static_cast<unsigned char>(*it) < 0x20) {
        char buffer[8];
        std::snprintf(buffer, sizeof(buffer), "\\u%04x",
                      static_cast<unsigned char>(*it));
        out += buffer;
      } else {
        out += *it;
      }
    }
  }
  return out;
}

struct Rectangle { long x = -1, y = -1, w = 0, h = 0; bool valid = false; };
Rectangle gCaret;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR && payload) {
    long v[4] = {0, 0, 0, 0};
    if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &v[0], &v[1], &v[2], &v[3]) == 4)
      gCaret = Rectangle{v[0], v[1], v[2], v[3], true};
  }
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

void emit(const char *arm, LibreOfficeKitDocument *document) {
  char *value = document->pClass->getA11yFocusedParagraph(document);
  const std::string payload = value ? std::string(value) : std::string();
  std::free(value);
  std::cout << "{\"probe\":\"arm\",\"arm\":\"" << arm
            << "\",\"payload\":\"" << jsonEscape(payload.c_str()) << "\""
            << ",\"caretValid\":" << (gCaret.valid ? "true" : "false")
            << ",\"caretY\":" << (gCaret.valid ? gCaret.y : -1) << "}\n";
  std::cout.flush();
}

void attach(LibreOfficeKitDocument *document, bool reattach) {
  const int viewId = document->pClass->getView(document);
  if (reattach)
    document->pClass->setAccessibilityState(document, viewId, false);
  document->pClass->setAccessibilityState(document, viewId, true);
  drain(400);
}

void click(LibreOfficeKitDocument *document, long x, long y) {
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                   x, y, 1, 1, 0);
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                   x, y, 1, 1, 0);
  drain(700);
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) { std::cerr << "lok_init_2 null\n"; return 2; }
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) { std::cerr << "documentLoad null\n"; return 3; }

  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);

  // Exactly what the product now does: switch it on at open, before anything
  // has put a caret anywhere.
  attach(document, /*reattach=*/false);
  emit("enabled-at-open-before-any-caret", document);

  const int kCanvas = 256;
  std::string pixels(static_cast<std::size_t>(kCanvas) * kCanvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              kCanvas, kCanvas, 0, 0, 3840, 3840);
  drain(500);
  emit("after-paint", document);

  click(document, 2000, 1500);
  emit("after-first-click", document);

  attach(document, /*reattach=*/true);
  emit("after-reattach", document);

  click(document, 2000, 2300);
  emit("after-second-click", document);

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
