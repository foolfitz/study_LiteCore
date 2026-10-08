# Shakedown of the reviewed merge runner, on v18: result

Per `PREDICTION.md` (committed `a8571811` before the run). `chain.sh`, launched detached, 2026-10-08 15:42:06 - 15:55:31 (+08:00). Runner sha256 prefix `79b33eae2b95b283` and page source `a7d8ffa1adc60a9a` at start and end (`chain.log`). Every step's exit code is captured first (`exit=0` ×8, including both `--pair`). Every stderr is empty. Uncounted: `BINDING` is None. Candidate page `b3ad0f645c70d954` (v18 with the 118 fix), the same as `../../v18/finding-118/` P4.

`read.py` (written before the run) → `reader-output.txt`: **R1, R2, R3, R4 HIT on Chrome and Firefox; exit 0.**

| | Chrome | Firefox |
|---|---|---|
| C01 (merge) | `verified-key-undo`; runner 132.8 ms, engine 38 ms. `toastsAtEnd` = two `已存出 14.3 KB` | same; 146.2 / 38 ms |
| Y01 (typed merge) | 748.4 / 628 ms (v18's typed plateau, finding 117); two save toasts | 748.5 / 631 ms |
| C15 (`key-deadline`, `keyPosted:true`) | 2094.1 ms; the ordered pair 「…，正在重新載入…」/「…，已重新載入。請看一下那個位置…」; generation + 1 at both reads | 2099.2 ms; same |
| C29 (`nothing-selected`) | 255.9 ms; the ordered pair with the lead 「這一下沒有取得可刪除的內容。文件沒有被改動」 | 257.3 ms; same |
| `--pair` | 4 pairs, `sameOrder: true`, 0 differ, exit 0 | same |
| M2-4 | 105/105 `verified-key-undo`. `latency` false: 102 presses slow, engine `keyToUndoMs` from 37 to 2001 ms (v18 has no 117 fix). Every other clause is true. `toastsAtEnd` = one `已存出 8.3 KB` | same; 37-2002 ms |

- Every report's `bound` has the nine `BOUND_KEYS`, each 64-hex. `counted` is false. No `teardownError`, and no `error` in `observerAtEnd`. No process with a CDP port, `geckodriver` or `-marionette` was alive after any step (`*.ps-after.txt.test-browsers`, all empty).
- What this shows: the fields the review added (`toastsAtEnd` and its two clauses, the ordered reopen pair with real product wording, `reopenedDocument.sha`, the second generation read, the nine bound values, the pair's new comparison and exit code) behave in both browsers as the unit tests assumed. It shows nothing about v19.
- Not looked at: the trace windows (`keyTrace`, `presses[n].trace`) beyond their presence.
