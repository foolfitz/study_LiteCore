#include "a11y_paragraph_identity.hpp"

#include <cstdio>
#include <string>
#include <vector>

// Finding 082's rule, driven on the host so it does not need a wasm link.
//
// Every fingerprint asserted here is one the ACCESSIBILITY PROFILE actually
// reported on 2026-08-26 (`findings/evidence/082/product-path-v9-round-2.json`,
// the `caretParagraphs` trace).  That makes this a cross-implementation check
// rather than a restatement: the slice-and-hash below is a second derivation of
// what `parseEditorSemanticJson` does, and if the two ever disagree about a
// paragraph the engine really read, this goes red.
namespace {

int gFailures = 0;

void check(const char *name, bool condition) {
  if (condition) return;
  ++gFailures;
  std::printf("FAIL %s\n", name);
}

// The slice the engine hashes: the content minus `listPrefixLength` characters,
// counted in the UTF-16 code units core counts in (`rtl::OUString::copy`).
// Written here in UTF-8 because the host has no `rtl`; the measured rows below
// are what say the two agree.
std::string sliceUtf16Units(const std::string &content, int prefixUnits) {
  int units = 0;
  std::size_t index = 0;
  while (index < content.size() && units < prefixUnits) {
    const unsigned char lead = static_cast<unsigned char>(content[index]);
    std::size_t width = 1;
    if ((lead & 0x80u) == 0x00u) width = 1;
    else if ((lead & 0xE0u) == 0xC0u) width = 2;
    else if ((lead & 0xF0u) == 0xE0u) width = 3;
    else width = 4;
    // Outside the BMP a code point is TWO UTF-16 units, which is the one place
    // this arithmetic could differ from core's.
    units += (width == 4) ? 2 : 1;
    index += width;
  }
  return content.substr(index);
}

struct Row {
  const char *name;
  const char *content;
  int listPrefixLength;
  int contentLength;
  std::uint64_t measuredFingerprint;
  bool usable;
};

void checkRow(const Row &row) {
  const std::uint64_t got =
      probe::fingerprintOf(sliceUtf16Units(row.content, row.listPrefixLength));
  if (got != row.measuredFingerprint) {
    ++gFailures;
    std::printf("FAIL %s: derived %llx, the engine reported %llx\n", row.name,
                static_cast<unsigned long long>(got),
                static_cast<unsigned long long>(row.measuredFingerprint));
  }
  const bool usable = probe::paragraphFingerprintIsUsable(row.listPrefixLength,
                                                          row.contentLength);
  if (usable != row.usable) {
    ++gFailures;
    std::printf("FAIL %s: usable=%d, expected %d\n", row.name, usable,
                row.usable);
  }
}

} // namespace

int main() {
  // ------------------------------------------- the constant IS the empty hash
  //
  // Not asserted for its own sake: "an empty slice cannot identify anything" is
  // only true because these are the same number.  The digit-short basis this
  // tree shipped on 2026-08-17 would fail here.
  check("the empty string hashes to the named constant",
        probe::fingerprintOf("") == probe::kEmptyFingerprint);
  check("a non-empty slice does not",
        probe::fingerprintOf("E1-LC-HEADING") != probe::kEmptyFingerprint);

  // ------------------------------------------------------------ MEASURED rows
  const Row rows[] = {
      // The heading finding 074 breaks: thirteen characters, thirteen claimed
      // as prefix, so the slice is empty and the fingerprint is the unfed
      // constant.  This is the row that killed the accessibility run.
      {"heading swallowed by its own prefix", "E1-LC-HEADING", 13, 13,
       0xcbf29ce484222325ull, false},
      // The row it collides with: a paragraph holding only a bullet.  Same
      // constant, and for this one the empty slice is not even wrong.
      {"a paragraph holding only a bullet", "\xE2\x80\xA2 ", 2, 2,
       0xcbf29ce484222325ull, false},
      // THE CASE THAT MUST SURVIVE.  A real bullet on a paragraph with text:
      // the slice removes the decoration, so bulleting does not change the
      // fingerprint.  That is why the stripping exists, and a fix that threw it
      // away would refuse every successful list action.
      {"text without its bullet", "E1-LC-END\xE7\x94\xB2\xE4\xB8\x80"
                                  "\xE4\xB9\x99\xE4\xBA\x8C\xE4\xB8\x99"
                                  "\xE4\xB8\x89\xE6\x8F\x92\xE5\x85\xA5"
                                  "\xE9\x88\x95\xE6\xA8\x99\xE8\xA8\x98",
       0, 20, 0x76f09d751bb341f7ull, true},
      {"the same text with its bullet",
       "\xE2\x80\xA2 E1-LC-END\xE7\x94\xB2\xE4\xB8\x80"
       "\xE4\xB9\x99\xE4\xBA\x8C\xE4\xB8\x99"
       "\xE4\xB8\x89\xE6\x8F\x92\xE5\x85\xA5"
       "\xE9\x88\x95\xE6\xA8\x99\xE8\xA8\x98",
       2, 22, 0x76f09d751bb341f7ull, true},
      {"a numbered item", "1. E1-LC-NUMBER-ONE", 3, 19,
       0xd0586a07b98862c6ull, true},
      {"an ordinary paragraph", "E1-LC-END", 0, 9,
       0x38f80576561a9997ull, true},
  };
  for (const Row &row : rows) checkRow(row);

  // The two collide, and it is stated as a check so that a change which
  // separated them would be noticed rather than assumed.
  check("the heading and the bullet are one fingerprint",
        probe::fingerprintOf(sliceUtf16Units("E1-LC-HEADING", 13))
            == probe::fingerprintOf(sliceUtf16Units("\xE2\x80\xA2 ", 2)));

  // ------------------------------------------------------- the empty paragraph
  //
  // Zero of zero is not swallowed: the empty hash is the CORRECT reading of an
  // empty paragraph, and the barrier already declares two of them
  // indistinguishable.  Refusing it would take away a reading that was never
  // wrong.
  check("a genuinely empty paragraph keeps its fingerprint",
        probe::paragraphFingerprintIsUsable(0, 0));
  check("and it is not called swallowed",
        !probe::prefixSwallowedTheParagraph(0, 0));

  // --------------------------------------------------------------- the margins
  check("a prefix longer than the content is swallowed",
        probe::prefixSwallowedTheParagraph(20, 13));
  check("one character short is not",
        !probe::prefixSwallowedTheParagraph(12, 13));
  check("an unread paragraph (contentLength -1) has no usable fingerprint",
        !probe::paragraphFingerprintIsUsable(0, -1));

  if (gFailures == 0)
    std::printf("a11y paragraph identity: all checks passed\n");
  return gFailures == 0 ? 0 : 1;
}
