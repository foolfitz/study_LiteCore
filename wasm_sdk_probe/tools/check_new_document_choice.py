#!/usr/bin/env python3
"""SPEC-M3-new-document N12 (closure) and the per-arm expectations of N2: the
host's `BlankDocument::choose()` is the truth source for which blank document a
user gets, so it is CALLED here (php -r), never re-implemented.

  * every Nextcloud language code (core/l10n/*.json of the instance, plus `en`)
    x locale {unset, en_US, zh_Hant_TW}: the chosen file is in blank/MANIFEST.json
    (a language added to the PHP table without a generated file -> red);
  * every file in MANIFEST.json is chosen by at least one of those inputs;
  * the spec's named cases come out as the spec says (section 3.2 examples).

  check_new_document_choice.py [--host DIR] [--nextcloud DIR] [--json]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_HOST = Path.home() / "Projects" / "Nextcloud_Apps" / "litecore"
LOCALES = [None, "en_US", "zh_Hant_TW"]
# (language, locale) -> (western, asian, paper): the spec's own examples, section 3.2.
NAMED = {
    ("zh_TW", None): ("en-US", "zh-TW", "A4"),          # the owner: language zh_TW, no locale set
    ("en", None): ("en-US", "zh-TW", "A4"),             # English UI, no region known
    ("en", "en_US"): ("en-US", "zh-TW", "Letter"),      # the EN arm
    ("zh_TW", "en_US"): ("en-US", "zh-TW", "Letter"),   # a region set on purpose wins
    ("zh_TW", "zh_Hant_TW"): ("en-US", "zh-TW", "A4"),
    ("en_GB", None): ("en-GB", "zh-TW", "A4"),
    ("es_MX", None): ("es-MX", "zh-TW", "Letter"),
    ("de_DE", None): ("de-DE", "zh-TW", "A4"),
    ("ja", None): ("en-US", "ja-JP", "A4"),
    ("ko", "en_US"): ("en-US", "ko-KR", "Letter"),
    ("zh_CN", None): ("en-US", "zh-CN", "A4"),
    ("zh_HK", None): ("en-US", "zh-HK", "A4"),
    ("pl", None): ("en-US", "zh-TW", "A4"),             # unsupported language: the fallback
    ("es_419", None): ("en-US", "zh-TW", "A4"),         # a region segment that is not a country
}


def php_choose(host: Path, inputs: list[tuple[str, str | None]]) -> list[dict[str, Any]]:
    script = (
        "require $argv[1]; $in = json_decode(file_get_contents('php://stdin'), true); $out = [];"
        " foreach ($in as $pair) { $out[] = OCA\\LiteCore\\Template\\BlankDocument::choose($pair[0], $pair[1]); }"
        " echo json_encode($out);"
    )
    done = subprocess.run(["php", "-r", script, str(host / "lib" / "Template" / "BlankDocument.php")],
                          input=json.dumps(inputs), capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        raise RuntimeError(f"php failed: {done.stderr.strip()}")
    return json.loads(done.stdout)


def nextcloud_languages(nextcloud: Path) -> list[str]:
    codes = {p.stem for p in (nextcloud / "core" / "l10n").glob("*.json")}
    codes.add("en")
    return sorted(codes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=Path, default=DEFAULT_HOST)
    parser.add_argument("--nextcloud", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    nextcloud = args.nextcloud or (args.host / "nextcloud")
    manifest = json.loads((args.host / "blank" / "MANIFEST.json").read_text(encoding="utf-8"))
    files = set(manifest["files"])

    languages = nextcloud_languages(nextcloud)
    grid = [(lang, loc) for lang in languages for loc in LOCALES]
    chosen = php_choose(args.host, grid)
    not_generated = sorted({c["file"] for c in chosen if c["file"] not in files})
    chosen_files = {c["file"] for c in chosen}
    unreachable = sorted(files - chosen_files)

    named_in = list(NAMED)
    named_out = php_choose(args.host, named_in)
    wrong = []
    for (lang, loc), got, want in zip(named_in, named_out, NAMED.values()):
        have = (got["western"], got["asian"], got["paper"])
        if have != want:
            wrong.append({"language": lang, "locale": loc, "got": have, "want": list(want)})

    report = {
        "check": "new-document-choice", "spec": "specs/SPEC-M3-new-document.md N12",
        "languages": len(languages), "inputs": len(grid), "manifestFiles": len(files),
        "chosenNotGenerated": not_generated, "generatedNeverChosen": unreachable,
        "namedCases": len(NAMED), "namedWrong": wrong,
        "passed": not not_generated and not unreachable and not wrong,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"N12 {'PASS' if report['passed'] else 'FAIL'}: {len(grid)} inputs over {len(languages)} languages,"
              f" {len(files)} files; not generated {not_generated}; never chosen {unreachable}; named wrong {wrong}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
