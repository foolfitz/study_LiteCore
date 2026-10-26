from pathlib import Path
import subprocess
import tempfile
import unittest
SDK=Path(__file__).resolve().parents[1]
class Abi(unittest.TestCase):
    def test_actual_c_entry_variants_and_causal_reversions(self):
        feature=['OXSDK_E2_V21_LINK_BATCH','OXSDK_E2_V23_LINK_BATCH','OXSDK_E2_V23_FEATURE_ABI6']
        source=(SDK/'src/editor_api.cpp').read_text()
        rows=[('abi4',[],4,source),('abi5',['OXSDK_E2_V21_LINK_BATCH'],5,source),
              ('diagnostic',['OXSDK_E2_V21_LINK_BATCH','OXSDK_E2_V23_LINK_BATCH','OXSDK_E2_V23_DIAGNOSTIC'],5,source),
              ('feature',feature,6,source),
              ('missing-line-extend',feature,6,source.replace('action == OXSDK_EDITOR_V3_MOVE_LINE_END;', 'false;')),
              ('document-extend-grant',feature,6,source.replace('action == OXSDK_EDITOR_V3_MOVE_LINE_END;', 'action == OXSDK_EDITOR_V3_MOVE_LINE_END || action == OXSDK_EDITOR_V4_MOVE_DOCUMENT_END;')),
              ('discard-extend',feature,6,source.replace('mapped, extendSelection != 0, enabled != 0)', 'mapped, false, enabled != 0)')),
              ('discard-enabled',feature,6,source.replace('mapped, extendSelection != 0, enabled != 0)', 'mapped, extendSelection != 0, false)')),
              ('bound-too-small',feature,6,source.replace('constexpr std::uint32_t kMaxExternalAction = 23;', 'constexpr std::uint32_t kMaxExternalAction = 21;').replace('static_assert(kMaxExternalAction == OXSDK_EDITOR_V4_MOVE_DOCUMENT_END,','static_assert(true,'))]
        with tempfile.TemporaryDirectory(dir=SDK/'build',prefix='feature-abi-') as tmp:
            p=Path(tmp);(p/'emscripten').mkdir();(p/'emscripten/emscripten.h').write_text('#define EMSCRIPTEN_KEEPALIVE\n')
            for name,defs,abi,text in rows:
                with self.subTest(name=name):
                    (p/'editor_api.cpp').write_text(text)
                    args=['g++','-std=c++17','-I'+tmp,'-I'+str(SDK/'src'),'-DOXSDK_E2_FORMAT_BARRIER','-DEXPECTED_ABI='+str(abi)]+['-D'+d for d in defs]+[str(p/'editor_api.cpp'),str(SDK/'tests/v23_feature_abi_test.cpp'),'-o',str(p/'test')]
                    r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
                    r=subprocess.run([str(p/'test')]);self.assertEqual(r.returncode==0,name in ('abi4','abi5','diagnostic','feature'))
            for defs in [feature+['OXSDK_E2_V23_DIAGNOSTIC'],feature[1:],feature[:1]+feature[2:]]:
                r=subprocess.run(['g++','-std=c++17','-x','c++','-fsyntax-only','-I'+str(SDK/'src')]+['-D'+d for d in defs]+['-'],input='#include "editor_api.h"\n',capture_output=True,text=True)
                self.assertNotEqual(r.returncode,0)
if __name__=='__main__':unittest.main()
