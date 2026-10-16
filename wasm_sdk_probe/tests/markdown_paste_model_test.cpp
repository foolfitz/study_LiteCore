// SPEC-M3-link-batch-v21 11.2 M0 (with 12.1): src/markdown_paste.hpp, run
// natively against the core's own md4c 0.5.3, over the fixture committed
// before any scanner code existed (tests/markdown_paste_expected.json at
// 975343c2; corpus tests/markdown_paste_corpus/).
//
// Build and run from wasm_sdk_probe/ (a native test; md4c.c is never compiled
// into the engine, spec 10.4):
//
//   MD4C=../wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src
//   gcc -std=c99 -O2 -c $MD4C/md4c.c -o build/md4c-native.o
//   g++ -std=c++17 -O2 -Wall -Isrc -I$MD4C -DOXSDK_E2_V21_LINK_BATCH
//       -o build/markdown_paste_model_test tests/markdown_paste_model_test.cpp
//       build/md4c-native.o -Wl,--wrap=malloc,--wrap=realloc
//   (one command; the line breaks are this comment's, not the shell's)
//   build/markdown_paste_model_test [FIXTURE.json [CORPUS_DIR]]
//
// tests/markdown_paste_mutations.py builds it exactly so, against the header
// and against each of M0's red mutations of it.
//
// What it checks:
//   A. the fixture, tool-closed: the corpus directory's files and the
//      fixture's items are the same set; each file's size and sha256 are the
//      fixture's; the fixture's verdict order is the header's label set;
//      every item's verdict from judgeBytes() equals the fixture's;
//   B. PARSE_FAIL by injection (12.1): every allocation inside md_parse fails
//      for an item marked `"inject": "allocation-failure"`.  Positive control:
//      the wrapper must actually have refused at least one allocation, and the
//      same bytes without the injection must give `verdictWithoutInjection`;
//   C. the RFC 3629 validator against an independent oracle (decode by bit
//      pattern, then reject overlong, surrogate and > U+10FFFF), exhaustively
//      over every 1-, 2- and 3-byte buffer and over every 4-byte buffer whose
//      last two bytes are drawn from a set of boundary values;
//   D. the size boundary (65,536 accepted, 65,537 refused), in ASCII and in
//      3-byte CJK with an ASCII tail, and the order of the byte rules;
//   E. 10.2's collapsed rule on the cases the spec names, and the interface's
//      order for codes 1-5 with the encoding and caret reads asked lazily;
//   F. 9.4's post-dispatch judge;
//   G. the code table: every byte verdict but PASS maps to a pre-dispatch
//      code, the pre-dispatch list is the interface's order without
//      duplicates, and the post-dispatch code is not in it.

#include "markdown_paste.hpp"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

// ---- allocation-failure injection (B) -----------------------------------------
//
// Linked with -Wl,--wrap=malloc,--wrap=realloc: md4c.o's calls land here.
// The test's own allocations go through operator new in libstdc++ (a shared
// library, which --wrap does not reach), so only md4c is affected.
extern "C" void *__real_malloc(std::size_t);
extern "C" void *__real_realloc(void *, std::size_t);
static bool gFailAllocations = false;
static std::size_t gRefusedAllocations = 0;
extern "C" void *__wrap_malloc(std::size_t n) {
  if (gFailAllocations) {
    ++gRefusedAllocations;
    return nullptr;
  }
  return __real_malloc(n);
}
extern "C" void *__wrap_realloc(void *p, std::size_t n) {
  if (gFailAllocations) {
    ++gRefusedAllocations;
    return nullptr;
  }
  return __real_realloc(p, n);
}

namespace {

namespace md = probe::markdown;

int gFailures = 0;
int gChecks = 0;
void check(bool ok, const std::string &what) {
  ++gChecks;
  if (!ok) {
    ++gFailures;
    std::printf("FAIL %s\n", what.c_str());
  }
}

// ---- a strict, small JSON reader (the fixture is the oracle; read it whole) ----

struct Json {
  enum Type { Null, Bool, Number, String, Array, Object } type = Null;
  bool boolean = false;
  double number = 0;
  std::string string;
  std::vector<Json> array;
  std::vector<std::pair<std::string, Json>> object;
  const Json *get(const std::string &key) const {
    for (const auto &kv : object)
      if (kv.first == key)
        return &kv.second;
    return nullptr;
  }
};

struct JsonReader {
  const std::string &s;
  std::size_t pos = 0;
  bool ok = true;
  explicit JsonReader(const std::string &text) : s(text) {}
  void space() {
    while (pos < s.size() &&
           (s[pos] == ' ' || s[pos] == '\n' || s[pos] == '\r' || s[pos] == '\t'))
      ++pos;
  }
  bool literal(const char *word) {
    const std::size_t n = std::strlen(word);
    if (s.compare(pos, n, word) != 0)
      return false;
    pos += n;
    return true;
  }
  static void utf8(std::string &out, std::uint32_t c) {
    if (c < 0x80) {
      out += static_cast<char>(c);
    } else if (c < 0x800) {
      out += static_cast<char>(0xc0 | (c >> 6));
      out += static_cast<char>(0x80 | (c & 0x3f));
    } else if (c < 0x10000) {
      out += static_cast<char>(0xe0 | (c >> 12));
      out += static_cast<char>(0x80 | ((c >> 6) & 0x3f));
      out += static_cast<char>(0x80 | (c & 0x3f));
    } else {
      out += static_cast<char>(0xf0 | (c >> 18));
      out += static_cast<char>(0x80 | ((c >> 12) & 0x3f));
      out += static_cast<char>(0x80 | ((c >> 6) & 0x3f));
      out += static_cast<char>(0x80 | (c & 0x3f));
    }
  }
  bool hex4(std::uint32_t &v) {
    if (pos + 4 > s.size())
      return false;
    v = 0;
    for (int i = 0; i < 4; ++i) {
      const char h = s[pos++];
      v <<= 4;
      if (h >= '0' && h <= '9') v |= h - '0';
      else if (h >= 'a' && h <= 'f') v |= h - 'a' + 10;
      else if (h >= 'A' && h <= 'F') v |= h - 'A' + 10;
      else return false;
    }
    return true;
  }
  bool str(std::string &out) {
    if (pos >= s.size() || s[pos] != '"')
      return false;
    ++pos;
    out.clear();
    while (pos < s.size()) {
      const char c = s[pos++];
      if (c == '"')
        return true;
      if (static_cast<unsigned char>(c) < 0x20)
        return false;
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
        std::uint32_t v;
        if (!hex4(v))
          return false;
        if (v >= 0xd800 && v <= 0xdbff) {
          std::uint32_t lo;
          if (!literal("\\u") || !hex4(lo) || lo < 0xdc00 || lo > 0xdfff)
            return false;
          v = 0x10000 + ((v - 0xd800) << 10) + (lo - 0xdc00);
        } else if (v >= 0xdc00 && v <= 0xdfff) {
          return false;
        }
        utf8(out, v);
        break;
      }
      default:
        return false;
      }
    }
    return false;
  }
  bool value(Json &out) {
    space();
    if (pos >= s.size())
      return false;
    const char c = s[pos];
    if (c == '{') {
      ++pos;
      out.type = Json::Object;
      space();
      if (pos < s.size() && s[pos] == '}') {
        ++pos;
        return true;
      }
      for (;;) {
        space();
        std::string key;
        if (!str(key))
          return false;
        space();
        if (pos >= s.size() || s[pos++] != ':')
          return false;
        Json v;
        if (!value(v))
          return false;
        out.object.emplace_back(std::move(key), std::move(v));
        space();
        if (pos < s.size() && s[pos] == ',') {
          ++pos;
          continue;
        }
        if (pos < s.size() && s[pos] == '}') {
          ++pos;
          return true;
        }
        return false;
      }
    }
    if (c == '[') {
      ++pos;
      out.type = Json::Array;
      space();
      if (pos < s.size() && s[pos] == ']') {
        ++pos;
        return true;
      }
      for (;;) {
        Json v;
        if (!value(v))
          return false;
        out.array.push_back(std::move(v));
        space();
        if (pos < s.size() && s[pos] == ',') {
          ++pos;
          continue;
        }
        if (pos < s.size() && s[pos] == ']') {
          ++pos;
          return true;
        }
        return false;
      }
    }
    if (c == '"') {
      out.type = Json::String;
      return str(out.string);
    }
    if (literal("true")) {
      out.type = Json::Bool;
      out.boolean = true;
      return true;
    }
    if (literal("false")) {
      out.type = Json::Bool;
      return true;
    }
    if (literal("null")) {
      out.type = Json::Null;
      return true;
    }
    const std::size_t start = pos;
    while (pos < s.size() && (std::strchr("+-0123456789.eE", s[pos]) != nullptr))
      ++pos;
    if (pos == start)
      return false;
    out.type = Json::Number;
    out.number = std::strtod(s.substr(start, pos - start).c_str(), nullptr);
    return true;
  }
};

// ---- SHA-256 (FIPS 180-4), to tie each corpus file to the fixture ----------

std::string sha256Hex(const std::string &data) {
  static const std::uint32_t k[64] = {
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
      0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
      0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
      0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
      0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
      0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
      0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
      0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
      0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
  std::uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
                        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  std::string m = data;
  const std::uint64_t bits = static_cast<std::uint64_t>(data.size()) * 8;
  m += static_cast<char>(0x80);
  while (m.size() % 64 != 56)
    m += static_cast<char>(0);
  for (int i = 7; i >= 0; --i)
    m += static_cast<char>((bits >> (8 * i)) & 0xff);
  auto rotr = [](std::uint32_t x, int n) { return (x >> n) | (x << (32 - n)); };
  for (std::size_t chunk = 0; chunk < m.size(); chunk += 64) {
    std::uint32_t w[64];
    for (int i = 0; i < 16; ++i)
      w[i] = (std::uint32_t(static_cast<unsigned char>(m[chunk + 4 * i])) << 24) |
             (std::uint32_t(static_cast<unsigned char>(m[chunk + 4 * i + 1])) << 16) |
             (std::uint32_t(static_cast<unsigned char>(m[chunk + 4 * i + 2])) << 8) |
             std::uint32_t(static_cast<unsigned char>(m[chunk + 4 * i + 3]));
    for (int i = 16; i < 64; ++i) {
      const std::uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
      const std::uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
      w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    std::uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5],
                  g = h[6], hh = h[7];
    for (int i = 0; i < 64; ++i) {
      const std::uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const std::uint32_t ch = (e & f) ^ (~e & g);
      const std::uint32_t t1 = hh + S1 + ch + k[i] + w[i];
      const std::uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const std::uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
      const std::uint32_t t2 = S0 + maj;
      hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d;
    h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
  }
  char out[65];
  for (int i = 0; i < 8; ++i)
    std::snprintf(out + 8 * i, 9, "%08x", h[i]);
  return std::string(out, 64);
}

bool readFile(const std::string &path, std::string &out) {
  std::ifstream in(path, std::ios::binary);
  if (!in)
    return false;
  std::ostringstream buffer;
  buffer << in.rdbuf();
  out = buffer.str();
  return true;
}

std::string facts(const md::ScanFacts &f) {
  std::ostringstream s;
  s << "parse=" << f.parseResult << " blocks=" << f.blocks
    << " images=" << f.images << " remote=" << f.remoteImages
    << " htmlBlocks=" << f.htmlBlocks << " htmlText=" << f.htmlText
    << " textOutsideImages=" << f.textOutsideImages;
  return s.str();
}

const md::Verdict kAllVerdicts[] = {
    md::Verdict::Nul,      md::Verdict::InvalidUtf8, md::Verdict::TooLarge,
    md::Verdict::ParseFail, md::Verdict::NoBlock,    md::Verdict::RemoteImage,
    md::Verdict::Html,     md::Verdict::Pass};

// ---- A, B: the fixture --------------------------------------------------------

void checkFixture(const std::string &fixturePath, const std::string &corpusDir) {
  std::string text;
  if (!readFile(fixturePath, text)) {
    check(false, "cannot read the fixture " + fixturePath);
    return;
  }
  Json root;
  JsonReader reader(text);
  const bool parsed = reader.value(root);
  reader.space();
  if (!parsed || reader.pos != text.size() || root.type != Json::Object) {
    check(false, "the fixture is not one JSON object");
    return;
  }

  // The fixture's order is the header's label set, in the header's order.
  const Json *rules = root.get("rules");
  const Json *order = rules ? rules->get("order") : nullptr;
  std::vector<std::string> labels;
  for (const md::Verdict v : kAllVerdicts)
    labels.push_back(md::verdictLabel(v));
  std::vector<std::string> fixtureOrder;
  if (order && order->type == Json::Array)
    for (const Json &v : order->array)
      fixtureOrder.push_back(v.string);
  check(fixtureOrder == labels,
        "the fixture's rules.order is not the header's verdict order");

  const Json *items = root.get("items");
  if (!items || items->type != Json::Array || items->array.empty()) {
    check(false, "the fixture has no items");
    return;
  }

  // Tool-closed: every corpus file has an item and every item a file.
  std::set<std::string> files;
  std::error_code ec;
  for (auto it = std::filesystem::recursive_directory_iterator(corpusDir, ec);
       !ec && it != std::filesystem::recursive_directory_iterator(); ++it)
    if (it->is_regular_file())
      files.insert(std::filesystem::relative(it->path(), corpusDir).generic_string());
  check(!ec, "cannot list the corpus " + corpusDir);
  std::set<std::string> paths;
  std::map<std::string, int> perVerdict;
  for (const Json &item : items->array) {
    const Json *path = item.get("path");
    const Json *verdict = item.get("verdict");
    const Json *bytes = item.get("bytes");
    const Json *sha = item.get("sha256");
    if (!path || path->type != Json::String || !verdict ||
        verdict->type != Json::String || !bytes || !sha) {
      check(false, "an item lacks path, verdict, bytes or sha256");
      continue;
    }
    check(paths.insert(path->string).second, "duplicate item " + path->string);
    check(files.count(path->string) == 1,
          "item without a corpus file: " + path->string);
    ++perVerdict[verdict->string];

    std::string data;
    if (!readFile(corpusDir + "/" + path->string, data)) {
      check(false, "cannot read " + path->string);
      continue;
    }
    check(static_cast<double>(data.size()) == bytes->number,
          path->string + ": size differs from the fixture");
    check(sha256Hex(data) == sha->string,
          path->string + ": sha256 differs from the fixture");

    const Json *inject = item.get("inject");
    md::ScanFacts f;
    md::Verdict got;
    if (inject) {
      check(inject->string == "allocation-failure",
            path->string + ": unknown injection " + inject->string);
      gRefusedAllocations = 0;
      gFailAllocations = true;
      got = md::judgeBytes(data.data(), data.size(), &f);
      gFailAllocations = false;
      // Positive control: the injection reached md4c.
      check(gRefusedAllocations > 0,
            path->string + ": the allocation injection refused nothing");
      const Json *without = item.get("verdictWithoutInjection");
      md::ScanFacts g;
      const md::Verdict plain = md::judgeBytes(data.data(), data.size(), &g);
      check(without && without->string == md::verdictLabel(plain),
            path->string + ": without the injection got " +
                md::verdictLabel(plain) + " (" + facts(g) + ")");
    } else {
      got = md::judgeBytes(data.data(), data.size(), &f);
    }
    check(verdict->string == md::verdictLabel(got),
          path->string + ": expected " + verdict->string + ", got " +
              md::verdictLabel(got) + " (" + facts(f) + ")");
  }
  for (const std::string &file : files)
    check(paths.count(file) == 1, "corpus file without an item: " + file);
  // Non-vacuity: every label the header knows is exercised by the fixture.
  for (const std::string &label : labels)
    check(perVerdict[label] > 0, "no fixture item has verdict " + label);
  std::printf("fixture: %zu items, %zu corpus files\n", paths.size(),
              files.size());
}

// ---- C: RFC 3629 against an independent oracle --------------------------------
//
// The oracle decodes by bit pattern (the generic UTF-8 scheme of RFC 3629
// section 3) and then applies the three exclusions of section 3 and 4 as
// statements about the decoded value: shortest form, not a surrogate, at most
// U+10FFFF.  The header instead tabulates the permitted byte ranges; the two
// are different formulations of one definition.
bool oracleValid(const unsigned char *p, std::size_t n) {
  std::size_t i = 0;
  while (i < n) {
    const unsigned char b = p[i];
    std::size_t len;
    std::uint32_t cp;
    if ((b & 0x80) == 0) { len = 1; cp = b; }
    else if ((b & 0xe0) == 0xc0) { len = 2; cp = b & 0x1f; }
    else if ((b & 0xf0) == 0xe0) { len = 3; cp = b & 0x0f; }
    else if ((b & 0xf8) == 0xf0) { len = 4; cp = b & 0x07; }
    else return false;
    if (i + len > n)
      return false;
    for (std::size_t k = 1; k < len; ++k) {
      if ((p[i + k] & 0xc0) != 0x80)
        return false;
      cp = (cp << 6) | (p[i + k] & 0x3f);
    }
    static const std::uint32_t minimum[5] = {0, 0, 0x80, 0x800, 0x10000};
    if (cp < minimum[len] || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff))
      return false;
    i += len;
  }
  return true;
}

void checkUtf8() {
  unsigned char buf[4];
  std::size_t disagreements = 0, valid = 0, cases = 0;
  auto compare = [&](std::size_t n) {
    ++cases;
    const bool want = oracleValid(buf, n);
    const bool got = md::isValidUtf8(reinterpret_cast<const char *>(buf), n);
    valid += want;
    if (want != got && ++disagreements <= 10) {
      char hex[16] = {0};
      for (std::size_t k = 0; k < n; ++k)
        std::snprintf(hex + 3 * k, 4, "%02X ", buf[k]);
      check(false, std::string("isValidUtf8 disagrees with the oracle on ") + hex);
    }
  };
  check(md::isValidUtf8("", 0), "the empty input is valid UTF-8");
  for (unsigned a = 0; a < 256; ++a) {
    buf[0] = static_cast<unsigned char>(a);
    compare(1);
    for (unsigned b = 0; b < 256; ++b) {
      buf[1] = static_cast<unsigned char>(b);
      compare(2);
      for (unsigned c = 0; c < 256; ++c) {
        buf[2] = static_cast<unsigned char>(c);
        compare(3);
      }
    }
  }
  static const unsigned char tails[] = {0x00, 0x41, 0x7f, 0x80, 0x8f, 0x90,
                                        0x9f, 0xa0, 0xbf, 0xc0, 0xc2, 0xe0,
                                        0xed, 0xf0, 0xf4, 0xf5, 0xff};
  for (unsigned a = 0; a < 256; ++a)
    for (unsigned b = 0; b < 256; ++b)
      for (unsigned char c : tails)
        for (unsigned char d : tails) {
          buf[0] = static_cast<unsigned char>(a);
          buf[1] = static_cast<unsigned char>(b);
          buf[2] = c;
          buf[3] = d;
          compare(4);
        }
  check(disagreements == 0, "isValidUtf8 disagreements: " +
                                std::to_string(disagreements));
  // Non-vacuity: both answers occur in quantity.
  check(valid > 1000 && valid < cases - 1000,
        "the UTF-8 comparison is lopsided: " + std::to_string(valid) +
            " valid of " + std::to_string(cases));
  std::printf("utf-8: %zu buffers compared, %zu valid, %zu disagreements\n",
              cases, valid, disagreements);

  // The named boundaries, so a failure reads as a sentence.
  struct Named { const char *bytes; std::size_t n; bool valid; const char *what; };
  const Named named[] = {
      {"\x7f", 1, true, "U+007F"},
      {"\xc2\x80", 2, true, "U+0080"},
      {"\xdf\xbf", 2, true, "U+07FF"},
      {"\xe0\xa0\x80", 3, true, "U+0800"},
      {"\xed\x9f\xbf", 3, true, "U+D7FF"},
      {"\xee\x80\x80", 3, true, "U+E000"},
      {"\xef\xbf\xbf", 3, true, "U+FFFF"},
      {"\xf0\x90\x80\x80", 4, true, "U+10000"},
      {"\xf4\x8f\xbf\xbf", 4, true, "U+10FFFF"},
      {"\xc0\xaf", 2, false, "overlong '/' (fixture X15)"},
      {"\xc1\xbf", 2, false, "overlong U+007F"},
      {"\xe0\x9f\xbf", 3, false, "overlong U+07FF"},
      {"\xf0\x8f\xbf\xbf", 4, false, "overlong U+FFFF"},
      {"\xed\xa0\x80", 3, false, "U+D800 (fixture X16)"},
      {"\xed\xbf\xbf", 3, false, "U+DFFF"},
      {"\xf4\x90\x80\x80", 4, false, "U+110000 (fixture X17)"},
      {"\xf5\x80\x80\x80", 4, false, "lead F5"},
      {"\xff", 1, false, "0xFF (fixture X07)"},
      {"\x80", 1, false, "a lone continuation byte"},
      {"\xe4\xb8", 2, false, "a 3-byte sequence cut at the end (fixture X06)"},
      {"\xe9 ", 2, false, "a 3-byte lead followed by a space (fixture X05)"},
      {"\xf0\x9f\x98", 3, false, "a 4-byte sequence cut at the end"},
  };
  for (const Named &n : named)
    check(md::isValidUtf8(n.bytes, n.n) == n.valid,
          std::string("isValidUtf8 on ") + n.what);
}

// ---- D: size and order --------------------------------------------------------

void checkSizeAndOrder() {
  md::ScanFacts f;
  const std::string ascii(md::kMaxBytes, 'a');
  check(md::judgeBytes(ascii.data(), ascii.size(), &f) == md::Verdict::Pass,
        "65,536 ASCII bytes are not refused (" + facts(f) + ")");
  const std::string asciiOver = ascii + "a";
  check(md::judgeBytes(asciiOver.data(), asciiOver.size()) ==
            md::Verdict::TooLarge,
        "65,537 ASCII bytes are TOO_LARGE");
  // M3's shape: repeated CJK (3 bytes each) and an ASCII tail.
  std::string cjk;
  while (cjk.size() + 3 <= md::kMaxBytes - 1)
    cjk += "\xe4\xb8\xad";
  cjk += std::string(md::kMaxBytes - cjk.size(), 'z');
  check(cjk.size() == md::kMaxBytes, "the CJK corpus is 65,536 bytes");
  check(md::judgeBytes(cjk.data(), cjk.size(), &f) == md::Verdict::Pass,
        "65,536 bytes of CJK are not refused (" + facts(f) + ")");
  const std::string cjkOver = cjk + "z";
  check(md::judgeBytes(cjkOver.data(), cjkOver.size()) == md::Verdict::TooLarge,
        "65,537 bytes of CJK are TOO_LARGE");
  // The order of the byte rules, where two hold at once.
  const std::string nulAndInvalid("a\0\xff", 3);
  check(md::judgeBytes(nulAndInvalid.data(), nulAndInvalid.size()) ==
            md::Verdict::Nul,
        "NUL comes before INVALID_UTF8");
  const std::string invalidAndLarge = ascii + "\xff";
  check(md::judgeBytes(invalidAndLarge.data(), invalidAndLarge.size()) ==
            md::Verdict::InvalidUtf8,
        "INVALID_UTF8 comes before TOO_LARGE");
  const std::string nulAndLarge = ascii + std::string(1, '\0');
  check(md::judgeBytes(nulAndLarge.data(), nulAndLarge.size()) ==
            md::Verdict::Nul,
        "NUL comes before TOO_LARGE");
  check(md::judgeBytes("", 0, &f) == md::Verdict::NoBlock,
        "the empty input has no block (" + facts(f) + ")");
}

// ---- E: 10.2 -------------------------------------------------------------------

void checkCollapsed() {
  struct Case { bool none, missing, observed; std::size_t rects; bool want; const char *what; };
  const Case cases[] = {
      {true, false, false, 0, true, "just opened: nothing observed, readback NONE"},
      {true, false, true, 0, true, "a caret: observed, no rectangles, NONE"},
      {true, false, true, 1, false, "one image selected: NONE, one rectangle"},
      {true, false, true, 3, false, "NONE with rectangles"},
      {false, false, true, 1, false, "a text selection"},
      {false, false, false, 0, false, "a text readback before any callback"},
      {false, true, true, 1, false, "text type with its text missing"},
      {true, true, false, 0, false, "textMissing is never a caret"},
  };
  for (const Case &c : cases)
    check(md::collapsedForPaste(c.none, c.missing, c.observed, c.rects) == c.want,
          std::string("collapsedForPaste: ") + c.what);
}

// ---- E2: the interface's order for codes 1-5, and the reads asked lazily -----

void checkOrder() {
  struct Case {
    md::Verdict verdict;
    bool utf8, collapsed;
    const char *code;   // nullptr: nothing refuses
    int encodingReads, caretReads;
    const char *what;
  };
  const Case cases[] = {
      {md::Verdict::Nul, false, false, "INVALID_ARGUMENT", 0, 0,
       "bytes refused: no read at all"},
      {md::Verdict::NoBlock, false, false, "INVALID_ARGUMENT", 0, 0,
       "NO_BLOCK is INVALID_ARGUMENT before any read"},
      {md::Verdict::Pass, false, false, "MARKDOWN_ENCODING_UNSUPPORTED", 1, 0,
       "encoding before the caret, and the caret not read"},
      {md::Verdict::RemoteImage, false, true, "MARKDOWN_ENCODING_UNSUPPORTED", 1, 0,
       "encoding before REMOTE"},
      {md::Verdict::RemoteImage, true, false, "MARKDOWN_NEEDS_CARET", 1, 1,
       "the caret before REMOTE"},
      {md::Verdict::Html, true, false, "MARKDOWN_NEEDS_CARET", 1, 1,
       "the caret before HTML"},
      {md::Verdict::RemoteImage, true, true, "MARKDOWN_REMOTE_IMAGE", 1, 1,
       "REMOTE at a caret"},
      {md::Verdict::Html, true, true, "MARKDOWN_HTML_UNSUPPORTED", 1, 1,
       "HTML at a caret"},
      {md::Verdict::Pass, true, true, nullptr, 1, 1, "PASS at a caret dispatches"},
  };
  for (const Case &c : cases) {
    int encodingReads = 0, caretReads = 0;
    const md::Refusal r = md::preDispatchRefusal(
        c.verdict, [&] { ++encodingReads; return c.utf8; },
        [&] { ++caretReads; return c.collapsed; });
    const bool sameCode = (c.code == nullptr && r.code == nullptr) ||
                          (c.code && r.code && std::strcmp(c.code, r.code) == 0);
    check(sameCode && encodingReads == c.encodingReads &&
              caretReads == c.caretReads && (r.code == nullptr || r.message),
          std::string("preDispatchRefusal: ") + c.what + " (got " +
              (r.code ? r.code : "nothing") + ", reads " +
              std::to_string(encodingReads) + "/" + std::to_string(caretReads) +
              ")");
  }
}

// ---- F: 9.4 --------------------------------------------------------------------

void checkJudge() {
  // The shape SfxUndoManager::GetUndoActionsInfo writes (svl undo.cxx).
  const std::string empty = "{\"actions\": \"\"}";
  const std::string one =
      "{\"actions\": [{\"index\": \"0\", \"comment\": \"Paste clipboard\", "
      "\"viewId\": \"0\", \"dateTime\": \"2026-10-16T10:00:00\"}]}";
  const std::string two =
      "{\"actions\": [{\"index\": \"0\", \"comment\": \"Paste clipboard\", "
      "\"viewId\": \"0\", \"dateTime\": \"2026-10-16T10:00:01\"}, "
      "{\"index\": \"1\", \"comment\": \"Typing: x\", \"viewId\": \"0\", "
      "\"dateTime\": \"2026-10-16T10:00:00\"}]}";
  md::PasteJudgement j = md::judgeAfterPaste(empty, true, one);
  check(j.completed && j.after.actions == 1 && j.after.topComment == "Paste clipboard",
        "empty -> one action completes");
  j = md::judgeAfterPaste(one, true, two);
  check(j.completed && j.after.actions == 2, "one -> two actions completes");
  j = md::judgeAfterPaste(one, false, two);
  check(!j.completed && j.reason &&
            std::strcmp(j.reason, "undo-read-after-paste-failed") == 0,
        "a failed read after the paste is unknown");
  j = md::judgeAfterPaste(one, true, one);
  check(!j.completed && j.reason &&
            std::strcmp(j.reason, "undo-payload-unchanged") == 0,
        "an unchanged payload is unknown (round 2 T2: protected section)");
  j = md::judgeAfterPaste(one, true, empty);
  check(!j.completed && j.reason &&
            std::strcmp(j.reason, "undo-payload-without-action") == 0,
        "a payload that changed to zero actions is unknown");
  j = md::judgeAfterPaste(empty, true, "{\"something\": 1}");
  check(!j.completed && j.reason &&
            std::strcmp(j.reason, "undo-payload-without-action") == 0,
        "an unparseable payload is unknown");
}

// ---- G: the code table ---------------------------------------------------------

void checkCodes() {
  const std::vector<std::string> interfaceOrder = {
      "INVALID_ARGUMENT",          "MARKDOWN_ENCODING_UNSUPPORTED",
      "MARKDOWN_NEEDS_CARET",      "MARKDOWN_REMOTE_IMAGE",
      "MARKDOWN_HTML_UNSUPPORTED", "MARKDOWN_UNDO_UNREADABLE"};
  std::vector<std::string> list;
  for (const char *code : md::kPreDispatchCodes)
    list.push_back(code);
  check(list == interfaceOrder,
        "kPreDispatchCodes is not the interface's six refusals in order");
  check(std::set<std::string>(list.begin(), list.end()).size() == list.size(),
        "kPreDispatchCodes has a duplicate");
  for (const md::Verdict v : kAllVerdicts) {
    const char *code = md::verdictCode(v);
    if (v == md::Verdict::Pass) {
      check(code == nullptr, "PASS has a code");
      continue;
    }
    check(code && std::set<std::string>(list.begin(), list.end()).count(code),
          std::string("verdict ") + md::verdictLabel(v) +
              " has no pre-dispatch code");
    check(md::verdictMessage(v)[0] != '\0',
          std::string("verdict ") + md::verdictLabel(v) + " has no message");
  }
  check(std::set<std::string>(list.begin(), list.end())
                .count(md::kCodeOutcomeUnknown) == 0,
        "the post-dispatch code is listed as pre-dispatch");
}

} // namespace

int main(int argc, char **argv) {
  const std::string fixture =
      argc > 1 ? argv[1] : "tests/markdown_paste_expected.json";
  const std::string corpus = argc > 2 ? argv[2] : "tests/markdown_paste_corpus";
  checkFixture(fixture, corpus);
  checkUtf8();
  checkSizeAndOrder();
  checkCollapsed();
  checkOrder();
  checkJudge();
  checkCodes();
  if (gFailures) {
    std::printf("FAILED %d of %d checks\n", gFailures, gChecks);
    return 1;
  }
  std::printf("ok %d checks\n", gChecks);
  return 0;
}
