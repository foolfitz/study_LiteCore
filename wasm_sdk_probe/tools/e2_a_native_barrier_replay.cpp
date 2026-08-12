// Finding 037: which step of the format barrier stalls on a paragraph that
// carries an inline image?
//
// The WASM run only tells us that the action never returned.  The engine's
// evidence is written when the barrier finishes, so a barrier that never
// finishes writes nothing, and the stage it died in is exactly the field that
// is missing.  Rebuilding the WASM engine with a diagnostic in it would work
// but would also mint a new artifact and unbind the A3/A4/A5 verdicts that were
// just re-swept onto ee185b3d -- finding 027's trap, for a diagnostic.
//
// So replay the same sequence natively, where a probe is cheap and nothing is
// bound to it.  The steps below are the barrier's stages in order, each with
// its own deadline and its own timing, so a stall names itself.
//
// Every anchor is run, not just the image one: a step that is slow everywhere
// is a property of the sequence, and one that is slow on a single shape is a
// property of that shape.  Without the other rows there is nothing to compare
// against and "20 seconds" is just a number.

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

namespace {

std::string jsonEscape(const std::string &value) {
  std::string out;
  for (const char character : value) {
    switch (character) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (static_cast<unsigned char>(character) < 0x20) {
          char buffer[7];
          std::snprintf(buffer, sizeof(buffer), "\\u%04x", character);
          out += buffer;
        } else {
          out += character;
        }
    }
  }
  return out;
}

struct Rectangle { long x = 0, y = 0, width = 0, height = 0; bool valid = false; };

Rectangle gCaret;
bool gSelectionSeen = false;
bool gSelectionEmpty = true;
bool gCommandResult = false;
std::string gLastCommand;

void onCallback(int type, const char *payload, void *) {
  const std::string text = payload ? payload : "";
  if (type == LOK_CALLBACK_TEXT_SELECTION) {
    gSelectionSeen = true;
    gSelectionEmpty = text.empty() || text == "EMPTY";
  } else if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
    gCommandResult = true;
    gLastCommand = text;
  } else if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR) {
    Rectangle parsed;
    if (std::sscanf(text.c_str(), "%ld, %ld, %ld, %ld", &parsed.x, &parsed.y,
                    &parsed.width, &parsed.height) == 4) {
      parsed.valid = true;
      gCaret = parsed;
    }
  }
}

using Clock = std::chrono::steady_clock;

long elapsedMs(Clock::time_point from) {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             Clock::now() - from).count();
}

// Poll rather than sleep a fixed span: the question is how long a step takes,
// and a fixed sleep would answer with the sleep.
template <typename Predicate>
long waitFor(Predicate satisfied, int deadlineMs) {
  const auto started = Clock::now();
  while (elapsedMs(started) < deadlineMs) {
    if (satisfied())
      return elapsedMs(started);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  return -1;  // deadline
}

bool positionAtAnchor(LibreOfficeKitDocument *document, const char *anchor) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"") +
      anchor + "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"long\",\"value\":0}}";
  gCaret.valid = false;
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  return waitFor([] { return gCaret.valid; }, 3000) >= 0;
}

const char *const kAnchors[] = {
    "PC-PLAIN", "PC-CJK-BOLD", "PC-LINK", "PC-FOOTNOTE", "PC-IMAGE", "PC-BREAK",
};

// One row of the barrier, replayed.  Deadlines are generous on purpose: the
// point is to measure where time goes, not to reproduce the client's 20 s.
void replay(LibreOfficeKitDocument *document, const char *anchor,
            const char *command) {
  std::string json = std::string("{\"probe\":\"barrier-replay\",\"anchor\":\"") +
                     anchor + "\",\"command\":\"" + command + "\"";

  if (!positionAtAnchor(document, anchor)) {
    std::cout << json << ",\"found\":false}\n" << std::flush;
    return;
  }
  const Rectangle restorePoint = gCaret;
  json += ",\"found\":true";

  // Stage 1: dispatch the action and wait for its own command result.
  gCommandResult = false;
  auto started = Clock::now();
  document->pClass->postUnoCommand(document, command, nullptr, true);
  long ms = waitFor([] { return gCommandResult; }, 10000);
  json += ",\"actionResultMs\":" + std::to_string(ms);

  // Stage 2: the select command, and its own result.
  gCommandResult = false;
  gSelectionSeen = false;
  started = Clock::now();
  document->pClass->postUnoCommand(document, ".uno:SelectText", nullptr, true);
  ms = waitFor([] { return gCommandResult; }, 10000);
  json += ",\"selectResultMs\":" + std::to_string(ms);

  // Stage 3: the selection callback the barrier advances on.
  ms = waitFor([] { return gSelectionSeen; }, 10000);
  json += ",\"selectionCallbackMs\":" + std::to_string(ms);

  // Stage 4: the postcondition read.
  started = Clock::now();
  char *html = document->pClass->getTextSelection(document, "text/html", nullptr);
  const std::string markup = html ? std::string(html) : std::string();
  std::free(html);
  json += ",\"readMs\":" + std::to_string(elapsedMs(started));
  json += ",\"readBytes\":" + std::to_string(markup.size());
  json += ",\"selectionType\":" +
          std::to_string(document->pClass->getSelectionType(document));

  // Stage 5: the restore, and waiting for the selection to actually clear.
  gSelectionSeen = false;
  gSelectionEmpty = false;
  started = Clock::now();
  document->pClass->setTextSelection(
      document, LOK_SETTEXTSELECTION_RESET, restorePoint.x,
      restorePoint.y + restorePoint.height / 2);
  ms = waitFor([] { return gSelectionSeen && gSelectionEmpty; }, 10000);
  json += ",\"restoreClearedMs\":" + std::to_string(ms);

  // Stage 6: is the document still answering?  This is the wedge signature the
  // browser run saw as "search timed out".
  //
  // Searching for a DIFFERENT anchor, not this row's.  The first version
  // re-searched the same string and reported handleUsableAfter=false on five
  // rows out of six, including the plain-paragraph control -- not a wedge, just
  // a search starting from a cursor already past its only match.  A signature
  // that fires on the control is not a signature.
  const char *probeAnchor =
      std::strcmp(anchor, "PC-PLAIN") == 0 ? "PC-BREAK" : "PC-PLAIN";
  started = Clock::now();
  const bool usable = positionAtAnchor(document, probeAnchor);
  json += ",\"handleUsableAfter\":" + std::string(usable ? "true" : "false");
  json += ",\"handleProbeMs\":" + std::to_string(elapsedMs(started));
  json += "}";
  std::cout << json << "\n" << std::flush;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc < 5) {
    std::cerr << "expected INSTALL PROFILE_URL DOC_URL COMMAND\n";
    return 64;
  }
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 failed\n";
    return 70;
  }
  LibreOfficeKitDocument *document =
      kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    std::cerr << "documentLoad failed\n";
    return 70;
  }
  document->pClass->initializeForRendering(document, nullptr);
  document->pClass->registerCallback(document, onCallback, nullptr);
  std::this_thread::sleep_for(std::chrono::milliseconds(500));

  for (const char *anchor : kAnchors)
    replay(document, anchor, argv[4]);

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  std::cout.flush();
  return 0;
}
