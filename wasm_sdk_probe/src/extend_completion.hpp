#ifndef OXOFFICE_EXTEND_COMPLETION_HPP
#define OXOFFICE_EXTEND_COMPLETION_HPP

// SPEC-M3-link-batch 10.1 and 12.2 (rulings 2 B1 and 3 Q2): how an extend, or
// a plain move that starts on a range, is allowed to complete -- rule (a), the
// transition rule -- and the one per-document flag, `extendUnconfirmed`, that
// a delete behind an unconfirmed extend is judged by.  The pure half, in the
// shape of merge_key_undo.hpp: the engine feeds the dispatch snapshot and each
// parsed callback in and acts on the answers; clocks, LOK calls and JSON stay
// in the engine, so tests/extend_completion_model_test.cpp can drive this with
// generated callback sequences on the host.  No engine code calls this yet
// (ruling 2 condition 2, ruling 3 condition 18: the model test is committed
// and red-cased before anything is wired).
//
// Rule (a).  A pending move is created with what the engine knew at dispatch:
// its kind and the selection rectangles cached at that moment.
//   caret-start plain    today's rule, unchanged (one variable per link): the
//                        first cursor or selection callback completes it.
//   extend-or-range-start  completion needs, in order, (1) a TEXT_SELECTION
//                        whose parsed rectangle list differs from the dispatch
//                        cache (empty against non-empty counts as different),
//                        then (2) the next INVALIDATE_VISIBLE_CURSOR.  The
//                        state serialised is the cache after that cursor.
// Why a transition and not the first callback: Writer computes a selection
// payload only at flush time and drops it when it equals the last one SENT
// (init.cxx:1592-1594, 2530-2537), so a Shift+key's trace is a selection that
// differs -- it can neither be forged by a relayout nor dropped (the merge
// spec's 3.2 applied to the selection).  Why the cursor after it: natively the
// cursor callback is always last (extend-signatures, 98 of 98 cells), and a
// completion on the first TEXT_SELECTION would put the pre-key caret in the
// reply.  The 250 ms readback stays as the fallback for the keys that produce
// no callback at all (096, ten native-silent cells).
//
// What rule (a) cannot see, named (L-extend-prior-flush): an operation that
// completed BEFORE its own flush, whose late flush carries a TEXT_SELECTION
// differing from the extend's dispatch cache, completes the extend early with
// that operation's state.  The population is whatever the model test prints
// (12.1); the examples are a synchronous insert over a selection, an operation
// completed by readback, a uno-command-result completion, and a multi-call
// select with a flush between its calls.  Not in it: the merge key (its flush
// is empty-to-empty, so it sends no TEXT_SELECTION) and plain moves from a
// caret (no TEXT_SELECTION).
//
// The flag (12.2).  An extend answered by the readback may still have its key
// queued in core.  A delete posted behind it stacks: the barrier's K1 extends
// the selection the pending key made, and the barrier deletes two units where
// Writer deletes one; in the other direction the two keys cancel, no callback
// comes, and C's window would report a silent no-op mid-paragraph.  So:
//   set      when an extend completes by readback (not a plain move, a click
//            or a select-range);
//   cleared  only by evidence that core has run every key posted before it:
//            an extend or range-start move completing under rule (a), or a
//            delete admitted under the flag completing with its proof; and on
//            close or a new worker.  NOT by a caret-start plain move: its
//            first-cursor completion is forgeable (merge spec 16.1).
//   while set  delete-selection is refused before dispatch (.uno:Delete runs
//            synchronously under the SolarMutex and jumps every posted key);
//            a Barrier-class K1 is admitted only when its selected text is
//            exactly one code point; a MergeKey unit keeps its fence plus K2
//            (unchanged, merge_key_undo.hpp); at the expiry of C's window the
//            answer is a refusal, never verified-boundary-noop.
// Every refusal here is stage `prior-key-unconfirmed`, keyPosted:false, with
// the user's key never dispatched.  Named cost: L-flagged-delete-grapheme (a
// multi-code-point grapheme is refused while the flag is set).

#include "merge_key_undo.hpp"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace probe {
namespace extend {

using merge::Rect;

// ---- the pending move --------------------------------------------------------

enum class MoveKind {
  CaretStartPlain,    // no Shift, and the dispatch cache held no selection
  ExtendOrRangeStart, // Shift held, or the dispatch cache held a selection
};

// 10.1: judged from the engine's cached rectangles at dispatch, as the
// gesture gate judges (probe_engine.cpp ~5285), never from a readback.
inline MoveKind classifyMove(bool extendSelection,
                             const std::vector<Rect> &cachedSelection) {
  return (extendSelection || !cachedSelection.empty())
             ? MoveKind::ExtendOrRangeStart
             : MoveKind::CaretStartPlain;
}

enum class Completion {
  Pending,
  FirstCallback, // caret-start plain: today's documented-callback completion
  Transition,    // rule (a): a differing TEXT_SELECTION, then the next cursor
  Readback,      // the deadline: today's verified-move-readback
};

inline const char *completionName(Completion c) {
  switch (c) {
  case Completion::Pending: return "pending";
  case Completion::FirstCallback: return "first-callback";
  case Completion::Transition: return "transition";
  case Completion::Readback: return "readback";
  }
  return "?";
}

struct PendingMove {
  MoveKind kind = MoveKind::CaretStartPlain;
  bool extend = false; // Shift was held: the flag cares, the rule does not
  std::vector<Rect> dispatchSelection;
  bool selectionDiffered = false; // rule (a) step 1 seen
  Completion completion = Completion::Pending;
};

// Right before posting the key.  `cachedSelection` is the engine's
// selectionRectangles at that moment, copied: it is compared against later.
inline PendingMove beginMove(bool extendSelection,
                             const std::vector<Rect> &cachedSelection) {
  PendingMove m;
  m.kind = classifyMove(extendSelection, cachedSelection);
  m.extend = extendSelection;
  m.dispatchSelection = cachedSelection;
  return m;
}

// A LOK_CALLBACK_TEXT_SELECTION, already parsed by the engine (an empty
// payload parses to an empty list).  Returns the completion, Pending if none.
inline Completion onTextSelection(PendingMove &m,
                                  const std::vector<Rect> &parsed) {
  if (m.completion != Completion::Pending)
    return m.completion;
  switch (m.kind) {
  case MoveKind::CaretStartPlain:
    m.completion = Completion::FirstCallback;
    break;
  case MoveKind::ExtendOrRangeStart:
    // Only a selection that differs from what was known at dispatch is the
    // key's trace; one equal to it is a relayout's resend or an unrelated
    // flush and proves nothing (merge spec 3.2).
    if (!m.selectionDiffered && parsed != m.dispatchSelection)
      m.selectionDiffered = true;
    break;
  }
  return m.completion;
}

// A LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR.
inline Completion onVisibleCursor(PendingMove &m) {
  if (m.completion != Completion::Pending)
    return m.completion;
  switch (m.kind) {
  case MoveKind::CaretStartPlain:
    m.completion = Completion::FirstCallback;
    break;
  case MoveKind::ExtendOrRangeStart:
    // A cursor before the differing selection is some earlier flush's (or a
    // relayout's, which can forge one, 16.1) and does not complete.
    if (m.selectionDiffered)
      m.completion = Completion::Transition;
    break;
  }
  return m.completion;
}

// The readback deadline fired with the move still pending.
inline Completion onReadbackDeadline(PendingMove &m) {
  if (m.completion == Completion::Pending)
    m.completion = Completion::Readback;
  return m.completion;
}

// ---- the flag ------------------------------------------------------------------

class ExtendUnconfirmed {
public:
  bool set() const { return set_; }

  // On every completion of a move, whatever its kind.  Only two of the twelve
  // (kind, extend, completion) cells touch the flag: an extend completed by
  // readback sets it; an extend-or-range-start move completed under rule (a)
  // clears it.  A caret-start plain move, a plain move completed by readback,
  // and a readback-completed range-start plain move leave it as it is -- the
  // last two are 12.2's "not for plain moves": their stacking under K1 was
  // judged Writer-equivalent, and the model test reports where it is not.
  void onMoveCompleted(const PendingMove &m) {
    if (m.completion == Completion::Transition)
      set_ = false;
    else if (m.completion == Completion::Readback && m.extend)
      set_ = true;
  }

  // A delete that was admitted while the flag was set completed with its
  // proof: for a Barrier-class unit, the one-code-point K1 selection and the
  // collapse after .uno:SwBackspace / .uno:Delete; for a MergeKey unit, the
  // fence, K2 and the undo payload (merge_key_undo.hpp, unchanged).  K1 was
  // posted behind every earlier key, so its selection arriving is the
  // evidence that core ran them all.
  void onFlaggedDeleteProved() { set_ = false; }

  // Close, or a new worker: no key of this document can be pending any more.
  void onDocumentClosed() { set_ = false; }

private:
  bool set_ = false;
};

// ---- the decisions while the flag is set ---------------------------------------
//
// Each returns nullptr to take today's path, else the stage to refuse with.
// The stage lives here, not in merge::kStages, because no engine code names
// it yet; wiring appends it to the engine's lookup (its keyPosted split is
// the same as the merge stages before the key: false).

constexpr merge::Stage kPriorKeyUnconfirmed{"prior-key-unconfirmed", false};

// delete-selection, before dispatch.  .uno:Delete is synchronous and would run
// on whatever core has selected NOW, ahead of a queued extend.
inline const merge::Stage *judgeDeleteSelection(bool flagSet) {
  return flagSet ? &kPriorKeyUnconfirmed : nullptr;
}

// A Barrier-class unit (classifyUnit == Barrier; never MergeKey, which keeps
// its fence plus K2).  `k1CodePoints` is K1's selected text as read back.
// Exactly one code point is the only proof a stacked K1 cannot produce: a K1
// that extended a pending one-unit extend holds two units.  Named cost: a
// multi-code-point grapheme is refused while the flag is set
// (L-flagged-delete-grapheme).
inline const merge::Stage *
judgeBarrierUnit(bool flagSet, const std::vector<std::uint32_t> &k1CodePoints) {
  if (!flagSet)
    return nullptr;
  return k1CodePoints.size() == 1 ? nullptr : &kPriorKeyUnconfirmed;
}

// C's window (10.5) expired with a second NONE and a collapsed cache.  With
// the flag clear this is verified-boundary-noop; with it set, a pending
// extend and K1 may have cancelled each other (empty-to-empty sends no
// callback at all), so the answer is a refusal.
inline const merge::Stage *judgeWindowExpiry(bool flagSet) {
  return flagSet ? &kPriorKeyUnconfirmed : nullptr;
}

} // namespace extend
} // namespace probe

#endif
