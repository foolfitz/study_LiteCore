#ifndef WASM_SDK_PROBE_ENGINE_HPP
#define WASM_SDK_PROBE_ENGINE_HPP

#include <cstdint>
#include <string>
#include <vector>

namespace probe {
enum class SubmitStatus : std::int32_t {
  Ok = 0,
  InvalidArgument = 1,
  IncompatibleAbi = 2,
  NotStarted = 3,
  DuplicateRequest = 4,
  RequestNotFound = 5,
  NotCancellable = 6,
  InternalError = 7
};

bool started();
void start();
SubmitStatus start(std::uint32_t requestId);
void open(std::string fileUrl);
SubmitStatus openBytes(std::uint32_t requestId, std::vector<std::uint8_t> bytes,
                       std::string name);
void paintTile(int xTwips, int yTwips, int widthTwips, int heightTwips,
               int canvasWidthPx, int canvasHeightPx);
SubmitStatus paintTile(std::uint32_t requestId, std::uint32_t documentHandle,
                       int xTwips, int yTwips, int widthTwips, int heightTwips,
                       int canvasWidthPx, int canvasHeightPx);
void click(int xTwips, int yTwips);
SubmitStatus click(std::uint32_t requestId, std::uint32_t documentHandle,
                   int xTwips, int yTwips);
void insertText(std::string utf8);
SubmitStatus insertText(std::uint32_t requestId, std::uint32_t documentHandle,
                        std::string utf8);
void key(int type, int charCode, int keyCode);
void save(std::string format);
SubmitStatus save(std::uint32_t requestId, std::uint32_t documentHandle,
                  std::string format);
void close();
SubmitStatus close(std::uint32_t requestId, std::uint32_t documentHandle);
SubmitStatus search(std::uint32_t requestId, std::uint32_t documentHandle,
                    std::string query, bool backward);
SubmitStatus getSelection(std::uint32_t requestId,
                          std::uint32_t documentHandle);
SubmitStatus replaceSelection(std::uint32_t requestId,
                              std::uint32_t documentHandle,
                              std::uint32_t expectedRevision,
                              std::string utf8);
SubmitStatus undo(std::uint32_t requestId, std::uint32_t documentHandle,
                  std::uint32_t expectedRevision);
SubmitStatus redo(std::uint32_t requestId, std::uint32_t documentHandle,
                  std::uint32_t expectedRevision);
SubmitStatus addComment(std::uint32_t requestId,
                        std::uint32_t documentHandle,
                        std::uint32_t expectedRevision, std::string text,
                        std::string author);
SubmitStatus listComments(std::uint32_t requestId,
                          std::uint32_t documentHandle);
SubmitStatus setTrackChanges(std::uint32_t requestId,
                             std::uint32_t documentHandle,
                             std::uint32_t expectedRevision, bool enabled);
SubmitStatus listChanges(std::uint32_t requestId,
                         std::uint32_t documentHandle);
SubmitStatus editorAction(std::uint32_t requestId,
                          std::uint32_t documentHandle,
                          std::uint32_t expectedRevision,
                          std::uint32_t action, bool extendSelection,
                          bool option);
// boundedReadback: complete from a selection readback if the requested range
// changes nothing and core therefore emits no selection callback (SPEC E1-D).
// The product range-select sets it; the diagnostic path does not, so the
// profiles the findings were measured on keep pure callback semantics.
SubmitStatus editorSelect(std::uint32_t requestId,
                          std::uint32_t documentHandle,
                          std::uint32_t method, int startXTwips,
                          int startYTwips, int endXTwips, int endYTwips,
                          bool boundedReadback = false);
// queue-verify-caret-by-block-identity: a click whose reply says where the
// caret went (paragraph fingerprint + offset), instead of a click that replies
// before core has processed it.
SubmitStatus editorPlaceCaret(std::uint32_t requestId,
                              std::uint32_t documentHandle,
                              std::int32_t xTwips, std::int32_t yTwips);

SubmitStatus editorGetState(std::uint32_t requestId,
                            std::uint32_t documentHandle);
#ifdef OXSDK_E2_FORMAT_BARRIER
// The gesture classes, spelled for the engine.  editor_api.h spells the same
// three bits for the ABI; editor_api.cpp sees both headers and static_asserts
// that they agree, so a drift between the public spelling and the routing is a
// compile error rather than a silently mismatched mask.
//
// They live here rather than being included from editor_api.h because the
// dependency runs API -> engine: editor_api.cpp includes probe_engine.hpp, and
// reversing that to reach three constants would tie the engine to the ABI
// header it exists underneath.
constexpr std::uint32_t kGestureCollapsed = 1u;
constexpr std::uint32_t kGestureRangeSingle = 2u;
constexpr std::uint32_t kGestureRangeCross = 4u;

// Restrict one INTERNAL action id to a set of gesture classes (SPEC E2-B 5.7).
// The mask lives here rather than in editor_api.cpp because the engine is what
// routes on gesture -- editor_api sees only an action name and coordinates.
// Narrowing only: the setter intersects, so a mask can withhold a class the
// binary implements but can never grant one it does not.
void editorSetActionGestures(std::uint32_t internalAction,
                             std::uint32_t gestureMask);
bool editorGesturePermitted(std::uint32_t internalAction,
                            std::uint32_t gesture);
#endif
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
SubmitStatus editorDrainScheduler(std::uint32_t requestId,
                                  std::uint32_t documentHandle);
#endif
SubmitStatus cancel(std::uint32_t requestId);

void emitError(const char *where, const std::string &message);
} // namespace probe

#endif
