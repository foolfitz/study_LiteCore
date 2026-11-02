# Handoff: demo batch 2 done, host 0.2.49 installed, the owner's hand test is next

Checkpoint **2026-11-02, after the 0.2.49 install (15:47 +0800)**. Supersedes `HANDOFF-2026-11-02c-demo-batch-1-host-0247-installed.md` for what is next; read 02c for everything before this checkpoint (batch 1, the `flex: none` regression, the Reds, the Cautions it lists). K's numbers in `HANDOFF-2026-11-02b-k-0245-holds.md` stand.

## State

- **Nominal shipped: 0.2.45** (K holds). **Installed on the own stack: 0.2.49**, an uncounted candidate: host `7782714`, engine `dd6159b571d9b966`, shell generation 84.
- Nothing of ours is running. Local commits are not pushed.
- Demo batch 1's hand test passed (owner's words: 「測試皆通過」, 02c Addendum). Batch 2 (Save first in the toolbar, Close at the far right, as Collabora; the whole Calc page light under any theme) has **not** been hand tested yet.
- Spec: `specs/SPEC-P-demo-batch-2.md`, results in sections 6 and 7. Evidence: `findings/evidence/host-0.2.48/README.md`, `findings/evidence/host-0.2.49/README.md`, `findings/evidence/demo-batch-2/`.

## Done since 02c

- **0.2.48 (spec sections 5, 6).** Save is the first toolbar control on both pages; Close is at the far right of the title row on all three pages (Writer, Calc, viewer). The viewer bar's padding went from 12 to 14 px (`templates/viewer.php`) so Close sits at the same distance everywhere. Both toolbars set their own ink, which fixed Writer's bold contrast 1.51 in the dark theme. Read: `LAYOUT_HOLDS` (14/14 on both browsers, dark arm 2/2), Z, C, F3-84, F4-84, V0', Files 52/52, `HOST_BATCH_HOLDS`.
- **0.2.49 (spec section 7, append 2).** The owner asked for Calc's formula bar and sheet tabs to follow. Only `web/ods-editor.html` changed (delta against 0.2.48: that file alone). The faded `I` was a colour, not an opacity: Nextcloud colours `<em>`, contrast 2.85 in the dark theme. T6 is `T6_HOLDS`: 15 controls equal under light and dark, none below 4.5, red on 0.2.48 (`demo-batch-2/t6-red-on-0248`). Also `DELTA_HOLDS`, `PACKAGE_HOLDS`, `CANDIDATE_INSTALLED`, mirror C (editor 14/14, viewer 11/11, both browsers), Files 52/52, `HOST_BATCH_HOLDS`, `LAYOUT_HOLDS`.
- Named limits still standing from spec section 4: `L-close-host-style`, `L-save-no-dirty-color`. `L-toolbar-only-theme` is superseded for Calc by append 2.
- `capture-after.py` is red on the lock table only, `L-capture-after-live-lock-refreshed`: the rows are equal once `ttl` is left out; the owner's open `.ods` (file 29431) moved. Documents, engine and tree hold. It clears once the owner's tabs are closed; the tool was not changed.

## Next

1. The owner's hand test on 0.2.49 (`https://litecore.localhost:18443`). Their two open tabs under `files/demo/` run an older page until reloaded. Whether 0.2.49 becomes the daily candidate is their word.
2. The ordered-commands product arms, 18 cells with a right answer and 24 records (SPEC-M3-ordered-commands 21.2 and 21.3); the owner put them behind the demo.
3. Microsoft formats and Calc zoom only when asked (what was read about the link is in 02c, Next item 3).

## Reds that are not this batch's

Unchanged; see 02c, "Reds that are not this batch's".

## Cautions

- **T6 and T1-T5 are judged on the host**: `findings/evidence/demo-batch-2/host_layout.py` and `host_calc_theme.py`. The mirror cannot reach an empty desk, so a mutation there stays green.
- A release touching only `ods-editor.html` does not repeat Z, F3, F4, V0'. A change to `web/e2-editor.html` does (F4's identity binds it); V0' then needs a new directory, `derive_v0_prime.py <dir>`.
- `capture-after.py` will read red on the lock table while the owner's tabs are open. Read the clause before calling it a release problem.
- Use absolute paths; a shell `cd` carries between calls (02c).

## Section 34.4

Work since 02c (batch 2: 0.2.48 and 0.2.49).

- **Fixed-by-execution: 0.** No tool changed after its first run. Two product changes were forced by a measurement: the viewer padding by T1's red on 0.2.47, the `<em>` colour by T6's red on 0.2.48.
- **Fixed-by-review: 0. Fable rulings: 0.**
- Wrong statements, corrected: 1. 02c's Addendum 2 says Nextcloud "fades" `<em>`, written before it was measured; T6 read a colour, not an opacity.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs in zh-TW. Linking and compiling `make` stay the owner's. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
