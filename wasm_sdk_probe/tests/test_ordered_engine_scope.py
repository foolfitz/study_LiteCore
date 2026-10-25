"""Actual v23 preprocessing and causal source mutations; never links a project.

This checks the named engine dependency graph, not external LOK internals.
Executable poll and format tests supply behavioral coverage separately.
"""
from pathlib import Path
import re
import subprocess
import sys
import unittest

SDK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SDK / 'tools'))
from check_merge_key_undo_scope import compile_command, preprocess_args
from ordered_format_scope import function_bodies, strip_noncode


def violations(source):
    code = strip_noncode(source)
    bodies = function_bodies(source)
    errors = []
    required = ('onLokCallback', 'handleEditorAction', 'handleOrderedDiagnostic',
                'dispatchOrderedKey', 'mainLoopAnyInputCallback', 'mainLoopPollCallbackImpl',
                'dispatchOne', 'sendPendingReply')
    for name in required:
        if name not in bodies:
            errors.append('missing root: ' + name)
    for name in ('engineLoop', 'mainLoopDrainCommands', 'startSelectionBarrierDelete',
                 'handleSelectionBarrierStep', 'queueSelectionBarrierStep',
                 'handleFormatBarrierStep', 'startFormatBarrierAction',
                 'armFormatBarrierDeadline', 'handleMergeKeyUndoStep'):
        if name in bodies:
            errors.append('legacy function compiled: ' + name)
    def walk(root):
        seen, todo = set(), [root]
        while todo:
            name = todo.pop()
            if name in seen or name not in bodies:
                continue
            seen.add(name)
            for body in bodies[name]:
                yield name, body
                todo.extend(call for call in re.findall(r'\b(\w+)\s*\(', body) if call in bodies)
    for name, body in walk('onLokCallback'):
        if re.search(r'\bpClass\b|\b(?:setOrderedReply|finishAsynchronous|composeOrdered\w*|completePending\w*|emitSdkError)\s*\(', body):
            errors.append('callback performs command/reply work: ' + name)
    for name in ('mainLoopPollCallbackImpl', 'dispatchOne'):
        body = '\n'.join(bodies.get(name, []))
        if re.search(r'\b(?:while|for|wait|wait_until|wait_for)\s*\(', body):
            errors.append('poll drains or waits: ' + name)
    poll = '\n'.join(bodies.get('mainLoopPollCallbackImpl', []))
    if 'runOnePoll' not in poll:
        errors.append('poll bypasses tested scheduler')
    any_input = '\n'.join(bodies.get('mainLoopAnyInputCallback', []))
    if not all(x in any_input for x in ('poll::anyInput', 'gOrderedReply', 'commands.size')):
        errors.append('anyInput omits queued reply')
    public = '\n'.join(bodies.get('handleEditorAction', []))
    gate = public.find('if (!permitted)')
    dispatch = public.find('dispatchOrderedKey(')
    if gate < 0 or dispatch < gate or not all(x in public[:dispatch] for x in
            ('editorGesturePermitted(action, kGestureCollapsed)',
             'editorGesturePermitted(action, kGestureRangeSingle)',
             'editorGesturePermitted(action, kGestureRangeCross)')):
        errors.append('public key bypasses gesture gate')
    private = '\n'.join(bodies.get('handleOrderedDiagnostic', []))
    if not re.search(r'kind == 4 && readSelection\(\).type != LOK_SELTYPE_TEXT', private):
        errors.append('private range Left omits TEXT precondition')
    if 'dispatchOrderedKey(key, pending)' not in private or 'requireDocument' not in private:
        errors.append('private key omits shared dispatch/document gate')
    return errors


class OrderedEngineScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        args = preprocess_args(compile_command('build/e2/editor-v23-diag/probe_engine.o'), [])
        result = subprocess.run(args, cwd=SDK, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
        # Exclude standard-library helper bodies; retain every engine function.
        cls.source = result.stdout[result.stdout.index('enum class CommandType'):]

    def test_actual_and_causal_mutations(self):
        self.assertEqual(violations(self.source), [])
        changes = {
            'callback-lok': ('void onLokCallback(int type, const char *payload, void *) {',
                             'void onLokCallback(int type, const char *payload, void *) { readSelection();'),
            'callback-reply': ('void onLokCallback(int type, const char *payload, void *) {',
                               'void onLokCallback(int type, const char *payload, void *) { finishAsynchronous(1);'),
            'reply-starvation': ('static_cast<bool>(gOrderedReply)', 'false'),
            'public-gesture-bypass': ('if (!permitted)', 'if (false)'),
            'private-range-bypass': ('kind == 4 && readSelection().type != LOK_SELTYPE_TEXT', 'false'),
            'poll-drain': ('return probe::poll::runOnePoll(engine, inOrderedPoll);',
                           'while (true) {} return probe::poll::runOnePoll(engine, inOrderedPoll);'),
        }
        for label, (before, after) in changes.items():
            with self.subTest(label=label):
                self.assertTrue(before in self.source, label)
                self.assertTrue(violations(self.source.replace(before, after)), label)
        self.assertTrue(violations(self.source + '\nvoid engineLoop() {}'))
        self.assertTrue(violations(''))


if __name__ == '__main__':
    unittest.main()
