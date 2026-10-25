"""Finite S-init population authorized before counts; public routes only."""
from pathlib import Path
import hashlib
import json

PROJECT = Path(__file__).resolve().parents[1]
PROFILES = ('e2-editor-v22', 'e2-editor-v23-diag-r2')
BROWSERS = ('chrome', 'firefox')
ROUNDS = (1, 2, 3)
MARKER = 'S_INIT_ROUNDTRIP_MARKER'
PARAGRAPH_MARKER = 'S_INIT_PARAGRAPH_MARKER'
CASES = {
    'direct-load-reopen': {'fixtures': ['language.odt'], 'input': MARKER},
    'input-teh': {'fixtures': ['empty-en-US.odt'], 'input': 'teh '},
    'input-quotes': {'fixtures': ['empty-en-US.odt'], 'input': '"word" '},
    'input-number': {'fixtures': ['empty-en-US.odt'], 'input': '1. '},
    'paragraph-break': {'fixtures': ['empty-en-US.odt'], 'input': PARAGRAPH_MARKER,
                        'setup': 'initial-empty-caret-once'},
    'linguistic-layout': {'fixtures': ['hyphenation-on.odt', 'hyphenation-off.odt']},
}
REGION = {'xTwips': 0, 'yTwips': 0, 'widthTwips': 8640, 'heightTwips': 11520,
          'canvasWidthPx': 600, 'canvasHeightPx': 800}
FIXTURES = PROJECT / 'test-docs/v23-s-init'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture_identity():
    declared = json.loads((FIXTURES / 'manifest.json').read_text())
    actual = {name: sha(FIXTURES / name) for name in sorted({f for c in CASES.values() for f in c['fixtures']})}
    if declared != actual: raise ValueError('pinned S-init fixture bytes changed')
    return actual


def profile_identity(profile, wasm):
    if profile not in PROFILES: raise ValueError('not a comparison profile')
    directory = PROJECT / 'dist/profiles' / profile
    manifest = json.loads((directory / 'sdk-manifest.json').read_text())
    if manifest['profile'] != profile or manifest['editorContract']['abiVersion'] != 5:
        raise ValueError('profile or ABI mismatch')
    paths = {'sdk-manifest.json', 'probe.js', 'probe.wasm', 'sdk-worker.js'}
    paths.update(manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks', []): paths.update((pack['data'], pack['metadata']))
    # Normalize URL spellings while retaining profile-relative resource paths.
    paths = {p[2:] if p.startswith('./') else p for p in paths}
    artifacts = {p: sha(directory / p) for p in sorted(paths)}
    if artifacts['probe.wasm'] != wasm: raise ValueError('actual WASM differs from explicit pin')
    return {'profile': profile, 'coreCommit': manifest['coreCommit'], 'artifacts': artifacts}


def instrument_identity():
    from build_e2_c_shell_bundle import imports_of
    files = {Path(__file__), PROJECT / 'tools/run_v23_s_init.py', PROJECT / 'tools/judge_v23_s_init.py',
             PROJECT / 'web/v23-s-init.html'}
    pending = [PROJECT / 'web/v23-s-init.js']
    while pending:
        path = pending.pop().resolve()
        if path in files: continue
        if not path.is_file(): raise ValueError(f'missing local instrument import: {path}')
        files.add(path)
        base = PROJECT if path.parent == PROJECT / 'web' else path.parent
        for specifier in imports_of(path.read_text()):
            if specifier.startswith('.'): pending.append((base / specifier).resolve())
    return {str(p.relative_to(PROJECT)): sha(p) for p in sorted(files)}


def served_sources():
    result = {}
    for path, digest in instrument_identity().items():
        if path.endswith(('.js', '.html')):
            served = 'e2-editor.html' if path == 'web/v23-s-init.html' else path.removeprefix('web/')
            result[served] = digest
    return result


def expected_mutations(case_id):
    plan = CASES[case_id]
    mutations = [('insertText', plan['input'])] if 'input' in plan else []
    if case_id == 'paragraph-break':
        mutations.insert(0, ('editorPlaceCaretV2', None))
        mutations.append(('editorActionV2', 'insert-paragraph-break'))
    return mutations


def config_bytes(config):
    return (json.dumps(config, indent=2) + '\n').encode()


def verify_mirror(target, config):
    target = Path(target)
    actual_sources = {name: sha(target / name) for name in config['servedSources']}
    if actual_sources != config['servedSources']: raise ValueError('executed mirror source bytes differ')
    actual_fixtures = {name: sha(target / 's-init-fixtures' / name) for name in config['fixtures']}
    if actual_fixtures != config['fixtures']: raise ValueError('copied fixture bytes differ')
    if (target / 's-init-config.json').read_bytes() != config_bytes(config):
        raise ValueError('served config bytes differ')
    return {'servedSources': actual_sources, 'fixtures': actual_fixtures,
            'configSha256': hashlib.sha256(config_bytes(config)).hexdigest()}
