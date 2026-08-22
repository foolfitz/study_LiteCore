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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import sha256  # noqa: E402
from run_e2_c_d0 import artifact_hashes  # noqa: E402

# Which profile a pinned reason is judged against.  The product page is served
# from this profile, so "the shipped artifact" in a registry reason means this.
BINDING_PROFILE = "e2-editor-v3"


def live_bindings(profile: str = BINDING_PROFILE) -> dict[str, str]:
    """The hashes a reason may be pinned to, each COMPUTED from its file.

    Deliberately not read from the profile's own sdk-manifest.json: a manifest
    that merely CLAIMS a hash is exactly what this tree has been bitten by, and
    a binding check that trusts the thing it is checking is not a check.

    `artifact_hashes` is imported rather than reimplemented -- it is the same
    function D0 freezes the matrix with, so a reason and the matrix cannot drift
    apart by being hashed two different ways.
    """
    directory = PROJECT / "dist" / "profiles" / profile
    if not directory.is_dir():
        return {}
    bindings = dict(artifact_hashes(profile))
    bindings.pop("profile", None)
    manifest = directory / "sdk-manifest.json"
    if manifest.is_file():
        bindings["manifestSha256"] = sha256(manifest)
    return bindings

LISTENER = re.compile(r"""(el\.[A-Za-z]+|globalThis)\.addEventListener\(\s*["']([a-z]+)["']""")
ACTION = re.compile(r"""data-action=["']([a-z-]+)["']""")

# `el.<name>` in the page maps to the element it was looked up as; the audit
# names a listener by its event type, and by its element when one element's
# listener is a different product path from another's with the same type.
# `openFile` earns a name for a reason worth stating: without it, the open
# button's click collapses into the toolbar's `listener:click` and the audit
# reports full coverage of a path nothing drives.  A path that hides inside
# another path is the failure this audit exists to prevent.
NAMED_ELEMENTS = {"noticeAction": "notice-action", "fixture": "fixture",
                  "openFile": "open-file", "file": "file",
                  "clearFormat": "clear-format"}


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


def audit(project: Path, registry_path: Path = REGISTRY,
          bindings: dict[str, str] | None = None) -> dict:
    registry = json.loads((project / registry_path).read_text(encoding="utf-8"))
    if bindings is None:
        bindings = live_bindings()
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

    # A REASON CAN EXPIRE, AND THE REGISTRY COULD NOT NOTICE.
    #
    # `listener:click#clear-format` was registered as not-driven "because
    # finding 059 has every one of those failing on the shipped artifact".  That
    # reason was written against artifact d538ce0b; the binding moved to
    # 296f3ea7 and then 29ec627b, and 059's fix shipped in the first of those.
    # The audit went on reporting ok:true, because it only ever asked whether a
    # path was ACCOUNTED FOR -- never whether the account still held.
    #
    # Optional and typed, both on purpose.  Optional because most reasons here
    # are structural (a browser takes the pointer away; the OS file chooser
    # needs a human) and do not expire when an artifact moves -- binding all of
    # them would manufacture a false expiry on every relink.  Typed because
    # product-path identity is five hashes, not one (SPEC E2-C 11.3), so a
    # reason about engine behaviour pins the wasm and one about a worker
    # allowlist pins the worker.
    stale_reasons = []
    for kind in ("uncovered", "waived"):
        for item in registry.get(kind, []):
            pinned = item.get("reasonBoundTo") or {}
            if not isinstance(pinned, dict):
                problems.append(
                    f"reasonBoundTo must be an object of hashes: {item['path']}")
                continue
            for key, expected in pinned.items():
                if key not in bindings:
                    problems.append(
                        f"{item['path']} pins `{key}`, which this audit cannot "
                        f"evaluate (known: {sorted(bindings)})")
                elif bindings[key] != expected:
                    stale_reasons.append(item["path"])
                    problems.append(
                        f"the reason for {item['path']} is pinned to "
                        f"{key} {expected[:16]}… and the tree is on "
                        f"{bindings[key][:16]}…: it was written about an "
                        f"artifact that is gone, so it can no longer support "
                        f"leaving this path undriven. Re-measure and either "
                        f"re-pin it or drive the path.")

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
        "staleReasons": sorted(set(stale_reasons)),
        "bindingsChecked": sorted(bindings),
        "problems": problems,
        "ok": not problems,
    }


def self_test(project: Path) -> int:
    """Each way of getting past the rule, tried."""
    failures: list[str] = []
    registry = json.loads((project / REGISTRY).read_text(encoding="utf-8"))
    bindings = live_bindings()

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
            return audit(root, REGISTRY, bindings=bindings)

    # Split from the expiry rule below on purpose.  The ACCOUNTING rule
    # (paths - driven - waived is empty) and the EXPIRY rule (a pinned reason
    # still describes the tree) fail for different reasons and must not mask
    # each other: a declared, expected expiry may NOT make the audit stop
    # noticing an unaccounted path.
    live = audit(project)
    accounting = [p for p in live["problems"]
                  if not any(path in p for path in live["staleReasons"])]
    check("the tree as it stands is accounted for", not accounting,
          str(accounting))
    if live["staleReasons"]:
        print(f"      (expected red: {live['staleReasons']} -- a pinned reason "
              f"outlived its artifact; this is the rule working, not failing)")

    check("a path removed from the registry is unaccounted for",
          not rejudge(lambda r: r["uncovered"].pop())["ok"])
    check("a registry naming a path the page lost is caught",
          not rejudge(lambda r: r["uncovered"].append(
              {"path": "action:not-in-the-page", "risk": "HIGH"}))["ok"])
    check("driven without a method is not driven",
          not rejudge(lambda r: r["driven"].append(
              {"path": "action:undo", "by": "somebody", "how": ""}))["ok"])
    # DERIVED, not named.  This mutation has gone stale twice by naming a path
    # that later moved into `driven` -- once with `action:undo`, once with
    # `listener:click#notice-action` -- and each time it went green for the
    # wrong reason: it was adding a duplicate to `driven` instead of creating
    # the overlap it exists to detect.  Taking whatever is uncovered right now
    # cannot go stale, and the guard below says so if nothing is.
    check("there is an uncovered path to build the overlap mutation from",
          bool(registry.get("uncovered")))
    if registry.get("uncovered"):
        overlapping = registry["uncovered"][0]["path"]
        check("a path cannot be driven and uncovered at once",
              not rejudge(lambda r: r["driven"].append(
                  {"path": overlapping, "by": "x", "how": "y"}))["ok"],
              overlapping)
    check("an uncovered path with no risk is not accounted for",
          not rejudge(lambda r: r["uncovered"].append(
              {"path": "listener:focus"}))["ok"])
    # The one that matters most: claiming coverage must be a claim, not a
    # spelling.  A driven entry whose driver does not mention the page cannot be
    # detected here -- said out loud rather than pretended otherwise.
    # The expiry rule, each direction.  Built from whatever is uncovered right
    # now for the same reason the overlap mutation is: a named path goes stale.
    check("the profile on disk yields bindings to pin against", bool(bindings),
          "no dist/profiles/%s -- the expiry rule cannot run" % BINDING_PROFILE)
    if bindings and registry.get("uncovered"):
        target = registry["uncovered"][0]["path"]
        wrong = {"wasmSha256": "0" * 64}
        right = {"wasmSha256": bindings["wasmSha256"]}

        # Every case below first STRIPS the pins the real registry carries, so
        # it measures its own axis and not whatever the tree happens to be
        # declaring today.  Without this, a genuine expiry standing in the
        # registry makes three of these cases red for the wrong reason -- which
        # is how a self-test starts reporting the tree instead of the rule.
        def pin(value=None, path=None):
            def mutate(r):
                for kind in ("uncovered", "waived"):
                    for item in r.get(kind, []):
                        item.pop("reasonBoundTo", None)
                if value is not None:
                    for item in r["uncovered"]:
                        if item["path"] == (path or target):
                            item["reasonBoundTo"] = value
            return mutate

        check("a reason pinned to an artifact that is gone goes red",
              not rejudge(pin(wrong))["ok"], target)
        check("a reason pinned to the current artifact does not",
              rejudge(pin(right))["ok"],
              str(rejudge(pin(right))["problems"]))
        check("a reason pinning a hash this audit cannot evaluate goes red",
              not rejudge(pin({"noSuchSha256": "x"}))["ok"], target)
        check("reasonBoundTo must be an object, not a bare string",
              not rejudge(pin("d538ce0b"))["ok"], target)
        check("a path with no reasonBoundTo is judged exactly as before",
              rejudge(pin())["ok"], str(rejudge(pin())["problems"]))

    print("      (not checked: whether the named driver really drives that path;"
          " this audit reads the page, not the harness)")

    print(f"\nself-test: {12 - len(failures)}/12 checks moved the verdict")
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
