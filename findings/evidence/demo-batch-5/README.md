# Demo batch 5 (SPEC-P-demo-batch-5)

Enter over a selection deletes it and breaks, as Writer's `SwWrtShell::SplitNode` does; an empty copy gets a sentence instead of `CLIPBOARD_EMPTY_SELECTION`. Page only, `web/e2-editor-app.js`; engine `e2-editor-v32` and its four pins unchanged. Shell generation 88.

| Read | Result |
|---|---|
| `p5/red-on-generation-87` | E1 red on all seven shapes (raw `EDITOR_FORMAT_GESTURE_UNSUPPORTED`), E7 red: a copy on a caret printed the raw code too |
| `p5/run-01` | The witness. Chrome's E4, E5, E7: E3 left the page unsaved and `beforeunload` held the next navigation. Firefox's E5 unexplained |
| `p5/run-02` | Only E5: the text and structure are back after two undos; what stayed is Writer's paragraph-rsid mark, an automatic style undo does not take back |
| `p5/reader_check.py` | The rsid-only reading, proved both ways before use; its first version dropped a newline |
| `p5/run-03-e5` | E5 holds: exactly two undos on both browsers and both shapes (`L-enter-range-two-undos`) |
| `freeze-88/` | Generation 88, E1-C intact |
| `chain-88.log` | P5 59/59, P4 126/126, S1 25/25, Z, P1 108/108, C, F4 24/24, F3 46/46 equal with nothing moved, V0' eleven stages; all on both browsers |
| `units/` | Shell 578/578, Calc 104/104, three mutation tools, `test-demo-batch-4-static` |

The main criterion was measured, not typed: on every shape Enter must save the same document as Delete then Enter.
