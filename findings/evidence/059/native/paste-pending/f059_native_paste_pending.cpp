// Finding 059: does a PASTE carry the caret's pending inline attribute?
//
// This exists to disambiguate one specific null result, and only that.
//
// The WASM half of finding 059 has to read the document effect of a command the
// product reports as failed.  On a collapsed caret an inline format is a
// PENDING attribute -- it changes nothing until something is inserted -- and
// the product's only text-entry path is `handleInsertText`, which calls LOK
// `paste` first and falls back to postKeyEvent only when paste returns false
// (src/probe_engine.cpp).  The page discards the response, so a browser run
// cannot tell which mechanism ran.
//
// So if the WASM marker comes back UNSTYLED, there are two explanations:
//
//   a) core did not apply the command on WASM
//   b) core applied it, and the paste did not carry the pending attribute
//
// This probe settles (b) on native, where the same two mechanisms are directly
// callable.  It says nothing about WASM -- native never describes WASM in this
// tree (040, 048, and 059's own first mechanism).
//
// Arms, all with a collapsed caret at the end of their own paragraph:
//
//   paste-after-bold      dispatch bold true, then insert by PASTE
//   type-after-bold       dispatch bold true, then insert by postKeyEvent
//                         (positive control: the predicate round already showed
//                          this comes back bold, so if it does not, the probe
//                          is broken rather than the mechanism)
//   paste-no-command      no dispatch, insert by PASTE
//                         (negative control: the fixture must not style it)
//
// Usage: f059-native-paste-pending INSTALL PROFILE_URL DOC_URL OUT_DIR_URL

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
    default:
      if (static_cast<unsigned char>(*it) < 0x20)
        continue;
      out += *it;
    }
  }
  return out;
}

int gSequence = 0;
std::string gLastUnoResult;
int gUnoResultSeq = -1;

void onCallback(int type, const char *payload, void *) {
  if (!payload)
    return;
  ++gSequence;
  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
    gLastUnoResult = payload;
    gUnoResultSeq = gSequence;
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

void arm(LibreOfficeKitDocument *document, const char *name, bool dispatch,
         bool byPaste, int paragraph, const char *marker) {
  caretToParagraph(document, paragraph);
  gLastUnoResult.clear();
  gUnoResultSeq = -1;
  const int armStart = gSequence;

  if (dispatch) {
    const std::string arguments =
        "{\"Bold\":{\"type\":\"boolean\",\"value\":true}}";
    document->pClass->postUnoCommand(document, ".uno:Bold", arguments.c_str(),
                                     /*bNotifyWhenFinished=*/true);
    for (int waited = 0; waited < 40 && gUnoResultSeq < 0; ++waited)
      drain(100);
  }
  drain(500);

  bool pasted = false;
  if (byPaste) {
    // The same call handleInsertText makes, with the same mime type.
    pasted = document->pClass->paste(document, "text/plain;charset=utf-8",
                                     marker, std::strlen(marker));
  } else {
    for (const char *it = marker; *it; ++it) {
      document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT,
                                     static_cast<int>(*it), 0);
      drain(120);
    }
  }
  drain(600);

  std::cout << "{\"probe\":\"arm\",\"arm\":\"" << name
            << "\",\"dispatched\":" << (dispatch ? "true" : "false")
            << ",\"insertedBy\":\"" << (byPaste ? "paste" : "postKeyEvent")
            << "\",\"pasteReturned\":" << (byPaste ? (pasted ? "true" : "false")
                                                   : "null")
            << ",\"paragraph\":" << paragraph
            << ",\"marker\":\"" << marker
            << "\",\"answered\":" << (gUnoResultSeq > armStart ? "true" : "false")
            << ",\"result\":\"" << jsonEscape(gLastUnoResult.c_str()) << "\"}\n";
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

  arm(document, "paste-after-bold", true, true, 1, "PPP");
  arm(document, "type-after-bold", true, false, 2, "TTT");
  arm(document, "paste-no-command", false, true, 3, "QQQ");

  const std::string target = std::string(argv[4]) + "/paste-pending-arms.odt";
  const bool saved = document->pClass->saveAs(document, target.c_str(), "odt",
                                              nullptr);
  std::cout << "{\"probe\":\"save\",\"saved\":" << (saved ? "true" : "false")
            << "}\n";
  std::cout.flush();

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
