"""Is there a visible caret? One screenshot, before and after a click."""
import subprocess, sys, time
from pathlib import Path
P = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(P / "tools"))
from r7_support import evaluate, wait_page
from run_browser_probe import FirefoxSession, free_port
from run_e2_c_page_smoke import READ_STATE, navigate

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
port = free_port()
srv = subprocess.Popen([sys.executable, str(P/"web"/"serve.py"), "--port", str(port),
                        "--root", str(P/"dist")], cwd=P,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    s = FirefoxSession("caret")
    navigate(s, base)
    for _ in range(120):
        st = evaluate(s, READ_STATE)
        if st and st.get("state") == "ready": break
        time.sleep(1)
    (OUT/"01-before-click.png").write_bytes(s.screenshot())
    POINT = open(P/"tools"/"run_e2_c_product_path.py").read()
    import re
    pa = re.search(r'POINT_AT = """(.*?)"""', POINT, re.S).group(1)
    evaluate(s, pa.replace("ARG_X","0.35").replace("ARG_Y","0.28"))
    time.sleep(3)
    (OUT/"02-after-click-caret-placed.png").write_bytes(s.screenshot())
    print("state:", evaluate(s, READ_STATE).get("latency"))
    # And a drag, for the selection highlight.
    dr = re.search(r'DRAG = """(.*?)"""', POINT, re.S).group(1)
    evaluate(s, dr.replace("ARG_X1","0.20").replace("ARG_Y1","0.28")
                 .replace("ARG_X2","0.75").replace("ARG_Y2","0.28"))
    time.sleep(3)
    (OUT/"03-after-drag-selection.png").write_bytes(s.screenshot())
    print("wrote 3 screenshots")
finally:
    srv.terminate()
