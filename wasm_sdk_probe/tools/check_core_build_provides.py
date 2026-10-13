#!/usr/bin/env python3
"""Does the CORE build we link against actually provide what the product claims?

Written 2026-08-17, after the second v3 link.

`check_product_build_reaches.py` asks whether OUR call survives OUR
preprocessor.  It passed.  The call was in the build, it ran, and it still did
nothing -- because the capability it asks core for is not in CORE's build.  One
layer down, and invisible to every check we had.

Concretely: the product runs on a core configured with
`--with-wasm-module=writer`.  That sets ENABLE_WASM_STRIP_ACCESSIBILITY, which
removes 26 objects from sw/source/core/access and makes
`SwEditWin::CreateAccessible()` return an empty reference.  LOK's
`setAccessibilityState()` returns void and silently does nothing when there is
no accessible, so the product had no way to learn any of this: it asked for
accessibility, got no error, and read empty paragraphs forever.

A capability has TWO independent switches in this tree, and they are wired to
different configure inputs (see finding 057).  Checking either one alone would
have agreed with a build that cannot work:

  * the Make variable  -- decides whether the objects are COMPILED
  * the C++ macro      -- decides whether the CALLERS are compiled

This check requires both, and it is pointed at a real passing build (native) as
well as a real failing one (wasm), so "it can fail" is demonstrated against
actual builds rather than against a mutation we invented.

Second capability, added 2026-10-13 (ODS plan W6): `calc-spreadsheet`.  The
same lesson applies one module over -- `--with-wasm-module=calc` is what puts
Calc in a WASM core, the product's core is `writer` only, and a core without Calc
cannot open an ODS no matter what our own code does.  Unlike accessibility, Calc
has NO C++ macro (see the comment on the capability), so its independent
switches are different ones: the Make variable, the compiled objects, the
linked library, and the runtime registration.

Usage:
  check_core_build_provides.py                 # check the product's core build
  check_core_build_provides.py --build DIR     # check some other core build
  check_core_build_provides.py --capability NAME   # judge only NAME (repeatable)
  check_core_build_provides.py --self-test     # controls must pass, writer-only must fail

With no --capability the tool judges EVERY capability and the exit code is 0
only if all are provided.  `probe_a11y_gate0.py` calls it with `--build` only and
reads exit 0 as "provides accessibility"; that is true for every build that
exists today and is deliberately left alone (see the README next to the W6
evidence for the one way it could stop being true).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent

# The core build the product's WASM artifact is linked from.
PRODUCT_CORE_BUILD = WORKSPACE / "wasm-lite" / "build-headless-probe"
# A core build of the SAME source that does provide the capability.  This is the
# positive control: not a mutation, an actual build that works.
NATIVE_CORE_BUILD = WORKSPACE / "build-native-26-8"
# The self-test's calc controls get their OWN names instead of borrowing
# PRODUCT_CORE_BUILD.  That constant is a statement about what the product
# ships and is going to be repointed at the ODS cutover (ODS plan section 6); the
# negative control for "a writer-only core cannot open an ODS" must keep naming
# the writer-only build after that, or the self-test would silently start
# asserting something else.
WRITER_ONLY_CORE_BUILD = WORKSPACE / "wasm-lite" / "build-headless-probe"
# Same platform, same source, Calc linked in.  The positive control that makes
# "writer-only fails" mean "Calc is missing" instead of "some path is wrong".
WRITER_CALC_CORE_BUILD = WORKSPACE / "wasm-lite" / "build-a11y-gate0"

A11Y = "writer-lok-accessibility"
CALC = "calc-spreadsheet"


class Capability:
    """Something the product asks core for, and every switch that can remove it.

    `objects` are compiled units; `macro_must_be` is the value the C++ callers
    are compiled against.  Both are required, because in this tree they answer
    to different configure inputs and can disagree.

    A capability may have no macro at all (`macro=None`): then there is no
    caller-side switch to consult and none is invented.  The other switches are
    optional and are judged only when declared, so a capability that does not
    declare them produces exactly the report it always did:

      make_variable      name in config_host.mk, and make_variable_must_be, the
                         value it must have: the switch that decides whether
                         the objects are compiled at all
      libraries          stems, e.g. "sclo": the compiled objects are LINKED in
                         (static build: libX.a exists AND soffice.js.linkdeps
                         lists -lX; dynamic build: libX.so exists)
      implementations    (UNO implementation name, constructor symbol, library
                         stem): the runtime can find the code.  services.rdb must
                         register the name under that library; a static build
                         must also have the constructor in component_maps.cxx,
                         because there is no dlopen to look it up
    """

    def __init__(self, name, why, objects, macro_header=None, macro=None,
                 macro_must_be=None, make_variable=None,
                 make_variable_must_be=None, libraries=(), implementations=()):
        self.name = name
        self.why = why
        self.objects = objects
        self.macro_header = macro_header
        self.macro = macro
        self.macro_must_be = macro_must_be
        self.make_variable = make_variable
        self.make_variable_must_be = make_variable_must_be
        self.libraries = libraries
        self.implementations = implementations


CAPABILITIES = (
    Capability(
        name=A11Y,
        why="getA11yFocusedParagraph() and LOK_CALLBACK_A11Y_FOCUS_CHANGED are "
            "the only source of paragraph identity in LOK (measured: LOK has no "
            "paragraph index anywhere).  Without this, every caret fingerprint "
            "is the hash of an empty string and finding 046's identity gate has "
            "no input -- not broken, unfed.",
        # accmap builds the accessibility tree; accpara IS the focused paragraph.
        # Both are removed by sw/Library_sw.mk:108 when the Make variable is set.
        objects=(
            "workdir/CxxObject/sw/source/core/access/accmap.o",
            "workdir/CxxObject/sw/source/core/access/accpara.o",
            "workdir/CxxObject/sw/source/core/access/accdoc.o",
        ),
        macro_header="config_host/config_wasm_strip.h",
        macro="ENABLE_WASM_STRIP_ACCESSIBILITY",
        # 1 means STRIP, so the capability requires 0.  With 1, the objects may
        # still be compiled and SwEditWin::CreateAccessible() returns {} anyway
        # (sw/source/uibase/docvw/edtwin.cxx:6532) -- dead code, no capability.
        macro_must_be=0,
    ),
    Capability(
        name=CALC,
        why="Opening an ODS needs the Calc document shell, the ODS importer, the "
            "document model and the LOK part/tile entry points.  A core built "
            "with --with-wasm-module=writer has none of them: the module's "
            "directories are not even in the build.  This asks whether the "
            "objects that ARE that capability exist, are linked, and are "
            "registered; it does not claim to have opened a spreadsheet.",
        # Each of these is in Library_sc.mk (so in libsclo) and is named for the
        # job it does in the ODS path, not because it is the biggest file:
        #   docsh      ScDocShell, the document shell that loads and owns a doc
        #   xmlimprt   ScXMLImport -- the ODS content.xml importer; its
        #              Calc_XMLOasisImporter_get_implementation lives here
        #   document   ScDocument, the cell/sheet model that layout reads
        #   docuno     ScModelObj, the UNO model: getParts/getPartName/setPart,
        #              which LOK uses to switch sheets
        #   gridwin4   ScGridWindow::PaintTile, the tile painter
        # They sit on the same Make variable, so they usually come and go
        # together; they are listed separately because a tree can be configured
        # for Calc and then not (fully) built, and that must read as missing.
        objects=(
            "workdir/CxxObject/sc/source/ui/docshell/docsh.o",
            "workdir/CxxObject/sc/source/filter/xml/xmlimprt.o",
            "workdir/CxxObject/sc/source/core/data/document.o",
            "workdir/CxxObject/sc/source/ui/unoobj/docuno.o",
            "workdir/CxxObject/sc/source/ui/view/gridwin4.o",
        ),
        # NO C++ macro.  Measured by reading, 2026-10-13:
        #   * configure.ac:4414 only AC_SUBSTs ENABLE_WASM_STRIP_CALC; there is
        #     no AC_DEFINE for it (contrast :4421-4422 for ACCESSIBILITY).
        #   * grep over libreoffice-26-8 finds the name in exactly five files,
        #     all Make or configure inputs; sc/ has no ENABLE_WASM_STRIP_* at all.
        #   * of the config_host headers, only config_wasm_strip.h differs
        #     between the writer-only and the writer+calc WASM builds, and it
        #     differs in ENABLE_WASM_STRIP_ACCESSIBILITY alone.
        #     config_options_calc.h exists but holds ENABLE_FORMULA_LOGGER only.
        # So there is nothing on the caller side to consult.  If a Calc macro
        # ever appears, add it here (macro_header/macro/macro_must_be) rather
        # than letting the Make variable stand in for it -- that is finding 057.
        macro_header=None,
        macro=None,
        macro_must_be=None,
        # configure.ac:4371-4383: starts TRUE on Emscripten, cleared by
        # --with-wasm-module=calc.  It gates the sc/scaddins/sccomp modules in
        # RepositoryModule_host.mk:57,134, Library_wpftcalc in
        # writerperfect/Module_writerperfect.mk:27, and the scalc UI files in
        # static/CustomTarget_emscripten_fs_image.mk:1143.  Native builds leave
        # every ENABLE_WASM_STRIP_* empty, which is what "not stripped" means.
        make_variable="ENABLE_WASM_STRIP_CALC",
        make_variable_must_be="",
        # sclo hosts both implementations below (read from services.rdb).  The
        # other Calc libraries (-lscfiltlo -lscuilo -lscdlo -lwpftcalclo
        # -lanalysislo -ldatelo) differ between the two WASM builds too, but
        # nothing measured says ODS import/layout needs them, so requiring them
        # would put an unmeasured claim into a verdict.
        libraries=("sclo",),
        implementations=(
            ("com.sun.star.comp.Calc.SpreadsheetDocument",
             "Calc_SpreadsheetDocument_get_implementation", "sclo"),
            ("com.sun.star.comp.Calc.XMLOasisImporter",
             "Calc_XMLOasisImporter_get_implementation", "sclo"),
        ),
        # Looked at and deliberately NOT a switch: share/registry/calc.xcd (the
        # `calc8` type and filter data) is byte-identical in the writer-only and
        # the writer+calc WASM builds, as are main.xcd, static.xcd and
        # writer.xcd.  Presence of the type registration says nothing about
        # whether the code is linked.  Also not matched: the writer-only build's
        # services.rdb DOES register five "com.sun.star.comp.Calc.*" names
        # (xmloff's XMLCalc*ImportOOO), so the implementations above are named
        # in full, never found by looking for the word "Calc".
    ),
)


CAPABILITIES_BY_NAME = {c.name: c for c in CAPABILITIES}


def read_macro(build: Path, header: str, macro: str):
    path = build / header
    if not path.exists():
        return None
    match = re.search(rf"^\s*#define\s+{re.escape(macro)}\s+(\d+)\s*$",
                      path.read_text(encoding="utf-8"), re.MULTILINE)
    return int(match.group(1)) if match else None


def read_make_variable(build: Path, name: str):
    """What config_host.mk recorded for `name`, or None if it does not say.

    None and "" are different answers.  "" is configure saying the variable is
    empty -- for an ENABLE_WASM_STRIP_* that means "not stripped".  None is
    "this directory has no such line", and a check that requires "" must never
    accept it, or a missing directory would read as a build with everything on.
    """
    path = build / "config_host.mk"
    if not path.exists():
        return None
    found = re.findall(rf"^export\s+{re.escape(name)}=(.*)$",
                       path.read_text(encoding="utf-8", errors="replace"),
                       re.MULTILINE)
    return found[-1].strip() if found else None


LINKDEPS = "instdir/program/soffice.js.linkdeps"
SERVICES_RDB = "instdir/program/services/services.rdb"
COMPONENT_MAPS = "workdir/CustomTarget/static/component_maps.cxx"


def is_static_build(build: Path) -> bool:
    """A WASM build links everything into one image; a native build dlopens.

    DISABLE_DYNLOADING=TRUE is what configure records for the former.  Anything
    that does not positively say "dynamic loading is on" is judged by the static
    rules, because those are the rules this tool exists for -- a directory that
    cannot be read must not escape them by being unclassifiable.
    """
    return read_make_variable(build, "DISABLE_DYNLOADING") != ""


def library_problems(build: Path, cap: Capability, static: bool) -> list:
    problems = []
    tokens = None
    if static and (build / LINKDEPS).exists():
        tokens = set((build / LINKDEPS).read_text(
            encoding="utf-8", errors="replace").split())
    for stem in cap.libraries:
        library = f"instdir/program/lib{stem}.{'a' if static else 'so'}"
        if not (build / library).exists():
            problems.append(f"{library}: not built")
        if static:
            if tokens is None:
                problems.append(f"{LINKDEPS}: missing, so -l{stem} is not shown linked")
            elif f"-l{stem}" not in tokens:
                problems.append(f"{LINKDEPS}: does not list -l{stem}")
    return problems


def registered_implementations(build: Path) -> dict:
    """implementation name -> [(constructor, library uri)] from services.rdb."""
    path = build / SERVICES_RDB
    if not path.exists():
        return {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {}
    local = lambda element: element.tag.rsplit("}", 1)[-1]  # noqa: E731
    registered: dict = {}
    for component in root:
        if local(component) != "component":
            continue
        for implementation in component:
            if local(implementation) == "implementation":
                registered.setdefault(implementation.get("name"), []).append(
                    (implementation.get("constructor"), component.get("uri") or ""))
    return registered


def registration_problems(build: Path, cap: Capability, static: bool) -> list:
    problems = []
    registered = registered_implementations(build)
    maps = None
    if static and (build / COMPONENT_MAPS).exists():
        maps = (build / COMPONENT_MAPS).read_text(encoding="utf-8", errors="replace")
    for name, constructor, stem in cap.implementations:
        hosted = rf"(^|[/:])lib{re.escape(stem)}\.(a|so)$"
        if not any(c == constructor and re.search(hosted, uri)
                   for c, uri in registered.get(name, [])):
            problems.append(f"{SERVICES_RDB}: {name} is not registered "
                            f"as {constructor} in lib{stem}")
        if static:
            # The mapping line, not the declaration above it: the declaration
            # alone is what an unreferenced extern looks like.
            entry = rf'^\s*\{{\s*"{re.escape(constructor)}"\s*,\s*{re.escape(constructor)}\s*\}}'
            if maps is None or not re.search(entry, maps, re.MULTILINE):
                problems.append(f"{COMPONENT_MAPS}: {constructor} is not in the "
                                f"constructor map, so a static build cannot find it")
    return problems


def judge(build: Path, cap: Capability, relax=frozenset()):
    """One capability against one build: (report entry, {switch: satisfied}).

    `relax` is a set of (capability, switch) pairs treated as satisfied.  The
    CLI never uses it; the self-test does, to show every switch is wired into
    the verdict rather than merely printed.  The entry's key order for the
    accessibility capability is the order it has always had.
    """
    entry = {"capability": cap.name, "why": cap.why}
    switches = {}

    missing = [o for o in cap.objects if not (build / o).exists()]
    entry["objectsCompiled"] = not missing
    entry["missingObjects"] = missing
    switches["objects"] = not missing

    if cap.macro is not None:
        macro_value = read_macro(build, cap.macro_header, cap.macro)
        macro_ok = macro_value == cap.macro_must_be
        entry["macro"] = cap.macro
        entry["macroValue"] = macro_value
        entry["macroRequired"] = cap.macro_must_be
        entry["callersCompiled"] = macro_ok
        switches["macro"] = macro_ok

    if cap.make_variable is not None:
        value = read_make_variable(build, cap.make_variable)
        ok = value == cap.make_variable_must_be
        entry["makeVariable"] = cap.make_variable
        entry["makeVariableValue"] = value
        entry["makeVariableRequired"] = cap.make_variable_must_be
        entry["makeVariableAllows"] = ok
        switches["makeVariable"] = ok

    if cap.libraries or cap.implementations:
        entry["disableDynloading"] = read_make_variable(build, "DISABLE_DYNLOADING")
        static = is_static_build(build)
    if cap.libraries:
        problems = library_problems(build, cap, static)
        entry["librariesLinked"] = not problems
        entry["missingLibraries"] = problems
        switches["libraries"] = not problems
    if cap.implementations:
        problems = registration_problems(build, cap, static)
        entry["registered"] = not problems
        entry["missingRegistrations"] = problems
        switches["registration"] = not problems

    # Every switch, deliberately.  Either alone is a check that agrees with a
    # build that cannot work.
    entry["provided"] = all(ok or (cap.name, name) in relax
                            for name, ok in switches.items())
    return entry, switches


def check(build: Path, only=None, relax=frozenset()) -> dict:
    known = [c.name for c in CAPABILITIES]
    unknown = [n for n in (only or []) if n not in known]
    if unknown:
        raise ValueError(f"unknown capability {unknown}; known: {known}")
    results = [judge(build, cap, relax)[0] for cap in CAPABILITIES
               if not only or cap.name in only]
    absent = [r["capability"] for r in results if not r["provided"]]
    return {
        "schemaVersion": 1,
        "release": "core-build-capability",
        "coreBuild": str(build),
        "capabilities": results,
        "notProvidedByCoreBuild": absent,
        "ok": not absent,
    }


def by_name(report: dict, name: str):
    """A capability's entry, found by NAME.  Never by position: the list grows."""
    for entry in report["capabilities"]:
        if entry["capability"] == name:
            return entry
    return None


def brief(report: dict) -> str:
    """What a failing self-test line should print: the evidence, without the prose.

    The payload stays (a failure message that only says "wrong" costs a re-run),
    but `why` is a paragraph and would bury the part that matters.
    """
    return json.dumps([{k: v for k, v in entry.items() if k != "why"}
                       for entry in report["capabilities"]])


# The switches the calc capability must consult.  Written out on purpose: a
# self-test that derived this from the capability would stay green after
# someone deleted a switch, which is the one edit it exists to catch.
CALC_SWITCHES = {"makeVariable", "objects", "libraries", "registration"}


def self_test() -> int:
    failures: list[str] = []
    total = 0

    def verify(name: str, condition: bool, detail: str = "") -> None:
        nonlocal total
        total += 1
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    # ---- accessibility: unchanged logic, selected by name and judged alone,
    # ---- so adding a capability cannot change what these five assert.

    # The negative case, which is the product we ship today.  This check exists
    # because this build measured as unable to produce a focused paragraph.
    wasm = check(PRODUCT_CORE_BUILD, only=[A11Y])
    verify("the product's core build is reported as NOT providing a11y",
           not wasm["ok"], "the wasm build came back ok, so the check is blind")
    a11y = by_name(wasm, A11Y) or {}
    verify("...and names the compiled-out objects",
           not a11y.get("objectsCompiled", True) and a11y.get("missingObjects"))
    verify("...and names the macro that removes the callers",
           a11y.get("macroValue") == 1)

    # The positive control: a real build of the same source that DOES provide
    # it.  Without this the check could be failing for an unrelated reason (bad
    # path, typo in a filename) and look identical.
    native = check(NATIVE_CORE_BUILD, only=[A11Y])
    verify("a real core build that provides a11y is reported as providing it",
           native["ok"], json.dumps(native["notProvidedByCoreBuild"]))

    # The divergence itself (finding 057): the two switches are independent, so
    # a check that consulted only one would pass a build that cannot work.
    # Prove that by re-running with each half relaxed and showing the verdict
    # changes -- if it does not, this check is only really testing one thing.
    a = a11y.get("objectsCompiled")
    b = a11y.get("callersCompiled")
    verify("the two switches are checked independently",
           a is False and b is False and (a or b) is False,
           "both halves must be consulted; see finding 057")

    # ---- calc-spreadsheet.  By capability NAME throughout.

    # The negative case is the product's core, but named for what it is, not for
    # what the product points at: see WRITER_ONLY_CORE_BUILD.
    writer_only = check(WRITER_ONLY_CORE_BUILD, only=[CALC])
    calc = by_name(writer_only, CALC) or {}
    verify("calc: the writer-only core build is reported as NOT providing it",
           not writer_only["ok"] and not calc.get("provided", True),
           "the writer-only build came back ok, so the check is blind")
    verify("...and names what is missing: objects, Make variable, library, "
           "registration",
           bool(calc.get("missingObjects"))
           and calc.get("makeVariableValue") == "TRUE"
           and bool(calc.get("missingLibraries"))
           and bool(calc.get("missingRegistrations")),
           json.dumps({k: calc.get(k) for k in
                       ("missingObjects", "makeVariableValue",
                        "missingLibraries", "missingRegistrations")}))

    # The positive control on the SAME platform and the SAME source.  If an
    # object path were misspelled, the writer-only verdict above would be
    # exactly as red -- this is the line that tells the two apart.
    with_calc = check(WRITER_CALC_CORE_BUILD, only=[CALC])
    verify("calc: the writer+calc WASM build is reported as providing it",
           with_calc["ok"], brief(with_calc))
    native_calc = check(NATIVE_CORE_BUILD, only=[CALC])
    verify("calc: the native build is reported as providing it",
           native_calc["ok"], brief(native_calc))

    # Each independent switch is consulted.  Three views of the same fact:
    # (1) the switch set is what we meant to write down; (2) every switch is red
    # on the writer-only build and green on both controls, so none is vacuous;
    # (3) wired into the verdict -- relaxing one switch never turns the
    # writer-only verdict green, and relaxing all the others leaves that one
    # alone enough to keep it red.
    _, wo_sw = judge(WRITER_ONLY_CORE_BUILD, CAPABILITIES_BY_NAME[CALC])
    _, wc_sw = judge(WRITER_CALC_CORE_BUILD, CAPABILITIES_BY_NAME[CALC])
    _, nat_sw = judge(NATIVE_CORE_BUILD, CAPABILITIES_BY_NAME[CALC])
    verify("calc: the capability consults exactly the intended switches",
           set(wo_sw) == set(wc_sw) == set(nat_sw) == CALC_SWITCHES,
           json.dumps([sorted(wo_sw), sorted(wc_sw), sorted(nat_sw)]))
    verify("calc: every switch is red on the writer-only build",
           not any(wo_sw.values()), json.dumps(wo_sw))
    verify("calc: ...and green on both controls",
           all(wc_sw.values()) and all(nat_sw.values()),
           json.dumps([wc_sw, nat_sw]))
    for switch in sorted(CALC_SWITCHES):
        relaxed = check(WRITER_ONLY_CORE_BUILD, only=[CALC],
                        relax={(CALC, switch)})
        verify(f"calc: relaxing {switch} alone does not turn the writer-only "
               f"verdict green", not relaxed["ok"])
    for switch in sorted(CALC_SWITCHES):
        others = {(CALC, o) for o in CALC_SWITCHES if o != switch}
        relaxed = check(WRITER_ONLY_CORE_BUILD, only=[CALC], relax=others)
        verify(f"calc: with every other switch relaxed, {switch} alone keeps "
               f"it red", not relaxed["ok"])

    # --capability narrows; no flag judges everything.  The first is what lets
    # the a11y lines above stay a11y lines.
    narrowed = check(WRITER_CALC_CORE_BUILD, only=[A11Y])
    everything = check(WRITER_CALC_CORE_BUILD)
    verify("--capability judges only the named capability, and no flag judges all",
           [e["capability"] for e in narrowed["capabilities"]] == [A11Y]
           and [e["capability"] for e in everything["capabilities"]]
           == [c.name for c in CAPABILITIES])

    # A directory that does not exist is the cheapest wrong answer: a check that
    # looks for evidence of a stripped build would find none and say yes.
    gone = check(WORKSPACE / "no-such-core-build")
    verify("a build directory that does not exist provides nothing, for every "
           "capability, with every item missing",
           not gone["ok"] and len(gone["notProvidedByCoreBuild"]) == len(CAPABILITIES)
           and (by_name(gone, CALC) or {}).get("missingObjects")
           == list(CAPABILITIES_BY_NAME[CALC].objects)
           and (by_name(gone, CALC) or {}).get("makeVariableValue") is None)

    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, default=PRODUCT_CORE_BUILD)
    parser.add_argument("--capability", action="append",
                        choices=[c.name for c in CAPABILITIES],
                        help="judge only this capability (repeatable); with "
                             "none, judge all of them")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    report = check(args.build, only=args.capability)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
