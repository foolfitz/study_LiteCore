// Finding 048, native arm: WHY does a click take 22-28 ms to take effect?
//
// The product's remedy is already in and does not depend on this answer --
// `EditorSession.placeCaret` now waits for the engine to acknowledge the click
// rather than for a predicate that was already true.  What is still open is the
// mechanism, and 048 names two hypotheses whose product remedies differ:
//
//   A  the mouse event is queued and core processes it late   -> wait for the engine
//   B  core moves the caret promptly and the cursor callback
//      arrives late                                           -> wait for the callback
//
// Native separates them because nothing here crosses a worker, a postMessage
// boundary or a browser event loop.  Nothing this probe produces describes the
// WASM artifact -- the rule finding 016 and finding 045 both ran under.
//
// The two derived numbers per arm, both computed OFFLINE by
// tools/analyze_f048_native.py from absolute timestamps emitted here:
//
//   firstCallbackMs  post -> the first callback of any type in this arm's window
//                    ("when did core start telling anyone anything")
//   cursorRectMs     post -> LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR carrying a
//                    rectangle on the requested line (what placeCaret waits for)
//
// If those two are the same number, the cursor callback is not the laggard and
// hypothesis B is out.  This probe judges nothing; it emits JSONL and stops.
//
// Coordinates are MEASURED, not guessed: phase 0 walks the document with cursor
// commands and records the visible-cursor rectangle at each stop.  An arm aimed
// at a guessed coordinate measures nothing, which is how the first WASM run of
// D3 came to score eight cells that all acted on paragraph one.
//
// Usage: f048-native-click-latency INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR
//        [ANCHOR,ANCHOR,...]   -- searched for only if the cursor-command walk
//                                  measures fewer than two distinct lines

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
const auto gStarted = Clock::now();

// Callbacks arrive on core's thread while main() is draining, so every write to
// stdout is serialised.  Interleaved JSONL is not a smaller problem than no
// JSONL: it is the same problem, discovered later.
std::mutex gOutput;

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

void emit(const std::string &body) {
  std::lock_guard<std::mutex> guard(gOutput);
  std::cout << '{' << body << ",\"atMs\":" << elapsedMs() << "}\n";
  std::cout.flush();
}

void stage(const char *name, const std::string &extra = std::string()) {
  emit(std::string("\"stage\":\"") + name + "\"" +
       (extra.empty() ? std::string() : "," + extra));
}

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)
    parseRectangle(payload, gCaret);
  emit(std::string("\"callback\":") + std::to_string(type) + ",\"name\":\"" +
       lokCallbackTypeToString(type) + "\",\"payload\":\"" +
       jsonEscape(payload) + "\"");
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

// One arm repetition.  The window the analyzer measures in is
// [event=post, event=drain-end]; both ends are emitted here so the offline
// judge never has to infer a boundary.
void armEvent(const char *arm, int rep, const char *event, const char *kind,
              long targetX, long targetY, const std::string &extra = {}) {
  std::string body = std::string("\"arm\":\"") + arm + "\",\"rep\":" +
                     std::to_string(rep) + ",\"event\":\"" + event +
                     "\",\"kind\":\"" + kind + "\",\"targetX\":" +
                     std::to_string(targetX) + ",\"targetY\":" +
                     std::to_string(targetY);
  if (!extra.empty())
    body += "," + extra;
  emit(body);
}

const int kDrainMs = 900;

} // namespace

int main(int argc, char **argv) {
  if (argc != 5 && argc != 6) {
    std::cerr << "expected INSTALL_PATH PROFILE_URL DOCUMENT_URL OUTDIR "
                 "[ANCHOR,ANCHOR,...]\n";
    return 64;
  }

  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  stage("kit-init-enter");
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }
  stage("kit-init-return");

  stage("document-load-enter");
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    const char *error =
        kit->pClass->getError ? kit->pClass->getError(kit) : nullptr;
    std::cerr << (error ? error : "documentLoad returned null") << '\n';
    kit->pClass->destroy(kit);
    return 3;
  }
  stage("document-load-return");

  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  stage("callback-registered");

  // The product page paints before the user can click, so the probe paints too.
  // The D3 caret arms controlled for this separately (`paint=page`) and it made
  // no difference there; here it is simply the product's starting state.
  const int kCanvas = 256;
  std::string pixels(static_cast<std::size_t>(kCanvas) * kCanvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              kCanvas, kCanvas, 0, 0, 3840, 3840);
  stage("paint-return");
  drain(500);

  // ---- Phase 0: measure where the paragraphs are --------------------------
  //
  // The caret is already at the document start after load, so GoToStartOfDoc
  // would move nothing, emit no rectangle, and leave stop 0 unmeasured.  Step
  // off and come back, the way e2_a_native_caret_tracking.cpp had to.
  stage("phase", "\"name\":\"walk\"");
  std::vector<Rectangle> stops;
  document->pClass->postUnoCommand(document, ".uno:GoDown", nullptr, false);
  drain(700);
  gCaret = Rectangle{};
  document->pClass->postUnoCommand(document, ".uno:GoToStartOfDoc", nullptr,
                                   false);
  drain(900);
  stops.push_back(gCaret);
  stage("walk-stop", "\"index\":0,\"y\":" + std::to_string(gCaret.y));

  const int kWalkStops = 11;
  for (int index = 1; index < kWalkStops; ++index) {
    document->pClass->postUnoCommand(document, ".uno:GoDown", nullptr, false);
    drain(700);
    stops.push_back(gCaret);
    stage("walk-stop", "\"index\":" + std::to_string(index) + ",\"y\":" +
                           std::to_string(gCaret.y));
  }

  // ---- Phase 0b: the fallback, and why it exists -------------------------
  //
  // MEASURED, not assumed: on list-contexts.odt the GoDown walk above produces
  // STATE_CHANGED for every command and NOT ONE
  // LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR, while the same walk on
  // styled-list.odt produces 23 (both on this install, 2026-08-16).  The
  // document D3 measured 22-28 ms on is the silent one, so the choice is
  // between changing the fixture -- a second variable -- and finding another
  // way to MEASURE the coordinates in the fixture that matters.
  //
  // ExecuteSearch is the other way: the rectangle comes back from core, so the
  // coordinates are still measured rather than guessed.  It leaves a selection
  // rather than a collapsed caret, which is why N1's click runs before
  // anything is inferred from the caret's state.
  if (argc >= 6) {
    int distinct = 0;
    for (const Rectangle &stop : stops)
      if (stop.valid)
        ++distinct;
    if (distinct < 2) {
      stage("phase", "\"name\":\"walk-fallback-search\"");
      std::string anchors(argv[5]);
      std::size_t start = 0;
      while (start <= anchors.size()) {
        const std::size_t comma = anchors.find(',', start);
        const std::string anchor = anchors.substr(
            start, comma == std::string::npos ? std::string::npos
                                              : comma - start);
        start = comma == std::string::npos ? anchors.size() + 1 : comma + 1;
        if (anchor.empty())
          continue;
        const std::string arguments =
            std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                        "\"value\":\"") +
            anchor +
            "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
            "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
        gCaret = Rectangle{};
        document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                         arguments.c_str(), false);
        drain(900);
        stops.push_back(gCaret);
        stage("walk-stop", "\"anchor\":\"" + anchor + "\",\"y\":" +
                               std::to_string(gCaret.y) + ",\"via\":\"search\"");
      }
    }
  }

  // Two stops that are genuinely on different lines.  A click that lands where
  // the caret already is measures N3, not N2, and picking the targets by index
  // alone would silently turn one arm into the other on a document whose
  // paragraphs wrap differently than assumed.
  Rectangle a{}, b{};
  for (const Rectangle &stop : stops) {
    if (!stop.valid)
      continue;
    if (!a.valid) {
      a = stop;
      continue;
    }
    if (std::abs(stop.y - a.y) > stop.height) {
      b = stop;
      break;
    }
  }
  if (!a.valid || !b.valid) {
    stage("abort", "\"why\":\"walk did not measure two distinct lines\"");
    document->pClass->destroy(document);
    kit->pClass->destroy(kit);
    return 4;
  }
  stage("targets", "\"aY\":" + std::to_string(a.y) + ",\"bY\":" +
                       std::to_string(b.y) + ",\"aX\":" +
                       std::to_string(a.x) + ",\"bX\":" + std::to_string(b.x));

  auto clickAt = [&](const char *arm, int rep, const Rectangle &target) {
    const long y = target.y + target.height / 2;
    armEvent(arm, rep, "post", "mouse", target.x, y);
    document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN,
                                     target.x, y, 1, 1, 0);
    document->pClass->postMouseEvent(document, LOK_MOUSEEVENT_MOUSEBUTTONUP,
                                     target.x, y, 1, 1, 0);
    drain(kDrainMs);
    armEvent(arm, rep, "drain-end", "mouse", target.x, y);
  };

  // ---- N1: the cold click -------------------------------------------------
  //
  // One repetition by construction: there is exactly one first click per
  // process.  Three executions of the probe give three cold samples.
  stage("phase", "\"name\":\"N1 click-cold\"");
  clickAt("N1", 1, b);

  // ---- N2: warm clicks, alternating so every click really moves -----------
  stage("phase", "\"name\":\"N2 click-warm\"");
  for (int rep = 1; rep <= 5; ++rep)
    clickAt("N2", rep, (rep % 2) ? a : b);

  // ---- N3: clicking where the caret already is ----------------------------
  //
  // 048 records that the engine says nothing here, and the product's 400 ms
  // quiet rule rests on that.  A rule resting on an unmeasured claim is the
  // shape this whole finding is about.
  stage("phase", "\"name\":\"N3 click-same\"");
  // N2's last repetition (rep 5, odd) clicked `a`, so that is where the caret
  // is now.  Stated rather than recomputed: this arm is only N3 if the target
  // is the position already held, and the analyzer re-checks it from the
  // recorded rectangles rather than trusting this comment.
  const Rectangle &settled = a;
  for (int rep = 1; rep <= 5; ++rep)
    clickAt("N3", rep, settled);

  // ---- N4: a cursor command instead of a mouse event ----------------------
  //
  // Same queue, different entry point.  If this is as slow as N2, the latency
  // is not specific to mouse events and "the mouse path is special" is out.
  stage("phase", "\"name\":\"N4 uno-godown\"");
  for (int rep = 1; rep <= 5; ++rep) {
    const char *command = (rep % 2) ? ".uno:GoDown" : ".uno:GoUp";
    armEvent("N4", rep, "post", "uno", -1, -1,
             std::string("\"command\":\"") + command + "\"");
    document->pClass->postUnoCommand(document, command, nullptr, false);
    drain(kDrainMs);
    armEvent("N4", rep, "drain-end", "uno", -1, -1);
  }

  // ---- N5: setTextSelection(RESET), the harness's gesture -----------------
  //
  // The zero-width selectRange appeared to land synchronously in the browser,
  // which is why D3's first rounds used it.  SPEC E2-C 9.5.6 measured that the
  // gesture changes the engine's own classification, so its latency is worth
  // having next to the click's rather than assumed equal.
  stage("phase", "\"name\":\"N5 set-text-selection\"");
  for (int rep = 1; rep <= 5; ++rep) {
    const Rectangle &target = (rep % 2) ? b : a;
    const long y = target.y + target.height / 2;
    armEvent("N5", rep, "post", "select", target.x, y);
    document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                       target.x, y);
    drain(kDrainMs);
    armEvent("N5", rep, "drain-end", "select", target.x, y);
  }

  stage("complete");
  document->pClass->destroy(document);
  kit->pClass->destroy(kit);
  return 0;
}
