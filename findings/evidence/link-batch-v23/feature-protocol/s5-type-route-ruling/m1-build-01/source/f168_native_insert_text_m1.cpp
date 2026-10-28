// Type-route ruling M1 (finding 168): .uno:InsertText against the keyboard, natively.
//
// The ruling chooses .uno:InsertText for typed text and asks, before any engine change, for
// a native measurement on the shapes and texts the successor will meet: does the command
// deliver LOK_CALLBACK_UNO_COMMAND_RESULT (it is posted with bNotifyWhenFinished=true, as the
// engine's ordered-UNO proof requires), and does every save equal the keyboard's for the same
// text and shape?  Texts: x, xy, U+4E2D, U+00E9 (key and InsertText), U+1F600 (InsertText
// only; the keyboard route has no single event for it), and " teh " at the document end, the
// one input expected to differ (the keyboard autocorrects at word boundaries; InsertText runs
// no autocorrect) -- recorded as a named limit, not a gate.  Native LOK here is not unipoll,
// so nothing in this run says anything about ordering in the product.
//
// Reuses the archived signature setup unchanged; arm procedure as f168_native_table_type_routes.cpp.
#define main f168_m1_retained_signature_main
#include "link_native_extend_signatures.cpp"
#undef main
#include <filesystem>

namespace {
struct Shape {
  const char *name;
  const char *shape;
  std::vector<int> shiftKeys;
};
const std::vector<Shape> kM1Shapes = {
    {"table2", "cell-end", {kRight | kShift}},
    {"table4", "cell-end", {kRight | kShift, kDown | kShift}},
    {"cell-caret", "cell-end", {}},
    {"text", "caret-mid", {kRight | kShift}},
};
struct Text {
  const char *name;
  const char *utf8;
  bool keyRoute;
};
const std::vector<Text> kM1Texts = {
    {"x", "x", true},
    {"xy", "xy", true},
    {"cjk", "\xE4\xB8\xAD", true},
    {"e-acute", "\xC3\xA9", true},
    {"emoji", "\xF0\x9F\x98\x80", false},
};
struct Arm {
  std::string id, shape;
  std::vector<int> shiftKeys;
  std::string route, text;
};
const std::vector<Arm> &arms() {
  static std::vector<Arm> all;
  if (all.empty()) {
    for (const Shape &s : kM1Shapes)
      for (const Text &t : kM1Texts) {
        if (t.keyRoute)
          all.push_back({std::string(s.name) + "/key-" + t.name, s.shape, s.shiftKeys, "key", t.utf8});
        all.push_back({std::string(s.name) + "/uno-insert-text-" + t.name, s.shape, s.shiftKeys, "uno-insert-text", t.utf8});
      }
    all.push_back({"doc-end/key-teh", "doc-end", {}, "key", " teh "});
    all.push_back({"doc-end/uno-insert-text-teh", "doc-end", {}, "uno-insert-text", " teh "});
  }
  return all;
}

std::string intsJson(const std::vector<int> &v) {
  std::string out = "[";
  for (std::size_t i = 0; i < v.size(); ++i)
    out += (i ? "," : "") + std::to_string(v[i]);
  return out + "]";
}

// UTF-8 to UTF-16 code units; the key route posts one KEYINPUT/KEYUP per unit.
std::vector<int> utf16Units(const std::string &s) {
  std::vector<int> out;
  for (std::size_t i = 0; i < s.size();) {
    const unsigned char c = s[i];
    unsigned cp;
    int n;
    if (c < 0x80) { cp = c; n = 1; }
    else if ((c >> 5) == 6) { cp = c & 0x1F; n = 2; }
    else if ((c >> 4) == 14) { cp = c & 0x0F; n = 3; }
    else { cp = c & 0x07; n = 4; }
    for (int k = 1; k < n; ++k)
      cp = (cp << 6) | (static_cast<unsigned char>(s[i + k]) & 0x3F);
    i += n;
    if (cp >= 0x10000) {
      cp -= 0x10000;
      out.push_back(0xD800 + (cp >> 10));
      out.push_back(0xDC00 + (cp & 0x3FF));
    } else {
      out.push_back(static_cast<int>(cp));
    }
  }
  return out;
}

std::string runRoute(Doc &s, const Arm &arm) {
  if (arm.route == "key") {
    const auto units = utf16Units(arm.text);
    for (int u : units) {
      s.d->pClass->postKeyEvent(s.d, LOK_KEYEVENT_KEYINPUT, u, 0);
      s.d->pClass->postKeyEvent(s.d, LOK_KEYEVENT_KEYUP, u, 0);
    }
    return "{\"posted\":" + std::to_string(units.size() * 2) + "}";
  }
  const std::string args = "{\"Text\":{\"type\":\"string\",\"value\":" + q(arm.text) + "}}";
  s.d->pClass->postUnoCommand(s.d, ".uno:InsertText", args.c_str(), true);
  return "{\"arguments\":" + q(args) + ",\"notifyWhenFinished\":true}";
}

// Every UNO_COMMAND_RESULT payload since t0 (ms), in arrival order.
std::string unoResultsJson(Doc &s, double t0) {
  std::lock_guard<std::mutex> lock(s.ctx->m);
  std::string out = "[";
  bool first = true;
  for (const Cb &c : s.ctx->list)
    if (c.type == LOK_CALLBACK_UNO_COMMAND_RESULT && c.t >= t0) {
      out += (first ? "" : ",") + std::string("{\"tMs\":") + std::to_string(c.t - t0) + ",\"payload\":" + q(c.payload) + "}";
      first = false;
    }
  return out + "]";
}

bool measured(LibreOfficeKit *kit, const std::string &url, const std::filesystem::path &out, const Arm &arm,
              int round) {
  std::string stem = arm.id;
  std::replace(stem.begin(), stem.end(), '/', '_');
  stem += "-r" + std::to_string(round);
  const auto beforeFile = out / (stem + "-before.odt"), afterFile = out / (stem + "-after.odt");
  if (std::filesystem::exists(beforeFile) || std::filesystem::exists(afterFile))
    return false;
  Doc s = openDoc(kit, url);
  if (!s.d) {
    std::cout << "{\"id\":" << q(arm.id) << ",\"round\":" << round << ",\"fatal\":\"documentLoad\"}" << std::endl;
    return false;
  }
  const auto opened = settle(s, 800, 8000);
  const auto made = makeShape(s, arm.shape, 800);
  const auto before = snap(s);
  const bool saveBefore =
      s.d->pClass->saveAs(s.d, ("file://" + beforeFile.string()).c_str(), "odt", nullptr) != 0;
  std::vector<double> shiftSettles;
  for (int code : arm.shiftKeys) {
    keyPost(s, code);
    shiftSettles.push_back(settle(s, 800, 8000));
  }
  const auto between = snap(s);
  const int betweenType = s.d->pClass->getSelectionType(s.d);
  const auto start = nowMs();
  const auto routeResult = runRoute(s, arm);
  const auto routeReturned = nowMs() - start;
  const auto settled = settle(s, 800, 8000);
  const auto after = snap(s);
  const auto unoResults = unoResultsJson(s, start);
  const bool saveAfter = s.d->pClass->saveAs(s.d, ("file://" + afterFile.string()).c_str(), "odt", nullptr) != 0;
  std::cout << "{\"id\":" << q(arm.id) << ",\"round\":" << round << ",\"shape\":" << q(arm.shape)
            << ",\"shiftKeys\":" << intsJson(arm.shiftKeys) << ",\"route\":" << q(arm.route)
            << ",\"text\":" << q(arm.text) << ",\"openedSettleMs\":" << opened
            << ",\"setupSettleMs\":" << made.settleMs << ",\"shiftSettleMs\":[";
  for (std::size_t i = 0; i < shiftSettles.size(); ++i)
    std::cout << (i ? "," : "") << shiftSettles[i];
  std::cout << "],\"finalSettleMs\":" << settled << ",\"routeResult\":" << routeResult
            << ",\"routeReturnMs\":" << routeReturned << ",\"unoCommandResults\":" << unoResults
            << ",\"betweenSelectionType\":" << betweenType << ",\"before\":" << snapJson(before)
            << ",\"between\":" << snapJson(between) << ",\"after\":" << snapJson(after)
            << ",\"savedBefore\":" << (saveBefore ? "true" : "false")
            << ",\"savedAfter\":" << (saveAfter ? "true" : "false") << ",\"beforeFile\":"
            << q(beforeFile.filename().string()) << ",\"afterFile\":" << q(afterFile.filename().string()) << "}"
            << std::endl;
  closeDoc(s);
  bool settledAll = opened >= 0 && made.settleMs >= 0 && settled >= 0;
  for (double v : shiftSettles)
    settledAll = settledAll && v >= 0;
  return saveBefore && saveAfter && settledAll;
}
}  // namespace

int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--paragraphs")
    return f168_m1_retained_signature_main(argc, argv);
  if (argc == 2 && std::string(argv[1]) == "--inventory") {
    for (const Arm &arm : arms())
      std::cout << "{\"id\":" << q(arm.id) << ",\"shape\":" << q(arm.shape) << ",\"shiftKeys\":"
                << intsJson(arm.shiftKeys) << ",\"route\":" << q(arm.route) << ",\"text\":" << q(arm.text) << "}\n";
    return 0;
  }
  if (argc != 6) {
    std::cerr << "usage: f168-native-insert-text-m1 INSTALL PROFILE_URL FIXTURE_URL FRESH_SAVE_DIRECTORY ROUNDS\n"
                 "       f168-native-insert-text-m1 --inventory | --paragraphs\n";
    return 2;
  }
  const std::filesystem::path out = std::filesystem::absolute(argv[4]);
  if (!std::filesystem::is_directory(out) || !std::filesystem::is_empty(out))
    return 2;
  const int rounds = std::atoi(argv[5]);
  if (rounds < 1 || rounds > 10)
    return 2;
  std::cout.precision(15);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit)
    return 3;
  if (!discoverAll(kit, argv[3], 1, 800))
    return 4;
  bool ok = true;
  for (int round = 1; round <= rounds; ++round)
    for (const Arm &arm : arms())
      if (!measured(kit, argv[3], out, arm, round))
        ok = false;
  return ok ? 0 : 5;
}
