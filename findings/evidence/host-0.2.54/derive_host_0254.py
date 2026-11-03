#!/usr/bin/env python3
"""Derive host-0.2.54's scripts from host-0.2.53's (SPEC-P-demo-batch-6): each replacement must match its stated count; the 0.2.53 files are not
edited.  0.2.54 is host source only: no served file changes, the engine package is 0.2.53's.  What moves is the host source delta (the declared
list below, not only info.xml) and the gate, which adds G1 to G3 from static/ and re-runs G1 and G3 on the candidate it packages.
"""
from pathlib import Path

EV = Path(__file__).resolve().parents[1]
OLD, NEW = EV / 'host-0.2.53', EV / 'host-0.2.54'
A52, A53 = 'host-0.2.52-engine-21985315bc752e57', 'host-0.2.53-engine-89860962782b3a21'


def between(text, start, end):
    a = text.index(start)
    return text[a:text.index(end, a) + len(end)]


delta = (OLD / 'check-delta.py').read_text(encoding='utf-8')
release = (OLD / 'prepare-release.py').read_text(encoding='utf-8')
PLAN = {
 ('offline-package-check.py', 'offline-package-check.py'): [
  ('only BUILD_ID rebound for candidate 0.2.53.', 'only BUILD_ID rebound for candidate 0.2.54.', 1),
  ('this docstring (0.2.52 -> 0.2.53 in its first line, and', 'this docstring (0.2.53 -> 0.2.54 in its first line, and', 1),
  ('rebinding; the 0.2.53 delta is judged', 'rebinding; the 0.2.54 delta is judged', 1)],
 ('capture-after.py', 'capture-after.py'): [('"""Read the installed 0.2.53 identity', '"""Read the installed 0.2.54 identity', 1)],
 ('install-0.2.53.py', 'install-0.2.54.py'): [
  ('"""Guarded 0.2.53 candidate install;', '"""Guarded 0.2.54 candidate install;', 1),
  ('names: host c657aba (0.2.52)\nwith the exact 0.2.52 engine archive.', 'names: host 6b1660c (0.2.53)\nwith the exact 0.2.53 engine archive.', 1),
  ("candidate = SDK / 'build/host-0.2.53/litecore'", "candidate = SDK / 'build/host-0.2.54/litecore'", 1)],
 ('rollback-package.sh', 'rollback-package.sh'): [
  ('# Functional engine rollback to exact 0.2.52 bytes, preserving host label 0.2.53 (derived from host-0.2.47/rollback-package.sh, not edited).\n',
   '# Functional engine rollback to exact 0.2.53 bytes, preserving host label 0.2.54 (derived from host-0.2.47/rollback-package.sh, not edited).\n'
   '# 0.2.54 ships 0.2.53\'s engine package byte for byte, so this restores the same bytes: batch 6 is host source (the New spreadsheet creator,\n'
   '# blank-ods/, img/), which this script does not touch.  Taking batch 6 back is a host commit on a new version, not this script.\n', 1),
  ('EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.53', 'EVIDENCE=/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/host-0.2.54', 1),
  ("spec_from_file_location('host053_install',out/'install-0.2.53.py')", "spec_from_file_location('host054_install',out/'install-0.2.54.py')", 1),
  (f"{A52}')", f"{A53}')", 1),
  ('Exact 0.2.52 engine restored; host label stays 0.2.53;', 'Exact 0.2.53 engine restored; host label stays 0.2.54;', 1)],
 ('check-delta.py', 'check-delta.py'): [
  (between(delta, '"""SPEC-P-demo-batch-5', 'the red cases that follow.\n"""'),
   '"""SPEC-P-demo-batch-6: the 0.2.54 package is 0.2.53\'s -- no served file changed, none added or removed, no profile moves -- read from the two\n'
   "archived MANIFEST.json files, not from prepare-release.py's own say-so.  Batch 6 is host source only.\n\n"
   'Derived from findings/evidence/host-0.2.53/check-delta.py (not edited).  Closed list of differences: this docstring; the declared delta, now\n'
   'empty; the `fewer` red case goes, there is no declared file to put back.\n"""', 1),
  ("DECLARED = ['e2-editor-app.js']\n", 'DECLARED = []\n', 1),
  ("    def fewer(o, m):\n        m['files'][DECLARED[0]] = copy.deepcopy(o['files'][DECLARED[0]])\n\n", '', 1),
  ("for fn in (more, fewer, added, removed,", "for fn in (more, added, removed,", 1)],
 ('prepare-release.py', 'prepare-release.py'): [
  (between(release, '"""Package an isolated 0.2.53 host', "0.2.52's docstring follows.\n"),
   '"""Package an isolated 0.2.54 host (New spreadsheet, LibreOffice\'s document icons, SPEC-P-demo-batch-6) from current verified dist,\n'
   'preserving the live predecessor.\n\n'
   'Derived from findings/evidence/host-0.2.53/prepare-release.py (not edited).  Closed list of differences: this paragraph; the predecessor is host\n'
   '6b1660c (0.2.53) with the exact 0.2.53 engine, and the candidate is build/host-0.2.54; the host source delta is the declared list (SOURCE_DECLARED\n'
   'and blank-ods/ with its manifest\'s 30 files), not only info.xml; the served delta is empty and the buildId must be 0.2.53\'s; the gate adds G1 to\n'
   'G3 and their red cases from static/, and G1 and G3 are run again on the candidate before packaging, their output kept in release.json; the names.\n\n'
   "0.2.53's docstring follows.\n\n" + between(release, '"""Package an isolated 0.2.53 host', "0.2.52's docstring follows.\n")[3:], 1),
  ("APP = SDK / 'build/host-0.2.53/litecore'", "APP = SDK / 'build/host-0.2.54/litecore'", 1),
  ("PARENT = 'c657aba'", "PARENT = '6b1660c'", 1),
  (f"OLD = SDK / 'build/archive/{A52}'", f"OLD = SDK / 'build/archive/{A53}'", 1),
  ("DECLARED_CHANGED = ['e2-editor-app.js']\n", "DECLARED_CHANGED = []\n"
   "SOURCE_DECLARED = ['LICENSES/MPL-2.0.txt', 'appinfo/info.xml', 'img/README.md', 'img/oasis-spreadsheet.svg', 'img/oasis-text.svg', 'l10n/zh_TW.js',\n"
   "                   'l10n/zh_TW.json', 'lib/Listener/FileCreatedFromTemplateListener.php', 'lib/Listener/RegisterTemplateCreatorListener.php',\n"
   "                   'lib/Template/BlankDocument.php']\n"
   "STATIC = OUT / 'static'\n", 1),
  ("    regression = [load(BATCH3 / f'calc-regression/{n}/report.json') for n in ('cell-v3-01', 'range-v3-01', 'auto-v3-01')]\n",
   "    regression = [load(BATCH3 / f'calc-regression/{n}/report.json') for n in ('cell-v3-01', 'range-v3-01', 'auto-v3-01')]\n"
   "    g1, g1_red = load(STATIC / 'g1-check.stdout.txt'), load(STATIC / 'g1-red-one-byte.stdout.txt')\n"
   "    g2, g3 = load(STATIC / 'g2-validate.stdout.txt'), load(STATIC / 'g3-choose.stdout.txt')\n"
   "    g3_red = (STATIC / 'g3-red-manifest-missing-one.stdout.txt').read_text()\n", 1),
  ("        'E1-C': (e1c, [True, True]),\n",
   "        'E1-C': (e1c, [True, True]),\n"
   "        'G1': (g1.get('identical'), True),\n"
   "        'G1-red-one-byte': (g1_red.get('identical'), False),\n"
   "        'G2': ([g2.get('validated'), g2.get('passed'), g2.get('failed'), g2.get('hashesMatch')], [30, 30, [], True]),\n"
   "        'G3': (g3.get('verdict'), 'G3_HOLDS'),\n"
   "        'G3-red-manifest-missing-one': ('is not in MANIFEST.json' in g3_red, True),\n", 1),
  ("raise ValueError('live predecessor differs from clean c657aba (0.2.52)')", "raise ValueError('live predecessor differs from clean 6b1660c (0.2.53)')", 1),
  ("if '<version>0.2.53</version>' not in", "if '<version>0.2.54</version>' not in", 1),
  ("    if git(APP, 'diff', '--name-only', parent, candidate).splitlines() != ['appinfo/info.xml']:\n"
   "        raise ValueError('candidate host source delta is not only its version')\n",
   "    blank_ods = sorted(load(APP / 'blank-ods/MANIFEST.json')['files'])\n"
   "    if len(blank_ods) != 30:\n"
   "        raise ValueError('blank-ods manifest does not list 30 spreadsheets')\n"
   "    source_delta = git(APP, 'diff', '--name-only', parent, candidate).splitlines()\n"
   "    if sorted(source_delta) != sorted(SOURCE_DECLARED + ['blank-ods/MANIFEST.json'] + ['blank-ods/' + n for n in blank_ods]):\n"
   "        raise ValueError('candidate host source delta is not the declared list: ' + json.dumps(source_delta))\n"
   "    g1_argv = [sys.executable, '-I', str(SDK / 'tools/make_new_spreadsheet_templates.py'), '--check', str(APP / 'blank-ods')]\n"
   "    g3_argv = ['php', str(STATIC / 'g3_choose.php'), str(APP / 'lib/Template/BlankDocument.php')]\n"
   "    static_now = {}\n"
   "    for name, argv, key, want_value in (('G1', g1_argv, 'identical', True), ('G3', g3_argv, 'verdict', 'G3_HOLDS')):\n"
   "        done = subprocess.run(argv, capture_output=True, text=True, timeout=120)\n"
   "        static_now[name] = {'argv': argv, 'exit': done.returncode, 'stdout': json.loads(done.stdout), 'stderr': done.stderr}\n"
   "        if done.returncode or static_now[name]['stdout'].get(key) != want_value:\n"
   "            raise ValueError(name + ' does not hold on the candidate: ' + json.dumps(static_now[name]))\n", 1),
  ("    print('packaged', manifest['buildId'], round(time.monotonic() - started, 2), flush=True)\n",
   "    print('packaged', manifest['buildId'], round(time.monotonic() - started, 2), flush=True)\n"
   "    if manifest['buildId'] != old['buildId']:\n"
   "        raise ValueError('the engine package is not 0.2.53\\'s: ' + manifest['buildId'])\n", 1),
  ("raise ValueError('delta against 0.2.52 is not exactly e2-editor-app.js: '", "raise ValueError('delta against 0.2.53 is not empty: '", 1),
  ("archive = SDK / 'build/archive' / ('host-0.2.53-engine-' + manifest['buildId'])", "archive = SDK / 'build/archive' / ('host-0.2.54-engine-' + manifest['buildId'])", 1),
  ("(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.53 engine package\\n\\n'", "(archive / 'ATTRIBUTION.md').write_text('# Exact host 0.2.54 engine package\\n\\n'", 1),
  ("f'Host commit {candidate}, predecessor {parent} (0.2.52, exact 0.2.52 engine). Writer on profile e2-editor-v32, shell '",
   "f'Host commit {candidate}, predecessor {parent} (0.2.53, exact 0.2.53 engine). Writer on profile e2-editor-v32, shell '", 1),
  ("'generation 88, Calc on ods-editor-v3: Enter over a selection, the empty-copy sentence (SPEC-P-demo-batch-5). Uncounted candidate.\\n')",
   "'generation 88, Calc on ods-editor-v3; the same bytes as 0.2.53\\'s package. The host adds New spreadsheet and LibreOffice\\'s icons '\n"
   "        '(SPEC-P-demo-batch-6). Uncounted candidate.\\n')", 1),
  ("release = {'version': '0.2.53',", "release = {'version': '0.2.54',", 1),
  ("'branch': 'host-0.2.53',", "'branch': 'host-0.2.54',", 1),
  ("this release changes the Writer page on the same engine and is read by its own gates, not counted",
   "this release changes host source only, on 0.2.53\\'s engine package, and is read by its own gates, not counted", 1),
  ("               'shellBundleFileSha256': want['shell']['bundleFileSha256']}\n",
   "               'shellBundleFileSha256': want['shell']['bundleFileSha256'], 'hostSourceDelta': source_delta, 'staticOnCandidate': static_now}\n", 1)],
}
for (source, target), replacements in PLAN.items():
    text = (OLD / source).read_text(encoding='utf-8')
    for old, new, count in replacements:
        got = text.count(old)
        if got != count:
            raise SystemExit(f'{source}: {old[:70]!r} occurs {got} times, expected {count}')
        text = text.replace(old, new)
    (NEW / target).write_text(text, encoding='utf-8')
    print(target, 'written')
