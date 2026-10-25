#include "ordered_engine_guards.hpp"
#include <map>
#include <stdexcept>
int main() {
  std::map<int, unsigned> proof;
  probe::ordered::recordParsedCallback(proof, 1, true, 5u);
  // Tiles advanced the global sequence, then cursor parsing failed.
  probe::ordered::recordParsedCallback(proof, 2, false, 6u);
  if (proof.count(2) || proof.at(1) != 5) return 1;
  probe::ordered::recordParsedCallback(proof, 2, true, 7u);
  if (proof.at(2) != 7) return 1;
  bool poll = false, dispatch = false, composing = false;
  try {
    probe::ordered::FlagScope outer(poll);
    probe::ordered::FlagScope inner(dispatch);
    if (!poll || !dispatch) return 1;
    throw std::runtime_error("dispatch and its error serializer failed");
  } catch (const std::runtime_error &) {}
  if (poll || dispatch) return 1;
  try {
    probe::ordered::FlagScope scope(composing);
    throw std::runtime_error("reply error serializer failed");
  } catch (const std::runtime_error &) {}
  return composing ? 1 : 0;
}
