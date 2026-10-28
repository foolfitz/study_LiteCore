// Finding 168, native step: what does each text-input route do to the S5 table selection?
//
// The product types `x` with LOK paste(text/plain;charset=utf-8); the bound native S5 type
// oracle (run-03) types it with KEYINPUT.  Over the table selection that Shift+Right makes
// from A1's text end, the product saves A1 `A1 cell textx` / B1 `B1 cell textx#` and the
// oracle saves A1 `` / B1 `x`.  This harness puts the routes side by side on native, on the
// same fixture and the same selection, so that two questions can be answered separately:
//   1. is the append-instead-of-replace difference simply LOK paste's table-mode semantics
//      (native paste does it too), or something only the WASM build does;
//   2. is the later cell's `#` produced by native paste as well, and does it depend on the
//      inserted bytes (length, non-ASCII) and on the process locale (the runner's --lc-all).
// It also records two candidate repair routes (.uno:InsertText and the ext-text-input
// events) on the same selection, so a proposed product change starts from a native
// measurement rather than from a source reading.  It decides nothing.
//
// Reuses the archived signature setup (discovery, shapes, settle) unchanged.  Each arm is a
// fresh document: open, settle, make the shape, save "before", post the arm's Shift keys
// (each settled 800 ms quiet / 8000 ms cap, as run-03), read the selection, run the action,
// settle, save "after".  Arms are interleaved round by round.
#define main f168_retained_signature_main
#include "link_native_extend_signatures.cpp"
#undef main
#include <filesystem>

namespace {
struct Arm {
  const char *id;
  const char *shape;              // makeShape() name
  std::vector<int> shiftKeys;     // posted after the shape, each settled
  const char *route;              // key | paste | uno-insert-text | ext-text-input | none
  const char *text;               // UTF-8 bytes the route inserts
};
const std::vector<Arm> &arms() {
  static const std::vector<Arm> all = {
      // The S5 cell's selection, every route.
      {"table2/key-x", "cell-end", {kRight | kShift}, "key", "x"},
      {"table2/paste-x", "cell-end", {kRight | kShift}, "paste", "x"},
      {"table2/paste-xy", "cell-end", {kRight | kShift}, "paste", "xy"},
      {"table2/paste-hello-world", "cell-end", {kRight | kShift}, "paste", "hello world"},
      {"table2/paste-e-acute", "cell-end", {kRight | kShift}, "paste", "\xC3\xA9"},
      {"table2/paste-cjk", "cell-end", {kRight | kShift}, "paste", "\xE4\xB8\xAD"},
      {"table2/uno-insert-text-x", "cell-end", {kRight | kShift}, "uno-insert-text", "x"},
      {"table2/ext-text-input-x", "cell-end", {kRight | kShift}, "ext-text-input", "x"},
      // Four selected cells: does every PaM after the first get the suffix?
      {"table4/key-x", "cell-end", {kRight | kShift, kDown | kShift}, "key", "x"},
      {"table4/paste-x", "cell-end", {kRight | kShift, kDown | kShift}, "paste", "x"},
      // Controls: a caret in the cell (one PaM, no table mode) and a plain-text selection.
      {"cell-caret/paste-x", "cell-end", {}, "paste", "x"},
      {"cell-caret/key-x", "cell-end", {}, "key", "x"},
      {"text/paste-x", "caret-mid", {kRight | kShift}, "paste", "x"},
      {"text/key-x", "caret-mid", {kRight | kShift}, "key", "x"},
      // The window without any input: what the selection alone saves as.
      {"table2/none", "cell-end", {kRight | kShift}, "none", ""},
  };
  return all;
}

std::string intsJson(const std::vector<int> &v) {
  std::string out = "[";
  for (std::size_t i = 0; i < v.size(); ++i)
    out += (i ? "," : "") + std::to_string(v[i]);
  return out + "]";
}

// Returns a short description of what the route did ("returned": paste's bool).
std::string runRoute(Doc &s, const Arm &arm) {
  const std::string route = arm.route;
  const std::string text = arm.text;
  if (route == "key") {
    for (unsigned char c : text) {  // the arms only key ASCII
      s.d->pClass->postKeyEvent(s.d, LOK_KEYEVENT_KEYINPUT, c, 0);
      s.d->pClass->postKeyEvent(s.d, LOK_KEYEVENT_KEYUP, c, 0);
    }
    return "{\"posted\":" + std::to_string(text.size() * 2) + "}";
  }
  if (route == "paste") {
    const bool ok = s.d->pClass->paste(s.d, "text/plain;charset=utf-8", text.data(), text.size());
    return std::string("{\"returned\":") + (ok ? "true" : "false") + "}";
  }
  if (route == "uno-insert-text") {
    const std::string args = "{\"Text\":{\"type\":\"string\",\"value\":" + q(text) + "}}";
    s.d->pClass->postUnoCommand(s.d, ".uno:InsertText", args.c_str(), false);
    return "{\"arguments\":" + q(args) + "}";
  }
  if (route == "ext-text-input") {
    s.d->pClass->postWindowExtTextInputEvent(s.d, 0, LOK_EXT_TEXTINPUT, text.c_str());
    s.d->pClass->postWindowExtTextInputEvent(s.d, 0, LOK_EXT_TEXTINPUT_END, text.c_str());
    return "{\"posted\":2}";
  }
  return "{}";
}

std::string stemOf(const Arm &arm, int round) {
  std::string stem = arm.id;
  std::replace(stem.begin(), stem.end(), '/', '_');
  return stem + "-r" + std::to_string(round);
}

bool measured(LibreOfficeKit *kit, const std::string &url, const std::filesystem::path &out, const Arm &arm,
              int round) {
  const auto stem = stemOf(arm, round);
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
  const bool saveAfter = s.d->pClass->saveAs(s.d, ("file://" + afterFile.string()).c_str(), "odt", nullptr) != 0;
  std::cout << "{\"id\":" << q(arm.id) << ",\"round\":" << round << ",\"shape\":" << q(arm.shape)
            << ",\"shiftKeys\":" << intsJson(arm.shiftKeys) << ",\"route\":" << q(arm.route)
            << ",\"text\":" << q(arm.text) << ",\"textBytes\":" << std::string(arm.text).size()
            << ",\"openedSettleMs\":" << opened << ",\"setupSettleMs\":" << made.settleMs
            << ",\"shiftSettleMs\":[";
  for (std::size_t i = 0; i < shiftSettles.size(); ++i)
    std::cout << (i ? "," : "") << shiftSettles[i];
  std::cout << "],\"finalSettleMs\":" << settled << ",\"routeResult\":" << routeResult
            << ",\"routeReturnMs\":" << routeReturned << ",\"betweenSelectionType\":" << betweenType
            << ",\"before\":" << snapJson(before) << ",\"between\":" << snapJson(between)
            << ",\"after\":" << snapJson(after) << ",\"savedBefore\":" << (saveBefore ? "true" : "false")
            << ",\"savedAfter\":" << (saveAfter ? "true" : "false") << ",\"beforeFile\":"
            << q(beforeFile.filename().string()) << ",\"afterFile\":" << q(afterFile.filename().string())
            << ",\"callbacks\":" << callbacksJson(s, start, -500) << "}" << std::endl;
  closeDoc(s);
  bool settledAll = opened >= 0 && made.settleMs >= 0 && settled >= 0;
  for (double v : shiftSettles)
    settledAll = settledAll && v >= 0;
  return saveBefore && saveAfter && settledAll;
}
}  // namespace

int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--paragraphs")
    return f168_retained_signature_main(argc, argv);
  if (argc == 2 && std::string(argv[1]) == "--inventory") {
    for (const Arm &arm : arms())
      std::cout << "{\"id\":" << q(arm.id) << ",\"shape\":" << q(arm.shape)
                << ",\"shiftKeys\":" << intsJson(arm.shiftKeys) << ",\"route\":" << q(arm.route)
                << ",\"text\":" << q(arm.text) << "}\n";
    return 0;
  }
  if (argc != 6) {
    std::cerr << "usage: f168-native-table-type-routes INSTALL PROFILE_URL FIXTURE_URL FRESH_SAVE_DIRECTORY ROUNDS\n"
                 "       f168-native-table-type-routes --inventory | --paragraphs\n";
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
