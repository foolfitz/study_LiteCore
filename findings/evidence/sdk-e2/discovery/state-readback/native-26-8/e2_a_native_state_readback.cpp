// E2-A native state-readback probe.
//
// Question A2: do the documented paragraph-level state callbacks
// (.uno:DefaultBullet, .uno:DefaultNumbering, .uno:StyleApply) actually arrive,
// and what exact strings does StyleApply carry?
//
// E1-A observed that the paragraph/list fixed commands return no
// LOK_CALLBACK_UNO_COMMAND_RESULT, so they had no attributable completion. The
// E2 plan is to use the state callback as the sole completion source instead.
// That plan rests on an inference -- that DefaultBullet/DefaultNumbering/
// StyleApply behave like Bold/Italic because core lists all of them in the same
// closed table (GetKitUnoCommandList, sfx2/source/control/unoctitm.cxx:1165).
// This probe tests that inference against a native build before any of it is
// wired into a completion barrier.
//
// Two phases:
//
//   1. Observation only. The caret is moved between a heading, a plain
//      paragraph and a list item. No mutation at all, so whatever states arrive
//      arrive purely from core's own status broadcasting. This is also where
//      the exact StyleApply strings are captured -- they cannot be guessed,
//      and a wrong guess would silently weaken the barrier.
//
//   2. Mutation. Each of the five fixed commands is dispatched and the document
//      is saved afterwards, so the postcondition can be checked against ODT XML
//      rather than against the callbacks under test. A format command does not
//      change document text, so text length is useless as a validity guard
//      here; the saved files are the guard.
//
// Usage: e2-a-native-state-readback INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR

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

void emit(const char *stage, const std::string &extra = std::string()) {
  std::cout << "{\"stage\":\"" << stage << "\",\"atMs\":" << elapsedMs();
  if (!extra.empty())
    std::cout << ',' << extra;
  std::cout << "}\n";
  std::cout.flush();
}

void onCallback(int type, const char *payload, void *) {
  std::cout << "{\"callback\":" << type << ",\"name\":\""
            << lokCallbackTypeToString(type) << "\",\"atMs\":" << elapsedMs()
            << ",\"payload\":\"" << jsonEscape(payload) << "\"}\n";
  std::cout.flush();
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

void dispatch(LibreOfficeKitDocument *document, const char *command,
              bool notify, int drainMs) {
  emit("dispatch-enter", std::string("\"command\":\"") + command + "\"");
  document->pClass->postUnoCommand(document, command, nullptr, notify);
  drain(drainMs);
  emit("dispatch-return", std::string("\"command\":\"") + command + "\"");
}

// .uno:Heading1ParaStyle and .uno:TextBodyParaStyle are UI aliases, not
// dispatchable slots: WriterCommands.xcu declares them under
// UserInterface/Popups with a TargetURL of
// .uno:StyleApply?Style:string=...&FamilyName:string=ParagraphStyles, and no
// .sdi slot defines them.  Posting the alias name therefore does nothing at
// all.  The dispatchable command is StyleApply (SID_STYLE_APPLY,
// sfx2/sdi/sfx.sdi:4496) with Style and FamilyName arguments.
void dispatchStyle(LibreOfficeKitDocument *document, const char *styleName,
                   int drainMs) {
  const std::string arguments =
      std::string("{\"Style\":{\"type\":\"string\",\"value\":\"") + styleName +
      "\"},\"FamilyName\":{\"type\":\"string\",\"value\":\"ParagraphStyles\"}}";
  emit("dispatch-enter", std::string("\"command\":\".uno:StyleApply\",\"style\":\"") +
                             styleName + "\"");
  document->pClass->postUnoCommand(document, ".uno:StyleApply",
                                   arguments.c_str(), true);
  drain(drainMs);
  emit("dispatch-return",
       std::string("\"command\":\".uno:StyleApply\",\"style\":\"") + styleName +
           "\"");
}

void saveStep(LibreOfficeKitDocument *document, const std::string &outDir,
              const char *label) {
  const std::string url = "file://" + outDir + "/" + label + ".odt";
  const bool saved =
      document->pClass->saveAs(document, url.c_str(), "odt", nullptr);
  emit("save", std::string("\"label\":\"") + label + "\",\"saved\":" +
                   (saved ? "true" : "false"));
  drain(200);
}

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

  // ---- Phase 1: observation only, zero mutation -------------------------
  emit("phase", "\"name\":\"observe\"");

  // styled-list.odt layout: heading, plain paragraph, two list items, tail.
  emit("observe", "\"position\":\"heading\"");
  dispatch(document, ".uno:GoToStartOfDoc", false, 700);

  emit("observe", "\"position\":\"plain-paragraph\"");
  dispatch(document, ".uno:GoDown", false, 700);

  emit("observe", "\"position\":\"list-item\"");
  dispatch(document, ".uno:GoDown", false, 700);

  emit("observe", "\"position\":\"back-to-plain-paragraph\"");
  dispatch(document, ".uno:GoUp", false, 700);

  // ---- Phase 2: mutation, each postcondition saved to ODT ----------------
  emit("phase", "\"name\":\"mutate\"");

  dispatch(document, ".uno:DefaultBullet", true, 1200);
  saveStep(document, outDir, "after-bullet");

  dispatch(document, ".uno:DefaultNumbering", true, 1200);
  saveStep(document, outDir, "after-numbering");

  dispatch(document, ".uno:RemoveBullets", true, 1200);
  saveStep(document, outDir, "after-remove");

  // Both forms are dispatched, in this order, so the run itself shows that the
  // alias is inert and the parameterised command is not -- rather than leaving
  // the alias failure as an inference from the source tree.
  dispatch(document, ".uno:Heading1ParaStyle", true, 1200);
  saveStep(document, outDir, "after-heading-alias");

  dispatchStyle(document, "Heading 1", 1200);
  saveStep(document, outDir, "after-heading");

  dispatchStyle(document, "Text body", 1200);
  saveStep(document, outDir, "after-body");

  emit("complete");
  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
