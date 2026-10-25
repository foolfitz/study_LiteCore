// Exercise the production ordered_format.inc with a synchronous fake LOK.
#include <chrono>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <map>
#include <string>
#include <vector>
#include "format_types.inc"
constexpr int LOK_SELTYPE_NONE=0, LOK_SELTYPE_TEXT=1;
constexpr int LOK_SETTEXTSELECTION_RESET=0, LOK_SETTEXTSELECTION_START=1;
constexpr int OXSDK_EDITOR_SET_LIST_UNORDERED=1, OXSDK_EDITOR_SET_LIST_ORDERED=2,
 OXSDK_EDITOR_SET_LIST_NONE=3, OXSDK_EDITOR_SET_PARAGRAPH_HEADING=4,
 OXSDK_EDITOR_SET_PARAGRAPH_BODY=5;
struct Command { unsigned requestId=1; };
struct SelectionReadback { int type=0; };
FormatStateBarrier gFormatBarrier, emitted;
struct EditorState {
 unsigned sourceSequence=0; EditorRect caret; bool selectionObserved=true;
 std::vector<EditorRect> selectionRectangles;
 std::uint64_t a11yContentHash=42; bool a11yFingerprintUsable=true;
} gEditorState;
std::function<void()> reply;
std::map<std::string,std::string> results;
std::vector<std::string> calls;
std::string code;
int selectedType=1, currentType=0, htmlReads=0;
bool restoreWorks=true, deliverFormat=true, deliverSelect=true;
bool crossRoute=false, crossIdentity=true, malformed=false;
bool inSelect=false, coordinateMismatch=false;
const char *kFormatBarrierSelectCommand=".uno:SelectText";
const char *kFormatMutationOutcomeUnknown="MUTATION_OUTCOME_UNKNOWN";
const char *kListOnArguments="{}";
constexpr std::size_t FormatReadbackEvidenceLimit=2048;
struct Doc;
struct DocClass {
 void (*postUnoCommand)(Doc*,const char*,const char*,bool);
 char *(*getTextSelection)(Doc*,const char*,void*);
 void (*setTextSelection)(Doc*,int,int,int);
};
void post(Doc*,const char *name,const char*,bool listener) {
 calls.push_back(name);
 if (!listener) std::abort();
 bool select=std::string(name)==kFormatBarrierSelectCommand;
 if (select) { currentType=selectedType; inSelect=true; }
 if (select ? deliverSelect : deliverFormat) results[name]="true";
}
char *html(Doc*,const char*,void*) { ++htmlReads; return strdup("<p>text</p>"); }
void setSelection(Doc*,int type,int x,int y) {
 calls.push_back(type==LOK_SETTEXTSELECTION_RESET ? "reset" : "start");
 if(x!=37 || y!=68) coordinateMismatch=true;
 if(!restoreWorks) return;
 if(type==LOK_SETTEXTSELECTION_RESET) currentType=0;
 else { currentType=inSelect ? 0 : 1; inSelect=false; }
}
DocClass docClass{post,html,setSelection};
struct Doc { DocClass *pClass=&docClass; } doc;
struct State { Doc *document=&doc; unsigned documentHandle=1, revision=1; } gState;
void setOrderedReply(std::function<void()> f) { reply=std::move(f); }
void expectOrderedUno(const std::string&) {}
bool orderedUnoResult(const std::string &name,std::string &payload) {
 auto i=results.find(name); if(i==results.end()) return false; payload=i->second; return true;
}
bool commandResultSucceeded(const char*) { return true; }
const char *jsonFieldValue(const char*,const char*) { return "true"; }
void failFormatBarrier(const char *c,const char*) { code=c; emitted=gFormatBarrier; }
void completeFormatBarrier() { code="SUCCESS"; emitted=gFormatBarrier; }
bool formatBarrierReadbackSatisfied() { return gFormatBarrier.readback.blockTag=="p"; }
void emitCommandError(const Command&,const char*,const char *c,const char*) { code=c; }
std::string styleApplyArguments(bool) { return "{}"; }
std::vector<std::string> styleCandidates(bool) { return {}; }
bool routeFormatBarrier(FormatStateBarrier &b,unsigned,std::string&) {
 b.route=crossRoute ? FormatBarrierRoute::RangeCross : FormatBarrierRoute::Collapsed;
 b.preBlockTexts={"first", "second"}; return true;
}
bool refreshCaretParagraph() { calls.push_back("fingerprint"); return true; }
SelectionReadback readSelection() { calls.push_back("selection"); return {currentType}; }
FormatReadback parseFormatReadback(const std::string&) {
 FormatReadback r; r.parsed=true; r.blockTag="p"; r.blockCount=1; return r;
}
void checkFormatBarrierCrossParagraph() {
 gFormatBarrier.crossChecked=true;
 gFormatBarrier.selectionTypeReadable=true;
 gFormatBarrier.crossIdentityHeld=crossIdentity;
 gFormatBarrier.crossStateHeld=true;
 gFormatBarrier.postBlockTexts={"first", "second"};
 gFormatBarrier.readback.parsed=true;
 gFormatBarrier.readback.malformedNesting=malformed;
}
#include "ordered_format.inc"
int failures=0;
void check(bool ok,const char *label) {
 if(!ok) { std::cout << "FAIL " << label << '\n'; ++failures; }
}
void reset() {
 gFormatBarrier={}; results.clear(); calls.clear(); code.clear(); reply={};
 currentType=0; htmlReads=0; restoreWorks=true; deliverFormat=deliverSelect=true;
 crossRoute=false; crossIdentity=true; malformed=false;
 inSelect=false; coordinateMismatch=false;
 gEditorState.caret.x=37; gEditorState.caret.y=61; gEditorState.caret.height=15;
 gEditorState.caret.available=true;
 // Deliberately stale nonempty callbacks: NONE must come from direct read.
 gEditorState.selectionRectangles={gEditorState.caret};
}
void run() { startOrderedFormatAction(Command{},OXSDK_EDITOR_SET_PARAGRAPH_BODY,"body"); }
void flush() { check(bool(reply),"reply scheduled for first poll"); if(reply) reply(); }
int main() {
 // Both poisoned and clean initial mode must end markless and out of select.
 for(bool poisoned : {false, true}) {
  reset(); inSelect=poisoned; currentType=1;
  gFormatBarrier.restorePoint=gEditorState.caret;
  gFormatBarrier.restorePointValid=true;
  restoreOrderedFormatPoint();
  check(currentType==0 && !inSelect,"Q clears mark and selection mode");
  check(!coordinateMismatch,"Q uses recorded point and vertical midpoint");
  check(calls==std::vector<std::string>({"reset","start","reset"}),
        "Q is three contiguous calls without intermediate read");
 }
 reset(); gFormatBarrier.restorePointValid=false; restoreOrderedFormatPoint();
 check(calls.empty(),"unavailable restore point never reaches LOK");
 reset(); selectedType=0; run();
 check(code.empty(),"NONE reply not composed before poll");
 check(htmlReads==0,"NONE prevents HTML read");
 flush(); check(code=="MUTATION_OUTCOME_UNKNOWN","NONE refused on first poll");
 check(emitted.failureShape=="select-text-returned-none","NONE has precise shape");
 reset(); selectedType=1; run(); flush();
 check(code=="SUCCESS","synchronous read beats stale selection callbacks");
 check(emitted.restoreConfirmed,"NONE read confirms restore");
 check(!inSelect,"full format command leaves subsequent selecting movement usable");
 check(!coordinateMismatch,"both format restoration points use captured coordinates");
 reset(); selectedType=1; deliverSelect=false; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","missing SelectText proof refused");
 check(emitted.failureShape=="proof-absent-at-poll:UNO_COMMAND_RESULT:.uno:SelectText",
       "missing SelectText proof names callback and command");
 reset(); selectedType=1; deliverFormat=false; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","missing format proof refused");
 check(emitted.failureShape=="proof-absent-at-poll:UNO_COMMAND_RESULT:.uno:StyleApply",
       "missing format proof names callback and command");
 reset(); selectedType=1; restoreWorks=false; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","restore failure refused");
 reset(); crossRoute=true; deliverSelect=false; run(); flush();
 check(code=="SUCCESS","cross route preserves range without SelectText");
 reset(); crossRoute=true; crossIdentity=false; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","cross block identity failure refused");
 reset(); crossRoute=true; malformed=true; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","cross malformed readback refused");
 return failures ? 1 : 0;
}
