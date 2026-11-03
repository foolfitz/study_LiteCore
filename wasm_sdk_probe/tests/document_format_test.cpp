// specs/SPEC-P-ms-formats.md 6.1 F1: src/document_format.hpp, every cell of table E1, native, no core.
// Red cases: tests/document_format_mutations.py (generated from the header's table).
//   g++ -std=c++17 -I src tests/document_format_test.cpp -o /tmp/t && /tmp/t
#include "document_format.hpp"

#include <cstdio>
#include <string>
#include <vector>

namespace df = probe::docformat;

namespace {
int failures = 0;

void check(bool ok, const std::string &what) {
  if (!ok) {
    ++failures;
    std::printf("FAIL %s\n", what.c_str());
  }
}

struct Expected {
  std::string suffix, format;
  bool savable;
};

// Table E1 as the spec writes it.  The header must equal this exactly: an entry added there and not
// here is as red as one missing.
const std::vector<Expected> kWriter = {{".odt", "odt", true}, {".docx", "docx", true}};
const std::vector<Expected> kCalc = {{".odt", "odt", false}, {".ods", "ods", true}, {".xlsx", "xlsx", true}};

// Names no profile accepts (the spec's refusals and the shapes around a suffix).
const std::vector<std::string> kRefusedEverywhere = {
    "a.doc", "a.xls", "a.docm", "a.xlsm", "a.dotx", "a.xltx", "a.rtf", "a.csv", "a.pdf", "a.ott",
    "", "docx", "odt", "a.docx.zip", "a.ods.bak", "a.od", "a.xlsx ", " "};

void profile(df::Profile which, const char *label, const std::vector<Expected> &expected,
             const std::vector<std::string> &refusedHere) {
  const std::string p = label;
  std::size_t count = 0;
  const df::Entry *entries = df::table(which, count);
  // T1 the table is exactly the spec's.
  check(count == expected.size(), "T1 " + p + " has " + std::to_string(expected.size()) + " entries");
  for (std::size_t i = 0; i < expected.size() && i < count; ++i) {
    const auto &e = expected[i];
    check(entries[i].suffix == e.suffix && entries[i].format == e.format && entries[i].savable == e.savable,
          "T1 " + p + " entry " + std::to_string(i) + " is " + e.suffix);
  }
  for (const auto &e : expected) {
    const std::string stem = "Report";
    // A1 accepted under its own suffix, either case, with a one-character stem.
    check(df::acceptedSuffix(which, stem + e.suffix) == e.suffix, "A1 " + p + " accepts report" + e.suffix);
    check(df::acceptedSuffix(which, df::lower(stem) + df::lower(e.suffix)) == e.suffix, "A1 " + p + " lower case " + e.suffix);
    std::string upper = e.suffix;
    for (char &c : upper) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    check(df::acceptedSuffix(which, "REPORT" + upper) == e.suffix, "A1 " + p + " upper case " + e.suffix);
    check(df::acceptedSuffix(which, "a" + e.suffix) == e.suffix, "A1 " + p + " one-character stem " + e.suffix);
    check(df::acceptedSuffix(which, "我的文件" + e.suffix) == e.suffix, "A1 " + p + " a CJK stem " + e.suffix);
    // R1 the suffix alone is not a name.
    check(df::acceptedSuffix(which, e.suffix).empty(), "R1 " + p + " refuses the bare " + e.suffix);
    // O1 the open reply's format.
    check(df::openFormat(which, stem + e.suffix) == e.format, "O1 " + p + " reports " + e.format);
    // S1 save follows the table, as written (the worker sends lower case).
    check(df::savable(which, e.format) == e.savable, "S1 " + p + " save " + e.format);
    std::string upperFormat = e.format;
    for (char &c : upperFormat) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    check(!df::savable(which, upperFormat), "S1 " + p + " save is compared as written: " + upperFormat);
  }
  for (const auto &name : kRefusedEverywhere) {
    check(df::acceptedSuffix(which, name).empty(), "R1 " + p + " refuses '" + name + "'");
    check(df::openFormat(which, name).empty(), "O1 " + p + " reports nothing for '" + name + "'");
  }
  for (const auto &name : refusedHere)
    check(df::acceptedSuffix(which, name).empty(), "R1 " + p + " refuses '" + name + "'");
  for (const char *format : {"doc", "xls", "docm", "xlsm", "rtf", "csv", "pdf", "", "ods.", "odt "})
    check(!df::savable(which, format), "S1 " + p + " refuses to save '" + std::string(format) + "'");
}
} // namespace

int main() {
  profile(df::Profile::Writer, "writer", kWriter, {"a.ods", "a.xlsx"});
  profile(df::Profile::Calc, "calc", kCalc, {"a.docx"});
  check(!df::savable(df::Profile::Writer, "ods") && !df::savable(df::Profile::Writer, "xlsx"),
        "S1 writer does not save spreadsheet formats");
  check(!df::savable(df::Profile::Calc, "docx"), "S1 calc does not save docx");
  if (failures) {
    std::printf("%d failure(s)\n", failures);
    return 1;
  }
  std::printf("ok\n");
  return 0;
}
