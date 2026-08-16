// queue-verify-caret-by-block-identity: is there a datum that says WHICH BLOCK
// the caret is in, and would it settle the three ambiguities the queue item
// claims it would?
//
// The queue item asserts that findings 046, 052's residual, and the
// same-line-different-x case "all reduce to the same missing datum".  That
// sentence was written when the three were found, not after anyone checked --
// so it is a prediction, and this probe is where it can fail.
//
// Native, for the reason finding 048's native arm was native: a payload
// observed only through our transport cannot separate what core reports from
// what our worker forwards.  **Nothing here describes the WASM artifact.**
//
// Predictions: findings/evidence/queue-block-identity/native/PREDICTION.md,
// written before this file existed.
//
// Every arm records the caret rectangle as well as the payload, because three
// of the four predictions are of the form "these two payloads are the same" --
// and an identical payload from a caret that never moved would be a broken
// probe rather than a measurement.
//
// Usage: queue-native-block-identity INSTALL_PATH PROFILE_URL DOCUMENT_URL

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

struct Rectangle {
  long x = -1, y = -1, width = 0, height = 0;
  bool valid = false;
};

Rectangle gCaret;
long gA11yCallbacks = 0;
// Where the last click went, so the judge can check the geometry an arm CLAIMS
// rather than trusting the arm's name.  Adversarial review, 2026-08-16: P-BI-6
// asserted "the same x, on the line and below it" while the judge compared only
// offsets and never saw a coordinate.  Reset by anything that moves the caret
// without a click, so an arm that was not reached by one reports -1.
long gClickX = -1, gClickY = -1;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR && payload) {
    long v[4] = {0, 0, 0, 0};
    if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &v[0], &v[1], &v[2], &v[3]) == 4)
      gCaret = Rectangle{v[0], v[1], v[2], v[3], true};
  }
  if (type == LOK_CALLBACK_A11Y_FOCUS_CHANGED)
    ++gA11yCallbacks;
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

void dispatch(LibreOfficeKitDocument *document, const char *command, int ms = 600) {
  gClickX = gClickY = -1;
  document->pClass->postUnoCommand(document, command, nullptr, false);
  drain(ms);
}

void click(LibreOfficeKitDocument *document, long x, long y, int ms = 700) {
  gClickX = x;
  gClickY = y;
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                   x, y, 1, 1, 0);
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                   x, y, 1, 1, 0);
  drain(ms);
}

// Round 1 exited here: this returns false when the caret DID NOT MOVE, which a
// search that found the text the caret is already sitting on also produces.
// "Not found" and "found where we already were" are the same observation --
// the same shape as finding 052 one level up.  Callers must navigate from
// somewhere else rather than re-search their own position.
bool searchFor(LibreOfficeKitDocument *document, const char *needle) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"") +
      needle +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  gCaret = Rectangle{};
  gClickX = gClickY = -1;
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(900);
  return gCaret.valid;
}

// The synchronous query, not the callback.  Core notifies only when the focused
// paragraph's TEXT differs (sfx2/source/view/viewsh.cxx, updateParagraphInfo),
// while the caret position behind this query is refreshed on every caret event
// -- so the two carry different information and the predictions are about this
// one.
std::string focusedParagraph(LibreOfficeKitDocument *document) {
  if (!LIBREOFFICEKIT_DOCUMENT_HAS(document, getA11yFocusedParagraph))
    return std::string();
  char *value = document->pClass->getA11yFocusedParagraph(document);
  if (!value)
    return std::string();
  std::string out(value);
  std::free(value);
  return out;
}

// One arm is one row.  `payload` is verbatim: the predictions are about
// byte-for-byte equality, and a parsed-and-reprinted payload would answer a
// different question.
void emit(const char *arm, LibreOfficeKitDocument *document,
          const char *html = nullptr, const char *plain = nullptr) {
  const std::string payload = focusedParagraph(document);
  std::cout << "{\"probe\":\"arm\",\"arm\":\"" << arm
            << "\",\"payload\":\"" << jsonEscape(payload.c_str()) << "\""
            << ",\"caretValid\":" << (gCaret.valid ? "true" : "false")
            << ",\"caretX\":" << (gCaret.valid ? gCaret.x : -1)
            << ",\"caretY\":" << (gCaret.valid ? gCaret.y : -1)
            << ",\"caretHeight\":" << (gCaret.valid ? gCaret.height : -1)
            << ",\"a11yCallbacks\":" << gA11yCallbacks
            << ",\"clickX\":" << gClickX << ",\"clickY\":" << gClickY;
  if (html)
    std::cout << ",\"html\":\"" << jsonEscape(html) << "\"";
  if (plain)
    std::cout << ",\"plainText\":\"" << jsonEscape(plain) << "\"";
  std::cout << "}\n";
  std::cout.flush();
}

void emitReadback(const char *arm, LibreOfficeKitDocument *document) {
  char *html = document->pClass->getTextSelection(document, "text/html", nullptr);
  char *plain = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", nullptr);
  emit(arm, document, html, plain);
  std::free(html);
  std::free(plain);
}

// The PRE-034 selection pair.  Round 2 used this believing it was the barrier's
// read; it is not -- finding 034 replaced it with `.uno:SelectText`, which is
// what `kFormatBarrierSelectCommand` posts in the shipped engine.  Kept because
// round 2 measured something real with it (the read escaped UPWARD to the
// previous paragraph) and dropping it would make that round unrepeatable.
[[maybe_unused]] void emitAfterLegacyPair(const char *arm,
                                          LibreOfficeKitDocument *document) {
  dispatch(document, ".uno:GoToStartOfPara", 500);
  dispatch(document, ".uno:EndOfParaSel", 700);
  emitReadback(arm, document);
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL\n";
    return 64;
  }
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
  const int kCanvas = 256;
  std::string pixels(static_cast<std::size_t>(kCanvas) * kCanvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              kCanvas, kCanvas, 0, 0, 3840, 3840);
  drain(500);

  // Accessibility has to be asked for; the engine does the same toggle in
  // refreshEditorAccessibility().  Without it every payload below would be
  // empty for a reason that has nothing to do with the question.
  const bool hasA11y =
      LIBREOFFICEKIT_DOCUMENT_HAS(document, setAccessibilityState) &&
      LIBREOFFICEKIT_DOCUMENT_HAS(document, getA11yFocusedParagraph);
  int viewId = -1;
  if (hasA11y) {
    viewId = document->pClass->getView(document);
    document->pClass->setAccessibilityState(document, viewId, true);
    drain(500);
  }
  std::cout << "{\"probe\":\"environment\",\"a11yAvailable\":"
            << (hasA11y ? "true" : "false") << ",\"viewId\":" << viewId
            << "}\n";
  std::cout.flush();

  // ---- control: a paragraph with unique text ----------------------------
  if (!searchFor(document, "BI-ANCHOR-ONE")) {
    std::cerr << "anchor BI-ANCHOR-ONE not found\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 4;
  }
  const Rectangle anchorLine = gCaret;
  click(document, anchorLine.x, anchorLine.y + anchorLine.height / 2);
  emit("control-anchor", document);

  // ---- P-BI-4: two paragraphs whose text is identical -------------------
  if (!searchFor(document, "BI-TWIN")) {
    std::cerr << "anchor BI-TWIN not found\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 5;
  }
  dispatch(document, ".uno:GoToStartOfPara", 500);
  emit("twin-first", document);
  dispatch(document, ".uno:GoDown", 600);
  emit("twin-second", document);

  // ---- P-BI-3: one line, two x ------------------------------------------
  //
  // Each x comes from its own search rather than from a width, so neither is a
  // guess.  If the paragraph ever wrapped, the two y values would differ and
  // the judge says so instead of reading the pair as a same-line result.
  if (!searchFor(document, "BI-LONG-START")) {
    std::cerr << "anchor BI-LONG-START not found\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 6;
  }
  const Rectangle longStart = gCaret;
  if (!searchFor(document, "BI-LONG-END")) {
    std::cerr << "anchor BI-LONG-END not found\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 7;
  }
  const Rectangle longEnd = gCaret;
  click(document, longStart.x, longStart.y + longStart.height / 2);
  emit("long-left", document);
  click(document, longEnd.x, longEnd.y + longEnd.height / 2);
  emit("long-right", document);

  // ---- P-BI-2a / P-BI-2b: below the text --------------------------------
  if (!searchFor(document, "BI-LAST")) {
    std::cerr << "anchor BI-LAST not found\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 8;
  }
  // The search leaves the caret at the END of the match, so `lastLine.x` is the
  // x of the last character of `BI-LAST`.  Round 1 clicked there and 2400 twips
  // to the right of there, and both clamped to the same offset -- two x on the
  // same side of the text end cannot separate anything.  Round 2 keeps that
  // pair (it is what saturation looks like) and adds one to the LEFT of it.
  const Rectangle lastLine = gCaret;
  const long belowFirstY = lastLine.y + lastLine.height * 4;
  const long belowSecondY = lastLine.y + lastLine.height * 8;
  click(document, lastLine.x, belowFirstY);
  emit("below-first", document);
  click(document, lastLine.x, belowSecondY);
  emit("below-second-same-x", document);
  click(document, lastLine.x + 2400, belowSecondY);
  emit("below-second-other-x", document);
  click(document, lastLine.x - 400, belowSecondY);
  emit("below-second-inside-x", document);

  // The control for the pair above: if `below-second-same-x` reports nothing
  // moved, this shows clicks were still being delivered when it said so.
  click(document, anchorLine.x, anchorLine.y + anchorLine.height / 2);
  emit("below-control-on-text", document);

  // ---- round 3: the arms round 2 needed and did not have -----------------
  //
  // Round 2's below-* arms all reported the same offset, and could not tell
  // "the clamp ignores x" from "the caret was already there and no click did
  // anything".  Every arm here therefore starts by putting the caret on a
  // DIFFERENT paragraph, so a payload naming BI-LAST is a click that arrived.
  const long onLineY = lastLine.y + lastLine.height / 2;
  click(document, lastLine.x - 400, onLineY);
  emit("on-line-inside-x", document);

  click(document, anchorLine.x, anchorLine.y + anchorLine.height / 2);
  emit("before-below-from-elsewhere", document);
  click(document, lastLine.x, belowFirstY);
  emit("below-from-elsewhere", document);

  click(document, anchorLine.x, anchorLine.y + anchorLine.height / 2);
  emit("before-below-inside-x", document);
  click(document, lastLine.x - 400, belowFirstY);
  emit("below-from-elsewhere-inside-x", document);

  // ---- P-BI-1: finding 046's cell, and it mutates, so it goes last -------
  //
  // Navigated from BELOW the empty paragraph, because the caret is currently on
  // BI-ANCHOR-ONE: searching for where you already are looks exactly like
  // searching for something that is not there (see searchFor above).  That is
  // what ended round 1 at exit 9.
  if (!searchFor(document, "BI-AFTER-EMPTY")) {
    std::cerr << "anchor BI-AFTER-EMPTY not found\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 9;
  }
  dispatch(document, ".uno:GoToStartOfPara", 500);
  dispatch(document, ".uno:GoUp", 600);
  const Rectangle emptyLine = gCaret;
  const long emptyY = emptyLine.valid
      ? emptyLine.y + emptyLine.height / 2
      : anchorLine.y + anchorLine.height + anchorLine.height / 2;
  click(document, anchorLine.x + 20, emptyY);
  emit("empty-caret", document);
  dispatch(document, ".uno:DefaultBullet", 900);
  emit("empty-after-bullet", document);

  // The SHIPPED barrier's read.  `.uno:SelectText` sets m_bInSelect and nothing
  // on that path clears it (finding 039), so anything posted after it is
  // measuring a shell in selection mode -- which is why the legacy pair is not
  // run in the same round as this one.  Round 2 has the legacy pair; this arm
  // is the one the product actually performs.
  dispatch(document, ".uno:SelectText", 900);
  emitReadback("empty-after-selecttext", document);

  // Did the bullet reach the document?  Without this the readback above could
  // be describing a document nothing happened to.
  const std::string saveUrl = std::string(argv[3]) + ".after.odt";
  const bool saved =
      document->pClass->saveAs(document, saveUrl.c_str(), "odt", nullptr);
  std::cout << "{\"probe\":\"save\",\"url\":\"" << jsonEscape(saveUrl.c_str())
            << "\",\"ok\":" << (saved ? "true" : "false") << "}\n";
  std::cout.flush();

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
