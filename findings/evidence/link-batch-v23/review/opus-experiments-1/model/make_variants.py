#!/usr/bin/env python3
"""Opus seat, review 1, Q9: build scratch variants of the model test's C mode.

Every variant is base.cpp (the committed test, sha256 6201a62d...) with its main() renamed and a small
driver appended that runs only the SECTION D sweep (all keys, the four shapes) with one mutation.
Nothing here edits the repository; base.cpp is a scratch copy.

Variants:
  baseline        the committed C mode (expect forged 0, differs 0)
  E2_drain_all    C's poll executes every ready action, not one (the poll "does one thing" removed)
  E3_queued_flush C's poll may run while a flush is queued but not started (only "not mid-flush" kept),
                  i.e. svpinst.cxx:442-444's "no poll while a user event is pending" removed by itself
  E5_distinct     baseline, but also counts distinct C-relevant scenarios (lag knobs C never reads
                  dropped from the key) to compare with the printed "runs"
"""
import pathlib
import sys

here = pathlib.Path(__file__).resolve().parent
base = (here / 'base.cpp').read_text()
assert base.count('int main() {') == 1
base = base.replace('int main() {', 'int original_main() {')

POLL_ONE = """      for (std::size_t i = 0; i < actions.size(); ++i) {
        if (actions[i].readyAt > tick) continue;
        const Action a = actions[i];
        actions.erase(actions.begin() + static_cast<long>(i));
        execute(a);
        return;
      }
      return;"""
assert base.count(POLL_ONE) == 1, 'poll body not found'
POLL_ALL = """      for (bool again = true; again;) {
        again = false;
        for (std::size_t i = 0; i < actions.size(); ++i) {
          if (actions[i].readyAt > tick) continue;
          const Action a = actions[i];
          actions.erase(actions.begin() + static_cast<long>(i));
          execute(a);
          again = true;
          break;
        }
      }
      return;"""
GATE = "if (!(kn.syncPollMidFlush ? fifo.empty() : lokIdle())) return;"
assert base.count(GATE) == 1
GATE_QUEUED = "if (!(kn.syncPollMidFlush ? fifo.empty() : !midFlush)) return;"

DRIVER = r'''
int main() {
  Knobs c; c.sync = true; c.flagDisabled = true;
  static const char *follows[] = {"moves only", "Backspace", "typing", "inline format"};
  long forged = 0, differs = 0, runs = 0;
  for (int mode : {0, 1, 2, 3}) {
    const PhaseC t = sweepC(c, KeySet::Full, mode);
    std::printf("%-14s runs=%ld writerDiffers=%ld forged=%ld staleU=%ld refused=%ld undecided=%ld guard=%ld\n",
                follows[mode], t.runs, t.differs, t.forged, t.stale, t.refused, t.undecided, t.guard);
    for (const auto &[k, v] : t.first) std::printf("    first %-20s %s\n", k.c_str(), v.c_str());
    forged += t.forged; differs += t.differs; runs += t.runs;
#ifdef COUNT_DISTINCT
    std::set<std::string> keys;
    forEachScenario(mode, KeySet::Full, [&](const Scenario &sc0) {
      Scenario sc = sc0;
      // knobs the C path never reads: the move deadline lag, the barrier's two lags, the earlier
      // operation's deadline and the select's two flush gaps (registerMove/startEarlier/resolveBackspace
      // return before any of them is used when kn.sync is set)
      sc.lagDeadline = 0; sc.lagB1 = 0; sc.lagV = 0; sc.eDeadline = 0; sc.gapRS = 0; sc.gapSE = 0;
      keys.insert(describe(sc));
    });
    std::printf("    distinct C-relevant scenarios: %zu (printed runs %ld)\n", keys.size(), t.runs);
#endif
  }
  std::printf("TOTAL runs=%ld forged=%ld writerDiffers=%ld\n", runs, forged, differs);
  return 0;
}
'''

variants = {
    'baseline': base,
    'E2_drain_all': base.replace(POLL_ONE, POLL_ALL),
    'E3_queued_flush': base.replace(GATE, GATE_QUEUED),
    'E5_distinct': '#define COUNT_DISTINCT 1\n' + base,
}
for name, src in variants.items():
    (here / f'{name}.cpp').write_text(src + DRIVER)
    print(name)
