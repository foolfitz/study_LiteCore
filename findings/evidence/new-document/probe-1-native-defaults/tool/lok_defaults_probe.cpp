// Scratch probe: load an ODT through LOK (optionally with load options such as
// "Language=zh-TW"), save it as ODT, and print the environment the engine saw.
// Usage: lok_defaults_probe <install-dir> <profile-url> <in-url> <out-path> [options]
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

int main(int argc, char **argv) {
  if (argc < 5) { std::fprintf(stderr, "usage\n"); return 2; }
  const char *install = argv[1], *profile = argv[2], *inUrl = argv[3], *outPath = argv[4];
  const char *options = argc > 5 ? argv[5] : nullptr;
  const char *lang = std::getenv("LANG");
  std::printf("env LANG=%s LC_ALL=%s options=%s\n", lang ? lang : "(unset)",
              std::getenv("LC_ALL") ? std::getenv("LC_ALL") : "(unset)", options ? options : "(none)");
  LibreOfficeKit *kit = lok_init_2(install, profile);
  if (!kit) { std::fprintf(stderr, "lok_init_2 failed\n"); return 1; }
  LibreOfficeKitDocument *doc = nullptr;
  if (options && *options)
    doc = kit->pClass->documentLoadWithOptions(kit, inUrl, options);
  else
    doc = kit->pClass->documentLoad(kit, inUrl);
  if (!doc) {
    char *e = kit->pClass->getError(kit);
    std::fprintf(stderr, "load failed: %s\n", e ? e : "?");
    return 1;
  }
  std::printf("doc type=%d\n", doc->pClass->getDocumentType(doc));
  std::string outUrl = std::string("file://") + outPath;
  if (!doc->pClass->saveAs(doc, outUrl.c_str(), "odt", nullptr)) {
    char *e = kit->pClass->getError(kit);
    std::fprintf(stderr, "saveAs failed: %s\n", e ? e : "?");
    return 1;
  }
  std::printf("saved %s\n", outPath);
  doc->pClass->destroy(doc);
  kit->pClass->destroy(kit);
  return 0;
}
