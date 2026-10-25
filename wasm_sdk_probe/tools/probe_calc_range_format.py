#!/usr/bin/env python3
"""Exercise the built range successor through real UI, native writes and ODS.

The private browser mirror names its selected engine directory v2 and records
that source-only URL substitution. No frozen profile is changed.
"""
import hashlib
import json
from pathlib import Path
import time
import run_calc_editor_browser as browser
from create_calc_range_format_fixture import create, FORMATS, CASES
from probe_calc_input_range_full import pointer
from probe_calc_format_view import INSTRUMENT, SNAPSHOT
from r7_support import evaluate, run_in_page
from run_calc_cell_native import cells_from_xml, NAMES
from ods_cell_attributes import effective_attributes

_base_mirror = browser.mirror


def mirror(out, profile):
    root = _base_mirror(out, profile)
    (root/"profiles/ods-editor-v1").rename(root/"profiles/ods-editor-v2")
    app=root/"ods-editor-app.js";source=app.read_text()
    old='"./profiles/ods-editor-v1/sdk-worker.js"'
    new='"./profiles/ods-editor-v2/sdk-worker.js"'
    if source.count(old)==1:app.write_text(source.replace(old,new))
    elif source.count(new)!=1:raise RuntimeError("engine URL substitution premise changed")
    manifest=json.loads((profile/"sdk-manifest.json").read_text())
    files={"sdk-manifest.json","sdk-worker.js",*map(lambda x:x.removeprefix("./"),manifest["artifactFiles"].values())}
    record={"root":str(root),"patch":"private mirror engine URL v1 -> v2",
        "sha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()},
        "engineSha256":{name:hashlib.sha256((profile/name).read_bytes()).hexdigest() for name in files}}
    (out/"mirror-sources.json").write_text(json.dumps(record,indent=2)+"\n")
    return root


def exercise(session, out, run):
    run["toolSha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    def state(): return evaluate(session, "window.__calcEditor.state")
    def idle(): browser.wait(session, "!window.__calcEditor.state.busy && !window.__calcEditor.state.selectionPending")
    def check(name, passed, actual=None):
        run["checks"].append({"id": name, "pass": bool(passed), "actual": actual})
        if not passed: raise AssertionError(name)
    def call(body):
        if "setRangeFormat" in body or "setCellFormat" in body:
            # Diagnostic setup writes bypass session publishing; bring its tile
            # context forward before any following product event can publish.
            body="try{"+body+"}finally{window.__calcEditor.session.scheduler.invalidateRevision(d.revision);}"
        return evaluate(session, "(async()=>{const d=window.__calcEditor.session.document;" + body + "})()")
    def geometry(c, r):
        return call(f"const a=(await d.readCell({c},{r})).cell;const s=document.querySelector('#surface').getBoundingClientRect();return {{x:s.x+(a.xTwips+a.widthTwips/2)/15,y:s.y+(a.yTwips+a.heightTwips/2)/15}};")
    check("successor-capability", state()["rangeFormattingSupported"] is True, state())
    run_in_page(session, INSTRUMENT)
    run_in_page(session, "(()=>{const d=window.__calcEditor.session.document,f=d.setRangeFormat.bind(d);window.__rangeWrites=0;d.setRangeFormat=(...a)=>{window.__rangeWrites++;return f(...a);};})();")
    for fmt in FORMATS:
        call(f"await d.setRangeFormat(0,0,2,1,'{fmt}',false);await d.setCellFormat(1,1,'{fmt}',true);")
        browser.select(session, "A1");pointer(session, [geometry(0,0),geometry(2,1)]);idle()
        check("mixed/" + fmt, state()["rangeFormat"][fmt] is None, state()["rangeFormat"])
        check("mixed-ui/" + fmt, evaluate(session, f"document.querySelector('[data-format={fmt}]').getAttribute('aria-pressed')") == "mixed")
        before = state()["revision"]; count = evaluate(session, "window.__rangeWrites")
        session.click(f"[data-format={fmt}]");idle()
        check("toolbar-on/" + fmt, state()["rangeFormat"][fmt] is True and state()["revision"] == before+1
              and evaluate(session,"window.__rangeWrites") == count+1 and state()["selection"]["multiple"], state())
        session.click(f"[data-format={fmt}]");idle()
        check("toolbar-off/" + fmt, state()["rangeFormat"][fmt] is False, state()["rangeFormat"])
        session.click(f"[data-format={fmt}]");idle()
    # Explicit SDK target remains authoritative after unrelated cursor-changing reads.
    call("await d.readCell(0,0,{part:1});")
    target = call("return (await d.setRangeFormat(0,0,2,1,'bold',true,{part:0})).range;")
    check("explicit-target", target["part"] == 0 and target["endColumn"] == 2, target)
    for case in CASES:
        c,r,ec,er = case["bounds"]
        for fmt in FORMATS:
            before = state()["revision"]
            result = call(f"try{{const x=await d.setRangeFormat({c},{r},{ec},{er},'{fmt}',true,{{part:{case['part']}}});return {{ok:true,...x}};}}catch(e){{return {{ok:false,code:e.code}};}}")
            check(case["id"] + "/" + fmt,
                  (result.get("code") == case["code"] and state()["revision"] == before) if case["code"]
                  else result.get("ok") is True and result["range"][fmt] is True, result)
    revision = state()["revision"]
    stale = call("try{await d.setRangeFormat(0,0,2,1,'bold',false,{expectedRevision:4294967295});return null;}catch(e){return e.code;}")
    check("stale-refusal", stale == "STALE_REVISION" and state()["revision"] == revision, stale)
    limit = call("try{await d.setRangeFormat(7,0,7,65536,'bold',true);return null;}catch(e){return e.code;}")
    check("sdk-cap", limit == "RANGE_TOO_LARGE" and state()["revision"] == revision, limit)
    # A whole hidden cell is read without cursor geometry; it must be included.
    hidden = call("return (await d.readRange(3,3,3,3)).range;")
    check("hidden-model", all(hidden[f] is True for f in FORMATS), hidden)
    neighbor = call("return (await d.readRange(5,1,5,1,{part:0})).range;")
    other = call("return (await d.readCell(0,0,{part:1})).cell;")
    check("neighbors-preserved", all(neighbor[f] is False and other[f] is False for f in FORMATS)
          and other["input"] == "第二表不應改動", {"neighbor":neighbor,"other":other})
    # A real session operation invalidates after all SDK diagnostic writes.
    browser.select(session,"A1");pointer(session,[geometry(0,0),geometry(2,1)]);idle()
    session.click("[data-format=bold]");idle();session.click("[data-format=bold]");idle()
    browser.wait(session,"document.querySelectorAll('#tiles canvas').length>0")
    time.sleep(.3)
    view = evaluate(session,SNAPSHOT)
    path = out / f"{run['browser']}-r{run['repeat']}-range-view.json"
    path.write_text(json.dumps(view,indent=2)+"\n")
    check("tiles", view["visibleTiles"]>0 and bool(view["tiles"]) and all(t["matched"] for t in view["tiles"]), {"artifact":path.name})
    session.click("#save-button");idle()
    downloads = Path(run["downloadDirectory"])
    deadline = time.monotonic()+30
    while not list(downloads.glob("*.ods")) and time.monotonic()<deadline:time.sleep(.1)
    saved = next(downloads.glob("*.ods"))
    fields = [f"{{{NAMES['f']}}}font-weight",f"{{{NAMES['s']}}}font-weight-asian",f"{{{NAMES['s']}}}font-weight-complex",
              f"{{{NAMES['f']}}}font-style",f"{{{NAMES['s']}}}font-style-asian",f"{{{NAMES['s']}}}font-style-complex",
              f"{{{NAMES['s']}}}text-underline-style"]
    expected = ["bold","bold","bold","italic","italic","italic","solid"]
    exported = {f"{c},{r}":effective_attributes(saved,0,c,r) for c in range(3) for r in range(2)}
    check("xml-script-families", all([a.get(k) for k in fields] == expected for a in exported.values()), exported)
    run["saved"]={"path":str(saved),"sha256":hashlib.sha256(saved.read_bytes()).hexdigest()}
    run_in_page(session,"window.__rangeOldSession=window.__calcEditor.session;")
    session.set_file("#file-input",saved)
    browser.wait(session,"window.__calcEditor.session!==window.__rangeOldSession && window.__calcEditor.state.state==='ready' && !!window.__calcEditor.state.cell && !window.__calcEditor.state.busy")
    session.click('[data-part="0"]');idle()
    reopened = call("return (await d.readRange(0,0,2,1,{part:0})).range;")
    check("reopen-range", all(reopened[f] is True for f in FORMATS), reopened)


if __name__ == "__main__":
    browser.mirror=mirror
    browser.create=create
    browser.exercise=exercise
    raise SystemExit(browser.main())
