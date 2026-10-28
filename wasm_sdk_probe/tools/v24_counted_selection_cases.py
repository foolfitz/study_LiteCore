"""Fresh v24 counted plan; preserve the preparation plan and all live-asserted bytes."""
import ast
from pathlib import Path

import v24_feature_selection_cases as preparation
from v24_feature_selection_cases import (ROOT, PROJECT, BROWSERS, encoded, digest, sha,
                                         mirror, verify_mirror)

KINDS = ('s5', 'r1', 'selection')
STARTS = ('run_v24_counted_selection.py', 'judge_v24_counted_selection.py',
          'run_v24_counted_cohort.py', 'read_v24_counted_cohort.py',
          'freeze_v24_counted_cohort.py')


def instrument_closure():
    pending = [PROJECT / 'tools' / n for n in STARTS] + [PROJECT / 'web/serve.py']
    seen = set()
    while pending:
        path = pending.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = [n.name for n in node.names] if isinstance(node, ast.Import) else (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                candidate = PROJECT / 'tools' / Path(*name.split('.')).with_suffix('.py')
                if candidate.is_file():
                    pending.append(candidate)
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in sorted(seen)}


def config():
    return {**preparation.config(), 'instrumentSources': instrument_closure()}


def population(plan, kind):
    if kind not in KINDS:
        raise ValueError('undeclared population: ' + str(kind))
    return list(plan['s5']) if kind == 's5' else list(plan['r1']) if kind == 'r1' else [
        *plan['cases'], *plan['interactions']]
