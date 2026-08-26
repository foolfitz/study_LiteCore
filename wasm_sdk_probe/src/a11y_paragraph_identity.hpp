#ifndef OXOFFICE_A11Y_PARAGRAPH_IDENTITY_HPP
#define OXOFFICE_A11Y_PARAGRAPH_IDENTITY_HPP

// Whether a focused-paragraph fingerprint may be used as an IDENTITY.
//
// Finding 082, and it is the decision `queue-a11y-prefix-swallows-the-paragraph`
// has been waiting for since 2026-08-22.
//
// The engine fingerprints the focused paragraph as FNV-1a 64 over its content
// AFTER stripping `listPrefixLength` characters.  Stripping is deliberate: a
// bullet is part of the content LOK reports, so hashing the whole string would
// change the fingerprint on every successful list action and the format
// barrier's identity gate would refuse each one.  Measured, and it works --
// `E1-LC-END甲一乙二丙三插入鈕標記` and `• E1-LC-END甲一乙二丙三插入鈕標記` share
// one fingerprint (`76f09d751bb341f7`, 2026-08-26).
//
// It stops working when the reported prefix is the WHOLE paragraph.  Finding
// 074: `getListPrefixSize()` in `sfx2/source/view/viewsh.cxx` returns the end
// index of the FIRST ATTRIBUTE RUN rather than the length of the numbering
// prefix, and an outline-numbered paragraph with uniform character formatting
// is one run -- which is the common shape of a heading.  The slice is then
// empty and the fingerprint is the FNV-1a offset basis: the value that means
// NOTHING WAS HASHED.
//
// Measured on `list-contexts.odt` (2026-08-26, `e2-editor-v9`, chrome):
//
//     text              contentLength  listPrefixLength  fingerprint
//     "E1-LC-HEADING"        13              13          cbf29ce484222325
//     "• "                    2               2          cbf29ce484222325
//
// A thirteen-character heading and an empty bulleted paragraph are the same
// number.  So the barrier's identity gate compared a degenerate value against a
// real one, concluded "a different paragraph", and refused a mutation that had
// in fact landed -- with a disposition of `rollback`, on a session with no
// checkpoint.  That is finding 082.
//
// The rule below is therefore NOT "the prefix is wrong".  The engine cannot
// tell finding 074's bogus prefix from a real bullet on an otherwise empty
// paragraph, and it does not have to: in BOTH cases the hashed body is empty,
// so the fingerprint distinguishes nothing and must not be gated on.  For the
// empty-bullet case that makes an already-documented blind spot explicit --
// probe_engine.cpp says in as many words that an overshoot from one empty
// paragraph into another is not caught -- rather than costing anything that was
// working.
//
// A separate header so it can be driven on the host without a wasm link, the
// same way `format_readback_text.hpp` is.  A gate that only a relink can
// exercise is a gate nobody has tested.

#include <cstdint>
#include <string>

namespace probe {

// 14695981039346656037.  A NAMED value rather than a number here, because in
// this tree it already means something: it is what `fingerprintOf` returns when
// its loop never runs, and on 2026-08-17 it was what EVERY paragraph reported
// after the basis was written one digit short.  It is the value that means
// UNFED, and the whole point of the rule below is that an unfed hash must not
// be mistaken for an answer.
inline constexpr std::uint64_t kEmptyFingerprint = 14695981039346656037ull;

// FNV-1a 64.  An equality check between two observations made seconds apart in
// one process, not a security boundary.
inline std::uint64_t fingerprintOf(const std::string &content) {
  std::uint64_t hash = kEmptyFingerprint;
  for (const unsigned char byte : content) {
    hash ^= static_cast<std::uint64_t>(byte);
    hash *= 1099511628211ull;
  }
  return hash;
}

// Did the reported list prefix consume the whole paragraph?
//
// `>=` rather than `==`: a prefix longer than the content is not a shape anyone
// has seen, and reading it as "not swallowed" would be the more dangerous of
// the two mistakes.  Both counts are in the UTF-16 code units core counts in.
inline constexpr bool prefixSwallowedTheParagraph(int listPrefixLength,
                                                  int contentLength) {
  return contentLength > 0 && listPrefixLength >= contentLength;
}

// May this paragraph's fingerprint be compared against another one?
//
// A paragraph that is genuinely empty (contentLength 0) keeps its fingerprint:
// the empty hash is the CORRECT reading of an empty paragraph, and the barrier
// already declares that two empty paragraphs are indistinguishable to it.
inline constexpr bool paragraphFingerprintIsUsable(int listPrefixLength,
                                                   int contentLength) {
  return contentLength >= 0
         && !prefixSwallowedTheParagraph(listPrefixLength, contentLength);
}

} // namespace probe

#endif
