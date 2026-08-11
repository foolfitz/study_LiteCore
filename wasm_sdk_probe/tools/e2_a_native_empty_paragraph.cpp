// Does .uno:EndOfParaSel produce a selection on an EMPTY paragraph?
//
// The format barrier waits in AwaitingSelection for a non-empty TEXT_SELECTION
// after posting GoToStartOfPara + EndOfParaSel.  If an empty paragraph yields
// no selection, that wait never ends and the barrier wedges the document handle
// -- and "press the list button on a blank line" is an ordinary gesture, not an
// exotic one.  Every E2-A fixture has text in every paragraph, which is why 375
// judged dispatches never reached it.
//
// The WASM attempt at this measured nothing: placing the caret by geometry put
// it on the paragraph *above* the empty one (the readback came back with that
// paragraph's text), and the harness check validated the requested coordinate
// rather than where the caret landed.  Native has no such problem -- the caret
// can be walked there with .uno:GoDown from a paragraph found by text, and the
// callback payload is visible directly.
//
// Nothing here can hang: there is no barrier, only dispatches and reads.
//
// Usage: e2-a-native-empty-paragraph INSTALL_PATH PROFILE_URL DOCUMENT_URL

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
  long x = 0, y = 0, width = 0, height = 0;
  bool valid = false;
};

Rectangle gCaret;
// The exact payload the barrier's AwaitingSelection stage consumes.  "EMPTY"
// is a real value core sends; an absent callback is a different fact, so the
// two are kept distinguishable rather than both reported as "no selection".
std::string gSelectionPayload;
bool gSelectionSeen = false;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_TEXT_SELECTION) {
    gSelectionSeen = true;
    gSelectionPayload = payload ? payload : "";
  }
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR && payload) {
    Rectangle parsed;
    if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &parsed.x, &parsed.y,
                    &parsed.width, &parsed.height) == 4) {
      parsed.valid = true;
      gCaret = parsed;
    }
  }
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

void dispatch(LibreOfficeKitDocument *document, const char *command,
              bool notify) {
  document->pClass->postUnoCommand(document, command, nullptr, notify);
  drain(400);
}

// Returns whether the caret was actually placed.  It used to return nothing and
// skip the placement when no cursor callback had arrived, which made a case
// silently measure from wherever the previous one left off -- `triple-text-
// caret-at-end` did exactly that on the first run (caretY -1) and its result
// was not evidence about the position it named.
bool positionAtAnchor(LibreOfficeKitDocument *document, const char *anchor) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") +
      anchor +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  // Start every case from the top of the document.  Without this, a search for
  // text that the previous case already selected produces no movement and no
  // callback, placement is skipped, and the case measures from wherever the
  // previous one left the caret -- which silently poisoned a whole matrix run
  // (a case named offset-zero reported caretY 1807, the empty paragraph two
  // paragraphs away).
  document->pClass->postUnoCommand(document, ".uno:GoToStartOfDoc", nullptr,
                                   false);
  drain(400);
  gCaret = Rectangle{};
  gSelectionPayload.clear();
  gSelectionSeen = false;
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(700);
  Rectangle hit = gCaret;
  // A search whose match is already selected produces no cursor callback, and
  // the caret then silently stays wherever the previous case left it -- which
  // is how two rows came back with caretY -1 and had to be discarded.  The
  // match's own selection rectangle answers the same question, so fall back to
  // it rather than to the previous case's state.
  if (!hit.valid && gSelectionSeen) {
    Rectangle parsed;
    if (std::sscanf(gSelectionPayload.c_str(), "%ld, %ld, %ld, %ld", &parsed.x,
                    &parsed.y, &parsed.width, &parsed.height) == 4) {
      parsed.valid = true;
      hit = parsed;
    }
  }
  if (!hit.valid)
    return false;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     hit.x, hit.y + hit.height / 2);
  drain(400);
  return true;
}

// Where in the paragraph to put the caret before measuring.  This used to be a
// bool meaning "offset 0", with the default silently described as "caret at the
// end" -- but placement lands on the anchor rectangle's LEFT edge, so those
// rows measured something near the start and were named for the opposite.
//
// Offset Len() matters most: it is where the WASM harness puts the caret
// (caretAtAnchor uses rectangle.x + width), so it is the position all 375
// judged dispatches started from, and a repair that broke it would break
// everything currently passing.
// A search leaves the caret AFTER the match, so placement at the caret
// rectangle lands on offset Len() -- measured: asking for CaretAt::End from
// there escaped to the next paragraph (caretY 2196 -> 2585), which is
// GoCurrPara doing exactly what this probe exists to document.  There is
// therefore no separate "End": as-placed already is it.
//
// This matters beyond the probe: the WASM harness places the caret at
// rectangle.x + width, also offset Len.  Both agree, which is why every one of
// the 375 judged dispatches started from the one offset where the current
// sequence is correct.
enum class CaretAt { Len, Zero, Middle };

void putCaret(LibreOfficeKitDocument *document, CaretAt where) {
  if (where == CaretAt::Zero)
    dispatch(document, ".uno:GoToStartOfPara", false);
  else if (where == CaretAt::Middle)
    // One character back from Len, i.e. strictly inside the paragraph -- the
    // offset where neither edge rule can fire.
    dispatch(document, ".uno:GoLeft", false);
}

const char *caretName(CaretAt where) {
  switch (where) {
  case CaretAt::Zero: return "offset-zero";
  case CaretAt::Middle: return "offset-middle";
  default: return "offset-len";
  }
}

// A snapshot of what a reader would see right now.
struct Snapshot {
  int selectionType = -1;
  std::size_t htmlBytes = 0;
  std::string text;
};

Snapshot snapshot(LibreOfficeKitDocument *document) {
  Snapshot value;
  char *html = document->pClass->getTextSelection(document, "text/html",
                                                  nullptr);
  char *text = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", nullptr);
  value.selectionType = document->pClass->getSelectionType(document);
  value.htmlBytes = html ? std::strlen(html) : 0;
  value.text = text ? text : "";
  std::free(html);
  std::free(text);
  return value;
}

void emitSnapshot(const char *name, const Snapshot &value) {
  std::cout << ",\"" << name << "\":{\"selectionType\":" << value.selectionType
            << ",\"htmlBytes\":" << value.htmlBytes << ",\"text\":\""
            << jsonEscape(value.text.c_str()) << "\"}";
}

// One measurement: walk `down` paragraphs from the anchor, run the barrier's
// own selection pair, and report what came back.
//
// The state is read BEFORE the pair as well as after.  Without that, "the
// selection covers the paragraph above" cannot be told apart from "the pair did
// nothing and this was already on screen" -- and the first run of this probe
// produced exactly that ambiguity.
void measure(LibreOfficeKitDocument *document, const char *label,
             const char *anchor, int down, CaretAt where = CaretAt::Len) {
  const bool placed = positionAtAnchor(document, anchor);
  if (!placed) {
    // Not a measurement.  Saying so beats emitting a row whose caret
    // position is whatever the previous case happened to leave behind.
    std::cout << "{\"case\":\"" << label
              << "\",\"sequence\":\"pair\",\"placed\":false,"
                 "\"skipped\":true}\n";
    std::cout.flush();
    return;
  }
  for (int step = 0; step < down; ++step)
    dispatch(document, ".uno:GoDown", false);
  putCaret(document, where);
  const Rectangle caretBefore = gCaret;
  const Snapshot before = snapshot(document);

  gSelectionSeen = false;
  gSelectionPayload.clear();
  dispatch(document, ".uno:GoToStartOfPara", true);
  const Rectangle caretAfterStart = gCaret;
  const bool startMovedCaret =
      caretBefore.valid && caretAfterStart.valid &&
      (caretBefore.x != caretAfterStart.x || caretBefore.y != caretAfterStart.y);
  dispatch(document, ".uno:EndOfParaSel", true);

  const Snapshot after = snapshot(document);

  std::cout << "{\"case\":\"" << label << "\",\"anchor\":\"" << anchor
            << "\",\"caretAt\":\"" << caretName(where)
            << "\",\"goDown\":" << down
            << ",\"caretY\":" << (caretBefore.valid ? caretBefore.y : -1)
            << ",\"caretYAfterStartOfPara\":"
            << (caretAfterStart.valid ? caretAfterStart.y : -1)
            << ",\"startOfParaMovedCaret\":"
            << (startMovedCaret ? "true" : "false")
            << ",\"selectionCallbackSeen\":"
            << (gSelectionSeen ? "true" : "false")
            << ",\"selectionPayload\":\""
            << jsonEscape(gSelectionPayload.c_str()) << "\"";
  emitSnapshot("before", before);
  emitSnapshot("after", after);
  std::cout << "}\n";
  std::cout.flush();
}

// Candidate repair: nudge the caret off whichever edge it is sitting on before
// selecting.  GoCurrPara() only leaves the paragraph when the caret is ALREADY
// at the edge it is being sent to, so EndOfPara-then-StartOfPara should be safe
// for any non-empty paragraph from any offset.  Should is why this is measured.
//
// An empty paragraph is predicted to stay broken (nOld == nNew == 0 at both
// ends, so both moves leave the paragraph) and is included precisely so the
// prediction can fail visibly instead of being assumed.
void measureTriple(LibreOfficeKitDocument *document, const char *label,
                   const char *anchor, int down, CaretAt where) {
  const bool placed = positionAtAnchor(document, anchor);
  if (!placed) {
    // Not a measurement.  Saying so beats emitting a row whose caret
    // position is whatever the previous case happened to leave behind.
    std::cout << "{\"case\":\"" << label
              << "\",\"sequence\":\"triple\",\"placed\":false,"
                 "\"skipped\":true}\n";
    std::cout.flush();
    return;
  }
  for (int step = 0; step < down; ++step)
    dispatch(document, ".uno:GoDown", false);
  putCaret(document, where);
  const Rectangle caretBefore = gCaret;

  dispatch(document, ".uno:GoToEndOfPara", true);
  const Rectangle afterEnd = gCaret;
  dispatch(document, ".uno:GoToStartOfPara", true);
  const Rectangle afterStart = gCaret;
  dispatch(document, ".uno:EndOfParaSel", true);
  const Snapshot after = snapshot(document);

  std::cout << "{\"case\":\"" << label << "\",\"sequence\":\"triple\""
            << ",\"placed\":" << (placed ? "true" : "false")
            << ",\"caretAt\":\"" << caretName(where) << "\""
            << ",\"caretY\":" << (caretBefore.valid ? caretBefore.y : -1)
            << ",\"caretYAfterEndOfPara\":" << (afterEnd.valid ? afterEnd.y : -1)
            << ",\"caretYAfterStartOfPara\":"
            << (afterStart.valid ? afterStart.y : -1);
  emitSnapshot("after", after);
  std::cout << "}\n";
  std::cout.flush();
}

// The candidate fable found: .uno:SelectText (FN_SELECT_PARA).  Core's dispatch
// handler carries the offset-0 clamp itself --
// sw/source/uibase/shells/textsh1.cxx:1975 in this baseline:
//
//     if ( !rWrtSh.IsSttOfPara() ) rWrtSh.SttPara();
//     else                         rWrtSh.EnterStdMode();
//     rWrtSh.EndPara( true );
//
// so the escape that breaks both motion pairs is already handled upstream, on
// the dispatch path, for a non-empty paragraph at any offset.  Reading that is
// not the same as measuring it, which is what this does.
void measureSelectText(LibreOfficeKitDocument *document, const char *label,
                       const char *anchor, int down, CaretAt where) {
  const bool placed = positionAtAnchor(document, anchor);
  if (!placed) {
    // Not a measurement.  Saying so beats emitting a row whose caret
    // position is whatever the previous case happened to leave behind.
    std::cout << "{\"case\":\"" << label
              << "\",\"sequence\":\"selecttext\",\"placed\":false,"
                 "\"skipped\":true}\n";
    std::cout.flush();
    return;
  }
  for (int step = 0; step < down; ++step)
    dispatch(document, ".uno:GoDown", false);
  putCaret(document, where);
  const Rectangle caretBefore = gCaret;

  gSelectionSeen = false;
  gSelectionPayload.clear();
  dispatch(document, ".uno:SelectText", true);
  const Snapshot after = snapshot(document);

  std::cout << "{\"case\":\"" << label << "\",\"sequence\":\"selecttext\""
            << ",\"placed\":" << (placed ? "true" : "false")
            << ",\"caretAt\":\"" << caretName(where) << "\""
            << ",\"caretY\":" << (caretBefore.valid ? caretBefore.y : -1)
            << ",\"selectionCallbackSeen\":"
            << (gSelectionSeen ? "true" : "false")
            << ",\"selectionPayload\":\""
            << jsonEscape(gSelectionPayload.c_str()) << "\"";
  emitSnapshot("after", after);
  std::cout << "}\n";
  std::cout.flush();
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
    const char *error =
        kit->pClass->getError ? kit->pClass->getError(kit) : nullptr;
    std::cerr << (error ? error : "documentLoad returned null") << '\n';
    kit->pClass->destroy(kit);
    return 3;
  }
  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);

  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              canvas, canvas, 0, 0, 3840, 3840);
  drain(500);

  // The control comes first, and it is what makes the empty-paragraph line
  // readable: the same sequence on a paragraph that *has* text must produce a
  // selection, or the probe is measuring its own dispatch and not the shape of
  // the paragraph.
  // The full matrix.  Two sequences x three caret offsets on a non-empty
  // paragraph, then the two empty paragraphs -- which are different failures
  // and must not be collapsed into one row.
  //
  // offset-len is the position every one of the 375 judged A3/A4 dispatches
  // started from, so it is the regression guard: a repair that fixes offset-zero
  // and breaks offset-len is worse than no repair.
  for (int variant = 0; variant < 3; ++variant) {
    const CaretAt where = variant == 0   ? CaretAt::Zero
                          : variant == 1 ? CaretAt::Middle
                                         : CaretAt::Len;
    const std::string suffix = std::string("-") + caretName(where);
    measure(document, (std::string("pair-text") + suffix).c_str(),
            "E1-EMPTY-AFTER", 0, where);
    measureSelectText(document, (std::string("selecttext-text") + suffix).c_str(),
                      "E1-EMPTY-AFTER", 0, where);
  }

  measure(document, "pair-empty-mid-document", "E1-EMPTY-BEFORE", 1,
          CaretAt::Len);
  measureSelectText(document, "selecttext-empty-mid-document", "E1-EMPTY-BEFORE", 1,
                    CaretAt::Len);
  measure(document, "pair-empty-document-end", "E1-EMPTY-AFTER", 1,
          CaretAt::Len);
  measureSelectText(document, "selecttext-empty-document-end", "E1-EMPTY-AFTER", 1,
                    CaretAt::Len);

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
