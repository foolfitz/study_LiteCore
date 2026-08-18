// Finding 059, replacement predicate: does the STATE readback track the
// document for the four inline slots on a COLLAPSED caret?
//
// Prediction was committed first:
//   findings/evidence/059/native/predicate/PREDICTION.md
//
// A separate program from f059_native_inline_format_argument.cpp on purpose.
// That probe's four arms and its after-all-arms.odt are existing evidence for
// the mechanism ("core applies the command and reports failure"); rewriting it
// in place would overwrite the bytes that finding rests on.
//
// What this asks, and why it is not what the other probe asked
// ------------------------------------------------------------
// The other probe read core's LOK_CALLBACK_UNO_COMMAND_RESULT.  Finding 020
// already showed that field lying in both directions on list commands, and
// core's source shows `wasModified` is the document's dirty flag sampled
// BEFORE the dispatch (init.cxx:5517-5518).  So neither field is a candidate.
//
// The surviving candidate is the one the format barrier already gates on:
// LOK_CALLBACK_STATE_CHANGED.  Finding 020 measured it agreeing with the saved
// file where the other two disagreed -- but only for PARAGRAPH-level commands
// with the caret inside existing text.  An inline format on a collapsed caret
// is a different shape: it sets the pending attributes of the insertion point
// and changes nothing until something is typed.
//
// So each arm: move the caret to a paragraph of its own by keystroke, clear the
// buffers, dispatch, record every state change that arrives, type its own marker,
// and the document verdict is read from the style attached to that marker.
//
// Arms
// ----
//   control            no command at all -- the marker must come back unstyled,
//                      or "the marker is bold" could be the fixture's own style
//   <slot>-true        parameterised, value:true
//   <slot>-false       parameterised, value:false
//   readonly-refusal   the view is set read-only first, so this is a command
//                      core KNOWS but cannot run.  An unknown slot would emit
//                      no result callback at all (dispatchcommand.cxx:48-50)
//                      and would measure nothing.
//
// No selection command is issued anywhere in this probe.  That is prediction P7:
// if the state arrives anyway, the predicate does not need the barrier's
// .uno:SelectText step, which on an empty paragraph is the shape that produced
// finding 046.
//
// Usage: f059-native-format-predicate INSTALL PROFILE_URL DOC_URL OUT_DIR_URL

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

// Every callback is stamped with a monotonically increasing sequence, so an arm
// can prove it saw a FRESH one rather than reading whatever was left over.  An
// arm that cannot show that is reported as unanswered and must not be scored --
// without this, an analyzer that defaults a missing field scores a silent arm
// as a pass.
int gSequence = 0;
std::string gLastUnoResult;
int gUnoResultSeq = -1;
std::vector<std::pair<int, std::string>> gStateChanges;

void onCallback(int type, const char *payload, void *) {
  if (!payload)
    return;
  ++gSequence;
  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
    gLastUnoResult = payload;
    gUnoResultSeq = gSequence;
  } else if (type == LOK_CALLBACK_STATE_CHANGED) {
    gStateChanges.emplace_back(gSequence, payload);
  }
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

// com::sun::star::awt::Key, and vcl's modifier bits.  Spelled out rather than
// included so this probe keeps building against nothing but the LOK headers.
constexpr int KEY_DOWN = 1024;
constexpr int KEY_HOME = 1028;
constexpr int KEY_END = 1029;
constexpr int KEY_MOD1 = 0x2000;

void pressKey(LibreOfficeKitDocument *document, int keyCode) {
  document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT, 0, keyCode);
  drain(150);
}

// The caret goes to the end of paragraph `index`, by keystroke.
//
// NOT by clicking a guessed y.  Two arms that share a paragraph would let one
// arm's PENDING inline attribute reach the next arm's marker, and a click below
// the last line snaps back up to it -- which is exactly how arms would end up
// sharing a paragraph without saying so.  The fixture
// (tools/create_f059_predicate_fixture.py) gives every paragraph one short
// line, so Down moves by a paragraph and not within one.
void caretToParagraph(LibreOfficeKitDocument *document, int index) {
  pressKey(document, KEY_HOME | KEY_MOD1);
  for (int step = 0; step < index; ++step)
    pressKey(document, KEY_DOWN);
  pressKey(document, KEY_END);
  drain(400);
}

void typeText(LibreOfficeKitDocument *document, const char *text) {
  for (const char *it = text; *it; ++it) {
    document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT,
                                   static_cast<int>(*it), 0);
    drain(120);
  }
  drain(400);
}

std::string argumentFor(const char *slot, bool enabled) {
  return std::string("{\"") + slot + "\":{\"type\":\"boolean\",\"value\":"
         + (enabled ? "true" : "false") + "}}";
}

// One arm.  `slot` is the argument name the engine uses (Bold/Italic/Underline/
// Strikeout); `command` is the .uno: name.  `slot` nullptr means dispatch
// nothing at all.
void arm(LibreOfficeKitDocument *document, const char *name,
         const char *command, const char *slot, bool enabled,
         int paragraph, const char *marker, bool readOnly) {
  caretToParagraph(document, paragraph);
  // Cleared AFTER the caret move: placing the caret itself makes core broadcast the
  // attributes at the new position, and counting those as the dispatch's answer
  // would make every arm look like it worked.
  drain(400);
  gStateChanges.clear();
  gLastUnoResult.clear();
  gUnoResultSeq = -1;
  const int armStart = gSequence;

  if (readOnly)
    document->pClass->setViewReadOnly(document, 0, true);

  std::string arguments;
  if (command) {
    if (slot)
      arguments = argumentFor(slot, enabled);
    document->pClass->postUnoCommand(document, command,
                                     slot ? arguments.c_str() : nullptr,
                                     /*bNotifyWhenFinished=*/true);
    for (int waited = 0; waited < 40 && gUnoResultSeq < 0; ++waited)
      drain(100);
  }
  drain(600);

  // Snapshot before typing: typing itself provokes further state changes, and
  // the question is what the DISPATCH produced.
  const std::vector<std::pair<int, std::string>> afterDispatch = gStateChanges;

  if (readOnly)
    document->pClass->setViewReadOnly(document, 0, false);
  drain(300);
  typeText(document, marker);

  std::cout << "{\"probe\":\"arm\",\"arm\":\"" << name
            << "\",\"command\":\"" << (command ? command : "(none)")
            << "\",\"slot\":\"" << (slot ? slot : "")
            << "\",\"requested\":" << (slot ? (enabled ? "true" : "false") : "null")
            << ",\"readOnly\":" << (readOnly ? "true" : "false")
            << ",\"marker\":\"" << marker
            << "\",\"answered\":" << (gUnoResultSeq > armStart ? "true" : "false")
            << ",\"result\":\"" << jsonEscape(gLastUnoResult.c_str())
            << "\",\"stateChanges\":[";
  bool first = true;
  for (const auto &entry : afterDispatch) {
    if (entry.first <= armStart)
      continue;
    if (!first)
      std::cout << ",";
    first = false;
    std::cout << "\"" << jsonEscape(entry.second.c_str()) << "\"";
  }
  std::cout << "]}\n";
  std::cout.flush();
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL PROFILE_URL DOC_URL OUT_DIR_URL\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) { std::cerr << "lok_init_2 null\n"; return 2; }
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) { std::cerr << "documentLoad null\n"; return 3; }

  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  drain(400);

  // One paragraph per arm, so a pending attribute from one arm cannot leak into
  // the next.  Markers are three letters and unique, so the analyzer can find
  // each one's own text run in content.xml.
  struct Arm {
    const char *name; const char *command; const char *slot;
    bool enabled; int paragraph; const char *marker; bool readOnly;
  };
  const Arm arms[] = {
    {"control-no-command",    nullptr,          nullptr,      false, 0,  "AAA", false},
    {"bold-true",             ".uno:Bold",      "Bold",       true,  1,  "BBB", false},
    {"bold-false",            ".uno:Bold",      "Bold",       false, 2,  "CCC", false},
    {"italic-true",           ".uno:Italic",    "Italic",     true,  3,  "DDD", false},
    {"italic-false",          ".uno:Italic",    "Italic",     false, 4,  "EEE", false},
    {"underline-true",        ".uno:Underline", "Underline",  true,  5,  "FFF", false},
    {"underline-false",       ".uno:Underline", "Underline",  false, 6,  "GGG", false},
    {"strikeout-true",        ".uno:Strikeout", "Strikeout",  true,  7,  "HHH", false},
    {"strikeout-false",       ".uno:Strikeout", "Strikeout",  false, 8,  "III", false},
    {"bold-true-readonly",    ".uno:Bold",      "Bold",       true,  9,  "JJJ", true},
  };
  for (const Arm &a : arms)
    arm(document, a.name, a.command, a.slot, a.enabled, a.paragraph, a.marker,
        a.readOnly);

  const std::string target = std::string(argv[4]) + "/predicate-arms.odt";
  const bool saved = document->pClass->saveAs(document, target.c_str(), "odt",
                                              nullptr);
  std::cout << "{\"probe\":\"save\",\"savedTo\":\"" << jsonEscape(target.c_str())
            << "\",\"saved\":" << (saved ? "true" : "false") << "}\n";
  std::cout.flush();

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
