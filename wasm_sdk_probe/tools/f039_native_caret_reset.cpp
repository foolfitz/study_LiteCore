// Finding 039 native probe: is RESET silent when there is no selection to
// clear?
//
// The browser request waits for a selection callback after every
// setTextSelection(RESET).  If core only broadcasts a real selection change,
// the first reset and a reset after a range will answer, while repeated resets
// on an already-empty selection will be silent.  Run those cases on one native
// document so a missing callback cannot be attributed to the WASM bridge.
//
// Usage: f039-native-caret-reset INSTALL PROFILE_URL DOCUMENT_URL OUTDIR

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

bool parseRectangle(const char *payload, Rectangle &out) {
  if (!payload)
    return false;
  Rectangle parsed;
  if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &parsed.x, &parsed.y,
                  &parsed.width, &parsed.height) != 4)
    return false;
  // A visible caret is a zero-width rectangle; selection rectangles still
  // require a positive width at the call site that uses one as an anchor.
  parsed.valid = parsed.height > 0;
  out = parsed;
  return parsed.valid;
}

struct Trace {
  int textSelection = 0;
  int textSelectionStart = 0;
  int textSelectionEnd = 0;
  int invalidateVisibleCursor = 0;
  std::vector<std::string> textSelectionPayloads;
  std::vector<std::string> textSelectionStartPayloads;
  std::vector<std::string> textSelectionEndPayloads;

  bool anySelectionCallback() const {
    return textSelection + textSelectionStart + textSelectionEnd > 0;
  }
};

Trace gTrace;
Rectangle gSelectionRectangle;
Rectangle gCaret;

void onCallback(int type, const char *payload, void *) {
  const std::string text = payload ? payload : "";
  if (type == LOK_CALLBACK_TEXT_SELECTION) {
    ++gTrace.textSelection;
    gTrace.textSelectionPayloads.push_back(text);
    Rectangle parsed;
    if (parseRectangle(payload, parsed))
      gSelectionRectangle = parsed;
  } else if (type == LOK_CALLBACK_TEXT_SELECTION_START) {
    ++gTrace.textSelectionStart;
    gTrace.textSelectionStartPayloads.push_back(text);
  } else if (type == LOK_CALLBACK_TEXT_SELECTION_END) {
    ++gTrace.textSelectionEnd;
    gTrace.textSelectionEndPayloads.push_back(text);
  } else if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR) {
    ++gTrace.invalidateVisibleCursor;
    Rectangle parsed;
    if (parseRectangle(payload, parsed))
      gCaret = parsed;
  }
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

void emitPayloads(const char *name, const std::vector<std::string> &payloads) {
  std::cout << ",\"" << name << "\":[";
  for (std::size_t index = 0; index < payloads.size(); ++index) {
    if (index)
      std::cout << ',';
    std::cout << '"' << jsonEscape(payloads[index].c_str()) << '"';
  }
  std::cout << ']';
}

bool emitArm(const char *arm, long x, long y, int selectionTypeBeforeReset) {
  const bool selectionSeen = gTrace.anySelectionCallback();
  std::cout << "{\"arm\":\"" << arm << "\",\"x\":" << x
            << ",\"y\":" << y
            << ",\"selectionTypeBeforeReset\":"
            << selectionTypeBeforeReset
            << ",\"textSelection\":" << gTrace.textSelection
            << ",\"textSelectionStart\":" << gTrace.textSelectionStart
            << ",\"textSelectionEnd\":" << gTrace.textSelectionEnd
            << ",\"invalidateVisibleCursor\":"
            << gTrace.invalidateVisibleCursor
            << ",\"anySelectionCallback\":"
            << (selectionSeen ? "true" : "false");
  emitPayloads("textSelectionPayloads", gTrace.textSelectionPayloads);
  emitPayloads("textSelectionStartPayloads", gTrace.textSelectionStartPayloads);
  emitPayloads("textSelectionEndPayloads", gTrace.textSelectionEndPayloads);
  std::cout << "}\n";
  std::cout.flush();
  return selectionSeen;
}

bool measureReset(LibreOfficeKitDocument *document, const char *arm, long x,
                  long y) {
  const int selectionTypeBeforeReset =
      document->pClass->getSelectionType(document);
  gTrace = Trace{};
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET, x,
                                     y);
  // Native callbacks normally arrive synchronously, but leave a bounded window
  // for queued notifications before declaring an arm silent.
  drain(900);
  return emitArm(arm, x, y, selectionTypeBeforeReset);
}

bool locateText(LibreOfficeKitDocument *document, Rectangle &rectangle) {
  const std::string arguments =
      "{\"SearchItem.SearchString\":{\"type\":\"string\","
      "\"value\":\"E1-LC-ISOLATED\"},"
      "\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  gTrace = Trace{};
  gSelectionRectangle = Rectangle{};
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(900);
  rectangle = gSelectionRectangle;
  return rectangle.valid && rectangle.width > 0;
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL PROFILE_URL DOCUMENT_URL OUTDIR\n";
    return 64;
  }
  (void)argv[4];
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

  Rectangle text;
  if (!locateText(document, text)) {
    std::cerr << "could not locate E1-LC-ISOLATED selection rectangle\n";
    for (const char *arm : {"reset-1", "reset-2", "reset-3",
                            "range-then-reset", "format-then-reset"}) {
      gTrace = Trace{};
      emitArm(arm, 0, 0, -1);
    }
    std::cout << "{\"summary\":{\"setupSucceeded\":false,"
                 "\"resetWithNothingToClearIsSilent\":false}}\n";
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 0;
  }

  const long y = text.y + text.height / 2;
  const long x1 = text.x + text.width / 4;
  const long x2 = text.x + (text.width * 3) / 4;

  const bool reset1 = measureReset(document, "reset-1", x1, y);
  const bool reset2 = measureReset(document, "reset-2", x2, y);
  const bool reset3 = measureReset(document, "reset-3", x2, y);

  // Build the range outside the measured trace so the arm attributes only the
  // callback caused by clearing it, not the callbacks that created it.
  gTrace = Trace{};
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_START, x1,
                                     y);
  drain(300);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END, x2,
                                     y);
  drain(700);
  const bool rangeThenReset =
      measureReset(document, "range-then-reset", x1, y);

  // Let formatting and its status notifications settle before measuring the
  // following RESET; otherwise callbacks from the command could be attributed
  // to the wrong operation.
  document->pClass->postUnoCommand(
      document, ".uno:DefaultBullet",
      "{\"On\":{\"type\":\"boolean\",\"value\":true}}", true);
  drain(1200);
  const long formatX = gCaret.valid ? gCaret.x : x1;
  const long formatY = gCaret.valid ? gCaret.y + gCaret.height / 2 : y;
  const bool formatThenReset =
      measureReset(document, "format-then-reset", formatX, formatY);

  const bool silent = reset1 && rangeThenReset && !reset2 && !reset3 &&
                      !formatThenReset;
  std::cout << "{\"summary\":{\"setupSucceeded\":true,"
               "\"resetWithNothingToClearIsSilent\":"
            << (silent ? "true" : "false") << "}}\n";
  std::cout.flush();

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  std::cout.flush();
  std::cerr.flush();

  // This build can crash in process-static teardown while lazily creating the
  // system clipboard after a selection and DefaultBullet have both run.  All
  // owned LOK objects are already destroyed here; skip only that faulty static
  // teardown so a completed measurement does not become exit 134.
  std::_Exit(0);
}
