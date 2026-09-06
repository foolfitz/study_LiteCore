# The `trap … EXIT` was exercised by two unplanned kills, and it held both times

**2026-09-06.** Ruling E-3 asks for a re-run of the revert rehearsal with
`NEWGEN` = v45. Two attempts were started; both were **killed by the system for
low memory**, in the same place — during the first net run, after the cutover
had been performed and the generation frozen.

That is the exact moment the rehearsal is dangerous: page written, `dist/`
staged, `v45` frozen, `MANIFEST` repointed, and nothing yet undone.

## What the tree looked like after each kill

```
web/e2-editor-app.js   5aeae0e1dbfe492d…   (baseline)
dist/e2-editor-app.js  5aeae0e1dbfe492d…   (baseline)
MANIFEST               e2/editor-shell-v2-bundle-v44.json   (the E-1 freeze)
e2/…-v45.json          absent
git status             empty
```

Both logs end with the trap's own output — `=== RESTORE: undoing all three ===`
followed by the restored hashes — which is the handler running, not a tidy
ending. `rerun-KILLED-attempt1.log` and `rerun-KILLED-attempt2.log`.

## Why this is worth banking rather than just retrying

The 2026-08-28 rehearsal wired the `trap` for a reason it stated: *"a run dying
in the middle could not strand the tree."* Until today that was a mechanism that
had never been needed. **A safety mechanism that has never fired is in exactly
the position the rehearsal criterion puts a revert: it is a hope.** These two
kills are the first evidence that it is not.

Note what it protects against and what it does not: the handler runs on the
shell's EXIT, so it covers the harness stopping the job and the script failing;
it would not cover a `SIGKILL` to the shell itself, or the machine losing power.
Those remain unmeasured, and the recovery for them is the same three lines the
handler runs — `git checkout`, `cp web/ dist/`, `rm` the new generation — which
a person can run by hand from this file.

## What is NOT established

Ruling E-3 is **not** discharged. Neither attempt produced a
`reconcile-after-revert.json`, so the post-revert reconciliation on
`20f09cc9…` — revert condition 3 — is still open, with the default the ruling
gave it: the gate does not close.

Stopped rather than attempted a third time. Two failures with the same cause,
at the same point, from a condition outside this tree (machine memory) is not
something a third run answers.
