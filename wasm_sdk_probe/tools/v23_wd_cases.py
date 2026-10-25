"""Fixed W-D wire population and native oracle sources, not a new gate."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / 'findings/evidence/link-batch-v23/native/ordered-commands'
sys.path.insert(0, str(NATIVE / 'tool'))
from run_arms import ARMS

# (route, name): the actual request projection is checked independently from
# the page's labels. The last two private inputs are native L's observer.
P, D = 'public', 'private-closed-input'
PLANS = {
    'd1': [(P, 'move-line-down'), (P, 'move-document-start'), (P, 'delete-backward')],
    'd2': [(P, 'move-character-right')] * 4 + [(P, 'move-character-left'), (P, 'delete-forward')],
    'd2p': [(P, 'move-character-right')] * 3 + [(P, 'delete-backward')],
    'd3': [(P, 'move-character-right'), (P, 'move-character-left'), (P, 'move-character-right'), (P, 'insert-x')],
    'd4': [(D, 'shift-right'), (D, 'left-on-range'), (P, 'set-bold')],
    'd5': [(P, 'move-character-right')] * 4 + [(D, 'shift-left'), (P, 'delete-selection')],
    'd6': [(P, 'move-character-right')] * 3 + [(P, 'move-character-left')] * 3
          + [(P, 'place-recorded-caret'), (P, 'insert-x')],
    'merge': [(P, 'move-line-down'), (P, 'move-line-home'), (P, 'delete-backward')],
    'd7i': [(P, 'move-character-left'), (P, 'delete-forward')],
    'd7ii': [(P, 'move-character-right'), (P, 'move-character-left'), (P, 'delete-backward')],
    'd7iii': [(P, 'move-character-right'), (P, 'move-character-left'), (P, 'delete-backward')],
    'd7plain': [(P, 'move-character-right'), (P, 'move-character-left'), (P, 'delete-backward')],
}
BASE = {arm['name']: arm for arm in ARMS if arm['decides']}
assert set(BASE) == set(PLANS) - {'merge', 'd7i', 'd7ii', 'd7iii', 'd7plain'}, 'native decision population drift'
FIXTURES = {arm['name']: arm['fixture'] for arm in ARMS}
FIXTURES['merge'] = 'plain3'
PRIVATE = {4: 'left-on-range', 5: 'shift-left', 6: 'shift-right',
           7: 'locator-shift-end', 8: 'locator-shift-home'}
LOCATOR = [(D, 'locator-shift-end'), (D, 'locator-shift-home')]


def instrument_files():
    """Actual local import graph plus the W-D runner/reader/case sources."""
    from build_e2_c_shell_bundle import imports_of
    sdk = ROOT / 'wasm_sdk_probe'
    files = {sdk / name for name in ('tools/run_v23_diagnostic.py', 'tools/judge_v23_diagnostic.py',
             'tools/judge_v23_wd.py', 'tools/v23_wd_cases.py', 'web/v23-diagnostic.html')}
    pending = [sdk / 'web/v23-diagnostic.js']
    while pending:
        path = pending.pop().resolve()
        if path in files:
            continue
        if not path.is_file():
            raise ValueError(f'missing W-D local module: {path}')
        files.add(path)
        base = sdk if path.parent == sdk / 'web' else path.parent
        for specifier in imports_of(path.read_text()):
            if not specifier.startswith('.'):
                continue
            imported = (base / specifier).resolve()
            if imported.parent == sdk and imported.name.startswith('v23-diagnostic'):
                imported = sdk / 'web' / imported.name
            pending.append(imported)
    return sorted(files)
