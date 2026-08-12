// Minimal LibreOfficeKit reproducer for two hangs that share one trigger.
//
// Trigger: a draw:frame anchored text:anchor-type="as-char" inside a text:p.
// No image is needed -- the frame in these fixtures holds only a draw:text-box.
//
//   (1) getTextSelection(doc, "text/html", nullptr) over a selection covering
//       that paragraph never returns.
//   (2) destroy(doc) never returns, on the same document, even without (1).
//
// Both return promptly in a native build of the same commit.  Both fail to
// return in an Emscripten/WASM build of that commit.
//
// The two fixtures differ by exactly one attribute: frame-no-image.odt anchors
// the frame as-char, frame-paragraph-anchored.odt anchors it to the paragraph.
// Everything else -- the three paragraphs, the text box, the styles, the
// absence of any image anywhere -- is identical.  The second is the control:
// it is expected to pass every step, in both builds.
//
// Build (native):
//   g++ -std=c++17 -O2 -I<core>/include lok_frame_hang.cpp -ldl -o lok_frame_hang
//
// Run:
//   SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
//       <instdir>/program file:///tmp/lok-profile file://$PWD/frame-no-image.odt FNI-TEXTBOX
//   SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
//       <instdir>/program file:///tmp/lok-profile file://$PWD/frame-paragraph-anchored.odt FPA-FRAME
//
// Each step prints before it starts and after it returns, so the step that
// hangs is the one whose "enter" line has no matching "exit" line.  That is
// the whole design: a call that does not return cannot report its own timing.

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>

#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

namespace {

using Clock = std::chrono::steady_clock;
Clock::time_point gStarted;

long nowMs() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             Clock::now() - gStarted).count();
}

void enter(const char *step) {
  std::printf("[%6ld ms] enter  %s\n", nowMs(), step);
  std::fflush(stdout);
}

void exitStep(const char *step) {
  std::printf("[%6ld ms] exit   %s\n", nowMs(), step);
  std::fflush(stdout);
}

bool gCaretSeen = false;
bool gSelectionSeen = false;

void onCallback(int type, const char *, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)
    gCaretSeen = true;
  else if (type == LOK_CALLBACK_TEXT_SELECTION)
    gSelectionSeen = true;
}

// Poll rather than sleep a fixed span: a fixed sleep would report the sleep.
template <typename Predicate>
bool waitFor(Predicate satisfied, int deadlineMs) {
  const auto started = Clock::now();
  while (std::chrono::duration_cast<std::chrono::milliseconds>(
             Clock::now() - started).count() < deadlineMs) {
    if (satisfied())
      return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return false;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 5) {
    std::fprintf(stderr,
                 "expected INSTALL_DIR PROFILE_URL DOC_URL ANCHOR_TEXT\n");
    return 64;
  }
  gStarted = Clock::now();

  enter("lok_init_2");
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::fprintf(stderr, "lok_init_2 failed\n");
    return 70;
  }
  exitStep("lok_init_2");

  enter("documentLoad");
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    std::fprintf(stderr, "documentLoad failed\n");
    return 70;
  }
  exitStep("documentLoad");

  document->pClass->initializeForRendering(document, nullptr);
  document->pClass->registerCallback(document, onCallback, nullptr);
  std::this_thread::sleep_for(std::chrono::milliseconds(500));

  // Put the caret in the paragraph that carries the frame.
  const std::string search =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"") +
      argv[4] + "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"long\",\"value\":0}}";
  enter("ExecuteSearch");
  gCaretSeen = false;
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   search.c_str(), false);
  if (!waitFor([] { return gCaretSeen; }, 5000))
    std::printf("[%6ld ms] WARN   no caret callback for %s\n", nowMs(), argv[4]);
  exitStep("ExecuteSearch");

  // Select the whole paragraph, which is what puts the frame inside the
  // selection.  A collapsed caret reads back nothing, so this is required.
  enter("SelectText");
  gSelectionSeen = false;
  document->pClass->postUnoCommand(document, ".uno:SelectText", nullptr, true);
  if (!waitFor([] { return gSelectionSeen; }, 5000))
    std::printf("[%6ld ms] WARN   no selection callback\n", nowMs());
  exitStep("SelectText");

  std::printf("[%6ld ms] info   selectionType=%d\n", nowMs(),
              document->pClass->getSelectionType(document));
  std::fflush(stdout);

  // Symptom 1.  Native: returns in ~1 ms with a few hundred bytes.
  // WASM: does not return.
  enter("getTextSelection(text/html)");
  char *html = document->pClass->getTextSelection(document, "text/html", nullptr);
  exitStep("getTextSelection(text/html)");
  std::printf("[%6ld ms] info   html bytes=%zu\n", nowMs(),
              html ? std::string(html).size() : 0u);
  std::free(html);

  // Symptom 2.  On these two fixtures it was observed after the sequence
  // above; a bare open->destroy has not been run on them.  It was measured on
  // a bare open->close for a different document carrying an as-char image
  // frame, in both browsers, at the full 180 s timeout.  Comment out
  // everything from ExecuteSearch to here to test the bare path.
  enter("destroy(document)");
  document->pClass->destroy(document);
  exitStep("destroy(document)");

  enter("destroy(kit)");
  kit->pClass->destroy(kit);
  exitStep("destroy(kit)");

  std::printf("[%6ld ms] done\n", nowMs());
  return 0;
}
