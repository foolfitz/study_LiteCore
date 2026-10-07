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

    def test_asked_charset_marks_glyph_fallback(self):
        # Review N6: the primary lookup asks without FC_CHARSET, glyph fallback
        # with the missing code points.  Both known answers, both ways.
        self.assertFalse(blocks("native-full-config-zh-tw.txt")[0]["askedCharset"])
        b = blocks("native-bare-config-zh-tw-charset-3001.txt")[0]
        self.assertTrue(b["askedCharset"])
        self.assertEqual(b["askedLang"], ["zh-tw", "en"])  # fc-match adds its weak default
        self.assertEqual(b["bestFamily"], ["Noto Sans CJK JP"])

    def test_pitch_table_reads_run1_like_113(self):
        # run1's runs, read by hand in RESULT.md (TW-TC 20, TW-SIYUAN 16).
        import json
        report = json.loads((CHECK.parent / "run1/fc-debug.json").read_text(encoding="utf-8"))
        table = p.pitch_table(report["profiles"][1]["pitches"]["runs"])
        self.assertEqual((table["TW-TC"], table["TW-SIYUAN"], table["LATIN-DEFAULT"]), (20, 16, 16))
        # An extra ink run (not a 1-row frame rule) breaks the pairing: nothing is claimed.
        self.assertIsNone(p.pitch_table(report["profiles"][1]["pitches"]["runs"] + [[500, 510]]))

    def test_not_vacuous(self):
        # A renamed directory must fail, not read zero blocks as "no match".
        self.assertTrue((CHECK / "native-full-config-zh-tw.txt").is_file())
        self.assertEqual(p.match_blocks(["unrelated", ""]), [])


if __name__ == "__main__":
    unittest.main()
