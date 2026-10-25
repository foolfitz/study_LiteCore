// Actual unipoll adapter. The pure runOnePoll helper supplies the same
// reply-first, one-command and nonblocking rules exercised by the unit tests.
struct OrderedPollEngine {
  probe::poll::Inputs pollInputs() {
    std::lock_guard<std::mutex> lock(gState.mutex);
    return {gState.commands.size(), static_cast<bool>(gOrderedReply)};
  }
  void recordPoll(const probe::poll::Inputs &in, probe::poll::Step step) {
#ifdef OXSDK_E2_V23_DIAGNOSTIC
    static std::uint64_t poll = 0;
    std::uint32_t requestId = 0;
    if (step == probe::poll::Step::SendReply)
      requestId = gOrderedCommand.requestId;
    else if (step == probe::poll::Step::DispatchOne) {
      std::lock_guard<std::mutex> lock(gState.mutex);
      requestId = gState.commands.front().requestId;
    }
    std::ostringstream json;
    json << "{\"type\":\"v23-poll\",\"poll\":" << ++poll
         << ",\"queued\":" << in.queued << ",\"drained\":"
         << (step == probe::poll::Step::DispatchOne ? 1 : 0)
         << ",\"replyPending\":" << (in.replyPending ? "true" : "false")
         << ",\"reply\":" << (step == probe::poll::Step::SendReply ? "true" : "false")
         << ",\"requestId\":" << requestId << "}";
    emitJson(json.str());
#else
    (void)in;
    (void)step;
#endif
  }
  void sendPendingReply() {
    auto reply = std::move(gOrderedReply);
    gOrderedReply = {};
    gOrderedComposing = true;
    try {
      reply();
    } catch (const std::exception &error) {
      emitSdkError(gOrderedCommand.requestId, gOrderedCommand.documentHandle,
                   "ordered-reply", "MUTATION_OUTCOME_UNKNOWN", error.what());
    } catch (...) {
      emitSdkError(gOrderedCommand.requestId, gOrderedCommand.documentHandle,
                   "ordered-reply", "MUTATION_OUTCOME_UNKNOWN", "reply composition failed");
    }
    gOrderedComposing = false;
    finishAsynchronous(gOrderedCommand.requestId);
    gEditorPending = EditorPendingOperation{};
    gOrderedProof = OrderedCommandProof{};
  }
  void dispatchOne() {
    Command command;
    bool cancelled = false;
    {
      std::lock_guard<std::mutex> lock(gState.mutex);
      command = std::move(gState.commands.front());
      gState.commands.pop_front();
      if (command.sdk) {
        gState.pendingRequests.erase(command.requestId);
        cancelled = gState.cancelledRequests.erase(command.requestId) != 0;
        if (!cancelled)
          gState.executingRequest = command.requestId;
      }
    }
    gOrderedCommand = command;
    gOrderedProof = OrderedCommandProof{};
    gOrderedDispatching = true;
    executeQueuedCommand(command, cancelled);
    gOrderedDispatching = false;
  }
};

int mainLoopPollCallbackImpl(void *, int) {
  static bool inOrderedPoll = false;
  OrderedPollEngine engine;
  return probe::poll::runOnePoll(engine, inOrderedPoll);
}
