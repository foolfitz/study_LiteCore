#ifndef WASM_SDK_PROBE_ODS_VIEWER_HPP
#define WASM_SDK_PROBE_ODS_VIEWER_HPP

// SPEC-M4-ods-in-nextcloud §3.2: the parts of the ODS viewer's engine additions
// that are rules rather than calls into core, in a header so a native test can
// hold them (tests/ods_viewer_test.cpp, its red cases in
// tests/ods_viewer_mutations.py).  probe_engine.cpp includes it only under
// OXSDK_ODS_VIEWER, so no other rule's objects see a byte of it.
//
// What is here:
//   * which names `oxsdk_document_open` accepts, and the suffix the input file
//     then gets (review M1: the file used to be `.odt` whatever was accepted);
//   * the spelling of LOK's document types on the wire;
//   * the part range;
//   * the order of part_text: switch, select all, read, deselect, switch back.
//     Written against a small document interface so the order, and what it
//     restores on every exit, is tested without core.

#include <cctype>
#include <cstddef>
#include <string>

namespace probe::odsviewer {

// The suffix a name is accepted under, lower-case, or "" for a refusal.  Case
// does not matter for either: a spreadsheet saved as `BOOK.ODS` is the same
// file, and the viewer passes the user's name through untouched.
inline std::string acceptedSuffix(const std::string &name) {
  if (name.size() < 5)                  // at least one character before ".od?"
    return {};
  std::string tail = name.substr(name.size() - 4);
  for (char &c : tail)
    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  if (tail == ".odt" || tail == ".ods")
    return tail;
  return {};
}

// LOK_DOCTYPE_* (LibreOfficeKitEnums.h: TEXT, SPREADSHEET, PRESENTATION,
// DRAWING, OTHER, in that order; probe_engine.cpp static_asserts the values).
inline const char *documentTypeName(int lokDocumentType) {
  switch (lokDocumentType) {
  case 0:
    return "text";
  case 1:
    return "spreadsheet";
  case 2:
    return "presentation";
  case 3:
    return "drawing";
  default:
    return "other";
  }
}

inline bool partInRange(int part, int parts) {
  return part >= 0 && part < parts;
}

enum class PartTextStatus { Ok, OutOfRange };

inline const char *partTextStatusCode(PartTextStatus status) {
  switch (status) {
  case PartTextStatus::Ok:
    return "OK";
  case PartTextStatus::OutOfRange:
    return "INVALID_ARGUMENT";
  }
  return "LOK_ERROR";
}

struct PartTextResult {
  PartTextStatus status = PartTextStatus::Ok;
  std::string text;
  // Core returned no text at all -- what an EMPTY sheet gives after SelectAll
  // (the native oracle reads `text: null` there, and the corpus expects "").
  // Reported as the empty text, flagged, never as an error: E3 compares the
  // text, so a sheet with content that came back empty is red there anyway.
  bool textNull = false;
  // Core confirmed the SelectAll before the caller's deadline.  When it did
  // not, the text is read anyway and this says so: a read of a selection that
  // had not landed is a wrong text, which E3 sees, and this tells it why.
  bool selectAllConfirmed = false;
  int partBefore = -1;
  int partAfter = -1;
};

// `Document` provides:
//   int parts();  int part();  void setPart(int);
//   bool selectAll();             true when core confirmed the selection
//                                 before the caller's deadline; the text is
//                                 read either way, and the result says which
//   bool text(std::string &out);  false when core returned no text at all
//                                 (an empty sheet: the text is "", flagged)
//   void resetSelection();
//
// The rules, each a red case in the test:
//   * a part out of range is refused before anything but parts() is asked;
//   * the text is read whether or not the SelectAll was confirmed, and the
//     result records which (one missing notification must not need a relink
//     to see past);
//   * the selection is reset on EVERY path past selectAll, the unconfirmed
//     one included;
//   * the part is put back to the one that was current before, on every path,
//     and what is reported as partAfter is READ, not assumed;
//   * no switch is made when part k is already the current one.
template <typename Document>
PartTextResult readPartText(Document &document, int part) {
  PartTextResult result;
  if (!partInRange(part, document.parts())) {
    result.status = PartTextStatus::OutOfRange;
    return result;
  }
  result.partBefore = document.part();
  if (part != result.partBefore)
    document.setPart(part);
  result.selectAllConfirmed = document.selectAll();
  if (!document.text(result.text)) {
    result.text.clear();
    result.textNull = true;
  }
  document.resetSelection();
  if (document.part() != result.partBefore)
    document.setPart(result.partBefore);
  result.partAfter = document.part();
  return result;
}

#ifdef OXSDK_ODS_VIEWER_V2
// SPEC-M4-viewer-v2 8 (finding 160).  LOK at times does not dispatch
// .uno:SelectAll at all: getError() says "Failed to dispatch .uno:SelectAll",
// no listener is called, no result comes and nothing is selected (5 of 5
// unconfirmed reads over six corpus sweeps, v1 and v2; the next sheet's
// dispatch worked).  A longer wait cannot help a command that was never sent.
// So a post LOK did not dispatch is posted again after a pause, until the
// deadline; a dispatched one is waited for as before and never posted twice.
struct SelectAllAttempt {
  bool confirmed = false;   // a dispatched SelectAll's result came in time
  bool dispatched = false;  // some post was dispatched
  int dispatchFailures = 0; // posts LOK did not dispatch
};

// `Poster` provides:
//   bool post();         true when LOK dispatched the command
//   bool await(int ms);  true when its result came within ms (ms may be 0)
//   int elapsedMs();     since the first post
//   void pause(int ms);
//
// The rules, each a red case in the test:
//   * a post that was not dispatched is posted again, after a pause;
//   * a dispatched post is awaited for what is left of the deadline and is
//     never posted again, confirmed or not;
//   * no post starts once the next pause would reach the deadline.
template <typename Poster>
SelectAllAttempt selectAllUntilDispatched(Poster &poster, int deadlineMs, int pauseMs) {
  SelectAllAttempt attempt;
  for (;;) {
    if (poster.post()) {
      attempt.dispatched = true;
      const int left = deadlineMs - poster.elapsedMs();
      attempt.confirmed = poster.await(left > 0 ? left : 0);
      return attempt;
    }
    ++attempt.dispatchFailures;
    if (poster.elapsedMs() + pauseMs >= deadlineMs)
      return attempt;
    poster.pause(pauseMs);
  }
}
#endif

} // namespace probe::odsviewer

#endif
