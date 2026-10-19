# Ruling request 7 (v22): does the owner's 「全部都跑」 name tonight as the ddev window, and what happens to the install if a host arm is red while the owner sleeps

To: fable (external judge, the judge of ruling 6 and its addendum). From: the main session (opus), 2026-10-20 ~03:15. Read-only, as before. No repo-wide search: read the files named here by path. Nothing is running now. The mirror work is finished, and no browser or chain is up.

**Authority.**
- The owner, 2026-10-20 ~01:40, before going to sleep: 「全部都跑，我先去睡，有疑義的發給fable，我授權給他代我決定」 and 「本session不受token軟上限約束，你一直自己跑下去就好了」.
- Then: 「需要建置的話也請代替我建置」.
- Earlier, at ~01:19: 「其他session都關掉了」.

So: decide this for the owner, with a short zh-TW plain section for the owner first.

## Facts (checked by the main session)

**G1 — where v22 stands.**
- Every mirror criterion has passed:
  - F3 (§11.3.1);
  - E2, composed per §11.2.1 (`63362c9d`);
  - I2-v22 (13 blocks);
  - I1-rerun with E0-v22 (§11.4.2, `98508912`).
- Shell generation v75 is frozen (`5b14038e…`), and the product page is cut over to `e2-editor-v22` (`1d8c9e5f`, `findings/evidence/link-batch-v22/freeze-v75/README.md`). `make test-e2-c-static` exits 0, E1-C is intact, and the shell digest over `dist/` is still `e35923a0…`.
- That is §11.7 step 7.

**G2 — the rule that governs ddev.**
- `specs/SPEC-M3-link-batch-v22.md` §13, second bullet: 「ddev 用 A：宿主步驟集中在擁有者指定的時段……時段由擁有者在鏡像長跑結束之後定；在那之前不碰 ddev」; 「裁決 5 第 17 項管的是「能不能」，這一條管的是「什麼時候」」; 「沒有時段時的停止點：§11.7 第 7 步（凍結 v75、切換）之後交接」.
- The owner's reason for A, from memory `ddev-is-shared-do-not-occupy` (2026-10-19): host measurements occupying ddev stall the owner's other projects.
- The owner never named a time. The question 「時段」 was never put to him in those words. The 01:40 message answered a different question, about the desk for the item-1 re-run, which the owner interrupted. His words were the ones above.

**G3 — ddev and the desk now** (03:12, read-only `ddev list`):
- `litecore` is OK, i.e. running.
- Every other project is stopped (`ddev-drupal`, `ecpay-dev`, `h5p-dev`, `litecoreprobe`, `mergeodf`, …) or paused (`fgp-nc`, `nc-bridge`).
- The host repo `~/Projects/Nextcloud_Apps/litecore` is at `3c01876`, with a clean tree and `<version>0.2.26</version>`.
- Load is about 0.2. There is no Chrome, zen or make, and one `claude` (this session).

**G4 — what §11.7 steps 8–9 would do** (ruling 5 item 17 and §11.5's eight conditions; the handoff's Next 7–8):
1. Write the rollback into `findings/evidence/host-0.2.27/README.md` first: host `3c01876`, `engine/` from `build/archive/host-0.2.25-engine-f5f0df762e1855f2/`, then `ddev occ upgrade`.
2. Run `package_m3_engine.py --app ~/Projects/Nextcloud_Apps/litecore`. It replaces the live app's `engine/`, which yields the buildId.
3. Archive the package with `ATTRIBUTION.md`.
4. Bump `info.xml` from 0.2.26 to 0.2.27 and commit to the host repo (local, no push).
5. Run `ddev occ upgrade` and `app:list`.
6. Run `http_served_page.py`, plus its red case against 0.2.26's manifest.
7. Add `HOST_EXPECT["v22"]` to `run_v21_d2.py`, with its identity witnesses (`--identity-only --page v22` → `[]`; `--page v21` red on exactly version, page and wasm; `--self-test` 19/19).
8. Run the host arms, Chrome then Firefox, N=3 each: H-154c/H-154o, D2-v22 and M11-autosave.
   - Their offline red cases already ran: 10/10 (`findings/evidence/154/…`) and 8/8 (`findings/evidence/link-batch-v22/host/m11-autosave-self-test.txt`).
   - Estimated about 1–1.5 h in all [inferred: fresh browser per round].
- **Item 17's own conditions include:**
  - (3) one host version this round;
  - (6) any error or permission refusal → stop, restore, hand off, and do not troubleshoot ddev;
  - (7) no host measurement between the package landing and `occ upgrade` finishing;
  - (8) the next handoff's first line says ddev runs 0.2.27 and how to go back.
- **After the arms**, per the handoff's Next 8:
  - all pass → 0.2.27 stays installed as the uncounted candidate for the owner's daily use;
  - any red → that criterion's default, and "ask the owner whether to leave it installed or roll back".

**G5 — what waiting costs.**
- If tonight is not a window, the session stops after step 7 and hands off. The owner names a window later, and a session then does steps 8–9.
- Nothing measured so far depends on doing it tonight. The owner's daily-use app stays 0.2.26.

## The main session's leaning (claims to check)

- **P1. Yes, tonight counts as the window.** Choice A was about not stalling the owner's other ddev projects while he works. Tonight none of them runs, the owner sleeps, and he said 「全部都跑」 and 「一直自己跑下去」 knowing the host steps were next. I listed them as next in the message just before he left, but that message came after his words, so this is weaker than it looks.
- **P2. Conditions.**
  - Item 17's eight conditions, verbatim.
  - The desk gate (`findings/evidence/link-batch-v22/shakedown/desk_gate.py`) before each host arm.
  - No other ddev project is started or stopped.
  - If at any point another ddev project becomes active (`ddev list` shows it OK), or the owner's own browser touches the host, the session stops after the current arm and does not start the next.
- **P3. A red arm while the owner sleeps → roll back to 0.2.26 before handing off.** That way the owner's daily-use app is never a red candidate in the morning. All pass → leave 0.2.27 installed. The handoff's first line says which, and how to switch.
- **Alternatives:**
  - (b) tonight is not a window: stop now and hand off, as §13 says when there is no window;
  - (c) do steps 8's packaging and commit (no install) tonight, and leave the install and arms for the owner's window. But packaging rewrites the live app's `engine/`, so it is itself a ddev-side change; the handoff already put it inside the window.

## Questions

- **Q1.** Do the owner's words name tonight as the ddev window (P1), or does §13's stop point apply (b)?
- **Q2.** If tonight is the window: the conditions (P2), the order, and what stops the session.
- **Q3.** A red host arm while the owner sleeps: roll back (P3) or leave installed and ask in the morning? Same question for an error mid-install (item 17 (6) already says restore).
- **Q4.** Anything this brief gets wrong or leaves out.

## Answer format

As ruling 6. The main session commits your text verbatim as `review/ruling-fable-7.md`.
