Review this completed R1 prerequisite unit adversarially. Reply in English. Identify only concrete bugs/false claims with file/line or code references, exploit/mutation and consequence. Distinguish an input census from a WASM verdict: no runtime/feature result is claimed here. The existing native population is72 cells/216 observations, tool-derived from ref/emu logs; known three wrong-click Down cells are independently measured. An owner-delegated Astra approved36 literal vs36 same-browser layout-control comparisons as stated. No new feature grants or criteria may be invented. Do not treat the fact that runtime is pending as a defect. Check the Python collector's provenance and completeness claims and whether the protocol could falsely count unsupported setup/oracle. No tools or external resources. State NO_CONCRETE_FINDING if appropriate.


===== handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md =====
# R1 input census and executable comparison protocol

Authority: ordered-commands sections6 and9.3, link-batch R1, and owner-delegated Astra `/root/astra_calc_scope`'s protocol decision of2026-10-26. This supplies the existing R1 prerequisite; it grants no new case, action, native coordinate assumption, build or host operation. The finite hard diagnostic stage is already closed by `RULING-2026-10-26-v23-diagnostic-closure.md`.

## Population and exact historical evidence

Run `python3 wasm_sdk_probe/tools/collect_v23_r1_inputs.py` from the repository root. The source-owned ref/emu records generate72 unique cells:42 in `point-click-round-20261012T031459Z`,18 in `point-click-extras-round-20261012T033055Z`,12 in `point-click-extras-drag-round-20261012T034525Z`, all under `findings/evidence/129/native/`. Each has three retained native reference observations. The generated index at `findings/evidence/link-batch-v23/feature-protocol/r1/native-inputs.json` binds raw records/line numbers, full marked text, cursor/selection state, source-as-run, input manifests, successful exit files and actual fixture hashes. Its SHA256 is `6e13c04d6acc901bdc7988d65ac4e616a9bf35ddbcce5549dbb76f6e40ab6fdd`.

Every shape below contributes all six existing keys Left,Right,Up,Down,Home,End; this table describes the recorded population rather than allocating another one. The original native setup code is the source-as-run in each indexed directory. WASM setup uses actual public search/coordinate placement/drag or the six authorized moves, with shape readback. It does not require a public CtrlDown action. Recreate semantic positions in the actual browser layout, not the native source's fixed coordinates or discovered numeric wrap offsets.

| Group / shape | Recorded semantic setup and point |
| --- | --- |
| main / p2-forward | `arrow-selection.fodt`, P2 `BETA GAMMA`, forward selection of offsets9..19; point19. |
| main / p2-backward | Same text selected backward from19 to9; point9. |
| main / s1 | `arrow-selection-shapes.fodt`, discover first visual wrap W by a fresh Right walk and cursor y transition; select ten characters before W with ShiftRight; point at start of line2. |
| main / s2 | Same fixture, select `visual line` in the first hard-break line; point immediately before the line break. |
| main / s3 | Same fixture, select `paragraph` plus its paragraph break; point in the empty paragraph. |
| main / s4 | Same fixture, select `cell A1` within A1; point after that substring. |
| main / s5 | Same fixture, cross A1→B1 as the source does. Native readback is both whole cells, with point at B1 start. Require the actual cell-selection/semantic witness; a small ordinary text range is not this shape. |
| wrap-keys / s1e | Shapes fixture, from W−10 use ShiftEnd; point displayed at the end of line1, before the trailing space. |
| wrap-keys / m1r | `arrow-selection-wrap.fodt`, discover midword wrap B; select ten characters before B with ShiftRight; point at start of line2. |
| wrap-keys / m1e | Same token and starting position, select with ShiftEnd; point displayed at line1 end while selection end is line2 start. |
| wrap-drag / s1d | Shapes fixture, drag from inside the final characters of line1 past its right edge; native selected text includes the trailing space. Point is displayed at line1 end, selection end at line2 start. |
| wrap-drag / m1d | Token fixture, corresponding drag across its midword wrap; same two-location affinity as m1e. |

Use the original fixture bytes (the index verifies all three SHA256s). For setup, capture the selected text/type, paragraph/table identity, caret, selection start/end rectangles and actual visual-line transition/affinity. A setup which does not reproduce those semantics is NE and cannot count. Search/placement is setup only: the candidate key itself must go from the existing range through the product's public six-move path without a preliminary collapse click. Capture its actual request/action/extend flag and response plus unchanged revision/changed:false, collapsed readback and the final marker/export witness. No private diagnostic input supplies a public acceptance result.

## Owner-proxy comparison decision:36 literal and36 layout-relative cells

Astra approved this classification before feature wiring. There is no missing native oracle for these72 cells under the rules below. Actual feature setup/affinity and outcomes have not yet been measured; they remain NE until the feature artifact exists and the declared witnesses pass. Missing browser setup does not authorize guessing an endpoint and does not block source preparation once the protocol prerequisites as a whole close.

- **36 literal logical landings:** Left/Right for all12 shapes (24); Home/End for the six nonwrap shapes p2-forward,p2-backward,s2,s3,s4,s5 (12). Compare the native marked text/logical document position, preserving paragraph, hard-break and cell topology. For the Home/End rows, first establish the same single visual line/hard-break/table condition. If browser wrapping invalidates that premise, the literal predicate is NE; do not compare native pixels or silently relabel it a pass.
- **36 layout-relative landings:** Up/Down for all12 shapes (24); Home/End for s1,s1e,m1r,m1e,s1d,m1d (12). Create a fresh same-browser control from the shape's independently established active point and affinity, then send the same unshifted own key with a collapsed caret. Compare the candidate range-key's resulting caret/logical marker against that control. The control setup cannot be obtained from the candidate range-key result. Its semantic point/affinity must be witnessed before either key.

The point-collapse reference is independently supported by the native paired measurements: `ref` equals `emu` in all cells except three Down cells. For **m1e/Down,s1d/Down,m1d/Down**, use the independent corrected `emuend` rule: position the control at the actual browser `TEXT_SELECTION_END` rectangle at line2 start, not the visible cursor at line1 end. The native `point-click-extras-dragend-round-20261012T034823Z` has corrected emuend controls for all six keys on those three shapes, each in three rounds, and all agree with ref. This is per-cell retained evidence, not a general point-click workaround or a new public capability. The three wrong-emu Down cells are causal controls, not a replacement for the remaining69 cells.

## Execution/default/closure

Run each of the72 cells once in each browser, as the protocol ruling specifies; the three historical native repetitions do not multiply the new browser population. Bind actual feature artifacts, public page/import graph, fixture bytes, UA, setup/control/candidate traces and unique observation identities before judging. Keep old native and diagnostic evidence immutable.

No setup, missing control, a nonpublic candidate request, an uncollapsed result, changed revision, missing required marker/export or a late/error/recovery result cannot count as R1 PASS. Valid setup with a mismatching logical/control landing is FAIL. If required setup/oracle observations remain unavailable, R1 is NOT_ESTABLISHED and six range movements cannot be declared shipped. Record each cell separately; do not substitute an aggregate percentage. The finite closure point is the complete generated72-cell population in both browsers, with the three old-workaround controls distinguished. No new timeout, tolerance, browser repetition multiplier or statistical condition is introduced here.

===== wasm_sdk_probe/tools/collect_v23_r1_inputs.py =====
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

===== wasm_sdk_probe/tests/test_v23_r1_inputs.py =====
#!/usr/bin/env python3
"""Reject broken native input provenance before an R1 protocol uses it."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'collect_v23_r1_inputs', ROOT / 'wasm_sdk_probe/tools/collect_v23_r1_inputs.py')
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class NativeR1InputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for _, directory in collector.SOURCES:
            source = ROOT / collector.NATIVE / directory
            target = self.root / collector.NATIVE / directory
            target.mkdir(parents=True)
            for pattern in ('inputs.sha256', 'tool-source-as-run.cpp', 'arms-r*.jsonl', 'arms-r*.exit'):
                for path in source.glob(pattern):
                    shutil.copyfile(path, target / path.name)
        fixtures = Path('wasm_sdk_probe/test-docs/f129')
        (self.root / fixtures).mkdir(parents=True)
        for path in (ROOT / fixtures).glob('arrow-selection*.fodt'):
            shutil.copyfile(path, self.root / fixtures / path.name)
        self.folder = self.root / collector.NATIVE / collector.SOURCES[0][1]
        self.raw = self.folder / 'arms-r1.jsonl'

    def tearDown(self):
        self.temp.cleanup()

    def rows(self):
        return [json.loads(line) for line in self.raw.read_text().splitlines()]

    def write(self, rows):
        self.raw.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def test_actual_population_and_old_workaround_red_controls(self):
        result = collector.collect(self.root)
        self.assertEqual({'main': 42, 'wrap-keys': 18, 'wrap-drag': 12}, result['groups'])
        self.assertEqual(216, result['nativeObservationCount'])
        self.assertEqual({'wrap-keys/m1e/Down', 'wrap-drag/m1d/Down', 'wrap-drag/s1d/Down'},
                         {row['id'] for row in result['wrongOldClickControls']})
        self.assertEqual('NOT_ESTABLISHED', result['wasmVerdict'])

    def test_missing_directory_cannot_pass_vacuously(self):
        shutil.rmtree(self.folder)
        with self.assertRaises(FileNotFoundError):
            collector.collect(self.root)

    def test_missing_reference_is_rejected(self):
        rows = self.rows()
        self.write([row for row in rows if row.get('arm') != 'ref-p2-forward-Left'])
        with self.assertRaisesRegex(ValueError, 'incomplete repetitions'):
            collector.collect(self.root)

    def test_duplicate_reference_is_rejected(self):
        rows = self.rows()
        self.write(rows + [next(row for row in rows if row.get('kind') == 'ref')])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            collector.collect(self.root)

    def test_changed_native_reference_cannot_hide_in_other_rounds(self):
        rows = self.rows()
        next(row for row in rows if row.get('kind') == 'ref')['text'] += 'wrong'
        self.write(rows)
        with self.assertRaisesRegex(ValueError, 'unstable native reference'):
            collector.collect(self.root)

    def test_fixture_drift_is_rejected(self):
        (self.root / 'wasm_sdk_probe/test-docs/f129/arrow-selection.fodt').write_text('wrong')
        with self.assertRaisesRegex(ValueError, 'fixture binding'):
            collector.collect(self.root)

    def test_as_run_source_drift_is_rejected(self):
        (self.folder / 'tool-source-as-run.cpp').write_text('wrong')
        with self.assertRaisesRegex(ValueError, 'as-run source binding'):
            collector.collect(self.root)

    def test_failed_native_process_is_rejected(self):
        (self.folder / 'arms-r1.exit').write_text('exit 1\n')
        with self.assertRaisesRegex(ValueError, 'native exit'):
            collector.collect(self.root)


if __name__ == '__main__':
    unittest.main()
