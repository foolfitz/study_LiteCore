"""What names the build under test for a frozen generation's four-arm (F4) and F3 runs, read from
e2/generations/generation-NN.json.

One tool for every generation from 90 on (CLAUDE.md, the section on cadence, item 2; PLAN-2026-11-04 section 3.1), in
place of the per-generation copies tools/v25..v89_four_arms_identity.py, which stay as they are (each bound by its own
generation's evidence).  generation-89.json carries tools/v89_four_arms_identity.py's constants; the witness that this
tool reads a generation as that copy did is V0' 90's v89 stage (judge_product_four_arms.py --generation 89 re-reads
F4-89 byte for byte) and tests/test_four_arms_identity.py (the constants equal the copy's).

The checks are v89_four_arms_identity.py's, in the same order, with the generation's values:
  shell()     the live shell (the bundle tool's own computation) is the frozen generation: digest, manifest file,
              every included module equal to the manifest and to its dist/ copy, the page the generation's page
  identity()  the profile in dist/profiles and its archive both carry the four pinned artifacts; ABI 6 with the
              typedInsert leaf; then shell(); the record the four-arm readers compare
"""
import json

from v23_feature_selection_cases import PROJECT, sha
import build_e2_c_shell_bundle as shell_bundle

TYPED_INSERT = 'document-sdk-insert-typed-text'
GENERATIONS = PROJECT / 'e2/generations'


class Generation:
    def __init__(self, number):
        self.number = int(number)
        self.path = GENERATIONS / f'generation-{self.number}.json'
        data = json.loads(self.path.read_text())
        if data['generation'] != self.number:
            raise ValueError(f'{self.path.name} names generation {data["generation"]}')
        self.file_sha256 = sha(self.path)
        self.profile = data['profile']
        self.page_sha256 = data['pageSha256']
        self.shell_digest = data['shellDigest']
        self.bundle = data['bundle']
        self.bundle_file_sha256 = data['bundleFileSha256']
        self.artifact_pins = dict(data['artifactPins'])
        self.archived_profile = PROJECT / data['archivedProfile']

    def shell(self):
        n = self.number
        state = shell_bundle.compute(PROJECT)
        if state['digest'] != self.shell_digest:
            raise ValueError(f'shell digest is not generation {n}: ' + state['digest'])
        if sha(PROJECT / self.bundle) != self.bundle_file_sha256:
            raise ValueError(f'generation {n} manifest differs: ' + self.bundle)
        frozen = json.loads((PROJECT / self.bundle).read_text())
        if frozen['bundleSha256'] != state['digest'] or {r['path']: r['sha256'] for r in frozen['included']} != state['hashes']:
            raise ValueError(f'live shell is not frozen generation {n}')
        for path in state['included']:
            if state['distHashes'].get(path) != state['hashes'][path]:
                raise ValueError('shell source/dist differs: ' + path)
        if state['hashes'][shell_bundle.ENTRYPOINT.as_posix()] != self.page_sha256:
            raise ValueError(f'page is not the generation-{n} page')
        return state

    def identity(self):
        directory = PROJECT / 'dist/profiles' / self.profile
        for name, expected in self.artifact_pins.items():
            if sha(directory / name) != expected or sha(self.archived_profile / name) != expected:
                raise ValueError(f'{self.profile} profile/archive identity differs: ' + name)
        manifest = json.loads((directory / 'sdk-manifest.json').read_text())
        contract = manifest['editorContract']
        if manifest['profile'] != self.profile or contract['abiVersion'] != 6 or contract.get('typedInsert') != TYPED_INSERT:
            raise ValueError(f'{self.profile} ABI/profile/typedInsert differs')
        state = self.shell()
        paths = set(self.artifact_pins)
        paths.update(v.removeprefix('./') for v in manifest['artifactFiles'].values())
        for pack in manifest.get('resourcePacks', []):
            paths.update((pack['data'], pack['metadata']))
        return {'profile': self.profile, 'editorAbi': 6, 'typedInsert': TYPED_INSERT,
                'artifacts': {n: sha(directory / n) for n in sorted(paths)},
                'shell': {'generation': self.number, 'bundle': self.bundle, 'bundleFileSha256': self.bundle_file_sha256,
                          'digest': state['digest'], 'included': {p: state['hashes'][p] for p in state['included']}},
                'pageSha256': self.page_sha256, 'originalHtmlSha256': sha(PROJECT / 'web/e2-editor.html')}
