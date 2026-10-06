#include "merge_key_undo.hpp"

#include <cstdio>
#include <deque>
#include <string>
#include <vector>

// SPEC-M3-paragraph-merge M1-2 (as amended in 10.2, 13.1, 14.6): the
// attribution rule and the anchor fence driven by callback sequences GENERATED
// from a model of LOK, not listed by hand.
//
// The model, and what each part of it stands for:
//   - one FIFO queue of user events and flushes (P1); processing an event
//     schedules a flush only when none is pending (init.cxx:2578-2582), so an
//     event still queued when the Shift press is posted shares its flush;
//   - a flush computes its payloads at flush time (P2): START, END,
//     TEXT_SELECTION, then the caret (P3); TEXT_SELECTION and the caret are
//     dropped when equal to the last sent, START/END never are (14.1);
//   - no START/END for a table-cell selection (14.1);
//   - rectangles as R0b measured them: caret (x, top+offset, 0, portion
//     height) with no mark, (x, top, 0, line height) with one; anchor
//     (x, top, 0, line height - 1);
//   - a relayout event that moves every line and so changes the caret's
//     rectangle without any key (the idle-layout caret of 10.1(a));
//   - switch P4off: press 1 flushes once in the middle of its own processing.
//
// The property, checked at every "post the key" decision: no restore press is
// still queued, there is no selection, and the caret is where the Shift press
// ran.  Every generated sequence ends in a key that satisfies it, a refusal,
// or no decision (the engine's deadline refuses).
//
// It must hold with zero counterexamples for the real rule on the faithful
// model, and the generator must FIND counterexamples for the rules the spec
// rejected (first-different-caret, P as the transaction-start snapshot, no
// fence) and for the real rule when P4 is broken -- otherwise the generator
// is too weak to say anything.  Positions that share a rectangle (a zero-width
// portion, or a relayout that lands one line exactly on another) are the
// registered limit (14.2, 14.5): with them switched on, counterexamples are
// expected and counted, not failed.

using namespace probe::merge;

namespace {

int gFailures = 0;
void fail(const std::string &what) {
  ++gFailures;
  std::printf("FAIL %s\n", what.c_str());
}

// ---- layout -----------------------------------------------------------------

struct Line {
  long top, height, caretOff, caretH;
};
struct Pos {
  int line;
  long x;
};

struct Layout {
  std::vector<Line> lines;
  std::vector<Pos> pos;
  long shift = 0;
  Rect caret(int p, bool withMark) const {
    const Line &l = lines[pos[p].line];
    if (withMark)
      return {pos[p].x, l.top + shift, 0, l.height};
    return {pos[p].x, l.top + shift + l.caretOff, 0, l.caretH};
  }
  Rect anchor(int p) const {
    const Line &l = lines[pos[p].line];
    return {pos[p].x, l.top + shift, 0, l.height - 1};
  }
};

// Line 0 as boundaries.odt (caret = line), line 1 as P27 (a taller portion
// on the line: the caret is 52 lower and 51 shorter than the anchor).
Layout makeLayout(bool alias) {
  Layout l;
  l.lines = {{1000, 276, 0, 276}, {1418, 400, 52, 348}};
  l.pos = {{0, 1418}, {0, 2000}, {0, 2991}, {1, 1418}, {1, 2138}, {1, 3000}};
  if (alias)
    l.pos[4].x = 1418; // a zero-width portion: positions 3 and 4 share a rect
  return l;
}

// ---- trackers ---------------------------------------------------------------
//
// The real one is probe::merge::Attribution.  The two below are the rules the
// spec rejected, kept to the same interface so the same generator drives all.

// 3.2 as first written: P snapshotted when the transaction begins, press N's
// evidence = the first caret after posting press N that differs from the
// caret known then, no collapse requirement, no fence.
class OldRule {
public:
  using Phase = Attribution::Phase;
  void beginTransaction(bool) {
    phase_ = Phase::AwaitUnitSelection;
    p_ = last_;
  }
  bool restorePosted() {
    if (phase_ != Phase::UnitReady && phase_ != Phase::NeedSecondPress)
      return false;
    phase_ = phase_ == Phase::UnitReady ? Phase::AwaitRestore1 : Phase::AwaitRestore2;
    known_ = last_;
    return true;
  }
  void onSelectionStart(const Rect &) {}
  void onSelectionEnd(const Rect &) {}
  void onTextSelection(bool nonEmpty) {
    if (phase_ == Phase::AwaitUnitSelection && nonEmpty)
      phase_ = Phase::AwaitUnitCaret;
  }
  void onCaret(const Rect &r) {
    if (phase_ == Phase::AwaitUnitCaret && r != p_)
      phase_ = Phase::UnitReady;
    else if ((phase_ == Phase::AwaitRestore1 || phase_ == Phase::AwaitRestore2) && r != known_)
      phase_ = r == p_ ? Phase::Restored
               : phase_ == Phase::AwaitRestore1 ? Phase::NeedSecondPress
                                                : Phase::NotRestored;
    last_ = r;
  }
  Phase phase() const { return phase_; }
  bool fenceHolds() const { return true; }

private:
  Phase phase_ = Phase::Idle;
  Rect last_, p_, known_;
};

// The real rule's evidence handling (collapse first for press 1, "differs
// from the caret known when posted" for press 2), but P is the
// transaction-start snapshot and there is no fence -- the two things 10.1(a)
// and 13.1 changed about P.
class SnapshotP {
public:
  using Phase = Attribution::Phase;
  void beginTransaction(bool) {
    phase_ = Phase::AwaitUnitSelection;
    p_ = last_;
  }
  bool restorePosted() {
    if (phase_ == Phase::UnitReady) {
      phase_ = Phase::AwaitRestore1;
      collapse_ = false;
      return true;
    }
    if (phase_ == Phase::NeedSecondPress) {
      phase_ = Phase::AwaitRestore2;
      known_ = last_;
      return true;
    }
    return false;
  }
  void onSelectionStart(const Rect &) {}
  void onSelectionEnd(const Rect &) {}
  void onTextSelection(bool nonEmpty) {
    if (phase_ == Phase::AwaitUnitSelection && nonEmpty)
      phase_ = Phase::AwaitUnitCaret;
    else if (phase_ == Phase::AwaitRestore1 && !nonEmpty)
      collapse_ = true;
  }
  void onCaret(const Rect &r) {
    if (phase_ == Phase::AwaitUnitCaret && r != p_)
      phase_ = Phase::UnitReady;
    else if (phase_ == Phase::AwaitRestore1 && collapse_)
      phase_ = r == p_ ? Phase::Restored : Phase::NeedSecondPress;
    else if (phase_ == Phase::AwaitRestore2 && r != known_)
      phase_ = r == p_ ? Phase::Restored : Phase::NotRestored;
    last_ = r;
  }
  Phase phase() const { return phase_; }
  bool fenceHolds() const { return true; }

private:
  Phase phase_ = Phase::Idle;
  Rect last_, p_, known_;
  bool collapse_ = false;
};

// ---- the model run ------------------------------------------------------------

// None: the caret has been at q all along.  Flushed: an event moved it s -> q
// and its flush was delivered before the transaction.  Straddling: the event
// was processed before the Shift press was posted but its flush runs after
// (a caret from before the transaction delivered after it began).  Queued:
// the event was still queued when the Shift press was posted (13.1).
enum class EventMode { None, Flushed, Straddling, Queued };
enum class Outcome { Merged, AnchorRefused, RestoreRefused, NoDecision, Counterexample };

struct Scenario {
  bool backward;
  int q;             // where the Shift press runs
  EventMode e;
  int s;             // the caret before the event (== q when e is None)
  bool table;
  int r1, r2;        // where restore presses 1 and 2 leave the caret
  int relayoutAt;    // 0 none, 1 before K, 2 after K, 3 after R1, 4 after R2,
                     // 5 when the unit's caret is delivered
  long relayoutShift;
  bool bounce;       // the relayout moves back right after its caret is delivered
  int intermediate;  // P4off: press 1 flushes with the caret here; -1 = off
  bool alias;
  int lag[3];        // engine posts press 1, press 2, the key after this many
                     // more LOK events (0 = at once)
  bool resend;       // every caret is delivered twice (only a side field changed)
};

struct Ev {
  enum Kind { E, K, R1, R2, Relayout, RelayoutBack, Key, Flush } kind;
};

template <class Tracker> struct Run {
  const Scenario &sc;
  Layout lay;
  Tracker tr;
  bool ignoreFence = false;
  std::deque<Ev> q;
  int caret;
  bool hasSel = false;
  int selAnchor = 0, selPoint = 0;
  bool flushPending = false;
  std::string lastSel;
  Rect lastCaret;
  bool hasLastCaret = false;
  int kOrigin = -1;
  Outcome outcome = Outcome::NoDecision;
  bool decided = false;
  Attribution::Phase acted = Attribution::Phase::Idle;
  int presses = 0;
  // The engine thread: what it decided, posted only after `countdown` more
  // LOK events have completed (the post crosses threads).
  struct Pending { bool key; int countdown; };
  bool bouncePending = false;
  std::vector<Pending> pending;

  explicit Run(const Scenario &s) : sc(s), lay(makeLayout(s.alias)) {
    caret = s.e == EventMode::None ? s.q : s.s;
    lastSel = "";
    lastCaret = lay.caret(caret, false);
    hasLastCaret = true;
    tr.onCaret(lastCaret); // the caret at rest, delivered long ago
  }

  void post(Ev::Kind k) {
    q.push_back({k});
    if (k == Ev::R1 && sc.relayoutAt == 3) q.push_back({Ev::Relayout});
    if (k == Ev::R2 && sc.relayoutAt == 4) q.push_back({Ev::Relayout});
  }

  void flush() {
    flushPending = false;
    if (hasSel && !sc.table) {
      const int lo = selAnchor < selPoint ? selAnchor : selPoint;
      const int hi = selAnchor < selPoint ? selPoint : selAnchor;
      deliverStart(lay.anchor(lo));
      deliverEnd(lay.anchor(hi));
    }
    std::string sel;
    if (hasSel)
      sel = "S" + std::to_string(selAnchor) + "-" + std::to_string(selPoint);
    if (sel != lastSel) {
      lastSel = sel;
      deliverTextSelection(!sel.empty());
    }
    const Rect c = lay.caret(caret, hasSel);
    if (!hasLastCaret || c != lastCaret) {
      lastCaret = c;
      hasLastCaret = true;
      deliverCaret(c);
      if (sc.resend)
        deliverCaret(c);
    }
    if (bouncePending) {
      bouncePending = false;
      q.push_back({Ev::RelayoutBack});
    }
  }

  void process(const Ev &ev) {
    switch (ev.kind) {
    case Ev::E:
      caret = sc.q;
      break;
    case Ev::K:
      kOrigin = caret;
      hasSel = true;
      selAnchor = caret;
      selPoint = caret + (sc.backward ? -1 : 1);
      caret = selPoint;
      break;
    case Ev::R1:
      hasSel = false;
      if (sc.intermediate >= 0) {
        caret = sc.intermediate;
        flush(); // P4 broken: a flush inside the key's own processing
      }
      caret = sc.r1;
      break;
    case Ev::R2:
      caret = sc.r2;
      break;
    case Ev::Relayout:
      lay.shift += sc.relayoutShift;
      bouncePending = sc.bounce;
      break;
    case Ev::RelayoutBack:
      lay.shift -= sc.relayoutShift;
      break;
    case Ev::Key:
      // The property: the user's key runs where the Shift press ran.
      if (!decided)
        decide(!hasSel && caret == kOrigin ? Outcome::Merged : Outcome::Counterexample);
      return;
    case Ev::Flush:
      flush();
      return;
    }
    if (!flushPending) {
      flushPending = true;
      q.push_back({Ev::Flush});
    }
  }

  void deliverStart(const Rect &r) { tr.onSelectionStart(r); react(); }
  void deliverEnd(const Rect &r) { tr.onSelectionEnd(r); react(); }
  void deliverTextSelection(bool nonEmpty) { tr.onTextSelection(nonEmpty); react(); }
  void deliverCaret(const Rect &r) { tr.onCaret(r); react(); }

  void schedule(bool key) {
    const int lag = sc.lag[key ? 2 : presses];
    if (lag == 0) execute(key);
    else pending.push_back({key, lag});
  }
  void execute(bool key) {
    if (key) {
      post(Ev::Key);
      return;
    }
    if (tr.restorePosted()) {
      ++presses;
      post(presses == 1 ? Ev::R1 : Ev::R2);
    }
  }
  void tick() {
    std::vector<Pending> due;
    for (std::size_t i = 0; i < pending.size();) {
      if (--pending[i].countdown == 0) {
        due.push_back(pending[i]);
        pending.erase(pending.begin() + i);
      } else {
        ++i;
      }
    }
    for (const Pending &p : due) execute(p.key);
  }

  // The engine, acting once per phase it reaches.
  void react() {
    if (decided || tr.phase() == acted)
      return;
    acted = tr.phase();
    using P = Attribution::Phase;
    switch (acted) {
    case P::AwaitUnitCaret:
      // P and A are known at the unit's TEXT_SELECTION: a failing fence
      // refuses here, without waiting for U (whose caret may be deduplicated
      // away when the stale P happens to be the unit's far end).
      if (!ignoreFence && !tr.fenceHolds())
        decide(Outcome::AnchorRefused);
      return;
    case P::UnitReady:
      if (sc.relayoutAt == 5) q.push_back({Ev::Relayout});
      schedule(false);
      return;
    case P::NeedSecondPress:
      schedule(false);
      return;
    case P::Restored: {
      // Every press posted must have been seen: one still queued is a
      // counterexample now, whatever happens later.
      bool queuedPress = false;
      for (const Ev &ev : q)
        if (ev.kind == Ev::R1 || ev.kind == Ev::R2) queuedPress = true;
      if (queuedPress) {
        decide(Outcome::Counterexample);
        return;
      }
      schedule(true);
      return;
    }
    case P::NotRestored:
      decide(Outcome::RestoreRefused);
      return;
    default:
      return;
    }
  }
  void decide(Outcome o) {
    decided = true;
    outcome = o;
  }

  void drain() {
    for (int guard = 0; (!q.empty() || !pending.empty()) && guard < 1000; ++guard) {
      if (q.empty()) { tick(); continue; }
      Ev ev = q.front();
      q.pop_front();
      process(ev);
      tick();
    }
  }

  Outcome go() {
    if (sc.e == EventMode::Flushed) {
      process({Ev::E});
      drain();
    }
    if (sc.e == EventMode::Straddling)
      process({Ev::E}); // processed; its flush is still queued
    if (sc.e == EventMode::Queued)
      q.push_back({Ev::E}); // posted, not yet processed, when K is posted
    if (sc.relayoutAt == 1)
      q.push_back({Ev::Relayout});
    tr.beginTransaction(sc.backward);
    post(Ev::K);
    if (sc.relayoutAt == 2)
      q.push_back({Ev::Relayout});
    drain();
    return outcome;
  }
};

struct Tally {
  long runs = 0, merged = 0, merged2 = 0, anchor = 0, restore = 0, none = 0, counter = 0;
  long live = 0; // liveness violations (expected outcome not reached)
  long counterBounce = 0; // counterexamples whose scenario has a transient reflow
  std::string firstCounter, firstLive;
};

// Liveness, for the scenarios where nothing disturbs the transaction: no
// table, no relayout, P4 intact, no coincident rects, no event still queued.
// Safety alone would let a rule that refuses everything pass; this is what
// makes "type, then Delete at once" (M2-1b, the Straddling mode) merge.
// Returns false when the outcome is not the one the design promises.
bool liveOutcome(const Scenario &s, Outcome o, int presses) {
  if (s.relayoutAt != 0 || s.intermediate >= 0 || s.alias)
    return true;
  if (s.table || s.e == EventMode::Queued)
    return o == Outcome::AnchorRefused; // 14.1 / 13.1: refused before the key
  const int unitPoint = s.q + (s.backward ? -1 : 1);
  if (s.r1 == s.q)
    return o == Outcome::Merged && presses == 1;
  if (s.r1 == unitPoint)
    return true; // its caret can equal the unit's (dedup): a deadline refusal
  if (s.r2 == s.q)
    return o == Outcome::Merged && presses == 2;
  if (s.r2 == s.r1)
    return o == Outcome::NoDecision; // deduplicated: the deadline refuses
  return o == Outcome::RestoreRefused;
}

std::string describe(const Scenario &s) {
  const char *e = s.e == EventMode::None      ? "none"
                  : s.e == EventMode::Flushed ? "flushed"
                  : s.e == EventMode::Straddling ? "straddling"
                                                 : "queued";
  return std::string(s.backward ? "back" : "fwd") + " q=" + std::to_string(s.q) + " e=" + e +
         " s=" + std::to_string(s.s) + (s.table ? " table" : "") + " r1=" + std::to_string(s.r1) +
         " r2=" + std::to_string(s.r2) + " relayout@" + std::to_string(s.relayoutAt) + "(" +
 std::to_string(s.relayoutShift) + (s.bounce ? " bounce" : "") + ") mid=" + std::to_string(s.intermediate) +
         (s.alias ? " alias" : "") + " lag=" + std::to_string(s.lag[0]) + std::to_string(s.lag[1]) +
         std::to_string(s.lag[2]) + (s.resend ? " resend" : "");
}

template <class Tracker>
Tally sweep(bool p4off, bool coincidence, bool ignoreFence) {
  Tally t;
  const int n = 6;
  // +100 moves every line for good, +100 bounce moves it and back (a
  // transient reflow), -418 lands line 1 exactly on line 0 (coincidence).
  const long shifts[] = {100, 100, -418};
  const bool bounces[] = {false, true, false};
  for (int b = 0; b < 2; ++b)
    for (int qq = 0; qq < n; ++qq) {
      if ((b && qq == 0) || (!b && qq == n - 1)) continue;
      for (int em = 0; em < 4; ++em)
        for (int ss = 0; ss < n; ++ss) {
          if (em == 0 && ss != qq) continue;
          if (em != 0 && ss == qq) continue;
          for (int tb = 0; tb < 2; ++tb)
            for (int r1 = 0; r1 < n; ++r1)
              for (int r2 = 0; r2 < n; ++r2)
                for (int ra = 0; ra < 6; ++ra)
                  for (int si = 0; si < (coincidence ? 3 : 2); ++si) {
                    if (ra == 0 && si) continue;
                    for (int mid = -1; mid < (p4off ? n : 0); ++mid)
                      for (int al = 0; al < (coincidence ? 2 : 1); ++al)
                      for (int lg = 0; lg < 27; ++lg)
                      for (int rs = 0; rs < 2; ++rs) {
                        Scenario sc{b != 0, qq, static_cast<EventMode>(em), ss, tb != 0,
                                    r1, r2, ra, shifts[si], bounces[si], mid, al != 0,
                                    {lg % 3, lg / 3 % 3, lg / 9}, rs != 0};
                        Run<Tracker> run(sc);
                        run.ignoreFence = ignoreFence;
                        const Outcome o = run.go();
                        ++t.runs;
                        if (!liveOutcome(sc, o, run.presses)) {
                          if (!t.live) t.firstLive = describe(sc);
                          ++t.live;
                        }
                        switch (o) {
                        case Outcome::Merged:
                          ++t.merged;
                          if (run.presses == 2) ++t.merged2;
                          break;
                        case Outcome::AnchorRefused: ++t.anchor; break;
                        case Outcome::RestoreRefused: ++t.restore; break;
                        case Outcome::NoDecision: ++t.none; break;
                        case Outcome::Counterexample:
                          if (!t.counter) t.firstCounter = describe(sc);
                          ++t.counter;
                          if (sc.relayoutAt && sc.bounce) ++t.counterBounce;
                          break;
                        }
                      }
                  }
        }
    }
  return t;
}

void report(const char *name, const Tally &t) {
  std::printf("%-34s runs=%ld merged=%ld (2 presses %ld) anchor=%ld restore=%ld none=%ld counter=%ld live=%ld\n",
              name, t.runs, t.merged, t.merged2, t.anchor, t.restore, t.none, t.counter, t.live);
  if (t.counter) std::printf("    first counterexample: %s (with a transient reflow: %ld)\n", t.firstCounter.c_str(), t.counterBounce);
  if (t.live) std::printf("    first liveness miss:  %s\n", t.firstLive.c_str());
}

// ---- unit cells ----------------------------------------------------------------

void fenceCells() {
  // R0b rows (findings/evidence/merge-native/r0b/anchor-rect.json).
  struct C { const char *name; Rect caret, anchor; bool holds; };
  const C cells[] = {
      {"R0b C01 (anchor = caret - 1)", {2991, 1418, 0, 276}, {2991, 1418, 0, 275}, true},
      {"R0b D04", {1418, 3458, 0, 368}, {1418, 3458, 0, 367}, true},
      {"R0b P27 (taller line)", {10058, 42820, 0, 348}, {10058, 42768, 0, 399}, true},
      {"x one off", {2991, 1418, 0, 276}, {2992, 1418, 0, 275}, false},
      {"anchor on the next line", {2991, 1418, 0, 276}, {2991, 1836, 0, 275}, false},
      {"caret one below the line", {2991, 1419, 0, 276}, {2991, 1418, 0, 275}, false},
      {"caret above the line", {10058, 42767, 0, 348}, {10058, 42768, 0, 399}, false},
  };
  for (const C &c : cells)
    if (anchorFenceHolds(c.caret, c.anchor) != c.holds)
      fail(std::string("fence cell: ") + c.name);

  // 14.6: an anchor left from before the Shift press is never read.
  {
    Attribution a;
    a.onCaret({100, 200, 0, 276});
    a.onSelectionStart({100, 200, 0, 275}); // a flush whose TEXT_SELECTION was deduplicated
    a.beginTransaction(false);
    a.onTextSelection(true); // the unit's flush: a table selection, no START
    a.onCaret({300, 200, 0, 276});
    if (a.hasAnchor() || a.fenceHolds())
      fail("14.6: a START from before the transaction was read as the unit's anchor");
  }
  {
    Attribution a;
    a.onCaret({100, 200, 0, 276});
    a.beginTransaction(false);
    a.onSelectionStart({100, 200, 0, 275});
    a.onCaret({100, 200, 0, 276}); // not the unit's flush: a caret ends it
    a.onTextSelection(true);
    if (a.hasAnchor())
      fail("14.6: a START from an earlier flush survived a caret callback");
  }
  {
    Attribution a; // backward reads END, not START
    a.onCaret({1418, 1836, 0, 276});
    a.beginTransaction(true);
    a.onSelectionStart({2991, 1418, 0, 275});
    a.onSelectionEnd({1418, 1836, 0, 275});
    a.onTextSelection(true);
    if (!a.hasAnchor() || a.anchor() != Rect{1418, 1836, 0, 275})
      fail("backward unit did not take TEXT_SELECTION_END as its anchor");
  }
}

void payloadCells() {
  const std::string empty = "{\n    \"actions\": \"\"\n}\n";
  const std::string one =
      "{\n    \"actions\": [\n        {\n            \"index\": \"0\",\n            \"comment\": "
      "\"Delete paragraph\",\n            \"viewId\": \"2\",\n            \"dateTime\": "
      "\"2026-10-06T10:36:27,944738774\"\n        }\n    ]\n}\n";
  const std::string two =
      "{\n    \"actions\": [\n        {\n            \"index\": \"0\",\n            \"comment\": "
      "\"Number On\\/Off\",\n            \"viewId\": \"2\",\n            \"dateTime\": \"x\"\n        },\n"
      "        {\n            \"index\": \"1\",\n            \"comment\": \"Delete \xe2\x80\x9c\\\"o\\\"\xe2\x80\x9d\","
      "\n            \"viewId\": \"2\",\n            \"dateTime\": \"y\"\n        }\n    ]\n}\n";
  UndoSummary s = summarizeUndoPayload(empty);
  if (!s.ok || s.actions != 0) fail("payload: empty list");
  s = summarizeUndoPayload(one);
  if (!s.ok || s.actions != 1 || s.topComment != "Delete paragraph") fail("payload: one action");
  s = summarizeUndoPayload(two);
  if (!s.ok || s.actions != 2 || s.topComment != "Number On/Off") fail("payload: two actions, escaped slash");
  if (summarizeUndoPayload("").ok || summarizeUndoPayload("{\"actions\": [ {\"index\": \"0\"} ]}").ok)
    fail("payload: malformed accepted");

  // Every exit after the key is keyPosted:true; every one before it false.
  for (const Stage &stage : kStages) {
    const bool keyName = std::string(stage.name).rfind("key-", 0) == 0;
    if (keyName != stage.keyPosted)
      fail(std::string("stage table: ") + stage.name);
  }
  const KeyJudgement cases[] = {
      judgeAfterKey(one, false, one, false), judgeAfterKey(one, true, one, true),
      judgeAfterKey(one, true, "garbage", false), judgeAfterKey(empty, true, empty, true),
  };
  for (const KeyJudgement &j : cases) {
    const Stage *stage = j.stage ? findStage(j.stage) : nullptr;
    if (j.verdict != KeyVerdict::Refused || !stage || !stage->keyPosted)
      fail("after-key exit not refused with keyPosted:true");
  }
  if (judgeAfterKey(one, true, one, false).verdict != KeyVerdict::Pending)
    fail("unchanged before the deadline is not pending");
  const KeyJudgement ok = judgeAfterKey(one, true, two, false);
  if (ok.verdict != KeyVerdict::Verified || ok.after.actions != 2 || ok.before.actions != 1)
    fail("changed payload not verified");
  const char *pre[] = {judgeBeforeKey(false, one, true, one), judgeBeforeKey(true, one, false, one),
                       judgeBeforeKey(true, one, true, two)};
  for (const char *name : pre) {
    const Stage *stage = name ? findStage(name) : nullptr;
    if (!stage || stage->keyPosted)
      fail("before-key exit not refused with keyPosted:false");
  }
  if (judgeBeforeKey(true, one, true, one) != nullptr)
    fail("equal P_start and P0 refused");

  const std::vector<std::uint32_t> para = {'\n'}, line = {0x2028}, tab = {'\t'}, text = {'a'},
                                   row = {'a', '\t', 'b', '\n'};
  if (classifyUnit(para) != UnitClass::MergeKey || classifyUnit(line) != UnitClass::MergeKey ||
      classifyUnit(row) != UnitClass::MergeKey || classifyUnit(tab) != UnitClass::Refused ||
      classifyUnit(text) != UnitClass::Barrier)
    fail("unit classification");
}

} // namespace

int main() {
  fenceCells();
  payloadCells();

  const Tally real = sweep<Attribution>(false, false, false);
  report("real rule, faithful model", real);
  if (real.counter) fail("real rule has a counterexample on the faithful model: " + real.firstCounter);
  if (real.live) fail("real rule misses a promised outcome on the faithful model: " + real.firstLive);
  if (!real.merged || !real.merged2 || !real.anchor || !real.restore)
    fail("faithful sweep is vacuous (a class of outcome never occurred)");

  // The generator has to be able to see the dangers.
  const Tally old = sweep<OldRule>(false, false, false);
  report("old rule (3.2 as first written)", old);
  if (!old.counter) fail("generator found no counterexample for the old rule");
  const Tally snap = sweep<SnapshotP>(false, false, false);
  report("P = transaction-start snapshot", snap);
  if (!snap.counter) fail("generator found no counterexample for the snapshot P");
  const Tally nofence = sweep<Attribution>(false, false, true);
  report("real rule without the fence", nofence);
  if (!nofence.counter) fail("generator found no counterexample without the fence");
  const Tally p4 = sweep<Attribution>(true, false, false);
  report("real rule, P4 broken", p4);
  if (!p4.counter) fail("generator found no counterexample with P4 broken");

  // Registered limit: coincident rectangles.  Counted, not failed.
  const Tally co = sweep<Attribution>(false, true, false);
  report("real rule, coincident rects (limit)", co);
  if (!co.counter) fail("coincident-rect sweep found nothing: the limit's model is not exercised");

  if (gFailures) {
    std::printf("%d failure(s)\n", gFailures);
    return 1;
  }
  std::printf("ok\n");
  return 0;
}
