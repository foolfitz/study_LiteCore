#ifndef OXOFFICE_MARKDOWN_PASTE_HPP
#define OXOFFICE_MARKDOWN_PASTE_HPP

// SPEC-M3-link-batch-v21 (pinned 523871fa; 12.1 appended at 3d9ca3a4): the
// pure half of "paste as Markdown".  No LOK, no JSON, no clock: the engine
// feeds bytes and payloads in and acts on the answers, so
// tests/markdown_paste_model_test.cpp can drive this natively against the
// committed fixture (tests/markdown_paste_expected.json, M0).
//
// Three things live here:
//   1. the byte-level pre-dispatch judgement, in the order the task brief's
//      interface fixes (spec 9.14, 10.4, 12.1):
//        NUL -> INVALID_UTF8 -> TOO_LARGE -> PARSE_FAIL -> NO_BLOCK
//            -> REMOTE -> HTML -> PASS
//      The engine reports the first five as INVALID_ARGUMENT.  Between them
//      and REMOTE it checks two things that are not properties of the bytes
//      (the thread encoding and the collapsed caret); see the engine.
//   2. the 10.2 "collapsed" rule, as a function of what the engine read;
//   3. the post-dispatch judge over the `.uno:Undo` payload, reusing
//      merge_key_undo.hpp's summarizeUndoPayload (spec 9.4).
//
// The scan is md4c's own: the same md_parse the core links (libmd4c.a, md4c
// 0.5.3) with the flags Writer parses with, copied from
// sw/source/filter/md/swmd.cxx:950-958.  "What is an image" and "what is raw
// HTML" are therefore the parser's answers, not ours (spec 9.3).  The engine
// does NOT compile md4c.c (10.4): it links the core's md_parse.  Only the
// native model test compiles md4c.c, to run this header on the host.

#ifndef OXSDK_E2_V21_LINK_BATCH
#error "markdown_paste.hpp is part of the v21 link batch only (OXSDK_E2_V21_LINK_BATCH)"
#else

#include <md4c.h>

#include "merge_key_undo.hpp"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>

namespace probe {
namespace markdown {

// The engine's hard limit (spec 9.2: the operative one is the SDK's).
constexpr std::size_t kMaxBytes = 65536;

// swmd.cxx:950-958: `MD_PARSER parser = { 0, MD_DIALECT_GITHUB |
// MD_FLAG_WIKILINKS, ... }`.  Copied, not chosen.
constexpr unsigned kParserFlags = MD_DIALECT_GITHUB | MD_FLAG_WIKILINKS;

// The MIME type is the engine's, never the caller's (spec 4.2).
constexpr const char *kMimeType = "text/markdown;charset=utf-8";

enum class Verdict {
  Pass,
  Nul,         // a 0x00 byte anywhere (10.4)
  InvalidUtf8, // not well-formed UTF-8 by RFC 3629 (12.1)
  TooLarge,    // more than kMaxBytes
  ParseFail,   // md_parse returned non-zero (10.4)
  NoBlock,     // no block other than MD_BLOCK_DOC (9.14 rule 3)
  RemoteImage, // an MD_SPAN_IMG whose src is not data: (9.14 rule 1)
  Html,        // any MD_BLOCK_HTML or MD_TEXT_HTML (9.14 rule 2)
};

// The labels of the M0 fixture, verbatim.
inline const char *verdictLabel(Verdict verdict) {
  switch (verdict) {
  case Verdict::Pass: return "PASS";
  case Verdict::Nul: return "NUL";
  case Verdict::InvalidUtf8: return "INVALID_UTF8";
  case Verdict::TooLarge: return "TOO_LARGE";
  case Verdict::ParseFail: return "PARSE_FAIL";
  case Verdict::NoBlock: return "NO_BLOCK";
  case Verdict::RemoteImage: return "REMOTE";
  case Verdict::Html: return "HTML";
  }
  return "?";
}

// ---- the error codes ---------------------------------------------------------
//
// Every code the engine's paste handler can send BEFORE it calls paste(), in
// the interface's order, each with `dispatched: false`.  The session must give
// every one of them `recovery: "none"` (spec 10.4): the document is provably
// untouched.  The last one is the interface's sixth refusal ("the .uno:Undo
// read before the paste fails"), which the interface names no code for.
constexpr const char *kCodeInvalidArgument = "INVALID_ARGUMENT";
constexpr const char *kCodeEncodingUnsupported = "MARKDOWN_ENCODING_UNSUPPORTED";
constexpr const char *kCodeNeedsCaret = "MARKDOWN_NEEDS_CARET";
constexpr const char *kCodeRemoteImage = "MARKDOWN_REMOTE_IMAGE";
constexpr const char *kCodeHtmlUnsupported = "MARKDOWN_HTML_UNSUPPORTED";
constexpr const char *kCodeUndoUnreadable = "MARKDOWN_UNDO_UNREADABLE";
constexpr const char *kPreDispatchCodes[] = {
    kCodeInvalidArgument, kCodeEncodingUnsupported, kCodeNeedsCaret,
    kCodeRemoteImage,     kCodeHtmlUnsupported,     kCodeUndoUnreadable,
};
// The one code sent AFTER paste() was called (`dispatched: true`).  The
// session's existing recovery for it is the fail-closed rollback.
constexpr const char *kCodeOutcomeUnknown = "MUTATION_OUTCOME_UNKNOWN";

// Code 1 of the interface: the byte-level refusals.
inline bool isInvalidArgument(Verdict verdict) {
  return verdict == Verdict::Nul || verdict == Verdict::InvalidUtf8 ||
         verdict == Verdict::TooLarge || verdict == Verdict::ParseFail ||
         verdict == Verdict::NoBlock;
}

// The wire code of a byte-level verdict; nullptr for PASS.
inline const char *verdictCode(Verdict verdict) {
  if (isInvalidArgument(verdict))
    return kCodeInvalidArgument;
  if (verdict == Verdict::RemoteImage)
    return kCodeRemoteImage;
  if (verdict == Verdict::Html)
    return kCodeHtmlUnsupported;
  return nullptr;
}

inline const char *verdictMessage(Verdict verdict) {
  switch (verdict) {
  case Verdict::Pass: return "";
  case Verdict::Nul: return "the Markdown contains a NUL byte";
  case Verdict::InvalidUtf8: return "the Markdown is not valid UTF-8";
  case Verdict::TooLarge: return "the Markdown is longer than 65536 UTF-8 bytes";
  case Verdict::ParseFail: return "the Markdown parser failed";
  case Verdict::NoBlock: return "the Markdown has no content";
  case Verdict::RemoteImage:
    return "the Markdown has an image that is not a data: URI; "
           "network images are not supported";
  case Verdict::Html:
    return "the Markdown has raw HTML outside code; it is not supported";
  }
  return "";
}

// ---- RFC 3629 -----------------------------------------------------------------
//
// Spec 12.1.  Well-formed UTF-8, Table 3-7 of the Unicode standard (RFC 3629
// section 4): the second byte's range depends on the first, which is what
// excludes overlong forms (C0, C1, E0 80-9F, F0 80-8F), surrogates (ED A0-BF)
// and values above U+10FFFF (F4 90-BF, F5-FF).  A sequence cut short -- at the
// end of the input or by any other byte -- is ill-formed.  Why it matters:
// Writer decodes the bytes with the thread encoding and replaces every
// ill-formed sequence with U+FFFD before md_parse sees them, so on ill-formed
// input the scan and Writer would parse different bytes (fixture item X07).
inline bool isValidUtf8(const char *data, std::size_t size) {
  const unsigned char *p = reinterpret_cast<const unsigned char *>(data);
  std::size_t i = 0;
  while (i < size) {
    const unsigned char b0 = p[i];
    if (b0 <= 0x7f) {
      ++i;
      continue;
    }
    std::size_t length;
    unsigned char lo = 0x80, hi = 0xbf; // the second byte's range
    if (b0 >= 0xc2 && b0 <= 0xdf) {
      length = 2;
    } else if (b0 == 0xe0) {
      length = 3;
      lo = 0xa0;
    } else if ((b0 >= 0xe1 && b0 <= 0xec) || b0 == 0xee || b0 == 0xef) {
      length = 3;
    } else if (b0 == 0xed) {
      length = 3;
      hi = 0x9f;
    } else if (b0 == 0xf0) {
      length = 4;
      lo = 0x90;
    } else if (b0 >= 0xf1 && b0 <= 0xf3) {
      length = 4;
    } else if (b0 == 0xf4) {
      length = 4;
      hi = 0x8f;
    } else {
      return false; // 80-C1, F5-FF never start a sequence
    }
    if (size - i < length)
      return false;
    if (p[i + 1] < lo || p[i + 1] > hi)
      return false;
    for (std::size_t k = 2; k < length; ++k)
      if (p[i + k] < 0x80 || p[i + k] > 0xbf)
        return false;
    i += length;
  }
  return true;
}

// ---- the scan -----------------------------------------------------------------

struct ScanFacts {
  int parseResult = 0;
  std::size_t blocks = 0;       // entered, MD_BLOCK_DOC excluded
  std::size_t images = 0;       // MD_SPAN_IMG entered
  std::size_t remoteImages = 0; // ... whose src is not data:
  std::size_t htmlBlocks = 0;   // MD_BLOCK_HTML entered
  std::size_t htmlText = 0;     // MD_TEXT_HTML callbacks
  // Not read by any rule.  MD_TEXT_NORMAL/CODE/ENTITY/NULLCHAR callbacks
  // outside an image that hold a byte other than ASCII blank: the fact the
  // old 9.3 "no text" rule used, kept so the model test can show what that
  // rule would answer (M0's third red mutation) and print it on a mismatch.
  std::size_t textOutsideImages = 0;
};

namespace detail {

struct ScanState {
  ScanFacts facts;
  std::size_t imageDepth = 0;
};

// Writer reads the src attribute raw, without resolving entities
// (mdcallbcks.cxx:177-180), so the test is on src.text[0..size).  Case-
// insensitive: natively `DATA:` is embedded and nothing is fetched (round 2,
// S15).
inline bool srcIsData(const MD_ATTRIBUTE &src) {
  static const char kData[] = "data:";
  if (src.size < 5)
    return false;
  for (std::size_t k = 0; k < 5; ++k) {
    char c = src.text[k];
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');
    if (c != kData[k])
      return false;
  }
  return true;
}

inline bool hasNonBlank(const MD_CHAR *text, MD_SIZE size) {
  for (MD_SIZE k = 0; k < size; ++k) {
    const char c = text[k];
    if (!(c == ' ' || c == '\t' || c == '\n' || c == '\v' || c == '\f' ||
          c == '\r'))
      return true;
  }
  return false;
}

// No callback ever returns non-zero: an abort would make md_parse fail, and
// a parse failure is its own verdict (PARSE_FAIL), not a way to stop early.
inline int enterBlock(MD_BLOCKTYPE type, void *, void *user) {
  ScanState *state = static_cast<ScanState *>(user);
  if (type != MD_BLOCK_DOC)
    ++state->facts.blocks;
  if (type == MD_BLOCK_HTML)
    ++state->facts.htmlBlocks;
  return 0;
}

inline int leaveBlock(MD_BLOCKTYPE, void *, void *) { return 0; }

inline int enterSpan(MD_SPANTYPE type, void *detail, void *user) {
  ScanState *state = static_cast<ScanState *>(user);
  if (type == MD_SPAN_IMG) {
    ++state->facts.images;
    if (!srcIsData(static_cast<const MD_SPAN_IMG_DETAIL *>(detail)->src))
      ++state->facts.remoteImages;
    ++state->imageDepth;
  }
  return 0;
}

inline int leaveSpan(MD_SPANTYPE type, void *, void *user) {
  ScanState *state = static_cast<ScanState *>(user);
  if (type == MD_SPAN_IMG && state->imageDepth > 0)
    --state->imageDepth;
  return 0;
}

inline int onText(MD_TEXTTYPE type, const MD_CHAR *text, MD_SIZE size,
                  void *user) {
  ScanState *state = static_cast<ScanState *>(user);
  if (type == MD_TEXT_HTML) {
    ++state->facts.htmlText;
  } else if ((type == MD_TEXT_NORMAL || type == MD_TEXT_CODE ||
              type == MD_TEXT_ENTITY || type == MD_TEXT_NULLCHAR) &&
             state->imageDepth == 0 && hasNonBlank(text, size)) {
    ++state->facts.textOutsideImages;
  }
  return 0;
}

} // namespace detail

// One md_parse over the bytes, exactly as Writer will parse them (given the
// NUL and UTF-8 rules, the same bytes).  `size` must not exceed kMaxBytes.
inline ScanFacts scan(const char *data, std::size_t size) {
  detail::ScanState state;
  MD_PARSER parser = {0,
                      kParserFlags,
                      detail::enterBlock,
                      detail::leaveBlock,
                      detail::enterSpan,
                      detail::leaveSpan,
                      detail::onText,
                      nullptr,
                      nullptr};
  state.facts.parseResult =
      md_parse(data, static_cast<MD_SIZE>(size), &parser, &state);
  return state.facts;
}

// The byte-level judgement, first rule that fires.  `factsOut`, when given,
// receives the scan's facts (zeroed when the scan did not run).
inline Verdict judgeBytes(const char *data, std::size_t size,
                          ScanFacts *factsOut = nullptr) {
  if (factsOut)
    *factsOut = ScanFacts{};
  if (size != 0 && std::memchr(data, 0, size) != nullptr)
    return Verdict::Nul;
  if (!isValidUtf8(data, size))
    return Verdict::InvalidUtf8;
  if (size > kMaxBytes)
    return Verdict::TooLarge;
  const ScanFacts facts = scan(data, size);
  if (factsOut)
    *factsOut = facts;
  if (facts.parseResult != 0)
    return Verdict::ParseFail;
  if (facts.blocks == 0)
    return Verdict::NoBlock;
  if (facts.remoteImages != 0)
    return Verdict::RemoteImage;
  if (facts.htmlBlocks != 0 || facts.htmlText != 0)
    return Verdict::Html;
  return Verdict::Pass;
}

// ---- 10.2: where the paste may go --------------------------------------------
//
// Read by the engine at the moment of dispatch: `readSelection().type` is NONE
// and its text is not missing, AND (no selection was ever observed, or the
// cached selection rectangles are empty).  Anything else is
// MARKDOWN_NEEDS_CARET.  The cache alone would refuse every paste right after
// opening (nothing reported yet); the readback alone reads a selected image as
// NONE.  The same shape as C's condition (probe_engine.cpp, the boundary-noop
// deadline).
inline bool collapsedForPaste(bool readbackNone, bool readbackTextMissing,
                              bool selectionObserved,
                              std::size_t selectionRectangles) {
  return readbackNone && !readbackTextMissing &&
         (!selectionObserved || selectionRectangles == 0);
}

// ---- the interface's order, codes 1-5 ------------------------------------------
//
// Everything before paste() but the undo read (code 6, which needs the
// payload), in the order the task brief's interface fixes: the byte verdict's
// INVALID_ARGUMENT, then the thread encoding, then the caret, then the scan's
// REMOTE and HTML.  The two engine reads are asked for lazily and in that
// order, so refused bytes cost no LOK call at all and a refused encoding no
// selection read.  `code` is nullptr when nothing refuses.
struct Refusal {
  const char *code = nullptr;
  const char *message = nullptr;
};

template <typename EncodingIsUtf8, typename Collapsed>
inline Refusal preDispatchRefusal(Verdict verdict, EncodingIsUtf8 &&encodingIsUtf8,
                                  Collapsed &&collapsed) {
  if (isInvalidArgument(verdict))
    return {kCodeInvalidArgument, verdictMessage(verdict)};
  // The flavour's bytes are decoded with the thread's encoding (vcl
  // transfer.cxx:1517); anything but UTF-8 garbles them (natively LANG=C).
  if (!encodingIsUtf8())
    return {kCodeEncodingUnsupported,
            "the engine's text encoding is not UTF-8, so the Markdown would be "
            "decoded wrongly"};
  if (!collapsed())
    return {kCodeNeedsCaret,
            "Markdown is pasted only at a caret; remove the selection first"};
  if (verdict == Verdict::RemoteImage || verdict == Verdict::Html)
    return {verdictCode(verdict), verdictMessage(verdict)};
  return {};
}

// ---- 9.4: after paste() --------------------------------------------------------
//
// paste() says true whatever happened (init.cxx:6165-6192; natively 152/152,
// and 7 positions where nothing was inserted, round 2 T2), so the engine
// judges by the `.uno:Undo` payload it read before and after.  Completed only
// when the after-read succeeded, the payload changed, and it parses with at
// least one action.  Every other outcome is MUTATION_OUTCOME_UNKNOWN: paste()
// was called, so "the document did not change" must never be claimed.  The
// direction of every error is safe (L-md-undo-collision: an undo stack at its
// limit whose shifted payload happens to repeat would be judged unknown, never
// completed).
struct PasteJudgement {
  bool completed = false;
  const char *reason = nullptr; // set when !completed
  probe::merge::UndoSummary before, after;
};

inline PasteJudgement judgeAfterPaste(const std::string &before,
                                      bool afterReadOk,
                                      const std::string &after) {
  PasteJudgement out;
  if (!afterReadOk) {
    out.reason = "undo-read-after-paste-failed";
    return out;
  }
  if (after == before) {
    out.reason = "undo-payload-unchanged";
    return out;
  }
  out.before = probe::merge::summarizeUndoPayload(before);
  out.after = probe::merge::summarizeUndoPayload(after);
  if (!out.after.ok || out.after.actions < 1) {
    out.reason = "undo-payload-without-action";
    return out;
  }
  out.completed = true;
  return out;
}

} // namespace markdown
} // namespace probe

#endif // OXSDK_E2_V21_LINK_BATCH
#endif // OXOFFICE_MARKDOWN_PASTE_HPP
