// SPEC-M3-v28-last-line-fallback 7.2 E1/E2: the production ordered_format.inc, compiled with the v25, v27 and
// v28 defines against the fake LOK of ordered_format_test.cpp (preamble written by test_ordered_format_v28.py:
// v27's switches, plus a `.uno:CharLeftSel` with its own selection type and markup, a gOrderedProof stand-in,
// and the real parser and fallback predicate cut from probe_engine.cpp).  The markup below is the shape the
// native arm recorded (findings/evidence/176/native-q52/out/cl-*/r1.jsonl, fallback.html).
#include "preamble.inc"
#include "ordered_format.inc"
int failures=0;
void check(bool ok,const char *label) {
 if(!ok) { std::cout << "FAIL " << label << '\n'; ++failures; }
}
const char *TWO_UL="<html><body dir=\"ltr\"><p style=\"x\"><br/></p> <ul> <li><p style=\"x\"></p></li> </ul> </body></html>";
const char *TRAP="<html><body><ul><li><p>Bullet before</p></li></ul><p></p></body></html>";
const char *TABLE="<html><body><table><tr><td><p>Cell text</p></td></tr></table><ul><li><p></p></li></ul></body></html>";
const char *THREE="<html><body><p>a</p><p><br/></p><ul><li><p></p></li></ul></body></html>";
void reset() {
 gFormatBarrier={}; emitted={}; results.clear(); calls.clear(); code.clear(); reply={};
 currentType=0; htmlReads=0; restoreWorks=true; deliverFormat=deliverSelect=true;
 crossRoute=false; crossIdentity=true; malformed=false; inSelect=false;
 coordinateMismatch=false; refuseRoute=false; multiBlock=false; firstBlockTag="p";
 rangeSingle=false; undoReads=0; undoReadable=true;
 selectedType=0; fallbackType=1; fallbackHtml=TWO_UL; fallbackHtmlReads=0;
 fallbackSelected=false; deliverFallback=true; gOrderedProof.uno.clear();
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
int restoresBetween(std::size_t from, std::size_t to) {
 int n=0;
 for(std::size_t i=from;i<to && i<calls.size();++i) if(calls[i]=="reset"||calls[i]=="start") ++n;
 return n;
}
bool posted(const char *name) { return indexOf(name)<calls.size(); }
int main() {
 // (a) the empty last paragraph: SelectText reads NONE, the fallback reads two blocks, the last in a list.
 reset(); run(); flush();
 check(code=="SUCCESS","(a) the fallback's last block in the target state is verified");
 check(emitted.fallbackRan && emitted.fallbackReadable,"(a) the record says the fallback ran and read");
 check(emitted.fallbackReadback.lastListTag=="ul" && emitted.fallbackReadback.lastBlockTag=="p",
       "(a) the last-block fields are filled");
 check(emitted.fallbackReadback.blockCount==2,"(a) two blocks");
 // (b) the n8 trap: the first block is a bullet, the last is not -> the last decides.
 reset(); fallbackHtml=TRAP; run(); flush();
 check(code=="EDITOR_FORMAT_POSTCONDITION_FAILED","(b) the trap is a postcondition failure");
 check(emitted.failureShape=="postcondition-not-met","(b) shape postcondition-not-met");
 // (c) the blank document: the fallback reads NONE too -> 083's shape, unchanged; no html read.
 reset(); fallbackType=0; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","(c) the fallback's NONE keeps the unknown outcome");
 check(emitted.failureShape=="select-text-returned-none","(c) 083's shape, not a new name");
 check(emitted.fallbackRan && emitted.fallbackSelectionType==0,"(c) the record shows the fallback read NONE");
 check(fallbackHtmlReads==0,"(c) no html read on NONE");
 // (d) a table before the paragraph: the existing parser refuses it -> the fallback's own shape.
 reset(); fallbackHtml=TABLE; run(); flush();
 check(code=="MUTATION_OUTCOME_UNKNOWN","(d) a refused fallback is an unknown outcome");
 check(emitted.failureShape=="fallback-readback-refused","(d) shape fallback-readback-refused");
 check(emitted.fallbackRefusal=="unknown-structural-tag","(d) sub-reason unknown-structural-tag");
 // (e) three blocks: not the measured shape -> refused.
 reset(); fallbackHtml=THREE; run(); flush();
 check(emitted.failureShape=="fallback-readback-refused","(e) three blocks refused");
 check(emitted.fallbackRefusal=="unexpected-block-count","(e) sub-reason unexpected-block-count");
 // (f) the sequence: no fallback when SelectText reads TEXT; otherwise after the NONE read, before the only Q.
 reset(); selectedType=1; run(); flush();
 check(!posted(".uno:CharLeftSel"),"(f) no fallback post when SelectText reads TEXT");
 check(code=="SUCCESS" && !emitted.fallbackRan,"(f) the TEXT path is v27's");
 reset(); run(); flush();
 {
  const std::size_t select=indexOf(".uno:SelectText"), fallback=indexOf(".uno:CharLeftSel");
  const std::size_t noneRead=indexOf("selection",select);
  check(select<noneRead && noneRead<fallback && fallback<calls.size(),
        "(f) the fallback comes after SelectText's synchronous read");
  check(restoresBetween(select,fallback)==0,"(f) no restore before the fallback");
  check(restoresBetween(fallback,calls.size())==3,"(f) exactly one Q sequence after the fallback");
  check(!coordinateMismatch,"(f) the restore uses the captured point");
 }
 // (g) RangeSingle reading NONE: no fallback.
 reset(); rangeSingle=true; run(); flush();
 check(!posted(".uno:CharLeftSel"),"(g) no fallback on the RangeSingle route");
 // (h) the fallback reads COMPLEX (an object): refused, and its markup is never read (finding 037's guard).
 reset(); fallbackType=3; run(); flush();
 check(emitted.failureShape=="fallback-readback-refused","(h) COMPLEX refused");
 check(emitted.fallbackRefusal=="selection-type-not-readable","(h) sub-reason selection-type-not-readable");
 check(fallbackHtmlReads==0,"(h) no html read on a non-TEXT fallback");
 // (i) no valid restore point: no fallback (its selection could not be cleared) -> 083's shape.
 reset(); gEditorState.caret.available=false; run(); flush();
 check(!posted(".uno:CharLeftSel"),"(i) no fallback without a restore point");
 check(emitted.failureShape=="select-text-returned-none","(i) 083's shape");
 // (j) a refused fallback whose restore failed: the restore failure wins (spec 3; review item 1).
 reset(); fallbackHtml=TABLE; restoreWorks=false; run(); flush();
 check(emitted.failureShape=="selection-not-restored","(j) a live selection is selection-not-restored, not review");
 // E2 guards.
 reset(); restoreWorks=false; run(); flush();
 check(emitted.failureShape=="selection-not-restored","(k) a judgeable fallback with a failed restore");
 reset(); fallbackType=0; restoreWorks=false; run(); flush();
 check(emitted.failureShape=="select-text-returned-none","(k) NONE fallback: nothing to restore, 083's shape");
 for(const char *h : {TWO_UL, TRAP, TABLE}) {
  reset(); fallbackHtml=h; run(); flush();
  check(emitted.undoAttempted && emitted.undoRead,"(l) every outcome carries the undo record");
 }
 reset(); deliverFallback=false; run(); flush();
 check(code=="SUCCESS","(l) an absent fallback result decides nothing");
 check(!emitted.fallbackResultSeen,"(l) recorded as not seen");
 reset(); run(); flush();
 check(emitted.fallbackResultSeen,"(l) a delivered fallback result is recorded");
 return failures ? 1 : 0;
}
