// Finding 016 native LOK probe.
//
// Question: when a forward delete removes the character to the right of a
// collapsed caret -- so caret geometry does not move -- does LibreOfficeKit
// emit any documented callback at all?
//
// The e1-editor-discovery WASM profile emits none: the document changes, but
// sourceSequence, documentChangeSequence and the a11y counters are all
// unchanged across the mutation. This probe asks the same question of a
// native stock LibreOffice install, so that a headless/WASM build artefact
// can be told apart from a LibreOfficeKit-wide gap.
//
// Usage: finding-016-native-lok INSTALL_PATH PROFILE_URL DOCUMENT_URL
//
// Every callback is printed as one JSON line with a millisecond timestamp, so
// ordering relative to the dispatched command is visible. No assertion is made
// here; the caller compares the emitted stream against the WASM profile.

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
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

// Bounded wait so late callbacks are still caught -- the whole point of the
// probe. This does NOT pump a main loop: runLoop() requires SAL_LOK_OPTIONS
//=unipoll and never returns, so it cannot be used in a sequential probe. If
// core turns out to need a pumped loop for .uno:Delete to execute at all, the
// validity check below fails and the run must be discarded rather than read as
// "no callbacks were emitted".
void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

// Whole-document text, used only to prove the mutation really happened.
std::string documentText(LibreOfficeKitDocument *document) {
  document->pClass->postUnoCommand(document, ".uno:SelectAll", nullptr, false);
  drain(200);
  char *text = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", nullptr);
  std::string out(text ? text : "");
  if (text)
    std::free(text);
  return out;
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL\n";
    return 64;
  }

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
    const char *error = kit->pClass->getError ? kit->pClass->getError(kit) : nullptr;
    std::cerr << (error ? error : "documentLoad returned null") << '\n';
    kit->pClass->destroy(kit);
    return 3;
  }
  emit("document-load-return");

  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  emit("callback-registered");

  // Render once, so the view is in the same state a tile client would leave it.
  const int canvasWidth = 256;
  const int canvasHeight = 256;
  std::string pixels(static_cast<std::size_t>(canvasWidth) * canvasHeight * 4, '\0');
  document->pClass->paintTile(document, reinterpret_cast<unsigned char *>(pixels.data()),
                              canvasWidth, canvasHeight, 0, 0, 3840, 3840);
  emit("paint-return");
  drain(300);

  const std::string before = documentText(document);
  emit("text-before", std::string("\"length\":") + std::to_string(before.size()));

  // Put the caret at the very start of the body text. This is a caret move, so
  // it is expected to produce cursor callbacks; seeing them confirms the
  // callback channel is alive before the interesting part.
  emit("caret-home-enter");
  document->pClass->postUnoCommand(document, ".uno:GoToStartOfDoc", nullptr, false);
  drain(500);
  emit("caret-home-return");

  emit("delete-forward-enter");
  document->pClass->postUnoCommand(document, ".uno:Delete", nullptr, true);
  drain(1500);
  emit("delete-forward-return");

  const std::string after = documentText(document);
  const bool mutated = after.size() + 1 == before.size();
  emit("text-after", std::string("\"length\":") + std::to_string(after.size())
                         + ",\"mutated\":" + (mutated ? "true" : "false"));

  // A run in which the delete did not land proves nothing about callbacks.
  emit("verdict", std::string("\"valid\":") + (mutated ? "true" : "false")
                      + ",\"note\":\""
                      + (mutated ? "callback stream above is meaningful"
                                 : "DISCARD: delete did not execute, callback "
                                   "absence is not evidence")
                      + "\"");

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  emit("complete");
  return 0;
}
