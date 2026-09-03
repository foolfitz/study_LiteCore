// The native oracle for the ODS corpus.
//
// `handoff/PLAN-2026-09-03-ods-reading.md`, work item W4.  Criterion G3 compares
// what the WASM candidate reports for each sheet against an expectation.  For
// the synthetic fixtures the expectation comes from the generator that placed
// the cells; for the ~300 upstream fixtures there is no generator, so it comes
// from here.
//
// WHY LOK AND NOT UNO.  The candidate will produce its per-sheet text with
// `.uno:SelectAll` followed by `getTextSelection("text/plain")`.  An oracle
// built on UNO's text interfaces would answer the same QUESTION through a
// different API, and every formatting difference between the two -- column
// separators, number formatting, trailing rows -- would arrive as a G3 failure
// about the product.  This uses the same two calls on the same commit, so a
// difference is a difference in the engine and not in the question.
//
// WHY build-native-26-8 AND NOT native-lok-26-8.  The latter is built from a
// different commit than `libreoffice-26-8`, so it would be an oracle for a
// codebase the candidate is not built from.  The runner passes the install path
// explicitly and records the commit beside the output.
//
// It reports, per document: whether it loaded, the document type, the part
// count, every part's name, the document size, and per part the plain-text
// selection of everything.  It asserts nothing -- the judging is done by the
// sweep against the manifest.  A probe that also judged would make its own
// failures look like the product's.
//
// Usage: ods-native-oracle INSTALL_PATH FILE.ods [FILE.ods ...]
// Emits one JSON object per line on stdout.

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

std::string quoted(const char *value) {
  return value ? ("\"" + jsonEscape(value) + "\"") : std::string("null");
}

// A path, not a URL, is what the caller passes; LOK wants a URL.
std::string fileUrl(const char *path) {
  std::string out = "file://";
  out += path;
  return out;
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

} // namespace

int main(int argc, char **argv) {
  if (argc < 3) {
    std::fprintf(stderr,
                 "usage: %s INSTALL_PATH FILE.ods [FILE.ods ...]\n", argv[0]);
    return 2;
  }
  const char *install = argv[1];

  LibreOfficeKit *office = lok_init_2(install, nullptr);
  if (!office) {
    std::cout << "{\"fatal\":\"lok_init_2 returned null\",\"install\":"
              << quoted(install) << "}\n";
    return 1;
  }

  for (int index = 2; index < argc; ++index) {
    const char *path = argv[index];
    const std::string url = fileUrl(path);
    const auto started = Clock::now();

    std::cout << "{\"file\":" << quoted(path);

    LibreOfficeKitDocument *document =
        office->pClass->documentLoad(office, url.c_str());
    if (!document) {
      char *error = office->pClass->getError(office);
      std::cout << ",\"loaded\":false,\"error\":" << quoted(error) << "}\n";
      std::cout.flush();
      continue;
    }

    // The engine needs a view before selections mean anything.
    document->pClass->initializeForRendering(document, nullptr);
    drain(50);

    const int type = document->pClass->getDocumentType(document);
    const int parts = document->pClass->getParts(document);
    long width = 0, height = 0;
    document->pClass->getDocumentSize(document, &width, &height);

    std::cout << ",\"loaded\":true,\"documentType\":" << type
              << ",\"parts\":" << parts
              << ",\"documentWidth\":" << width
              << ",\"documentHeight\":" << height
              << ",\"sheets\":[";

    for (int part = 0; part < parts; ++part) {
      document->pClass->setPart(document, part);
      drain(20);
      char *name = document->pClass->getPartName(document, part);
      document->pClass->postUnoCommand(document, ".uno:SelectAll", nullptr,
                                       false);
      drain(60);
      char *used = nullptr;
      char *text = document->pClass->getTextSelection(document, "text/plain;charset=utf-8",
                                                      &used);
      if (part)
        std::cout << ',';
      std::cout << "{\"part\":" << part << ",\"name\":" << quoted(name)
                << ",\"usedMimeType\":" << quoted(used)
                << ",\"text\":" << quoted(text) << "}";
      std::free(name);
      std::free(text);
      std::free(used);
    }

    const double ms =
        std::chrono::duration<double, std::milli>(Clock::now() - started)
            .count();
    std::cout << "],\"loadAndReadMs\":" << ms << "}\n";
    std::cout.flush();
    document->pClass->destroy(document);
  }

  office->pClass->destroy(office);
  return 0;
}
