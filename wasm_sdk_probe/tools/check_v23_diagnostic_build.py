#!/usr/bin/env python3
"""The v23 diagnostic profile's two build preconditions, read from the build record rather than stated
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

Exit 0 when every precondition read holds; 1 otherwise.
"""
import argparse
import pathlib
import re
import sys

BUILD_DIR = 'build/e2/editor-v23-diag'
BUILD_VAR = '$(E2_V23D_BUILD)'
LINK_MACRO = 'link_v23_diagnostic'
FLAG = '-sSTACK_OVERFLOW_CHECK=2'
PROBE_016 = 'OXSDK_FINDING_016_SCHEDULER_PROBE'
V23_DEFINES = ('-DOXSDK_E2_V23_LINK_BATCH', '-DOXSDK_E2_V23_DIAGNOSTIC', '-DOXSDK_MAINLOOP_ENGINE')


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


def read_makefile(text):
    problems = []
    defs = macros(text)
    if LINK_MACRO not in defs:
        problems.append(f'P-SOC: no `define {LINK_MACRO}`')
    elif FLAG not in defs[LINK_MACRO]:
        problems.append(f'P-SOC: {LINK_MACRO} does not carry {FLAG}')
    for name, body in defs.items():
        if name != LINK_MACRO and 'STACK_OVERFLOW_CHECK' in body:
            problems.append(f'P-SOC: link macro {name} mentions STACK_OVERFLOW_CHECK')
    link = rule_body(text, f'{BUILD_VAR}/probe.js:')
    if link is None:
        problems.append(f'P-SOC: no rule for {BUILD_VAR}/probe.js')
    elif f'$(call {LINK_MACRO},' not in link:
        problems.append(f'P-SOC: {BUILD_VAR}/probe.js does not call {LINK_MACRO}')
    callers = [m.start() for m in re.finditer(r'\$\(call ' + LINK_MACRO + ',', text)]
    if len(callers) != 1:
        problems.append(f'P-SOC: {LINK_MACRO} is called {len(callers)} times (exactly one: the diagnostic)')
    compile_rule = rule_body(text, f'{BUILD_VAR}/%.o:')
    if compile_rule is None:
        problems.append(f'P-016: no compile rule for {BUILD_VAR}/%.o')
    else:
        if PROBE_016 in compile_rule:
            problems.append(f'P-016: the diagnostic compile rule defines {PROBE_016}')
        for d in V23_DEFINES:
            if d not in compile_rule:
                problems.append(f'P-016: the diagnostic compile rule lacks {d}')
    return problems


def read_build_log(text):
    problems = []
    compiles = [l for l in logical_lines(text) if ' -c ' in l and f'-o {BUILD_DIR}/' in l and l.rstrip().endswith('.o')]
    links = [l for l in logical_lines(text) if f'-o {BUILD_DIR}/probe.js' in l]
    if not compiles:
        problems.append(f'P-016: the log has no compile line writing into {BUILD_DIR} (an empty record)')
    for l in compiles:
        obj = l.rsplit('-o ', 1)[1].strip()
        if PROBE_016 in l:
            problems.append(f'P-016: {obj} was compiled with {PROBE_016}')
        for d in V23_DEFINES:
            if d not in l.split():
                problems.append(f'P-016: {obj} was compiled without {d}')
    if len(links) != 1:
        problems.append(f'P-SOC: {len(links)} link lines write {BUILD_DIR}/probe.js (exactly one)')
    for l in links:
        if FLAG not in l.split():
            problems.append(f'P-SOC: the diagnostic link line lacks {FLAG}')
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
    ]
    ok = True
    for kind, label, text, needle in cases:
        found = read_makefile(text) if kind == 'makefile' else read_build_log(text)
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
    g.add_argument('--self-test', action='store_true')
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    text = pathlib.Path(a.makefile or a.build_log).read_text(errors='replace')
    problems = read_makefile(text) if a.makefile else read_build_log(text)
    for p in problems:
        print(p)
    print('preconditions hold' if not problems else f'{len(problems)} precondition problem(s)')
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
