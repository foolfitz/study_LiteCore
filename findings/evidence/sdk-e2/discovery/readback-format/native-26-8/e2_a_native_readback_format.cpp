// E2-A native probe: what can the postcondition read actually be read AS, and
// which tags does the HTML flavour really produce?
//
// Two questions in one document load, because finding 035 makes them the same
// decision.  The readback's closed tag set accepts ul/ol/li/h1/p and rejects
// everything else, so <b>, <i> and -- because the serialiser wraps every CJK
// run -- <font>/<span> all fail closed.  Widening that set by hand is the
// option this probe exists to price.
//
//   1. FORMAT.  odfdom classifies elements from the ODF RelaxNG schema
//      (generated sources; `paragraph-content` alone has 163 refs), which is
//      why a hand-written inline allowlist is the wrong shape: the list is
//      long, machine-derivable, and ours would be neither.  If the selection
//      can be read back AS ODF, the classification gets a schema behind it and
//      SPEC E2-A 2.8's own warning -- that the HTML is a serialiser output and
//      not a documented contract -- stops applying.  Writer's transferable
//      offers EMBED_SOURCE for a text selection (sw/source/uibase/dochdl/
//      swdtflvr.cxx:3734), whose mime string is the ODF package
//      (sot/source/base/exchange.cxx:136).  Whether LOK can hand it over is a
//      different question and the one measured here.
//
//   2. TAGS.  If ODF is not reachable, the fix is odfdom's other idea: a small
//      closed set of structural roots, everything inside one of them ignored
//      (OdfElement::getComponentRoot walks up to the nearest root; only nine
//      elements declare themselves one).  That needs the real tag inventory of
//      this serialiser, per paragraph shape -- not a list written from memory.
//
// Two APIs, because they are not interchangeable:
//
//   * getTextSelection() reads pDoc->getSelection() and returns a bare char*.
//     convertOString memcpy's the whole payload and tolerates embedded NULs
//     (desktop/source/lib/init.cxx:377) -- but the caller is given no length,
//     so for a ZIP-shaped payload strlen() is a LOWER BOUND and nothing more.
//     Reported as `strlenLowerBound`, never as "bytes".
//   * getClipboard() reads the LOK clipboard (so a copy has to happen first)
//     and returns explicit sizes.  Passing pMimeTypes=NULL makes it enumerate
//     getTransferDataFlavors() -- the actual offer, measured rather than
//     guessed (init.cxx:6082).
//
// Usage: e2-a-native-readback-format INSTALL PROFILE_URL OUTDIR DOC_URL...

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
#include <set>
#include <string>
#include <thread>
#include <vector>

namespace {

std::string jsonEscape(const char *value, std::size_t length) {
  std::string out;
  if (!value)
    return out;
  for (std::size_t index = 0; index < length; ++index) {
    const unsigned char character = static_cast<unsigned char>(value[index]);
    switch (character) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': out += "\\r"; break;
    case '\t': out += "\\t"; break;
    default:
      if (character < 0x20 || character == 0x7f) {
        char buffer[8];
        std::snprintf(buffer, sizeof(buffer), "\\u%04x", character);
        out += buffer;
      } else {
        out += static_cast<char>(character);
      }
    }
  }
  return out;
}

std::string jsonEscape(const std::string &value) {
  return jsonEscape(value.data(), value.size());
}

// Binary payloads are hex, not "escaped text".  The first version escaped only
// control characters and passed every byte >= 0x20 through, which emitted the
// ODF package's raw bytes into a JSON string and made the whole evidence file
// invalid UTF-8 -- unreadable by the tool that was meant to read it.  A flavour
// this probe exists to discover may be binary by definition, so the encoding
// cannot assume text.
std::string hexPrefix(const char *value, std::size_t length) {
  static const char kDigits[] = "0123456789abcdef";
  std::string out;
  if (!value)
    return out;
  out.reserve(length * 2);
  for (std::size_t index = 0; index < length; ++index) {
    const unsigned char character = static_cast<unsigned char>(value[index]);
    out += kDigits[character >> 4];
    out += kDigits[character & 0x0f];
  }
  return out;
}

// Only when every byte is printable ASCII, so a text flavour stays readable and
// a binary one never masquerades as text.
std::string asciiPrefix(const char *value, std::size_t length) {
  if (!value)
    return std::string();
  for (std::size_t index = 0; index < length; ++index) {
    const unsigned char character = static_cast<unsigned char>(value[index]);
    if (character != '\n' && character != '\r' && character != '\t' &&
        (character < 0x20 || character > 0x7e))
      return std::string();
  }
  return jsonEscape(value, length);
}

struct Rectangle {
  long x = 0, y = 0, width = 0, height = 0;
  bool valid = false;
};

Rectangle gCaret;
std::string gSelectionPayload;
bool gSelectionSeen = false;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_TEXT_SELECTION) {
    gSelectionSeen = true;
    gSelectionPayload = payload ? payload : "";
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
              bool notify, int drainMs = 400) {
  document->pClass->postUnoCommand(document, command, nullptr, notify);
  drain(drainMs);
}

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
  gSelectionSeen = false;
  gSelectionPayload.clear();
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(700);
  Rectangle hit = gCaret;
  if (!hit.valid && gSelectionSeen) {
    Rectangle parsed;
    if (std::sscanf(gSelectionPayload.c_str(), "%ld, %ld, %ld, %ld", &parsed.x,
                    &parsed.y, &parsed.width, &parsed.height) == 4) {
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

// Derived from source, not guessed.  SwTransferable::SetDataForDragAndDrop
// adds EMBED_SOURCE, RTF, RICHTEXT, HTML, MARKDOWN and STRING for a text
// selection (sw/source/uibase/dochdl/swdtflvr.cxx:3734-3746); the strings come
// from sot/source/base/exchange.cxx.  The last entry is a NEGATIVE CONTROL: it
// is a plausible-looking ODF mime type that appears nowhere in that table, so a
// run where everything "works" is distinguishable from a run where the probe
// cannot report a failure.
const char *const kMimeTypes[] = {
    "text/plain;charset=utf-8",
    "text/html",
    "application/x-openoffice-embed-source-xml;windows_formatname=\"Star Embed Source (XML)\"",
    "text/rtf",
    "text/richtext",
    "text/markdown",
    "application/vnd.oasis.opendocument.text",
};
const bool kMimeIsNegativeControl[] = {
    false, false, false, false, false, false, true,
};

void sweepMimeTypes(LibreOfficeKitDocument *document, const char *label) {
  for (std::size_t index = 0;
       index < sizeof(kMimeTypes) / sizeof(kMimeTypes[0]); ++index) {
    char *used = nullptr;
    char *value = document->pClass->getTextSelection(document,
                                                     kMimeTypes[index], &used);
    const std::size_t lower = value ? std::strlen(value) : 0;
    std::cout << "{\"probe\":\"mime\",\"anchor\":\"" << jsonEscape(label)
              << "\",\"mimeType\":\"" << jsonEscape(kMimeTypes[index])
              << "\",\"negativeControl\":"
              << (kMimeIsNegativeControl[index] ? "true" : "false")
              << ",\"returned\":" << (value ? "true" : "false")
              // Named for what it is.  getTextSelection hands back no length,
              // so for any payload that can contain a NUL this is a floor.
              << ",\"strlenLowerBound\":" << lower << ",\"prefixAscii\":\""
              << asciiPrefix(value, lower < 160 ? lower : 160)
              << "\",\"prefixHex\":\""
              << hexPrefix(value, lower < 32 ? lower : 32) << "\"}\n";
    std::free(value);
    std::free(used);
  }
  std::cout.flush();
}

// The offer itself, enumerated by core rather than listed by us.
void enumerateClipboardFlavors(LibreOfficeKitDocument *document,
                               const char *label) {
  // getClipboard reads the LOK clipboard, not the live selection, so the
  // selection has to be copied there first.
  dispatch(document, ".uno:Copy", false, 600);

  size_t count = 0;
  char **mimes = nullptr;
  size_t *sizes = nullptr;
  char **streams = nullptr;
  const int ok = document->pClass->getClipboard(document, nullptr, &count,
                                                &mimes, &sizes, &streams);
  std::cout << "{\"probe\":\"clipboard\",\"anchor\":\"" << jsonEscape(label)
            << "\",\"ok\":" << ok << ",\"count\":" << count << "}\n";
  for (size_t index = 0; index < count; ++index) {
    const std::size_t size = sizes ? sizes[index] : 0;
    const char *stream = streams ? streams[index] : nullptr;
    std::cout << "{\"probe\":\"flavor\",\"anchor\":\"" << jsonEscape(label)
              << "\",\"mimeType\":\""
              << jsonEscape(mimes && mimes[index] ? mimes[index] : "")
              // This one IS the byte count: getClipboard reports sizes.
              << "\",\"bytes\":" << size << ",\"prefixAscii\":\""
              << asciiPrefix(stream, size < 120 ? size : 120)
              << "\",\"prefixHex\":\""
              << hexPrefix(stream, size < 32 ? size : 32) << "\"}\n";
  }
  std::cout.flush();
  for (size_t index = 0; index < count; ++index) {
    if (mimes) std::free(mimes[index]);
    if (streams) std::free(streams[index]);
  }
  std::free(mimes);
  std::free(sizes);
  std::free(streams);
}

// Every open tag, with the nesting context it appeared in.
//
// The question the fix turns on is not "which tags exist" but "can a tag that
// does not affect the answer be told from one that does, without a list of
// every tag".  odfdom answers it structurally: a small set of component roots,
// and getComponentRoot() walks up to the nearest one.  The equivalent claim
// here is that every non-structural tag appears INSIDE an already-open block --
// so the inventory records, for each tag, whether it was ever seen at body
// level.  A tag seen at body level cannot be ignored by that rule.
const char *const kCandidateBlockTags[] = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
    "table", "tr", "td", "th", "blockquote", "div", "pre",
};

bool isCandidateBlock(const std::string &tag) {
  for (const char *candidate : kCandidateBlockTags)
    if (tag == candidate)
      return true;
  return false;
}

bool isVoidTag(const std::string &tag) {
  return tag == "br" || tag == "img" || tag == "hr" || tag == "meta" ||
         tag == "link" || tag == "col" || tag == "input";
}

struct TagObservation {
  std::set<std::string> anchors;
  std::size_t insideBlock = 0;
  std::size_t atBodyLevel = 0;
};
std::map<std::string, TagObservation> gInventory;

void inventoryTags(const std::string &html, const std::string &anchor) {
  const std::size_t body = html.find("<body");
  if (body == std::string::npos)
    return;
  std::size_t index = html.find('>', body);
  if (index == std::string::npos)
    return;
  std::vector<std::string> stack;
  for (++index; index < html.size(); ++index) {
    if (html[index] != '<')
      continue;
    std::size_t start = index + 1;
    if (start >= html.size())
      break;
    const bool closing = html[start] == '/';
    if (closing)
      ++start;
    std::size_t end = start;
    while (end < html.size() &&
           ((html[end] >= 'a' && html[end] <= 'z') ||
            (html[end] >= 'A' && html[end] <= 'Z') ||
            (html[end] >= '0' && html[end] <= '9')))
      ++end;
    if (end == start)
      continue;
    std::string tag = html.substr(start, end - start);
    for (char &character : tag)
      if (character >= 'A' && character <= 'Z')
        character = static_cast<char>(character - 'A' + 'a');
    if (tag == "body")
      break;
    if (closing) {
      if (!stack.empty() && stack.back() == tag)
        stack.pop_back();
      index = end - 1;
      continue;
    }
    // "Inside a block" means an ancestor is one of the candidate block tags --
    // the property option (B) would rely on.
    bool insideBlock = false;
    for (const std::string &open : stack)
      if (isCandidateBlock(open))
        insideBlock = true;
    TagObservation &record = gInventory[tag];
    record.anchors.insert(anchor);
    if (insideBlock)
      ++record.insideBlock;
    else
      ++record.atBodyLevel;
    if (!isVoidTag(tag))
      stack.push_back(tag);
    index = end - 1;
  }
}

void readAndInventory(LibreOfficeKitDocument *document,
                      const std::string &anchor) {
  char *html = document->pClass->getTextSelection(document, "text/html",
                                                  nullptr);
  char *text = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", nullptr);
  // Read for every anchor, not only in the action sweep: the escaping question
  // is about an untouched paragraph, with no dispatch involved at all.
  char *markdown = document->pClass->getTextSelection(document, "text/markdown",
                                                      nullptr);
  const std::string markup = html ? html : "";
  const std::size_t markdownLength = markdown ? std::strlen(markdown) : 0;
  std::cout << "{\"probe\":\"readback\",\"anchor\":\"" << jsonEscape(anchor)
            << "\",\"selectionType\":"
            << document->pClass->getSelectionType(document)
            << ",\"htmlBytes\":" << markup.size() << ",\"text\":\""
            << jsonEscape(text ? text : "", text ? std::strlen(text) : 0)
            << "\",\"markdown\":\""
            << jsonEscape(markdown ? markdown : "", markdownLength)
            // Hex as well: whether an escape character is present is exactly
            // what this row exists to answer, and a backslash is easy to lose
            // in a chain of escaping layers.
            << "\",\"markdownHex\":\""
            << hexPrefix(markdown, markdownLength < 40 ? markdownLength : 40)
            << "\",\"html\":\"" << jsonEscape(markup) << "\"}\n";
  std::cout.flush();
  inventoryTags(markup, anchor);
  std::free(html);
  std::free(text);
  std::free(markdown);
}

// text/markdown turned up in the flavour list and it changes the question, so
// it gets measured rather than admired.  If the five closed actions are
// distinguishable in Markdown, the postcondition parser stops needing a tag
// classification at all -- and finding 035 disappears at the root rather than
// being worked around, because Markdown has no font runs to wrap CJK text in.
//
// Both flavours are read for every step, so "Markdown can express this" and
// "the HTML we already trust says the same thing" are checked against each
// other rather than one being taken on faith.
struct ActionStep {
  const char *label;
  const char *command;
  const char *arguments;
};

const ActionStep kActionSteps[] = {
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

void measureActionsInBothFlavours(LibreOfficeKitDocument *document,
                                  const char *anchor, const char *shape) {
  for (const ActionStep &step : kActionSteps) {
    if (!positionAtAnchor(document, anchor)) {
      std::cout << "{\"probe\":\"action\",\"shape\":\"" << jsonEscape(shape)
                << "\",\"step\":\"" << step.label
                << "\",\"placed\":false,\"skipped\":true}\n";
      continue;
    }
    document->pClass->postUnoCommand(document, step.command, step.arguments,
                                     true);
    drain(1200);
    dispatch(document, ".uno:SelectText", true, 600);
    char *html = document->pClass->getTextSelection(document, "text/html",
                                                    nullptr);
    char *markdown = document->pClass->getTextSelection(document,
                                                        "text/markdown",
                                                        nullptr);
    const std::string markupHtml = html ? html : "";
    const std::size_t markdownLength = markdown ? std::strlen(markdown) : 0;
    std::size_t bodyIndex = markupHtml.find("<body");
    if (bodyIndex != std::string::npos)
      bodyIndex = markupHtml.find('>', bodyIndex);
    const std::string htmlBody =
        bodyIndex == std::string::npos
            ? markupHtml
            : markupHtml.substr(bodyIndex + 1,
                                markupHtml.size() - bodyIndex - 1);
    std::cout << "{\"probe\":\"action\",\"shape\":\"" << jsonEscape(shape)
              << "\",\"step\":\"" << step.label << "\",\"placed\":true"
              << ",\"markdownBytes\":" << markdownLength
              << ",\"markdown\":\""
              << jsonEscape(markdown ? markdown : "", markdownLength)
              << "\",\"markdownHex\":\""
              << hexPrefix(markdown, markdownLength < 48 ? markdownLength : 48)
              << "\",\"htmlBody\":\""
              << jsonEscape(htmlBody.substr(0, 300)) << "\"}\n";
    std::cout.flush();
    std::free(html);
    std::free(markdown);
  }
}

struct Fixture {
  const char *name;
  std::vector<const char *> anchors;
};

// One entry per document, covering the paragraph shapes the coverage axis
// added on 2026-08-11 names: plain ASCII with no runs (the only shape the 375
// judged dispatches ever used), inline character formatting, CJK, headings,
// list items, table cells, and an empty paragraph.
const Fixture kFixtures[] = {
    {"styled-list",
     {"E1-STYLED-HEADING", "bold anchor", "E1-LIST-ONE", "E1-STYLED-END"}},
    {"multi-paragraph",
     {"E1-MULTI-START alpha", "\xe7\xac\xac\xe4\xba\x8c\xe6\xae\xb5"
      "\xe4\xb8\xad\xe6\x96\x87 beta", "E1-MULTI-END omega"}},
    {"plain-grapheme",
     {"E1-PLAIN-START", "\xe8\x87\xba\xe7\x81\xa3\xe4\xb8\xad\xe6\x96\x87"
      "\xe6\xb8\xb8\xe6\xa8\x99\xe6\xb8\xac\xe8\xa9\xa6",
      "emoji \xf0\x9f\x98\x80 grapheme", "combining \xc3\xa9 boundary"}},
    {"table-boundary", {"E1-TABLE-BEFORE", "E1-CELL-A1", "E1-TABLE-AFTER"}},
    {"empty-paragraph", {"E1-EMPTY-BEFORE", "E1-EMPTY-AFTER"}},
    {"r7-t2-styled", {"R1 \xe6\xa8\xa3\xe5\xbc\x8f\xe6\x96\x87\xe4\xbb\xb6"}},
    // finding 035 / the Markdown candidate.  Each look-alike is paired with the
    // real thing, because the question is whether the two can be told apart.
    {"markdown-syntax",
     {"MD-CONTROL", "MD-DASH", "MD-NUMBER", "MD-HASH", "MD-QUOTE", "MD-STAR",
      "MD-REAL-ITEM", "MD-REAL-HEADING"}},
};

const Fixture *fixtureFor(const std::string &url) {
  for (const Fixture &fixture : kFixtures) {
    const std::string needle = std::string("/") + fixture.name + ".odt";
    if (url.size() >= needle.size() &&
        url.compare(url.size() - needle.size(), needle.size(), needle) == 0)
      return &fixture;
  }
  return nullptr;
}

} // namespace

int main(int argc, char **argv) {
  if (argc < 5) {
    std::cerr << "expected INSTALL PROFILE_URL OUTDIR DOC_URL...\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }
  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');

  bool sweptMimeTypes = false;
  for (int argument = 4; argument < argc; ++argument) {
    const std::string url = argv[argument];
    const Fixture *fixture = fixtureFor(url);
    if (!fixture) {
      std::cout << "{\"probe\":\"document\",\"url\":\"" << jsonEscape(url)
                << "\",\"skipped\":\"no anchor list for this fixture\"}\n";
      continue;
    }
    LibreOfficeKitDocument *document =
        kit->pClass->documentLoad(kit, url.c_str());
    if (!document) {
      std::cout << "{\"probe\":\"document\",\"fixture\":\"" << fixture->name
                << "\",\"loaded\":false}\n";
      continue;
    }
    document->pClass->initializeForRendering(document, "{}");
    document->pClass->registerCallback(document, onCallback, nullptr);
    document->pClass->paintTile(document,
                                reinterpret_cast<unsigned char *>(pixels.data()),
                                canvas, canvas, 0, 0, 3840, 3840);
    drain(500);
    std::cout << "{\"probe\":\"document\",\"fixture\":\"" << fixture->name
              << "\",\"loaded\":true}\n";

    for (const char *anchor : fixture->anchors) {
      const std::string label =
          std::string(fixture->name) + "/" + anchor;
      if (!positionAtAnchor(document, anchor)) {
        std::cout << "{\"probe\":\"readback\",\"anchor\":\""
                  << jsonEscape(label) << "\",\"placed\":false,"
                     "\"skipped\":true}\n";
        continue;
      }
      dispatch(document, ".uno:SelectText", true, 600);
      readAndInventory(document, label);
      if (!sweptMimeTypes) {
        // Once is enough for the format question -- the flavour offer is a
        // property of the transferable, not of the paragraph -- and doing it
        // on the first anchor keeps the run short.
        sweepMimeTypes(document, label.c_str());
        enumerateClipboardFlavors(document, label.c_str());
        sweptMimeTypes = true;
      }
    }
    // The action sweep runs on styled-list only: the five closed actions are a
    // property of the command set, not of the document, and one fixture keeps
    // the run short.  The two shapes finding 035 is about are both included --
    // a paragraph with character formatting, and one with CJK text.
    // The multi-block signature.  finding 034's guard refuses any readback that
    // covers more than one paragraph, and that guard is load-bearing -- so a
    // flavour that cannot express "this was more than one paragraph" cannot
    // replace the one we have.  SelectAll is the cheapest way to produce a
    // selection that is definitely multi-block.
    if (std::strcmp(fixture->name, "styled-list") == 0) {
      dispatch(document, ".uno:SelectAll", false, 600);
      char *html = document->pClass->getTextSelection(document, "text/html",
                                                      nullptr);
      char *markdown = document->pClass->getTextSelection(document,
                                                          "text/markdown",
                                                          nullptr);
      std::cout << "{\"probe\":\"multiblock\",\"markdown\":\""
                << jsonEscape(markdown ? markdown : "",
                              markdown ? std::strlen(markdown) : 0)
                << "\",\"htmlBytes\":" << (html ? std::strlen(html) : 0)
                << "}\n";
      std::cout.flush();
      std::free(html);
      std::free(markdown);
    }
    if (std::strcmp(fixture->name, "styled-list") == 0)
      measureActionsInBothFlavours(document, "E1-STYLED-END", "plain-ascii");
    if (std::strcmp(fixture->name, "styled-list") == 0)
      measureActionsInBothFlavours(document, "bold anchor", "inline-formatted");
    if (std::strcmp(fixture->name, "multi-paragraph") == 0)
      measureActionsInBothFlavours(
          document, "\xe7\xac\xac\xe4\xba\x8c\xe6\xae\xb5"
                    "\xe4\xb8\xad\xe6\x96\x87 beta", "cjk");
    document->pClass->destroy(document);
  }

  std::cout << "{\"probe\":\"inventory\",\"tags\":[";
  bool first = true;
  for (const auto &entry : gInventory) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << "{\"tag\":\"" << jsonEscape(entry.first)
              << "\",\"candidateBlock\":"
              << (isCandidateBlock(entry.first) ? "true" : "false")
              << ",\"insideBlock\":" << entry.second.insideBlock
              << ",\"atBodyLevel\":" << entry.second.atBodyLevel
              << ",\"anchors\":[";
    bool firstAnchor = true;
    for (const std::string &anchor : entry.second.anchors) {
      if (!firstAnchor)
        std::cout << ',';
      firstAnchor = false;
      std::cout << '"' << jsonEscape(anchor) << '"';
    }
    std::cout << "]}";
  }
  std::cout << "]}\n";
  std::cout.flush();

  kit->pClass->destroy(kit);
  return 0;
}
