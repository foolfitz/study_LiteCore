// SPEC-P-demo-batch-4 N3: what the paragraph actions leave behind on a read that uses no coordinates.  Each arm is a fresh document.
// Routes on one caret: truth (dispatch only), post (dispatch, then the one-character read), pre+post (the read, dispatch, the read).
// Each arm inserts X afterwards and saves, so the document says where the caret was.  Observations, not verdicts.
//   n3-native-writer-toggle INSTALL_PATH PROFILE_URL FIXTURE_DIR OUTDIR PART
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
namespace {
void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }
void onCallback(int, const char *, void *) {}
std::string escape(const std::string &value) {
  std::string out;
  for (const char c : value) {
    if (c == '"' || c == '\\') { out += '\\'; out += c; }
    else if (c == '\n') out += "\\n"; else if (c == '\r') out += "\\r"; else if (c == '\t') out += "\\t";
    else if (static_cast<unsigned char>(c) < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); out += b; }
    else out += c;
  }
  return out;
}
void uno(LibreOfficeKitDocument *d, const char *command, const char *args = nullptr, bool notify = true, int ms = 200) {
  d->pClass->postUnoCommand(d, command, args, notify);
  drain(ms);
}
std::string html(LibreOfficeKitDocument *d) {
  char *used = nullptr;
  char *raw = d->pClass->getTextSelection(d, "text/html", &used);
  std::string out = raw ? raw : "";
  std::free(raw); std::free(used);
  const auto body = out.find("<body");
  return body == std::string::npos ? out : out.substr(body);
}
struct Read { int type = -1; int typeAfter = -1; std::string how = "none", markup; };
Read caretRead(LibreOfficeKitDocument *d) {
  Read r;
  uno(d, ".uno:CharLeftSel");
  r.type = d->pClass->getSelectionType(d);
  r.how = "left";
  if (r.type == LOK_SELTYPE_TEXT) {
    r.markup = html(d);
    uno(d, ".uno:GoRight");
  } else {
    uno(d, ".uno:CharRightSel");
    r.type = d->pClass->getSelectionType(d);
    r.how = "right";
    if (r.type == LOK_SELTYPE_TEXT) {
      r.markup = html(d);
      uno(d, ".uno:GoLeft");
    } else r.how = "blank";
  }
  r.typeAfter = d->pClass->getSelectionType(d);
  return r;
}
struct Place { const char *name, *needle; std::vector<const char *> steps; };
struct Cmd { const char *name, *command, *args; };
std::string search(const char *needle) {
  return std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"") + needle +
         "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
}
const char *kOn = "{\"On\":{\"type\":\"boolean\",\"value\":true}}";
std::string styleArgs(const char *style) {
  return std::string("{\"Style\":{\"type\":\"string\",\"value\":\"") + style + "\"},\"FamilyName\":{\"type\":\"string\",\"value\":\"ParagraphStyles\"}}";
}
LibreOfficeKitDocument *open(LibreOfficeKit *kit, const std::string &url) {
  auto *d = kit->pClass->documentLoad(kit, url.c_str());
  if (!d) { std::cerr << "load failed " << url << "\n"; std::exit(3); }
  d->pClass->initializeForRendering(d, "{}");
  d->pClass->registerCallback(d, onCallback, nullptr);
  drain(300);
  return d;
}
void close(LibreOfficeKitDocument *d) {
  d->pClass->registerCallback(d, nullptr, nullptr);
  d->pClass->destroy(d);
  drain(120);
}
void place(LibreOfficeKitDocument *d, const Place &where) {
  uno(d, ".uno:GoToStartOfDoc");
  if (where.needle && *where.needle) uno(d, ".uno:ExecuteSearch", search(where.needle).c_str(), false, 420);
  for (const char *step : where.steps) uno(d, step);
  drain(150);
}
void emit(const std::string &part, const char *where, const char *route, const char *cmd, const Read *pre, const Read *post, const std::string &saved,
          const std::string &extra = "") {
  std::cout << "{\"part\":\"" << part << "\",\"place\":\"" << where << "\",\"route\":\"" << route << "\",\"command\":\"" << cmd << "\"";
  if (pre) std::cout << ",\"preHow\":\"" << pre->how << "\",\"preType\":" << pre->type << ",\"preAfter\":" << pre->typeAfter << ",\"preHtml\":\"" << escape(pre->markup) << "\"";
  if (post) std::cout << ",\"postHow\":\"" << post->how << "\",\"postType\":" << post->type << ",\"postAfter\":" << post->typeAfter << ",\"postHtml\":\"" << escape(post->markup) << "\"";
  std::cout << ",\"saved\":\"" << saved << "\"" << extra << "}" << std::endl;
}
std::string saveAs(LibreOfficeKitDocument *d, const std::string &out, int &counter) {
  const std::string saved = "file://" + out + "/n3-" + std::to_string(++counter) + ".odt";
  d->pClass->saveAs(d, saved.c_str(), "odt", nullptr);
  drain(150);
  return saved;
}
void caretArm(LibreOfficeKit *kit, const std::string &url, const std::string &out, const char *part, const Place &where, const char *route, const Cmd &cmd, int &counter) {
  auto *d = open(kit, url);
  place(d, where);
  Read pre, post;
  const bool hasPre = !std::strcmp(route, "pre+post"), hasPost = std::strcmp(route, "truth") != 0;
  if (hasPre) pre = caretRead(d);
  uno(d, cmd.command, cmd.args);
  if (hasPost) post = caretRead(d);
  uno(d, ".uno:InsertText", "{\"Text\":{\"type\":\"string\",\"value\":\"X\"}}");
  const std::string saved = saveAs(d, out, counter);
  emit(part, where.name, route, cmd.name, hasPre ? &pre : nullptr, hasPost ? &post : nullptr, saved);
  close(d);
}
}  // namespace
int main(int argc, char **argv) {
  if (argc < 6) return 64;
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 2;
  const std::string dir = std::string("file://") + argv[3], out = argv[4], part = argv[5];
  int counter = argc > 6 ? std::atoi(argv[6]) : 0;
  const std::string h1 = styleArgs("Heading 1"), h2 = styleArgs("Heading 2"), h3 = styleArgs("Heading 3"), h4 = styleArgs("Heading 4"), body = styleArgs("Text body");
  const std::vector<Cmd> cmds{{"bullet-on", ".uno:DefaultBullet", kOn}, {"number-on", ".uno:DefaultNumbering", kOn}, {"remove", ".uno:RemoveBullets", nullptr},
                              {"h1", ".uno:StyleApply", h1.c_str()}, {"h2", ".uno:StyleApply", h2.c_str()}, {"h3", ".uno:StyleApply", h3.c_str()},
                              {"h4", ".uno:StyleApply", h4.c_str()}, {"body", ".uno:StyleApply", body.c_str()}};
  const std::vector<Place> places{
      {"doc-start", "", {}},
      {"first-para-mid", "ALPHA", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight", ".uno:GoRight"}},
      {"para-start", "BRAVO", {".uno:GoLeft"}},
      {"para-mid", "BRAVO", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}},
      {"para-end", "BRAVO", {".uno:GoToEndOfPara"}},
      {"heading-mid", "CHARLIE", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}},
      {"list-start", "DELTA", {".uno:GoLeft"}},
      {"list-mid", "DELTA", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}},
      {"wrapped-mid", "word060", {".uno:GoLeft"}},
      {"empty-mid", "GOLF", {".uno:GoLeft", ".uno:GoUp"}},
      {"empty-last", "GOLF", {".uno:GoToEndOfDoc"}},
  };
  if (part == "caret") {
    for (const auto &cmd : cmds)
      for (const auto &where : places)
        for (const char *route : {"truth", "post", "pre+post"})
          caretArm(kit, dir + "/caret-fixture.odt", out, "caret", where, route, cmd, counter);
  } else if (part == "table") {
    const std::vector<Place> cells{
        {"cell-first-start", "CELLA", {".uno:GoLeft"}},
        {"cell-first-mid", "CELLA", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}},
        {"cell-first-end", "CELLA", {".uno:GoToEndOfPara"}},
        {"cell-second-start", "CELLB", {".uno:GoLeft"}},
        {"cell-last-end", "CELLD", {".uno:GoToEndOfPara"}},
        {"para-before-end", "BEFORE", {".uno:GoToEndOfPara"}},
        {"para-after-start", "AFTER", {".uno:GoLeft"}},
    };
    for (const auto &where : cells)
      for (const Cmd &cmd : {cmds[0], cmds[4]})
        for (const char *route : {"truth", "post", "pre+post"})
          caretArm(kit, dir + "/table-caret-fixture.odt", out, "table", where, route, cmd, counter);
  } else if (part == "blank") {
    const Place blank{"blank-doc", "", {}};
    for (const auto &cmd : cmds)
      for (const char *route : {"truth", "pre+post"})
        caretArm(kit, dir + "/blank-fixture.odt", out, "blank", blank, route, cmd, counter);
  } else if (part == "undo") {
    const Place where = places[3];
    for (const auto &cmd : cmds) {
      for (const char *route : {"truth", "pre+post"}) {
        auto *d = open(kit, dir + "/caret-fixture.odt");
        place(d, where);
        Read pre, post;
        const bool reads = !std::strcmp(route, "pre+post");
        if (reads) pre = caretRead(d);
        uno(d, cmd.command, cmd.args);
        if (reads) post = caretRead(d);
        const std::string changed = saveAs(d, out, counter);
        uno(d, ".uno:Undo");
        const std::string undone = saveAs(d, out, counter);
        emit("undo", where.name, route, cmd.name, reads ? &pre : nullptr, reads ? &post : nullptr, changed, ",\"undone\":\"" + undone + "\"");
        close(d);
      }
    }
  } else if (part == "range") {
    struct Range { const char *name; const char *needle; std::vector<const char *> steps; };
    const std::vector<Range> ranges{
        {"within-para", "BRAVO", {}},
        {"two-paras", "ALPHA", {".uno:GoLeft", ".uno:LineDownSel"}},
        {"body-into-heading", "BRAVO", {".uno:GoLeft", ".uno:LineDownSel", ".uno:CharRightSel"}},
        {"heading-into-list", "CHARLIE", {".uno:GoLeft", ".uno:LineDownSel", ".uno:CharRightSel"}},
        {"over-empty", "GOLF", {".uno:GoLeft", ".uno:LineUpSel", ".uno:LineUpSel"}},
        {"to-next-start", "ALPHA", {".uno:GoLeft", ".uno:LineDownSel"}},
        {"whole-doc", "", {".uno:SelectAll"}},
    };
    for (const auto &range : ranges)
      for (const auto &cmd : cmds) {
        auto *d = open(kit, dir + "/caret-fixture.odt");
        uno(d, ".uno:GoToStartOfDoc");
        if (*range.needle) uno(d, ".uno:ExecuteSearch", search(range.needle).c_str(), false, 420);
        for (const char *step : range.steps) uno(d, step);
        drain(150);
        Read before, after;
        before.type = d->pClass->getSelectionType(d);
        if (before.type == LOK_SELTYPE_TEXT) before.markup = html(d);
        uno(d, cmd.command, cmd.args);
        after.type = d->pClass->getSelectionType(d);
        if (after.type == LOK_SELTYPE_TEXT) after.markup = html(d);
        after.typeAfter = after.type;
        const std::string saved = saveAs(d, out, counter);
        uno(d, ".uno:Undo");
        const std::string undone = saveAs(d, out, counter);
        emit("range", range.name, "range", cmd.name, &before, &after, saved, ",\"undone\":\"" + undone + "\"");
        close(d);
      }
  } else if (part == "styles") {
    // A document whose styles.xml declares Heading 1 only: do 2 to 4 come from the pool?
    const Place where{"para-mid", "BRAVO", {".uno:GoLeft", ".uno:GoRight", ".uno:GoRight"}};
    for (const Cmd &cmd : {cmds[4], cmds[5], cmds[6]})
      for (const char *route : {"pre+post"})
        caretArm(kit, dir + "/align-fixture.odt", out, "styles", where, route, cmd, counter);
  }
  kit->pClass->destroy(kit);
  return 0;
}
