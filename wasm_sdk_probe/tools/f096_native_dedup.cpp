// Finding 096, arm U: is the boundary/same-position silence the flush handler
// dropping an UNCHANGED cursor callback, or is nothing enqueued at all?
//
// The browser cannot tell: the dedup (CallbackFlushHandler, init.cxx:2529-2537)
// runs UPSTREAM of onLokCallback, so a dropped INVALIDATE_VISIBLE_CURSOR never
// reaches the client.  But the dedup emits SAL_INFO("lok", "Skipping duplicate
// [1] ...") as it drops it -- that line IS the enqueue the browser cannot see.
//
// Criteria were pinned before this file existed:
//   handoff/tasks/TASK-2026-09-10-096-why-the-core-is-silent-at-a-boundary.md
//   ("Arm U is runnable today").  Nothing here widens them.
//
// Gesture: Ctrl+Home, End, Home (press A: end->start, rect CHANGES),
//          Home (press B: already at start, rect UNCHANGED).
// Before each key a marker is written to STDERR, where SAL_LOG also goes, so the
// interleaved "Skipping duplicate [1]" is attributable to a specific press.
// Callback types delivered per press go to STDOUT as JSONL.
//
// Usage: f096-native-dedup INSTALL PROFILE_URL DOC_URL

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

namespace {

int gSequence = 0;
std::vector<std::pair<int, int>> gCallbacks; // (sequence, type)

void onCallback(int type, const char * /*payload*/, void *) {
  ++gSequence;
  gCallbacks.emplace_back(gSequence, type);
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

// com::sun::star::awt::Key + vcl modifier bits, spelled out (LOK headers only).
constexpr int KEY_HOME = 1028;
constexpr int KEY_END = 1029;
constexpr int KEY_MOD1 = 0x2000;

// A marker into the SAL stream (stderr), flushed, so any "Skipping duplicate"
// that follows it belongs to this press and not an earlier one.
void mark(const char *label) {
  std::fprintf(stderr, ">>>MARK %s\n", label);
  std::fflush(stderr);
}

// Post one key, mark the SAL stream first, then let the flush handler run.
// Records which callback types arrived in this press's window; returns whether
// INVALIDATE_VISIBLE_CURSOR (type 1) was among them.
void press(LibreOfficeKitDocument *document, const char *label,
           int keyCode, int modifier) {
  const int before = gSequence;
  mark(label);
  document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT, 0,
                                 keyCode | modifier);
  // Generous: the flush handler runs on an idle/timer, not inline with the key.
  for (int waited = 0; waited < 12; ++waited)
    drain(100);

  std::vector<int> types;
  bool visibleCursor = false;
  for (const auto &cb : gCallbacks) {
    if (cb.first <= before)
      continue;
    types.push_back(cb.second);
    if (cb.second == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)
      visibleCursor = true;
  }
  std::cout << "{\"press\":\"" << label
            << "\",\"invalidateVisibleCursorDelivered\":"
            << (visibleCursor ? "true" : "false") << ",\"types\":[";
  for (size_t i = 0; i < types.size(); ++i)
    std::cout << (i ? "," : "") << types[i];
  std::cout << "]}\n";
  std::cout.flush();
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "expected INSTALL PROFILE_URL DOC_URL\n";
    return 64;
  }
  std::setvbuf(stderr, nullptr, _IONBF, 0);
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) { std::cerr << "lok_init_2 null\n"; return 2; }
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) { std::cerr << "documentLoad null\n"; return 3; }

  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  drain(600);

  // Ctrl+Home -> document start (= first line start); End -> first line end.
  // Neither is a scored press; they set up the two Homes.
  press(document, "setup-ctrl-home", KEY_HOME, KEY_MOD1);
  press(document, "setup-end", KEY_END, 0);

  // Press A: End -> line start, the rect CHANGES -> type 1 expected, no skip.
  press(document, "A-home-rect-changes", KEY_HOME, 0);
  // Press B: already at line start, the rect is UNCHANGED -> the dedup should
  // drop the enqueued type 1; no type 1 delivered, "Skipping duplicate [1]"
  // logged after this marker.
  press(document, "B-home-rect-unchanged", KEY_HOME, 0);

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
