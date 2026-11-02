// SPEC-P-demo-batch-4 N5: press sequences through the v32 decision, natively.  `press` is startOrderedParagraphRead's order with the LOK calls
// the engine makes: read, the refusal, the choice between the setters (the same helpers from writer_caret_bridge.h), the widening, dispatch,
// read, the verdict.  One document per sequence; every step saves.  Observations; the reader judges them against the saved files.
//   n5-native INSTALL_PATH PROFILE_URL FIXTURE_DIR OUTDIR
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
using probe::WriterParagraphRead;
namespace {
void drain(int ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }
void onCallback(int, const char *, void *) {}
void uno(LibreOfficeKitDocument *d, const char *command, const char *args = nullptr, int ms = 170) {
  d->pClass->postUnoCommand(d, command, args, true);
  drain(ms);
}
std::string search(const char *needle) {
  return std::string("{\"SearchItem.SearchString\":{\"type\":\"string\",\"value\":\"") + needle +
         "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
}
const char *kOn = "{\"On\":{\"type\":\"boolean\",\"value\":true}}";
std::string styleArgs(const std::string &style) {
  return "{\"Style\":{\"type\":\"string\",\"value\":\"" + style + "\"},\"FamilyName\":{\"type\":\"string\",\"value\":\"ParagraphStyles\"}}";
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
std::string show(const std::vector<WriterParagraphRead> &rows) {
  std::string json = "[";
  for (std::size_t i = 0; i < rows.size(); ++i)
    json += std::string(i ? "," : "") + "{\"list\":\"" + rows[i].list + "\",\"block\":\"" + rows[i].block + "\",\"text\":\"" + escape(rows[i].text.substr(0, 24)) + "\"}";
  return json + "]";
}
struct Press { std::string outcome, command; std::vector<WriterParagraphRead> before, after; };
Press press(LibreOfficeKitDocument *d, const std::string &name) {
  Press p;
  std::string reason, list, block;
  if (!probe::writerSelectionParagraphs(d, p.before, reason)) { p.outcome = "refused-not-paragraphs"; return p; }
  const int type = d->pClass->getSelectionType(d);
  const bool rangeSingle = type != LOK_SELTYPE_NONE && p.before.size() == 1;
  std::string command, args;
  auto setList = [&](const char *tag) {
    list = tag ? tag : "none";
    command = !tag ? ".uno:RemoveBullets" : tag[0] == 'u' ? ".uno:DefaultBullet" : ".uno:DefaultNumbering";
    args = tag ? kOn : "";
  };
  auto setStyle = [&](int level) {
    command = ".uno:StyleApply";
    args = styleArgs(level ? "Heading " + std::to_string(level) : std::string("Text body"));
    block = level ? "h" + std::to_string(level) : "p";
  };
  if (name == "bullet") setList(probe::toggleTakesOff(p.before, "ul", "") ? nullptr : "ul");
  else if (name == "number") {
    const bool off = probe::toggleTakesOff(p.before, "ol", "");
    if (!off && probe::numberingHasNoEffect(p.before)) { p.outcome = "refused-number-on-heading"; return p; }
    setList(off ? nullptr : "ol");
  } else if (name == "body") setStyle(0);
  else {
    const int level = name[1] - '0';
    setStyle(probe::toggleTakesOff(p.before, "", "h" + std::to_string(level)) ? 0 : level);
  }
  p.command = command;
  if (rangeSingle && command == ".uno:StyleApply") {
    uno(d, ".uno:SelectText");
    if (!probe::writerSelectionParagraphs(d, p.before, reason) || p.before.size() != 1) { p.outcome = "refused-widening"; return p; }
  }
  // The engine reads straight after the post, in the same command.  N5_DISPATCH_DRAIN_MS=0 does that here too.
  static const int drainAfter = std::getenv("N5_DISPATCH_DRAIN_MS") ? std::atoi(std::getenv("N5_DISPATCH_DRAIN_MS")) : 170;
  uno(d, command.c_str(), args.empty() ? nullptr : args.c_str(), drainAfter);
  if (!probe::writerSelectionParagraphs(d, p.after, reason)) { p.outcome = "paragraph-read-failed"; return p; }
  bool texts = p.after.size() == p.before.size();
  for (std::size_t i = 0; texts && i < p.after.size(); ++i) texts = p.after[i].text == p.before[i].text;
  p.outcome = !texts ? "identity-failed" : probe::everyParagraphMeets(p.after, list, block, "") ? "verified" : "postcondition-not-met";
  return p;
}
struct Seq { const char *name, *file, *needle; std::vector<const char *> steps; std::vector<const char *> presses; };
}  // namespace
int main(int argc, char **argv) {
  if (argc < 5) return 64;
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);
  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 2;
  const std::string dir = std::string("file://") + argv[3], out = argv[4];
  const char *S = ".uno:GoToStartOfPara", *R = ".uno:GoRight", *D = ".uno:LineDownSel", *Rs = ".uno:CharRightSel";
  const char *L = "levels-fixture.odt", *B = "blank-fixture.odt", *T = "table-caret-fixture.odt";
  const std::vector<Seq> seqs{
      {"bullet-thrice", L, "BRAVO", {S, R}, {"bullet", "bullet", "bullet"}},
      {"number-thrice", L, "BRAVO", {S, R}, {"number", "number", "number"}},
      {"bullet-to-number-to-bullet", L, "BRAVO", {S}, {"bullet", "number", "bullet", "bullet"}},
      {"h1-twice", L, "BRAVO", {S, R}, {"h1", "h1"}},
      {"h2-twice", L, "BRAVO", {S, R}, {"h2", "h2"}},
      {"h3-twice", L, "BRAVO", {S, R}, {"h3", "h3"}},
      {"h4-twice", L, "BRAVO", {S, R}, {"h4", "h4"}},
      {"level-to-level-to-body", L, "BRAVO", {S}, {"h1", "h4", "h2", "body", "body"}},
      {"existing-heading-off", L, "ECHO", {S, R}, {"h3", "h3"}},
      {"existing-heading-other-level", L, "ECHO", {S, R}, {"h1", "h3", "h3"}},
      {"existing-bullet-off-on", L, "GOLF", {S, R}, {"bullet", "bullet"}},
      {"existing-number-off-on", L, "INDIA", {S}, {"number", "number"}},
      {"existing-bullet-to-number", L, "GOLF", {S, R}, {"number", "number"}},
      {"existing-number-to-bullet", L, "INDIA", {S, R}, {"bullet", "bullet"}},
      {"heading-then-bullet-then-off", L, "BRAVO", {S}, {"h2", "bullet", "bullet", "h2"}},
      {"bullet-then-heading-then-off", L, "BRAVO", {S}, {"bullet", "h2", "h2", "bullet"}},
      {"number-then-heading", L, "BRAVO", {S}, {"number", "h3", "number", "h3", "number"}},
      {"number-refused-on-heading", L, "DELTA", {S, R}, {"number", "bullet", "number", "bullet", "h2", "number"}},
      {"empty-mid", L, "KILO", {S, ".uno:GoUp"}, {"bullet", "bullet", "h2", "h2", "number", "number"}},
      {"empty-last", L, "", {".uno:GoToEndOfDoc"}, {"bullet", "bullet", "h2", "h2", "number", "number"}},
      {"blank", B, "", {}, {"bullet", "bullet", "number", "number", "h2", "h2", "body"}},
      {"table-cell", T, "CELLB", {S, R}, {"bullet", "bullet", "h2", "h2", "number", "number"}},
      {"range-from-inside", L, "ALPHA", {S, R, R, D}, {"h3", "h3", "bullet", "bullet", "number", "number"}},
      {"range-whole-two", L, "ALPHA", {S, ".uno:EndOfParaSel", Rs, ".uno:EndOfParaSel"}, {"h1", "h1", "bullet", "bullet"}},
      {"range-leading", L, "BRAVO", {S, Rs, Rs, Rs}, {"h2", "h2", "bullet", "bullet"}},
      {"range-mixed-bullets", L, "HOTEL", {S, D, Rs}, {"bullet", "bullet", "number", "number"}},
      {"range-mixed-headings", L, "CHARLIE", {S, D}, {"h2", "h2", "bullet", "bullet"}},
      {"range-whole-doc", L, "", {".uno:SelectAll"}, {"bullet", "bullet", "number", "number", "h1", "h1"}},
  };
  int counter = 0;
  for (const Seq &seq : seqs) {
    auto *d = kit->pClass->documentLoad(kit, (dir + "/" + seq.file).c_str());
    if (!d) { std::cerr << "load failed\n"; return 3; }
    d->pClass->initializeForRendering(d, "{}");
    d->pClass->registerCallback(d, onCallback, nullptr);
    drain(280);
    uno(d, ".uno:GoToStartOfDoc");
    if (*seq.needle) uno(d, ".uno:ExecuteSearch", search(seq.needle).c_str(), 400);
    for (const char *step : seq.steps) uno(d, step);
    drain(120);
    int step = 0;
    for (const char *name : seq.presses) {
      const Press p = press(d, name);
      const std::string saved = "file://" + out + "/n5-" + std::to_string(++counter) + ".odt";
      d->pClass->saveAs(d, saved.c_str(), "odt", nullptr);
      drain(120);
      std::cout << "{\"sequence\":\"" << seq.name << "\",\"step\":" << ++step << ",\"press\":\"" << name << "\",\"outcome\":\"" << p.outcome << "\",\"command\":\"" << p.command
                << "\",\"before\":" << show(p.before) << ",\"after\":" << show(p.after) << ",\"saved\":\"" << saved << "\"}" << std::endl;
    }
    d->pClass->registerCallback(d, nullptr, nullptr);
    d->pClass->destroy(d);
    drain(100);
  }
  kit->pClass->destroy(kit);
  return 0;
}
