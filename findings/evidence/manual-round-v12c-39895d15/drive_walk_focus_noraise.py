# ARM A0, SETTING Y. Exactly one change from drive_walk_focus.py (sha256
# 414f1245c8fd02056e52906d420c6e58bbe2046897749aa273282f7371f29813): the call
# to raise_window() at the foot of that file's line 57 is commented out below.
# The function definition is left in place so the diff is one line. This file
# exists to remove a confound named in
# handoff/tasks/TASK-2026-09-06-4b-instrument-reproduction.md section 3.1 --
# it is a control, not new machinery, and no other line differs.
"""4b by arrow keys, take two.

Take one failed for two procedural reasons, both mine and both recorded:

  * the initial click used 5% of the canvas height and landed above the text,
    so the caret never entered the document and Orca browsed the toolbar
    instead. Placement now goes through `LINE_INK` + `place_caret_and_settle`,
    the method that has worked every other time in this tree.
  * ArrowDown moves the caret WITHIN a paragraph -- these paragraphs wrap --
    so eleven presses crossed one paragraph boundary. The walk now presses
    until the pointer actually CHANGES, which is what "arrow through the
    document" means when lines and paragraphs are not the same thing.
"""
import json, subprocess, sys, time, urllib.request
from pathlib import Path
import websockets.sync.client as wsc
PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))
import run_e2_c_product_path as P
from run_browser_probe import ChromeSession

tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9341/json/list", timeout=5))
page = next(t for t in tabs if t.get("type") == "page")
ws = wsc.connect(page["webSocketDebuggerUrl"], max_size=None)
_id = [0]
class S(ChromeSession):
    def __init__(self):
        self.process = None

    def call(self, m, p=None):
        _id[0] += 1
        ws.send(json.dumps({"id": _id[0], "method": m, "params": p or {}}))
        while True:
            r = json.loads(ws.recv(timeout=90))
            if r.get("id") == _id[0]: return r.get("result", {})
    def evaluate(self, e):
        r = self.call("Runtime.evaluate", {"expression": e, "returnByValue": True,
                                           "awaitPromise": True}).get("result", {})
        if r.get("subtype") == "error": raise RuntimeError(r)
        return r.get("value")
s = S()
def ev(e): return s.evaluate(e)

# RAISE THE WINDOW, and keep raising it.
#
# Measured 2026-09-06: a walk ran to completion while Orca narrated a DIFFERENT
# application entirely (a company-registry page in another window). The keys
# reached the right tab -- CDP does not need OS focus -- but a screen reader
# follows the focused WINDOW, so the log was about something else. `hasFocus`
# now records it per stop, and this raises the window so it is true.
def raise_window():
    try:
        s.call("Page.bringToFront")
    except Exception:
        pass

# raise_window()  # ARM A0 SETTING Y: this call is the single difference from drive_walk_focus.py.
ev(P.INSTALL)
P.wait_for(s, lambda st: st.get("state") == "ready", 300)
ev("""(() => { const el = document.querySelector('#fixture');
  el.value = 'a11y-audible';
  el.dispatchEvent(new Event('change', {bubbles: true})); return true; })()""")
P.wait_for(s, lambda st: "a11y-audible" in (st.get("doc") or ""), 300)
time.sleep(4)

# PLACE THE CARET ON REAL INK, the method that works.
placed = False
for i in range(2, 40):
    frac = f"{i * 0.02:.3f}"
    ink = ev(P.LINE_INK.replace("ARG_Y", frac)) or {}
    if not ink.get("available"): continue
    P.place_caret_and_settle(s, P.POINT_AT, P.caret_click_fractions(ink)["near"], frac)
    time.sleep(1.5)
    # WAIT ON THE POINTER, NOT ON THE LIVE REGION.
    #
    # Measured 2026-09-05: the live region carries NO TEXT while the caret is
    # on a heading -- `#a11y-para` is empty on the first heading and stale on
    # the second, while `aria-activedescendant` is correct on both. A
    # precondition that waited for the heading's text in the live region
    # therefore waited for something this page does not do, and reported "the
    # caret never reached the first heading" about a caret that was on it.
    ref = ev("(() => { const s=document.querySelector('#sink');"
             " return s.getAttribute('aria-activedescendant'); })()")
    if ref == "a11y-node-0":
        placed = {"yFraction": frac, "ref": ref,
                  "liveRegionAtTheHeading": ev(
                      "(() => { const e=document.querySelector('#a11y-para');"
                      " return e ? e.textContent : null; })()")}
        break
if not placed:
    print(json.dumps({"error": "caret never reached the first heading"},
                     ensure_ascii=False)); ws.close(); raise SystemExit(1)

def state():
    return json.loads(ev("""(() => {
      const sink = document.querySelector('#sink');
      const id = sink.getAttribute('aria-activedescendant');
      const el = id ? document.getElementById(id) : null;
      const live = document.querySelector('#a11y-para');
      return JSON.stringify({ ref: id, hasFocus: document.hasFocus(),
        role: el ? el.getAttribute('role') : null,
        level: el ? el.getAttribute('aria-level') : null,
        node: el ? (el.textContent||'').slice(0,34) : null,
        live: live ? (live.textContent||'').slice(0,34) : null });
    })()"""))

rows = [dict(state(), step=0)]
time.sleep(5)
presses = 0
while len(rows) < 10 and presses < 90:
    # RAISED ONCE, AT THE START, NOT HERE. Measured 2026-09-06: raising the
    # window before every press left Orca announcing 1 paragraph out of 10 with
    # `hasFocus` true at every stop -- the repeated activation is itself an
    # event, and it suppressed what it was added to protect. Keeping the
    # per-stop `hasFocus` reading is enough: it says whether the run is usable
    # instead of forcing a condition that changes what is measured.
    for t in ("rawKeyDown", "keyUp"):
        s.call("Input.dispatchKeyEvent", {"type": t, "windowsVirtualKeyCode": 40,
                                          "nativeVirtualKeyCode": 40,
                                          "key": "ArrowDown", "code": "ArrowDown"})
    presses += 1
    time.sleep(0.8)
    now = state()
    if now["ref"] != rows[-1]["ref"]:
        rows.append(dict(now, step=presses))
        time.sleep(11)         # 5s did not fit "List with N items" + the item text
ws.close()
lost = [r for r in rows if r.get("hasFocus") is not True]
print(json.dumps({
    "placed": placed, "presses": presses, "rows": rows,
    # WHY THIS FIELD EXISTS. On 2026-09-06 two walks were compared and BOTH had
    # lost window focus to the terminal driving them -- one silently, at
    # paragraph 4. The comparison could not mean anything, and nothing in the
    # record said so; it had to be read out of Orca announcing the terminal's
    # title. A stop taken while `document.hasFocus()` is false is not a
    # measurement of what a screen reader would say, so the run now states it.
    "focusHeldEveryStop": not lost,
    "stopsWithoutFocus": [r["ref"] for r in lost],
}, ensure_ascii=False, indent=1))
