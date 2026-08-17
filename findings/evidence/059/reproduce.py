"""Press each inline format on a collapsed caret; record what the product says."""
import subprocess, sys, time, json, re
from pathlib import Path
P = Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe")
sys.path.insert(0, str(P / "tools"))
from r7_support import evaluate, wait_page
from run_browser_probe import FirefoxSession, free_port
from run_e2_c_page_smoke import READ_STATE, navigate
src = (P/"tools"/"run_e2_c_product_path.py").read_text()
POINT = re.search(r'POINT_AT = """(.*?)"""', src, re.S).group(1)
PRESS = re.search(r'PRESS = """(.*?)"""', src, re.S).group(1)
CLEAR = re.search(r'CLEAR_TOAST = """(.*?)"""', src, re.S).group(1)
READT = "(() => document.querySelector('#toast').textContent)()"
port = free_port()
srv = subprocess.Popen([sys.executable, str(P/"web"/"serve.py"), "--port", str(port),
                        "--root", str(P/"dist")], cwd=P,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
out = {}
try:
    base = f"http://127.0.0.1:{port}/e2-editor.html"; wait_page(base)
    s = FirefoxSession("fmt"); navigate(s, base)
    for _ in range(120):
        st = evaluate(s, READ_STATE)
        if st and st.get("state") == "ready": break
        time.sleep(1)
    for action in ("set-bold","set-italic","set-underline","set-strikethrough",
                   "set-paragraph-heading","set-list-unordered"):
        evaluate(s, POINT.replace("ARG_X","0.30").replace("ARG_Y","0.24"))
        time.sleep(1.5); evaluate(s, CLEAR)
        evaluate(s, PRESS.replace("ARG_ACTION", action))
        time.sleep(2.5)
        st = evaluate(s, READ_STATE) or {}
        out[action] = {"toast": evaluate(s, READT), "state": st.get("state"),
                       "latency": st.get("latency")}
        if st.get("state") != "ready":   # a blocked queue poisons the next press
            evaluate(s, "(() => { document.querySelector('#notice-action').click(); return 1; })()")
            for _ in range(60):
                if (evaluate(s, READ_STATE) or {}).get("state") == "ready": break
                time.sleep(1)
    print(json.dumps(out, ensure_ascii=False, indent=2))
finally:
    srv.terminate()
