// Paragraph merge: what the shipped selection barrier would see and do at
// every boundary kind, against what the plain key does (native, 2026-10-06).
//
// The engine refuses a delete at a paragraph boundary (finding 109): its
// barrier selects one unit with Shift+Left/Right, accepts only a single-line
// text selection with no separator in it, dispatches .uno:SwBackspace /
// .uno:Delete on that selection, and proves completion by the command result
// plus a collapsed selection (probe_engine.cpp, startSelectionBarrierDelete,
// verifyAndDispatchSelectionBarrierDelete).  To let it merge paragraphs we
// need to know, per boundary kind:
//
//   1  what the one-unit selection looks like (type, code points, rectangles)
//      -- the signature the barrier would have to recognise;
//   2  whether deleting THAT selection gives the same document as the key the
//      user pressed -- the "select" arm against the "key" arm;
//   3  whether one .uno:Undo puts the document back.
//
// Native, because nothing is bound to it and it needs no relink.  The "key"
// arm is the reference: it is what Writer does for the user's own key, and the
// merge we ship must not differ from it.
//
// Usage: merge-native-boundaries INSTALL PROFILE_URL DOCUMENT_URL OUT_DIR ROUNDS [CASES_TSV [PRESSES]]
//
// CASES_TSV (optional) replaces the built-in cases, for another fixture: one
// case per line, "id<TAB>anchor<TAB>backward 0|1<TAB>line 0|1<TAB>boundary",
// blank lines and lines starting with '#' ignored.  The anchor must be the
// whole paragraph (or line) and occur once before any other copy of it.
//
// PRESSES (optional, default 1): the key arm presses its key this many times,
// saving after each press (-key.odt, then -key2.odt, -key3.odt, ...).  Added
// for the third round: where Writer's first Backspace does something other
// than merge (removes an indent, stops counting a heading), does a later press
// reach what the select arm's single delete gives?

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace {

constexpr int kShift = 0x1000;     // KEY_SHIFT, as probe_engine.cpp
constexpr int kLeft = 1026;        // css::awt::Key::LEFT
constexpr int kRight = 1027;       // css::awt::Key::RIGHT
constexpr int kBackspace = 1283;   // css::awt::Key::BACKSPACE
constexpr int kDelete = 1286;      // css::awt::Key::DELETE

struct Case {
  std::string id;
  std::string anchor;
  bool backward;      // Backspace at the start (true) or Delete at the end
  bool line;          // position by line (the line-break cases), not paragraph
  std::string boundary;
};

const std::vector<Case> kCases = {
    {"C01", "M01 plain alpha", false, false, "body|body"},
    {"C02", "M02 plain beta", true, false, "body|body"},
    {"C03", "M03 heading gamma", true, false, "body|numbered heading"},
    {"C04", "M03 heading gamma", false, false, "numbered heading|body"},
    {"C05", "M04 body after heading", true, false, "numbered heading|body"},
    {"C06", "M05 before empty", false, false, "body|empty"},
    {"C07", "M07 after empty", true, false, "empty|body"},
    {"C08", "M08 before list", false, false, "body|bullet item"},
    {"C09", "M09 item one", true, false, "body|bullet item"},
    {"C10", "M09 item one", false, false, "bullet item|bullet item"},
    {"C11", "M10 item two", true, false, "bullet item|bullet item"},
    {"C12", "M10 item two", false, false, "bullet item|body"},
    {"C13", "M11 after list", true, false, "bullet item|body"},
    {"C14", "M13 number two", true, false, "numbered item|numbered item"},
    {"C15", "M15 before table", false, false, "body|table"},
    {"C16", "M16 after table", true, false, "table|body"},
    {"C17", "M17 cell one", false, false, "cell|cell"},
    {"C19", "M19 before anchored", false, false, "body|body with anchored frame"},
    {"C20", "M20 has anchored frame", true, false, "body|body with anchored frame"},
    {"C21", "M21 before break", false, false, "body|body with page break"},
    {"C22", "M22 after break", true, false, "body|body with page break"},
    {"C23", "M23 before section", false, false, "body|section"},
    {"C24", "M24 in section", true, false, "body|section"},
    {"C25", "M24 in section", false, false, "section|body"},
    {"C26", "M25 after section", true, false, "section|body"},
    {"C27", "M26 line one", false, true, "line break inside a paragraph"},
    {"C28", "M26 line two", true, true, "line break inside a paragraph"},
    {"C29", "M01 plain alpha", true, false, "document start"},
    {"C30", "M29 last", false, false, "document end"},
};

std::mutex gMutex;
std::string gLastSelectionPayload;
std::string gLastCursorPayload;
int gSelectionCallbacks = 0;
std::vector<std::string> gUnoResults;

void onCallback(int type, const char *payload, void *) {
  std::lock_guard<std::mutex> lock(gMutex);
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR) {
    gLastCursorPayload = payload ? payload : "";
  } else if (type == LOK_CALLBACK_TEXT_SELECTION) {
    gLastSelectionPayload = payload ? payload : "";
    ++gSelectionCallbacks;
  } else if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
    gUnoResults.emplace_back(payload ? payload : "");
  }
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

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
        char buffer[8];
        std::snprintf(buffer, sizeof(buffer), "\\u%04x",
                      static_cast<unsigned char>(character));
        out += buffer;
      } else {
        out += character;
      }
    }
  }
  return out;
}

std::vector<unsigned> codePoints(const std::string &utf8) {
  std::vector<unsigned> out;
  for (std::size_t i = 0; i < utf8.size();) {
    const unsigned char lead = static_cast<unsigned char>(utf8[i]);
    unsigned value = lead;
    int extra = 0;
    if (lead >= 0xf0) { value = lead & 0x07; extra = 3; }
    else if (lead >= 0xe0) { value = lead & 0x0f; extra = 2; }
    else if (lead >= 0xc0) { value = lead & 0x1f; extra = 1; }
    for (int k = 1; k <= extra && i + k < utf8.size(); ++k)
      value = (value << 6) | (static_cast<unsigned char>(utf8[i + k]) & 0x3f);
    out.push_back(value);
    i += 1 + extra;
  }
  return out;
}

int rectangleCount(const std::string &payload) {
  if (payload.empty() || payload == "EMPTY")
    return 0;
  int count = 1;
  for (const char character : payload)
    count += character == ';';
  return count;
}

struct Readback {
  int type = -1;
  std::string text;
  std::string rectangles;
  std::string cursor;
  int callbacks = 0;
};

Readback readSelection(LibreOfficeKitDocument *document) {
  Readback out;
  char *text = nullptr;
  out.type = document->pClass->getSelectionTypeAndText(
      document, "text/plain;charset=utf-8", &text, nullptr);
  out.text = text ? text : "";
  std::free(text);
  std::lock_guard<std::mutex> lock(gMutex);
  out.rectangles = gLastSelectionPayload;
  out.cursor = gLastCursorPayload;
  out.callbacks = gSelectionCallbacks;
  return out;
}

std::string readbackJson(const Readback &readback) {
  std::string out = "{\"type\":" + std::to_string(readback.type) +
                    ",\"text\":\"" + jsonEscape(readback.text) +
                    "\",\"codePoints\":[";
  const std::vector<unsigned> points = codePoints(readback.text);
  for (std::size_t i = 0; i < points.size(); ++i)
    out += (i ? "," : "") + std::to_string(points[i]);
  out += "],\"rectangleCount\":" +
         std::to_string(rectangleCount(readback.rectangles)) +
         ",\"rectangles\":\"" + jsonEscape(readback.rectangles) +
         "\",\"cursor\":\"" + jsonEscape(readback.cursor) +
         "\",\"selectionCallbacks\":" + std::to_string(readback.callbacks) +
         "}";
  return out;
}

void key(LibreOfficeKitDocument *document, int code) {
  document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT, 0, code);
  document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYUP, 0, code);
}

// Returns the UNO_COMMAND_RESULT payload for `command`, or "" on timeout.
std::string dispatch(LibreOfficeKitDocument *document, const char *command,
                     const char *arguments = nullptr, int timeoutMs = 4000) {
  std::size_t before;
  {
    std::lock_guard<std::mutex> lock(gMutex);
    before = gUnoResults.size();
  }
  document->pClass->postUnoCommand(document, command, arguments, true);
  for (int waited = 0; waited < timeoutMs; waited += 50) {
    drain(50);
    std::lock_guard<std::mutex> lock(gMutex);
    for (std::size_t i = before; i < gUnoResults.size(); ++i)
      if (gUnoResults[i].find(command) != std::string::npos)
        return gUnoResults[i];
  }
  return "";
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

bool saveAs(LibreOfficeKitDocument *document, const std::string &path) {
  const std::string url = "file://" + path;
  return document->pClass->saveAs(document, url.c_str(), "odt", nullptr) != 0;
}

// Search the anchor, then move to the paragraph's (or line's) start or end.
// A move without Shift drops the search selection; the readback says whether
// the caret really ended up collapsed.
Readback position(LibreOfficeKitDocument *document, const Case &c,
                  std::string &searchResult) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") + jsonEscape(c.anchor) + "\"},"
      "\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  // From the document's start: a load can restore the cursor where the file
  // was last saved (the owner's PMPC document), and a search from there finds
  // a later copy of the anchor first -- the table of contents repeats every
  // heading (round-20261006T073914Z-second-search-fault).
  dispatch(document, ".uno:GoToStartOfDoc", nullptr, 1500);
  drain(300);
  // As e2b_native_crossparagraph.cpp: the search is posted without a result
  // request and given time; the selection readback below is the check.
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(900);
  searchResult = readSelection(document).text;
  // Always to the start first.  The search leaves the caret at the anchor's
  // end, which IS the paragraph's end when the anchor is the whole paragraph,
  // and GoToEndOfPara from a paragraph's end goes on to the NEXT paragraph's
  // end (the first run, round-20261006T063607Z-instrument-fault, measured
  // P2's boundary for C01 that way).  From the start, the end is this one's.
  dispatch(document, c.line ? ".uno:GoToStartOfLine" : ".uno:GoToStartOfPara",
           nullptr, 1500);
  drain(300);
  if (!c.backward) {
    dispatch(document, c.line ? ".uno:GoToEndOfLine" : ".uno:GoToEndOfPara",
             nullptr, 1500);
    drain(300);
  }
  return readSelection(document);
}

// Place the caret with ONE search, check the placement, and come back to it.
// The check selects from the caret to the paragraph's (line's) far edge and
// compares that text with the anchor; then a move without Shift returns to
// the caret's edge of the same paragraph.  The first version searched again
// after the check, and where the anchor had a second copy (a table of
// contents) the arm measured the copy while the check had passed on the
// original (round-20261006T073914Z-second-search-fault).
Readback placeAndCheck(LibreOfficeKitDocument *document, const Case &c,
                       std::string &search, std::string &checkText) {
  position(document, c, search);
  const char *edge = c.line ? (c.backward ? ".uno:EndOfLineSel" : ".uno:StartOfLineSel")
                            : (c.backward ? ".uno:EndOfParaSel" : ".uno:StartOfParaSel");
  dispatch(document, edge, nullptr, 1500);
  drain(300);
  checkText = readSelection(document).text;
  // Backward: the point is at the far end, GoToStartOfPara collapses at this
  // paragraph's start.  Forward: the point is at the start, and from a
  // paragraph's start GoToEndOfPara is this paragraph's end.
  const char *back = c.line ? (c.backward ? ".uno:GoToStartOfLine" : ".uno:GoToEndOfLine")
                            : (c.backward ? ".uno:GoToStartOfPara" : ".uno:GoToEndOfPara");
  dispatch(document, back, nullptr, 1500);
  drain(300);
  return readSelection(document);
}

void runCase(LibreOfficeKit *kit, const char *url, const Case &c, int round,
             const std::string &outDir, int presses) {
  const std::string stem =
      outDir + "/r" + std::to_string(round) + "-" + c.id;

  // Arm "select": what the shipped barrier does, up to and including the
  // dispatch it currently refuses to make.
  {
    LibreOfficeKitDocument *document = openDocument(kit, url);
    std::cout << "{\"round\":" << round << ",\"case\":\"" << c.id
              << "\",\"arm\":\"select\",\"boundary\":\"" << c.boundary
              << "\",\"backward\":" << (c.backward ? "true" : "false");
    if (!document) {
      std::cout << ",\"fatal\":\"documentLoad\"}" << std::endl;
      return;
    }
    std::string search, check;
    // Placement self-check: from the caret to the paragraph's (line's) far
    // edge must be exactly the anchor, or this case measured another boundary.
    const Readback placed = placeAndCheck(document, c, search, check);
    std::cout << ",\"search\":\"" << jsonEscape(search)
              << "\",\"placementCheck\":\"" << jsonEscape(check)
              << "\",\"placementOk\":" << (check == c.anchor ? "true" : "false")
              << ",\"placed\":" << readbackJson(placed);
    key(document, (c.backward ? kLeft : kRight) | kShift);
    drain(700);
    const Readback unit = readSelection(document);
    std::cout << ",\"unit\":" << readbackJson(unit);
    if (unit.type == LOK_SELTYPE_NONE) {
      // The product refuses here (nothing to delete); so does this arm.
      std::cout << ",\"dispatched\":false";
    } else {
      const std::string result = dispatch(
          document, c.backward ? ".uno:SwBackspace" : ".uno:Delete");
      drain(400);
      std::cout << ",\"dispatched\":true,\"result\":\"" << jsonEscape(result)
                << "\",\"after\":" << readbackJson(readSelection(document));
      std::cout << ",\"saved\":" << (saveAs(document, stem + "-select.odt") ? "true" : "false");
      const std::string undo = dispatch(document, ".uno:Undo");
      drain(400);
      std::cout << ",\"undo\":\"" << jsonEscape(undo) << "\",\"undoSaved\":"
                << (saveAs(document, stem + "-select-undo.odt") ? "true" : "false");
    }
    document->pClass->destroy(document);
    std::cout << "}" << std::endl;
  }

  // Arm "key": the reference -- the user's own key on a collapsed caret.
  {
    LibreOfficeKitDocument *document = openDocument(kit, url);
    std::cout << "{\"round\":" << round << ",\"case\":\"" << c.id
              << "\",\"arm\":\"key\",\"boundary\":\"" << c.boundary
              << "\",\"backward\":" << (c.backward ? "true" : "false");
    if (!document) {
      std::cout << ",\"fatal\":\"documentLoad\"}" << std::endl;
      return;
    }
    std::string search, check;
    const Readback placed = placeAndCheck(document, c, search, check);
    std::cout << ",\"search\":\"" << jsonEscape(search)
              << "\",\"placementCheck\":\"" << jsonEscape(check)
              << "\",\"placementOk\":" << (check == c.anchor ? "true" : "false")
              << ",\"placed\":" << readbackJson(placed);
    key(document, c.backward ? kBackspace : kDelete);
    drain(900);
    std::cout << ",\"after\":" << readbackJson(readSelection(document))
              << ",\"saved\":" << (saveAs(document, stem + "-key.odt") ? "true" : "false");
    if (presses > 1) {
      std::cout << ",\"laterPresses\":[";
      for (int press = 2; press <= presses; ++press) {
        key(document, c.backward ? kBackspace : kDelete);
        drain(900);
        std::cout << (press > 2 ? "," : "") << "{\"press\":" << press
                  << ",\"after\":" << readbackJson(readSelection(document))
                  << ",\"saved\":"
                  << (saveAs(document, stem + "-key" + std::to_string(press) + ".odt") ? "true" : "false")
                  << "}";
      }
      std::cout << "]";
    }
    document->pClass->destroy(document);
    std::cout << "}" << std::endl;
  }
}

std::vector<Case> readCases(const char *path) {
  std::vector<Case> out;
  std::ifstream in(path);
  std::string row;
  while (std::getline(in, row)) {
    if (row.empty() || row[0] == '#')
      continue;
    std::vector<std::string> fields;
    std::stringstream split(row);
    for (std::string field; std::getline(split, field, '\t');)
      fields.push_back(field);
    if (fields.size() != 5) {
      std::cerr << "bad case row (want 5 tab-separated fields): " << row << "\n";
      std::exit(2);
    }
    out.push_back({fields[0], fields[1], fields[2] == "1", fields[3] == "1", fields[4]});
  }
  return out;
}

} // namespace

int main(int argc, char **argv) {
  if (argc < 6) {
    std::cerr << "usage: merge-native-boundaries INSTALL PROFILE_URL DOCUMENT_URL OUT_DIR ROUNDS [CASES_TSV [PRESSES]]\n";
    return 2;
  }
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 failed\n";
    return 1;
  }
  const std::string outDir = argv[4];
  const int rounds = std::atoi(argv[5]);
  const std::vector<Case> cases = argc > 6 ? readCases(argv[6]) : kCases;
  const int presses = argc > 7 ? std::atoi(argv[7]) : 1;
  if (cases.empty() || presses < 1) {
    std::cerr << "no cases\n";
    return 2;
  }
  {
    LibreOfficeKitDocument *document = openDocument(kit, argv[3]);
    if (!document) {
      std::cerr << "documentLoad failed\n";
      return 1;
    }
    std::cout << "{\"original\":" << (saveAs(document, outDir + "/original.odt") ? "true" : "false")
              << "}" << std::endl;
    document->pClass->destroy(document);
  }
  for (int round = 1; round <= rounds; ++round)
    for (const Case &c : cases)
      runCase(kit, argv[3], c, round, outDir, presses);
  kit->pClass->destroy(kit);
  return 0;
}
