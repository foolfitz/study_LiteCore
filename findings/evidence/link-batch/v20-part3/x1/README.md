# X1 extended for a new identity: v20 = v19 plus three declared deltas (ruling 6 condition 49)

This is a new use of `wasm_sdk_probe/tools/check_profile_identity.py`, not a repair (ruling 6 Q5; condition 55 puts it on its own handoff line, "extended for a new identity", in neither §34.4 count). v19's claim was "the reference with only the link's outputs changed". v20's claim is "v19 plus exactly three declared deltas". Run unchanged on v20, X1 is red by design and a person would have to read the FAIL as a pass (the §34.7 shape); the flags remove that hand read.

## The flags

Three repeatable flags; with none of them the behaviour and the printed output are unchanged.

| flag | what must hold (all three also keep every other clause, and every manifest leaf is still compared) |
|---|---|
| `--declared-worker SHA` | `sdk-worker.js` hashes to SHA, SHA differs from the reference's `sdk-worker.js`, and the manifest's `.editorContract.workerSha256` equals it. This is the one leaf the flag licenses to move. |
| `--declared-new-leaf PATH=VALUE` | the leaf PATH is absent from the reference manifest and present in the candidate with exactly VALUE (JSON type included; VALUE is parsed as JSON if it is JSON, else it is a string). Clause `declared-leaf`. PATH uses the tool's own leaf syntax, a leading dot and dots between keys (`.editorContract.pageRectangles`; the same form as `.profile` in v19's printed `moved:` list). |
| `--declared-export SYMBOL` | the candidate's export list is the reference's bytes followed by `SYMBOL\n` for each declared symbol in flag order, and no declared symbol is already in the reference's list. |

An undeclared move still fails (`manifest`), and a declared delta that did not move fails its clause. The source is `tools/check_profile_identity.py` (module docstring, `check`, `parse_leaf`).

## No flags: byte-identical behaviour on v19's inputs

`default-identity.cmd.txt` is the exact invocation `handoff/RUNBOOK-relink-v19.md` §3 prescribes, run on the tool after the change: exit 0 (`default-identity.exit.txt`), stderr empty, and its stdout against the committed `findings/evidence/v19/post-link/x1-check-profile-identity.txt` is `diff exit 0`, empty (`default-identity-vs-v19-post-link.diff`). `default-identity-head.txt` has the tool's sha256 and the sha256 of every input (the v19 profile's four files equal the post-link README's `1aafd4f9…`, `46b2f40a…`, `00882139…`, `902111fa…`; the two export lists are both `d6c22670…`). The inputs are build and dist files that are not in git; their hashes are the identity.

## Tests

`tests/test_profile_identity.py`: the existing 12 tests are unchanged and pass. New class `DeclaredDeltas` runs on a SYNTHETIC `e2-editor-v20` built from v18's real profile (a stand-in worker, wasm and loader; the manifest leaf; the export list plus the symbol). It has one green, the seven red cases of condition 49 (d), six more that follow from "moved exactly as declared" (a declared leaf the candidate lacks, a declared export already in the reference, exports in another order, a new worker not declared, a manifest worker hash that is not the worker, a declared leaf of another JSON type), the unflagged run on the same candidate (red by design: `['manifest', 'worker', 'exports']`), and the command line end to end. 30 tests, OK (`unittest.stderr.txt`: this module and `test_merge_key_undo_scope`, 46 tests, exit 0). `mutation_check.py` mutates ten expressions of the declared-delta logic one at a time in memory and runs `DeclaredDeltas` against each: `mutation_check.stdout.txt`, exit 0, ten killed, `survivors: 0` (`mutation_check.exit.txt`, stderr empty). A first, uncommitted pass had one survivor (two worker checks covered each other), so the redundant check was removed from the tool before the committed run. One mutant (leaf present in the candidate) is killed by a crash (`KeyError`), not by a verdict.

## The v20 invocation (cannot run yet: v20 is not linked)

```
python3 tools/check_profile_identity.py \
    --candidate dist/profiles/e2-editor-v20 --reference dist/profiles/e2-editor-v19 \
    --candidate-exports build/e2/editor-v20/exports.txt \
    --reference-exports build/archive/e2-editor-v19-1aafd4f9-worker-00882139/exports.txt \
    --declared-worker 478d0da1dbfcf93615a00025c3c2f9b72c3cfa486d04746f03dea5fcf757b099 \
    --declared-new-leaf .editorContract.pageRectangles=document-sdk-page-rectangles \
    --declared-export _oxsdk_document_page_rectangles
```

`v20-invocation-before-link.*` is that command today: exit 3, `VERDICT NOT DONE: missing […e2-editor-v20 files, build/e2/editor-v20/exports.txt]`, stderr empty. It shows the flags parse and that nothing is judged before the link. The deltas come from the Makefile v20 block (worker pin `E2_V20_WORKER_SHA256`, `--page-rectangles`, the `printf` that appends `_oxsdk_document_page_rectangles`) and from `tools/build_e2_editor_v4_profile.py:89` (`PAGE_RECTANGLES_DECLARATION = "document-sdk-page-rectangles"`) and `:559-560`.

Choices and caveats:
- The reference is v19, the declared identity base; the reference export list is the v19 archive's copy (byte-identical to `build/e2/editor-v19/exports.txt`, both `d6c22670…`). The export clause holds only if the `build/r5/writer-review/exports.txt` that the v20 recipe copies is the one v19 was linked with; if it is not, the clause is red and that is the finding.
- Not claimed: that the real v20 manifest will move nothing else. Under the flags, any other moved leaf (the wasm and loader hashes and the two naming leaves are already licensed) makes `manifest` red. Whether v20's loader equals v19's is printed and recorded, as in v19.
- If this extension is not used before the link, condition 49's default applies: X1 runs unflagged, the FAIL is read by hand against the same three deltas, recorded as a hand read, and the extension is dropped.
