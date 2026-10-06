#!/usr/bin/env python3
"""SPEC-M3-paragraph-merge 13.2: nothing that can block on another thread runs
while gState.mutex is held.

Two invariants, both deadlocks if broken:
  * the engine thread must not call a LibreOfficeKit API (`pClass->...`) while
    holding gState.mutex: those take SolarMutex, and the LOK thread takes
    gState.mutex while holding SolarMutex (submit() from a callback);
  * no thread may emit to the SDK Worker (`emitJson`, `MAIN_THREAD_*`) while
    holding it: the Worker's own entry points take gState.mutex, and a Worker
    blocked in a futex wait does not run proxied calls.

Tool-closed in two ways.  Every line of the source that mentions gState.mutex
must be a lock the tool recognises (and checks) or one of the listed
non-acquiring uses; a new kind of use fails rather than going unchecked.  And
"calls something that emits" is computed, not listed: every function whose
body contains a forbidden token, or calls such a function, is tainted (to a
fixed point), and a call to a tainted function inside a lock scope fails like
the token itself.

Usage: check_engine_lock_scopes.py [SOURCE ...]   (default: src/probe_engine.cpp)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FORBIDDEN = re.compile(r"pClass->|\bemitJson\s*\(|\bMAIN_THREAD_")
# The engine's mutexes this rule covers (spec 13.2): gState.mutex, and
# gMergeMutex (option B's attribution, taken on the LOK thread under the
# SolarMutex -- the same ABBA shape).  Per mutex: the uses that do not
# acquire it, and whether it must exist.
MUTEXES = {
    "gState.mutex": ([re.compile(r"\bgState\.condition\.wait")], True),
    "gMergeMutex": ([re.compile(r"^\s*std::mutex\s+gMergeMutex\s*;")], False),
}


def lock_pattern(name: str) -> re.Pattern:
    return re.compile(r"\b(?:lock_guard|unique_lock|scoped_lock)\s*<[^>]*>\s*(\w+)\s*[({]\s*"
                      + re.escape(name) + r"\s*[)}]")
FUNCTION = re.compile(r"^(?!\s)(?:[\w:<>,\*&\s]+?)\b(\w+)\s*\([^;{}]*\)\s*(?:const\s*)?\{", re.M)
CALL = re.compile(r"\b(\w+)\s*\(")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    text = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), text)
    # String literals: keep their length, drop their content.
    return re.sub(r'"(?:\\.|[^"\\\n])*"', lambda m: '"' + " " * (len(m.group(0)) - 2) + '"', text)


def block_end(text: str, open_brace: int) -> int:
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return len(text)


def tainted_functions(text: str) -> set[str]:
    bodies: dict[str, str] = {}
    for match in FUNCTION.finditer(text):
        name = match.group(1)
        if name in {"if", "for", "while", "switch", "catch"}:
            continue
        start = match.end() - 1
        bodies[name] = bodies.get(name, "") + text[start:block_end(text, start) + 1]
    tainted = {name for name, body in bodies.items() if FORBIDDEN.search(body)}
    while True:
        grown = {name for name, body in bodies.items() if name not in tainted
                 and any(call in tainted for call in CALL.findall(body))}
        if not grown:
            return tainted
        tainted |= grown


def check(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    text = strip_comments(raw)
    tainted = tainted_functions(text)
    problems: list[str] = []
    counts = []
    for name, (non_acquiring, required) in MUTEXES.items():
        lock_re = lock_pattern(name)
        locks = 0
        mentioned = False
        for line_number, line in enumerate(text.splitlines(), 1):
            if not re.search(re.escape(name) + r"\b", line):
                continue
            mentioned = True
            lock = lock_re.search(line)
            if not lock:
                if not any(p.search(line) for p in non_acquiring):
                    problems.append(f"{path.name}:{line_number}: unrecognised use of {name}: "
                                    f"{raw.splitlines()[line_number - 1].strip()}")
                continue
            locks += 1
            # The scope: from the lock to the end of the block that holds it,
            # or to an explicit unlock of this lock.
            offset = sum(len(l) + 1 for l in text.splitlines()[:line_number - 1]) + lock.end()
            depth = 0
            end = len(text)
            for index in range(offset, len(text)):
                if text[index] == "{":
                    depth += 1
                elif text[index] == "}":
                    if depth == 0:
                        end = index
                        break
                    depth -= 1
            scope = text[offset:end]
            unlock = re.search(rf"\b{re.escape(lock.group(1))}\.unlock\s*\(", scope)
            if unlock:
                scope = scope[:unlock.start()]
            for bad in FORBIDDEN.finditer(scope):
                problems.append(f"{path.name}:{line_number}: `{bad.group(0)}` while {name} is held")
            for call in CALL.findall(scope):
                if call in tainted:
                    problems.append(f"{path.name}:{line_number}: calls {call}() (reaches a LOK call "
                                    f"or an emit) while {name} is held")
        if (required or mentioned) and locks == 0:
            problems.append(f"{path.name}: no {name} lock found -- the check would prove nothing")
        counts.append(f"{name} {locks}")
    print(f"{path.name}: lock scopes checked ({', '.join(counts)}), {len(tainted)} tainted functions")
    return problems


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv] or [Path(__file__).resolve().parent.parent / "src" / "probe_engine.cpp"]
    problems = [problem for path in paths for problem in check(path)]
    for problem in problems:
        print("FAIL " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
