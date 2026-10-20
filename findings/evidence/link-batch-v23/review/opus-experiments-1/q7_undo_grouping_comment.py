#!/usr/bin/env python3
"""Opus seat, review 1, Q6/Q7: a re-implementation (NOT LibreOffice) of the two pieces of Writer that decide
the top `.uno:Undo` comment after consecutive Backspaces, to show when the whole payload stops changing.

Read in lo/ (HEAD 671c848b1bb8):
  - DeleteAndJoin merges a single-character delete into the last SwUndoDelete when CanGrouping says so
    (sw/source/core/doc/DocumentContentOperationsManager.cxx:4648-4666); Backspace prepends the deleted
    character to m_aSttStr (sw/source/core/undo/undel.cxx:621-632); grouping needs the same letter/numeric
    class (undel.cxx:567-573) and the same paragraph (:542-545).
  - The comment is "Delete $1" (sw/inc/strings.hrc:435) with $1 = ShortenString(m_aSttStr, 20, "...")
    (undel.cxx:842; nUndoStringLength = 20, sw/source/core/inc/UndoCore.hxx:247; STR_LDOTS "...",
    strings.hrc:542), recomputed on every read (m_bCacheComment = false, undel.cxx:200; undobj.cxx:718-745).
  - Each payload entry is index, comment, viewId and the action's construction dateTime
    (svl/source/undo/undo.cxx:1310-1318, :76-78); grouping creates no new action, so index, viewId and
    dateTime of the top entry do not change.
So the payload is byte-identical before and after a grouped Backspace whenever the shortened deleted string
is.  ShortenString itself is copied from sw/source/core/undo/undobj.cxx:1626-1643.
"""


def shorten(s, n=20, fill='...'):
    if len(s) <= n:
        return s
    n -= len(fill)
    if n < 2:
        n = 2
    front = n - n // 2
    back = n - front
    return s[:front] + fill + s[len(s) - back:]


def run(line, presses):
    """Returns (press, number of actions, top comment, payload identical to the previous press)."""
    actions = 0
    deleted = ''
    prev = None
    rows = []
    caret = len(line)
    for k in range(1, presses + 1):
        c = line[caret - 1]
        caret -= 1
        # CanGrouping (undel.cxx:567-573): same isLetterNumeric class as the group's first character
        if deleted and c.isalnum() == deleted[0].isalnum():
            deleted = c + deleted           # merged: no new action
        else:
            deleted = c                     # a new SwUndoDelete
            actions += 1
        payload = (actions, f'Delete "{shorten(deleted)}"')
        rows.append((k, actions, payload[1], payload == prev))
        prev = payload
    return rows


for label, line, presses in (('a fill-in line of 30 underscores', 'Name: ' + '_' * 30, 26),
                             ('a run of 30 zeros', 'Amount 1' + '0' * 30, 26),
                             ('ordinary words', 'The quick brown fox jumps over the lazy dog', 26)):
    print(f'== {label}: {line!r}, caret at the end, Backspace pressed repeatedly ==')
    for k, n, comment, same in run(line, presses):
        print(f'  press {k:2}: actions {n:2}, top comment {comment!r:40} {"IDENTICAL payload to the previous press" if same else ""}')
