// E2-A native format-readback probe.
//
// Product route C decides completion from the postcondition alone, and finding
// 030 showed the postcondition source it uses -- the STATE_CHANGED broadcast --
// goes silent whenever the value did not change, which is exactly the case a
// repeated press produces.  The chosen way out is to read the document instead
// of listening for a broadcast.  Before building a barrier on that, this probe
// asks whether a readback that answers the five closed actions exists at all.
//
// getCommandValues is already ruled out by reading its implementation:
// sw/source/uibase/uno/loktxdoc.cxx serves form fields, bookmarks, sections and
// ExtractDocumentStructures (charts, content controls, doc props, track
// changes), none of which report the cursor paragraph's style or list state.
//
// What is left is the selection transferable: doc_getTextSelection
// (desktop/source/lib/init.cxx:5912) hands the selection to the clipboard
// machinery, so asking for text/html should yield <h1> for a heading and
// <ol>/<ul><li> for a list item -- document truth, no callback involved.
// "Should" is the reason this probe exists.
//
// Two things get measured, because they are different questions:
//
//   1. Does a *collapsed caret* yield anything?  If it does, the barrier costs
//      nothing extra.  Finding 017 is a standing reason to doubt it.
//   2. Does selecting the paragraph yield it?  That works if (1) fails, but it
//      moves the selection, which a postcondition read must not do silently.
//
// Both are read before and after a format dispatch, since a readback that
// cannot see the change is no use as a postcondition.
//
// Usage: e2-a-native-format-readback INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR

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

using Clock = std::chrono::steady_clock;
const auto gStarted = Clock::now();

double elapsedMs() {
  return std::chrono::duration<double, std::milli>(Clock::now() - gStarted)
      .count();
}

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
  long x = 0;
  long y = 0;
  long width = 0;
  long height = 0;
  bool valid = false;
};

Rectangle gCaret;

void emit(const char *stage, const std::string &extra = std::string()) {
  std::cout << "{\"stage\":\"" << stage << "\",\"atMs\":" << elapsedMs();
  if (!extra.empty())
    std::cout << ',' << extra;
  std::cout << "}\n";
  std::cout.flush();
}

void onCallback(int type, const char *payload, void *) {
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
              const char *arguments, int drainMs) {
  document->pClass->postUnoCommand(document, command, arguments, true);
  drain(drainMs);
}

void positionAtAnchor(LibreOfficeKitDocument *document, const char *anchor) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") +
      anchor +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  gCaret = Rectangle{};
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(700);
  const Rectangle hit = gCaret;
  if (hit.valid)
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       hit.x, hit.y + hit.height / 2);
  drain(500);
}

// The whole payload is emitted, not a summary of it.  A summary would be this
// probe deciding in advance which part of the markup answers the question,
// which is the mistake the earlier StyleApply constants made.
void readSelection(LibreOfficeKitDocument *document, const char *label,
                   const char *position, const char *mime) {
  char *used = nullptr;
  char *value = document->pClass->getTextSelection(document, mime, &used);
  const int type = document->pClass->getSelectionType(document);
  emit("readback",
       std::string("\"phase\":\"") + label + "\",\"position\":\"" + position +
           "\",\"mime\":\"" + mime + "\",\"selectionType\":" +
           std::to_string(type) + ",\"bytes\":" +
           std::to_string(value ? std::strlen(value) : 0) + ",\"value\":\"" +
           (value ? jsonEscape(value) : "") + "\"");
  std::free(value);
  std::free(used);
}

const char *const kMimes[] = {
    "text/plain;charset=utf-8",
    "text/html",
};

void readAll(LibreOfficeKitDocument *document, const char *label,
             const char *position) {
  for (const char *mime : kMimes)
    readSelection(document, label, position, mime);
}

struct Position {
  const char *name;
  const char *anchor;
};

} // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR\n";
    return 64;
  }
  const std::string outDir = argv[4];

  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    const char *error =
        kit->pClass->getError ? kit->pClass->getError(kit) : nullptr;
    std::cerr << (error ? error : "documentLoad returned null") << '\n';
    kit->pClass->destroy(kit);
    return 3;
  }
  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);

  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              canvas, canvas, 0, 0, 3840, 3840);
  drain(500);

  const Position positions[] = {
      {"heading", "E1-STYLED-HEADING"},
      {"body-paragraph", "bold anchor"},
      {"list-item", "E1-LIST-ONE"},
  };

  // ---- Phase 1: collapsed caret ------------------------------------------
  emit("phase", "\"name\":\"collapsed\"");
  for (const Position &position : positions) {
    positionAtAnchor(document, position.anchor);
    readAll(document, "collapsed", position.name);
  }

  // ---- Phase 2: paragraph selected ---------------------------------------
  //
  // FN_START_OF_PARA / FN_END_OF_PARA_SEL (sw/sdi/swriter.sdi:2246, :1130) are
  // paragraph-relative, not line-relative, so this stays correct when applying
  // a heading style rewraps the text.
  emit("phase", "\"name\":\"paragraph-selected\"");
  for (const Position &position : positions) {
    positionAtAnchor(document, position.anchor);
    dispatch(document, ".uno:GoToStartOfPara", nullptr, 300);
    dispatch(document, ".uno:EndOfParaSel", nullptr, 300);
    readAll(document, "paragraph-selected", position.name);
  }

  // ---- Phase 3: does the readback follow a format change? -----------------
  //
  // A postcondition source that cannot see the mutation is worthless no matter
  // how rich it looks, so the same two reads are repeated after each dispatch.
  emit("phase", "\"name\":\"after-dispatch\"");
  const struct {
    const char *label;
    const char *command;
    const char *arguments;
  } steps[] = {
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

  for (const auto &step : steps) {
    positionAtAnchor(document, "bold anchor");
    dispatch(document, step.command, step.arguments, 1200);
    readAll(document, (std::string("after-") + step.label).c_str(),
            "body-paragraph");
    dispatch(document, ".uno:GoToStartOfPara", nullptr, 300);
    dispatch(document, ".uno:EndOfParaSel", nullptr, 300);
    readAll(document, (std::string("after-") + step.label + "-selected").c_str(),
            "body-paragraph");
    const std::string url = "file://" + outDir + "/after-" + step.label + ".odt";
    const bool saved =
        document->pClass->saveAs(document, url.c_str(), "odt", nullptr);
    emit("save", std::string("\"label\":\"") + step.label + "\",\"saved\":" +
                     (saved ? "true" : "false"));
    drain(200);
  }

  emit("complete");
  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
