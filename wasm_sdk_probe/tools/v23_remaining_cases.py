"""Inputs derived before execution; one-time corpus interpretation is explicit."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
PROFILE = 'e2-editor-v23-diag'
PROFILES = (PROFILE, 'e2-editor-v23-diag-r2')
FRAME_SHA256 = 'b2869e0eb89bc5644e08e5d86c5d374615d1e641ec5ed8a7d7aca0198567c661'
CASES_040 = {'frame': 'frame-destroy', 'html-positive': 'frame-html-engine', 'html-negative': 'frame-html-js'}
ARMS = ('frame', 'html-negative', 'html-positive', 'largest', 'workload')
ARTIFACTS = ('probe.wasm', 'probe.js', 'sdk-worker.js', 'sdk-manifest.json')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(profile, wasm):
    if profile not in PROFILES:
        raise ValueError('only explicitly pinned v23 diagnostic identities are accepted')
    root = PROJECT / 'dist/profiles' / profile
    manifest = json.loads((root / 'sdk-manifest.json').read_text())
    if manifest['profile'] != profile or manifest['editorContract']['abiVersion'] != 5:
        raise ValueError('profile/ABI mismatch; ABI alone does not identify v23')
    result = {p: sha(root / p) for p in ARTIFACTS}
    if result['probe.wasm'] != wasm: raise ValueError('actual WASM differs from explicit pin')
    return result


def fixtures():
    manifest = PROJECT / 'test-docs/r7-compat/manifest.json'
    data = json.loads(manifest.read_text())
    entries = data['documents']
    eligible = [x for x in entries if x.get('expected', {}).get('open') == 'pass'
                and x.get('mediaType') == 'application/vnd.oasis.opendocument.text'
                and isinstance(x.get('expected', {}).get('pageCount'), int)]
    if not eligible: raise ValueError('empty positive layout corpus')
    largest = max(eligible, key=lambda x: (x['expected']['pageCount'], x['bytes'], x['path']))
    byte_max = max(eligible, key=lambda x: (x['bytes'], x['path']))
    path = manifest.parent / largest['path']
    if sha(path) != largest['sha256']: raise ValueError('largest fixture differs from frozen corpus')
    frame = PROJECT / 'test-docs/e1/image-variants.odt'
    if sha(frame) != FRAME_SHA256: raise ValueError('040 pinned fixture SHA mismatch')
    with zipfile.ZipFile(frame) as z:
        root = ET.fromstring(z.read('content.xml'))
    ns = {'t': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
          'd': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0'}
    paragraphs = [p for p in root.findall('.//t:p', ns) if ''.join(p.itertext()).startswith('IV-ASCHAR ')]
    if len(paragraphs) != 1: raise ValueError('nonunique frame anchor')
    frames = paragraphs[0].findall('.//d:frame', ns)
    if len(frames) != 1 or frames[0].get('{'+ns['t']+'}anchor-type') != 'as-char' or frames[0].find('d:image', ns) is None:
        raise ValueError('anchor lacks exact as-char image witness')
    return {'frame': frame, 'largest': path, 'plain': PROJECT / 'test-docs/t1-plain-zh.odt'}, {
        'corpusManifestSha256': sha(manifest), 'metric': 'maximum declared pageCount among expected-open-pass ODT',
        'eligible': eligible, 'selected': largest, 'packageByteMaximum': byte_max,
        'excluded': [{'id': x['id'], 'expected': x.get('expected'), 'mediaType': x.get('mediaType')}
                     for x in entries if x not in eligible]}


def instrument_files():
    """Resolve local JS imports and local tools' static Python import graph."""
    import ast
    from build_e2_c_shell_bundle import imports_of
    seeds = ('tools/run_v23_remaining.py', 'tools/judge_v23_remaining.py',
             'tools/v23_remaining_cases.py', 'tools/create_long_document.py',
             'tools/build_e2_c_shell_bundle.py', 'web/v23-remaining.html', 'web/v23-remaining.js')
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
                    if imported.parent == PROJECT and imported.name == 'v23-remaining.js':
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
        elif relative == Path('web/v23-remaining.html'):
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
        if page.get('instrumentServed') != {k:served[k] for k in ('e2-editor.html','v23-remaining.js')}:
            raise ValueError('browser-fetched private HTML/JS identity absent/different')
