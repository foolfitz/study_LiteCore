# Handoff, 2026-09-10 — 096 is fixed and linked, and the guard went quiet on the profile that has it

Written at the end of a very long day. Entry points, in order: this file, then
`findings/096-*.md` (read it whole; the rulings and results are appended in
order at the end), then
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`'s last two sections —
the soak's reordering lives there.

Tree at `7f2234c6`, clean, nothing pushed. `make test-e2-c-static` exit 0.

## What happened, in one paragraph

The owner's second T4 manual round found **finding 096**: at a document
boundary, one arrow key kills the session with the **no-checkpoint** notice —
data loss, `revision: 0`, no edit required. Four arms reproduced it 40/40
including byte-identical shipping bytes, so it was never a candidate
regression. A pre-registered three-way discrimination left one explanation
standing: **at a boundary the core broadcasts nothing**, and the engine's move
path is the only one of three siblings that arms no deadline, so it waits
forever. The owner ruled **A + C**; both landed, the owner linked
`e2-editor-v14`, and the fix measures out.

## The state of the fix

| | |
|---|---|
| profile | **`e2-editor-v14`**, `probe.wasm` `5847a1407d3af58f…` |
| archived | yes, same day — `build/archive/e2-editor-v14-5847a140-worker-6e75829a-manifest-9943b064/`, 10 files, `sha256sum -c` all OK |
| candidate page | `d74801324d24394924ef044cf3d291614538332d74e136aed531f8042332591e` — **not a git blob**, a reproducible derivation (`build_cutover_page.py --profile e2-editor-v14`, never `--write`) |
| shell generation | **v51** (v50 was spent by the revert rehearsal earlier the same day) |
| shipping page | still points at `e2-editor-v8`. **No cutover has been performed.** |

**A works, 10/10 both directions**, measured against a prediction written before
the artifact existed: `NOT_REPRODUCED`, `died: false`, session `ready`,
`revision 0`, no notice. Latencies: a moving press is 47–51 ms; a boundary press
is 259–263 ms (n=50) = the 250 ms deadline plus ~11 ms. **The controls died in
the same session**, v13 10/10 and v8 10/10, on page bytes byte-identical to the
pre-link runs — the green is not the instrument changing.

The product path on v14 is **40 PASS / 2 NE**, and the 42nd check
(`a-boundary-arrow-press-does-not-cost-the-work`) exercised clause **B2** for the
first time, driven rather than declared.

## The thing the next person must not miss

**The guard went quiet exactly where the fix landed.**

```
v14 (fixed)     clausesExercised = [B1, B3, B2]
v8  (shipping)  clausesExercised = [B1, B3, B4]
```

**No single run now covers all four clauses**, and the one that goes silent is
**B4 — "what comes back contains what was typed"**, which is the whole reason
half C exists. The logic is sound: the session never dies, so the notice never
appears, so there is nothing to press. But the consequence is that the property
C protects has nothing watching it on the profile that has C.

This is 069's shape one turn later: fix an element, and the net that guarded it
stops being driven. **Undecided, and it is the owner's**: either give the check
a second inducer so B4 is reachable on a fixed profile, or write down that B4 is
meaningful only on the shipping side and accept it explicitly.

## Three more things measured and not explained

* **The first boundary press costs 623–958 ms; every later one costs 261 ms.**
  10/10, both directions, not intermittent. Still answered, session still
  usable, so no prediction failed — but nobody has measured why the first
  differs. **No cause named.**
* **C is no longer reachable through this gesture on v14** (`armsDisagree:
  false`). Half C still runs — the checkpoint is taken — it is simply never
  needed, because A answers first. On the shipping page C is still cell-for-cell
  what it was: `without` WORK_LOST 3/3, `with` RECOVERED 3/3.
* **`boundaryPressAnsweredSeconds` measures the instrument, not the engine** —
  it is the probe's own 4-second watch ceiling. Only its null-ness informs, and
  the name invites misreading.

## Still open, with who owns each

1. **B4's coverage gap** (above) — owner's ruling.
2. **The wrong-gesture wording**: the notice reads 「回到選取手勢前的檢查點」 on
   a press that was an arrow key — finding 061's shape. Deliberately unfixed:
   it would move `pageSha256`, and making it exact for both gestures needs
   branching, which is new machinery. Owner's ruling; the cost argument is
   weaker now that the page moves with every link anyway.
3. **Findings 094, 095, 097** — the unbound page HTML; the no-caret-after-
   ArrowDown observation (**not investigated, harness path not excluded**, and
   the 096 trace now predicts its shape with a one-line discriminator: wait
   longer than 30 s); and the contract field that declares the opposite of what
   the product does and that nothing reads.
4. **Why the core broadcasts nothing at a boundary.** The fix did not need to
   know. Two named remedies: engine-side callback/command correlation (needs a
   relink) or the browser-free native LOK harness (`tools/f059_native_*.cpp`,
   no relink).

## The gate, and why nothing is being counted right now

Everything identity-bound to `31787584…` — the soak's 6 runs, condition 2, 4a,
the ODT round trip, revert condition 3, and **T4 itself** — died with the link
to v14. That was known and priced before the owner chose.

**The soak has been reordered to the end, behind development**
(`PLAN-2026-09-06…`, "The soak moves to the end"): running twelve clean runs on
an identity that development will move again is structurally wasted, not merely
slow. Two conditions were recorded with that decision and neither is relaxed:
the soak runs **in full on the final identity before any cutover**, and it has a
**floor of three calendar days**, so whoever schedules a cutover counts backwards
from it.

**T4 is the expensive one to re-earn.** It is the owner's evening, and it is the
round that produced 093 *and* 096 — two defects that nine clean automated runs
and a full agent-driven gate did not find. Budget it deliberately rather than
discovering it late.
