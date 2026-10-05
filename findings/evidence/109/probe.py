"""Finding 109 repro (scratch): a delete at a paragraph boundary on the M3 host."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
from check_m3_skeleton_open import (DEFAULT_DDEV, EventChrome, Instance, POINT_AT, PRESS, READ_STATE,
                                    browser_login, evaluate, navigate, wait_until, product_state, state_until)
OUT = Path(sys.argv[1])
ARM, FILEID = sys.argv[2], sys.argv[3]
inst = Instance(DEFAULT_DDEV)
s = EventChrome("cold")
rec = {"arm": ARM, "fileId": FILEID, "version": s.version, "steps": []}
def shot(name):
    import base64
    (OUT / f"{ARM}-{name}.png").write_bytes(s.screenshot())
def key(k, code, vk, text=None):
    for kind in (("rawKeyDown", "char", "keyUp") if text else ("rawKeyDown", "keyUp")):
        p = {"type": kind, "key": k, "code": code, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}
        if kind == "char": p["text"] = text
        s.call("Input.dispatchKeyEvent", p)
def step(name, **extra):
    st = product_state(s); st["disabled"] = [b["action"] for b in st.pop("buttons", []) or [] if b.get("disabled")]
    rec["steps"].append({"step": name, **extra, "state": st}); print(name, json.dumps(st, ensure_ascii=False)[:300], flush=True)
    return st
try:
    s.call("Emulation.setDeviceMetricsOverride", {"width": 1850, "height": 980, "deviceScaleFactor": 1, "mobile": False})
    rec["login"] = browser_login(s, inst.base, inst.password)
    navigate(s, f"{inst.base}/index.php/apps/litecore/r/e2-editor.html?fileId={FILEID}", timeout=120)
    raw = wait_until(s, "(() => { const v = document.documentElement.getAttribute('data-litecore'); return v && JSON.parse(v).done && v; })()", 400)
    rec["host"] = json.loads(raw) if isinstance(raw, str) else raw
    step("opened")
    rec["canvas"] = evaluate(s, "(() => { const b = document.querySelector('#canvas').getBoundingClientRect(); return {x: b.x, y: b.y, w: b.width, h: b.height, sx: scrollX, sy: scrollY}; })()")
    rec["css"] = evaluate(s, """(() => { const b = getComputedStyle(document.body); const h = document.querySelector('header, #header');
      const hs = h ? getComputedStyle(h) : null;
      return {bodyBg: b.backgroundColor, bodyBgImage: b.backgroundImage.slice(0, 120), bodyDisplay: b.display,
              header: h ? {bg: hs.backgroundColor, bgImage: hs.backgroundImage.slice(0, 80), height: h.getBoundingClientRect().height} : null,
              ncPrimary: getComputedStyle(document.documentElement).getPropertyValue('--color-primary'),
              ncBackground: getComputedStyle(document.documentElement).getPropertyValue('--color-main-background')}; })()""")
    shot("opened")
    if ARM == "calibrate":
        pass
    else:
        plan = json.loads(sys.argv[4])
        for item in plan:
            kind = item[0]
            if kind == "click":
                evaluate(s, POINT_AT.replace("ARG_X", str(item[1])).replace("ARG_Y", str(item[2])))
                time.sleep(2.5); step(f"click {item[1]},{item[2]}")
            elif kind == "type":
                for ch in item[1]:
                    key(ch, f"Key{ch.upper()}", ord(ch.upper()), ch); time.sleep(0.4)
                time.sleep(2.5); step(f"type {item[1]}")
            elif kind == "key":
                key(item[1], item[2], item[3]); time.sleep(4); step(f"key {item[1]}")
            elif kind == "press":
                evaluate(s, PRESS.replace("ARG_ACTION", item[1])); time.sleep(4); step(f"press {item[1]}")
            elif kind == "wait":
                st = state_until(s, lambda x: x.get("state") in ("restart-required", "recoverable-error", "ready") and x.get("pending") in ("0", 0), item[1]); step("settled")
            shot(f"{len(rec['steps']):02d}")
        rec["notice"] = evaluate(s, "(() => document.querySelector('#notice')?.innerText)()")
        rec["projection"] = evaluate(s, "(() => [...document.querySelectorAll('.a11y-only, [aria-live]')].map(e => e.innerText).filter(Boolean).slice(0, 4))()")
except Exception:
    import traceback; rec["fatal"] = traceback.format_exc(); print(rec["fatal"])
finally:
    (OUT / f"{ARM}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    s.close()
