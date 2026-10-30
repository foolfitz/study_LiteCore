"""SPEC-M3-v27-finding-176 7.3 F4-81: what names the build under test for the generation-81 four-arm run.

Derived from tools/v80_four_arms_identity.py (bound by F4-80's evidence; not edited).  The differences are a
closed list (spec 7.3): this paragraph and the line above it; PROFILE e2-editor-v26 -> e2-editor-v27; ARTIFACT_PINS
-> the v27 link's four (probe.wasm c089dfd6, probe.js 0a73eb5a, sdk-worker.js 8152448a, sdk-manifest.json
d5d07639); ARCHIVED_PROFILE -> the v27 archive; the page (b63d8ee5, generation 81), the shell digest and the
bundle file (generation 81, v27-176/freeze-81/); 80 -> 81 and v26 -> v27 in the messages, in the record and in
shell()'s docstring.  Everything below is that file's text from its own derivation note on.

SPEC-M3-select-all-v26 5.6 F4-80: what names the build under test for the generation-80 four-arm run.

Derived from tools/v79_four_arms_identity.py (bound by F4-79's evidence; not edited).  The differences are a
closed list (spec 5.6, review item 9): this paragraph and the line above it; PROFILE e2-editor-v25 ->
e2-editor-v26; ARTIFACT_PINS sdk-worker.js 75557b22 -> 95d6e7ae and sdk-manifest.json e7780061 -> 835752a3
(probe.wasm and probe.js are v25's bytes, unchanged); ARCHIVED_PROFILE -> the v26 archive; the page
(3b6c023e, generation 80), the shell digest and the bundle file (generation 80, select-all-v26/freeze-80/);
79 -> 80 and v25 -> v26 in the messages, in the record and in shell()'s docstring.  Everything below is that
file's text from its own derivation note on.

Derived from tools/v25_four_arms_identity.py (bound by v25 F4's evidence; not edited).  The differences are a
closed list: this paragraph and the line above it; the page (9cb6ea1f, e5170c84d), the shell digest and the
bundle file (generation 79, freeze-79/); 78 -> 79 in the messages, in the record and in shell()'s
docstring.  The profile is unchanged: e2-editor-v25,
the same archive pins.  Everything below is that file's text, including its own derivation note.

v24's `tools/v24_feature_selection_cases.py` hard-codes v24's profile, page and generation 77 and is bound
by v24's counts, so it is not edited.  This is its `shell()` / `identity()` with v25's names: profile
e2-editor-v25 pinned to the v25 archive, ABI 6 with the typedInsert leaf (spec v25 4.5: every leaf equals
v24's), the live shell equal to frozen generation 78 (`9450e5340`), the page 6e66c930 (`e06d10a1b`).
"""
import json

from v23_feature_selection_cases import PROJECT, sha
import build_e2_c_shell_bundle as shell_bundle

PROFILE = 'e2-editor-v27'
TYPED_INSERT = 'document-sdk-insert-typed-text'
PAGE_SHA256 = 'b63d8ee53659c8b6216ecfc6ddaf4e3ef909f99f96b5975204ff31039816b1c7'
CANDIDATE_SHELL_DIGEST = '6eb7ca108ea77c4ad735f97344ee9befa76a2c3c76fb7a6bce2f6da1bdc5c094'
BUNDLE = 'e2/editor-shell-v2-bundle-v81.json'
BUNDLE_FILE_SHA256 = '91f180232b33f2addb410cae25834561780c3b5344d021fed53e0e5b31fffbb1'
ARTIFACT_PINS = {
    'probe.wasm': 'c089dfd699d646e373113fa8437d05e01e150987302e9851543a31debc7ffb3c',
    'probe.js': '0a73eb5ae83e42d6ce799b7ba32d6a4f821b184c66eff2053be7a83c1a4e6526',
    'sdk-worker.js': '8152448ab83bc323edfa6982a1db08c4367b15b4c99978eeb1b39b3ef41a669d',
    'sdk-manifest.json': 'd5d076399b921d2749fcb4ded45aa1a7613759a330c42e307a82dce6fbd4e9fe'}
ARCHIVED_PROFILE = PROJECT / 'build/archive/e2-editor-v27-c089dfd6-worker-8152448a'


def shell():
    """The live shell: the bundle tool's own computation, equal to frozen generation 81."""
    state = shell_bundle.compute(PROJECT)
    if state['digest'] != CANDIDATE_SHELL_DIGEST:
        raise ValueError('shell digest is not generation 81: ' + state['digest'])
    if sha(PROJECT / BUNDLE) != BUNDLE_FILE_SHA256:
        raise ValueError('generation 81 manifest differs: ' + BUNDLE)
    frozen = json.loads((PROJECT / BUNDLE).read_text())
    if frozen['bundleSha256'] != state['digest'] or {r['path']: r['sha256'] for r in frozen['included']} != state['hashes']:
        raise ValueError('live shell is not frozen generation 81')
    for path in state['included']:
        if state['distHashes'].get(path) != state['hashes'][path]:
            raise ValueError('shell source/dist differs: ' + path)
    if state['hashes'][shell_bundle.ENTRYPOINT.as_posix()] != PAGE_SHA256:
        raise ValueError('page is not the generation-81 page')
    return state


def identity():
    directory = PROJECT / 'dist/profiles' / PROFILE
    for name, expected in ARTIFACT_PINS.items():
        if sha(directory / name) != expected or sha(ARCHIVED_PROFILE / name) != expected:
            raise ValueError('v27 profile/archive identity differs: ' + name)
    manifest = json.loads((directory / 'sdk-manifest.json').read_text())
    contract = manifest['editorContract']
    if manifest['profile'] != PROFILE or contract['abiVersion'] != 6 or contract.get('typedInsert') != TYPED_INSERT:
        raise ValueError('v27 ABI/profile/typedInsert differs')
    state = shell()
    paths = set(ARTIFACT_PINS)
    paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
    for pack in manifest.get('resourcePacks', []):
        paths.update((pack['data'], pack['metadata']))
    return {'profile': PROFILE, 'editorAbi': 6, 'typedInsert': TYPED_INSERT,
            'artifacts': {n: sha(directory / n) for n in sorted(paths)},
            'shell': {'generation': 81, 'bundle': BUNDLE, 'bundleFileSha256': BUNDLE_FILE_SHA256, 'digest': state['digest'],
                      'included': {p: state['hashes'][p] for p in state['included']}},
            'pageSha256': PAGE_SHA256, 'originalHtmlSha256': sha(PROJECT / 'web/e2-editor.html')}
