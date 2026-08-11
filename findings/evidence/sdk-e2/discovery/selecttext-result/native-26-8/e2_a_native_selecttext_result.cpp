// E2-A native probe: is .uno:SelectText usable as the barrier's select step?
//
// Finding 034 measured that .uno:SelectText selects the intended paragraph from
// every reachable caret offset, which is why the barrier is switching to it.
// It did NOT measure the two properties the barrier actually runs on:
//
//   1. Does .uno:SelectText emit LOK_CALLBACK_UNO_COMMAND_RESULT carrying
//      commandName ".uno:SelectText"?  Since finding 033 the barrier leaves
//      AwaitingSelection only when that result has been attributed AND the
//      selection is non-empty.  A silent command stalls every dispatch until
//      the deadline, which would not be a repair, it would be a dead feature.
//      "This command returns no result" is exactly the belief native
//      measurement overturned on 2026-08-05 and again for EndOfParaSel on
//      2026-08-11 (8 dispatches / 8 results), so it is measured, not reasoned.
//
//   2. Does the readback taken through SelectText still carry the tags
//      parseFormatReadback keys on, for all five closed actions?  The
//      feasibility measurement behind SPEC E2-A 2.8 was taken through the
//      GoToStartOfPara + EndOfParaSel pair.  Substituting the selection step
//      and assuming the markup is unchanged would be assuming the answer.
//
// And one property the deadline design depends on: on the document-end empty
// paragraph, finding 034 measured selType 0 -- no selection at all.  Does the
// command result still arrive there?  If it does, the barrier sits in
// AwaitingSelection with selectionResultSeen=true and no rectangles, which is
// precisely the stall the deadline exists to end; if it does not, the stall has
// two causes and the evidence should say so.
//
// Every result payload is emitted raw and counted by commandName.  Counting is
// done in this process rather than by grepping the log afterwards, because a
// grep for the wrong token silently reports zero -- how the first pass of
// run_e2_a_native.sh produced a wrong headline.
//
// Nothing here can hang: dispatches and reads only, no barrier.
//
// Usage: e2-a-native-selecttext-result INSTALL PROFILE_URL STYLED_URL EMPTY_URL OUTDIR

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
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

// Extracts commandName the same way the engine's commandResultMatches does --
// find the field, expect a quoted value.  Matching more loosely here would
// measure a property the engine does not actually test for.
std::string commandNameOf(const char *payload) {
  if (!payload)
    return std::string();
  const char *field = std::strstr(payload, "\"commandName\"");
  if (!field)
    return std::string();
  const char *colon = std::strchr(field, ':');
  if (!colon)
    return std::string();
  const char *open = std::strchr(colon, '"');
  if (!open)
    return std::string();
  const char *close = std::strchr(open + 1, '"');
  if (!close)
    return std::string();
  return std::string(open + 1, close - open - 1);
}

long gEventSeq = 0;
Rectangle gCaret;

// Per-case trace, reset immediately before the dispatch under measurement.
struct Trace {
  int results = 0;                  // results carrying the watched commandName
  long firstResultSeq = -1;
  long firstSelectionSeq = -1;      // first non-empty TEXT_SELECTION
  bool anySelectionCallback = false;
  std::string selectionPayload;
};
Trace gTrace;
std::string gWatchedCommand;

std::map<std::string, int> gResultCounts;
std::map<std::string, int> gDispatchCounts;

void onCallback(int type, const char *payload, void *) {
  ++gEventSeq;
  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
    const std::string name = commandNameOf(payload);
    ++gResultCounts[name.empty() ? std::string("<no-commandName>") : name];
    std::cout << "{\"event\":\"uno-result\",\"seq\":" << gEventSeq
              << ",\"commandName\":\"" << jsonEscape(name.c_str())
              << "\",\"payload\":\"" << jsonEscape(payload) << "\"}\n";
    std::cout.flush();
    if (!gWatchedCommand.empty() && name == gWatchedCommand) {
      ++gTrace.results;
      if (gTrace.firstResultSeq < 0)
        gTrace.firstResultSeq = gEventSeq;
    }
  }
  if (type == LOK_CALLBACK_TEXT_SELECTION) {
    gTrace.anySelectionCallback = true;
    gTrace.selectionPayload = payload ? payload : "";
    // "EMPTY" is a value core really sends; it is not the same fact as no
    // callback at all, and the engine treats it as no rectangles.
    const bool nonEmpty = payload && *payload &&
                          std::strcmp(payload, "EMPTY") != 0;
    if (nonEmpty && gTrace.firstSelectionSeq < 0)
      gTrace.firstSelectionSeq = gEventSeq;
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
              const char *arguments, bool notify, int drainMs = 400) {
  ++gDispatchCounts[command];
  document->pClass->postUnoCommand(document, command, arguments, notify);
  drain(drainMs);
}

// Same shape as the finding 034 probe: start from the top of the document every
// time, and fall back to the match's selection rectangle when the search
// produces no cursor callback, so a case never silently measures from wherever
// the previous one left the caret.
bool positionAtAnchor(LibreOfficeKitDocument *document, const char *anchor) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") +
      anchor +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  document->pClass->postUnoCommand(document, ".uno:GoToStartOfDoc", nullptr,
                                   false);
  drain(400);
  gCaret = Rectangle{};
  gTrace = Trace{};
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(700);
  Rectangle hit = gCaret;
  if (!hit.valid && gTrace.anySelectionCallback) {
    Rectangle parsed;
    if (std::sscanf(gTrace.selectionPayload.c_str(), "%ld, %ld, %ld, %ld",
                    &parsed.x, &parsed.y, &parsed.width, &parsed.height) == 4) {
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

struct Readback {
  int selectionType = -1;
  std::size_t htmlBytes = 0;
  std::string html;
  std::string text;
};

Readback readSelection(LibreOfficeKitDocument *document) {
  Readback value;
  char *html = document->pClass->getTextSelection(document, "text/html",
                                                  nullptr);
  char *text = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", nullptr);
  value.selectionType = document->pClass->getSelectionType(document);
  value.htmlBytes = html ? std::strlen(html) : 0;
  value.html = html ? html : "";
  value.text = text ? text : "";
  std::free(html);
  std::free(text);
  return value;
}

// One measurement of the select step alone: place the caret, optionally walk
// down, run .uno:SelectText, report what the barrier would have seen.
void measureSelect(LibreOfficeKitDocument *document, const char *label,
                   const char *anchor, int down) {
  const bool placed = positionAtAnchor(document, anchor);
  if (!placed) {
    std::cout << "{\"case\":\"" << label
              << "\",\"placed\":false,\"skipped\":true}\n";
    std::cout.flush();
    return;
  }
  for (int step = 0; step < down; ++step)
    dispatch(document, ".uno:GoDown", nullptr, false);

  gWatchedCommand = ".uno:SelectText";
  gTrace = Trace{};
  dispatch(document, ".uno:SelectText", nullptr, true, 600);
  const Trace trace = gTrace;
  gWatchedCommand.clear();

  const Readback readback = readSelection(document);
  std::cout << "{\"case\":\"" << label << "\",\"anchor\":\""
            << jsonEscape(anchor) << "\",\"goDown\":" << down
            << ",\"placed\":true"
            << ",\"selectTextResults\":" << trace.results
            << ",\"resultSeq\":" << trace.firstResultSeq
            << ",\"selectionSeq\":" << trace.firstSelectionSeq
            << ",\"selectionCallbackSeen\":"
            << (trace.anySelectionCallback ? "true" : "false")
            << ",\"selectionPayload\":\""
            << jsonEscape(trace.selectionPayload.c_str())
            << "\",\"selectionType\":" << readback.selectionType
            << ",\"htmlBytes\":" << readback.htmlBytes << ",\"text\":\""
            << jsonEscape(readback.text.c_str()) << "\",\"html\":\""
            << jsonEscape(readback.html.c_str()) << "\"}\n";
  std::cout.flush();
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 6) {
    std::cerr << "expected INSTALL PROFILE_URL STYLED_URL EMPTY_URL OUTDIR\n";
    return 64;
  }
  const std::string outDir = argv[5];
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }

  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');

  // ---- Phase 1: styled-list, the three paragraph kinds ---------------------
  {
    LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
    if (!document) {
      std::cerr << "documentLoad(styled) returned null\n";
      kit->pClass->destroy(kit);
      return 3;
    }
    document->pClass->initializeForRendering(document, "{}");
    document->pClass->registerCallback(document, onCallback, nullptr);
    document->pClass->paintTile(document,
                                reinterpret_cast<unsigned char *>(pixels.data()),
                                canvas, canvas, 0, 0, 3840, 3840);
    drain(500);

    std::cout << "{\"phase\":\"select-only\",\"fixture\":\"styled-list\"}\n";
    measureSelect(document, "select-heading", "E1-STYLED-HEADING", 0);
    measureSelect(document, "select-body", "bold anchor", 0);
    measureSelect(document, "select-list-item", "E1-LIST-ONE", 0);

    // ---- Phase 2: readback through SelectText for all five closed actions --
    //
    // The postcondition the barrier compares is parsed out of this markup, so
    // if the substitution changed what the serialiser writes, it shows here and
    // not three hours later in a browser sweep.
    std::cout << "{\"phase\":\"after-dispatch\",\"fixture\":\"styled-list\"}\n";
    const struct {
      const char *label;
      const char *command;
      const char *arguments;
    } steps[] = {
        {"list-unordered", ".uno:DefaultBullet",
         "{\"On\":{\"type\":\"boolean\",\"value\":true}}"},
        {"list-ordered", ".uno:DefaultNumbering",
         "{\"On\":{\"type\":\"boolean\",\"value\":true}}"},
        {"list-none", ".uno:RemoveBullets", nullptr},
        {"paragraph-heading", ".uno:StyleApply",
         "{\"Style\":{\"type\":\"string\",\"value\":\"Heading 1\"},"
         "\"FamilyName\":{\"type\":\"string\",\"value\":\"ParagraphStyles\"}}"},
        {"paragraph-body", ".uno:StyleApply",
         "{\"Style\":{\"type\":\"string\",\"value\":\"Text body\"},"
         "\"FamilyName\":{\"type\":\"string\",\"value\":\"ParagraphStyles\"}}"},
    };
    for (const auto &step : steps) {
      if (!positionAtAnchor(document, "bold anchor")) {
        std::cout << "{\"case\":\"after-" << step.label
                  << "\",\"placed\":false,\"skipped\":true}\n";
        continue;
      }
      dispatch(document, step.command, step.arguments, true, 1200);

      gWatchedCommand = ".uno:SelectText";
      gTrace = Trace{};
      dispatch(document, ".uno:SelectText", nullptr, true, 600);
      const Trace trace = gTrace;
      gWatchedCommand.clear();

      const Readback readback = readSelection(document);
      const std::string url =
          "file://" + outDir + "/after-" + step.label + ".odt";
      const bool saved =
          document->pClass->saveAs(document, url.c_str(), "odt", nullptr);
      std::cout << "{\"case\":\"after-" << step.label
                << "\",\"placed\":true,\"command\":\"" << step.command
                << "\",\"selectTextResults\":" << trace.results
                << ",\"resultSeq\":" << trace.firstResultSeq
                << ",\"selectionSeq\":" << trace.firstSelectionSeq
                << ",\"selectionType\":" << readback.selectionType
                << ",\"htmlBytes\":" << readback.htmlBytes << ",\"text\":\""
                << jsonEscape(readback.text.c_str()) << "\",\"html\":\""
                << jsonEscape(readback.html.c_str()) << "\",\"saved\":"
                << (saved ? "true" : "false") << "}\n";
      std::cout.flush();
      drain(200);
    }
    document->pClass->destroy(document);
  }

  // ---- Phase 3: the empty paragraphs, where the deadline has to carry it ---
  {
    LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[4]);
    if (!document) {
      std::cerr << "documentLoad(empty) returned null\n";
      kit->pClass->destroy(kit);
      return 3;
    }
    document->pClass->initializeForRendering(document, "{}");
    document->pClass->registerCallback(document, onCallback, nullptr);
    document->pClass->paintTile(document,
                                reinterpret_cast<unsigned char *>(pixels.data()),
                                canvas, canvas, 0, 0, 3840, 3840);
    drain(500);

    std::cout << "{\"phase\":\"empty\",\"fixture\":\"empty-paragraph\"}\n";
    // One paragraph down from each anchor is the empty paragraph; the second is
    // the last paragraph of the document, where finding 034 measured no
    // selection at all.
    measureSelect(document, "select-empty-mid-document", "E1-EMPTY-BEFORE", 1);
    measureSelect(document, "select-empty-document-end", "E1-EMPTY-AFTER", 1);
    document->pClass->destroy(document);
  }

  // ---- Summary -------------------------------------------------------------
  std::cout << "{\"summary\":{\"dispatches\":{";
  bool first = true;
  for (const auto &entry : gDispatchCounts) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << '"' << jsonEscape(entry.first.c_str()) << "\":" << entry.second;
  }
  std::cout << "},\"unoCommandResults\":{";
  first = true;
  for (const auto &entry : gResultCounts) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << '"' << jsonEscape(entry.first.c_str()) << "\":" << entry.second;
  }
  std::cout << "}}}\n";
  std::cout.flush();

  kit->pClass->destroy(kit);
  return 0;
}
