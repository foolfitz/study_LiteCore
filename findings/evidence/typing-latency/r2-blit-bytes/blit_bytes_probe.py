#!/usr/bin/env python3
"""DIAGNOSTIC ONLY -- not the 122-B instrument; nothing here counts.  Spec SPEC-M3-production-ui §15.8 registered
R2 ("updateState() -> paint() re-blits the whole canvas on every state write, ~6 per key, both pages: measure the
bytes blitted per key, v58 against A+B, before any design") and R1 ("A' is admissible only if every invalidation
after an insert carries the post-increment revision: record document-invalidated revisions").  This runs
tools/probe_typing_latency.py (dbad93c0...) with, in memory only:

  * the probe's own per-call dataset writes coalesced into one per task (as ../diagnostic-shim-overhead/), so the
    instrument's cost does not scale with the number of putImageData calls (standing rule pp);
  * one more classic script injected BEFORE the probe's shim, so that the probe's wrapper calls ours and ours calls
    the native putImageData: per call it times only the native call and counts bytes (width x height x 4).  A call
    on an ImageData not blitted before is "fresh" (a new render), any later call on the same image is "stale" (a
    re-blit of the cached picture).  Stale calls in one task are one group (= one paint()).  On every keydown it
    snapshots the counters;
  * the served worker (mirror copy of profiles/e2-editor-v19/sdk-worker.js only; dist/ untouched) adds the LOK
    callback id and payload to each document-invalidated event, which the script records with its revision;
  * --skip-stale (what-if, added after the first eight runs): stale re-blits are counted but NOT passed to the native
    call, so the page pays nothing for paint()'s whole-canvas re-blit (the overlay is drawn over old pixels; timing
    only).  Fresh blits are always native, and each one is logged [t, dy, height, ms];
  * --dpr N (added after the what-if runs): devicePixelRatio N -- Chrome via Emulation.setDeviceMetricsOverride before
    the first navigation, Firefox via the layout.css.devPixelsPerPx pref; READ also samples, in 120-row strips at the caret line, the middle and the end of the canvas, the transparent pixels (never drawn) and the opaque ones with red < 128 (ink), so a blank
    canvas is visible (a first version counted transparent black as ink; caught on the smoke run);
  * --window WxH (added after the ratio-2 runs): a CSS viewport of W x H -- Chrome via the same Emulation call,
    Firefox via MOZ_HEADLESS_WIDTH/HEIGHT (device pixels, W x ratio by H x ratio) -- so the page's 900-px canvas
    cap is reached;
  * READ also records the opaque fraction of each of the canvas's last 120 rows (raw.ink.bottomOpaqueRows);
  * every toast text is recorded with its time in raw.r2.toasts (added while explaining the Chrome ratio-2 null);
  * --page v58 serves the v58 page (537d62d7..., bytes from git 05f46923^) from the mirror instead of dist's.

Usage: blit_bytes_probe.py --page {current,v58} [--skip-stale] [--dpr N] [--window WxH] + the probe's own arguments (--browser, --document, --gap, --chars,
--out).  The report's `runner` says what ran; its `page` is the hash of the page actually served."""
import hashlib, json, os, statistics, subprocess, sys
from pathlib import Path

ROOT = Path("/home/jiajun/LibreOffice/study_LiteCore")
TOOLS = ROOT / "wasm_sdk_probe" / "tools"
sys.path.insert(0, str(TOOLS))
import probe_typing_latency as ptl  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

BASE = hashlib.sha256((TOOLS / "probe_typing_latency.py").read_bytes()).hexdigest()
assert BASE.startswith("dbad93c0dcf27fbf"), BASE
V58_PAGE = "537d62d73b8a38d56210fc1df3bf332155b0194a1304ab6b946d657cfd53eb5d"
WORKER = "profiles/e2-editor-v19/sdk-worker.js"

skip_stale = "--skip-stale" in sys.argv
if skip_stale:
    sys.argv.remove("--skip-stale")
dpr = None
if "--dpr" in sys.argv:
    i = sys.argv.index("--dpr")
    dpr = float(sys.argv[i + 1])
    del sys.argv[i:i + 2]
window = None
if "--window" in sys.argv:
    i = sys.argv.index("--window")
    window = tuple(int(v) for v in sys.argv[i + 1].split("x"))
    del sys.argv[i:i + 2]
page_choice = "current"
if "--page" in sys.argv:
    i = sys.argv.index("--page")
    page_choice = sys.argv[i + 1]
    del sys.argv[i:i + 2]
assert page_choice in ("current", "v58"), page_choice

# 1. The probe's dataset writes, coalesced (identical to ../diagnostic-shim-overhead/lazy_shim_probe.py).
s = ptl.PAINT_SHIM
for old, new in [
    ("  const stale = [], blits = [];\n",
     "  const stale = [], blits = [];\n  let flushPending = false;\n"
     "  const flush = () => { flushPending = false; root.dataset.blits = JSON.stringify(blits.slice(-600));\n"
     "                        root.dataset.paints = JSON.stringify(stale.slice(-400)); };\n"
     "  const later = () => { if (!flushPending) { flushPending = true; setTimeout(flush, 0); } };\n"),
    ("      root.dataset.blits = JSON.stringify(blits.slice(-600));\n", "      later();\n"),
    ("      root.dataset.paints = JSON.stringify(stale.slice(-400));\n", "      later();\n"),
]:
    assert s.count(old) == 1, old
    s = s.replace(old, new)

# 2. Our accounting, installed first so it sits between the probe's wrapper and the native call.
R2_SHIM = """<script>
(() => {
  const root = document.documentElement;
  const st = { c: { staleCalls: 0, staleBytes: 0, staleMs: 0, freshCalls: 0, freshBytes: 0, freshMs: 0, groups: 0 },
               keys: [], groups: [], inval: [], fresh: [], dirty: false };
  const SKIP_STALE = __SKIP_STALE__;
  const seen = new WeakSet();
  let group = null;
  const snap = () => Object.assign({}, st.c, { staleMs: Math.round(st.c.staleMs * 100) / 100,
                                               freshMs: Math.round(st.c.freshMs * 100) / 100 });
  setInterval(() => { if (st.dirty) { st.dirty = false; st.final = snap(); root.dataset.r2 = JSON.stringify(st); } }, 200);
  const proto = CanvasRenderingContext2D.prototype, native = proto.putImageData;
  proto.putImageData = function (image, dx, dy, ...rest) {
    const isFresh = !seen.has(image);
    const t0 = performance.now();
    const out = (isFresh || !SKIP_STALE) ? native.call(this, image, dx, dy, ...rest) : undefined;
    const dt = performance.now() - t0;
    const bytes = image.width * image.height * 4;
    if (isFresh) {
      seen.add(image);
      st.c.freshCalls += 1; st.c.freshBytes += bytes; st.c.freshMs += dt;
      st.fresh.push([Math.round(t0 * 10) / 10, dy, image.height, Math.round(dt * 100) / 100]);
      if (st.fresh.length > 4000) st.fresh.splice(0, 1000);
    } else {
      st.c.staleCalls += 1; st.c.staleBytes += bytes; st.c.staleMs += dt;
      if (!group) {
        group = { t: Math.round(t0 * 10) / 10, calls: 0, bytes: 0, ms: 0, end: 0 };
        st.c.groups += 1;
        queueMicrotask(() => { group.end = Math.round(performance.now() * 10) / 10;
                               group.ms = Math.round(group.ms * 100) / 100;
                               st.groups.push(group); if (st.groups.length > 3000) st.groups.splice(0, 1000);
                               group = null; st.dirty = true; });
      }
      group.calls += 1; group.bytes += bytes; group.ms += dt;
    }
    st.dirty = true;
    return out;
  };
  document.addEventListener('keydown', (e) => {
    st.keys.push([e.key, Math.round(performance.now() * 10) / 10, snap()]); st.dirty = true; }, true);
  const NativeWorker = window.Worker;
  st.toasts = [];
  document.addEventListener('DOMContentLoaded', () => {
    const t = document.querySelector('#toast');
    if (t) new MutationObserver(() => { if (t.textContent) { st.toasts.push([Math.round(performance.now() * 10) / 10, t.textContent.slice(0, 120)]);
      if (st.toasts.length > 500) st.toasts.splice(0, 100); st.dirty = true; } })
      .observe(t, { childList: true, characterData: true, subtree: true });
  });
  window.Worker = class extends NativeWorker {
    constructor(...args) {
      super(...args);
      this.addEventListener("message", (e) => {
        const d = e.data;
        if (d && d.kind === "event" && d.event === "document-invalidated") {
          st.inval.push([Math.round(performance.now() * 10) / 10, d.revision, d.diagLokId ?? null,
                         typeof d.diagPayload === "string" ? d.diagPayload.slice(0, 80) : null]);
          if (st.inval.length > 4000) st.inval.splice(0, 1000);
          st.dirty = true;
        }
      });
    }
  };
})();
</script>"""
ptl.PAINT_SHIM = R2_SHIM.replace("__SKIP_STALE__", "true" if skip_stale else "false") + s

old_read = "blits: JSON.parse(d.blits || '[]'), canvasHeight: c ? c.height : null }; })()"
assert ptl.READ.count(old_read) == 1
ptl.READ = ptl.READ.replace(
    old_read, "blits: JSON.parse(d.blits || '[]'), canvasHeight: c ? c.height : null,\n"
              "           canvasWidth: c ? c.width : null, r2: JSON.parse(d.r2 || 'null'), dpr: window.devicePixelRatio,\n"
              "           ink: (() => { const out = {}; try { const x = c.getContext('2d');\n"
              "             for (const [name, f] of [['caretLine', 0.010373], ['middle', 0.5], ['end', 0.98]]) {\n"
              "               const y = Math.max(0, Math.min(c.height - 120, Math.round(c.height * f) - 60));\n"
              "               const px = x.getImageData(0, y, c.width, 120).data; let ink = 0, clear = 0;\n"
              "               for (let i = 0; i < px.length; i += 4) { if (px[i + 3] === 0) clear += 1;\n"
              "                 else if (px[i] < 128) ink += 1; }\n"
              "               out[name] = { ink, transparent: clear, pixels: px.length / 4 }; }\n"
              "             const n = Math.min(120, c.height); const bp = x.getImageData(0, c.height - n, c.width, n).data;\n"
              "             out.bottomOpaqueRows = []; for (let r = 0; r < n; r++) { let o = 0;\n"
              "               for (let i = r * c.width * 4 + 3; i < (r + 1) * c.width * 4; i += 4) if (bp[i] > 128) o += 1;\n"
              "               out.bottomOpaqueRows.push(Math.round(o / c.width * 100) / 100); } } catch (e) { out.error = String(e && e.message || e); } return out; })() }; })()")

# 3. The mirror: worker always patched; the page only for --page v58.
worker_src = (ROOT / "wasm_sdk_probe" / "dist" / WORKER).read_text(encoding="utf-8")
old_ev = ('        postEvent("document-invalidated", {\n'
          '          documentHandle: event.documentHandle,\n'
          '          revision: event.revision,\n')
assert worker_src.count(old_ev) == 1
worker_patched = worker_src.replace(old_ev, old_ev + "          diagLokId: event.id,\n          diagPayload: event.payload,\n")
overrides = {WORKER: worker_patched.encode("utf-8")}
if page_choice == "v58":
    v58 = subprocess.run(["git", "-C", str(ROOT), "show", "05f46923^:wasm_sdk_probe/web/e2-editor-app.js"],
                         check=True, capture_output=True).stdout
    assert hashlib.sha256(v58).hexdigest() == V58_PAGE
    overrides["e2-editor-app.js"] = v58
served_page = (overrides.get("e2-editor-app.js")
               or (ROOT / "wasm_sdk_probe" / "dist" / "e2-editor-app.js").read_bytes())
native_build_mirror = pp.build_mirror
if dpr or window:
    dpr = dpr or 1.0
    native_navigate, NativeFirefox = pp.navigate, pp.FirefoxSession
    if window:  # headless Firefox sizes its screen from these, in device pixels
        os.environ["MOZ_HEADLESS_WIDTH"] = str(round(window[0] * dpr))
        os.environ["MOZ_HEADLESS_HEIGHT"] = str(round(window[1] * dpr))

    def navigate_at_dpr(session, *args, **kwargs):
        if isinstance(session, pp.ChromeSession) and not getattr(session, "_r2_dpr", False):
            session.call("Emulation.setDeviceMetricsOverride",
                         {"width": window[0] if window else 0, "height": window[1] if window else 0,
                          "deviceScaleFactor": dpr, "mobile": False})
            session._r2_dpr = True
        return native_navigate(session, *args, **kwargs)
    pp.navigate = navigate_at_dpr
    pp.FirefoxSession = lambda mode: NativeFirefox(mode, extra_prefs={"layout.css.devPixelsPerPx": str(dpr)})
pp.build_mirror = lambda source, target, extra: native_build_mirror(source, target, {**extra, **overrides})


def per_key(report):
    raw = report.get("raw") or {}
    r2 = raw.get("r2") or {}
    width, height = raw.get("canvasWidth") or 0, raw.get("canvasHeight") or 0
    canvas = width * height * 4
    letters = [k for k in r2.get("keys", []) if len(k[0]) == 1]
    final = r2.get("final")
    out = []
    for i, (key, t, c) in enumerate(letters):
        nxt = letters[i + 1][2] if i + 1 < len(letters) else final
        if not nxt:
            continue
        d = {f: round(nxt[f] - c[f], 2) for f in c}
        d["staleCanvases"] = round(d["staleBytes"] / canvas, 2) if canvas else None
        d["freshCanvases"] = round(d["freshBytes"] / canvas, 2) if canvas else None
        out.append({"i": i, "key": key, "t": t, **d})
    return canvas, out


def invalidations(report):
    raw = report.get("raw") or {}
    r2 = raw.get("r2") or {}
    base = report.get("startRevision")
    base = int(base) if str(base).isdigit() else None
    letters = [k for k in r2.get("keys", []) if len(k[0]) == 1]
    commit = {r["i"]: r["revisionMs"] for r in report.get("rows", [])}
    rows = []
    for i, (key, t, _) in enumerate(letters):
        end = letters[i + 1][1] if i + 1 < len(letters) else float("inf")
        want = None if base is None else base + 1 + i
        ev = [e for e in r2.get("inval", []) if t <= e[0] < end]
        rows.append({"i": i, "want": want, "commitMs": commit.get(i),
                     "events": [[round(e[0] - t, 1), e[1], e[2]] for e in ev],
                     "pre": sum(1 for e in ev if want is not None and e[1] == want - 1),
                     "post": sum(1 for e in ev if e[1] == want),
                     "other": sum(1 for e in ev if want is None or e[1] not in (want, want - 1))})
    return rows


def med(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else round(statistics.median(xs), 2)


code = ptl.main()
out = Path(sys.argv[sys.argv.index("--out") + 1])
report = json.loads(out.read_text())
report["page"] = hashlib.sha256(served_page).hexdigest()
report["pageChoice"] = page_choice
report["skipStale"] = skip_stale
report["dprRequested"] = dpr
report["windowRequested"] = window
report["runner"] = (f"DIAGNOSTIC r2-blit-bytes/blit_bytes_probe.py "
                    f"{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]} over probe {BASE[:16]}"
                    f" (probe's dataset writes coalesced; native putImageData timed and counted; worker adds"
                    f" diagLokId/diagPayload to document-invalidated; page {page_choice}"
                    f"{'; STALE RE-BLITS SKIPPED (what-if)' if skip_stale else ''}"
                    f"{f'; devicePixelRatio {dpr} (Chrome: Emulation.setDeviceMetricsOverride; Firefox: layout.css.devPixelsPerPx)' if dpr else ''}"
                    f"{f'; CSS window {window[0]}x{window[1]} (Chrome: Emulation; Firefox: MOZ_HEADLESS_WIDTH/HEIGHT)' if window else ''})")
canvas, keys = per_key(report)
inv = invalidations(report)
report["r2Summary"] = {
    "canvasWidth": (report.get("raw") or {}).get("canvasWidth"),
    "canvasHeight": (report.get("raw") or {}).get("canvasHeight"),
    "canvasBytes": canvas, "keys": len(keys),
    "perKeyMedian": {f: med([k[f] for k in keys]) for f in
                     ("staleCalls", "groups", "staleBytes", "staleCanvases", "staleMs",
                      "freshCalls", "freshBytes", "freshCanvases", "freshMs")},
    "perKeyMean": {f: (round(sum(k[f] for k in keys) / len(keys), 2) if keys else None) for f in
                   ("groups", "staleBytes", "staleCanvases", "staleMs", "freshCanvases", "freshMs")},
}
report["r1Summary"] = {
    "keys": len(inv), "pre": sum(r["pre"] for r in inv), "post": sum(r["post"] for r in inv),
    "other": sum(r["other"] for r in inv),
    "lokIds": sorted({e[2] for r in inv for e in r["events"]}, key=str),
}
report["r2PerKey"] = keys
report["r1PerKey"] = inv
out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
print(json.dumps({"r2": report["r2Summary"], "r1": report["r1Summary"]}, ensure_ascii=False))
sys.exit(code)
