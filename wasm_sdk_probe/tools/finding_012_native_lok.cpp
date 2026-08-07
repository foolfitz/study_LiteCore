#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdlib>
#include <iostream>
#include <string>

namespace {

using Clock = std::chrono::steady_clock;
const auto gStarted = Clock::now();

void emit(const char *stage) {
  const auto elapsed = std::chrono::duration<double, std::milli>(Clock::now() - gStarted).count();
  std::cout << "{\"stage\":\"" << stage << "\",\"atMs\":" << elapsed << "}\n";
  std::cout.flush();
}

void emitError(const std::string &message) {
  std::cerr << "finding-012 native LOK probe: " << message << '\n';
  std::cerr.flush();
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    emitError("expected INSTALL_PATH PROFILE_URL DOCUMENT_URL");
    return 64;
  }

  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  emit("kit-init-enter");
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    emitError("lok_init_2 returned null");
    return 2;
  }
  emit("kit-init-return");

  emit("document-load-enter");
  LibreOfficeKitDocument *document = kit->pClass->documentLoad(kit, argv[3]);
  if (!document) {
    const char *error = kit->pClass->getError ? kit->pClass->getError(kit) : nullptr;
    emitError(error ? error : "documentLoad returned null");
    kit->pClass->destroy(kit);
    return 3;
  }
  emit("document-load-return");

  emit("document-destroy-enter");
  document->pClass->destroy(document);
  emit("document-destroy-return");

  kit->pClass->destroy(kit);
  emit("complete");
  return 0;
}
