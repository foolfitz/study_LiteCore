#!/usr/bin/env python3
"""Opus seat, review 1, Q9 experiment E6: the committed model test, unchanged except that C's reply to a
caret Backspace that DID delete is labelled `verified-boundary-noop` (changed:false) whenever the caret
ends at position 0.  This is the shape of the undo-grouping hole (a real deletion reported as nothing).
The whole committed main() runs, with every committed check; the question is whether any check turns red."""
import pathlib
here = pathlib.Path(__file__).resolve().parent
src = (here / 'base.cpp').read_text()
old = '''      completionName = keyChanged ? "verified-key-undo" : "verified-boundary-noop";
      outcome = keyChanged ? Outcome::Deleted : Outcome::Noop;'''
assert src.count(old) == 1
new = '''      completionName = (keyChanged && core.pt != 0) ? "verified-key-undo" : "verified-boundary-noop";
      outcome = (keyChanged && core.pt != 0) ? Outcome::Deleted : Outcome::Noop;'''
(here / 'E6_lying_noop.cpp').write_text(src.replace(old, new))
print('E6_lying_noop.cpp')
