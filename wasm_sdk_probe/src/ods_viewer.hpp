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

enum class PartTextStatus { Ok, OutOfRange, SelectAllTimedOut, NoText };

inline const char *partTextStatusCode(PartTextStatus status) {
  switch (status) {
  case PartTextStatus::Ok:
    return "OK";
  case PartTextStatus::OutOfRange:
    return "INVALID_ARGUMENT";
  case PartTextStatus::SelectAllTimedOut:
    return "PART_TEXT_TIMEOUT";
  case PartTextStatus::NoText:
    return "LOK_ERROR";
  }
  return "LOK_ERROR";
}

struct PartTextResult {
  PartTextStatus status = PartTextStatus::Ok;
  std::string text;
  int partBefore = -1;
  int partAfter = -1;
};

// `Document` provides:
//   int parts();  int part();  void setPart(int);
//   bool selectAll();             true when core confirmed the selection
//                                 before the caller's deadline
//   bool text(std::string &out);  false when core returned no text at all
//   void resetSelection();
//
// The rules, each a red case in the test:
//   * a part out of range is refused before anything but parts() is asked;
//   * the selection is reset on EVERY path past selectAll, the timed-out one
//     included: a SelectAll that lands late must not stay on screen;
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
  if (!document.selectAll())
    result.status = PartTextStatus::SelectAllTimedOut;
  else if (!document.text(result.text))
    result.status = PartTextStatus::NoText;
  document.resetSelection();
  if (document.part() != result.partBefore)
    document.setPart(result.partBefore);
  result.partAfter = document.part();
  return result;
}

} // namespace probe::odsviewer

#endif
