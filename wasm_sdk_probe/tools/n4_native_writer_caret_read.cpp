// SPEC-P-demo-batch-4 N4: the read that selects nothing.  On each caret place and command, on a fresh document: read, dispatch, read,
// insert X, save.  truth arms dispatch and insert only, so a difference in the saved document is the read's doing.  Observations.
//   n4-native INSTALL_PATH PROFILE_URL FIXTURE_DIR OUTDIR PART
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
#include "../src/writer_caret_bridge.h"
namespace {
void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }
void onCallback(int, const char *, void *) {}
void uno(LibreOfficeKitDocument *d, const char *command, const char *args = nullptr, bool notify = true, int ms = 180) {
  d->pClass->postUnoCommand(d, command, args, notify);
  drain(ms);
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
  drain(280);
  return d;
}
void close(LibreOfficeKitDocument *d) {
  d->pClass->registerCallback(d, nullptr, nullptr);
  d->pClass->destroy(d);
  drain(100);
}
void place(LibreOfficeKitDocument *d, const Place &where) {
  uno(d, ".uno:GoToStartOfDoc");
  if (where.needle && *where.needle) uno(d, ".uno:ExecuteSearch", search(where.needle).c_str(), false, 400);
  for (const char *step : where.steps) uno(d, step);
  drain(120);
}
std::string escape(const std::string &value) {
  std::string out;
  for (const char c : value) {
    if (c == '"' || c == '\\') { out += '\\'; out += c; }
    else if (static_cast<unsigned char>(c) < 0x20) out += ' ';
    else out += c;
  }
  return out;
}
std::string read(LibreOfficeKitDocument *d) {
  std::vector<probe::WriterParagraphRead> rows;
  std::string reason;
  const auto started = std::chrono::steady_clock::now();
  const bool ok = probe::writerSelectionParagraphs(d, rows, reason);
  const auto us = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - started).count();
  std::string json = std::string("{\"ok\":") + (ok ? "1" : "0") + ",\"us\":" + std::to_string(us) + ",\"reason\":\"" + escape(reason) + "\",\"rows\":[";
  for (std::size_t i = 0; i < rows.size(); ++i)
    json += std::string(i ? "," : "") + "{\"list\":\"" + rows[i].list + "\",\"block\":\"" + rows[i].block + "\",\"align\":\"" + rows[i].align + "\",\"style\":\"" + escape(rows[i].style) + "\",\"text\":\"" + escape(rows[i].text) + "\"}";
  return json + "]}";
}
std::string saveAs(LibreOfficeKitDocument *d, const std::string &out, int &counter) {
  const std::string saved = "file://" + out + "/n4-" + std::to_string(++counter) + ".odt";
  d->pClass->saveAs(d, saved.c_str(), "odt", nullptr);
  drain(130);
  return saved;
}
void arm(LibreOfficeKit *kit, const std::string &url, const std::string &out, const char *part, const Place &where, const char *route, const Cmd &cmd, int &counter, bool insert = true) {
  auto *d = open(kit, url);
  place(d, where);
  const bool reads = !std::strcmp(route, "read");
  const int typeBefore = d->pClass->getSelectionType(d);
  const std::string pre = reads ? read(d) : "null";
  uno(d, cmd.command, cmd.args);
  const std::string post = reads ? read(d) : "null";
  const int typeAfter = d->pClass->getSelectionType(d);
  if (insert) uno(d, ".uno:InsertText", "{\"Text\":{\"type\":\"string\",\"value\":\"X\"}}");
  const std::string saved = saveAs(d, out, counter);
  std::cout << "{\"part\":\"" << part << "\",\"place\":\"" << where.name << "\",\"route\":\"" << route << "\",\"command\":\"" << cmd.name << "\",\"needle\":\"" << (where.needle ? where.needle : "")
            << "\",\"typeBefore\":" << typeBefore << ",\"typeAfter\":" << typeAfter << ",\"pre\":" << pre << ",\"post\":" << post << ",\"saved\":\"" << saved << "\"}" << std::endl;
  close(d);
}
}  // namespace
int main(int argc, char **argv) {
  if (argc < 6) return 64;
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 2;
  const std::string dir = std::string("file://") + argv[3], out = argv[4], part = argv[5];
  int counter = 0;
  const std::string h1 = styleArgs("Heading 1"), h2 = styleArgs("Heading 2"), h3 = styleArgs("Heading 3"), h4 = styleArgs("Heading 4"), body = styleArgs("Text body");
  const std::vector<Cmd> cmds{{"bullet-on", ".uno:DefaultBullet", kOn}, {"number-on", ".uno:DefaultNumbering", kOn}, {"remove", ".uno:RemoveBullets", nullptr},
                              {"h1", ".uno:StyleApply", h1.c_str()}, {"h2", ".uno:StyleApply", h2.c_str()}, {"h3", ".uno:StyleApply", h3.c_str()},
                              {"h4", ".uno:StyleApply", h4.c_str()}, {"body", ".uno:StyleApply", body.c_str()},
                              {"left", ".uno:LeftPara", nullptr}, {"center", ".uno:CenterPara", nullptr}, {"right", ".uno:RightPara", nullptr}, {"justify", ".uno:JustifyPara", nullptr}};
  // Search leaves a selection; GoToStartOfPara, not GoLeft, reaches the paragraph's start (GoLeft moves from the point, finding 129).
  const char *S = ".uno:GoToStartOfPara", *R = ".uno:GoRight";
  const std::vector<Place> places{
      {"doc-start", "", {}},
      {"second-para-start", "BRAVO", {S}},
      {"second-para-after-2", "BRAVO", {S, R, R}},
      {"second-para-end", "BRAVO", {".uno:GoToEndOfPara"}},
      {"heading1-start", "CHARLIE", {S}},
      {"heading1-after-2", "CHARLIE", {S, R, R}},
      {"heading2-after-2", "DELTA", {S, R, R}},
      {"heading4-after-2", "FOXTROT", {S, R, R}},
      {"bullet-start", "GOLF", {S}},
      {"bullet-after-2", "GOLF", {S, R, R}},
      {"number-start", "INDIA", {S}},
      {"number-after-2", "INDIA", {S, R, R}},
      {"empty-mid", "KILO", {S, ".uno:GoUp"}},
      {"empty-last", "", {".uno:GoToEndOfDoc"}},
  };
  if (part == "caret") {
    for (const auto &cmd : cmds)
      for (const auto &where : places)
        for (const char *route : {"truth", "read"})
          arm(kit, dir + "/levels-fixture.odt", out, "caret", where, route, cmd, counter);
  } else if (part == "blank") {
    const Place blank{"blank-doc", "", {}};
    for (const auto &cmd : cmds) arm(kit, dir + "/blank-fixture.odt", out, "blank", blank, "read", cmd, counter);
  } else if (part == "table") {
    const std::vector<Place> whole{{"selection-into-table", "BEFORE", {S, ".uno:LineDownSel", ".uno:LineDownSel"}},
                                   {"cell-to-cell", "CELLA", {S, ".uno:LineDownSel"}}, {"inside-cell", "CELLB", {}}};
    for (const auto &where : whole)
      for (const Cmd &cmd : {cmds[0], cmds[4]})
        arm(kit, dir + "/table-caret-fixture.odt", out, "table", where, "read", cmd, counter, false);
    const std::vector<Place> cells{{"cell-start", "CELLB", {S}}, {"cell-mid", "CELLB", {S, R, R}}, {"cell-end", "CELLB", {".uno:GoToEndOfPara"}}, {"after-table-start", "AFTER", {S}}, {"before-table-end", "BEFORE", {".uno:GoToEndOfPara"}}};
    for (const auto &where : cells)
      for (const Cmd &cmd : {cmds[0], cmds[1], cmds[4], cmds[9]})
        for (const char *route : {"truth", "read"})
          arm(kit, dir + "/table-caret-fixture.odt", out, "table", where, route, cmd, counter);
  } else if (part == "large") {
    // What the read costs on a long selection, no rows printed.
    auto *d = open(kit, dir + "/long-fixture.odt");
    uno(d, ".uno:GoToStartOfDoc");
    for (const int lines : {100, 1000, 5000}) {
      uno(d, ".uno:GoToStartOfDoc");
      for (int i = 0; i < 1; ++i) (void)i;
      const std::string args = "{\"Count\":{\"type\":\"long\",\"value\":" + std::to_string(lines) + "},\"Select\":{\"type\":\"boolean\",\"value\":true}}";
      uno(d, ".uno:GoDown", args.c_str(), true, 400);
      std::vector<probe::WriterParagraphRead> rows;
      std::string reason;
      const auto started = std::chrono::steady_clock::now();
      const bool ok = probe::writerSelectionParagraphs(d, rows, reason);
      const auto us = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - started).count();
      std::cout << "{\"part\":\"large\",\"lines\":" << lines << ",\"ok\":" << ok << ",\"rows\":" << rows.size() << ",\"us\":" << us << ",\"reason\":\"" << escape(reason) << "\"}" << std::endl;
    }
    uno(d, ".uno:SelectAll");
    {
      std::vector<probe::WriterParagraphRead> rows;
      std::string reason;
      const auto started = std::chrono::steady_clock::now();
      const bool ok = probe::writerSelectionParagraphs(d, rows, reason);
      const auto us = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - started).count();
      std::cout << "{\"part\":\"large\",\"lines\":\"all\",\"ok\":" << ok << ",\"rows\":" << rows.size() << ",\"us\":" << us << ",\"reason\":\"" << escape(reason) << "\"}" << std::endl;
    }
    close(d);
    const std::vector<Place> shapes{{"caret-after-image", "and after", {S, R, R}}, {"selection-over-image", "IMAGE", {S, ".uno:EndOfParaSel"}}, {"across-image", "BEFORE", {S, ".uno:LineDownSel", ".uno:LineDownSel"}}};
    for (const auto &where : shapes)
      for (const Cmd &cmd : {cmds[0], cmds[4], cmds[9]})
        arm(kit, dir + "/image-fixture.odt", out, "large", where, "read", cmd, counter, false);
  } else if (part == "widen") {
    // A paragraph style on a leading part of one paragraph builds an inline heading frame (SwDocShell::MakeInlineHeading).  Selection
    // by keys, three shapes, each with and without the widening: `plain` dispatches on the selection, `widened` selects the paragraph first.
    const char *Rs = ".uno:CharRightSel";
    const std::vector<Place> shapes{{"leading", "BRAVO", {S, Rs, Rs, Rs}}, {"middle", "BRAVO", {S, R, R, Rs, Rs, Rs}}, {"trailing", "BRAVO", {".uno:GoToEndOfPara", ".uno:CharLeftSel", ".uno:CharLeftSel"}},
                                    {"leading-bullet", "GOLF", {S, Rs, Rs}}, {"leading-heading", "DELTA", {S, Rs, Rs}}};
    for (const auto &where : shapes)
      for (const Cmd &cmd : {cmds[4], cmds[7]})
        for (const char *route : {"plain", "widened"}) {
          auto *d = open(kit, dir + "/levels-fixture.odt");
          place(d, where);
          if (!std::strcmp(route, "widened")) uno(d, ".uno:SelectText");
          const int typeBefore = d->pClass->getSelectionType(d);
          const std::string pre = read(d);
          uno(d, cmd.command, cmd.args);
          const std::string post = read(d);
          const int typeAfter = d->pClass->getSelectionType(d);
          const std::string saved = saveAs(d, out, counter);
          std::cout << "{\"part\":\"widen\",\"place\":\"" << where.name << "\",\"route\":\"" << route << "\",\"command\":\"" << cmd.name << "\",\"needle\":\"" << where.needle
                    << "\",\"typeBefore\":" << typeBefore << ",\"typeAfter\":" << typeAfter << ",\"pre\":" << pre << ",\"post\":" << post << ",\"saved\":\"" << saved << "\"}" << std::endl;
          close(d);
        }
  } else if (part == "range") {
    // The needle stays selected, or the steps extend from it: read and acted on as it stands.
    const char *D = ".uno:LineDownSel", *Rs = ".uno:CharRightSel", *U = ".uno:LineUpSel";
    const std::vector<Place> shapes{
        {"inside-body", "BRAVO", {}}, {"inside-heading", "CHARLIE", {}}, {"inside-bullet", "GOLF", {}}, {"inside-number", "INDIA", {}},
        {"from-mid-across-two", "ALPHA", {R, D}},                  // starts inside a paragraph: the HTML read loses its style (N3)
        {"whole-two", "ALPHA", {S, ".uno:EndOfParaSel", Rs, ".uno:EndOfParaSel"}},
        {"heading-into-bullet", "FOXTROT", {S, D, Rs, Rs}},
        {"bullet-pair", "GOLF", {S, D, Rs}},
        {"bullet-into-number", "HOTEL", {S, D, Rs}},
        {"over-empty", "KILO", {S, U, U}},
        {"to-next-start", "ALPHA", {S, ".uno:EndOfParaSel", Rs}},
        {"whole-doc", "", {".uno:SelectAll"}},
    };
    for (const auto &where : shapes)
      for (const Cmd &cmd : {cmds[0], cmds[1], cmds[2], cmds[3], cmds[5], cmds[7], cmds[9]})
        arm(kit, dir + "/levels-fixture.odt", out, "range", where, "read", cmd, counter, false);
  }
  kit->pClass->destroy(kit);
  return 0;
}
