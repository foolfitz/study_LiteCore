#ifndef OXSDK_WRITER_CARET_BRIDGE_H
#define OXSDK_WRITER_CARET_BRIDGE_H

// SPEC-P-demo-batch-4: the paragraphs the caret or the selection covers, read from
// the document without selecting anything, so the caret never moves and no
// coordinate is needed.  Writer profiles link this core-internal bridge; only its
// translation unit uses internal headers.  Calls run on the engine thread under
// SolarMutex.
#include <cstddef>
#include <string>
#include <vector>

namespace probe {

struct WriterParagraphRead {
  std::string list;   // "ul", "ol" or "": the outline rule on a heading is not a list
  std::string block;  // "h1" to "h9" for a style named exactly Heading 1 to 9, else "p"
  std::string align;  // "left", "center", "right", "justify", or "" for anything else
  std::string style;  // the paragraph style's programmatic name
  std::string text;   // the covered part of the paragraph, UTF-8
};

// N4 large: the walk is worse than linear, 8 ms for 100 paragraphs, 329 ms for 1,000,
// 7.9 s for 5,000, 157 s for 20,000 (native, and the Wasm engine is slower).  It runs
// under the solar mutex and twice per press, so it stops here and the press is refused
// before anything is dispatched.  The HTML read it replaced refused at about 10 KB of
// text, roughly 150 of these paragraphs.
constexpr std::size_t kWriterParagraphReadLimit = 500;
constexpr const char *kWriterReadTooLong = "the selection covers too many paragraphs";

// True with one row per paragraph, in the selection's own order (one text range for
// everything this product can select).  False with `reason` set when the selection is
// not text (a frame, cells), holds anything but paragraphs, or passes the limit.
bool writerSelectionParagraphs(void *lokDocument, std::vector<WriterParagraphRead> &out,
                               std::string &reason);

// The verdicts, pure so they can be tested on the host against the rows N4 recorded.

// An empty expectation makes no claim.  `list` "none" means not in a list.
inline bool paragraphMeets(const WriterParagraphRead &row, const std::string &list,
                           const std::string &block, const std::string &align) {
  if (!list.empty() && (row.list.empty() ? std::string("none") : row.list) != list)
    return false;
  if (!block.empty() && row.block != block)
    return false;
  return align.empty() || row.align == align;
}

// Empty input is false: "every paragraph of none" would verify a read that found nothing.
inline bool everyParagraphMeets(const std::vector<WriterParagraphRead> &rows, const std::string &list,
                                const std::string &block, const std::string &align) {
  if (rows.empty())
    return false;
  for (const WriterParagraphRead &row : rows)
    if (!paragraphMeets(row, list, block, align))
      return false;
  return true;
}

// Which way a toggle goes.  Off only when every paragraph is already there: a mixed
// selection goes on, as core's SelectionHasBullet and a word processor's button do.
inline bool toggleTakesOff(const std::vector<WriterParagraphRead> &rows, const std::string &list,
                           const std::string &block) {
  return everyParagraphMeets(rows, list, block, std::string());
}

// `.uno:DefaultNumbering` with On=true does nothing when core's SelectionHasNumber is
// already true, and that counts a heading's outline rule: a heading alone stays as it
// was, a heading with a bullet item loses the bullet (N4 range).  True when every
// paragraph counts as numbered that way and at least one is a heading.  An
// approximation of core's rule from what the read carries, and it errs towards a clean
// refusal.  A press it lets through that does nothing ends in review, not rollback.
inline bool numberingHasNoEffect(const std::vector<WriterParagraphRead> &rows) {
  bool heading = false;
  for (const WriterParagraphRead &row : rows) {
    const bool isHeading = row.block != "p";
    if (!isHeading && row.list.empty())
      return false;
    heading = heading || isHeading;
  }
  return heading;
}

} // namespace probe

#endif
