// Candidate C state: owned by the engine thread. No callback owns a reply.
struct OrderedUnoProof {
  bool seen = false;
  std::string payload;
  std::uint64_t sequence = 0;
};
struct OrderedCommandProof {
  std::map<std::string, OrderedUnoProof> uno;
  std::map<int, std::uint64_t> callbacks;
  std::unordered_set<std::string> stateItems;
  bool viewReady = false;
  int searchType = -1;
  std::string searchPayload;
  bool commentAdded = false;
  std::string commentPayload;
  bool missingReported = false;
};
OrderedCommandProof gOrderedProof;
Command gOrderedCommand{CommandType::EmitReady};
std::function<void()> gOrderedReply;
bool gOrderedDispatching = false;
bool gOrderedComposing = false;
void markAsynchronous(std::uint32_t requestId);
void emitJson(const std::string &json);

void setOrderedReply(std::function<void()> reply) {
  if (gOrderedReply)
    throw std::logic_error("one ordered command attempted to install two replies");
  gOrderedReply = std::move(reply);
  if (gOrderedCommand.requestId)
    markAsynchronous(gOrderedCommand.requestId);
}

void expectOrderedUno(const std::string &name) {
  // Inserting a second expectation must not erase an already observed proof.
  gOrderedProof.uno.emplace(name, OrderedUnoProof{});
}

void noteOrderedProofAbsent(const char *callback) {
  if (gOrderedProof.missingReported)
    return;
  gOrderedProof.missingReported = true;
#ifdef OXSDK_E2_V23_DIAGNOSTIC
  static std::uint64_t missing = 0;
  std::ostringstream json;
  json << "{\"type\":\"v23-proof-absent\",\"requestId\":"
       << gOrderedCommand.requestId << ",\"count\":" << ++missing
       << ",\"callback\":\"" << callback << "\"}";
  emitJson(json.str());
#else
  (void)callback;
#endif
}

bool orderedUnoResult(const std::string &name, std::string &payload) {
  const auto found = gOrderedProof.uno.find(name);
  if (found == gOrderedProof.uno.end() || !found->second.seen) {
    if (gOrderedComposing)
      noteOrderedProofAbsent("UNO_COMMAND_RESULT");
    return false;
  }
  payload = found->second.payload;
  return true;
}
