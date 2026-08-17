// Finding 059: does core accept the parameterised .uno:Bold, or not?
//
// The product build dispatches
//     .uno:Bold  {"Bold":{"type":"boolean","value":true}}
// (probe_engine.cpp, `inlineFormatArgument`, finding 045's fix) and the shipped
// WASM artifact answers LOK_COMMAND_FAILED for bold, italic and underline while
// the list actions -- which use the same parameterised mechanism -- still work.
//
// Finding 045's own note says the parameter form was measured natively and
// worked.  Either that measurement does not describe what the engine now sends,
// or the two platforms differ.  This probe asks the question the same way the
// engine does, on native core, and reports what comes back:
//
//   A  .uno:Bold with {"Bold":{"type":"boolean","value":true}}
//   B  .uno:Bold with no arguments at all      (the pre-045 form)
//   C  .uno:Bold with {"Bold":{"type":"boolean","value":false}}
//   D  .uno:DefaultBullet with {"On":{"type":"boolean","value":true}}
//
// D is the CONTROL and it is the point of the whole probe: it is the same
// parameterised shape on a slot that demonstrably still works in the product.
// If A fails and D succeeds on native too, the difference is this slot's
// argument, not parameters in general -- which is the fork the fix depends on.
//
// The verdict for each arm is core's own LOK_CALLBACK_UNO_COMMAND_RESULT, which
// is exactly what the engine turns into LOK_COMMAND_FAILED.
//
// Usage: f059-native-inline-format INSTALL_PATH PROFILE_URL DOCUMENT_URL OUT_URL

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

std::string gLastUnoResult;
int gUnoResultCount = 0;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT && payload) {
    gLastUnoResult = payload;
    ++gUnoResultCount;
  }
}

void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

void click(LibreOfficeKitDocument *document, long x, long y) {
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                   x, y, 1, 1, 0);
  document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                   x, y, 1, 1, 0);
  drain(600);
}

// One arm.  `arguments` empty means the bare form -- and passing nullptr rather
// than "" matters: an empty STRING is still an argument set to core, and the
// toggle branch is taken only when the set is genuinely absent.
// The uno result is NOT the oracle.  Measured 2026-08-17: the parameterised
// .uno:DefaultBullet -- the shape the product's own barrier uses and which
// demonstrably works -- reports `success: false` while `wasModified` is true.
// So each arm saves the document and the verdict is read out of the bytes,
// which is this tree's standing rule and the reason finding 049 was found.
void typeText(LibreOfficeKitDocument *document, const char *text) {
  for (const char *it = text; *it; ++it) {
    document->pClass->postKeyEvent(document, LOK_KEYEVENT_KEYINPUT,
                                   static_cast<int>(*it), 0);
    drain(120);
  }
  drain(400);
}

// Bold on a COLLAPSED caret changes nothing in the document until something is
// typed -- the attribute is pending.  Measured the hard way: the first version
// of this probe saved straight after dispatching and every arm looked
// identical.  So each arm types its own marker, on its own paragraph, and the
// verdict is which markers come back inside a bold span.
void arm(LibreOfficeKitDocument *document, const char *name,
         const char *command, const char *arguments,
         long clickY, const char *marker) {
  click(document, 2000, clickY);
  gLastUnoResult.clear();
  const int before = gUnoResultCount;
  if (command) {
    document->pClass->postUnoCommand(document, command, arguments,
                                     /*bNotifyWhenFinished=*/true);
    for (int waited = 0; waited < 40 && gUnoResultCount == before; ++waited)
      drain(100);
  }
  typeText(document, marker);
  std::cout << "{\"probe\":\"arm\",\"arm\":\"" << name
            << "\",\"command\":\"" << (command ? command : "(none)")
            << "\",\"arguments\":\"" << jsonEscape(arguments ? arguments : "")
            << "\",\"marker\":\"" << marker
            << "\",\"answered\":" << (gUnoResultCount > before ? "true" : "false")
            << ",\"result\":\"" << jsonEscape(gLastUnoResult.c_str()) << "\"";
  std::cout << "}\n";
  std::cout.flush();
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTPUT_DIR_URL\n";
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

  // A caret inside a paragraph with text in it, which is the situation the
  // product is in when a user presses B.
  click(document, 2000, 1500);

  // argv[4] is a directory the arms save into, so the verdict can be read from
  // the document rather than from the command result.  Each arm saves BEFORE
  // the next one runs, because they share one document and one caret.
  const std::string out = argv[4];
  // Distinct paragraphs so a pending attribute from one arm cannot leak into
  // the next, and a control arm that dispatches nothing at all.
  arm(document, "control-no-command", nullptr, nullptr, 1500, "AAA");
  arm(document, "bold-parameter-true", ".uno:Bold",
      "{\"Bold\":{\"type\":\"boolean\",\"value\":true}}", 1700, "BBB");
  arm(document, "bold-bare", ".uno:Bold", nullptr, 1900, "CCC");
  arm(document, "bold-parameter-false", ".uno:Bold",
      "{\"Bold\":{\"type\":\"boolean\",\"value\":false}}", 2100, "DDD");
  const std::string target = out + "/after-all-arms.odt";
  const bool saved = document->pClass->saveAs(document, target.c_str(), "odt",
                                              nullptr);
  std::cout << "{\"probe\":\"save\",\"savedTo\":\"" << jsonEscape(target.c_str())
            << "\",\"saved\":" << (saved ? "true" : "false") << "}\n";
  std::cout.flush();

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
