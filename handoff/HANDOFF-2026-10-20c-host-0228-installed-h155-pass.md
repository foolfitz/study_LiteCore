# Handoff, 2026-10-20c: host 0.2.28 installed, H-154c / H-154o / H-155 all PASS

**First line: ddev runs host 0.2.28** (host commit `0870695`, buildId `817413d5ad5bd502`, unchanged engine package). It replaces 0.2.27 as the uncounted candidate for daily use. The nominal shipped version is still **0.2.26**. v23 is not linked, and nothing about it changed in this stretch.

This continues `HANDOFF-2026-10-20b-v23-spec-pinned-n1-holds.md`. That handoff stays valid for everything v23 (Next 2–5 there). Its first line and its Next 1 are superseded here.

## Authority this stretch

- The owner, in the conversation at 14:00: 「現在可以裝 0.2.28」. Asked for the end, they chose **14:45**. This is the window ruling 1 §2.9 form 1 asks for. It is recorded in `SPEC-M3-link-batch-v22` §14.5 (`9c8ef1d6`).
- **The desk gate is withdrawn for 0.2.28** (§14.5). At 14:02 the gate read dirty for two reasons:
  - desktop Chrome, 28 processes;
  - two containers whose main process is `make run`: `oxool-dev` and `modaodfweb-rhtest`. They are services, not builds; the load was 0.49.

  The owner said the gate was far too strict here, and that CPU contention is in fact rare. The gate guards timing cells (ruling 6 addendum 1 item 9); H-155 is a geometry reading. The owner chose A:
  - withdraw the gate for 0.2.28, with no replacement mechanism;
  - `chain-h155.sh` now guards on the window, `ddev list` and KWallet (`pre_run_checks()["refuse"]`);
  - the red cases are in `chain-guard-red.txt`;
  - `desk_gate.py` is unchanged and still applies to timing cells.
- My first proposal (B, a container-exclusion flag on the gate) was the wrong shape: it was new machinery built to keep a premise that does not hold here (CLAUDE.md §4). The owner's question caught it.
- No build. Nothing was pushed. The host commit is local.

## What happened (14:31–14:35)

All of it is in `findings/evidence/host-0.2.28/README.md` ("The window's run"):

1. `ddev start litecore`. It had been paused since this morning's reboot. Only litecore was running.
2. The pre-apply checks of §14.4 step 3 passed.
3. The patch was applied and committed as host `0870695`.
4. `occ upgrade` printed 0.2.28, with maintenance false.
5. The HTTP check was as green as 0.2.27's, with the same address and the same decoded sha256s.
6. The chain ran, 3 rounds in each browser. **H-154c, H-154o and H-155 PASS in both.**
   - Chrome: box `[605, 323, 640, 335]` in a 1850×980 viewport; centre offset `[0, +0.5]`.
   - Firefox: box `[605, 326, 640, 342]` in a 1850×994 viewport; centre offset `[0, 0]`.
   - On 0.2.27 it was `[-605, -322.5]`.

Finding 155's status now reads fixed on host 0.2.28. The release text successor is `handoff/RELEASE-TEXT-DRAFT-0.2.27-0.2.28.md`. In it, finding 155 has moved from "known" to "fixed" (§3.4).

## State left behind

- **litecore is left running on ddev** for the owner's hand tests. Before the window it was paused, but only because of the reboot. Pause it if the owner asks.
- The owner's hand tests (F3-hand, Ctrl+Home/End, the dialog's look) are still pending. They now run on 0.2.28, whose page is the same as 0.2.27's. That equivalence is an inference: the two versions differ only by the dialog CSS rule.

## Next

1. **Point the owner to ruling 1 §1 and addendum 1 §1** again (the 10-20b handoff's Next 1, first half). It is still unanswered.
2. Then continue v23 exactly as the 10-20b handoff's Next 2–5:
   - the model in two modes;
   - the two-seat review;
   - the diagnostic-profile engine code;
   - the feature profile and host 0.2.29.

## §34.4

- **This stretch:** repaired because of execution **+1**, the chain's guard (§14.5). Repaired because of review **0**.
- **Running total since 10-14b: 33 / 18.**

## Hazards (new)

- Never `cd` in shell commands. I slipped once this stretch (`cd findings/evidence/host-0.2.28`), and the harness moved the primary working directory. Use absolute paths.
- When you copy a chain's shape, ask what each guard protects in the new measurement. See memory `timing-runs-need-quiet-desk-and-idle-session`, appended 10-20.
