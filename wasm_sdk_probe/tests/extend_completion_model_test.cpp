#include "extend_completion.hpp"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <map>
#include <set>
#include <string>
#include <vector>

// SPEC-M3-link-batch 10.1, 12.1, 12.2 (rulings 2 B1, 3 Q1/Q2): rule (a) and
// the flag `extendUnconfirmed`, driven by sequences GENERATED from a model of
// LOK, not listed by hand.  The model of tests/merge_key_undo_model_test.cpp
// with the shapes 12.1 asks for.
//
// The model, and what each part of it stands for:
//   - one FIFO of posted keys and flushes (lokhelper.cxx:1291 posts a key as
//     a user event; init.cxx:2577-2581 schedules one flush when none is
//     pending; a repaint that happens while one is pending joins it);
//   - a flush computes every payload at flush time (init.cxx:2485-2486), after
//     whatever UNO_COMMAND_RESULT was queued before it, in the order START,
//     END, TEXT_SELECTION, then the cursor (init.cxx:2394-2410); TEXT_SELECTION
//     and the cursor are dropped when equal to the last value SENT
//     (init.cxx:1592-1594, 2530-2537), START/END never are;
//   - one line of text with a caret and a mark, so Shift+Left/Right/End,
//     plain Left/Right and the barrier's own Shift+Left have real effects;
//     an empty mark is not a selection (crsrsh.cxx:3040-3047); a plain arrow
//     on a range clears the mark and moves one unit from the point (the
//     model's choice; natively every plain key on a range sends SEL0 CUR);
//     the selection payload is one rectangle per line, as Writer sends it;
//   - the engine's synchronous calls (paste, setTextSelection, .uno:* with a
//     listener, unoctitm.cxx:655-657) run at an event boundary (the
//     SolarMutex); its decisions that need no mutex (the dispatch snapshot,
//     the readback deadline) land between any two callbacks -- the engine is
//     a second thread (probe_engine.cpp:6518) and a command's snapshot can be
//     taken while a flush is half delivered; `lag` counts the LOK steps
//     (keys, or single callbacks) between a decision and its landing;
//   - the earlier operations 12.1 names, every one generated: a synchronous
//     insert (typing, and typing over a range) whose flush is still queued;
//     a move completed by the readback deadline with its flush late; a
//     uno-command-result completion (delete-selection, undo, an inline
//     format) ahead of the same flush's SEL/CUR; a range select made of three
//     synchronous setTextSelection calls, each able to flush;
//   - the page's queue runs one item at a time and binds the delete's form
//     when the item runs (12.4): delete-selection when its snapshot holds a
//     range, else delete-backward through the barrier; rule A keeps the key's
//     own collapsed form right after a delete;
//   - the barrier (probe_engine.cpp ~3785-3895, ~4004-4049): core NONE and a
//     collapsed cache before K1; K1's TEXT_SELECTION queues the verifier
//     (readSelection, one rectangle, text without a separator); the 250 ms
//     deadline reads core; C's window (10.5) waits until core is idle and
//     answers verified-boundary-noop or, flagged, a refusal.
//
// Property for rule (a): when a rule-(a) move completes, the cache serialised
// equals core's state right after that move's own key ran.  Every generated
// sequence where it does not is PRINTED (phase 1); that printout is
// L-extend-prior-flush's population (12.1).  Each printed sequence must fall
// in a declared class, by mechanism (which operation's flush carried the
// differing selection and how that operation completed), and each declared
// class must occur.
//
// Property for the flag (phase 2): after an extend answered by the readback
// with its key still queued, the Backspace behind it refuses with
// prior-key-unconfirmed; never a verified-selection-delete of other than one
// unit, never .uno:Delete on a range other than the dispatch's, never a
// verified-boundary-noop with a key pending.  Liveness: no disturbance -> rule
// (a); a flagged Backspace whose K1 is one code point deletes one; Shift+End
// at the line end then Backspace deletes one, as Writer does; a range then
// Backspace is delete-selection with the flag clear; a pending plain move
// then Backspace deletes what Writer deletes.
//
// Red cases in the same generator: 9's rule (first cursor) and v19's rule
// (first TEXT_SELECTION) must fail "insert then Shift+key" and "type over a
// range then Shift+key"; no flag must print a two-unit delete and a silent
// mid-paragraph no-op; the one-code-point rule applied unflagged must refuse a
// multi-code-point grapheme in an undisturbed sequence.
//
// SPEC-M3-ordered-commands §8 (ruling 1 §2.7, addendum 1): SECTION D runs the same generator in a
// synchronous-key mode, C (unipoll).  A key or a command applies inside its call; the flush is still a
// posted user event; the poll, where every engine decision lands, runs only on a tick with no user event
// pending (svpinst.cxx:440-444) and does one thing; a command's reply goes at the next poll and carries the
// engine's cache as it is then; a caret delete is the user's own Backspace (no barrier).  Property: every
// shape, condition 33's two included, ends as Writer ends (text, caret and mark), and no reply carries a
// state other than core's (the forged-completion class is empty).  Red cases: the reply in the same poll
// as its command (before its flush), and a poll between two callbacks of one flush; each must print a
// forged reply.  The threaded mode stays the red case that the generator is alive (27,744 / 2,448 /
// 5,474 / 3,868, pinned).  Limits: a key is one event with no hops (only the withdrawn FIFO candidates
// depended on hops); bold does not change a rectangle's width (condition 40); the page sends one item at
// a time, so "one command per poll" is never contested here and is not discriminated by this model.
//
// What the model reports but the spec's rule does not cover is printed under
// its own name and counted (REPORTED 1-5 at the end of main()).  One sequence
// can be traced: EXTEND_MODEL_TRACE='<its describe() line>' <binary>.

using namespace probe::extend;
using probe::merge::Rect;
using probe::merge::Stage;

namespace {

int gFailures = 0;
void fail(const std::string &what) {
  ++gFailures;
  std::printf("FAIL %s\n", what.c_str());
}

// ---- the core: one line --------------------------------------------------------

struct Unit {
  char id;
  int cps; // code points in this Writer unit (grapheme)
  bool bold = false; // condition 33: an inline format on the unit, shown as '*' in text()
};

struct Core {
  std::vector<Unit> units;
  int pt = 0, mk = 0;
  bool hasMark = false;
  int n() const { return static_cast<int>(units.size()); }
  bool nonEmpty() const { return hasMark && mk != pt; }
  int lo() const { return hasMark ? std::min(pt, mk) : pt; }
  int hi() const { return hasMark ? std::max(pt, mk) : pt; }
  std::vector<std::uint32_t> selText() const {
    std::vector<std::uint32_t> out;
    for (int i = lo(); i < hi(); ++i)
      for (int c = 0; c < units[i].cps; ++c)
        out.push_back(static_cast<std::uint32_t>(units[i].id) * 16 + c);
    return out;
  }
  std::vector<Rect> selRects() const {
    if (!nonEmpty())
      return {};
    return {Rect{lo() * 100L, 0, (hi() - lo()) * 100L, 276}};
  }
  Rect caretRect() const { return Rect{pt * 100L, 0, 0, 276}; }
  std::string text() const {
    std::string s;
    for (const Unit &u : units) {
      s += u.id;
      if (u.bold) s += '*';
    }
    return s;
  }
  // An empty mark is not a selection: nothing observable tells it from no
  // mark (HasSelection, the payloads, the next key), so it is normalised.
  void normalize() {
    if (hasMark && mk == pt)
      hasMark = false;
  }
  bool operator==(const Core &o) const {
    return text() == o.text() && pt == o.pt && hasMark == o.hasMark &&
           (!hasMark || mk == o.mk);
  }
  int eraseSelection() {
    const int a = lo(), b = hi();
    units.erase(units.begin() + a, units.begin() + b);
    pt = a;
    hasMark = false;
    return b - a;
  }
};

enum class Key { ShiftLeft, ShiftRight, ShiftEnd, Left, Right };
const char *keyName(Key k) {
  static const char *names[] = {"Shift+Left", "Shift+Right", "Shift+End", "Left", "Right"};
  return names[static_cast<int>(k)];
}
bool isExtend(Key k) { return k == Key::ShiftLeft || k == Key::ShiftRight || k == Key::ShiftEnd; }

// Returns whether anything changed (a key that changes nothing produces no
// callback of any type: extend-signatures P-b).
bool applyKey(Core &c, Key k) {
  const Core before = c;
  const int n = c.n();
  const auto mark = [&] {
    if (!c.hasMark) {
      c.hasMark = true;
      c.mk = c.pt;
    }
  };
  switch (k) {
  case Key::ShiftLeft: mark(); if (c.pt > 0) --c.pt; break;
  case Key::ShiftRight: mark(); if (c.pt < n) ++c.pt; break;
  case Key::ShiftEnd: mark(); c.pt = n; break;
  case Key::Left: c.hasMark = false; if (c.pt > 0) --c.pt; break;
  case Key::Right: c.hasMark = false; if (c.pt < n) ++c.pt; break;
  }
  c.normalize();
  return !(c == before);
}

// ---- the scenario ----------------------------------------------------------------

enum class Earlier { None, InsertCaret, InsertRange, RbMove, UnoDelete, UnoUndo, UnoFormat, Select3 };
const char *earlierName(Earlier e) {
  static const char *names[] = {"none", "insert@caret", "insert@range", "readback-move",
                                "uno:delete-selection", "uno:undo", "uno:format", "select3"};
  return names[static_cast<int>(e)];
}

struct Scenario {
  int text;    // 0: a b c d (all one code point); 1: a b E c (E = two code points)
  int shape;   // 0..4 caret at that position; 5 range 1->3; 6 range 3->1; 7 range 2->3
  Earlier e;
  Key eKey;    // RbMove only
  int eDeadline; // RbMove, Select3: the earlier operation's readback lag
  int gapRS, gapSE; // Select3: a flush between RESET/START, START/END
  int u;       // 0 none; 1.. 1 + Key
  int lagReg;  // LOK steps between the earlier completion and U's snapshot
  int lagDeadline; // LOK steps between U's key post and its readback deadline
  bool backspace; // follow == 1
  int follow;     // 0 none; 1 Backspace; 2 typing (paste, synchronous); 3 inline format (.uno:Bold, synchronous)
  int lagReg2; // LOK steps between U's completion and the follow-up's resolution
  int lagB1;   // LOK steps between K1's post and the 250 ms read
  int lagV;    // LOK steps between K1's TEXT_SELECTION and the verifier
};

Core makeCore(const Scenario &s) {
  Core c;
  if (s.text == 0)
    c.units = {{'a', 1}, {'b', 1}, {'c', 1}, {'d', 1}};
  else
    c.units = {{'a', 1}, {'b', 1}, {'E', 2}, {'c', 1}};
  if (s.shape <= 4) {
    c.pt = s.shape;
  } else if (s.shape == 5) {
    c.hasMark = true; c.mk = 1; c.pt = 3;
  } else if (s.shape == 6) {
    c.hasMark = true; c.mk = 3; c.pt = 1;
  } else {
    c.hasMark = true; c.mk = 2; c.pt = 3;
  }
  return c;
}

std::string describe(const Scenario &s) {
  std::string out = std::string("text=") + (s.text ? "abEc" : "abcd") + " shape=";
  static const char *shapes[] = {"caret0", "caret1", "caret2", "caret3", "caret4", "range1-3", "range3-1", "range2-3"};
  out += shapes[s.shape];
  out += std::string(" E=") + earlierName(s.e);
  if (s.e == Earlier::RbMove)
    out += std::string("(") + keyName(s.eKey) + ",deadline=" + std::to_string(s.eDeadline) + ")";
  if (s.e == Earlier::Select3)
    out += "(gapRS=" + std::to_string(s.gapRS) + ",gapSE=" + std::to_string(s.gapSE) +
           ",deadline=" + std::to_string(s.eDeadline) + ")";
  out += std::string(" U=") + (s.u ? keyName(static_cast<Key>(s.u - 1)) : "none");
  out += " lagReg=" + std::to_string(s.lagReg) + " lagDeadline=" + std::to_string(s.lagDeadline);
  if (s.backspace)
    out += " Backspace(lagReg2=" + std::to_string(s.lagReg2) + ",lagB1=" + std::to_string(s.lagB1) +
           ",lagV=" + std::to_string(s.lagV) + ")";
  else if (s.follow == 2)
    out += " Type(lagReg2=" + std::to_string(s.lagReg2) + ")";
  else if (s.follow == 3)
    out += " Bold(lagReg2=" + std::to_string(s.lagReg2) + ")";
  return out;
}

// Writer with no engine in between: the same keys and commands, in order.
void writerEarlier(Core &w, const Scenario &s) {
  switch (s.e) {
  case Earlier::None: case Earlier::UnoFormat: break;
  case Earlier::InsertCaret: case Earlier::InsertRange: {
    const int a = w.lo();
    if (w.nonEmpty()) w.eraseSelection();
    w.units.insert(w.units.begin() + a, Unit{'x', 1});
    w.pt = a + 1; w.hasMark = false;
    break;
  }
  case Earlier::RbMove: applyKey(w, s.eKey); break;
  case Earlier::UnoDelete: if (w.nonEmpty()) w.eraseSelection(); else if (w.pt < w.n()) w.units.erase(w.units.begin() + w.pt); break;
  case Earlier::UnoUndo: w.units.insert(w.units.begin() + w.pt, Unit{'z', 1}); w.hasMark = true; w.mk = w.pt; w.pt += 1; break;
  case Earlier::Select3: w.hasMark = true; w.mk = 1; w.pt = 3; break;
  }
}
Core writerCore(const Scenario &s) {
  Core w = makeCore(s);
  writerEarlier(w, s);
  if (s.u) applyKey(w, static_cast<Key>(s.u - 1));
  if (s.backspace) {
    if (w.nonEmpty()) w.eraseSelection();
    else if (w.pt > 0) { w.units.erase(w.units.begin() + w.pt - 1); --w.pt; }
  } else if (s.follow == 2) {
    const int a = w.lo();
    if (w.nonEmpty()) w.eraseSelection();
    w.units.insert(w.units.begin() + a, Unit{'x', 1});
    w.pt = a + 1; w.hasMark = false;
  } else if (s.follow == 3) {
    // bold on a selection marks it; on a caret Writer only arms the insertion attribute (no change)
    if (w.nonEmpty())
      for (int i = w.lo(); i < w.hi(); ++i) w.units[i].bold = true;
  }
  return w;
}
std::string writerText(const Scenario &s) { return writerCore(s).text(); }

// ---- the rules under test ---------------------------------------------------------

enum class Rule { Transition, FirstCursor, FirstSelection };

struct Knobs {
  Rule rule = Rule::Transition;
  bool flagDisabled = false;     // red case: remove the flag
  bool alwaysOneCodePoint = false; // red case: the one-code-point rule unflagged
  bool resolverRuleA = true;     // 12.4 rule A in the run-time resolver
  // SPEC-M3-ordered-commands §8: the synchronous-key mode (C), and its two red cases
  bool sync = false;
  bool syncReplySamePoll = false; // red case: the reply in the same poll as its command, before its flush
  bool syncPollMidFlush = false;  // red case: a poll between two callbacks of one flush
};

// ---- the run ------------------------------------------------------------------------

enum Owner { OE = 0, OU = 1, OK1 = 2, OB = 3 };
enum CbType { RESULT, SS, SE, SEL, CUR };

struct Ev {
  bool isKey;
  Key key;
  int owner;
};
struct Cb {
  CbType t;
  std::vector<Rect> rects;
  Rect caret;
  int mask;
  int owner;
};

enum class ActionType { Arrive, PostKey, Deadline, SelectStart, SelectEnd, BarrierStart, BarrierDeadline1, Verify, WindowExpiry, DeleteSelection, FinishDelete, TypeChar, BoldSelection, Reply };
struct Action {
  ActionType type;
  int readyAt;
  bool boundary;
  bool whenIdle;
  int owner;
};

enum class Outcome { None, Refused, Deleted, Noop, Changed };

struct Run {
  const Scenario &sc;
  const Knobs &kn;
  Core core;
  // LOK
  std::deque<Ev> fifo;
  bool flushPending = false, repaint = false;
  int flushMask = 0;
  std::deque<int> resultQueue;
  std::vector<Cb> flushCbs;
  std::size_t flushPos = 0;
  bool midFlush = false;
  std::string lastSel;
  Rect lastCaret;
  // engine
  std::vector<Rect> cacheSel;
  Rect cacheCaret;
  std::uint64_t seq = 0;
  bool pendingActive = false;
  int pendingOwner = -1;
  bool pendingIsSelect = false;
  PendingMove pending;
  int pendingDeadline = -1; // index marker, see cancelDeadline
  ExtendUnconfirmed flag;
  bool busy = false;
  int tick = 0;
  std::vector<Action> actions;
  bool keyRan[4] = {false, false, false, false};
  bool keyPosted[4] = {false, false, false, false};
  // barrier
  enum class Stage { Idle, AwaitingUnit, UnitQueued, AwaitingDelete, Finished } stage = Stage::Idle;
  bool flaggedAdmit = false, ackSeen = false, collapseSeen = false, finishQueued = false;
  std::uint64_t dispatchSeq = 0;
  int deletedUnits = 0;
  // page
  int nextItem = 0; // 0 earlier, 1 U, 2 backspace, 3 done
  bool previousWasDelete = false;
  // records
  Completion eCompletion = Completion::Pending, uCompletion = Completion::Pending;
  MoveKind eKind = MoveKind::CaretStartPlain, uKind = MoveKind::CaretStartPlain;
  bool selectEndRan = false, eSelectStale = false;
  bool uRegistered = false, uKeyRan = false, uKeyRanAtCompletion = false;
  Core coreAfterU;
  bool uStale = false;
  int differedMask = -1; // the mask of the flush whose SEL was rule (a)'s step 1
  bool uStaleTransition = false;
  bool uStaleFirstCallback = false;
  bool flagAtU = false;
  Outcome outcome = Outcome::None;
  std::string stageName, completionName, refusalSite;
  int pendingMaskAtDelete = 0;
  bool flagAtDelete = false;
  bool deleteSelectionForm = false;
  bool admittedBeforeK1Ran = false;
  bool deleteSelOnOtherRange = false;
  bool noopWithKeyPending = false;
  bool guardHit = false;
  // C (SPEC-M3-ordered-commands §8): what the next reply answers, the page's snapshot (the state the
  // previous reply carried), and the replies whose state was not core's
  enum class ReplyFor { None, Item, Move, DeleteSelection, KeyDelete, Type, Format } replyFor = ReplyFor::None;
  bool keyChanged = false;
  std::vector<Rect> snapSel;
  int forgedReplies = 0;
  bool trace = false;
  void tr(const std::string &what) const { if (trace) std::printf("  t=%d %s | core=%s pt=%d mk=%s cache=%s fifo=%s\n", tick, what.c_str(), core.text().c_str(), core.pt, core.hasMark ? std::to_string(core.mk).c_str() : "-", cacheSel.empty() ? "collapsed" : "range", fifoText().c_str()); }
  std::string fifoText() const { std::string o; for (const Ev &e : fifo) o += e.isKey ? std::string(keyName(e.key)) + "@" + std::to_string(e.owner) + " " : "Flush "; if (midFlush) o += "(mid-flush)"; return o; }

  Run(const Scenario &s, const Knobs &k) : sc(s), kn(k), core(makeCore(s)) {
    // settled: the engine has seen the document as it is
    lastSel = selPayload();
    lastCaret = core.caretRect();
    cacheSel = core.selRects();
    cacheCaret = lastCaret;
    snapSel = cacheSel;
  }

  std::string selPayload() const {
    if (!core.nonEmpty()) return "";
    return std::to_string(core.lo()) + "-" + std::to_string(core.hi());
  }

  // ---- LOK side ----
  void scheduleFlush(int owner) {
    flushMask |= 1 << owner;
    if (!flushPending) {
      flushPending = true;
      fifo.push_back(Ev{false, Key::Left, -1});
    }
  }
  void repaintFrom(int owner) {
    repaint = true;
    scheduleFlush(owner);
  }
  void queueResult(int owner) {
    resultQueue.push_back(owner);
    scheduleFlush(owner);
  }
  int pendingKeyMask() const {
    int m = 0;
    for (const Ev &e : fifo)
      if (e.isKey) m |= 1 << e.owner;
    return m;
  }

  void startFlush() {
    flushPending = false;
    const int mask = flushMask;
    flushMask = 0;
    flushCbs.clear();
    for (int o : resultQueue) flushCbs.push_back(Cb{RESULT, {}, {}, mask, o});
    resultQueue.clear();
    if (repaint) {
      repaint = false;
      if (core.nonEmpty()) {
        flushCbs.push_back(Cb{SS, {}, {}, mask, -1});
        flushCbs.push_back(Cb{SE, {}, {}, mask, -1});
      }
      const std::string sel = selPayload();
      if (sel != lastSel) {
        lastSel = sel;
        flushCbs.push_back(Cb{SEL, core.selRects(), {}, mask, -1});
      }
      const Rect c = core.caretRect();
      if (c != lastCaret) {
        lastCaret = c;
        flushCbs.push_back(Cb{CUR, {}, c, mask, -1});
      }
    }
    flushPos = 0;
    midFlush = !flushCbs.empty();
  }

  void lokStep() {
    if (midFlush) {
      const Cb cb = flushCbs[flushPos++];
      if (flushPos == flushCbs.size()) midFlush = false;
      deliver(cb);
      return;
    }
    if (fifo.empty()) return;
    const Ev ev = fifo.front();
    fifo.pop_front();
    if (ev.isKey) {
      keyRan[ev.owner] = true;
      if (applyKey(core, ev.key)) repaintFrom(ev.owner);
      tr(std::string("LOK ran key ") + keyName(ev.key) + "@" + std::to_string(ev.owner));
      if (ev.owner == OU) { uKeyRan = true; coreAfterU = core; }
    } else {
      startFlush();
      if (midFlush) {
        const Cb cb = flushCbs[flushPos++];
        if (flushPos == flushCbs.size()) midFlush = false;
        deliver(cb);
      }
    }
  }

  // ---- engine: callbacks ----
  void deliver(const Cb &cb) {
    static const char *names[] = {"RESULT", "SS", "SE", "SEL", "CUR"};
    tr(std::string("LOK delivered ") + names[cb.t] + (cb.t == SEL ? (cb.rects.empty() ? "0" : "") : ""));
    switch (cb.t) {
    case RESULT:
      if (kn.sync) break; // C: every completion is at the poll after the flush (syncAnswer)
      if (cb.owner == OE && nextItem == 0 && !pendingActive) {
        // the earlier uno operation: completes at its result (probe_engine.cpp:2742-2797)
        eCompletion = Completion::FirstCallback;
        pageNext(true);
      } else if (cb.owner == OB && deleteSelectionForm) {
        completionName = "uno-command-result";
        outcome = Outcome::Deleted;
        nextItem = 3;
      } else if (cb.owner == OB && sc.follow == 3) {
        completionName = "uno-command-result";
        outcome = Outcome::Changed;
        nextItem = 3;
      } else if (cb.owner == OB && stage == Stage::AwaitingDelete) {
        ackSeen = true;
        maybeQueueFinish();
      }
      break;
    case SS: case SE:
      break;
    case SEL:
      cacheSel = cb.rects;
      ++seq;
      barrierSel();
      feedPending(cb);
      break;
    case CUR:
      cacheCaret = cb.caret;
      ++seq;
      feedPending(cb);
      break;
    }
  }

  void feedPending(const Cb &cb) {
    if (!pendingActive || kn.sync) return;
    Completion c = Completion::Pending;
    if (pendingIsSelect) {
      if (cb.t == SEL) c = Completion::FirstCallback;
    } else if (pending.kind == MoveKind::CaretStartPlain || kn.rule == Rule::Transition) {
      if (cb.t == SEL) {
        const bool before = pending.selectionDiffered;
        c = onTextSelection(pending, cb.rects);
        if (!before && pending.selectionDiffered) differedMask = cb.mask;
      } else {
        c = onVisibleCursor(pending);
      }
    } else if (kn.rule == Rule::FirstCursor) {
      if (cb.t == CUR) { pending.completion = c = Completion::Transition; differedMask = cb.mask; }
    } else {
      if (cb.t == SEL) { pending.completion = c = Completion::Transition; differedMask = cb.mask; }
    }
    if (c != Completion::Pending) completeMove(c, true);
  }

  void completeMove(Completion c, bool inLokPhase) {
    tr(std::string("completed move@") + std::to_string(pendingOwner) + " by " + probe::extend::completionName(c));
    pendingActive = false;
    removeActions(ActionType::Deadline, pendingOwner);
    if (!pendingIsSelect && !kn.flagDisabled) flag.onMoveCompleted(pending);
    if (pendingOwner == OE) {
      eCompletion = c;
      // the select-range completed before its final selection was delivered (ruling 3 Q1 B)
      if (pendingIsSelect) eSelectStale = !selectEndRan || cacheSel != core.selRects();
    } else {
      uCompletion = c;
      uKeyRanAtCompletion = uKeyRan;
      if (c == Completion::Transition || c == Completion::FirstCallback) {
        uStale = !uKeyRan || cacheSel != coreAfterU.selRects() || cacheCaret != coreAfterU.caretRect();
        if (uStale && c == Completion::Transition) uStaleTransition = true;
        if (uStale && c == Completion::FirstCallback) uStaleFirstCallback = true;
      }
      flagAtU = flag.set();
    }
    pageNext(inLokPhase);
  }

  // ---- the page ----
  void pageNext(bool inLokPhase) {
    ++nextItem;
    if (nextItem == 1 && sc.u == 0 && sc.follow == 0) { nextItem = 3; return; }
    if (nextItem == 1 && sc.u == 0) ++nextItem; // straight to the follow-up
    if (nextItem == 2 && sc.follow == 0) { nextItem = 3; return; }
    if (nextItem >= 3) return;
    const int lag = nextItem == 1 ? sc.lagReg : sc.lagReg2;
    schedule(ActionType::Arrive, lag, inLokPhase, nextItem == 2 && previousItemCarriesNoState(), false, nextItem == 1 ? OU : OB);
  }

  // ---- engine: actions ----
  // `lag` = LOK steps between the decision and the landing.  The engine phase
  // of a tick follows that tick's LOK step, so a decision taken during a LOK
  // step (a callback) with lag 0 lands before the next LOK step, as does a
  // decision taken in the engine phase.
  void schedule(ActionType t, int lag, bool inLokPhase, bool boundary, bool whenIdle, int owner) {
    (void)inLokPhase;
    actions.push_back(Action{t, tick + lag, boundary, whenIdle, owner});
  }
  void removeActions(ActionType t, int owner) {
    actions.erase(std::remove_if(actions.begin(), actions.end(),
                                 [&](const Action &a) { return a.type == t && a.owner == owner; }),
                  actions.end());
  }
  bool lokIdle() const { return fifo.empty() && !midFlush; }

  void enginePhase() {
    if (kn.sync) {
      // C: the poll runs only on a tick with no user event pending, and does one thing
      if (!(kn.syncPollMidFlush ? fifo.empty() : lokIdle())) return;
      for (std::size_t i = 0; i < actions.size(); ++i) {
        if (actions[i].readyAt > tick) continue;
        const Action a = actions[i];
        actions.erase(actions.begin() + static_cast<long>(i));
        execute(a);
        return;
      }
      return;
    }
    for (bool progress = true; progress;) {
      progress = false;
      for (std::size_t i = 0; i < actions.size(); ++i) {
        const Action a = actions[i];
        if (a.whenIdle ? !lokIdle() : a.readyAt > tick) continue;
        if (a.boundary && midFlush) continue;
        if (busy && (a.type == ActionType::Arrive || a.type == ActionType::Deadline)) continue;
        actions.erase(actions.begin() + static_cast<long>(i));
        execute(a);
        progress = true;
        break;
      }
    }
  }

  void registerMove(int owner, Key k) {
    pendingActive = true;
    pendingOwner = owner;
    pendingIsSelect = false;
    pending = beginMove(isExtend(k), cacheSel);
    (owner == OU ? uKind : eKind) = pending.kind;
    if (owner == OU) uRegistered = true;
    if (kn.sync) { syncKey(owner, k); syncReply(owner, ReplyFor::Move); return; }
    schedule(ActionType::PostKey, 0, false, true, false, owner);
  }

  // ---- C (SPEC-M3-ordered-commands §8) ----
  // A key inside its call (postEventAsync runs LOKPostAsyncEvent inline under unipoll, lokhelper.cxx:1283-1288).
  void syncKey(int owner, Key k) {
    keyPosted[owner] = keyRan[owner] = true;
    keyChanged = applyKey(core, k);
    if (keyChanged) repaintFrom(owner);
    tr(std::string("C ran key ") + keyName(k) + "@" + std::to_string(owner));
    if (owner == OU) { uKeyRan = true; coreAfterU = core; }
  }
  void syncReply(int owner, ReplyFor what) {
    replyFor = what;
    if (kn.syncReplySamePoll) { syncAnswer(owner); return; }
    schedule(ActionType::Reply, 0, false, false, false, owner);
  }
  void syncAnswer(int owner) {
    (void)owner;
    const ReplyFor what = replyFor;
    replyFor = ReplyFor::None;
    if (cacheSel != core.selRects() || cacheCaret != core.caretRect()) {
      ++forgedReplies;
      tr("FORGED reply: the cache is not core");
    }
    snapSel = cacheSel;
    switch (what) {
    case ReplyFor::Move:
      completeMove(pendingIsSelect ? Completion::FirstCallback : keyChanged ? Completion::Transition : Completion::Readback, false);
      return;
    case ReplyFor::Item: eCompletion = Completion::FirstCallback; pageNext(false); return;
    case ReplyFor::DeleteSelection: completionName = "uno-command-result"; outcome = Outcome::Deleted; nextItem = 3; return;
    case ReplyFor::KeyDelete:
      completionName = keyChanged ? "verified-key-undo" : "verified-boundary-noop";
      outcome = keyChanged ? Outcome::Deleted : Outcome::Noop;
      nextItem = 3;
      return;
    case ReplyFor::Type: completionName = "inserted"; outcome = Outcome::Changed; nextItem = 3; return;
    case ReplyFor::Format: completionName = "uno-command-result"; outcome = Outcome::Changed; nextItem = 3; return;
    case ReplyFor::None: fail("C: a reply with nothing to answer"); return;
    }
  }
  // The user's own Backspace inside its call: Writer deletes the selection, else the unit before the caret.
  void syncKeyBackspace() {
    pendingMaskAtDelete = pendingKeyMask();
    const int before = core.n();
    if (core.nonEmpty()) core.eraseSelection();
    else if (core.pt > 0) { core.units.erase(core.units.begin() + core.pt - 1); --core.pt; }
    deletedUnits = before - core.n();
    keyChanged = deletedUnits > 0;
    if (keyChanged) repaintFrom(OB);
    syncReply(OB, ReplyFor::KeyDelete);
  }

  void postKey(int owner, Key k) {
    fifo.push_back(Ev{true, k, owner});
    keyPosted[owner] = true;
  }

  void execute(const Action &a) {
    static const char *names[] = {"Arrive", "PostKey", "Deadline", "SelectStart", "SelectEnd", "BarrierStart", "BarrierDeadline1", "Verify", "WindowExpiry", "DeleteSelection", "FinishDelete", "TypeChar", "BoldSelection", "Reply"};
    tr(std::string("engine ") + names[static_cast<int>(a.type)] + "@" + std::to_string(a.owner));
    switch (a.type) {
    case ActionType::Arrive:
      if (a.owner == OU) {
        registerMove(OU, static_cast<Key>(sc.u - 1));
      } else if (sc.follow == 1) {
        resolveBackspace();
      } else if (kn.sync) {
        sc.follow == 2 ? typeChar() : boldSelection();
      } else {
        // condition 33: typing and an inline format are synchronous calls that jump the
        // posted-key FIFO exactly as .uno:Delete does; the page consults no snapshot for them
        schedule(sc.follow == 2 ? ActionType::TypeChar : ActionType::BoldSelection, 0, false, true, false, OB);
      }
      return;
    case ActionType::PostKey: {
      const Key k = a.owner == OE ? sc.eKey : static_cast<Key>(sc.u - 1);
      postKey(a.owner, k);
      schedule(ActionType::Deadline, a.owner == OE ? sc.eDeadline : sc.lagDeadline, false, false, false, a.owner);
      return;
    }
    case ActionType::Deadline:
      if (pendingActive && pendingOwner == a.owner) {
        if (!pendingIsSelect) onReadbackDeadline(pending);
        completeMove(Completion::Readback, false);
      }
      return;
    case ActionType::SelectStart: // START, then END (gapSE decides whether a flush runs between)
      core.hasMark = true; core.mk = 1; core.normalize();
      repaintFrom(OE);
      if (sc.gapSE) schedule(ActionType::SelectEnd, 0, false, true, true, OE);
      else execute(Action{ActionType::SelectEnd, tick, true, false, OE});
      return;
    case ActionType::SelectEnd:
      core.pt = 3; core.normalize();
      repaintFrom(OE);
      busy = false;
      selectEndRan = true;
      return;
    case ActionType::BarrierStart: barrierStart(); return;
    case ActionType::BarrierDeadline1: barrierDeadline1(); return;
    case ActionType::Verify: verify(); return;
    case ActionType::WindowExpiry: windowExpiry(); return;
    case ActionType::DeleteSelection: deleteSelection(); return;
    case ActionType::FinishDelete: finishDelete(); return;
    case ActionType::TypeChar: typeChar(); return;
    case ActionType::BoldSelection: boldSelection(); return;
    case ActionType::Reply: syncAnswer(a.owner); return;
    }
  }

  // ---- the earlier operation, at tick 0 ----
  void startEarlier() {
    switch (sc.e) {
    case Earlier::None:
      pageNext(false);
      return;
    case Earlier::InsertCaret: case Earlier::InsertRange: {
      // paste: synchronous, answers `inserted` at once (probe_engine.cpp:3186-3221)
      const int a = core.lo();
      if (core.nonEmpty()) core.eraseSelection();
      core.units.insert(core.units.begin() + a, Unit{'x', 1});
      core.pt = a + 1; core.hasMark = false;
      repaintFrom(OE);
      if (kn.sync) { syncReply(OE, ReplyFor::Item); return; }
      eCompletion = Completion::FirstCallback;
      pageNext(false);
      return;
    }
    case Earlier::RbMove:
      registerMove(OE, sc.eKey);
      return;
    case Earlier::UnoDelete: case Earlier::UnoUndo: case Earlier::UnoFormat: {
      // dispatch with a listener: synchronous; the result is queued (init.cxx:5106)
      bool changed = false;
      if (sc.e == Earlier::UnoDelete) {
        if (core.nonEmpty()) { core.eraseSelection(); changed = true; }
        else if (core.pt < core.n()) { core.units.erase(core.units.begin() + core.pt); changed = true; }
      } else if (sc.e == Earlier::UnoUndo) {
        core.units.insert(core.units.begin() + core.pt, Unit{'z', 1});
        core.hasMark = true; core.mk = core.pt; core.pt += 1; core.normalize();
        changed = true;
      }
      if (changed) repaintFrom(OE);
      queueResult(OE);
      previousWasDelete = sc.e == Earlier::UnoDelete;
      if (kn.sync) syncReply(OE, ReplyFor::Item);
      return;
    }
    case Earlier::Select3:
      // the product's select-range: pending on TEXT_SELECTION, readback armed;
      // RESET, START, END as three LOK calls (probe_engine.cpp:5555-5625)
      pendingActive = true; pendingOwner = OE; pendingIsSelect = true;
      if (kn.sync) {
        // C: RESET, START, END inside one command; no flush can run between them (§5.7 rule 1)
        core.hasMark = false; core.pt = 2; repaintFrom(OE);
        core.hasMark = true; core.mk = 1; core.normalize(); repaintFrom(OE);
        core.pt = 3; core.normalize(); repaintFrom(OE);
        selectEndRan = true;
        syncReply(OE, ReplyFor::Move);
        return;
      }
      busy = true;
      schedule(ActionType::Deadline, sc.eDeadline, false, false, false, OE);
      core.hasMark = false; core.pt = 2;
      repaintFrom(OE);
      if (sc.gapRS) schedule(ActionType::SelectStart, 0, false, true, true, OE);
      else execute(Action{ActionType::SelectStart, tick, true, false, OE});
      return;
    }
  }

  // ---- the delete (12.4: the form is bound when the item runs) ----
  // The session writes its snapshot from the previous item's result, or, when
  // that result carries no state (the synchronous insert), from getState(),
  // which reads the selection actively (editor-session.js:287-311;
  // probe_engine.cpp:5701-5721).  Every other item here answers with a state.
  bool previousItemCarriesNoState() const {
    return sc.u == 0 && (sc.e == Earlier::InsertCaret || sc.e == Earlier::InsertRange);
  }
  void resolveBackspace() {
    const bool snapshotRange = previousItemCarriesNoState() ? core.nonEmpty() : !(kn.sync ? snapSel : cacheSel).empty();
    bool selectionForm = snapshotRange;
    if (kn.resolverRuleA && previousWasDelete) selectionForm = false;
    deleteSelectionForm = selectionForm;
    if (kn.sync) { selectionForm ? deleteSelection() : syncKeyBackspace(); return; }
    schedule(selectionForm ? ActionType::DeleteSelection : ActionType::BarrierStart, 0, false, true, false, OB);
  }

  // condition 33, shape 1: paste, synchronous, answers `inserted` at once (probe_engine.cpp:3186-3221)
  void typeChar() {
    pendingMaskAtDelete = pendingKeyMask();
    flagAtDelete = flag.set();
    const int a = core.lo();
    if (core.nonEmpty()) core.eraseSelection();
    core.units.insert(core.units.begin() + a, Unit{'x', 1});
    core.pt = a + 1; core.hasMark = false;
    repaintFrom(OB);
    if (kn.sync) { syncReply(OB, ReplyFor::Type); return; }
    outcome = Outcome::Changed;
    completionName = "inserted";
    nextItem = 3;
  }

  // condition 33, shape 2: .uno:Bold with a listener, synchronous (unoctitm.cxx:655-657); the
  // result is queued and the completion is at that result.  The model's rectangles do not change
  // width with bold, so the flush carries only the RESULT (natively a bolder line may re-send the
  // selection rectangles; see the README's limits).
  void boldSelection() {
    pendingMaskAtDelete = pendingKeyMask();
    flagAtDelete = flag.set();
    if (core.nonEmpty())
      for (int i = core.lo(); i < core.hi(); ++i) core.units[i].bold = true;
    queueResult(OB);
    if (kn.sync) syncReply(OB, ReplyFor::Format);
  }

  void refuse(const char *stageN, const char *site) {
    tr(std::string("REFUSED ") + stageN + " at " + site);
    outcome = Outcome::Refused;
    stageName = stageN;
    refusalSite = site;
    stage = Stage::Finished;
    nextItem = 3;
  }

  void deleteSelection() {
    pendingMaskAtDelete = pendingKeyMask();
    flagAtDelete = flag.set();
    if (!kn.flagDisabled && judgeDeleteSelection(flag.set())) { refuse(kPriorKeyUnconfirmed.name, "delete-selection"); return; }
    if (cacheSel.empty()) { refuse("gesture", "gate"); return; } // the gate reads the cache (5285-5300)
    // .uno:Delete, synchronous, on whatever core has selected NOW
    const std::vector<Rect> coreNow = core.selRects();
    deleteSelOnOtherRange = coreNow != cacheSel;
    if (core.nonEmpty()) deletedUnits = core.eraseSelection();
    else if (core.pt < core.n()) { core.units.erase(core.units.begin() + core.pt); deletedUnits = 1; }
    repaintFrom(OB);
    queueResult(OB);
    if (kn.sync) syncReply(OB, ReplyFor::DeleteSelection);
  }

  void barrierStart() {
    pendingMaskAtDelete = pendingKeyMask();
    flagAtDelete = flag.set();
    if (core.nonEmpty() || !cacheSel.empty()) { refuse("EDITOR_STATE_UNAVAILABLE", "barrier-start"); return; }
    stage = Stage::AwaitingUnit;
    postKey(OK1, Key::ShiftLeft);
    schedule(ActionType::BarrierDeadline1, sc.lagB1, false, true, false, OB);
  }

  void barrierSel() {
    if (stage == Stage::AwaitingUnit) {
      stage = Stage::UnitQueued;
      schedule(ActionType::Verify, sc.lagV, true, true, false, OB);
    } else if (stage == Stage::AwaitingDelete && seq > dispatchSeq && cacheSel.empty()) {
      collapseSeen = true;
      maybeQueueFinish();
    }
  }

  void maybeQueueFinish() {
    if (ackSeen && collapseSeen && !finishQueued) {
      finishQueued = true;
      schedule(ActionType::FinishDelete, 0, true, true, false, OB);
    }
  }

  void verify() {
    if (stage != Stage::UnitQueued) return;
    const bool geometrySafe = cacheSel.size() == 1;
    const bool textSafe = core.nonEmpty();
    if (textSafe && !geometrySafe) { stage = Stage::AwaitingUnit; return; }
    if (!geometrySafe || !textSafe) { refuse("unit-unsafe", "verify"); return; }
    const std::vector<std::uint32_t> cps = core.selText();
    const bool flagged = kn.alwaysOneCodePoint || (!kn.flagDisabled && flag.set());
    if (judgeBarrierUnit(flagged, cps)) { refuse(kPriorKeyUnconfirmed.name, "verify"); return; }
    flaggedAdmit = !kn.flagDisabled && flag.set();
    admittedBeforeK1Ran = !keyRan[OK1];
    // .uno:SwBackspace, synchronous, on the selection the barrier read
    deletedUnits = core.eraseSelection();
    repaintFrom(OB);
    queueResult(OB);
    stage = Stage::AwaitingDelete;
    dispatchSeq = seq;
  }

  void barrierDeadline1() {
    if (stage != Stage::AwaitingUnit) return;
    if (!core.nonEmpty() && cacheSel.empty()) {
      schedule(ActionType::WindowExpiry, 0, false, true, true, OB); // 10.5: one more MergeStepDeadlineMs
      return;
    }
    refuse("EDITOR_STATE_UNAVAILABLE", "deadline-sees-selection"); // selection visible without its typed callback (today)
  }

  void windowExpiry() {
    if (stage != Stage::AwaitingUnit) return;
    if (core.nonEmpty()) { refuse("unit-late", "window"); return; }
    if (!kn.flagDisabled && judgeWindowExpiry(flag.set())) { refuse(kPriorKeyUnconfirmed.name, "window"); return; }
    noopWithKeyPending = pendingKeyMask() != 0;
    outcome = Outcome::Noop;
    completionName = "verified-boundary-noop";
    stage = Stage::Finished;
    nextItem = 3;
  }

  void finishDelete() {
    if (core.nonEmpty() || !cacheSel.empty()) { refuse("MUTATION_OUTCOME_UNKNOWN", "finish"); return; }
    outcome = Outcome::Deleted;
    completionName = "verified-selection-delete";
    if (flaggedAdmit) flag.onFlaggedDeleteProved();
    stage = Stage::Finished;
    nextItem = 3;
  }

  void go() {
    startEarlier();
    for (int guard = 0;; ++guard) {
      enginePhase();
      if (lokIdle() && actions.empty()) break;
      if (guard > 400) { guardHit = true; break; }
      ++tick;
      lokStep();
    }
  }
};

// ---- the population's classes, by mechanism ----------------------------------------

std::string staleClass(const Run &r) {
  const Scenario &s = r.sc;
  const int m = r.differedMask;
  if (m < 0) return "UNDECLARED: no differing selection recorded";
  if (m & (1 << OU)) return "UNDECLARED: the move's own flush";
  if (m & ((1 << OK1) | (1 << OB))) return "UNDECLARED: a later operation's flush";
  if (!(m & (1 << OE))) return "UNDECLARED: a flush nobody owns";
  switch (s.e) {
  case Earlier::InsertRange: return "insert over a selection: synchronous reply, flush still queued";
  case Earlier::RbMove:
    if (r.eCompletion == Completion::Readback)
      return isExtend(s.eKey) ? "readback-completed extend: own TEXT_SELECTION late"
                              : "readback-completed plain move on a range: own TEXT_SELECTION late";
    return "UNDECLARED: a callback-completed move's flush";
  case Earlier::UnoDelete: case Earlier::UnoUndo: return "uno-command-result ahead of the same flush's SEL/CUR";
  case Earlier::Select3: return "select-range: a flush between its three calls";
  default: return std::string("UNDECLARED: ") + earlierName(s.e);
  }
}

const std::vector<std::string> kDeclaredClasses = {
    "insert over a selection: synchronous reply, flush still queued",
    "readback-completed extend: own TEXT_SELECTION late",
    "readback-completed plain move on a range: own TEXT_SELECTION late",
    "uno-command-result ahead of the same flush's SEL/CUR",
    "select-range: a flush between its three calls",
};

// ---- the generator ------------------------------------------------------------------

// Ruling 4 condition 32: v20 offers plain caret-start moves only (no extend, no range-start move).
// The key set here removes the Shift keys; a plain move that the engine would classify as
// range-start (the cache holds a range at dispatch) is excluded by the sweeps after the run,
// because that classification is the run's, not the scenario's.
enum class KeySet { Full, V20 };

template <class F> void forEachScenario(int followMode, KeySet keys, F &&f) {
  static const int lagRegs[] = {0, 1, 2, 3, 4, 5};
  static const int lagDeadlines[] = {0, 1, 2, 3, 4, 6, 9};
  const std::vector<Key> moveKeys = keys == KeySet::Full ? std::vector<Key>{Key::ShiftLeft, Key::ShiftRight, Key::Left, Key::Right}
                                                         : std::vector<Key>{Key::Left, Key::Right};
  const std::vector<int> userKeys = keys == KeySet::Full ? std::vector<int>{0, 1, 2, 3, 4, 5}
                                                         : std::vector<int>{0, 1 + static_cast<int>(Key::Left), 1 + static_cast<int>(Key::Right)};
  for (int text = 0; text < 2; ++text)
    for (int shape = 0; shape < 8; ++shape)
      for (int e = 0; e < 8; ++e) {
        const Earlier earlier = static_cast<Earlier>(e);
        const bool range = shape >= 5;
        if ((earlier == Earlier::InsertRange || earlier == Earlier::UnoDelete) && !range) continue;
        if ((earlier == Earlier::InsertCaret || earlier == Earlier::UnoUndo) && range) continue;
        std::vector<Scenario> variants;
        Scenario base{text, shape, earlier, Key::Left, 0, 0, 0, 0, 0, 0, false, 0, 0, 0, 0};
        if (earlier == Earlier::RbMove) {
          for (Key k : moveKeys)
            for (int d : {0, 1, 2, 3}) { Scenario v = base; v.eKey = k; v.eDeadline = d; variants.push_back(v); }
        } else if (earlier == Earlier::Select3) {
          for (int rs = 0; rs < 2; ++rs)
            for (int se = 0; se < 2; ++se)
              for (int d : {1, 9}) { Scenario v = base; v.gapRS = rs; v.gapSE = se; v.eDeadline = d; variants.push_back(v); }
        } else {
          variants.push_back(base);
        }
        for (Scenario v : variants)
          for (int u : userKeys)
            for (int lagReg : lagRegs) {
              if (earlier == Earlier::None && lagReg) continue; // no earlier completion to lag behind
              if (u == 0 && lagReg) continue;
              for (int lagDeadline : lagDeadlines) {
                if (u == 0 && lagDeadline) continue;
                Scenario sc = v;
                sc.u = u; sc.lagReg = lagReg; sc.lagDeadline = lagDeadline;
                if (followMode == 0) { f(sc); continue; }
                sc.follow = followMode;
                sc.backspace = followMode == 1;
                if (followMode != 1) {
                  for (int lagReg2 : {0, 1, 2, 3}) { sc.lagReg2 = lagReg2; f(sc); }
                  continue;
                }
                for (int lagReg2 : {0, 1, 2, 3})
                  for (int lagB1 : {0, 1, 9})
                    for (int lagV : {0, 1}) {
                      sc.lagReg2 = lagReg2; sc.lagB1 = lagB1; sc.lagV = lagV;
                      f(sc);
                    }
              }
            }
      }
}

// ---- phase 1: rule (a) and L-extend-prior-flush ------------------------------------------

struct Phase1 {
  long runs = 0, transition = 0, firstCallback = 0, readback = 0, readbackKeyPending = 0, readbackFlushLate = 0;
  long stale = 0, staleCaretPlain = 0, undeclared = 0, guard = 0;
  std::map<std::string, long> byClass;
  std::map<std::string, std::string> firstOfClass;
  std::map<Earlier, long> staleByEarlier, runsByEarlier;
  std::string firstUndeclared;
  long printedLines = 0;
};

Phase1 sweep1(const Knobs &kn, bool print, const std::set<std::string> *onlyPrintClasses = nullptr) {
  Phase1 t;
  // one line per sequence-minus-deadline-lag, listing the deadline lags on which it is stale
  std::string lastKey;
  std::string lastLine;
  std::vector<int> staleLags;
  const auto flushLine = [&] {
    if (lastKey.empty() || staleLags.empty()) return;
    std::string lags;
    for (int l : staleLags) lags += (lags.empty() ? "" : ",") + std::to_string(l);
    if (print) {
      std::printf("%s deadline-lags={%s}\n", lastLine.c_str(), lags.c_str());
      ++t.printedLines;
    }
  };
  forEachScenario(0, KeySet::Full, [&](const Scenario &sc) {
    Run r(sc, kn);
    r.go();
    ++t.runs;
    ++t.runsByEarlier[sc.e];
    if (r.guardHit) ++t.guard;
    if (sc.u == 0) return;
    switch (r.uCompletion) {
    case Completion::Transition: ++t.transition; break;
    case Completion::FirstCallback: ++t.firstCallback; break;
    case Completion::Readback:
      ++t.readback;
      if (!r.uKeyRanAtCompletion) ++t.readbackKeyPending; else ++t.readbackFlushLate;
      break;
    case Completion::Pending: break;
    }
    if (r.uStaleFirstCallback) ++t.staleCaretPlain;
    Scenario key = sc;
    key.lagDeadline = -1;
    const std::string k = describe(key);
    if (k != lastKey) {
      flushLine();
      lastKey = k;
      staleLags.clear();
      lastLine.clear();
    }
    if (r.uStaleTransition) {
      ++t.stale;
      ++t.staleByEarlier[sc.e];
      const std::string cls = staleClass(r);
      ++t.byClass[cls];
      if (!t.firstOfClass.count(cls)) t.firstOfClass[cls] = describe(sc);
      if (cls.rfind("UNDECLARED", 0) == 0) {
        ++t.undeclared;
        if (t.firstUndeclared.empty()) t.firstUndeclared = cls + " | " + describe(sc);
      }
      if (!onlyPrintClasses || onlyPrintClasses->count(cls)) {
        staleLags.push_back(sc.lagDeadline);
        lastLine = "L-extend-prior-flush | " + cls + " | " + k;
      }
    }
  });
  flushLine();
  return t;
}

// ---- phase 2: the flag ---------------------------------------------------------------------

struct Phase2 {
  long runs = 0, refused = 0, deleted = 0, noop = 0, undecided = 0, guard = 0, excludedRangeStart = 0;
  long writerEqual = 0, writerDiffers = 0;
  std::map<std::string, long> refusedBy, refusedSite, deletedBy, writerDiffersBy;
  // the spec's three "never"s
  long selDeleteNotOne = 0, deleteSelOtherRange = 0, noopKeyPending = 0;
  // flagged, with an extend key still queued at the delete's dispatch
  long fp = 0, fpRefusedDeleteSelection = 0, fpRefusedVerify = 0, fpRefusedWindow = 0, fpRefusedToday = 0;
  long fpAdmittedEqual = 0, fpAdmittedShrink = 0, fpAdmittedOther = 0;
  // an extend key still queued with the flag clear: only after a forged completion
  long forged = 0, forgedWithoutStale = 0, forgedWrongDelete = 0, plainStale = 0, plainStaleWrongDelete = 0;
  // a range-start plain move still queued (12.2 sets no flag for it)
  long rangePlainPending = 0, rangePlainPendingDiffers = 0;
  long notK1 = 0, notK1Wedged = 0, notK1Completed = 0, notK1Differs = 0;
  long selectStale = 0, selectStaleWrongDelete = 0;
  // today's refusal when the 250 ms read lands between K1 and its flush
  long deadlineSeesSelection = 0;
  // red-case counters
  long twoUnitDelete = 0, silentNoop = 0, falseRefusal = 0;
  // liveness
  long silentEnd = 0, silentEndDeletedOne = 0;
  long rangeBackspace = 0, rangeBackspaceSelectionForm = 0;
  long plainPending = 0, plainPendingDeletedWriter = 0;
  long flaggedAdmitted = 0, flaggedAdmittedCleared = 0;
  std::map<std::string, std::string> first;
  void note(const std::string &k, const Scenario &sc) { if (!first.count(k)) first[k] = describe(sc); }
};

// `population` (condition 32): print every Writer-divergent sequence, grouped by the sequence
// minus the Backspace's timing, with the number of divergent timings out of 24.
Phase2 sweep2(const Knobs &kn, KeySet keys = KeySet::Full, bool population = false) {
  Phase2 t;
  std::vector<std::string> order;
  std::map<std::string, std::pair<std::string, long>> grouped;
  forEachScenario(1, keys, [&](const Scenario &sc) {
    Run r(sc, kn);
    r.go();
    if (keys == KeySet::V20 && ((sc.e == Earlier::RbMove && r.eKind == MoveKind::ExtendOrRangeStart) ||
                                (sc.u && r.uKind == MoveKind::ExtendOrRangeStart))) {
      ++t.excludedRangeStart; // not offered on v20: the manifest's moves are collapsed-only
      return;
    }
    ++t.runs;
    if (r.guardHit) ++t.guard;
    Scenario noB = sc;
    noB.backspace = false;
    noB.follow = 0;
    const std::string writerBefore = writerText(noB), writer = writerText(sc);
    const long writerDeleted = static_cast<long>(writerBefore.size()) - static_cast<long>(writer.size());
    const bool equal = r.core.text() == writer;
    const Key uKey = static_cast<Key>(sc.u ? sc.u - 1 : 0);
    const bool uPending = sc.u && (r.pendingMaskAtDelete & (1 << OU));
    const bool ePending = sc.e == Earlier::RbMove && (r.pendingMaskAtDelete & (1 << OE));
    const bool extendPending = (uPending && isExtend(uKey)) || (ePending && isExtend(sc.eKey));
    // K1 shrank a pending forward extension of two or more units to one code point: one unit deleted
    // where Writer deletes the whole extension (Shift+End mid-line, or two Shift+Right stacked)
    const bool shrinkShape = r.outcome == Outcome::Deleted && r.deletedUnits == 1 && writerDeleted >= 2;
    // behind a forged rule-(a) completion (phase 1's population) the flag is clear and the page's
    // snapshot is wrong: ruling 3 names every wrong deletion here as the residual.  A caret-start
    // plain move keeps today's rule (10.1) and today's rule completes on an earlier operation's
    // late TEXT_SELECTION as well (084's shape): the same wrong snapshot, reported separately.
    const bool plainRangePending = uPending && !isExtend(uKey) && r.uKind == MoveKind::ExtendOrRangeStart;
    // a range-start plain move answered by the readback: its reply and the cache still say "range" while
    // its key is queued or its SEL0 undelivered; 12.2 sets no flag for it
    const bool rangePlainReadback =
        (sc.u && !isExtend(uKey) && r.uKind == MoveKind::ExtendOrRangeStart && r.uCompletion == Completion::Readback) ||
        (sc.e == Earlier::RbMove && !isExtend(sc.eKey) && r.eKind == MoveKind::ExtendOrRangeStart && r.eCompletion == Completion::Readback);
    const bool residualA = r.uStaleTransition, residualPlain = r.uStaleFirstCallback;
    const bool selectStale = sc.e == Earlier::Select3 && r.eSelectStale;
    const bool residual = residualA || residualPlain || rangePlainReadback || selectStale;
    const bool prior = r.stageName == kPriorKeyUnconfirmed.name;
    switch (r.outcome) {
    case Outcome::Refused: ++t.refused; ++t.refusedBy[r.stageName]; ++t.refusedSite[r.refusalSite]; break;
    case Outcome::Deleted: ++t.deleted; ++t.deletedBy[r.completionName]; break;
    case Outcome::Noop: ++t.noop; break;
    case Outcome::None: ++t.undecided; t.note("undecided", sc); break;
    case Outcome::Changed: break; // typing and formats are sweep3's; a Backspace never answers Changed
    }
    if (r.refusalSite == "deadline-sees-selection") ++t.deadlineSeesSelection;
    std::string kind;
    if (r.outcome == Outcome::Refused) {
      if (r.core.text() != writerBefore) { ++t.writerDiffers; kind = "refused but the text changed"; }
      else ++t.writerEqual;
    } else if (equal) {
      ++t.writerEqual;
    } else {
      ++t.writerDiffers;
      kind = r.outcome == Outcome::Noop ? "noop" : r.completionName;
      if (residualA) kind += " / behind a forged rule-(a) completion (the residual)";
      else if (residualPlain) kind += " / behind a stale first-callback completion (today's rule for caret-start plain moves)";
      else if (extendPending && r.flagAtDelete) kind += shrinkShape ? " / multi-unit forward extend pending, flagged, K1 shrank it" : " / extend pending, flagged";
      else if (extendPending) kind += " / extend pending, flag clear";
      else if (rangePlainReadback) kind += " / behind a range-start plain move answered by the readback (12.2 sets no flag for plain moves)";
      else if (selectStale) kind += " / behind a select-range completed before its final selection (ruling 3 Q1 B)";
      else kind += " / no key pending";
    }
    if (!kind.empty()) {
      ++t.writerDiffersBy[kind];
      t.note("differs: " + kind, sc);
      if (population) {
        Scenario g = sc;
        g.lagReg2 = g.lagB1 = g.lagV = 0;
        const std::string key = describe(g);
        if (!grouped.count(key)) { order.push_back(key); grouped[key] = {kind, 0}; }
        ++grouped[key].second;
      }
    }
    // the spec's three "never"s, outside the residual
    if (!residual) {
      if (r.outcome == Outcome::Deleted && r.completionName == "verified-selection-delete" && r.deletedUnits != 1) {
        ++t.selDeleteNotOne; t.note("selection-delete-not-one-unit", sc);
      }
      if (r.deleteSelOnOtherRange) { ++t.deleteSelOtherRange; t.note("delete-selection-other-range", sc); }
      if (r.noopWithKeyPending) { ++t.noopKeyPending; t.note("noop-with-key-pending", sc); }
      // red-case counters: the stacked two-unit delete (Writer deletes one) and the silent no-op
      if (r.outcome == Outcome::Deleted && r.deletedUnits == 2 && writerDeleted == 1) { ++t.twoUnitDelete; t.note("two-unit-delete", sc); }
      if (r.outcome == Outcome::Noop && writerDeleted >= 1) { ++t.silentNoop; t.note("silent-noop", sc); }
    }
    // the verifier read a selection before K1 had run: an extend's late flush, not K1's
    if (r.admittedBeforeK1Ran) {
      ++t.notK1;
      if (r.outcome == Outcome::None) ++t.notK1Wedged; else ++t.notK1Completed;
      if (r.outcome != Outcome::None && !equal) ++t.notK1Differs;
      t.note("admitted-before-K1-ran", sc);
    }
    if (kn.alwaysOneCodePoint && prior && !r.flagAtDelete && !r.pendingMaskAtDelete && sc.e == Earlier::None) {
      ++t.falseRefusal; t.note("false-refusal", sc);
    }
    // flagged with an extend pending
    if (extendPending && r.flagAtDelete && !residual) {
      ++t.fp;
      if (r.outcome == Outcome::Refused) {
        if (prior && r.refusalSite == "delete-selection") ++t.fpRefusedDeleteSelection;
        else if (prior && r.refusalSite == "verify") ++t.fpRefusedVerify;
        else if (prior && r.refusalSite == "window") ++t.fpRefusedWindow;
        else ++t.fpRefusedToday;
      } else if (equal) {
        ++t.fpAdmittedEqual; t.note("flagged-admitted-writer-equal", sc);
      } else if (shrinkShape) {
        ++t.fpAdmittedShrink; t.note("flagged-admitted-shrink", sc);
      } else {
        ++t.fpAdmittedOther; t.note("flagged-admitted-other", sc);
      }
    }
    if (extendPending && !r.flagAtDelete && !kn.flagDisabled && !residual) {
      ++t.forgedWithoutStale; t.note("extend-pending-unflagged-without-stale", sc);
    }
    if (residualA) {
      ++t.forged;
      if (r.outcome != Outcome::Refused && !equal) { ++t.forgedWrongDelete; t.note("forged-residual-wrong-delete", sc); }
    } else if (residualPlain) {
      ++t.plainStale;
      if (r.outcome != Outcome::Refused && !equal) { ++t.plainStaleWrongDelete; t.note("plain-stale-wrong-delete", sc); }
    }
    if (selectStale && !residualA && !residualPlain && !rangePlainReadback) {
      ++t.selectStale;
      if (r.outcome != Outcome::Refused && !equal) { ++t.selectStaleWrongDelete; t.note("select-stale-wrong-delete", sc); }
    }
    if (rangePlainReadback && !residualA && !residualPlain) {
      ++t.rangePlainPending;
      if (r.outcome != Outcome::Refused && !equal) { ++t.rangePlainPendingDiffers; t.note("range-plain-pending-differs", sc); }
    }
    (void)plainRangePending;
    // liveness; the 250 ms read between K1 and its flush is today's refusal and is counted above
    if (sc.e == Earlier::None && sc.u == 1 + static_cast<int>(Key::ShiftEnd) && sc.shape == 4 && sc.lagB1 != 1) {
      ++t.silentEnd;
      if (r.outcome == Outcome::Deleted && r.deletedUnits == 1 && equal && r.flagAtDelete) ++t.silentEndDeletedOne;
      else t.note("silent-end-miss", sc);
    }
    if (sc.e == Earlier::None && sc.u == 0 && sc.shape >= 5) {
      ++t.rangeBackspace;
      if (r.deleteSelectionForm && r.outcome == Outcome::Deleted && equal) ++t.rangeBackspaceSelectionForm;
      else t.note("range-backspace-miss", sc);
    }
    if (sc.e == Earlier::None && sc.shape <= 4 && sc.u && !isExtend(uKey) && uPending && sc.lagB1 != 1) {
      ++t.plainPending;
      // at the document start Writer's Backspace deletes nothing and C's no-op is the right answer
      if ((r.outcome == Outcome::Deleted || r.outcome == Outcome::Noop) && equal) ++t.plainPendingDeletedWriter;
      else t.note("plain-pending-miss", sc);
    }
    if (r.flaggedAdmit && r.outcome == Outcome::Deleted) {
      ++t.flaggedAdmitted;
      if (!r.flag.set()) ++t.flaggedAdmittedCleared;
    }
  });
  if (population) {
    std::printf("== condition 32: the Writer-divergent population, v20's keys only; one line per sequence minus the Backspace's timing ==\n");
    for (const std::string &key : order)
      std::printf("137 | %s | %s | divergent-timings=%ld/24\n", grouped[key].first.c_str(), key.c_str(), grouped[key].second);
    std::printf("== end of population (%zu lines) ==\n", order.size());
  }
  return t;
}

// ---- condition 33: typing and an inline format behind a pending key (reported, not ruled) ----

struct Phase3 {
  long runs = 0, equal = 0, differs = 0, excludedRangeStart = 0, guard = 0;
  std::map<std::string, long> byKind;
  std::map<std::string, std::string> first;
};

Phase3 sweep3(const Knobs &kn, KeySet keys, int followMode) {
  Phase3 t;
  forEachScenario(followMode, keys, [&](const Scenario &sc) {
    Run r(sc, kn);
    r.go();
    if (keys == KeySet::V20 && ((sc.e == Earlier::RbMove && r.eKind == MoveKind::ExtendOrRangeStart) ||
                                (sc.u && r.uKind == MoveKind::ExtendOrRangeStart))) {
      ++t.excludedRangeStart;
      return;
    }
    ++t.runs;
    if (r.guardHit) ++t.guard;
    const bool equal = r.core.text() == writerText(sc);
    if (equal) { ++t.equal; return; }
    ++t.differs;
    const Key uKey = static_cast<Key>(sc.u ? sc.u - 1 : 0);
    std::string kind = followMode == 2 ? "typing" : "inline format";
    if (r.outcome != Outcome::Changed) kind += " (never answered)";
    if (r.pendingMaskAtDelete & (1 << OU)) kind += std::string(" behind the user's queued ") + (isExtend(uKey) ? "extend" : "plain move");
    else if (r.pendingMaskAtDelete & (1 << OE)) kind += std::string(" behind the earlier queued ") + (isExtend(sc.eKey) ? "extend" : "plain move");
    else kind += " with no key queued";
    if (sc.e == Earlier::Select3 && r.eSelectStale && !(r.pendingMaskAtDelete)) kind += " (select-range completed early; its END still to run)";
    ++t.byKind[kind];
    if (!t.first.count(kind)) t.first[kind] = describe(sc);
  });
  return t;
}

// ---- SPEC-M3-ordered-commands §8: the synchronous-key mode (C) ----
// Writer-divergent here is the whole end state (text, caret and mark), not the text alone.

struct PhaseC {
  long runs = 0, excludedRangeStart = 0, guard = 0, differs = 0, forged = 0, stale = 0, undecided = 0, refused = 0;
  std::map<std::string, long> byCompletion;
  std::map<Earlier, long> runsByEarlier;
  std::map<std::string, std::string> first;
};

PhaseC sweepC(const Knobs &kn, KeySet keys, int followMode) {
  PhaseC t;
  forEachScenario(followMode, keys, [&](const Scenario &sc) {
    Run r(sc, kn);
    r.go();
    if (keys == KeySet::V20 && ((sc.e == Earlier::RbMove && r.eKind == MoveKind::ExtendOrRangeStart) ||
                                (sc.u && r.uKind == MoveKind::ExtendOrRangeStart))) {
      ++t.excludedRangeStart;
      return;
    }
    ++t.runs;
    ++t.runsByEarlier[sc.e];
    if (r.guardHit) ++t.guard;
    const auto note = [&](const char *k) { if (!t.first.count(k)) t.first[k] = describe(sc); };
    if (r.forgedReplies) { ++t.forged; note("forged reply"); }
    if (r.uStale) { ++t.stale; note("stale U completion"); }
    if (followMode && r.outcome == Outcome::None) { ++t.undecided; note("never answered"); }
    if (r.outcome == Outcome::Refused) { ++t.refused; note("refused"); }
    if (!(r.core == writerCore(sc))) { ++t.differs; note("Writer-divergent"); }
    if (followMode) ++t.byCompletion[r.completionName.empty() ? std::string("(none)") : r.completionName];
    else if (sc.u) ++t.byCompletion[std::string("move: ") + probe::extend::completionName(r.uCompletion)];
  });
  return t;
}

void reportC(const char *name, const PhaseC &t) {
  std::printf("%-44s runs=%ld writerDiffers=%ld forged=%ld staleU=%ld refused=%ld undecided=%ld excludedRangeStart=%ld guard=%ld\n",
              name, t.runs, t.differs, t.forged, t.stale, t.refused, t.undecided, t.excludedRangeStart, t.guard);
  std::printf("    by earlier operation:");
  for (const auto &[e, n] : t.runsByEarlier) std::printf(" %s=%ld", earlierName(e), n);
  std::printf("\n    completions:");
  for (const auto &[c, n] : t.byCompletion) std::printf(" %s=%ld", c.c_str(), n);
  std::printf("\n");
  for (const auto &[k, v] : t.first) std::printf("    first %-20s %s\n", k.c_str(), v.c_str());
}

void report3(const char *name, const Phase3 &t) {
  std::printf("%-44s runs=%ld writerEqual=%ld writerDiffers=%ld excludedRangeStart=%ld guard=%ld\n",
              name, t.runs, t.equal, t.differs, t.excludedRangeStart, t.guard);
  for (const auto &[k, n] : t.byKind) std::printf("    differs %7ld  %s\n        first: %s\n", n, k.c_str(), t.first.at(k).c_str());
}

void report1(const char *name, const Phase1 &t) {
  std::printf("%-44s runs=%ld transition=%ld firstCallback=%ld readback=%ld(keyPending=%ld flushLate=%ld) stale=%ld staleCaretPlain=%ld undeclared=%ld guard=%ld\n",
              name, t.runs, t.transition, t.firstCallback, t.readback, t.readbackKeyPending, t.readbackFlushLate,
              t.stale, t.staleCaretPlain, t.undeclared, t.guard);
  std::printf("    generated, by earlier operation:");
  for (const auto &[e, n] : t.runsByEarlier) std::printf(" %s=%ld", earlierName(e), n);
  std::printf("\n");
  for (const auto &[cls, n] : t.byClass)
    std::printf("    %6ld  %s\n        first: %s\n", n, cls.c_str(), t.firstOfClass.at(cls).c_str());
}

void report2(const char *name, const Phase2 &t) {
  std::printf("%-44s runs=%ld refused=%ld deleted=%ld noop=%ld undecided=%ld writerEqual=%ld writerDiffers=%ld excludedRangeStart=%ld guard=%ld\n",
              name, t.runs, t.refused, t.deleted, t.noop, t.undecided, t.writerEqual, t.writerDiffers, t.excludedRangeStart, t.guard);
  for (const auto &[k, n] : t.refusedBy) std::printf("    refused %7ld  stage %s\n", n, k.c_str());
  for (const auto &[k, n] : t.refusedSite) std::printf("    refused %7ld  at %s\n", n, k.c_str());
  for (const auto &[k, n] : t.deletedBy) std::printf("    deleted %7ld  %s\n", n, k.c_str());
  for (const auto &[k, n] : t.writerDiffersBy) std::printf("    differs %7ld  %s\n", n, k.c_str());
  std::printf("    never: selection-delete-not-one-unit=%ld delete-selection-other-range=%ld noop-with-key-pending=%ld\n",
              t.selDeleteNotOne, t.deleteSelOtherRange, t.noopKeyPending);
  std::printf("    flagged, extend pending: %ld = refused at delete-selection %ld + at verify %ld + at window %ld + today's refusals %ld + admitted Writer-equal %ld + admitted shrink %ld + admitted other %ld\n",
              t.fp, t.fpRefusedDeleteSelection, t.fpRefusedVerify, t.fpRefusedWindow, t.fpRefusedToday,
              t.fpAdmittedEqual, t.fpAdmittedShrink, t.fpAdmittedOther);
  std::printf("    behind a forged rule-(a) completion: %ld (wrong deletes: %ld); behind a stale first-callback completion: %ld (wrong deletes: %ld); extend pending with the flag clear and no forged completion: %ld; behind a readback-answered range-start plain move: %ld (Writer-divergent: %ld); deadline-sees-selection: %ld\n",
              t.forged, t.forgedWrongDelete, t.plainStale, t.plainStaleWrongDelete, t.forgedWithoutStale, t.rangePlainPending, t.rangePlainPendingDiffers, t.deadlineSeesSelection);
  std::printf("    verifier admitted before K1 ran (not K1's selection): %ld = wedged (no collapse ever) %ld + completed %ld (Writer-divergent %ld); behind an early-completed select-range: %ld (wrong deletes: %ld)\n",
              t.notK1, t.notK1Wedged, t.notK1Completed, t.notK1Differs, t.selectStale, t.selectStaleWrongDelete);
  std::printf("    red counters: two-unit-delete=%ld silent-noop=%ld false-refusal=%ld\n", t.twoUnitDelete, t.silentNoop, t.falseRefusal);
  std::printf("    liveness: silent Shift+End then Backspace %ld/%ld; range then Backspace delete-selection %ld/%ld; pending plain move then Backspace Writer-equal %ld/%ld; flagged one-code-point admitted %ld (flag cleared after %ld)\n",
              t.silentEndDeletedOne, t.silentEnd, t.rangeBackspaceSelectionForm, t.rangeBackspace,
              t.plainPendingDeletedWriter, t.plainPending, t.flaggedAdmitted, t.flaggedAdmittedCleared);
  for (const auto &[k, v] : t.first) std::printf("    first %-52s %s\n", k.c_str(), v.c_str());
}

// ---- unit cells for the header ---------------------------------------------------------------

void headerCells() {
  const std::vector<Rect> none, one = {Rect{100, 0, 200, 276}}, two = {Rect{100, 0, 300, 276}};
  if (classifyMove(false, none) != MoveKind::CaretStartPlain || classifyMove(true, none) != MoveKind::ExtendOrRangeStart ||
      classifyMove(false, one) != MoveKind::ExtendOrRangeStart)
    fail("classifyMove");
  {
    PendingMove m = beginMove(true, none);
    if (onVisibleCursor(m) != Completion::Pending) fail("rule (a): a cursor before any differing selection completed");
    if (onTextSelection(m, none) != Completion::Pending || m.selectionDiffered) fail("rule (a): an equal (empty) selection counted as step 1");
    if (onTextSelection(m, one) != Completion::Pending || !m.selectionDiffered) fail("rule (a): a differing selection did not count as step 1");
    if (onVisibleCursor(m) != Completion::Transition) fail("rule (a): the cursor after the differing selection did not complete");
    if (onReadbackDeadline(m) != Completion::Transition) fail("rule (a): a deadline after completion changed the completion");
  }
  {
    PendingMove m = beginMove(false, one); // a plain move from a range: rule (a), empty counts as different
    if (m.kind != MoveKind::ExtendOrRangeStart) fail("range-start plain move not classified as rule (a)");
    if (onTextSelection(m, one) != Completion::Pending || m.selectionDiffered) fail("rule (a): the dispatch selection resent counted as step 1");
    onTextSelection(m, none);
    if (!m.selectionDiffered) fail("rule (a): empty against non-empty did not count as different");
  }
  {
    PendingMove m = beginMove(false, none); // caret-start plain: today's rule
    if (onTextSelection(m, none) != Completion::FirstCallback) fail("caret-start plain: a selection callback did not complete");
    PendingMove c = beginMove(false, none);
    if (onVisibleCursor(c) != Completion::FirstCallback) fail("caret-start plain: a cursor did not complete");
    PendingMove d = beginMove(true, none);
    if (onReadbackDeadline(d) != Completion::Readback) fail("readback fallback");
  }
  // the flag's table
  struct Cell { bool extend; bool range; Completion c; bool before, after; const char *name; };
  const Cell cells[] = {
      {true, false, Completion::Readback, false, true, "extend by readback sets"},
      {true, true, Completion::Readback, false, true, "extend from a range by readback sets"},
      {false, false, Completion::Readback, false, false, "plain move by readback does not set"},
      {false, true, Completion::Readback, false, false, "range-start plain move by readback does not set (12.2)"},
      {false, false, Completion::FirstCallback, true, true, "caret-start plain move does not clear"},
      {true, false, Completion::Transition, true, false, "extend under rule (a) clears"},
      {false, true, Completion::Transition, true, false, "range-start plain move under rule (a) clears"},
      {true, false, Completion::Readback, true, true, "a second readback extend keeps it set"},
  };
  for (const Cell &c : cells) {
    ExtendUnconfirmed f;
    if (c.before) { PendingMove s = beginMove(true, none); s.completion = Completion::Readback; f.onMoveCompleted(s); }
    PendingMove m = beginMove(c.extend, c.range ? one : none);
    m.completion = c.c;
    f.onMoveCompleted(m);
    if (f.set() != c.after) fail(std::string("flag table: ") + c.name);
  }
  {
    ExtendUnconfirmed f;
    PendingMove s = beginMove(true, none); s.completion = Completion::Readback; f.onMoveCompleted(s);
    f.onFlaggedDeleteProved();
    if (f.set()) fail("flag: a proved flagged delete did not clear");
    f.onMoveCompleted(s);
    f.onDocumentClosed();
    if (f.set()) fail("flag: close did not clear");
  }
  // the decisions
  const std::vector<std::uint32_t> oneCp = {'a'}, twoCp = {'e', 0x301}, twoUnits = {'a', 'b'};
  if (judgeDeleteSelection(false) || !judgeDeleteSelection(true)) fail("judgeDeleteSelection");
  if (judgeBarrierUnit(false, twoUnits) || judgeBarrierUnit(false, twoCp)) fail("judgeBarrierUnit: unflagged refused");
  if (judgeBarrierUnit(true, oneCp) || !judgeBarrierUnit(true, twoUnits) || !judgeBarrierUnit(true, twoCp))
    fail("judgeBarrierUnit: flagged one-code-point rule");
  if (judgeWindowExpiry(false) || !judgeWindowExpiry(true)) fail("judgeWindowExpiry");
  for (const Stage *s : {judgeDeleteSelection(true), judgeBarrierUnit(true, twoCp), judgeWindowExpiry(true)})
    if (std::string(s->name) != "prior-key-unconfirmed" || s->keyPosted) fail("stage: prior-key-unconfirmed, keyPosted:false");
  if (probe::merge::findStage(kPriorKeyUnconfirmed.name)) fail("stage: the name already exists in merge::kStages (wiring would collide)");
}

} // namespace

int main() {
  headerCells();
  if (const char *only = std::getenv("EXTEND_MODEL_TRACE")) {
    // one scenario, traced: EXTEND_MODEL_TRACE='<exact describe() text>' build/extend_completion_model_test
    for (int mode : {1, 2, 3}) forEachScenario(mode, KeySet::Full, [&](const Scenario &sc) {
      if (describe(sc) != only) return;
      Knobs kn;
      Run r(sc, kn);
      r.trace = true;
      std::printf("TRACE %s\n", only);
      r.go();
      std::printf("  outcome=%d stage=%s completion=%s deleted=%d text=%s writer=%s\n", static_cast<int>(r.outcome),
                  r.stageName.c_str(), r.completionName.c_str(), r.deletedUnits, r.core.text().c_str(), writerText(sc).c_str());
    });
    return 0;
  }

  // ---- phase 1: rule (a), and the population of L-extend-prior-flush ----
  std::printf("== L-extend-prior-flush: the population (rule (a) stale), one line per sequence, deadline lags listed ==\n");
  Knobs faithful;
  const Phase1 p1 = sweep1(faithful, true);
  std::printf("== end of population (%ld lines) ==\n", p1.printedLines);
  report1("rule (a), faithful model", p1);
  if (p1.guard) fail("phase 1: a run hit the tick guard");
  if (p1.undeclared) fail("phase 1: a stale rule-(a) completion outside the declared classes: " + p1.firstUndeclared);
  if (!p1.transition || !p1.readbackKeyPending || !p1.readbackFlushLate) fail("phase 1 is vacuous (a completion class never occurred)");
  for (const std::string &cls : kDeclaredClasses)
    if (!p1.byClass.count(cls)) fail("phase 1: declared class never occurred: " + cls);
  for (const auto &[cls, n] : p1.byClass)
    if (std::find(kDeclaredClasses.begin(), kDeclaredClasses.end(), cls) == kDeclaredClasses.end())
      fail("phase 1: class outside the declaration: " + cls);
  {
    // undisturbed: every non-silent extend completes under rule (a) with the deadline late enough
    long undisturbed = 0, transition = 0, silentReadback = 0, silent = 0;
    forEachScenario(0, KeySet::Full, [&](const Scenario &sc) {
      if (sc.e != Earlier::None || !sc.u || sc.lagDeadline != 9) return;
      Run r(sc, faithful);
      r.go();
      Core w = makeCore(sc);
      const bool changes = applyKey(w, static_cast<Key>(sc.u - 1));
      const bool ruleA = r.pending.kind == MoveKind::ExtendOrRangeStart;
      if (!ruleA) return;
      if (changes) { ++undisturbed; if (r.uCompletion == Completion::Transition && !r.uStale) ++transition; }
      else { ++silent; if (r.uCompletion == Completion::Readback) ++silentReadback; }
    });
    std::printf("liveness: undisturbed rule-(a) moves complete by transition %ld/%ld; silent ones by readback %ld/%ld\n",
                transition, undisturbed, silentReadback, silent);
    if (transition != undisturbed || !undisturbed) fail("liveness: an undisturbed rule-(a) move did not complete by transition");
    if (silentReadback != silent || !silent) fail("liveness: a silent move did not complete by readback");
  }

  // ---- red cases for rule (a) ----
  Knobs firstCursor; firstCursor.rule = Rule::FirstCursor;
  const Phase1 r9 = sweep1(firstCursor, false);
  report1("9's rule (first cursor)", r9);
  Knobs firstSel; firstSel.rule = Rule::FirstSelection;
  const Phase1 r19 = sweep1(firstSel, false);
  report1("v19's rule (first TEXT_SELECTION)", r19);
  for (const auto *red : {&r9, &r19}) {
    // counted by the sequence, not by the class: v19's rule fails "insert then Shift+key" through
    // the move's own flush (the pre-key caret), 9's rule through the insert's late cursor
    long insertCaret = 0, insertRange = 0;
    for (const auto &[e, n] : red->staleByEarlier) {
      if (e == Earlier::InsertCaret) insertCaret += n;
      if (e == Earlier::InsertRange) insertRange += n;
    }
    std::printf("red case %s: stale on insert then Shift+key = %ld, on type over a range then Shift+key = %ld\n",
                red == &r9 ? "9's rule" : "v19's rule", insertCaret, insertRange);
    if (!insertCaret) fail(std::string("red case: ") + (red == &r9 ? "9's" : "v19's") + " rule did not fail \"insert then Shift+key\"");
    if (!insertRange) fail(std::string("red case: ") + (red == &r9 ? "9's" : "v19's") + " rule did not fail \"type over a range then Shift+key\"");
  }

  // ---- condition 32 (ruling 4, 5a8d69f1): v20's offered keys only, no flag, today's delete routing ----
  // C ships as 10.5 minus the flag clauses: the flag is left unwired (flagDisabled); the page's
  // form is chosen at beforeinput from its snapshot with rule A as today (resolverRuleA).
  std::printf("== SECTION A: ruling 4 condition 32 -- v20's keys (plain caret-start moves), the flag unwired ==\n");
  Knobs v20; v20.flagDisabled = true; v20.resolverRuleA = true;
  const Phase2 c32 = sweep2(v20, KeySet::V20, true);
  report2("condition 32: v20 keys, flag unwired", c32);
  if (c32.guard) fail("condition 32: a run hit the tick guard");
  if (c32.undecided) fail("condition 32: a Backspace was never answered: " + c32.first.at("undecided"));
  if (!c32.runs || !c32.excludedRangeStart) fail("condition 32 is vacuous (no run, or no range-start move was excluded)");
  {
    // the stop condition: any Writer-divergent kind outside items 5/6 of finding 137 stops the relink
    long item5 = 0, item6 = 0;
    for (const auto &[kind, n] : c32.writerDiffersBy) {
      if (kind.find("today's rule for caret-start plain moves") != std::string::npos) item5 += n;
      else if (kind.find("ruling 3 Q1 B") != std::string::npos) item6 += n;
      else fail("STOP CONDITION (ruling 4 condition 32): a Writer-divergent kind outside finding 137's items 5/6 on v20's keys: " + kind + " | " + c32.first.at("differs: " + kind));
    }
    std::printf("condition 32: Writer-divergent by kind: item 5 (stale first-callback completion) %ld, item 6 (select-range completed early) %ld, other 0; runs %ld, range-start moves excluded %ld\n",
                item5, item6, c32.runs, c32.excludedRangeStart);
    // pinned by condition 32 (replacing the REPORTED pins of fce084d6): re-rule before changing either
    const long kPinnedItem5 = 27744, kPinnedItem6 = 2448;
    if (item5 != kPinnedItem5) fail("condition 32 pin: item 5 count changed (pinned " + std::to_string(kPinnedItem5) + ", now " + std::to_string(item5) + "); re-rule before trusting");
    if (item6 != kPinnedItem6) fail("condition 32 pin: item 6 count changed (pinned " + std::to_string(kPinnedItem6) + ", now " + std::to_string(item6) + "); re-rule before trusting");
  }

  // ---- condition 33 (ruling 4): typing and an inline format behind a pending key; reported, not ruled ----
  std::printf("== SECTION C: ruling 4 condition 33 -- typing and an inline format dispatched behind a pending key (reported) ==\n");
  const Phase3 c33type = sweep3(v20, KeySet::V20, 2), c33format = sweep3(v20, KeySet::V20, 3);
  report3("typing, v20 keys", c33type);
  report3("inline format, v20 keys", c33format);
  // SPEC-M3-ordered-commands §8: the threaded mode is the red case that the generator is alive
  if (c33type.differs != 5474) fail("threaded mode pin (SPEC-M3-ordered-commands §8): typing, v20 keys, Writer-divergent " + std::to_string(c33type.differs) + ", pinned 5474; stop");
  if (c33format.differs != 3868) fail("threaded mode pin (SPEC-M3-ordered-commands §8): inline format, v20 keys, Writer-divergent " + std::to_string(c33format.differs) + ", pinned 3868; stop");
  report3("typing, all keys (next spec)", sweep3(faithful, KeySet::Full, 2));
  report3("inline format, all keys (next spec)", sweep3(faithful, KeySet::Full, 3));

  // ---- SPEC-M3-ordered-commands §8: the synchronous-key mode (C, unipoll) ----
  std::printf("== SECTION D: SPEC-M3-ordered-commands §8 -- the synchronous-key mode (C): every shape, its red cases ==\n");
  {
    Knobs c; c.sync = true; c.flagDisabled = true;
    static const char *follows[] = {"moves only", "Backspace", "typing (condition 33)", "inline format (condition 33)"};
    std::map<std::string, long> completions;
    for (KeySet keys : {KeySet::V20, KeySet::Full})
      for (int mode : {0, 1, 2, 3}) {
        const std::string name = std::string("C, ") + (keys == KeySet::V20 ? "v20 keys, " : "all keys, ") + follows[mode];
        const PhaseC t = sweepC(c, keys, mode);
        reportC(name.c_str(), t);
        for (const auto &[k, n] : t.byCompletion) completions[k] += n;
        if (!t.runs) fail(name + ": vacuous (no run)");
        if (t.guard) fail(name + ": a run hit the tick guard");
        if (t.differs) fail(name + ": Writer-divergent " + std::to_string(t.differs) + "; first: " + t.first.at("Writer-divergent"));
        if (t.forged) fail(name + ": a forged reply; first: " + t.first.at("forged reply"));
        if (t.stale) fail(name + ": a stale U completion; first: " + t.first.at("stale U completion"));
        if (t.undecided) fail(name + ": never answered; first: " + t.first.at("never answered"));
        if (t.runsByEarlier.size() != 8) fail(name + ": an earlier operation never occurred");
      }
    // non-vacuity: every answer the frozen client accepts under C occurs (§5.4, §5.5, §5.8)
    for (const char *k : {"move: transition", "move: readback", "verified-key-undo", "verified-boundary-noop", "uno-command-result", "inserted"})
      if (!completions.count(k)) fail(std::string("C: the answer never occurred: ") + k);
    // red cases: each rule of §5.2 that C's zero depends on, removed, must print a forged reply
    long forgedSamePoll = 0, differsSamePoll = 0, forgedMidFlush = 0, differsMidFlush = 0;
    Knobs samePoll = c; samePoll.syncReplySamePoll = true;
    Knobs midFlush = c; midFlush.syncPollMidFlush = true;
    for (int mode : {0, 1, 2, 3}) {
      const std::string a = std::string("red: reply in the command's poll, ") + follows[mode];
      const PhaseC ta = sweepC(samePoll, KeySet::Full, mode);
      reportC(a.c_str(), ta);
      forgedSamePoll += ta.forged; differsSamePoll += ta.differs;
      const std::string b = std::string("red: a poll inside a flush, ") + follows[mode];
      const PhaseC tb = sweepC(midFlush, KeySet::Full, mode);
      reportC(b.c_str(), tb);
      forgedMidFlush += tb.forged; differsMidFlush += tb.differs;
    }
    std::printf("C red cases: reply in the command's poll forged=%ld writerDiffers=%ld; a poll inside a flush forged=%ld writerDiffers=%ld\n",
                forgedSamePoll, differsSamePoll, forgedMidFlush, differsMidFlush);
    if (!forgedSamePoll) fail("C red case vacuous: the reply in the command's poll forged nothing");
    if (!forgedMidFlush) fail("C red case vacuous: a poll inside a flush forged nothing");
    std::printf("C limits: a key is one event with no hops; bold does not change a rectangle's width (condition 40); the page sends one item at a time, so one command per poll is not discriminated here\n");
  }

  // ---- the flag (SPEC 12.2), SUPERSEDED by ruling 4 (5a8d69f1): kept as the record of the six holes ----
  // The header's flag functions stay unwired; this section exercises them and prints REPORTED 1-6 as
  // the ruling read them.  Nothing here is a pin any more; the structural checks that still hold are
  // kept so that a change in the model is seen.
  std::printf("== SECTION B: the flag of 12.2, superseded by ruling 4 -- the record of the six holes (all keys) ==\n");
  const Phase2 p2 = sweep2(faithful);
  report2("flag, faithful model", p2);
  if (p2.guard) fail("phase 2: a run hit the tick guard");
  if (p2.undecided != p2.notK1Wedged) fail("phase 2: a Backspace was never answered outside the not-K1 wedge: " + p2.first.at("undecided"));
  if (p2.selDeleteNotOne) fail("flag: a verified-selection-delete of other than one unit: " + p2.first.at("selection-delete-not-one-unit"));
  if (p2.deleteSelOtherRange) fail("flag: .uno:Delete on a range other than the dispatch's: " + p2.first.at("delete-selection-other-range"));
  if (p2.noopKeyPending) fail("flag: verified-boundary-noop with a key pending: " + p2.first.at("noop-with-key-pending"));
  if (p2.twoUnitDelete || p2.silentNoop) fail("flag: the faithful model deleted two units for Writer's one, or answered a silent no-op");
  // the three stacked shapes of ruling 3 Q2 each refuse, and each occurs
  if (!p2.fpRefusedVerify) fail("phase 2 is vacuous: no same-direction stacking refused at the verifier");
  if (!p2.fpRefusedWindow) fail("phase 2 is vacuous: no cancelled pair refused at the window");
  if (!p2.fpRefusedDeleteSelection) fail("phase 2 is vacuous: no delete-selection refused with an extend queued");
  if (p2.fpAdmittedOther) fail("flag: a flagged delete with an extend queued was admitted and differs from Writer outside the named shrink class: " + p2.first.at("flagged-admitted-other"));
  if (p2.forgedWithoutStale) fail("flag: an extend was queued with the flag clear and no forged completion before it: " + p2.first.at("extend-pending-unflagged-without-stale"));
  if (!p2.forgedWrongDelete) fail("phase 2: the forged-completion residual (12.2) never occurred; the model does not reach it");
  if (p2.silentEndDeletedOne != p2.silentEnd || !p2.silentEnd) fail("liveness: Shift+End at the line end then Backspace did not delete one as Writer does");
  if (p2.rangeBackspaceSelectionForm != p2.rangeBackspace || !p2.rangeBackspace) fail("liveness: a range then Backspace did not use delete-selection with the flag clear");
  if (p2.plainPendingDeletedWriter != p2.plainPending || !p2.plainPending) fail("liveness: a pending caret-start plain move then Backspace did not delete what Writer deletes");
  if (!p2.flaggedAdmitted || p2.flaggedAdmittedCleared != p2.flaggedAdmitted) fail("liveness: a flagged one-code-point delete did not complete and clear the flag");
  for (const auto &[kind, n] : p2.writerDiffersBy) {
    const bool named = kind.find("K1 shrank it") != std::string::npos ||
                       kind.find("the residual") != std::string::npos ||
                       kind.find("today's rule for caret-start plain moves") != std::string::npos ||
                       kind.find("12.2 sets no flag for plain moves") != std::string::npos ||
                       kind.find("ruling 3 Q1 B") != std::string::npos;
    if (!named) fail("flag: a Writer-divergent run of an unnamed kind: " + kind + " | " + p2.first.at("differs: " + kind));
  }
  // What the model shows that the rule as written does not cover: printed under its name, counted, and
  // pinned (a change in either count means the rule or the model changed; re-rule before trusting it).
  std::printf("REPORTED 1 (12.2's one-code-point proof): a pending forward extension of two or more units (Shift+End mid-line, or two Shift+Right) answered by the readback, then Backspace: K1 SHRINKS the selection, and when one code point remains the flag admits the delete; Writer deletes the whole extension: %ld sequences; first: %s\n",
              p2.fpAdmittedShrink, p2.fpAdmittedShrink ? p2.first.at("flagged-admitted-shrink").c_str() : "-");
  std::printf("REPORTED 2 (12.2 sets no flag for plain moves): a range-start plain move answered by the readback (its key still queued, or run with its SEL0 undelivered), then delete-selection from the stale range: .uno:Delete removes the range Writer would have collapsed, or deletes forward at the collapsed caret (ruling 3 Q4's correction): %ld sequences; first: %s\n",
              p2.rangePlainPendingDiffers, p2.rangePlainPendingDiffers ? p2.first.at("range-plain-pending-differs").c_str() : "-");
  std::printf("REPORTED 3 (12.2's forged-completion residual): %ld sequences delete one unit wrongly behind a forged rule-(a) completion; first: %s\n",
              p2.forgedWrongDelete, p2.first.at("forged-residual-wrong-delete").c_str());
  std::printf("REPORTED 4 (12.2's one-code-point proof does not identify K1): a pending extend's own flush lands between K1's post and K1's run (a flush slot an earlier key had already queued), the verifier reads that selection as K1's and admits it when it is one code point; K1 then runs on the deleted text and the collapse the transaction waits for never comes: %ld sequences, %ld of them never answered (the engine's AwaitingDeleteCompletion has no deadline); first: %s\n",
              p2.notK1, p2.notK1Wedged, p2.notK1 ? p2.first.at("admitted-before-K1-ran").c_str() : "-");
  std::printf("REPORTED 5 (10.1 keeps today's rule for caret-start plain moves): a plain move registered while an earlier operation's flush is half delivered completes on that operation's late TEXT_SELECTION before its own key is posted; the page's snapshot is that operation's range, delete-selection passes the gate and .uno:Delete runs ahead of the queued move (ruling 3 Q4's correction, reached without a delete before it): %ld sequences, %ld of them wrong deletions; first: %s\n",
              p2.plainStale, p2.plainStaleWrongDelete, p2.plainStaleWrongDelete ? p2.first.at("plain-stale-wrong-delete").c_str() : "-");
  std::printf("REPORTED 6 (ruling 3 Q1 B, its effect on a delete): a select-range completed on RESET's or START's flush, or by its readback, before END's selection was delivered; the page's snapshot is the partial range and delete-selection's .uno:Delete runs on what core holds by then: %ld sequences, %ld of them wrong deletions; first: %s\n",
              p2.selectStale, p2.selectStaleWrongDelete, p2.selectStaleWrongDelete ? p2.first.at("select-stale-wrong-delete").c_str() : "-");
  // (the pins of fce084d6 on REPORTED 1, 4 and 5 were replaced by condition 32's pins above)
  if (!p2.rangePlainPendingDiffers) fail("REPORTED 2 vanished: the rule or the model changed; re-rule before trusting");

  // ---- red cases for the flag ----
  Knobs noFlag; noFlag.flagDisabled = true;
  const Phase2 rNoFlag = sweep2(noFlag);
  report2("without the flag", rNoFlag);
  if (!rNoFlag.twoUnitDelete) fail("red case: without the flag the generator found no two-unit delete");
  if (!rNoFlag.silentNoop) fail("red case: without the flag the generator found no silent mid-paragraph no-op");
  Knobs oneCp; oneCp.alwaysOneCodePoint = true;
  const Phase2 rOneCp = sweep2(oneCp);
  report2("one-code-point rule unflagged", rOneCp);
  if (!rOneCp.falseRefusal) fail("red case: the unflagged one-code-point rule produced no false refusal on a multi-code-point grapheme");
  Knobs noRuleA; noRuleA.resolverRuleA = false;
  const Phase2 rNoRuleA = sweep2(noRuleA);
  report2("resolver without rule A (12.4, reported)", rNoRuleA);

  if (gFailures) {
    std::printf("%d failure(s)\n", gFailures);
    return 1;
  }
  std::printf("ok\n");
  return 0;
}
