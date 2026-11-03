#ifndef WASM_SDK_PROBE_DOCUMENT_FORMAT_HPP
#define WASM_SDK_PROBE_DOCUMENT_FORMAT_HPP

// specs/SPEC-P-ms-formats.md 5.1 E1: which names `oxsdk_document_open` accepts and which formats
// `oxsdk_document_save` writes, per profile, as one closed table.  Only the OXSDK_MS_FORMATS builds
// (Writer e2-editor-v33, Calc ods-editor-v5) include it; the older builds keep src/ods_viewer.hpp's
// acceptedSuffix and the literal checks in src/sdk_api.cpp, byte for byte.
//
// Held by tests/document_format_test.cpp (native, no core); its red cases, one per table entry and
// one per rule, are generated from this file by tests/document_format_mutations.py.
//
// finding 013's prescription: the name that passes validation is the name the input file gets in
// MEMFS, and the format the open reply reports, so validation, path and capability say one thing.

#include <cctype>
#include <cstddef>
#include <string>

namespace probe::docformat {

enum class Profile { Writer, Calc };

struct Entry {
  const char *suffix; // accepted at open, lower-case, with the dot
  const char *format; // reported by the open reply and accepted by save
  bool savable;       // the save boundary writes this format
};

// The table.  Calc keeps `.odt` at open because ods-editor-v4 accepts it (ods_viewer.hpp); it was
// never savable there, and is not here.
inline constexpr Entry kWriter[] = {
    {".odt", "odt", true},
    {".docx", "docx", true},
};
inline constexpr Entry kCalc[] = {
    {".odt", "odt", false},
    {".ods", "ods", true},
    {".xlsx", "xlsx", true},
};

// The profile this build is: the Calc editor's rules define OXSDK_ODS_EDITOR, the Writer editor's do not.
#ifdef OXSDK_ODS_EDITOR
inline constexpr Profile kThisBuild = Profile::Calc;
#else
inline constexpr Profile kThisBuild = Profile::Writer;
#endif

template <std::size_t N>
constexpr std::size_t countOf(const Entry (&)[N]) { return N; }

inline const Entry *table(Profile profile, std::size_t &count) {
  if (profile == Profile::Calc) {
    count = countOf(kCalc);
    return kCalc;
  }
  count = countOf(kWriter);
  return kWriter;
}

inline std::string lower(std::string text) {
  for (char &c : text)
    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return text;
}

// The table entry a name is accepted under, or nullptr.  Case does not matter (`REPORT.DOCX` is the
// same file); a name must have at least one character before the suffix.
inline const Entry *acceptedEntry(Profile profile, const std::string &name) {
  std::size_t count = 0;
  const Entry *entries = table(profile, count);
  const std::string lowered = lower(name);
  for (std::size_t i = 0; i < count; ++i) {
    const std::string suffix = entries[i].suffix;
    if (lowered.size() > suffix.size() &&
        lowered.compare(lowered.size() - suffix.size(), suffix.size(), suffix) == 0)
      return &entries[i];
  }
  return nullptr;
}

// The suffix a name is accepted under ("" for a refusal), as ods_viewer.hpp's acceptedSuffix.
inline std::string acceptedSuffix(Profile profile, const std::string &name) {
  const Entry *entry = acceptedEntry(profile, name);
  return entry ? entry->suffix : "";
}

// The format the open reply reports for an accepted name ("" for a refusal).
inline std::string openFormat(Profile profile, const std::string &name) {
  const Entry *entry = acceptedEntry(profile, name);
  return entry ? entry->format : "";
}

// Whether the save boundary writes `format` (compared as written: the worker sends lower case).
inline bool savable(Profile profile, const std::string &format) {
  std::size_t count = 0;
  const Entry *entries = table(profile, count);
  for (std::size_t i = 0; i < count; ++i)
    if (entries[i].savable && format == entries[i].format)
      return true;
  return false;
}

} // namespace probe::docformat

#endif
