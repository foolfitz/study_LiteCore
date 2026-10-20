#include "ods_viewer.hpp"

// The engine is compiled with it (E2_V5_CPPFLAGS); the document types are under it.
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKitEnums.h>

#include <cstdio>
#include <string>
#include <vector>

// SPEC-M4-ods-in-nextcloud §3.2: the rules of the ODS viewer's engine additions
// (src/ods_viewer.hpp), each checked here; tests/ods_viewer_mutations.py breaks
// the header one rule at a time and requires the named check to fail.
//
//   S1 names       .ods and .odt are accepted in any case, with a stem; the
//                  input file's suffix is the accepted one (review M1)
//   T1 types       LOK's document types on the wire, against LOK's own enum
//   R1 range       0 <= part < parts
//   X1 refused     a part out of range is refused before anything but parts()
//   X2 order       switch, select all, read, deselect, switch back
//   X3 no switch   part k already current: no setPart at all
//   X4 unconfirmed a SelectAll core did not confirm: read anyway, say so,
//                  deselect and restore
//   X5 no text     core returned nothing (an empty sheet): the empty text,
//                  flagged, not an error; deselect and restore as always
//   X6 read back   partAfter is what the document says, not what was asked for

namespace {
namespace ov = probe::odsviewer;

int gFailures = 0;
void check(bool condition, const std::string &what) {
  if (!condition) {
    ++gFailures;
    std::printf("FAIL %s\n", what.c_str());
  }
}

// Every call is logged, so a test can say what was NOT asked.
struct FakeDocument {
  int partCount = 3;
  int current = 0;
  bool selectAllLands = true;
  bool hasText = true;
  bool restoreSticks = true;      // false: setPart back to the original is ignored
  int originalPart = -1;
  std::vector<std::string> calls;

  int parts() { calls.push_back("parts"); return partCount; }
  int part() { calls.push_back("part"); return current; }
  void setPart(int k) {
    calls.push_back("setPart(" + std::to_string(k) + ")");
    if (originalPart < 0)
      originalPart = current;
    if (!restoreSticks && k == originalPart)
      return;
    current = k;
  }
  bool selectAll() { calls.push_back("selectAll"); return selectAllLands; }
  bool text(std::string &out) {
    calls.push_back("text");
    if (!hasText)
      return false;
    out = "sheet " + std::to_string(current) + "\n";
    return true;
  }
  void resetSelection() { calls.push_back("resetSelection"); }
};

std::string joined(const std::vector<std::string> &calls) {
  std::string out;
  for (const auto &call : calls)
    out += (out.empty() ? "" : " ") + call;
  return out;
}

bool contains(const std::vector<std::string> &calls, const std::string &what) {
  for (const auto &call : calls)
    if (call == what)
      return true;
  return false;
}
} // namespace

static_assert(LOK_DOCTYPE_TEXT == 0 && LOK_DOCTYPE_SPREADSHEET == 1 &&
                  LOK_DOCTYPE_PRESENTATION == 2 && LOK_DOCTYPE_DRAWING == 3 &&
                  LOK_DOCTYPE_OTHER == 4,
              "documentTypeName's numbering is LibreOfficeKitEnums.h's");

int main() {
  // S1
  check(ov::acceptedSuffix("book.ods") == ".ods", "S1 book.ods is accepted as .ods");
  check(ov::acceptedSuffix("BOOK.ODS") == ".ods", "S1 BOOK.ODS is accepted as .ods");
  check(ov::acceptedSuffix("Report.Odt") == ".odt", "S1 Report.Odt is accepted as .odt");
  check(ov::acceptedSuffix("a.odt") == ".odt", "S1 a one-character stem is a stem");
  check(ov::acceptedSuffix(".ods").empty(), "S1 a name that is only the suffix is refused");
  check(ov::acceptedSuffix("sheet.xlsx").empty(), "S1 .xlsx is refused");
  check(ov::acceptedSuffix("bookods").empty(), "S1 no dot, no suffix");
  check(ov::acceptedSuffix("book.ods.zip").empty(), "S1 the suffix is the last one");
  check(ov::acceptedSuffix("").empty(), "S1 the empty name is refused");

  // T1
  check(std::string(ov::documentTypeName(LOK_DOCTYPE_TEXT)) == "text", "T1 text");
  check(std::string(ov::documentTypeName(LOK_DOCTYPE_SPREADSHEET)) == "spreadsheet", "T1 spreadsheet");
  check(std::string(ov::documentTypeName(LOK_DOCTYPE_PRESENTATION)) == "presentation", "T1 presentation");
  check(std::string(ov::documentTypeName(LOK_DOCTYPE_DRAWING)) == "drawing", "T1 drawing");
  check(std::string(ov::documentTypeName(LOK_DOCTYPE_OTHER)) == "other", "T1 other");
  check(std::string(ov::documentTypeName(-1)) == "other", "T1 an unknown value is other");

  // R1
  check(ov::partInRange(0, 1) && ov::partInRange(2, 3), "R1 in range");
  check(!ov::partInRange(3, 3), "R1 parts itself is out of range");
  check(!ov::partInRange(-1, 3), "R1 a negative part is out of range");
  check(!ov::partInRange(0, 0), "R1 a document with no parts has no part 0");

  // X1
  {
    FakeDocument document;
    const auto result = ov::readPartText(document, 3);
    check(result.status == ov::PartTextStatus::OutOfRange, "X1 part 3 of 3 is refused");
    check(joined(document.calls) == "parts", "X1 nothing but parts() is asked: " + joined(document.calls));
    check(std::string(ov::partTextStatusCode(result.status)) == "INVALID_ARGUMENT", "X1 the code");
    FakeDocument negative;
    check(ov::readPartText(negative, -1).status == ov::PartTextStatus::OutOfRange, "X1 a negative part");
  }
  // X2
  {
    FakeDocument document;
    const auto result = ov::readPartText(document, 2);
    check(result.status == ov::PartTextStatus::Ok, "X2 ok");
    check(result.text == "sheet 2\n", "X2 the text is part 2's: " + result.text);
    check(joined(document.calls) ==
              "parts part setPart(2) selectAll text resetSelection part setPart(0) part",
          "X2 the order: " + joined(document.calls));
    check(result.partBefore == 0 && result.partAfter == 0 && document.current == 0,
          "X2 back on part 0");
  }
  // X3
  {
    FakeDocument document;
    document.current = 1;
    const auto result = ov::readPartText(document, 1);
    check(result.status == ov::PartTextStatus::Ok && result.text == "sheet 1\n", "X3 ok");
    for (const auto &call : document.calls)
      check(call.rfind("setPart", 0) != 0, "X3 no switch when part k is current: " + joined(document.calls));
  }
  // X4
  {
    FakeDocument document;
    document.selectAllLands = false;
    const auto result = ov::readPartText(document, 1);
    check(result.status == ov::PartTextStatus::Ok, "X4 an unconfirmed SelectAll is not an error");
    check(!result.selectAllConfirmed, "X4 the result says the SelectAll was not confirmed");
    check(contains(document.calls, "text") && result.text == "sheet 1\n", "X4 the text is read anyway");
    check(contains(document.calls, "resetSelection"), "X4 deselected anyway: " + joined(document.calls));
    check(document.current == 0 && result.partAfter == 0, "X4 restored anyway");
  }
  {
    FakeDocument document;
    check(ov::readPartText(document, 1).selectAllConfirmed, "X4 a confirmed SelectAll says so");
  }
  // X5
  {
    FakeDocument document;
    document.hasText = false;
    const auto result = ov::readPartText(document, 2);
    check(result.status == ov::PartTextStatus::Ok, "X5 an empty sheet is not an error");
    check(result.text.empty() && result.textNull, "X5 the empty text, flagged");
    check(contains(document.calls, "resetSelection"), "X5 deselected anyway: " + joined(document.calls));
    check(document.current == 0 && result.partAfter == 0, "X5 restored anyway");
  }
  {
    FakeDocument document;
    const auto result = ov::readPartText(document, 1);
    check(!result.textNull, "X5 a sheet with text is not flagged");
  }
  // X6
  {
    FakeDocument document;
    document.restoreSticks = false;
    const auto result = ov::readPartText(document, 2);
    check(result.partBefore == 0, "X6 partBefore");
    check(result.partAfter == 2 && document.current == 2,
          "X6 a switch back that did not take is reported as such: partAfter " +
              std::to_string(result.partAfter));
  }

  std::printf("%s (%d failure%s)\n", gFailures ? "FAILED" : "ok", gFailures, gFailures == 1 ? "" : "s");
  return gFailures ? 1 : 0;
}
