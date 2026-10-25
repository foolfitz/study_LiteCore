#!/usr/bin/env python3
"""Read-only AST inventory of the actual local Python import closure.

Run from the repository root. Emits JSON to stdout; never imports or executes
any inventoried module, invokes make, or writes a product/build artifact.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

root = Path.cwd().resolve()
sdk = root / 'wasm_sdk_probe'
tools = sdk / 'tools'
makefile = sdk / 'Makefile'
make = makefile.read_text()
start = make.index('$(E2_V23D_R2_DIST)/sdk-manifest.json:')
end = make.index('\n$(E2_V23D_R2_BUILD) $(E2_V23D_R2_DIST):', start)
recipe = make[start:end]
roots = {tools / 'build_e2_v23_diagnostic_r2_profile.py': ['explicit successor packer'],
         tools / 'check_v23_diagnostic_build.py': ['explicit build/artifact reader']}
for match in re.finditer(r'^\tpython3\s+(tools/[^\s]+\.py)([^\n]*)', recipe, re.M):
    roots.setdefault(sdk / match[1], []).append('actual r2 manifest recipe: ' + match[0].strip())

def resolve(module, origin, level=0):
    if level:
        base = origin.parent
        for _ in range(level - 1): base = base.parent
        bases = [base]
    else:
        # Script directory and the observed same-tools bootstrap, then repository
        # package roots. This does not evaluate arbitrary sys.path mutations.
        bases = [origin.parent, tools, sdk, root]
    parts = module.split('.') if module else []
    for base in bases:
        path = base.joinpath(*parts)
        for candidate in (path.with_suffix('.py'), path / '__init__.py'):
            if candidate.is_file() and candidate.resolve().is_relative_to(root):
                return candidate.resolve()
    return None

def row(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(root)), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}

pending = list(roots)
files, edges, nonlocal_imports, dynamics, path_changes = {}, [], [], [], []
while pending:
    path = pending.pop().resolve()
    if path in files: continue
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    files[path] = row(path)
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names: aliases[item.asname or item.name] = item.name
        elif isinstance(node, ast.ImportFrom):
            for item in node.names: aliases[item.asname or item.name] = (node.module or '') + '.' + item.name
    def visit(module, line, level=0, optional=False):
        destination = resolve(module, path, level)
        record = {'from': str(path.relative_to(root)), 'line': line, 'module': module, 'level': level}
        if destination:
            record['to'] = str(destination.relative_to(root))
            edges.append(record); pending.append(destination)
        elif not optional:
            nonlocal_imports.append(record)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names: visit(item.name, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            visit(node.module or '', node.lineno, node.level)
            for item in node.names:
                if item.name != '*':
                    visit('.'.join(filter(None, [node.module, item.name])), node.lineno, node.level, optional=True)
        elif isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            first, _, rest = name.partition('.')
            expanded = aliases.get(first, first) + ('.' + rest if rest else '')
            if name.startswith('sys.path.'):
                path_changes.append({'file':str(path.relative_to(root)), 'line':node.lineno,
                                     'expression':ast.get_source_segment(source,node)})
            if expanded in ('__import__','importlib.import_module','runpy.run_module','runpy.run_path') or name in ('exec','eval'):
                record = {'file':str(path.relative_to(root)), 'line':node.lineno,
                          'expression':ast.get_source_segment(source,node), 'resolved':False}
                if expanded in ('__import__','importlib.import_module','runpy.run_module') and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
                    destination = resolve(node.args[0].value,path)
                    if destination:
                        record.update(resolved=True,to=str(destination.relative_to(root)))
                        pending.append(destination)
                dynamics.append(record)
# Re-read each inventory entry after traversal: fail if anything changed while collected.
for path, captured in files.items():
    if row(path) != captured: raise RuntimeError('input changed while collecting: ' + str(path))
print(json.dumps({'method':'AST Import/ImportFrom recursive local resolution; literal dynamic module calls when locally resolvable',
                  'roots':[{'path':str(p.relative_to(root)),'provenance':why} for p,why in sorted(roots.items())],
                  'makefile':row(makefile), 'collector':row(Path(__file__).resolve()),
                  'files':sorted(files.values(),key=lambda r:r['path']),
                  'localImportEdges':sorted(edges,key=lambda r:(r['from'],r['line'],r['module'])),
                  'notResolvedLocally':sorted(nonlocal_imports,key=lambda r:(r['from'],r['line'],r['module'])),
                  'dynamicImportOrExecutionSites':dynamics,'sysPathMutationSites':path_changes,
                  'verification':'Every captured file rehashed identically after traversal; no modules executed.',
                  'limits':['Standard-library and third-party modules are listed but not traversed or hashed.',
                            'Resolution uses importer directory, tools directory, SDK root and repository root; arbitrary runtime sys.path changes are not evaluated.',
                            'Nonliteral dynamic imports/exec/eval remain explicitly unresolved. Subprocesses and non-Python resource inputs are outside this import closure.']},indent=2))
