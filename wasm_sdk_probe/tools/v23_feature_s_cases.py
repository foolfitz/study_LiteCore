#!/usr/bin/env python3
"""Source-only §9.3 S1–S5 membership and oracle inventory; never runs a probe."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = 'findings/evidence/link-batch/extend-signatures/run-20261013T095104Z'
PINS = {
    'arms-r1.jsonl': '56130009e0b8745bb0438ad2559fcde8ead099f206f5a3d73aeafe97849ed0cd',
    'arms-r2.jsonl': '32d6b808cce3c9aaa076599976dc6c5d24dd2812ba3bdf287870b0d4678959b2',
    'arms-r3.jsonl': 'e5ad753731c9f2bf6c8e47bf01fba52d8a8c62531fec9f30490cb4d0980cb53f',
    'fixture-as-run.fodt': 'ede9cb038b8edabfb8dc6c05fb46b15deacfc6f529756ca816096bfd2c18b7bc',
    'tool-source-as-run.cpp': '1e29f73bfa0a0b73a5ced6d5f5a91fbaac48bfdfa1fb1c1799514aa0913eef17',
}
# Existing six actions; this table grants nothing and allocates no IDs.
MOVES = {'Left': ('move-character-left', 1), 'Right': ('move-character-right', 2),
         'Up': ('move-line-up', 16), 'Down': ('move-line-down', 17),
         'Home': ('move-line-home', 18), 'End': ('move-line-end', 19)}
# §10.4 + §12.4, resolved by original ruling-3 Q4's Sequence A.
FAMILIES = {
    'backspace': ['SHIFT', 'Backspace'],
    'delete': ['SHIFT', 'Delete'],
    'type': ['SHIFT', 'text:x'],
    'backspace-twice': ['SHIFT', 'Backspace', 'Backspace'],
    'delete-twice': ['SHIFT', 'Delete', 'Delete'],
    'backspace-before-and-after': ['Backspace', 'SHIFT', 'Backspace'],
    'delete-before-and-after': ['Delete', 'SHIFT', 'Delete'],
}
EXCLUDED_PRE_RED = {'shift-Left@doc-start', 'shift-Right@doc-end'}


def read_rounds(root=ROOT):
    directory = root / ARCHIVE
    for name, expected in PINS.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'changed native evidence: {name}')
    return [[dict(row, sourceLine=n) for n, line in enumerate(
        (directory / f'arms-r{r}.jsonl').read_text().splitlines(), 1)
        if (row := json.loads(line))] for r in (1, 2, 3)]


def derive(rounds):
    """Membership comes from actual arm rows, never a copied shape list."""
    if len(rounds) != 3: raise ValueError('three archived native rounds required')
    indices = []
    for rows in rounds:
        if any(row.get('fatal') for row in rows): raise ValueError('native fatal')
        measured = [r for r in rows if r.get('kind') in ('shift', 'plain', 'interaction')]
        index = {r['arm']: r for r in measured}
        if not measured or len(index) != len(measured): raise ValueError('empty/duplicate native arms')
        indices.append(index)
    if any(set(index) != set(indices[0]) for index in indices):
        raise ValueError('native round membership differs')
    shift = sorted(k for k, r in indices[0].items() if r['kind'] == 'shift')
    plain = sorted(k for k, r in indices[0].items() if r['kind'] == 'plain')
    interactions = sorted(k for k, r in indices[0].items() if r['kind'] == 'interaction')
    if (len(shift), len(plain), len(interactions)) != (84, 24, 9):
        raise ValueError('declared native table cardinality differs')
    for key in shift + plain:
        rows = [index[key] for index in indices]
        if any((r['kind'], r['shape'], r['key'], r['shift']) !=
               (rows[0]['kind'], rows[0]['shape'], rows[0]['key'], rows[0]['shift']) for r in rows):
            raise ValueError(f'native arm identity differs: {key}')
        for r in rows:
            if r['before']['getTextSelection'] != r['shapeMake']['expectedSelection']:
                raise ValueError(f'native setup mismatch: {key}')
    no_callbacks = [key for key in shift + plain if all(
        not any(cb['tMs'] >= 0 for cb in index[key]['callbacks']) for index in indices)]
    pre_red = [key for key in shift if indices[0][key]['key'] in ('Left', 'Right')
               and not indices[0][key]['shapeMake']['expectRange'] and key not in EXCLUDED_PRE_RED]
    if len(no_callbacks) != 10 or len(pre_red) != 16:
        raise ValueError('no-callback or corrected pre-red membership differs')

    def refs(key):
        return [{'path': f'{ARCHIVE}/arms-r{n}.jsonl', 'line': index[key]['sourceLine'],
                 'round': n, 'arm': key} for n, index in enumerate(indices, 1)]

    cases = []
    for key in shift + plain:
        row = indices[0][key]
        setup = row['shapeMake']
        literal = ('native-literal' if row['key'] in ('Left', 'Right') else
                   'native-literal-only-with-single-line-witness' if row['key'] in ('Home', 'End') else
                   'same-browser-unshifted-endpoint')
        cases.append({'id': key, 'shape': row['shape'], 'key': row['key'], 'extendSelection': row['shift'],
            'action': MOVES[row['key']][0], 'externalId': MOVES[row['key']][1],
            'memberships': ['S2'] + (['S1', 'S5-source'] if row['shift'] else []) +
                           (['S3'] if key in no_callbacks else []) + (['v19-pre-red'] if key in pre_red else []),
            'setup': {'method': setup['method'], 'logicalPointNames': [p['name'] for p in setup['points']],
                      'expectedSelection': setup['expectedSelection'], 'expectRange': setup['expectRange'],
                      'expectedMovingPointName': setup['expectedCursorPoint'],
                      'haveExpectHomeEnd': setup['haveExpectHomeEnd'],
                      'expectedShiftHome': setup['expectShiftHome'], 'expectedShiftEnd': setup['expectShiftEnd']},
            'nativeReferences': refs(key), 'nativeAfterSelectionText': [i[key]['after']['getTextSelection'] for i in indices],
            'nativeOracleStatus': 'AVAILABLE_SELECTION_SNAPSHOTS_ONLY',
            'endpointOracle': literal,
            'browserEndpointOracleStatus': 'NOT_ESTABLISHED_UNPERFORMED',
            'default': 'NOT_ESTABLISHED_UNPERFORMED'})
    s4 = []
    for key in interactions:
        r = indices[0][key]
        s4.append({'id': key, 'firstKey': r['firstKey'], 'step': r['step'],
                   'action': r['action'], 'logicalPointNames': [p['name'] for p in r['points']],
                   'expectedSelection': r['expectedSelection'],
                   'expectedShiftHomeAfterClick': r['expectedShiftHomeAfterClick'],
                   'nativeReferences': refs(key), 'nativeOracleStatus': 'AVAILABLE_INTERACTION_SNAPSHOTS',
                   'browserStatus': 'NOT_ESTABLISHED_UNPERFORMED'})
    s5 = []
    for base in cases:
        if not base['extendSelection']: continue
        for family, sequence in FAMILIES.items():
            s5.append({'id': base['id'] + '/' + family, 'sourceArm': base['id'], 'family': family,
                'sequence': [f"Shift+{base['key']}" if op == 'SHIFT' else op for op in sequence],
                'comparison': 'paragraph-text-sequence' if family == 'type' else 'reduce_content-byte-equality',
                'layoutRule': base['endpointOracle'],
                'referencePolicy': ('native' if base['key'] in ('Left', 'Right') else
                    'native-if-single-line-otherwise-settled-wasm' if base['key'] in ('Home', 'End') else
                    'settled-wasm'),
                'settledWasmOracle': {'status': 'NOT_APPLICABLE' if base['key'] in ('Left', 'Right') else
                    'NOT_ESTABLISHED_UNPERFORMED', 'freshArm': True,
                    'sameInputs': ['fixture', 'profile', 'browser', 'shape', 'sequence'],
                    'waitOnlyInReference': 'after Shift terminal, >=500ms actual engine-state plus active-selection witness before follow-up'},
                'nativeContinuationOracle': {'status': 'NOT_APPLICABLE' if base['key'] in ('Up', 'Down') else
                    'NOT_ESTABLISHED_MISSING_EXECUTION',
                    'requiredArtifacts': ['exact-input-and-sequence', 'actual-native-before-and-after-save',
                                          'native-pre-key-and-post-key-selection', 'core-tool-fixture-identities'],
                    'existingSnapshotReferences': base['nativeReferences']},
                'continuationTiming': 'actual-product-beforeinput-without-awaiting-predecessor',
                'overlapEvidence': 'actual-posted-unanswered-move-or-extend-request-keys-at-each-continuation-beforeinput',
                'default': 'NOT_ESTABLISHED_WITHHOLD_PAGE_EXTEND_SELECTION'})
    return {'schema': 1, 'scope': 'source-only executable membership; no feature/runtime authorization',
        'fixture': {'path': f'{ARCHIVE}/fixture-as-run.fodt', 'sha256': PINS['fixture-as-run.fodt']},
        'inputPins': {f'{ARCHIVE}/{name}': value for name, value in PINS.items()},
        'counts': {'S1': len(shift), 'S2': len(cases), 'v19PreRed': len(pre_red),
                   'S3': len(no_callbacks), 'S4': len(s4), 'S5': len(s5)},
        'browsers': ['chrome', 'firefox'], 'executionsPerCellPerBrowser': 1,
        'historicalNativeRoundsAreRuntimeMultiplier': False,
        'contracts': {
            'S1': {'anchorUnchanged': True, 'movingEndpoint': 'same-browser independent unshifted control',
                   'logicalCoordinates': 'paragraph index and Unicode code-point offset; never native twips'},
            'S2': {'wireStateOperation': 'editorGetStateV1', 'wireActiveSelectionOperation': 'getSelection',
                   'minimumReadbackDelayAfterTerminalMs': 500,
                   'compare': ['caret', 'selection'], 'captureFullState': True,
                   'uniqueTerminalPerRequest': True, 'moveChanged': False, 'revisionUnchanged': True,
                   'collapsedMatchesActiveType': True,
                   'recordLateCursorThrough': 'actual close reply; no extra sleep'},
            'v19PreRed': {'readiness': 'separate fresh-document actual open/state/edit/save positive witness',
                         'route': 'existing public SDK client, not old Shift-dropping page',
                         'requiredRed': 'successful move terminal with stale reply versus delayed engine state',
                         'unexpectedGreen': 'stop and investigate before proceeding',
                         'unavailableOrRefused': 'NOT_ESTABLISHED; not an expected-red witness'},
            'S3': {'completion': 'verified-move-readback', 'changed': False,
                   'revisionUnchanged': True, 'recoveryForbidden': True},
            'S5': {'typedLiteral': 'x', 'nativeOracleExecutions': 'missing where native comparison is required',
                   'layoutDependent': 'fresh same-input WASM arm with settled wait before follow-up',
                   'oracleAuthority': 'findings/evidence/link-batch/review/ruling-3.md:55',
                   'overlapCount': 'derive actual posted move/extend request keys minus matching terminal/cancel keys',
                   'queuedAdmissionsAreSeparate': True}},
        'cases': cases, 'S4': s4, 'S5': s5,
        'preRedExcluded': sorted(EXCLUDED_PRE_RED),
        'oracleFunctions': {'delete': 'wasm_sdk_probe/tools/run_merge_wasm_shakedown.py:reduce_content',
                            'type': 'wasm_sdk_probe/tools/odt_paragraphs.py:paragraph_texts_from_xml'},
        'closure': 'all declared per-browser cells satisfy their oracle; no percentage substitute; missing oracle is NE',
        'overlapClosure': 'report overlapping and non-overlapping cells separately; empty overlap set FAIL'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    table = derive(read_rounds())
    table['generator'] = {'path': str(Path(__file__).resolve().relative_to(ROOT)),
                          'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    table['oracleSourcePins'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ('wasm_sdk_probe/tools/run_merge_wasm_shakedown.py',
                     'wasm_sdk_probe/tools/odt_paragraphs.py')}
    result = json.dumps(table, indent=2, ensure_ascii=False) + '\n'
    if args.output: args.output.write_text(result)
    else: print(result, end='')

if __name__ == '__main__': main()
