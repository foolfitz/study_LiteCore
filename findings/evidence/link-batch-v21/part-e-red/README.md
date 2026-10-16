# v21 part E: red-first and gate record

These are copied from part E's scratch directory (2026-10-16). Part E's report is summarised in the commit that adds this folder.

- mutations-run2.txt: tests/markdown_paste_mutations.py. Control ok, six mutations red.
- abi-header-red-before-edit.txt: the header test failed (5 == 4) under the define before it was edited.
- v5-builder-red.txt, x1-cl-red.txt: the builder and X1 changed-leaf mutations, all red.
- m1-1-base*: M1-1 at base 523871fa (carrier E2_V21) and at base 5d77dc84 (E2_V15, E2_V19, E2_V20, E2_V21), both exit 0.
- make-n-v21.txt: make -n of the v21 manifest target, which compiles nothing.
- step8-part*.txt: the RUNBOOK-relink-v20 §0 item 9 gates.

The main session re-ran these on 2026-10-16:

- the M0 model test: 65 items, 478 checks ok;
- the mutation runner: every mutation red;
- the 94 python unit tests: OK;
- the ABI header test, with and without the define: exit 0;
- E1-C: intact.

It did not re-run M1-1.
