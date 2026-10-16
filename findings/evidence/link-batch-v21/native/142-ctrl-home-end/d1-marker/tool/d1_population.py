#!/usr/bin/env python3
"""The D1 population, generated from the 142 native arm table by the script grammar.

Usage: python3 -I d1_population.py ARMS_JSON [--json OUT_JSON]

ARMS_JSON is ../../out/arms.json (written by ../../tool/run_arms.py). The rule is
specs/SPEC-M3-link-batch-v21.md section 9.5, applied to every step of every arm:

  An arm is IN iff every step is one the product can send --
    k<code>[x<n>]   with code in {1024 Down, 1025 Up, 1027 Right, 1028 Home, 1029 End}
    r<name>         records a caret point that feeds s/c (the engine's select-range / place-caret)
    s<a>:<b>        range via select-range (the engine's text-handles path)
    c<name>         click via place-caret
    M<label>=<code> measured press with code in {9220 Ctrl+Home, 9221 Ctrl+End}
  -- and it has at least one Ctrl+Home/Ctrl+End press (section 9.5 names place-*
  as not in; an arm without a press has nothing for D1 to land).

  Instrument steps, allowed anywhere after the last press and nowhere before it:
    L  the locator (Shift+End / Shift+Home read-back)  -- moved after the save in D1
    S  saveAs fodt                                      -- replaced by D1's own save

  OUT rules (every rule an arm breaks is listed):
    bksp      a Backspace press (label bksp, or code 1283)
    del       a Delete press (label del, or code 1286)
    K / J     K1 barrier steps (Shift+Left / Shift+Right with timed reads)
    B         back-to-back pair
    Q         pair queued inside a callback
    u.        UNO command (postUnoCommand) -- the product does not send these
    k-code    a k step whose code is not in the set above
    M-code    a measured press whose code is not 9220/9221 (e.g. plain Home 1028, Down 1024)
    no-ctrl   no M…=9220|9221 press (a Ctrl code inside a B or Q pair does not count)

Exit 1 (refuse) when: a step's kind is not in the grammar above (unknown step);
the IN population is empty; an IN arm has a product step after its last
Ctrl press, or an instrument step before it (D1's "after the last press" would
be ambiguous); the arm table is empty or names an arm twice.
"""
import argparse
import json
import re
import sys

SENDABLE_K = {1024, 1025, 1027, 1028, 1029}
CTRL = {9220, 9221}
BKSP, DEL = 1283, 1286

RE_K = re.compile(r'^k(\d+)(?:x(\d+))?$')
RE_M = re.compile(r'^M([^=]+)=(\d+)$')
RE_R = re.compile(r'^r(\w+)$')
RE_C = re.compile(r'^c(\w+)$')
RE_S = re.compile(r'^s(\w+):(\w+)$')


def classify_step(step):
    """Return (kind, out_rules) for one step. kind is one of 'product', 'ctrl',
    'instrument', 'out'. Raises ValueError on a step outside the grammar."""
    if step in ('L', 'S'):
        return 'instrument', []
    head = step[0]
    if head == 'k':
        m = RE_K.match(step)
        if not m:
            raise ValueError(f'malformed k step {step!r}')
        code = int(m.group(1))
        return ('product', []) if code in SENDABLE_K else ('out', [f'k-code ({step})'])
    if head == 'M':
        m = RE_M.match(step)
        if not m:
            raise ValueError(f'malformed M step {step!r}')
        label, code = m.group(1), int(m.group(2))
        rules = []
        if label == 'bksp' or code == BKSP:
            rules.append(f'bksp ({step})')
        if label == 'del' or code == DEL:
            rules.append(f'del ({step})')
        if code in CTRL and not rules:
            return 'ctrl', []
        if code not in CTRL:
            rules.append(f'M-code ({step})')
        return 'out', rules
    if head == 'r':
        if not RE_R.match(step):
            raise ValueError(f'malformed r step {step!r}')
        return 'product', []
    if head == 'c':
        if not RE_C.match(step):
            raise ValueError(f'malformed c step {step!r}')
        return 'product', []
    if head == 's':
        if not RE_S.match(step):
            raise ValueError(f'malformed s step {step!r}')
        return 'product', []
    if head in 'BQ':
        rules = [f'{head} ({step})']
        for code in re.findall(r'\d+', step.split('=', 1)[1] if '=' in step else ''):
            if int(code) == BKSP:
                rules.append(f'bksp ({step})')
            if int(code) == DEL:
                rules.append(f'del ({step})')
        return 'out', rules
    if head in 'KJ':
        return 'out', [f'{head} ({step})']
    if head == 'u':
        if not step.startswith('u.'):
            raise ValueError(f'malformed u step {step!r}')
        return 'out', [f'u. ({step})']
    raise ValueError(f'unknown step kind {step!r}')


def classify(arms):
    """Return (in_arms, out_arms, errors). in_arms: list of dicts with name,
    fixture, script, last_ctrl (index), d1_script, control_script. out_arms:
    list of (name, rules)."""
    ins, outs, errors = [], [], []
    seen = set()
    for arm in arms:
        name = arm['name']
        if name in seen:
            errors.append(f'{name}: listed twice')
        seen.add(name)
        steps = [s for s in arm['script'].split(',') if s]
        kinds, rules = [], []
        for st in steps:
            try:
                kind, r = classify_step(st)
            except ValueError as e:
                errors.append(f'{name}: {e}')
                kind, r = 'unknown', []
            kinds.append(kind)
            rules.extend(r)
        if 'unknown' in kinds:
            continue
        ctrl_idx = [i for i, k in enumerate(kinds) if k == 'ctrl']
        if not ctrl_idx:
            rules.append('no-ctrl (no M…=9220|9221 press; Ctrl codes inside B/Q pairs do not count)')
        if rules:
            # de-duplicate, keep order
            seen_r, uniq = set(), []
            for r in rules:
                if r not in seen_r:
                    uniq.append(r)
                    seen_r.add(r)
            outs.append((name, uniq))
            continue
        last = ctrl_idx[-1]
        after = [steps[i] for i in range(last + 1, len(steps)) if kinds[i] != 'instrument']
        before_instr = [steps[i] for i in range(last) if kinds[i] == 'instrument']
        if after:
            errors.append(f'{name}: product step(s) after the last Ctrl press: {after}')
            continue
        if before_instr:
            errors.append(f'{name}: instrument step(s) before the last Ctrl press: {before_instr}')
            continue
        prefix = steps[:last + 1]
        control_prefix = [s for s, k in zip(prefix, kinds) if k != 'ctrl']
        ins.append({
            'name': name,
            'fixture': arm['fixture'],
            'script142': arm['script'],
            'nCtrlPresses': len(ctrl_idx),
            'd1Script': ','.join(prefix + ['T', 'S', 'L']),
            'noCtrlScript': ','.join(control_prefix + ['T', 'S', 'L']),
        })
    return ins, outs, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arms_json')
    ap.add_argument('--json', default='')
    a = ap.parse_args()
    arms = json.loads(open(a.arms_json, encoding='utf-8').read())
    if not arms:
        print('RED: the arm table is empty')
        return 1
    ins, outs, errors = classify(arms)
    print(f'D1 population from {a.arms_json}: {len(arms)} arms, {len(ins)} IN, {len(outs)} OUT')
    print()
    print('IN (every step product-sendable, at least one Ctrl+Home/End press):')
    for x in ins:
        print(f'- {x["name"]} [{x["fixture"]}]: {x["script142"]}  ->  D1 script {x["d1Script"]}')
    print()
    print('OUT (with every rule that excludes the arm):')
    for name, rules in outs:
        print(f'- {name}: {"; ".join(rules)}')
    print()
    if not ins:
        errors.append('zero arms IN')
    if errors:
        print('RED:')
        for e in errors:
            print(f'- {e}')
        return 1
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump({'source': a.arms_json, 'in': ins, 'out': [{'name': n, 'rules': r} for n, r in outs]}, f,
                      indent=1)
            f.write('\n')
    print(f'GREEN: {len(ins)} IN, {len(outs)} OUT, {len(arms)} total; no unknown step')
    return 0


if __name__ == '__main__':
    sys.exit(main())
