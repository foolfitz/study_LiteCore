#!/usr/bin/env python3
"""Read the existing native R1 population; this is not a WASM verdict.

The reference cells come from the recorded ref/emu pairs, not a handwritten
shape list.  Historical timings, fonts and offsets are evidence, never a
license to use native coordinates as a browser-layout oracle.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NATIVE = Path('findings/evidence/129/native')
ROUNDS = (1, 2, 3)  # The already recorded native repetitions, not new runs.
SOURCES = (
    ('main', 'point-click-round-20261012T031459Z'),
    ('wrap-keys', 'point-click-extras-round-20261012T033055Z'),
    ('wrap-drag', 'point-click-extras-drag-round-20261012T034525Z'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def collect(root=ROOT):
    root = Path(root)
    files, cells, controls = {}, [], []
    fixtures = {}
    for group, directory in SOURCES:
        relative = NATIVE / directory
        folder = root / relative
        source = folder / 'tool-source-as-run.cpp'
        inputs = folder / 'inputs.sha256'
        for path in (source, inputs):
            files[str(path.relative_to(root))] = sha(path)
        pins = dict(line.split(None, 1)[::-1] for line in inputs.read_text().splitlines() if line.strip())
        source_pins = [digest for name, digest in pins.items()
                       if name.endswith('/tools/f129_native_point_click.cpp')]
        require(source_pins == [sha(source)], f'{relative}: as-run source binding')
        for name, digest in pins.items():
            if '/test-docs/f129/' not in name:
                continue
            fixture = Path('wasm_sdk_probe/test-docs/f129') / Path(name).name
            require(sha(root / fixture) == digest, f'{fixture}: fixture binding')
            require(str(fixture) not in fixtures or fixtures[str(fixture)] == digest,
                    f'{fixture}: inconsistent historical fixture pins')
            fixtures[str(fixture)] = digest
        references, emulations = {}, {}
        for round_id in ROUNDS:
            raw = folder / f'arms-r{round_id}.jsonl'
            status = folder / f'arms-r{round_id}.exit'
            require(status.read_text().strip() == 'exit 0', f'{status}: native exit')
            for path in (raw, status):
                files[str(path.relative_to(root))] = sha(path)
            rows = [json.loads(line) for line in raw.read_text().splitlines() if line.strip()]
            require(rows, f'{raw}: empty input')
            require(not any(row.get('fatal') for row in rows), f'{raw}: native fatal')
            for line_no, row in enumerate(rows, 1):
                require(row.get('round') == round_id, f'{raw}:{line_no}: wrong round')
                if row.get('kind') not in ('ref', 'emu'):
                    continue
                key = (row['shape'], row['key'])
                mapping = references if row['kind'] == 'ref' else emulations
                mapping.setdefault(key, {})
                require(round_id not in mapping[key], f'{raw}: duplicate {row["arm"]}')
                require(row['text'].count('#') == 1, f'{raw}: nonunique marker {row["arm"]}')
                mapping[key][round_id] = {'path': str(raw.relative_to(root)),
                                         'line': line_no, 'record': row}
        require(references and references.keys() == emulations.keys(),
                f'{relative}: empty or unpaired ref/emu population')
        for (shape, key), observations in sorted(references.items()):
            peers = emulations[(shape, key)]
            require(set(observations) == set(ROUNDS) == set(peers),
                    f'{relative}: incomplete repetitions for {shape}/{key}')
            first = observations[ROUNDS[0]]['record']
            fields = ('made', 'selectedAfterKey', 'cursorAfter', 'text', 'selectionState')
            require(all(all(item['record'].get(field) == first.get(field) for field in fields)
                        for item in observations.values()),
                    f'{relative}: unstable native reference {shape}/{key}')
            require(first['selectedAfterKey'] == '', f'{relative}: move did not collapse {shape}/{key}')
            cell_id = f'{group}/{shape}/{key}'
            wrong = [round_id for round_id in ROUNDS
                     if peers[round_id]['record']['text'] != observations[round_id]['record']['text']]
            require(not wrong or wrong == list(ROUNDS), f'{relative}: unstable emulation control')
            cell = {'id': cell_id, 'group': group, 'shape': shape, 'key': key,
                    'native': {field: first.get(field) for field in fields},
                    'nativeMarkerIndex': first['text'].index('#'),
                    'observations': [{'round': r, **{k: v for k, v in observations[r].items()
                                                   if k != 'record'}} for r in ROUNDS],
                    'oldClickEmulationDiffers': bool(wrong)}
            cells.append(cell)
            if wrong:
                controls.append({'id': cell_id, 'rounds': wrong,
                                 'nativeMarkerIndex': cell['nativeMarkerIndex'],
                                 'emulatedMarkerIndex': peers[ROUNDS[0]]['record']['text'].index('#')})
    require(len({cell['id'] for cell in cells}) == len(cells), 'duplicate cell IDs')
    return {'schema': 1, 'purpose': 'existing-native-R1-input-index-only',
            'wasmVerdict': 'NOT_ESTABLISHED',
            'nativeRounds': list(ROUNDS), 'cellCount': len(cells),
            'nativeObservationCount': len(cells) * len(ROUNDS),
            'groups': {group: sum(cell['group'] == group for cell in cells) for group, _ in SOURCES},
            'files': files, 'fixtures': fixtures, 'cells': cells,
            'wrongOldClickControls': controls,
            'limitations': ['Native pixels and offsets do not establish browser layout parity.',
                            'The dragend folder contains emuend controls, not more ref cells.',
                            'A feature protocol must bind public setup and a layout-aware oracle.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = collect()
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        with args.output.open('x') as output:
            output.write(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
