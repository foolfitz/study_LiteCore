#ifndef OXOFFICE_ORDERED_POLL_HPP
#define OXOFFICE_ORDERED_POLL_HPP

// SPEC-M3-ordered-commands 5.2 as corrected by 15.2, and 15.4: what one call of
// the poll callback does under candidate C (unipoll).  The pure half, so that
// tests/ordered_poll_test.cpp can hold the old drain against the new rules.
//
// The engine is the VCL main thread.  SvpSalInstance::ImplYield dispatches one
// user event per tick and returns if it did; otherwise it may run one scheduler
// task, and only then -- if that ran nothing, or if the client's anyInput says
// so -- calls the poll (5.2).  LOK's callback flush is a posted user event, so
// every callback a command causes has been delivered before the first poll
// after that command returns (N1a, measured natively).  Three rules follow,
// each with the defect of today's mainloop profile it replaces:
//
//   1. One unit of work per poll.  `mainLoopDrainCommands` ran every queued
//      command in one call, so with two queued the second ran before the
//      first's flush (facts sheet, mainloop profile gap 5).
//   2. A reply that is pending goes first, and it counts as input.  A command
//      that has returned is answered at the next poll (5.2); `anyInput` must
//      say so, or a long document's idle layout runs ahead of every reply
//      (`mainLoopAnyInputCallback` looked at the queue only).
//   3. The poll never waits.  The pacing is the 100 fps tick; the old idle
//      `wait_until` of up to one second blocked the main-loop tick itself.
//
// The re-entrancy guard is kept (5.7 rule 1 forbids a command to pump, but a
// core path that does -- an HTML or Markdown import's Reschedule -- must not
// nest a second dispatch inside the first).

#include <cstddef>

namespace probe {
namespace poll {

struct Inputs {
  std::size_t queued = 0;    // commands waiting in the engine's queue
  bool replyPending = false; // a command has returned; its reply is due now
};

enum class Step { SendReply, DispatchOne, Nothing };

inline Step choose(const Inputs &in) {
  if (in.replyPending)
    return Step::SendReply;
  if (in.queued > 0)
    return Step::DispatchOne;
  return Step::Nothing;
}

// 5.2's hard rule: anyInput = a command is queued or a reply is pending.
inline bool anyInput(const Inputs &in) {
  return in.queued > 0 || in.replyPending;
}

// One poll.  `Engine` provides:
//   Inputs pollInputs();             read under the engine's own locking
//   void recordPoll(const Inputs &, Step);   the 15.4 depth record
//   void sendPendingReply();         compose and emit the due reply
//   void dispatchOne();              pop one command and run it
// `inPoll` is the engine's re-entrancy flag (engine thread only).  Returns the
// units of work done: 0 or 1.  Nothing here waits.
template <class Engine> int runOnePoll(Engine &engine, bool &inPoll) {
  if (inPoll)
    return 0;
  // Cleared on every way out, an exception from the dispatch included: a flag
  // left set would make every later poll a no-op, a silent total wedge.
  struct Reset {
    bool &flag;
    ~Reset() { flag = false; }
  } reset{inPoll};
  inPoll = true;
  const Inputs in = engine.pollInputs();
  const Step step = choose(in);
  engine.recordPoll(in, step);
  int done = 0;
  switch (step) {
  case Step::SendReply:
    engine.sendPendingReply();
    done = 1;
    break;
  case Step::DispatchOne:
    engine.dispatchOne();
    done = 1;
    break;
  case Step::Nothing:
    break;
  }
  return done;
}

} // namespace poll
} // namespace probe

#endif
