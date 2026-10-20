#ifndef OXOFFICE_CARET_DELETE_WITNESS_HPP
#define OXOFFICE_CARET_DELETE_WITNESS_HPP

// SPEC-M3-ordered-commands 15.1 (fable ruling 2 2.1 item 3), measured before
// it was written (15.7, VERDICT G-HOLDS): the at-return proof of a caret
// Backspace or Delete sent as the user's own key under candidate C.
//
// The pure half, the merge_key_undo.hpp pattern.  The engine reads `.uno:Undo`
// and getA11yFocusedParagraph before the key and at its return, in the same
// poll with nothing between them (5.7 rule 1), and asks this header what the
// key did.  LOK calls, clocks and JSON stay in the engine, so
// tests/caret_delete_witness_test.cpp can drive the decision with the inputs
// the native G run recorded, labelled from the saved documents rather than by
// the decider itself.
//
// Why two witnesses.  Writer merges a run of single-character deletes into one
// SwUndoDelete and shortens its comment to 20 characters, so after 19 deleted
// IDENTICAL characters the payload stops changing while every press still
// deletes one (ev/review/disposition-1/grouping/; the G run: undo-only 19 of
// 25 on both underscore arms, 25 of 25 on distinct CJK).  The undo payload
// alone would answer "no effect" for a key that deleted a character.
//
// Why the guard.  The focused paragraph is the engine's one synchronous content
// read, and it is trusted only while the caret was strictly inside the
// paragraph before the key.  At a paragraph start or end Writer may join (a new
// undo action, which the undo branch sees) or may only move or restore the
// caret without touching the document (a table boundary, sw delete.cxx:198-237),
// and a read of a different paragraph is not a change of this one.

#include "a11y_paragraph_identity.hpp"
#include "merge_key_undo.hpp"

#include <cstdint>
#include <string>

namespace probe {
namespace caretdelete {

enum class Key { Backspace, Delete };

// One getA11yFocusedParagraph read as the engine parsed it
// (parseEditorSemanticJson): the caret's UTF-16 index, the content's UTF-16
// length, the list prefix length, and the fingerprint over the content past
// that prefix.  `ok` false is a read that failed or did not parse.
struct ParagraphRead {
  bool ok = false;
  int position = -1;
  int length = -1;
  int listPrefixLength = 0;
  std::uint64_t fingerprint = 0;
};

inline bool contentDiffers(const ParagraphRead &a, const ParagraphRead &b) {
  return a.length != b.length || a.listPrefixLength != b.listPrefixLength ||
         a.fingerprint != b.fingerprint;
}

// Ruling 2 2.1 item 3, literally: Backspace `position >= 1`, Delete
// `position < length`.
inline bool caretStrictlyInside(Key key, const ParagraphRead &before) {
  if (!before.ok)
    return false;
  return key == Key::Backspace ? before.position >= 1
                               : before.position < before.length;
}

enum class Verdict { KeyUndo, BoundaryNoop, Refused };

struct Judgement {
  Verdict verdict = Verdict::Refused;
  const char *stage = nullptr; // set when Refused
  bool keyPosted = false;      // set when Refused
  // KeyUndo through the paragraph branch: the undo payload did not change and
  // the key's action was merged into the existing one.
  bool byParagraph = false;
  merge::UndoSummary before, after; // set when KeyUndo
};

// Before the key.  nullptr: post it.  Otherwise the stage of a refusal with
// nothing dispatched.
//
// The a11y-available guard comes first and is not a fallback.  On a core built
// without accessibility getA11yFocusedParagraph still answers, with an empty
// paragraph at position 0 (refreshCaretParagraph's comment in the engine), so
// a decider that went on without it would be the undo-only decider -- the one
// the G run showed answering "no effect" for 6 of 25 deletions -- without
// saying so.  The engine passes gEditorAccessibilityEnabled.
inline const char *judgeBeforeKey(bool accessibilityAvailable, bool undoReadOk,
                                  const ParagraphRead &before) {
  if (!accessibilityAvailable)
    return "a11y-unavailable";
  if (!undoReadOk)
    return "undo-read";
  if (!before.ok)
    return "paragraph-read";
  return nullptr;
}

// At the key's return.  `undoBefore` is the payload read before the key (its
// read succeeded, or judgeBeforeKey refused).
//   - payload changed and the new one parses to >= 1 action: KeyUndo;
//   - payload unchanged, caret strictly inside before the key, content
//     changed: KeyUndo through the paragraph branch, `after.actions` from the
//     unchanged payload (>= 1: the merged action exists, so the client's
//     `actionsAfter >= 1` is literally true);
//   - otherwise BoundaryNoop.
// A read that fails after the key is refused with the key posted, never read
// as "no effect".
inline Judgement judgeAtReturn(Key key, const std::string &undoBefore,
                               bool undoAfterOk, const std::string &undoAfter,
                               const ParagraphRead &before,
                               const ParagraphRead &after) {
  Judgement out;
  if (!undoAfterOk) {
    out.stage = "key-read";
    out.keyPosted = true;
    return out;
  }
  out.before = merge::summarizeUndoPayload(undoBefore);
  out.after = merge::summarizeUndoPayload(undoAfter);
  const bool parsed = out.after.ok && out.after.actions >= 1;
  if (undoAfter != undoBefore) {
    if (!parsed) {
      out.stage = "key-unparsed";
      out.keyPosted = true;
      return out;
    }
    out.verdict = Verdict::KeyUndo;
    return out;
  }
  if (caretStrictlyInside(key, before)) {
    if (!after.ok) {
      out.stage = "paragraph-read-after";
      out.keyPosted = true;
      return out;
    }
    if (contentDiffers(before, after)) {
      if (!parsed) {
        out.stage = "key-unparsed";
        out.keyPosted = true;
        return out;
      }
      out.verdict = Verdict::KeyUndo;
      out.byParagraph = true;
      return out;
    }
  }
  out.verdict = Verdict::BoundaryNoop;
  return out;
}

// The paragraph read of a recorded payload, for the host test: UTF-16 length
// and the fingerprint over the content past `listPrefixLength` UTF-16 units,
// the way parseEditorSemanticJson computes them on the engine.  `content` is
// UTF-8.
inline ParagraphRead paragraphReadOf(const std::string &content, int position,
                                     int listPrefixLength) {
  ParagraphRead read;
  int units = 0;
  std::size_t bodyStart = std::string::npos;
  for (std::size_t i = 0; i < content.size();) {
    if (units >= listPrefixLength && bodyStart == std::string::npos)
      bodyStart = i;
    const unsigned char lead = static_cast<unsigned char>(content[i]);
    const std::size_t width = lead < 0x80 ? 1 : lead < 0xe0 ? 2 : lead < 0xf0 ? 3 : 4;
    units += width == 4 ? 2 : 1;
    i += width;
  }
  if (bodyStart == std::string::npos)
    bodyStart = content.size();
  read.ok = position >= 0;
  read.position = position;
  read.length = units;
  read.listPrefixLength = listPrefixLength;
  read.fingerprint = fingerprintOf(content.substr(bodyStart));
  return read;
}

} // namespace caretdelete
} // namespace probe

#endif
