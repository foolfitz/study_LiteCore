#!/usr/bin/env python3
"""Actual Files range formatting/autosave on exclusively runner-owned fixtures.

No service lifecycle commands or global lock mutations. Run only after the
guarded candidate install and fresh external preservation snapshots.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from run_calc_editor_host import Harness, ODS, OBSERVE
from check_m3_host_entry import host_record
from probe_calc_input_range import insert, press
from probe_calc_format_view import INSTRUMENT, SNAPSHOT
from probe_m3_gate0_coep import browser_login
from r7_support import evaluate, run_in_page
from run_calc_editor_browser import select, wait
from run_calc_cell_native import cells_from_xml, NAMES
from v21_shakedown_common import browser_lock, close_browser

FORMATS = ("bold", "italic", "underline")
TOOLS = Path(__file__).resolve().parent


def ods_snapshot(path):
    from ods_cell_attributes import effective_attributes
    _, cells = cells_from_xml(path)
    addresses = {"target": (0, 1, 1), "rangeNeighbor": (0, 2, 1), "outside": (0, 0, 1), "otherSheet": (1, 0, 0)}
    result = {}
    for name, address in addresses.items():
        text = "".join(cells[address].itertext())
        attrs = effective_attributes(path, *address)
        result[name] = {"text": text, "attributes": attrs}
    return result


def formats_on(attrs):
    wanted = {f"{{{NAMES['f']}}}font-weight": "bold", f"{{{NAMES['s']}}}font-weight-asian": "bold",
              f"{{{NAMES['s']}}}font-weight-complex": "bold", f"{{{NAMES['f']}}}font-style": "italic",
              f"{{{NAMES['s']}}}font-style-asian": "italic", f"{{{NAMES['s']}}}font-style-complex": "italic",
              f"{{{NAMES['s']}}}text-underline-style": "solid"}
    return all(attrs.get(key) == value for key, value in wanted.items())


def formats_off(attrs):
    return all(attrs.get(f"{{{namespace}}}{name}") not in ("bold", "italic", "solid")
        for namespace, name in [(NAMES['f'], "font-weight"), (NAMES['s'], "font-weight-asian"),
            (NAMES['s'], "font-weight-complex"), (NAMES['f'], "font-style"),
            (NAMES['s'], "font-style-asian"), (NAMES['s'], "font-style-complex"),
            (NAMES['s'], "text-underline-style")])


def snapshot_matches(snapshot, browser, phase):
    marker = ("Host autosave " if phase == "idle" else "Host export snapshot ") + browser
    return (snapshot["target"]["text"] == marker and formats_on(snapshot["target"]["attributes"])
        and snapshot["rangeNeighbor"]["text"] == "待清除" and formats_on(snapshot["rangeNeighbor"]["attributes"])
        and snapshot["outside"]["text"] == "鄰格必須保留" and formats_off(snapshot["outside"]["attributes"])
        and snapshot["otherSheet"]["text"] == "第二表不應改動" and formats_off(snapshot["otherSheet"]["attributes"]))


class Focused(Harness):
    def __init__(self, out, scratch, build_id):
        super().__init__(out, scratch, kind="both")
        self.build_id = build_id
        self.report.update(expectedBuildId=build_id,
            toolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            dependencySha256={name: hashlib.sha256((TOOLS/name).read_bytes()).hexdigest()
                for name in ("run_calc_editor_host.py", "ods_cell_attributes.py")})

    def admin_round(self, browser):
        run = {"browser": browser, "kind": "admin", "serverSnapshots": []}
        self.report["runs"].append(run)
        session = self.browser(browser, "range-autosave-admin")
        run["version"] = session.version
        name = self.folder + "/" + browser + ".ods"
        self.paths.append(name)
        def state(): return evaluate(session, "window.__calcEditor.state")
        def idle(): wait(session, "!window.__calcEditor.state.busy && !window.__calcEditor.state.selectionPending")
        def saves(): return host_record(session).get("saves", [])
        def settled(count):
            wait(session, f"(()=>{{const h=JSON.parse(document.documentElement.getAttribute('data-litecore'));return h.saves.length==={count} && h.saves[{count-1}].settled;}})()", 55)
            idle()
            return saves()[-1]
        def server_file(phase):
            code, body, headers = self.dav("GET", name)
            path = self.out / (browser + "-" + phase + "-server.ods")
            path.write_bytes(body)
            record = {"phase": phase, "file": path.name, "status": code,
                "sha256": hashlib.sha256(body).hexdigest(), "contentType": headers.get("Content-Type")}
            run["serverSnapshots"].append(record)
            return code, path, ods_snapshot(path)
        try:
            self.check(browser+"/upload", self.dav("PUT", name, self.fixture.read_bytes(), {"Content-Type": ODS})[0] in (200,201,204), name)
            browser_login(session, self.instance.base, self.instance.password)
            run["entry"] = self.open_file(session, name, "ods-editor.html")
            self.ready_calc(session)
            evaluate(session, "window.__calcEditor.ready")
            self.check(browser+"/candidate", "/"+self.build_id+"-" in run["entry"]["landed"] and state()["rangeFormattingSupported"] is True, run["entry"])
            props = self.props(name)
            self.check(browser+"/own-lock", props["lock"] == "1" and bool(props["token"]), {k:v for k,v in props.items() if k!="token"})
            run_in_page(session, OBSERVE)
            run_in_page(session, INSTRUMENT)
            for fmt in FORMATS:
                select(session, "B2")
                session.click(f"[data-format={fmt}]");idle()
                select(session, "B2")
                press(session, "ArrowRight", True);idle()
                self.check(browser+"/mixed/"+fmt, state()["rangeFormat"][fmt] is None
                    and evaluate(session, f"document.querySelector('[data-format={fmt}]').getAttribute('aria-pressed')") == "mixed", state()["rangeFormat"])
                before = state()["revision"]
                session.click(f"[data-format={fmt}]");idle()
                self.check(browser+"/range-on/"+fmt, state()["rangeFormat"][fmt] is True
                    and state()["revision"] == before+1 and state()["selection"]["column"] == 1
                    and state()["selection"]["endColumn"] == 2 and state()["cell"]["column"] == 1, state())
                session.click(f"[data-format={fmt}]");idle()
                self.check(browser+"/range-off/"+fmt, state()["rangeFormat"][fmt] is False, state()["rangeFormat"])
                session.click(f"[data-format={fmt}]");idle()
            snapshot = evaluate(session, SNAPSHOT)
            tile_file = self.out / (browser+"-range-tiles.json")
            tile_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n")
            self.check(browser+"/tiles", snapshot["visibleTiles"] > 0 and bool(snapshot["tiles"])
                and all(t["matched"] for t in snapshot["tiles"]) and snapshot["revision"] == snapshot["context"]["revision"], {"file":tile_file.name,"tiles":len(snapshot["tiles"])})
            select(session, "B2");insert(session, "Host autosave "+browser);press(session, "Enter");idle()
            count = len(saves())
            started = evaluate(session, "performance.now()")
            first = settled(count+1)
            elapsed = evaluate(session, "performance.now()") - started
            run["idleElapsedMs"] = elapsed
            self.check(browser+"/automatic-original", 29000 <= elapsed <= 55000 and first["trigger"] == "auto"
                and first["outcome"] == "saved" and first["target"] == "original"
                and not state()["dirty"] and not state()["committedDirty"], {"elapsedMs":elapsed,"save":first})
            puts = [r for r in evaluate(session,"window.__cellHostRequests") if r["method"] == "PUT"]
            self.check(browser+"/conditional-put", bool(puts) and all(r["contentType"] == ODS and bool(r["ifMatch"])
                and r["withToken"] and r.get("status") in (200,201,204) for r in puts), puts)
            code, path, xml = server_file("idle")
            self.check(browser+"/idle-server-xml", code == 200 and snapshot_matches(xml,browser,"idle"), {"file":path.name,"cells":xml})
            count = len(saves())
            insert(session, "Unconfirmed host draft "+browser)
            time.sleep(31)
            self.check(browser+"/draft-not-forced", len(saves()) == count and state()["editing"] == "inline"
                and state()["draft"] == "Unconfirmed host draft "+browser and state()["dirty"] and not state()["committedDirty"], state())
            press(session,"Escape")
            # Hold one real native export while trusted typing enters a new draft.
            run_in_page(session, "(()=>{const d=window.__calcEditor.session.document,original=d.save.bind(d);d.save=async(...a)=>{d.save=original;window.__rangeHostExportStarted=true;await new Promise(resolve=>window.__rangeHostExportRelease=resolve);return original(...a);};})();")
            insert(session,"Host export snapshot "+browser);press(session,"Enter");idle()
            count = len(saves())
            wait(session,"window.__rangeHostExportStarted===true && window.__calcEditor.state.saving",45)
            insert(session,"Typed during host export "+browser)
            run_in_page(session,"window.__rangeHostExportRelease();")
            second = settled(count+1)
            self.check(browser+"/typing-during-export", state()["editing"] == "inline"
                and state()["draft"] == "Typed during host export "+browser and state()["dirty"]
                and not state()["committedDirty"] and evaluate(session,"document.activeElement.id") == "cell-editor", state())
            self.check(browser+"/second-automatic-original", second["trigger"] == "auto" and second["outcome"] == "saved" and second["target"] == "original", second)
            code, path, xml = server_file("export")
            self.check(browser+"/export-server-xml", code == 200 and snapshot_matches(xml,browser,"export"), {"file":path.name,"cells":xml})
            press(session,"Escape");idle()
            self.check(browser+"/cancel-leaves-saved", not state()["dirty"] and not state()["committedDirty"]
                and state()["cell"]["input"] == "Host export snapshot "+browser, state())
            run["host"] = host_record(session)
            run["requests"] = evaluate(session,"window.__cellHostRequests")
            release = self.leave(session,name)
            self.check(browser+"/own-lock-released", release["lock"] != "1", release)
            run["reentry"] = self.open_file(session,name,"ods-editor.html")
            self.ready_calc(session);evaluate(session,"window.__calcEditor.ready")
            read = evaluate(session,"window.__calcEditor.session.document.readRange(1,1,2,1,{part:0})")
            cell = self.calc_read(session,"B2")
            self.check(browser+"/server-reopen", cell["input"] == "Host export snapshot "+browser
                and all(read["range"][fmt] is True for fmt in FORMATS), {"cell":cell,"range":read["range"]})
            release = self.leave(session,name)
            self.check(browser+"/reopen-lock-released", release["lock"] != "1", release)
        finally:
            # If an assertion interrupts the controlled export, unblock only it
            # so normal close and the inherited owned-token cleanup can finish.
            try: run_in_page(session,"window.__rangeHostExportRelease?.();")
            except Exception: pass
            try: (self.out/(browser+"-last.png")).write_bytes(session.screenshot())
            except Exception: pass
            run["browserClose"] = close_browser(session)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--build-id",required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    with browser_lock("calc-range-autosave-host"), tempfile.TemporaryDirectory(prefix="calc-range-autosave-host-",dir=TOOLS.parent/"build") as scratch:
        raise SystemExit(0 if Focused(args.out.resolve(),Path(scratch),args.build_id).run() else 1)
