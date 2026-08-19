// Finding 059, the two things still owed before the engine's predicate changes:
//
//   1. A GENUINE NEGATIVE ARM.  The replacement predicate is the barrier's own
//      postcondition -- observed state against requested state.  Ten native
//      arms showed it AGREEING nine times.  Nothing has shown it disagreeing:
//      the intended refusal arm (`setViewReadOnly`) did not refuse, because
//      core applied the command anyway.  A predicate that has only ever been
//      seen to agree is not yet a predicate.
//
//   2. STATE CACHE PRIMING (finding 021's shape).  `formatBarrierPostcondition
//      Met()` returns false BOTH when the state is unknown and when it is known
//      and wrong (probe_engine.cpp:1189).  Those are not the same thing, and if
//      the cache is not primed at the moment the predicate runs, every verdict
//      it gives is "unknown" wearing the word "failed".  So this probe records,
//      for every arm, what the caret move ALONE broadcast -- before any command
//      is dispatched.
//
// A separate program from f059_native_format_predicate.cpp on purpose: that
// probe's round is the evidence finding 059's predicate section rests on, and
// rewriting it in place would overwrite the bytes.
//
// The negative candidates, and why more than one
// ----------------------------------------------
// Finding 037's lesson is that a guard you expect to decline may decline for a
// different reason, or not at all -- and 059's own first refusal arm did not
// refuse.  So this asks several ways and reports which ones actually leave the
// document in the wrong state, rather than assuming any of them does:
//
//   wrong-argument-type   {"Bold":{"type":"string","value":"true"}} -- core
//                         knows the slot and cannot convert the argument
//   wrong-argument-name   {"Bald":{...}} -- core knows the slot and gets no
//                         usable argument.  Finding 045 says a bare .uno:Bold
//                         TOGGLES, so this one may well apply in the wrong
//                         direction, which is its own answer
//   protected-section     the caret is walked into a section declared
//                         text:protected="true".  Whether the caret can even
//                         ENTER is a measurement: Writer's default keeps the
//                         cursor out of protected areas, and an arm that could
//                         not aim must say so rather than report a refusal it
//                         did not observe
//   readonly-control      setViewReadOnly again, kept as a control: it did not
//                         refuse on 2026-08-18 and if it starts refusing, that
//                         changes what the earlier round meant
//
// A positive control runs first and last.  If the positive controls do not come
// back styled, the round measured nothing and no negative may be read from it.
//
// Usage: f059-native-negative-arm INSTALL PROFILE_URL DOC_URL OUT_DIR_URL

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

constexpr int KEY_DOWN = 1024;
constexpr int KEY_HOME = 1028;
constexpr int KEY_END = 1029;
constexpr int KEY_MOD1 = 0x2000;

void pressKey(LibreOfficeKitDocument *document, int keyCode) {
  document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT, 0, keyCode);
  drain(150);
}

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

void emitList(const std::vector<std::pair<int, std::string>> &entries,
              int after) {
  bool first = true;
  for (const auto &entry : entries) {
    if (entry.first <= after)
      continue;
    if (!first)
      std::cout << ",";
    first = false;
    std::cout << "\"" << jsonEscape(entry.second.c_str()) << "\"";
  }
}

struct Arm {
  const char *name;
  const char *command;     // nullptr = dispatch nothing
  const char *arguments;   // nullptr = no argument at all
  const char *requested;   // "true" / "false" / "null" -- what the caller asked
  int paragraph;
  const char *marker;
  bool readOnly;
};

void runArm(LibreOfficeKitDocument *document, const Arm &a) {
  // PRIMING, measured before anything is dispatched: the caret move is the only
  // thing that has happened, so whatever arrives here is what the state cache
  // would hold at the moment the predicate runs.
  gStateChanges.clear();
  const int beforeCaret = gSequence;
  caretToParagraph(document, a.paragraph);
  drain(400);
  const std::vector<std::pair<int, std::string>> fromCaretMove = gStateChanges;

  gStateChanges.clear();
  gLastUnoResult.clear();
  gUnoResultSeq = -1;
  const int armStart = gSequence;

  if (a.readOnly)
    document->pClass->setViewReadOnly(document, 0, true);

  if (a.command) {
    document->pClass->postUnoCommand(document, a.command, a.arguments,
                                     /*bNotifyWhenFinished=*/true);
    for (int waited = 0; waited < 40 && gUnoResultSeq < 0; ++waited)
      drain(100);
  }
  drain(600);

  const std::vector<std::pair<int, std::string>> afterDispatch = gStateChanges;

  if (a.readOnly)
    document->pClass->setViewReadOnly(document, 0, false);
  drain(300);
  typeText(document, a.marker);

  std::cout << "{\"probe\":\"arm\",\"arm\":\"" << a.name
            << "\",\"command\":\"" << (a.command ? a.command : "(none)")
            << "\",\"arguments\":\""
            << jsonEscape(a.arguments ? a.arguments : "")
            << "\",\"requested\":" << a.requested
            << ",\"paragraph\":" << a.paragraph
            << ",\"readOnly\":" << (a.readOnly ? "true" : "false")
            << ",\"marker\":\"" << a.marker
            << "\",\"answered\":" << (gUnoResultSeq > armStart ? "true" : "false")
            << ",\"result\":\"" << jsonEscape(gLastUnoResult.c_str())
            << "\",\"fromCaretMove\":[";
  emitList(fromCaretMove, beforeCaret);
  std::cout << "],\"stateChanges\":[";
  emitList(afterDispatch, armStart);
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

  // Paragraph indices follow the fixture: 0-7 are F059-NEG-PLAIN-00..07, 8 is
  // the paragraph inside the protected section, 9 is F059-NEG-AFTER.
  const Arm arms[] = {
    {"control-no-command",   nullptr, nullptr, "null", 0, "AAA", false},
    {"positive-bold-true",   ".uno:Bold",
     "{\"Bold\":{\"type\":\"boolean\",\"value\":true}}", "true", 1, "BBB", false},
    {"wrong-argument-type",  ".uno:Bold",
     "{\"Bold\":{\"type\":\"string\",\"value\":\"true\"}}", "true", 2, "CCC", false},
    {"wrong-argument-name",  ".uno:Bold",
     "{\"Bald\":{\"type\":\"boolean\",\"value\":true}}", "true", 3, "DDD", false},
    {"bare-no-argument",     ".uno:Bold", nullptr, "true", 4, "EEE", false},
    {"readonly-control",     ".uno:Bold",
     "{\"Bold\":{\"type\":\"boolean\",\"value\":true}}", "true", 5, "FFF", true},
    {"protected-section",    ".uno:Bold",
     "{\"Bold\":{\"type\":\"boolean\",\"value\":true}}", "true", 8, "GGG", false},
    {"after-the-section",    ".uno:Bold",
     "{\"Bold\":{\"type\":\"boolean\",\"value\":true}}", "true", 9, "HHH", false},
    {"positive-bold-true-2", ".uno:Bold",
     "{\"Bold\":{\"type\":\"boolean\",\"value\":true}}", "true", 6, "III", false},
  };
  for (const Arm &a : arms)
    runArm(document, a);

  const std::string target = std::string(argv[4]) + "/negative-arms.odt";
  const bool saved = document->pClass->saveAs(document, target.c_str(), "odt",
                                              nullptr);
  std::cout << "{\"probe\":\"save\",\"savedTo\":\"" << jsonEscape(target.c_str())
            << "\",\"saved\":" << (saved ? "true" : "false") << "}\n";
  std::cout.flush();

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
