from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_r5_profiles import (  # noqa: E402
    BASE_FONTS,
    CJK_FONT,
    FONT_PREFIX,
    classify,
    create_pack,
)


class R5ResourceProfileTest(unittest.TestCase):
    def test_classifier_is_disjoint_complete_and_rewrites_offsets(self) -> None:
        names = ["/instdir/share/config/test.xcu"]
        names.extend(FONT_PREFIX + name for name in sorted(BASE_FONTS))
        names.append(FONT_PREFIX + CJK_FONT)
        names.append(FONT_PREFIX + "NotoSansArabic-Regular.ttf")
        files = []
        payload = bytearray()
        for index, filename in enumerate(names, start=1):
            start = len(payload)
            payload.extend(bytes([index]) * index)
            files.append({"filename": filename, "start": start, "end": len(payload)})

        groups = classify(files)
        self.assertEqual(sum(map(len, groups.values())), len(files))
        self.assertEqual(len(groups["base"]), 13)
        self.assertEqual(len(groups["cjk"]), 1)
        self.assertEqual(len(groups["fallback-fonts"]), 1)

        with tempfile.TemporaryDirectory(prefix="r5-profile-test-") as temporary:
            root = Path(temporary)
            source = root / "source.data"
            source.write_bytes(payload)
            packs = {
                name: create_pack(source, entries, root, name)
                for name, entries in groups.items()
            }
            self.assertEqual(sum(pack["bytes"] for pack in packs.values()), len(payload))
            for pack in packs.values():
                metadata = json.loads(pack["metadataPath"].read_text(encoding="utf-8"))
                self.assertEqual(metadata["files"][0]["start"], 0)
                self.assertEqual(metadata["files"][-1]["end"], pack["bytes"])
                self.assertEqual(metadata["sha256"], pack["sha256"])

    def test_classifier_rejects_non_contiguous_metadata(self) -> None:
        files = [{"filename": "/bad", "start": 1, "end": 2}]
        with self.assertRaisesRegex(RuntimeError, "non-contiguous"):
            classify(files)


if __name__ == "__main__":
    unittest.main()
