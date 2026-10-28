"""SPEC-M3-link-batch-v24 6.3/6.4: the v23 selection population on the v24 profile; no browser execution.

v23's module (tools/v23_feature_selection_cases.py) is byte-bound by counted-r1-s5-01's
instrumentSources and hard-codes v23's profile, page and generation-76 bundle, so it is imported,
never edited.  Everything that builds a population (Table 1 cases, S4 interactions, S5 with its
native references bound by hash, R1) is v23's function unchanged; only what names the build under
test is new here:

  identity()  the v24 profile files (pinned to build/archive/e2-editor-v24-27615808-worker-41041fe7),
              ABI 6 with the typedInsert leaf, and the shell.  Generation 77 is not frozen yet
              (spec 15): until it is, the shell is bound by the candidate digest the bundle tool
              computes over the live tree, every included file's dist copy equal to its source,
              and the page b15a6d8e....  When 77 is frozen with this digest, nothing here changes.
  sources()   that included set plus the harness web/v24-feature-selection.js, served in place of
              the page's entry exactly as v23's harness was.
  config()    v23's population, this identity and sources, and this module's instrument closure.
"""
import ast
import json
from pathlib import Path
import posixpath
import re

from v23_feature_selection_cases import (ROOT, PROJECT, BROWSERS, FIXTURE, PINS, digest, encoded, sha,
                                         paragraphs, point_plan, cases, interactions, s5, r1, verify_mirror)
from v23_feature_s_cases import derive, read_rounds
import build_e2_c_shell_bundle as shell_bundle

PROFILE = 'e2-editor-v24'
TYPED_INSERT = 'document-sdk-insert-typed-text'
PAGE_SHA256 = 'b15a6d8e07b6a4f3e551f27971b7cfe8bec2cb743e5f6809013ca7f2082de669'
CANDIDATE_SHELL_DIGEST = '56ce44c78043220e4f135343dc87a8e847e83849e4c6571345b1ac9e2e8a294a'
ARTIFACT_PINS = {
    'probe.wasm': '276158084a602178f9b7219c086f749910601b1a121fca9339b10a79b0f7b639',
    'probe.js': '64aaa8dc2c7a1c366c76911213090ae60d39c26cd4207274ef1c0420a5a0b301',
    'sdk-worker.js': '41041fe746b2355a1768bc774a10ac59802a8e359579618be405e3696f3b9461',
    'sdk-manifest.json': 'f9554e8c1b79ff4955dbfdf7dbe7c9975f3d0bcc945665c3491a730cb44cd04e'}
ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v24-27615808-worker-41041fe7'
HARNESS = 'v24-feature-selection.js'
INSTRUMENTS = ('v24_feature_selection_cases.py', 'run_v24_feature_selection.py', 'judge_v24_feature_selection.py')


def shell():
    """The live shell: the bundle tool's own computation, bound to the candidate digest."""
    state = shell_bundle.compute(PROJECT)
    if state['digest'] != CANDIDATE_SHELL_DIGEST:
        raise ValueError('candidate shell digest differs: ' + state['digest'])
    for path in state['included']:
        if state['distHashes'].get(path) != state['hashes'][path]:
            raise ValueError('shell source/dist differs: ' + path)
    if state['hashes'][shell_bundle.ENTRYPOINT.as_posix()] != PAGE_SHA256:
        raise ValueError('page differs')
    return state


def identity():
    directory = PROJECT / 'dist/profiles' / PROFILE
    for name, expected in ARTIFACT_PINS.items():
        if sha(directory / name) != expected or sha(ARCHIVED_PROFILE / name) != expected:
            raise ValueError('actual v24 profile/archive identity differs: ' + name)
    manifest = json.loads((directory / 'sdk-manifest.json').read_text())
    contract = manifest['editorContract']
    if manifest['profile'] != PROFILE or contract['abiVersion'] != 6 or contract.get('typedInsert') != TYPED_INSERT:
        raise ValueError('actual v24 ABI/profile/typedInsert differs')
    state = shell()
    paths = set(ARTIFACT_PINS)
    paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks', []):
        paths.update((pack['data'], pack['metadata']))
    return {'profile': PROFILE, 'editorAbi': 6, 'typedInsert': TYPED_INSERT,
            'artifacts': {n: sha(directory / n) for n in sorted(paths)},
            'shell': {'generation': 'candidate-77-not-frozen', 'digest': state['digest'],
                      'included': {p: state['hashes'][p] for p in state['included']}},
            'pageSha256': PAGE_SHA256, 'originalHtmlSha256': sha(PROJECT / 'web/e2-editor.html')}


def sources():
    state = shell()
    out = {}
    for path in state['included']:
        raw = (PROJECT / path).read_bytes()
        if digest(raw) != state['hashes'][path]:
            raise ValueError('shell source changed while reading: ' + path)
        out[path.removeprefix('web/')] = raw
    original = (PROJECT / 'web/e2-editor.html').read_bytes()
    needle = b'<script type="module" src="./e2-editor-app.js"></script>'
    if original.count(needle) != 1:
        raise ValueError('product HTML entry differs')
    out['e2-editor.html'] = original.replace(needle, ('<script type="module" src="./' + HARNESS + '"></script>').encode())
    out[HARNESS] = (PROJECT / 'web' / HARNESS).read_bytes()
    for name, raw in out.items():
        if not name.endswith('.js'):
            continue
        for spec in re.findall(r'(?:from\s*|import\s*\(?)\s*["\']([^"\']+)["\']', raw.decode()):
            if spec.startswith('.') and posixpath.normpath(posixpath.join(posixpath.dirname(name), spec)) not in out:
                raise ValueError('missing executed import: ' + spec)
    return out


def instrument_closure():
    pending = [PROJECT / 'tools' / n for n in INSTRUMENTS] + [PROJECT / 'web/serve.py']
    closure = set()
    while pending:
        path = pending.pop().resolve()
        if path in closure:
            continue
        closure.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = [x.name for x in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                candidate = PROJECT / 'tools' / Path(*name.split('.')).with_suffix('.py')
                if candidate.is_file():
                    pending.append(candidate)
    return {str(p.relative_to(PROJECT)): sha(p) for p in sorted(closure)}


def config():
    texts = paragraphs(); rounds = read_rounds(); table = derive(rounds); selection = cases(table)
    s5_plan = s5(table, selection); interaction_plan = interactions(table, rounds, texts); r1_plan, r1_fixture_plan = r1()
    if len({*selection, *interaction_plan, *s5_plan, *r1_plan}) != len(selection) + len(interaction_plan) + len(s5_plan) + len(r1_plan):
        raise ValueError('population identifiers overlap')
    return {'schema': 1, 's5NativeReferenceSchema': 2, 'profile': identity(),
            'servedSources': {n: digest(v) for n, v in sources().items()},
            'instrumentSources': instrument_closure(),
            'cases': selection, 'interactions': interaction_plan, 's5': s5_plan, 'r1': r1_plan, 'r1Fixtures': r1_fixture_plan,
            'sourceTable': table, 'fixtureSha256': PINS['fixture-as-run.fodt'],
            'fixtureParagraphs': texts, 'fixtureManifest': {'fixtures': [{'id': 'list-contexts'}]},
            'readinessPoint': point_plan('p0.0', texts),
            'mappingPoints': [point_plan(f'p{i}.0', texts) for i in range(len(texts))]}


def mirror(target, plan, overrides=None):
    """v23's mirror layout; `overrides` (served name -> bytes) replaces a served source, and the
    plan given must already name the override's hash (the runner's scratch arms, e.g. (i))."""
    target.mkdir(parents=True, exist_ok=False)
    (target / 'profiles').symlink_to(PROJECT / 'dist/profiles', target_is_directory=True)
    served = sources()
    for name, raw in (overrides or {}).items():
        if name not in served:
            raise ValueError('override of an unserved source: ' + name)
        served[name] = raw
    for name, raw in served.items():
        path = target / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    (target / 'e1-fixtures').mkdir()
    (target / 'e1-fixtures/manifest.json').write_bytes(encoded(plan['fixtureManifest']))
    for name in ('e1-fixtures/list-contexts.odt', 'feature-selection.odt'):
        (target / name).write_bytes(FIXTURE.read_bytes())
    for f in plan.get('r1Fixtures', {}).values():
        (target / f['servedName']).write_bytes((ROOT / f['path']).read_bytes())
    (target / 'selection-config.json').write_bytes(encoded(plan))


def type_cells(plan):
    """M2's population: every S5 row of the type family, in the plan's order."""
    rows = [cid for cid, row in plan['s5'].items() if row['family'] == 'type']
    if len(rows) != 84:
        raise ValueError('S5 type population differs: %d' % len(rows))
    return rows
