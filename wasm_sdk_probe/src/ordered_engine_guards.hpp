#ifndef OXSDK_ORDERED_ENGINE_GUARDS_HPP
#define OXSDK_ORDERED_ENGINE_GUARDS_HPP
namespace probe::ordered {
// Engine-thread flags must reset even when dispatch or error serialization throws.
struct FlagScope {
  bool &flag;
  explicit FlagScope(bool &value) : flag(value) { flag = true; }
  ~FlagScope() { flag = false; }
  FlagScope(const FlagScope &) = delete;
  FlagScope &operator=(const FlagScope &) = delete;
};
template<class Map, class Sequence>
void recordParsedCallback(Map &proof, int type, bool parsed, Sequence sequence) {
  // An unrelated event's newer sequence cannot validate a malformed payload.
  if (parsed)
    proof[type] = sequence;
}
}
#endif
