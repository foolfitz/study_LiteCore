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
enum class TailMode {
  ResetEnd,
  ResetEndTwice,
  // Round 4, arm AE: the repeat with no drain and no readback between the two
  // attempts.  The first attempt is judged only by the TEXT_SELECTION callback
  // count, which is passive -- reading the text would be the very thing this
  // arm exists to rule out.
  ResetEndTwiceNoReadback,
  ResetStartEnd,
};

// Which x coordinates the three calls use.
//
// Standard is what rounds 1-3 used: RESET and START share an x, so an arm could
// not tell an anchor at the RESET position from one at the START position.
// Triple separates them; Reverse asks the same question with END to the left of
// START.
enum class Coords { Standard, Triple, Reverse };

struct Arm {
  const char *name;
  bool format;      // dispatch .uno:DefaultBullet
  bool barrier;     // RESET -> .uno:SelectText -> getTextSelection(html) -> RESET
  const char *tail; // extra command after the barrier, or nullptr
  TailMode mode;
  // Round 3: one uno command dispatched straight after the caret is placed and
  // before anything else, to ask whether *that command* poisons the next range
  // selection.  Rounds 1 and 2 only ever asked it about .uno:SelectText, but
  // the cause is an unpaired SttSelect(), which is a shape rather than a
  // property of one command.
  const char *poison = nullptr;
  const char *poisonArgs = nullptr;
  Coords coords = Coords::Standard;
  // Round 4, arm AF: a markless RESET at the END coordinate before the real
  // measurement.  It runs the same direct SwCursorShell::SetCursor the failed
  // END runs, but takes the bClearMark branch and so never calls EndSelect().
  // If this rescues the selection, the rescue is not EndSelect().
  bool marklessResetFirst = false;
};

const char *const kSearchArguments =
    "{\"SearchItem.SearchString\":{\"type\":\"string\","
    "\"value\":\"E1-LC-BETWEEN\"},"
    "\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
    "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";

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

    // Round 3.  One command each, dispatched with the caret collapsed, then the
    // engine's own range selection.  J is the negative control and K the
    // positive one; if those two do not disagree the rest of the sweep says
    // nothing.
    {"J-poison-none", false, false, nullptr, TailMode::ResetEndTwice, nullptr},
    {"K-poison-selecttext", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:SelectText"},
    {"L-poison-search", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:ExecuteSearch", kSearchArguments},
    {"M-poison-undo", false, false, nullptr, TailMode::ResetEndTwice, ".uno:Undo"},
    {"N-poison-redo", false, false, nullptr, TailMode::ResetEndTwice, ".uno:Redo"},
    {"O-poison-bold", false, false, nullptr, TailMode::ResetEndTwice, ".uno:Bold"},
    {"P-poison-italic", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:Italic"},
    {"Q-poison-underline", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:Underline"},
    {"R-poison-strikeout", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:Strikeout"},
    {"S-poison-bullet", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:DefaultBullet", kListOnArguments},
    {"T-poison-numbering", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:DefaultNumbering", kListOnArguments},
    {"U-poison-removebullets", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:RemoveBullets"},
    {"V-poison-styleapply", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:StyleApply",
     "{\"Style\":{\"type\":\"string\",\"value\":\"Heading 1\"},"
     "\"FamilyName\":{\"type\":\"string\",\"value\":\"ParagraphStyles\"}}"},
    {"W-poison-delete", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:Delete"},
    {"X-poison-backspace", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:SwBackspace"},
    {"Y-poison-insertpara", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:InsertPara"},
    {"Z-poison-linebreak", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:InsertLinebreak"},
    {"AB-poison-trackchanges", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:TrackChanges"},
    {"AC-poison-accepttracked", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:AcceptTrackedChanges"},
    {"AD-poison-escape", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:Escape"},

    // Round 4.  Every arm here was named by the adversarial review of rounds
    // 1-3; see codex-review-round1-3.md and PREDICTION-round4.md.
    //
    // AE and AF separate "the failed attempt cleared it" from "the readback,
    // the wait, or a plain SetCursor cleared it".  AG/AH/AI ask whether the
    // proposed fix anchors where it claims to, with AI as the reference the
    // other two have to match.  AJ/AK repeat that with END left of START.
    {"AE-twice-no-readback", true, true, nullptr,
     TailMode::ResetEndTwiceNoReadback},
    {"AF-markless-reset-first", true, true, nullptr, TailMode::ResetEndTwice,
     nullptr, nullptr, Coords::Standard, true},
    {"AG-endpoints-stuck", true, true, nullptr, TailMode::ResetStartEnd,
     nullptr, nullptr, Coords::Triple},
    {"AH-endpoints-clean", false, false, nullptr, TailMode::ResetStartEnd,
     nullptr, nullptr, Coords::Triple},
    {"AI-endpoints-reference", false, false, nullptr, TailMode::ResetEnd},
    {"AJ-reverse-stuck", true, true, nullptr, TailMode::ResetStartEnd, nullptr,
     nullptr, Coords::Reverse},
    {"AK-reverse-clean", false, false, nullptr, TailMode::ResetStartEnd,
     nullptr, nullptr, Coords::Reverse},

    // Last on purpose.  Round 3 died here with "Unspecified Application
    // Error" and took the four arms after it down with it; at the end it can
    // only lose itself.
    {"AA-poison-annotation", false, false, nullptr, TailMode::ResetEndTwice,
     ".uno:InsertAnnotation"},
};

struct Measurement {
  std::string text;
  int selectionType = -1;
  int callbacks = 0;
  bool selected() const { return !text.empty(); }
};

Measurement measureResetEnd(LibreOfficeKitDocument *document, long xReset,
                            long xEnd, long y, bool readBack = true) {
  gTextSelectionCallbacks = 0;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     xReset, y);
  if (readBack)
    drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END, xEnd,
                                     y);
  Measurement out;
  if (readBack) {
    drain(600);
    out.text = takeSelectionText(document);
    out.selectionType = document->pClass->getSelectionType(document);
  }
  out.callbacks = gTextSelectionCallbacks;
  return out;
}

Measurement measureResetStartEnd(LibreOfficeKitDocument *document, long xReset,
                                 long xStart, long xEnd, long y) {
  gTextSelectionCallbacks = 0;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     xReset, y);
  drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_START,
                                     xStart, y);
  drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END, xEnd,
                                     y);
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
  std::string text;     // exactly what the arm selected, for endpoint checks
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
  const long x0 = anchor.x + anchor.width / 8;
  const long x1 = anchor.x + anchor.width / 4;
  const long x2 = anchor.x + (anchor.width * 3) / 4;
  // RESET, START, END.  Standard keeps rounds 1-3 comparable; the other two
  // exist because an arm where RESET and START share an x cannot say which of
  // them the selection anchored to.
  const long xReset = arm.coords == Coords::Triple    ? x0
                      : arm.coords == Coords::Reverse ? x2
                                                      : x1;
  const long xStart = arm.coords == Coords::Reverse ? x2 : x1;
  const long xEnd = arm.coords == Coords::Reverse ? x0 : x2;

  std::cout << "{\"arm\":\"" << arm.name << "\",\"loaded\":true,\"steps\":[";
  bool first = true;

  // Put the caret where the action is about to be dispatched from, the way the
  // demo's click-then-poll gesture does.
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     caretX, caretY);
  drain(400);
  emitStep(first, "caret-placed",
           document->pClass->getSelectionType(document));

  if (arm.poison) {
    post(document, arm.poison, arm.poisonArgs);
    // Back to the caret, the way the barrier's restore does.  Without this the
    // arm would measure "a selection left behind by the command" instead of
    // "state left behind by the command", and a command that selects something
    // would look identical to one that poisons.
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       caretX, caretY);
    drain(400);
    emitStep(first, "after-poison",
             document->pClass->getSelectionType(document));
  }

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
  if (arm.marklessResetFirst) {
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       xEnd, caretY);
    drain(400);
    emitStep(first, "after-markless-reset",
             document->pClass->getSelectionType(document));
  }

  const bool noReadback = arm.mode == TailMode::ResetEndTwiceNoReadback;
  const Measurement primary =
      arm.mode == TailMode::ResetStartEnd
          ? measureResetStartEnd(document, xReset, xStart, xEnd, caretY)
          : measureResetEnd(document, xReset, xEnd, caretY, !noReadback);
  // With no readback there is no text to judge, so the passive callback count
  // stands in: a selection that materialised would have broadcast one.
  result.first = noReadback ? primary.callbacks > 0 : primary.selected();
  result.text = primary.text;

  // Round 2, arm G: repeat the identical call with no uno command dispatched in
  // between.  If the second attempt succeeds, whatever blocked the first was
  // cleared by the first attempt itself, which is what the
  // `if (m_bInSelect) return;` reading predicts.
  //
  // "No uno command" is not "nothing": the readback below and the drain inside
  // measureResetEnd both happen between the two attempts, so this alone does
  // not exclude a cursor/layout priming explanation.  Arms AE and AF exist to
  // separate those; an earlier version of this comment claimed no other
  // candidate could produce this reading, which was wrong.
  Measurement repeat;
  bool hasRepeat = false;
  if (arm.mode == TailMode::ResetEndTwice || noReadback) {
    repeat = measureResetEnd(document, xReset, xEnd, caretY);
    result.second = repeat.selected();
    hasRepeat = true;
  }

  // Per-arm sanity check.  If the range selection came back empty, this says
  // whether the document was still reachable at all -- an arm that cannot
  // select even everything is a broken arm, not a finding.
  post(document, ".uno:SelectAll", nullptr);
  const std::size_t selectAllChars = takeSelectionText(document).size();

  std::cout << "],\"mode\":\""
            << (arm.mode == TailMode::ResetEnd ? "reset-end"
                : arm.mode == TailMode::ResetEndTwice
                    ? "reset-end-twice"
                    : arm.mode == TailMode::ResetEndTwiceNoReadback
                          ? "reset-end-twice-no-readback"
                          : "reset-start-end")
            << "\",\"xReset\":" << xReset << ",\"xStart\":" << xStart
            << ",\"xEnd\":" << xEnd
            << ",\"tail\":" << (arm.tail ? "\"" : "null");
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

  // Predicates are looked up by arm name, not by index: this table has grown
  // three times, and an index-based predicate silently means something else
  // after a reorder.
  auto armResult = [&](const char *name) -> const ArmResult & {
    for (std::size_t index = 0; index < kArmCount; ++index)
      if (std::strcmp(kArms[index].name, name) == 0)
        return results[index];
    std::cerr << "unknown arm in summary: " << name << '\n';
    std::abort();
  };
  auto selected = [&](const char *name) { return armResult(name).first; };
  // The two-attempt signature: the first attempt failed and the second, with
  // no uno command dispatched in between, succeeded.
  auto healed = [&](const char *name) {
    const ArmResult &result = armResult(name);
    return !result.first && result.second;
  };
  auto textOf = [&](const char *name) -> const std::string & {
    return armResult(name).text;
  };

  // Round 1: control and format-only select, both barrier arms do not,
  // .uno:Escape does not rescue and .uno:GoLeft does.
  const bool round1 = selected("A-control") && selected("B-format-only") &&
                      !selected("C-select-text-only") &&
                      !selected("D-full-barrier") &&
                      !selected("E-full-barrier-escape") &&
                      selected("F-full-barrier-goleft");

  // Round 2: the repeat succeeds where the first attempt failed, and inserting
  // a START avoids the failure -- with an unbarriered control proving START+END
  // is not simply always fine.
  const bool round2 = healed("G-barrier-then-twice") &&
                      selected("H-barrier-reset-start-end") &&
                      selected("I-control-reset-start-end");

  // Round 3 verdict per poison arm.  "Poisoned" is the two-attempt signature,
  // not "came back empty": a command that deletes the text under the
  // coordinates also comes back empty, and then both attempts fail.
  std::string poisoned;
  std::string emptyBoth;
  for (std::size_t index = 0; index < kArmCount; ++index) {
    if (!kArms[index].poison || results[index].first)
      continue;
    std::string &bucket = results[index].second ? poisoned : emptyBoth;
    if (!bucket.empty())
      bucket += ',';
    bucket += '"';
    bucket += kArms[index].name;
    bucket += '"';
  }
  // J is the negative control and K the positive one; the sweep says nothing
  // about the other commands if those two agree.
  const bool round3 =
      selected("J-poison-none") && healed("K-poison-selecttext");

  // Round 4, named by the adversarial review of rounds 1-3.  AE: the repeat
  // still heals with no readback and no wait between the attempts, so neither
  // of those is what healed it.  AF: a markless RESET -- the same direct
  // SetCursor, minus EndSelect -- does NOT heal it.
  const bool round4Healing = healed("AE-twice-no-readback") &&
                             healed("AF-markless-reset-first");
  // AG/AH/AI: the proposed fix selects the same characters in the stuck state
  // as in the clean one, and the same ones a plain RESET+END from the START
  // position selects -- so it anchors at START, not at RESET.
  const bool round4Endpoints =
      !textOf("AG-endpoints-stuck").empty() &&
      textOf("AG-endpoints-stuck") == textOf("AH-endpoints-clean") &&
      textOf("AG-endpoints-stuck") == textOf("AI-endpoints-reference");
  // AJ/AK: the same question with END to the left of START.
  const bool round4Reverse =
      !textOf("AJ-reverse-stuck").empty() &&
      textOf("AJ-reverse-stuck") == textOf("AK-reverse-clean");

  std::cout << "{\"summary\":{\"setupSucceeded\":true";
  for (std::size_t index = 0; index < kArmCount; ++index) {
    std::cout << ",\"" << kArms[index].name << "\":"
              << (results[index].first ? "true" : "false");
    if (kArms[index].mode == TailMode::ResetEndTwice ||
        kArms[index].mode == TailMode::ResetEndTwiceNoReadback)
      std::cout << ",\"" << kArms[index].name << "-attempt2\":"
                << (results[index].second ? "true" : "false");
  }
  std::cout << ",\"matchesRound1PredictedShape\":"
            << (round1 ? "true" : "false")
            << ",\"matchesRound2PredictedShape\":"
            << (round2 ? "true" : "false")
            << ",\"round3ControlsDisagree\":" << (round3 ? "true" : "false")
            << ",\"round3Poisoned\":[" << poisoned
            << "],\"round3EmptyBothAttempts\":[" << emptyBoth
            << "],\"round4HealingSurvivesBothControls\":"
            << (round4Healing ? "true" : "false")
            << ",\"round4EndpointsAgree\":"
            << (round4Endpoints ? "true" : "false")
            << ",\"round4ReverseAgrees\":"
            << (round4Reverse ? "true" : "false")
            << ",\"agEndpointsText\":\""
            << jsonEscape(textOf("AG-endpoints-stuck").c_str())
            << "\",\"ahEndpointsText\":\""
            << jsonEscape(textOf("AH-endpoints-clean").c_str())
            << "\",\"aiReferenceText\":\""
            << jsonEscape(textOf("AI-endpoints-reference").c_str())
            << "\",\"ajReverseText\":\""
            << jsonEscape(textOf("AJ-reverse-stuck").c_str())
            << "\",\"akReverseText\":\""
            << jsonEscape(textOf("AK-reverse-clean").c_str()) << "\"}}\n";
  std::cout.flush();

  kit->pClass->destroy(kit);
  return 0;
}
