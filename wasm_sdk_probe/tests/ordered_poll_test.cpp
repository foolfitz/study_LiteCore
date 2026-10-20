#include "ordered_poll.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <string>
#include <vector>

// SPEC-M3-ordered-commands 15.4 (ruling 2 2.5 item 2(a)): the engine unit red
// cases for the poll, where the rule lives.  Each property is checked on the
// new poll (src/ordered_poll.hpp), which must pass, and on the variant that
// breaks it, which must fail on the same inputs -- among them today's mainloop
// drain, transcribed from probe_engine.cpp `mainLoopPollCallbackImpl` and
// `mainLoopDrainCommands` (pe:6688-6825) and `mainLoopAnyInputCallback`
// (pe:6845-6851).
//
//   P1 one per poll    two commands queued, one poll: exactly one dispatched.
//   P2 anyInput        a pending reply with nothing queued is input.
//   P3 reply first     a pending reply and a queued command: the reply goes,
//                      the command stays.
//   P4 never waits     an idle poll with timeout -1 returns without waiting.
//   P5 alternation     (form 1 over generated arrivals) between any two
//                      dispatches there is the first one's reply.
//   P7 reply latency   with a scheduler that is never idle (the poll runs
//                      only when anyInput says so), every reply is sent on
//                      the tick after its command: the old anyInput leaves
//                      the last reply of a burst waiting for the next command.
//   P6 re-entrancy     a dispatch that pumps the loop does not nest a second
//                      dispatch, and the guard is cleared after an exception.

namespace {
namespace pl = probe::poll;

int gFailures = 0;
void check(bool condition, const std::string &what) {
  if (!condition) {
    ++gFailures;
    std::printf("FAIL %s\n", what.c_str());
  }
}

struct Fake {
  std::deque<int> queue;
  int pending = 0; // the id whose reply is due, 0 for none
  int waits = 0;
  std::vector<std::string> log; // "D<id>" dispatched, "R<id>" replied
  std::vector<int> logTick;     // the tick of each log entry
  int tick = 0;
  std::vector<std::size_t> depthAtEntry;
  bool *inPoll = nullptr;
  int (*pump)(Fake &) = nullptr; // a dispatch that re-enters the loop
  bool throwOnDispatch = false;

  pl::Inputs pollInputs() const { return {queue.size(), pending != 0}; }
  void recordPoll(const pl::Inputs &in, pl::Step) {
    depthAtEntry.push_back(in.queued);
  }
  void sendPendingReply() {
    log.push_back("R" + std::to_string(pending));
    logTick.push_back(tick);
    pending = 0;
  }
  void dispatchOne() {
    const int id = queue.front();
    queue.pop_front();
    log.push_back("D" + std::to_string(id));
    logTick.push_back(tick);
    if (throwOnDispatch)
      throw 1;
    pending = id; // the command returned; its reply is due at the next poll
    if (pump)
      pump(*this);
  }
};

using Poll = int (*)(Fake &, bool &, int timeoutUs);

int newPoll(Fake &f, bool &inPoll, int) { return pl::runOnePoll(f, inPoll); }

// Today's mainloop poll, transcribed: drain every queued command; if that did
// nothing and the timeout is not zero, wait (bounded at 1 s for -1) for a
// command or a wake, then drain again.  It has no notion of a pending reply:
// replies are emitted from inside the callbacks.  Modelled here by sending a
// due reply the moment the next command is about to run -- the most generous
// reading, and it still fails P1, P4 and P5.
int oldPoll(Fake &f, bool &inPoll, int timeoutUs) {
  if (inPoll)
    return 0;
  inPoll = true;
  auto drain = [&f] {
    int n = 0;
    while (!f.queue.empty()) {
      f.dispatchOne();
      ++n;
    }
    return n;
  };
  f.depthAtEntry.push_back(f.queue.size());
  int processed = drain();
  if (processed == 0 && timeoutUs != 0) {
    ++f.waits;
    processed = drain();
  }
  if (f.pending)
    f.sendPendingReply();
  inPoll = false;
  return processed;
}

// The new poll with the order of the two branches swapped.  A reply still due
// when the next command runs is composed after it -- from a cache that command
// has already changed -- so it is logged after the dispatch.
int commandFirstPoll(Fake &f, bool &inPoll, int) {
  if (inPoll)
    return 0;
  inPoll = true;
  int done = 0;
  f.depthAtEntry.push_back(f.queue.size());
  if (!f.queue.empty()) {
    const int replying = f.pending;
    f.dispatchOne();
    if (replying) {
      f.log.push_back("R" + std::to_string(replying));
      f.logTick.push_back(f.tick);
    }
    done = 1;
  } else if (f.pending) {
    f.sendPendingReply();
    done = 1;
  }
  inPoll = false;
  return done;
}

bool oldAnyInput(const pl::Inputs &in) { return in.queued > 0; }

bool p1(Poll poll) {
  Fake f;
  f.queue = {1, 2};
  bool inPoll = false;
  poll(f, inPoll, 0);
  const int dispatched = static_cast<int>(
      std::count_if(f.log.begin(), f.log.end(),
                    [](const std::string &e) { return e[0] == 'D'; }));
  return dispatched == 1 && f.queue.size() == 1;
}

bool p3(Poll poll) {
  Fake f;
  f.pending = 7;
  f.queue = {8};
  bool inPoll = false;
  poll(f, inPoll, 0);
  return f.log.size() == 1 && f.log[0] == "R7" && f.queue.size() == 1;
}

bool p4(Poll poll) {
  Fake f;
  bool inPoll = false;
  poll(f, inPoll, -1);
  return f.waits == 0;
}

// P5 and P7: a tick loop over generated arrivals.  Each tick: arrivals, then
// the flush of whatever the last command posted (nothing to model: the fake's
// reply is already "due"), then the poll if anyInput -- or, when `idleEvery`
// is not 0, on every idleEvery-th tick as well (the scheduler went idle).  The
// properties are read off the log.  `maxLatency` is the most ticks a reply
// may follow its dispatch by; 0 means unchecked.
bool p5(Poll poll, bool (*anyInput)(const pl::Inputs &), std::uint32_t seed,
        int idleEvery, int maxLatency, std::string &why) {
  Fake f;
  bool inPoll = false;
  int next = 1;
  std::uint32_t x = seed;
  for (f.tick = 0; f.tick < 400; ++f.tick) {
    x = x * 1664525u + 1013904223u;
    const int arrivals = (x >> 24) % 4 == 0 ? static_cast<int>((x >> 16) % 3) : 0;
    for (int i = 0; i < arrivals; ++i)
      f.queue.push_back(next++);
    if (anyInput(f.pollInputs()) || (idleEvery && f.tick % idleEvery == 0))
      poll(f, inPoll, 0);
  }
  for (int spin = 0; (!f.queue.empty() || f.pending) && spin < 10000; ++spin, ++f.tick)
    poll(f, inPoll, 0);
  int lastDispatched = 0, lastTick = 0;
  bool replied = true;
  for (std::size_t k = 0; k < f.log.size(); ++k) {
    const std::string &e = f.log[k];
    const int id = std::stoi(e.substr(1));
    if (e[0] == 'D') {
      if (!replied) {
        why = "D" + std::to_string(id) + " before R" + std::to_string(lastDispatched);
        return false;
      }
      lastDispatched = id;
      lastTick = f.logTick[k];
      replied = false;
    } else {
      if (id != lastDispatched || replied) {
        why = "R" + std::to_string(id) + " out of order";
        return false;
      }
      if (maxLatency && f.logTick[k] - lastTick > maxLatency) {
        why = "R" + std::to_string(id) + " " +
              std::to_string(f.logTick[k] - lastTick) + " ticks after its dispatch";
        return false;
      }
      replied = true;
    }
  }
  if (next - 1 == 0) {
    why = "no command arrived (vacuous)";
    return false;
  }
  if (!replied)
    why = "D" + std::to_string(lastDispatched) + " never replied";
  return replied;
}

bool p5All(Poll poll, bool (*anyInput)(const pl::Inputs &), int idleEvery,
           int maxLatency, std::string &why) {
  for (std::uint32_t seed = 1; seed <= 200; ++seed)
    if (!p5(poll, anyInput, seed, idleEvery, maxLatency, why)) {
      why = "seed " + std::to_string(seed) + ": " + why;
      return false;
    }
  return true;
}

int pumpOnce(Fake &f) { return pl::runOnePoll(f, *f.inPoll); }
} // namespace

int main() {
  // P1
  check(p1(newPoll), "P1 new: two queued, one poll did not dispatch exactly one");
  check(!p1(oldPoll), "P1 red: the old drain-until-empty passed");
  // P2
  check(pl::anyInput({0, true}), "P2 new: a pending reply is not input");
  check(!oldAnyInput({0, true}), "P2 red: the old anyInput saw a pending reply");
  check(pl::anyInput({1, false}) && !pl::anyInput({0, false}),
        "P2 new: the queue term is wrong");
  // P3
  check(p3(newPoll), "P3 new: the reply did not go first");
  check(!p3(commandFirstPoll), "P3 red: command-first passed");
  // P4
  check(p4(newPoll), "P4 new: the idle poll waited");
  check(!p4(oldPoll), "P4 red: the old idle poll did not wait");
  // P5
  std::string why;
  // The reason is filled in by the call, so the call comes first.
  bool held = p5All(newPoll, pl::anyInput, 3, 0, why);
  check(held, "P5 new: " + why);
  check(!p5All(oldPoll, pl::anyInput, 3, 0, why), "P5 red: the old drain alternated");
  check(!p5All(commandFirstPoll, pl::anyInput, 3, 0, why),
        "P5 red: command-first alternated");
  // P7
  held = p5All(newPoll, pl::anyInput, 0, 1, why);
  check(held, "P7 new: " + why);
  check(!p5All(newPoll, oldAnyInput, 0, 1, why),
        "P7 red: the old anyInput answered every reply on the next tick");
  // P6
  {
    Fake f;
    bool inPoll = false;
    f.inPoll = &inPoll;
    f.pump = pumpOnce;
    f.queue = {1, 2};
    pl::runOnePoll(f, inPoll);
    check(f.log.size() == 1 && f.log[0] == "D1",
          "P6: a pumping dispatch nested a second unit of work");
    check(!inPoll, "P6: the guard stayed set");
  }
  {
    Fake f;
    bool inPoll = false;
    f.throwOnDispatch = true;
    f.queue = {1, 2};
    try {
      pl::runOnePoll(f, inPoll);
    } catch (int) {
    }
    check(!inPoll, "P6: the guard stayed set after an exception");
    f.throwOnDispatch = false;
    check(pl::runOnePoll(f, inPoll) == 1, "P6: the poll after an exception did nothing");
  }
  // The 15.4 record: the depth at entry is what the diagnostic histograms.
  {
    Fake f;
    bool inPoll = false;
    f.queue = {1, 2, 3};
    pl::runOnePoll(f, inPoll);
    check(f.depthAtEntry.size() == 1 && f.depthAtEntry[0] == 3,
          "15.4: the depth at entry was not recorded");
  }
  std::printf("ordered poll: P1-P6 on the new poll and their red variants, "
              "failures %d\n",
              gFailures);
  return gFailures == 0 ? 0 : 1;
}
