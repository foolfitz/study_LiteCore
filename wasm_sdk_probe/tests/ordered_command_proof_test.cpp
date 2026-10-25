#include "ordered_command_proof.hpp"
#include "ordered_poll.hpp"

#include <cstdio>
#include <string>
#include <vector>

// Synthetic flush required by spec 16.4. This exercises the production poll
// helper with a cursor callback followed by a selection callback. The old
// callback-time composer is the red control on the identical input.
// Engine integration/routing is deliberately not established by this test.
namespace {
namespace proof = probe::orderedproof;
int failures = 0;
void check(bool ok, const char *name) {
  if (!ok) {
    ++failures;
    std::printf("FAIL %s\n", name);
  }
}
struct State {
  std::string cursor = "before-cursor", selection = "before-selection";
  bool operator==(const State &other) const {
    return cursor == other.cursor && selection == other.selection;
  }
};
struct Engine {
  int queued = 1;
  bool pending = false;
  bool callbackComposer = false;
  bool dispatchFailed = false;
  bool resultPresent = false;
  State cache;
  std::vector<State> replies;
  std::vector<proof::Verdict> verdicts;
  probe::poll::Inputs pollInputs() { return {static_cast<std::size_t>(queued), pending}; }
  void recordPoll(const probe::poll::Inputs &, probe::poll::Step) {}
  void dispatchOne() { --queued; pending = true; }
  void sendPendingReply() {
    replies.push_back(cache);
    verdicts.push_back(proof::atPoll(dispatchFailed, resultPresent));
    pending = false;
  }
  void callback(bool cursor) {
    if (cursor)
      cache.cursor = "after-cursor";
    else
      cache.selection = "after-selection";
    if (callbackComposer && pending)
      sendPendingReply();
  }
};

bool wholeFlush(bool oldComposer) {
  Engine engine;
  bool inPoll = false;
  engine.callbackComposer = oldComposer;
  probe::poll::runOnePoll(engine, inPoll);
  if (!engine.replies.empty())
    return false;
  engine.callback(true);
  engine.callback(false);
  engine.resultPresent = true;
  probe::poll::runOnePoll(engine, inPoll);
  return engine.replies.size() == 1 && engine.replies[0] == engine.cache &&
         engine.verdicts[0] == proof::Verdict::Available;
}

bool absentProof(bool dispatchFailed) {
  Engine engine;
  engine.dispatchFailed = dispatchFailed;
  bool inPoll = false;
  probe::poll::runOnePoll(engine, inPoll);
  // A cursor/selection flush does not substitute for UNO_COMMAND_RESULT.
  engine.callback(true);
  engine.callback(false);
  probe::poll::runOnePoll(engine, inPoll);
  const auto expected = dispatchFailed ? proof::Verdict::DispatchFailed
                                      : proof::Verdict::MutationUnknown;
  return engine.verdicts.size() == 1 && engine.verdicts[0] == expected &&
         !engine.pending && !probe::poll::anyInput(engine.pollInputs());
}
} // namespace

int main() {
  check(wholeFlush(false), "post-command poll contains cursor and selection");
  check(!wholeFlush(true), "red: callback-time reply must lose part of the flush");
  check(absentProof(false), "missing result refuses at first poll after dispatch");
  check(absentProof(true), "dispatch failure refuses at first poll");
  check(std::string(proof::errorCode(proof::Verdict::DispatchFailed)) ==
            "LOK_COMMAND_FAILED", "dispatch failure code");
  check(std::string(proof::errorCode(proof::Verdict::MutationUnknown)) ==
            "MUTATION_OUTCOME_UNKNOWN", "unknown mutation code");
  check(proof::errorCode(proof::Verdict::Available) == nullptr, "proof has no refusal");
  check(proof::atPoll(true, true) == proof::Verdict::DispatchFailed,
        "a stale proof cannot override dispatch failure");
  std::printf("ordered command proof: %d failures\n", failures);
  return failures ? 1 : 0;
}
