"""Does a document saved on the candidate open on the profile we would revert to?

`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, revert condition 2. A
revert is only a pointer flip if nothing written under v11 is unreadable by v8.
Grepped: the shell uses no localStorage, sessionStorage or indexedDB and the
checkpoint lives in memory, so the ONLY cross-version artifact is the saved ODT.

Both directions are driven, because a revert is not the only crossing: a user
who saved under v8 before the cutover opens that file under v11 afterwards.

Everything goes through the product's own buttons -- the file input and the save
button -- because a round-trip performed by the harness would be a round-trip
nobody ships.
"""
import base64, json, subprocess, sys, tempfile, time
from pathlib import Path

PROJECT = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page                            # noqa: E402
from run_browser_probe import ChromeSession, free_port                 # noqa: E402
from run_e2_c_page_smoke import navigate                              # noqa: E402
import run_e2_c_product_path as P                                     # noqa: E402

MARK = "ROUNDTRIP-SENTINEL"


def serve(root: Path):
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
         "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_page(f"http://127.0.0.1:{port}/e2-editor.html")
    return port, proc


def ready(session, timeout=180):
    deadline = time.monotonic() + timeout
    state = {}
    while time.monotonic() < deadline:
        state = evaluate(session, P.READ_STATE) or {}
        if state.get("state") == "ready":
            return state
        time.sleep(0.5)
    return state


def open_page(session, port):
    navigate(session, f"http://127.0.0.1:{port}/e2-editor.html")
    evaluate(session, P.INSTALL)
    return ready(session)


def type_and_save(session, text):
    """Type through the product's own commit path, then press its save button."""
    ink = evaluate(session, P.LINE_INK.replace("ARG_Y", "0.28")) or {}
    clicks = P.caret_click_fractions(ink)
    P.place_caret_and_settle(session, P.POINT_AT, clicks["near"], "0.28")
    floor = P.revision_of(evaluate(session, P.READ_STATE))
    evaluate(session, P.COMPOSE.replace("ARG_TEXT", text))
    P.wait_for(session,
               lambda s, f=floor: P.revision_of(s) is not None and f is not None
               and P.revision_of(s) > f, 60)
    return P.capture_save(session, evaluate(session, P.SAVE_COUNT) or 0)


scratch = Path(tempfile.mkdtemp(prefix="odt-roundtrip-"))
candidate_root = scratch / "candidate"
manifest = PROJECT / "dist" / "profiles" / "e2-editor-v11" / "sdk-manifest.json"
page, _pin_before, _wasm = P.repointed_page(
    (PROJECT / "dist" / "e2-editor-app.js").read_text(encoding="utf-8"),
    "e2-editor-v11", manifest)
P.build_mirror(PROJECT / "dist", candidate_root,
               {"e2-editor-app.js": page.encode("utf-8")})

report = {"mark": MARK}
session = None
servers = []
try:
    v11_port, s1 = serve(candidate_root); servers.append(s1)
    v8_port, s2 = serve(PROJECT / "dist"); servers.append(s2)
    session = ChromeSession("cold")

    # --- written on the CANDIDATE (v11) -------------------------------------
    report["candidateOpened"] = open_page(session, v11_port).get("state")
    saved_on_v11 = type_and_save(session, MARK + "-FROM-V11")
    report["savedOnCandidate"] = {
        "isOdt": P.is_an_odt(saved_on_v11),
        "bytes": saved_on_v11.get("bytes"),
        "hasMark": (MARK + "-FROM-V11") in (saved_on_v11.get("content") or ""),
    }
    b64_v11 = base64.b64encode(
        base64.b64decode(evaluate(session, P.READ_SAVE.replace(
            "ARG_INDEX", str((evaluate(session, P.SAVE_COUNT) or 1) - 1)))["b64"])
    ).decode()

    # --- opened on the SHIPPED page (v8), which is what a revert means -------
    report["shippedOpened"] = open_page(session, v8_port).get("state")
    report["v11ToV8Dispatch"] = evaluate(
        session, P.OPEN_BYTES.replace("ARG_B64", b64_v11)
        .replace("ARG_NAME", "from-v11.odt"))
    # WAIT ON THE DOCUMENT NAME, NOT ON `ready`.
    #
    # The page is ALREADY ready before the file input is touched, so a predicate
    # of `state == "ready"` returns instantly and the probe reports on the boot
    # fixture -- which is what the first run of this did: `doc` came back
    # `list-contexts.odt` in both directions and nothing had been opened at all.
    # `doc` is the only field that says WHICH document is in front of you.
    after = P.wait_for(session,
                       lambda s: (s.get("doc") or "") == "from-v11.odt"
                       and s.get("state") == "ready", 300) or {}
    report["v11ToV8"] = {"state": after.get("state"),
                         "doc": after.get("doc"),
                         "toast": after.get("toast")}
    resaved = P.capture_save(session, evaluate(session, P.SAVE_COUNT) or 0)
    report["v11ToV8"].update({
        "reopenedIsOdt": P.is_an_odt(resaved),
        "markSurvived": (MARK + "-FROM-V11") in (resaved.get("content") or ""),
        "lines": [l["text"][:40] for l in P.document_lines(resaved)][:6],
    })

    # --- and the other crossing: saved on v8, opened on the candidate --------
    saved_on_v8 = type_and_save(session, MARK + "-FROM-V8")
    report["savedOnShipped"] = {"isOdt": P.is_an_odt(saved_on_v8),
                                "bytes": saved_on_v8.get("bytes")}
    b64_v8 = evaluate(session, P.READ_SAVE.replace(
        "ARG_INDEX", str((evaluate(session, P.SAVE_COUNT) or 1) - 1)))["b64"]
    report["candidateReopened"] = open_page(session, v11_port).get("state")
    report["v8ToV11Dispatch"] = evaluate(
        session, P.OPEN_BYTES.replace("ARG_B64", b64_v8)
        .replace("ARG_NAME", "from-v8.odt"))
    after = P.wait_for(session,
                       lambda s: (s.get("doc") or "") == "from-v8.odt"
                       and s.get("state") == "ready", 300) or {}
    report["v8ToV11"] = {"state": after.get("state"), "doc": after.get("doc"),
                         "toast": after.get("toast")}
    resaved = P.capture_save(session, evaluate(session, P.SAVE_COUNT) or 0)
    report["v8ToV11"].update({
        "reopenedIsOdt": P.is_an_odt(resaved),
        "markSurvived": (MARK + "-FROM-V8") in (resaved.get("content") or ""),
    })
finally:
    if session is not None:
        try: session.close()
        except Exception: pass
    for s in servers:
        s.terminate()
print(json.dumps(report, indent=2, ensure_ascii=False))
