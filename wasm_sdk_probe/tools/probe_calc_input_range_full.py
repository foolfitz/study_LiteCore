#!/usr/bin/env python3
"""Finite I-entry/R-select acceptance using product events and exported ODS."""
import json
from pathlib import Path
import time

import run_calc_editor_browser as browser
from create_calc_range_fixture import create
from probe_calc_input_range import press, insert
from probe_calc_format_view import INSTRUMENT, SNAPSHOT
from r7_support import evaluate, run_in_page
from run_browser_probe import ChromeSession
from run_calc_cell_native import cells_from_xml, NAMES


def pointer(session, points, shift=False):
    if isinstance(session, ChromeSession):
        start, end = points
        for kind, p in [("mouseMoved", start), ("mousePressed", start), ("mouseMoved", end), ("mouseReleased", end)]:
            session.call("Input.dispatchMouseEvent", {"type": kind, "x": p["x"], "y": p["y"],
                "button": "left", "buttons": 0 if kind == "mouseReleased" else 1,
                "clickCount": 1, "modifiers": 8 if shift else 0})
            time.sleep(.08)
    else:
        actions = [{"type": "pointerMove", "duration": 0, "origin": "viewport", "x": round(points[0]["x"]), "y": round(points[0]["y"])},
                   {"type": "pointerDown", "button": 0},
                   {"type": "pointerMove", "duration": 160, "origin": "viewport", "x": round(points[1]["x"]), "y": round(points[1]["y"])},
                   {"type": "pointerUp", "button": 0}]
        sources = [{"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": actions}]
        if shift:
            sources.append({"type": "key", "id": "keyboard", "actions": [{"type": "keyDown", "value": "\ue008"},
                {"type": "pause", "duration": 0}, {"type": "pause", "duration": 160}, {"type": "keyUp", "value": "\ue008"}]})
        session.command("POST", "/actions", {"actions": sources})


def shortcut(session, key):
    if isinstance(session, ChromeSession):
        for kind in ("keyDown", "keyUp"):
            session.call("Input.dispatchKeyEvent", {"type": kind, "key": key, "code": "Key"+key.upper(),
                "windowsVirtualKeyCode": ord(key.upper()), "modifiers": 2})
    else:
        session.command("POST", "/actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
            {"type": "keyDown", "value": "\ue009"}, {"type": "keyDown", "value": key},
            {"type": "keyUp", "value": key}, {"type": "keyUp", "value": "\ue009"}]}]})


def exercise(session, out, run):
    prefix = f"{run['browser']}-r{run['repeat']}"
    manifest = json.loads((out / "fixture/manifest.json").read_text())
    run["selectionCases"] = [c["id"] for c in manifest["selectionCases"]]

    def state(): return evaluate(session, "window.__calcEditor.state")
    def idle(): browser.wait(session, "!window.__calcEditor.state.busy")
    def check(name, passed, actual):
        run["checks"].append({"id": name, "pass": bool(passed), "actual": actual})
        if not passed: raise RuntimeError(f"{name}: {actual!r}")
    def view(name):
        snap = evaluate(session, SNAPSHOT)
        file = prefix+"-"+name+".json"
        (out / file).write_text(json.dumps(snap, ensure_ascii=False, indent=2)+"\n")
        check(name+"/tiles", snap["visibleTiles"] > 0 and bool(snap["tiles"]) and
            all(t["matched"] for t in snap["tiles"]) and snap["context"]["revision"] == snap["revision"] and snap["state"]["tileErrors"] == 0,
            {"snapshot": file, "tiles": len(snap["tiles"]), "revision": snap["revision"]})
    def geom(c, r):
        return evaluate(session, f"(async()=>{{const c=(await window.__calcEditor.session.document.readCell({c},{r})).cell;const s=document.querySelector('#surface').getBoundingClientRect();return {{cell:c,x:s.x+(c.xTwips+c.widthTwips/2)/15,y:s.y+(c.yTwips+c.heightTwips/2)/15}};}})()")
    def range_ok(a, b):
        s = state(); sel = s["selection"]
        wanted = [min(a["column"],b["column"]), min(a["row"],b["row"]), max(a["endColumn"],b["endColumn"]), max(a["endRow"],b["endRow"])]
        actual = [sel[k] for k in ("column","row","endColumn","endRow")]
        overlay = evaluate(session, "(()=>{const n=document.querySelector('#selection');return ['left','top','width','height'].map(k=>parseFloat(n.style[k])*15);})()")
        coords = [min(a["xTwips"],b["xTwips"]), min(a["yTwips"],b["yTwips"]),
            max(a["xTwips"]+a["widthTwips"],b["xTwips"]+b["widthTwips"])-min(a["xTwips"],b["xTwips"]),
            max(a["yTwips"]+a["heightTwips"],b["yTwips"]+b["heightTwips"])-min(a["yTwips"],b["yTwips"])]
        return (actual == wanted and s["cell"]["column"] == a["column"] and s["cell"]["row"] == a["row"]
            and all(abs(x-y)<.02 for x,y in zip(overlay,coords))), {"selection":sel,"active":s["cell"],"overlay":overlay,"expected":wanted,"engineEnvelope":coords}

    browser.wait(session, "document.querySelectorAll('#tiles canvas').length > 0")
    run_in_page(session, INSTRUMENT)
    run_in_page(session, "(()=>{const d=window.__calcEditor.session.document;window.__selectionCalls=0;for(const k of ['readCell','hitCell']){const f=d[k].bind(d);d[k]=(...a)=>{window.__selectionCalls++;return f(...a);};}})();")
    browser.select(session, "B2")
    original = state(); press(session, "F2")
    check("entry/F2-text", state()["editing"] == "inline" and state()["draft"] == "格式測試", state())
    insert(session, "!"); press(session, "Escape")
    check("entry/Escape-no-mutation", state()["revision"] == original["revision"] and state()["draft"] == "格式測試", state())
    insert(session, "replacement 中文"); press(session, "Enter"); idle()
    check("entry/replacement", state()["cell"]["input"] == "replacement 中文", state())
    view("replacement")
    browser.select(session, "C1"); press(session, "F2")
    check("entry/F2-formula", state()["draft"] == "=B1*2", state())
    press(session, "Escape"); insert(session, "'=B1*9"); press(session, "Enter"); idle()
    check("entry/literal", state()["cell"]["cellType"] == 2 and state()["cell"]["text"] == "=B1*9", state())
    browser.select(session, "G2")
    if isinstance(session, ChromeSession):
        session.call("Input.imeSetComposition", {"text":"組字", "selectionStart":2, "selectionEnd":2})
        rev = state()["revision"]; press(session, "Enter")
        check("entry/IME-Enter-held", state()["revision"] == rev and state()["editing"] == "inline", state())
        session.call("Input.insertText", {"text":"組字完成"})
        run["imePath"] = "trusted CDP preedit and commit; not an OS input-method claim"
    else:
        run_in_page(session, "(()=>{const n=document.activeElement;n.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true}));n.value='組字完成';n.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertCompositionText',data:'組字完成',isComposing:true}));})();")
        rev = state()["revision"]; press(session, "Enter")
        check("entry/IME-Enter-held", state()["revision"] == rev and state()["editing"] == "inline", state())
        run_in_page(session, "document.activeElement.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true,data:'組字完成'}));")
        run["imePath"] = "synthetic composition lifecycle guard plus trusted Enter; not OS/Firefox preedit proof"
    press(session, "Enter"); idle()
    check("entry/IME-commit", state()["cell"]["input"] == "組字完成", state())
    browser.type_text(session, "#formula-input", "formula field");
    check("entry/formula-focus-isolated", state()["editing"] == "formula" and state()["draft"] == "formula field", state())
    press(session, "Escape")
    browser.select(session, "A1")

    for case in manifest["selectionCases"]:
        start, end = geom(*case["from"]), geom(*case["to"])
        run_in_page(session,"window.__selectionCalls=0;")
        pointer(session, [start,end]);idle();time.sleep(.1)
        ok, actual = range_ok(start["cell"],end["cell"])
        check("range/"+case["id"], ok, actual)
        count=evaluate(session,"window.__selectionCalls")
        check("bounded/"+case["id"],count<=2,{"calls":count,"selection":state()["selection"]})
    (out / (prefix+"-range.png")).write_bytes(session.screenshot())

    browser.select(session,"B2");a=geom(1,1);b=geom(2,1)
    press(session,"ArrowRight",True);idle()
    ok,actual=range_ok(a["cell"],b["cell"]);check("range/shift-right",ok,actual)
    rev=state()["revision"]
    for fmt,key in [("bold","b"),("italic","i"),("underline","u")]:
        check("range/toolbar-disabled/"+fmt,evaluate(session,f"document.querySelector('[data-format={fmt}]').disabled"),state()["selection"])
        shortcut(session,key);idle()
        refusal=evaluate(session,f"window.__calcEditor.session.setFormat('{fmt}',true).then(()=>null,e=>e.code)")
        check("range/refuses/"+fmt,refusal=="RANGE_FORMAT_UNSUPPORTED" and state()["revision"]==rev,{"code":refusal,"revision":state()["revision"]})
    press(session,"ArrowLeft",True);idle()
    check("range/shrink-to-anchor",not state()["selection"]["multiple"] and state()["cell"]["column"]==1,state()["selection"])
    for key in ("ArrowLeft","ArrowUp","ArrowDown"):
        browser.select(session,"B2");press(session,key,True);idle()
        check("range/"+key,state()["selection"]["multiple"] and state()["cell"]["column"]==1 and state()["cell"]["row"]==1,state()["selection"])
    browser.select(session,"C1");press(session,"ArrowRight");idle()
    check("range/skip-hidden-columns",state()["cell"]["column"]==6 and not state()["selection"]["multiple"],state()["selection"])
    browser.select(session,"C3");press(session,"ArrowDown");idle()
    check("range/skip-hidden-rows",state()["cell"]["row"]==6,state()["selection"])
    browser.select(session,"A1");p=geom(2,1);pointer(session,[p,p],True);idle()
    check("range/shift-click",state()["selection"]["multiple"] and state()["cell"]["column"]==0,state()["selection"])
    # A delayed old gesture is invalidated when a newer pointerdown arrives.
    run_in_page(session,"(()=>{const d=window.__calcEditor.session.document;d.__hit=d.hitCell;d.hitCell=async(...a)=>{const r=await d.__hit(...a);await new Promise(resolve=>setTimeout(resolve,400));return r;};})();")
    a,b,c=geom(0,0),geom(2,1),geom(1,1)
    pointer(session,[a,b]);pointer(session,[c,a]);idle();time.sleep(.6);idle()
    ok,actual=range_ok(c["cell"],a["cell"]);check("race/reversed-gestures",ok,actual)
    # Cancel lifecycle: a synthetic cancellation exercises the browser event
    # handler while real pointer/hit work is outstanding (not device proof).
    before=state()["selection"]
    if isinstance(session,ChromeSession):
        session.call("Input.dispatchMouseEvent",{"type":"mousePressed","x":b['x'],"y":b['y'],"button":"left","clickCount":1})
        run_in_page(session,"document.querySelector('#viewport').dispatchEvent(new PointerEvent('pointercancel',{bubbles:true}));")
        session.call("Input.dispatchMouseEvent",{"type":"mouseReleased","x":b['x'],"y":b['y'],"button":"left","clickCount":1})
    else:
        session.command('POST','/actions',{'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[
            {'type':'pointerMove','duration':0,'origin':'viewport','x':round(b['x']),'y':round(b['y'])},{'type':'pointerDown','button':0}]}]})
        run_in_page(session,"document.querySelector('#viewport').dispatchEvent(new PointerEvent('pointercancel',{bubbles:true}));")
        session.command('DELETE','/actions')
    idle();time.sleep(.5)
    check("race/cancelled-gesture",state()["selection"]==before,state()["selection"])
    run_in_page(session,"(()=>{const d=window.__calcEditor.session.document;d.hitCell=d.__hit;delete d.__hit;})();")
    browser.select(session,"A1");p=geom(2,1);pointer(session,[p,p],True);idle()
    press(session,"F2")
    check("range/F2-collapses-active",not state()["selection"]["multiple"] and state()["draft"]=="原始中文 Alpha",state())
    press(session,"Escape")
    browser.select(session,"A1");press(session,"ArrowRight",True);idle();insert(session,"active replacement")
    check("range/typing-collapses-active",not state()["selection"]["multiple"] and state()["cell"]["column"]==0 and state()["draft"]=="active replacement",state())
    press(session,"Enter");idle();view("range-active-input")
    session.click('[data-part="1"]');idle()
    check("range/sheet-reset",not state()["selection"]["multiple"] and state()["cell"]["input"]=="第二表不應改動",state())
    session.click('[data-part="2"]');idle()
    check("entry/protected-disabled",evaluate(session,"document.querySelector('#cell-editor').disabled && document.querySelector('#formula-input').disabled"),state())
    press(session,"F2");insert(session,"must not write");
    check("entry/protected-preserved",state()["cell"]["input"]=="鎖定內容" and not state()["editing"],state())
    session.click('[data-part="0"]');idle()
    session.click('#save-button');browser.wait(session,"Boolean(window.__calcEditor.lastExport) && !window.__calcEditor.state.saving")
    downloaded=Path(run["downloadDirectory"])/"cell-editing.ods"
    deadline=time.monotonic()+30
    while not downloaded.is_file() and time.monotonic()<deadline:time.sleep(.1)
    saved=out/(prefix+"-saved.ods");saved.write_bytes(downloaded.read_bytes())
    content,cells=cells_from_xml(saved)
    def text_at(part,col,row): return ''.join(cells[(part,col,row)].itertext())
    check("save/XML-values",text_at(0,0,0)=="active replacement" and text_at(0,1,1)=="replacement 中文" and text_at(0,2,0)=="=B1*9" and text_at(0,6,1)=="組字完成",{"file":saved.name})
    check("save/XML-preserved",text_at(0,0,1)=="鄰格必須保留" and text_at(1,0,0)=="第二表不應改動",{"file":saved.name})
    session.set_file('#file-input',saved)
    browser.wait(session,f"window.__calcEditor.state?.fileName === {json.dumps(saved.name)} && Boolean(window.__calcEditor.state.cell)")
    for address,text in [("A1","active replacement"),("B2","replacement 中文"),("C1","'=B1*9"),("G2","組字完成")]:
        browser.select(session,address);check("save/reopen/"+address,state()["cell"]["input"]==text,state()["cell"])
    (out/(prefix+"-reopened.png")).write_bytes(session.screenshot())
    evaluate(session,"window.__calcEditor.openBytes(window.__calcEditor.lastExport,'readonly.ods',{readOnly:true})")
    p=geom(0,0);pointer(session,[p,p]);idle();press(session,"F2");insert(session,"forbidden")
    check("entry/readonly-preserved",not state()["editing"] and state()["cell"]["input"]=="active replacement" and not state()["dirty"],state())


if __name__ == "__main__":
    browser.exercise=exercise
    browser.create=create
    raise SystemExit(browser.main())
