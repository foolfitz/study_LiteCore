# Ruling on finding 175's scope (fable, on the owner's authority, 2026-10-30)

The owner, going to sleep, authorized fable to rule in their place ("需要裁決的地方請發給fable，我授權他帶我裁決").
Asked by the main session after the S1 shakedown (`tools/check_v26_select_all.py --plan shake`, run 4:
after/list-contexts/copy/chrome) showed the copy toast listing every code point. Verbatim:

> RULING (on the owner's authority, 2026-10-30): **A, with conditions** — fix the copy/cut toast in generation 80 before freezing.
>
> **Why (plain language).** Ctrl+A makes "copy the whole document" the normal case, and on that case the toast becomes a screen of `U+0045,U+0031,…`. The owner would hit it within minutes of his hand test (b), exactly like 173 and 174 — then we ship 0.2.43 anyway, at more than 30 minutes' cost. The fix is two expressions in one file, touches no engine/manifest/shell, and the gate is still open (§7 step 5 before step 6; gen 80 not frozen). Verified in source: `summarizeUnicode` (input-adapter.js:444) returns an array; page lines 2729 and 3736 interpolate it. Note: this was already seen 2026-08-23 and written into a tool comment (`probe_inline_range_format.py:75-79`) instead of a finding — file 175 regardless of A/B.
>
> **Conditions.**
> 1. Order: spec append committed → red-before witness → page fix → green → `make -n e2-c-assets` (3 cp) → `make e2-c-assets` + cmp → full `node --test` (U1/U2/U3 again; U2/U3 are cut from page source) → S2 full 24 runs again (page bytes changed after it ran) → full S1 with the new clause → freeze 80.
> 2. Fix page-only: use the count (e.g. `result.codePoints.length`) in both toasts. Do NOT change `summarizeUnicode` (shared by r7 apps and evidence shapes).
> 3. New unit test U4 (`page-copy-toast-count.test.mjs`, witness `u4/red-before.txt`): both toasts match `已(複製|剪下) (\d+) 字` with the number = code-point count. Keep U2's existing witness untouched.
> 4. S1: add clause `C.count` (Chrome, non-frame fixtures): toast number == code-point count of `follow.clipboard`; with its own self-test mutation (number+1 must go red). Cut has no browser arm — say so in a named limit; U4 covers it.
> 5. The 11-run shakedown is evidence for finding 175 only; it must not be cited as a gate run.
> 6. Do NOT touch `run_e2_c_product_path.py` (bound). Its `copy-lies` mutation (line 2489) embeds the old toast line; `apply_mutation` will abort "tree moved" on the next `--mutate copy-lies`. F3-80/F4-80 run without `--mutate`, so no cell moves, but the spec must name this debt (L-copy-lies-pattern-stale) so the next census isn't surprised.
> 7. Done = spec append + finding 175 committed; U4 red/green; U1-U3 green; S2 24/24 on new bytes; `S1_HOLDS` incl. C.count and self-test all red.
>
> **§9 compliance: yes.** (1) Before-satisfaction: full S1 has not run, gen 80 not frozen; nothing from the old bytes will count. (2) Forced and named: shakedown run[4] (after/list-contexts/copy/chrome), report path, finding 175. (3) Form: per-instance property (form one), enumerated in the tool's clause table with a self-test mutation (form two). (4) Deadline: closes when `S1_HOLDS` lands; later toast concerns become findings. Counting: S2 and S1 counts reset (bytes changed); criteria for S2 unchanged.
>
> **Wording/position (append-only, dated 2026-10-30 "追加一"):** §2 add item 6; §5.4 add a dated sub-block defining C.count; new §5.10 U4; §6 add L-cut-toast-browser-unmeasured and L-copy-lies-pattern-stale; §8 append "因執行而修 1（S1 shakedown, finding 175）"; §9 revision row. Original text stays.

Main session checks before acting (2026-10-30): `probe_inline_range_format.py:74-79` holds the 2026-08-23
comment; `run_e2_c_product_path.py:2489` holds the `copy-lies` mutation with the old toast line. Both as stated.
The shakedown report itself was in the session scratchpad; its run 4 record is copied to
`shake-run4-copy.json` here (the evidence for 175, not a gate run).
