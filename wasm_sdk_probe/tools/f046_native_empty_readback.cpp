// Finding 046: what does the readback for an EMPTY paragraph actually contain?
//
// 046's remedy needs a criterion and does not have one.  The 2026-08-15
// correction is why: the same empty paragraph comes back
// `postcondition-not-met` after the product's click and `multi-block-readback`
// after a zero-width selection, both with `postBlocks: 0`, and the difference
// turns on `itemCount` -- a field the shipped product does not project.  So the
// question "is zero blocks 'nothing was read' or 'only list items were read'"
// cannot be answered in a browser on this artifact at all.
//
// It can be answered here.  This probe captures the RAW `text/html` readback --
// not its length, which is all `e2_a_native_empty_paragraph.cpp` recorded -- and
// emits it as the JSONL shape `tools/test_format_readback_parser.py` already
// consumes.  That tool slices the scanner out of probe_engine.cpp and compiles
// it, so the classification comes from the shipped parser rather than from a
// Python restatement of its rules.
//
// Nothing here can hang: there is no barrier, only dispatches and reads.
//
// Predictions: findings/evidence/046/native/PREDICTION.md, written first.
//
// Usage: f046-native-empty-readback INSTALL_PATH PROFILE_URL DOCUMENT_URL

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
bool gSelectionSeen = false;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR && payload) {
    long v[4] = {0, 0, 0, 0};
    if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &v[0], &v[1], &v[2], &v[3]) == 4)
      gCaret = Rectangle{v[0], v[1], v[2], v[3], true};
  }
  if (type == LOK_CALLBACK_TEXT_SELECTION && payload && *payload)
    gSelectionSeen = true;
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

void dispatch(LibreOfficeKitDocument *document, const char *command, int ms = 500) {
  document->pClass->postUnoCommand(document, command, nullptr, false);
  drain(ms);
}

bool searchFor(LibreOfficeKitDocument *document, const char *needle) {
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

// One row.  `html` is the whole payload, verbatim: the parser tool needs the
// markup, and a length would answer a different question than the one asked.
void emit(const char *arm, LibreOfficeKitDocument *document,
          const Rectangle &caret, bool pair) {
  char *html = document->pClass->getTextSelection(document, "text/html", nullptr);
  char *text = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", nullptr);
  const int type = document->pClass->getSelectionType(document);
  std::cout << "{\"probe\":\"readback\",\"anchor\":\"" << arm
            << "\",\"pair\":" << (pair ? "true" : "false")
            << ",\"selectionType\":" << type
            << ",\"selectionCallbackSeen\":" << (gSelectionSeen ? "true" : "false")
            << ",\"caretY\":" << (caret.valid ? caret.y : -1)
            << ",\"plainText\":\"" << jsonEscape(text) << "\""
            << ",\"html\":\"" << jsonEscape(html) << "\"}\n";
  std::cout.flush();
  std::free(html);
  std::free(text);
}

// The barrier's own selection pair, exactly as probe_engine.cpp posts it.
void selectionPair(LibreOfficeKitDocument *document) {
  gSelectionSeen = false;
  dispatch(document, ".uno:GoToStartOfPara", 500);
  dispatch(document, ".uno:EndOfParaSel", 700);
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

  // The anchor with text, so the empty paragraph can be reached from a KNOWN
  // position rather than from wherever the document opened.
  if (!searchFor(document, "E1-EMPTY-BEFORE")) {
    std::cerr << "anchor E1-EMPTY-BEFORE not found\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 4;
  }
  const Rectangle textLine = gCaret;

  // ---- control: the paragraph that HAS text -----------------------------
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                   textLine.x, textLine.y + textLine.height / 2,
                                   1, 1, 0);
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                   textLine.x, textLine.y + textLine.height / 2,
                                   1, 1, 0);
  drain(500);
  selectionPair(document);
  emit("click-text-pair", document, gCaret, true);

  // Walk one paragraph down to the empty one, and record where that is.
  dispatch(document, ".uno:GoDown", 600);
  const Rectangle emptyLine = gCaret;
  std::cout << "{\"probe\":\"position\",\"anchor\":\"empty-line\",\"y\":"
            << (emptyLine.valid ? emptyLine.y : -1) << ",\"validRectangle\":"
            << (emptyLine.valid ? "true" : "false") << "}\n";
  std::cout.flush();

  const long emptyY = emptyLine.valid
      ? emptyLine.y + emptyLine.height / 2
      : textLine.y + textLine.height + textLine.height / 2;
  const long emptyX = textLine.x + 20;

  // ---- arm 1: the product's gesture, a click ----------------------------
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                   emptyX, emptyY, 1, 1, 0);
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                   emptyX, emptyY, 1, 1, 0);
  drain(600);
  gSelectionSeen = false;
  emit("click-empty-bare", document, gCaret, false);
  selectionPair(document);
  emit("click-empty-pair", document, gCaret, true);

  // ---- arm 2: the harness gesture, a zero-width selection ---------------
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     emptyX, emptyY);
  drain(600);
  gSelectionSeen = false;
  emit("select-empty-bare", document, gCaret, false);
  selectionPair(document);
  emit("select-empty-pair", document, gCaret, true);

  // ---- arm 3: what the barrier actually reads AFTER the action ----------
  //
  // The browser's `postBlocks: 0` comes from the POSTCONDITION read, which
  // happens after the dispatch -- by which time an empty paragraph has become
  // an empty LIST ITEM.  `<ul><li></li></ul>` parses as blockCount 0 with
  // itemCount 1, and two of them as blockCount 0 with itemCount 2, which is
  // `multiBlock` with no block in it: exactly the pair of shapes finding 046
  // inferred and could not measure.  So the action goes in, and the readback
  // is captured the way the barrier captures it.
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                   emptyX, emptyY, 1, 1, 0);
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                   emptyX, emptyY, 1, 1, 0);
  drain(600);
  dispatch(document, ".uno:DefaultBullet", 900);
  gSelectionSeen = false;
  emit("after-bullet-bare", document, gCaret, false);
  selectionPair(document);
  emit("after-bullet-pair", document, gCaret, true);

  // ---- arm 4: the LAST paragraph, which is also empty --------------------
  //
  // 046 names this as a separate known path (`.uno:SelectText` returning no
  // selection callback -> stage deadline), so it cannot be assumed to behave
  // like the middle one.  `.uno:GoToEndOfDoc` lands on it without geometry.
  dispatch(document, ".uno:GoToEndOfDoc", 700);
  const Rectangle lastLine = gCaret;
  std::cout << "{\"probe\":\"position\",\"anchor\":\"last-line\",\"y\":"
            << (lastLine.valid ? lastLine.y : -1) << ",\"validRectangle\":"
            << (lastLine.valid ? "true" : "false") << "}\n";
  std::cout.flush();
  gSelectionSeen = false;
  emit("last-empty-bare", document, gCaret, false);
  selectionPair(document);
  emit("last-empty-pair", document, gCaret, true);

  // Did the bullet in arm 3 actually reach the document?  Without this the
  // readbacks above could be describing a document nothing happened to, and
  // "the pair reads the previous paragraph" would be indistinguishable from
  // "the action never applied".
  if (argc == 4) {
    const std::string saveUrl = std::string(argv[3]) + ".after.odt";
    const bool saved = document->pClass->saveAs(document, saveUrl.c_str(),
                                                "odt", nullptr);
    std::cout << "{\"probe\":\"save\",\"url\":\"" << jsonEscape(saveUrl.c_str())
              << "\",\"ok\":" << (saved ? "true" : "false") << "}\n";
    std::cout.flush();
  }

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
