// Finding 176 (SPEC-M3-v27-finding-176 7.2 E1/E2): the production ordered_format.inc,
// compiled with OXSDK_E2_V25_FORMAT_PROOF and OXSDK_E2_V27_FIRST_BLOCK against the
// fake LOK of ordered_format_test.cpp (its preamble, written by the driver with
// switches added: a multi-paragraph readback, an unsatisfied first block, a
// RangeSingle route, a refusing route, and an undo stack that gains one action).
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
 coordinateMismatch=false; refuseRoute=false; multiBlock=false; firstBlockTag="p";
 rangeSingle=false; undoReads=0; undoReadable=true; selectedType=1;
 gEditorState.caret.x=37; gEditorState.caret.y=61; gEditorState.caret.height=15;
 gEditorState.caret.available=true;
 gEditorState.selectionRectangles={gEditorState.caret};
}
void run() { startOrderedFormatAction(Command{},OXSDK_EDITOR_SET_LIST_UNORDERED,"bullet"); }
void flush() { check(bool(reply),"reply scheduled for first poll"); if(reply) reply(); }
std::size_t indexOf(const std::string &name, std::size_t from=0) {
 for(std::size_t i=from;i<calls.size();++i) if(calls[i]==name) return i;
 return calls.size();
}
// The LOK selection calls between two indices of `calls`.
int restoresBetween(std::size_t from, std::size_t to) {
 int n=0;
 for(std::size_t i=from;i<to && i<calls.size();++i) if(calls[i]=="reset"||calls[i]=="start") ++n;
 return n;
}
int main() {
 // (a) collapsed, two paragraphs read back, the first in the target state: verified.
 reset(); multiBlock=true; run(); flush();
 check(code=="SUCCESS","(a) collapsed multi-block with a satisfied first block is verified");
 check(emitted.readback.multiBlock,"(a) the record says the verdict came from a multi-block read");
 // (b) the same, the first block NOT in the target state: the postcondition failed.
 reset(); multiBlock=true; firstBlockTag="h1"; run(); flush();
 check(code=="EDITOR_FORMAT_POSTCONDITION_FAILED","(b) unsatisfied first block is a postcondition failure");
 check(emitted.failureShape=="postcondition-not-met","(b) shape postcondition-not-met");
 // (d) collapsed: nothing between the dispatch and the select; exactly one Q after the read.
 reset(); multiBlock=true; run(); flush();
 {
  const std::size_t dispatch=indexOf(".uno:DefaultBullet"), select=indexOf(".uno:SelectText");
  check(dispatch<select && select<calls.size(),"(d) dispatch then select");
  check(restoresBetween(dispatch,select)==0,"(d) no restore between the dispatch and the select");
  check(restoresBetween(select,calls.size())==3,"(d) exactly one Q sequence after the select");
  check(!coordinateMismatch,"(d) the remaining restore uses the captured point");
 }
 // (c) RangeSingle keeps refusing a multi-block read, and keeps the restore before the select.
 reset(); multiBlock=true; rangeSingle=true; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","(c) RangeSingle multi-block is refused as unknown");
 check(emitted.failureShape=="multi-block-readback","(c) RangeSingle shape");
 {
  const std::size_t dispatch=indexOf(".uno:DefaultBullet"), select=indexOf(".uno:SelectText");
  check(restoresBetween(dispatch,select)==3,"(c) RangeSingle keeps the Q sequence before the select");
 }
 // A failed restore is still refused on the collapsed multi-block path.
 reset(); multiBlock=true; restoreWorks=false; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","restore failure still refused");
 check(emitted.failureShape=="selection-not-restored","restore failure shape");
 // (f) the undo record: on success, on the postcondition failure, on the RangeSingle refusal.
 reset(); multiBlock=true; run(); flush();
 check(emitted.undoAttempted && emitted.undoRead,"(f) success carries a read undo record");
 check(emitted.undoChanged && emitted.undoActionsBefore==0 && emitted.undoActionsAfter==1,
       "(f) success: one action gained");
 check(emitted.undoTop=="Number On/Off","(f) success: the new top comment");
 reset(); multiBlock=true; firstBlockTag="h1"; run(); flush();
 check(emitted.undoAttempted && emitted.undoRead,"(f) postcondition failure carries the undo record");
 reset(); multiBlock=true; rangeSingle=true; run(); flush();
 check(emitted.undoAttempted && emitted.undoRead,"(f) RangeSingle refusal carries the undo record");
 reset(); multiBlock=true; undoReadable=false; run(); flush();
 check(code=="SUCCESS","(f) an unreadable undo stack decides nothing");
 check(emitted.undoAttempted && !emitted.undoRead,"(f) unreadable undo is recorded as not read");
 // A pre-dispatch refusal never reads the undo stack.
 reset(); refuseRoute=true; run(); flush();
 check(code=="EDITOR_FORMAT_GESTURE_UNSUPPORTED","pre-dispatch refusal code");
 check(!emitted.undoAttempted && undoReads==0,"pre-dispatch refusal reads no undo");
 // A single-paragraph read is unchanged: verified.
 reset(); run(); flush();
 check(code=="SUCCESS","single-block collapsed read still verified");
 return failures ? 1 : 0;
}
