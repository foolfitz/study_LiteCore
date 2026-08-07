#!/usr/bin/env python3
"""Create the frozen R7-C compatibility corpus without modifying LibreOffice core."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


CORE_COMMIT = "671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb"
LIMITS = {
    "maxFileBytes": 5 * 1024 * 1024,
    "maxZipEntries": 2048,
    "maxUncompressedBytes": 64 * 1024 * 1024,
    "maxCompressionRatio": 200,
}
MEDIA_ODT = "application/vnd.oasis.opendocument.text"
MEDIA_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}
for prefix, uri in NS.items():
    ElementTree.register_namespace(prefix, uri)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_valid(manifest_path: Path) -> bool:
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("documents", []):
        path = manifest_path.parent / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"frozen R7-C corpus mismatch: {path}")
    return True


def rewrite_zip(source: Path, output: Path, replacements: dict[str, bytes] | None = None,
                remove: set[str] | None = None, additions: dict[str, bytes] | None = None) -> None:
    replacements = replacements or {}
    remove = remove or set()
    additions = additions or {}
    with zipfile.ZipFile(source) as archive:
        entries = [(info, archive.read(info)) for info in archive.infolist() if info.filename not in remove]
    with zipfile.ZipFile(output, "w") as archive:
        for info, data in entries:
            value = replacements.get(info.filename, data)
            target = zipfile.ZipInfo(info.filename, info.date_time)
            target.compress_type = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
            target.external_attr = info.external_attr
            archive.writestr(target, value)
        existing = {info.filename for info, _ in entries}
        for name, data in additions.items():
            if name not in existing:
                archive.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)


def convert_docx(soffice: str, source: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="r7-c-docx-") as temporary:
        temporary_path = Path(temporary)
        profile = temporary_path / "profile"
        input_path = temporary_path / source.name
        shutil.copyfile(source, input_path)
        command = [
            soffice, "--headless", "--nologo", "--nodefault",
            "--nofirststartwizard", "--norestore",
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--convert-to", "docx:Office Open XML Text",
            "--outdir", str(temporary_path), str(input_path),
        ]
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=180
        )
        generated = temporary_path / f"{source.stem}.docx"
        if completed.returncode != 0 or not generated.is_file():
            raise RuntimeError(f"DOCX conversion failed for {source}: {completed.stdout}\n{completed.stderr}")
        shutil.copyfile(generated, output)
    return {
        "command": command,
        "returnCode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def make_missing_font_odt(source: Path, output: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        styles = ElementTree.fromstring(archive.read("styles.xml"))
    declarations = styles.find("office:font-face-decls", NS)
    if declarations is None:
        declarations = ElementTree.SubElement(styles, f"{{{NS['office']}}}font-face-decls")
    face = ElementTree.SubElement(declarations, f"{{{NS['style']}}}font-face")
    face.set(f"{{{NS['style']}}}name", "R7MissingFont")
    face.set(f"{{{NS['svg']}}}font-family", "R7 Missing Font Fixture")
    styles_section = styles.find("office:styles", NS)
    style = ElementTree.SubElement(styles_section, f"{{{NS['style']}}}style")
    style.set(f"{{{NS['style']}}}name", "R7MissingFontParagraph")
    style.set(f"{{{NS['style']}}}family", "paragraph")
    properties = ElementTree.SubElement(style, f"{{{NS['style']}}}text-properties")
    properties.set(f"{{{NS['style']}}}font-name", "R7MissingFont")
    rewrite_zip(source, output, {"styles.xml": ElementTree.tostring(styles, encoding="utf-8", xml_declaration=True)})


def make_stress_odt(source: Path, image: Path, output: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        content = ElementTree.fromstring(archive.read("content.xml"))
        manifest = ElementTree.fromstring(archive.read("META-INF/manifest.xml"))
    automatic_styles = content.find("office:automatic-styles", NS)
    page_style = ElementTree.SubElement(automatic_styles, f"{{{NS['style']}}}style")
    page_style.set(f"{{{NS['style']}}}name", "R7PageBreak")
    page_style.set(f"{{{NS['style']}}}family", "paragraph")
    page_properties = ElementTree.SubElement(page_style, f"{{{NS['style']}}}paragraph-properties")
    page_properties.set(f"{{{NS['fo']}}}break-before", "page")
    body = content.find("office:body/office:text", NS)
    for child in list(body):
        body.remove(child)
    for page in range(1, 101):
        heading = ElementTree.SubElement(body, f"{{{NS['text']}}}h")
        heading.set(f"{{{NS['text']}}}outline-level", "1")
        if page > 1:
            heading.set(f"{{{NS['text']}}}style-name", "R7PageBreak")
        heading.text = f"R7 stress page {page:03d} 頁面錨點"
        for paragraph in range(1, 4):
            item = ElementTree.SubElement(body, f"{{{NS['text']}}}p")
            item.text = (
                f"第 {page:03d} 頁第 {paragraph} 段：臺灣文件長時間閱讀測試。"
                "English lifecycle anchor 0123456789."
            )
        frame = ElementTree.SubElement(body, f"{{{NS['draw']}}}frame")
        frame.set(f"{{{NS['text']}}}anchor-type", "as-char")
        frame.set(f"{{{NS['svg']}}}width", "4cm")
        frame.set(f"{{{NS['svg']}}}height", "2.25cm")
        picture = ElementTree.SubElement(frame, f"{{{NS['draw']}}}image")
        picture.set(f"{{{NS['xlink']}}}href", "Pictures/r7-test.png")
        picture.set(f"{{{NS['xlink']}}}type", "simple")
        picture.set(f"{{{NS['xlink']}}}show", "embed")
        picture.set(f"{{{NS['xlink']}}}actuate", "onLoad")
    file_entry = ElementTree.SubElement(manifest, f"{{{NS['manifest']}}}file-entry")
    file_entry.set(f"{{{NS['manifest']}}}full-path", "Pictures/r7-test.png")
    file_entry.set(f"{{{NS['manifest']}}}media-type", "image/png")
    rewrite_zip(
        source, output,
        {
            "content.xml": ElementTree.tostring(content, encoding="utf-8", xml_declaration=True),
            "META-INF/manifest.xml": ElementTree.tostring(manifest, encoding="utf-8", xml_declaration=True),
        },
        additions={"Pictures/r7-test.png": image.read_bytes()},
    )


def make_external_relationship_docx(source: Path, output: Path) -> None:
    relationship = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdR7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
    Target="https://example.invalid/r7-external" TargetMode="External"/>
</Relationships>'''
    rewrite_zip(source, output, {"word/_rels/document.xml.rels": relationship})


def entry(identifier: str, path: Path, tier: str, media_type: str, expected_open: str,
          *, source_kind: str, source_path: str, features: list[str], anchors: list[dict[str, Any]],
          expected_code: str | None = None, mutation: str = "read-only",
          degradations: list[str] | None = None, page_count: int | None = None,
          parent: dict[str, str] | None = None, derivation: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": identifier,
        "tier": tier,
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "mediaType": media_type,
        "source": {
            "kind": source_kind,
            "path": source_path,
            "license": "MPL-2.0",
            **({"coreCommit": CORE_COMMIT} if source_kind == "libreoffice-qa" else {}),
        },
        "features": features,
        "expected": {
            "open": expected_open,
            "save": "odt" if mutation != "read-only" and expected_open == "pass" else "none",
            "typedCode": expected_code,
            "degradation": degradations or [],
        },
        "mutationPolicy": mutation,
        "anchors": anchors,
        "limits": {"openMs": 180000},
    }
    if page_count is not None:
        value["expected"]["pageCount"] = page_count
    if parent:
        value["parent"] = parent
    if derivation:
        value["derivation"] = derivation
    return value


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    workspace = project.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=project / "test-docs" / "r7-compat")
    parser.add_argument("--core", type=Path, default=workspace / "libreoffice-26-8")
    parser.add_argument("--soffice", default=shutil.which("soffice") or "soffice")
    args = parser.parse_args()
    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    if frozen_valid(manifest_path):
        print(json.dumps({"manifest": str(manifest_path), "status": "frozen-valid"}))
        return
    output.mkdir(parents=True, exist_ok=True)

    generated: list[dict[str, Any]] = []
    conversion_logs: dict[str, Any] = {}
    sources = {
        "l0-t1-plain-zh.odt": project / "test-docs" / "t1-plain-zh.odt",
        "l0-t2-styled.odt": project / "test-docs" / "t2-styled.odt",
        "l0-t3-long.odt": project / "test-docs" / "t3-long.odt",
        "l1-plain.odt": project / "test-docs" / "r7" / "r7-plain.odt",
        "l1-layout-table-image.odt": project / "test-docs" / "t2-styled.odt",
        "l1-review.odt": args.core / "sw/qa/filter/md/data/redlines-and-comments.odt",
    }
    for name, source in sources.items():
        shutil.copyfile(source, output / name)
    make_missing_font_odt(
        args.core / "sw/qa/extras/tiledrendering/data/hyperlink.odt",
        output / "l1-hyperlink-font.odt",
    )
    for stem in ("l1-plain", "l1-layout-table-image", "l1-review", "l1-hyperlink-font"):
        conversion_logs[stem] = convert_docx(
            args.soffice, output / f"{stem}.odt", output / f"{stem}.docx"
        )

    qa_sources = {
        "l2-qa-comments-on-load.docx": "sw/qa/extras/tiledrendering/data/comments-on-load.docx",
        "l2-qa-redline-range-comment.docx": "sw/qa/writerfilter/dmapper/data/redline-range-comment.docx",
        "l2-qa-image-lazy-read.docx": "sw/qa/extras/ooxmlimport/data/image-lazy-read.docx",
        "l2-qa-subsetted-embedded-font.docx": "sw/qa/writerfilter/dmapper/data/subsetted-embedded-font.docx",
        "l2-qa-hyperlink.odt": "sw/qa/extras/tiledrendering/data/hyperlink.odt",
        "l2-qa-redlines-and-comments.odt": "sw/qa/filter/md/data/redlines-and-comments.odt",
    }
    for name, relative in qa_sources.items():
        shutil.copyfile(args.core / relative, output / name)

    plain_odt = output / "l1-plain.odt"
    plain_docx = output / "l1-plain.docx"
    (output / "l3-truncated.odt").write_bytes(plain_odt.read_bytes()[:-257])
    (output / "l3-truncated.docx").write_bytes(plain_docx.read_bytes()[:-257])
    bad = bytearray(plain_odt.read_bytes())
    eocd = bad.rfind(b"PK\x05\x06")
    if eocd < 0:
        raise RuntimeError("ODT EOCD not found")
    bad[eocd:eocd + 4] = b"BADC"
    (output / "l3-bad-central-directory.odt").write_bytes(bad)
    rewrite_zip(plain_odt, output / "l3-missing-content-xml.odt", remove={"content.xml"})
    shutil.copyfile(plain_docx, output / "l3-docx-disguised-as-odt.odt")
    (output / "l3-unknown.bin").write_bytes(b"R7-C unsupported deterministic bytes\n\x00\x01\xff")
    (output / "l3-too-large.bin").write_bytes(b"R7-C" + b"L" * LIMITS["maxFileBytes"])
    rewrite_zip(
        plain_odt, output / "l3-too-many-entries.odt",
        additions={f"R7Entries/{index:04d}.txt": b"" for index in range(LIMITS["maxZipEntries"] + 1)},
    )
    rewrite_zip(
        plain_odt, output / "l3-high-ratio.odt",
        additions={"R7Ratio/repeated.bin": b"0" * (8 * 1024 * 1024)},
    )
    make_external_relationship_docx(plain_docx, output / "l3-external-relationship.docx")
    make_stress_odt(
        project / "test-docs" / "t1-plain-zh.odt",
        project / "assets" / "r1-test-image.png",
        output / "l4-stress-100.odt",
    )

    def add(*args: Any, **kwargs: Any) -> None:
        generated.append(entry(*args, **kwargs))

    add("l0-t1", output / "l0-t1-plain-zh.odt", "L0", MEDIA_ODT, "pass",
        source_kind="project-generated", source_path="wasm_sdk_probe/test-docs/t1-plain-zh.odt",
        features=["plain", "cjk"], anchors=[{"text": "Final line：ODT round-trip 完整性檢查。", "count": 1}],
        mutation="append-and-save", page_count=1)
    add("l0-t2", output / "l0-t2-styled.odt", "L0", MEDIA_ODT, "pass",
        source_kind="project-generated", source_path="wasm_sdk_probe/test-docs/t2-styled.odt",
        features=["styles", "table", "image", "comment"], anchors=[{"text": "文件結尾：請確認表格、圖片、註解與標題樣式均保留。", "count": 1}],
        degradations=["finding-012-known-discovery-sequence"], page_count=3)
    add("l0-t3", output / "l0-t3-long.odt", "L0", MEDIA_ODT, "pass",
        source_kind="project-generated", source_path="wasm_sdk_probe/test-docs/t3-long.odt",
        features=["long-document"], anchors=[{"text": "第 1 頁：長文件記憶體與效能測試", "count": 1}, {"text": "第 22 頁：長文件記憶體與效能測試", "count": 1}],
        page_count=22)

    pair_definitions = [
        ("plain", ["plain", "cjk"], [{"text": "Final line：ODT round-trip 完整性檢查。", "count": 1}], []),
        ("layout-table-image", ["styles", "table", "image", "comment"], [{"text": "文件結尾：請確認表格、圖片、註解與標題樣式均保留。", "count": 1}], []),
        ("review", ["comments", "tracked-changes"], [{"text": "Lorem ipsum", "count": 1}], []),
        ("hyperlink-font", ["hyperlink", "missing-font"], [{"text": "Normal text, hyperlink", "count": 1}], ["font-not-observable"]),
    ]
    for stem, features, anchors, degradations in pair_definitions:
        odt = output / f"l1-{stem}.odt"
        docx = output / f"l1-{stem}.docx"
        add(f"l1-{stem}-odt", odt, "L1", MEDIA_ODT, "pass",
            source_kind="project-derived", source_path=str(sources.get(f"l1-{stem}.odt", "LibreOffice QA derived ODT")),
            features=features, anchors=anchors, mutation="append-and-save" if stem == "plain" else "read-only",
            degradations=degradations)
        add(f"l1-{stem}-docx", docx, "L1", MEDIA_DOCX, "typed-failure",
            source_kind="desktop-converted", source_path=f"l1-{stem}.odt",
            features=features, anchors=anchors, expected_code="UNSUPPORTED_FORMAT",
            degradations=["finding-013-public-docx-unsupported", *degradations])

    qa_anchors = {
        "l2-qa-comments-on-load.docx": [{"text": "end of the line?", "count": 1}],
        "l2-qa-redline-range-comment.docx": [{"text": "Aaa", "count": 1}],
        "l2-qa-image-lazy-read.docx": [],
        "l2-qa-subsetted-embedded-font.docx": [{"text": "MASTER SERVICES AGREEMENT", "count": 1}],
        "l2-qa-hyperlink.odt": [{"text": "Normal text, hyperlink", "count": 1}],
        "l2-qa-redlines-and-comments.odt": [{"text": "Lorem ipsum", "count": 1}],
    }
    for name, relative in qa_sources.items():
        is_docx = name.endswith(".docx")
        features = [
            feature for feature in ("comments", "redline", "image", "embedded-font", "hyperlink")
            if feature.replace("-", "") in name.replace("-", "")
        ] or ["qa-regression"]
        add(name.rsplit(".", 1)[0], output / name, "L2", MEDIA_DOCX if is_docx else MEDIA_ODT,
            "typed-failure" if is_docx else "pass",
            source_kind="libreoffice-qa", source_path=relative, features=features,
            anchors=qa_anchors[name], expected_code="UNSUPPORTED_FORMAT" if is_docx else None,
            degradations=["finding-013-public-docx-unsupported"] if is_docx else [])

    parent_odt = {"path": plain_odt.name, "sha256": sha256(plain_odt)}
    parent_docx = {"path": plain_docx.name, "sha256": sha256(plain_docx)}
    negatives = [
        ("l3-truncated-odt", "l3-truncated.odt", MEDIA_ODT, "CORRUPT_DOCUMENT", parent_odt, "remove final 257 bytes"),
        ("l3-truncated-docx", "l3-truncated.docx", MEDIA_DOCX, "UNSUPPORTED_FORMAT", parent_docx, "remove final 257 bytes; format remains outside public capability"),
        ("l3-bad-central", "l3-bad-central-directory.odt", MEDIA_ODT, "CORRUPT_DOCUMENT", parent_odt, "replace EOCD signature with BADC"),
        ("l3-missing-content", "l3-missing-content-xml.odt", MEDIA_ODT, "CORRUPT_DOCUMENT", parent_odt, "remove content.xml and rebuild ZIP"),
        ("l3-format-mismatch", "l3-docx-disguised-as-odt.odt", MEDIA_ODT, "UNSUPPORTED_FORMAT", parent_docx, "copy DOCX bytes with ODT basename"),
        ("l3-unknown", "l3-unknown.bin", "application/octet-stream", "UNSUPPORTED_FORMAT", None, "literal deterministic bytes"),
        ("l3-too-large", "l3-too-large.bin", "application/octet-stream", "DOCUMENT_TOO_LARGE", None, "literal maxFileBytes plus deterministic prefix"),
        ("l3-entry-limit", "l3-too-many-entries.odt", MEDIA_ODT, "DOCUMENT_TOO_LARGE", parent_odt, "add maxZipEntries plus one deterministic empty entries"),
        ("l3-ratio-limit", "l3-high-ratio.odt", MEDIA_ODT, "DOCUMENT_TOO_LARGE", parent_odt, "add eight MiB repeated zero payload"),
        ("l3-external", "l3-external-relationship.docx", MEDIA_DOCX, "UNSUPPORTED_FORMAT", parent_docx, "replace document relationships with deterministic external hyperlink"),
    ]
    for identifier, name, media, code, parent, recipe in negatives:
        add(identifier, output / name, "L3", media, "typed-failure",
            source_kind="derived-negative", source_path=parent["path"] if parent else "literal",
            features=["negative"], anchors=[], expected_code=code, parent=parent, derivation=recipe)

    add("l4-stress-100", output / "l4-stress-100.odt", "L4", MEDIA_ODT, "pass",
        source_kind="project-derived", source_path="t1-plain-zh.odt + assets/r1-test-image.png",
        features=["100-pages", "cjk", "image", "stress"],
        anchors=[{"text": "R7 stress page 001 頁面錨點", "count": 1}, {"text": "R7 stress page 050 頁面錨點", "count": 1}, {"text": "R7 stress page 100 頁面錨點", "count": 1}],
        page_count=100)

    manifest = {
        "schemaVersion": 2,
        "release": "R7-C",
        "frozenDate": "2026-08-03",
        "scope": "ODT-first; DOCX is typed unsupported by finding 013",
        "limits": LIMITS,
        "generator": {
            "scriptSha256": sha256(Path(__file__)),
            "soffice": subprocess.run([args.soffice, "--version"], check=True, capture_output=True, text=True).stdout.strip(),
            "coreCommit": CORE_COMMIT,
            "conversionLogs": conversion_logs,
            "rawUnoUsed": False,
        },
        "documents": generated,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "documents": len(generated)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
