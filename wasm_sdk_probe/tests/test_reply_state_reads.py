"""SPEC-M3-ordered-commands 15.2 (fable ruling 2 2.2, form 2): the engine's table of STATE_CHANGED items a
reply may read (src/reply_state_reads.hpp) against the on-time list generated from the native N1 records.

The list is ../findings/evidence/link-batch-v23/native/ordered-commands/out-n1b/on-time-list.json, written by
`read_n1.py --on-time-list out-n1b` (N = 5, every clean uni1ai round).  A table entry is accepted only if the
list carries (an op dispatching that command, that key) under `onTime` in 5 or more rounds with 0 late,
and nowhere under `lateOrMixed`.

Red cases, built from the real list: Bold made late; an entry for a key the list never saw; an empty list.
Run from wasm_sdk_probe/: python3 -m unittest tests/test_reply_state_reads.py
"""
import json
import pathlib
import re
import unittest

HERE = pathlib.Path(__file__).resolve().parent.parent
HEADER = HERE / 'src' / 'reply_state_reads.hpp'
LIST = HERE.parent / 'findings/evidence/link-batch-v23/native/ordered-commands/out-n1b/on-time-list.json'
COUNTED_ROUNDS = 5


def table(text):
    body = text.split('kReads[] = {', 1)[1].split('};', 1)[0]
    return re.findall(r'\{"([^"]+)",\s*"([^"]+)"\}', body)


def op_command(op):
    # the harness's notation: U<command>|<arguments>, or U<command>
    return op[1:].split('|', 1)[0] if op.startswith('U') else None


def problems(entries, on_time_list):
    found = []
    if not on_time_list.get('onTime'):
        return ['the on-time list is empty']
    for command, key in entries:
        ok = [e for e in on_time_list['onTime']
              if op_command(e['op']) == command and e['key'] == key
              and e['rounds'] >= COUNTED_ROUNDS and e['late'] == 0]
        bad = [e for e in on_time_list.get('lateOrMixed', [])
               if op_command(e['op']) == command and e['key'] == key]
        if not ok:
            found.append(f'{command} reads {key}: not on time in {COUNTED_ROUNDS} rounds')
        if bad:
            found.append(f'{command} reads {key}: late or mixed in {bad}')
    return found


class ReplyStateReads(unittest.TestCase):
    def setUp(self):
        self.entries = table(HEADER.read_text())
        self.assertEqual(len(self.entries), 4, 'the table parse found a different number of entries')
        self.assertTrue(LIST.exists(), f'{LIST} is missing: generate it from out-n1b first')
        self.list = json.loads(LIST.read_text())

    def test_every_read_is_on_time(self):
        self.assertEqual(problems(self.entries, self.list), [])

    def test_red_bold_made_late(self):
        mutated = json.loads(json.dumps(self.list))
        for e in mutated['onTime']:
            if op_command(e['op']) == '.uno:Bold' and e['key'] == '.uno:Bold':
                e['late'] = 1
                mutated['lateOrMixed'].append(e)
        mutated['onTime'] = [e for e in mutated['onTime'] if e['late'] == 0]
        self.assertTrue(any('.uno:Bold' in p for p in problems(self.entries, mutated)))

    def test_red_unlisted_key(self):
        self.assertTrue(problems(self.entries + [('.uno:Bold', '.uno:TableCellBackgroundColor')], self.list))

    def test_red_empty_list(self):
        self.assertEqual(problems(self.entries, {'onTime': [], 'lateOrMixed': []}),
                         ['the on-time list is empty'])


if __name__ == '__main__':
    unittest.main()
