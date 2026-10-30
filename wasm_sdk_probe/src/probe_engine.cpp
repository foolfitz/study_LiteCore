#ifndef LOK_USE_UNSTABLE_API
#define LOK_USE_UNSTABLE_API
#endif

#include "probe_engine.hpp"

#ifdef OXSDK_E2_FORMAT_BARRIER
#include "format_readback_text.hpp"
#include "a11y_paragraph_identity.hpp"
#ifdef OXSDK_MERGE_KEY_UNDO
// SPEC-M3-paragraph-merge 3.1 item 10: option B's deadlines are wired into the
// blocking engineLoop only, and B rides on the selection barrier.  A build
// that combines them otherwise must fail here, not wait silently in front of
// the user.
#if defined(OXSDK_MAINLOOP_ENGINE) && !defined(OXSDK_E2_V23_LINK_BATCH)
#error "OXSDK_MERGE_KEY_UNDO is not wired into OXSDK_MAINLOOP_ENGINE"
#endif
#ifndef OXSDK_FINDING_016_SELECTION_BARRIER
#error "OXSDK_MERGE_KEY_UNDO requires OXSDK_FINDING_016_SELECTION_BARRIER"
#endif
#include "merge_key_undo.hpp"
#endif
#endif
#ifdef OXSDK_E2_V23_LINK_BATCH
#if !defined(OXSDK_MAINLOOP_ENGINE) || !defined(OXSDK_E2_V21_LINK_BATCH)
#error "OXSDK_E2_V23_LINK_BATCH requires MAINLOOP_ENGINE and v21's transitive defines"
#endif
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
#error "ordered commands must not pump the scheduler inside a command"
#endif
#include "ordered_poll.hpp"
#include "ordered_engine_guards.hpp"
#include "ordered_command_proof.hpp"
#include "ordered_delete_route.hpp"
#include "reply_state_reads.hpp"
#include <functional>
#include <map>
#endif
#if defined(OXSDK_E2_V23_DIAGNOSTIC) && !defined(OXSDK_E2_V23_LINK_BATCH)
#error "OXSDK_E2_V23_DIAGNOSTIC requires the ordered engine"
#endif
#ifdef OXSDK_E2_V21_LINK_BATCH
// SPEC-M3-link-batch-v21: everything this batch adds -- move-document-start/
// -end (finding 142) and the Markdown paste -- sits on v20's machinery (the
// key path, the merge's `.uno:Undo` reader, the barriers' busy gates), so the
// define is meaningless without v20's.  Fail here rather than link a v21 that
// silently lacks a piece.
#if !defined(OXSDK_E2_V20_LINK_BATCH) || !defined(OXSDK_MERGE_KEY_UNDO) ||     \
    !defined(OXSDK_E2_FORMAT_BARRIER) || !defined(OXSDK_EDITOR_DISCOVERY)
#error "OXSDK_E2_V21_LINK_BATCH requires v20's defines (OXSDK_E2_V20_LINK_BATCH, OXSDK_MERGE_KEY_UNDO, OXSDK_E2_FORMAT_BARRIER, OXSDK_EDITOR_DISCOVERY)"
#endif
// The pure half of the paste: md4c's scan, the byte rules, the collapsed rule
// and the post-dispatch judge (tests/markdown_paste_model_test.cpp).  It
// includes <md4c.h> from the core's unpacked tarball (-I on the v21 rule
// only); md_parse itself is the core's, from libmd4c.a in the link.
#include "markdown_paste.hpp"
// osl_getThreadTextEncoding(): the pasted bytes are decoded with the thread's
// encoding (vcl transfer.cxx:1517), so a non-UTF-8 one is refused (10.4).
#include <osl/thread.h>
#endif
#ifdef OXSDK_ODS_VIEWER
// SPEC-M4-ods-in-nextcloud §3.2: the read-only spreadsheet viewer.  The reader
// rule's shape plus this define, and nothing of the editor's -- no actions, no
// barriers, no v20/v21 batch -- so the shape is a compile error to get wrong.
#if !defined(OXSDK_READER_PROFILE) || defined(OXSDK_EDITOR_DISCOVERY) ||       \
    defined(OXSDK_E2_FORMAT_BARRIER) || defined(OXSDK_E2_V20_LINK_BATCH) ||    \
    defined(OXSDK_E2_V21_LINK_BATCH) || defined(OXSDK_MAINLOOP_ENGINE) ||      \
    defined(OXSDK_MERGE_KEY_UNDO) || defined(OXSDK_FINDING_016_SELECTION_BARRIER)
#error "OXSDK_ODS_VIEWER is the reader rule's shape: OXSDK_READER_PROFILE and none of the editor's defines"
#endif
// The pure half: which names are accepted, the document type's spelling, the
// part range and part_text's order (tests/ods_viewer_test.cpp).
#include "ods_viewer.hpp"
#endif
#if defined(OXSDK_ODS_VIEWER_V2) && !defined(OXSDK_ODS_VIEWER)
#error "OXSDK_ODS_VIEWER_V2 is added to the viewer's shape, never used alone"
#endif
#include "sdk_api.h"
#ifdef OXSDK_ODS_EDITOR
#include "calc_cell_bridge.h"
#if !defined(OXSDK_ODS_VIEWER_V2)
#error "OXSDK_ODS_EDITOR requires the v2 spreadsheet engine shape"
#endif
#endif
#ifdef OXSDK_EDITOR_DISCOVERY
#include "editor_discovery_api.h"
#endif

/*
 * queue-engine-must-report-core-lacks-accessibility.
 *
 * The core build's own generated configuration, on the include path already
 * (`-I$(LOBUILD)/config_host`).  It is read here so the engine can say
 * `core-built-without-accessibility` instead of reporting `enabled: true` for a
 * mechanism this build compiled out -- a capability failure wearing the costume
 * of data, which is the shape finding 056 spent a round on.
 *
 * Measured, not assumed: the WASM build's copy says
 * `ENABLE_WASM_STRIP_ACCESSIBILITY 1` and the native build's says `0`, which is
 * why the same source answers differently on the two and why this has to be a
 * compile-time question rather than a LOK capability probe.
 */
#include <config_wasm_strip.h>

#ifdef OXSDK_A11Y_TREE_PROBE
// Defined in src/a11y_tree_probe.cpp, the ONLY translation unit built with
// -DLIBO_INTERNAL_ONLY.  Declared rather than included so this file keeps
// seeing core through the PUBLIC headers, which is the whole reason that file
// is separate.
extern "C" char *oxsdk_a11y_tree_snapshot();
#endif
#ifdef OXSDK_A11Y_OUTLINE
// The PRODUCT half of the same file.  Guarded separately from the probe: the
// diagnostic dump must never ship, and this must, so they cannot share a flag.
extern "C" char *oxsdk_a11y_document_outline();
#endif

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#ifdef OXSDK_EDITOR_DISCOVERY
#include <com/sun/star/awt/Key.hpp>
#endif
#include <com/sun/star/uno/Exception.hpp>
#include <emscripten.h>
#include <emscripten/heap.h>
#include <rtl/string.hxx>

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>

#ifdef OXSDK_E2_FORMAT_BARRIER
#include <algorithm>
#endif
#include <atomic>
#include <cctype>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cxxabi.h>
#include <deque>
#include <fstream>
#include <limits>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <typeinfo>
#include <unordered_set>
#include <utility>
#include <vector>
#ifdef OXSDK_MAINLOOP_ENGINE
#include <emscripten/eventloop.h>
#include <memory>
#include <pthread.h>
#include <stdexcept>
#endif

extern "C" LibreOfficeKit *libreofficekit_hook_2(const char *installPath,
                                                 const char *userProfileUrl);
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
extern "C" void unit_lok_process_events_to_idle();

// Finding 021 design input.  Under __EMSCRIPTEN__ the svp instance constructor
// sets m_bUseSystemLoop unconditionally (vcl/headless/svpinst.cxx:103), which
// makes Application::Reschedule() return false without doing anything
// (vcl/source/app/svapp.cxx:400-406) and Application::Yield() abort.  The
// intended pump is then the emscripten main loop that Application::Execute()
// starts -- and this probe never calls it.  Reading that off the source is not
// enough: if the flag were false here, Reschedule would be the right fix, and
// if it is true, Reschedule is a fix that silently does nothing.  So measure it.
//
// vcl/svapp.hxx cannot be included from here -- it needs the core's own internal
// build defines, which this out-of-tree probe does not compile with.  Declaring
// the two static members is enough: the mangled names depend only on the global
// class name and the signatures, so this binds to the real VCL symbols and the
// strict-undefined-symbol link would fail loudly if it did not.
class Application {
public:
  static bool IsUseSystemEventLoop();
  static bool Reschedule(bool allEvents);
#ifdef OXSDK_MAINLOOP_ENGINE
  // Combined mainloop+drain profile (finding 021 discriminating experiment):
  // the loop entry lives in the same declaration so both flags can coexist.
  static void Execute();
#endif
};
#endif
#if defined(OXSDK_MAINLOOP_ENGINE) && !defined(OXSDK_FINDING_016_SCHEDULER_PROBE)
// Same out-of-tree binding technique as above: vcl/svapp.hxx is not
// includable here, and declaring the static member binds to the real VCL
// symbol by mangled name under the strict-undefined-symbol link.
// Application::Execute is the upstream entry that installs the emscripten
// main loop for the headless backend (DoExecute,
// vcl/headless/svpinst.cxx:315).
class Application {
public:
  static void Execute();
};
#endif
#ifdef OXSDK_MAINLOOP_ENGINE
// Diagnostic only.  WARNING (measured 2026-08-06): this is useless at the
// call site below.  The probe samples only when timeoutUs != 0, which implies
// ImplYield's CheckTimeout() returned false, i.e. the sal timer has not
// expired -- and GetMostUrgentTaskPriority() returns -1 for exactly that
// condition (its nTime < mnTimerStart + mnTimerPeriod - 1 guard, plus the
// InfiniteTimeoutMs guard when no timer is armed).  So it can only ever print
// -1, whether or not work is scheduled.  Any future use must sample outside
// ImplYield (e.g. around command dispatch).
class Scheduler {
public:
  static int GetMostUrgentTaskPriority();
};
#endif

namespace probe {
namespace {
constexpr std::uint32_t ProtocolSchemaVersion = 1;

enum class CommandType {
  EmitReady,
#ifdef OXSDK_E2_V23_DIAGNOSTIC
  DiagnosticNeverReturn,
  DiagnosticMissingProof,
  DiagnosticHtml,
  DiagnosticKey,
#endif
  OpenUrl,
  OpenBytes,
  PaintTile,
  Click,
  InsertText,
  Search,
  GetSelection,
#ifdef OXSDK_ODS_EDITOR
  Cell,
#endif
  ReplaceSelection,
  Undo,
  // Redo is a SIBLING OF UNDO, not an editor action with a wire id.
  //
  // The engine has dispatched `.uno:Redo` through the editor-action path since
  // the discovery ABI, but that path is the narrow editor's allowlist and redo
  // does not belong in it: undo is not in it either. Undo reached the product
  // as a document operation, and redo is the same kind of thing -- so it costs
  // a compiled export and ZERO wire ids, and a caller that has undo already
  // knows the shape.
  Redo,
  AddComment,
  ListComments,
  SetTrackChanges,
  ListChanges,
#ifdef OXSDK_ODS_VIEWER
  // SPEC-M4-ods-in-nextcloud §3.2: the viewer's document-level queries,
  // siblings of GetSelection -- no wire id, no gesture.
  SetPart,
  CurrentPart,
  PartName,
  PartText,
#ifdef OXSDK_ODS_VIEWER_V2
  // SPEC-M4-viewer-v2 3.1 (finding 157).
  PartInfo,
#endif
#endif
#ifdef OXSDK_E2_V20_LINK_BATCH
  // SPEC-M3-link-batch 10.8 (S-11): a document-level QUERY, the sibling of
  // GetSelection, never an editor action -- no wire id, no gesture, so
  // kMaxExternalAction and kMaxInternalEditorAction do not move.
  PageRectangles,
#endif
#ifdef OXSDK_E2_V21_LINK_BATCH
  // SPEC-M3-link-batch-v21 4.2: paste as Markdown, a document-level export
  // like PageRectangles and insert-text -- no wire id, no gesture.
  PasteMarkdown,
#endif
#ifdef OXSDK_E2_V24_TYPED_INSERT
  // SPEC-M3-link-batch-v24 4.1: typed text through .uno:InsertText, the
  // sibling of InsertText -- a document-level export, no wire id, no gesture.
  InsertTypedText,
#endif
#ifdef OXSDK_EDITOR_DISCOVERY
  EditorAction,
  // FINDING 096.  The key path's own deadline step, and it is a THIRD kind
  // rather than a reuse of EditorSelectReadback: that one completes an
  // operation whose answer is a selection, and a move's answer is neither a
  // selection nor a click.  Sharing the enumerator would have meant sharing
  // completePendingEditorSelectByReadback's guard, which refuses anything that
  // is not `selection || caret` -- so the step would have fired, answered
  // nothing, and been re-synthesised for ever because the deadline stays in
  // the past.  A busy loop instead of a wedge is not an improvement.
#ifndef OXSDK_E2_V23_LINK_BATCH
  EditorActionReadback,
#endif
  EditorSelect,
#ifndef OXSDK_E2_V23_LINK_BATCH
  EditorSelectReadback,
#endif
  EditorPlaceCaret,
#ifndef OXSDK_E2_V23_LINK_BATCH
  EditorPlaceCaretReadback,
#endif
  EditorGetState,
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
#ifndef OXSDK_E2_V23_LINK_BATCH
  EditorSelectionBarrierStep,
#endif
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
#ifndef OXSDK_E2_V23_LINK_BATCH
  EditorFormatBarrierStep,
#endif
#endif
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
  EditorDrainScheduler,
#endif
#endif
  Key,
  Save,
  Close
};

struct Command {
  CommandType type;
  bool sdk = false;
  std::uint32_t requestId = 0;
  std::uint32_t documentHandle = 0;
  std::string text;
  std::string name;
  std::vector<std::uint8_t> bytes;
  std::uint32_t expectedRevision = 0;
  std::uint64_t correlation = 0;
  int values[6] = {0, 0, 0, 0, 0, 0};
};

struct EngineState {
  std::mutex mutex;
  std::condition_variable condition;
  std::deque<Command> commands;
  std::unordered_set<std::uint32_t> pendingRequests;
  std::unordered_set<std::uint32_t> cancelledRequests;
  std::unordered_set<std::uint32_t> asynchronousRequests;
  std::uint32_t executingRequest = 0;
  LibreOfficeKit *kit = nullptr;
  LibreOfficeKitDocument *document = nullptr;
  std::uint32_t nextDocumentHandle = 1;
  std::uint32_t documentHandle = 0;
  std::uint32_t revision = 0;
  // The document's size as of the last time anything looked (finding 062).
  // Written at open and refreshed on every paint, so a client can be told that
  // the page count moved under it -- which until 2026-08-19 nothing could,
  // because getDocumentSize was called once and never again.
  long documentWidthTwips = 0;
  long documentHeightTwips = 0;
};

EngineState gState;
std::atomic<bool> gStarted{false};
std::atomic<std::uint32_t> gCallbackDocumentHandle{0};
std::atomic<std::uint32_t> gCallbackRevision{0};
std::atomic<std::uint32_t> gOpenRequestId{0};
std::atomic<std::uint32_t> gSearchRequestId{0};
std::atomic<std::uint32_t> gUnoRequestId{0};
std::string gSearchQuery;
std::string gUnoOperation;
const char *gStage = "not-started";

#ifdef OXSDK_MAINLOOP_ENGINE
// Finding 021 candidate 1: this profile has no blocking engine command loop.
// After LOK init the engine thread enters the upstream emscripten main loop
// through the public LOK runLoop API -- the unipoll mechanism the Collabora
// Online kit runs in production (cool kit/Kit.cpp startMainLoop) -- and
// commands are dispatched from the poll callback that
// SvpSalInstance::ImplYield invokes.  The VCL scheduler is therefore pumped
// between any two commands by Application::Execute's emscripten main-loop
// tick, which is what the idle-driven LOK status updates needed and what the
// unit_lok_process_events_to_idle() hook was standing in for in the
// e2-scheduler-attribution profile.  That hook is not linked here.
//
// ImplYield reaches the poll callback with a non-zero timeout only on a pass
// that dispatched no user event and fired no expired scheduler task: the
// scheduler is idle.  Idle-poll entry therefore carries the meaning the
// return of Scheduler::ProcessEventsToIdle carried in the discovery profile:
// core has recomputed everything it was going to, so a format cache that
// received no watched payload since the caret moved is a cache whose value
// did not change, not one that was never refreshed.
struct MainLoopState {
  // Total poll-callback entries, and the subset entered with the scheduler
  // idle.  Exposed in the typed state so the host's bounded freshness wait is
  // judged from evidence rather than asserted.
  std::atomic<std::uint64_t> pollCount{0};
  std::atomic<std::uint64_t> idlePollCount{0};
  // Set by the VCL wake callback (SvpSalInstance::Wakeup) to interrupt a
  // blocked poll so a timer armed by another thread is serviced.  Guarded by
  // gState.mutex.
  bool wakeRequested = false;
};
MainLoopState gMainLoop;
#endif

#ifdef OXSDK_EDITOR_DISCOVERY
struct EditorRect {
  bool available = false;
  int x = 0;
  int y = 0;
  int width = 0;
  int height = 0;
};

struct EditorState {
  std::uint64_t sourceSequence = 0;
  std::uint64_t documentChangeSequence = 0;
#ifdef OXSDK_E2_V20_LINK_BATCH
  // SPEC-M3-link-batch 10.8 / 12.3 (ruling 3 condition 21).  Every
  // LOK_CALLBACK_DOCUMENT_SIZE_CHANGED, counted on ARRIVAL -- not on a payload
  // change, and not only when the parsed size differs from the last one.  It
  // is the page number's re-read trigger: typing emits no INVALIDATE_TILES on
  // this engine (ruling 2 F2), so `documentChangeSequence` would never move
  // for a page added by typing, while this callback was measured 1.2-1.8 ms
  // after the edit with the rectangles already current
  // (findings/evidence/link-batch/page-rectangles/).
  std::uint64_t documentSizeChangedCount = 0;
#endif
  bool cursorVisible = true;
  EditorRect caret;
  EditorRect selectionStart;
  EditorRect selectionEnd;
  std::vector<EditorRect> selectionRectangles;
  // False until LOK_CALLBACK_TEXT_SELECTION has been seen at least once. An
  // empty rectangle list means "no selection" only once this is true;
  // before that it merely means core has not reported a selection yet.
  bool selectionObserved = false;
  // Finding 016 gate. LOK_CALLBACK_A11Y_FOCUS_CHANGED is emitted only when the
  // focused paragraph's text actually differs (sfx2/source/view/viewsh.cxx
  // updateParagraphInfo, `if (m_sFocusedParagraph != sText)`), so its arrival
  // is an authoritative statement that content changed -- unlike caret or
  // selection callbacks, which also fire when nothing changed. Recorded as
  // closed typed counters; the raw payload is never forwarded to JS.
  bool a11yObserved = false;
  std::uint64_t a11yChangeCount = 0;
  std::uint64_t a11yUnparsedCount = 0;
  std::uint64_t a11yLastSequence = 0;
  int a11yContentLength = -1;
  int a11yPosition = -1;
  // The caret paragraph's fingerprint and list prefix, kept for the same reason
  // the length is kept: so the barrier can ask whether a readback describes the
  // paragraph the action was dispatched on (finding 046), and so a host can ask
  // whether a click moved the caret to a different paragraph without receiving
  // any of the document's text.
  std::uint64_t a11yContentHash = 0;
  // FINDING 082.  Whether `a11yContentHash` may be COMPARED, which is a
  // different question from `a11yParagraphFresh` (did the last read succeed).
  // False when the reported list prefix consumed the whole paragraph, because
  // the hashed body is then empty and the value distinguishes nothing --
  // finding 074's shape, measured on a heading and on a paragraph holding only
  // a bullet, which report the same number.
  bool a11yFingerprintUsable = false;
  int a11yListPrefixLength = 0;
  // Did the LAST synchronous read succeed?  Distinct from `a11yObserved` (a
  // callback fired at some point) and from `enabled` (accessibility was
  // switched on once).  Neither of those answers "is the fingerprint below
  // describing where the caret is now".
  bool a11yParagraphFresh = false;
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
  // Cleared wherever the fingerprint is cleared, never left standing: a stale
  // paragraph read aloud is worse than silence, and it is the same rule the
  // fingerprint already obeys one field up.
  std::string a11yParagraphText;
#endif
  bool boldKnown = false;
  bool bold = false;
  bool italicKnown = false;
  bool italic = false;
#ifdef OXSDK_E2_FORMAT_BARRIER
  // E2-A paragraph-level state.  These come from the same closed core table as
  // Bold/Italic (GetKitUnoCommandList, sfx2/source/control/unoctitm.cxx:1165):
  // DefaultBullet and DefaultNumbering are IsActivePayload, StyleApply is
  // StyleApplyPayload.  The style name is data, not a command, and is never
  // fed back to core -- it is recorded so E2-A can freeze the observed set.
  //
  // Guarded, so that the frozen e1-editor-discovery and e1-editor-v1 profiles
  // keep the exact state shape E1-C validated.  Adding fields here unguarded
  // silently changes what those profiles emit.
  // Finding 059.  Underline and Strikeout ARE in core's GetKitUnoCommandList
  // (unoctitm.cxx:1165ff) and both were measured broadcasting -- at document
  // load, with values, alongside Bold and Italic
  // (findings/evidence/059/native/negative-arm/).  The comment further down
  // that said otherwise was wrong, and it was the reason no cache was kept.
  //
  // Inside the barrier guard on purpose: boldKnown/italicKnown are unguarded
  // and E1-C validated the frozen e1-editor profiles at a specific WASM hash,
  // so a field added beside them changes what those profiles emit.
  bool underlineKnown = false;
  bool underline = false;
  bool strikeoutKnown = false;
  bool strikeout = false;
  bool listBulletKnown = false;
  bool listBullet = false;
  bool listNumberKnown = false;
  bool listNumber = false;
  bool paragraphStyleKnown = false;
  std::string paragraphStyle;
  // Finding 021: every STATE_CHANGED that reaches this build, and the subset
  // whose payload matched none of the commands in the closed table.  Counts
  // only; payloads are never forwarded.
  std::uint64_t stateChangedTotal = 0;
  std::uint64_t stateChangedUnrecognised = 0;
  // Set when the caret moves, cleared when a watched payload arrives.  True
  // means the cached values belong to a paragraph the caret has since left.
  bool formatStateStale = true;
#endif
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
  // Finding 016 diagnostic only.  These are typed aggregates from the
  // documented state-changed callback; the raw payload never crosses the ABI.
  std::uint64_t stateChangedCount = 0;
  std::uint64_t wordCountUpdateCount = 0;
  int wordCountWords = -1;
  int wordCountCharacters = -1;
#endif
};

struct EditorPendingOperation {
  std::uint32_t requestId = 0;
  std::uint32_t documentHandle = 0;
  std::uint32_t beforeRevision = 0;
  std::uint64_t beforeSequence = 0;
  int requiredCallback = -1;
  bool mutation = false;
  bool selection = false;
  bool option = false;
  // A click whose ANSWER is where the caret ended up.  See handleEditorPlaceCaret.
  bool caret = false;
  std::string name;
  // SPEC E1-D.  A range that selects nothing when nothing was selected before
  // changes no state, so core emits no LOK_CALLBACK_TEXT_SELECTION and waiting
  // for one wedges the operation for good -- the finding 018 shape.  Only the
  // *product* range-select arms this: the diagnostic profiles keep the pure
  // callback semantics the findings were measured against.
  //
  // The deadline never declares success.  When it fires the selection is read
  // back and whatever is actually there is reported, including "nothing".
  bool readbackDeadlineArmed = false;
  std::chrono::steady_clock::time_point readbackDeadline{};
};

constexpr int EditorSelectReadbackDeadlineMs = 250;

// The same 250, chosen for its own reason rather than because it is nearby.
// A click takes 22-28 ms to take effect on this engine (finding 048, measured
// both browsers), so this is an order of magnitude above the thing it bounds --
// the same ratio the select deadline has to its own operation.  It is a floor
// on the answer for the ONE case that produces no callback at all: a click on
// the point the caret already occupies, where core emits nothing because
// nothing changed.
constexpr int EditorPlaceCaretDeadlineMs = 250;

// FINDING 096, and the third path that needed what the two above already had.
//
// THE NUMBER IS THE SIBLINGS' NUMBER, and it is here for its own reason rather
// than because it is nearby -- the same sentence EditorPlaceCaretDeadlineMs was
// given, and it is owed the same arithmetic.
//
//   * 250 comes from EditorSelectReadbackDeadlineMs, which is an order of
//     magnitude above the 22-28 ms a click takes to take effect (finding 048,
//     both browsers).
//   * What THIS one bounds was measured on this exact path and not borrowed:
//     the press one BEFORE the boundary produces LOK_CALLBACK_INVALIDATE_
//     VISIBLE_CURSOR and completes in 37-39 ms, 20 of 20 attempts, on two
//     different engines (findings/evidence/096/RESULT-engine-side.md section
//     2).  250 is 6.4x the top of that band, not the siblings' ~10x, and that
//     ratio is written down rather than rounded away: a press slower than
//     250 ms is answered from the readback instead of from the callback, which
//     reports where the caret ACTUALLY is at the deadline and never claims a
//     move happened.  The late callback then arrives with gEditorPending
//     cleared and still updates gEditorState, so the caret the host draws
//     catches up through the ordinary editor-state announcement.
//
// What it costs to have no deadline here is measured too: 40 of 40 attempts,
// four artifacts including the shipping bytes, the press wedges the engine for
// the life of the worker, every later action answers BUSY, and 30 s later the
// SDK gives up and the page shows the no-checkpoint notice.
constexpr int EditorMoveReadbackDeadlineMs = 250;

struct SelectionReadback {
  int type = LOK_SELTYPE_NONE;
  std::string text;
  bool textMissing = false;
};

#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
enum class SelectionBarrierStage {
  Idle,
  AwaitingUnitSelection,
  UnitVerificationQueued,
  AwaitingDeleteCompletion,
  FinalVerificationQueued,
#ifdef OXSDK_MERGE_KEY_UNDO
  // Option B, the E shape (SPEC-M3-paragraph-merge 16.2).  Each stage waits
  // for one proof from the callback stream.  The LOK thread only feeds
  // gMergeAttribution and queues a step; these stages are written by the
  // engine thread alone (review S1: a stage written from both threads could
  // be resurrected after a reset and wedge every command as BUSY).
  MergeAwaitingCollapse1,     // .uno:Escape #1 sent
  MergeAwaitingReturn,        // K2 posted
  MergeAwaitingCollapse2,     // .uno:Escape #2 sent
  MergeAwaitingKey,           // the user's key posted: payload must change
#endif
};

enum class SelectionBarrierAck {
  Pending,
  MatchedSuccess,
  Mismatch,
  Failed,
};

struct SelectionBarrierTransaction {
  SelectionBarrierStage stage = SelectionBarrierStage::Idle;
  std::uint32_t requestId = 0;
  std::uint32_t documentHandle = 0;
  std::uint32_t beforeRevision = 0;
  std::uint64_t transactionSerial = 0;
  std::uint64_t beforeSequence = 0;
  std::uint64_t preselectionSequence = 0;
  std::uint64_t dispatchSequence = 0;
  std::uint64_t collapseSequence = 0;
  std::uint64_t acknowledgementSequence = 0;
  bool backward = false;
  bool acknowledgementSeen = false;
  bool collapseCallbackSeen = false;
  SelectionBarrierAck acknowledgement = SelectionBarrierAck::Pending;
  std::string action;
  std::string command;
  std::string selectedText;
  std::vector<std::uint32_t> selectedCodePoints;
  std::chrono::steady_clock::time_point boundaryDeadline;
#ifdef OXSDK_MERGE_KEY_UNDO
  bool mergeKey = false;
  bool pStartRead = false;     // .uno:Undo read before K1 (10.1(f))
  std::string pStart;
  std::string p0;              // .uno:Undo read right before the key
  bool keyPosted = false;
  std::chrono::steady_clock::time_point keyPostedAt;
  bool stageDeadlineArmed = false;
  std::chrono::steady_clock::time_point stageDeadline;
#endif
#ifdef OXSDK_E2_V20_LINK_BATCH
  // SPEC-M3-link-batch 4.5(2) as refined by 10.6: the engine's cached caret
  // and its sourceSequence at the moment the barrier started, carried on
  // every refusal as `caretBefore`.  DATA ONLY in this link: nothing in the
  // engine reads it back.
  EditorRect caretBefore;
  std::uint64_t caretBeforeSequence = 0;
  // 10.5, C's window.  False until the first 250 ms NONE; true while the
  // transaction waits one more MergeStepDeadlineMs for K1's TEXT_SELECTION.
  bool boundaryNoopWindow = false;
  // When K1 was posted; `boundaryNoop.waitedMs` is measured from here.
  std::chrono::steady_clock::time_point startedAt;
#endif
};

SelectionBarrierTransaction gSelectionBarrier;
#if defined(OXSDK_MERGE_KEY_UNDO) && !defined(OXSDK_E2_V23_LINK_BATCH)
// Fed on the LOK thread (onLokCallback), told about our sends on the engine
// thread.  13.2 holds for this mutex too: nothing under it calls LOK or emits.
std::mutex gMergeMutex;
probe::merge::Attribution gMergeAttribution;
// What the LOK thread may know about the running transaction, under
// gMergeMutex: enough to address a step to it, nothing it could write back.
struct MergeTicket {
  bool active = false;
  std::uint64_t serial = 0;
  std::uint32_t requestId = 0;
  std::uint32_t documentHandle = 0;
  bool afterKey = false;    // the key is posted: any callback asks for a re-read
  bool stepPending = false; // a step is queued and the engine has not taken it
};
MergeTicket gMergeTicket;
constexpr int MergeStepDeadlineMs = 2000;
// Finding 117: the key stage alone also re-reads .uno:Undo on this period.
constexpr int MergeKeyPollMs = 15;
#endif
constexpr int SelectionBarrierBoundaryDeadlineMs = 250;
std::uint64_t gNextSelectionBarrierSerial = 1;
#endif

#ifdef OXSDK_E2_FORMAT_BARRIER
// E2-A verified-format-state barrier.
//
// E1-A inherited the claim that these commands emit no
// LOK_CALLBACK_UNO_COMMAND_RESULT.  Measuring natively on 2026-08-05 refuted it:
// four of the five dispatch forms do return a result, and the two real defects
// are that the paragraph-style names E1-A posted were UI aliases with no slot
// (finding 019) and that the result's success/wasModified fields contradict the
// document (finding 020).
//
// So neither source is sufficient alone.  The command result carries
// commandName, the only thing tying an outcome to this request; the state
// callback is the only thing that reports what the document actually became.
// Completion requires both, and the result's verdict fields are recorded but
// never believed.  The barrier still refuses to run unless the pre-state is
// known, which keeps "already in the target state" distinguishable from "the
// callback never arrived" -- the property Finding 016 showed we cannot fake.
enum class FormatBarrierTarget {
  None,
  ListBullet,
  ListNumber,
  ListNone,
  ParagraphStyle,
};

// Route C, revised 2026-08-11 after finding 030.
//
// The state broadcast cannot serve as the postcondition: core stays silent
// when the value did not change, so a repeated press -- the case route C
// created by dropping the precondition read -- is indistinguishable from a
// command that never arrived.  The postcondition is therefore read out of the
// document, measured feasible in SPEC E2-A section 2.8.
//
// A collapsed caret reads back nothing at all, so the read has to select the
// paragraph and put the caret back afterwards.  That is a visible side effect,
// which is why restoring is a stage with its own confirmation rather than a
// fire-and-forget call: "we posted a restore" is not "the selection is
// collapsed again".
enum class FormatBarrierStage {
  Idle,
  // Dispatched; waiting for the command result that attributes an outcome to
  // this request.  The result is still the only thing carrying commandName.
  AwaitingResult,
  // Result seen; a step is queued to select the paragraph off the callback
  // thread, the same non-reentrancy rule the selection barrier follows.
  SelectQueued,
  // Paragraph selection posted; waiting for the selection callback that says
  // there is something to read.
  AwaitingSelection,
  // Selection confirmed; a step is queued to do the read and compare.
  ReadQueued,
  // Read done; caret restore posted, waiting for the collapse to be confirmed.
  AwaitingRestore,
};

// The structural set, and every member of it was measured at body level rather
// than listed from imagination (M2, evidence paragraph-content/native-26-8/,
// 21 paragraph shapes).  The previous set was ul/ol/li/h1/p, which was measured
// against three fixtures whose paragraphs happen to carry no character
// formatting -- finding 035.
//
// h7 and above are deliberately absent: HTML has no such tags, and ODF outline
// levels 7-10 were measured to serialise as a plain <p>.  A level-7 heading is
// therefore indistinguishable from body text here, the same narrowing that
// already applies to Title and Subtitle.
bool formatTagIsStructural(const std::string &tag) {
  return tag == "p" || tag == "h1" || tag == "h2" || tag == "h3" ||
         tag == "h4" || tag == "h5" || tag == "h6" || tag == "pre" ||
         tag == "blockquote" || tag == "ul" || tag == "ol" || tag == "li";
}

// Membership and counting are one decision, not two.  A structural tag that did
// not contribute to blockCount would let a selection that ran into a <pre>
// neighbour read as a single block and walk straight past finding 034's guard.
// ul/ol stay containers and li is counted separately, as before.
bool formatTagIsBlock(const std::string &tag) {
  return tag == "p" || tag == "h1" || tag == "h2" || tag == "h3" ||
         tag == "h4" || tag == "h5" || tag == "h6" || tag == "pre" ||
         tag == "blockquote";
}

// No void-tag table here on purpose.  Void tags are all non-structural, so they
// are already ignored inside an open block and already fail closed outside one;
// a separate list would be a second place to keep correct for no gain.

// Reads the open-tag sequence inside <body>, which is all the postcondition
// needs and far less than parsing HTML.
//
// Two values, not one: taking only the first tag would conflate list
// membership with paragraph style, so a heading inside a list would read as
// "ul" and the paragraph-style postcondition could never be satisfied there.
// The list kind and the block tag are separate questions and are answered
// separately.
struct FormatReadback {
  bool parsed = false;
  bool unknownTag = false;
  // Which tag stopped the scan.  "we refused" cannot answer "refused what"
  // without this, and that question is the whole point of a fail-closed set.
  std::string unknownTagName;
  // A structural close tag met at depth 0: the markup is not shaped the way
  // every measured sample is shaped.  Kept apart from unknownTag because the
  // two say different things about what went wrong.
  bool malformedNesting = false;
  // Finding 035 / M2.  A paragraph carrying a footnote or endnote serialises as
  // TWO body-level blocks: the paragraph, then <div id="sdfootnoteN"> holding
  // the note body.  Either way the read is refused, but it is refused for a
  // reason we measured, so it gets its own channel instead of flooding the two
  // that exist to report a cross-paragraph read and a genuinely unmeasured tag.
  bool footnoteApparatus = false;
  std::string listTag;   // "ul", "ol", or empty
  std::string blockTag;  // the first block-level structural tag, or empty
  // Finding 034.  The select step can cover more than one paragraph -- measured
  // on an empty paragraph mid-document, where the selection spans it and the
  // paragraph after it (native 26.8, selecttext-result/, and the same shape
  // through the old GoToStartOfPara pair).  The tag scan above answers with the
  // *first* block tag it meets, so a two-paragraph read is reported as if it
  // described one paragraph, and whichever verdict follows is a verdict about
  // an unknown mixture.  Counted here so the barrier can refuse instead.
  std::uint32_t blockCount = 0;  // block-level structural tags
  std::uint32_t itemCount = 0;   // <li>
  bool multiBlock = false;
#ifdef OXSDK_E2_V28_LAST_BLOCK
  // SPEC-M3-v28-last-line-fallback 4.1 item 2.  The LAST block-level tag and
  // the innermost list still open when it opened ("" = none).  Read only by
  // the fallback's predicate; the first-block fields above are unchanged.
  std::string lastListTag;
  std::string lastBlockTag;
#endif
};

// The footnote/endnote container, recognised from what the writer actually
// emits rather than from the shape of the markup.  sw/source/filter/html/
// htmlftn.cxx:344-365 writes <div id="sdfootnoteN"> for footnotes and
// "sdendnoteN" for endnotes, where N is a plain incrementing counter -- a
// literal and an integer, with no container iteration and no locale in the
// path, so this is stable by construction rather than by having been seen once.
//
// Reading the id is required, not fastidious: the same writer emits <div> from
// at least seven other places (fly frames, paragraph attributes, sections and
// multi-column, tables), so treating any body-level div as note apparatus would
// mislabel six of them.
bool formatDivIsFootnoteApparatus(const std::string &attributes) {
  const std::size_t id = attributes.find("id=\"");
  if (id == std::string::npos)
    return false;
  const std::size_t value = id + 4;
  return attributes.compare(value, 10, "sdfootnote") == 0 ||
         attributes.compare(value, 9, "sdendnote") == 0;
}

FormatReadback parseFormatReadback(const std::string &html) {
  FormatReadback readback;
  const std::size_t body = html.find("<body");
  if (body == std::string::npos)
    return readback;
  std::size_t index = html.find('>', body);
  if (index == std::string::npos)
    return readback;
  // Structural nesting depth.  Only structural tags move it, and only
  // non-structural tags are filtered by it.  A structural tag is recognised and
  // counted at EVERY depth: <li> is never at body level, and the <p> inside a
  // list item never is either, so a rule that ignored everything inside an open
  // block would zero itemCount and blockCount and take finding 034's
  // multi-block guard down with them.
  int depth = 0;
  bool first = true;
#ifdef OXSDK_E2_V28_LAST_BLOCK
  // The structural tags `depth` counts, innermost last (4.1 item 3).
  std::vector<std::string> open;
#endif
  for (++index; index < html.size(); ++index) {
    if (html[index] != '<')
      continue;
    std::size_t start = index + 1;
    if (start >= html.size())
      break;
    const bool closing = html[start] == '/';
    if (closing)
      ++start;
    std::size_t end = start;
    while (end < html.size() &&
           ((html[end] >= 'a' && html[end] <= 'z') ||
            (html[end] >= 'A' && html[end] <= 'Z') ||
            (html[end] >= '0' && html[end] <= '9')))
      ++end;
    // No tag name: <!-- a comment --> or <!DOCTYPE ...>.  A comment is what the
    // serialiser writes for an annotation, measured in M2, so this path is
    // reached by an ordinary document and must not be a refusal.
    if (end == start)
      continue;
    std::string tag = html.substr(start, end - start);
    for (char &character : tag)
      if (character >= 'A' && character <= 'Z')
        character = static_cast<char>(character - 'A' + 'a');
    const std::size_t bracket = html.find('>', end);
    const std::string attributes =
        bracket == std::string::npos ? std::string()
                                     : html.substr(end, bracket - end);
    const bool selfClosing = !attributes.empty() && attributes.back() == '/';
    index = (bracket == std::string::npos ? end : bracket) - 1;

    if (formatTagIsStructural(tag)) {
      readback.parsed = true;
      if (closing) {
        if (depth == 0) {
          readback.malformedNesting = true;
          break;
        }
        --depth;
#ifdef OXSDK_E2_V28_LAST_BLOCK
        if (!open.empty())
          open.pop_back();
#endif
        continue;
      }
      if (first) {
        first = false;
        if (tag == "ul" || tag == "ol")
          readback.listTag = tag;
      }
      if (formatTagIsBlock(tag)) {
        ++readback.blockCount;
        if (readback.blockTag.empty())
          readback.blockTag = tag;
#ifdef OXSDK_E2_V28_LAST_BLOCK
        readback.lastBlockTag = tag;
        readback.lastListTag.clear();
        for (auto inner = open.rbegin(); inner != open.rend(); ++inner)
          if (*inner == "ul" || *inner == "ol") {
            readback.lastListTag = *inner;
            break;
          }
#endif
      } else if (tag == "li") {
        ++readback.itemCount;
      }
      if (!selfClosing)
        ++depth;
#ifdef OXSDK_E2_V28_LAST_BLOCK
      if (!selfClosing)
        open.push_back(tag);
#endif
      continue;
    }

    // Non-structural.  Inside an open block it cannot change any answer this
    // barrier asks, so it is ignored -- that, and only that, is finding 035's
    // fix.  Outside one it can, so it fails closed.  Closing forms are ignored
    // either way: an inline close tag answers nothing.
    if (depth > 0 || closing)
      continue;
    if (tag == "div" && formatDivIsFootnoteApparatus(attributes)) {
      readback.footnoteApparatus = true;
      break;
    }
    readback.unknownTag = true;
    readback.unknownTagName = tag;
    break;
  }
  // Either count above one means the selection was not one paragraph.  Both are
  // checked: a two-paragraph plain read shows up as two block tags, and two
  // list items show up as two <li> even when the serialiser writes one <ul>.
  readback.multiBlock = readback.blockCount > 1 || readback.itemCount > 1;
  return readback;
}

// Which shape the CALLER's selection had when the action was dispatched.
//
// Decided before the dispatch, from the html readback's block count, and it is
// the only thing that decides how the postcondition is verified (SPEC E2-B
// 9.9).  RangeSingle and Collapsed both go to the .uno:SelectText barrier that
// has always been here and is honest for one paragraph; RangeCross cannot,
// because that barrier selects exactly one paragraph and would report success
// for a mutation covering two.
enum class FormatBarrierRoute {
  // SPEC E2-C 9.5.4: the FIRST member is what the struct is initialised to, and
  // the type guard returns before the route is ever assigned -- so every
  // refusal on that path used to report `route: "collapsed"`, which is a
  // default wearing an observation's clothes.  `Unclassified` first means the
  // record says "nobody classified this" unless somebody did.
  Unclassified,
  Collapsed,
  RangeSingle,
  RangeCross,
};

struct FormatStateBarrier {
  std::uint32_t requestId = 0;
  std::uint32_t documentHandle = 0;
  std::uint32_t beforeRevision = 0;
  std::uint64_t beforeSequence = 0;
  std::uint64_t dispatchSequence = 0;
  FormatBarrierTarget target = FormatBarrierTarget::None;
  bool expected = false;
  // Counts qualifying-command payloads that arrived after dispatch but did not
  // carry the expected value.  A non-zero count means core is broadcasting
  // state we must not mistake for our own completion; it is reported so the
  // state-crosstalk case can be judged from evidence rather than assumed away.
  std::uint32_t crosstalkCount = 0;
  // Counts state payloads that already carry the expected value but arrive
  // before this request's command result.  Native ordering is result-then-state
  // by ~300ms, so a non-zero count means the ordering assumption does not hold
  // in this profile and the evidence should say so rather than the barrier
  // quietly accepting an unattributed state.
  std::uint32_t earlyStateCount = 0;
  // Finding 020: the result's own success/wasModified fields are demonstrably
  // wrong for some list commands, so they are recorded but never believed.  The
  // result is used only to attribute a completion to this request.
  bool resultSeen = false;
  bool resultSuccess = false;
  bool resultModified = false;
#ifdef OXSDK_E2_V25_FORMAT_PROOF
  // Finding 171.  The ordered path knows whether it posted the command; the
  // record says so instead of leaving a projection to infer it from `stage`.
  bool dispatchRecorded = false;
  bool dispatched = false;
#endif
#ifdef OXSDK_E2_V27_FIRST_BLOCK
  // Finding 176 (SPEC-M3-v27-finding-176 4.1 item 4).  The undo stack read
  // before the dispatch and after the final restore.  RECORDED, never a verdict
  // input (fable ruling 3 Q4): it is an action trace that cannot name the
  // paragraph, and it is silent on a no-op.  `undoAttempted` is false on a
  // pre-dispatch refusal, which never reads it -- "not attempted" is not "not
  // readable".
  bool undoAttempted = false;
  bool undoRead = false;
  bool undoChanged = false;
  std::size_t undoActionsBefore = 0;
  std::size_t undoActionsAfter = 0;
  std::string undoTop;
#endif
#ifdef OXSDK_E2_V28_LAST_BLOCK
  // SPEC-M3-v28-last-line-fallback 4.1 item 4.  The one-position-back fallback
  // (`.uno:CharLeftSel`), run only when the collapsed route's `.uno:SelectText`
  // read NONE and the restore point is valid.  Judged by the LAST block.
  bool fallbackRan = false;
  bool fallbackResultSeen = false;
  int fallbackSelectionType = -1;
  bool fallbackReadable = false;
  std::size_t fallbackReadbackBytes = 0;
  std::string fallbackReadbackHtml;
  FormatReadback fallbackReadback;
  std::string fallbackRefusal;
#endif
  // Finding 033.  The barrier used to advance out of AwaitingSelection on any
  // TEXT_SELECTION carrying rectangles, and a search dispatched by the caller
  // selects its match -- so the caller's own caret move could hand the barrier
  // a selection and the read would describe that paragraph instead.
  //
  // .uno:EndOfParaSel returns a UNO command result on every dispatch (measured
  // natively, 8 dispatches / 8 results, findings/evidence/sdk-e2/discovery/
  // endofparasel-result/native-26-8), and .uno:GoToStartOfPara returns one too
  // -- which is why the condition matches the command *name* rather than "a
  // result arrived".
  bool selectionResultSeen = false;
  // Non-empty selections seen while this barrier's own EndOfParaSel was still
  // unacknowledged.  Deliberately *not* called "unattributed": the delivery
  // order of TEXT_SELECTION versus UNO_COMMAND_RESULT has been measured for the
  // five format commands (result first, by ~300ms) and never for this one, so
  // the barrier's own selection may well land here.  The number is reported
  // raw; what it means is a reading of the evidence, not a verdict baked into
  // the name.
  std::uint32_t selectionBeforeResultCount = 0;
  std::vector<std::string> expectedStyles;
  std::string action;
  std::string command;
  std::string arguments;
  // Route C readback (finding 030 / SPEC E2-A 2.8).
  FormatBarrierStage stage = FormatBarrierStage::Idle;
  // Routing, and the evidence it rests on.  preBlockTexts is the identity the
  // cross route verifies against: per-block TEXT, because the plain-text
  // readback injects list decoration across a paragraph boundary and would
  // therefore differ on every SUCCESSFUL list dispatch.
  FormatBarrierRoute route = FormatBarrierRoute::Unclassified;
  std::uint32_t preBlockCount = 0;
  std::vector<std::string> preBlockTexts;
  std::uint32_t postBlockCount = 0;
  std::vector<std::string> postBlockTexts;
  // Whether anything ever WROTE the two counts above.
  //
  // Measured 2026-08-16 (findings/evidence/046/browser-vs-native/): each of
  // them is assigned in exactly one place -- preBlockCount only when the
  // selection rectangles are non-empty (the range routes), postBlockCount only
  // in the cross route's check.  On the collapsed route both stay 0, including
  // on barriers that SUCCEED, and two rounds of evidence were read as if that
  // zero meant "read the paragraph, found no blocks in it".  Finding 046's
  // whole native-versus-browser disagreement was that misreading.
  //
  // Same defect as the `route` field's (SPEC E2-C 9.5.4): a default reported as
  // an observation.  The counts keep their type and their value; these say
  // whether the value is one.
  bool preBlockCountObserved = false;
  bool postBlockCountObserved = false;
  bool crossChecked = false;
  bool crossIdentityHeld = false;
  bool crossStateHeld = false;
  std::uint64_t serial = 0;
  // Where the caret was before the read selected the paragraph, so it can be
  // put back.  Recorded before the dispatch, because the dispatch itself may
  // move it.
  EditorRect restorePoint;
  bool restorePointValid = false;
  bool restoreConfirmed = false;
  // SPEC E2-A 10.14 narrowing 7.  "All 395 dispatches came from a collapsed
  // caret" was inferred from the harness shape and never recorded, and the two
  // fields that look like they answer it do not: `selectionType` is read at
  // ReadQueued, one stage AFTER the barrier posted its own paragraph selection,
  // and `state.selection.collapsed` is emitted after the restore, so being
  // collapsed there just means the restore worked.  These two are read at the
  // dispatch itself, next to restorePoint, which is the only moment that can
  // answer what the CALLER had selected.
  //
  // Read from the engine's tracked rectangles rather than by asking LOK: a
  // readSelection() here would be the call measured to hang forever on finding
  // 038's construct (findings/040, third entry point), so a field added to
  // record evidence would have introduced a wedge.
  bool dispatchSelectionCollapsed = true;
  bool dispatchSelectionObserved = false;
  std::size_t dispatchSelectionRectangles = 0;
  // Finding 046, and the reason it needed a measurement before it could have a
  // fix: the barrier verified the WRONG PARAGRAPH.  `.uno:SelectText` on an
  // empty paragraph overshoots into the neighbour, so the readback describes a
  // paragraph the action was never dispatched on -- and containment cannot see
  // it, because containment asks whether the selection COVERS the caret, never
  // whether it covers ONLY the caret's paragraph.
  //
  // Captured at the dispatch, next to restorePoint, for the same reason: it is
  // the only moment that can say what the caller acted on.  Compared after the
  // read.  A fingerprint, so two paragraphs with the same text are the named
  // limit of this check rather than a silent hole
  // (findings/evidence/queue-block-identity/).
  std::uint64_t dispatchParagraphFingerprint = 0;
  bool dispatchParagraphKnown = false;
  std::uint64_t readbackParagraphFingerprint = 0;
  bool readbackParagraphKnown = false;
  // FINDING 082.  Whether each end's fingerprint may be COMPARED at all.
  // `Known` says the read succeeded; these say the value it produced carries an
  // identity rather than the constant that means nothing was hashed.
  bool dispatchParagraphUsable = false;
  bool readbackParagraphUsable = false;
  // Did the identity comparison actually run?  See the verdict path.
  bool paragraphIdentityChecked = false;
  // And if it did not, WHICH of the reasons it was.  "" while it ran.
  const char *paragraphIdentityDeclined = "";
  // What the postcondition demands of the readback.  Empty means "this action
  // makes no claim about that half".
  std::string expectedListTag;   // "ul" / "ol" / "none"
  std::string expectedBlockTag;  // "h1" / "p"
  // Finding 033's open gap, made reachable by finding 034's repair.
  //
  // The barrier had no deadline of its own: a stage that never advanced left it
  // active forever, and because the BUSY gate refuses every caret mover while a
  // barrier is in flight, one stall wedged the whole document handle (observed,
  // A5 styled-list attempt-04).  That was reachable only through a command
  // ordering bug.  Adopting .uno:SelectText *creates* a reachable stall on
  // purpose: on the document's last paragraph, if it is empty, the command
  // returns its result and no selection callback ever arrives (native 26.8,
  // selectionType 0, selecttext-result/).  So the deadline is a required part
  // of that change, not a defence against something hypothetical.
  //
  // 5000ms, not the 250 the matrix records for the selection barrier's boundary
  // readback: that number was measured for a different question (how long a
  // structural boundary probe needs) and reusing it because it is nearby is how
  // a measurement becomes a habit.  This one only has to be longer than any
  // healthy stage; every barrier measured so far completes in under 40ms.
  std::chrono::steady_clock::time_point stageDeadline{};
  bool stageDeadlineArmed = false;
  // Which shape of failure ended this barrier.  The code the caller sees is
  // deliberately coarse -- three different stalls all mean "do not replay" --
  // so the distinction that matters for diagnosis lives here instead of being
  // smuggled into the code.
  std::string failureShape;
  // Containment, recorded whether or not it decides anything, because "the
  // selection did not cover the caret" and "we never worked out where either
  // was" must not both report as a bare false.
  bool containmentChecked = false;
  bool containmentHeld = false;
  long selectionTop = 0;
  long selectionBottom = 0;
  long restoreCentre = 0;
  // Finding 037.  The selection type as it was immediately before the read,
  // recorded on every barrier and not only on the refused ones: it is the
  // field that answers "which paragraph shapes would this guard refuse?" out
  // of ordinary sweep evidence, instead of needing its own measurement every
  // time somebody asks.  -1 means the guard never ran (the barrier ended
  // before reaching the read step).
  int selectionType = -1;
  bool selectionTypeReadable = false;
  FormatReadback readback;
  std::size_t readbackBytes = 0;
  // Kept verbatim and bounded.  A postcondition that failed is only auditable
  // if the markup it judged is in the evidence -- reporting "did not match"
  // without it is the shape of claim this project keeps having to retract.
  std::string readbackHtml;
};

constexpr std::size_t FormatReadbackEvidenceLimit = 2048;
constexpr int FormatBarrierStageDeadlineMs = 5000;

// The command the barrier posts to select the paragraph it is about to read.
// Named once so the dispatch and the attribution cannot drift apart.
//
// Finding 034 replaced the pair .uno:GoToStartOfPara + .uno:EndOfParaSel with
// this one command.  The pair is not idempotent at the paragraph edges --
// GoCurrPara moves to the *previous* paragraph when the caret is already at
// offset 0 (sw/source/core/crsr/pam.cxx:1238, and core's own comment says so),
// with the mirror flaw at offset Len() -- so "move to one end, select to the
// other" has two blind spots by construction.  FN_SELECT_PARA carries the clamp
// in core's dispatch handler (26.8 sw/source/uibase/shells/textsh1.cxx:1975),
// and measuring it across every reachable caret offset showed no escape and no
// regression at offset Len(), where all 375 previously judged dispatches sat.
//
// One dispatch also removes, as a class, the ordering bug finding 033 recorded:
// there are no longer two dispatch paths that can take effect out of order.
//
// It returns a UNO command result on every dispatch (native 26.8, 10/10,
// findings/evidence/sdk-e2/discovery/selecttext-result/), which is what the
// AwaitingSelection attribution needs and was measured before this switch
// rather than assumed from the pair's behaviour.
const char *const kFormatBarrierSelectCommand = ".uno:SelectText";
#ifdef OXSDK_E2_V28_LAST_BLOCK
const char *const kFormatBarrierFallbackCommand = ".uno:CharLeftSel";
#endif

FormatStateBarrier gFormatBarrier;
std::uint64_t gNextFormatBarrierSerial = 1;

bool formatBarrierActive() {
  return gFormatBarrier.target != FormatBarrierTarget::None;
}

// Finding 021 remediation, discovery only.
//
// The cached format state does not follow the caret in this build, because
// nothing runs the VCL scheduler between operations, so the idle job that
// recomputes those slots never fires.  Reading the precondition without fixing
// that answers for whichever paragraph last reported -- the silent no-op.
//
// Pumping alone is not enough either: measurement showed the callbacks are
// delivered *after* the pump call returns, not during it, so a synchronous
// pump-then-read still reads the stale value.  The precondition therefore needs
// the same shape as the completion barrier: pump, then wait, bounded, for a
// watched payload to arrive, and only then decide.
//
// Timing out means the precondition stays unknown, which is
// EDITOR_FORMAT_STATE_UNAVAILABLE and zero mutation -- fail closed, never a
// guess.  Nothing here is a product mechanism: the pump used is a unit-test
// hook, and the product pump is still an open question.
#endif

EditorState gEditorState;
EditorPendingOperation gEditorPending;
std::string gEditorUnoAction;
std::string gEditorUnoCommand;
std::uint32_t gEditorUnoBeforeRevision = 0;
std::uint64_t gEditorUnoBeforeSequence = 0;
bool gEditorUnoOption = false;
bool gEditorUnoSemanticReadback = false;
// Why accessibility is not on, when it is not on.  Empty means "it is".
//
// The v3 link shipped with accessibility never switched on, and the ONLY
// symptom was that every paragraph read back as empty -- which is exactly what
// a genuinely empty paragraph looks like.  A mechanism whose "off" is
// indistinguishable from a legitimate reading is a mechanism that can be off
// for a month.  So it says so now, and the three silent guards below each say
// which one refused.
const char *gEditorAccessibilityUnavailable = "not-attempted";
bool gEditorAccessibilityEnabled = false;
constexpr int EditorShiftModifier = 0x1000;
// KEY_MOD1 -- Ctrl.  Same scheme as the shift bit above, and the only other
// modifier this ABI has any use for.
constexpr int EditorMod1Modifier = 0x2000;
constexpr int EditorCaretOrSelectionCallback = -2;
constexpr int EditorMutationCallback = -3;
void finishAsynchronous(std::uint32_t requestId);
void advanceRevision();
SelectionReadback readSelection();
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
void handleSelectionBarrierStateCallback(int callbackType);
#ifdef OXSDK_MERGE_KEY_UNDO
void feedMergeAttribution(int type, const char *payload);
#endif
bool handleSelectionBarrierUnoResult(const char *payload);
void handleSelectionBarrierStep(const Command &command);
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
void handleFormatBarrierStateCallback(int callbackType);
void handleFormatBarrierStep(const Command &command);
#endif
#endif

#ifdef OXSDK_E2_V23_LINK_BATCH
#include "ordered_engine_state.inc"
#endif

std::string jsonEscape(const char *value) {
  if (!value)
    return {};

  std::string escaped;
  for (const unsigned char *p = reinterpret_cast<const unsigned char *>(value);
       *p; ++p) {
    switch (*p) {
    case '"':
      escaped += "\\\"";
      break;
    case '\\':
      escaped += "\\\\";
      break;
    case '\b':
      escaped += "\\b";
      break;
    case '\f':
      escaped += "\\f";
      break;
    case '\n':
      escaped += "\\n";
      break;
    case '\r':
      escaped += "\\r";
      break;
    case '\t':
      escaped += "\\t";
      break;
    default:
      if (*p < 0x20) {
        char buffer[7];
        std::snprintf(buffer, sizeof(buffer), "\\u%04x", *p);
        escaped += buffer;
      } else
        escaped += static_cast<char>(*p);
    }
  }
  return escaped;
}

void emitJson(const std::string &json) {
  MAIN_THREAD_EM_ASM(
      {
        const eventJson = UTF8ToString($0);
        // `===` is split into `== =` by the C preprocessor in EM_ASM.
        // typeof always returns a string, so loose equality is safe here.
        if (typeof globalThis.__probe_on_event == 'function')
          globalThis.__probe_on_event(eventJson);
        else
          console.warn('wasm_sdk_probe event handler is not installed',
                       eventJson);
      },
      json.c_str());
}

#ifdef OXSDK_EDITOR_DISCOVERY
bool parseEditorRectangleText(const std::string &text, EditorRect &rectangle) {
  int consumed = 0;
  EditorRect parsed;
  if (std::sscanf(text.c_str(), " %d , %d , %d , %d %n", &parsed.x,
                  &parsed.y, &parsed.width, &parsed.height, &consumed) != 4) {
    return false;
  }
  for (std::size_t index = static_cast<std::size_t>(consumed);
       index < text.size(); ++index) {
    if (!std::isspace(static_cast<unsigned char>(text[index])))
      return false;
  }
  if (parsed.width < 0 || parsed.height < 0)
    return false;
  parsed.available = true;
  rectangle = parsed;
  return true;
}

bool parseEditorRectangle(const char *payload, EditorRect &rectangle) {
  if (!payload)
    return false;
  std::string value(payload);
  if (!value.empty() && value.front() == '{') {
    const std::string key = "\"rectangle\"";
    const std::size_t keyPosition = value.find(key);
    if (keyPosition == std::string::npos)
      return false;
    const std::size_t colon = value.find(':', keyPosition + key.size());
    const std::size_t quote =
        colon == std::string::npos ? std::string::npos : value.find('"', colon);
    const std::size_t end = quote == std::string::npos
                                ? std::string::npos
                                : value.find('"', quote + 1);
    if (quote == std::string::npos || end == std::string::npos)
      return false;
    value = value.substr(quote + 1, end - quote - 1);
  }
  return parseEditorRectangleText(value, rectangle);
}

bool parseEditorSelectionRectangles(const char *payload,
                                    std::vector<EditorRect> &rectangles) {
  if (!payload)
    return false;
  rectangles.clear();
  const std::string value(payload);
  if (value.empty())
    return true;
  std::size_t start = 0;
  while (start <= value.size()) {
    const std::size_t separator = value.find(';', start);
    const std::string item = value.substr(
        start, separator == std::string::npos ? std::string::npos
                                               : separator - start);
    EditorRect rectangle;
    if (!parseEditorRectangleText(item, rectangle)) {
      rectangles.clear();
      return false;
    }
    rectangles.push_back(rectangle);
    if (separator == std::string::npos)
      break;
    start = separator + 1;
  }
  return true;
}

void appendEditorRectangle(std::ostringstream &json,
                           const EditorRect &rectangle) {
  if (!rectangle.available) {
    json << "null";
    return;
  }
  json << "{\"x\":" << rectangle.x << ",\"y\":" << rectangle.y
       << ",\"width\":" << rectangle.width << ",\"height\":"
       << rectangle.height << "}";
}

void appendEditorState(std::ostringstream &json) {
  json << "\"sourceSequence\":" << gEditorState.sourceSequence
       << ",\"documentChangeSequence\":"
       << gEditorState.documentChangeSequence
#ifdef OXSDK_E2_V20_LINK_BATCH
       // Top level, beside the sequence it replaces as the page number's
       // trigger; the worker names it in every editor-state projection.
       << ",\"documentSizeChangedCount\":"
       << gEditorState.documentSizeChangedCount
#endif
       << ",\"visible\":" << (gEditorState.cursorVisible ? "true" : "false")
       << ",\"caret\":";
  appendEditorRectangle(json, gEditorState.caret);
  json << ",\"selection\":{\"observed\":"
       << (gEditorState.selectionObserved ? "true" : "false")
       << ",\"collapsed\":"
       << (gEditorState.selectionRectangles.empty() ? "true" : "false")
       << ",\"start\":";
  appendEditorRectangle(json, gEditorState.selectionStart);
  json << ",\"end\":";
  appendEditorRectangle(json, gEditorState.selectionEnd);
  json << ",\"rectangles\":[";
  for (std::size_t index = 0; index < gEditorState.selectionRectangles.size();
       ++index) {
    if (index)
      json << ',';
    appendEditorRectangle(json, gEditorState.selectionRectangles[index]);
  }
  json << "]},\"a11y\":{\"observed\":"
       << (gEditorState.a11yObserved ? "true" : "false")
       << ",\"changeCount\":" << gEditorState.a11yChangeCount
       << ",\"unparsedCount\":" << gEditorState.a11yUnparsedCount
       << ",\"lastSequence\":" << gEditorState.a11yLastSequence
       << ",\"contentLength\":" << gEditorState.a11yContentLength
       << ",\"position\":" << gEditorState.a11yPosition
       << ",\"enabled\":"
       << (gEditorAccessibilityEnabled ? "true" : "false")
       << ",\"unavailable\":\""
       << jsonEscape(gEditorAccessibilityUnavailable) << "\""
       << ",\"paragraphFresh\":"
       << (gEditorState.a11yParagraphFresh ? "true" : "false")
       << ",\"paragraphFingerprint\":\"" << std::hex
       << gEditorState.a11yContentHash << std::dec << "\""
       // FINDING 082.  A host that compares fingerprints has to be able to
       // tell "this one identifies a paragraph" from "this one is the value
       // that means nothing was hashed", and until this field existed the two
       // arrived as the same hex string.
       << ",\"fingerprintUsable\":"
       << (gEditorState.a11yFingerprintUsable ? "true" : "false")
       << ",\"listPrefixLength\":" << gEditorState.a11yListPrefixLength
#ifdef OXSDK_A11Y_OUTLINE
       // ROADMAP 3.4, the product field.  WCAG 2.1 1.3.1 is Level A and asks
       // for information and relationships to be programmatically
       // determinable; a canvas says "heading" by drawing it bigger, so this
       // is where the document says it in words.
       //
       // Emitted on every state read rather than only when the structure
       // moved, and that is a MEASURED choice rather than a lazy one: the
       // diagnostic build has been emitting the whole tree on every read since
       // 2026-08-23 and a 133-paragraph document showed no trouble.  A
       // change-sequence optimisation is a later change WITH a measurement
       // behind it; guessing at one now would be optimising ahead of evidence.
       << ",\"outline\":" << [] {
              char *raw = oxsdk_a11y_document_outline();
              const std::string owned = raw ? raw : "{\"unavailable\":\"null\"}";
              std::free(raw);
              return owned;
          }()
#endif
#ifdef OXSDK_A11Y_TREE_PROBE
       // DIAGNOSTIC ONLY.  `src/a11y_tree_probe.cpp` is the one translation
       // unit compiled with -DLIBO_INTERNAL_ONLY; this is the only place that
       // calls it, and neither exists in a product build.  It rides the a11y
       // block because the worker's raw branch forwards that wholesale -- no
       // worker change for a thing that is going to be deleted.
       << ",\"tree\":" << [] {
              char *raw = oxsdk_a11y_tree_snapshot();
              const std::string owned = raw ? raw : "{\"unavailable\":\"null\"}";
              std::free(raw);
              return owned;
          }()
#endif
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
       // Uncapped, like `selectionText` beside it. Capping one text field and
       // not the other would be an inconsistency a host cannot see, and a
       // silently truncated paragraph is exactly the kind of plausible wrong
       // answer this engine clears fields to avoid.
       << ",\"paragraphText\":\""
       << jsonEscape(gEditorState.a11yParagraphText.c_str()) << "\""
#endif
       << "},\"format\":{\"bold\":";
  if (gEditorState.boldKnown)
    json << (gEditorState.bold ? "true" : "false");
  else
    json << "null";
  json << ",\"italic\":";
  if (gEditorState.italicKnown)
    json << (gEditorState.italic ? "true" : "false");
  else
    json << "null";
#ifdef OXSDK_E2_FORMAT_BARRIER
  // Underline and Strikeout, now that a cache exists for them.  Without these
  // the page can dispatch the two commands but can never read them back, so a
  // toolbar button or a shortcut for either can only ever ask for ON -- the
  // asymmetry `clearInlineFormatting()` was written to work around.
  json << ",\"underline\":";
  if (gEditorState.underlineKnown)
    json << (gEditorState.underline ? "true" : "false");
  else
    json << "null";
  json << ",\"strikethrough\":";
  if (gEditorState.strikeoutKnown)
    json << (gEditorState.strikeout ? "true" : "false");
  else
    json << "null";
  json << ",\"listBullet\":";
  if (gEditorState.listBulletKnown)
    json << (gEditorState.listBullet ? "true" : "false");
  else
    json << "null";
  json << ",\"listNumber\":";
  if (gEditorState.listNumberKnown)
    json << (gEditorState.listNumber ? "true" : "false");
  else
    json << "null";
  json << ",\"paragraphStyle\":";
  if (gEditorState.paragraphStyleKnown)
    json << '"' << jsonEscape(gEditorState.paragraphStyle.c_str()) << '"';
  else
    json << "null";
  json << ",\"stateChangedTotal\":" << gEditorState.stateChangedTotal
       << ",\"stateChangedUnrecognised\":"
       << gEditorState.stateChangedUnrecognised;
  // `formatStale` is the validity bit for the two fields directly above it,
  // and until 2026-08-17 it was emitted ONLY under OXSDK_MAINLOOP_ENGINE --
  // which the product does not define.  So the product shipped a cached format
  // measurement and compiled out the only thing that says whether it describes
  // the paragraph the caret is in.  Same disease as the accessibility call that
  // cost the v3 link: a capability whose failure is indistinguishable from a
  // reading.
  //
  // The poll counters stay behind the guard -- they are the main-loop build's
  // own instrumentation and mean nothing here.
  json << ",\"formatStale\":"
       << (gEditorState.formatStateStale ? "true" : "false");
#ifdef OXSDK_MAINLOOP_ENGINE
  json << ",\"pollCount\":"
       << gMainLoop.pollCount.load(std::memory_order_relaxed)
       << ",\"idlePollCount\":"
       << gMainLoop.idlePollCount.load(std::memory_order_relaxed);
#endif
#endif
  json << "}";
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
  json << ",\"schedulerProbe\":{\"stateChangedCount\":"
       << gEditorState.stateChangedCount
       << ",\"wordCountUpdateCount\":"
       << gEditorState.wordCountUpdateCount << ",\"wordCountWords\":"
       << gEditorState.wordCountWords << ",\"wordCountCharacters\":"
       << gEditorState.wordCountCharacters << "}";
#endif
}

void emitEditorStateEvent(const char *source) {
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-state\",\"requestId\":0"
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << ",\"source\":\""
       << jsonEscape(source) << "\",";
  appendEditorState(json);
  json << "}";
  emitJson(json.str());
}

#ifdef OXSDK_E2_FORMAT_BARRIER
struct FormatStatePayload {
  std::string command;
  bool boolean = false;
  bool booleanValue = false;
  std::string style;
};

// Only the commands core lists in GetKitUnoCommandList() are recognised, and
// each one is matched whole -- no prefix or substring guessing.  The style name
// is the single free-form value, and it is treated as opaque data.
bool parseFormatStatePayload(const std::string &value,
                             FormatStatePayload &parsed) {
  static const char *const booleanCommands[] = {
      ".uno:Bold", ".uno:Italic", ".uno:Underline", ".uno:Strikeout",
      ".uno:DefaultBullet", ".uno:DefaultNumbering"};
  for (const char *command : booleanCommands) {
    const std::string prefix(command);
    if (value == prefix + "=true" || value == prefix + "=false") {
      parsed.command = prefix;
      parsed.boolean = true;
      parsed.booleanValue = value == prefix + "=true";
      return true;
    }
  }
  static const std::string styleCommand = ".uno:StyleApply";
  if (value.rfind(styleCommand + "=", 0) == 0) {
    parsed.command = styleCommand;
    parsed.boolean = false;
    parsed.style = value.substr(styleCommand.size() + 1);
    return true;
  }
  return false;
}

bool formatBarrierPostconditionMet() {
  switch (gFormatBarrier.target) {
  case FormatBarrierTarget::ListBullet:
    return gEditorState.listBulletKnown &&
           gEditorState.listBullet == gFormatBarrier.expected;
  case FormatBarrierTarget::ListNumber:
    return gEditorState.listNumberKnown &&
           gEditorState.listNumber == gFormatBarrier.expected;
  case FormatBarrierTarget::ListNone:
    return gEditorState.listBulletKnown && !gEditorState.listBullet &&
           gEditorState.listNumberKnown && !gEditorState.listNumber;
  case FormatBarrierTarget::ParagraphStyle:
    return gEditorState.paragraphStyleKnown &&
           std::find(gFormatBarrier.expectedStyles.begin(),
                     gFormatBarrier.expectedStyles.end(),
                     gEditorState.paragraphStyle) !=
               gFormatBarrier.expectedStyles.end();
  case FormatBarrierTarget::None:
    break;
  }
  return false;
}

bool formatBarrierWatches(const std::string &command) {
  switch (gFormatBarrier.target) {
  case FormatBarrierTarget::ListBullet:
    return command == ".uno:DefaultBullet";
  case FormatBarrierTarget::ListNumber:
    return command == ".uno:DefaultNumbering";
  case FormatBarrierTarget::ListNone:
    return command == ".uno:DefaultBullet" ||
           command == ".uno:DefaultNumbering";
  case FormatBarrierTarget::ParagraphStyle:
    return command == ".uno:StyleApply";
  case FormatBarrierTarget::None:
    break;
  }
  return false;
}

const char *formatBarrierStageName(FormatBarrierStage stage) {
  switch (stage) {
  case FormatBarrierStage::Idle: return "idle";
  case FormatBarrierStage::AwaitingResult: return "awaiting-result";
  case FormatBarrierStage::SelectQueued: return "select-queued";
  case FormatBarrierStage::AwaitingSelection: return "awaiting-selection";
  case FormatBarrierStage::ReadQueued: return "read-queued";
  case FormatBarrierStage::AwaitingRestore: return "awaiting-restore";
  }
  return "unknown";
}

#ifdef OXSDK_E2_V28_LAST_BLOCK
// SPEC-M3-v28-last-line-fallback 4.1 item 9.  The fallback's record, called
// mid-chain below so that the v27 block's close is not touched.
std::string formatBarrierFallbackJson(const FormatStateBarrier &barrier) {
  std::ostringstream json;
  json << ",\"fallback\":{\"ran\":" << (barrier.fallbackRan ? "true" : "false");
  if (barrier.fallbackRan) {
    const FormatReadback &readback = barrier.fallbackReadback;
    json << ",\"command\":\"" << kFormatBarrierFallbackCommand
         << "\",\"resultSeen\":" << (barrier.fallbackResultSeen ? "true" : "false")
         << ",\"selectionType\":" << barrier.fallbackSelectionType
         << ",\"readable\":" << (barrier.fallbackReadable ? "true" : "false")
         << ",\"readbackBytes\":" << barrier.fallbackReadbackBytes
         << ",\"readback\":{\"parsed\":" << (readback.parsed ? "true" : "false")
         << ",\"unknownTag\":" << (readback.unknownTag ? "true" : "false")
         << ",\"unknownTagName\":\"" << jsonEscape(readback.unknownTagName.c_str())
         << "\",\"malformedNesting\":" << (readback.malformedNesting ? "true" : "false")
         << ",\"footnoteApparatus\":" << (readback.footnoteApparatus ? "true" : "false")
         << ",\"listTag\":\"" << jsonEscape(readback.listTag.c_str())
         << "\",\"blockTag\":\"" << jsonEscape(readback.blockTag.c_str())
         << "\",\"lastListTag\":\"" << jsonEscape(readback.lastListTag.c_str())
         << "\",\"lastBlockTag\":\"" << jsonEscape(readback.lastBlockTag.c_str())
         << "\",\"blockCount\":" << readback.blockCount
         << ",\"itemCount\":" << readback.itemCount
         << ",\"multiBlock\":" << (readback.multiBlock ? "true" : "false")
         << "},\"readbackHtml\":\"" << jsonEscape(barrier.fallbackReadbackHtml.c_str())
         << "\",\"refusal\":\"" << jsonEscape(barrier.fallbackRefusal.c_str()) << "\"";
  }
  json << "}";
  return json.str();
}
#endif

void appendFormatBarrierDetails(std::ostringstream &json,
                                const FormatStateBarrier &barrier) {
  json << "\"formatBarrier\":{\"command\":\""
       << jsonEscape(barrier.command.c_str())
       << "\",\"selectCommand\":\""
       << jsonEscape(kFormatBarrierSelectCommand)
       << "\",\"dispatchSequence\":" << barrier.dispatchSequence
       // The stage the barrier was in when it ended.  Without it a deadline
       // failure cannot be told from a containment failure in the evidence,
       // and both arrive under the same caller-facing code on purpose.
       << ",\"stage\":\"" << formatBarrierStageName(barrier.stage)
#ifdef OXSDK_E2_V25_FORMAT_PROOF
       << "\"" << (barrier.dispatchRecorded
                       ? (barrier.dispatched ? ",\"dispatched\":true" : ",\"dispatched\":false")
                       : "")
       << ",\"failureShape\":\"" << jsonEscape(barrier.failureShape.c_str())
#else
       << "\",\"failureShape\":\"" << jsonEscape(barrier.failureShape.c_str())
#endif
       << "\",\"crosstalkCount\":" << barrier.crosstalkCount
       << ",\"earlyStateCount\":" << barrier.earlyStateCount
       << ",\"resultSeen\":" << (barrier.resultSeen ? "true" : "false")
       << ",\"selectionResultSeen\":"
       << (barrier.selectionResultSeen ? "true" : "false")
       << ",\"selectionBeforeResultCount\":"
       << barrier.selectionBeforeResultCount
       // Finding 046's identity gate, and above all whether it RAN.  A verdict
       // reached without it is not the same verdict, and until this field
       // existed the two were indistinguishable in the evidence.
       << ",\"paragraphIdentity\":{\"checked\":"
       << (barrier.paragraphIdentityChecked ? "true" : "false")
       << ",\"dispatchKnown\":"
       << (barrier.dispatchParagraphKnown ? "true" : "false")
       << ",\"readbackKnown\":"
       << (barrier.readbackParagraphKnown ? "true" : "false")
       // FINDING 082.  `checked: false` had two causes and now has three, and
       // one of them is a defect in what the engine was given rather than in
       // what it could reach.  A reader who cannot tell them apart will read
       // "accessibility is off" over a build where it is on.
       << ",\"dispatchUsable\":"
       << (barrier.dispatchParagraphUsable ? "true" : "false")
       << ",\"readbackUsable\":"
       << (barrier.readbackParagraphUsable ? "true" : "false")
       << ",\"declined\":\""
       << jsonEscape(barrier.paragraphIdentityDeclined) << "\""
       << "}"
       << ",\"containment\":{\"checked\":"
       << (barrier.containmentChecked ? "true" : "false")
       << ",\"held\":" << (barrier.containmentHeld ? "true" : "false")
       << ",\"selectionTop\":" << barrier.selectionTop
       << ",\"selectionBottom\":" << barrier.selectionBottom
       << ",\"restoreCentre\":" << barrier.restoreCentre
       // Finding 037.  Emitted on every barrier, not only the refused ones:
       // this is the field that makes "which paragraph shapes does the guard
       // refuse?" answerable from any sweep's evidence.  -1 means the barrier
       // ended before the read step, so the guard never ran -- which is not
       // the same as "the selection was fine".
       << "},\"selectionType\":" << barrier.selectionType
       << ",\"selectionTypeReadable\":"
       << (barrier.selectionTypeReadable ? "true" : "false")
       // SPEC E2-A 10.14 narrowing 7.  Named `dispatch*` on purpose: the field
       // above it is read after the barrier selected the paragraph, so a reader
       // comparing them must be able to tell which moment each describes
       // without going to the source.
       << ",\"dispatchSelectionCollapsed\":"
       << (barrier.dispatchSelectionCollapsed ? "true" : "false")
       << ",\"dispatchSelectionObserved\":"
       << (barrier.dispatchSelectionObserved ? "true" : "false")
       << ",\"dispatchSelectionRectangles\":"
       << barrier.dispatchSelectionRectangles
       << ",\"resultSuccess\":" << (barrier.resultSuccess ? "true" : "false")
       << ",\"resultModified\":" << (barrier.resultModified ? "true" : "false")
       << ",\"expectedStyles\":[";
  for (std::size_t index = 0; index < barrier.expectedStyles.size(); ++index) {
    if (index)
      json << ',';
    json << '"' << jsonEscape(barrier.expectedStyles[index].c_str()) << '"';
  }
  // SPEC E2-B 7.1: the gesture class is decided by the ENGINE's routing read,
  // and "completion cannot be attributed to a single request" is a stop
  // condition -- so the routing has to be in the record, not inferred by the
  // harness from coordinates it did not route on.
  json << "],\"route\":"
       << (barrier.route == FormatBarrierRoute::Unclassified   ? "null"
           : barrier.route == FormatBarrierRoute::Collapsed    ? "\"collapsed\""
           : barrier.route == FormatBarrierRoute::RangeSingle  ? "\"range-single\""
                                                               : "\"range-cross\"")
       << ",\"preBlocks\":" << barrier.preBlockCount
       << ",\"preBlocksObserved\":"
       << (barrier.preBlockCountObserved ? "true" : "false")
       << ",\"postBlocks\":" << barrier.postBlockCount
       << ",\"postBlocksObserved\":"
       << (barrier.postBlockCountObserved ? "true" : "false")
       << ",\"crossChecked\":"
       << (barrier.crossChecked ? "true" : "false")
       << ",\"crossIdentityHeld\":"
       << (barrier.crossIdentityHeld ? "true" : "false")
       << ",\"crossStateHeld\":"
       << (barrier.crossStateHeld ? "true" : "false")
       << ",\"blockTextsMatched\":"
       << (barrier.preBlockTexts == barrier.postBlockTexts ? "true" : "false")
#ifdef OXSDK_E2_V28_LAST_BLOCK
       << formatBarrierFallbackJson(barrier)
#endif
       << ",\"readback\":{\"parsed\":"
       << (barrier.readback.parsed ? "true" : "false")
       << ",\"unknownTag\":"
       << (barrier.readback.unknownTag ? "true" : "false")
       // Which tag stopped the scan.  Without it the evidence can say the read
       // was refused but not what it was refused over, which is the one thing
       // the next person needs in order to decide whether to measure it.
       << ",\"unknownTagName\":\""
       << jsonEscape(barrier.readback.unknownTagName.c_str())
       << "\",\"malformedNesting\":"
       << (barrier.readback.malformedNesting ? "true" : "false")
       << ",\"footnoteApparatus\":"
       << (barrier.readback.footnoteApparatus ? "true" : "false")
       << ",\"multiBlock\":"
       << (barrier.readback.multiBlock ? "true" : "false")
       << ",\"blockCount\":" << barrier.readback.blockCount
       << ",\"itemCount\":" << barrier.readback.itemCount
       << ",\"listTag\":\"" << jsonEscape(barrier.readback.listTag.c_str())
       << "\",\"blockTag\":\"" << jsonEscape(barrier.readback.blockTag.c_str())
#ifdef OXSDK_E2_V28_LAST_BLOCK
       << "\",\"lastListTag\":\"" << jsonEscape(barrier.readback.lastListTag.c_str())
       << "\",\"lastBlockTag\":\"" << jsonEscape(barrier.readback.lastBlockTag.c_str())
#endif
       << "\",\"expectedListTag\":\""
       << jsonEscape(barrier.expectedListTag.c_str())
       << "\",\"expectedBlockTag\":\""
       << jsonEscape(barrier.expectedBlockTag.c_str())
       << "\",\"bytes\":" << barrier.readbackBytes
       << ",\"restoreConfirmed\":"
       << (barrier.restoreConfirmed ? "true" : "false")
       << ",\"html\":\"" << jsonEscape(barrier.readbackHtml.c_str())
#ifdef OXSDK_E2_V27_FIRST_BLOCK
       << "\"}";
  // Inside `formatBarrier`, where the worker reads it (event.formatBarrier).
  if (barrier.undoAttempted) {
    json << ",\"undo\":{\"read\":" << (barrier.undoRead ? "true" : "false");
    if (barrier.undoRead)
      json << ",\"changed\":" << (barrier.undoChanged ? "true" : "false")
           << ",\"actionsBefore\":" << barrier.undoActionsBefore
           << ",\"actionsAfter\":" << barrier.undoActionsAfter
           << ",\"top\":\"" << jsonEscape(barrier.undoTop.c_str()) << "\"";
    json << "}";
  }
  json << "}";
#else
       << "\"}}";
#endif
}

void completeFormatBarrier() {
  const FormatStateBarrier barrier = gFormatBarrier;
  gFormatBarrier = FormatStateBarrier{};
  advanceRevision();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-action-completed\",\"requestId\":"
       << barrier.requestId << ",\"documentHandle\":"
       << barrier.documentHandle << ",\"beforeRevision\":"
       << barrier.beforeRevision << ",\"revision\":" << gState.revision
       << ",\"action\":\"" << jsonEscape(barrier.action.c_str())
       // `changed` is null on purpose, and this is the whole point of route C.
       //
       // The readback answers "is the document in the target state now".  It
       // does not answer "did this dispatch put it there" -- a repeat press
       // lands on a document that was already correct and reads back exactly
       // the same.  The previous shape emitted changed:true unconditionally,
       // which asserted something no check performed: on a repeat it was
       // simply false.  SPEC E2-A v10 already decided not to claim it
       // (documented-state-noop was removed precisely because the claim was
       // not supportable); the code was still making the claim anyway.
       << "\",\"option\":false,\"changed\":null"
       // Route C reports what it verified, and it verified the document, not a
       // broadcast.  The name changed with the source deliberately: evidence
       // recorded under the old name was produced by a different check.
       << ",\"completion\":\"verified-format-readback\""
       << ",\"callbackSequenceBefore\":" << barrier.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence << ',';
  appendFormatBarrierDetails(json, barrier);
  json << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  finishAsynchronous(barrier.requestId);
}

void failFormatBarrier(const char *code, const char *message) {
  const FormatStateBarrier barrier = gFormatBarrier;
  gFormatBarrier = FormatStateBarrier{};
  std::ostringstream json;
  // `code` is what the caller branches on and `failureShape` is what a reader
  // diagnoses from; both are emitted, and appendFormatBarrierDetails carries
  // the shape.
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << barrier.requestId
       << ",\"documentHandle\":" << barrier.documentHandle
       << ",\"operation\":\"editor-action\",\"code\":\"" << code
       << "\",\"message\":\"" << jsonEscape(message) << "\",";
  appendFormatBarrierDetails(json, barrier);
  json << "}";
  emitJson(json.str());
  finishAsynchronous(barrier.requestId);
}

// The state broadcast no longer decides anything -- finding 030 showed it is
// silent exactly when the answer would matter most.  The two attribution
// counters stay, because "how much unrelated watched traffic arrived while this
// request was in flight" is still worth having in the evidence, and A5's
// state-crosstalk case is judged from them.  They now count observations, not
// rejections.
void observeFormatBarrierPayload(const FormatStatePayload &parsed) {
  if (!formatBarrierActive() || !formatBarrierWatches(parsed.command))
    return;
  if (!formatBarrierPostconditionMet()) {
    ++gFormatBarrier.crosstalkCount;
    return;
  }
  if (!gFormatBarrier.resultSeen)
    ++gFormatBarrier.earlyStateCount;
}

void updateEditorFormatState(const char *payload) {
  if (!payload)
    return;
  FormatStatePayload parsed;
  if (!parseFormatStatePayload(std::string(payload), parsed)) {
    ++gEditorState.stateChangedUnrecognised;
    return;
  }
  if (parsed.command == ".uno:Bold") {
    gEditorState.boldKnown = true;
    gEditorState.bold = parsed.booleanValue;
  } else if (parsed.command == ".uno:Italic") {
    gEditorState.italicKnown = true;
    gEditorState.italic = parsed.booleanValue;
  } else if (parsed.command == ".uno:Underline") {
    gEditorState.underlineKnown = true;
    gEditorState.underline = parsed.booleanValue;
  } else if (parsed.command == ".uno:Strikeout") {
    gEditorState.strikeoutKnown = true;
    gEditorState.strikeout = parsed.booleanValue;
  } else if (parsed.command == ".uno:DefaultBullet") {
    gEditorState.listBulletKnown = true;
    gEditorState.listBullet = parsed.booleanValue;
  } else if (parsed.command == ".uno:DefaultNumbering") {
    gEditorState.listNumberKnown = true;
    gEditorState.listNumber = parsed.booleanValue;
  } else if (parsed.command == ".uno:StyleApply") {
    // An empty style name carries no postcondition, so it must never mark the
    // state as known -- otherwise a blank broadcast would satisfy a fail-closed
    // precondition check that is supposed to reject exactly this case.
    if (parsed.style.empty())
      return;
    gEditorState.paragraphStyleKnown = true;
    gEditorState.paragraphStyle = parsed.style;
  } else {
    return;
  }
  // A watched payload for the caret's current paragraph has arrived, so the
  // cache describes where the caret actually is again.
  gEditorState.formatStateStale = false;
  ++gEditorState.sourceSequence;
  emitEditorStateEvent("format-state");
#ifdef OXSDK_E2_V23_LINK_BATCH
  if (gOrderedDispatching || gOrderedReply) {
    for (const auto &read : probe::replystate::kReads)
      if (parsed.command == read.stateKey)
        gOrderedProof.stateItems.insert(parsed.command);
  }
#else
  observeFormatBarrierPayload(parsed);
#endif
}
#else
// Restored verbatim for every non-E2 profile.  E1-C validated e1-editor-v1 at a
// specific WASM hash, so the preprocessed translation unit for that profile has
// to stay exactly what it was; anything added here changes the frozen artifact.
void updateEditorFormatState(const char *payload) {
  if (!payload)
    return;
  const std::string value(payload);
  if (value == ".uno:Bold=true" || value == ".uno:Bold=false") {
    gEditorState.boldKnown = true;
    gEditorState.bold = value == ".uno:Bold=true";
  } else if (value == ".uno:Italic=true" ||
             value == ".uno:Italic=false") {
    gEditorState.italicKnown = true;
    gEditorState.italic = value == ".uno:Italic=true";
  } else {
    return;
  }
  ++gEditorState.sourceSequence;
  emitEditorStateEvent("format-state");
}
#endif

#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
bool parseEditorWordCountState(const std::string &value, int &words,
                               int &characters) {
  int parsedWords = -1;
  int parsedCharacters = -1;
  int consumed = 0;
  if (std::sscanf(value.c_str(),
                  ".uno:StateWordCount=%d words, %d characters%n",
                  &parsedWords, &parsedCharacters, &consumed) != 2)
    return false;
  for (std::size_t index = static_cast<std::size_t>(consumed);
       index < value.size(); ++index) {
    if (!std::isspace(static_cast<unsigned char>(value[index])))
      return false;
  }
  if (parsedWords < 0 || parsedCharacters < 0)
    return false;
  words = parsedWords;
  characters = parsedCharacters;
  return true;
}

void updateEditorSchedulerProbeState(const char *payload) {
  ++gEditorState.stateChangedCount;
  if (payload) {
    int words = -1;
    int characters = -1;
    if (parseEditorWordCountState(payload, words, characters)) {
      ++gEditorState.wordCountUpdateCount;
      gEditorState.wordCountWords = words;
      gEditorState.wordCountCharacters = characters;
    }
  }
  ++gEditorState.sourceSequence;
  emitEditorStateEvent("scheduler-state-changed");
}
#endif

struct EditorSemanticSnapshot {
  int position = -1;
  int selectionStart = -1;
  int selectionEnd = -1;
  int contentLength = -1;
  int listPrefixLength = 0;
  // A FINGERPRINT of the paragraph's text, not the text.  Measured natively
  // over four rounds (findings/evidence/queue-block-identity/): LOK carries no
  // paragraph index anywhere, and this payload's `content` is the only
  // per-block datum there is -- so "is this the paragraph I dispatched on?" is
  // answerable and "which paragraph is this?" is not.  Two paragraphs with the
  // same text are indistinguishable here, deliberately named as the limit
  // rather than papered over.
  //
  // A hash, because the engine does not forward the raw payload to JS (see the
  // typed-counter comment on EditorState) and the host needs to compare, not to
  // read.  FNV-1a: this is an equality check between two observations made
  // seconds apart in one process, not a security boundary.
  std::uint64_t contentHash = 0;
  // FINDING 082.  Whether `contentHash` may be used as an IDENTITY, which is a
  // different question from whether the read succeeded.
  //
  // The hash is taken over the content with `listPrefixLength` characters
  // stripped, and finding 074 makes that length the WHOLE PARAGRAPH for an
  // outline-numbered heading -- so the slice is empty and the hash is the
  // offset basis, the value that means nothing was hashed.  Measured
  // 2026-08-26: `E1-LC-HEADING` (13 of 13) and a paragraph holding only `• `
  // (2 of 2) report one number.  The rule lives in the header beside the hash.
  bool fingerprintUsable = false;
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
  // ROADMAP 3.4.  The text itself, and it is behind a guard for the reason the
  // format-barrier members two hundred lines up are: adding a field to the
  // emitted editor state changes the SHAPE the frozen E1 profiles would emit,
  // and E1-C's verdict binds to that shape.  A build without this flag is
  // byte-for-byte the same engine it was.
  //
  // Opened deliberately, and the closure it reverses is worth naming rather
  // than quietly dropping: the fingerprint exists because "the host needs to
  // compare, not to read".  That premise held while the only consumer was the
  // identity gate.  A screen reader genuinely needs to READ, and no other
  // layer has the text -- so the premise changed, and this is the reversal.
  //
  // The WHOLE content, prefix included.  `listPrefixLength` is emitted beside
  // it, so a host can slice; sending only the body would throw away the "1."
  // of an ordered list with no way to get it back.  The fingerprint stays
  // defined over `content[listPrefixLength:]`, unchanged.
  std::string content;
#endif
};

// MOVED to src/a11y_paragraph_identity.hpp on 2026-08-26, with the rule that
// reads its output (finding 082).  One implementation, and now one that a host
// compiler can drive: `tests/a11y_paragraph_identity_test.cpp` reproduces six
// fingerprints this engine actually reported on the accessibility profile.
//
// The comment it carried stays with it: 14695981039346656037 is the FNV-1a
// 64-bit offset basis, written one digit short until 2026-08-17 -- a perfectly
// serviceable hash that was not the algorithm the comment named, and caught
// because every paragraph then reported the constant that means UNFED.
using probe::fingerprintOf;

// Parses the documented focused-paragraph JSON shape shared by
// getA11yFocusedParagraph() and the LOK_CALLBACK_A11Y_FOCUS_CHANGED payload:
//   { "content": "...", "position": N, "start": N1, "end": N2,
//     "listPrefixLength": L }
bool parseEditorSemanticJson(const std::string &json,
                             EditorSemanticSnapshot &snapshot) {
  snapshot = EditorSemanticSnapshot{};
  try {
    boost::property_tree::ptree tree;
    std::istringstream input(json);
    boost::property_tree::read_json(input, tree);
    const std::string content = tree.get<std::string>("content");
    snapshot.position = tree.get<int>("position");
    snapshot.selectionStart = tree.get<int>("start", -1);
    snapshot.selectionEnd = tree.get<int>("end", -1);
    snapshot.listPrefixLength = tree.get<int>("listPrefixLength", 0);
    const rtl::OUString wide = rtl::OUString::fromUtf8(rtl::OString(
        content.data(), static_cast<sal_Int32>(content.size())));
    snapshot.contentLength = wide.getLength();
    // The fingerprint is taken over the paragraph WITHOUT its list prefix, and
    // that is not a detail -- it is what makes the fingerprint an identity for
    // the paragraph rather than a description of its current formatting.
    //
    // Measured, round 3 (findings/evidence/queue-block-identity/native/run-3/):
    // the same empty paragraph reads `content: ""` before `.uno:DefaultBullet`
    // and `content: "\u2022 "`, `listPrefixLength: 2` after it.  A fingerprint
    // over the whole string would therefore differ across every successful list
    // action, and a check comparing dispatch against readback would fire on
    // every one of them -- the false positive that would have made this fix
    // worse than the defect.
    //
    // Sliced on the UTF-16 index core counts in, not on bytes: the prefix is a
    // character count, and `"\u2022 "` is two characters and four bytes.
    const sal_Int32 prefix = std::min<sal_Int32>(
        snapshot.listPrefixLength, wide.getLength());
    const rtl::OString body = wide.copy(prefix).toUtf8();
    snapshot.contentHash =
        fingerprintOf(std::string(body.getStr(),
                                  static_cast<std::size_t>(body.getLength())));
    // Decided from the two COUNTS rather than from the hash, so that a
    // paragraph whose text happens to hash to the basis is not swept up with
    // the degenerate ones.  Finding 082.
    snapshot.fingerprintUsable = probe::paragraphFingerprintIsUsable(
        snapshot.listPrefixLength, snapshot.contentLength);
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
    snapshot.content = content;
#endif
  } catch (const std::exception &) {
    return false;
  }
  return snapshot.position >= 0 && snapshot.contentLength >= 0;
}

// Cached readback. Finding 016 established this is a listener cache rather
// than an authoritative synchronous query, so it can lag the document; the
// LOK_CALLBACK_A11Y_FOCUS_CHANGED path below is the live one.
bool readEditorSemanticSnapshot(EditorSemanticSnapshot &snapshot) {
  snapshot = EditorSemanticSnapshot{};
  if (!gState.document ||
      !LIBREOFFICEKIT_DOCUMENT_HAS(gState.document,
                                   getA11yFocusedParagraph))
    return false;
  char *value =
      gState.document->pClass->getA11yFocusedParagraph(gState.document);
  if (!value)
    return false;
  const std::string json(value);
  std::free(value);
  return parseEditorSemanticJson(json, snapshot);
}

// Refresh the caret paragraph's fingerprint from the SYNCHRONOUS query.
//
// The callback above is gated on the paragraph's TEXT changing (core:
// `if (m_sFocusedParagraph != sText)`), so moving between two paragraphs that
// read the same emits nothing at all -- while the query behind
// getA11yFocusedParagraph() is refreshed on every caret event.  Measured
// natively, four rounds.  So anything that wants to know WHICH paragraph the
// caret is in now has to ask, not wait.
//
// Called at the three points that need it rather than on every callback: the
// query walks the accessibility tree, and paying for it on every cursor blink
// would be a cost nothing reads.
bool refreshCaretParagraph() {
  EditorSemanticSnapshot snapshot;
  // THE SAME LIE ONE LEVEL DOWN, and it was found by running the control the
  // gate needed rather than by reading (2026-08-22,
  // findings/evidence/a11y-gate-0/).
  //
  // On a core built with ENABLE_WASM_STRIP_ACCESSIBILITY, every LOK entry
  // point below still EXISTS and getA11yFocusedParagraph() returns a
  // well-formed empty answer -- `content: ""`, `position: 0`.  The parse then
  // succeeds (`position >= 0 && contentLength >= 0`), so this used to record
  // `paragraphFresh = true` with contentLength 0 and the FNV-1a offset basis
  // as the fingerprint.  Measured on the shipped profile: all three caret
  // placements, identical.
  //
  // `fresh` is the bit that says "the LAST read succeeded, so the fingerprint
  // describes where the caret is NOW".  Saying that on a build where no read
  // can succeed is exactly the defect
  // `queue-engine-must-report-core-lacks-accessibility` fixed for `enabled` --
  // a capability failure wearing the costume of data.  A host that gates on
  // `fresh` alone, which is what the field is FOR, would take the empty-string
  // fingerprint for a live identity.
  //
  // Gated on the enabled flag rather than on a second `#if`: this also covers
  // the runtime cases (no document, LOK missing an entry point) where the
  // answer is equally not a reading.
  if (!gEditorAccessibilityEnabled) {
    gEditorState.a11yParagraphFresh = false;
    gEditorState.a11yContentLength = -1;
    gEditorState.a11yPosition = -1;
    gEditorState.a11yContentHash = 0;
    gEditorState.a11yFingerprintUsable = false;
    gEditorState.a11yListPrefixLength = 0;
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
    gEditorState.a11yParagraphText.clear();
#endif
    return false;
  }
  if (!readEditorSemanticSnapshot(snapshot)) {
    // Cleared, not left standing.  The first version returned false and touched
    // nothing, so a reply built after a failed read serialised the PREVIOUS
    // paragraph's fingerprint -- a plausible wrong answer, which is worse than
    // an obviously absent one.  `enabled` cannot cover this: it says
    // setAccessibilityState was called once, not that THIS read succeeded.
    gEditorState.a11yParagraphFresh = false;
    gEditorState.a11yContentLength = -1;
    gEditorState.a11yPosition = -1;
    gEditorState.a11yContentHash = 0;
    gEditorState.a11yFingerprintUsable = false;
    gEditorState.a11yListPrefixLength = 0;
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
    gEditorState.a11yParagraphText.clear();
#endif
    return false;
  }
  gEditorState.a11yContentLength = snapshot.contentLength;
  gEditorState.a11yPosition = snapshot.position;
  gEditorState.a11yContentHash = snapshot.contentHash;
  gEditorState.a11yFingerprintUsable = snapshot.fingerprintUsable;
  gEditorState.a11yListPrefixLength = snapshot.listPrefixLength;
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
  gEditorState.a11yParagraphText = snapshot.content;
#endif
  gEditorState.a11yParagraphFresh = true;
  return true;
}

bool deleteHasSafeSemanticPrecondition(const char *action,
                                       const EditorSemanticSnapshot &snapshot) {
  if (snapshot.selectionStart >= 0 && snapshot.selectionEnd >= 0 &&
      snapshot.selectionStart != snapshot.selectionEnd)
    return true;
  if (std::strcmp(action, "delete-backward") == 0)
    return snapshot.position > snapshot.listPrefixLength;
  if (std::strcmp(action, "delete-forward") == 0)
    return snapshot.position < snapshot.contentLength;
  return false;
}

const char *jsonFieldValue(const char *payload, const char *field) {
  if (!payload || !field)
    return nullptr;
  const std::string token = "\"" + std::string(field) + "\"";
  const char *position = std::strstr(payload, token.c_str());
  if (!position)
    return nullptr;
  position += token.size();
  while (*position && std::isspace(static_cast<unsigned char>(*position)))
    ++position;
  if (*position++ != ':')
    return nullptr;
  while (*position && std::isspace(static_cast<unsigned char>(*position)))
    ++position;
  return position;
}

bool commandResultMatches(const char *payload, const std::string &command) {
  const char *value = jsonFieldValue(payload, "commandName");
  if (!value || command.empty() || *value++ != '"')
    return false;
  return std::strncmp(value, command.c_str(), command.size()) == 0 &&
         value[command.size()] == '"';
}

bool commandResultSucceeded(const char *payload) {
  const char *value = jsonFieldValue(payload, "success");
  return value && std::strncmp(value, "true", 4) == 0 &&
         (value[4] == ',' || value[4] == '}' ||
          std::isspace(static_cast<unsigned char>(value[4])));
}

#ifdef OXSDK_E2_FORMAT_BARRIER
/**
 * Finding 059: did the inline format the caller asked for actually take?
 *
 * `success` cannot answer that.  Measured on 2026-08-19 against core 26.8, nine
 * arms: `success: true` appeared on exactly the two arms where core IGNORED the
 * argument and toggled, and `success: false` on every arm where core honoured
 * the parameterised form.  On this build the field is ANTI-CORRELATED with the
 * caller's request being honoured, so gating on it turns every working
 * parameterised format into LOK_COMMAND_FAILED -- which is what shipped.
 *
 * What survives is the format barrier's own shape: compare the OBSERVED state
 * against the REQUESTED one.  Not "did a broadcast arrive": core broadcasts a
 * state CHANGE, so a request for the state the caret already had produces no
 * broadcast at all while being perfectly satisfied.  Asking about the state
 * instead of the event makes that case a pass, which is the honest answer --
 * the postcondition holds either way.
 *
 * `...Known` is required, so "I do not know" can never be read as "yes".  It is
 * reliably true in practice because core emits a complete state set at document
 * load (measured, all four slots), but the guard stays: the load broadcast is
 * the only thing that primes this, caret movement does not, and an engine that
 * started listening later would be back in finding 021's shape.
 *
 * A genuine negative exists and was measured, which is what makes this a
 * predicate rather than a rubber stamp: a wrong argument TYPE leaves the text
 * unchanged with no broadcast, and a paragraph inside a protected section
 * refuses the dispatch -- and this returns false for both, agreeing with the
 * saved document on all nine arms.
 */
bool inlineFormatArgumentResolved(const std::string &unoCommand, bool requested) {
#ifdef OXSDK_E2_V23_LINK_BATCH
  if (!gOrderedProof.stateItems.count(unoCommand))
    return false;
#endif
  if (unoCommand == ".uno:Bold")
    return gEditorState.boldKnown && gEditorState.bold == requested;
  if (unoCommand == ".uno:Italic")
    return gEditorState.italicKnown && gEditorState.italic == requested;
  if (unoCommand == ".uno:Underline")
    return gEditorState.underlineKnown && gEditorState.underline == requested;
  if (unoCommand == ".uno:Strikeout")
    return gEditorState.strikeoutKnown && gEditorState.strikeout == requested;
  return false;
}

void queueFormatBarrierStep(FormatBarrierStage next);
void maybeAdvanceFormatBarrierSelection();

#ifndef OXSDK_E2_V23_LINK_BATCH
void handleFormatBarrierUnoResult(const char *payload) {
  if (!formatBarrierActive())
    return;
  // The barrier's own selection command, acknowledged.  Checked before the
  // action's command so a build where the two are ever the same command still
  // resolves the selection half here rather than silently skipping it.
  if (gFormatBarrier.stage == FormatBarrierStage::AwaitingSelection &&
      commandResultMatches(payload, kFormatBarrierSelectCommand)) {
    gFormatBarrier.selectionResultSeen = true;
    maybeAdvanceFormatBarrierSelection();
    return;
  }
  if (gFormatBarrier.resultSeen ||
      !commandResultMatches(payload, gFormatBarrier.command))
    return;
  gFormatBarrier.resultSeen = true;
  // Recorded for evidence only.  Finding 020 shows .uno:RemoveBullets reports
  // success:false and .uno:DefaultBullet reports wasModified:false while both
  // demonstrably change the document, so acting on either field would invert
  // the answer for those commands.
  gFormatBarrier.resultSuccess = commandResultSucceeded(payload);
  const char *modified = jsonFieldValue(payload, "wasModified");
  gFormatBarrier.resultModified =
      modified && std::strncmp(modified, "true", 4) == 0;
  // Attribution is settled; truth is not.  The read happens off this callback,
  // on the engine loop, for the same non-reentrancy reason the selection
  // barrier queues its verification instead of doing it here.
  if (gFormatBarrier.stage == FormatBarrierStage::AwaitingResult)
    queueFormatBarrierStep(FormatBarrierStage::SelectQueued);
}
#endif
#endif

void refreshEditorAccessibility() {
#if ENABLE_WASM_STRIP_ACCESSIBILITY
  /*
   * FIRST, and before any question about the document or about LOK.
   *
   * The three guards below ask whether LOK HAS the entry points.  On a build
   * with accessibility stripped they are all present and all useless: the calls
   * link, return, and change nothing, so the engine used to fall through to
   * `gEditorAccessibilityEnabled = true` and report a working mechanism.  The
   * only symptom was that every paragraph read back empty -- indistinguishable
   * from a genuinely empty paragraph, which is how it stayed unnoticed.
   *
   * This is not a runtime failure to be retried or a document that is not ready
   * yet.  It is a property of the binary, so it is answered at compile time and
   * it can never be anything else for this artifact.
   */
  gEditorAccessibilityUnavailable = "core-built-without-accessibility";
  gEditorAccessibilityEnabled = false;
  return;
#else
  if (!gState.document) {
    gEditorAccessibilityUnavailable = "no-document";
    return;
  }
  if (!LIBREOFFICEKIT_DOCUMENT_HAS(gState.document, setAccessibilityState)) {
    gEditorAccessibilityUnavailable = "lok-lacks-setAccessibilityState";
    return;
  }
  if (!LIBREOFFICEKIT_DOCUMENT_HAS(gState.document, getView)) {
    gEditorAccessibilityUnavailable = "lok-lacks-getView";
    return;
  }
  if (!LIBREOFFICEKIT_DOCUMENT_HAS(gState.document,
                                   getA11yFocusedParagraph)) {
    gEditorAccessibilityUnavailable = "lok-lacks-getA11yFocusedParagraph";
    return;
  }
  gEditorAccessibilityUnavailable = "";
  const int viewId = gState.document->pClass->getView(gState.document);
  if (gEditorAccessibilityEnabled)
    gState.document->pClass->setAccessibilityState(gState.document, viewId,
                                                   false);
  gState.document->pClass->setAccessibilityState(gState.document, viewId,
                                                 true);
  gEditorAccessibilityEnabled = true;
#endif
}

#ifndef OXSDK_E2_V23_LINK_BATCH
void completePendingEditorOperation(int callbackType) {
  const bool matches = callbackType == gEditorPending.requiredCallback ||
                       (gEditorPending.requiredCallback ==
                            EditorCaretOrSelectionCallback &&
                        (callbackType ==
                             LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR ||
                         callbackType == LOK_CALLBACK_TEXT_SELECTION)) ||
                       (gEditorPending.requiredCallback ==
                            EditorMutationCallback &&
                        (callbackType == LOK_CALLBACK_INVALIDATE_TILES ||
                         callbackType ==
                             LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR ||
                         callbackType == LOK_CALLBACK_TEXT_SELECTION));
  if (gEditorPending.requestId == 0 || !matches)
    return;
  const EditorPendingOperation pending = gEditorPending;
  gEditorPending = EditorPendingOperation{};
  if (pending.mutation)
    advanceRevision();
  std::ostringstream json;
  // Asked for before the state is serialised, because the a11y CALLBACK is
  // gated on the paragraph's text changing: a click that moves the caret to a
  // paragraph reading the same as the last one emits nothing, and the answer
  // would describe wherever the caret was before.
  if (pending.caret)
    refreshCaretParagraph();
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion << ",\"type\":\""
       << (pending.caret ? "editor-caret-placed"
                         : pending.selection ? "editor-selection-completed"
                                             : "editor-action-completed")
       << "\",\"requestId\":" << pending.requestId
       << ",\"documentHandle\":" << pending.documentHandle;
  if (pending.caret) {
    json << ",\"revision\":" << gState.revision;
  } else if (pending.selection) {
    json << ",\"revision\":" << gState.revision << ",\"method\":\""
         << jsonEscape(pending.name.c_str()) << "\"";
  } else {
    json << ",\"beforeRevision\":" << pending.beforeRevision
         << ",\"revision\":" << gState.revision << ",\"action\":\""
         << jsonEscape(pending.name.c_str()) << "\",\"option\":"
         << (pending.option ? "true" : "false") << ",\"changed\":"
         << (pending.mutation ? "true" : "false");
  }
  json << ",\"completion\":\"documented-callback-";
  switch (callbackType) {
  case LOK_CALLBACK_INVALIDATE_TILES:
    json << "invalidate-tiles";
    break;
  case LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR:
    json << "visible-cursor";
    break;
  case LOK_CALLBACK_TEXT_SELECTION:
    json << "text-selection";
    break;
  default:
    json << "unknown";
    break;
  }
  json << "\",\"callbackSequenceBefore\":" << pending.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence
       << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  finishAsynchronous(pending.requestId);
}
#endif

// SPEC E1-D bounded completion.  Runs only when a product range-select armed a
// readback deadline and no LOK_CALLBACK_TEXT_SELECTION arrived before it.  That
// happens when the requested range selects nothing and nothing was selected
// before: no state changed, so core had nothing to broadcast.
//
// This does not turn a timeout into a success.  It reports the selection that
// is actually there, read back at the deadline -- normally "none" -- under its
// own completion name so callers can tell the two paths apart.  Callers judge
// by the reported selection, never by the fact that the call returned.
#ifndef OXSDK_E2_V23_LINK_BATCH
void completePendingEditorSelectByReadback() {
  if (gEditorPending.requestId == 0 ||
      !(gEditorPending.selection || gEditorPending.caret) ||
      !gEditorPending.readbackDeadlineArmed) {
    return;
  }
  const EditorPendingOperation pending = gEditorPending;
  gEditorPending = EditorPendingOperation{};
  if (pending.caret)
    refreshCaretParagraph();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\""
       << (pending.caret ? "editor-caret-placed"
                         : "editor-selection-completed")
       << "\",\"requestId\":"
       << pending.requestId << ",\"documentHandle\":"
       << pending.documentHandle << ",\"revision\":" << gState.revision
       << ",\"method\":\"" << jsonEscape(pending.name.c_str())
       << "\",\"completion\":\""
       << (pending.caret ? "verified-caret-readback"
                         : "verified-selection-readback")
       << "\""
       << ",\"callbackSequenceBefore\":" << pending.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence
       << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  finishAsynchronous(pending.requestId);
}
#endif

// FINDING 096 bounded completion, and the same discipline as the two above.
//
// WHAT IT IS FOR.  A movement key pressed at a document boundary moves nothing,
// so core broadcasts nothing, so the callback this operation is waiting for
// never arrives.  That was not deduced: three explanations were pre-registered
// and two were excluded by measurement -- the engine thread was answering
// commands after the verdict (20/20) and no LOK_CALLBACK_INVALIDATE_VISIBLE_
// CURSOR and no LOK_CALLBACK_TEXT_SELECTION reached the window in any attempt,
// while the press one earlier produced one and completed in 37-39 ms
// (findings/evidence/096/RESULT-engine-side.md).
//
// CORE MAY BE ENTIRELY RIGHT.  At a boundary there is genuinely nothing to
// broadcast.  The defect this answers is the engine's, and it is exactly the
// one E1-D's comment names 250 lines above: treating "nothing moved" as "still
// waiting".
//
// THIS DOES NOT TURN A TIMEOUT INTO A SUCCESS, and the shape says so twice.
// `changed` is false and the revision is the one the operation started from --
// both are claims about the DOCUMENT, and both are true whether or not the
// caret moved.  The completion carries its own name, so a caller can tell a
// readback from a broadcast; what it must NOT be is an error, because the
// host's disposition for an editor error is to block the queue and offer a
// rollback, and a boundary press is not a failure the user should be asked to
// recover from.
//
// WHY IT IS NOT REACHED FROM `mainLoopDrainCommands`.  That loop synthesises
// deadline steps for the two barriers and for neither readback deadline, so
// the OXSDK_MAINLOOP_ENGINE profiles keep the pure callback semantics -- which
// is the rule the select path already states in EditorPendingOperation's own
// comment ("the diagnostic profiles keep the pure callback semantics the
// findings were measured against"), and finding 018's attribution turns on
// exactly that difference.  The shipped and candidate profiles are built
// WITHOUT that define, so the product reaches this through engineLoop.
// DEFAULT CONCLUSION IF THIS IS NEVER REVISITED: an attribution profile
// relinked in the future still wedges at a boundary, on purpose, and anyone
// measuring 096 there is measuring the unbounded path deliberately.
#ifndef OXSDK_E2_V23_LINK_BATCH
void completePendingEditorActionByReadback() {
  if (gEditorPending.requestId == 0 || gEditorPending.selection ||
      gEditorPending.caret || !gEditorPending.readbackDeadlineArmed) {
    return;
  }
  const EditorPendingOperation pending = gEditorPending;
  gEditorPending = EditorPendingOperation{};
  // Asked for, not waited for -- the same reason handleEditorGetState gives:
  // the a11y callback is gated on the paragraph's TEXT changing, so a state
  // serialised without this would describe the last paragraph that differed
  // rather than the one the caret is in.
  refreshCaretParagraph();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-action-completed\",\"requestId\":"
       << pending.requestId << ",\"documentHandle\":" << pending.documentHandle
       << ",\"beforeRevision\":" << pending.beforeRevision
       << ",\"revision\":" << gState.revision << ",\"action\":\""
       << jsonEscape(pending.name.c_str()) << "\",\"option\":"
       << (pending.option ? "true" : "false")
       << ",\"changed\":false,\"completion\":\"verified-move-readback\""
       << ",\"callbackSequenceBefore\":" << pending.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence
       << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  finishAsynchronous(pending.requestId);
}
#endif
#endif

void emitStage(const char *stage) {
  gStage = stage;
  const auto heapSize =
      static_cast<unsigned long long>(emscripten_get_heap_size());
  const auto heapBreak =
      static_cast<unsigned long long>(*emscripten_get_sbrk_ptr());
  std::ostringstream json;
  json << "{\"type\":\"stage\",\"name\":\"" << jsonEscape(stage)
       << "\",\"heapBytes\":" << heapSize << ",\"sbrk\":" << heapBreak << "}";
  emitJson(json.str());
}

std::string kitError() {
  if (!gState.kit || !gState.kit->pClass || !gState.kit->pClass->getError)
    return "LibreOfficeKit did not provide an error message";

  char *error = gState.kit->pClass->getError(gState.kit);
  if (!error)
    return "LibreOfficeKit did not provide an error message";

  std::string result(error);
  if (gState.kit->pClass->freeError)
    gState.kit->pClass->freeError(error);
  return result;
}

void emitSdkError(std::uint32_t requestId, std::uint32_t documentHandle,
                  const char *operation, const char *code,
                  const std::string &message) {
#ifdef OXSDK_E2_V23_LINK_BATCH
  if (gOrderedDispatching) {
    setOrderedReply([requestId, documentHandle, operation = std::string(operation), code = std::string(code), message] { emitSdkError(requestId, documentHandle, operation.c_str(), code.c_str(), message); });
    return;
  }
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << requestId
       << ",\"documentHandle\":" << documentHandle
       << ",\"revision\":" << gCallbackRevision.load(std::memory_order_acquire)
       << ",\"operation\":\"" << jsonEscape(operation) << "\",\"code\":\""
       << jsonEscape(code) << "\",\"message\":\"" << jsonEscape(message.c_str())
       << "\",\"where\":\"" << jsonEscape(operation) << "\",\"msg\":\""
       << jsonEscape(message.c_str()) << "\"}";
  emitJson(json.str());
}

void emitStaleRevision(const Command &command, const char *operation) {
#ifdef OXSDK_E2_V23_LINK_BATCH
  if (gOrderedDispatching) {
    setOrderedReply([command, operation = std::string(operation)] { emitStaleRevision(command, operation.c_str()); });
    return;
  }
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << command.documentHandle
       << ",\"revision\":" << gState.revision << ",\"operation\":\""
       << jsonEscape(operation) << "\",\"code\":\"STALE_REVISION\""
       << ",\"expectedRevision\":" << command.expectedRevision
       << ",\"currentRevision\":" << gState.revision
       << ",\"message\":\"expected revision " << command.expectedRevision
       << " but current revision is " << gState.revision << "\"}";
  emitJson(json.str());
}

std::uint32_t capabilityBits() {
  return oxsdk_capabilities();
}

void emitCommandError(const Command &command, const char *operation,
                      const char *code, const std::string &message) {
  if (command.sdk)
    emitSdkError(command.requestId, command.documentHandle, operation, code,
                 message);
  else
    emitError(operation, message);
}

void emitReady(const Command &command) {
#ifdef OXSDK_E2_V23_LINK_BATCH
  if (gOrderedDispatching) {
    setOrderedReply([command] { emitReady(command); });
    return;
  }
#endif
  if (!command.sdk) {
    if (gState.kit)
      emitJson("{\"type\":\"ready\"}");
    else
      emitError("start", "LibreOfficeKit initialization failed");
    return;
  }

  if (!gState.kit) {
    emitSdkError(command.requestId, 0, "start", "LOK_INIT_FAILED",
                 "LibreOfficeKit initialization failed");
    return;
  }

  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"ready\",\"requestId\":" << command.requestId
       << ",\"abiVersion\":" << OXSDK_ABI_VERSION << ",\"capabilities\":"
       << capabilityBits()
       << "}";
  emitJson(json.str());
}

SubmitStatus submit(Command command) {
  if (!gStarted.load(std::memory_order_acquire))
    return SubmitStatus::NotStarted;

  {
    std::lock_guard<std::mutex> lock(gState.mutex);
    if (command.sdk) {
      if (command.requestId == 0)
        return SubmitStatus::InvalidArgument;
      if (gState.pendingRequests.count(command.requestId) ||
          gState.executingRequest == command.requestId ||
          gState.asynchronousRequests.count(command.requestId)) {
        return SubmitStatus::DuplicateRequest;
      }
      gState.pendingRequests.insert(command.requestId);
    }
    gState.commands.push_back(std::move(command));
  }
  gState.condition.notify_one();
  return SubmitStatus::Ok;
}

bool requireDocument(const Command &command, const char *operation) {
  if (!gState.document) {
    emitCommandError(command, operation, "NO_DOCUMENT", "no document is open");
    return false;
  }
  if (command.sdk && command.documentHandle != gState.documentHandle) {
    emitCommandError(
        command, operation, "INVALID_HANDLE",
        "document handle is closed or does not belong to this engine");
    return false;
  }
  return true;
}

bool requireRevision(const Command &command, const char *operation) {
  if (command.expectedRevision == gState.revision)
    return true;
  emitStaleRevision(command, operation);
  return false;
}

void markAsynchronous(std::uint32_t requestId) {
  std::lock_guard<std::mutex> lock(gState.mutex);
  gState.asynchronousRequests.insert(requestId);
}

void finishAsynchronous(std::uint32_t requestId) {
  if (requestId == 0)
    return;
  std::lock_guard<std::mutex> lock(gState.mutex);
  gState.asynchronousRequests.erase(requestId);
}

void advanceRevision() {
  ++gState.revision;
  gCallbackRevision.store(gState.revision, std::memory_order_release);
}

void closeDocument(const Command *command) {
  const std::uint32_t closedHandle = gState.documentHandle;
  gOpenRequestId.store(0, std::memory_order_release);
  gCallbackDocumentHandle.store(0, std::memory_order_release);
  if (gState.document) {
// The viewer emits them too (SPEC-M4 addendum 1): its memory criterion E6 is
// read from the stage lines, and without these it sees none after the open.
#if defined(OXSDK_DIAGNOSTIC_CLOSE_STAGES) || defined(OXSDK_ODS_VIEWER)
    emitStage("document-destroy-enter");
#endif
    gState.document->pClass->destroy(gState.document);
#if defined(OXSDK_DIAGNOSTIC_CLOSE_STAGES) || defined(OXSDK_ODS_VIEWER)
    emitStage("document-destroy-return");
#endif
    gState.document = nullptr;
  }
  gState.documentHandle = 0;
  gState.revision = 0;
  gCallbackRevision.store(0, std::memory_order_release);
#ifdef OXSDK_EDITOR_DISCOVERY
  gEditorState = EditorState{};
  gEditorPending = EditorPendingOperation{};
#ifdef OXSDK_E2_FORMAT_BARRIER
  gFormatBarrier = FormatStateBarrier{};
#endif
  gEditorUnoAction.clear();
  gEditorUnoCommand.clear();
  gEditorUnoBeforeRevision = 0;
  gEditorUnoBeforeSequence = 0;
  gEditorUnoSemanticReadback = false;
  gEditorAccessibilityEnabled = false;
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
  gSelectionBarrier = SelectionBarrierTransaction{};
#endif
#if defined(OXSDK_MERGE_KEY_UNDO) && !defined(OXSDK_E2_V23_LINK_BATCH)
  {
    // Review N6: no caret of this document may become P in the next one.
    std::lock_guard<std::mutex> merge(gMergeMutex);
    gMergeAttribution = probe::merge::Attribution{};
    gMergeTicket = MergeTicket{};
  }
#endif
#endif

  if (!command)
    return;
#ifdef OXSDK_E2_V23_LINK_BATCH
  const Command replyCommand = *command;
  setOrderedReply([replyCommand, closedHandle] {
    const Command *command = &replyCommand;
#endif
  if (!command->sdk) {
    emitJson("{\"type\":\"closed\"}");
    return;
  }

  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"closed\",\"requestId\":" << command->requestId
       << ",\"documentHandle\":" << closedHandle << ",\"revision\":0}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

#ifdef OXSDK_ODS_VIEWER
// SPEC-M4-ods-in-nextcloud §3.2 (W7c-e, B1): the viewer's document-level
// queries.  Each runs whole on the engine thread and replies once.

static_assert(LOK_DOCTYPE_TEXT == 0 && LOK_DOCTYPE_SPREADSHEET == 1 &&
                  LOK_DOCTYPE_PRESENTATION == 2 && LOK_DOCTYPE_DRAWING == 3 &&
                  LOK_DOCTYPE_OTHER == 4,
              "probe::odsviewer::documentTypeName numbers LOK's document types");

// part_text's SelectAll is waited for ON THE ENGINE THREAD.  While it waits,
// nothing else in the queue runs, so no paint lands between the switch, the
// selection and the switch back -- the viewer never shows a selection.  The
// barrier is LOK_CALLBACK_UNO_COMMAND_RESULT: postUnoCommand(..., true) queues
// it on the view's callback flush handler (desktop/source/lib/init.cxx,
// DispatchResultListener::dispatchFinished), and it arrives from LOK's own
// thread.  Its own mutex, never gState.mutex.  If it has not come by the
// deadline the text is read anyway and the reply says `selectAllConfirmed:
// false` (SPEC-M4 addendum 4): a notification that never comes must not need a
// relink to see past.  A SelectAll that lands after the deadline finds `active`
// false and is ignored; readPartText has reset the selection and put the part
// back by then (registered: that late selection stays, SPEC-M4 §8).
#ifdef OXSDK_ODS_VIEWER_V2
// SPEC-M4-viewer-v2 3.3 (finding 160): 3 s was not always enough under a
// corpus sweep (2 of 482 reads once, 0 of 464 twice).  Each reply now says how
// long the wait took and how many SelectAll results came while nobody was
// waiting, so a read that is still unconfirmed says whether its result was
// late or never came.
constexpr int kPartTextSelectAllDeadlineMs = 10000;
#else
constexpr int kPartTextSelectAllDeadlineMs = 3000;
#endif

struct PartTextAwait {
  std::mutex mutex;
  std::condition_variable condition;
  bool active = false;
  bool done = false;
#ifdef OXSDK_ODS_VIEWER_V2
  // Arrived with `active` false: after its deadline, or unasked.  Read and
  // reset by the next part-text reply, so a late one is counted there.
  int lateResults = 0;
#endif
};
PartTextAwait gPartTextAwait;

void notePartTextUnoResult(const char *payload) {
  if (!payload || std::strstr(payload, "\".uno:SelectAll\"") == nullptr)
    return;
  {
    std::lock_guard<std::mutex> lock(gPartTextAwait.mutex);
#ifdef OXSDK_ODS_VIEWER_V2
    if (!gPartTextAwait.active)
      ++gPartTextAwait.lateResults;
#endif
    if (!gPartTextAwait.active)
      return;
    gPartTextAwait.done = true;
  }
  gPartTextAwait.condition.notify_all();
}

#ifdef OXSDK_ODS_VIEWER_V2
int takeLatePartTextResults() {
  std::lock_guard<std::mutex> lock(gPartTextAwait.mutex);
  const int late = gPartTextAwait.lateResults;
  gPartTextAwait.lateResults = 0;
  return late;
}

// SPEC-M4-viewer-v2 8 (finding 160): every unconfirmed SelectAll of six corpus
// sweeps had LOK's "Failed to dispatch .uno:SelectAll" beside it, and no other
// read did.  doc_postUnoCommand clears the error first and sets that one when
// comphelper::dispatchCommand finds nothing to dispatch to, so the error
// right after the post says whether the post was dispatched.
constexpr int kPartTextRedispatchPauseMs = 50;

bool lokSaidNotDispatched() {
  if (!gState.kit || !gState.kit->pClass || !gState.kit->pClass->getError)
    return false;
  char *error = gState.kit->pClass->getError(gState.kit);
  const bool failed =
      error && std::strstr(error, "Failed to dispatch") != nullptr;
  if (error && gState.kit->pClass->freeError)
    gState.kit->pClass->freeError(error);
  return failed;
}

// selectAllUntilDispatched's Poster (src/ods_viewer.hpp), on LOK.
struct PartTextSelectAllPoster {
  LibreOfficeKitDocument *document;
  std::chrono::steady_clock::time_point started;

  bool post() {
    document->pClass->postUnoCommand(document, ".uno:SelectAll", nullptr, true);
    return !lokSaidNotDispatched();
  }
  bool await(int ms) {
    std::unique_lock<std::mutex> lock(gPartTextAwait.mutex);
    const bool landed = gPartTextAwait.condition.wait_for(
        lock, std::chrono::milliseconds(ms), [] { return gPartTextAwait.done; });
    gPartTextAwait.active = false;
    return landed;
  }
  int elapsedMs() const {
    return static_cast<int>(
        std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - started)
            .count());
  }
  void pause(int ms) {
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
  }
};
#endif

// readPartText's document, on LOK.  The text is read the way the native
// oracle reads its expected text (tools/ods_native_oracle.cpp): getTextSelection
// as text/plain;charset=utf-8, not the selection-type readback.
struct LokPartTextDocument {
  LibreOfficeKitDocument *document;
#ifdef OXSDK_ODS_VIEWER_V2
  int selectAllWaitMs = -1; // -1: selectAll() was not reached
#endif

  int parts() { return document->pClass->getParts(document); }
  int part() { return document->pClass->getPart(document); }
  void setPart(int k) { document->pClass->setPart(document, k); }
  bool selectAll() {
    {
      std::lock_guard<std::mutex> lock(gPartTextAwait.mutex);
      gPartTextAwait.active = true;
      gPartTextAwait.done = false;
    }
#ifdef OXSDK_ODS_VIEWER_V2
    // A post LOK did not dispatch is posted again until the deadline.  The
    // engine's line beside LOK's own warnings says how many posts this read
    // took, so the two can be matched in the worker's stderr.
    PartTextSelectAllPoster poster{document, std::chrono::steady_clock::now()};
    const probe::odsviewer::SelectAllAttempt attempt =
        probe::odsviewer::selectAllUntilDispatched(
            poster, kPartTextSelectAllDeadlineMs, kPartTextRedispatchPauseMs);
    {
      std::lock_guard<std::mutex> lock(gPartTextAwait.mutex);
      gPartTextAwait.active = false;
    }
    selectAllWaitMs = poster.elapsedMs();
    if (attempt.dispatchFailures > 0)
      std::fprintf(stderr,
                   "oxsdk part-text: .uno:SelectAll not dispatched %d time(s), "
                   "%s\n",
                   attempt.dispatchFailures,
                   attempt.dispatched ? "then dispatched" : "never dispatched");
    return attempt.confirmed;
#else
    document->pClass->postUnoCommand(document, ".uno:SelectAll", nullptr, true);
    std::unique_lock<std::mutex> lock(gPartTextAwait.mutex);
    const bool landed = gPartTextAwait.condition.wait_for(
        lock, std::chrono::milliseconds(kPartTextSelectAllDeadlineMs),
        [] { return gPartTextAwait.done; });
    gPartTextAwait.active = false;
    return landed;
#endif
  }
  bool text(std::string &out) {
    char *used = nullptr;
    char *value = document->pClass->getTextSelection(
        document, "text/plain;charset=utf-8", &used);
    std::free(used);
    if (!value)
      return false;
    out = value;
    std::free(value);
    return true;
  }
  void resetSelection() { document->pClass->resetSelection(document); }
};

void emitPartReply(const Command &command, const char *type,
                   const std::string &fields) {
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion << ",\"type\":\""
       << type << "\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << fields << "}";
  emitJson(json.str());
}

bool requirePartInRange(const Command &command, const char *operation,
                        int part) {
  const int parts = gState.document->pClass->getParts(gState.document);
  if (probe::odsviewer::partInRange(part, parts))
    return true;
  emitCommandError(command, operation, "INVALID_ARGUMENT",
                   "part " + std::to_string(part) + " is not in 0.." +
                       std::to_string(parts - 1));
  return false;
}

// W7c.  The reply's part is READ after the switch, and the size is the new
// part's.  It is also what the next paint's documentSizeChanged compares
// against: the client has just been told this size (finding 062's "as of the
// last time the client looked").
void handleSetPart(const Command &command) {
  if (!requireDocument(command, "part-set") ||
      !requirePartInRange(command, "part-set", command.values[0]))
    return;
  if (gState.document->pClass->getPart(gState.document) != command.values[0])
    gState.document->pClass->setPart(gState.document, command.values[0]);
  long width = 0;
  long height = 0;
  gState.document->pClass->getDocumentSize(gState.document, &width, &height);
  gState.documentWidthTwips = width;
  gState.documentHeightTwips = height;
  std::ostringstream fields;
  fields << ",\"part\":" << gState.document->pClass->getPart(gState.document)
         << ",\"width\":" << width << ",\"height\":" << height;
  emitPartReply(command, "part-set", fields.str());
}

// W7d.
void handleCurrentPart(const Command &command) {
  if (!requireDocument(command, "current-part"))
    return;
  std::ostringstream fields;
  fields << ",\"part\":" << gState.document->pClass->getPart(gState.document);
  emitPartReply(command, "current-part", fields.str());
}

// W7e.
void handlePartName(const Command &command) {
  if (!requireDocument(command, "part-name") ||
      !requirePartInRange(command, "part-name", command.values[0]))
    return;
  char *name =
      gState.document->pClass->getPartName(gState.document, command.values[0]);
  if (!name) {
    emitCommandError(command, "part-name", "LOK_ERROR", kitError());
    return;
  }
  std::ostringstream fields;
  fields << ",\"part\":" << command.values[0] << ",\"name\":\""
         << jsonEscape(name) << "\"";
  std::free(name);
  emitPartReply(command, "part-name", fields.str());
}

// B1.  The order and what is restored on every exit are readPartText's.
void handlePartText(const Command &command) {
  if (!requireDocument(command, "part-text"))
    return;
  LokPartTextDocument document{gState.document};
  const probe::odsviewer::PartTextResult result =
      probe::odsviewer::readPartText(document, command.values[0]);
  if (result.status != probe::odsviewer::PartTextStatus::Ok) {
    emitCommandError(command, "part-text",
                     probe::odsviewer::partTextStatusCode(result.status),
                     "part " + std::to_string(command.values[0]) +
                         " is not a part of this document");
    return;
  }
  std::ostringstream fields;
  fields << ",\"part\":" << command.values[0] << ",\"text\":\""
         << jsonEscape(result.text.c_str()) << "\",\"textNull\":"
         << (result.textNull ? "true" : "false") << ",\"selectAllConfirmed\":"
         << (result.selectAllConfirmed ? "true" : "false")
         << ",\"partBefore\":" << result.partBefore
         << ",\"partAfter\":" << result.partAfter;
#ifdef OXSDK_ODS_VIEWER_V2
  fields << ",\"selectAllWaitMs\":" << document.selectAllWaitMs
         << ",\"selectAllDeadlineMs\":" << kPartTextSelectAllDeadlineMs
         << ",\"lateSelectAllResults\":" << takeLatePartTextResults();
#endif
  emitPartReply(command, "part-text", fields.str());
}

#ifdef OXSDK_ODS_VIEWER_V2
// SPEC-M4-viewer-v2 3.1 (finding 157).  ScTabControl inserts a page only for a
// visible sheet, so setPart to a hidden one does nothing and the read-back
// stays on the previous sheet; the page has to know before it offers the tab.
// LOK's JSON goes through as a string, parsed by the SDK, as page-rectangles'
// does.  Core answers "" without a view (ScDocShell::GetViewData()): that is
// an error here, not a visible sheet.
void handlePartInfo(const Command &command) {
  if (!requireDocument(command, "part-info") ||
      !requirePartInRange(command, "part-info", command.values[0]))
    return;
  char *info =
      gState.document->pClass->getPartInfo(gState.document, command.values[0]);
  if (!info || info[0] == '\0') {
    const std::string message =
        info ? "getPartInfo returned an empty string" : kitError();
    std::free(info);
    emitCommandError(command, "part-info", "LOK_ERROR", message);
    return;
  }
  std::ostringstream fields;
  fields << ",\"part\":" << command.values[0] << ",\"info\":\""
         << jsonEscape(info) << "\"";
  std::free(info);
  emitPartReply(command, "part-info", fields.str());
}
#endif
#endif

#ifdef OXSDK_E2_V23_LINK_BATCH
#include "ordered_engine_reply.inc"
#endif

void onLokCallback(int type, const char *payload, void *) {
  const std::uint32_t documentHandle =
      gCallbackDocumentHandle.load(std::memory_order_acquire);
  const std::uint32_t revision =
      gCallbackRevision.load(std::memory_order_acquire);
  std::ostringstream json;
  json << "{\"type\":\"lok\",\"id\":" << type << ",\"payload\":\""
       << jsonEscape(payload) << "\",\"documentHandle\":" << documentHandle
       << ",\"revision\":" << revision << "}";
  emitJson(json.str());

#ifdef OXSDK_EDITOR_DISCOVERY
#if defined(OXSDK_MERGE_KEY_UNDO) && !defined(OXSDK_E2_V23_LINK_BATCH)
  feedMergeAttribution(type, payload);
#endif
  bool editorStateChanged = false;
  const char *editorSource = nullptr;
  switch (type) {
  case LOK_CALLBACK_INVALIDATE_TILES:
    editorStateChanged = true;
    editorSource = "invalidate-tiles";
    break;
  case LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR:
    editorStateChanged = parseEditorRectangle(payload, gEditorState.caret);
    editorSource = editorStateChanged ? "visible-cursor" : nullptr;
    break;
  case LOK_CALLBACK_TEXT_SELECTION:
    editorStateChanged = parseEditorSelectionRectangles(
        payload, gEditorState.selectionRectangles);
    if (editorStateChanged)
      gEditorState.selectionObserved = true;
    editorSource = editorStateChanged ? "selection-rectangles" : nullptr;
    break;
  case LOK_CALLBACK_TEXT_SELECTION_START:
    editorStateChanged =
        parseEditorRectangle(payload, gEditorState.selectionStart);
    editorSource = editorStateChanged ? "selection-start" : nullptr;
    break;
  case LOK_CALLBACK_TEXT_SELECTION_END:
    editorStateChanged = parseEditorRectangle(payload, gEditorState.selectionEnd);
    editorSource = editorStateChanged ? "selection-end" : nullptr;
    break;
  case LOK_CALLBACK_CURSOR_VISIBLE:
    if (payload && (std::strcmp(payload, "true") == 0 ||
                    std::strcmp(payload, "false") == 0)) {
      gEditorState.cursorVisible = std::strcmp(payload, "true") == 0;
      editorStateChanged = true;
      editorSource = "cursor-visible";
    }
    break;
  case LOK_CALLBACK_STATE_CHANGED:
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
    updateEditorSchedulerProbeState(payload);
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
    // Finding 021 attribution.  "No format state arrived" has two causes that
    // the parsed events alone cannot separate: core never sent one, or core
    // sent one this build failed to recognise.  Counting arrivals here -- the
    // count only, never the payload -- separates them without widening the
    // callback surface.
    ++gEditorState.stateChangedTotal;
#endif
    updateEditorFormatState(payload);
    break;
  case LOK_CALLBACK_A11Y_FOCUS_CHANGED: {
    // Only counted when the documented payload parses; a malformed payload
    // must not be recorded as an observed content change.
    EditorSemanticSnapshot snapshot;
    if (payload && parseEditorSemanticJson(std::string(payload), snapshot)) {
      gEditorState.a11yObserved = true;
      ++gEditorState.a11yChangeCount;
      gEditorState.a11yContentLength = snapshot.contentLength;
      gEditorState.a11yPosition = snapshot.position;
      gEditorState.a11yContentHash = snapshot.contentHash;
      gEditorState.a11yFingerprintUsable = snapshot.fingerprintUsable;
      gEditorState.a11yListPrefixLength = snapshot.listPrefixLength;
#ifdef OXSDK_A11Y_PARAGRAPH_TEXT
      gEditorState.a11yParagraphText = snapshot.content;
#endif
      editorStateChanged = true;
      editorSource = "a11y-paragraph-changed";
    } else {
      // Counted separately so that "no content change was reported" stays
      // distinguishable from "the callback arrived but could not be read".
      ++gEditorState.a11yUnparsedCount;
    }
    break;
  }
#ifdef OXSDK_E2_V20_LINK_BATCH
  case LOK_CALLBACK_DOCUMENT_SIZE_CHANGED:
    // SPEC-M3-link-batch 12.3: counted on every arrival, and the arrival
    // PUSHES editor-state by itself -- until this case the switch pushed
    // seven callback types and this was not one of them, so a page added by
    // typing announced nothing the page could re-read on.  The payload is
    // not parsed and not forwarded; the page re-reads `page-rectangles`.
    ++gEditorState.documentSizeChangedCount;
    editorStateChanged = true;
    editorSource = "document-size-changed";
    break;
#endif
  default:
    break;
  }
  if (editorStateChanged) {
    ++gEditorState.sourceSequence;
    if (type == LOK_CALLBACK_INVALIDATE_TILES)
      gEditorState.documentChangeSequence = gEditorState.sourceSequence;
    if (type == LOK_CALLBACK_A11Y_FOCUS_CHANGED)
      gEditorState.a11yLastSequence = gEditorState.sourceSequence;
#ifdef OXSDK_E2_FORMAT_BARRIER
    // Finding 021: the caret moved, so whatever paragraph format state is
    // cached now describes some *other* paragraph until a fresh payload
    // arrives.  Marking it here is what lets the precondition tell "known for
    // this paragraph" from "known for the previous one" -- without it, the
    // no-op check silently answers for the wrong paragraph.
    if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR ||
        type == LOK_CALLBACK_TEXT_SELECTION ||
        type == LOK_CALLBACK_TEXT_SELECTION_START ||
        type == LOK_CALLBACK_TEXT_SELECTION_END)
      gEditorState.formatStateStale = true;
#endif
    emitEditorStateEvent(editorSource);
#ifndef OXSDK_E2_V23_LINK_BATCH
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
    handleSelectionBarrierStateCallback(type);
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
    handleFormatBarrierStateCallback(type);
#endif
    completePendingEditorOperation(type);
#endif
  } else if (type >= LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR &&
             type <= LOK_CALLBACK_CURSOR_VISIBLE && editorSource == nullptr) {
    std::ostringstream parseError;
    parseError << "{\"schemaVersion\":" << ProtocolSchemaVersion
               << ",\"type\":\"editor-callback-parse-error\",\"requestId\":0"
               << ",\"documentHandle\":" << documentHandle
               << ",\"revision\":" << revision << ",\"callbackId\":"
               << type << "}";
    emitJson(parseError.str());
  }
#endif

#ifdef OXSDK_E2_V23_LINK_BATCH
  // Cache/evidence only. The pending command owns the first-poll composer.
  if (gOrderedDispatching || gOrderedReply) {
    probe::ordered::recordParsedCallback(gOrderedProof.callbacks, type,
        editorStateChanged, gEditorState.sourceSequence);
    if (type == 70 && payload && std::strstr(payload, "afterCallbackRegistered invoked"))
      gOrderedProof.viewReady = true;
    if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
      for (auto &entry : gOrderedProof.uno) {
        if (commandResultMatches(payload, entry.first)) {
          entry.second = {true, payload ? payload : "", gEditorState.sourceSequence};
        }
      }
    }
    if (type == LOK_CALLBACK_SEARCH_RESULT_SELECTION || type == LOK_CALLBACK_SEARCH_NOT_FOUND) {
      gOrderedProof.searchType = type;
      gOrderedProof.searchPayload = payload ? payload : "";
    }
    if (type == LOK_CALLBACK_COMMENT && payload &&
        std::strstr(payload, "\"action\": \"Add\"")) {
      gOrderedProof.commentAdded = true;
      gOrderedProof.commentPayload = payload;
    }
  }
#else
  if (type == 70 && payload &&
      std::strstr(payload, "afterCallbackRegistered invoked")) {
    const std::uint32_t requestId =
        gOpenRequestId.exchange(0, std::memory_order_acq_rel);
    if (requestId != 0) {
      std::ostringstream ready;
      ready << "{\"schemaVersion\":" << ProtocolSchemaVersion
            << ",\"type\":\"view-ready\",\"requestId\":" << requestId
            << ",\"documentHandle\":" << documentHandle
            << ",\"revision\":" << revision << "}";
      emitJson(ready.str());
    }
  }

  if (type == LOK_CALLBACK_SEARCH_RESULT_SELECTION ||
      type == LOK_CALLBACK_SEARCH_NOT_FOUND) {
    const std::uint32_t requestId =
        gSearchRequestId.exchange(0, std::memory_order_acq_rel);
    if (requestId != 0) {
      const bool found = type == LOK_CALLBACK_SEARCH_RESULT_SELECTION;
#ifdef OXSDK_EDITOR_DISCOVERY
      // Search establishes a real Writer selection after the view has become
      // interactive.  Reattach here so the documented focused-paragraph
      // snapshot reflects that selection instead of an early empty focus.
#ifndef OXSDK_FINDING_016_SELECTION_BARRIER
      if (found)
        refreshEditorAccessibility();
#endif
#endif
      std::ostringstream result;
      result << "{\"schemaVersion\":" << ProtocolSchemaVersion
             << ",\"type\":\"search-result\",\"requestId\":" << requestId
             << ",\"documentHandle\":" << documentHandle
             << ",\"revision\":" << revision << ",\"found\":"
             << (found ? "true" : "false") << ",\"query\":\""
             << jsonEscape(gSearchQuery.c_str()) << "\",\"resultPayload\":\""
             << jsonEscape(payload) << "\"}";
      gSearchQuery.clear();
      emitJson(result.str());
      finishAsynchronous(requestId);
    }
  }

  if (type == LOK_CALLBACK_COMMENT &&
      gUnoOperation == "comment-added" && payload &&
      std::strstr(payload, "\"action\": \"Add\"") != nullptr) {
    const std::uint32_t requestId =
        gUnoRequestId.exchange(0, std::memory_order_acq_rel);
    if (requestId != 0) {
      gUnoOperation.clear();
      advanceRevision();
      std::ostringstream result;
      result << "{\"schemaVersion\":" << ProtocolSchemaVersion
             << ",\"type\":\"comment-added\",\"requestId\":" << requestId
             << ",\"documentHandle\":" << documentHandle
             << ",\"revision\":" << gState.revision
             << ",\"resultPayload\":\"" << jsonEscape(payload) << "\"}";
      emitJson(result.str());
      finishAsynchronous(requestId);
    }
  }

  if (type == LOK_CALLBACK_UNO_COMMAND_RESULT) {
#ifdef OXSDK_ODS_VIEWER
    notePartTextUnoResult(payload);
#endif
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
    if (handleSelectionBarrierUnoResult(payload))
      return;
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
    handleFormatBarrierUnoResult(payload);
#endif
    const std::uint32_t requestId =
        gUnoRequestId.load(std::memory_order_acquire);
    if (requestId != 0) {
#ifdef OXSDK_EDITOR_DISCOVERY
      if (gUnoOperation == "editor-action-completed") {
        gUnoRequestId.store(0, std::memory_order_release);
        gUnoOperation.clear();
        const std::string action = std::move(gEditorUnoAction);
        const std::string command = std::move(gEditorUnoCommand);
        gEditorUnoSemanticReadback = false;
        if (!commandResultMatches(payload, command)) {
          emitSdkError(requestId, documentHandle, "editor-action",
                       "LOK_RESULT_MISMATCH",
                       "fixed editor command returned an unexpected result");
          finishAsynchronous(requestId);
          return;
        }
        bool rejected = !commandResultSucceeded(payload);
#ifdef OXSDK_E2_FORMAT_BARRIER
        // Finding 059: for the four inline formats, `success` is not evidence
        // about the document.  Ask the document's own state instead, and only
        // fall back to reporting a failure when the state disagrees with what
        // was asked for.  Every other command keeps the old gate.
        if (rejected && inlineFormatArgumentResolved(command, gEditorUnoOption))
          rejected = false;
#endif
        if (rejected) {
          emitSdkError(requestId, documentHandle, "editor-action",
                       "LOK_COMMAND_FAILED",
                       "LibreOfficeKit rejected the fixed editor command");
          finishAsynchronous(requestId);
          return;
        }
        const bool manualObservation =
            gEditorUnoOption &&
            (action == "delete-backward" || action == "delete-forward");
        advanceRevision();
        std::ostringstream result;
        result << "{\"schemaVersion\":" << ProtocolSchemaVersion
               << ",\"type\":\"editor-action-completed\",\"requestId\":"
               << requestId << ",\"documentHandle\":" << documentHandle
               << ",\"beforeRevision\":" << gEditorUnoBeforeRevision
               << ",\"revision\":" << gState.revision << ",\"action\":\""
               << jsonEscape(action.c_str())
               << "\",\"option\":" << (gEditorUnoOption ? "true" : "false")
               << ",\"changed\":"
               << (manualObservation ? "null" : "true")
               << ",\"completion\":\""
               << (manualObservation
                       ? "uno-command-result-manual-observation"
                       : "uno-command-result")
               << "\"";
        if (manualObservation)
          result << ",\"manualVerificationRequired\":true";
        result
               << ",\"callbackSequenceBefore\":" << gEditorUnoBeforeSequence
               << ",\"callbackSequenceAfter\":"
               << gEditorState.sourceSequence << ",\"state\":{";
        appendEditorState(result);
        result << "}}";
        emitJson(result.str());
        finishAsynchronous(requestId);
        return;
      }
#endif
      if (gUnoOperation == "comment-added") {
        // InsertAnnotation enters comment edit mode. Commit it and wait for
        // LOK_CALLBACK_COMMENT Add before resolving the SDK operation.
        gState.document->pClass->postUnoCommand(gState.document, ".uno:Escape",
                                                nullptr, false);
        return;
      }
      gUnoRequestId.store(0, std::memory_order_release);
      const std::string operation = std::move(gUnoOperation);
      gUnoOperation.clear();
      // LOK reports success:false for several successful void commands.
      // Treat command-result as the completion barrier; semantic follow-up
      // queries verify undo and track-changes effects in the conformance flow.
      advanceRevision();
      std::ostringstream result;
      result << "{\"schemaVersion\":" << ProtocolSchemaVersion
             << ",\"type\":\"" << jsonEscape(operation.c_str())
             << "\",\"requestId\":" << requestId
             << ",\"documentHandle\":" << documentHandle
             << ",\"revision\":" << gState.revision
             << ",\"resultPayload\":\"" << jsonEscape(payload) << "\"}";
      emitJson(result.str());
      finishAsynchronous(requestId);
    }
  }
#endif
}

bool decodeUtf8(const std::string &text,
                std::vector<std::uint32_t> &codePoints) {
  const auto *bytes = reinterpret_cast<const unsigned char *>(text.data());
  std::size_t offset = 0;
  while (offset < text.size()) {
    std::uint32_t value = 0;
    std::size_t length = 0;
    const unsigned char first = bytes[offset];
    if (first < 0x80) {
      value = first;
      length = 1;
    } else if ((first & 0xe0) == 0xc0) {
      value = first & 0x1f;
      length = 2;
    } else if ((first & 0xf0) == 0xe0) {
      value = first & 0x0f;
      length = 3;
    } else if ((first & 0xf8) == 0xf0) {
      value = first & 0x07;
      length = 4;
    } else
      return false;

    if (offset + length > text.size())
      return false;
    for (std::size_t index = 1; index < length; ++index) {
      if ((bytes[offset + index] & 0xc0) != 0x80)
        return false;
      value = (value << 6) | (bytes[offset + index] & 0x3f);
    }

    const bool overlong = (length == 2 && value < 0x80) ||
                          (length == 3 && value < 0x800) ||
                          (length == 4 && value < 0x10000);
    if (overlong || value > 0x10ffff || (value >= 0xd800 && value <= 0xdfff))
      return false;

    codePoints.push_back(value);
    offset += length;
  }
  return true;
}

std::uint32_t allocateDocumentHandle() {
  std::uint32_t handle = gState.nextDocumentHandle++;
  if (handle == 0)
    handle = gState.nextDocumentHandle++;
  return handle;
}

#ifdef OXSDK_ODS_VIEWER
// Review M1: the file core loads carries the suffix the name was accepted
// under, so documentLoad sees `.ods` for a spreadsheet.  sdk_api.cpp refuses
// every other name before the queue; `.odt` is what a non-SDK open gets.
std::string inputSuffixFor(const Command &command) {
  const std::string suffix = probe::odsviewer::acceptedSuffix(command.name);
  return suffix.empty() ? ".odt" : suffix;
}
#endif

bool writeInputFile(const Command &command, std::string &fileUrl) {
#ifdef OXSDK_ODS_VIEWER
  const std::string path = "/tmp/oxsdk-input-" +
                           std::to_string(command.requestId) +
                           inputSuffixFor(command);
#else
  const std::string path =
      "/tmp/oxsdk-input-" + std::to_string(command.requestId) + ".odt";
#endif
  std::ofstream output(path, std::ios::binary | std::ios::trunc);
  if (!output)
    return false;
  output.write(reinterpret_cast<const char *>(command.bytes.data()),
               static_cast<std::streamsize>(command.bytes.size()));
  if (!output)
    return false;
  output.close();
  fileUrl = "file://" + path;
  return true;
}

void handleOpen(const Command &command) {
  if (command.sdk && gState.document) {
    emitCommandError(command, "open", "BUSY",
                     "R2 ABI v1 supports one open document per engine");
    return;
  }

  std::string fileUrl = command.text;
  if (command.sdk && !writeInputFile(command, fileUrl)) {
    emitCommandError(command, "open", "IO_ERROR",
                     "unable to write input bytes to MEMFS");
    return;
  }

  emitStage("open.begin");
  if (!gState.kit) {
    emitCommandError(command, "open", "LOK_INIT_FAILED",
                     "LibreOfficeKit initialization failed");
    return;
  }

  if (!command.sdk) {
    emitStage("open.close-previous");
    closeDocument(nullptr);
  }
  emitStage("open.documentLoad");
#ifdef OXSDK_E2_UI_LANGUAGE
  // Finding 031 measurement profile, discovery only.
  //
  // The paragraph-style postcondition compares whole strings against
  // "Heading 1" and "Body Text", and those come from core's UIName table,
  // which SwStyleNameMapper keys by UI language tag.  Nothing in this project
  // selects a language, so every reading so far has been en-US and the
  // comparison has always matched.  This profile asks for a language so the
  // two arms can be compared in one build.
  //
  // Language= is consumed by LOK itself (desktop/source/lib/init.cxx:2843-2866)
  // and sets comphelper::LibreOfficeKit::setLanguageTag / setLocale, which is
  // what SvtSysLocale::GetUILanguageTag reads back.  The tag is compiled in, so
  // JS cannot choose it and this stays a build-level experiment rather than a
  // surface.
  {
    const std::string options =
        std::string("Language=") + OXSDK_E2_UI_LANGUAGE;
    emitStage("open.documentLoadWithOptions");
    gState.document = gState.kit->pClass->documentLoadWithOptions(
        gState.kit, fileUrl.c_str(), options.c_str());
  }
#else
  gState.document =
      gState.kit->pClass->documentLoad(gState.kit, fileUrl.c_str());
#endif
  emitStage("open.documentLoad-returned");
  if (!gState.document) {
    emitCommandError(command, "open", "LOK_ERROR", kitError());
    return;
  }

  gState.documentHandle = allocateDocumentHandle();
  gState.revision = 0;
#ifdef OXSDK_EDITOR_DISCOVERY
  gEditorState = EditorState{};
  gEditorPending = EditorPendingOperation{};
#ifdef OXSDK_E2_FORMAT_BARRIER
  gFormatBarrier = FormatStateBarrier{};
#endif
#endif
  gCallbackDocumentHandle.store(gState.documentHandle,
                                std::memory_order_release);
  gCallbackRevision.store(0, std::memory_order_release);
  gOpenRequestId.store(command.sdk ? command.requestId : 0,
                       std::memory_order_release);

  emitStage("open.initializeForRendering");
  gState.document->pClass->initializeForRendering(gState.document, "{}");
  emitStage("open.registerCallback");
  gState.document->pClass->registerCallback(gState.document, onLokCallback,
                                            &gState);
  // Accessibility has to be ASKED FOR, and until 2026-08-17 the product build
  // never asked.
  //
  // `refreshEditorAccessibility()` had exactly one call site, inside
  // `#ifdef OXSDK_EDITOR_DISCOVERY` AND `#ifndef
  // OXSDK_FINDING_016_SELECTION_BARRIER` -- and the product defines both, so
  // the call was compiled out of the profile that ships.  Every
  // `getA11yFocusedParagraph()` in the product therefore returned an empty
  // focused paragraph, and `a11yObserved` stayed false because the callback
  // that sets it only fires once accessibility is on.
  //
  // Measured, not deduced: the first run after the v3 link reported the SAME
  // fingerprint for every paragraph, and that fingerprint was the hash of the
  // empty string.  The whole block-identity mechanism was inert.
  //
  // This is the lesson this tree keeps paying for, one level in: my native
  // rounds enabled accessibility themselves, so they measured a capability the
  // product does not switch on -- "what the harness does" standing in for
  // "what the product does" again.
  //
  // At open, because that is the one moment every profile reaches.
  //
  // Every profile WITH THE EDITOR, since 2026-10-20 (SPEC-M4 addendum 3): the
  // function is the editor's, and a profile without OXSDK_EDITOR_DISCOVERY had
  // stopped compiling at this line.  The read-only spreadsheet viewer is such a
  // profile and switches no accessibility on.  The editor rules all define it,
  // so they preprocess to the same tokens as before.
#ifdef OXSDK_EDITOR_DISCOVERY
  refreshEditorAccessibility();
#endif
  emitStage("open.query-metadata");
  long width = 0;
  long height = 0;
  gState.document->pClass->getDocumentSize(gState.document, &width, &height);
  // Remembered so a later paint can say whether the document has changed shape
  // since (finding 062).  Set here rather than lazily, or the first paint of
  // every document would report a change it never observed.
  gState.documentWidthTwips = width;
  gState.documentHeightTwips = height;
  const int parts = gState.document->pClass->getParts(gState.document);
  const int tileMode = gState.document->pClass->getTileMode(gState.document);

#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
    if (command.sdk && !gOrderedProof.viewReady) {
      emitOrderedMissingProof(command, "open", "view-ready", "LOK_ERROR");
      return;
    }
#endif
  std::ostringstream json;
  json << "{\"type\":\"opened\",\"parts\":" << parts << ",\"width\":" << width
       << ",\"height\":" << height << ",\"tileMode\":" << tileMode;
#ifdef OXSDK_ODS_VIEWER
  // W7b and M1, both read rather than assumed: what core says the document
  // is, and the suffix of the file it was loaded from.
  json << ",\"documentType\":\""
       << probe::odsviewer::documentTypeName(
              gState.document->pClass->getDocumentType(gState.document))
       << "\",\"inputSuffix\":\"" << inputSuffixFor(command) << "\"";
#endif
  if (command.sdk) {
    json << ",\"schemaVersion\":" << ProtocolSchemaVersion
         << ",\"requestId\":" << command.requestId
         << ",\"documentHandle\":" << gState.documentHandle
         << ",\"revision\":0";
  }
  json << "}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
    if (command.sdk) {
      std::ostringstream ready;
      ready << "{\"schemaVersion\":" << ProtocolSchemaVersion
            << ",\"type\":\"view-ready\",\"requestId\":" << command.requestId
            << ",\"documentHandle\":" << gState.documentHandle
            << ",\"revision\":" << gState.revision << "}";
      emitJson(ready.str());
      gOpenRequestId.store(0, std::memory_order_release);
    }
#endif
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
  gStage = "idle";
}

void handlePaintTile(const Command &command) {
  if (!requireDocument(command, "tile"))
    return;

  const int canvasWidth = command.values[4];
  const int canvasHeight = command.values[5];

  // FINDING 062.  Refuse a tile Cairo cannot make, INSTEAD of asking for one
  // and reporting success over the blank buffer that comes back.
  //
  // The limit is Cairo's, and it is attributed rather than inferred
  // (findings/evidence/062/layer/ATTRIBUTION.md):
  //
  //     cairo/src/cairo-image-surface.c:59
  //     /* Limit on the width / height of an image surface in pixels.  This is
  //      * mainly determined by coordinates of things sent to pixman at the
  //      * moment being in 16.16 format. */
  //     #define MAX_IMAGE_SIZE 32767
  //
  // Note what the source says and the number does not: it is NOT a signed
  // 16-bit height and NOT an overflow -- pixman_fixed_t is int32_t.  It is an
  // explicit range check, and it applies to WIDTH EQUALLY.  Our widths have
  // always been small, so what was measured was a height boundary; it is a
  // dimension boundary, so both are checked here.
  //
  // Why the engine has to refuse rather than forward what happened: LOK's
  // `paintTile` returns **void**.  SVP computes a correct boolean and
  // `doc_paintTile` (init.cxx:4288) discards it, so there is no failure for
  // this layer to pass on -- the caller gets a correctly sized buffer that was
  // never drawn into, and every downstream surface reads that as a blank page.
  // That is the upstream defect; refusing early is the honest thing to do
  // while it stands.
  //
  // `<=` is Cairo's own comparison: 32767 is valid, 32768 is not.
  constexpr int kCairoMaxImageSize = 32767;
  if (canvasWidth > kCairoMaxImageSize || canvasHeight > kCairoMaxImageSize) {
    std::ostringstream refusal;
    refusal << "tilePaintRefusedAboveLimit: requested " << canvasWidth << "x"
            << canvasHeight << " px and Cairo's image-surface limit is "
            << kCairoMaxImageSize
            << " per dimension; core would return an undrawn buffer and report "
               "nothing, so this is refused instead of painted";
    emitCommandError(command, "tile", "TILE_EXCEEDS_ENGINE_LIMIT",
                     refusal.str().c_str());
    return;
  }

  const std::uint64_t byteCount = static_cast<std::uint64_t>(canvasWidth) *
                                  static_cast<std::uint64_t>(canvasHeight) * 4;
  if (byteCount > std::numeric_limits<std::uint32_t>::max() ||
      byteCount > std::numeric_limits<std::size_t>::max()) {
    emitCommandError(command, "tile", "BUFFER_TOO_LARGE",
                     "tile pixel buffer exceeds the WASM address space");
    return;
  }

  // ZEROED, and `malloc` here was finding 076.
  //
  // `paintTile` draws the PAGE and leaves the rest of the buffer alone, so
  // whatever `malloc` handed back survives in the margins -- and the client
  // blits the buffer verbatim with `putImageData`, which writes ALPHA too.
  // The product was therefore painting uninitialised heap onto the user's
  // screen, in colour, wherever the document does not cover the tile.
  //
  // It was always happening and was always invisible, because a freshly grown
  // WASM heap is zero: the shipped core's off-page area comes back 0.0042%
  // non-zero (88 of 2,105,340 sampled points, measured for `tileWasPainted`)
  // and 0% opaque, so it reads as transparent. On the accessibility core --
  // +19.9 MB of code and far more allocation churn, so this buffer lands on
  // REUSED memory rather than a fresh page -- the same region came back 1.08%
  // opaque (290 of 26,941) with 184 distinct alpha values against 33.
  // Two hundred and fifty times as much of the same thing.
  //
  // Thirty-one of those pixels were dark enough to be ink, they fell in the
  // gaps between lines, and the harness's band scan merged two lines and threw
  // the pair away below its density floor. That is finding 075, and it is the
  // cheap consequence: the expensive one is that a canvas the user can
  // screenshot was displaying fragments of this process's heap.
  //
  // `calloc` rather than a `memset` after the fact so there is no window and
  // no second statement to forget. On a fresh page the allocator's zeroing is
  // free; on reused memory it is one pass over 2.7 MB, against a paint that
  // rasterises the same buffer.
  auto *pixels = static_cast<unsigned char *>(
      std::calloc(static_cast<std::size_t>(byteCount), 1));
  if (!pixels) {
    emitCommandError(command, "tile", "OUT_OF_MEMORY",
                     "unable to allocate the tile pixel buffer");
    return;
  }

  gState.document->pClass->paintTile(
      gState.document, pixels, canvasWidth, canvasHeight, command.values[0],
      command.values[1], command.values[2], command.values[3]);

  // Finding 062, the half the page could not fix: `getDocumentSize` was called
  // exactly once, at open, and NOTHING re-read it -- so after an edit that adds
  // a page the client's height is stale, and the canvas it sizes from that
  // height is the wrong size, silently.  None of the SDK's operations reported
  // a size, so no client could have known.
  //
  // Reported on the paint reply rather than as a new event: paint's caller is
  // by definition about to draw the document, so it is the caller that needs
  // the number, and it already awaits this message.
  long documentWidth = 0;
  long documentHeight = 0;
  gState.document->pClass->getDocumentSize(gState.document, &documentWidth,
                                           &documentHeight);
  const bool documentSizeChanged =
      documentWidth != gState.documentWidthTwips ||
      documentHeight != gState.documentHeightTwips;
  gState.documentWidthTwips = documentWidth;
  gState.documentHeightTwips = documentHeight;

#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"type\":\"tile\",\"ptr\":"
       << reinterpret_cast<std::uintptr_t>(pixels) << ",\"size\":" << byteCount
       << ",\"w\":" << canvasWidth << ",\"h\":" << canvasHeight;
// The viewer gets them as well (SPEC-M4 §3.2, review B2): its page refits the
// surface to the post-paint width, and E4 reads documentSizeChanged.
#if defined(OXSDK_E2_FORMAT_BARRIER) || defined(OXSDK_ODS_VIEWER)
  // Guarded, and the guard is about blast radius rather than about formatting:
  // every profile shares this function, and the frozen e1-editor profiles were
  // validated at a specific WASM hash with a specific reply shape.  Adding
  // fields to their replies unguarded is the shape the EditorState comment
  // above warns about, so the new fields go only to the profile that needs
  // them.
  json << ",\"documentWidthTwips\":" << documentWidth
       << ",\"documentHeightTwips\":" << documentHeight
       << ",\"documentSizeChanged\":"
       << (documentSizeChanged ? "true" : "false");
#else
  (void)documentSizeChanged;
#endif
  if (command.sdk) {
    json << ",\"schemaVersion\":" << ProtocolSchemaVersion
         << ",\"requestId\":" << command.requestId
         << ",\"documentHandle\":" << gState.documentHandle
         << ",\"revision\":" << gState.revision;
  }
  json << "}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

void handleClick(const Command &command) {
  if (!requireDocument(command, "click"))
    return;

  gState.document->pClass->postMouseEvent(
      gState.document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, command.values[0],
      command.values[1], 1, 1, 0);
  gState.document->pClass->postMouseEvent(
      gState.document, LOK_MOUSEEVENT_MOUSEBUTTONUP, command.values[0],
      command.values[1], 1, 1, 0);

#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([command] {
#endif
  if (!command.sdk) {
    emitJson("{\"type\":\"clicked\"}");
    return;
  }
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"clicked\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << "}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

void handleInsertText(const Command &command) {
  if (!requireDocument(command, "insert"))
    return;

  std::string method = "paste";
  if (!gState.document->pClass->paste(
          gState.document, "text/plain;charset=utf-8", command.text.data(),
          command.text.size())) {
    method = "postKeyEvent";
    std::vector<std::uint32_t> codePoints;
    if (!decodeUtf8(command.text, codePoints)) {
      emitCommandError(command, "insert", "INVALID_UTF8",
                       "paste failed and fallback input is not valid UTF-8");
      return;
    }
    for (std::uint32_t codePoint : codePoints) {
      gState.document->pClass->postKeyEvent(gState.document,
                                            LOK_KEYEVENT_KEYINPUT,
                                            static_cast<int>(codePoint), 0);
      gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYUP,
                                            static_cast<int>(codePoint), 0);
    }
  }

  ++gState.revision;
  gCallbackRevision.store(gState.revision, std::memory_order_release);
#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"type\":\"inserted\",\"method\":\"" << method << "\"";
  if (command.sdk) {
    json << ",\"schemaVersion\":" << ProtocolSchemaVersion
         << ",\"requestId\":" << command.requestId
         << ",\"documentHandle\":" << gState.documentHandle
         << ",\"revision\":" << gState.revision;
  }
  json << "}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

#ifdef OXSDK_E2_V24_TYPED_INSERT
// SPEC-M3-link-batch-v24 4.1 (finding 168).  TYPED text goes through
// .uno:InsertText -- FN_INSERT_STRING, SwWrtShell::InsertByWord, the
// keyboard's own Insert -- so a selection is replaced the way the keyboard
// replaces it, table-selection mode included, where LOK paste appends to every
// cell instead.  Real paste stays on handleInsertText above, byte for byte.
//
// The SDK routes a line break or NUL to the paste export, never here (Enter is
// another family, and jsonEscape stops at NUL), so this export refuses them
// before anything is dispatched rather than routing them itself: one layer
// decides the route, and a foreign caller sees a refusal, not a silent paste.
void emitTypedInsertRefusal(const Command &command, const char *code,
                            const char *message) {
  if (gOrderedDispatching) {
    setOrderedReply([command, code = std::string(code), message = std::string(message)] {
      emitTypedInsertRefusal(command, code.c_str(), message.c_str());
    });
    return;
  }
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << command.documentHandle
       << ",\"revision\":" << gState.revision
       << ",\"operation\":\"insert\",\"code\":\"" << code
       << "\",\"message\":\"" << jsonEscape(message)
       << "\",\"where\":\"insert\",\"msg\":\"" << jsonEscape(message)
       << "\",\"dispatched\":false}";
  emitJson(json.str());
}

void handleInsertTypedText(const Command &command) {
  if (!requireDocument(command, "insert"))
    return;
  std::vector<std::uint32_t> codePoints;
  if (!decodeUtf8(command.text, codePoints)) {
    emitTypedInsertRefusal(command, "INVALID_UTF8", "typed text is not valid UTF-8");
    return;
  }
  for (std::uint32_t codePoint : codePoints) {
    if (codePoint == 0 || codePoint == 0x0a || codePoint == 0x0d) {
      emitTypedInsertRefusal(command, "INVALID_ARGUMENT",
                             "typed text carries NUL or a line break; those keep the paste route");
      return;
    }
  }

  expectOrderedUno(".uno:InsertText");
  setOrderedReply([command] {
    // The result's PRESENCE is the proof (the void-command policy).  Its
    // fields are not: FN_INSERT_STRING never calls rReq.Done(), so `success`
    // is false on every delivery and `wasModified` is false although the text
    // changed -- M1, 16 shape x text pairs, 3 rounds each, native.
    std::string payload;
    if (!orderedUnoResult(".uno:InsertText", payload)) {
      emitOrderedMissingProof(command, "insert", "UNO_COMMAND_RESULT");
      return;
    }
    advanceRevision();
    std::ostringstream json;
    json << "{\"schemaVersion\":" << ProtocolSchemaVersion
         << ",\"type\":\"inserted\",\"method\":\"uno-insert-text\""
         << ",\"completion\":\"uno-command-result\",\"requestId\":" << command.requestId
         << ",\"documentHandle\":" << command.documentHandle
         << ",\"revision\":" << gState.revision << ",\"resultPayload\":\""
         << jsonEscape(payload.c_str()) << "\"}";
    emitJson(json.str());
  });
  std::ostringstream arguments;
  arguments << "{\"Text\":{\"type\":\"string\",\"value\":\""
            << jsonEscape(command.text.c_str()) << "\"}}";
  // Unipoll: dispatched synchronously inside postUnoCommand (init.cxx adds
  // SynchronMode=false only when not unipoll), like .uno:Paste in doc_paste.
  gState.document->pClass->postUnoCommand(gState.document, ".uno:InsertText",
                                          arguments.str().c_str(), true);
}
#endif

void handleSearch(const Command &command) {
  if (!requireDocument(command, "search"))
    return;
  if (gSearchRequestId.load(std::memory_order_acquire) != 0) {
    emitCommandError(command, "search", "BUSY",
                     "another search request is still in flight");
    return;
  }
#ifdef OXSDK_E2_FORMAT_BARRIER
  // Search is a caret mover, not just a query: .uno:ExecuteSearch selects its
  // match.  That is the concrete path A5's crosstalk case takes, and it is how
  // a caller could hand the barrier someone else's selection to read.
  if (formatBarrierActive()) {
    emitCommandError(command, "search", "BUSY",
                     "a verified format-state action is still in flight");
    return;
  }
#endif

#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([command] {
    if (gOrderedProof.searchType < 0) {
      emitOrderedMissingProof(command, "search", "SEARCH_RESULT_SELECTION", "LOK_ERROR");
      return;
    }
    std::ostringstream result;
    result << "{\"schemaVersion\":" << ProtocolSchemaVersion
           << ",\"type\":\"search-result\",\"requestId\":" << command.requestId
           << ",\"documentHandle\":" << command.documentHandle
           << ",\"revision\":" << gState.revision << ",\"found\":"
           << (gOrderedProof.searchType == LOK_CALLBACK_SEARCH_RESULT_SELECTION ? "true" : "false")
           << ",\"query\":\"" << jsonEscape(command.text.c_str())
           << "\",\"resultPayload\":\"" << jsonEscape(gOrderedProof.searchPayload.c_str()) << "\"}";
    emitJson(result.str());
  });
#else
  gSearchQuery = command.text;
  gSearchRequestId.store(command.requestId, std::memory_order_release);
  markAsynchronous(command.requestId);
#endif
  std::ostringstream arguments;
  arguments
      << "{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\""
      << jsonEscape(command.text.c_str())
      << "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":"
      << (command.values[0] ? "true" : "false")
      << "},\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  gState.document->pClass->postUnoCommand(
      gState.document, ".uno:ExecuteSearch", arguments.str().c_str(), false);
}

// Selection readback shared by the public and the diagnostic contract.
//
// getTextSelection() cannot express an empty selection: getFromTransferable()
// canonicalizes text/plain;charset=utf-8 into an internal utf-16 flavor, and a
// caret-only selection has no such flavor, so the call returns nullptr exactly
// as it does for a real failure. getSelectionTypeAndText() folds that same
// flavor miss into LOK_SELTYPE_NONE instead, which is what lets "nothing is
// selected" be a success.
//
// Two consequences for callers. Core collapses three distinct states -- no
// transferable, empty text, and a missing plain-text flavor -- into
// LOK_SELTYPE_NONE, so this readback alone cannot tell them apart; confirm a
// collapsed caret against the LOK_CALLBACK_TEXT_SELECTION path as well. And
// never consult kitError() after a NONE result: getFromTransferable() leaves
// its "Flavor ... is not supported" message set even when the call succeeds.
// SelectionReadback is the editor's type (2026-10-20, SPEC-M4 addendum 3: a
// profile without the editor had stopped compiling here).
#ifdef OXSDK_EDITOR_DISCOVERY
SelectionReadback readSelection() {
  SelectionReadback readback;
  char *text = nullptr;
  if (LIBREOFFICEKIT_DOCUMENT_HAS(gState.document, getSelectionTypeAndText)) {
    readback.type = gState.document->pClass->getSelectionTypeAndText(
        gState.document, "text/plain;charset=utf-8", &text, nullptr);
  } else {
    readback.type = gState.document->pClass->getSelectionType(gState.document);
    if (readback.type == LOK_SELTYPE_TEXT)
      text = gState.document->pClass->getTextSelection(
          gState.document, "text/plain;charset=utf-8", nullptr);
  }
  if (readback.type == LOK_SELTYPE_TEXT) {
    if (text)
      readback.text = text;
    else
      readback.textMissing = true;
  }
  if (text)
    std::free(text);
  return readback;
}
#endif

const char *selectionTypeName(int type) {
  switch (type) {
  case LOK_SELTYPE_NONE:
    return "none";
  case LOK_SELTYPE_TEXT:
    return "text";
  case LOK_SELTYPE_LARGE_TEXT:
  case LOK_SELTYPE_COMPLEX:
    return "complex";
  default:
    return "unknown";
  }
}

#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
bool selectionBarrierActive() {
  return gSelectionBarrier.stage != SelectionBarrierStage::Idle;
}

bool selectionBarrierContainsBoundary(
    const std::vector<std::uint32_t> &codePoints) {
  for (const std::uint32_t value : codePoints) {
    if (value == '\r' || value == '\n' || value == '\t' || value == 0x2028 ||
        value == 0x2029 || value == 0xfffc)
      return true;
  }
  return false;
}

#ifdef OXSDK_E2_V20_LINK_BATCH
// SPEC-M3-link-batch 4.5(2) / 10.6 (ruling 2 S-8): every refusal of the
// barrier carries `caretBefore: { rect, sourceSequence, source }`.
//
// `source` is "attribution-P" when the merge attribution has established P --
// the last caret callback before K1's own selection, i.e. where the caret was
// when K1 RAN -- and "cache" otherwise, meaning the engine's cached caret at
// the moment the barrier started.  `sourceSequence` is the cache's
// sourceSequence at barrier start in both cases: the attribution records no
// sequence for P (merge_key_undo.hpp keeps rectangles only), and widening
// that header is the merge model's business, not this link's.  `rect` is
// null when neither exists (a barrier that started before any caret callback
// was ever observed), never a zero rectangle dressed as a position.
//
// Data only: the engine reads none of this back.  The page's reopen may read
// it in a later part; E2's oracle is K1's anchor rectangle of the same
// transaction (10.6).
void appendCaretBefore(std::ostringstream &json,
                       const SelectionBarrierTransaction &transaction) {
  EditorRect rect = transaction.caretBefore;
  bool fromAttribution = false;
#if defined(OXSDK_MERGE_KEY_UNDO) && !defined(OXSDK_E2_V23_LINK_BATCH)
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    if (gMergeAttribution.hasP()) {
      const probe::merge::Rect &p = gMergeAttribution.p();
      rect.available = true;
      rect.x = static_cast<int>(p.x);
      rect.y = static_cast<int>(p.y);
      rect.width = static_cast<int>(p.w);
      rect.height = static_cast<int>(p.h);
      fromAttribution = true;
    }
  }
#endif
  json << ",\"caretBefore\":{\"rect\":";
  if (rect.available)
    appendEditorRectangle(json, rect);
  else
    json << "null";
  json << ",\"sourceSequence\":" << transaction.caretBeforeSequence
       << ",\"source\":\"" << (fromAttribution ? "attribution-P" : "cache")
       << "\"}";
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void finishSelectionBarrierError(const char *code, const char *message,
                                 bool viewRecoveryRequired) {
  const SelectionBarrierTransaction transaction = gSelectionBarrier;
  gSelectionBarrier = SelectionBarrierTransaction{};
  std::string finalMessage = message ? message : "selection barrier failed";
  if (viewRecoveryRequired)
    finalMessage += "; no mutation was dispatched; start a fresh Worker";
#ifdef OXSDK_E2_V20_LINK_BATCH
  // emitSdkError's exact shape plus `caretBefore` (10.6); the value is as
  // well defined here as in finishMergeKeyError, because every call site of
  // this function runs inside a transaction that startSelectionBarrierDelete
  // opened, and that is where the cache was captured.
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << transaction.requestId
       << ",\"documentHandle\":" << transaction.documentHandle
       << ",\"revision\":" << gCallbackRevision.load(std::memory_order_acquire)
       << ",\"operation\":\"editor-action\",\"code\":\"" << jsonEscape(code)
       << "\",\"message\":\"" << jsonEscape(finalMessage.c_str())
       << "\",\"where\":\"editor-action\",\"msg\":\""
       << jsonEscape(finalMessage.c_str()) << "\"";
  appendCaretBefore(json, transaction);
  json << "}";
  emitJson(json.str());
#else
  emitSdkError(transaction.requestId, transaction.documentHandle,
               "editor-action", code, finalMessage);
#endif
  finishAsynchronous(transaction.requestId);
}
#endif

#ifdef OXSDK_MERGE_KEY_UNDO
probe::merge::Rect mergeRect(const EditorRect &r) {
  return {r.x, r.y, r.width, r.height};
}

#ifndef OXSDK_E2_V23_LINK_BATCH
void armMergeDeadline() {
  gSelectionBarrier.stageDeadlineArmed = true;
  gSelectionBarrier.stageDeadline =
      std::chrono::steady_clock::now() +
      std::chrono::milliseconds(MergeStepDeadlineMs);
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
bool mergeStageAwaiting() {
  switch (gSelectionBarrier.stage) {
  case SelectionBarrierStage::MergeAwaitingCollapse1:
  case SelectionBarrierStage::MergeAwaitingReturn:
  case SelectionBarrierStage::MergeAwaitingCollapse2:
  case SelectionBarrierStage::MergeAwaitingKey:
    return true;
  default:
    return false;
  }
}
#endif

// Engine thread only (getCommandValues takes the SolarMutex): never under
// gState.mutex or gMergeMutex.
bool readMergeUndoPayload(std::string &out) {
  char *values = gState.document->pClass->getCommandValues(gState.document,
                                                           ".uno:Undo");
  if (!values)
    return false;
  out = values;
  std::free(values);
  return true;
}

// Every refusal of option B ends here (SPEC-M3-paragraph-merge 10.1(d)).
// The code is always EDITOR_BOUNDARY_UNSUPPORTED: the session checkpoints the
// engine's current document and reopens (109), so typed text survives
// whether or not the key was posted.  mergeKey says which: before the key
// nothing was dispatched; after it, the key's own effect is unknown and the
// message must not claim otherwise.
#ifndef OXSDK_E2_V23_LINK_BATCH
void finishMergeKeyError(const char *stage) {
  const probe::merge::Stage *known = probe::merge::findStage(stage);
  const bool keyPosted =
      gSelectionBarrier.keyPosted || (known && known->keyPosted);
  const SelectionBarrierTransaction transaction = gSelectionBarrier;
  gSelectionBarrier = SelectionBarrierTransaction{};
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    gMergeTicket = MergeTicket{};
  }
  const std::string message =
      keyPosted
          ? std::string("the user's key was posted but its effect could not "
                        "be verified (") +
                stage + "); start a fresh Worker"
          : std::string("paragraph merge refused before the key (") + stage +
                "); no mutation was dispatched; start a fresh Worker";
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << transaction.requestId
       << ",\"documentHandle\":" << transaction.documentHandle
       << ",\"revision\":" << gCallbackRevision.load(std::memory_order_acquire)
       << ",\"operation\":\"editor-action\""
       << ",\"code\":\"EDITOR_BOUNDARY_UNSUPPORTED\",\"message\":\""
       << jsonEscape(message.c_str()) << "\",\"where\":\"editor-action\""
       << ",\"msg\":\"" << jsonEscape(message.c_str()) << "\""
       << ",\"mergeKey\":{\"keyPosted\":" << (keyPosted ? "true" : "false")
#ifdef OXSDK_E2_V20_LINK_BATCH
       << ",\"stage\":\"" << jsonEscape(stage) << "\",\"restorePresses\":0}";
  appendCaretBefore(json, transaction);
  json << "}";
#else
       << ",\"stage\":\"" << jsonEscape(stage) << "\",\"restorePresses\":0}}";
#endif
  emitJson(json.str());
  finishAsynchronous(transaction.requestId);
}
#endif

#ifdef OXSDK_E2_V20_LINK_BATCH
// SPEC-M3-link-batch 10.5 (ruling 2 condition 8; ruling 4 condition 35, no
// flag clauses): C's second exit.  The window expired with a second
// readSelection() still NONE and the typed selection still collapsed, so the
// press changed nothing: `editor-action-completed`, `changed: false`, the
// revision unchanged, completion `verified-boundary-noop`, and
// `boundaryNoop.waitedMs` measured from K1's post -- the number L-C-late-K1
// and "about 2.25 s at the start of the document" are stated in, kept so a
// later section can shorten the window from a measurement.
//
// No EDITOR_BOUNDARY_UNSUPPORTED, no reopen.  The residual is named in the
// spec (L-C-late-K1): a K1 that runs after this reply leaves a selection in a
// live session, and nothing here can wait for a signal that a key which
// changes nothing never sends (ruling 2 F1).
#ifndef OXSDK_E2_V23_LINK_BATCH
void finishSelectionBarrierBoundaryNoop() {
  const SelectionBarrierTransaction transaction = gSelectionBarrier;
  gSelectionBarrier = SelectionBarrierTransaction{};
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    gMergeTicket = MergeTicket{};
  }
  const long long waitedMs =
      std::chrono::duration_cast<std::chrono::milliseconds>(
          std::chrono::steady_clock::now() - transaction.startedAt)
          .count();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-action-completed\",\"requestId\":"
       << transaction.requestId << ",\"documentHandle\":"
       << transaction.documentHandle << ",\"beforeRevision\":"
       << transaction.beforeRevision << ",\"revision\":" << gState.revision
       << ",\"action\":\"" << jsonEscape(transaction.action.c_str())
       << "\",\"option\":false,\"changed\":false"
       << ",\"completion\":\"verified-boundary-noop\""
       << ",\"callbackSequenceBefore\":" << transaction.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence
       << ",\"boundaryNoop\":{\"waitedMs\":" << waitedMs << "}"
       << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  finishAsynchronous(transaction.requestId);
}
#endif
#endif
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void maybeFinishSelectionBarrier() {
  if (!selectionBarrierActive() ||
      gSelectionBarrier.stage !=
          SelectionBarrierStage::FinalVerificationQueued ||
      !gSelectionBarrier.acknowledgementSeen)
    return;

  if (gSelectionBarrier.acknowledgement == SelectionBarrierAck::Mismatch) {
    finishSelectionBarrierError(
        "LOK_RESULT_MISMATCH",
        "selection delete returned an unexpected fixed command result", false);
    return;
  }
  if (gSelectionBarrier.acknowledgement == SelectionBarrierAck::Failed) {
    finishSelectionBarrierError(
        "LOK_COMMAND_FAILED",
        "LibreOfficeKit rejected the verified selection delete", false);
    return;
  }
  if (gSelectionBarrier.acknowledgement !=
          SelectionBarrierAck::MatchedSuccess ||
      !gSelectionBarrier.collapseCallbackSeen)
    return;

  const SelectionReadback postcondition = readSelection();
  if (postcondition.type != LOK_SELTYPE_NONE || postcondition.textMissing ||
      !gEditorState.selectionObserved ||
      !gEditorState.selectionRectangles.empty()) {
    finishSelectionBarrierError(
        "MUTATION_OUTCOME_UNKNOWN",
        "delete acknowledgement arrived without a verified collapsed selection",
        false);
    return;
  }

  const SelectionBarrierTransaction transaction = gSelectionBarrier;
  gSelectionBarrier = SelectionBarrierTransaction{};
  advanceRevision();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-action-completed\",\"requestId\":"
       << transaction.requestId << ",\"documentHandle\":"
       << transaction.documentHandle << ",\"beforeRevision\":"
       << transaction.beforeRevision << ",\"revision\":" << gState.revision
       << ",\"action\":\"" << jsonEscape(transaction.action.c_str())
       << "\",\"option\":false,\"changed\":true"
       << ",\"completion\":\"verified-selection-delete\""
       << ",\"callbackSequenceBefore\":" << transaction.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence
       << ",\"selectionBarrier\":{\"selectedText\":\""
       << jsonEscape(transaction.selectedText.c_str())
       << "\",\"utf8Bytes\":" << transaction.selectedText.size()
       << ",\"transactionSerial\":" << transaction.transactionSerial
       << ",\"codePoints\":[";
  for (std::size_t index = 0; index < transaction.selectedCodePoints.size();
       ++index) {
    if (index)
      json << ',';
    json << transaction.selectedCodePoints[index];
  }
  json << "],\"preselectionSequence\":"
       << transaction.preselectionSequence << ",\"dispatchSequence\":"
       << transaction.dispatchSequence << ",\"collapseSequence\":"
       << transaction.collapseSequence
       << ",\"acknowledgementSequence\":"
       << transaction.acknowledgementSequence
       << ",\"acknowledgementBeforeCollapse\":"
       << (transaction.acknowledgementSequence < transaction.collapseSequence
               ? "true"
               : "false")
       << "},\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  finishAsynchronous(transaction.requestId);
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void queueSelectionBarrierStep(bool boundaryDeadline = false) {
  Command command{CommandType::EditorSelectionBarrierStep};
  command.requestId = gSelectionBarrier.requestId;
  command.documentHandle = gSelectionBarrier.documentHandle;
  command.correlation = gSelectionBarrier.transactionSerial;
  command.values[0] = boundaryDeadline ? 1 : 0;
  if (submit(std::move(command)) != SubmitStatus::Ok) {
    finishSelectionBarrierError(
        "EDITOR_STATE_UNAVAILABLE",
        "selection barrier could not schedule a non-reentrant verification",
        false);
  }
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void maybeQueueSelectionBarrierFinalVerification() {
  if (gSelectionBarrier.stage !=
          SelectionBarrierStage::AwaitingDeleteCompletion ||
      !gSelectionBarrier.acknowledgementSeen)
    return;
  if (gSelectionBarrier.acknowledgement ==
          SelectionBarrierAck::MatchedSuccess &&
      !gSelectionBarrier.collapseCallbackSeen)
    return;
  gSelectionBarrier.stage = SelectionBarrierStage::FinalVerificationQueued;
  queueSelectionBarrierStep();
}
#endif

#ifdef OXSDK_MERGE_KEY_UNDO
// LOK thread, every callback, before anything else looks at it.  Feeds the
// attribution with each START/END/TEXT_SELECTION/caret as delivered, and,
// when a proof arrives (or, after the key, any callback), queues one merge
// step addressed by the ticket.  It writes nothing the engine thread owns.
#ifndef OXSDK_E2_V23_LINK_BATCH
void feedMergeAttribution(int type, const char *payload) {
  using Phase = probe::merge::Attribution::Phase;
  EditorRect parsed;
  bool relevant = true;
  bool nonEmpty = false;
  switch (type) {
  case LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR:
  case LOK_CALLBACK_TEXT_SELECTION_START:
  case LOK_CALLBACK_TEXT_SELECTION_END:
    relevant = parseEditorRectangle(payload, parsed);
    break;
  case LOK_CALLBACK_TEXT_SELECTION:
    nonEmpty = payload && *payload && std::strcmp(payload, "EMPTY") != 0;
    break;
  default:
    relevant = false;
    break;
  }
  Command step{CommandType::EditorSelectionBarrierStep};
  bool queue = false;
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    const Phase before = gMergeAttribution.phase();
    if (relevant) {
      if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR)
        gMergeAttribution.onCaret(mergeRect(parsed));
      else if (type == LOK_CALLBACK_TEXT_SELECTION_START)
        gMergeAttribution.onSelectionStart(mergeRect(parsed));
      else if (type == LOK_CALLBACK_TEXT_SELECTION_END)
        gMergeAttribution.onSelectionEnd(mergeRect(parsed));
      else
        gMergeAttribution.onTextSelection(nonEmpty);
    }
    const Phase after = gMergeAttribution.phase();
    const bool proof = after != before && (after == Phase::Collapsed1 ||
                                           after == Phase::Returned ||
                                           after == Phase::Ready);
    if (gMergeTicket.active && !gMergeTicket.stepPending &&
        (proof || gMergeTicket.afterKey)) {
      gMergeTicket.stepPending = true;
      step.requestId = gMergeTicket.requestId;
      step.documentHandle = gMergeTicket.documentHandle;
      step.correlation = gMergeTicket.serial;
      step.values[0] = 3;
      queue = true;
    }
  }
  // Outside gMergeMutex: submit() takes gState.mutex.  A failed submit is
  // left to the step deadline, which the engine thread owns.
  if (queue)
    submit(std::move(step));
}
#endif

// Engine thread: send a .uno:Escape after marking it sent (16.2 steps 2, 4).
// postUnoCommand with a listener runs synchronously here (unoctitm.cxx:654).
#ifndef OXSDK_E2_V23_LINK_BATCH
void sendMergeEscape(SelectionBarrierStage awaiting) {
  gSelectionBarrier.stage = awaiting;
  bool sent;
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    sent = gMergeAttribution.escapeSent();
  }
  if (!sent) {
    finishMergeKeyError("restore");
    return;
  }
  gState.document->pClass->postUnoCommand(gState.document, ".uno:Escape",
                                          nullptr, true);
  // Review N2: armed after the call returns -- it waits for the SolarMutex,
  // and a busy LOK must not use up the step's 2000 ms before the step ran.
  armMergeDeadline();
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void postMergeKeyEvents(int keyCode) {
  gState.document->pClass->postKeyEvent(gState.document,
                                        LOK_KEYEVENT_KEYINPUT, 0, keyCode);
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYUP,
                                        0, keyCode);
}
#endif

// Step 1 passed the classification: the unit holds a paragraph or line
// separator.  K1's anchor must satisfy the fence against P (13.1, 14.2).
#ifndef OXSDK_E2_V23_LINK_BATCH
void startMergeKeyUndo(const SelectionReadback &selected,
                       std::vector<std::uint32_t> codePoints) {
  bool fence;
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    fence = gMergeAttribution.fenceHolds();
  }
  gSelectionBarrier.mergeKey = true;
  if (!fence) {
    finishMergeKeyError("anchor-mismatch");
    return;
  }
  if (!gSelectionBarrier.pStartRead) {
    finishMergeKeyError("undo-read");
    return;
  }
  gSelectionBarrier.selectedText = selected.text;
  gSelectionBarrier.selectedCodePoints = std::move(codePoints);
  sendMergeEscape(SelectionBarrierStage::MergeAwaitingCollapse1);
}
#endif

// Step 3: K2, Shift+arrow back; it has a mark, so no stop in front of a label.
#ifndef OXSDK_E2_V23_LINK_BATCH
void postMergeReturn() {
  gSelectionBarrier.stage = SelectionBarrierStage::MergeAwaitingReturn;
  bool posted;
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    posted = gMergeAttribution.returnPosted();
  }
  if (!posted) {
    finishMergeKeyError("restore");
    return;
  }
  postMergeKeyEvents((gSelectionBarrier.backward
                          ? com::sun::star::awt::Key::RIGHT
                          : com::sun::star::awt::Key::LEFT) |
                     EditorShiftModifier);
  armMergeDeadline();
}
#endif

// K2's selection: the same text as K1's, its point side at P.
#ifndef OXSDK_E2_V23_LINK_BATCH
void verifyMergeReturn() {
  const SelectionReadback selected = readSelection();
  bool fence;
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    fence = gMergeAttribution.returnFenceHolds();
  }
  if (selected.type != LOK_SELTYPE_TEXT || selected.textMissing ||
      selected.text != gSelectionBarrier.selectedText || !fence) {
    finishMergeKeyError("return-mismatch");
    return;
  }
  sendMergeEscape(SelectionBarrierStage::MergeAwaitingCollapse2);
}
#endif

// Step 5: P0, P_start == P0 (10.1(f)), then the user's own key.
#ifndef OXSDK_E2_V23_LINK_BATCH
void postMergeKey() {
  std::string p0;
  const bool read = readMergeUndoPayload(p0);
  if (const char *stage = probe::merge::judgeBeforeKey(
          gSelectionBarrier.pStartRead, gSelectionBarrier.pStart, read, p0)) {
    finishMergeKeyError(stage);
    return;
  }
  gSelectionBarrier.p0 = std::move(p0);
  gSelectionBarrier.keyPosted = true;
  gSelectionBarrier.keyPostedAt = std::chrono::steady_clock::now();
  gSelectionBarrier.stage = SelectionBarrierStage::MergeAwaitingKey;
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    gMergeTicket.afterKey = true;
  }
  postMergeKeyEvents(gSelectionBarrier.backward
                         ? com::sun::star::awt::Key::BACKSPACE
                         : com::sun::star::awt::Key::DELETE);
  armMergeDeadline();
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void finishMergeKeyUndo(const probe::merge::KeyJudgement &judgement) {
  const SelectionBarrierTransaction transaction = gSelectionBarrier;
  gSelectionBarrier = SelectionBarrierTransaction{};
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    gMergeTicket = MergeTicket{};
  }
  advanceRevision();
  const long long keyToUndoMs =
      std::chrono::duration_cast<std::chrono::milliseconds>(
          std::chrono::steady_clock::now() - transaction.keyPostedAt)
          .count();
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-action-completed\",\"requestId\":"
       << transaction.requestId << ",\"documentHandle\":"
       << transaction.documentHandle << ",\"beforeRevision\":"
       << transaction.beforeRevision << ",\"revision\":" << gState.revision
       << ",\"action\":\"" << jsonEscape(transaction.action.c_str())
       << "\",\"option\":false,\"changed\":true"
       << ",\"completion\":\"verified-key-undo\""
       << ",\"callbackSequenceBefore\":" << transaction.beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence
       << ",\"keyUndo\":{\"comment\":\""
       << jsonEscape(judgement.after.topComment.c_str())
       << "\",\"actionsBefore\":" << judgement.before.actions
       << ",\"actionsAfter\":" << judgement.after.actions
       << ",\"restorePresses\":0,\"keyToUndoMs\":" << keyToUndoMs
       << ",\"codePoints\":[";
  for (std::size_t index = 0; index < transaction.selectedCodePoints.size();
       ++index) {
    if (index)
      json << ',';
    json << transaction.selectedCodePoints[index];
  }
  json << "]},\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
  finishAsynchronous(transaction.requestId);
}
#endif

// After the key: the whole payload against P0 (3.1 items 8-9, 10.1(b)).
#ifndef OXSDK_E2_V23_LINK_BATCH
void verifyMergeKey(bool atDeadline) {
  std::string now;
  const bool read = readMergeUndoPayload(now);
  const probe::merge::KeyJudgement judgement = probe::merge::judgeAfterKey(
      gSelectionBarrier.p0, read, now, atDeadline);
  if (judgement.verdict == probe::merge::KeyVerdict::Pending)
    return;
  if (judgement.verdict == probe::merge::KeyVerdict::Refused) {
    finishMergeKeyError(judgement.stage);
    return;
  }
  finishMergeKeyUndo(judgement);
}
#endif

// A step queued by the feed: act on the proof the attribution now holds, if
// it is the one the current stage waits for.  The pending flag is cleared
// before anything is read (review N3): a callback after this point queues
// the next step instead of being absorbed by this one.
#ifndef OXSDK_E2_V23_LINK_BATCH
void advanceMerge() {
  using Phase = probe::merge::Attribution::Phase;
  Phase phase;
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    gMergeTicket.stepPending = false;
    phase = gMergeAttribution.phase();
  }
  switch (gSelectionBarrier.stage) {
  case SelectionBarrierStage::MergeAwaitingCollapse1:
    if (phase == Phase::Collapsed1)
      postMergeReturn();
    return;
  case SelectionBarrierStage::MergeAwaitingReturn:
    if (phase == Phase::Returned)
      verifyMergeReturn();
    return;
  case SelectionBarrierStage::MergeAwaitingCollapse2:
    if (phase == Phase::Ready)
      postMergeKey();
    return;
  case SelectionBarrierStage::MergeAwaitingKey:
    verifyMergeKey(false);
    return;
  default:
    return;
  }
}
#endif

// A step's proof did not arrive within MergeStepDeadlineMs.
#ifndef OXSDK_E2_V23_LINK_BATCH
void handleMergeDeadline() {
  if (!gSelectionBarrier.stageDeadlineArmed || !mergeStageAwaiting() ||
      std::chrono::steady_clock::now() < gSelectionBarrier.stageDeadline)
    return;
  if (gSelectionBarrier.stage == SelectionBarrierStage::MergeAwaitingKey) {
    gSelectionBarrier.stageDeadlineArmed = false;
    verifyMergeKey(true);
    return;
  }
  finishMergeKeyError("restore");
}
#endif
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void verifyAndDispatchSelectionBarrierDelete() {
  if (gSelectionBarrier.stage !=
      SelectionBarrierStage::UnitVerificationQueued)
    return;

  const SelectionReadback selected = readSelection();
  std::vector<std::uint32_t> codePoints;
#ifdef OXSDK_MERGE_KEY_UNDO
  // 3.1 item 2: only a text unit holding a paragraph or line separator takes
  // option B; it spans lines, so the single-rectangle check below does not
  // apply to it.  Entered only from the TEXT_SELECTION branch (13.3).
  if (selected.type == LOK_SELTYPE_TEXT && !selected.textMissing &&
      !selected.text.empty() && selected.text.size() <= 4096 &&
      decodeUtf8(selected.text, codePoints) &&
      probe::merge::classifyUnit(codePoints) ==
          probe::merge::UnitClass::MergeKey) {
    try {
      startMergeKeyUndo(selected, std::move(codePoints));
    } catch (...) {
      if (selectionBarrierActive())
        finishMergeKeyError("restore");
    }
    return;
  }
  codePoints.clear();
#endif
  const bool geometrySafe = gEditorState.selectionObserved &&
                            gEditorState.selectionRectangles.size() == 1;
  const bool textSafe = selected.type == LOK_SELTYPE_TEXT &&
                        !selected.textMissing && !selected.text.empty() &&
                        selected.text.size() <= 128 &&
                        decodeUtf8(selected.text, codePoints) &&
                        !codePoints.empty() &&
                        !selectionBarrierContainsBoundary(codePoints);
  // The public selection readback can become visible one event-loop turn
  // before the typed geometry callback.  This is not a boundary and must not
  // be rejected; wait for that callback, which will queue this verifier again.
  if (textSafe && !geometrySafe) {
    gSelectionBarrier.stage = SelectionBarrierStage::AwaitingUnitSelection;
    return;
  }
  if (!geometrySafe || !textSafe) {
    finishSelectionBarrierError(
        "EDITOR_BOUNDARY_UNSUPPORTED",
        "one Writer unit did not produce a safe single-line text selection",
        selected.type != LOK_SELTYPE_NONE);
    return;
  }

  gSelectionBarrier.selectedText = selected.text;
  gSelectionBarrier.selectedCodePoints = std::move(codePoints);
  gSelectionBarrier.stage =
      SelectionBarrierStage::AwaitingDeleteCompletion;
  gSelectionBarrier.dispatchSequence = gEditorState.sourceSequence;
  gState.document->pClass->postUnoCommand(
      gState.document, gSelectionBarrier.command.c_str(), nullptr, true);
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void rejectSelectionBarrierAtDeadline(const Command &command) {
  if (gSelectionBarrier.stage !=
      SelectionBarrierStage::AwaitingUnitSelection)
    return;
  const SelectionReadback selected = readSelection();
  // readSelection itself may deliver the typed callback.  In that case its
  // queued positive verifier owns the transaction and the deadline is stale.
  if (!selectionBarrierActive() ||
      command.correlation != gSelectionBarrier.transactionSerial ||
      gSelectionBarrier.stage !=
          SelectionBarrierStage::AwaitingUnitSelection)
    return;

  const bool typedCollapsed = gEditorState.selectionObserved &&
                              gEditorState.selectionRectangles.empty();
  if (selected.type == LOK_SELTYPE_NONE && !selected.textMissing &&
      typedCollapsed) {
#ifdef OXSDK_MERGE_KEY_UNDO
#ifdef OXSDK_E2_V20_LINK_BATCH
    // SPEC-M3-link-batch 10.5 (C): the first 250 ms NONE is no longer a
    // refusal.  The transaction stays in AwaitingUnitSelection for one
    // MergeStepDeadlineMs more, driven by the SAME deadline the engine loop
    // already waits on for this stage (`boundaryDeadline`, read at the three
    // wait sites) -- so a TEXT_SELECTION inside the window takes the ordinary
    // path through handleSelectionBarrierStateCallback, with the attribution's
    // P and anchor fence set up before K1 as today, and the loop synthesises
    // this step again at expiry.  "Pull the caret back" was dropped by the
    // ruling: there is no mechanism for it.
    if (!gSelectionBarrier.boundaryNoopWindow) {
      gSelectionBarrier.boundaryNoopWindow = true;
      gSelectionBarrier.boundaryDeadline =
          std::chrono::steady_clock::now() +
          std::chrono::milliseconds(MergeStepDeadlineMs);
      return;
    }
    // Expiry, second read still NONE, typed selection still collapsed.
    finishSelectionBarrierBoundaryNoop();
#else
    // 10.1(h): the page says "nothing deletable was obtained", not "the end
    // of the document" -- 250 ms of NONE can also be a Shift press not run yet.
    finishMergeKeyError("nothing-selected");
#endif
#else
    finishSelectionBarrierError(
        "EDITOR_BOUNDARY_UNSUPPORTED",
        "one Writer unit remained unselected at the negative boundary deadline",
        false);
#endif
    return;
  }

  std::vector<std::uint32_t> codePoints;
  const bool boundaryText = selected.type == LOK_SELTYPE_TEXT &&
                            !selected.textMissing &&
                            decodeUtf8(selected.text, codePoints) &&
                            selectionBarrierContainsBoundary(codePoints);
#ifdef OXSDK_MERGE_KEY_UNDO
  // Review N5: B is never entered from this branch (13.3) -- the unit's
  // selection came after the deadline, so there is no anchored P -- but on a
  // build that can merge, the page must not be told "cannot delete at a
  // paragraph boundary".
  if (boundaryText) {
    finishMergeKeyError("unit-late");
    return;
  }
#endif
  finishSelectionBarrierError(
      boundaryText ? "EDITOR_BOUNDARY_UNSUPPORTED"
                   : "EDITOR_STATE_UNAVAILABLE",
      boundaryText
          ? "the negative boundary deadline observed a structural separator"
          : "selection text became visible without its required typed callback",
      selected.type != LOK_SELTYPE_NONE || !typedCollapsed);
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void handleSelectionBarrierStateCallback(int callbackType) {
  if (!selectionBarrierActive() || callbackType != LOK_CALLBACK_TEXT_SELECTION)
    return;

  if (gSelectionBarrier.stage ==
      SelectionBarrierStage::AwaitingUnitSelection) {
    gSelectionBarrier.preselectionSequence = gEditorState.sourceSequence;
    gSelectionBarrier.stage = SelectionBarrierStage::UnitVerificationQueued;
    queueSelectionBarrierStep();
    return;
  }

  if (gSelectionBarrier.stage ==
      SelectionBarrierStage::AwaitingDeleteCompletion) {
    if (gEditorState.sourceSequence > gSelectionBarrier.dispatchSequence &&
        gEditorState.selectionObserved &&
        gEditorState.selectionRectangles.empty()) {
      gSelectionBarrier.collapseCallbackSeen = true;
      gSelectionBarrier.collapseSequence = gEditorState.sourceSequence;
      maybeQueueSelectionBarrierFinalVerification();
    }
  }
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
bool handleSelectionBarrierUnoResult(const char *payload) {
#ifdef OXSDK_MERGE_KEY_UNDO
  // Option B's Escapes are proven by the selection turning empty, not by
  // their result; keep the result away from every other handler.
  if (selectionBarrierActive() && gSelectionBarrier.mergeKey &&
      commandResultMatches(payload, ".uno:Escape"))
    return true;
#endif
  if (!selectionBarrierActive() ||
      gSelectionBarrier.stage !=
          SelectionBarrierStage::AwaitingDeleteCompletion)
    return false;
  if (!commandResultMatches(payload, gSelectionBarrier.command)) {
    gSelectionBarrier.acknowledgement = SelectionBarrierAck::Mismatch;
    gSelectionBarrier.acknowledgementSeen = true;
    gSelectionBarrier.acknowledgementSequence = gEditorState.sourceSequence;
    maybeQueueSelectionBarrierFinalVerification();
    return true;
  }
  if (!commandResultSucceeded(payload)) {
    gSelectionBarrier.acknowledgement = SelectionBarrierAck::Failed;
    gSelectionBarrier.acknowledgementSeen = true;
    gSelectionBarrier.acknowledgementSequence = gEditorState.sourceSequence;
    maybeQueueSelectionBarrierFinalVerification();
    return true;
  }
  gSelectionBarrier.acknowledgement = SelectionBarrierAck::MatchedSuccess;
  gSelectionBarrier.acknowledgementSeen = true;
  gSelectionBarrier.acknowledgementSequence = gEditorState.sourceSequence;
  maybeQueueSelectionBarrierFinalVerification();
  return true;
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void handleSelectionBarrierStep(const Command &command) {
  if (!selectionBarrierActive() ||
      command.requestId != gSelectionBarrier.requestId ||
      command.documentHandle != gSelectionBarrier.documentHandle ||
      command.correlation != gSelectionBarrier.transactionSerial ||
      command.documentHandle != gState.documentHandle) {
    return;
  }
  if (command.values[0] == 1 &&
      gSelectionBarrier.stage ==
          SelectionBarrierStage::AwaitingUnitSelection) {
    rejectSelectionBarrierAtDeadline(command);
    return;
  }
#ifdef OXSDK_MERGE_KEY_UNDO
  if (command.values[0] == 2 || command.values[0] == 3) {
    // Review S2: an exception in a merge step must leave through B's exit
    // (keyPosted:true after the key), not as a non-SDK engine error that
    // leaves the transaction BUSY until the SDK's timeout rolls back.
    try {
      if (command.values[0] == 2)
        handleMergeDeadline();
      else
        advanceMerge();
    } catch (...) {
      if (selectionBarrierActive())
        finishMergeKeyError(gSelectionBarrier.keyPosted ? "key-step"
                                                        : "restore");
    }
    return;
  }
#endif
  if (gSelectionBarrier.stage ==
      SelectionBarrierStage::UnitVerificationQueued) {
    verifyAndDispatchSelectionBarrierDelete();
    return;
  }
  if (gSelectionBarrier.stage ==
      SelectionBarrierStage::FinalVerificationQueued)
    maybeFinishSelectionBarrier();
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void startSelectionBarrierDelete(const Command &command, const char *action,
                                 const char *unoCommand, bool backward) {
  if (selectionBarrierActive() ||
      gUnoRequestId.load(std::memory_order_acquire) != 0) {
    emitCommandError(command, "editor-action", "BUSY",
                     "another editor mutation is still in flight");
    return;
  }
  const SelectionReadback initial = readSelection();
  if (initial.type != LOK_SELTYPE_NONE || initial.textMissing ||
      !gEditorState.selectionObserved ||
      !gEditorState.selectionRectangles.empty()) {
    emitCommandError(
        command, "editor-action", "EDITOR_STATE_UNAVAILABLE",
        "selection barrier requires a callback-confirmed collapsed caret");
    return;
  }

  gSelectionBarrier.stage = SelectionBarrierStage::AwaitingUnitSelection;
  gSelectionBarrier.requestId = command.requestId;
  gSelectionBarrier.documentHandle = command.documentHandle;
  gSelectionBarrier.beforeRevision = gState.revision;
  gSelectionBarrier.transactionSerial = gNextSelectionBarrierSerial++;
  gSelectionBarrier.beforeSequence = gEditorState.sourceSequence;
  gSelectionBarrier.backward = backward;
  gSelectionBarrier.action = action;
  gSelectionBarrier.command = unoCommand;
  gSelectionBarrier.boundaryDeadline =
      std::chrono::steady_clock::now() +
      std::chrono::milliseconds(SelectionBarrierBoundaryDeadlineMs);
#ifdef OXSDK_E2_V20_LINK_BATCH
  // 10.6: the cache as it stands the moment the barrier starts, before K1.
  gSelectionBarrier.caretBefore = gEditorState.caret;
  gSelectionBarrier.caretBeforeSequence = gEditorState.sourceSequence;
  gSelectionBarrier.boundaryNoopWindow = false;
#endif
  markAsynchronous(command.requestId);
#ifdef OXSDK_MERGE_KEY_UNDO
  // P_start (10.1(f)), then the attribution's transaction, both before K1.
  gSelectionBarrier.pStartRead = readMergeUndoPayload(gSelectionBarrier.pStart);
  // Review N2: the 250 ms window for K1's selection starts after that read.
  gSelectionBarrier.boundaryDeadline =
      std::chrono::steady_clock::now() +
      std::chrono::milliseconds(SelectionBarrierBoundaryDeadlineMs);
  {
    std::lock_guard<std::mutex> merge(gMergeMutex);
    gMergeAttribution.beginTransaction(backward);
    gMergeTicket = MergeTicket{};
    gMergeTicket.active = true;
    gMergeTicket.serial = gSelectionBarrier.transactionSerial;
    gMergeTicket.requestId = gSelectionBarrier.requestId;
    gMergeTicket.documentHandle = gSelectionBarrier.documentHandle;
  }
#endif

  int keyCode = backward ? com::sun::star::awt::Key::LEFT
                         : com::sun::star::awt::Key::RIGHT;
  keyCode |= EditorShiftModifier;
#ifdef OXSDK_E2_V20_LINK_BATCH
  // `boundaryNoop.waitedMs` counts from K1's post, not from the request.
  gSelectionBarrier.startedAt = std::chrono::steady_clock::now();
#endif
  gState.document->pClass->postKeyEvent(gState.document,
                                        LOK_KEYEVENT_KEYINPUT, 0, keyCode);
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYUP, 0,
                                        keyCode);
}
#endif
#endif

#ifdef OXSDK_E2_V20_LINK_BATCH
// SPEC-M3-link-batch 4.3 / 10.8 (S-10, S-11; ruling 2 conditions 11 and 13):
// the page number's data, as a document-level query like GetSelection.
//
// The reply carries three things and the engine PARSES NONE OF THEM: the raw
// `getPartPageRectangles()` string ("x, y, w, h; x, y, w, h; ..." in twips,
// measured natively in findings/evidence/link-batch/page-rectangles/), the
// document size, and `getParts()` -- two core sources for the page count, so
// P1 can assert rectangles = parts without self-reference.  Parsing lives in
// the SDK, where a malformed string is a typed error and never an empty list.
//
// It does NOT refresh gState.documentWidthTwips/HeightTwips: those are what
// the paint reply's `documentSizeChanged` compares against ("as of the last
// paint", finding 062), and 10.8 keeps that trigger exactly as it is today
// beside the new counter.
void handlePageRectangles(const Command &command) {
  if (!requireDocument(command, "page-rectangles"))
    return;
  char *rectangles =
      gState.document->pClass->getPartPageRectangles(gState.document);
  if (!rectangles) {
    emitCommandError(command, "page-rectangles", "LOK_ERROR", kitError());
    return;
  }
  long width = 0;
  long height = 0;
  gState.document->pClass->getDocumentSize(gState.document, &width, &height);
  const int parts = gState.document->pClass->getParts(gState.document);
#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"page-rectangles\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << ",\"rectangles\":\""
       << jsonEscape(rectangles) << "\",\"parts\":" << parts
       << ",\"documentWidthTwips\":" << width
       << ",\"documentHeightTwips\":" << height << "}";
  std::free(rectangles);
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}
#endif

#ifdef OXSDK_EDITOR_DISCOVERY
void handleGetSelection(const Command &command) {
  if (!requireDocument(command, "get-selection"))
    return;
  const SelectionReadback readback = readSelection();
  if (readback.textMissing) {
    emitCommandError(
        command, "get-selection", "LOK_ERROR",
        "selection type is text but no utf-8 text was returned");
    return;
  }
#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"selection\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << ",\"selectionType\":\""
       << selectionTypeName(readback.type)
       << "\",\"mimeType\":\"text/plain;charset=utf-8\",\"text\":\""
       << jsonEscape(readback.text.c_str()) << "\"}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}
#endif

void handleReplaceSelection(const Command &command) {
  if (!requireDocument(command, "replace-selection") ||
      !requireRevision(command, "replace-selection"))
    return;
  if (!gState.document->pClass->paste(
          gState.document, "text/plain;charset=utf-8", command.text.data(),
          command.text.size())) {
    emitCommandError(command, "replace-selection", "LOK_ERROR",
                     "LibreOfficeKit rejected the replacement paste");
    return;
  }
  advanceRevision();
#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"replaced\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << "}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

void startUnoMutation(const Command &command, const char *operation,
                      const char *unoCommand, const std::string &arguments) {
#ifdef OXSDK_E2_V23_LINK_BATCH
  const std::string operationName(operation), unoName(unoCommand);
  const auto beforeRevision = gState.revision;
  const auto beforeSequence = gEditorState.sourceSequence;
  const std::string action = gEditorUnoAction;
  const bool option = command.values[2] != 0;
  expectOrderedUno(unoName);
  setOrderedReply([command, operationName, unoName, action, beforeRevision, beforeSequence, option] {
    composeOrderedUno(command, operationName, unoName, action, beforeRevision, beforeSequence, option);
  });
  gState.document->pClass->postUnoCommand(gState.document, unoCommand,
      arguments.empty() ? nullptr : arguments.c_str(), true);
  if (operationName == "comment-added")
    gState.document->pClass->postUnoCommand(gState.document, ".uno:Escape", nullptr, false);
#else
  if (gUnoRequestId.load(std::memory_order_acquire) != 0) {
    emitCommandError(command, operation, "BUSY",
                     "another UNO mutation is still in flight");
    return;
  }
  gUnoOperation = operation;
  gUnoRequestId.store(command.requestId, std::memory_order_release);
  markAsynchronous(command.requestId);
  gState.document->pClass->postUnoCommand(
      gState.document, unoCommand,
      arguments.empty() ? nullptr : arguments.c_str(), true);
#endif
}

void handleUndo(const Command &command) {
  if (!requireDocument(command, "undone") ||
      !requireRevision(command, "undo"))
    return;
  startUnoMutation(command, "undone", ".uno:Undo", {});
}

void handleRedo(const Command &command) {
  if (!requireDocument(command, "redone") ||
      !requireRevision(command, "redo"))
    return;
  startUnoMutation(command, "redone", ".uno:Redo", {});
}

void handleAddComment(const Command &command) {
  if (!requireDocument(command, "comment-added") ||
      !requireRevision(command, "add-comment"))
    return;
  std::ostringstream arguments;
  arguments << "{\"Text\":{\"type\":\"string\",\"value\":\""
            << jsonEscape(command.text.c_str())
            << "\"},\"Author\":{\"type\":\"string\",\"value\":\""
            << jsonEscape(command.name.c_str()) << "\"}}";
  startUnoMutation(command, "comment-added", ".uno:InsertAnnotation",
                   arguments.str());
}

void emitCommandValues(const Command &command, const char *operation,
                       const char *eventType, const char *unoCommand) {
  if (!requireDocument(command, operation))
    return;
  char *values =
      gState.document->pClass->getCommandValues(gState.document, unoCommand);
  if (!values) {
    emitCommandError(command, operation, "LOK_ERROR", kitError());
    return;
  }
#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion << ",\"type\":\""
       << eventType << "\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << ",\"dataJson\":\""
       << jsonEscape(values) << "\"}";
  std::free(values);
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

void handleListComments(const Command &command) {
  emitCommandValues(command, "list-comments", "comments",
                    ".uno:ViewAnnotations");
}

void handleSetTrackChanges(const Command &command) {
  if (!requireDocument(command, "track-changes-set") ||
      !requireRevision(command, "set-track-changes"))
    return;
  std::ostringstream arguments;
  arguments << "{\"TrackChanges\":{\"type\":\"boolean\",\"value\":"
            << (command.values[0] ? "true" : "false") << "}}";
  startUnoMutation(command, "track-changes-set", ".uno:TrackChanges",
                   arguments.str());
}

void handleListChanges(const Command &command) {
  emitCommandValues(command, "list-changes", "tracked-changes",
                    ".uno:AcceptTrackedChanges");
}

#ifdef OXSDK_EDITOR_DISCOVERY
const char *editorActionName(std::uint32_t action) {
  switch (action) {
  case OXSDK_EDITOR_MOVE_CHARACTER_LEFT:
    return "move-character-left";
  case OXSDK_EDITOR_MOVE_CHARACTER_RIGHT:
    return "move-character-right";
  case OXSDK_EDITOR_MOVE_LINE_UP:
    return "move-line-up";
  case OXSDK_EDITOR_MOVE_LINE_DOWN:
    return "move-line-down";
  case OXSDK_EDITOR_MOVE_LINE_HOME:
    return "move-line-home";
  case OXSDK_EDITOR_MOVE_LINE_END:
    return "move-line-end";
  case OXSDK_EDITOR_DELETE_BACKWARD:
    return "delete-backward";
  case OXSDK_EDITOR_DELETE_FORWARD:
    return "delete-forward";
  case OXSDK_EDITOR_INSERT_PARAGRAPH_BREAK:
    return "insert-paragraph-break";
  case OXSDK_EDITOR_INSERT_LINE_BREAK:
    return "insert-line-break";
  case OXSDK_EDITOR_UNDO:
    return "undo";
  case OXSDK_EDITOR_REDO:
    return "redo";
  case OXSDK_EDITOR_SET_BOLD:
    return "set-bold";
  case OXSDK_EDITOR_SET_ITALIC:
    return "set-italic";
  case OXSDK_EDITOR_SET_UNDERLINE:
    return "set-underline";
  case OXSDK_EDITOR_SET_STRIKETHROUGH:
    return "set-strikethrough";
  case OXSDK_EDITOR_DELETE_SELECTION:
    return "delete-selection";
  case OXSDK_EDITOR_SELECT_ALL:
    return "select-all";
  case OXSDK_EDITOR_SET_PARAGRAPH_BODY:
    return "set-paragraph-body";
  case OXSDK_EDITOR_SET_PARAGRAPH_HEADING:
    return "set-paragraph-heading";
  case OXSDK_EDITOR_SET_LIST_NONE:
    return "set-list-none";
  case OXSDK_EDITOR_SET_LIST_UNORDERED:
    return "set-list-unordered";
  case OXSDK_EDITOR_SET_LIST_ORDERED:
    return "set-list-ordered";
#ifdef OXSDK_E2_V21_LINK_BATCH
  case OXSDK_EDITOR_MOVE_DOCUMENT_START:
    return "move-document-start";
  case OXSDK_EDITOR_MOVE_DOCUMENT_END:
    return "move-document-end";
#endif
  default:
    return "unsupported";
  }
}

bool editorActionMutates(std::uint32_t action) {
#ifdef OXSDK_E2_V21_LINK_BATCH
  // SPEC-M3-link-batch-v21 4.1: `action >= 7` would class the two document
  // moves (24, 25) as mutations that demand a revision.  They change nothing,
  // like 1-6.  Select-all (23) keeps its class.
  if (action == OXSDK_EDITOR_MOVE_DOCUMENT_START ||
      action == OXSDK_EDITOR_MOVE_DOCUMENT_END)
    return false;
#endif
  return action >= OXSDK_EDITOR_DELETE_BACKWARD;
}

bool editorActionMoves(std::uint32_t action) {
  return action >= OXSDK_EDITOR_MOVE_CHARACTER_LEFT &&
         action <= OXSDK_EDITOR_MOVE_LINE_END;
}

void emitEditorActionResult(const Command &command, const char *action,
                            std::uint32_t beforeRevision,
                            std::uint64_t beforeSequence, bool changedKnown,
                            bool changed, const char *completion) {
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-action-completed\",\"requestId\":"
       << command.requestId << ",\"documentHandle\":"
       << gState.documentHandle << ",\"beforeRevision\":" << beforeRevision
       << ",\"revision\":" << gState.revision << ",\"action\":\""
       << jsonEscape(action) << "\",\"option\":"
       << (command.values[2] ? "true" : "false") << ",\"changed\":";
  if (changedKnown)
    json << (changed ? "true" : "false");
  else
    json << "null";
  json << ",\"completion\":\"" << jsonEscape(completion)
       << "\",\"callbackSequenceBefore\":" << beforeSequence
       << ",\"callbackSequenceAfter\":" << gEditorState.sourceSequence
       << ",\"state\":{";
  appendEditorState(json);
  json << "}}";
  emitJson(json.str());
}

// Finding 045: the inline format slots are declared `Toggle = TRUE`, and core
// takes the toggle branch only when the argument set is EMPTY
// (sfx2/source/control/unoctitm.cxx:733-737, "execute using bindings, enables
// support for toggle/enum etc.").  With a single argument named for the slot,
// TransformParameters hands it to PutValue(value, 0), and MemberId 0 is the
// boolean accessor for all four items -- so the command becomes a setter.
//
// Measured natively before this was written, on core 671c848b: parameter false
// at a caret in plain text produces `fo:font-weight="normal"`, parameter false
// over an already-bold selection REMOVES the property, and the bare form
// toggles relative to the state at the caret.  Evidence and the seven
// registered predictions: findings/evidence/045/native/.
std::string inlineFormatArgument(const char *slot, bool enabled) {
  return std::string("{\"") + slot + "\":{\"type\":\"boolean\",\"value\":"
         + (enabled ? "true" : "false") + "}}";
}

void startEditorUnoAction(const Command &command, const char *action,
                          const char *unoCommand,
                          bool semanticReadback = false,
                          const std::string &arguments = {}) {
  if (gUnoRequestId.load(std::memory_order_acquire) != 0) {
    emitCommandError(command, "editor-action", "BUSY",
                     "another UNO mutation is still in flight");
    return;
  }
  EditorSemanticSnapshot semanticSnapshot;
  if (semanticReadback) {
    if (!readEditorSemanticSnapshot(semanticSnapshot)) {
      emitCommandError(
          command, "editor-action", "EDITOR_SEMANTIC_READBACK_UNAVAILABLE",
          "focused-paragraph readback is unavailable before mutation");
      return;
    }
    if (!deleteHasSafeSemanticPrecondition(action, semanticSnapshot)) {
      emitCommandError(
          command, "editor-action", "EDITOR_BOUNDARY_UNSUPPORTED",
          "paragraph-boundary delete is outside the safe discovery scope");
      return;
    }
  }
  gEditorUnoAction = action;
  gEditorUnoCommand = unoCommand;
  gEditorUnoBeforeRevision = gState.revision;
  gEditorUnoBeforeSequence = gEditorState.sourceSequence;
  gEditorUnoOption = command.values[2] != 0;
  gEditorUnoSemanticReadback = semanticReadback;
  startUnoMutation(command, "editor-action-completed", unoCommand, arguments);
}

#ifdef OXSDK_E2_FORMAT_BARRIER
bool editorActionIsParagraphFormat(std::uint32_t action) {
  return action >= OXSDK_EDITOR_SET_PARAGRAPH_BODY &&
         action <= OXSDK_EDITOR_SET_LIST_ORDERED;
}

// One paragraph style is three different strings, and A2 had to measure all
// three rather than assume they matched:
//
//   applied via .uno:StyleApply Style argument : "Text body"
//   stored in ODT as text:style-name           : "Text_20_body"
//   reported back by .uno:StyleApply state     : "Body Text"
//
// Both values below are compiled in and matched whole.  JS never supplies a
// style name, and no prefix or fuzzy matching is done: a name outside these
// sets fails the postcondition, which keeps A2's recorded payloads the way to
// correct them rather than a reason to loosen the check.
const char *const kHeadingAppliedStyle = "Heading 1";
const char *const kBodyAppliedStyle = "Text body";
const char *const kHeadingReportedStyles[] = {"Heading 1"};
const char *const kBodyReportedStyles[] = {"Body Text"};

std::vector<std::string> styleCandidates(bool heading) {
  std::vector<std::string> names;
  if (heading)
    for (const char *name : kHeadingReportedStyles)
      names.emplace_back(name);
  else
    for (const char *name : kBodyReportedStyles)
      names.emplace_back(name);
  return names;
}

std::string styleApplyArguments(bool heading) {
  return std::string("{\"Style\":{\"type\":\"string\",\"value\":\"") +
         (heading ? kHeadingAppliedStyle : kBodyAppliedStyle) +
         "\"},\"FamilyName\":{\"type\":\"string\",\"value\":"
         "\"ParagraphStyles\"}}";
}

// Finding 030: dispatched bare, these two commands ask for the *opposite* of
// what is there.  svx/sdi/svx.sdi:2251 and :4985 declare an `On` boolean
// (FN_PARAM_1) and sw/source/uibase/shells/txtnum.cxx:81-108 uses it as an
// explicit mode, falling back to `!SelectionHasBullet()` only when it is
// absent.  A closed set-list(...) enum is a setter, so it has to send the
// parameter -- the same correction finding 019 made for paragraph styles, where
// the convenient command name was also not the dispatchable one.
//
// This was latent under the fail-closed design, which only dispatches when the
// cached state is known and differs from the target -- exactly when a toggle
// does the right thing by accident.  It becomes live the moment the
// precondition read goes away.
const char *const kListOnArguments = "{\"On\":{\"type\":\"boolean\","
                                     "\"value\":true}}";

void startFormatBarrierActionResolved(const Command &command,
                                      std::uint32_t action, const char *name);

// One caller-facing code for every way the barrier ends without a clean read
// of a single paragraph.  The caller's only decision is the same in all of them
// -- do not replay, the document's state is unknown to us -- and giving each
// shape its own code would invite branching on distinctions the caller cannot
// act on.  EDITOR_FORMAT_POSTCONDITION_FAILED keeps its narrower meaning: one
// paragraph was read cleanly and it is not in the state the action asked for.
const char *const kFormatMutationOutcomeUnknown = "MUTATION_OUTCOME_UNKNOWN";

// Every awaiting stage gets a fresh deadline as it is entered, so a barrier
// that keeps making progress is never cut off by a clock started three stages
// ago; only a stage that stops advancing runs out.
#ifndef OXSDK_E2_V23_LINK_BATCH
void armFormatBarrierDeadline() {
  gFormatBarrier.stageDeadline = std::chrono::steady_clock::now() +
                                 std::chrono::milliseconds(
                                     FormatBarrierStageDeadlineMs);
  gFormatBarrier.stageDeadlineArmed = true;
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void failFormatBarrierAtDeadline() {
  // Re-checked by the caller as well; repeated here because this function is
  // reachable from two loops and neither is allowed to end a barrier that has
  // already moved on.
  if (!formatBarrierActive() || !gFormatBarrier.stageDeadlineArmed)
    return;
  gFormatBarrier.failureShape =
      std::string("stage-deadline:") +
      formatBarrierStageName(gFormatBarrier.stage);
  // Never a success.  At the document-end empty paragraph getTextSelection
  // still returns 490 bytes of markup with no selection at all (native 26.8),
  // a single <p> -- so a deadline that fell back to "read whatever is there"
  // would satisfy the set-paragraph-body postcondition without any selection
  // having existed.  The rule has an instance, not just a principle behind it.
  failFormatBarrier(kFormatMutationOutcomeUnknown,
                    "the format barrier stopped advancing before it could read "
                    "the paragraph, so what the dispatch did is unknown");
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void queueFormatBarrierStep(FormatBarrierStage next) {
  gFormatBarrier.stage = next;
  Command step{CommandType::EditorFormatBarrierStep};
  step.requestId = gFormatBarrier.requestId;
  step.documentHandle = gFormatBarrier.documentHandle;
  step.correlation = gFormatBarrier.serial;
  if (submit(std::move(step)) != SubmitStatus::Ok)
    failFormatBarrier("EDITOR_STATE_UNAVAILABLE",
                      "format barrier could not schedule a non-reentrant "
                      "postcondition read");
}
#endif

// SPEC E2-A 2.8: a collapsed caret reads back nothing, so the paragraph has to
// be selected first.  Paragraph-relative, not line-relative -- applying a
// heading style rewraps the text, and a line-relative walk would then select
// something else and read back a postcondition for a paragraph nobody touched.
//
// One dispatch, notify=true.  The flag is load-bearing rather than stylistic:
// this command's result is what attributes the selection the next stage reads.
//
// This used to be two commands, and the pair taught two things worth keeping in
// view.  Mixing the notify flags across them reordered their effects (finding
// 033), because the two values are two dispatch paths; and the pair escaped to
// a neighbouring paragraph whenever the caret already sat at a paragraph edge
// (finding 034).  A single dispatch has neither problem to have.
#ifndef OXSDK_E2_V23_LINK_BATCH
void postFormatBarrierParagraphSelection() {
  gState.document->pClass->postUnoCommand(
      gState.document, kFormatBarrierSelectCommand, nullptr, true);
}
#endif

// Does the selection the read is about to serialise actually cover the caret
// the action was dispatched from?
//
// The readback describes whatever is selected, and nothing else in this barrier
// ties that back to the paragraph the command changed.  Comparing the two is
// the cheapest available identity check: the restore point is the caret as it
// was *before* the dispatch, and if the selection does not span it then the
// selection is somewhere else and the verdict would be about another paragraph.
//
// Vertical only.  Horizontal position within a line says nothing about which
// paragraph is selected, and a selection that wraps has rectangles at every
// x.  This does not survive an extreme reflow -- the dispatch itself changes
// the paragraph's height, which is the residual finding 033 records and which
// needs a paragraph identity LOK does not expose -- so it is a check that can
// fail, not a proof.
#ifndef OXSDK_E2_V23_LINK_BATCH
void checkFormatBarrierContainment() {
  gFormatBarrier.containmentChecked = false;
  gFormatBarrier.containmentHeld = false;
  if (!gFormatBarrier.restorePointValid ||
      gEditorState.selectionRectangles.empty())
    return;
  long top = 0;
  long bottom = 0;
  bool first = true;
  for (const EditorRect &rectangle : gEditorState.selectionRectangles) {
    if (!rectangle.available)
      continue;
    const long rectangleTop = rectangle.y;
    const long rectangleBottom = rectangle.y + rectangle.height;
    if (first) {
      first = false;
      top = rectangleTop;
      bottom = rectangleBottom;
      continue;
    }
    top = std::min(top, rectangleTop);
    bottom = std::max(bottom, rectangleBottom);
  }
  if (first)
    return;
  gFormatBarrier.selectionTop = top;
  gFormatBarrier.selectionBottom = bottom;
  gFormatBarrier.restoreCentre =
      gFormatBarrier.restorePoint.y + gFormatBarrier.restorePoint.height / 2;
  gFormatBarrier.containmentChecked = true;
  gFormatBarrier.containmentHeld =
      gFormatBarrier.restoreCentre >= top && gFormatBarrier.restoreCentre <= bottom;
}
#endif

// Finding 037: is this selection one the html readback is known to survive?
//
// getTextSelection(…, "text/html", …) does not return on a selection that
// contains an as-char image.  Not "is slow" -- does not return: the engine
// thread stops inside the call, the command queue is never drained again, and
// the 5000ms stage deadline cannot fire because it is only consulted in the
// branch the loop takes when that queue is empty.  Measured on both browsers,
// on both engines that have ever run this fixture, for all five closed
// actions, and natively the identical call on the identical paragraph returns
// 798 bytes in 1ms.  So this is not a timeout to tune; it is a call that must
// not be made.
//
// The guard reads the selection type first, which is safe on exactly the
// selection that wedges: getSelectionTypeAndText("text/plain…") returned
// "complex" in 1ms there, twice, with the paragraph selected to the same
// endpoints the barrier selects.  That is the whole reason a guard is possible
// at all -- if asking the type had wedged too, there would be nothing to ask.
//
// TEXT only.  LOK_SELTYPE_LARGE_TEXT is documented in
// LibreOfficeKitEnums.h:56 as "unused (same as LOK_SELTYPE_COMPLEX)", so
// accepting it would be accepting a value core does not produce; NONE means
// there is nothing to read.  Refusing everything that is not TEXT is the
// fail-closed rule this barrier uses everywhere else, and here it has an
// instance behind it rather than a principle.
bool formatBarrierSelectionIsReadable() {
  const SelectionReadback selection = readSelection();
  gFormatBarrier.selectionType = selection.type;
  gFormatBarrier.selectionTypeReadable = selection.type == LOK_SELTYPE_TEXT;
#ifdef OXSDK_037_GUARD_OFF
  // Diagnostic builds only, and never defined for any shipped or verdict-bound
  // profile.  Finding 040 predicts that the thread parked during finding 037
  // sits at Scheduler::IdlesLockGuard, but the artifact that reproduces 037 has
  // no name section and the one that has names carries this guard, so the two
  // can never be the same build.  Turning the guard off is the only way to make
  // 037 reachable on a build that can name its own frames -- and the prediction
  // is falsifiable precisely because that build has to be made.
  //
  // The type is still read and still recorded; only the refusal is skipped, so
  // evidence from such a build still says what the selection type was.
  return true;
#else
  return gFormatBarrier.selectionTypeReadable;
#endif
}

// SPEC E2-B 9.9: decide the route BEFORE the dispatch, from the caller's own
// selection.
//
// Returns false to refuse before dispatching anything, in which case the shape
// is written to `shape` and the document is untouched.  That is a strictly
// better outcome than the post-dispatch MUTATION_OUTCOME_UNKNOWN this build
// produces today for the same inputs: nothing was sent, so nothing can have
// changed.
//
// Finding 037 governs the order here and is the reason the type is read first.
// getTextSelection(..., "text/html", ...) does not return on a selection
// holding an as-char image, and this is a NEW call site for it -- earlier than
// the barrier's own, with no stage armed and therefore no deadline to fall
// back on.  Reading the type first and refusing anything that is not TEXT is
// what keeps that call from ever being made on such a selection.
bool routeFormatBarrier(FormatStateBarrier &barrier,
                        std::uint32_t internalAction, std::string &shape) {
  // `selectionObserved` is load-bearing here for the same reason it is in the
  // ten inherited actions' gate below: an empty rectangle list means "no
  // selection" ONLY once core has reported one at least once (see the field's
  // own comment at the declaration).  Before that it means "nobody has said
  // yet", and admitting that as a collapsed caret is classifying without an
  // observation.
  //
  // The 2026-08-15 review that added the other gate recorded this one as fixed
  // at the same time.  It was not: a second-party audit on 2026-08-16 found
  // this function still classifying an unobserved selection as Collapsed, and
  // reading the source confirmed it.  "Both places were fixed" was a sentence,
  // not a state of the tree.
  if (!gEditorState.selectionObserved) {
    shape = "routing-selection-not-observed";
    return false;
  }
  if (gEditorState.selectionRectangles.empty()) {
    barrier.route = FormatBarrierRoute::Collapsed;
  } else {
    const SelectionReadback selection = readSelection();
    if (selection.type != LOK_SELTYPE_TEXT) {
      shape = "routing-selection-not-readable";
      return false;
    }
    char *html = gState.document->pClass->getTextSelection(
        gState.document, "text/html", nullptr);
    const std::string markup = html ? std::string(html) : std::string();
    std::free(html);
    const FormatReadback parsed = parseFormatReadback(markup);
    barrier.preBlockCount = parsed.blockCount;
    barrier.preBlockCountObserved = true;
    barrier.preBlockTexts = blockTexts(extractBlocks(markup));
    barrier.route = parsed.blockCount >= 2 ? FormatBarrierRoute::RangeCross
                                           : FormatBarrierRoute::RangeSingle;
  }

  const std::uint32_t gesture =
      barrier.route == FormatBarrierRoute::Collapsed    ? kGestureCollapsed
      : barrier.route == FormatBarrierRoute::RangeSingle ? kGestureRangeSingle
                                                         : kGestureRangeCross;
  if (!editorGesturePermitted(internalAction, gesture)) {
    shape = "gesture-not-permitted";
    return false;
  }
  return true;
}

// The cross-paragraph postcondition, read from the selection the CALLER made
// and which is still there -- not from one this barrier created.
//
// The barrier's usual read replaces the selection with .uno:SelectText, which
// covers exactly one paragraph; on a two-paragraph mutation that reports
// success for half of what changed, which is the defect this route exists to
// remove.  Nothing here collapses or re-selects before the read.
void checkFormatBarrierCrossParagraph() {
  gFormatBarrier.crossChecked = true;
  if (!formatBarrierSelectionIsReadable())
    return;
  char *html = gState.document->pClass->getTextSelection(
      gState.document, "text/html", nullptr);
  const std::string markup = html ? std::string(html) : std::string();
  std::free(html);
  gFormatBarrier.readbackBytes = markup.size();
  gFormatBarrier.readbackHtml =
      markup.size() > FormatReadbackEvidenceLimit
          ? markup.substr(0, FormatReadbackEvidenceLimit)
          : markup;
  gFormatBarrier.readback = parseFormatReadback(markup);
  const std::vector<ReadbackBlock> parsedBlocks = extractBlocks(markup);
  gFormatBarrier.postBlockCount = gFormatBarrier.readback.blockCount;
  gFormatBarrier.postBlockCountObserved = true;
  gFormatBarrier.postBlockTexts = blockTexts(parsedBlocks);

  // Identity: same number of blocks, and each block's text unchanged.  A
  // selection that shrank to one paragraph loses a block AND loses its text,
  // so either half catches it; both are checked because they fail for
  // different reasons and the shape should say which.
  gFormatBarrier.crossIdentityHeld =
      gFormatBarrier.postBlockTexts.size() ==
          gFormatBarrier.preBlockTexts.size() &&
      !gFormatBarrier.preBlockTexts.empty() &&
      gFormatBarrier.postBlockTexts == gFormatBarrier.preBlockTexts;

  // State: every block reached the target, not just the first.  The readback
  // parser keeps only the first tag, so the counts are what carry "every".
  const FormatReadback &readback = gFormatBarrier.readback;
  const std::size_t blocks = gFormatBarrier.postBlockTexts.size();
  switch (gFormatBarrier.target) {
  case FormatBarrierTarget::ListBullet:
    gFormatBarrier.crossStateHeld =
        readback.listTag == "ul" && readback.itemCount == blocks;
    break;
  case FormatBarrierTarget::ListNumber:
    gFormatBarrier.crossStateHeld =
        readback.listTag == "ol" && readback.itemCount == blocks;
    break;
  case FormatBarrierTarget::ListNone:
    gFormatBarrier.crossStateHeld =
        readback.listTag.empty() && readback.itemCount == 0;
    break;
  case FormatBarrierTarget::ParagraphStyle:
    // EVERY block tag, not the first one.  parseFormatReadback keeps only the
    // first, and reading that as if it described the range is the exact defect
    // this route removes -- so the per-block tags carry it instead.
    gFormatBarrier.crossStateHeld =
        everyBlockHasTag(parsedBlocks, gFormatBarrier.expectedBlockTag);
    break;
  case FormatBarrierTarget::None:
    gFormatBarrier.crossStateHeld = false;
    break;
  }
}

#ifndef OXSDK_E2_V23_LINK_BATCH
void readFormatBarrierPostcondition() {
  // Finding 046.  Asked HERE, at the read, and not at the verdict: by the time
  // the verdict runs the restore has been posted, so the caret is back on the
  // dispatch paragraph and the comparison would hold for the wrong reason --
  // it would be measuring the restore, not the read.
  gFormatBarrier.readbackParagraphKnown = refreshCaretParagraph();
  gFormatBarrier.readbackParagraphFingerprint = gEditorState.a11yContentHash;
  gFormatBarrier.readbackParagraphUsable = gEditorState.a11yFingerprintUsable;
  char *html = gState.document->pClass->getTextSelection(
      gState.document, "text/html", nullptr);
  const std::string markup = html ? std::string(html) : std::string();
  std::free(html);
  gFormatBarrier.readbackBytes = markup.size();
  gFormatBarrier.readbackHtml =
      markup.size() > FormatReadbackEvidenceLimit
          ? markup.substr(0, FormatReadbackEvidenceLimit)
          : markup;
  gFormatBarrier.readback = parseFormatReadback(markup);
}
#endif

bool formatBarrierReadbackSatisfied() {
  const FormatReadback &readback = gFormatBarrier.readback;
  // unknownTag, malformedNesting and footnoteApparatus are judged before this
  // function is reached, each with its own failure shape.  They are still
  // tested here so that this predicate cannot report satisfaction from a scan
  // that aborted, whatever order a future caller uses.  Finding 037's guard is
  // in the same list for the same reason, and it is the strongest case of it:
  // when the guard refuses, no scan happened at all.
  if (!gFormatBarrier.selectionTypeReadable || !readback.parsed ||
      readback.unknownTag || readback.malformedNesting ||
      readback.footnoteApparatus)
    return false;
  if (!gFormatBarrier.expectedListTag.empty()) {
    const std::string observed =
        readback.listTag.empty() ? std::string("none") : readback.listTag;
    if (observed != gFormatBarrier.expectedListTag)
      return false;
  }
  if (!gFormatBarrier.expectedBlockTag.empty() &&
      readback.blockTag != gFormatBarrier.expectedBlockTag)
    return false;
  return true;
}

#ifdef OXSDK_E2_V28_LAST_BLOCK
// SPEC-M3-v28-last-line-fallback 4.1 item 5.  formatBarrierReadbackSatisfied on
// the fallback's readback and its LAST block.  The fallback selects from the end
// of the previous paragraph to the dispatch paragraph, so the last block is the
// dispatch paragraph and the first block is not (native-q52's n8 trap).
bool formatBarrierFallbackReadbackSatisfied() {
  const FormatReadback &readback = gFormatBarrier.fallbackReadback;
  if (!gFormatBarrier.fallbackReadable || !readback.parsed ||
      readback.unknownTag || readback.malformedNesting ||
      readback.footnoteApparatus || readback.lastBlockTag.empty())
    return false;
  if (!gFormatBarrier.expectedListTag.empty()) {
    const std::string observed =
        readback.lastListTag.empty() ? std::string("none") : readback.lastListTag;
    if (observed != gFormatBarrier.expectedListTag)
      return false;
  }
  if (!gFormatBarrier.expectedBlockTag.empty() &&
      readback.lastBlockTag != gFormatBarrier.expectedBlockTag)
    return false;
  return true;
}
#endif

// Putting the caret back is part of the operation, not cleanup after it.  The
// stage waits for the collapse to be confirmed rather than assuming the posted
// restore worked, because "we asked for it" is the class of claim this project
// keeps having to retract.
void postFormatBarrierRestore() {
  if (!gFormatBarrier.restorePointValid)
    return;
  gState.document->pClass->setTextSelection(
      gState.document, LOK_SETTEXTSELECTION_RESET,
      gFormatBarrier.restorePoint.x,
      gFormatBarrier.restorePoint.y + gFormatBarrier.restorePoint.height / 2);
}

#ifndef OXSDK_E2_V23_LINK_BATCH
void finishFormatBarrierAfterRestore() {
  gFormatBarrier.restoreConfirmed = gEditorState.selectionRectangles.empty();

  // The cross-paragraph route is judged on its own two readings and never
  // reaches the checks below: those describe a selection this barrier created
  // with .uno:SelectText, and on this route it created none.
  if (gFormatBarrier.route == FormatBarrierRoute::RangeCross) {
    if (!gFormatBarrier.crossChecked ||
        !gFormatBarrier.selectionTypeReadable) {
      gFormatBarrier.failureShape = "block-extraction-failed";
      failFormatBarrier(
          kFormatMutationOutcomeUnknown,
          "the action was dispatched but the selection could not be read back "
          "to check it -- look at the paragraphs and use undo if they are not "
          "what you wanted");
      return;
    }
    if (!gFormatBarrier.crossIdentityHeld) {
      // Which half failed changes what a reader should conclude, so they are
      // separate shapes: a different block COUNT means the selection changed
      // size, a different TEXT means it moved or the document did.
      gFormatBarrier.failureShape =
          gFormatBarrier.postBlockTexts.size() !=
                  gFormatBarrier.preBlockTexts.size()
              ? "block-count-changed"
              : "block-text-mismatch";
      failFormatBarrier(
          kFormatMutationOutcomeUnknown,
          "the action was dispatched but the paragraphs it covered are no "
          "longer the ones that were selected, so it could not be checked -- "
          "look at them and use undo if they are not what you wanted");
      return;
    }
    if (!gFormatBarrier.crossStateHeld) {
      gFormatBarrier.failureShape = "postcondition-not-met";
      failFormatBarrier(
          "EDITOR_FORMAT_POSTCONDITION_FAILED",
          "the document does not show the state this action asked for");
      return;
    }
    completeFormatBarrier();
    return;
  }
  // Ordered by what each answer is about.  The first two say the read does not
  // describe one known paragraph, so no verdict about the postcondition is
  // available at all; only after both hold does "is it in the target state"
  // become a question with a meaning.  Reversing the order would let a
  // two-paragraph read that happens to start with the right tag report success.
  // Finding 035 / M2.  These three come FIRST, before multiBlock and before
  // containment, because each of them means the scan stopped early: the counts
  // are truncated at that point, so multiBlock is not a fact about the document
  // but an artefact of where the scan gave up.  They are three channels rather
  // than one on purpose -- "we refused a shape we measured and chose not to
  // verify", "we met a tag nobody has ever measured" and "the markup is not
  // shaped like anything we have seen" are different signals, and folding them
  // together would make the last one invisible under the traffic of the first.
  // Finding 037 comes first, before every readback shape, because when the
  // guard refuses there IS no readback -- the html read was never made, so
  // `parsed` is false and every count is zero.  Judged in any later position,
  // this refusal would be reported as whatever an empty scan looks like
  // (multiBlock false, blockTag empty, therefore "postcondition not met"),
  // which says the document is in the wrong state when what actually happened
  // is that nobody looked.
  if (!gFormatBarrier.selectionTypeReadable) {
    gFormatBarrier.failureShape = "selection-type-not-readable";
    failFormatBarrier(
        kFormatMutationOutcomeUnknown,
        "this paragraph contains an image or another object, and reading it "
        "back would stop this document responding, so the check was not made. "
        "The action was dispatched and the paragraph may already have changed "
        "-- check it and use undo if it is not what you wanted. This is a "
        "limit of the check, not a problem with the document");
    return;
  }
  if (gFormatBarrier.readback.footnoteApparatus) {
    gFormatBarrier.failureShape = "footnote-apparatus-readback";
    failFormatBarrier(
        kFormatMutationOutcomeUnknown,
        "this paragraph carries a footnote or endnote. The action was "
        "dispatched and the paragraph may already have changed, but this build "
        "does not verify paragraphs with notes -- check the paragraph and use "
        "undo if it is not what you wanted. This is a limit of the check, not "
        "a problem with the document");
    return;
  }
  if (gFormatBarrier.readback.unknownTag) {
    gFormatBarrier.failureShape = "unknown-structural-tag";
    failFormatBarrier(
        kFormatMutationOutcomeUnknown,
        "the postcondition read met a tag at body level that this build has "
        "never measured, so no verdict about it is available");
    return;
  }
  if (gFormatBarrier.readback.malformedNesting) {
    gFormatBarrier.failureShape = "malformed-readback-nesting";
    failFormatBarrier(
        kFormatMutationOutcomeUnknown,
        "the postcondition read closed a block that was never opened, so the "
        "markup is not shaped like any sample this build was measured against");
    return;
  }
  if (gFormatBarrier.readback.multiBlock) {
    gFormatBarrier.failureShape = "multi-block-readback";
    failFormatBarrier(
        kFormatMutationOutcomeUnknown,
        "the postcondition read covered more than one paragraph, so it does "
        "not describe the paragraph this action was dispatched on");
    return;
  }
  // Finding 046, and the fix the finding has been waiting for since 2026-08-15.
  //
  // The barrier used to report `postcondition-not-met` -- "the document does
  // not show the state this action asked for" -- when `.uno:SelectText`
  // overshot an empty paragraph and the read described the NEIGHBOUR.  That
  // message is a claim about the document made from evidence about a different
  // paragraph, and its disposition sends the host into a rollback that throws
  // away the user's work since the last checkpoint.  The bullet had in fact
  // applied.
  //
  // Containment cannot catch it: it asks whether the selection COVERS the
  // caret, never whether it covers ONLY the caret's paragraph, and it HELD on
  // every overshooting cell measured (findings/evidence/046/native/).
  //
  // This compares the paragraph the action was dispatched on against the
  // paragraph the read is of.  Both are fingerprints of the paragraph's own
  // text, which is the only per-block datum LOK carries (four native rounds,
  // findings/evidence/queue-block-identity/) -- so two paragraphs with the same
  // text are indistinguishable, and this check is silent on exactly that case.
  // Said out loud rather than left to be discovered: an overshoot from one
  // empty paragraph into another is NOT caught here.
  //
  // Placed BEFORE the postcondition test on purpose.  If the read describes
  // another paragraph then the postcondition verdict has nothing to stand on,
  // and reporting the weaker, more alarming shape first is how 046 came to say
  // something the evidence contradicted.
  // Whether this check RAN is part of the verdict, not a detail.
  //
  // The gate below needs both reads to have succeeded, and when either did not
  // it simply does not fire -- so a barrier that never checked paragraph
  // identity and one that checked and was satisfied produce the same verdict.
  // That is fail-open, and it is the same shape as everything else this link is
  // repairing.
  //
  // NOT made fail-closed: accessibility being unavailable would then fail every
  // format action in the product, which is far worse than the defect.  Made
  // VISIBLE instead -- the payload says whether identity was verified, so
  // evidence can tell the two apart and a round that relied on it can say so.
  //
  // FINDING 082, and it is a THIRD condition rather than a wider first one.
  //
  // A read can succeed and still produce a fingerprint that identifies nothing:
  // the hash is taken over the content with `listPrefixLength` characters
  // stripped, and finding 074 makes that length the whole paragraph for an
  // outline-numbered heading -- so the slice is empty and the hash is the
  // offset basis.  Measured 2026-08-26 on `e2-editor-v9`: `E1-LC-HEADING`
  // (13 of 13) and a paragraph holding only `• ` (2 of 2) report the SAME
  // number, and a `set-paragraph-body` on that heading was refused as "a
  // different paragraph" -- with a `rollback` disposition, on a session with no
  // checkpoint -- while the readback markup shows the action had landed on the
  // right paragraph and worked.
  //
  // So the gate declines the comparison instead of failing it.  That is the
  // same fail-open this comment already argues for, extended to the case where
  // the value is present and meaningless rather than absent: the alternative is
  // a FALSE refusal prescribing a rollback, which is worse than the defect the
  // gate exists to catch.  Which reason it was is in the payload, because "the
  // gate did not run" has three causes now and a reader must not have to guess.
  gFormatBarrier.paragraphIdentityChecked =
      gFormatBarrier.dispatchParagraphKnown
      && gFormatBarrier.readbackParagraphKnown
      && gFormatBarrier.dispatchParagraphUsable
      && gFormatBarrier.readbackParagraphUsable;
  gFormatBarrier.paragraphIdentityDeclined =
      gFormatBarrier.paragraphIdentityChecked ? ""
      : (!gFormatBarrier.dispatchParagraphKnown
         || !gFormatBarrier.readbackParagraphKnown)
          ? "a paragraph read did not succeed"
          : "the reported list prefix consumed the whole paragraph, so the "
            "fingerprint is the empty-string constant and identifies nothing "
            "(finding 074)";
  if (gFormatBarrier.paragraphIdentityChecked
      && gFormatBarrier.dispatchParagraphFingerprint
             != gFormatBarrier.readbackParagraphFingerprint) {
    gFormatBarrier.failureShape = "readback-is-a-different-paragraph";
    failFormatBarrier(
        kFormatMutationOutcomeUnknown,
        "the postcondition read describes a different paragraph from the one "
        "this action was dispatched on, so it says nothing about whether the "
        "action took effect");
    return;
  }
  if (gFormatBarrier.containmentChecked && !gFormatBarrier.containmentHeld) {
    gFormatBarrier.failureShape = "selection-does-not-contain-restore-point";
    failFormatBarrier(
        kFormatMutationOutcomeUnknown,
        "the paragraph selected for the postcondition read does not cover the "
        "caret this action was dispatched from");
    return;
  }
  if (!formatBarrierReadbackSatisfied()) {
    gFormatBarrier.failureShape = "postcondition-not-met";
    failFormatBarrier(
        "EDITOR_FORMAT_POSTCONDITION_FAILED",
        "the document does not show the state this action asked for");
    return;
  }
  if (!gFormatBarrier.restoreConfirmed) {
    // The document reached the target, but the selection this read created is
    // still there.  Reporting success would leave the caller holding a
    // selection it never made, so this is a failure with a distinct code --
    // the mutation happened and the evidence says so.
    gFormatBarrier.failureShape = "selection-not-restored";
    failFormatBarrier(
        "EDITOR_SELECTION_NOT_RESTORED",
        "the postcondition read left a selection the barrier could not undo");
    return;
  }
  completeFormatBarrier();
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void handleFormatBarrierStep(const Command &command) {
  if (!formatBarrierActive() ||
      command.requestId != gFormatBarrier.requestId ||
      command.documentHandle != gFormatBarrier.documentHandle ||
      command.correlation != gFormatBarrier.serial ||
      command.documentHandle != gState.documentHandle)
    return;
  // values[0] == 1 is a step nobody queued: the loop synthesised it because an
  // awaiting stage ran out of time.  The identity checks above already proved
  // it belongs to *this* barrier; the stage check inside re-proves it has not
  // moved on since the loop decided to wake, which it can have done between the
  // wait returning and this running.
  if (command.values[0] == 1) {
    failFormatBarrierAtDeadline();
    return;
  }
  switch (gFormatBarrier.stage) {
  case FormatBarrierStage::SelectQueued:
    if (gFormatBarrier.route == FormatBarrierRoute::RangeCross) {
      // Do not restore, and do not select: the selection the CALLER made is
      // still there and is the only thing that covers the whole mutation.
      // Replacing it with .uno:SelectText is what makes the usual path report
      // success for one paragraph out of two.
      checkFormatBarrierCrossParagraph();
      gFormatBarrier.stage = FormatBarrierStage::AwaitingRestore;
      armFormatBarrierDeadline();
      postFormatBarrierRestore();
      if (!gFormatBarrier.restorePointValid)
        finishFormatBarrierAfterRestore();
      return;
    }
    gFormatBarrier.stage = FormatBarrierStage::AwaitingSelection;
    armFormatBarrierDeadline();
    // Go back to where the caret was when the action was dispatched, *before*
    // selecting the paragraph to read.
    //
    // A5's state-crosstalk case is what forced this: move the caret away while
    // the barrier is in flight and the read lands on whatever paragraph the
    // caret reached, not the one the command changed.  Failing closed there is
    // right, but it is right by luck -- move to a paragraph that happens to be
    // in the target state already and the barrier would report success for a
    // mutation that landed somewhere else.
    //
    // This does not make the read immune to geometry: the point is in document
    // coordinates and the dispatch may have changed the paragraph's height or
    // indent, so an extreme reflow could still land elsewhere.  It closes the
    // caret-moved-away path, which is the one a caller can actually cause.
    if (gFormatBarrier.restorePointValid)
      postFormatBarrierRestore();
    postFormatBarrierParagraphSelection();
    return;
  case FormatBarrierStage::ReadQueued:
    // Containment before the restore, because the restore collapses the very
    // selection the check is about.
    checkFormatBarrierContainment();
    // Finding 037.  The guard skips the read and nothing else: the restore
    // still runs, the stage machine still advances, and the refusal is judged
    // in finishFormatBarrierAfterRestore() with every other refusal.  Failing
    // here instead would end the barrier with the paragraph still selected --
    // a selection the caller never made, which is the defect
    // EDITOR_SELECTION_NOT_RESTORED exists to report.
    if (formatBarrierSelectionIsReadable())
      readFormatBarrierPostcondition();
    gFormatBarrier.stage = FormatBarrierStage::AwaitingRestore;
    armFormatBarrierDeadline();
    postFormatBarrierRestore();
    if (!gFormatBarrier.restorePointValid) {
      // Nothing was ever recorded to restore to, so waiting for a collapse
      // that will never be posted would hang.  Judge now and let the evidence
      // carry restoreConfirmed:false.
      finishFormatBarrierAfterRestore();
    }
    return;
  case FormatBarrierStage::AwaitingRestore:
    finishFormatBarrierAfterRestore();
    return;
  default:
    return;
  }
}
#endif

// Both halves of the advance condition, checked from whichever side arrived
// last.  Native ordering puts the command result after the state broadcast for
// the format commands, but that was measured for those five and not for this
// one, so neither order is assumed here.
//
// Two conditions, because each answers a question the other cannot: the result
// says *this* barrier's selection command ran, the rectangles say there is
// something to read.  Either alone was the defect -- rectangles alone accepted
// the caller's search, and a result alone would read before the selection
// materialised.
#ifndef OXSDK_E2_V23_LINK_BATCH
void maybeAdvanceFormatBarrierSelection() {
  if (gFormatBarrier.stage != FormatBarrierStage::AwaitingSelection)
    return;
  if (!gFormatBarrier.selectionResultSeen ||
      gEditorState.selectionRectangles.empty())
    return;
  queueFormatBarrierStep(FormatBarrierStage::ReadQueued);
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void handleFormatBarrierStateCallback(int callbackType) {
  if (!formatBarrierActive())
    return;
  if (gFormatBarrier.stage == FormatBarrierStage::AwaitingSelection) {
    if (callbackType == LOK_CALLBACK_TEXT_SELECTION &&
        !gEditorState.selectionRectangles.empty()) {
      if (!gFormatBarrier.selectionResultSeen)
        ++gFormatBarrier.selectionBeforeResultCount;
      maybeAdvanceFormatBarrierSelection();
    }
    return;
  }
  if (gFormatBarrier.stage == FormatBarrierStage::AwaitingRestore &&
      callbackType == LOK_CALLBACK_TEXT_SELECTION &&
      gEditorState.selectionRectangles.empty())
    queueFormatBarrierStep(FormatBarrierStage::AwaitingRestore);
}
#endif

// Route C: no precondition read at all.
//
// The staleness gate that used to live here refused whenever the cached state
// might describe another paragraph, which is most of the time (finding 021).
// Route C does not consult the cache, so there is nothing here to be stale --
// the action dispatches and the postcondition is read from the document.
#ifndef OXSDK_E2_V23_LINK_BATCH
void startFormatBarrierAction(const Command &command, std::uint32_t action,
                              const char *name) {
  startFormatBarrierActionResolved(command, action, name);
}
#endif

#ifndef OXSDK_E2_V23_LINK_BATCH
void startFormatBarrierActionResolved(const Command &command,
                                      std::uint32_t action, const char *name) {
  FormatStateBarrier barrier;
  barrier.action = name;

  switch (action) {
  case OXSDK_EDITOR_SET_LIST_UNORDERED:
    barrier.target = FormatBarrierTarget::ListBullet;
    barrier.expected = true;
    barrier.command = ".uno:DefaultBullet";
    barrier.arguments = kListOnArguments;
    barrier.expectedListTag = "ul";
    break;
  case OXSDK_EDITOR_SET_LIST_ORDERED:
    barrier.target = FormatBarrierTarget::ListNumber;
    barrier.expected = true;
    barrier.command = ".uno:DefaultNumbering";
    barrier.arguments = kListOnArguments;
    barrier.expectedListTag = "ol";
    break;
  case OXSDK_EDITOR_SET_LIST_NONE:
    barrier.target = FormatBarrierTarget::ListNone;
    barrier.expected = false;
    // Dispatched bare on purpose: FN_NUM_BULLET_OFF forwards to
    // FN_NUM_BULLET_ON with On=false and then calls DelNumRules, so it is
    // already a setter.  Finding 030 measured it landing on "no list" three
    // presses running, from both a bulleted and a numbered start.
    barrier.command = ".uno:RemoveBullets";
    barrier.expectedListTag = "none";
    break;
  case OXSDK_EDITOR_SET_PARAGRAPH_HEADING:
  case OXSDK_EDITOR_SET_PARAGRAPH_BODY: {
    const bool heading = action == OXSDK_EDITOR_SET_PARAGRAPH_HEADING;
    barrier.target = FormatBarrierTarget::ParagraphStyle;
    // Finding 019: .uno:Heading1ParaStyle and .uno:TextBodyParaStyle are UI
    // aliases with no dispatchable slot, so E1-A's mapping posted names that do
    // nothing.  The real command is StyleApply with fixed arguments; the enum
    // stays closed because neither the name nor the arguments cross the ABI.
    barrier.command = ".uno:StyleApply";
    barrier.arguments = styleApplyArguments(heading);
    barrier.expectedStyles = styleCandidates(heading);
    // SPEC E2-A 2.8, narrowing 2: the serialiser writes <p> for both "Text
    // body" and the default paragraph style, so this half of the postcondition
    // reads "is it a heading" and not "is it Text body".  The closed enum
    // promises two states, which this answers; it does not promise the style
    // name, and must not be reported as if it did.
    barrier.expectedBlockTag = heading ? "h1" : "p";
    break;
  }
  default:
    emitCommandError(command, "editor-action", "EDITOR_ACTION_UNSUPPORTED",
                     "closed editor action is unsupported");
    return;
  }

  barrier.requestId = command.requestId;
  barrier.documentHandle = gState.documentHandle;
  barrier.beforeRevision = gState.revision;

  // Routing happens BEFORE the dispatch, and a refusal here is the cleanest
  // outcome this barrier can produce: nothing was sent, so the document is
  // provably untouched.  Both shapes are pre-dispatch refusals and must not
  // carry MUTATION_OUTCOME_UNKNOWN -- that code sends the host into recovery,
  // and there is nothing to recover from.
  {
    std::string refusal;
    if (!routeFormatBarrier(barrier, action, refusal)) {
      barrier.failureShape = refusal;
      gFormatBarrier = barrier;
      if (refusal == "gesture-not-permitted") {
        failFormatBarrier(
            "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
            "this action is not offered for this kind of selection in this "
            "profile, so nothing was dispatched and the document is unchanged");
      } else if (refusal == "routing-selection-not-observed") {
        // Its own branch, and not folded into the readback message below: an
        // action refused because core has not reported a selection YET is not
        // an action refused because the selection holds an image.  Telling the
        // host the second when the first happened is how a caller learns to
        // work around the wrong thing.  Same typed code and same wording as
        // the inherited actions' gate, because it is the same refusal.
        failFormatBarrier(
            "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
            "no selection has been reported yet, so this action cannot be "
            "classified; nothing was dispatched and the document is unchanged");
      } else {
        failFormatBarrier(
            "EDITOR_FORMAT_SELECTION_NOT_READABLE",
            "this selection holds an image or another object, and reading it "
            "back would stop this document responding, so nothing was "
            "dispatched and the document is unchanged");
      }
      return;
    }
  }
  barrier.beforeSequence = gEditorState.sourceSequence;
  barrier.dispatchSequence = gEditorState.sourceSequence;
  // Captured before the dispatch, because the dispatch can move the caret and
  // the read is going to move it again.  A restore aimed at where the caret
  // ended up would put it back to the wrong place and still look like success.
  barrier.restorePoint = gEditorState.caret;
  barrier.restorePointValid = gEditorState.caret.available;
  // Same instant, same reason (SPEC E2-A 10.14 narrowing 7).  Recorded here and
  // nowhere later: every later moment describes a selection the barrier itself
  // made.
  barrier.dispatchSelectionCollapsed = gEditorState.selectionRectangles.empty();
  barrier.dispatchSelectionObserved = gEditorState.selectionObserved;
  barrier.dispatchSelectionRectangles = gEditorState.selectionRectangles.size();
  // Finding 046.  Asked for at the dispatch, because from the next stage onward
  // every paragraph the engine can see is one the barrier's own selection
  // reached.
  barrier.dispatchParagraphKnown = refreshCaretParagraph();
  barrier.dispatchParagraphFingerprint = gEditorState.a11yContentHash;
  barrier.dispatchParagraphUsable = gEditorState.a11yFingerprintUsable;
  barrier.stage = FormatBarrierStage::AwaitingResult;
  barrier.serial = gNextFormatBarrierSerial++;
  gFormatBarrier = barrier;
  armFormatBarrierDeadline();
  markAsynchronous(command.requestId);
  gState.document->pClass->postUnoCommand(
      gState.document, gFormatBarrier.command.c_str(),
      gFormatBarrier.arguments.empty() ? nullptr
                                       : gFormatBarrier.arguments.c_str(),
      true);
}
#endif
#endif

#ifdef OXSDK_E2_V23_LINK_BATCH
#include "ordered_format.inc"
#include "ordered_engine_delete.inc"
#endif

#ifdef OXSDK_E2_V23_LINK_BATCH
void dispatchOrderedKey(int keyCode, EditorPendingOperation pending) {
  setOrderedReply([pending] { composeOrderedEditorPending(pending); });
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYINPUT, 0, keyCode);
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYUP, 0, keyCode);
  refreshCaretParagraph();
}
#endif

void handleEditorAction(const Command &command) {
  if (!requireDocument(command, "editor-action"))
    return;
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
  if (selectionBarrierActive()) {
    emitCommandError(command, "editor-action", "BUSY",
                     "a verified selection delete is still in flight");
    return;
  }
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
  if (formatBarrierActive()) {
    emitCommandError(command, "editor-action", "BUSY",
                     "a verified format-state action is still in flight");
    return;
  }
#endif
  if (gEditorPending.requestId != 0) {
    emitCommandError(command, "editor-action", "BUSY",
                     "another callback-correlated editor operation is in flight");
    return;
  }
  const std::uint32_t action = static_cast<std::uint32_t>(command.values[0]);
  const char *name = editorActionName(action);
  if (std::strcmp(name, "unsupported") == 0) {
    emitCommandError(command, "editor-action", "EDITOR_ACTION_UNSUPPORTED",
                     "closed editor action is unsupported");
    return;
  }
  if (command.values[1] && !editorActionMoves(action)) {
    emitCommandError(command, "editor-action", "INVALID_ARGUMENT",
                     "extend-selection is valid only for move actions");
    return;
  }
  if (editorActionMutates(action) &&
      !requireRevision(command, "editor-action"))
    return;

  // Removed 2026-08-06 (finding 022, product route C).  set-bold and
  // set-italic used to short-circuit to `documented-state-noop` whenever the
  // cached value equalled the request.  The cache does not track the caret
  // (finding 021) and this path has no staleness flag at all, so the shortcut
  // answered a question about *this* text with the value of wherever the user
  // clicked before: the shipped e1-editor-v1 reported "already bold, nothing
  // changed" and left the document untouched, reproduced in Chrome and Firefox
  // for bold, italic and un-bold alike.
  //
  // The fix is to stop reading the precondition rather than to make it
  // trustworthy: dispatching unconditionally is idempotent for these commands,
  // and the postcondition -- which *is* trustworthy, verified 5/5 against saved
  // ODTs -- is what the result reports.  The cost is that `changed` no longer
  // distinguishes "was already in that state", a claim finding 021 forbids
  // treating as validated in the first place.

#ifdef OXSDK_E2_FORMAT_BARRIER
  if (editorActionIsParagraphFormat(action)) {
#ifdef OXSDK_E2_V23_LINK_BATCH
    startOrderedFormatAction(command, action, name);
#else
    startFormatBarrierAction(command, action, name);
#endif
    return;
  }

  // SPEC E2-C 2.5: the gesture mask has to bind the ten inherited actions too.
  //
  // Until now `editorGesturePermitted` was consulted in exactly one place --
  // routeFormatBarrier(), which only the five paragraph actions reach -- so the
  // manifest could declare `gestures: ["collapsed"]` for these ten and nothing
  // enforced it.  A declaration nobody executes is the same defect as an action
  // nobody can reach.
  //
  // Classified WITHOUT a readback, on purpose: the html read that would tell
  // range-single from range-cross is the wedge risk findings 037/038 describe.
  // What that costs is spelled out below -- an unclassified range has to
  // satisfy both range bits.
  {
    // `selectionObserved` is load-bearing and the first version of this gate
    // ignored it: an empty rectangle list means "no selection" ONLY once core
    // has reported a selection at least once (see the field's own comment).
    // Before that it means "nobody has said yet", and admitting that as a
    // collapsed caret is classifying without an observation -- the thing this
    // tree keeps having to relearn.
    if (!gEditorState.selectionObserved) {
      emitCommandError(
          command, "editor-action", "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
          "no selection has been reported yet, so this action cannot be "
          "classified; nothing was dispatched and the document is unchanged");
      return;
    }
    const bool collapsed = gEditorState.selectionRectangles.empty();
    // An unclassified range must satisfy BOTH range bits, because
    // editorGesturePermitted() accepts on any intersection: passing the OR of
    // the two would let a profile that allows only range-single admit a range
    // this build never classified, which may be a cross-paragraph one.
    // Telling them apart needs the html read, and that read is the wedge risk
    // findings 037/038 describe -- so the check is conservative instead.
    const bool permitted =
        collapsed ? editorGesturePermitted(action, kGestureCollapsed)
                  : (editorGesturePermitted(action, kGestureRangeSingle) &&
                     editorGesturePermitted(action, kGestureRangeCross));
    if (!permitted) {
      emitCommandError(
          command, "editor-action", "EDITOR_FORMAT_GESTURE_UNSUPPORTED",
          "this action is not offered for this kind of selection in this "
          "profile, so nothing was dispatched and the document is unchanged");
      return;
    }
  }
#endif

  switch (action) {
  case OXSDK_EDITOR_DELETE_BACKWARD:
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
    if (command.values[2]) {
      emitCommandError(command, "editor-action", "INVALID_ARGUMENT",
                       "manual delete bypass is disabled for verified-selection delete");
      return;
    }
#ifdef OXSDK_E2_V23_LINK_BATCH
    startOrderedCaretDelete(command, name, ".uno:SwBackspace", true);
#else
    startSelectionBarrierDelete(command, name, ".uno:SwBackspace", true);
#endif
#else
    startEditorUnoAction(command, name, ".uno:SwBackspace",
                         command.values[2] == 0);
#endif
    return;
  case OXSDK_EDITOR_DELETE_FORWARD:
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
    if (command.values[2]) {
      emitCommandError(command, "editor-action", "INVALID_ARGUMENT",
                       "manual delete bypass is disabled for verified-selection delete");
      return;
    }
#ifdef OXSDK_E2_V23_LINK_BATCH
    startOrderedCaretDelete(command, name, ".uno:Delete", false);
#else
    startSelectionBarrierDelete(command, name, ".uno:Delete", false);
#endif
#else
    startEditorUnoAction(command, name, ".uno:Delete",
                         command.values[2] == 0);
#endif
    return;
  case OXSDK_EDITOR_DELETE_SELECTION:
    // queue-cut-cannot-remove-text.  A plain dispatch on the selection the
    // caller already has -- deliberately NOT startSelectionBarrierDelete,
    // which refuses a pre-existing selection by design (:3143-3151) and posts
    // shift+Left/Right to manufacture its own. That barrier is right for a
    // caret-only delete and exactly wrong here: the whole point of this action
    // is that the range is the caller's.
    //
    // Nor is it a widened delete-backward. Widening that one would discard the
    // caret-only characterisation it was measured under, and this way the
    // manifest can declare range-single + range-cross for this action alone
    // and the engine's gesture gate refuses it at a collapsed caret -- a
    // refusal, not a silent no-op.
    //
    // The empty-paste route was measured on 2026-08-21 and is closed: the
    // refusal lives in COMPILED code at sdk_api.cpp:172-174, one layer above
    // the handler that has no gate, so relaxing it would be an engine change
    // too and would buy nothing.
    startEditorUnoAction(command, name, ".uno:Delete");
    return;
  case OXSDK_EDITOR_INSERT_PARAGRAPH_BREAK:
    startEditorUnoAction(command, name, ".uno:InsertPara");
    return;
  case OXSDK_EDITOR_INSERT_LINE_BREAK:
    startEditorUnoAction(command, name, ".uno:InsertLinebreak");
    return;
  case OXSDK_EDITOR_UNDO:
    startEditorUnoAction(command, name, ".uno:Undo");
    return;
  case OXSDK_EDITOR_REDO:
    startEditorUnoAction(command, name, ".uno:Redo");
    return;
  case OXSDK_EDITOR_SET_BOLD:
    // finding 045: the value has to reach core, or the command toggles.
    startEditorUnoAction(command, name, ".uno:Bold", false,
                         inlineFormatArgument("Bold",
                                              command.values[2] != 0));
    return;
  case OXSDK_EDITOR_SET_ITALIC:
    // finding 045: the value has to reach core, or the command toggles.
    startEditorUnoAction(command, name, ".uno:Italic", false,
                         inlineFormatArgument("Italic",
                                              command.values[2] != 0));
    return;
  // Same shape as bold and italic: an explicit boolean, dispatched
  // unconditionally, judged by the saved document.
  //
  // This comment used to say neither command appears in core's
  // GetKitUnoCommandList(), and that no format-state cache was therefore kept
  // for them.  BOTH HALVES WERE WRONG.  Both commands are in that list
  // (sfx2/source/control/unoctitm.cxx:1165ff, ungated), and both were measured
  // broadcasting at document load with values
  // (findings/evidence/059/native/negative-arm/).  A cache is now kept, and it
  // is what `inlineFormatArgumentResolved` reads.
  case OXSDK_EDITOR_SET_UNDERLINE:
    // finding 045: the value has to reach core, or the command toggles.
    startEditorUnoAction(command, name, ".uno:Underline", false,
                         inlineFormatArgument("Underline",
                                              command.values[2] != 0));
    return;
  case OXSDK_EDITOR_SET_STRIKETHROUGH:
    // finding 045: the value has to reach core, or the command toggles.
    startEditorUnoAction(command, name, ".uno:Strikeout", false,
                         inlineFormatArgument("Strikeout",
                                              command.values[2] != 0));
    return;
  case OXSDK_EDITOR_SET_PARAGRAPH_BODY:
    startEditorUnoAction(command, name, ".uno:TextBodyParaStyle");
    return;
  case OXSDK_EDITOR_SET_PARAGRAPH_HEADING:
    startEditorUnoAction(command, name, ".uno:Heading1ParaStyle");
    return;
  case OXSDK_EDITOR_SET_LIST_NONE:
    startEditorUnoAction(command, name, ".uno:RemoveBullets");
    return;
  case OXSDK_EDITOR_SET_LIST_UNORDERED:
    startEditorUnoAction(command, name, ".uno:DefaultBullet");
    return;
  case OXSDK_EDITOR_SET_LIST_ORDERED:
    startEditorUnoAction(command, name, ".uno:DefaultNumbering");
    return;
  default:
    break;
  }

  int keyCode = 0;
  switch (action) {
  case OXSDK_EDITOR_MOVE_CHARACTER_LEFT:
    keyCode = com::sun::star::awt::Key::LEFT;
    break;
  case OXSDK_EDITOR_MOVE_CHARACTER_RIGHT:
    keyCode = com::sun::star::awt::Key::RIGHT;
    break;
  case OXSDK_EDITOR_MOVE_LINE_UP:
    keyCode = com::sun::star::awt::Key::UP;
    break;
  case OXSDK_EDITOR_MOVE_LINE_DOWN:
    keyCode = com::sun::star::awt::Key::DOWN;
    break;
  case OXSDK_EDITOR_MOVE_LINE_HOME:
    keyCode = com::sun::star::awt::Key::HOME;
    break;
  case OXSDK_EDITOR_MOVE_LINE_END:
    keyCode = com::sun::star::awt::Key::END;
    break;
  case OXSDK_EDITOR_SELECT_ALL:
    // queue-no-select-all-action.  Deliberately on the KEY path with the
    // movements rather than through startEditorUnoAction, and the reason is
    // the shape this tree keeps finding: select-all changes the SELECTION, not
    // the document, and the uno-mutation route reports a mutation. Sending it
    // that way would advance the revision for an edit that never happened --
    // finding 067's engine half, reproduced on purpose.
    //
    // This route is already characterised: `mutation = false`, no revision
    // advance, completion documented from the callback. Reusing it means
    // select-all inherits a postcondition somebody measured instead of a new
    // one nobody has.
    //
    // SHIPPED BUT WITHHELD. The manifest grants it no gesture, so this is
    // unreachable on the v4 profile; what it buys is that granting it later
    // needs a measurement and not another relink. Its postcondition is NOT
    // characterised -- that measurement is the precondition for granting it.
    keyCode = com::sun::star::awt::Key::A | EditorMod1Modifier;
    break;
#ifdef OXSDK_E2_V21_LINK_BATCH
  // SPEC-M3-link-batch-v21 4.1 (finding 142): Ctrl+Home / Ctrl+End, posted
  // the way select-all posts its key -- and on this path for select-all's
  // reason: it changes the caret, not the document, so `mutation = false`,
  // completion on EditorCaretOrSelectionCallback, the 250 ms readback always
  // armed (a press at the boundary is silent natively, finding 096's shape),
  // and the completion strings of the six moves.  NOT .uno:GoToStartOfDoc
  // through startEditorUnoAction: that is the mutation route and would
  // advance the revision for an edit that never happened (finding 067).
  // Writer runs the same command either way (Accelerators.xcu HOME_MOD1).
  // Inside a table or a header one press goes up one level (L-142-steps).
  case OXSDK_EDITOR_MOVE_DOCUMENT_START:
    keyCode = com::sun::star::awt::Key::HOME | EditorMod1Modifier;
    break;
  case OXSDK_EDITOR_MOVE_DOCUMENT_END:
    keyCode = com::sun::star::awt::Key::END | EditorMod1Modifier;
    break;
#endif
  default:
    emitCommandError(command, "editor-action", "EDITOR_ACTION_UNSUPPORTED",
                     "closed editor action has no diagnostic mapping");
    return;
  }
  if (command.values[1])
    keyCode |= EditorShiftModifier;
  const std::uint32_t beforeRevision = gState.revision;
  const std::uint64_t beforeSequence = gEditorState.sourceSequence;
  gEditorPending.requestId = command.requestId;
  gEditorPending.documentHandle = command.documentHandle;
  gEditorPending.beforeRevision = beforeRevision;
  gEditorPending.beforeSequence = beforeSequence;
  gEditorPending.requiredCallback =
      command.values[1] ? LOK_CALLBACK_TEXT_SELECTION
                        : EditorCaretOrSelectionCallback;
  gEditorPending.mutation = false;
  gEditorPending.selection = false;
  gEditorPending.option = command.values[2] != 0;
  gEditorPending.name = name;
  // FINDING 096.  ALWAYS armed, like the place-caret path and unlike the
  // select path where it is a parameter -- and for the place-caret path's
  // reason rather than by analogy: the case it covers is not an edge here, it
  // is the one a user reaches by holding an arrow key until the document runs
  // out.  Measured 40/40 on four artifacts, including the shipping bytes.
  //
  // It is armed for EVERY key-path action rather than only for the two the
  // finding measured.  Up and Down are what 096 measured and End is what 018
  // measured; Home and the two character moves are unmeasured in both
  // directions, and the property that makes the wedge possible -- a posted key
  // that changes nothing, so core broadcasts nothing -- belongs to the path,
  // not to a subset of the keys on it.  Arming only the measured ones would be
  // choosing the smaller fix by taste.
  //
  // COST, NAMED: `editor-shell/editor-client.js` validates the two character
  // moves with `completion` starting `documented-callback-` and it is
  // hash-registered by E1-C, so it cannot be widened.  A v1 host whose profile
  // is relinked after this change would see a boundary ArrowLeft answered with
  // `verified-move-readback`, reject it as EDITOR_RESULT_INVALID and enter
  // recovery -- the same death it reaches today, 30 seconds earlier and with a
  // less accurate code.  No v1 artifact moves for this change; the e1 profiles
  // are frozen and none is relinked here.
#ifdef OXSDK_E2_V23_LINK_BATCH
  const EditorPendingOperation pending = gEditorPending;
  dispatchOrderedKey(keyCode, pending);
  return;
#else
  gEditorPending.readbackDeadlineArmed = true;
  gEditorPending.readbackDeadline =
      std::chrono::steady_clock::now() +
      std::chrono::milliseconds(EditorMoveReadbackDeadlineMs);
  markAsynchronous(command.requestId);
#endif
#ifndef OXSDK_E2_V23_LINK_BATCH
  gState.document->pClass->postKeyEvent(gState.document,
                                        LOK_KEYEVENT_KEYINPUT, 0, keyCode);
  gState.document->pClass->postKeyEvent(gState.document, LOK_KEYEVENT_KEYUP, 0,
                                        keyCode);
#endif
#ifdef OXSDK_E2_V23_LINK_BATCH
  refreshCaretParagraph();
#endif
}

#ifdef OXSDK_E2_V21_LINK_BATCH
// SPEC-M3-link-batch-v21 4.2 / 9.3 / 9.4 / 9.14 / 10.2 / 10.4 / 12.1: paste as
// Markdown.
//
// emitSdkError's shape plus `dispatched`.  false on every refusal before
// paste() is called -- the document is provably untouched, so the session
// gives it `recovery: "none"` whatever the code (10.4) -- and true on the one
// error after it, MUTATION_OUTCOME_UNKNOWN, where nothing may be claimed.
void emitPasteMarkdownError(const Command &command, const char *code,
                            const std::string &message, bool dispatched) {
#ifdef OXSDK_E2_V23_LINK_BATCH
  if (gOrderedDispatching) {
    setOrderedReply([command, code = std::string(code), message, dispatched] { emitPasteMarkdownError(command, code.c_str(), message, dispatched); });
    return;
  }
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"error\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << command.documentHandle
       << ",\"revision\":" << gCallbackRevision.load(std::memory_order_acquire)
       << ",\"operation\":\"paste-markdown\",\"code\":\"" << jsonEscape(code)
       << "\",\"message\":\"" << jsonEscape(message.c_str())
       << "\",\"where\":\"paste-markdown\",\"msg\":\""
       << jsonEscape(message.c_str())
       << "\",\"dispatched\":" << (dispatched ? "true" : "false") << "}";
  emitJson(json.str());
}

// Synchronous on the engine thread, like insert-text: paste() returns after
// `.uno:Paste` has run (doc_paste dispatches under the SolarMutex), so the
// after-read below sees its undo action.  Every check before paste() is in
// the interface's order (task brief, "Engine reply"); the byte rules and the
// scan are markdown_paste.hpp's, the reads are the engine's.
void handlePasteMarkdown(const Command &command) {
  namespace md = probe::markdown;
  if (!gState.document) {
    emitPasteMarkdownError(command, "NO_DOCUMENT", "no document is open",
                           false);
    return;
  }
  if (command.documentHandle != gState.documentHandle) {
    emitPasteMarkdownError(
        command, "INVALID_HANDLE",
        "document handle is closed or does not belong to this engine", false);
    return;
  }
  // The same gates insert-text's neighbours keep: a barrier, a pending key
  // or a UNO mutation in flight owns the caret and the undo stack, and the
  // payload comparison below would attribute its action to this paste.
  if (selectionBarrierActive() || formatBarrierActive() ||
      gEditorPending.requestId != 0 ||
      gUnoRequestId.load(std::memory_order_acquire) != 0 ||
      gSearchRequestId.load(std::memory_order_acquire) != 0) {
    emitPasteMarkdownError(command, "BUSY",
                           "another editor operation is still in flight",
                           false);
    return;
  }

  const char *data = command.text.data();
  const std::size_t size = command.text.size();
  // Codes 1-5, in the interface's order (markdown_paste.hpp, model-tested):
  //   1. NUL, invalid UTF-8 (12.1), the hard size limit, md_parse failing, no
  //      block other than MD_BLOCK_DOC -- INVALID_ARGUMENT;
  //   2. the thread encoding (10.4);
  //   3. 10.2's collapsed rule, read here at the dispatch from both sources.
  //      A paste over two table cells fills each cell, the second with source
  //      text or mojibake (finding 148), and the engine cannot tell that range
  //      from any other, so only a caret is accepted (L-md-collapsed-only);
  //   4, 5. 9.14 rules 1 and 2: Writer fetches a non-data: image while
  //      pasting, and hands raw HTML to its HTML import, which fetches too.
  // The two reads run only when the earlier codes have not refused.
  const md::Verdict verdict = md::judgeBytes(data, size);
  const md::Refusal refusal = md::preDispatchRefusal(
      verdict,
      [] { return osl_getThreadTextEncoding() == RTL_TEXTENCODING_UTF8; },
      [] {
        const SelectionReadback selection = readSelection();
        return md::collapsedForPaste(selection.type == LOK_SELTYPE_NONE,
                                     selection.textMissing,
                                     gEditorState.selectionObserved,
                                     gEditorState.selectionRectangles.size());
      });
  if (refusal.code) {
    emitPasteMarkdownError(command, refusal.code, refusal.message, false);
    return;
  }
  // 6. The payload the after-read is compared with.
  std::string before;
  if (!readMergeUndoPayload(before)) {
    emitPasteMarkdownError(command, md::kCodeUndoUnreadable,
                           "the undo stack could not be read before the "
                           "paste, so its outcome could not be verified; "
                           "nothing was pasted",
                           false);
    return;
  }

  const std::uint32_t beforeRevision = gState.revision;
  // The MIME type is the engine's (4.2).  The return value is recorded and
  // not trusted: natively it is true whatever happened (9.4).
  const bool pasteReturned = gState.document->pClass->paste(
      gState.document, md::kMimeType, data, size);
  std::string after;
  const bool afterRead = readMergeUndoPayload(after);
  const md::PasteJudgement judgement =
      md::judgeAfterPaste(before, afterRead, after);
  if (!judgement.completed) {
    emitPasteMarkdownError(
        command, md::kCodeOutcomeUnknown,
        std::string("the paste was dispatched and its outcome could not be "
                    "verified (") +
            judgement.reason + (pasteReturned ? "" : "; paste() returned false") +
            ")",
        true);
    return;
  }
  advanceRevision();
#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"markdown-pasted\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"beforeRevision\":" << beforeRevision
       << ",\"revision\":" << gState.revision
       << ",\"undoActionsBefore\":" << judgement.before.actions
       << ",\"undoActionsAfter\":" << judgement.after.actions
       << ",\"undoTopComment\":\""
       << jsonEscape(judgement.after.topComment.c_str()) << "\"}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}
#endif

void handleEditorSelect(const Command &command) {
  if (!requireDocument(command, "editor-select"))
    return;
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
  if (selectionBarrierActive()) {
    emitCommandError(command, "editor-select", "BUSY",
                     "a verified selection delete is still in flight");
    return;
  }
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
  // Finding 033's second layer.  Attribution decides what may advance the
  // barrier out of AwaitingSelection; this decides what may run at all while
  // it is in flight.  They cover different intervals -- attribution covers the
  // instant of advancing, this covers everything between advancing and the
  // read -- so neither one alone closes the case.
  if (formatBarrierActive()) {
    emitCommandError(command, "editor-select", "BUSY",
                     "a verified format-state action is still in flight");
    return;
  }
#endif
  if (gEditorPending.requestId != 0) {
    emitCommandError(command, "editor-select", "BUSY",
                     "another callback-correlated editor operation is in flight");
    return;
  }
  const std::uint32_t method = static_cast<std::uint32_t>(command.values[0]);
  const std::uint64_t beforeSequence = gEditorState.sourceSequence;
  const char *methodName = "unsupported";
  if (method == OXSDK_EDITOR_SELECTION_MOUSE_DRAG)
    methodName = "mouse-drag";
  else if (method == OXSDK_EDITOR_SELECTION_TEXT_HANDLES)
    methodName = "text-handles-unstable";
  else if (method == OXSDK_EDITOR_SELECTION_RESET)
    methodName = "selection-reset-unstable";
  else {
    emitCommandError(command, "editor-select", "EDITOR_ACTION_UNSUPPORTED",
                     "closed selection method is unsupported");
    return;
  }
  gEditorPending.requestId = command.requestId;
  gEditorPending.documentHandle = command.documentHandle;
  gEditorPending.beforeRevision = gState.revision;
  gEditorPending.beforeSequence = beforeSequence;
  gEditorPending.requiredCallback = LOK_CALLBACK_TEXT_SELECTION;
  gEditorPending.mutation = false;
  gEditorPending.selection = true;
  gEditorPending.name = methodName;
#ifdef OXSDK_E2_V23_LINK_BATCH
  const EditorPendingOperation pending = gEditorPending;
  setOrderedReply([pending] { composeOrderedEditorPending(pending); });
#else
  gEditorPending.readbackDeadlineArmed = command.values[5] != 0;
  if (gEditorPending.readbackDeadlineArmed) {
    gEditorPending.readbackDeadline =
        std::chrono::steady_clock::now() +
        std::chrono::milliseconds(EditorSelectReadbackDeadlineMs);
  }
  markAsynchronous(command.requestId);
#endif
  if (method == OXSDK_EDITOR_SELECTION_MOUSE_DRAG) {
    gState.document->pClass->postMouseEvent(
        gState.document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, command.values[1],
        command.values[2], 1, 1, 0);
    gState.document->pClass->postMouseEvent(
        gState.document, LOK_MOUSEEVENT_MOUSEMOVE, command.values[3],
        command.values[4], 1, 1, 0);
    gState.document->pClass->postMouseEvent(
        gState.document, LOK_MOUSEEVENT_MOUSEBUTTONUP, command.values[3],
        command.values[4], 1, 1, 0);
  } else if (method == OXSDK_EDITOR_SELECTION_TEXT_HANDLES) {
    gState.document->pClass->setTextSelection(
        gState.document, LOK_SETTEXTSELECTION_RESET, command.values[1],
        command.values[2]);
    // The START is a workaround for a core defect, not part of the protocol.
    //
    // RESET followed by END is the documented way to build a selection, and it
    // is what core's own test asserts:
    // sw/qa/extras/tiledrendering/tiledrendering.cxx:151, "test that
    // LOK_SETTEXTSELECTION_RESET + LOK_SETTEXTSELECTION_END can be used to
    // create a selection".  So the two-call form is not a misuse.
    //
    // It stops working after .uno:SelectText.  FN_SELECT_PARA
    // (sw/source/uibase/shells/textsh1.cxx:1975) ends in EndPara(true), which
    // reaches SwWrtShell::SttSelect() through MoveCursor(true) and sets
    // m_bInSelect -- and nothing on that path ever calls EndSelect().  A RESET
    // does not clear it either: SwEditWin::SetCursorTwipPosition takes the
    // bClearMark branch and skips both SttSelect and EndSelect
    // (sw/source/uibase/docvw/edtwin.cxx:7102).  The caller's END then calls
    // SttSelect(), returns early on `if (m_bInSelect)` (select.cxx:409), and
    // SetMark() never runs.  No mark, no selection, and no callback -- which is
    // the whole of finding 039's "the discovery selection path completes at
    // most once" and of the E2-A narrowing 4 that blocks E2-B.
    //
    // The START rescues it because EndSelect() at the end of
    // SetCursorTwipPosition is called on bCreateSelection rather than on
    // whether SttSelect() did anything (edtwin.cxx:7121), so this call clears
    // the flag the failed selection would otherwise have burned.
    //
    // Measured natively, four rounds, findings/evidence/sdk-e2/discovery/
    // 049-selection-after-format/: the two-call form selects nothing after
    // .uno:SelectText in every run, the three-call form selects the same
    // characters whether or not the flag is stuck, and it anchors at the START
    // position rather than the RESET one (arms AG/AH/AI, and AJ/AK for a range
    // running right to left).  A markless RESET at the same coordinate does not
    // rescue it (arm AF), so the rescue is EndSelect and not a plain SetCursor.
    //
    // Remove this when core pairs FN_SELECT_PARA's SttSelect with an EndSelect.
    // Until then the extra call is free: with the flag clear it produces the
    // identical selection, measured.
    gState.document->pClass->setTextSelection(
        gState.document, LOK_SETTEXTSELECTION_START, command.values[1],
        command.values[2]);
    gState.document->pClass->setTextSelection(
        gState.document, LOK_SETTEXTSELECTION_END, command.values[3],
        command.values[4]);
  } else if (method == OXSDK_EDITOR_SELECTION_RESET) {
    gState.document->pClass->setTextSelection(
        gState.document, LOK_SETTEXTSELECTION_RESET, command.values[1],
        command.values[2]);
  }
#ifdef OXSDK_E2_V23_LINK_BATCH
  refreshCaretParagraph();
#endif
}

// SPEC E2-C, queue item queue-verify-caret-by-block-identity.
//
// Placing the caret is a CALL THAT ANSWERS, not a click followed by a guess.
//
// `handleClick` posts the two mouse events and replies "clicked" in the same
// breath -- before core has processed anything, and saying nothing about where
// the caret went.  Everything downstream had to invert that: the host posted a
// pixel and then tried to decide, from a returned rectangle, whether the caret
// had landed where it asked.  Findings 048, 051 and 052 are all that inversion:
// a confirmation that was already true before the click; a band that refused
// the bottom half of every line; and a click outside the text, where the line
// the host is comparing against does not exist, waiting out thirty seconds.
//
// Four native rounds (findings/evidence/queue-block-identity/) say the datum
// the host wanted -- which paragraph -- exists nowhere in LOK as an index, and
// the reference implementation (Muya) says why that does not matter: an editor's
// cursor IS (block, offset), and geometry only ever runs model->pixels.  So the
// engine answers with what it can see: the caret rectangle, the paragraph's
// fingerprint, and the offset within it.
//
// The deadline is not a timeout dressed up as success.  It is the E1-D shape,
// and E1-D's comment is the argument: a click on the point the caret already
// occupies changes nothing, so core emits no callback and waiting for one waits
// for ever.  The answer arrives either way, and the CALLER judges from what it
// reports -- never from the fact that it returned.
void handleEditorPlaceCaret(const Command &command) {
  if (!requireDocument(command, "editor-place-caret"))
    return;
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
  if (selectionBarrierActive()) {
    emitCommandError(command, "editor-place-caret", "BUSY",
                     "a verified selection delete is still in flight");
    return;
  }
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
  if (formatBarrierActive()) {
    emitCommandError(command, "editor-place-caret", "BUSY",
                     "a verified format-state action is still in flight");
    return;
  }
#endif
  if (gEditorPending.requestId != 0) {
    emitCommandError(command, "editor-place-caret", "BUSY",
                     "another callback-correlated editor operation is in flight");
    return;
  }
  gEditorPending.requestId = command.requestId;
  gEditorPending.documentHandle = command.documentHandle;
  gEditorPending.beforeRevision = gState.revision;
  gEditorPending.beforeSequence = gEditorState.sourceSequence;
  gEditorPending.requiredCallback = LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR;
  gEditorPending.mutation = false;
  gEditorPending.selection = false;
  gEditorPending.caret = true;
  gEditorPending.name = "click";
  // ALWAYS armed, unlike the select path where it is a parameter.  The case it
  // covers -- a click that changes nothing -- is not an edge here; it is the
  // one a user reaches by clicking twice in the same place.
#ifdef OXSDK_E2_V23_LINK_BATCH
  const EditorPendingOperation pending = gEditorPending;
  setOrderedReply([pending] { composeOrderedEditorPending(pending); });
#else
  gEditorPending.readbackDeadlineArmed = true;
  gEditorPending.readbackDeadline =
      std::chrono::steady_clock::now() +
      std::chrono::milliseconds(EditorPlaceCaretDeadlineMs);
  markAsynchronous(command.requestId);
#endif
  gState.document->pClass->postMouseEvent(
      gState.document, LOK_MOUSEEVENT_MOUSEBUTTONDOWN, command.values[0],
      command.values[1], 1, 1, 0);
  gState.document->pClass->postMouseEvent(
      gState.document, LOK_MOUSEEVENT_MOUSEBUTTONUP, command.values[0],
      command.values[1], 1, 1, 0);
#ifdef OXSDK_E2_V23_LINK_BATCH
  refreshCaretParagraph();
#endif
}

void handleEditorGetState(const Command &command) {
  if (!requireDocument(command, "editor-get-state"))
    return;
  // Asked for, not waited for: the a11y CALLBACK is gated on the paragraph's
  // text changing, so a state read that relied on it would report the last
  // paragraph whose text differed rather than the one the caret is in.
  refreshCaretParagraph();
  const SelectionReadback readback = readSelection();
#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"editor-state-result\",\"requestId\":"
       << command.requestId << ",\"documentHandle\":"
       << gState.documentHandle << ",\"revision\":" << gState.revision
       << ",\"selectionType\":\"" << selectionTypeName(readback.type)
       << "\",\"selectionTextMissing\":"
       << (readback.textMissing ? "true" : "false")
       << ",\"selectionText\":\"" << jsonEscape(readback.text.c_str())
       << "\",";
  appendEditorState(json);
  json << "}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
struct SchedulerProbeSnapshot {
  std::uint64_t stateChangedCount = 0;
  std::uint64_t wordCountUpdateCount = 0;
  int wordCountWords = -1;
  int wordCountCharacters = -1;
};

SchedulerProbeSnapshot schedulerProbeSnapshot() {
  return SchedulerProbeSnapshot{
      gEditorState.stateChangedCount, gEditorState.wordCountUpdateCount,
      gEditorState.wordCountWords, gEditorState.wordCountCharacters};
}

void appendSchedulerProbeSnapshot(std::ostringstream &json,
                                  const SchedulerProbeSnapshot &snapshot) {
  json << "{\"stateChangedCount\":" << snapshot.stateChangedCount
       << ",\"wordCountUpdateCount\":" << snapshot.wordCountUpdateCount
       << ",\"wordCountWords\":" << snapshot.wordCountWords
       << ",\"wordCountCharacters\":" << snapshot.wordCountCharacters
       << "}";
}

void handleEditorDrainScheduler(const Command &command) {
  if (!requireDocument(command, "finding-016-drain-scheduler"))
    return;
  const SchedulerProbeSnapshot before = schedulerProbeSnapshot();
  const std::uint32_t beforeRevision = gState.revision;
  // Measured in this order on purpose: Reschedule first, so the run shows
  // whether the documented public pump does anything here before the
  // test-only path is used to get the work done.
  const bool useSystemEventLoop = Application::IsUseSystemEventLoop();
  const bool rescheduleProcessedEvent = Application::Reschedule(true);
  const std::uint64_t afterReschedule = gEditorState.stateChangedTotal;
  unit_lok_process_events_to_idle();
  const std::uint64_t afterProcessToIdle = gEditorState.stateChangedTotal;
  // Core broadcasts only on change, so "no payload arrived" cannot be read as
  // "not recomputed".  What can be relied on is that the scheduler ran to idle:
  // after the flush, the cache matches what core would report.  The host owns
  // the wait for that flush, the same way E1-B's session owns the bounded poll
  // after click; the engine does not sleep.
  gEditorState.formatStateStale = false;
  const SchedulerProbeSnapshot after = schedulerProbeSnapshot();

  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"finding-016-scheduler-drained\",\"requestId\":"
       << command.requestId << ",\"documentHandle\":"
       << gState.documentHandle << ",\"beforeRevision\":" << beforeRevision
       << ",\"revision\":" << gState.revision << ",\"before\":";
  appendSchedulerProbeSnapshot(json, before);
  json << ",\"after\":";
  appendSchedulerProbeSnapshot(json, after);
  json << ",\"delta\":{\"stateChangedCount\":"
       << (after.stateChangedCount - before.stateChangedCount)
       << ",\"wordCountUpdateCount\":"
       << (after.wordCountUpdateCount - before.wordCountUpdateCount)
       << "},\"pump\":{\"useSystemEventLoop\":"
       << (useSystemEventLoop ? "true" : "false")
       << ",\"rescheduleProcessedEvent\":"
       << (rescheduleProcessedEvent ? "true" : "false")
       << ",\"stateChangedAfterReschedule\":" << afterReschedule
       << ",\"stateChangedAfterProcessToIdle\":" << afterProcessToIdle
       << "}}";
  emitJson(json.str());
}
#endif
#endif

void handleKey(const Command &command) {
  if (!requireDocument(command, "key"))
    return;
  gState.document->pClass->postKeyEvent(gState.document, command.values[0],
                                        command.values[1], command.values[2]);
}

bool readOutputBuffer(const std::string &path, void *&pointer,
                      std::uint32_t &byteLength) {
  std::ifstream input(path, std::ios::binary | std::ios::ate);
  if (!input)
    return false;
  const std::streampos end = input.tellg();
  if (end <= 0 || static_cast<unsigned long long>(end) >
                      std::numeric_limits<std::uint32_t>::max())
    return false;
  byteLength = static_cast<std::uint32_t>(end);
  pointer = std::malloc(byteLength);
  if (!pointer)
    return false;
  input.seekg(0, std::ios::beg);
  input.read(static_cast<char *>(pointer),
             static_cast<std::streamsize>(byteLength));
  if (!input) {
    std::free(pointer);
    pointer = nullptr;
    byteLength = 0;
    return false;
  }
  return true;
}

#ifdef OXSDK_ODS_EDITOR
void handleCell(const Command &command) {
  if (!requireDocument(command, "cell")) return;
  const int operation = command.values[3];
  const bool mutation = (operation >= 1 && operation <= 4) || operation >= 7;
  if ((mutation || operation == 6) && !requireRevision(command, "cell")) return;
  char *raw = oxsdk_calc_cell_model(gState.document, command.values[0],
      command.values[1], command.values[2], operation, command.text.data(),
      command.text.size(), command.values[4]);
  if (!raw) {
    emitCommandError(command, "cell", "INTERNAL_ERROR", "cell model allocation failed");
    return;
  }
  const std::string json(raw);
  std::free(raw);
  try {
    boost::property_tree::ptree result;
    std::istringstream stream(json);
    boost::property_tree::read_json(stream, result);
    if (!result.get<bool>("ok")) {
      const bool uncertain = result.get<bool>("mutationAttempted", false);
      if (uncertain) advanceRevision();
      emitCommandError(command, "cell", uncertain ? "MUTATION_OUTCOME_UNKNOWN"
          : result.get<std::string>("code", "CELL_MODEL_ERROR").c_str(), json);
      return;
    }
    const bool changed = result.get<bool>("changed", false);
    if (changed) advanceRevision();
    std::ostringstream reply;
    reply << "{\"schemaVersion\":" << ProtocolSchemaVersion
          << ",\"type\":\"cell-result\",\"requestId\":" << command.requestId
          << ",\"documentHandle\":" << gState.documentHandle
          << ",\"revision\":" << gState.revision << ",\"changed\":"
          << (changed ? "true" : "false") << ",\"cellJson\":\""
          << jsonEscape(json.c_str()) << "\"}";
    emitJson(reply.str());
  } catch (const std::exception &e) {
    emitCommandError(command, "cell", mutation ? "MUTATION_OUTCOME_UNKNOWN"
        : "CELL_RESULT_INVALID", json + " -- " + e.what());
  }
}
#endif

void handleSave(const Command &command) {
  if (!requireDocument(command, "save"))
    return;

  const std::string path =
      command.sdk
          ? "/tmp/oxsdk-output-" + std::to_string(gState.documentHandle) + "-" +
                std::to_string(command.requestId) + "." + command.text
          : "/tmp/out." + command.text;
  const std::string url = "file://" + path;
  if (!gState.document->pClass->saveAs(gState.document, url.c_str(),
                                       command.text.c_str(), nullptr)) {
    emitCommandError(command, "save", "LOK_ERROR", kitError());
    return;
  }

  if (!command.sdk) {
    emitJson("{\"type\":\"saved\",\"url\":\"" + jsonEscape(url.c_str()) +
             "\"}");
    return;
  }

  void *output = nullptr;
  std::uint32_t byteLength = 0;
  if (!readOutputBuffer(path, output, byteLength)) {
    emitCommandError(command, "save", "IO_ERROR",
                     "unable to read saved output from MEMFS");
    return;
  }

#ifdef OXSDK_E2_V23_LINK_BATCH
  setOrderedReply([=] {
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"saved\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << gState.documentHandle
       << ",\"revision\":" << gState.revision << ",\"format\":\""
       << jsonEscape(command.text.c_str())
       << "\",\"ptr\":" << reinterpret_cast<std::uintptr_t>(output)
       << ",\"size\":" << byteLength << "}";
  emitJson(json.str());
#ifdef OXSDK_E2_V23_LINK_BATCH
  });
#endif
}

#ifdef OXSDK_E2_V23_DIAGNOSTIC
void emitOrderedControl(int kind, std::uint32_t requestId) {
  std::ostringstream json;
  json << "{\"type\":\"v23-control\",\"kind\":" << kind
       << ",\"requestId\":" << requestId << "}";
  emitJson(json.str());
}

#include "ordered_diagnostic_html.inc"

void handleOrderedDiagnostic(const Command &command) {
  const int kind = command.values[0];
  if (kind == 1) {
    emitOrderedControl(kind, command.requestId);
    std::mutex mutex;
    std::condition_variable condition;
    std::unique_lock<std::mutex> lock(mutex);
    condition.wait(lock, [] { return false; });
    return;
  }
  if (kind == 2) {
    emitOrderedControl(kind, command.requestId);
    setOrderedReply([command] {
      emitOrderedMissingProof(command, "v23Diagnostic", "UNO_COMMAND_RESULT");
    });
    return;
  }
  if (!requireDocument(command, "v23Diagnostic"))
    return;
  if (kind == 4 && readSelection().type != LOK_SELTYPE_TEXT) {
    emitCommandError(command, "v23Diagnostic", "INVALID_ARGUMENT",
                     "the private range-Left control requires a TEXT selection");
    return;
  }
  if (kind == 9) {
    startOrderedHtmlRead(command);
    return;
  }
  emitOrderedControl(kind, command.requestId);
  EditorPendingOperation pending;
  pending.requestId = command.requestId;
  pending.documentHandle = command.documentHandle;
  pending.beforeRevision = gState.revision;
  pending.beforeSequence = gEditorState.sourceSequence;
  pending.requiredCallback = kind == 4 ? EditorCaretOrSelectionCallback : LOK_CALLBACK_TEXT_SELECTION;
  pending.name = kind == 6 ? "move-character-right" : kind == 7 ? "move-line-end"
                 : kind == 8 ? "move-line-home" : "move-character-left";
  int key = kind == 6 ? com::sun::star::awt::Key::RIGHT
            : kind == 7 ? com::sun::star::awt::Key::END
            : kind == 8 ? com::sun::star::awt::Key::HOME : com::sun::star::awt::Key::LEFT;
  if (kind != 4)
    key |= EditorShiftModifier;
  dispatchOrderedKey(key, pending);
}
#endif

void dispatch(const Command &command) {
#if defined(OXSDK_FINDING_016_SELECTION_BARRIER) && !defined(OXSDK_E2_V23_LINK_BATCH)
  if (selectionBarrierActive() &&
      command.type != CommandType::EditorSelectionBarrierStep) {
#ifdef OXSDK_E2_V21_LINK_BATCH
    // 10.4: every refusal of the paste before paste() says so itself.
    if (command.type == CommandType::PasteMarkdown) {
      emitPasteMarkdownError(command, "BUSY",
                             "a verified selection delete is still in flight",
                             false);
      return;
    }
#endif
    emitCommandError(command, "selection-barrier", "BUSY",
                     "a verified selection delete is still in flight");
    return;
  }
#endif
  switch (command.type) {
#ifdef OXSDK_E2_V23_DIAGNOSTIC
  case CommandType::DiagnosticNeverReturn:
  case CommandType::DiagnosticMissingProof:
  case CommandType::DiagnosticHtml:
  case CommandType::DiagnosticKey:
    handleOrderedDiagnostic(command);
    break;
#endif
#ifdef OXSDK_ODS_EDITOR
  case CommandType::Cell:
    handleCell(command);
    break;
#endif
  case CommandType::EmitReady:
    emitReady(command);
    break;
  case CommandType::OpenUrl:
  case CommandType::OpenBytes:
    handleOpen(command);
    break;
  case CommandType::PaintTile:
    handlePaintTile(command);
    break;
  case CommandType::Click:
    handleClick(command);
    break;
  case CommandType::InsertText:
    handleInsertText(command);
    break;
#ifdef OXSDK_E2_V24_TYPED_INSERT
  case CommandType::InsertTypedText:
    handleInsertTypedText(command);
    break;
#endif
  case CommandType::Search:
    handleSearch(command);
    break;
  case CommandType::GetSelection:
#ifdef OXSDK_EDITOR_DISCOVERY
    handleGetSelection(command);
#else
    // No profile without the editor exports get_selection (sdk_api.cpp); a
    // command that got here anyway is answered rather than left pending.
    emitCommandError(command, "get-selection", "UNSUPPORTED_OPERATION",
                     "this engine has no selection readback");
#endif
    break;
  case CommandType::ReplaceSelection:
    handleReplaceSelection(command);
    break;
  case CommandType::Undo:
    handleUndo(command);
    break;
  case CommandType::Redo:
    handleRedo(command);
    break;
  case CommandType::AddComment:
    handleAddComment(command);
    break;
  case CommandType::ListComments:
    handleListComments(command);
    break;
  case CommandType::SetTrackChanges:
    handleSetTrackChanges(command);
    break;
  case CommandType::ListChanges:
    handleListChanges(command);
    break;
#ifdef OXSDK_ODS_VIEWER
  case CommandType::SetPart:
    handleSetPart(command);
    break;
  case CommandType::CurrentPart:
    handleCurrentPart(command);
    break;
  case CommandType::PartName:
    handlePartName(command);
    break;
  case CommandType::PartText:
    handlePartText(command);
    break;
#ifdef OXSDK_ODS_VIEWER_V2
  case CommandType::PartInfo:
    handlePartInfo(command);
    break;
#endif
#endif
#ifdef OXSDK_E2_V20_LINK_BATCH
  case CommandType::PageRectangles:
    handlePageRectangles(command);
    break;
#endif
#ifdef OXSDK_E2_V21_LINK_BATCH
  case CommandType::PasteMarkdown:
    handlePasteMarkdown(command);
    break;
#endif
#ifdef OXSDK_EDITOR_DISCOVERY
#if defined(OXSDK_E2_FORMAT_BARRIER) && !defined(OXSDK_E2_V23_LINK_BATCH)
  case CommandType::EditorFormatBarrierStep:
    handleFormatBarrierStep(command);
    break;
#endif
  case CommandType::EditorAction:
    handleEditorAction(command);
    break;
  case CommandType::EditorSelect:
    handleEditorSelect(command);
    break;
#ifndef OXSDK_E2_V23_LINK_BATCH
  case CommandType::EditorSelectReadback:
  case CommandType::EditorPlaceCaretReadback:
    if (command.requestId == gEditorPending.requestId &&
        command.documentHandle == gEditorPending.documentHandle) {
      completePendingEditorSelectByReadback();
    }
    break;
  // FINDING 096.  Same correlation guard as the two above, and it is not
  // decoration: the deadline is synthesised from whatever is pending NOW, so a
  // step that arrived after the slot was already cleared and refilled would
  // otherwise complete the wrong request.
  case CommandType::EditorActionReadback:
    if (command.requestId == gEditorPending.requestId &&
        command.documentHandle == gEditorPending.documentHandle) {
      completePendingEditorActionByReadback();
    }
    break;
#endif
  case CommandType::EditorPlaceCaret:
    handleEditorPlaceCaret(command);
    break;
  case CommandType::EditorGetState:
    handleEditorGetState(command);
    break;
#if defined(OXSDK_FINDING_016_SELECTION_BARRIER) && !defined(OXSDK_E2_V23_LINK_BATCH)
  case CommandType::EditorSelectionBarrierStep:
    handleSelectionBarrierStep(command);
    break;
#endif
#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
  case CommandType::EditorDrainScheduler:
    handleEditorDrainScheduler(command);
    break;
#endif
#endif
  case CommandType::Key:
    handleKey(command);
    break;
  case CommandType::Save:
    handleSave(command);
    break;
  case CommandType::Close:
    if (requireDocument(command, "close"))
      closeDocument(&command);
    break;
  }
}

void emitCancelled(const Command &command) {
#ifdef OXSDK_E2_V23_LINK_BATCH
  if (gOrderedDispatching) {
    setOrderedReply([command] { emitCancelled(command); });
    return;
  }
#endif
  std::ostringstream json;
  json << "{\"schemaVersion\":" << ProtocolSchemaVersion
       << ",\"type\":\"cancelled\",\"requestId\":" << command.requestId
       << ",\"documentHandle\":" << command.documentHandle
       << ",\"revision\":" << gCallbackRevision.load(std::memory_order_acquire)
       << ",\"code\":\"CANCELLED\"}";
  emitJson(json.str());
}

void finishExecuting(std::uint32_t requestId) {
  if (requestId == 0)
    return;
  std::lock_guard<std::mutex> lock(gState.mutex);
  if (gState.executingRequest == requestId)
    gState.executingRequest = 0;
}

#ifndef OXSDK_MAINLOOP_ENGINE
void engineLoop(Command initialReady) {
  gStage = "start.libreofficekit_hook_2";
  gState.kit = libreofficekit_hook_2("/instdir/program", "file:///tmp/user");
  emitReady(initialReady);
  finishExecuting(initialReady.requestId);

  for (;;) {
    Command command;
    bool cancelled = false;
    bool syntheticSelectionDeadline = false;
    {
      std::unique_lock<std::mutex> lock(gState.mutex);
      while (gState.commands.empty()) {
        // SPEC E1-D.  A product range-select that changed nothing gets no
        // callback; wake at its deadline and complete it from the readback
        // instead of waiting for a broadcast that is never coming.
        //
        // FINDING 096 added the third arm below.  The three kinds are told
        // apart by the flags the pending operation already carries, so there
        // is no fourth place that has to agree about which kind this is.
        // The editor's (2026-10-20, SPEC-M4 addendum 3).
#ifdef OXSDK_EDITOR_DISCOVERY
        if (gEditorPending.requestId != 0 &&
            gEditorPending.readbackDeadlineArmed) {
          const auto deadline = gEditorPending.readbackDeadline;
          if (!gState.condition.wait_until(
                  lock, deadline,
                  [] { return !gState.commands.empty(); }) &&
              gEditorPending.requestId != 0 &&
              gEditorPending.readbackDeadlineArmed &&
              std::chrono::steady_clock::now() >= deadline) {
            command = Command{gEditorPending.caret
                                  ? CommandType::EditorPlaceCaretReadback
                              : gEditorPending.selection
                                  ? CommandType::EditorSelectReadback
                                  : CommandType::EditorActionReadback};
            command.requestId = gEditorPending.requestId;
            command.documentHandle = gEditorPending.documentHandle;
            syntheticSelectionDeadline = true;
            break;
          }
          continue;
        }
#endif
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
        if (gSelectionBarrier.stage ==
            SelectionBarrierStage::AwaitingUnitSelection) {
          const auto deadline = gSelectionBarrier.boundaryDeadline;
          if (!gState.condition.wait_until(
                  lock, deadline,
                  [] { return !gState.commands.empty(); }) &&
              gSelectionBarrier.stage ==
                  SelectionBarrierStage::AwaitingUnitSelection &&
              std::chrono::steady_clock::now() >= deadline) {
            command = Command{CommandType::EditorSelectionBarrierStep};
            command.requestId = gSelectionBarrier.requestId;
            command.documentHandle = gSelectionBarrier.documentHandle;
            command.correlation = gSelectionBarrier.transactionSerial;
            command.values[0] = 1;
            syntheticSelectionDeadline = true;
            break;
          }
          continue;
        }
#ifdef OXSDK_MERGE_KEY_UNDO
        // Option B: each step waits at most MergeStepDeadlineMs for its proof.
        // Same re-check after waking as above: the step may have advanced.
        //
        // FINDING 117.  The key stage's proof is a STATE -- the .uno:Undo
        // payload against P0 -- and nothing promised a callback after it: on
        // blank paragraphs 102 of 105 presses waited out the whole deadline
        // and then found the record already there.  So that one stage also
        // wakes every MergeKeyPollMs and takes the step a callback would have
        // queued (values[0] = 3, `verifyMergeKey(false)`).  A read cannot land
        // inside the key: both hold the SolarMutex.  The other three stages
        // prove themselves by transitions and are not polled; the deadline and
        // its reading are unchanged.  New order, harmless and named for review:
        // the completion may now be sent between the key's KEYINPUT and KEYUP.
        if (gSelectionBarrier.stageDeadlineArmed && mergeStageAwaiting()) {
          const auto deadline = gSelectionBarrier.stageDeadline;
          const std::uint64_t serial = gSelectionBarrier.transactionSerial;
          const bool poll =
              gSelectionBarrier.stage == SelectionBarrierStage::MergeAwaitingKey;
          const auto wake =
              poll ? std::min(deadline,
                              std::chrono::steady_clock::now() +
                                  std::chrono::milliseconds(MergeKeyPollMs))
                   : deadline;
          if (!gState.condition.wait_until(
                  lock, wake,
                  [] { return !gState.commands.empty(); }) &&
              gSelectionBarrier.transactionSerial == serial &&
              gSelectionBarrier.stageDeadlineArmed && mergeStageAwaiting()) {
            const bool expired = std::chrono::steady_clock::now() >= deadline;
            if (expired || (poll && gSelectionBarrier.stage ==
                                        SelectionBarrierStage::MergeAwaitingKey)) {
              command = Command{CommandType::EditorSelectionBarrierStep};
              command.requestId = gSelectionBarrier.requestId;
              command.documentHandle = gSelectionBarrier.documentHandle;
              command.correlation = gSelectionBarrier.transactionSerial;
              command.values[0] = expired ? 2 : 3;
              syntheticSelectionDeadline = true;
              break;
            }
          }
          continue;
        }
#endif
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
        // Finding 034: adopting .uno:SelectText makes a stall reachable on
        // purpose (an empty last paragraph produces no selection at all), and
        // the BUSY gate means a stalled barrier wedges the whole handle.  Same
        // shape as the selection barrier's deadline above, including the
        // re-check after waking: the barrier may have advanced while the wait
        // was returning, and ending one that has moved on would be worse than
        // the stall.
        if (formatBarrierActive() && gFormatBarrier.stageDeadlineArmed) {
          const auto deadline = gFormatBarrier.stageDeadline;
          const std::uint64_t serial = gFormatBarrier.serial;
          if (!gState.condition.wait_until(
                  lock, deadline,
                  [] { return !gState.commands.empty(); }) &&
              formatBarrierActive() && gFormatBarrier.serial == serial &&
              gFormatBarrier.stageDeadlineArmed &&
              std::chrono::steady_clock::now() >= deadline) {
            command = Command{CommandType::EditorFormatBarrierStep};
            command.requestId = gFormatBarrier.requestId;
            command.documentHandle = gFormatBarrier.documentHandle;
            command.correlation = gFormatBarrier.serial;
            command.values[0] = 1;
            syntheticSelectionDeadline = true;
            break;
          }
          continue;
        }
#endif
        gState.condition.wait(lock,
                              [] { return !gState.commands.empty(); });
      }
      if (!syntheticSelectionDeadline) {
        command = std::move(gState.commands.front());
        gState.commands.pop_front();
      }
      if (command.sdk) {
        gState.pendingRequests.erase(command.requestId);
        cancelled = gState.cancelledRequests.erase(command.requestId) != 0;
        if (!cancelled)
          gState.executingRequest = command.requestId;
      }
    }

    if (cancelled) {
      emitCancelled(command);
      continue;
    }

    try {
      dispatch(command);
    } catch (const com::sun::star::uno::Exception &exception) {
      const rtl::OString message =
          OUStringToOString(exception.Message, RTL_TEXTENCODING_UTF8);
      emitCommandError(command, "engine", "UNO_EXCEPTION",
                       std::string(gStage) +
                           ": UNO exception: " + message.getStr());
    } catch (const std::exception &exception) {
      emitCommandError(command, "engine", "CPP_EXCEPTION",
                       std::string(gStage) + ": " + exception.what());
    } catch (...) {
      const std::type_info *type = __cxxabiv1::__cxa_current_exception_type();
      emitCommandError(command, "engine", "UNKNOWN_EXCEPTION",
                       std::string(gStage) + ": unknown C++ exception type=" +
                           (type ? type->name() : "<unavailable>"));
    }
    finishExecuting(command.requestId);
  }
}
#else

// Stage telemetry on the channel emitJson already proves works from this
// thread (MAIN_THREAD_EM_ASM).  stderr from this pthread turned out not to be
// visible in the captured browser console, so diagnostics must not rely on it.
void mainLoopTrace(const char *message, double a, double b) {
  MAIN_THREAD_EM_ASM(
      { console.log('oxsdk-mainloop:', UTF8ToString($0), $1, $2); }, message,
      a, b);
}

// Liveness probe for the engine worker's own JS event loop.  Scheduled with
// emscripten_set_interval before runLoop: after the 'unwind' these callbacks
// share the event loop with the emscripten main-loop ticks, so their absence
// distinguishes "worker event loop dead" from "loop tick stuck".
void mainLoopTickAliveProbe(void *) {
  static int beats = 0;
  if (beats < 20 || beats % 30 == 0) {
    // Reads this worker realm's MainLoop state (plain EM_ASM on purpose --
    // the emscripten main loop lives in the engine worker, not the module
    // main thread).  bits: 1 func set, 2 scheduler set, 4 running, 8
    // timeout-method; second value is how often the runner actually fired.
    const int state = EM_ASM_INT({
      try {
        if (typeof MainLoop == 'undefined')
          return -1;
        if (!globalThis.__oxsdkRunnerWrapped && MainLoop.runner) {
          globalThis.__oxsdkRunnerWrapped = 1;
          const original = MainLoop.runner;
          MainLoop.runner = function() {
            globalThis.__oxsdkRunnerCalls = (globalThis.__oxsdkRunnerCalls || 0) + 1;
            return original.apply(this, arguments);
          };
        }
        return (MainLoop.func ? 1 : 0) | (MainLoop.scheduler ? 2 : 0) |
               (MainLoop.running ? 4 : 0) |
               (MainLoop.method === 'timeout' ? 8 : 0);
      } catch (error) {
        return -2;
      }
    });
    const int runnerCalls =
        EM_ASM_INT({ return globalThis.__oxsdkRunnerCalls || 0; });
    mainLoopTrace("tick-alive", state, runnerCalls);
  }
  ++beats;
}

// The counterpart of one engineLoop iteration after the command has been
// popped: dispatch inside the same exception envelope.  Deliberately a copy
// rather than a shared helper, so the non-mainloop translation units stay
// byte-identical to what E1-C validated.
void executeQueuedCommand(const Command &command, bool cancelled) {
  if (cancelled) {
    emitCancelled(command);
    return;
  }
  try {
    dispatch(command);
  } catch (const com::sun::star::uno::Exception &exception) {
    const rtl::OString message =
        OUStringToOString(exception.Message, RTL_TEXTENCODING_UTF8);
#ifdef OXSDK_E2_V23_LINK_BATCH
    gOrderedReply = {};
#endif
    emitCommandError(command, "engine", "UNO_EXCEPTION",
                     std::string(gStage) +
                         ": UNO exception: " + message.getStr());
  } catch (const std::exception &exception) {
#ifdef OXSDK_E2_V23_LINK_BATCH
    gOrderedReply = {};
#endif
    emitCommandError(command, "engine", "CPP_EXCEPTION",
                     std::string(gStage) + ": " + exception.what());
  } catch (...) {
    const std::type_info *type = __cxxabiv1::__cxa_current_exception_type();
#ifdef OXSDK_E2_V23_LINK_BATCH
    gOrderedReply = {};
#endif
    emitCommandError(command, "engine", "UNKNOWN_EXCEPTION",
                     std::string(gStage) + ": unknown C++ exception type=" +
                         (type ? type->name() : "<unavailable>"));
  }
  finishExecuting(command.requestId);
}

// Dispatches every queued command, plus a synthesized selection-barrier
// deadline step when one is due, and returns how many ran.  Never blocks.
#ifdef OXSDK_E2_V23_LINK_BATCH
#include "ordered_engine_poll.inc"
#else
int mainLoopDrainCommands() {
  int processed = 0;
  for (;;) {
    Command command;
    bool cancelled = false;
    bool synthetic = false;
    {
      std::lock_guard<std::mutex> lock(gState.mutex);
      if (gState.commands.empty()) {
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
        if (gSelectionBarrier.stage ==
                SelectionBarrierStage::AwaitingUnitSelection &&
            std::chrono::steady_clock::now() >=
                gSelectionBarrier.boundaryDeadline) {
          command = Command{CommandType::EditorSelectionBarrierStep};
          command.requestId = gSelectionBarrier.requestId;
          command.documentHandle = gSelectionBarrier.documentHandle;
          command.correlation = gSelectionBarrier.transactionSerial;
          command.values[0] = 1;
          synthetic = true;
        }
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
        // The same deadline under the main-loop engine profile.  It shares the
        // barrier code, so leaving it without one would give the two profiles
        // different failure behaviour for the same source.
        if (!synthetic && formatBarrierActive() &&
            gFormatBarrier.stageDeadlineArmed &&
            std::chrono::steady_clock::now() >= gFormatBarrier.stageDeadline) {
          command = Command{CommandType::EditorFormatBarrierStep};
          command.requestId = gFormatBarrier.requestId;
          command.documentHandle = gFormatBarrier.documentHandle;
          command.correlation = gFormatBarrier.serial;
          command.values[0] = 1;
          synthetic = true;
        }
#endif
        if (!synthetic)
          break;
      }
      if (!synthetic) {
        command = std::move(gState.commands.front());
        gState.commands.pop_front();
      }
      if (command.sdk) {
        gState.pendingRequests.erase(command.requestId);
        cancelled = gState.cancelledRequests.erase(command.requestId) != 0;
        if (!cancelled)
          gState.executingRequest = command.requestId;
      }
    }
    static std::uint32_t loggedDispatches = 0;
    if (loggedDispatches < 10) {
      ++loggedDispatches;
      mainLoopTrace("dispatch", static_cast<long long>(command.type),
                    command.requestId);
    }
    executeQueuedCommand(command, cancelled);
    if (loggedDispatches <= 10)
      mainLoopTrace("dispatch-done", static_cast<long long>(command.type),
                    command.requestId);
    ++processed;
  }
  return processed;
}

int mainLoopPollCallbackImpl(void *, int timeoutUs) {
  const std::uint64_t entry =
      gMainLoop.pollCount.fetch_add(1, std::memory_order_relaxed);
  // Stage telemetry for the browser console: the first few polls prove the
  // upstream loop reached the unipoll branch at all, the periodic line proves
  // it kept running.  Diagnostic profile only; the payload is just counters.
  if (entry < 3 || entry % 2000 == 0)
    mainLoopTrace("poll", static_cast<double>(entry), timeoutUs);
  // Structurally always -1 here; see the warning on the Scheduler
  // declaration.  Kept only so the retracted measurement stays reproducible.
  if (timeoutUs != 0 && (entry < 60 || entry % 200 == 0))
    mainLoopTrace("poll-pending-uninformative", static_cast<double>(entry),
                  ::Scheduler::GetMostUrgentTaskPriority());
  if (timeoutUs != 0) {
    gMainLoop.idlePollCount.fetch_add(1, std::memory_order_relaxed);
    // Deliberately NOT clearing formatStateStale here.  The first version of
    // this profile did, on the theory that reaching an idle poll meant core
    // had recomputed the watched command states for the current caret
    // position.  Measured 2026-08-06: reaching an idle poll does not mean the
    // matching payload has arrived -- under the live loop the watched
    // payloads arrive one placement late, so clearing here answers the
    // precondition with the previous paragraph's cache: the silent-noop path
    // finding 021 exists to forbid.
    //
    // (An earlier revision of this comment claimed that clearing on a watched
    // payload is not sufficient either, because a late payload would clear it
    // just the same.  RETRACTED 2026-08-06: updateEditorFormatState clears the
    // flag before it emits the event, so no payload arrives without clearing
    // it, and the flag measured true in every search row of both browsers.
    // The misread signal was the harness's own fresh field.  See finding 021.)
    //
    // Residual gap (inferred, no instance observed): one flag guards five
    // fields, so any watched payload -- .uno:Bold, say -- clears it for a
    // later list precondition that was never re-broadcast.  Per-field
    // generation marking is the fix if the precondition is ever read again;
    // product route C does not read it.
  }
  int processed = mainLoopDrainCommands();
  if (processed > 0 || timeoutUs == 0)
    return processed;
  // Idle with nothing queued: wait for a command or a wake request.  The wait
  // is bounded even for timeoutUs == -1 so a scheduler timer armed while
  // blocked is still serviced promptly; COOL's kit caps the -1 case the same
  // way (cool kit/Kit.cpp pollCallback).
  auto waitUntil =
      std::chrono::steady_clock::now() +
      std::chrono::microseconds(timeoutUs < 0 ? 1000000 : timeoutUs);
#ifdef OXSDK_FINDING_016_SELECTION_BARRIER
  if (gSelectionBarrier.stage ==
          SelectionBarrierStage::AwaitingUnitSelection &&
      gSelectionBarrier.boundaryDeadline < waitUntil)
    waitUntil = gSelectionBarrier.boundaryDeadline;
#endif
#ifdef OXSDK_E2_FORMAT_BARRIER
  if (formatBarrierActive() && gFormatBarrier.stageDeadlineArmed &&
      gFormatBarrier.stageDeadline < waitUntil)
    waitUntil = gFormatBarrier.stageDeadline;
#endif
  {
    std::unique_lock<std::mutex> lock(gState.mutex);
    gState.condition.wait_until(lock, waitUntil, [] {
      return !gState.commands.empty() || gMainLoop.wakeRequested;
    });
    gMainLoop.wakeRequested = false;
  }
  return mainLoopDrainCommands();
}

#endif

// One command at a time is an engine invariant.  A dispatched command can
// itself pump the scheduler (the combined drain profile runs
// ProcessEventsToIdle from inside a command), which nests ImplYield and would
// re-enter this callback; the guard makes the nested pass a no-op so command
// dispatch never nests.  Engine-thread only, so a plain static suffices.
int mainLoopPollCallback(void *closure, int timeoutUs) {
  static bool inPollCallback = false;
  if (inPollCallback)
    return 0;
#ifdef OXSDK_E2_V23_LINK_BATCH
  probe::ordered::FlagScope scope(inPollCallback);
  return mainLoopPollCallbackImpl(closure, timeoutUs);
#else
  inPollCallback = true;
  const int processed = mainLoopPollCallbackImpl(closure, timeoutUs);
  inPollCallback = false;
  return processed;
#endif
}

void mainLoopWakeCallback(void *) {
  {
    std::lock_guard<std::mutex> lock(gState.mutex);
    gMainLoop.wakeRequested = true;
  }
  gState.condition.notify_one();
}

bool mainLoopAnyInputCallback(void *, int) {
  // Lets ImplYield route a pass to the poll callback while scheduler work is
  // still pending, so a busy stretch cannot starve command dispatch
  // (vcl/headless/svpinst.cxx ImplYield's anyInput check).
  std::lock_guard<std::mutex> lock(gState.mutex);
#ifdef OXSDK_E2_V23_LINK_BATCH
  return probe::poll::anyInput({gState.commands.size(), static_cast<bool>(gOrderedReply)});
#else
  return !gState.commands.empty();
#endif
}

extern "C" void *mainLoopEngineThreadMain(void *argument) {
  // emscripten_set_main_loop_arg(simulateInfiniteLoop=1) at the bottom of
  // runLoop unwinds this entire frame with a JS 'unwind' exception that the
  // emscripten pthread runtime catches, keeping the worker alive so the loop
  // ticks keep running on this thread (emscripten runtime_pthread.js).  Under
  // -fwasm-exceptions that unwind runs destructors and a catch clause would
  // swallow it, so everything owning state is scoped out before runLoop and
  // nothing after this point may catch (see the EMSCRIPTEN HACK note in
  // desktop/source/app/sofficemain.cxx).
  {
    std::unique_ptr<Command> initial(static_cast<Command *>(argument));
    // Upstream's own switch for this topology.  Without "unipoll" in
    // SAL_LOK_OPTIONS, lo_initialize spawns its lo_startmain thread, which
    // runs a soffice_main of its own (desktop/source/lib/init.cxx:8378) --
    // and the runLoop below would then start a second one and collide with
    // it.  With it, init skips that thread and calls InitVCL on this thread,
    // leaving the one and only main loop to the runLoop call below.  COOL's
    // kit sets the same option before its LOK init
    // (cool kit/SetupKitEnvironment.hpp).
    gStage = "start.sal_lok_options";
    {
      const char *existing = std::getenv("SAL_LOK_OPTIONS");
      if (!existing || !*existing)
        setenv("SAL_LOK_OPTIONS", "unipoll", 1);
      else if (!std::strstr(existing, "unipoll"))
        setenv("SAL_LOK_OPTIONS",
               (std::string(existing) + ":unipoll").c_str(), 1);
    }
    gStage = "start.libreofficekit_hook_2";
    gState.kit = libreofficekit_hook_2("/instdir/program", "file:///tmp/user");
#ifdef OXSDK_E2_V23_LINK_BATCH
    if (gState.kit) {
      std::lock_guard<std::mutex> lock(gState.mutex);
      gState.commands.push_front(*initial);
    } else {
      emitReady(*initial);
      finishExecuting(initial->requestId);
    }
#else
    emitReady(*initial);
    finishExecuting(initial->requestId);
#endif
  }
  mainLoopTrace("init-done", gState.kit != nullptr, 0);
  if (!gState.kit)
    return nullptr;
  // Same-thread requirement: LOK init above and runLoop below must share this
  // thread (COOL kit/Kit.cpp documents the loop getting stuck otherwise), and
  // this thread became the VCL main thread when the hook ran InitVCL.
  gStage = "mainloop.runLoop";
#ifndef OXSDK_E2_V23_LINK_BATCH
  emscripten_set_interval(mainLoopTickAliveProbe, 1000.0, nullptr);
#endif
  mainLoopTrace("entering-runLoop", 0, 0);
  // The closure must be non-null: SvpSalInstance::ImplYield only invokes the
  // poll callback when mpPollClosure is set (vcl/headless/svpinst.cxx, the
  // isUnipoll branch), so passing nullptr silently disables unipoll.  COOL
  // passes its KitSocketPoll pointer; this engine keys everything off
  // globals, so any stable non-null pointer serves.
  gState.kit->pClass->registerAnyInputCallback(
      gState.kit, mainLoopAnyInputCallback, &gMainLoop);
  gState.kit->pClass->runLoop(gState.kit, mainLoopPollCallback,
                              mainLoopWakeCallback, &gMainLoop);
  // Measured 2026-08-06: with VCL already initialized by the unipoll init
  // path, soffice_main returns immediately (ImplSVMain's IsVCLInit early
  // return, vcl/source/app/svmain.cxx), so lo_runLoop only contributes the
  // poll-callback and view-callback registration.  The loop itself is then
  // entered the way the upstream headless backend intends under
  // __EMSCRIPTEN__: Application::Execute -> DoExecute ->
  // emscripten_set_main_loop_arg (vcl/headless/svpinst.cxx:315), whose
  // 'unwind' unwinds only this engine-owned frame -- no upstream frames with
  // destructors or catch clauses sit between the throw and the pthread
  // runtime's catch.
  mainLoopTrace("runLoop-returned", 0, 0);
  gStage = "mainloop.execute";
  mainLoopTrace("entering-execute", 0, 0);
  Application::Execute();
  // Unreachable under emscripten; if this fires the loop never started.
  mainLoopTrace("execute-returned", 0, 0);
  return nullptr;
}

void startMainLoopEngineThread(Command initial) {
  auto owned = std::make_unique<Command>(std::move(initial));
  pthread_t thread;
  if (pthread_create(&thread, nullptr, mainLoopEngineThreadMain,
                     owned.get()) != 0)
    throw std::runtime_error("pthread_create failed for the main-loop engine");
  (void)owned.release();
  pthread_detach(thread);
}
#endif

SubmitStatus startEngine(std::uint32_t requestId, bool sdk) {
  bool expected = false;
  if (!gStarted.compare_exchange_strong(expected, true,
                                        std::memory_order_acq_rel)) {
    Command command{CommandType::EmitReady};
    command.sdk = sdk;
    command.requestId = requestId;
    return submit(std::move(command));
  }

  if (sdk) {
    std::lock_guard<std::mutex> lock(gState.mutex);
    gState.executingRequest = requestId;
  }

  Command initial{CommandType::EmitReady};
  initial.sdk = sdk;
  initial.requestId = requestId;
  try {
#ifdef OXSDK_MAINLOOP_ENGINE
    startMainLoopEngineThread(std::move(initial));
#else
    std::thread(engineLoop, std::move(initial)).detach();
#endif
  } catch (const std::exception &exception) {
    {
      std::lock_guard<std::mutex> lock(gState.mutex);
      gState.executingRequest = 0;
    }
    gStarted.store(false, std::memory_order_release);
    if (sdk)
      emitSdkError(requestId, 0, "start", "THREAD_START_FAILED",
                   exception.what());
    else
      emitError("start", exception.what());
    return SubmitStatus::InternalError;
  }
  return SubmitStatus::Ok;
}
} // namespace

#ifdef OXSDK_E2_V23_DIAGNOSTIC
extern "C" int oxsdk_v23_diagnostic(int kind, int requestId) {
  if (kind < 1 || kind > 9 || requestId <= 0)
    return static_cast<int>(SubmitStatus::InvalidArgument);
  if (!gStarted.load(std::memory_order_acquire))
    return static_cast<int>(SubmitStatus::NotStarted);
  if (kind == 3) {
    // Deliberately the sole off-engine-thread LOK entrance, for the 040
    // negative control. An isolated harness invokes it with a settled doc.
    LibreOfficeKitDocument *document = nullptr;
    {
      std::lock_guard<std::mutex> lock(gState.mutex);
      if (!gCallbackDocumentHandle.load(std::memory_order_acquire) ||
          gState.executingRequest || !gState.commands.empty() ||
          !gState.asynchronousRequests.empty())
        return static_cast<int>(SubmitStatus::InvalidArgument);
      document = gState.document;
    }
    if (!document)
      return static_cast<int>(SubmitStatus::InvalidArgument);
    emitOrderedControl(kind, static_cast<std::uint32_t>(requestId));
    char *text = document->pClass->getTextSelection(document, "text/html", nullptr);
    std::free(text);
    emitSdkError(requestId, gCallbackDocumentHandle.load(), "v23Diagnostic",
                 "DIAGNOSTIC_CONTROL_RETURNED", "JS-thread LOK negative control returned");
    return static_cast<int>(SubmitStatus::Ok);
  }
  Command command{kind == 1 ? CommandType::DiagnosticNeverReturn
                           : kind == 2 ? CommandType::DiagnosticMissingProof
                           : kind == 9 ? CommandType::DiagnosticHtml
                                       : CommandType::DiagnosticKey};
  command.sdk = true;
  command.requestId = static_cast<std::uint32_t>(requestId);
  command.documentHandle = gCallbackDocumentHandle.load(std::memory_order_acquire);
  command.values[0] = kind;
  return static_cast<int>(submit(std::move(command)));
}
#endif

void emitError(const char *where, const std::string &message) {
  emitJson("{\"type\":\"error\",\"where\":\"" + jsonEscape(where) +
           "\",\"msg\":\"" + jsonEscape(message.c_str()) + "\"}");
}

bool started() { return gStarted.load(std::memory_order_acquire); }

void start() { (void)startEngine(0, false); }

SubmitStatus start(std::uint32_t requestId) {
  return startEngine(requestId, true);
}

void open(std::string fileUrl) {
  Command command{CommandType::OpenUrl};
  command.text = std::move(fileUrl);
  (void)submit(std::move(command));
}

SubmitStatus openBytes(std::uint32_t requestId, std::vector<std::uint8_t> bytes,
                       std::string name) {
  Command command{CommandType::OpenBytes};
  command.sdk = true;
  command.requestId = requestId;
  command.name = std::move(name);
  command.bytes = std::move(bytes);
  return submit(std::move(command));
}

void paintTile(int xTwips, int yTwips, int widthTwips, int heightTwips,
               int canvasWidthPx, int canvasHeightPx) {
  Command command{CommandType::PaintTile};
  command.values[0] = xTwips;
  command.values[1] = yTwips;
  command.values[2] = widthTwips;
  command.values[3] = heightTwips;
  command.values[4] = canvasWidthPx;
  command.values[5] = canvasHeightPx;
  (void)submit(std::move(command));
}

SubmitStatus paintTile(std::uint32_t requestId, std::uint32_t documentHandle,
                       int xTwips, int yTwips, int widthTwips, int heightTwips,
                       int canvasWidthPx, int canvasHeightPx) {
  Command command{CommandType::PaintTile};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.values[0] = xTwips;
  command.values[1] = yTwips;
  command.values[2] = widthTwips;
  command.values[3] = heightTwips;
  command.values[4] = canvasWidthPx;
  command.values[5] = canvasHeightPx;
  return submit(std::move(command));
}

void click(int xTwips, int yTwips) {
  Command command{CommandType::Click};
  command.values[0] = xTwips;
  command.values[1] = yTwips;
  (void)submit(std::move(command));
}

SubmitStatus click(std::uint32_t requestId, std::uint32_t documentHandle,
                   int xTwips, int yTwips) {
  Command command{CommandType::Click};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.values[0] = xTwips;
  command.values[1] = yTwips;
  return submit(std::move(command));
}

void insertText(std::string utf8) {
  Command command{CommandType::InsertText};
  command.text = std::move(utf8);
  (void)submit(std::move(command));
}

SubmitStatus insertText(std::uint32_t requestId, std::uint32_t documentHandle,
                        std::string utf8) {
  Command command{CommandType::InsertText};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.text = std::move(utf8);
  return submit(std::move(command));
}

#ifdef OXSDK_E2_V24_TYPED_INSERT
SubmitStatus insertTypedText(std::uint32_t requestId,
                             std::uint32_t documentHandle, std::string utf8) {
  Command command{CommandType::InsertTypedText};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.text = std::move(utf8);
  return submit(std::move(command));
}
#endif

void key(int type, int charCode, int keyCode) {
  Command command{CommandType::Key};
  command.values[0] = type;
  command.values[1] = charCode;
  command.values[2] = keyCode;
  (void)submit(std::move(command));
}

void save(std::string format) {
  Command command{CommandType::Save};
  command.text = std::move(format);
  (void)submit(std::move(command));
}

SubmitStatus save(std::uint32_t requestId, std::uint32_t documentHandle,
                  std::string format) {
  Command command{CommandType::Save};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.text = std::move(format);
  return submit(std::move(command));
}

void close() { (void)submit({CommandType::Close}); }

SubmitStatus close(std::uint32_t requestId, std::uint32_t documentHandle) {
  Command command{CommandType::Close};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  return submit(std::move(command));
}

SubmitStatus search(std::uint32_t requestId, std::uint32_t documentHandle,
                    std::string query, bool backward) {
  Command command{CommandType::Search};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.text = std::move(query);
  command.values[0] = backward ? 1 : 0;
  return submit(std::move(command));
}

SubmitStatus getSelection(std::uint32_t requestId,
                          std::uint32_t documentHandle) {
  Command command{CommandType::GetSelection};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  return submit(std::move(command));
}

#ifdef OXSDK_ODS_EDITOR
SubmitStatus cell(std::uint32_t requestId, std::uint32_t documentHandle,
                  std::uint32_t expectedRevision, int part, int column,
                  int row, int operation, std::string text, bool enabled) {
  Command command{CommandType::Cell};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.expectedRevision = expectedRevision;
  command.values[0] = part;
  command.values[1] = column;
  command.values[2] = row;
  command.values[3] = operation;
  command.values[4] = enabled;
  command.text = std::move(text);
  return submit(std::move(command));
}
#endif

#ifdef OXSDK_ODS_VIEWER
namespace {
SubmitStatus submitPartQuery(CommandType type, std::uint32_t requestId,
                             std::uint32_t documentHandle, int part) {
  Command command{type};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.values[0] = part;
  return submit(std::move(command));
}
} // namespace

SubmitStatus setPart(std::uint32_t requestId, std::uint32_t documentHandle,
                     int part) {
  return submitPartQuery(CommandType::SetPart, requestId, documentHandle, part);
}

SubmitStatus currentPart(std::uint32_t requestId,
                         std::uint32_t documentHandle) {
  return submitPartQuery(CommandType::CurrentPart, requestId, documentHandle, 0);
}

SubmitStatus partName(std::uint32_t requestId, std::uint32_t documentHandle,
                      int part) {
  return submitPartQuery(CommandType::PartName, requestId, documentHandle, part);
}

SubmitStatus partText(std::uint32_t requestId, std::uint32_t documentHandle,
                      int part) {
  return submitPartQuery(CommandType::PartText, requestId, documentHandle, part);
}

#ifdef OXSDK_ODS_VIEWER_V2
SubmitStatus partInfo(std::uint32_t requestId, std::uint32_t documentHandle,
                      int part) {
  return submitPartQuery(CommandType::PartInfo, requestId, documentHandle, part);
}
#endif
#endif

#ifdef OXSDK_E2_V20_LINK_BATCH
SubmitStatus pageRectangles(std::uint32_t requestId,
                            std::uint32_t documentHandle) {
  Command command{CommandType::PageRectangles};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  return submit(std::move(command));
}
#endif

#ifdef OXSDK_E2_V21_LINK_BATCH
SubmitStatus pasteMarkdown(std::uint32_t requestId,
                           std::uint32_t documentHandle, std::string utf8) {
  Command command{CommandType::PasteMarkdown};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.text = std::move(utf8);
  return submit(std::move(command));
}
#endif

SubmitStatus replaceSelection(std::uint32_t requestId,
                              std::uint32_t documentHandle,
                              std::uint32_t expectedRevision,
                              std::string utf8) {
  Command command{CommandType::ReplaceSelection};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.expectedRevision = expectedRevision;
  command.text = std::move(utf8);
  return submit(std::move(command));
}

SubmitStatus undo(std::uint32_t requestId, std::uint32_t documentHandle,
                  std::uint32_t expectedRevision) {
  Command command{CommandType::Undo};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.expectedRevision = expectedRevision;
  return submit(std::move(command));
}

SubmitStatus redo(std::uint32_t requestId, std::uint32_t documentHandle,
                  std::uint32_t expectedRevision) {
  Command command{CommandType::Redo};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.expectedRevision = expectedRevision;
  return submit(std::move(command));
}

SubmitStatus addComment(std::uint32_t requestId,
                        std::uint32_t documentHandle,
                        std::uint32_t expectedRevision, std::string text,
                        std::string author) {
  Command command{CommandType::AddComment};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.expectedRevision = expectedRevision;
  command.text = std::move(text);
  command.name = std::move(author);
  return submit(std::move(command));
}

SubmitStatus listComments(std::uint32_t requestId,
                          std::uint32_t documentHandle) {
  Command command{CommandType::ListComments};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  return submit(std::move(command));
}

SubmitStatus setTrackChanges(std::uint32_t requestId,
                             std::uint32_t documentHandle,
                             std::uint32_t expectedRevision, bool enabled) {
  Command command{CommandType::SetTrackChanges};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.expectedRevision = expectedRevision;
  command.values[0] = enabled ? 1 : 0;
  return submit(std::move(command));
}

SubmitStatus listChanges(std::uint32_t requestId,
                         std::uint32_t documentHandle) {
  Command command{CommandType::ListChanges};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  return submit(std::move(command));
}

#ifdef OXSDK_EDITOR_DISCOVERY
SubmitStatus editorAction(std::uint32_t requestId,
                          std::uint32_t documentHandle,
                          std::uint32_t expectedRevision,
                          std::uint32_t action, bool extendSelection,
                          bool option) {
  Command command{CommandType::EditorAction};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.expectedRevision = expectedRevision;
  command.values[0] = static_cast<int>(action);
  command.values[1] = extendSelection ? 1 : 0;
  command.values[2] = option ? 1 : 0;
  return submit(std::move(command));
}

SubmitStatus editorSelect(std::uint32_t requestId,
                          std::uint32_t documentHandle,
                          std::uint32_t method, int startXTwips,
                          int startYTwips, int endXTwips, int endYTwips,
                          bool boundedReadback) {
  Command command{CommandType::EditorSelect};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.values[0] = static_cast<int>(method);
  command.values[1] = startXTwips;
  command.values[2] = startYTwips;
  command.values[3] = endXTwips;
  command.values[4] = endYTwips;
  command.values[5] = boundedReadback ? 1 : 0;
  return submit(std::move(command));
}

#ifdef OXSDK_E2_FORMAT_BARRIER
// SPEC E2-B 5.7: which gesture classes each action accepts.
//
// Keyed by INTERNAL action id, because that is what the engine routes on.  The
// default is every class; the worker calls the setter once per action at init
// from the profile manifest, and the setter INTERSECTS -- so a manifest can
// withhold a class this binary implements and can never grant one it does not.
// That direction is the whole point: it makes a partial GO enforceable at
// runtime without letting an edited manifest widen the ABI.
//
// The A-versus-B' disposition for cross-paragraph ranges rides on this too.  A
// is this mask with RANGE_CROSS withheld from all five actions; B' is the mask
// left open.  Both are therefore a manifest choice made after the artifact
// exists, which is why neither needs its own link.
constexpr std::uint32_t kAllEditorGestures =
    kGestureCollapsed | kGestureRangeSingle | kGestureRangeCross;
// 23 as of ABI 4 (was 21).  THIS BOUND MUST MOVE WITH THE ACTION LIST, and the
// failure mode if it does not is silent and total: `editorSetActionGestures`
// returns early for an action above it, so the manifest's mask is never stored,
// and `editorGesturePermitted` returns FALSE for it -- the new action is
// refused unconditionally while the manifest says it is granted.  Caught here
// on 2026-08-22 by reading the bound before building, one commit after adding
// internal action 22.
#ifdef OXSDK_E2_V21_LINK_BATCH
// 25 as of ABI 5 (SPEC-M3-link-batch-v21 4.1): the two document moves are
// internal 24 and 25, and this bound moved with them for the reason above.
constexpr std::uint32_t kMaxInternalEditorAction = 25;
static_assert(kMaxInternalEditorAction == OXSDK_EDITOR_MOVE_DOCUMENT_END,
              "the gesture table's bound must follow the action list");
#else
constexpr std::uint32_t kMaxInternalEditorAction = 23;
#endif
std::uint32_t gEditorActionGestures[kMaxInternalEditorAction + 1] = {};
bool gEditorActionGesturesInitialised = false;

void editorSetActionGestures(std::uint32_t internalAction,
                             std::uint32_t gestureMask) {
  if (internalAction == 0 || internalAction > kMaxInternalEditorAction)
    return;
  if (!gEditorActionGesturesInitialised) {
    for (std::uint32_t index = 0; index <= kMaxInternalEditorAction; ++index)
      gEditorActionGestures[index] = kAllEditorGestures;
    gEditorActionGesturesInitialised = true;
  }
  gEditorActionGestures[internalAction] &= gestureMask;
}

bool editorGesturePermitted(std::uint32_t internalAction,
                            std::uint32_t gesture) {
  if (internalAction == 0 || internalAction > kMaxInternalEditorAction)
    return false;
  if (!gEditorActionGesturesInitialised)
    return true;
  return (gEditorActionGestures[internalAction] & gesture) != 0;
}
#endif

SubmitStatus editorPlaceCaret(std::uint32_t requestId,
                             std::uint32_t documentHandle,
                             std::int32_t xTwips, std::int32_t yTwips) {
  Command command{CommandType::EditorPlaceCaret};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  command.values[0] = xTwips;
  command.values[1] = yTwips;
  return submit(std::move(command));
}

SubmitStatus editorGetState(std::uint32_t requestId,
                            std::uint32_t documentHandle) {
  Command command{CommandType::EditorGetState};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  return submit(std::move(command));
}

#ifdef OXSDK_FINDING_016_SCHEDULER_PROBE
SubmitStatus editorDrainScheduler(std::uint32_t requestId,
                                  std::uint32_t documentHandle) {
  Command command{CommandType::EditorDrainScheduler};
  command.sdk = true;
  command.requestId = requestId;
  command.documentHandle = documentHandle;
  return submit(std::move(command));
}
#endif
#endif

SubmitStatus cancel(std::uint32_t requestId) {
  if (!gStarted.load(std::memory_order_acquire))
    return SubmitStatus::NotStarted;
  std::lock_guard<std::mutex> lock(gState.mutex);
  if (gState.executingRequest == requestId)
    return SubmitStatus::NotCancellable;
  if (gState.asynchronousRequests.count(requestId))
    return SubmitStatus::NotCancellable;
  if (!gState.pendingRequests.count(requestId))
    return SubmitStatus::RequestNotFound;
  gState.cancelledRequests.insert(requestId);
  return SubmitStatus::Ok;
}
} // namespace probe
