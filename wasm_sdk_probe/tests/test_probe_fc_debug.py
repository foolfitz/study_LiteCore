"""The fontconfig debug-log reader of `tools/probe_fc_debug.py`, offline.

Known answers are two real native fontconfig logs (finding 114,
findings/evidence/114/fc-debug/parser-check/README.md).  Each test also says
what the reader's first version got wrong on that input, so a regression to it
fails here and not in a WASM run nobody can repeat cheaply.

    python3 -m unittest tests.test_probe_fc_debug
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import probe_fc_debug as p  # noqa: E402

CHECK = Path(__file__).resolve().parents[2] / "findings/evidence/114/fc-debug/parser-check"


def blocks(name: str) -> list[dict]:
    return p.match_blocks((CHECK / name).read_text(encoding="utf-8").split("\n"))


class ReaderKnownAnswers(unittest.TestCase):
    def test_full_config_zh_tw(self):
        found = blocks("native-full-config-zh-tw.txt")
        self.assertEqual(len(found), 1)
        b = found[0]
        self.assertEqual(b["askedFamily"][0], "思源黑體")
        # First version: ['en'] -- the unquoted langset value was dropped.
        self.assertEqual(b["askedLang"], ["zh-tw", "en"])
        self.assertEqual(b["bestFamily"], ["Noto Sans CJK TC"])
        self.assertEqual(b["bestFile"], ["FONTS/NotoSansCJK-Regular-subset-E.ttc"])
        self.assertTrue(b["bestIndex"].startswith("index: 3"))
        # First version: False -- the charset dump's closing `(s)` ended the pattern.
        self.assertTrue(b["bestLangHasZhTw"])

    def test_bare_config_en(self):
        found = blocks("native-bare-config-en.txt")
        self.assertEqual(len(found), 1)
        b = found[0]
        self.assertEqual(b["askedFamily"], ["思源黑體"])
        self.assertEqual(b["askedLang"], ["en"])
        self.assertEqual(b["bestFamily"], ["Liberation Mono"])
        self.assertFalse(b["bestLangHasZhTw"])

    def test_not_vacuous(self):
        # A renamed directory must fail, not read zero blocks as "no match".
        self.assertTrue((CHECK / "native-full-config-zh-tw.txt").is_file())
        self.assertEqual(p.match_blocks(["unrelated", ""]), [])


if __name__ == "__main__":
    unittest.main()
