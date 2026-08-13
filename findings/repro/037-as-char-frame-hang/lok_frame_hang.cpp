// Minimal LibreOfficeKit reproducer for three hangs that share one trigger.
//
// Trigger: a draw:frame anchored text:anchor-type="as-char".  No image is
// needed -- the frame in these fixtures holds only a draw:text-box.
//
//   (1) getTextSelection(doc, "text/html", nullptr) over a selection covering
//       the paragraph that holds the frame never returns.
//   (2) destroy(doc) never returns, on the same document, even without (1).
//   (3) getSelectionTypeAndText(doc, "text/plain;charset=utf-8", ...) never
//       returns when the selection covers the CITATION MARK of a footnote
//       whose body holds the frame -- the frame itself is nowhere near the
//       selected text.
//
// All three return promptly in a native build of the same commit.  All three
// fail to return in an Emscripten/WASM build of that commit.
//
// (1) and (3) are the same extraction path reached two ways.  In (1) the frame
// is directly inside the selection, so the selection type is COMPLEX and the
// text is never extracted -- it hangs on the explicit html request.  In (3) the
// selection is ordinary text, type TEXT, and the extraction walks into the
// footnote body on its own and meets the frame there.  That is why a guard on
// the selection type stops (1) and does not stop (3).
//
// Modes:
//
//   paragraph  fixtures frame-no-image.odt / frame-paragraph-anchored.odt.
//              .uno:SelectText over the paragraph, then symptom (1), then (2).
//              The two fixtures differ by exactly one attribute -- as-char
//              versus paragraph anchoring -- and nothing else, so the
//              paragraph-anchored one is the control and should pass every
//              step in both builds.
//
//   range      fixture frame-contexts.odt.  Selects a span with
//              setTextSelection(RESET)+setTextSelection(END), which is what a
//              mouse drag through a text-handle client does, then symptom (3).
//              Anchor FX-NOTE is the failing case; FX-PLAIN, an ordinary
//              paragraph in the same document, is the control.
//
// Build (native):
//   g++ -std=c++17 -O2 -I<core>/include lok_frame_hang.cpp -ldl -o lok_frame_hang
//
// Run:
//   SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
//       <instdir>/program file:///tmp/lok-profile file://$PWD/frame-no-image.odt FNI-TEXTBOX
//   SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
//       <instdir>/program file:///tmp/lok-profile file://$PWD/frame-paragraph-anchored.odt FPA-FRAME
//   SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
//       <instdir>/program file:///tmp/lok-profile file://$PWD/frame-contexts.odt FX-NOTE range
//   SAL_USE_VCLPLUGIN=svp ./lok_frame_hang \
//       <instdir>/program file:///tmp/lok-profile file://$PWD/frame-contexts.odt FX-PLAIN range
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
// The rectangle the search landed on, as "x, y, width, height" in twips.  The
// range mode needs it to know where to drag, and taking it from the callback
// rather than hard-coding coordinates keeps the probe working if the fixture's
// layout ever shifts.
std::string gSearchRectangle;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)
    gCaretSeen = true;
  else if (type == LOK_CALLBACK_TEXT_SELECTION) {
    gSelectionSeen = true;
    if (payload && *payload && gSearchRectangle.empty())
      gSearchRectangle = payload;
  }
}

// "1418, 1418, 1093, 275" -> the four numbers.  Returns false rather than
// guessing if the payload is not the shape this expects.
bool parseRectangle(const std::string &text, long out[4]) {
  return std::sscanf(text.c_str(), "%ld, %ld, %ld, %ld",
                     &out[0], &out[1], &out[2], &out[3]) == 4;
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
                 "expected INSTALL_DIR PROFILE_URL DOC_URL ANCHOR_TEXT"
                 " [MODE=paragraph|range] [SPAN_TWIPS]\n");
    return 64;
  }
  const std::string mode = argc >= 6 ? argv[5] : "paragraph";
  if (mode != "paragraph" && mode != "range") {
    std::fprintf(stderr, "MODE must be paragraph or range\n");
    return 64;
  }
  // 8000 twips is what the browser-side harness drags: past the end of the
  // line, so the selection covers the whole run including the citation mark.
  const long spanTwips = argc >= 7 ? std::atol(argv[6]) : 8000;
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

  if (mode == "range") {
    // Drag a span across the anchor, the way a text-handle client does:
    // setTextSelection(RESET) at the start point, setTextSelection(END) at the
    // far point.  For FX-NOTE the far point is past the end of the line, so the
    // selection covers the footnote's citation mark -- which is the whole
    // trigger.  Nothing about the frame is selected: it is inside the footnote
    // body, which is not on this line at all.
    long rectangle[4] = {0, 0, 0, 0};
    if (!parseRectangle(gSearchRectangle, rectangle)) {
      std::fprintf(stderr, "no usable search rectangle: '%s'\n",
                   gSearchRectangle.c_str());
      return 70;
    }
    const long midY = rectangle[1] + (rectangle[3] > 1 ? rectangle[3] / 2 : 1);
    std::printf("[%6ld ms] info   anchor rect=%s  dragging x %ld -> %ld at y %ld\n",
                nowMs(), gSearchRectangle.c_str(), rectangle[0],
                rectangle[0] + spanTwips, midY);
    std::fflush(stdout);

    enter("setTextSelection(RESET,END)");
    gSelectionSeen = false;
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       rectangle[0], midY);
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END,
                                       rectangle[0] + spanTwips, midY);
    if (!waitFor([] { return gSelectionSeen; }, 5000))
      std::printf("[%6ld ms] WARN   no selection callback\n", nowMs());
    exitStep("setTextSelection(RESET,END)");

    // Symptom 3.  Native: returns in ~1 ms.  WASM: does not return, and after
    // it the engine thread answers nothing else -- not search, not render, not
    // save, which all work right up until this call is made.
    enter("getSelectionTypeAndText(text/plain)");
    char *plain = nullptr;
    const int type = document->pClass->getSelectionTypeAndText(
        document, "text/plain;charset=utf-8", &plain, nullptr);
    exitStep("getSelectionTypeAndText(text/plain)");
    // Print the text, not just its length.  Whether this selection reached the
    // citation mark is the entire difference between the failing case and the
    // control, and a byte count cannot show it -- a drag that fell short would
    // look like a pass.  Compare against the same fixture at SPAN_TWIPS=2400,
    // which is the span measured NOT to trigger the hang under WASM.
    std::printf("[%6ld ms] info   selectionType=%d  text bytes=%zu  text=\"%s\"\n",
                nowMs(), type, plain ? std::string(plain).size() : 0u,
                plain ? plain : "");
    std::fflush(stdout);
    std::free(plain);
  } else {
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
  }

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
