// Finding 129 -- what does NATIVE LibreOffice Writer do with an arrow key (or
// Home/End) pressed while text is selected?  And with Shift held, from a caret?
//
// The engine refuses every move action on a range (v19's manifest grants the
// six moves `collapsed` only), and the page shows the engine's developer
// message.  Before choosing a remedy -- the page collapsing the selection
// itself, or the manifest granting the moves on ranges so that Writer handles
// the key -- the reference has to be known: where Writer puts the caret.  The
// answer depends on which end of the selection the caret (the "point") is at,
// so both are made: FORWARD (Shift+Right from the selection's start: the point
// at its end) and BACKWARD (Shift+Left from its end: the point at its start).
//
// The reading is a marker, not a rectangle: after the key, '#' is typed and the
// document's text is read back.  Where '#' lands is where the caret was.  If
// the key did NOT collapse the selection, the typed '#' replaces the selected
// text -- which the read-back shows too, so the instrument reports that case
// instead of hiding it.
//
// Arms "shift-*": from a collapsed caret at the selection's start, Shift+Right
// (or Shift+End etc.); then '#' replaces what the key selected.  That is the
// reference for the request "Shift + 方向鍵 = 選取文字".
//
// Usage: f129-native-arrow-on-selection INSTALL PROFILE_URL FIXTURE_URL
// Output: one JSON line per arm on stdout.

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

namespace {

constexpr int kShift = 0x1000;  // KEY_SHIFT
constexpr int kDown = 1024, kUp = 1025, kLeft = 1026, kRight = 1027,
              kHome = 1028, kEnd = 1029;  // css::awt::Key

std::mutex gMutex;
std::string gSelection;
std::string gCursor;

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  if (type == LOK_CALLBACK_TEXT_SELECTION)
    gSelection = payload ? payload : "";
  else if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)
    gCursor = payload ? payload : "";
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

std::string jsonEscape(const std::string &value) {
  std::string out;
  for (const char c : value) {
    switch (c) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': out += "\\r"; break;
    case '\t': out += "\\t"; break;
    default:
      if (static_cast<unsigned char>(c) < 0x20) {
        char b[8];
        std::snprintf(b, sizeof b, "\\u%04x", static_cast<unsigned char>(c));
        out += b;
      } else {
        out += c;
      }
    }
  }
  return out;
}

void key(LibreOfficeKitDocument *d, int code) {
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYINPUT, 0, code);
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYUP, 0, code);
  drain(150);
}

void typeChar(LibreOfficeKitDocument *d, char c) {
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYINPUT, c, 0);
  d->pClass->postKeyEvent(d, LOK_KEYEVENT_KEYUP, c, 0);
  drain(300);
}

std::string selectedText(LibreOfficeKitDocument *d) {
  char *used = nullptr;
  char *text = d->pClass->getTextSelection(d, "text/plain;charset=utf-8", &used);
  std::string out = text ? text : "";
  std::free(text);
  std::free(used);
  return out;
}

std::string uno(LibreOfficeKitDocument *d, const char *command) {
  d->pClass->postUnoCommand(d, command, nullptr, false);
  drain(400);
  return "";
}

struct Arm {
  std::string id;
  std::string make;  // "forward", "backward", "caret"
  int keyCode;       // may carry kShift
};

}  // namespace

int main(int argc, char **argv) {
  if (argc < 4) {
    std::cerr << "usage: f129-native-arrow-on-selection INSTALL PROFILE_URL FIXTURE_URL\n";
    return 2;
  }
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 failed\n";
    return 1;
  }
  // P2's text is "P2 ALPHA BETA GAMMA DELTA": "BETA GAMMA" is offsets 9..19.
  const int selStart = 9, selLength = 10;
  const std::vector<std::pair<std::string, int>> keys = {
      {"Left", kLeft}, {"Right", kRight}, {"Up", kUp},
      {"Down", kDown}, {"Home", kHome},   {"End", kEnd}};
  std::vector<Arm> arms;
  for (const char *make : {"forward", "backward"})
    for (const auto &k : keys)
      arms.push_back({std::string(make) + "-" + k.first, make, k.second});
  for (const auto &k : keys)
    arms.push_back({"caret-shift-" + k.first, "caret", k.second | kShift});
  arms.push_back({"control-none", "forward", 0});  // the selection, then '#'

  for (const Arm &arm : arms) {
    LibreOfficeKitDocument *d = kit->pClass->documentLoad(kit, argv[3]);
    if (!d) {
      std::cout << "{\"arm\":\"" << arm.id << "\",\"fatal\":\"documentLoad\"}" << std::endl;
      continue;
    }
    d->pClass->initializeForRendering(d, "{}");
    d->pClass->registerCallback(d, onCallback, nullptr);
    std::string pixels(256 * 256 * 4, '\0');
    d->pClass->paintTile(d, reinterpret_cast<unsigned char *>(pixels.data()), 256, 256, 0, 0, 3840, 3840);
    drain(500);
    // To P2's start with keys only: a fresh load has the caret at the
    // document's start.  (The first round posted .uno:GoToStartOfDoc /
    // GoToStartOfPara around the Down key without waiting for their results
    // and landed in P1 -- round-20261012T020312Z; kept as a P1 round.)
    key(d, kDown);
    key(d, kHome);
    drain(300);
    std::string made;
    if (arm.make == "forward") {
      for (int i = 0; i < selStart; ++i) key(d, kRight);
      for (int i = 0; i < selLength; ++i) key(d, kRight | kShift);
    } else if (arm.make == "backward") {
      for (int i = 0; i < selStart + selLength; ++i) key(d, kRight);
      for (int i = 0; i < selLength; ++i) key(d, kLeft | kShift);
    } else {
      for (int i = 0; i < selStart; ++i) key(d, kRight);
    }
    made = selectedText(d);
    std::string selectionBefore, cursorBefore, selectionAfter, cursorAfter;
    {
      std::lock_guard<std::mutex> lock(gMutex);
      selectionBefore = gSelection;
      cursorBefore = gCursor;
    }
    if (arm.keyCode)
      key(d, arm.keyCode);
    drain(300);
    const std::string afterKey = selectedText(d);
    {
      std::lock_guard<std::mutex> lock(gMutex);
      selectionAfter = gSelection;
      cursorAfter = gCursor;
    }
    typeChar(d, '#');
    uno(d, ".uno:SelectAll");
    const std::string text = selectedText(d);
    std::cout << "{\"arm\":\"" << arm.id << "\",\"made\":\"" << jsonEscape(made)
              << "\",\"selectedAfterKey\":\"" << jsonEscape(afterKey)
              << "\",\"cursorBefore\":\"" << jsonEscape(cursorBefore)
              << "\",\"cursorAfter\":\"" << jsonEscape(cursorAfter)
              << "\",\"selectionCallbackAfter\":\"" << jsonEscape(selectionAfter.substr(0, 120))
              << "\",\"text\":\"" << jsonEscape(text) << "\"}" << std::endl;
    d->pClass->destroy(d);
    drain(200);
  }
  return 0;
}
