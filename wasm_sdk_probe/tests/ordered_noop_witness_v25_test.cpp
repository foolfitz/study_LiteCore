// Finding 172 (SPEC-M3-link-batch-v25 R1/R2): the production v25 witness helpers
// (extracted from ordered_engine_reply.inc by the driver) and, beside them, the
// shipped v23/v24 gate (inlineFormatArgumentResolved, extracted from
// probe_engine.cpp and compiled under the v23 define) on the same inputs.
#include <iostream>
#include <set>
#include <string>
#include "reply_state_reads.hpp"
struct EditorState {
 bool boldKnown=false, bold=false, italicKnown=false, italic=false;
 bool underlineKnown=false, underline=false, strikeoutKnown=false, strikeout=false;
} gEditorState;
struct OrderedProof { std::set<std::string> stateItems; } gOrderedProof;
bool commandResultSucceeded(const char *payload) {
 return std::string(payload).find("\"success\":true")!=std::string::npos;
}
#include "witness.inc"
#include "shipped_gate.inc"
const std::string kFalse="{\"commandName\":\".uno:Bold\",\"success\":false}";
const std::string kTrue="{\"commandName\":\".uno:Bold\",\"success\":true}";
int failures=0;
void check(bool ok,const char *label) {
 if(!ok) { std::cout << "FAIL " << label << '\n'; ++failures; }
}
std::string w(const char *uno,bool requested,const std::string &payload) {
 const char *v=orderedInlineFormatWitness(uno,requested,payload); return v ? v : "";
}
bool shippedFails(const char *uno,bool requested,const std::string &payload) {
 return !commandResultSucceeded(payload.c_str()) && !inlineFormatArgumentResolved(uno,requested);
}
void reset() { gEditorState={}; gOrderedProof={}; }
int main() {
 // R1: bold off requested on plain text; no broadcast because nothing changes.
 reset(); gEditorState.boldKnown=true; gEditorState.bold=false;
 check(w(".uno:Bold",false,kFalse)=="state-noop","R1 no-op answered as state-noop");
 check(shippedFails(".uno:Bold",false,kFalse),"R1 the shipped gate refuses the same no-op (finding 172)");
 // R1 positive control: a real change with its item in this flush.
 reset(); gEditorState.boldKnown=true; gEditorState.bold=true; gOrderedProof.stateItems={".uno:Bold"};
 check(w(".uno:Bold",true,kFalse)=="on-time-item","R1 control: change proven by its on-time item");
 check(!shippedFails(".uno:Bold",true,kFalse),"R1 control: the shipped gate accepts it too");
 // R2: the state disagrees with the request and nothing arrived: a failure.
 reset(); gEditorState.boldKnown=true; gEditorState.bold=true;
 check(w(".uno:Bold",false,kFalse).empty(),"R2 cache != requested without item fails");
 // An unknown state is never read as yes.
 reset(); gEditorState.italicKnown=false;
 check(w(".uno:Italic",false,kFalse).empty(),"unknown state fails");
 // Item present but disagreeing: a failure, as before.
 reset(); gEditorState.underlineKnown=true; gEditorState.underline=false;
 gOrderedProof.stateItems={".uno:Underline"};
 check(w(".uno:Underline",true,kFalse).empty(),"item present but wrong fails");
 // Each of the four inline items is on the on-time table.
 reset(); gEditorState.strikeoutKnown=true;
 check(w(".uno:Strikeout",false,kFalse)=="state-noop","strikeout no-op");
 // Other commands keep the result-only policy.
 reset();
 check(w(".uno:DefaultBullet",true,kFalse).empty(),"non-inline success:false fails");
 check(w(".uno:DefaultBullet",true,kTrue)=="uno-success","non-inline success:true passes");
 check(w(".uno:Bold",true,kTrue)=="uno-success","a successful result is uno-success");
 return failures ? 1 : 0;
}
