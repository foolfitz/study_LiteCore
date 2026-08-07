#!/usr/bin/env python3
"""Create deterministic ODF feature combinations for finding 012.

This is a package-level diagnostic generator.  It deliberately does not use
UNO, LibreOffice internals, or the WebAssembly SDK to alter the source bytes.
Desktop LibreOffice is used only as an independent open/PDF validator.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


FEATURES = ("table", "image", "annotation", "page-break")
IMAGE_AXIS_VARIANTS = (
    ("t2-original", ()),
    ("t2-image-no-mime", ("image.mime-type",)),
    ("t2-image-no-style-ref", ("frame.style-ref",)),
    ("t2-image-no-name-zindex", ("frame.identity",)),
    ("t2-image-no-clip", ("graphic-style.clip",)),
    ("t2-image-no-graphic-properties", ("graphic-style.properties",)),
    ("t2-image-unwrapped", ("frame.wrapper",)),
    ("t2-image-l4-geometry", ("frame.geometry",)),
    (
        "t2-image-l4-like-frame",
        (
            "image.mime-type",
            "frame.style-ref",
            "frame.identity",
            "frame.wrapper",
            "frame.geometry",
        ),
    ),
)
NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "manifest": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
}
for prefix, uri in NS.items():
    ElementTree.register_namespace(prefix, uri)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _remove_elements(root: ElementTree.Element, tag: str) -> int:
    parents = {child: parent for parent in root.iter() for child in parent}
    removed = 0
    for element in list(root.iter(tag)):
        parent = parents.get(element)
        if parent is None:
            continue
        # Preserve any text following the removed element.
        if element.tail:
            previous = list(parent).index(element) - 1
            if previous >= 0:
                sibling = list(parent)[previous]
                sibling.tail = (sibling.tail or "") + element.tail
            else:
                parent.text = (parent.text or "") + element.tail
        parent.remove(element)
        removed += 1
    return removed


def transform_content(raw: bytes, retained: set[str]) -> tuple[bytes, dict[str, int]]:
    root = ElementTree.fromstring(raw)
    changes = {feature: 0 for feature in FEATURES}
    if "table" not in retained:
        changes["table"] = _remove_elements(root, f"{{{NS['table']}}}table")
    if "image" not in retained:
        changes["image"] = _remove_elements(root, f"{{{NS['draw']}}}frame")
    if "annotation" not in retained:
        changes["annotation"] = _remove_elements(root, f"{{{NS['office']}}}annotation")
    if "page-break" not in retained:
        attribute = f"{{{NS['fo']}}}break-before"
        for properties in root.iter(f"{{{NS['style']}}}paragraph-properties"):
            if properties.get(attribute) == "page":
                del properties.attrib[attribute]
                changes["page-break"] += 1
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True), changes


def transform_manifest(raw: bytes, retained: set[str]) -> bytes:
    if "image" in retained:
        return raw
    root = ElementTree.fromstring(raw)
    path_attribute = f"{{{NS['manifest']}}}full-path"
    for entry in list(root):
        if (entry.get(path_attribute) or "").startswith("Pictures/"):
            root.remove(entry)
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def write_variant(source: Path, output: Path, retained: set[str]) -> dict[str, int]:
    if retained == set(FEATURES):
        shutil.copyfile(source, output)
        return {feature: 0 for feature in FEATURES}
    changes: dict[str, int] = {}
    with zipfile.ZipFile(source) as source_archive, zipfile.ZipFile(output, "w") as target:
        for info in source_archive.infolist():
            if "image" not in retained and info.filename.startswith("Pictures/"):
                continue
            raw = source_archive.read(info.filename)
            if info.filename == "content.xml":
                raw, changes = transform_content(raw, retained)
            elif info.filename == "META-INF/manifest.xml":
                raw = transform_manifest(raw, retained)
            target.writestr(info, raw)
    return changes


def transform_image_axis_content(raw: bytes, changed_axes: tuple[str, ...]) -> bytes:
    root = ElementTree.fromstring(raw)
    frames = list(root.iter(f"{{{NS['draw']}}}frame"))
    images = list(root.iter(f"{{{NS['draw']}}}image"))
    if len(frames) != 1 or len(images) != 1:
        raise ValueError(f"expected one frame/image, got {len(frames)}/{len(images)}")
    frame = frames[0]
    image = images[0]

    if "image.mime-type" in changed_axes:
        image.attrib.pop(f"{{{NS['draw']}}}mime-type", None)
    if "frame.style-ref" in changed_axes:
        frame.attrib.pop(f"{{{NS['draw']}}}style-name", None)
    if "frame.identity" in changed_axes:
        frame.attrib.pop(f"{{{NS['draw']}}}name", None)
        frame.attrib.pop(f"{{{NS['draw']}}}z-index", None)
    if "graphic-style.clip" in changed_axes:
        for properties in root.iter(f"{{{NS['style']}}}graphic-properties"):
            properties.attrib.pop(f"{{{NS['fo']}}}clip", None)
    if "graphic-style.properties" in changed_axes:
        parents = {child: parent for parent in root.iter() for child in parent}
        for properties in list(root.iter(f"{{{NS['style']}}}graphic-properties")):
            parent = parents.get(properties)
            if parent is not None and parent.get(f"{{{NS['style']}}}name") == "fr1":
                parent.remove(properties)
    if "frame.geometry" in changed_axes:
        frame.set(f"{{{NS['svg']}}}width", "4cm")
        frame.set(f"{{{NS['svg']}}}height", "2.25cm")
    if "frame.wrapper" in changed_axes:
        parents = {child: parent for parent in root.iter() for child in parent}
        paragraph = parents.get(frame)
        body = parents.get(paragraph) if paragraph is not None else None
        if (
            paragraph is None
            or paragraph.tag != f"{{{NS['text']}}}p"
            or body is None
            or body.tag != f"{{{NS['office']}}}text"
        ):
            raise ValueError("expected image frame inside a direct text:p wrapper")
        index = list(body).index(paragraph)
        paragraph.remove(frame)
        frame.tail = paragraph.tail
        body.remove(paragraph)
        body.insert(index, frame)

    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def write_image_axis_variant(
    source: Path, output: Path, changed_axes: tuple[str, ...]
) -> None:
    if not changed_axes:
        shutil.copyfile(source, output)
        return
    with zipfile.ZipFile(source) as source_archive, zipfile.ZipFile(output, "w") as target:
        for info in source_archive.infolist():
            raw = source_archive.read(info.filename)
            if info.filename == "content.xml":
                raw = transform_image_axis_content(raw, changed_axes)
            target.writestr(info, raw)


def image_axis_validation(path: Path, changed_axes: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "zip": False,
        "crc": False,
        "xml": False,
        "axisChecks": {},
        "embeddedImageSha256": None,
        "pass": False,
    }
    try:
        with zipfile.ZipFile(path) as archive:
            result["zip"] = True
            result["crc"] = archive.testzip() is None
            for name in archive.namelist():
                if name.endswith(".xml"):
                    ElementTree.fromstring(archive.read(name))
            result["xml"] = True
            content = ElementTree.fromstring(archive.read("content.xml"))
            frame = next(content.iter(f"{{{NS['draw']}}}frame"))
            image = next(content.iter(f"{{{NS['draw']}}}image"))
            parents = {child: parent for parent in content.iter() for child in parent}
            graphic_properties = [
                properties
                for style in content.iter(f"{{{NS['style']}}}style")
                if style.get(f"{{{NS['style']}}}name") == "fr1"
                for properties in style.findall(f"{{{NS['style']}}}graphic-properties")
            ]
            checks = {
                "image.mime-type": image.get(f"{{{NS['draw']}}}mime-type") is None,
                "frame.style-ref": frame.get(f"{{{NS['draw']}}}style-name") is None,
                "frame.identity": frame.get(f"{{{NS['draw']}}}name") is None
                and frame.get(f"{{{NS['draw']}}}z-index") is None,
                "graphic-style.clip": bool(graphic_properties)
                and all(properties.get(f"{{{NS['fo']}}}clip") is None for properties in graphic_properties),
                "graphic-style.properties": not graphic_properties,
                "frame.wrapper": parents.get(frame) is not None
                and parents[frame].tag == f"{{{NS['office']}}}text",
                "frame.geometry": frame.get(f"{{{NS['svg']}}}width") == "4cm"
                and frame.get(f"{{{NS['svg']}}}height") == "2.25cm",
            }
            result["axisChecks"] = {axis: checks[axis] for axis in changed_axes}
            picture_paths = [name for name in archive.namelist() if name.startswith("Pictures/")]
            if len(picture_paths) == 1:
                result["embeddedImageSha256"] = hashlib.sha256(
                    archive.read(picture_paths[0])
                ).hexdigest()
            result["pass"] = (
                result["crc"]
                and result["xml"]
                and len(picture_paths) == 1
                and all(result["axisChecks"].values())
            )
    except (KeyError, StopIteration, zipfile.BadZipFile, ElementTree.ParseError) as error:
        result["error"] = {"name": type(error).__name__, "message": str(error)}
    return result


def create_image_axis_corpus(
    source: Path, output: Path, *, validate_desktop: bool = True
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    variants = []
    for identifier, changed_axes in IMAGE_AXIS_VARIANTS:
        path = output / f"{identifier}.odt"
        write_image_axis_variant(source, path, changed_axes)
        package = image_axis_validation(path, changed_axes)
        variants.append({
            "id": identifier,
            "path": path.name,
            "changedAxes": list(changed_axes),
            "retainedFeatures": list(FEATURES),
            "removedFeatures": [],
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "packageValidation": package,
            "expectedClose": "discovery",
        })
    desktop = desktop_validate([output / item["path"] for item in variants]) if validate_desktop else {}
    for item in variants:
        item["desktopValidation"] = desktop.get(item["path"], {"status": "not-run", "pass": None})
    with zipfile.ZipFile(source) as archive:
        picture_paths = [name for name in archive.namelist() if name.startswith("Pictures/")]
        if len(picture_paths) != 1:
            raise ValueError(f"expected one embedded image, got {len(picture_paths)}")
        embedded_image = {
            "path": picture_paths[0],
            "bytes": len(archive.read(picture_paths[0])),
            "sha256": hashlib.sha256(archive.read(picture_paths[0])).hexdigest(),
        }
    manifest = {
        "schemaVersion": 1,
        "release": "finding-012-r7-image-axis",
        "axis": "t2-styled-image-object",
        "source": {"path": str(source), "bytes": source.stat().st_size, "sha256": sha256(source)},
        "embeddedImage": embedded_image,
        "recipe": "one declared ODF image-object axis per variant; no UNO; source ZIP metadata retained",
        "variants": variants,
        "pass": len(variants) == len(IMAGE_AXIS_VARIANTS)
        and all(item["packageValidation"]["pass"] for item in variants)
        and (not validate_desktop or all(item["desktopValidation"]["pass"] for item in variants)),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def package_validation(path: Path, retained: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {"zip": False, "crc": False, "xml": False, "features": {}, "pass": False}
    try:
        with zipfile.ZipFile(path) as archive:
            result["zip"] = True
            result["crc"] = archive.testzip() is None
            for name in archive.namelist():
                if name.endswith(".xml"):
                    ElementTree.fromstring(archive.read(name))
            result["xml"] = True
            content = ElementTree.fromstring(archive.read("content.xml"))
            observed = {
                "table": next(content.iter(f"{{{NS['table']}}}table"), None) is not None,
                "image": next(content.iter(f"{{{NS['draw']}}}frame"), None) is not None,
                "annotation": next(content.iter(f"{{{NS['office']}}}annotation"), None) is not None,
                "page-break": any(
                    node.get(f"{{{NS['fo']}}}break-before") == "page"
                    for node in content.iter(f"{{{NS['style']}}}paragraph-properties")
                ),
            }
            result["features"] = observed
            result["pass"] = result["crc"] and result["xml"] and all(
                observed[feature] is (feature in retained) for feature in FEATURES
            )
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        result["error"] = {"name": type(error).__name__, "message": str(error)}
    return result


def variant_id(retained: tuple[str, ...]) -> str:
    if set(retained) == set(FEATURES):
        return "t2-original"
    return "t2-keep-" + ("-".join(feature.replace("-", "") for feature in retained) or "none")


def desktop_validate(paths: list[Path]) -> dict[str, dict[str, Any]]:
    soffice = shutil.which("soffice") or "soffice"
    pdfinfo = shutil.which("pdfinfo") or "pdfinfo"
    version = subprocess.run(
        [soffice, "--version"], check=False, capture_output=True, text=True, timeout=30
    ).stdout.strip()
    results: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="finding-012-desktop-") as temporary:
        root = Path(temporary)
        profile = root / "profile"
        command = [
            soffice, "--headless", "--nologo", "--nodefault", "--nofirststartwizard", "--norestore",
            f"-env:UserInstallation={profile.resolve().as_uri()}",
            "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(root),
            *[str(path.resolve()) for path in paths],
        ]
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=300
        )
        for path in paths:
            pdf = root / f"{path.stem}.pdf"
            info = subprocess.run(
                [pdfinfo, str(pdf)], check=False, capture_output=True, text=True, timeout=30
            ) if pdf.is_file() else None
            pages = None
            if info and info.returncode == 0:
                for line in info.stdout.splitlines():
                    if line.startswith("Pages:"):
                        pages = int(line.split(":", 1)[1].strip())
                        break
            results[path.name] = {
                "desktopVersion": version,
                "batchReturnCode": completed.returncode,
                "pdfGenerated": pdf.is_file() and pdf.stat().st_size > 0,
                "pages": pages,
                "pass": completed.returncode == 0 and pdf.is_file()
                and pdf.stat().st_size > 0 and info is not None and info.returncode == 0,
            }
    return results


def create_corpus(
    source: Path, output: Path, *, validate_desktop: bool = True, axis: str = "features"
) -> dict[str, Any]:
    if axis == "image":
        return create_image_axis_corpus(source, output, validate_desktop=validate_desktop)
    if axis != "features":
        raise ValueError(f"unsupported finding 012 axis: {axis}")
    output.mkdir(parents=True, exist_ok=True)
    variants = []
    for count in range(len(FEATURES) + 1):
        for retained_tuple in itertools.combinations(FEATURES, count):
            retained = set(retained_tuple)
            identifier = variant_id(retained_tuple)
            path = output / f"{identifier}.odt"
            changes = write_variant(source, path, retained)
            package = package_validation(path, retained)
            variants.append({
                "id": identifier,
                "path": path.name,
                "retainedFeatures": list(retained_tuple),
                "removedFeatures": [feature for feature in FEATURES if feature not in retained],
                "changes": changes,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "packageValidation": package,
                "expectedClose": "discovery",
            })
    variants.sort(key=lambda item: (len(item["retainedFeatures"]), item["id"]))
    desktop = desktop_validate([output / item["path"] for item in variants]) if validate_desktop else {}
    for item in variants:
        item["desktopValidation"] = desktop.get(item["path"], {"status": "not-run", "pass": None})
    manifest = {
        "schemaVersion": 1,
        "release": "finding-012-r7-minimization",
        "source": {
            "path": str(source), "bytes": source.stat().st_size, "sha256": sha256(source),
        },
        "features": list(FEATURES),
        "recipe": "package-level ODF XML removal; no UNO; source ZIP metadata retained",
        "variants": variants,
        "pass": len(variants) == 16
        and all(item["packageValidation"]["pass"] for item in variants)
        and (not validate_desktop or all(item["desktopValidation"]["pass"] for item in variants)),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=project / "test-docs" / "t2-styled.odt")
    parser.add_argument("--output", type=Path, default=project / "test-docs" / "r7-finding-012")
    parser.add_argument("--axis", choices=("features", "image"), default="features")
    parser.add_argument("--skip-desktop", action="store_true")
    args = parser.parse_args()
    manifest = create_corpus(
        args.source,
        args.output,
        validate_desktop=not args.skip_desktop,
        axis=args.axis,
    )
    print(json.dumps({
        "output": str(args.output / "manifest.json"),
        "variants": len(manifest["variants"]), "pass": manifest["pass"],
    }, ensure_ascii=False, indent=2))
    if not manifest["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
