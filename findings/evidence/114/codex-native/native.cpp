#define main original_merge_probe_main
#include "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/merge_native_boundaries.cpp"
#undef main

int main(int argc, char **argv) {
  if (argc != 4) return 2;
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 3;
  LibreOfficeKitDocument *doc = openDocument(kit, argv[3]);
  if (!doc) return 4;
  const std::vector<Case> cases = {
    {"SIYUAN-12-1", "第一組中文字", true, false, "", 1},
    {"SIYUAN-12-2", "第一組中文字", true, false, "", 2},
    {"NOTO-12-1", "第二組中文字", true, false, "", 1},
    {"NOTO-12-2", "第二組中文字", true, false, "", 2},
    {"SIYUAN-18-1", "第三組中文字", true, false, "", 1},
    {"SIYUAN-18-2", "第三組中文字", true, false, "", 2},
    {"LATIN-12-1", "Latin control", true, false, "", 1},
    {"LATIN-12-2", "Latin control", true, false, "", 2},
  };
  bool ok = true;
  for (const auto &c : cases) {
    std::string selected;
    const auto rb = position(doc, c, selected);
    const bool found = selected == c.anchor;
    ok = ok && found && !rb.cursor.empty();
    std::cout << "{\"case\":\"" << c.id << "\",\"searchMatched\":"
              << (found ? "true" : "false") << ",\"caret\":\""
              << jsonEscape(rb.cursor) << "\"}" << std::endl;
  }
  doc->pClass->destroy(doc);
  kit->pClass->destroy(kit);
  return ok ? 0 : 5;
}
