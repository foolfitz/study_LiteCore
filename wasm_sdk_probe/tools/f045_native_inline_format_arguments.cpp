// Finding 045 native probe: does sending the parameter make the four inline
// format commands setters instead of toggles?
//
// The engine dispatches `.uno:Bold` with EMPTY arguments today
// (probe_engine.cpp:3036), and core declares the slot `Toggle = TRUE`
// (svx/sdi/svx.sdi:832,838).  The proposed fix is finding 030's shape -- send
// the value -- and it has to be measured before it goes into a relink, because
// a relink here costs an E2-B re-run plus a full E2-C round.
//
// Predictions are written down first, in
// findings/evidence/045/native/PREDICTION.md, and this file was written after
// them.  The derivation being tested: TransformParameters hands a single
// argument named for the slot to PutValue(value, 0), MemberId 0 is the boolean
// accessor for all four items, and unoctitm.cxx takes the toggle branch only
// when the argument set is EMPTY.
//
// Native, because a negative result on the WASM build alone cannot separate
// "core does not accept this form" from "our build does not send it properly".
//
// Every arm loads a fresh document, and the arms that use two positions use two
// anchors in DIFFERENT paragraphs: text inserted beside a bold run inherits it,
// which is exactly why finding 045 could not make the toggle claim from its
// first round.
//
// Usage: f045-native INSTALL PROFILE_URL DOCUMENT_URL OUTPUT_DIR

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

struct Rectangle {
  int x = 0, y = 0, width = 0, height = 0;
  bool valid = false;
};

Rectangle gSelectionRectangle;
bool gSelectionRectangleSeen = false;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_TEXT_SELECTION && payload && *payload) {
    Rectangle rectangle;
    if (std::sscanf(payload, "%d, %d, %d, %d", &rectangle.x, &rectangle.y,
                    &rectangle.width, &rectangle.height) == 4) {
      rectangle.valid = true;
      gSelectionRectangle = rectangle;
      gSelectionRectangleSeen = true;
    }
  }
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

LibreOfficeKitDocument *openDocument(LibreOfficeKit *kit, const char *url) {
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, url);
  if (!document)
    return nullptr;
  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  // A coordinate means nothing until the layout exists.
  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              canvas, canvas, 0, 0, 3840, 3840);
  drain(500);
  return document;
}

// Located on a document that is then thrown away: ExecuteSearch SELECTS, and a
// selection made by the setup is exactly the state these arms are about.
bool locateAnchor(LibreOfficeKit *kit, const char *url, const char *anchor,
                  Rectangle &out) {
  LibreOfficeKitDocument *document = openDocument(kit, url);
  if (!document)
    return false;
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"")
      + anchor + "\"},"
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

void post(LibreOfficeKitDocument *document, const char *command,
          const std::string &arguments) {
  document->pClass->postUnoCommand(document, command,
                                   arguments.empty() ? nullptr
                                                     : arguments.c_str(),
                                   true);
  drain(400);
}

void caretAt(LibreOfficeKitDocument *document, const Rectangle &anchor) {
  const int x = anchor.x + anchor.width / 2;
  const int y = anchor.y + anchor.height / 2;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET, x, y);
  drain(200);
}

void rangeOver(LibreOfficeKitDocument *document, const Rectangle &anchor) {
  const int y = anchor.y + anchor.height / 2;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     anchor.x, y);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_START,
                                     anchor.x, y);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END,
                                     anchor.x + anchor.width, y);
  drain(300);
}

void insertMarker(LibreOfficeKitDocument *document, const char *marker) {
  const std::string arguments =
      std::string("{\"Text\":{\"type\":\"string\",\"value\":\"") + marker + "\"}}";
  post(document, ".uno:InsertText", arguments);
}

std::string booleanArgument(const char *slot, bool value) {
  return std::string("{\"") + slot + "\":{\"type\":\"boolean\",\"value\":"
         + (value ? "true" : "false") + "}}";
}

struct Command {
  const char *name;        // arm name fragment
  const char *uno;         // .uno:Bold
  const char *slot;        // Bold
  const char *anchorOne;   // first position
  const char *anchorTwo;   // second position, a DIFFERENT paragraph
  const char *markerOne;
  const char *markerTwo;
};

const Command kCommands[] = {
  {"bold", ".uno:Bold", "Bold", "E2-D1-BOLD-ON", "E2-D1-MOVE",
   "F45BOLDA", "F45BOLDB"},
  {"italic", ".uno:Italic", "Italic", "E2-D1-ITALIC-ON", "E2-D1-INSERT",
   "F45ITALA", "F45ITALB"},
  {"underline", ".uno:Underline", "Underline", "E2-D1-UNDERLINE-ON",
   "E2-D1-LIST-UNORDERED", "F45UNDRA", "F45UNDRB"},
  {"strikethrough", ".uno:Strikeout", "Strikeout", "E2-D1-STRIKE-ON",
   "E2-D1-LIST-ORDERED", "F45STRKA", "F45STRKB"},
};

// How each arm drives one command.  The oracle is NOT here: every arm saves a
// document and the judging happens offline, in tools/analyze_f045_native.py,
// against the predictions registered before this ran.
enum class Arm {
  ParamOff,        // P1: parameter false at a caret in plain text
  ParamOn,         // P2: parameter true
  Bare,            // P3: no arguments at all
  BareTwice,       // P4: bare at two non-adjacent positions
  ParamOffThenOn,  // P5: false at one position, true at another
  ParamOnRange,    // P6: parameter true over a SELECTION
  ParamOffRange,   // P7: parameter false over a selection already formatted
};

struct ArmSpec {
  const char *name;
  Arm kind;
};

const ArmSpec kArms[] = {
  {"param-off", Arm::ParamOff},
  {"param-on", Arm::ParamOn},
  {"bare", Arm::Bare},
  {"bare-twice", Arm::BareTwice},
  {"param-off-then-on", Arm::ParamOffThenOn},
  {"param-on-range", Arm::ParamOnRange},
  {"param-off-range", Arm::ParamOffRange},
};

bool runArm(LibreOfficeKit *kit, const char *url, const std::string &outputDir,
            const Command &command, const ArmSpec &arm,
            const Rectangle &anchorOne, const Rectangle &anchorTwo) {
  LibreOfficeKitDocument *document = openDocument(kit, url);
  if (!document)
    return false;
  const std::string label = std::string(command.name) + "-" + arm.name;

  switch (arm.kind) {
  case Arm::ParamOff:
    caretAt(document, anchorOne);
    post(document, command.uno, booleanArgument(command.slot, false));
    insertMarker(document, command.markerOne);
    break;
  case Arm::ParamOn:
    caretAt(document, anchorOne);
    post(document, command.uno, booleanArgument(command.slot, true));
    insertMarker(document, command.markerOne);
    break;
  case Arm::Bare:
    caretAt(document, anchorOne);
    post(document, command.uno, "");
    insertMarker(document, command.markerOne);
    break;
  case Arm::BareTwice:
    caretAt(document, anchorOne);
    post(document, command.uno, "");
    insertMarker(document, command.markerOne);
    caretAt(document, anchorTwo);
    post(document, command.uno, "");
    insertMarker(document, command.markerTwo);
    break;
  case Arm::ParamOffThenOn:
    caretAt(document, anchorOne);
    post(document, command.uno, booleanArgument(command.slot, false));
    insertMarker(document, command.markerOne);
    caretAt(document, anchorTwo);
    post(document, command.uno, booleanArgument(command.slot, true));
    insertMarker(document, command.markerTwo);
    break;
  case Arm::ParamOnRange:
    rangeOver(document, anchorOne);
    post(document, command.uno, booleanArgument(command.slot, true));
    break;
  case Arm::ParamOffRange:
    // Put the property on first, with the same parameter form, then ask for it
    // to come off.  Turning off something that was never on proves nothing.
    rangeOver(document, anchorOne);
    post(document, command.uno, booleanArgument(command.slot, true));
    rangeOver(document, anchorOne);
    post(document, command.uno, booleanArgument(command.slot, false));
    break;
  }

  const std::string path = outputDir + "/after-" + label + ".odt";
  const std::string url_out = "file://" + path;
  const bool saved = document->pClass->saveAs(document, url_out.c_str(),
                                              "odt", nullptr);
  document->pClass->destroy(document);
  std::cout << "{\"arm\":\"" << label << "\",\"saved\":"
            << (saved ? "true" : "false") << "}\n";
  std::cout.flush();
  return saved;
}

}  // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL PROFILE_URL DOCUMENT_URL OUTPUT_DIR\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }

  int failures = 0;
  for (const Command &command : kCommands) {
    Rectangle one, two;
    if (!locateAnchor(kit, argv[3], command.anchorOne, one)
        || !locateAnchor(kit, argv[3], command.anchorTwo, two)) {
      std::cout << "{\"command\":\"" << command.name
                << "\",\"anchorsLocated\":false}\n";
      failures += 1;
      continue;
    }
    std::cout << "{\"command\":\"" << command.name << "\",\"anchorsLocated\":true,"
              << "\"one\":{\"x\":" << one.x << ",\"y\":" << one.y << "},"
              << "\"two\":{\"x\":" << two.x << ",\"y\":" << two.y << "}}\n";
    std::cout.flush();
    for (const ArmSpec &arm : kArms)
      if (!runArm(kit, argv[3], argv[4], command, arm, one, two))
        failures += 1;
  }

  kit->pClass->destroy(kit);
  std::cout << "{\"summary\":{\"failures\":" << failures << "}}\n";
  return failures == 0 ? 0 : 1;
}
