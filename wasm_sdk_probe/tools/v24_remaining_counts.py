"""SPEC v24 section 19: fresh R1/selection after complete S5 and a zero-cell CPU refusal.

Keep the original config and every original instrument unchanged. Only the cohort verifier is
adapted in-process; its own code object runs with two globals changed (KINDS and stage_spec).
Additional orchestration sources have their own closed archive and live bindings.
"""
import ast
import gzip
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile
from types import FunctionType

import run_v24_counted_cohort as base
import read_v24_counted_cohort as original_reader
from v24_counted_selection_cases import ROOT, PROJECT, config, encoded, digest, sha, population, BROWSERS

KINDS = ('r1', 'selection')
SOURCE = ROOT / 'findings/evidence/link-batch-v24/counted-selection-01/cohort.json'
BASE_VERIFY = base.verify
BASE_STAGE_SPEC = base.stage_spec
STARTS = ('run_v24_remaining_cohort.py', 'run_v24_remaining_selection.py',
          'judge_v24_remaining_selection.py', 'read_v24_remaining_cohort.py',
          'freeze_v24_remaining_cohort.py')
OVERRIDES = {'verifier': 'run_v24_counted_cohort.verify', 'KINDS': list(KINDS),
             'collector': 'tools/run_v24_remaining_selection.py',
             'judge': 'tools/judge_v24_remaining_selection.py'}


def stage_spec(cohort, kind, plan, pre_red):
    result = BASE_STAGE_SPEC(cohort, kind, plan, pre_red)
    result['runnerArgv'][2] = OVERRIDES['collector']
    result['judgeArgv'][2] = OVERRIDES['judge']
    return result


VERIFY_GLOBALS = {**vars(base), 'KINDS': KINDS, 'stage_spec': stage_spec}
REMAINING_VERIFY = FunctionType(BASE_VERIFY.__code__, VERIFY_GLOBALS, 'remaining_verify', BASE_VERIFY.__defaults__)


def sources():
    pending = [PROJECT / 'tools' / n for n in STARTS]
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
    # The original plan also binds its frozen entry points, including tools not executed by this adapter.
    seen.update(PROJECT / n for n in config()['instrumentSources'])
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in sorted(seen)}


def retained(frozen):
    source = ROOT / frozen['retainedS5']['cohort']
    BASE_VERIFY(source)
    receipt = frozen['retainedS5']
    for key, name in (('cohortSha256', 'cohort.json'), ('statusSha256', 'status.json'),
                      ('completionSha256', 'completion-read-01.json')):
        if sha(source.with_name(name)) != receipt[key]:
            raise ValueError('retained S5 receipt differs: ' + name)
    report = json.loads(source.with_name('completion-read-01.json').read_bytes())
    stages = report['stages']
    s5 = next(s for s in stages if s['population'] == 's5')
    r1 = next(s for s in stages if s['population'] == 'r1')
    if report['cohortSha256'] != receipt['cohortSha256'] or report['statusSha256'] != receipt['statusSha256']:
        raise ValueError('retained S5 completion binding differs')
    if report['state'] != 'STOPPED_FIRST_NONPASS' or s5['verdict'] != 'PASS' or not s5['populationComplete']:
        raise ValueError('retained S5 is not complete PASS')
    if s5['observed'] != 1176 or s5['required'] != 1176 or r1['observed'] != 0:
        raise ValueError('retained population is not S5 complete / R1 zero')
    return source, s5


def verify(cohort):
    cohort = Path(cohort).resolve()
    frozen = REMAINING_VERIFY(cohort)
    if frozen.get('namespaceOverrides') != OVERRIDES:
        raise ValueError('remaining namespace override differs')
    if frozen.get('orchestrationSources') != sources():
        raise ValueError('remaining orchestration source drift')
    with tarfile.open(cohort.with_name('orchestration-sources.tar.gz'), 'r:gz') as archive:
        expected = frozen['orchestrationSources']
        if len(archive.getmembers()) != len(expected) or set(archive.getnames()) != set(expected):
            raise ValueError('orchestration archive membership differs')
        for m in archive.getmembers():
            if not m.isfile() or digest(archive.extractfile(m).read()) != expected[m.name]:
                raise ValueError('orchestration archive blob differs: ' + m.name)
    retained(frozen)
    return frozen


def install():
    """The sole module override used by the existing launcher, collector and judge entry points."""
    base.verify = verify


def freeze(out):
    out = Path(out).resolve(); out.relative_to(ROOT)
    source_frozen = BASE_VERIFY(SOURCE)
    source_report = original_reader.read(SOURCE)
    if source_report != json.loads(SOURCE.with_name('completion-read-01.json').read_bytes()):
        raise ValueError('source raw reread differs from preserved completion')
    frozen = {**source_frozen, 'createdAt': base.now(),
              'authority': 'SPEC-M3-link-batch-v24 section 19; owner authorized agent execution while away',
              'scope': 'Fresh R1 and S1-S4 only; retain complete original S5; no retry or missing-cell credit',
              'namespaceOverrides': OVERRIDES, 'orchestrationSources': sources(),
              'retainedS5': {'cohort': str(SOURCE.relative_to(ROOT)), 'cohortSha256': sha(SOURCE),
                             'statusSha256': sha(SOURCE.with_name('status.json')),
                             'completionSha256': sha(SOURCE.with_name('completion-read-01.json'))}}
    retained(frozen)
    out.mkdir(parents=True, exist_ok=False)
    for name in ('frozen-config.json.gz', 'frozen-sources.tar.gz'):
        shutil.copyfile(SOURCE.with_name(name), out / name)
    with tarfile.open(out / 'orchestration-sources.tar.gz', 'x:gz') as archive:
        for name in frozen['orchestrationSources']:
            raw = (PROJECT / name).read_bytes(); info = tarfile.TarInfo(name); info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
    plan = config(); cohort = out / 'cohort.json'
    frozen['stages'] = [stage_spec(cohort, kind, plan, frozen['preRed']['path']) for kind in KINDS]
    frozen['prerequisites'] = {**source_frozen['prerequisites'], **{
        str(p.relative_to(ROOT)): sha(p) for p in (
            SOURCE, SOURCE.with_name('status.json'), SOURCE.with_name('completion-read-01.json'),
            SOURCE.parent / 's5/report.json', SOURCE.parent / 's5.judge.txt',
            out / 'frozen-config.json.gz', out / 'frozen-sources.tar.gz', out / 'orchestration-sources.tar.gz')}}
    cohort.write_bytes(encoded(frozen)); verify(cohort)
    return frozen


READ_GLOBALS = {**vars(original_reader), 'verify': verify}
READ_REMAINING = FunctionType(original_reader.read.__code__, READ_GLOBALS, 'read_remaining', original_reader.read.__defaults__)


def read(cohort):
    frozen = verify(cohort); source, _ = retained(frozen)
    old = original_reader.read(source)  # Real raw reread, not the preserved verdict alone.
    s5 = next(s for s in old['stages'] if s['population'] == 's5')
    remaining = READ_REMAINING(cohort)
    complete = s5['verdict'] == 'PASS' and s5['populationComplete'] and remaining['verdict'] == 'V24_SELECTION_COUNTS_HOLD'
    return {'scope': 'Original complete S5 plus fresh R1/S1-S4; raw artifacts re-read for every population',
            'retainedS5': {'cohort': str(source), 'stage': s5}, 'remaining': remaining,
            'verdict': 'V24_SELECTION_COUNTS_HOLD' if complete else 'NOT_ESTABLISHED'}
