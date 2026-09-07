// Finding 093, option B, step 1 -- the LOK-client half of the calibration
// probe.  Native only.  **Nothing here describes the wasm artifact.**
//
// THE QUESTION, restated from the runbook:
//
// `handoff/RUNBOOK-operator-093-engine-geometry.md` section 2 is read from
// source, not measured.  What unit does
// `XAccessibleComponent::getBounds()` return, what origin is it relative to,
// and does converting it to twips line up with the caret rectangle LOK already
// hands the page?  The wasm relink is a one-way door; this measurement is the
// look behind it, and it costs a native compile.
//
// HOW A PARAGRAPH IS CHOSEN, and why it matters:
//
// By a unique text marker (`LD-Pnn-Lmm`, put there by
// `tools/create_long_document.py`), navigated to with `.uno:ExecuteSearch`.
// Never by a coordinate.  If the probe aimed a click using the geometry under
// test, agreement would be structural -- the tree has paid for that shape
// before (findings 046, 052).
//
// The paragraph the caret landed in is then identified in the accessibility
// tree by its FOCUSED state, and the marker is cross-checked against the text
// the accessible reports.  State and text; still no coordinates.
//
// WHAT IS EMITTED, and what is NOT decided here:
//
// One JSONL record per target: the marker, the LOK caret rectangle (twips, by
// LOK's own contract), and the bridge's snapshot of the focused paragraph.  Two
// full snapshots -- before the first target and after the last -- so the judge
// can see whether the geometry moved under the walk.  Every verdict is the
// judge's (`tools/analyze_f093_native_geometry.py`), against
// `findings/evidence/093/step1-native-geometry/ACCEPTANCE.md` (`bcb7caf4`,
// registered before either half of this probe existed).
//
// Usage: f093-native-a11y-geometry INSTALL_PATH PROFILE_URL DOCUMENT_URL MARKERS...

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
#include <vector>

// The core-internal half.  Declared, not included: the two translation units
// are compiled against different views of core's headers on purpose.
extern "C" char* f093_geometry_snapshot(int bAllParagraphs, const char* pMarker);

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

struct Rectangle {
  long x = -1, y = -1, width = 0, height = 0;
  bool valid = false;
};

Rectangle gCaret;
long gCaretCallbacks = 0;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR && payload) {
    long v[4] = {0, 0, 0, 0};
    if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &v[0], &v[1], &v[2], &v[3]) == 4) {
      gCaret = Rectangle{v[0], v[1], v[2], v[3], true};
      ++gCaretCallbacks;
    }
  }
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

// Returns false when the caret did not move -- which a search that found the
// text the caret already sits on ALSO produces.  Every target below is reached
// from a different paragraph, so the two cases do not collide here; the note is
// kept because the collision cost a round once already
// (tools/queue_native_block_identity.cpp).
bool searchFor(LibreOfficeKitDocument *document, const std::string &needle) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"") +
      needle +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  gCaret = Rectangle{};
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(900);
  return gCaret.valid;
}

std::string snapshot(int bAll, const char *marker) {
  char *value = f093_geometry_snapshot(bAll, marker);
  std::string out = value ? std::string(value) : std::string("null");
  std::free(value);
  return out;
}

void emitSnapshot(const char *arm, int bAll) {
  // The snapshot is already JSON.  It is embedded, not escaped into a string:
  // a judge that has to unescape before it can read a number is a judge that
  // can silently read the wrong one.
  std::cout << "{\"record\":\"snapshot\",\"arm\":\"" << arm
            << "\",\"snapshot\":" << snapshot(bAll, nullptr) << "}\n";
  std::cout.flush();
}

} // namespace

int main(int argc, char **argv) {
  if (argc < 5) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL MARKERS...\n";
    return 64;
  }
  std::vector<std::string> markers;
  for (int i = 4; i < argc; ++i)
    markers.emplace_back(argv[i]);

  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    std::cerr << "documentLoad returned null\n";
    kit->pClass->destroy(kit);
    return 3;
  }
  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);

  // Force a layout.  Without it the frames the accessibility tree describes may
  // not exist yet, and "the bounds were zero" would be a statement about this
  // probe rather than about core.
  const int kCanvas = 256;
  std::string pixels(static_cast<std::size_t>(kCanvas) * kCanvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              kCanvas, kCanvas, 0, 0, 3840, 3840);
  drain(500);

  const bool hasA11y =
      LIBREOFFICEKIT_DOCUMENT_HAS(document, setAccessibilityState);
  int viewId = -1;
  if (hasA11y) {
    viewId = document->pClass->getView(document);
    document->pClass->setAccessibilityState(document, viewId, true);
    drain(600);
  }
  std::cout << "{\"record\":\"environment\",\"a11yAvailable\":"
            << (hasA11y ? "true" : "false") << ",\"viewId\":" << viewId
            << ",\"markerCount\":" << markers.size() << "}\n";
  std::cout.flush();

  emitSnapshot("before-first-target", 1);

  for (const std::string &marker : markers) {
    const bool found = searchFor(document, marker);
    const Rectangle caret = gCaret;
    std::cout << "{\"record\":\"target\",\"marker\":\"" << jsonEscape(marker.c_str())
              << "\",\"found\":" << (found ? "true" : "false")
              << ",\"caretValid\":" << (caret.valid ? "true" : "false")
              << ",\"caret\":{\"x\":" << caret.x << ",\"y\":" << caret.y
              << ",\"w\":" << caret.width << ",\"h\":" << caret.height << "}"
              << ",\"caretCallbacks\":" << gCaretCallbacks
              << ",\"snapshot\":" << snapshot(0, marker.c_str()) << "}\n";
    std::cout.flush();
  }

  emitSnapshot("after-last-target", 1);

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
