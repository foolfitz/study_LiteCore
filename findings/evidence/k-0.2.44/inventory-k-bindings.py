#!/usr/bin/env python3
"""Read-only K preparation inventory for host 0.2.44 (engine v28, shell generation 82), derived from
findings/evidence/host-0.2.39/inventory-k-bindings.py (not edited).  Closed list of differences: this sentence; the
release read is host-0.2.44's; the bundle manifest v82 and tools/v82_four_arms_identity.py; profile e2-editor-v28;
the host worktree build/host-0.2.44/litecore.

Read-only K preparation inventory from the actual prior chain/imports, git deltas and candidate.

This is a one-time inventory, not a claim that shell/import analysis is an exhaustive execution
graph. It neither edits constants nor authorizes a count. Frozen membership is read from receipts.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SDK = ROOT / 'wasm_sdk_probe'
OUT = Path(__file__).resolve().parent
TOOLS = SDK / 'tools'
CHAIN = ROOT / 'findings/evidence/m3-production-ui/runs-0.2.26/chain-0.2.26.sh'
READER = CHAIN.with_name('read-0.2.26.sh')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def main():
    release = json.loads((ROOT / 'findings/evidence/host-0.2.44/release.json').read_bytes())
    old = json.loads((SDK / 'build/archive/host-0.2.25-engine-f5f0df762e1855f2/MANIFEST.json').read_bytes())
    new = json.loads((Path(release['archive']) / 'MANIFEST.json').read_bytes())
    source = CHAIN.read_text() + '\n' + READER.read_text()
    six = re.findall(r'^SIX="([^"]+)"', CHAIN.read_text(), re.M)
    if len(six) != 1:
        raise ValueError('legacy stage population not uniquely derived')
    seeds = {TOOLS / ('check_m3_' + name + '.py') for name in six[0].split()}
    seeds.update(TOOLS / name for name in re.findall(r'\$T/([a-zA-Z0-9_]+\.py)', source))
    seeds.update(ROOT / name for name in re.findall(r'(findings/evidence/[a-zA-Z0-9_./-]+\.py)', source))
    seeds.add(ROOT / 'findings/evidence/release-0.2.26/product-path/judge.py')
    if not seeds or any(not p.is_file() for p in seeds):
        raise ValueError('empty/missing legacy Python entry point: ' + str([str(p) for p in seeds if not p.is_file()]))
    pending = list(seeds); seen = set()
    while pending:
        path = pending.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                p = TOOLS / Path(*name.split('.')).with_suffix('.py')
                if p.is_file():
                    pending.append(p)
    frozen = {}
    records = (
        ('v23-count', ROOT / 'findings/evidence/link-batch-v23/feature-protocol/counted-r1-s5-01/cohort.json', 'instrumentSources'),
        ('v24-count', ROOT / 'findings/evidence/link-batch-v24/counted-selection-01/cohort.json', 'instrumentSources'),
        ('v24-remaining', ROOT / 'findings/evidence/link-batch-v24/remaining-counted-01/cohort.json', 'orchestrationSources'),
        ('v24-a4', ROOT / 'findings/evidence/link-batch-v24/count-preparation/a4-instruments.json', 'bindings'))
    for label, path, field in records:
        for name in json.loads(path.read_bytes())[field]:
            frozen.setdefault('wasm_sdk_probe/' + name, []).append(label)
    settled = ROOT / 'findings/evidence/link-batch-v23/feature-protocol/s5-native/settled-reference-reader-05.json'
    for name in json.loads(settled.read_bytes())['bindings']:
        frozen.setdefault(name, []).append('settled-reader-05')
    sys.path.insert(0, str(TOOLS))
    import build_e2_c_shell_bundle as bundle
    bundle.MANIFEST = Path('e2/editor-shell-v2-bundle-v82.json')
    import run_merge_wasm_shakedown as merge
    from v82_four_arms_identity import identity
    want = identity(); page = (SDK / 'web/e2-editor-app.js').read_text(); html = (SDK / 'dist/e2-editor.html').read_text()
    binding = merge.bound_values(SDK / 'dist', 'e2-editor-v28', page, page, html)
    roles = {'PAGE_SHA256': want['pageSha256'], 'FINAL_PAGE_SHA256': want['pageSha256'],
             'SESSION_SHA256': sha(SDK / 'dist/editor-shell-v2/narrow-editor-v2-session.js'),
             'HOST_VERSION': release['version'], 'HOST_COMMIT': release['hostCommit'],
             'BUILD_ID': release['buildId'], 'ENGINE_BUILD_ID': release['buildId'],
             'SHELL_BUNDLE_SHA256': want['shell']['digest'], 'BINDING': binding}
    pins = []
    for path in sorted(seen):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name, value = node.targets[0].id, node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name, value = node.target.id, node.value
            else:
                continue
            if name not in roles:
                continue
            try:
                old_value = ast.literal_eval(value)
            except (ValueError, TypeError):
                continue
            rel = path.relative_to(ROOT).as_posix()
            pins.append({'path': rel, 'line': node.lineno, 'symbol': name, 'current': old_value,
                         'candidate': roles[name], 'differs': old_value != roles[name], 'frozenBy': frozen.get(rel, [])})
    if not pins or not any(p['symbol'] == 'BINDING' for p in pins):
        raise ValueError('empty binding inventory or merge BINDING not reached')
    engine_delta = []
    for name in sorted(set(old['files']) | set(new['files'])):
        a, b = old['files'].get(name), new['files'].get(name)
        kind = 'added' if a is None else 'removed' if b is None else 'identical-record' if a == b else 'changed'
        engine_delta.append({'path': name, 'kind': kind, 'old': a, 'new': b})
    result = {'scope': __doc__.strip(), 'candidateRelease': release,
              'legacyChain': {'path': str(CHAIN.relative_to(ROOT)), 'sha256': sha(CHAIN), 'readerSha256': sha(READER)},
              'entryPoints': sorted(p.relative_to(ROOT).as_posix() for p in seeds),
              'staticImportClosure': {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(seen)},
              'pinOccurrences': pins, 'proposedMergeBinding': binding, 'originalMergeBinding': merge.BINDING,
              'studyGitDeltaSinceLastCount': git(ROOT, 'diff', '--name-status', '9c8d83cc', 'HEAD').splitlines(),
              'hostGitDeltaSinceLastCount': git(SDK / 'build/host-0.2.44/litecore', 'diff', '--name-status', '3c01876', release['hostCommit']).splitlines(),
              'engineDeltaSinceLastCount': engine_delta,
              'unresolvedPremise': 'legacy v8 current-page repoint is refused by the required typedInsert gate; do not change the gate to preserve the old K protocol'}
    (OUT / 'k-binding-inventory.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({'entries': len(seeds), 'closureFiles': len(seen), 'pinOccurrences': len(pins),
                       'frozenPinOccurrences': sum(bool(p['frozenBy']) for p in pins),
                       'mergeKeys': len(binding), 'enginePaths': len(engine_delta)}, indent=1))


if __name__ == '__main__':
    main()
