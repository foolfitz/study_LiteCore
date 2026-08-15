// SPEC E2-B 9.7: the three checks that decide B' against A.
//
// B' verifies a cross-paragraph format dispatch by reading back the SURVIVING
// original selection and requiring its text to equal what was captured before
// the dispatch.  Three things have to be true for that to be buildable, and
// any one of them failing sends the decision back to A (refuse before
// dispatch):
//
//   1  substrate  -- getTextSelection("text/html") returns on a cross-paragraph
//                    selection, and the markup can be enumerated per block
//   2  survival   -- the selection survives the dispatch with identical text
//   3  undo       -- the dispatch is a single undo step
//
// The prediction for all three was committed before this file existed:
// findings/evidence/sdk-e2/discovery/e2b-crossparagraph/PREDICTION.md
//
// Native, and native for a specific reason: B' reads the selection AFTER the
// uno command and BEFORE anything collapses it.  The shipped engine's barrier
// collapses to its restore point and re-selects with .uno:SelectText, so from
// JavaScript that intermediate state is not observable on this build -- making
// it observable is the very relink these checks exist to de-risk.
//
// Every check has a single-paragraph control arm running the identical code
// path.  Without them, "two blocks" cannot be told from "this build says two
// blocks for everything", and "survived" cannot be told from "nothing here
// ever clears a selection".
//
// Usage: e2b-native-crossparagraph INSTALL PROFILE_URL DOCUMENT_URL SAVE_DIR

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

const char *const kFirstAnchor = "E1-MULTI-START";
const char *const kSecondAnchor = "第二段中文";
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
  long values[4] = {0, 0, 0, 0};
  if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &values[0], &values[1],
                  &values[2], &values[3]) != 4)
    return false;
  out.x = values[0];
  out.y = values[1];
  out.width = values[2];
  out.height = values[3];
  out.valid = true;
  return true;
}

Rectangle gSelectionRectangle;
bool gSelectionRectangleSeen = false;

void onCallback(int type, const char *payload, void *) {
  if (type != LOK_CALLBACK_TEXT_SELECTION)
    return;
  Rectangle parsed;
  if (parseRectangle(payload, parsed)) {
    gSelectionRectangle = parsed;
    gSelectionRectangleSeen = true;
  }
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

std::string takeSelection(LibreOfficeKitDocument *document,
                          const char *mimeType) {
  char *used = nullptr;
  char *text = document->pClass->getTextSelection(document, mimeType, &used);
  std::string out = text ? std::string(text) : std::string();
  std::free(text);
  std::free(used);
  return out;
}

// How many block-level elements the html readback contains.
//
// Deliberately the same question probe_engine.cpp's parser asks (`:601`:
// blockCount > 1 || itemCount > 1), not a reimplementation of the parser: what
// check 1 needs to know is whether the markup can be enumerated per block at
// all, and a count that a five-line scanner can get right is evidence that it
// can.
struct BlockCount {
  int blocks = 0;
  int items = 0;
};

BlockCount countBlocks(const std::string &html) {
  static const char *const kBlockTags[] = {"<p", "<h1", "<h2", "<h3",
                                           "<h4", "<h5", "<h6", "<div"};
  BlockCount out;
  for (const char *tag : kBlockTags) {
    const std::size_t length = std::strlen(tag);
    for (std::size_t at = html.find(tag); at != std::string::npos;
         at = html.find(tag, at + 1)) {
      // Only a real tag: the next character must end the tag name.
      const char next = at + length < html.size() ? html[at + length] : '\0';
      if (next == '>' || next == ' ' || next == '\t' || next == '\n')
        ++out.blocks;
    }
  }
  for (std::size_t at = html.find("<li"); at != std::string::npos;
       at = html.find("<li", at + 1)) {
    const char next = at + 3 < html.size() ? html[at + 3] : '\0';
    if (next == '>' || next == ' ')
      ++out.items;
  }
  return out;
}

LibreOfficeKitDocument *openDocument(LibreOfficeKit *kit, const char *url) {
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, url);
  if (!document)
    return nullptr;
  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              canvas, canvas, 0, 0, 3840, 3840);
  drain(500);
  return document;
}

// Located on a throwaway document: the search itself selects, and a selection
// left by ExecuteSearch is shell state this probe is trying to measure.
bool locateAnchor(LibreOfficeKit *kit, const char *url, const char *anchor,
                  Rectangle &out) {
  LibreOfficeKitDocument *document = openDocument(kit, url);
  if (!document)
    return false;
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") + anchor + "\"},"
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

// The engine's shipped selection sequence: RESET + START + END.  The START is
// the task #49 workaround (probe_engine.cpp,
// OXSDK_EDITOR_SELECTION_TEXT_HANDLES) and it is included because this probe
// must exercise what the product does, not a cleaner variant of it.
void selectRange(LibreOfficeKitDocument *document, long x1, long y1, long x2,
                 long y2) {
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET, x1,
                                     y1);
  drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_START, x1,
                                     y1);
  drain(200);
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_END, x2,
                                     y2);
  drain(600);
}

// Round 1's control was confounded, and the confound was mine: its range was a
// PARTIAL span inside paragraph 1 (the anchor rectangle covers
// "E1-MULTI-START", not "E1-MULTI-START alpha"), so it differed from the test
// arm in two ways at once -- one paragraph versus two, AND partial versus
// whole.  `wholeParagraph` adds the third arm that separates them.
// Round 3 adds two arms.
//
// `partialHead` starts the range INSIDE paragraph 1 rather than at its head.
// Every crossing selection measured before it -- these arms and the browser
// gate's G3 -- started at a paragraph head, so only the trailing edge was ever
// partial, and dragging from the middle of a line is the ordinary gesture.
//
// `ordered` dispatches .uno:DefaultNumbering instead of .uno:DefaultBullet, for
// SAMPLING ONLY: the repaired verification needs a closed set of decoration
// prefixes measured on this build, and "    \u2022 " is the only sample so far.
// No prediction was committed for its value, so it is recorded, not judged.
struct Arm {
  const char *name;
  bool crossParagraph;
  bool wholeParagraph;
  bool partialHead;
  bool ordered;
};

const Arm kArms[] = {
    {"cross-paragraph", true, false, false, false},
    {"single-paragraph-control", false, false, false, false},
    {"single-paragraph-whole", false, true, false, false},
    {"cross-paragraph-partial-head", true, false, true, false},
    {"cross-paragraph-ordered-sample", true, false, false, true},
};

bool saveAs(LibreOfficeKitDocument *document, const std::string &path) {
  const std::string url = "file://" + path;
  return document->pClass->saveAs(document, url.c_str(), "odt", nullptr) != 0;
}

void runArm(LibreOfficeKit *kit, const char *url, const Arm &arm, int round,
            const Rectangle &first, const Rectangle &second,
            const std::string &saveDir) {
  LibreOfficeKitDocument *document = openDocument(kit, url);
  std::cout << "{\"arm\":\"" << arm.name << "\",\"round\":" << round;
  if (!document) {
    std::cout << ",\"fatal\":\"documentLoad returned null\"}\n";
    return;
  }

  const std::string stem =
      saveDir + "/" + arm.name + "-round" + std::to_string(round);

  // A save with no action at all: the comparison baseline has to come through
  // the same engine, because the export normalises what the fixture leaves
  // implicit.  This is the e2b-gate lesson, repeated here rather than
  // rediscovered.
  const bool savedBefore = saveAs(document, stem + "-before.odt");

  const long y1 = first.y + first.height / 2;
  const long y2 = arm.crossParagraph ? second.y + second.height / 2 : y1;
  // Two thirds into the first anchor's width: unambiguously inside paragraph 1
  // and past its first characters, without needing to know where a word ends.
  const long x1 = arm.partialHead ? first.x + (first.width * 2) / 3 : first.x;
  // 9000 twips is what the browser gate uses: far enough right that the
  // endpoint clamps to the end of the line, so the range covers the whole
  // paragraph without needing to know where it ends.
  const long x2 = arm.crossParagraph ? second.x + second.width
                  : arm.wholeParagraph ? 9000
                                       : first.x + first.width;
  selectRange(document, x1, y1, x2, y2);

  const std::string plainBefore = takeSelection(document,
                                                "text/plain;charset=utf-8");
  const int typeBefore = document->pClass->getSelectionType(document);

  // CHECK 1, and it is timed: the failure this guards against is the call not
  // returning at all (findings 037, 038), which shows up as a wall-clock
  // outlier, not as an error.
  const auto htmlStart = std::chrono::steady_clock::now();
  const std::string html = takeSelection(document, "text/html");
  const long htmlMs = std::chrono::duration_cast<std::chrono::milliseconds>(
      std::chrono::steady_clock::now() - htmlStart).count();
  const BlockCount blocks = countBlocks(html);

  std::cout << ",\"range\":{\"x1\":" << x1 << ",\"y1\":" << y1
            << ",\"x2\":" << x2 << ",\"y2\":" << y2 << '}'
            << ",\"savedBefore\":" << (savedBefore ? "true" : "false")
            << ",\"selectionBefore\":{\"type\":" << typeBefore
            << ",\"bytes\":" << plainBefore.size() << ",\"text\":\""
            << jsonEscape(plainBefore.c_str()) << "\"}"
            << ",\"check1\":{\"htmlBytes\":" << html.size()
            << ",\"htmlMs\":" << htmlMs << ",\"blocks\":" << blocks.blocks
            << ",\"items\":" << blocks.items
            // Round 4: the counts were never enough.  The adjudicated identity
            // gate runs on text extracted FROM this markup, so the markup
            // itself is the evidence and a count of it is not.
            << ",\"html\":\"" << jsonEscape(html.c_str()) << "\"}";

  // CHECK 2.  Nothing between the dispatch and the readback collapses or
  // re-selects anything: that is the whole point.
  document->pClass->postUnoCommand(
      document, arm.ordered ? ".uno:DefaultNumbering" : ".uno:DefaultBullet",
      kListOnArguments, true);
  drain(800);
  const std::string plainAfter = takeSelection(document,
                                               "text/plain;charset=utf-8");
  const int typeAfter = document->pClass->getSelectionType(document);
  const std::string htmlAfter = takeSelection(document, "text/html");
  const BlockCount blocksAfter = countBlocks(htmlAfter);
  const bool survived = !plainAfter.empty() && plainAfter == plainBefore;

  std::cout << ",\"check2\":{\"type\":" << typeAfter
            << ",\"bytes\":" << plainAfter.size() << ",\"text\":\""
            << jsonEscape(plainAfter.c_str()) << "\",\"textEqual\":"
            << (plainAfter == plainBefore ? "true" : "false")
            << ",\"survived\":" << (survived ? "true" : "false")
            << ",\"blocks\":" << blocksAfter.blocks
            << ",\"items\":" << blocksAfter.items
            << ",\"html\":\"" << jsonEscape(htmlAfter.c_str()) << "\"}";

  const bool savedAfter = saveAs(document, stem + "-after.odt");

  // CHECK 3.  Exactly one undo, then the document is judged by a separate
  // comparator -- not by anything this probe returns.
  document->pClass->postUnoCommand(document, ".uno:Undo", nullptr, true);
  drain(800);
  const bool savedUndo = saveAs(document, stem + "-undo.odt");

  // And a second undo, saved separately.  If one undo is not enough, the next
  // question is immediately "how many", and asking it now costs one call.
  document->pClass->postUnoCommand(document, ".uno:Undo", nullptr, true);
  drain(800);
  const bool savedUndoTwice = saveAs(document, stem + "-undo2.odt");

  std::cout << ",\"check3\":{\"savedAfter\":" << (savedAfter ? "true" : "false")
            << ",\"savedUndo\":" << (savedUndo ? "true" : "false")
            << ",\"savedUndoTwice\":" << (savedUndoTwice ? "true" : "false")
            << "}}\n";
  std::cout.flush();
  document->pClass->destroy(document);
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL PROFILE_URL DOCUMENT_URL SAVE_DIR\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }

  Rectangle first, second;
  if (!locateAnchor(kit, argv[3], kFirstAnchor, first) ||
      !locateAnchor(kit, argv[3], kSecondAnchor, second)) {
    std::cerr << "could not locate both anchors\n";
    std::cout << "{\"setupSucceeded\":false}\n";
    kit->pClass->destroy(kit);
    return 3;
  }
  std::cout << "{\"anchors\":{\"first\":{\"x\":" << first.x << ",\"y\":"
            << first.y << ",\"width\":" << first.width << ",\"height\":"
            << first.height << "},\"second\":{\"x\":" << second.x << ",\"y\":"
            << second.y << ",\"width\":" << second.width << ",\"height\":"
            << second.height << "}}}\n";
  std::cout.flush();

  const std::string saveDir = argv[4];
  for (int round = 1; round <= 3; ++round)
    for (const Arm &arm : kArms)
      runArm(kit, argv[3], arm, round, first, second, saveDir);

  kit->pClass->destroy(kit);
  return 0;
}
