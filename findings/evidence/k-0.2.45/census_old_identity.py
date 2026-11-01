#!/usr/bin/env python3
"""The census before the K 0.2.45 repin (SPEC-M3-K-0.2.44 append 3: the survey of counted-only paths is a pre-chain step).

Tool-closed: the population is the static import closure of what the chain and the reader name, walked from their own text, not a
hand list.  It answers two questions a shakedown cannot:
  1. which files in that closure still carry a literal of the 0.2.44 identity, and at which lines;
  2. every `ddev` argv shape in that closure, against what host-stack/bin/ddev accepts.
Non-vacuity: an empty closure, a chain with no entry points, or an old identity list with a literal found nowhere is an error, so a
renamed directory reads red instead of "zero".  Read-only.  Writes census.json next to itself.  Exit 0 always on a completed census:
it is a list to work through, not a verdict.
"""
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / 'wasm_sdk_probe/tools'
CHAIN = ROOT / 'findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh'
READER = CHAIN.with_name('read-0.2.44.sh')
OLD = {'page': '3b0a2ebb', 'html': 'b9c2b975', 'buildId': 'dacdfa20', 'host': 'a97724f', 'version': '0.2.44', 'profile': 'e2-editor-v28',
       'wasm': '13f674e4', 'generation': 'bundle-v82', 'digest': 'a02673fa', 'manifest': 'da4e595d', 'identityTool': 'v82_four_arms_identity',
       'f3': 'run_v82_f3_clipboard', 'enter': 'check_v82_shift_enter', 'merge': 'run_k_0244_merge', 'kdir': 'k-0.2.44'}
ADAPTER = {'describe', 'list', 'occ', 'exec', 'mysql'}


def closure():
    source = CHAIN.read_text() + '\n' + READER.read_text()
    seeds = {TOOLS / name for name in re.findall(r'\$T/([a-zA-Z0-9_]+\.py)', source)}
    seeds |= {TOOLS / f'check_m3_{name}.py' for name in re.findall(r'^SIX="([^"]+)"', CHAIN.read_text(), re.M)[0].split()}
    seeds |= {ROOT / name for name in re.findall(r'(findings/evidence/[a-zA-Z0-9_./-]+\.py)', source)}
    seeds = {p for p in seeds if p.is_file()}
    if len(seeds) < 12:
        raise SystemExit(f'only {len(seeds)} entry points')
    pending, seen = list(seeds), set()
    while pending:
        path = pending.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                p = TOOLS / Path(*name.split('.')).with_suffix('.py')
                if p.is_file():
                    pending.append(p)
    return sorted(seen)


def main():
    files = closure()
    hits, shapes = {}, {}
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            for name, literal in OLD.items():
                if literal in line:
                    kind = 'comment' if stripped.startswith('#') else 'code'
                    hits.setdefault(rel, []).append({'line': number, 'name': name, 'kind': kind, 'text': stripped[:150]})
            for match in re.finditer(r'\[\s*"ddev"\s*,\s*("[^"]*"|\*?[a-zA-Z_]\w*)', line):
                word = match.group(1).strip('"')
                shapes.setdefault(word, []).append(f'{rel}:{number}')
    used = {h['name'] for rows in hits.values() for h in rows}
    report = {'closureFiles': len(files), 'filesWithOldLiterals': len(hits), 'hits': hits,
              'notFoundAnywhere': sorted(set(OLD) - used), 'ddevShapes': shapes,
              'ddevShapesOutsideAdapter': sorted(w for w in shapes if w not in ADAPTER and not w.startswith('*'))}
    (Path(__file__).with_name('census.json')).write_text(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: report[k] for k in ('closureFiles', 'filesWithOldLiterals', 'notFoundAnywhere', 'ddevShapesOutsideAdapter')}))
    for rel, rows in sorted(hits.items()):
        code = [r for r in rows if r['kind'] == 'code']
        print(f"{rel}: {len(code)} code, {len(rows) - len(code)} comment  {sorted({r['name'] for r in code})}")
    print({k: len(v) for k, v in shapes.items()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
