#!/usr/bin/env python3
"""The item-2 populations (M1, M2, M3, M4, M5), generated from their sources and committed, with their output,
before any WASM run (ARMS-item2.md §4 and §9; ARMS.md §4 step 3).

Sources, read here and nowhere else:
  - the M0 fixture tests/markdown_paste_expected.json (verdicts, codes, rules);
  - the native rounds' arm folders (findings/evidence/link-batch-v21/native/markdown-paste/{out, round-2/out,
    round-3/out}): references, placements, outcomes;
  - the served SDK source (sdk/document-sdk.js, the tree's: it is one of the five lagging files served
    from the tree) for the operative limit L;
  - tools/v21_item2_fixtures.py for the generated corpora.

Rules (written here, applied mechanically; an item or arm no rule places makes the tool fail):
  M1  every PASS item; its native P1 reference is round 1's out/P1-<id>, round 2's T3-P1-<id> or round 3's
      R3-P1-<id> (exactly one must exist, 3 runs, one signature by the comparator).
  M2  round-1/M8.md; expected = the comparator's paragraph texts of out/P1-M8 (3 runs agreeing).
  M3  every non-PASS item except X14 (spec §12.2 (b): PARSE_FAIL only by injection).  Routes: R-dialog and
      R-sdk when the bytes decode as UTF-8 (strict), else R-bytes only (§12.1, §12.2 (a)).  Expected code =
      the fixture's code for the verdict.  Layer: "sdk" for empty text and for more than L bytes on R-dialog /
      R-sdk, else "engine".  Size arms: SDK-L, SDK-L+1 (R-sdk), ENG-65536, ENG-65537 (R-worker).
  M4  the native position arms (DM-10 A): round 1 P1-P7 x {M1, M2, M4, M8}; round 2 T1 P8-P11 x {M1, M2, M4,
      M5, M8}; round 2 T2, classified by its own recorded outcome.  Classes: collapsed (one Undo restores),
      range (MARKDOWN_NEEDS_CARET on R-sdk, the page's refusal on R-dialog), protected (M9's clean-arm
      expectation), excluded (with the rule).
  M5  the M3 items whose verdict is REMOTE or HTML, plus every NUL item with a URL (X03); targets = every
      scheme://host[:port] in the bytes.

  v21_item2_population.py --out PATH.json     write it (refuses to overwrite)
  v21_item2_population.py --check PATH.json   regenerate and compare (exit 1 when they differ)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import fodt_to_odt  # noqa: E402
import v21_item2_compare as cmp  # noqa: E402

PROJECT = TOOLS.parent
REPO = PROJECT.parent
NATIVE = REPO / "findings/evidence/link-batch-v21/native/markdown-paste"
EXPECTED = PROJECT / "tests/markdown_paste_expected.json"
CORPUS = PROJECT / "tests/markdown_paste_corpus"
SDK_SOURCE = PROJECT / "sdk/document-sdk.js"
FIXTURES_TOOL = TOOLS / "v21_item2_fixtures.py"

KEY = {1024: "ArrowDown", 1025: "ArrowUp", 1026: "ArrowLeft", 1027: "ArrowRight", 1028: "Home", 1029: "End"}
SHIFT, MOD1 = 0x1000, 0x2000
URL = re.compile(rb"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s)\"'>\]]+")


class PopulationError(RuntimeError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def load_fixtures_tool():
    spec = importlib.util.spec_from_file_location("v21_item2_fixtures_pop", FIXTURES_TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sdk_limit() -> int:
    found = re.findall(r"export const MARKDOWN_PASTE_LIMIT_BYTES = (\d+);", SDK_SOURCE.read_text(encoding="utf-8"))
    if len(found) != 1:
        raise PopulationError("MARKDOWN_PASTE_LIMIT_BYTES is not in sdk/document-sdk.js exactly once")
    return int(found[0])


def runs_of(folder: Path) -> list[Path]:
    return sorted(folder.glob("run*/after.fodt.gz"))


def reference(item_path: str) -> dict:
    name = Path(item_path).stem
    candidates = [NATIVE / "out" / f"P1-{name}", NATIVE / "round-2/out" / f"T3-P1-{name}",
                  NATIVE / "round-3/out" / f"R3-P1-{name}"]
    found = [c for c in candidates if c.is_dir()]
    if len(found) != 1:
        raise PopulationError(f"{item_path}: {len(found)} native P1 references ({[rel(c) for c in found]})")
    runs = runs_of(found[0])
    if len(runs) != 3:
        raise PopulationError(f"{item_path}: {len(runs)} native runs with after.fodt.gz")
    sigs = {cmp.signature_sha256(r.read_bytes()) for r in runs}
    if len(sigs) != 1:
        raise PopulationError(f"{item_path}: the native runs disagree ({sorted(sigs)})")
    summary = json.loads((found[0] / "run1" / "summary.json").read_text(encoding="utf-8"))
    return {"folder": rel(found[0]), "afterRuns": [{"path": rel(r), "sha256": sha(r.read_bytes())} for r in runs],
            "signatureSha256": sigs.pop(), "inputSha256": summary.get("inputSha256"),
            "threadTextEncoding": summary.get("threadTextEncoding")}


def decodable(data: bytes) -> bool:
    try:
        data.decode("utf-8", errors="strict")
        return True
    except UnicodeDecodeError:
        return False


def m1_m2_m3_m5(expected: dict, limit: int) -> dict:
    items = expected["items"]
    if not items:
        raise PopulationError("the M0 fixture has no items")
    codes = {v: spec["code"] for v, spec in expected["rules"]["verdicts"].items()}
    m1, m3, m5, excluded = [], [], [], []
    for item in items:
        path = CORPUS / item["path"]
        data = path.read_bytes()
        if sha(data) != item["sha256"]:
            raise PopulationError(f"{item['path']}: bytes differ from the fixture's sha256")
        verdict = item["verdict"]
        if verdict not in codes:
            raise PopulationError(f"{item['path']}: unknown verdict {verdict}")
        base = {"path": item["path"], "sha256": item["sha256"], "bytes": len(data), "verdict": verdict}
        if verdict == "PASS":
            m1.append({**base, "reference": reference(item["path"])})
            continue
        if item.get("inject"):
            excluded.append({**base, "criterion": "M3", "rule": "spec 12.2 (b): non-PASS only by injection "
                             f"({item['inject']}); on WASM its bytes are {item.get('verdictWithoutInjection')}"})
            continue
        routes = ["dialog", "sdk"] if decodable(data) else ["bytes"]
        layer = "sdk" if (len(data) == 0 or len(data) > limit) and routes != ["bytes"] else "engine"
        entry = {**base, "routes": routes, "expectedCode": codes[verdict], "layerOnDialogAndSdk":
                 layer if routes != ["bytes"] else None}
        if len(data) == 0:
            entry["layerOnWorker"] = "worker"     # sdk-worker.js refuses empty text before the export
        m3.append(entry)
        targets = sorted({u.decode("ascii", "replace") for u in URL.findall(data)})
        if verdict in ("REMOTE", "HTML") or (verdict == "NUL" and targets):
            if routes == ["bytes"]:
                raise PopulationError(f"{item['path']}: an M5 item that only R-bytes can carry")
            m5.append({"path": item["path"], "sha256": item["sha256"], "verdict": verdict, "targets": targets,
                       "originsNamed": sorted({re.sub(r"^(\w+://[^/]+).*$", r"\1", t) for t in targets})})
    if not (m1 and m3 and m5):
        raise PopulationError("an empty population (M1, M3 or M5)")
    m8 = CORPUS / "round-1/M8.md"
    ref = reference("round-1/M8.md")
    texts = [cmp.paragraph_texts(gzip.decompress((REPO / r["path"]).read_bytes())) for r in ref["afterRuns"]]
    if any(t != texts[0] for t in texts):
        raise PopulationError("M2: the native M8 runs disagree on their texts")
    fixtures = load_fixtures_tool()
    sizes = []
    for arm, n, route, layer in (("SDK-L", limit, "sdk", None), ("SDK-L+1", limit + 1, "sdk", "sdk"),
                                 ("ENG-65536", 65536, "worker", None), ("ENG-65537", 65537, "worker", "engine")):
        data = fixtures.size_corpus(n)
        sizes.append({"arm": arm, "bytes": n, "route": route, "sha256": sha(data), "refusingLayer": layer,
                      "expectedCode": "INVALID_ARGUMENT" if layer else None, "corpusFile": f"size-{n}.md"})
    return {"M1": m1,
            "M2": {"item": "round-1/M8.md", "sha256": sha(m8.read_bytes()), "reference": ref,
                   "expectedTexts": texts[0]},
            "M3": {"items": m3, "sizeArms": sizes, "limitL": limit,
                   "positiveControl": {"path": "round-1/M2.md", "sha256": sha((CORPUS / "round-1/M2.md").read_bytes())}},
            "M5": m5, "excluded": excluded}


# ---------------------------------------------------------------- M4

ROUND1_KEYS = {  # tool/md_paste_probe.cpp place() after its leading Ctrl+Home [source :300-325]
    "doc-start": [], "para-start": ["ArrowDown", "Home"], "para-middle": ["ArrowDown", "Home"] + ["ArrowRight"] * 6,
    "bullet-start": ["ArrowDown"] * 3 + ["Home"],
}
ROUND1_RANGES = {"range-single": (ROUND1_KEYS["para-middle"], ["ArrowRight"] * 4),
                 "range-cross": (ROUND1_KEYS["para-middle"], ["ArrowRight"] * 16)}


def native_script_to_product(script: str) -> tuple[list[str], list[str], list[str]]:
    """(keys before the range, keys that extend the range, clicks) from a round-2 PLACE script.  Leading
    Ctrl+Home steps are dropped: the open leaves the caret at the document start.  A Shift step is a range
    end the product reaches by a drag between two engine carets."""
    keys, extend, clicks = [], [], []
    for step in script.split(","):
        if not step or step == "-":
            continue
        if step[0] == "k":
            code, _, times = step[1:].partition("x")
            code, times = int(code), int(times or 1)
            if code == (1028 | MOD1):
                if keys or extend:
                    raise PopulationError(f"Ctrl+Home after other steps: {script}")
                continue
            base = code & ~SHIFT
            if base not in KEY or code & MOD1:
                raise PopulationError(f"no product key for step {step} in {script}")
            (extend if code & SHIFT else keys).extend([KEY[base]] * times)
        elif step[0] == "c":
            clicks.append(step[1:])
        elif step[0] == "a":
            x, y = step[1:].split(":")
            clicks.append({"x": int(x), "y": int(y)})
        else:
            raise PopulationError(f"unknown step {step} in {script}")
    return keys, extend, clicks


def rect(text: str) -> list[int]:
    return [int(v) for v in text.split(",")]


def fixture_entry(path: Path) -> dict:
    raw = path.read_bytes()
    entry = {"source": rel(path), "sourceSha256": sha(raw)}
    if path.suffix == ".fodt":
        odt = fodt_to_odt.convert(raw)
        problems = fodt_to_odt.verify(raw, odt)
        if problems:
            raise PopulationError(f"{path.name}: S-6 proof (ii) failed: {problems[:3]}")
        if not cmp.compare(raw, odt)["same"]:
            raise PopulationError(f"{path.name}: the comparator calls the converted ODT different")
        entry.update({"odtName": f"v21-m4-{path.stem}.odt", "odtSha256": sha(odt)})
    else:
        entry.update({"odtName": f"v21-m4-{path.stem}{path.suffix}", "odtSha256": sha(raw)})
    return entry


def m4() -> dict:
    instances, excluded = [], []
    fixtures: dict[str, dict] = {}

    def fixture(path: Path) -> str:
        key = rel(path)
        if key not in fixtures:
            fixtures[key] = fixture_entry(path)
        return key

    # Round 1.
    for folder in sorted((NATIVE / "out").glob("P[1-7]-M[1248]")):
        arm = folder.name
        summary = json.loads((folder / "run1/summary.json").read_text(encoding="utf-8"))
        position_line = next(json.loads(line) for line in (folder / "run1/stdout.jsonl").read_text().splitlines()
                             if '"probe":"position"' in line)
        position = position_line["position"]
        doc = {"P1": "empty-template.odt", "P2": "new-document-en-US_zh-TW_A4.odt"}.get(arm[:2], "positions.fodt")
        base = {"id": "M4-" + arm, "native": rel(folder), "corpus": f"round-1/{arm.split('-')[1]}.md",
                "fixture": fixture(NATIVE / "tool/inputs" / doc),
                "nativeBefore": rel(folder / "run1/before.fodt.gz"), "nativeAfter": rel(folder / "run1/after.fodt.gz")}
        if position_line.get("range"):
            start, extend = ROUND1_RANGES[position]
            instances.append({**base, "class": "range", "startKeys": start, "endKeys": start + extend,
                              "confirm": {"selectionText": summary["positionReadback"]}})
        else:
            if summary.get("undoStepsToRestore") != 1:
                raise PopulationError(f"{arm}: native one Undo did not restore")
            instances.append({**base, "class": "collapsed", "keys": ROUND1_KEYS[position],
                              "confirm": {"afterEqualsNative": base["nativeAfter"]}})
    # Round 2: T1 and T2.
    for folder in sorted((NATIVE / "round-2/out").glob("T[12]-*")):
        arm = folder.name
        summary = json.loads((folder / "run1/summary.json").read_text(encoding="utf-8"))
        spec = summary["positionSpec"]
        corpus_name = summary["arm"]["corpus"]
        corpus = f"round-1/{corpus_name}.md" if (CORPUS / f"round-1/{corpus_name}.md").exists() else None
        rule = None
        undo = summary.get("undo", {})
        flags = spec.get("flags") or "-"
        if "typekey" in flags:
            rule = "a control without a paste (typekey)"
        elif "viewro" in flags:
            rule = "LOK setViewReadOnly, which the product never calls"
        elif spec.get("chmod"):
            rule = "a file mode 0444: the product's read-only open is the host's view-only, refused before queueing"
        elif summary["arm"].get("mime") != cmp_md():
            rule = "not a Markdown paste (text/plain control)"
        elif corpus is None or not _is_pass(corpus):
            rule = "the item is not M0-PASS (M3's)"
        elif arm == "T2-ctl-normal-M2":
            rule = "a duplicate of round 1's P4-M2"
        elif summary.get("afterSameAsBefore") is False and summary.get("undoStepsToRestore") is None:
            rule = "native one Undo does not restore: finding 147, L-md-input-field (spec 9.14)"
        if rule:
            excluded.append({"native": rel(folder), "rule": rule})
            continue
        keys, extend, clicks = native_script_to_product(spec["place"])
        points = {s["step"][1:]: rect(s["rect"]) for s in summary.get("setupSteps", []) if "rect" in s}
        click_rects = []
        for c in clicks:
            if isinstance(c, dict):
                click_rects.append({"x": c["x"], "y": c["y"], "absolute": True})
            else:
                if c not in points:
                    raise PopulationError(f"{arm}: click on an unrecorded point {c}")
                x, y, _w, h = points[c]
                click_rects.append({"x": x, "y": y + h // 2, "absolute": False, "point": c})
        base = {"id": "M4-" + arm, "native": rel(folder), "corpus": corpus,
                "fixture": fixture(REPO / spec["document"]),
                "nativeBefore": rel(folder / "run1/before.fodt.gz"), "nativeAfter": rel(folder / "run1/after.fodt.gz"),
                "clicks": click_rects}
        selection = summary.get("selectionAtPaste") or ""
        if spec["readback"] == "sel" and selection:
            instances.append({**base, "class": "range", "startKeys": keys, "endKeys": keys + extend,
                              "confirm": {"selectionText": summary["positionReadback"]}})
        elif undo.get("countAfter") == undo.get("countBefore") and undo.get("payloadChanged") is False:
            instances.append({**base, "class": "protected", "keys": keys,
                              "confirm": {"caret": rect(summary["cursorAtPaste"])}})
        elif summary.get("undoStepsToRestore") == 1:
            instances.append({**base, "class": "collapsed", "keys": keys,
                              "confirm": {"caret": rect(summary["cursorAtPaste"])}})
        else:
            raise PopulationError(f"{arm}: no rule places it")
    classes = {c: sum(1 for i in instances if i["class"] == c) for c in ("collapsed", "range", "protected")}
    if not all(classes.values()):
        raise PopulationError(f"an empty M4 class: {classes}")
    return {"instances": instances, "excluded": excluded, "fixtures": fixtures, "classCounts": classes}


def cmp_md() -> str:
    return "text/markdown;charset=utf-8"


_PASS = {}


def _is_pass(corpus: str) -> bool:
    if not _PASS:
        _PASS.update({i["path"]: i["verdict"] == "PASS" for i in json.loads(EXPECTED.read_text())["items"]})
    return _PASS.get(corpus, False)


def build() -> dict:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    limit = sdk_limit()
    out = {"generatedBy": "tools/v21_item2_population.py", "fixtureSha256": sha(EXPECTED.read_bytes()),
           "sdkSourceSha256": sha(SDK_SOURCE.read_bytes()), "comparatorSha256": cmp.self_sha256(),
           "readerSha256": cmp.reader_sha256()}
    out.update(m1_m2_m3_m5(expected, limit))
    out["M4"] = m4()
    out["counts"] = {"M1": len(out["M1"]), "M1withReference": sum(1 for i in out["M1"] if i.get("reference")),
                     "M3items": len(out["M3"]["items"]),
                     "M3routes": {r: sum(1 for i in out["M3"]["items"] if r in i["routes"])
                                  for r in ("dialog", "sdk", "bytes")},
                     "M3excluded": len(out["excluded"]), "M4": out["M4"]["classCounts"],
                     "M4excluded": len(out["M4"]["excluded"]), "M5": len(out["M5"])}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    built = build()
    text = json.dumps(built, ensure_ascii=False, indent=1) + "\n"
    if args.check:
        same = args.check.read_text(encoding="utf-8") == text
        print("SAME" if same else "DIFFERENT")
        return 0 if same else 1
    if args.out:
        if args.out.exists():
            raise SystemExit(f"refusing to overwrite {args.out}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(json.dumps(built["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
