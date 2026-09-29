import json, sys, time
from pathlib import Path
sys.path.insert(0, '/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools')
import check_m3_page_honesty as H
from check_m3_locks import Server, login, open_from_files
from check_m3_skeleton_open import Instance, DEFAULT_DDEV, NAME, product_state, state_until
from r7_support import evaluate
from run_e2_c_page_smoke import POINT_AT
BANDS = """(() => { const c = document.querySelector('#canvas'); const w = c.width, h = c.height;
const d = c.getContext('2d').getImageData(0, 0, w, h).data; const rows = [];
for (let y = 0; y < h; y++) { let n = 0; for (let x = 0; x < w; x++) { const i = (y*w+x)*4;
 if (d[i+3] > 128 && d[i] < 100 && d[i+1] < 100 && d[i+2] < 100) n++; } rows.push(n); }
const bands = []; let start = -1;
for (let y = 0; y <= h; y++) { const on = y < h && rows[y] > 2; if (on && start < 0) start = y;
 if (!on && start >= 0) { bands.push([start, y - 1]); start = -1; } }
return { h, w, bands: bands.map(([a, b]) => ({ a, b, mid: +(((a + b) / 2) / h).toFixed(4) })) }; })()"""
inst = Instance(DEFAULT_DDEV); log = []; server = Server(inst, log)
out = {}
server.setup()
try:
    server.clear_locks(); server.upload(server.admin, NAME)
    s = H.new_session('chrome', Path(sys.argv[1]))
    try:
        login(s, inst.base, 'admin', inst.password)
        rec = {}; open_from_files(s, inst.base, '', NAME, rec)
        time.sleep(1.5)
        out['bands'] = evaluate(s, BANDS)
        mids = [b['mid'] for b in out['bands']['bands']]
        steps = []
        for label, y in [('click-0.28', '0.28')] + [(f'band{i}', str(m)) for i, m in enumerate(mids[:6])]:
            evaluate(s, POINT_AT.replace('ARG_X','0.35').replace('ARG_Y', y))
            time.sleep(0.4)
            st = H.quiet_state(s, 40)
            steps.append({'at': label, 'y': y, 'sink': evaluate(s, H.SINK_TOP), 'latency': st.get('latency'), 'state': st.get('state'), 'toast': st.get('toast'), 'timedOut': st.get('timedOut')})
            if st.get('state') != 'ready':
                break
        out['clicks'] = steps
        if steps and steps[-1].get('state') == 'ready' and mids:
            evaluate(s, POINT_AT.replace('ARG_X','0.35').replace('ARG_Y', str(mids[0])))
            time.sleep(0.4); H.quiet_state(s, 40)
            before = evaluate(s, H.SINK_TOP); t0 = time.monotonic()
            out['arrow'] = evaluate(s, H.ARROW_DOWN)
            st = state_until(s, lambda st: '下移一行' in (st.get('latency') or '') or st.get('state') == 'recoverable-error', 40)
            out['down'] = {'sinkBefore': before, 'sinkAfter': evaluate(s, H.SINK_TOP), 'secs': round(time.monotonic()-t0,2), 'latency': st.get('latency'), 'state': st.get('state'), 'toast': st.get('toast')}
    finally:
        s.close()
finally:
    server.teardown()
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False)[:3000])
