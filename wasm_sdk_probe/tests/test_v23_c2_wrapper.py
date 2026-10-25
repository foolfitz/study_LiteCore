"""Pure wrapper preparation checks; starts no browser/server and imports no C2 gate."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import record_v23_c2 as r


class Wrapper(unittest.TestCase):
    def test_only_copied_worker_url_changes(self):
        original=b'prefix\nworkerUrl: "./profiles/e2-editor-v22/sdk-worker.js",\nsuffix'
        unchanged,patch=r.patched_page(original,'e2-editor-v22')
        self.assertEqual(unchanged,original);self.assertFalse(patch['changed'])
        changed,patch=r.patched_page(original,'e2-editor-v23-diag-r2')
        self.assertEqual(changed.replace(b'e2-editor-v23-diag-r2',b'e2-editor-v22'),original)
        self.assertTrue(patch['changed'])
        for raw in (b'wrong',original+original):
            with self.assertRaises(ValueError):r.patched_page(raw,'e2-editor-v23-diag-r2')
    def test_actual_observation_bindings(self):
        artifacts={'probe.wasm':'synthetic'}
        good={'userAgent':'Mozilla/5.0 HeadlessChrome/132.0','geometry':{'width':1400,'height':1000,'dpr':2},'artifacts':artifacts}
        self.assertEqual(r.browser_observation_problems(good,'chrome',artifacts),[])
        for key,value in [('userAgent','Firefox/136.0'),('geometry',{'width':1400,'height':1000,'dpr':1}),('artifacts',{})]:
            changed={**good,key:value};self.assertTrue(r.browser_observation_problems(changed,'chrome',artifacts))
    def test_literal_fixture_and_source_population(self):
        self.assertEqual(r.sha(r.OWNER),r.OWNER_SHA)
        graph=r.probe_source_graph()
        self.assertIn('tools/probe_typing_latency.py',graph)
        self.assertIn('tools/probe_typing_latency_view.py',graph)
        self.assertIn('tools/probe_111_overtake.py',graph)
        self.assertIn('input/input-adapter.js',r.served_graph(r.DIST))
        raw=(r.DIST/'e2-editor-app.js').read_bytes()
        self.assertEqual(r.patched_page(raw,'e2-editor-v22')[0],raw)

if __name__=='__main__':unittest.main()
