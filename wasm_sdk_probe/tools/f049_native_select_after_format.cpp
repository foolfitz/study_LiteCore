// Task #49 native probe: after a format action, why does a range selection
// select nothing?
//
// P2 measured it on the combination artifact -- same document, same
// coordinates, same format action: the product path returns in 251ms and
// reports `none`, while the identical selection without a preceding format
// action returns in 20ms with the text.  What P2 could not say is *which* part
// of the barrier does it.
//
// The prediction being tested is written down before this file ran, in
// findings/evidence/sdk-e2/discovery/049-selection-after-format/PREDICTION.md:
// .uno:SelectText goes through FN_SELECT_PARA -> EndPara(true) ->
// MoveCursor(true) -> SttSelect(), which sets SwWrtShell::m_bInSelect and is
// never paired with EndSelect() on that path.  Both of the barrier's RESETs
// leave the flag alone (bClearMark takes the branch that skips SttSelect and
// EndSelect both), so the caller's END later calls SttSelect(), hits
// `if (m_bInSelect) return;` and never reaches SetMark().  No mark, no
// selection.
//
// Native, because the same sequence run natively separates "core does this"
// from "the WASM build does this".  Nothing here describes the wasm artifact.
//
// Usage: f049-native-select-after-format INSTALL PROFILE_URL DOCUMENT_URL

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

const char *const kAnchor = "E1-LC-ISOLATED";
const char *const kListOnArguments = "{\"On\":{\"type\":\"boolean\","
                                     "\"value\":true}}";

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
  parsed.valid = parsed.height > 0;
  out = parsed;
  return parsed.valid;
}

int gTextSelectionCallbacks = 0;
Rectangle gSelectionRectangle;
bool gSelectionRectangleSeen = false;

void onCallback(int type, const char *payload, void *) {
  if (type != LOK_CALLBACK_TEXT_SELECTION)
    return;
  ++gTextSelectionCallbacks;
  Rectangle parsed;
  if (parseRectangle(payload, parsed)) {
    gSelectionRectangle = parsed;
    gSelectionRectangleSeen = true;
  }
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

std::string takeSelectionText(LibreOfficeKitDocument *document) {
  char *used = nullptr;
  char *text = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", &used);
  std::string out = text ? std::string(text) : std::string();
  std::free(text);
  std::free(used);
  return out;
}

void post(LibreOfficeKitDocument *document, const char *command,
          const char *arguments) {
  document->pClass->postUnoCommand(document, command, arguments, true);
  drain(400);
}

LibreOfficeKitDocument *openDocument(LibreOfficeKit *kit, const char *url) {
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, url);
  if (!document)
    return nullptr;
  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  // The layout has to exist before a coordinate means anything.
  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              canvas, canvas, 0, 0, 3840, 3840);
  drain(500);
  return document;
}

// Located once, on a document that is then thrown away.
//
// The search itself selects, and a selection made by ExecuteSearch is exactly
// the kind of shell state this probe is trying to measure.  Running it inside
// an arm would put the thing under test into the setup, so the anchor is
// found on a separate load and only the numbers cross over.  The file is the
// same on every load, so the layout is too.
bool locateAnchor(LibreOfficeKit *kit, const char *url, Rectangle &out) {
  LibreOfficeKitDocument *document = openDocument(kit, url);
  if (!document)
    return false;
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") + kAnchor + "\"},"
      "\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  gSelectionRectangle = Rectangle{};
  gSelectionRectangleSeen = false;
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(900);
  out = gSelectionRectangle;
  document->pClass->destroy(document);
  return gSelectionRectangleSeen && out.valid && out.width > 0;
}

// How the arm asks for its range selection.
//
// ResetEnd is what the engine ships today (probe_engine.cpp,
// OXSDK_EDITOR_SELECTION_TEXT_HANDLES: RESET then END, no START).  The other
// two are round 2's questions -- does a failed attempt clear whatever is
// stuck, and does inserting a START avoid the problem altogether.
enum class TailMode { ResetEnd, ResetEndTwice, ResetStartEnd };

struct Arm {
  const char *name;
  bool format;      // dispatch .uno:DefaultBullet
  bool barrier;     // RESET -> .uno:SelectText -> getTextSelection(html) -> RESET
  const char *tail; // extra command after the barrier, or nullptr
  TailMode mode;
};

// The order inside `barrier` is the engine's order, not a tidied version of it:
// probe_engine.cpp posts the restore RESET *before* .uno:SelectText
// (FormatBarrierStage::SelectQueued), reads the html postcondition, and posts
// the restore RESET again (FormatBarrierStage::ReadQueued).
const Arm kArms[] = {
    {"A-control", false, false, nullptr, TailMode::ResetEnd},
    {"B-format-only", true, false, nullptr, TailMode::ResetEnd},
    {"C-select-text-only", false, true, nullptr, TailMode::ResetEnd},
    {"D-full-barrier", true, true, nullptr, TailMode::ResetEnd},
    {"E-full-barrier-escape", true, true, ".uno:Escape", TailMode::ResetEnd},
    {"F-full-barrier-goleft", true, true, ".uno:GoLeft", TailMode::ResetEnd},
    {"G-barrier-then-twice", true, true, nullptr, TailMode::ResetEndTwice},
    {"H-barrier-reset-start-end", true, true, nullptr, TailMode::ResetStartEnd},
    {"I-control-reset-start-end", false, false, nullptr,
     TailMode::ResetStartEnd},
};

struct Measurement {
  std::string text;
  int selectionType = -1;
  int callbacks = 0;
  bool selected() const { return !text.empty(); }
};

Measurement measureResetEnd(LibreOfficeKitDocument *document, long x1, long x2,
                            long y) {
  gTextSelectionCallbacks = 0;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET, x1,
                                     y);
  drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END, x2, y);
  drain(600);
  Measurement out;
  out.text = takeSelectionText(document);
  out.selectionType = document->pClass->getSelectionType(document);
  out.callbacks = gTextSelectionCallbacks;
  return out;
}

Measurement measureResetStartEnd(LibreOfficeKitDocument *document, long x1,
                                 long x2, long y) {
  gTextSelectionCallbacks = 0;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET, x1,
                                     y);
  drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_START, x1,
                                     y);
  drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END, x2, y);
  drain(600);
  Measurement out;
  out.text = takeSelectionText(document);
  out.selectionType = document->pClass->getSelectionType(document);
  out.callbacks = gTextSelectionCallbacks;
  return out;
}

void emitMeasurement(const char *label, const Measurement &measurement) {
  std::cout << ",\"" << label << "\":{\"bytes\":" << measurement.text.size()
            << ",\"text\":\"" << jsonEscape(measurement.text.c_str())
            << "\",\"selectionType\":" << measurement.selectionType
            << ",\"textSelectionCallbacks\":" << measurement.callbacks
            << ",\"selected\":" << (measurement.selected() ? "true" : "false")
            << '}';
}

struct ArmResult {
  bool first = false;   // did the arm's first range selection select?
  bool second = false;  // ResetEndTwice only; false everywhere else
  bool ran = false;
};

void emitStep(bool &first, const char *label, int selectionType) {
  if (!first)
    std::cout << ',';
  first = false;
  std::cout << "{\"step\":\"" << label << "\",\"selectionType\":"
            << selectionType << '}';
}

ArmResult runArm(LibreOfficeKit *kit, const char *url, const Arm &arm,
                 const Rectangle &anchor) {
  ArmResult result;
  LibreOfficeKitDocument *document = openDocument(kit, url);
  if (!document) {
    std::cout << "{\"arm\":\"" << arm.name << "\",\"loaded\":false}\n";
    std::cout.flush();
    return result;
  }
  result.ran = true;

  const long caretY = anchor.y + anchor.height / 2;
  const long caretX = anchor.x + 1;
  const long x1 = anchor.x + anchor.width / 4;
  const long x2 = anchor.x + (anchor.width * 3) / 4;

  std::cout << "{\"arm\":\"" << arm.name << "\",\"loaded\":true,\"steps\":[";
  bool first = true;

  // Put the caret where the action is about to be dispatched from, the way the
  // demo's click-then-poll gesture does.
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     caretX, caretY);
  drain(400);
  emitStep(first, "caret-placed",
           document->pClass->getSelectionType(document));

  if (arm.format) {
    post(document, ".uno:DefaultBullet", kListOnArguments);
    emitStep(first, "after-format",
             document->pClass->getSelectionType(document));
  }

  if (arm.barrier) {
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       caretX, caretY);
    drain(400);
    emitStep(first, "after-barrier-restore-1",
             document->pClass->getSelectionType(document));

    post(document, ".uno:SelectText", nullptr);
    emitStep(first, "after-select-text",
             document->pClass->getSelectionType(document));

    char *html = document->pClass->getTextSelection(document, "text/html",
                                                    nullptr);
    const std::size_t htmlBytes = html ? std::strlen(html) : 0;
    std::free(html);
    std::cout << ",{\"step\":\"after-html-readback\",\"htmlBytes\":"
              << htmlBytes << '}';

    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       caretX, caretY);
    drain(400);
    emitStep(first, "after-barrier-restore-2",
             document->pClass->getSelectionType(document));
  }

  if (arm.tail) {
    post(document, arm.tail, nullptr);
    emitStep(first, "after-tail",
             document->pClass->getSelectionType(document));
  }

  // The measurement.  ResetEnd is the engine's own range selection: RESET then
  // END, no START -- see probe_engine.cpp's OXSDK_EDITOR_SELECTION_TEXT_HANDLES.
  const Measurement primary =
      arm.mode == TailMode::ResetStartEnd
          ? measureResetStartEnd(document, x1, x2, caretY)
          : measureResetEnd(document, x1, x2, caretY);
  result.first = primary.selected();

  // Round 2, arm G: repeat the identical call with nothing dispatched in
  // between.  If the second attempt succeeds, whatever blocked the first was
  // cleared by the first attempt itself, which is the signature the
  // `if (m_bInSelect) return;` reading predicts and no other candidate does.
  Measurement repeat;
  bool hasRepeat = false;
  if (arm.mode == TailMode::ResetEndTwice) {
    repeat = measureResetEnd(document, x1, x2, caretY);
    result.second = repeat.selected();
    hasRepeat = true;
  }

  // Per-arm sanity check.  If the range selection came back empty, this says
  // whether the document was still reachable at all -- an arm that cannot
  // select even everything is a broken arm, not a finding.
  post(document, ".uno:SelectAll", nullptr);
  const std::size_t selectAllChars = takeSelectionText(document).size();

  std::cout << "],\"mode\":\""
            << (arm.mode == TailMode::ResetEnd
                    ? "reset-end"
                    : arm.mode == TailMode::ResetEndTwice ? "reset-end-twice"
                                                          : "reset-start-end")
            << "\",\"tail\":" << (arm.tail ? "\"" : "null");
  if (arm.tail)
    std::cout << arm.tail << '"';
  emitMeasurement("attempt1", primary);
  if (hasRepeat)
    emitMeasurement("attempt2", repeat);
  std::cout << ",\"selectAllBytes\":" << selectAllChars << "}\n";
  std::cout.flush();

  document->pClass->destroy(document);
  return result;
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "expected INSTALL PROFILE_URL DOCUMENT_URL\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }

  Rectangle anchor;
  if (!locateAnchor(kit, argv[3], anchor)) {
    std::cerr << "could not locate " << kAnchor << '\n';
    std::cout << "{\"summary\":{\"setupSucceeded\":false}}\n";
    kit->pClass->destroy(kit);
    return 3;
  }
  std::cout << "{\"anchor\":{\"x\":" << anchor.x << ",\"y\":" << anchor.y
            << ",\"width\":" << anchor.width << ",\"height\":" << anchor.height
            << "}}\n";
  std::cout.flush();

  constexpr std::size_t kArmCount = sizeof(kArms) / sizeof(kArms[0]);
  ArmResult results[kArmCount];
  for (std::size_t index = 0; index < kArmCount; ++index)
    results[index] = runArm(kit, argv[3], kArms[index], anchor);

  // Both predicted shapes, named so a reader does not have to re-derive them
  // from the arm table.  Round 1: control and format-only select, both barrier
  // arms do not, .uno:Escape does not rescue and .uno:GoLeft does.  Round 2:
  // the repeat succeeds where the first attempt failed, and inserting a START
  // avoids the failure -- with an unbarriered control proving START+END is not
  // simply always fine.
  const bool round1 = results[0].first && results[1].first &&
                      !results[2].first && !results[3].first &&
                      !results[4].first && results[5].first;
  const bool round2 = !results[6].first && results[6].second &&
                      results[7].first && results[8].first;
  std::cout << "{\"summary\":{\"setupSucceeded\":true";
  for (std::size_t index = 0; index < kArmCount; ++index) {
    std::cout << ",\"" << kArms[index].name << "\":"
              << (results[index].first ? "true" : "false");
    if (kArms[index].mode == TailMode::ResetEndTwice)
      std::cout << ",\"" << kArms[index].name << "-attempt2\":"
                << (results[index].second ? "true" : "false");
  }
  std::cout << ",\"matchesRound1PredictedShape\":"
            << (round1 ? "true" : "false")
            << ",\"matchesRound2PredictedShape\":"
            << (round2 ? "true" : "false") << "}}\n";
  std::cout.flush();

  kit->pClass->destroy(kit);
  return 0;
}
