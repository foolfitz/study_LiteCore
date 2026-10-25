"""Source and executed-module identity for bounded v23 and W-D instruments."""
import hashlib
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def instrument_files():
    """Resolve local JS imports and local tools' static Python import graph."""
    import ast
    from build_e2_c_shell_bundle import imports_of
    seeds = ('tools/run_v23_diagnostic.py', 'tools/judge_v23_diagnostic.py',
             'tools/v23_diagnostic_instruments.py', 'tools/judge_v23_wd.py', 'tools/v23_wd_cases.py',
             'tools/build_e2_c_shell_bundle.py', 'web/v23-diagnostic.html', 'web/v23-diagnostic.js')
    pending = [PROJECT/name for name in seeds]
    found = set()
    while pending:
        path = pending.pop().resolve()
        if path in found: continue
        if not path.is_file(): raise ValueError(f'missing local instrument dependency: {path}')
        found.add(path)
        if path.suffix == '.js':
            base = PROJECT if path.parent == PROJECT/'web' else path.parent
            for target in imports_of(path.read_text()):
                if target.startswith('.'):
                    imported = (base/target).resolve()
                    if imported.parent == PROJECT and imported.name.startswith('v23-diagnostic'):
                        imported = PROJECT/'web'/imported.name
                    pending.append(imported)
        if path.suffix == '.py':
            for node in ast.walk(ast.parse(path.read_text())):
                names = [n.name for n in node.names] if isinstance(node, ast.Import) else (
                    [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
                for name in names:
                    target = PROJECT/'tools'/Path(*name.split('.')).with_suffix('.py')
                    if target.is_file(): pending.append(target)
    return sorted(found)


def served_instruments():
    """Actual server paths for every JS import and the private entry HTML."""
    result = {}
    for path in instrument_files():
        relative = path.relative_to(PROJECT)
        if path.suffix == '.js':
            served = path.name if relative.parts[0] == 'web' else str(relative)
            result[served] = sha(path)
        elif relative == Path('web/v23-diagnostic.html'):
            result['e2-editor.html'] = sha(path)
    return result


def verify_bindings(report, mirror, check_pages=True):
    expected = {str(p.relative_to(PROJECT)): sha(p) for p in instrument_files()}
    if report.get('instrument') != expected: raise ValueError('actual instrument source graph drift/absence')
    served = served_instruments()
    if report.get('mirrorInstrument') != served: raise ValueError('recorded executed graph drift/absence')
    for name, digest in served.items():
        if sha(Path(mirror)/name) != digest: raise ValueError(f'executed mirror differs: {name}')
    for run in report.get('runs', []) if check_pages else []:
        page = run.get('page') or {}
        if page.get('instrumentServed') != {k:served[k] for k in (('e2-editor.html','v23-diagnostic.js','v23-diagnostic-wd.js') if page.get('arm')=='wd' else ('e2-editor.html','v23-diagnostic.js'))}:
            raise ValueError('browser-fetched private HTML/JS identity absent/different')
