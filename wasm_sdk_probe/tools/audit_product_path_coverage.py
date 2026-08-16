#!/usr/bin/env python3
"""Which of the product page's own paths has an automated round ever driven?

Three product defects were found by a person on 2026-08-16 -- findings 049 and
050, and the unbound Ctrl+C -- and not one of them was reachable by any
automated round in this tree, because every harness calls the shell directly.
They were found one at a time, by walking into them.

This turns that into a rule with the same shape the shell bundle uses:

    paths(page) - driven - waived  must be empty

Anything the page has that no harness drives and nobody has waived fails the
audit, so a new handler cannot arrive unaccounted for.  The `uncovered` list in
the registry is the honest middle: paths that are registered as NOT driven, with
the risk written down -- because "we know about it" and "it is covered" are
different claims and this tree has paid for confusing them.

Usage:
  audit_product_path_coverage.py            # audit, exit 1 if unaccounted
  audit_product_path_coverage.py --self-test
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REGISTRY = Path("e2/product-path-coverage.json")

LISTENER = re.compile(r"""(el\.[A-Za-z]+|globalThis)\.addEventListener\(\s*["']([a-z]+)["']""")
ACTION = re.compile(r"""data-action=["']([a-z-]+)["']""")

# `el.<name>` in the page maps to the element it was looked up as; the audit
# names a listener by its event type, and by its element when one element's
# listener is a different product path from another's with the same type.
NAMED_ELEMENTS = {"noticeAction": "notice-action", "fixture": "fixture"}


def page_paths(project: Path, page: Path, markup: Path) -> list[str]:
    """Every path the product page exposes, as the audit names them."""
    source = (project / page).read_text(encoding="utf-8")
    html = (project / markup).read_text(encoding="utf-8")
    paths: set[str] = set()
    for element, event in LISTENER.findall(source):
        name = element.split(".")[-1]
        suffix = f"#{NAMED_ELEMENTS[name]}" if name in NAMED_ELEMENTS else ""
        paths.add(f"listener:{event}{suffix}")
    for action in ACTION.findall(html):
        paths.add(f"action:{action}")
    return sorted(paths)


def audit(project: Path, registry_path: Path = REGISTRY) -> dict:
    registry = json.loads((project / registry_path).read_text(encoding="utf-8"))
    page = Path(registry["auditedPage"])
    markup = page.with_name(page.name.replace("-app.js", ".html"))
    paths = page_paths(project, page, markup)

    driven = {item["path"] for item in registry.get("driven", [])}
    waived = {item["path"] for item in registry.get("waived", [])}
    uncovered = {item["path"] for item in registry.get("uncovered", [])}
    accounted = driven | waived | uncovered

    problems = []
    unaccounted = [p for p in paths if p not in accounted]
    if unaccounted:
        problems.append(
            f"the page has paths nobody has accounted for: {unaccounted}")
    stale = sorted(accounted - set(paths))
    if stale:
        problems.append(
            f"the registry names paths the page does not have: {stale}")
    overlap = sorted((driven & uncovered) | (driven & waived) | (waived & uncovered))
    if overlap:
        problems.append(f"a path is in two lists at once: {overlap}")
    for item in registry.get("driven", []):
        if not str(item.get("by", "")).strip() or not str(item.get("how", "")).strip():
            problems.append(f"driven without a driver or a method: {item['path']}")
    for item in registry.get("waived", []):
        if not str(item.get("reason", "")).strip():
            problems.append(f"waived without a reason: {item['path']}")
    for item in registry.get("uncovered", []):
        if not str(item.get("risk", "")).strip():
            problems.append(f"uncovered without a risk: {item['path']}")

    high = [item["path"] for item in registry.get("uncovered", [])
            if str(item.get("risk", "")).startswith("HIGH")]
    return {
        "schemaVersion": 1,
        "release": "e2-c-product-path-coverage",
        "page": str(page),
        "pathsInPage": len(paths),
        "driven": sorted(driven),
        "uncovered": sorted(uncovered),
        "waived": sorted(waived),
        "highRiskUncovered": sorted(high),
        "problems": problems,
        "ok": not problems,
    }


def self_test(project: Path) -> int:
    """Each way of getting past the rule, tried."""
    failures: list[str] = []
    registry = json.loads((project / REGISTRY).read_text(encoding="utf-8"))

    def check(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    def rejudge(mutate) -> dict:
        cloned = copy.deepcopy(registry)
        mutate(cloned)
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "e2").mkdir()
            (root / "web").mkdir()
            (root / "e2" / REGISTRY.name).write_text(
                json.dumps(cloned), encoding="utf-8")
            page = Path(cloned["auditedPage"])
            markup = page.with_name(page.name.replace("-app.js", ".html"))
            for relative in (page, markup):
                (root / relative).write_bytes((project / relative).read_bytes())
            return audit(root, REGISTRY)

    check("the tree as it stands is accounted for", audit(project)["ok"],
          str(audit(project)["problems"]))

    check("a path removed from the registry is unaccounted for",
          not rejudge(lambda r: r["uncovered"].pop())["ok"])
    check("a registry naming a path the page lost is caught",
          not rejudge(lambda r: r["uncovered"].append(
              {"path": "action:not-in-the-page", "risk": "HIGH"}))["ok"])
    check("driven without a method is not driven",
          not rejudge(lambda r: r["driven"].append(
              {"path": "action:undo", "by": "somebody", "how": ""}))["ok"])
    check("a path cannot be driven and uncovered at once",
          not rejudge(lambda r: r["driven"].append(
              {"path": "action:undo", "by": "x", "how": "y"}))["ok"])
    check("an uncovered path with no risk is not accounted for",
          not rejudge(lambda r: r["uncovered"].append(
              {"path": "listener:focus"}))["ok"])
    # The one that matters most: claiming coverage must be a claim, not a
    # spelling.  A driven entry whose driver does not mention the page cannot be
    # detected here -- said out loud rather than pretended otherwise.
    print("      (not checked: whether the named driver really drives that path;"
          " this audit reads the page, not the harness)")

    print(f"\nself-test: {6 - len(failures)}/6 checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test(PROJECT)
    report = audit(PROJECT)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
