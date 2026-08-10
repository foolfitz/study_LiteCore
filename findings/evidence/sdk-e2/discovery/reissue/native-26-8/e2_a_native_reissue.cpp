// E2-A native re-issue probe.
//
// Product route C (2026-08-06) removed the precondition read: a closed action
// dispatches unconditionally and only the postcondition is believed.  That
// deletes `documented-state-noop`, and with it the only thing that used to stop
// a second press from reaching core.  So route C rests on an assumption the
// bold/italic comment states outright -- "dispatching unconditionally is
// idempotent for these commands" -- which has never been measured for the five
// paragraph-level commands.  If any of them is really a toggle, the closed enum
// `set-list(none|unordered|ordered)` inverts on the second press, which is the
// opposite of what SPEC E2-000 section 140 promises.
//
// Native first, same reason as A2: a WASM-only answer cannot separate "core
// toggles" from "our engine dispatched twice by accident".
//
// Method: for each of the five actions, put the paragraph into the *opposite*
// state first, so issue 1 is a real change, then dispatch the same action three
// more times without ever reading state.  Every step is saved to ODT, because
// the callbacks under test are exactly what must not be trusted as evidence
// here.  Three issues rather than two: two can only say "issue 2 differs", three
// separate a toggle (issue 3 back at issue 1) from a one-way collapse.
//
// Usage: e2-a-native-reissue INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
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
  std::cout << "{\"callback\":" << type << ",\"name\":\""
            << lokCallbackTypeToString(type) << "\",\"atMs\":" << elapsedMs()
            << ",\"payload\":\"" << jsonEscape(payload) << "\"}\n";
  std::cout.flush();
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

std::string styleArguments(const char *styleName) {
  return std::string("{\"Style\":{\"type\":\"string\",\"value\":\"") +
         styleName +
         "\"},\"FamilyName\":{\"type\":\"string\",\"value\":"
         "\"ParagraphStyles\"}}";
}

// A step is one dispatch plus the ODT that shows what it did.  The label names
// the file, so the analyzer never has to infer which snapshot belongs to which
// press.
void step(LibreOfficeKitDocument *document, const std::string &outDir,
          const std::string &label, const char *command, const char *arguments) {
  emit("dispatch-enter",
       std::string("\"label\":\"") + label + "\",\"command\":\"" + command +
           "\",\"arguments\":\"" + jsonEscape(arguments) + "\"");
  document->pClass->postUnoCommand(document, command, arguments, true);
  drain(1200);
  const std::string url = "file://" + outDir + "/" + label + ".odt";
  const bool saved =
      document->pClass->saveAs(document, url.c_str(), "odt", nullptr);
  emit("save", std::string("\"label\":\"") + label + "\",\"saved\":" +
                   (saved ? "true" : "false"));
  drain(200);
}

// Positioning by search, not by GoDown.  Applying a heading style changes the
// paragraph's height and wrapping a paragraph into a list changes its indent,
// so a line-relative walk stops meaning the same thing partway through a run --
// and it would fail silently, by formatting a paragraph nobody asked about.
// The anchor text is unaffected by any of the five commands.
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
  emit("positioned", std::string("\"anchor\":\"") + anchor + "\",\"valid\":" +
                         (hit.valid ? "true" : "false"));
}

// FN_NUM_BULLET_ON and FN_NUM_NUMBERING_ON both declare an `On` boolean
// parameter (svx/sdi/svx.sdi:2251 and :4985, FN_PARAM_1) and
// sw/source/uibase/shells/txtnum.cxx:81-108 uses it as an explicit mode when
// present, falling back to `!SelectionHasBullet()` -- a toggle -- when it is
// absent.  Dispatching the bare command therefore asks for the opposite of
// whatever is there, which is not what a closed `set-list(...)` enum means.
// The parameterised form is measured here rather than assumed correct; this is
// the same shape as finding 019, where the fix was also to send the documented
// parameterised command instead of the convenient one.
std::string onArguments(bool on) {
  return std::string("{\"On\":{\"type\":\"boolean\",\"value\":") +
         (on ? "true" : "false") + "}}";
}

struct Case {
  const char *group;
  const char *name;
  // The opposite state, so issue 1 is a real change rather than a no-op that
  // would make every command look idempotent.
  const char *resetCommand;
  const char *resetArguments;
  const char *command;
  const char *arguments;
};

} // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR\n";
    return 64;
  }
  const std::string outDir = argv[4];

  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  emit("kit-init-enter");
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }
  emit("kit-init-return");

  emit("document-load-enter");
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    const char *error =
        kit->pClass->getError ? kit->pClass->getError(kit) : nullptr;
    std::cerr << (error ? error : "documentLoad returned null") << '\n';
    kit->pClass->destroy(kit);
    return 3;
  }
  emit("document-load-return");

  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  emit("callback-registered");

  const int canvasWidth = 256;
  const int canvasHeight = 256;
  std::string pixels(
      static_cast<std::size_t>(canvasWidth) * canvasHeight * 4, '\0');
  document->pClass->paintTile(
      document, reinterpret_cast<unsigned char *>(pixels.data()), canvasWidth,
      canvasHeight, 0, 0, 3840, 3840);
  emit("paint-return");
  drain(500);

  const std::string bodyStyle = styleArguments("Text body");
  const std::string headingStyle = styleArguments("Heading 1");

  const std::string onTrue = onArguments(true);

  const Case cases[] = {
      // Group `bare`: the form the E2 engine dispatches today.
      {"bare", "set-list-unordered", ".uno:RemoveBullets", nullptr,
       ".uno:DefaultBullet", nullptr},
      {"bare", "set-list-ordered", ".uno:RemoveBullets", nullptr,
       ".uno:DefaultNumbering", nullptr},
      {"bare", "set-list-none", ".uno:DefaultBullet", nullptr,
       ".uno:RemoveBullets", nullptr},
      {"bare", "set-paragraph-heading", ".uno:StyleApply", bodyStyle.c_str(),
       ".uno:StyleApply", headingStyle.c_str()},
      {"bare", "set-paragraph-body", ".uno:StyleApply", headingStyle.c_str(),
       ".uno:StyleApply", bodyStyle.c_str()},
      // Group `param`: the documented explicit-mode form.  The last two cases
      // start from the *other* list kind rather than from no list, because a
      // three-state closed enum has to be able to cross between them, and a
      // reset-to-none start would never exercise that.
      {"param", "set-list-unordered", ".uno:RemoveBullets", nullptr,
       ".uno:DefaultBullet", onTrue.c_str()},
      {"param", "set-list-ordered", ".uno:RemoveBullets", nullptr,
       ".uno:DefaultNumbering", onTrue.c_str()},
      {"param", "set-list-unordered-from-ordered", ".uno:DefaultNumbering",
       onTrue.c_str(), ".uno:DefaultBullet", onTrue.c_str()},
      {"param", "set-list-none-from-ordered", ".uno:DefaultNumbering",
       onTrue.c_str(), ".uno:RemoveBullets", nullptr},
  };

  const char *const kAnchor = "bold anchor";

  // The analyzer reads this rather than carrying its own copy of the case list.
  // Two hand-maintained copies of the same table is how a case gets added here
  // and silently never judged.
  {
    std::ofstream manifest(outDir + "/cases.json");
    manifest << "{\"anchor\":\"" << kAnchor << "\",\"steps\":[\"reset\","
                "\"issue1\",\"issue2\",\"issue3\"],\"cases\":[";
    bool first = true;
    for (const Case &item : cases) {
      if (!first)
        manifest << ',';
      first = false;
      manifest << "{\"group\":\"" << item.group << "\",\"name\":\"" << item.name
               << "\",\"command\":\"" << item.command << "\",\"arguments\":\""
               << jsonEscape(item.arguments) << "\",\"reset\":\""
               << item.resetCommand << "\",\"resetArguments\":\""
               << jsonEscape(item.resetArguments) << "\"}";
    }
    manifest << "]}\n";
  }

  for (const Case &item : cases) {
    std::filesystem::create_directories(outDir + "/" + item.group);
    emit("case", std::string("\"group\":\"") + item.group + "\",\"name\":\"" +
                     item.name + "\"");

    const std::string prefix = std::string(item.group) + "/" + item.name;

    positionAtAnchor(document, kAnchor);
    step(document, outDir, prefix + "-reset", item.resetCommand,
         item.resetArguments);

    for (int issue = 1; issue <= 3; ++issue) {
      positionAtAnchor(document, kAnchor);
      step(document, outDir, prefix + "-issue" + std::to_string(issue),
           item.command, item.arguments);
    }
  }

  emit("complete");
  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
