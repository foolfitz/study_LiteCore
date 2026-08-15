#ifndef OXOFFICE_FORMAT_READBACK_TEXT_HPP
#define OXOFFICE_FORMAT_READBACK_TEXT_HPP

// SPEC E2-B 9.9: the identity half of the cross-paragraph verification.
//
// A format dispatch on a range spanning more than one paragraph is verified by
// comparing the text of each block in the html readback, before the dispatch
// against after.  Identity is per-block TEXT; the list state is the STRUCTURE
// around it, which parseFormatReadback already counts.
//
// Two things this deliberately does NOT do, both measured rather than assumed
// (findings/evidence/sdk-e2/discovery/e2b-crossparagraph/):
//
//   It does not compare the plain-text readback.  getTextSelection("text/plain")
//   injects list decoration -- "    * " for bullets, "    1. ", "    2. "
//   incrementing for numbering -- but ONLY when the selection crosses a
//   paragraph boundary.  So plain-text equality fails on exactly the successful
//   cross-paragraph dispatches this check exists to verify.  The html
//   serialisation puts the number in the <ol> and leaves the text alone.
//
//   It does not strip tags from the whole <body>.  "</li>\n<li>" leaves a tab
//   between paragraphs after the dispatch that was not there before, and
//   wrapping a lone paragraph in <ul><li> does the same, so a whole-body
//   comparison reports a difference that is pure serialisation.  Per-block
//   extraction has no such seam.
//
// It is a separate scan rather than an extension of parseFormatReadback on
// purpose: that parser is load-bearing for every verdict already recorded, and
// this needs none of its state.
//
// Header-only so it can be unit-tested on the host, against the actual markup
// captured by the native rounds, without an Emscripten build.

#include <cstddef>
#include <string>
#include <vector>

namespace probe {

// True for the block-level tags this contract can produce: a paragraph, or a
// heading at any level.  Deliberately not the same predicate as the readback
// parser's -- that one also counts containers, and a container carries no text
// of its own.
inline bool formatTextBlockTag(const std::string &tag) {
  if (tag == "p")
    return true;
  return tag.size() == 2 && tag[0] == 'h' && tag[1] >= '1' && tag[1] <= '6';
}

// One text-bearing block: its tag and its text.
//
// The tag is here because the paragraph-style postcondition has to hold for
// EVERY block, and parseFormatReadback keeps only the first one.  Verifying the
// first block and reporting success for the whole range is precisely the defect
// the cross-paragraph route exists to remove -- rebuilding it inside the fix
// would be the same lie in a new place.
struct ReadbackBlock {
  std::string tag;
  std::string text;
};

// The tag and text of each block, with inline markup (<font>, <span>, <b> ...)
// concatenated away.  Entities are left exactly as the serialiser wrote them:
// what the gate needs is that the two reads agree, and "&amp;" agrees with
// "&amp;".  Resolving them would be a second place to be wrong.
inline std::vector<ReadbackBlock> extractBlocks(const std::string &html) {
  std::vector<ReadbackBlock> blocks;
  const std::size_t body = html.find("<body");
  if (body == std::string::npos)
    return blocks;
  std::size_t index = html.find('>', body);
  if (index == std::string::npos)
    return blocks;

  std::string current;
  std::string openTag;      // empty when not inside a block
  for (++index; index < html.size(); ++index) {
    if (html[index] != '<') {
      if (!openTag.empty())
        current += html[index];
      continue;
    }
    std::size_t start = index + 1;
    if (start >= html.size())
      break;
    const bool closing = start < html.size() && html[start] == '/';
    if (closing)
      ++start;
    std::size_t end = start;
    while (end < html.size() &&
           ((html[end] >= 'a' && html[end] <= 'z') ||
            (html[end] >= 'A' && html[end] <= 'Z') ||
            (html[end] >= '0' && html[end] <= '9')))
      ++end;
    const std::size_t bracket = html.find('>', end);
    std::string tag = html.substr(start, end - start);
    for (char &character : tag)
      if (character >= 'A' && character <= 'Z')
        character = static_cast<char>(character - 'A' + 'a');

    if (end != start && formatTextBlockTag(tag)) {
      if (closing) {
        if (!openTag.empty() && tag == openTag) {
          blocks.push_back({openTag, current});
          current.clear();
          openTag.clear();
        }
      } else {
        // An unclosed block followed by another one: keep the first rather
        // than silently merging the two, because a merge would make two
        // paragraphs compare equal to one.
        if (!openTag.empty()) {
          blocks.push_back({openTag, current});
          current.clear();
        }
        openTag = tag;
      }
    }
    if (bracket == std::string::npos)
      break;
    // Land ON the '>' so the loop's ++index steps past it.  The readback
    // parser writes `bracket - 1` here and is right to: it never accumulates
    // text, so the '>' it re-visits is harmless.  Here it is not -- it lands in
    // the block's text.  Caught by running this against the markup the native
    // rounds actually captured.
    index = bracket;
  }
  // A block still open at the end of the markup is truncated input, not a
  // block.  Dropping it means the count differs from the structural count,
  // which is what the caller checks first.
  return blocks;
}

// The text alone, for the identity comparison.
inline std::vector<std::string> blockTexts(const std::vector<ReadbackBlock> &blocks) {
  std::vector<std::string> texts;
  texts.reserve(blocks.size());
  for (const ReadbackBlock &block : blocks)
    texts.push_back(block.text);
  return texts;
}

// True when every block carries `tag`.  Empty input is false: "every block of
// none" is vacuously true and would report a verified mutation from a readback
// that found nothing.
inline bool everyBlockHasTag(const std::vector<ReadbackBlock> &blocks,
                             const std::string &tag) {
  if (blocks.empty())
    return false;
  for (const ReadbackBlock &block : blocks)
    if (block.tag != tag)
      return false;
  return true;
}

} // namespace probe

#endif
