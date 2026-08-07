// Minimal module for the finding 023 session-depth ladder.  It links with the
// exact resource shape of the real engine (-pthread -sTOTAL_MEMORY=1GB
// -sPTHREAD_POOL_SIZE=7, see link_r5_product in the Makefile) but contains no
// LibreOffice code at all.  If repeated navigations of THIS module wedge at the
// same fixed depth as the full engine, the exhausted budget belongs to the
// emscripten runtime or the browser, not to LibreOffice initialisation.

#include <atomic>
#include <thread>

extern "C" int oxsdk_minimal_ping() {
  // Touch one pthread from the preloaded pool so the rung proves the pool is
  // live, not merely allocated.
  std::atomic<int> value{0};
  std::thread worker([&value] { value.store(42, std::memory_order_seq_cst); });
  worker.join();
  return value.load(std::memory_order_seq_cst);
}
