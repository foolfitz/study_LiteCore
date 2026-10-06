#ifndef OXOFFICE_MERGE_KEY_UNDO_HPP
#define OXOFFICE_MERGE_KEY_UNDO_HPP

// SPEC-M3-paragraph-merge, option B: merge at a paragraph boundary by pressing
// the user's own key, proven by the `.uno:Undo` payload.  The pure half
// (3.1 item 11): classifying the unit, attributing caret callbacks to the
// presses that caused them, the anchor fence, and judging the payload.  The
// engine feeds LOK's callbacks in and acts on the answers; clocks, LOK calls
// and JSON stay in the engine, so tests/merge_key_undo_model_test.cpp can drive
// this with generated callback sequences on the host (M1-2).
//
// What the attribution rests on (spec 10.1(a), 11, 13.1, 14), in short:
//   P   the last caret delivered before the unit's non-empty TEXT_SELECTION.
//   A   the anchor-side selection rectangle delivered in that same flush
//       (TEXT_SELECTION_START for Shift+Right, _END for Shift+Left).  Writer
//       computes it at flush time from wherever the caret really was when the
//       Shift press ran, so it catches a P made stale by an event still queued
//       when the Shift press was posted (13.1).  It is not sent at all for a
//       table-cell selection (14.1); "absent" refuses.
//   U   the first caret after that TEXT_SELECTION (the unit's own caret;
//       10.1(a), which replaced 3.1 item 4's "differs from the placed caret").
//   press 1 evidence: the first caret after the collapse TEXT_SELECTION that
//       follows posting press 1 (carets before the collapse never count).
//   press 2 evidence: the first caret after posting press 2 whose rectangle
//       differs from the caret known when it was posted.
// Premises P1-P4 are in the spec's table; the model test has a switch that
// breaks P4 and must then find a counterexample.

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace probe {
namespace merge {

// A LOK rectangle payload "x, y, w, h" (twips), parsed by the engine.
struct Rect {
  long x = 0, y = 0, w = 0, h = 0;
  bool operator==(const Rect &o) const {
    return x == o.x && y == o.y && w == o.w && h == o.h;
  }
  bool operator!=(const Rect &o) const { return !(*this == o); }
};

// ---- the unit -------------------------------------------------------------

enum class UnitClass {
  Barrier,  // no separator at all: today's verified-selection-delete
  MergeKey, // holds a paragraph or line separator: option B
  Refused,  // only a tab or an object placeholder: refused as before
};

// Spec 3.1 item 2.  13 is in B's set like 10: Writer reports paragraph ends
// as either, depending on the readback path.
inline UnitClass classifyUnit(const std::vector<std::uint32_t> &codePoints) {
  bool other = false;
  for (const std::uint32_t c : codePoints) {
    if (c == '\n' || c == '\r' || c == 0x2028 || c == 0x2029)
      return UnitClass::MergeKey;
    if (c == '\t' || c == 0xfffc)
      other = true;
  }
  return other ? UnitClass::Refused : UnitClass::Barrier;
}

// ---- the anchor fence (spec 14.2) -------------------------------------------
//
// R0b: x equal on every unit; the caret's height is never the anchor's -- the
// caret payload is printed closed, the anchor through SwRect::SVRect() (one
// less), and on a line holding a taller portion the anchor is the whole line
// while the caret is the portion, lower and shorter, bottoms coinciding.  So:
// equal x, and the caret's vertical span inside the anchor's.
inline bool anchorFenceHolds(const Rect &caret, const Rect &anchor) {
  return anchor.x == caret.x && anchor.y <= caret.y &&
         caret.y + caret.h <= anchor.y + anchor.h + 1;
}

// ---- callback attribution ---------------------------------------------------

class Attribution {
public:
  enum class Phase {
    Idle,
    AwaitUnitSelection, // Shift press posted
    AwaitUnitCaret,     // unit's TEXT_SELECTION seen; P and A captured
    UnitReady,          // U seen: the engine decides fence / restore
    AwaitRestore1,      // press 1 posted
    NeedSecondPress,    // press 1 evidence was not P
    AwaitRestore2,      // press 2 posted
    Restored,           // the last press's evidence is P
    NotRestored,        // press 2's evidence is not P
  };

  // Right before posting the unit's Shift press (K).  Clears the anchors
  // (14.3); keeps the last caret, which is what P will be if nothing else
  // arrives before the unit's selection.
  void beginTransaction(bool backward) {
    const bool hasLast = hasLastCaret_;
    const Rect last = lastCaret_;
    *this = Attribution{};
    hasLastCaret_ = hasLast;
    lastCaret_ = last;
    backward_ = backward;
    phase_ = Phase::AwaitUnitSelection;
  }

  // Right before posting a restore press.  Returns false when the phase does
  // not allow one (at most two presses; the second only after press 1's
  // evidence said "not back").
  bool restorePosted() {
    if (phase_ == Phase::UnitReady) {
      phase_ = Phase::AwaitRestore1;
      collapseSeen_ = false;
      presses_ = 1;
      return true;
    }
    if (phase_ == Phase::NeedSecondPress) {
      phase_ = Phase::AwaitRestore2;
      known_ = lastCaret_;
      hasKnown_ = hasLastCaret_;
      presses_ = 2;
      return true;
    }
    return false;
  }

  void onSelectionStart(const Rect &r) {
    start_ = r;
    hasStart_ = true;
  }
  void onSelectionEnd(const Rect &r) {
    end_ = r;
    hasEnd_ = true;
  }

  void onTextSelection(bool nonEmpty) {
    if (phase_ == Phase::AwaitUnitSelection && nonEmpty) {
      hasP_ = hasLastCaret_;
      p_ = lastCaret_;
      hasAnchor_ = backward_ ? hasEnd_ : hasStart_;
      anchor_ = backward_ ? end_ : start_;
      phase_ = Phase::AwaitUnitCaret;
    } else if (phase_ == Phase::AwaitRestore1 && !nonEmpty) {
      collapseSeen_ = true;
    }
    clearAnchors();
  }

  void onCaret(const Rect &r) {
    switch (phase_) {
    case Phase::AwaitUnitCaret:
      hasU_ = true;
      u_ = r;
      phase_ = Phase::UnitReady;
      break;
    case Phase::AwaitRestore1:
      if (collapseSeen_)
        phase_ = (hasP_ && r == p_) ? Phase::Restored : Phase::NeedSecondPress;
      break;
    case Phase::AwaitRestore2:
      if (!hasKnown_ || r != known_)
        phase_ = (hasP_ && r == p_) ? Phase::Restored : Phase::NotRestored;
      break;
    default:
      break;
    }
    hasLastCaret_ = true;
    lastCaret_ = r;
    clearAnchors();
  }

  Phase phase() const { return phase_; }
  int presses() const { return presses_; }
  bool hasP() const { return hasP_; }
  const Rect &p() const { return p_; }
  bool hasAnchor() const { return hasAnchor_; }
  const Rect &anchor() const { return anchor_; }
  bool hasU() const { return hasU_; }
  const Rect &u() const { return u_; }
  bool fenceHolds() const {
    return hasP_ && hasAnchor_ && anchorFenceHolds(p_, anchor_);
  }

private:
  // 14.3: an anchor is only ever read at the TEXT_SELECTION of its own flush.
  // Writer queues START, END, TEXT_SELECTION contiguously at flush time
  // (init.cxx:2395-2412) and the caret after them, so clearing on every
  // TEXT_SELECTION and caret leaves, at the unit's TEXT_SELECTION, only what
  // that flush sent.
  void clearAnchors() { hasStart_ = hasEnd_ = false; }

  Phase phase_ = Phase::Idle;
  bool backward_ = false;
  bool hasLastCaret_ = false;
  Rect lastCaret_;
  bool hasStart_ = false, hasEnd_ = false;
  Rect start_, end_;
  bool hasP_ = false, hasAnchor_ = false, hasU_ = false, hasKnown_ = false;
  Rect p_, anchor_, u_, known_;
  bool collapseSeen_ = false;
  int presses_ = 0;
};

// ---- stages and refusals ----------------------------------------------------
//
// Every refusal after the key is posted is EDITOR_BOUNDARY_UNSUPPORTED with
// keyPosted:true (10.1(d)); before it, keyPosted:false.  The engine names a
// stage only from this table, so the model test can check the split for every
// stage there is.
struct Stage {
  const char *name;
  bool keyPosted;
};

constexpr Stage kStages[] = {
    {"nothing-selected", false}, {"unit-caret", false},
    {"anchor-mismatch", false},  {"restore", false},
    {"undo-read", false},        {"restore-mutated", false},
    {"key-deadline", true},      {"key-read", true},
    {"key-unparsed", true},      {"key-step", true},
};

inline const Stage *findStage(const std::string &name) {
  for (const Stage &stage : kStages)
    if (name == stage.name)
      return &stage;
  return nullptr;
}

// ---- the undo payload ---------------------------------------------------------

struct UndoSummary {
  bool ok = false;
  std::size_t actions = 0;
  std::string topComment; // index 0 is the newest action (undo.cxx:1325)
};

namespace detail {
inline void appendUtf8(std::string &out, std::uint32_t c) {
  if (c < 0x80) {
    out += static_cast<char>(c);
  } else if (c < 0x800) {
    out += static_cast<char>(0xc0 | (c >> 6));
    out += static_cast<char>(0x80 | (c & 0x3f));
  } else {
    out += static_cast<char>(0xe0 | (c >> 12));
    out += static_cast<char>(0x80 | ((c >> 6) & 0x3f));
    out += static_cast<char>(0x80 | (c & 0x3f));
  }
}

// The JSON string starting after its opening quote at `pos`; false on a
// malformed escape or an unterminated string.  boost's write_json passes UTF-8
// through and escapes '"', '\\', '/' and control characters.
inline bool readJsonString(const std::string &s, std::size_t pos,
                           std::string &out) {
  out.clear();
  while (pos < s.size()) {
    const char c = s[pos++];
    if (c == '"')
      return true;
    if (c != '\\') {
      out += c;
      continue;
    }
    if (pos >= s.size())
      return false;
    const char e = s[pos++];
    switch (e) {
    case '"': out += '"'; break;
    case '\\': out += '\\'; break;
    case '/': out += '/'; break;
    case 'b': out += '\b'; break;
    case 'f': out += '\f'; break;
    case 'n': out += '\n'; break;
    case 'r': out += '\r'; break;
    case 't': out += '\t'; break;
    case 'u': {
      if (pos + 4 > s.size())
        return false;
      std::uint32_t v = 0;
      for (int i = 0; i < 4; ++i) {
        const char h = s[pos++];
        v <<= 4;
        if (h >= '0' && h <= '9') v |= h - '0';
        else if (h >= 'a' && h <= 'f') v |= h - 'a' + 10;
        else if (h >= 'A' && h <= 'F') v |= h - 'A' + 10;
        else return false;
      }
      if (v >= 0xd800 && v <= 0xdfff)
        return false;
      appendUtf8(out, v);
      break;
    }
    default:
      return false;
    }
  }
  return false;
}

inline std::size_t skipSpace(const std::string &s, std::size_t pos) {
  while (pos < s.size() &&
         (s[pos] == ' ' || s[pos] == '\n' || s[pos] == '\r' || s[pos] == '\t'))
    ++pos;
  return pos;
}

// Position just after `"key"` followed by ':' and spaces, from `from`.
inline std::size_t findKey(const std::string &s, const char *key,
                           std::size_t from) {
  const std::string quoted = std::string("\"") + key + "\"";
  std::size_t at = s.find(quoted, from);
  while (at != std::string::npos) {
    std::size_t pos = skipSpace(s, at + quoted.size());
    if (pos < s.size() && s[pos] == ':')
      return skipSpace(s, pos + 1);
    at = s.find(quoted, at + 1);
  }
  return std::string::npos;
}
} // namespace detail

// `{"actions": ""}` (boost's empty child) is zero actions; otherwise one
// object per action, each with "index" and "comment".  Not a JSON parser: the
// payload's shape is fixed by SfxUndoManager::GetUndoActionsInfo, and anything
// else is ok=false.
inline UndoSummary summarizeUndoPayload(const std::string &payload) {
  UndoSummary out;
  std::size_t pos = detail::findKey(payload, "actions", 0);
  if (pos == std::string::npos || pos >= payload.size())
    return out;
  if (payload[pos] == '"') {
    std::string empty;
    if (!detail::readJsonString(payload, pos + 1, empty) || !empty.empty())
      return out;
    out.ok = true;
    return out;
  }
  if (payload[pos] != '[')
    return out;
  std::size_t from = pos;
  for (;;) {
    const std::size_t index = detail::findKey(payload, "index", from);
    if (index == std::string::npos)
      break;
    const std::size_t comment = detail::findKey(payload, "comment", index);
    std::string text;
    if (comment == std::string::npos || comment >= payload.size() ||
        payload[comment] != '"' ||
        !detail::readJsonString(payload, comment + 1, text))
      return UndoSummary{};
    if (out.actions == 0)
      out.topComment = text;
    ++out.actions;
    from = comment;
  }
  out.ok = out.actions > 0;
  return out;
}

// Before the key (10.1(f)): P_start was read when the transaction began, P0
// after the restore.  Returns nullptr to post the key, else the stage.
inline const char *judgeBeforeKey(bool startReadOk, const std::string &pStart,
                                  bool p0ReadOk, const std::string &p0) {
  if (!startReadOk || !p0ReadOk)
    return "undo-read";
  if (pStart != p0)
    return "restore-mutated";
  return nullptr;
}

enum class KeyVerdict { Pending, Verified, Refused };

struct KeyJudgement {
  KeyVerdict verdict = KeyVerdict::Pending;
  const char *stage = nullptr; // set when Refused
  UndoSummary before, after;   // set when Verified
};

// After the key (3.1 items 8 and 9, 10.1(b), 10.1(d)): the whole payload
// against P0.  Changed and readable with at least one action -> verified.
// Changed but unreadable is refused with the key posted rather than completed
// with a count the shell would reject (10.1(e): that rejection rolls back).
inline KeyJudgement judgeAfterKey(const std::string &p0, bool readOk,
                                  const std::string &now, bool atDeadline) {
  KeyJudgement out;
  if (!readOk) {
    out.verdict = KeyVerdict::Refused;
    out.stage = "key-read";
    return out;
  }
  if (now == p0) {
    if (atDeadline) {
      out.verdict = KeyVerdict::Refused;
      out.stage = "key-deadline";
    }
    return out;
  }
  out.before = summarizeUndoPayload(p0);
  out.after = summarizeUndoPayload(now);
  if (!out.after.ok || out.after.actions < 1) {
    out.verdict = KeyVerdict::Refused;
    out.stage = "key-unparsed";
    return out;
  }
  out.verdict = KeyVerdict::Verified;
  return out;
}

} // namespace merge
} // namespace probe

#endif
