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

void positionAtAnchor(LibreOfficeKitDocument *document, const char *anchor) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") +
      anchor +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  gCaret = Rectangle{};
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(700);
  const Rectangle hit = gCaret;
  if (hit.valid)
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       hit.x, hit.y + hit.height / 2);
  drain(400);
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
             const char *anchor, int down, bool caretToParagraphStart = false) {
  positionAtAnchor(document, anchor);
  for (int step = 0; step < down; ++step)
    dispatch(document, ".uno:GoDown", false);
  // Put the caret exactly at offset 0 before measuring.  An empty paragraph is
  // always at offset 0, so if that is what makes GoToStartOfPara leave the
  // paragraph, a text paragraph with the caret at its start must behave the
  // same -- and clicking at the start of a line is not a rare gesture.
  if (caretToParagraphStart)
    dispatch(document, ".uno:GoToStartOfPara", false);
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
  measure(document, "control-text-paragraph", "E1-EMPTY-BEFORE", 0);
  measure(document, "empty-paragraph", "E1-EMPTY-BEFORE", 1);
  measure(document, "control-text-paragraph-below", "E1-EMPTY-BEFORE", 2);
  measure(document, "text-paragraph-caret-at-offset-zero", "E1-EMPTY-AFTER", 0,
          true);

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
