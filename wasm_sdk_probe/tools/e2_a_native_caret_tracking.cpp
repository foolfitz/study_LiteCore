// Finding 021 decisive experiment: does paragraph format state track the caret
// natively, and does it depend on how the caret was moved?
//
// A2-native reported "the three states update on pure caret movement with no
// mutation".  A2-wasm reported the opposite.  The two runs were not measuring
// the same thing:
//
//   A2-native moved the caret with .uno:GoToStartOfDoc / .uno:GoDown / .uno:GoUp
//   A2-wasm   moved it with .uno:ExecuteSearch + setTextSelection(RESET), and
//             with postMouseEvent clicks
//
// Both dispatch *a* UNO command, so "a dispatch pumps the status cycle" does not
// separate them.  What differs is whether the moving command is itself a cursor
// command that core recomputes cursor-dependent slots for.
//
// This probe runs all three movement methods against the same document and the
// same four paragraphs, on the same core commit the WASM profile is built from,
// so the comparison has exactly one variable.  The caret coordinates are not
// guessed: phase 0 walks the document with cursor commands and records the
// visible-cursor rectangle at each stop, and phases 1 and 2 reuse those measured
// positions.
//
// Usage: e2-a-native-caret-tracking INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR

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
  long x = -1;
  long y = -1;
  long width = 0;
  long height = 0;
  bool valid = false;
};

Rectangle gCaret;

// LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR carries "x, y, width, height" in twips.
bool parseRectangle(const char *payload, Rectangle &out) {
  if (!payload)
    return false;
  long values[4] = {0, 0, 0, 0};
  int parsed = std::sscanf(payload, "%ld, %ld, %ld, %ld", &values[0],
                           &values[1], &values[2], &values[3]);
  if (parsed != 4)
    return false;
  out.x = values[0];
  out.y = values[1];
  out.width = values[2];
  out.height = values[3];
  out.valid = true;
  return true;
}

void emit(const char *stage, const std::string &extra = std::string()) {
  std::cout << "{\"stage\":\"" << stage << "\",\"atMs\":" << elapsedMs();
  if (!extra.empty())
    std::cout << ',' << extra;
  std::cout << "}\n";
  std::cout.flush();
}

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)
    parseRectangle(payload, gCaret);
  std::cout << "{\"callback\":" << type << ",\"name\":\""
            << lokCallbackTypeToString(type) << "\",\"atMs\":" << elapsedMs()
            << ",\"payload\":\"" << jsonEscape(payload) << "\"}\n";
  std::cout.flush();
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

void dispatch(LibreOfficeKitDocument *document, const char *command,
              int drainMs) {
  emit("dispatch", std::string("\"command\":\"") + command + "\"");
  document->pClass->postUnoCommand(document, command, nullptr, false);
  drain(drainMs);
}

std::string positionJson(const char *method, const char *position,
                         const Rectangle &rectangle) {
  std::string json = std::string("\"method\":\"") + method +
                     "\",\"position\":\"" + position + "\"";
  if (rectangle.valid) {
    json += ",\"x\":" + std::to_string(rectangle.x) +
            ",\"y\":" + std::to_string(rectangle.y);
  }
  return json;
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR\n";
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

  // ---- Phase 0: walk with cursor commands, and measure where they land ----
  //
  // This is A2-native's own movement method, so it doubles as the reproduction
  // of the original observation.  styled-list.odt is heading, plain paragraph,
  // two list items, tail.
  const char *const kPositionNames[] = {"heading", "body-paragraph",
                                        "list-item", "list-item-2",
                                        "after-list"};
  std::vector<Rectangle> positions;

  emit("phase", "\"name\":\"cursor-command\"");
  // The caret already sits at the document start after load, so dispatching
  // GoToStartOfDoc first moves nothing, emits no cursor rectangle, and leaves
  // the heading position unmeasured -- which silently dropped the heading from
  // the later phases on the first run.  Step off the position and come back so
  // the move is real and the rectangle is measured rather than assumed.
  dispatch(document, ".uno:GoDown", 700);
  gCaret = Rectangle{};
  emit("observe", positionJson("cursor-command", kPositionNames[0], gCaret));
  dispatch(document, ".uno:GoToStartOfDoc", 900);
  positions.push_back(gCaret);
  emit("measured", positionJson("cursor-command", kPositionNames[0], gCaret));

  for (int index = 1; index < 5; ++index) {
    emit("observe", positionJson("cursor-command", kPositionNames[index], gCaret));
    dispatch(document, ".uno:GoDown", 900);
    positions.push_back(gCaret);
    emit("measured",
         positionJson("cursor-command", kPositionNames[index], gCaret));
  }

  // The four paragraphs the WASM run visited, by index into the walk above.
  const int kVisitOrder[] = {0, 1, 2, 4};

  // ---- Phase 1: setTextSelection(RESET) -- the E1-A discovery path ---------
  emit("phase", "\"name\":\"set-text-selection\"");
  for (int index : kVisitOrder) {
    const Rectangle &target = positions[static_cast<std::size_t>(index)];
    if (!target.valid) {
      emit("skip", positionJson("set-text-selection", kPositionNames[index],
                                target));
      continue;
    }
    emit("observe",
         positionJson("set-text-selection", kPositionNames[index], target));
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       target.x, target.y + target.height / 2);
    drain(900);
    emit("observed",
         positionJson("set-text-selection", kPositionNames[index], target));
  }

  // ---- Phase 2: postMouseEvent click -- the E1-B product path -------------
  emit("phase", "\"name\":\"mouse-click\"");
  for (int index : kVisitOrder) {
    const Rectangle &target = positions[static_cast<std::size_t>(index)];
    if (!target.valid) {
      emit("skip", positionJson("mouse-click", kPositionNames[index], target));
      continue;
    }
    const long y = target.y + target.height / 2;
    emit("observe", positionJson("mouse-click", kPositionNames[index], target));
    document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                     target.x, y, 1, 1, 0);
    document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                     target.x, y, 1, 1, 0);
    drain(900);
    emit("observed", positionJson("mouse-click", kPositionNames[index], target));
  }

  // ---- Phase 3: exactly what the WASM harness did -------------------------
  //
  // Search for the anchor, then setTextSelection at the hit.  Included so the
  // comparison covers the WASM sequence verbatim and not just its components.
  emit("phase", "\"name\":\"search-then-select\"");
  const char *const kAnchors[] = {"E1-STYLED-HEADING", "bold anchor",
                                  "E1-LIST-ONE", "E1-STYLED-END"};
  for (int slot = 0; slot < 4; ++slot) {
    const int index = kVisitOrder[slot];
    const std::string arguments =
        std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                    "\"value\":\"") +
        kAnchors[slot] +
        "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
        "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
    emit("observe",
         positionJson("search-then-select", kPositionNames[index], gCaret));
    document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                     arguments.c_str(), false);
    drain(700);
    const Rectangle hit = gCaret;
    if (hit.valid) {
      document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                         hit.x, hit.y + hit.height / 2);
    }
    drain(900);
    emit("observed",
         positionJson("search-then-select", kPositionNames[index], hit));
  }

  emit("complete");
  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
