from pathlib import Path
import subprocess
import tempfile
import unittest
SDK = Path(__file__).resolve().parents[1]
class Guards(unittest.TestCase):
    def test_real_helpers_and_causal_mutations(self):
        header = (SDK/'src/ordered_engine_guards.hpp').read_text()
        variants = [('control',header),
                    ('malformed-borrows-sequence',header.replace('if (parsed)','if (true)')),
                    ('flag-stuck-on-throw',header.replace('~FlagScope() { flag = false; }','~FlagScope() {}'))]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for label, text in variants:
                with self.subTest(label=label):
                    (work/'ordered_engine_guards.hpp').write_text(text)
                    result = subprocess.run(['g++','-std=c++17','-I'+tmp,str(SDK/'tests/ordered_engine_guards_test.cpp'),'-o',str(work/'test')],capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    code = subprocess.run([str(work/'test')]).returncode
                    self.assertEqual(code,0 if label=='control' else 1)
if __name__=='__main__': unittest.main()
