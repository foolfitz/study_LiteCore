#!/usr/bin/env python3
"""Spec K-0.2.44 4.1: the red set of a `make -i test-e2-c-static` transcript, one name per line, sorted, unique: every
`✖ <test>` (node), every `FAIL: <test>` (unittest), and how many errors make ignored.  Read-only."""
import re
import sys

text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
names = {re.sub(r" \(\d+(\.\d+)?ms\)$", "", m) for m in re.findall(r"^✖ (.+)$", text, re.M)} - {"failing tests:"}
names |= {m for m in re.findall(r"^FAIL: (\S+)", text, re.M)}
names.add(f"make ignored errors: {len(re.findall(r'^make: .* Error [0-9]+ .ignored.$', text, re.M))}")
print("\n".join(sorted(names)))
