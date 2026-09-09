# Finding 096 — the build-and-link rule for `e2-editor-v14`

Written 2026-09-09. **Nothing was linked.** No `probe.wasm` was produced, no
`dist/profiles/**` byte was written, no core was rebuilt. What this directory
records is a Makefile rule and the measurements that say it will work, taken
without walking through the one-way door.

The rule is in `wasm_sdk_probe/Makefile`, the `E2_V14_*` block. It mirrors the
`E2_V13_*` block written on 2026-09-08 (`a36cbc5e`); where it does not mirror
it, §5 says so.

---

## 1. Why a new profile rather than re-running v13's target

Finding 096's engine half landed in `src/probe_engine.cpp` at `761fc80d`. That
one edit was enough to make v13's target dirty. Measured **before** anything
was written:

```
make -n dist/profiles/e2-editor-v13/sdk-manifest.json   ->  2 em++ lines
                                                            (probe_engine.o, then the link)
```

`src/probe_engine.cpp` is from 20:21 on 2026-09-09; `build/e2/e2-editor-v13/`'s
objects are from 12:10. So the runbook's step-4 command, run again today, would
have recompiled and **relinked into `dist/profiles/e2-editor-v13/` in place** —
producing a profile *named* v13 whose bytes are not v13's, while six soak runs,
the 4a acceptance, the ODT round, the revert rehearsal and the T4 manual round
all bind to that name (findings 027, 036, 042). `build/archive/` would have made
it recoverable; it would not have made it unconfusing, and unconfusing is what
that directory's naming convention exists for.

The v14 block gives 096's link its own build and dist directories, so v13 is
never a prerequisite of anything.

---

## 2. The one variable against v13

v13's artifact was linked from `ec3402bf` (the last commit before 2026-09-09
12:13). Since that commit:

```
git diff --stat ec3402bf..HEAD -- src/ sdk/
  wasm_sdk_probe/src/probe_engine.cpp | 146 +++++++++++++++++++++++++++++++++-
  1 file changed, 145 insertions(+), 1 deletion(-)
```

and the tree's own instrument agrees:

```
what_the_link_ships.py --variant a11y --since ec3402bf
  same     sdk_api
  same     unoembind_stub
  same     editor_api
  CHANGED  probe_engine
```

`sdk/sdk-worker.js` is **byte-identical** to the copy v13 packaged
(`cmp` clean against `dist/profiles/e2-editor-v13/sdk-worker.js`), so the worker
is not a variable either.

**The instrument's gap is closed this round, and it is named because it was open
last round.** `what_the_link_ships.py` deliberately does not preprocess
`a11y_tree_probe` (`notPreprocessed`, its own word), and for v13 that TU was
precisely what moved — v13's Makefile comment says so. For v14, `git` covers it:
`src/a11y_tree_probe.cpp` has not been touched since `c2a7abad`, well before v13
was linked. Option B's geometry rides across unchanged rather than unmeasured.

---

## 3. No core rebuild — and this round's control linked today

Both versions of the changed TU — `ec3402bf`'s and the tree's — were compiled to
**scratch** with the exact flags the v14 rule's product-TU pattern uses. Both
clean, about 1.8 s each. Their **undefined symbol sets are identical**:

| | undefined symbols |
|---|---|
| `probe_engine.cpp` @ `ec3402bf` | **151** |
| `probe_engine.cpp` @ HEAD | **151** |
| added by finding 096 | **0** |
| removed | **0** |

v13's argument had to reach back to v10 through archive indexes, and set-
differenced against 170 archives to get there. This one does not need to: the
`ec3402bf` object **is** the object that linked into `e2-editor-v13` on
2026-09-09. Same undefined set, same link line, already resolved once, today.

Data: `symbol-resolution.txt`.

---

## 4. Finding 042 — nothing else moves

Full numbers in `make-n-and-guard.txt`. Three things, in order of how easy each
is to state wrongly.

**4.1 `make -n` is NOT byte-identical before and after, and saying it was would
be false.** `Makefile` is a prerequisite of `build/r5/writer-review/exports.txt`
and of every `%.o` rule. The owner's v13 link regenerated `exports.txt` at
12:10:37 on 2026-09-09, which is **newer** than the Makefile's 2026-09-08 07:49
mtime — so any edit at all, or a bare `touch`, makes it stale again. The v13
round got byte-identity because that file happened to already be older than the
Makefile. The baseline changed between rounds; the property did not survive it.

**4.2 The property that does hold, measured by replacing the edit with a
touch.** The original Makefile content was copied back over itself (fresh mtime,
same bytes), `make -n` taken over the 18 targets, then the v14 block restored
and `make -n` taken again:

```
original content, fresh mtime : sha256 c054bc1c4b6c9278124621740e2e2a6bdbb39c2ecee73c260755435dd6fa3cf3
with the E2_V14_* block       : sha256 c054bc1c4b6c9278124621740e2e2a6bdbb39c2ecee73c260755435dd6fa3cf3
```

**Byte-identical.** The v14 block adds exactly zero work to any of the 18
existing targets; the entire delta against the baseline is the mtime.

**4.3 What the baseline delta consists of.** `exports.txt` regeneration (`grep`
and `printf` into text files — no compiler, no linker) plus four extra `em++`
on `e2-editor-v13`, whose target was **already** at 2 `em++` before this edit.
Per-target `em++` counts are unchanged everywhere else.

**4.4 What actually holds the artifacts still.** Not make's dependency graph.
Every `.o` in this tree has been out of date for a long time — the baseline
already prints 5–6 `em++` per existing target. What stops them is
`refuse_unasked_relink`, sitting in every link recipe and aborting before `em++`
runs. "Nothing relinks" means **the guard still stands**, not that make would
decline.

**4.5 Measured.** All **334** files under `dist/profiles/` and `build/e2/` are
byte-identical before the edit, after the edit, and after the red cases in §5
were executed. Listing: `artifacts-unchanged.sha256`. The four hashes the
runbook has the owner record are unmoved: `4a2710bb` (v8), `4ec1e389` (v10),
`4ec1e389` (v12), `0fe25650` (v13).

Reproduce:

```
find dist/profiles build/e2 -type f -print0 | sort -z \
  | xargs -0 -P 8 -n 40 sha256sum | sort -k2
```

---

## 5. The red cases

Green from a checker you wrote yourself only proves the checker returns green
(AGENTS.md §6).

### 5.1 The relink guard refuses, and it was really executed

The guard's own line was extracted from `make -n <link target>` and **run**,
after checking the extracted text contained zero `em++` lines:

| link target | `ALLOW_FROZEN_RELINK` unset | `ALLOW_FROZEN_RELINK=1` |
|---|---|---|
| `build/e2/e2-editor-v14/probe.js` (this rule, new) | **exit 1, refused** | exit 0, proceeds |
| `build/e2/e2-editor-v13/probe.js` (today's evidence) | **exit 1, refused** | exit 0, proceeds |
| `build/e2/editor-v8/probe.js` (the SHIPPED product) | **exit 1, refused** | exit 0, proceeds |
| `build/e2/e2-editor-v10/probe.js` | **exit 1, refused** | exit 0, proceeds |

Hashes re-taken after: unchanged (§4.5). `make test-e1-c-frozen-guard`, the
tree's existing mtime-independent assertion of the same property, still passes.

The v14 rule carries the guard on its **first** link, when nothing frozen exists
yet — deliberate, for the reason v13's comment gives: the second link of that
name would be a relink, and a guard you can forget to add later is not a guard.

### 5.2 The manifest checker, red on real manifests

`V14_MANIFEST_MUST_DECLARE` extracted from the Makefile and run:

| input | result |
|---|---|
| `dist/profiles/e2-editor-v13/sdk-manifest.json` | **exit 1** — four name-shaped declarations absent |
| `dist/profiles/e2-editor-v8/sdk-manifest.json` | **exit 1** — seven absent, including `documentOutlineGeometry` |
| v13's manifest with `v13`→`v14` substituted | exit 0, all nine found |

The flag-by-flag census that gives each of the nine entries its discriminating
power was taken for v13 and is
`findings/evidence/093/step4-build-and-link-rule/FLAG-CENSUS.md` — nine cases on
the real builder, one flag dropped per run. The builder takes the profile name
as data, so only the three name-shaped literals change here. That census is
**not re-taken**; §6 lists that as an inherited claim rather than a fresh one.

### 5.3 The one assertion v13's rule does not have

**Finding 096 is invisible to every manifest assertion, and that is the honest
statement of a gap rather than a design choice.** It adds no export, no ABI
bump and no manifest field — it adds a `CommandType`, a deadline and a
completion string. A v14 packaged from v13's wasm, or v10's, or the shipped
v8's, would satisfy all nine manifest declarations and ship the bug under a new
identity.

So the rule also greps the packaged `probe.wasm` for the completion literal
`verified-move-readback`, with `verified-caret-readback` as a positive control
run **first** — because "the fix is not in these bytes" and "the grep is not
looking at a wasm" are otherwise the same colour of red (the tree's own rule:
every "X did not happen" arm needs a positive control).

Measured on every artifact this tree holds, before the rule existed:

| profile | `verified-move-readback` | `verified-caret-readback` (control) |
|---|---|---|
| `e2-editor-v8` (shipped) | absent | PRESENT |
| `e2-editor-v10` | absent | PRESENT |
| `e2-editor-v12` | absent | PRESENT |
| `e2-editor-v13` | absent | PRESENT |

The assertion is red on all four and the control is green on all four. It is
also green/red at the object level, on the two scratch objects from §3:
`probe_engine.cpp` @ `ec3402bf` → red, @ HEAD → green. Pointed at a
`sdk-manifest.json` instead of a wasm, the control fires and says so. Cost:
0.01 s on 135 MB.

**What it does not cover, said plainly:** there is no equivalent literal for
option B's geometry. That code emits `,"x":`, `,"y":`, `,"width":`, `,"height":`
— fragments with no discriminating power — and every distinctive string in
`a11y_tree_probe.cpp` (`no-accessible`, `paragraphCount`) is present in v12's
pre-option-B wasm too, measured. Geometry is covered by the manifest's
`documentOutlineGeometry` declaration (the flag half) and by the product path's
41st check (the behaviour half); it is **not** covered by these bytes.

---

## 6. What is NOT validated, because the link was not run

Stated plainly, because the owner is about to run it.

1. **The link itself has never been executed.** Symbol resolution was measured
   as an undefined-set comparison against an object that did link. Archive
   member selection, `--wrap`, duplicate definitions and link order are all
   outside what that can see. If it fails, it fails at the owner's command.
2. **The `E2_V14_*` recipes have never run.** `make -n` says the graph is right
   (6 `em++`, every `-o` under `build/e2/e2-editor-v14/`, the guard present
   once, all seven packaging flags on the builder line); it does not say the
   commands succeed.
3. **The wasm literal assertion has never run on a real v14 `probe.wasm`**,
   because none exists. It ran on four real wasms (all red), on two real objects
   (one red, one green) and on a non-wasm (control red). String containment over
   a file the builder copies verbatim is what it is, but that is reasoning about
   the green case, not a run of it.
4. **The manifest assertions have never run on a real v14 manifest.** They ran
   on two real manifests (both red) and on one substituted manifest (green).
5. **The v13 flag census was not re-taken.** It is inherited. The builder takes
   the profile name as data; that is an argument, not a re-run.
6. **Wall clock is still unknown.** Unchanged from the v13 round: this tree has
   no record of how long a profile link takes and this work did not invent one.
   `probe.wasm` is 135 MB.
7. **The per-paragraph `getBounds()` cost is still unmeasured.**
8. **The four product `.o` and `a11y_tree_probe.o` have never been built in
   `build/e2/e2-editor-v14/`.** Only `probe_engine.cpp` was compiled here, and
   only into scratch.
9. **Nothing here says v14 is a good candidate.** Half A's acceptance is
   `probe_096_boundary_arrow.py` (prediction: `NOT_REPRODUCED`) and
   `probe_096_checkpoint_before_the_gesture.py` (prediction: the `with` arm
   reports `ENGINE_ANSWERED`, not `RECOVERED`), both written before the link and
   neither takeable until after it. Option B's acceptance is still
   `tools/probe_093_fix_shape_oracle.py`, which v13 already passed 3/3 — on v14
   it has to be re-earned, because the artifact is new.
