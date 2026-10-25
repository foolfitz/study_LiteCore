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
