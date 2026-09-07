# Finding 093, option B, step 4 — the build-and-link rule

Written 2026-09-08. **Nothing was linked.** No `probe.wasm` was produced, no
`dist/profiles/**` byte was written, no core was rebuilt. What this directory
records is a Makefile rule and the measurements that say it will work, taken
without walking through the one-way door.

The rule itself is in `wasm_sdk_probe/Makefile`, the `E2_V13_*` block.

---

## 1. Why there was no rule to begin with

`handoff/RUNBOOK-operator-093-engine-geometry.md` §5 step 4 told the owner to
run `make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v13/sdk-manifest.json`.
That target had no rule. The reason is deeper than an oversight:

**v9, v11 and v12 were never linked.** Each is a REPACKAGING of an already
archived artifact under different flags, a different worker and a different
manifest:

| profile | its rule consumes | links? |
|---|---|---|
| `e2-editor-v9` | `$(A11Y_CALLOC_ARCHIVE)/probe.js`, `/probe.wasm` | no |
| `e2-editor-v11` | `$(E2_V10_ARCHIVE)/probe.js`, `/probe.wasm` | no |
| `e2-editor-v12` | no Makefile rule at all — the builder was invoked by hand | no |
| `e2-editor-v10` | its own `.o` files | **yes** |

That is why `dist/profiles/e2-editor-v12/probe.wasm` and
`dist/profiles/e2-editor-v10/probe.wasm` are the same bytes,
`4ec1e389aaab3b03…` — verified again here, see §4.

Option B changed `src/a11y_tree_probe.cpp`. For the first time on this lineage
since v10, the bytes have to be **made**, not carried across. So the missing
piece was never a target name; it was a whole compile-and-link chain.

---

## 2. No core rebuild is needed — measured, not reasoned

The runbook's §1 concluded this and its §1.2(d) argument was corrected in step 3
(`new-undefined-symbols.txt`). Both the conclusion and the correction were
re-verified here independently, and one measurement was added that neither had:
a **control**.

### 2.1 The four new symbols are defined on the link line

```
$ llvm-nm-19 --defined-only wasm-lite/build-a11y-gate0/instdir/program/libvcllo.a
  _ZN3vcl6Window9GetOutDevEv                                        T
  _ZN7MapModeC1E7MapUnit                                            T
  _ZN7MapModeD1Ev                                                   T
  _ZNK12OutputDevice12PixelToLogicERKN5tools9RectangleERK7MapMode   T
```

and `-lvcllo`, `-lcomphelper` and `-lswlo` are each on `soffice.js.linkdeps`
(207 `-l` entries, 172 distinct). `comphelper::OAccessible::getBounds()` and
`SwAccessibleContext::implGetBounds()` are `T` in their archives as the runbook
said.

### 2.2 The control: the unresolved set does not change

Counting the four new symbols only says the change *adds* things that resolve.
It does not say the TU as a whole links. So both versions of the TU were
compiled to an object **in scratch** with the exact flags the new rule uses —

```
em++ -DLOK_USE_UNSTABLE_API -I../libreoffice-26-8/include \
     -I../wasm-lite/build-a11y-gate0/config_host \
     -I.../UnoApiHeadersTarget/udkapi/comprehensive \
     -I.../UnoApiHeadersTarget/offapi/comprehensive \
     -I.../UnpackedTarball/boost \
     -Oz -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm \
     -std=c++20 -DLIBO_INTERNAL_ONLY -c src/a11y_tree_probe.cpp -o <scratch>.o
```

— their undefined symbols set-differenced against the defined symbols of **all
170 archives the link line resolves to** (every `-l` except `dl` and `m`, which
are emscripten builtins):

| | undefined in the TU | not defined in any archive on the link line |
|---|---|---|
| before `c2a7abad` | 72 | **44** |
| after (HEAD) | 76 | **44** |

The remainder is **identical**, and it is 44 libc / libc++ / libc++abi /
emscripten-runtime symbols (`malloc`, `strlen`, `__cxa_throw`,
`std::__2::basic_ostream…`, `__stack_pointer`, …) supplied by the sysroot.

**The control is the whole argument.** Those same 44 were already unresolved for
the version of this TU that *did* link successfully into `e2-editor-v10`. So the
change adds nothing the link cannot resolve, and that statement does not depend
on my classifying any symbol by eye.

Data: `symbol-resolution.txt`.

### 2.3 The TU compiles

1.3 s, clean, no warnings surfaced, 89,679-byte object. The geometry call needs
no new compile flag: `vcl/window.hxx` and `vcl/outdev.hxx` live under
`$(LOSRC)/include`, which `E2_V5_CPPFLAGS` already carries. Measured by
compiling it, not read off the include list.

---

## 3. What the link would ship, and the gap in the instrument

`what_the_link_ships.py --variant a11y --since e18429eb` (the commit v10's
artifact was linked from):

```
since e18429eb: 4 unit(s) preprocess identically, 0 changed
  same     sdk_api
  same     probe_engine
  same     unoembind_stub
  same     editor_api
  CHANGED  sdk-worker.js 03f5b69a002895a9 -> 6e75829a2911c1df (+23/-0 lines, 4 of them code)
      + x: typeof p.x === "number" ? p.x : null,
      + y: typeof p.y === "number" ? p.y : null,
      + width: typeof p.width === "number" ? p.width : null,
      + height: typeof p.height === "number" ? p.height : null,
```

So v13 is one variable against v12: the four product translation units are
unchanged, and the worker moves by exactly the four allowlist fields option B
added.

**Read the gap in that sentence.** That instrument lists four units and
deliberately does not preprocess the fifth — `"notPreprocessed":
["a11y_tree_probe"]`, its own word, `tools/what_the_link_ships.py:95`. That TU is
precisely what option B changes. So the only unit that moved is the one the
single-variable instrument does not look at, and the one-variable claim rests on
the source diff of `c2a7abad` rather than on this tool. Said here rather than
left to be discovered later.

A second-order note on the same measurement: `e18429eb` is timestamped
2026-08-26 21:31:46, twenty-eight minutes **after** v10's `probe.wasm` mtime
(Aug 26 21:03). That ordering is consistent with the artifact having been linked
from the working tree and committed afterwards, which is what the Makefile
comment on `E2_V10_*` asserts it carries. It is consistent with, not proof of.

---

## 4. Nothing existing moved — before/after, not an assertion

### 4.1 The hazard being tested

Finding 042: `Makefile` is a prerequisite of every `.o`, so a Makefile edit for
one profile makes every other profile's objects out of date, and a relink is a
new artifact because the wasm hash is not a function of the source (finding
036). Editing the Makefile is exactly what this work does.

### 4.2 The baseline was already dirty, and that has to be said first

The task's success condition was "`make -n` for the existing profile targets
must show no compile or link". **That was already false before this edit**, and
pretending otherwise would have hidden it. Measured before touching anything,
16 existing targets:

```
build/e2/a11y-calloc/probe.js                    em++ = 6   guard = 1
build/e2/combination/probe.js                    em++ = 6   guard = 1
build/e2/e2-editor-v10/probe.js                  em++ = 6   guard = 1
build/e2/editor-v4/probe.js                      em++ = 5   guard = 1
build/e2/editor-v5/probe.js                      em++ = 6   guard = 1
build/e2/editor-v8/probe.js                      em++ = 5   guard = 1
build/e2/format-discovery/probe.js               em++ = 5   guard = 1
dist/profiles/a11y-calloc/sdk-manifest.json      em++ = 6   guard = 1
dist/profiles/e2-combination/sdk-manifest.json   em++ = 6   guard = 1
dist/profiles/e2-editor-v10/sdk-manifest.json    em++ = 6   guard = 1
dist/profiles/e2-editor-v2/sdk-manifest.json     em++ = 5   guard = 1
dist/profiles/e2-editor-v4/sdk-manifest.json     em++ = 5   guard = 1
dist/profiles/e2-editor-v8/sdk-manifest.json     em++ = 5   guard = 1
dist/profiles/e2-editor-v5/sdk-manifest.json     nothing to be done
dist/profiles/e2-editor-v9/sdk-manifest.json     repackage only, no em++
dist/profiles/e2-editor-v11/sdk-manifest.json    repackage only, no em++
```

Every `.o` in this tree has been out of date for a long time, because the
Makefile has been edited many times since those artifacts were minted. That is
042's edge sitting there permanently, not something this edit created. **What
holds the artifacts still is not make's dependency graph; it is
`refuse_unasked_relink`, which is present in all seven link recipes (guard = 1
above) and aborts before `em++` runs.**

### 4.3 The property this edit actually has

Both measurements taken before the edit and again after it, same commands:

**`make -n` for all 16 targets is byte-identical.**

```
bytes  79054 == 79054
sha256 df09482c48b21946314c15db3f09d998… == df09482c48b21946314c15db3f09d998…
```

**All 316 files under `dist/profiles/` and `build/e2/` are byte-identical.**
The full sha256 listing is `artifacts-unchanged.sha256`; `diff` of the before
and after listings is empty. Spot check, quoted from the after listing:

```
4ec1e389aaab3b03  build/e2/e2-editor-v10/probe.wasm
4ec1e389aaab3b03  dist/profiles/e2-editor-v10/probe.wasm
d57de339939bfbc9  dist/profiles/e2-editor-v10/sdk-manifest.json
4ec1e389aaab3b03  dist/profiles/e2-editor-v12/probe.wasm
2734229351dac1da  dist/profiles/e2-editor-v12/sdk-manifest.json
4a2710bba1ef07d9  dist/profiles/e2-editor-v8/probe.wasm
d70481cb1be5b1f9  dist/profiles/e2-editor-v8/sdk-manifest.json
```

Those match the archive directory names `e2-editor-v10-4ec1e389-…-manifest-d57de339`,
`e2-editor-v12-4ec1e389-…-manifest-27342293` and
`e2-editor-v8-4a2710bb-…-manifest-d70481cb`, and the v10 = v12 wasm identity is
re-confirmed as a hash rather than inherited from the shared name prefix.

To reproduce:

```
find dist/profiles build/e2 -type f -print0 | sort -z \
  | xargs -0 -P 8 -n 40 sha256sum | sort -k2
```

---

## 5. The red cases

Green from a checker you wrote yourself only proves the checker returns green
(AGENTS.md §6). Both guards this rule leans on were made to go red first.

### 5.1 The relink guard fires, and it fires before any compiler runs

`make --always-make -n <link target>` prints the recipe make WOULD run, fully
expanded, without running it. The guard's own line was extracted from that
output and **executed** — the executed text was checked to contain zero `em++`
lines first, so nothing could have compiled or linked:

| link target | `ALLOW_FROZEN_RELINK` unset | `ALLOW_FROZEN_RELINK=1` |
|---|---|---|
| `build/e2/e2-editor-v10/probe.js` (frozen candidate) | **exit 1, refused** | exit 0, proceeds |
| `build/e2/editor-v8/probe.js` (the SHIPPED product) | **exit 1, refused** | exit 0, proceeds |
| `build/e2/e2-editor-v13/probe.js` (this rule, new) | **exit 1, refused** | exit 0, proceeds |

The refusal, verbatim, for v10:

```
refusing to relink a frozen profile: build/e2/e2-editor-v10/probe.js
it carries: the a11y product candidate carrying finding 082's fix -- every link mints a new hash and five identities bind to one
a new link mints a new artifact and unbinds that (findings 027, 036).
if that is really what you want:  make ALLOW_FROZEN_RELINK=1 build/e2/e2-editor-v10/probe.js
```

v10's `probe.js` and `probe.wasm` were re-hashed after that execution and are
unchanged (`96f18d0c1f6b9b11`, `4ec1e389aaab3b03`).

The v13 rule carries the same guard on its first link, when nothing frozen
exists yet. That is deliberate: the second link of that name would be a relink,
and a guard you can forget to add later is not a guard.

`make test-e1-c-frozen-guard` — the tree's existing, mtime-independent assertion
of this same property — still passes after the edit.

### 5.2 Every packaging flag has a red case

See `FLAG-CENSUS.md`. Nine cases run through the real builder, one flag dropped
at a time, all red; the full line green. That census is what corrected a broken
assertion of mine before it shipped — see §6.

### 5.3 A failing assertion has to remove the manifest, and that was measured too

This Makefile does not set `.DELETE_ON_ERROR`, so GNU make leaves behind a
target whose recipe wrote it and then failed. A narrowed `sdk-manifest.json`
left on disk is **newer than its prerequisites**, so the next `make` reports it
up to date and hands over the narrowed profile without running the check again —
the exact failure the check exists to catch, reappearing one level up.

Demonstrated in a scratch Makefile of the same shape:

```
=== WITHOUT the rm ===
   ASSERTION RED
make: *** [out/manifest.json] Error 1
   retry:  make: 'out/manifest.json' is up to date.
   on disk: {"narrowed": true}          <- narrowed manifest survives, silently

=== WITH the rm, as the rule now has it ===
   retry:  ASSERTION RED                <- the builder really re-runs
   on disk: 0 files
```

So the recipe ends `|| { rm -f …/sdk-manifest.json; exit 1; }`. That `rm` is
load-bearing, not tidiness, and the comment in the Makefile says so.

---

## 6. What the census caught in my own work

The first assertion I wrote for `--inline-range-gestures all` was
`grep "range-cross"`. It has **zero discriminating power**: the paragraph
actions carry `range-cross` unconditionally and `gestureBits` names it, so it is
present in the manifest even with the flag dropped. The census showed
`drop-gestures` coming out green.

Replaced with `"inlineRangeEvidence"`, which is emitted for `all` alone and
separates it from both `none` and the narrower `range-single` — the latter
matters, because `range-single` is a *plausible* wrong value, not an absurd one.

Second thing the census caught: the pack **names** cannot say which core image
was sliced. Packaging against the product core still produces
`./base-e2-editor-v13.<something>.data` and sails past every name-shaped
assertion. Measured: it comes out `ba15a988a7fec468` instead of
`9901e9be29c9ded2`. The bare hash literal in the checker exists for that alone.

Both are instances of the same thing this tree keeps writing down: asking "is
this claim true" gets you yes; asking "what would go red if it stopped being
true" gets you the hole.

---

## 7. What is NOT validated, because the link was not run

Stated plainly, because the owner is about to run it.

1. **The link itself has never been executed.** Symbol resolution was checked as
   a set difference over archive indexes, not by `wasm-ld`. Archive member
   selection, `--wrap`, duplicate definitions across archives and link order are
   all outside what this measurement can see. If it fails, it fails at the
   owner's command.
2. **Wall clock is still unknown.** The runbook §4(a) said the tree has no record
   of how long a profile link takes and declined to invent one. That is still
   true; this work added nothing to it. `probe.wasm` is 135 MB.
3. **The per-paragraph `getBounds()` cost is still unmeasured.** Runbook §7
   point 3. Step 1 measured coordinates, not time; this step measured neither.
4. **The four product `.o` files have never been built in
   `build/e2/e2-editor-v13/`.** Only `a11y_tree_probe.cpp` was compiled here, and
   only into scratch. The other four use v10's flags verbatim and their sources
   preprocess identically to v10's (§3), but "identical flags and identical
   preprocessed source" is an argument, not a compile.
5. **The manifest assertions have never run on a real v13 manifest**, only on
   nine manifests built in scratch from v10's archived artifact. They are string
   containment over the builder's own output, so the artifact behind it does not
   change what they test — but that is reasoning, not a run.
6. **Nothing here says v13 is a good candidate.** Acceptance is still
   `tools/probe_093_fix_shape_oracle.py` against `ORACLE-fix-shape.md`, two arms
   3/3 on the 133-paragraph document, and it cannot be taken before the link.
