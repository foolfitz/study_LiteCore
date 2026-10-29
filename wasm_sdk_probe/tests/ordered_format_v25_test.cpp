// Finding 171 (SPEC-M3-link-batch-v25 D1/D2): the production ordered_format.inc,
// compiled with OXSDK_E2_V25_FORMAT_PROOF against the fake LOK of
// ordered_format_test.cpp (its preamble, written by the driver with two switches
// added: a refusing route and a multi-paragraph readback).
#include "preamble.inc"
#include "ordered_format.inc"
int failures=0;
void check(bool ok,const char *label) {
 if(!ok) { std::cout << "FAIL " << label << '\n'; ++failures; }
}
void reset() {
 gFormatBarrier={}; emitted={}; results.clear(); calls.clear(); code.clear(); reply={};
 currentType=0; htmlReads=0; restoreWorks=true; deliverFormat=deliverSelect=true;
 crossRoute=false; crossIdentity=true; malformed=false; inSelect=false;
 coordinateMismatch=false; refuseRoute=false; multiBlock=false; selectedType=1;
 gEditorState.caret.x=37; gEditorState.caret.y=61; gEditorState.caret.height=15;
 gEditorState.caret.available=true;
 gEditorState.selectionRectangles={gEditorState.caret};
}
void run() { startOrderedFormatAction(Command{},OXSDK_EDITOR_SET_LIST_UNORDERED,"bullet"); }
void flush() { check(bool(reply),"reply scheduled for first poll"); if(reply) reply(); }
bool posted(const char *name) {
 for(const auto &c : calls) if(c==name) return true;
 return false;
}
int main() {
 // D1: a dispatched bullet whose readback covers more than one paragraph.
 reset(); multiBlock=true; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","D1 multi-block is refused as unknown");
 check(emitted.failureShape=="multi-block-readback","D1 shape");
 check(posted(".uno:DefaultBullet"),"D1 the command was posted");
 check(emitted.dispatchRecorded && emitted.dispatched,"D1 record says dispatched");
 check(emitted.stage==FormatBarrierStage::AwaitingResult,"D1 stage is not idle");
 // D2: refused by routing before any post.
 reset(); refuseRoute=true; run(); flush();
 check(code=="EDITOR_FORMAT_GESTURE_UNSUPPORTED","D2 refusal code");
 check(!posted(".uno:DefaultBullet"),"D2 nothing posted");
 check(emitted.dispatchRecorded && !emitted.dispatched,"D2 record says not dispatched");
 check(emitted.stage==FormatBarrierStage::Idle,"D2 stage stays idle");
 // A verified success carries the same truthful record.
 reset(); run(); flush();
 check(code=="SUCCESS","success path still completes");
 check(emitted.dispatchRecorded && emitted.dispatched,"success record says dispatched");
 return failures ? 1 : 0;
}
