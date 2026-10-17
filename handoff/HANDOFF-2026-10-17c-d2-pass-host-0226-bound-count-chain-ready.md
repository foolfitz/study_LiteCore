# Handoff, 2026-10-17c: D2 passes on host 0.2.26 (finding 154 fixed in the host), v21 is bound, and the 0.2.26 count chain is ready for the owner

This continues `HANDOFF-2026-10-17b-d7-pass-v74-frozen-d2-host-arm-ready.md` and covers commits `f8e66e8a..HEAD`. The main session is opus. The owner was present, mostly from the phone (remote control). They said ddev was free for this session. They answered three questions:
- the 0.2.25 install: they ran it themselves (B), after a permission-rule attempt failed;
- finding 154's fix: sent to fable (D);
- the page-honesty Vrw red: the main session fixes the check (A).

## State

| item | state |
|---|---|
| Nominal shipped version | **0.2.24**, unchanged. v21 / host 0.2.26 is a **bound, uncounted candidate** |
| v21 scope | Item 1 only (Ctrl/Cmd+Home/End, finding 142). Item 2 withheld (finding 153) |
| Item-1 criteria | **All PASS in Chrome and Firefox.** D2 (host) PASS 6/6 on 0.2.26 (`2d6c984b`); the rest as in 10-17b |
| Host | **0.2.26** installed: host `3c01876` = 0.2.25 (`03970d0`, the v21 package) + finding 154's CSS rule. Engine package `f5f0df762e1855f2`, byte-equal to the 0.2.25 archive (`build/archive/host-0.2.25-engine-f5f0df762e1855f2/`). HTTP serving checked (`findings/evidence/host-0.2.26/`) |
| Shell / engine | v74 (`27f33a13…`), page `605cf24b…`; `e2-editor-v21` (wasm `db3408f5…`, worker `0d55bcfa…`). Unchanged |
| Binding | Pins re-bound to 0.2.26 (`a643de39`, 11 files, 25 lines). Merge `BINDING` = v21 (`7ea8038f`). Merge runner frozen (§34.1) until the 0.2.26 count's verdict is read |
| Count chain | **Ready, not started**: `findings/evidence/m3-production-ui/runs-0.2.26/` (chain, reader, README). Preflight-only: P0–P4 and P6 ok; P5 refuses by design (no window; 2 lock rows) |
| First contact | The chain's whole shakedown phase, the merge shakedown on v21 and the product-path net on v21 all ran once before the window, clean or the same shape as 0.2.24 (`findings/evidence/link-batch-v21/first-contact/`) |
| Tree | Clean after this handoff's commit |

## What happened

1. **D2's 0.2.24 red case on the host** (`b6a92bbe`): red 6/6, as required. The server's first paragraph went `LD-PAGE-01` → `LD-AGE-01`. The positive control differed 6/6. One smoke round per browser came first.
2. **Host 0.2.25** (`f9f0d73e`, `ac949ad3`): `package_m3_engine.py` produced buildId `f5f0df76…`, then the archive and the HTTP check (with its red case against 0.2.24's manifest). The version bump and `occ upgrade` were refused to the session by the auto-mode classifier, and so was reading or editing the settings. The owner ran them.
3. **D2 on 0.2.25: NE 6/6 → finding 154** (`1e3dae22`).
   - v21's `e2-editor.html` added a closed `<dialog id="markdown-dialog">`. Nextcloud's `core/css/server.css` reset (`article, aside, dialog, … { display: block }`) beats the browser's own `dialog:not([open]) { display: none }`.
   - So on the host the withheld Markdown dialog sat over the editor's top left, and the first-line click landed in its textarea. No caret was placed, and no key did anything.
   - Measured in both browsers, with a one-rule counterfactual (`findings/evidence/154/`). Every earlier v21 run was no-host, `v21host` included, so none could see it.
4. **Fable ruling 3** (`review/ruling-fable-3.md`; brief `c6884f42`; adopted `64d5f10c`; spec §12.5):
   - fix A: one host rule `#litecore-editor-root dialog:not([open]) { display: none; }`, host 0.2.26, package untouched;
   - the unchanged diag tool as the fix's acceptance;
   - `HOST_EXPECT`'s version is a binding, not a repair;
   - D2 re-runs once, under a stop rule;
   - no new v21 criterion. Two v22 work items are written in finding 154.
5. **Host 0.2.26** (host `3c01876`, `fd72505b`).
   - The info.xml Edit failed (the file had not been read), but the commit sent in the same batch went through with the template alone. It was amended with the version (the host repo has no remote).
   - The owner's `!` command from the phone did not execute. The session ran `occ upgrade` on the owner's typed command.
6. **Fix acceptance** (spec §12.5 (c′)): `asShipped` passed every read in both browsers. Chrome's `withRule` (a second click) read too early: the latency label was still the first click's.
   - The main session stopped by the pre-registered rule and asked fable.
   - **Addendum 1:** the acceptance is met. The `withRule` clause is withdrawn (§4; premise false by construction), named **L-154-diag-second-click**. No tool change, no re-run (`7db85fb6`).
7. **Re-pin of `HOST_EXPECT`** (`090da6b6`, one line), then **D2 PASS 6/6** (`2d6c984b`). `waitedMs` was 2,258–2,259 in Chrome against a prediction of about 2,252–2,255; no judge clause reads it. The 12 item-1 reports' HTML source equals the package's (`html-source-equality-0226.txt`).
8. **Binding** (an opus subagent inventoried it read-only; the main session checked and applied it):
   - re-pin `a643de39`;
   - `BINDING` `7ea8038f`, red first: exactly 1 failing test, then 134 OK;
   - spec §12.6.
9. **Page honesty Vrw would have stopped the chain** (the subagent predicted it from source).
   - Witness (`1e2bb146`): the census un-hides and clicks the withheld `paste-markdown`, which does nothing, so `did not advance`.
   - The owner chose A: §7.14, the writable arm skips a button hidden at census, for that button only.
   - Two new red cases: 154 → 158 red. The wrong exemption ("any hidden exempts all") turns one of them GREEN.
   - Live clean in both browsers (`94b4913e`).
10. **First contact and chain prep** (`3967d4d0`, `b7997423`).
    - The chain's shakedown phase: 8 runners, all clean.
    - The merge shakedown on v21: its `bound` equals `BINDING`; 26/26 outcomes seen in v20's counted rounds.
    - Product path on v21: the same shape as 0.2.24's v20 runs.
    - The chain, reader, product-path judge copy and PREDICTION were written; preflight-only run.

## Next, in order

1. **The owner, before the window:**
   - delete the two expired lock rows the new-document shakedown left (ids 4882, 4886; command in `runs-0.2.26/README.md`);
   - agree a window;
   - start the chain (one line, in the README; about 8 h). During it: no `litecore.ddev.site`, no ddev start/stop of any project, no core build, no edit to any runner-imported file, desktop Chrome closed.
2. **After `DONE`, a new session reads it:**
   - `bash findings/evidence/m3-production-ui/runs-0.2.26/read-0.2.26.sh`;
   - the hand readings (J-b.2 on C2, §17.4's R-arm busy spans);
   - the product-path reader made red once offline (PREDICTION.md);
   - then `RESULT-0.2.26.md`.

   If the count holds, 0.2.26 becomes the nominal shipped version (spec §11.1 K).
3. **The 0.2.26 release text**, after the count. Named limits to carry:
   - L-142-readback-overtaken, -steps, -sdk-callable;
   - L-md-sdk-callable;
   - L-154-diag-second-click;
   - findings 150 (fixed), 151's remaining part, 153 (open, reachable on 0.2.24), and 154 (fixed in the host; v22 page hardening pending).
4. **v22** (order C): the stack-size relink alone (finding 153's criteria), with item 2's re-enable, fix 3 (finding 152), and finding 154's v22 work items (the page-side `dialog:not([open])` rule; item 2's host criteria for the closed and the open dialog).

## Hazards the next session must know

- **No edit to any file a runner imports until the 0.2.26 count's verdict is read.** The merge runner is under §34.1 again.
- **Re-judging 0.2.24's reports on the live tree reads NOT YET / NOT DONE (identity) by construction.** The pins moved. Use the runners as of `a8b5ff33` for that.
- **`dist/` is v21**: the `dist0224` no-host variants still serve v21 with `identityOk: true` (carried from 10-17b).
- **The owner on the phone:** `/permissions` does not open, and `!` does not execute. A command the owner types in full is a request for the session to run it.
- **The auto-mode classifier** refused the info.xml + `occ upgrade` combination and any settings read. An Edit to the host repo and `ddev occ upgrade` alone later passed.

## Not done / open

- Everything in "Next".
- Registered, one line each, no code:
  - **L-154-diag-second-click**;
  - D2's NE reason carries no payload about the click point;
  - `HOST_EXPECT` pins no buildId.
- Carried, unchanged:
  - the observer's docstring says "500 ms" (`v21_item1_observer.py:16`);
  - `audit_product_path_coverage.py` red;
  - `Language=` / D12;
  - the ordered-commands spec;
  - finding 147 on WASM.

## §34.4

- **Repaired because of execution: 1 this round** (page honesty §7.14; witness `1e2bb146`).
- **Repaired because of review: 0.**
- **Running total since 10-14b: execution 29, review 18.**
- **Not counted:**
  - the `HOST_EXPECT` version re-pin (witnesses: the before/after identity outputs);
  - the 0.2.26 re-pin and `BINDING` (bindings);
  - the diag tool (a diagnostic);
  - the host rule (a product change);
  - the withdrawn `withRule` clause (a withdrawal, not a repair).

## Subagents

- **Fable**, ruling 3 and its addendum 1, read-only. The main session recomputed the cited numbers before adopting each. One count in ruling 3 (served-HTML hashes, "11 reports") did not match; nothing depended on it.
- **Opus**, the binding and count-prep inventory, read-only. Every value was recomputed by the main session before applying. Its source-level prediction of the page-honesty red was confirmed by a live witness before any change.
