# RESET restoration before the v23 caret-delete implementation

This specification is committed before any counted execution. It implements the already required native prerequisite in ordered-command specification 16.2, not a new broad regression gate. No run has yet established RESET restoration.

The executable population is `R_ARMS` in `../ordered-commands/tool/run_arms.py`: three fixtures (plain P2, numbered P2, first-line-indented P2), each with direct, restore and wrong-line variants. Run all nine arms in `unipoll` mode for exactly five rounds: 45 processes. Accessibility is not enabled. The shared native harness adds only `R<point>`, a synchronous `setTextSelection(LOK_SETTEXTSELECTION_RESET, x, y)` using a previously recorded caret rectangle's x and vertical midpoint. Existing modes and operations are retained.

Each fixture has short one-line paragraphs. Setup records P1 start as `wrong`, moves Down and Home to P2 start and records `before`. The measured Home trigger leaves that start unchanged. Within one poll, without a settle between measured operations:

- direct: the user's Backspace;
- restore: Shift+Left (K1), RESET at `before`, the user's Backspace;
- wrong-line: Shift+Left, RESET at the recorded P1 `wrong` point, Backspace.

The wrong-line point is measured from the document, not a guessed line-height subtraction. The reader requires distinct recorded points with P2 below P1. The K1 at-return read must be TEXT containing a paragraph separator. The RESET at-return read must be NONE with empty text. The restored document's independently parsed saved paragraph shape (content, list membership/style, indent, run weights) and final locator must equal direct Backspace. The at-return undo top comment must also equal direct Backspace and be nonempty. Undo timestamps are deliberately not compared across processes. Every direct round must yield the same reference landing. The wrong-line saved landing must differ from that reference in every round, or the control is not established.

`read_reset.py` derives its population from `R_ARMS` and checks the recorded arms, exact run-log population, one successful child exit per cell, native unipoll initialization/environment, complete output, uncapped settle, saved document and locator. Its synthetic red controls reject changed saved content, different undo top, noncollapsed RESET, absent separator, a nondiscriminating wrong-line control, unclean input, unreadable undo, and missing cells. Synthetic controls establish the reader's rejection behavior only; they do not establish a native outcome.

Only `RESET-HOLDS` at N=5 authorizes writing the synchronous engine RESET-restore branch. Clean observed mismatches give `RESET-FAILS`; missing, unclean, unstable or nondiscriminating evidence gives `NOT_ESTABLISHED`. Both retain the original requirement to use the specified Escape/next-poll alternative only after measuring its own prerequisites. Do not silently replace a failed RESET run with a timing delay or treat it as an approval of that alternative. The current shipping-core L-C-number-or-indent limitation stays open; A3 and a core change are separate feature decisions.
