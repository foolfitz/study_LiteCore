// Finding 160 on native LOK: does part_text's SelectAll ever go unconfirmed off
// wasm, and when it does, was it dispatched at all?
//
// The engine (probe_engine.cpp, handlePartText -> readPartText) posts
// `.uno:SelectAll` with bNotifyWhenFinished and waits for its
// LOK_CALLBACK_UNO_COMMAND_RESULT.  On ods-viewer-v2 e96e01ec 3 of 1,392 reads
// waited the full 10 s and one read the wrong text, so the selection was never
// made.  Read in the source (desktop/source/lib/init.cxx doc_postUnoCommand ->
// comphelper::dispatchCommand without a frame): the command goes to the
// Desktop's ACTIVE frame; when there is none, nothing is dispatched, no listener
// is called, and LOK records "Failed to dispatch .uno:SelectAll" for getError().
//
// This does the engine's sequence natively, on the same commit (build-native-26-8,
// built from libreoffice-26-8), LOK multi-threaded as on wasm, and records per
// read: confirmed or not, the wait, and getError() right after the post.  Per
// document it first posts a command that does not exist, as the positive
// control that getError() reports a failed dispatch at all.  It judges nothing.
//
// Usage: probe-160-native INSTALL_PATH ROUNDS FILE.ods [FILE.ods ...]
// One JSON object per document per round on stdout.

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <condition_variable>
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
constexpr int kDeadlineMs = 10000; // ods-viewer-v2's
constexpr int kTile = 256;

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
        std::snprintf(buffer, sizeof(buffer), "\\u%04x", static_cast<unsigned char>(*it));
        out += buffer;
      } else {
        out += *it;
      }
    }
  }
  return out;
}

std::string quoted(const char *value) {
  return value ? ("\"" + jsonEscape(value) + "\"") : std::string("null");
}

// The engine's PartTextAwait, with the same rule: a SelectAll result that comes
// while nobody waits is counted as late.
struct Await {
  std::mutex mutex;
  std::condition_variable condition;
  bool active = false;
  bool done = false;
  int late = 0;
  int results = 0; // every SelectAll result seen, for the record
} gAwait;

void onCallback(int type, const char *payload, void *) {
  if (type != LOK_CALLBACK_UNO_COMMAND_RESULT || !payload ||
      std::strstr(payload, "\".uno:SelectAll\"") == nullptr)
    return;
  {
    std::lock_guard<std::mutex> lock(gAwait.mutex);
    ++gAwait.results;
    if (!gAwait.active) {
      ++gAwait.late;
      return;
    }
    gAwait.done = true;
  }
  gAwait.condition.notify_all();
}

std::string takeError(LibreOfficeKit *office) {
  char *error = office->pClass->getError(office);
  std::string out = error ? error : "";
  office->pClass->freeError(error);
  return out;
}

} // namespace

int main(int argc, char **argv) {
  if (argc < 4) {
    std::fprintf(stderr, "usage: %s INSTALL_PATH ROUNDS FILE.ods [FILE.ods ...]\n", argv[0]);
    return 2;
  }
  LibreOfficeKit *office = lok_init_2(argv[1], nullptr);
  if (!office) {
    std::cout << "{\"fatal\":\"lok_init_2 returned null\"}\n";
    return 1;
  }
  const int rounds = std::atoi(argv[2]);
  std::vector<unsigned char> buffer(kTile * kTile * 4);

  for (int round = 1; round <= rounds; ++round) {
    for (int index = 3; index < argc; ++index) {
      const char *path = argv[index];
      const std::string url = std::string("file://") + path;
      std::cout << "{\"round\":" << round << ",\"file\":" << quoted(path);
      LibreOfficeKitDocument *document = office->pClass->documentLoad(office, url.c_str());
      if (!document) {
        std::cout << ",\"loaded\":false,\"error\":" << quoted(takeError(office).c_str()) << "}\n";
        std::cout.flush();
        continue;
      }
      document->pClass->initializeForRendering(document, nullptr);
      document->pClass->registerCallback(document, onCallback, nullptr);
      {
        std::lock_guard<std::mutex> lock(gAwait.mutex);
        gAwait.active = gAwait.done = false;
        gAwait.late = gAwait.results = 0;
      }

      // Positive control: a command nothing provides must be reported failed.
      takeError(office);
      document->pClass->postUnoCommand(document, ".uno:OxsdkNoSuchCommand160", nullptr, true);
      std::cout << ",\"controlError\":" << quoted(takeError(office).c_str());

      const int parts = document->pClass->getParts(document);
      std::cout << ",\"parts\":" << parts << ",\"reads\":[";
      for (int part = 0; part < parts; ++part) {
        // Phase E paints before it reads; so does this.
        document->pClass->paintPartTile(document, buffer.data(), part, 0, kTile, kTile, 0, 0, 3840, 3840);

        // readPartText's order (src/ods_viewer.hpp).
        const int before = document->pClass->getPart(document);
        if (part != before)
          document->pClass->setPart(document, part);
        {
          std::lock_guard<std::mutex> lock(gAwait.mutex);
          gAwait.active = true;
          gAwait.done = false;
        }
        takeError(office);
        const auto started = Clock::now();
        document->pClass->postUnoCommand(document, ".uno:SelectAll", nullptr, true);
        const std::string dispatchError = takeError(office);
        bool confirmed;
        {
          std::unique_lock<std::mutex> lock(gAwait.mutex);
          confirmed = gAwait.condition.wait_for(lock, std::chrono::milliseconds(kDeadlineMs),
                                                [] { return gAwait.done; });
          gAwait.active = false;
        }
        const long waitMs =
            std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - started).count();
        char *used = nullptr;
        char *text = document->pClass->getTextSelection(document, "text/plain;charset=utf-8", &used);
        const size_t length = text ? std::strlen(text) : 0;
        const bool textNull = text == nullptr;
        std::free(text);
        std::free(used);
        document->pClass->resetSelection(document);
        if (document->pClass->getPart(document) != before)
          document->pClass->setPart(document, before);
        int late;
        {
          std::lock_guard<std::mutex> lock(gAwait.mutex);
          late = gAwait.late;
          gAwait.late = 0;
        }
        std::cout << (part ? "," : "") << "{\"part\":" << part << ",\"confirmed\":"
                  << (confirmed ? "true" : "false") << ",\"waitMs\":" << waitMs
                  << ",\"dispatchError\":" << quoted(dispatchError.c_str())
                  << ",\"textLength\":" << length << ",\"textNull\":" << (textNull ? "true" : "false")
                  << ",\"lateBeforeThisReply\":" << late << "}";
      }
      // Anything that arrives after the last read, before the document goes.
      std::this_thread::sleep_for(std::chrono::milliseconds(200));
      int tailLate, results;
      {
        std::lock_guard<std::mutex> lock(gAwait.mutex);
        tailLate = gAwait.late;
        results = gAwait.results;
      }
      std::cout << "],\"lateAfterLastRead\":" << tailLate << ",\"selectAllResults\":" << results << "}\n";
      std::cout.flush();
      document->pClass->destroy(document);
    }
  }
  office->pClass->destroy(office);
  return 0;
}
