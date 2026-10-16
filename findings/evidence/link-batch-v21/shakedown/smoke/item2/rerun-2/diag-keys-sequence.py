"""Development diagnostic (not evidence): which typed keys reach #markdown-text, key by key."""
import json, sys, tempfile, time
FAST = "--fast" in sys.argv
from pathlib import Path
sys.path.insert(0, "/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools")
import run_v21_shakedown_item2 as run
from run_v21_shakedown_item2 import common, v20, obs2, hook, clip, inp
pop = json.loads(run.POPULATION.read_text(encoding="utf-8"))
files = run.mirror_files(pop)
scratch = Path(tempfile.mkdtemp(prefix="v21-diag-"))
out = []
with common.browser_lock("diag_keys item2", wait_s=3600):
    ident = common.build_mirror(scratch / "m", snippets=[v20.OBSERVER, obs2.SNIPPET, hook.SNIPPET], extra_files=files)
    with common.served(Path(ident["mirror"])) as base:
        s = run.open_browser("chrome")
        try:
            ctx = run.Ctx(s, "chrome", base, scratch, ident)
            ctx.load(); ctx.open(run.EMPTY)
            for attempt in ("immediate",):
                ctx.real_click(run.DIALOG_BUTTON)
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and ctx.ev(run.ACTIVE) != "markdown-text":
                    time.sleep(0.1)
                if attempt == "settled":
                    time.sleep(1.0)
                steps = []
                for ch in list("# 打字 ABC") + ["Backspace", "ArrowLeft", "Enter"]:
                    run.type_char(s, "chrome", ch)
                    time.sleep(0.0 if FAST else 0.15)
                    if not FAST: steps.append([ch, ctx.ev("document.querySelector('#markdown-text').value"), ctx.ev(run.ACTIVE)])
                steps.append(["end", ctx.ev("document.querySelector('#markdown-text').value")])
                out.append({"attempt": attempt, "steps": steps})
                ctx.real_click("#markdown-cancel"); time.sleep(0.5)
        finally:
            common.close_browser(s)
print(json.dumps(out, ensure_ascii=False))
