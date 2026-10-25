"""Bounded source check of the real ordered FORMAT reply dependency graph.

This supplements executable fake-LOK tests; it does not certify preprocessor
routing, native restoration, or WASM behavior. Unknown external calls are not
interpreted. Engine-local named helpers are followed from their actual bodies.
"""
import re


def strip_noncode(source):
    pattern = r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    return re.sub(pattern, lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0]),
                  source, flags=re.S)


def function_bodies(source):
    code = strip_noncode(source)
    found = {}
    pattern = r'^\s*[\w:<>,*& ]+\b(\w+)\s*\([^;{}]*\)\s*\{'
    for match in re.finditer(pattern, code, re.M):
        name = match[1]
        if name in ('if', 'switch', 'while', 'for', 'catch'):
            continue
        start = match.end()
        depth, end = 1, start
        while end < len(code) and depth:
            depth += (code[end] == '{') - (code[end] == '}')
            end += 1
        if depth:
            raise ValueError(f'unbalanced function: {name}')
        found.setdefault(name, []).append(code[start:end-1])
    return found


def violations(engine, include):
    code = strip_noncode(include)
    errors = []
    # Old staging/containment has no place anywhere in this implementation.
    for token in ('queueFormatBarrierStep', 'armFormatBarrierDeadline', 'stageDeadline',
                  'checkFormatBarrierContainment', 'finishFormatBarrierAfterRestore',
                  'handleFormatBarrierStep', 'maybeAdvanceFormatBarrierSelection'):
        if re.search(r'\b' + token + r'\b', code):
            errors.append('legacy FORMAT dependency: ' + token)
    bodies = function_bodies(engine + '\n' + include)
    roots = ('deferOrderedFormatReply', 'finishOrderedFormatReadback')
    for root in roots:
        if root not in bodies:
            errors.append('missing reply root: ' + root)
    seen, todo = set(), list(roots)
    while todo:
        name = todo.pop()
        if name in seen or name not in bodies:
            continue
        seen.add(name)
        for body in bodies[name]:
            if re.search(r'\bpClass\b', body):
                errors.append('LOK access reachable from reply: ' + name)
            if re.search(r'\b(?:queueFormatBarrierStep|armFormatBarrierDeadline)\s*\(', body):
                errors.append('stage transition reachable from reply: ' + name)
            todo.extend(call for call in re.findall(r'\b(\w+)\s*\(', body) if call in bodies)
    # Vacuous parsing is a failure: the serializers are part of the real graph.
    for required in ('completeFormatBarrier', 'failFormatBarrier'):
        if required not in seen:
            errors.append('serializer dependency not reached: ' + required)
    return errors
