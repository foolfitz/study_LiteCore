#!/usr/bin/env python3
"""Read the ordered-commands native arms (fable ruling 1 §2.6, v23).

Usage:
  python3 -I read_results.py OUT_DIR [--rounds N]     the verdict; exit 0 iff the reading is complete
  python3 -I read_results.py --self-test SMOKE_DIR    the red cases (a)-(d) of ruling §2.6, built
                                                      from a real one-round run, plus its control

A cell is (arm, mode, round). Its landing is the saved document's shape (per
paragraph: text, list membership and list style, first-line indent and left
margin, the font weight of every run) plus the locator's caret (prefix and
suffix of the caret's line). The modes (oc_native.cpp header): seq = Writer's own
order, measured; q = the threaded queued form, the positive control; unipoll =
candidate C.

Per decision arm (ruling §2.6):
  seq      all rounds land the same                  else NE (no reference)
  q        all rounds land the same, and not as seq  else NE (the control does not reorder)
  unipoll  all rounds land the same, and as seq      else FAIL (C's by-construction claim is false)
Every cell must also be clean: exactly one run-log.jsonl entry, with exit 0 (two-seat review 1, F2: a
reused directory or a re-run cell is unclean); a `done` record; the X step fired (a q-mode fact: the
other modes record `fired` as constant true, oc_native.cpp:371); no capped settle; and its env as its
mode needs (unipoll: SAL_LOK_OPTIONS=unipoll and the init record; seq/q: no SAL_LOK_OPTIONS). An unclean
cell makes its arm NE, the records-only D7 arms included (review 1, F1): C-HOLDS needs every cell of
every arm clean and every D8 observation present.

D8, the discriminator (ruling §2.6), on the ops whose effect is visible at
return: d5's Shift+Left (the selected text) and d7i/d7ii/d7iii's key (the
.uno:Undo payload). Under unipoll the effect is there when the call returns;
under q it is not (the key is still queued). Plus, under unipoll, every
measured step's last op reads at return what the settled window reads after
(nothing left pending). A D8 failure under unipoll is a FAIL; D8 reads clean cells only, and a D8
observation missing or unclean makes the verdict NOT-ESTABLISHED (review 1, F1/F3).

Exit: 0 iff a verdict was reached (C-HOLDS or C-FAILS) on N >= 5 rounds; 2 when --rounds < 5 (printed: not
a counted reading). C-FAILS needs one clean failing cell, so it can
come with other cells unclean; "complete" in the first version's usage line was wrong (review 1).

D7 decides nothing: it prints the .uno:Undo top at return per position (the
content SPEC-M3-link-batch.md §15.1 requires of the spec's fixed question 2).

VERDICT C-HOLDS: every decision arm PASS and D8 holds. VERDICT C-FAILS: any FAIL.
Otherwise VERDICT NOT-ESTABLISHED.
"""
import argparse
import gzip
import json
import pathlib
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

NS = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
}
T = '{%s}' % NS['text']
D8_OPS = {'d5': 'selText', 'd7i': 'undo', 'd7ii': 'undo', 'd7iii': 'undo'}
# Ruling 2 §2.6 (F1): an op whose dropping lands as Writer's order needs a presence witness in its step.
# d4's Bold at a collapsed caret changes no landing; its state item is in the step (opus a9). d1's Backspace
# is a Writer no-op by design and has none (registered).
WITNESS = {'d4': ('LOK_CALLBACK_STATE_CHANGED', '.uno:Bold=true')}
COUNTED_ROUNDS = 5  # spec §9.1, ruling 1 §2.6


def q(tag):
    pre, local = tag.split(':')
    return '{%s}%s' % (NS[pre], local)


def styles_of(root):
    """Automatic and common styles: name -> (paragraph props, text props)."""
    out = {}
    for st in root.iter(q('style:style')):
        name = st.get(q('style:name'))
        pp = st.find(q('style:paragraph-properties'))
        tp = st.find(q('style:text-properties'))
        out[name] = ({k: (pp.get(q(k)) if pp is not None else None) for k in ('fo:text-indent', 'fo:margin-left')},
                     tp.get(q('fo:font-weight')) if tp is not None else None)
    return out


def runs_of(el, styles, weight, out):
    """(text, weight) runs of a paragraph, in order."""
    def add(s, w):
        if not s:
            return
        if out and out[-1][1] == w:
            out[-1] = (out[-1][0] + s, w)
        else:
            out.append((s, w))
    add(el.text, weight)
    for ch in el:
        if ch.tag == T + 'span':
            w = styles.get(ch.get(T + 'style-name'), ({}, None))[1] or weight
            runs_of(ch, styles, w, out)
        elif ch.tag == T + 's':
            add(' ' * int(ch.get(T + 'c', '1')), weight)
        elif ch.tag == T + 'tab':
            add('\t', weight)
        elif ch.tag == T + 'line-break':
            add('\n', weight)
        elif ch.tag in (T + 'bookmark', T + 'bookmark-start', T + 'bookmark-end', T + 'soft-page-break'):
            pass
        else:
            runs_of(ch, styles, weight, out)
        add(ch.tail, weight)
    return out


def shape(fodt_gz):
    root = ET.fromstring(gzip.decompress(fodt_gz.read_bytes()))
    styles = styles_of(root)
    body = root.find('office:body/office:text', NS)
    paras = []

    def walk(el, list_kind, list_style):
        for ch in el:
            if ch.tag == T + 'list':
                walk(ch, list_kind, ch.get(T + 'style-name') or list_style)
            elif ch.tag in (T + 'list-item', T + 'list-header'):
                walk(ch, 'item' if ch.tag == T + 'list-item' else 'header', list_style)
            elif ch.tag in (T + 'p', T + 'h'):
                pp, pw = styles.get(ch.get(T + 'style-name'), ({}, None))
                runs = runs_of(ch, styles, pw or 'normal', [])
                paras.append({'text': ''.join(r[0] for r in runs), 'list': list_kind,
                              'listStyle': list_style if list_kind else None,
                              'indent': pp.get('fo:text-indent'), 'marginLeft': pp.get('fo:margin-left'),
                              'weights': [[r[0], 'normal' if r[1] in (None, '400') else r[1]] for r in runs]})
            elif ch.tag in (T + 'sequence-decls', T + 'tracked-changes'):
                pass
            else:
                walk(ch, list_kind, list_style)
    walk(body, None, None)
    return paras


def run_log(out):
    """(arm, mode, round) -> the run-log entries of that cell (review 1, F2)."""
    entries = {}
    path = out / 'run-log.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                entries.setdefault((x.get('arm'), x.get('mode'), x.get('round')), []).append(x)
    return entries


def read_cell(arm_dir, mode, r, log=None):
    jl = arm_dir / f'{mode}-r{r}.jsonl'
    cell = {'problems': []}
    if log is not None:
        mine = log.get((arm_dir.name, mode, r), [])
        if len(mine) != 1:
            cell['problems'].append(f'{len(mine)} run-log entries (exactly one is required)')
        elif mine[0].get('exit') != 0:
            cell['problems'].append(f"child exit {mine[0].get('exit')!r}")
    if not jl.exists():
        cell['problems'].append('no output')
        return cell
    recs = [json.loads(line) for line in jl.read_text().splitlines() if line.strip()]
    by = {}
    for x in recs:
        by.setdefault(x['rec'], []).append(x)
    env = (by.get('env') or [{}])[0]
    if 'fatal' in by:
        cell['problems'].append(f"fatal {by['fatal'][0].get('what')}")
    if 'done' not in by:
        cell['problems'].append('no done record')
    if mode == 'unipoll':
        if env.get('SAL_LOK_OPTIONS') != 'unipoll':
            cell['problems'].append(f"env SAL_LOK_OPTIONS {env.get('SAL_LOK_OPTIONS')!r}, not 'unipoll'")
        init = (by.get('init') or [{}])[0]
        if not init.get('sofficeMainSkipped') or not init.get('execute'):
            cell['problems'].append('no unipoll init record')
    elif env.get('SAL_LOK_OPTIONS') is not None:
        cell['problems'].append(f"env SAL_LOK_OPTIONS {env.get('SAL_LOK_OPTIONS')!r} in mode {mode}")
    if env.get('mode') != mode:
        cell['problems'].append(f"env mode {env.get('mode')!r} != {mode}")
    meas = (by.get('measured') or [None])[0]
    if meas is None:
        cell['problems'].append('no measured record')
    else:
        if not meas.get('fired'):
            cell['problems'].append('the X step did not fire')
        if meas.get('capped'):
            cell['problems'].append('settle capped')
        if arm_dir.name in WITNESS:
            kind, payload = WITNESS[arm_dir.name]
            if not any(c.get('type') == kind and c.get('payload') == payload for c in meas.get('callbacks') or []):
                cell['problems'].append(f'no {payload} in the step (the op left no presence witness)')
        cell['measured'] = meas
    if not (by.get('saved') or [{}])[0].get('ok'):
        cell['problems'].append('not saved')
    gz = arm_dir / f'{mode}-r{r}.fodt.gz'
    if gz.exists():
        try:
            cell['shape'] = shape(gz)
        except Exception as error:  # noqa: BLE001 -- a broken file is a problem of the cell
            cell['problems'].append(f'unreadable save: {error}')
    else:
        cell['problems'].append('no saved file')
    loc = (by.get('locate') or [None])[0]
    cell['caret'] = [loc.get('prefix'), loc.get('suffix')] if loc else None
    if loc is None:
        cell['problems'].append('no locate record')
    return cell


def landing(cell):
    return json.dumps({'shape': cell.get('shape'), 'caret': cell.get('caret')}, ensure_ascii=False, sort_keys=True)


def undo_top(payload):
    try:
        acts = json.loads(payload).get('actions')
    except Exception:  # noqa: BLE001
        return f'<unparsed {payload[:40]!r}>'
    if not acts:
        return None
    return acts[0].get('comment')


def judge(out, rounds):
    arms = json.loads((out / 'arms.json').read_text())
    lines, verdicts, d8 = [], {}, []
    cells = {}
    log = run_log(out)
    for a in arms:
        for mode in ('seq', 'q', 'unipoll'):
            for r in range(1, rounds + 1):
                cells[(a['name'], mode, r)] = read_cell(out / a['name'], mode, r, log)
    any_unclean = []
    d8_missing = []
    for a in arms:
        name = a['name']
        unclean = [f"{m} r{r}: {p}" for m in ('seq', 'q', 'unipoll') for r in range(1, rounds + 1)
                   for p in cells[(name, m, r)]['problems']]
        any_unclean += [f'{name} {u}' for u in unclean]
        land = {m: [landing(cells[(name, m, r)]) for r in range(1, rounds + 1)] for m in ('seq', 'q', 'unipoll')}
        same = {m: len(set(v)) == 1 for m, v in land.items()}
        if a['decides']:
            if unclean:
                v, why = 'NE', '; '.join(unclean[:4])
            elif not same['seq']:
                v, why = 'NE', 'seq rounds disagree (no reference)'
            elif not same['q'] or land['q'][0] == land['seq'][0]:
                v, why = 'NE', ('q rounds disagree' if not same['q'] else 'q lands as seq: the control does not reorder')
            elif not same['unipoll']:
                v, why = 'FAIL', 'unipoll rounds disagree'
            elif land['unipoll'][0] != land['seq'][0]:
                v, why = 'FAIL', 'unipoll lands differently from seq'
            else:
                v, why = 'PASS', f'{rounds}/{rounds} as seq; q reorders {rounds}/{rounds}'
            verdicts[name] = v
            lines.append(f"{name:8} {v:4} {why}")
            lines.append(f"         seq:     {land['seq'][0][:220]}")
            if land['q'][0] != land['seq'][0]:
                lines.append(f"         q:       {land['q'][0][:220]}")
            if land['unipoll'][0] != land['seq'][0]:
                lines.append(f"         unipoll: {land['unipoll'][0][:220]}")
        else:
            tops = []
            for m in ('seq', 'unipoll'):
                per_round = []
                for r in range(1, rounds + 1):
                    c = cells[(name, m, r)].get('measured') or {}
                    ops = c.get('ops') or [{}]
                    per_round.append(f"at return {undo_top(ops[0].get('atReturn', {}).get('undo', '{}'))!r}, "
                                     f"after {undo_top((c.get('after') or {}).get('undo', '{}'))!r}")
                agree = sum(1 for x in per_round if x == per_round[0])
                tops.append(f"{m}: {per_round[0]} ({agree}/{rounds} rounds read the same)")
            lines.append(f"{name:8} --   (records only) " + ' | '.join(tops) + (f"; unclean: {unclean[:2]}" if unclean else ''))
        # D8
        for mode in ('unipoll', 'q'):
            for r in range(1, rounds + 1):
                cell = cells[(name, mode, r)]
                m = cell.get('measured')
                if cell['problems'] or not m or not m.get('ops'):
                    if name in D8_OPS or mode == 'unipoll':
                        d8_missing.append(f'{name} {mode} r{r}')
                    continue
                if name in D8_OPS:
                    field = D8_OPS[name]
                    at = m['ops'][0]['atReturn'][field]
                    before = m['before'][field]
                    changed = (at != before) if field == 'undo' else (at != '')
                    want = mode == 'unipoll'
                    if changed != want:
                        d8.append(f"{name} {mode} r{r}: {field} at return {'changed' if changed else 'unchanged'}"
                                  f" (expected {'changed' if want else 'unchanged'})")
                if mode == 'unipoll':
                    last = m['ops'][-1]['atReturn']
                    if last['undo'] != m['after']['undo'] or last['selText'] != m['after']['selText']:
                        d8.append(f"{name} unipoll r{r}: the last op's state at return differs from the settled state")
    lines.append('D8      ' + ('holds' if not d8 else 'FAILS: ' + '; '.join(d8[:6]))
                 + (f'; NOT OBSERVED (unclean or missing): {d8_missing[:6]}' if d8_missing else ''))
    if any_unclean:
        lines.append(f'unclean cells: {len(any_unclean)}: ' + '; '.join(any_unclean[:6]))
    decided = list(verdicts.values())
    if any(v == 'FAIL' for v in decided) or any('unipoll' in x for x in d8):
        verdict = 'C-FAILS'
    elif decided and all(v == 'PASS' for v in decided) and not d8 and not d8_missing and not any_unclean:
        verdict = 'C-HOLDS'
    else:
        verdict = 'NOT-ESTABLISHED'
    lines.append(f'VERDICT {verdict}')
    return verdict, lines


def self_test(smoke):
    """Ruling §2.6's red cases (a)-(d) on a real one-round run, and the run itself as the control."""
    results = []

    def case(label, mutate, expect, rounds=1):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'out'
            shutil.copytree(smoke, out)
            keep_last_runlog_entry(out)
            mutate(out)
            verdict, lines = judge(out, rounds)
            text = '\n'.join(lines)
            ok = verdict == expect[0] and all(s in text for s in expect[1:])
            results.append(ok)
            print(f"{'ok  ' if ok else 'BAD '} {label}: VERDICT {verdict} (expected {expect[0]}"
                  + (f", with {list(expect[1:])}" if expect[1:] else '') + ')')

    def rewrite(path, fn):
        recs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        path.write_text(''.join(json.dumps(fn(r)) + '\n' for r in recs))

    def keep_last_runlog_entry(out):
        # The smoke's d7i was re-run after its placement was corrected (smoke/NOTES.md:23-26); its files are
        # the re-run, and its run-log keeps both runs.  The copy keeps the last entry per cell, so that the
        # control is the re-run as recorded.  A counted directory gets no such help.
        path = out / 'run-log.jsonl'
        last = {}
        for x in (json.loads(line) for line in path.read_text().splitlines() if line.strip()):
            last[(x['arm'], x['mode'], x['round'])] = x
        path.write_text(''.join(json.dumps(x) + '\n' for x in last.values()))

    def two_rounds(out):          # a synthetic second round: every cell of round 1 copied as round 2
        for arm in json.loads((out / 'arms.json').read_text()):
            d = out / arm['name']
            for mode in ('seq', 'q', 'unipoll'):
                for ext in ('jsonl', 'fodt.gz', 'stderr'):
                    if (d / f'{mode}-r1.{ext}').exists():
                        shutil.copy(d / f'{mode}-r1.{ext}', d / f'{mode}-r2.{ext}')
        path = out / 'run-log.jsonl'
        xs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        path.write_text(''.join(json.dumps(x) + '\n' for x in xs + [{**x, 'round': 2} for x in xs]))

    def b2_rounds_disagree(out):  # ruling 1 §2.6 (b), as written: unipoll's rounds disagree
        two_rounds(out)
        p = out / 'd3' / 'unipoll-r2.fodt.gz'
        p.write_bytes(gzip.compress(gzip.decompress(p.read_bytes()).replace(b'axbcd', b'xabcd')))

    def j_no_witness(out):        # ruling 2 §2.6: d4's Bold dropped (no state item in the step)
        def fn(r):
            if r['rec'] == 'measured':
                r['callbacks'] = [c for c in r['callbacks'] if c.get('payload') != '.uno:Bold=true']
            return r
        rewrite(out / 'd4' / 'unipoll-r1.jsonl', fn)

    def e_d7_missing(out):        # F1: a records-only D7 cell missing
        (out / 'd7iii' / 'unipoll-r1.jsonl').unlink()

    def f_d7_unfired(out):        # F1: D7's q trigger never fired (fired:false, no ops)
        def fn(r):
            if r['rec'] == 'measured':
                r['fired'], r['ops'] = False, []
            return r
        rewrite(out / 'd7ii' / 'q-r1.jsonl', fn)

    def g_runlog_dup(out):        # F2: a cell executed twice (a reused directory or a re-run)
        with open(out / 'run-log.jsonl', 'a') as f:
            f.write(json.dumps({'arm': 'd1', 'mode': 'seq', 'round': 1, 'exit': 0}) + '\n')

    def h_runlog_exit(out):       # F2: a child that wrote its records and then exited non-zero
        path = out / 'run-log.jsonl'
        xs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        for x in xs:
            if (x['arm'], x['mode']) == ('d4', 'unipoll'):
                x['exit'] = -11
        path.write_text(''.join(json.dumps(x) + '\n' for x in xs))

    def i_unclean_d8_fail(out):   # F3: an unclean unipoll cell whose D8 reading would fail
        def fn(r):
            if r['rec'] == 'measured':
                r['ops'][0]['atReturn']['selText'] = ''
            return r
        rewrite(out / 'd5' / 'unipoll-r1.jsonl', fn)
        rewrite(out / 'd5' / 'unipoll-r1.jsonl', lambda r: {**r, 'rec': 'done-not'} if r['rec'] == 'done' else r)

    def a_relabel(out):           # (a) a threaded q output labelled as unipoll
        for arm in json.loads((out / 'arms.json').read_text()):
            d = out / arm['name']
            shutil.copy(d / 'q-r1.fodt.gz', d / 'unipoll-r1.fodt.gz')
            init = next(json.loads(x) for x in (d / 'unipoll-r1.jsonl').read_text().splitlines() if '"init"' in x)
            body = [json.loads(x) for x in (d / 'q-r1.jsonl').read_text().splitlines() if x.strip()]
            for r in body:
                if r['rec'] == 'env':
                    r['mode'], r['SAL_LOK_OPTIONS'] = 'unipoll', 'unipoll'
                if r['rec'] == 'measured':
                    r['mode'] = 'unipoll'
            body.insert(1, init)
            (d / 'unipoll-r1.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in body))

    def b_break(out):             # (b) one cell's landing broken (142's break_one_for_red_demo pattern)
        p = out / 'd3' / 'unipoll-r1.fodt.gz'
        p.write_bytes(gzip.compress(gzip.decompress(p.read_bytes()).replace(b'axbcd', b'xabcd')))

    def c_env(out):               # (c) labelled unipoll, env without SAL_LOK_OPTIONS=unipoll
        rewrite(out / 'd2' / 'unipoll-r1.jsonl',
                lambda r: {**r, 'SAL_LOK_OPTIONS': None} if r['rec'] == 'env' else r)

    def d_at_return(out):         # (d) unipoll, the moving key's effect not there at return
        def fn(r):
            if r['rec'] == 'measured':
                r['ops'][0]['atReturn']['selText'] = ''
            return r
        rewrite(out / 'd5' / 'unipoll-r1.jsonl', fn)

    case('control: the smoke run as recorded', lambda out: None, ('C-HOLDS',))
    case('(a) q output relabelled as unipoll', a_relabel, ('C-FAILS', 'unipoll lands differently from seq'))
    case('(b) one unipoll landing broken', b_break, ('C-FAILS', 'd3       FAIL'))
    case('(c) unipoll env without SAL_LOK_OPTIONS', c_env, ('NOT-ESTABLISHED', "env SAL_LOK_OPTIONS None"))
    case('(d) unipoll Shift+Left with nothing selected at return', d_at_return, ('C-FAILS', 'd5 unipoll r1: selText'))
    case('two-round control: round 1 copied as round 2', two_rounds, ('C-HOLDS',), rounds=2)
    case("(b') ruling 1 §2.6 (b) as written: unipoll rounds disagree", b2_rounds_disagree,
         ('C-FAILS', 'unipoll rounds disagree'), rounds=2)
    case('(j) ruling 2: d4 Bold left no presence witness', j_no_witness, ('NOT-ESTABLISHED', 'no .uno:Bold=true'))
    case('(e) F1: a records-only D7 cell missing', e_d7_missing, ('NOT-ESTABLISHED', 'd7iii unipoll r1'))
    case('(f) F1: D7 q trigger never fired', f_d7_unfired, ('NOT-ESTABLISHED', 'the X step did not fire'))
    case('(g) F2: a cell with two run-log entries', g_runlog_dup, ('NOT-ESTABLISHED', '2 run-log entries'))
    case('(h) F2: a child exit -11 after its records', h_runlog_exit, ('NOT-ESTABLISHED', 'child exit -11'))
    case('(i) F3: an unclean unipoll cell that would fail D8', i_unclean_d8_fail, ('NOT-ESTABLISHED', 'NOT OBSERVED'))
    print(f"self-test: {sum(results)}/{len(results)} as required")
    return 0 if all(results) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?')
    ap.add_argument('--rounds', type=int, default=5)
    ap.add_argument('--self-test', metavar='SMOKE_DIR')
    a = ap.parse_args()
    if a.self_test:
        return self_test(pathlib.Path(a.self_test))
    verdict, lines = judge(pathlib.Path(a.out), a.rounds)
    print('\n'.join(lines))
    print(f'N = {a.rounds} rounds' + ('' if a.rounds >= COUNTED_ROUNDS else
                                       f' < {COUNTED_ROUNDS}: NOT a counted reading (spec §9.1; ruling 2 §2.6)'))
    if a.rounds < COUNTED_ROUNDS:
        return 2
    return 0 if verdict in ('C-HOLDS', 'C-FAILS') else 1


if __name__ == '__main__':
    sys.exit(main())
