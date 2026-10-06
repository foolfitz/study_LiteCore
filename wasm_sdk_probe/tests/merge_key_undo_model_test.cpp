#include "merge_key_undo.hpp"

#include <cstdio>
#include <deque>
#include <string>
#include <utility>
#include <vector>

// SPEC-M3-paragraph-merge M1-2 (as amended in 10.2, 13.1, 14.6, 16.4): the
// E shape's attribution driven by callback sequences GENERATED from a model
// of LOK, not listed by hand.
//
// The model, and what each part of it stands for:
//   - one FIFO queue of posted events and flushes (P1); processing an event
//     schedules a flush only when none is pending (init.cxx:2578-2582);
//   - a flush computes every payload first and then delivers them (P2,
//     invoke(): enqueueUpdatedTypes, then the queue): START, END,
//     TEXT_SELECTION, then the caret (P3); TEXT_SELECTION and the caret are
//     dropped when equal to the last sent, START/END never are (14.1); a
//     table-cell selection sends no START/END (14.1);
//   - rectangles as R0b measured them; the caret's shape depends on whether
//     there is a mark (crsrsh.cxx:2402-2409);
//   - the engine's Escape is synchronous (postUnoCommand with a listener,
//     unoctitm.cxx:654-657) and runs at an event boundary (the SolarMutex);
//     its posted keys are appended to the queue; both happen `lag` events
//     after the decision;
//   - text between positions, so two different ranges can hold the same
//     text (an empty paragraph next to a paragraph end);
//   - relayouts (permanent, or moving back right after: the 15.1 family),
//     resends of an unchanged caret, an event still queued when K1 is posted
//     or processed with its flush after (straddling), and a P4-off switch: K2
//     flushes once with its point half-way.
//
// The property, checked when LOK processes the key: no selection, and the
// caret is where K1 ran.  Liveness: with nothing disturbing the transaction,
// a K2 that returns to the origin merges, a table or a queued event refuses at
// K1, a K2 that lands elsewhere refuses at K2.  An Escape executed with no
// selection is counted separately (in Writer it toggles full screen,
// view2.cxx:1276-1281).
//
// Red cases in the same generator: no K2 fence (text check alone) and P4
// broken must produce counterexamples; Escape #2 sent before K2's selection is
// seen must produce no counterexample and no merge it should not -- it can
// only lose the proof (liveness).  Coincident rectangles are reported.

using namespace probe::merge;

namespace {

int gFailures = 0;
void fail(const std::string &what) {
  ++gFailures;
  std::printf("FAIL %s\n", what.c_str());
}

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
  std::string text; // text[i] lies between positions i and i+1
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
  std::string range(int a, int b) const {
    return a < b ? text.substr(a, b - a) : text.substr(b, a - b);
  }
};

// Line 0 as boundaries.odt, line 1 as P27 (a taller portion).  Positions 1-2
// and 2-3 both hold a paragraph end: the same text in two ranges.
Layout makeLayout(bool alias) {
  Layout l;
  l.lines = {{1000, 276, 0, 276}, {1418, 400, 52, 348}};
  l.pos = {{0, 1418}, {0, 2000}, {0, 2991}, {1, 1418}, {1, 2138}, {1, 3000}};
  l.text = "a\n\nb\n";
  if (alias)
    l.pos[4].x = 1418; // a zero-width portion: positions 3 and 4 share a rect
  return l;
}

enum class EventMode { None, Flushed, Straddling, Queued };
enum class Outcome { Merged, RefusedK1, RefusedK2, NoDecision, Counterexample };

struct Scenario {
  bool backward;
  int q;          // where K1 runs
  EventMode e;
  int s;          // the caret before the event (== q when None)
  bool table;
  int k2;         // where K2 leaves its point (q when Writer behaves)
  int relayoutAt; // 0 none, 1 before K1, 2 after K1, 3 at Escape #1, 4 after K2, 5 at Escape #2
  bool bounce;
  int intermediate; // P4 off: K2 flushes with its point here first; -1 = off
  bool alias;
  int lag[4];       // Escape #1, K2, Escape #2, key
  bool resend;
  bool escDelay;    // the Escape is marked sent, then waits two LOK events for
                    // the SolarMutex before it runs (a flush may land between)
};

struct Ev {
  enum Kind { E, K1, K2, Relayout, RelayoutBack, Key, Flush } kind;
};

struct Run {
  const Scenario &sc;
  Layout lay;
  Attribution tr;
  bool noK2Fence = false, eagerEsc2 = false;
  std::deque<Ev> q;
  int caret;
  bool hasSel = false;
  int selAnchor = 0, selPoint = 0;
  bool flushPending = false;
  std::string lastSel;
  Rect lastCaret;
  bool bouncePending = false;
  int kOrigin = -1;
  std::string k1Text;
  Outcome outcome = Outcome::NoDecision;
  bool decided = false;
  int escNoSel = 0;
  Attribution::Phase acted = Attribution::Phase::Idle;
  enum Action { Esc1, PostK2, Esc2, PostKey, EscRun };
  struct Pending { Action action; int countdown; };
  std::vector<Pending> pending;

  explicit Run(const Scenario &s) : sc(s), lay(makeLayout(s.alias)) {
    caret = s.e == EventMode::None ? s.q : s.s;
    lastCaret = lay.caret(caret, false);
    tr.onCaret(lastCaret); // the caret at rest, delivered long ago
  }

  void schedule() {
    if (!flushPending) {
      flushPending = true;
      q.push_back({Ev::Flush});
    }
  }

  void flush() {
    flushPending = false;
    // Every payload is computed before any is delivered.
    std::vector<std::pair<int, Rect>> out; // 0 START, 1 END, 2 caret
    const bool area = hasSel && selAnchor != selPoint;
    if (area && !sc.table) {
      const int lo = selAnchor < selPoint ? selAnchor : selPoint;
      const int hi = selAnchor < selPoint ? selPoint : selAnchor;
      out.push_back({0, lay.anchor(lo)});
      out.push_back({1, lay.anchor(hi)});
    }
    std::string sel;
    if (area)
      sel = "S" + std::to_string(selAnchor) + "-" + std::to_string(selPoint) + "@" +
            std::to_string(lay.shift);
    const bool sendSel = sel != lastSel;
    const Rect c = lay.caret(caret, hasSel);
    const bool sendCaret = c != lastCaret;
    for (const auto &[kind, r] : out) {
      if (kind == 0) tr.onSelectionStart(r);
      else tr.onSelectionEnd(r);
    }
    if (sendSel) {
      lastSel = sel;
      tr.onTextSelection(!sel.empty());
      react();
    }
    if (sendCaret) {
      lastCaret = c;
      tr.onCaret(c);
      react();
      if (sc.resend) { tr.onCaret(c); react(); }
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
    case Ev::K1:
      kOrigin = caret;
      hasSel = true;
      selAnchor = caret;
      selPoint = caret + (sc.backward ? -1 : 1);
      caret = selPoint;
      k1Text = lay.range(selAnchor, selPoint);
      break;
    case Ev::K2:
      // Shift+arrow keeps an existing mark (SttSelect, select.cxx:407-423).
      if (!hasSel)
        selAnchor = caret;
      hasSel = true;
      if (sc.intermediate >= 0) {
        selPoint = caret = sc.intermediate;
        flush(); // P4 broken: a flush inside K2's own processing
      }
      selPoint = caret = sc.k2;
      break;
    case Ev::Relayout:
      lay.shift += 100;
      bouncePending = sc.bounce;
      break;
    case Ev::RelayoutBack:
      lay.shift -= 100;
      break;
    case Ev::Key:
      if (!decided)
        decide(!hasSel && caret == kOrigin ? Outcome::Merged : Outcome::Counterexample);
      return;
    case Ev::Flush:
      flush();
      return;
    }
    schedule();
  }

  // The synchronous Escape, at an event boundary.
  void escape() {
    if (!hasSel || selAnchor == selPoint) {
      // FN_ESCAPE needs HasSelection(), which an empty mark is not
      // (crsrsh.cxx:3040-3047): full screen, not a collapse.
      ++escNoSel;
      return;
    }
    hasSel = false; // EnterStdMode: ClearMark, the point stays
    schedule();
  }

  void execute(Action a) {
    switch (a) {
    case Esc1:
      if (sc.relayoutAt == 3) q.push_back({Ev::Relayout});
      if (tr.escapeSent()) runEscape();
      return;
    case PostK2:
      if (tr.returnPosted()) {
        q.push_back({Ev::K2});
        if (sc.relayoutAt == 4) q.push_back({Ev::Relayout});
        if (eagerEsc2) later(Esc2); // red case: no wait for K2's selection
      }
      return;
    case Esc2:
      if (sc.relayoutAt == 5) q.push_back({Ev::Relayout});
      if (eagerEsc2 ? true : tr.escapeSent()) runEscape();
      return;
    case PostKey:
      q.push_back({Ev::Key});
      return;
    case EscRun:
      escape();
      return;
    }
  }
  void later(Action a) { pending.push_back({a, sc.lag[a] + 1}); }
  void runEscape() {
    if (sc.escDelay) pending.push_back({EscRun, 2});
    else escape();
  }
  void tick() {
    std::vector<Action> due;
    for (std::size_t i = 0; i < pending.size();) {
      if (--pending[i].countdown == 0) {
        due.push_back(pending[i].action);
        pending.erase(pending.begin() + static_cast<long>(i));
      } else {
        ++i;
      }
    }
    for (Action a : due) execute(a);
  }

  void react() {
    if (decided || tr.phase() == acted)
      return;
    acted = tr.phase();
    using P = Attribution::Phase;
    switch (acted) {
    case P::UnitSeen:
      if (!tr.fenceHolds()) { decide(Outcome::RefusedK1); return; }
      later(Esc1);
      return;
    case P::Collapsed1:
      later(PostK2);
      return;
    case P::Returned:
      if (lay.range(selAnchor, selPoint) != k1Text ||
          (!noK2Fence && !tr.returnFenceHolds())) {
        decide(Outcome::RefusedK2);
        return;
      }
      if (!eagerEsc2) later(Esc2);
      return;
    case P::Ready:
      later(PostKey);
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
    for (int guard = 0; (!q.empty() || !pending.empty()) && guard < 2000; ++guard) {
      if (!q.empty()) {
        Ev ev = q.front();
        q.pop_front();
        process(ev);
      }
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
      q.push_back({Ev::E}); // posted, not yet processed, when K1 is posted
    if (sc.relayoutAt == 1)
      q.push_back({Ev::Relayout});
    tr.beginTransaction(sc.backward);
    q.push_back({Ev::K1});
    if (sc.relayoutAt == 2)
      q.push_back({Ev::Relayout});
    drain();
    return outcome;
  }
};

struct Tally {
  long runs = 0, merged = 0, k1 = 0, k2 = 0, none = 0, counter = 0, live = 0, escNoSel = 0;
  std::string firstCounter, firstLive;
};

std::string describe(const Scenario &s) {
  static const char *modes[] = {"none", "flushed", "straddling", "queued"};
  return std::string(s.backward ? "back" : "fwd") + " q=" + std::to_string(s.q) + " e=" +
         modes[static_cast<int>(s.e)] + " s=" + std::to_string(s.s) + (s.table ? " table" : "") +
         " k2=" + std::to_string(s.k2) + " relayout@" + std::to_string(s.relayoutAt) +
         (s.bounce ? " bounce" : "") + " mid=" + std::to_string(s.intermediate) +
         (s.alias ? " alias" : "") + " lag=" + std::to_string(s.lag[0]) + std::to_string(s.lag[1]) +
         std::to_string(s.lag[2]) + std::to_string(s.lag[3]) + (s.resend ? " resend" : "") +
         (s.escDelay ? " escDelay" : "");
}

bool liveOutcome(const Scenario &s, Outcome o) {
  if (s.relayoutAt != 0 || s.intermediate >= 0 || s.alias)
    return true;
  if (s.table || s.e == EventMode::Queued)
    return o == Outcome::RefusedK1;
  if (s.k2 == s.q)
    return o == Outcome::Merged;
  if (s.k2 == s.q + (s.backward ? -1 : 1))
    return o == Outcome::NoDecision; // K2 did not move: nothing selected, the deadline refuses
  return o == Outcome::RefusedK2;
}

Tally sweep(bool p4off, bool coincidence, bool noK2Fence, bool eagerEsc2) {
  Tally t;
  const int n = 6;
  for (int b = 0; b < 2; ++b)
    for (int qq = 0; qq < n; ++qq) {
      if ((b && qq == 0) || (!b && qq == n - 1)) continue;
      for (int em = 0; em < 4; ++em)
        for (int ss = 0; ss < n; ++ss) {
          if ((em == 0) != (ss == qq)) continue;
          for (int tb = 0; tb < 2; ++tb)
            for (int k2 = 0; k2 < n; ++k2)
              for (int ra = 0; ra < 6; ++ra)
                for (int bo = 0; bo < (ra ? 2 : 1); ++bo)
                  for (int mid = -1; mid < (p4off ? n : 0); ++mid)
                    for (int al = 0; al < (coincidence ? 2 : 1); ++al)
                      for (int lg = 0; lg < 16; ++lg)
                        for (int rs = 0; rs < 2; ++rs)
                        for (int ed = 0; ed < 2; ++ed) {
                          Scenario sc{b != 0, qq, static_cast<EventMode>(em), ss, tb != 0, k2,
                                      ra, bo != 0, mid, al != 0,
                                      {lg & 1, (lg >> 1) & 1, (lg >> 2) & 1, (lg >> 3) & 1},
                                      rs != 0, ed != 0};
                          Run run(sc);
                          run.noK2Fence = noK2Fence;
                          run.eagerEsc2 = eagerEsc2;
                          const Outcome o = run.go();
                          ++t.runs;
                          t.escNoSel += run.escNoSel;
                          switch (o) {
                          case Outcome::Merged: ++t.merged; break;
                          case Outcome::RefusedK1: ++t.k1; break;
                          case Outcome::RefusedK2: ++t.k2; break;
                          case Outcome::NoDecision: ++t.none; break;
                          case Outcome::Counterexample:
                            if (!t.counter) t.firstCounter = describe(sc);
                            ++t.counter;
                            break;
                          }
                          if (!liveOutcome(sc, o)) {
                            if (!t.live) t.firstLive = describe(sc);
                            ++t.live;
                          }
                        }
        }
    }
  return t;
}

void report(const char *name, const Tally &t) {
  std::printf("%-36s runs=%ld merged=%ld refusedK1=%ld refusedK2=%ld none=%ld counter=%ld live=%ld escNoSel=%ld\n",
              name, t.runs, t.merged, t.k1, t.k2, t.none, t.counter, t.live, t.escNoSel);
  if (t.counter) std::printf("    first counterexample: %s\n", t.firstCounter.c_str());
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

void phaseCells() {
  // K2 is never posted before Escape #1's empty selection is seen.
  Attribution a;
  a.onCaret({2991, 1418, 0, 276});
  a.beginTransaction(false);
  a.onSelectionStart({2991, 1418, 0, 275});
  a.onTextSelection(true);
  if (a.phase() != Attribution::Phase::UnitSeen || !a.escapeSent())
    fail("phase: K1's selection did not allow Escape #1");
  if (a.returnPosted())
    fail("phase: K2 allowed before Escape #1's empty selection");
  a.onTextSelection(true); // a relayout re-sending the selection: not the collapse
  if (a.phase() != Attribution::Phase::AwaitEmpty1)
    fail("phase: a non-empty selection counted as Escape #1's collapse");
  a.onTextSelection(false);
  a.onSelectionStart({2991, 1418, 0, 275}); // stale: no selection exists now
  if (!a.returnPosted())
    fail("phase: K2 refused after the collapse");
  a.onTextSelection(true); // K2's flush without START (cannot happen; defensive)
  if (a.hasPoint())
    fail("phase: a START from before K2 was read as K2's point");
  if (!a.escapeSent())
    fail("phase: Escape #2 refused after K2's selection");
  a.onTextSelection(true); // a relayout re-sending K2's selection: not the collapse
  if (a.phase() != Attribution::Phase::AwaitEmpty2)
    fail("phase: a non-empty selection counted as Escape #2's collapse");
  a.onTextSelection(false);
  if (a.phase() != Attribution::Phase::Ready)
    fail("phase: Escape #2's empty selection did not make the key ready");
}

// Mutants of merge_key_undo.hpp that this file does not kill, and why they are
// equivalent (spec 15.1, 16.4):
//   - AwaitReturn accepting an empty TEXT_SELECTION: after Escape #1's empty
//     selection was delivered, another empty one is deduplicated against the
//     last sent (init.cxx:2525-2537); nothing else of ours is in flight.
//   - not clearing the anchors on TEXT_SELECTION: they are also cleared by
//     every caret, by beginTransaction and by returnPosted, and are only read
//     at the first non-empty TEXT_SELECTION after one of those.
// The generator does not produce a relayout flush between an Escape being
// marked sent and running (it would need the engine to lose the SolarMutex
// race for longer than one flush), so the "only an empty selection is the
// collapse" rule is held by the phase cells above, not by the sweep.

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
  phaseCells();
  payloadCells();

  const Tally real = sweep(false, false, false, false);
  report("E shape, faithful model", real);
  if (real.counter) fail("counterexample on the faithful model: " + real.firstCounter);
  if (real.live) fail("liveness miss on the faithful model: " + real.firstLive);
  if (real.escNoSel) fail("an Escape ran with no selection on the faithful model");
  if (!real.merged || !real.k1 || !real.k2)
    fail("faithful sweep is vacuous (an outcome class never occurred)");

  const Tally nofence = sweep(false, false, true, false);
  report("without the K2 fence (text check only)", nofence);
  if (!nofence.counter) fail("generator found no counterexample without the K2 fence");
  const Tally p4 = sweep(true, false, false, false);
  report("P4 broken (K2 flushes half-way)", p4);
  if (!p4.counter) fail("generator found no counterexample with P4 broken");
  const Tally eager = sweep(false, false, false, true);
  report("Escape #2 before K2's selection is seen", eager);
  if (eager.counter) fail("eager Escape #2 produced a wrong key, not just a lost proof");
  if (!eager.none && !eager.escNoSel) fail("eager Escape #2 changed nothing: the red case is not exercised");

  const Tally co = sweep(false, true, false, false);
  report("coincident rects (limit, reported)", co);

  if (gFailures) {
    std::printf("%d failure(s)\n", gFailures);
    return 1;
  }
  std::printf("ok\n");
  return 0;
}
