from pathlib import Path
import subprocess
import tempfile
import unittest
SDK=Path(__file__).resolve().parents[1]
class Html(unittest.TestCase):
    def test_actual_helper_and_causal_mutations(self):
        original=(SDK/'src/ordered_diagnostic_html.inc').read_text()
        changes=[('control',None,None),('wrong-mime','"text/html"','"text/plain"'),
                 ('entry-absent','emitOrderedControl(9, command.requestId);',''),
                 ('return-absent','emitOrderedHtml("v23-html-return", command.requestId, html);',''),
                 ('reply-reads-lok','emitOrderedHtml("v23-html-result", requestId, html);','gState.document->pClass->getTextSelection(gState.document, "text/html", nullptr); emitOrderedHtml("v23-html-result", requestId, html);'),
                 ('early-reply','emitOrderedHtml("v23-html-return", command.requestId, html);','emitOrderedHtml("v23-html-return", command.requestId, html); emitOrderedHtml("v23-html-result", command.requestId, html);')]
        with tempfile.TemporaryDirectory(dir=SDK/'build',prefix='r2-html-') as tmp:
            p=Path(tmp)
            for name,before,after in changes:
                with self.subTest(name=name):
                    if before:self.assertEqual(original.count(before),1)
                    (p/'ordered_diagnostic_html.inc').write_text(original.replace(before,after) if before else original)
                    r=subprocess.run(['g++','-std=c++17','-I'+tmp,str(SDK/'tests/ordered_diagnostic_html_test.cpp'),'-o',str(p/'test')],capture_output=True,text=True)
                    self.assertEqual(r.returncode,0,r.stderr)
                    r=subprocess.run([str(p/'test')],capture_output=True)
                    if before:self.assertNotEqual(r.returncode,0)
                    else:self.assertEqual(r.returncode,0)
if __name__=='__main__':unittest.main()
