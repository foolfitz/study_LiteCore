#!/usr/bin/env python3
"""The v23 diagnostic/feature build preconditions, read from artifacts rather than stated
(SPEC-M3-ordered-commands 9.2 and 15.4; fable ruling 1 addendum 1 2.4; ruling 2 2.5 table, form 2).

  P-SOC  `-sSTACK_OVERFLOW_CHECK=2` is on the diagnostic link and on no other link: the product stays off
         (addendum 2.4; v22 3.3's L-153-no-overflow-check).
  P-016  `OXSDK_FINDING_016_SCHEDULER_PROBE` is not defined for any diagnostic object: its
         EditorDrainScheduler runs ProcessEventsToIdle inside a command, which 5.7 rule 1 forbids.

Two readings, because a Makefile is a claim and the build log is what ran:

  python3 -I tools/check_v23_diagnostic_build.py --makefile Makefile
      the rule as written: link_v23_diagnostic carries the flag; no other link macro mentions
      STACK_OVERFLOW_CHECK; the diagnostic probe.js calls that macro and nothing else does; the
      diagnostic compile rule carries the v23 defines and not the 016 probe.
  python3 -I tools/check_v23_diagnostic_build.py --build-log LOG
      the owner's make output for the link: every compile line writing into the diagnostic build
      directory has the v23 defines and not the 016 probe (EXTRA_DEFINES included, since this reads the
      command as run); exactly one link line writes its probe.js, and it carries the flag.  A log with
      no such compile line, or no such link line, is red: an empty record proves nothing.
  python3 -I tools/check_v23_diagnostic_build.py --self-test
      the red cases, on edited copies of a well-formed Makefile fragment and log.
  python3 -I tools/check_v23_diagnostic_build.py --wasm PATH
      actual diagnostic WebAssembly bytes: require core-built-without-accessibility and reject
      lok-lacks-setAccessibilityState (spec 16.5). This is a build precondition, not profile identity.
  python3 -I tools/check_v23_diagnostic_build.py --feature-build-log LOG
      actual feature object/link commands, default directory build/e2/editor-v23: require v23/mainloop
      and reject the diagnostic define and stack-overflow flag. --feature-build-dir overrides only
      the destination directory, not the required/forbidden flags. Empty/incremental-only logs fail.

Exit 0 when every precondition read holds; 1 otherwise.
"""
import argparse
import pathlib
import re
import sys

BUILD_DIR = 'build/e2/editor-v23-diag'
BUILD_VAR = '$(E2_V23D_BUILD)'
R2_BUILD_VAR = '$(E2_V23D_R2_BUILD)'
R2_BUILD_DIR = 'build/e2/editor-v23-diag-r2'
LINK_MACRO = 'link_v23_diagnostic'
FLAG = '-sSTACK_OVERFLOW_CHECK=2'
PROBE_016 = 'OXSDK_FINDING_016_SCHEDULER_PROBE'
V23_DEFINES = ('-DOXSDK_E2_V23_LINK_BATCH', '-DOXSDK_E2_V23_DIAGNOSTIC', '-DOXSDK_MAINLOOP_ENGINE')
DIAGNOSTIC_DEFINE = '-DOXSDK_E2_V23_DIAGNOSTIC'
FEATURE_BUILD_DIR = 'build/e2/editor-v23'


def logical_lines(text):
    return text.replace('\\\n', ' ').splitlines()


def macros(text):
    return dict(re.findall(r'^define (\S+)\n(.*?)^endef', text, flags=re.S | re.M))


def rule_body(text, target):
    """The recipe of the rule whose target line starts with `target`, joined."""
    lines = logical_lines(text)
    for i, line in enumerate(lines):
        if line.startswith(target):
            body = [line]
            for nxt in lines[i + 1:]:
                if nxt.startswith('\t') or not nxt.strip():
                    body.append(nxt)
                    if not nxt.strip():
                        break
                else:
                    break
            return '\n'.join(body)
    return None


def read_makefile(text, successor=False):
    problems = []
    build_var = R2_BUILD_VAR if successor else BUILD_VAR
    defs = macros(text)
    if LINK_MACRO not in defs:
        problems.append(f'P-SOC: no `define {LINK_MACRO}`')
    elif FLAG not in defs[LINK_MACRO]:
        problems.append(f'P-SOC: {LINK_MACRO} does not carry {FLAG}')
    for name, body in defs.items():
        if name != LINK_MACRO and 'STACK_OVERFLOW_CHECK' in body:
            problems.append(f'P-SOC: link macro {name} mentions STACK_OVERFLOW_CHECK')
    link = rule_body(text, f'{build_var}/probe.js:')
    if link is None:
        problems.append(f'P-SOC: no rule for {BUILD_VAR}/probe.js')
    elif f'$(call {LINK_MACRO},' not in link:
        problems.append(f'P-SOC: {BUILD_VAR}/probe.js does not call {LINK_MACRO}')
    callers = [m.start() for m in re.finditer(r'\$\(call ' + LINK_MACRO + ',', text)]
    allowed = 0
    for known in (BUILD_VAR, R2_BUILD_VAR):
        body = rule_body(text, f'{known}/probe.js:')
        if body is not None:
            allowed += 1
            if f'$(call {LINK_MACRO},' not in body:
                problems.append(f'P-SOC: {known}/probe.js does not call {LINK_MACRO}')
    if len(callers) != allowed:
        problems.append(f'P-SOC: {LINK_MACRO} is called {len(callers)} times (exactly {allowed}: named diagnostic targets only)')
    compile_rule = rule_body(text, f'{build_var}/%.o:')
    if compile_rule is None:
        problems.append(f'P-016: no compile rule for {BUILD_VAR}/%.o')
    else:
        if PROBE_016 in compile_rule:
            problems.append(f'P-016: the diagnostic compile rule defines {PROBE_016}')
        for d in V23_DEFINES:
            if d not in compile_rule:
                problems.append(f'P-016: the diagnostic compile rule lacks {d}')
    return problems


def read_build_log(text, successor=False):
    problems = []
    build_dir = R2_BUILD_DIR if successor else BUILD_DIR
    compiles = [l for l in logical_lines(text) if ' -c ' in l and f'-o {build_dir}/' in l and l.rstrip().endswith('.o')]
    links = [l for l in logical_lines(text) if f'-o {build_dir}/probe.js' in l]
    if not compiles:
        problems.append(f'P-016: the log has no compile line writing into {build_dir} (an empty record)')
    for l in compiles:
        obj = l.rsplit('-o ', 1)[1].strip()
        if PROBE_016 in l:
            problems.append(f'P-016: {obj} was compiled with {PROBE_016}')
        for d in V23_DEFINES:
            if d not in l.split():
                problems.append(f'P-016: {obj} was compiled without {d}')
    if len(links) != 1:
        problems.append(f'P-SOC: {len(links)} link lines write {build_dir}/probe.js (exactly one)')
    for l in links:
        if FLAG not in l.split():
            problems.append(f'P-SOC: the diagnostic link line lacks {FLAG}')
    return problems


def read_wasm(data):
    """Read the actual linked bytes; text/source metadata cannot satisfy this check."""
    problems = []
    if not data.startswith(b'\x00asm\x01\x00\x00\x00'):
        problems.append('P-A11Y: not a version-1 WebAssembly binary')
    if b'core-built-without-accessibility' not in data:
        problems.append('P-A11Y: missing core-built-without-accessibility')
    if b'lok-lacks-setAccessibilityState' in data:
        problems.append('P-A11Y: unexpected lok-lacks-setAccessibilityState')
    return problems


def read_feature_build_log(text, build_dir=FEATURE_BUILD_DIR):
    """The feature link must not inherit diagnostic instrumentation (spec 16.5)."""
    problems = []
    lines = logical_lines(text)
    compiles = [line for line in lines if ' -c ' in line
                and f'-o {build_dir}/' in line and line.rstrip().endswith('.o')]
    links = [line for line in lines if f'-o {build_dir}/probe.js' in line]
    if not compiles:
        problems.append('P-FEATURE: no feature compile lines (an empty record)')
    if len(links) != 1:
        problems.append(f'P-FEATURE: {len(links)} feature link lines (exactly one)')
    for line in compiles + links:
        if re.search(r'(?:^|\s)' + re.escape(DIAGNOSTIC_DEFINE) + r'(?:=|\s|$)', line):
            problems.append('P-FEATURE: diagnostic define present')
        if 'STACK_OVERFLOW_CHECK' in line:
            problems.append('P-FEATURE: diagnostic stack-overflow flag present')
    for line in compiles:
        for define in V23_DEFINES:
            if define != DIAGNOSTIC_DEFINE and define not in line.split():
                problems.append('P-FEATURE: missing ' + define)
    return problems


GOOD_MAKEFILE = f'''define link_product_stack_1m
\t$(CXX) $(1) -sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=1048576 -o $(3)
endef

define {LINK_MACRO}
\t$(CXX) $(1) -sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=1048576 \\
\t\t{FLAG} -o $(3)
endef

{BUILD_VAR}/%.o: src/%.cpp Makefile | {BUILD_VAR}
\t$(CXX) $(E1_CPPFLAGS) -DOXSDK_EDITOR_DISCOVERY \\
\t\t-DOXSDK_MAINLOOP_ENGINE -DOXSDK_E2_V23_LINK_BATCH -DOXSDK_E2_V23_DIAGNOSTIC \\
\t\t$(EXTRA_DEFINES) -c $< -o $@

{BUILD_VAR}/probe.js: $(E2_V23D_OBJECTS) Makefile
\t$(call {LINK_MACRO},$(E2_V23D_OBJECTS),{BUILD_VAR}/exports.txt,$@)

$(E2_V22_BUILD)/probe.js: $(E2_V22_OBJECTS) Makefile
\t$(call link_product_stack_1m,$(E2_V22_OBJECTS),$(E2_V22_BUILD)/exports.txt,$@)
'''

GOOD_LOG = f'''em++ -DLOK_USE_UNSTABLE_API -Oz -DOXSDK_EDITOR_DISCOVERY -DOXSDK_MAINLOOP_ENGINE -DOXSDK_E2_V23_LINK_BATCH -DOXSDK_E2_V23_DIAGNOSTIC -c src/probe_engine.cpp -o {BUILD_DIR}/probe_engine.o
em++ -DLOK_USE_UNSTABLE_API -Oz -DOXSDK_EDITOR_DISCOVERY -DOXSDK_MAINLOOP_ENGINE -DOXSDK_E2_V23_LINK_BATCH -DOXSDK_E2_V23_DIAGNOSTIC -c src/sdk_api.cpp -o {BUILD_DIR}/sdk_api.o
em++ {BUILD_DIR}/probe_engine.o {BUILD_DIR}/sdk_api.o -sSTACK_SIZE=131072 {FLAG} -o {BUILD_DIR}/probe.js
'''


def self_test():
    wasm = b'\x00asm\x01\x00\x00\x00' + b'core-built-without-accessibility'
    feature = GOOD_LOG.replace(BUILD_DIR, FEATURE_BUILD_DIR).replace(DIAGNOSTIC_DEFINE+' ', '').replace(FLAG+' ', '')
    cases = [
        ('makefile', 'well-formed', GOOD_MAKEFILE, None),
        ('makefile', 'the flag removed from the diagnostic macro', GOOD_MAKEFILE.replace(f'\\\n\t\t{FLAG} ', ''), 'does not carry'),
        ('makefile', 'the flag on the product macro too', GOOD_MAKEFILE.replace('-sDEFAULT_PTHREAD_STACK_SIZE=1048576 -o $(3)', f'-sDEFAULT_PTHREAD_STACK_SIZE=1048576 {FLAG} -o $(3)'), 'link_product_stack_1m mentions'),
        ('makefile', 'the product rule calls the diagnostic macro', GOOD_MAKEFILE.replace('$(call link_product_stack_1m,', f'$(call {LINK_MACRO},'), 'called 2 times'),
        ('makefile', 'the 016 probe defined', GOOD_MAKEFILE.replace('-DOXSDK_E2_V23_DIAGNOSTIC \\', f'-DOXSDK_E2_V23_DIAGNOSTIC -D{PROBE_016} \\'), 'defines OXSDK_FINDING_016'),
        ('makefile', 'no diagnostic rule at all', GOOD_MAKEFILE.split(f'{BUILD_VAR}/%.o')[0], 'no compile rule'),
        ('log', 'well-formed', GOOD_LOG, None),
        ('log', 'one object built with the 016 probe (EXTRA_DEFINES)', GOOD_LOG.replace('-c src/sdk_api.cpp', f'-D{PROBE_016} -c src/sdk_api.cpp'), 'sdk_api.o was compiled with'),
        ('log', 'the link without the flag', GOOD_LOG.replace(f' {FLAG} ', ' '), 'lacks -sSTACK'),
        ('log', 'an empty record', '', 'an empty record'),
        ('log', 'an object built without the v23 define', GOOD_LOG.replace('-DOXSDK_E2_V23_LINK_BATCH -DOXSDK_E2_V23_DIAGNOSTIC -c src/sdk_api.cpp', '-DOXSDK_E2_V23_DIAGNOSTIC -c src/sdk_api.cpp'), 'without -DOXSDK_E2_V23_LINK_BATCH'),
        ('wasm', 'headless core marker bytes', wasm, None),
        ('wasm', 'empty bytes', b'', 'not a version-1'),
        ('wasm', 'text masquerading as wasm', wasm[8:], 'not a version-1'),
        ('wasm', 'missing headless marker', wasm[:8], 'missing core-built'),
        ('wasm', 'wrong API absence marker', wasm+b'lok-lacks-setAccessibilityState', 'unexpected lok-lacks'),
        ('feature', 'well-formed feature log', feature, None),
        ('feature', 'diagnostic define via EXTRA_DEFINES', feature.replace('-c src/sdk_api.cpp', DIAGNOSTIC_DEFINE+'=1 -c src/sdk_api.cpp'), 'diagnostic define present'),
        ('feature', 'diagnostic overflow flag', feature.replace('-sSTACK_SIZE', FLAG+' -sSTACK_SIZE'), 'stack-overflow flag present'),
        ('feature', 'empty feature record', '', 'an empty record'),
        ('feature', 'no feature link', '\n'.join(feature.splitlines()[:-1]), '0 feature link'),
        ('feature', 'duplicate feature link', feature+feature.splitlines()[-1], '2 feature link'),
        ('feature', 'old engine without mainloop', feature.replace('-DOXSDK_MAINLOOP_ENGINE ', ''), 'missing -DOXSDK_MAINLOOP_ENGINE'),
    ]
    ok = True
    for kind, label, text, needle in cases:
        found = {'makefile': read_makefile, 'log': read_build_log,
                 'wasm': read_wasm, 'feature': read_feature_build_log}[kind](text)
        good = (not found) if needle is None else any(needle in p for p in found)
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {kind}: {label}: {found if found else 'holds'}")
    print('self-test: ' + ('all as required' if ok else 'FAILED'))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--makefile')
    g.add_argument('--build-log')
    g.add_argument('--wasm', help='linked diagnostic probe.wasm bytes (spec 16.5)')
    g.add_argument('--feature-build-log', help='actual feature compile/link log; diagnostic define must be absent')
    g.add_argument('--self-test', action='store_true')
    ap.add_argument('--profile', choices=('e2-editor-v23-diag', 'e2-editor-v23-diag-r2'), default='e2-editor-v23-diag')
    ap.add_argument('--feature-build-dir', default=FEATURE_BUILD_DIR)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if a.wasm:
        problems = read_wasm(pathlib.Path(a.wasm).read_bytes())
    elif a.feature_build_log:
        problems = read_feature_build_log(pathlib.Path(a.feature_build_log).read_text(errors='replace'), a.feature_build_dir)
    else:
        text = pathlib.Path(a.makefile or a.build_log).read_text(errors='replace')
        problems = read_makefile(text, a.profile.endswith('-r2')) if a.makefile else read_build_log(text, a.profile.endswith('-r2'))
    for p in problems:
        print(p)
    print('preconditions hold' if not problems else f'{len(problems)} precondition problem(s)')
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
