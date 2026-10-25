#ifndef OXOFFICE_ORDERED_COMMAND_PROOF_HPP
#define OXOFFICE_ORDERED_COMMAND_PROOF_HPP

// SPEC-M3-ordered-commands 16.4: at the first post-command poll there is
// either the requested proof or a typed refusal. There is no pending result
// here: waiting longer would silently restore the retired deadline machinery.
// The engine keeps the payloads and composes replies; callbacks only record.
// Available means presence, not success: matching payload validation and the
// 059 inline-format state exception remain the composer's responsibility.
// errorCode is the editor UNO policy. Search/annotation SDK operations retain
// their existing non-retry error codes; the engine adds the named failureShape.

namespace probe {
namespace orderedproof {

enum class Verdict { Available, DispatchFailed, MutationUnknown };

inline Verdict atPoll(bool dispatchFailed, bool proofPresent) {
  if (dispatchFailed)
    return Verdict::DispatchFailed;
  return proofPresent ? Verdict::Available : Verdict::MutationUnknown;
}

inline const char *errorCode(Verdict verdict) {
  switch (verdict) {
  case Verdict::DispatchFailed:
    return "LOK_COMMAND_FAILED";
  case Verdict::MutationUnknown:
    return "MUTATION_OUTCOME_UNKNOWN";
  case Verdict::Available:
    return nullptr;
  }
  return "MUTATION_OUTCOME_UNKNOWN";
}

} // namespace orderedproof
} // namespace probe

#endif
