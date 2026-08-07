---
name: build-variable-bisect
description: >
  Isolate which build option causes a behavioural difference, when each build
  takes hours. Use when a project builds fine one way and misbehaves another —
  a custom or reduced configuration crashes while the default works, a release
  build differs from a debug build, one machine's build differs from CI's — and
  the configuration has many options so guessing is expensive. Covers ordering
  experiments by rebuild cost, diffing resolved configuration rather than input
  flags, and finding experiments that need no rebuild at all.
---

The naive approach — flip one flag, rebuild, repeat — costs hours per iteration
and often tests the wrong flags first. Three moves cut that down.

## 1. Establish a known-good reference first

Build the project's **own default / documented configuration**, unmodified. Until
that is known to work, there is nothing to bisect against, and the problem might
not be the configuration at all.

Keep that build directory. Do not reconfigure it later to save disk — it is the
only fixed point in the search.

## 2. Diff the *resolved* configuration, not the input flags

Input flags are misleading: many are no-ops on a given platform because the
build system already defaults them, or because another option implies them.

Compare whatever the build system writes out after configuring — the generated
config makefile, header, or cache:

```bash
diff <(grep '^export ' A/config_host.mk | sort) \
     <(grep '^export ' B/config_host.mk | sort) \
  | grep -E '^[<>]' | grep -vE 'SRCDIR|BUILDDIR|WORKDIR|PATH='
```

Filter out path variables, which differ trivially between build directories.

This routinely collapses a 30-flag difference to 3 or 4 real variables. It also
tells the user something worth knowing: **most of the flags they carefully chose
had no effect at all.** Say so — it changes what they maintain going forward.

## 3. Order experiments by rebuild cost, not by likelihood

With hours per build, a cheap experiment that is probably not the cause beats an
expensive one that probably is. Estimate cost first:

| change | cost |
|---|---|
| removes code from the build | cheap — nothing new to compile |
| affects only packaging, resources, product naming | cheap — mostly relink |
| adds code to the build | expensive |
| changes compile flags for everything (`-g`, optimisation, sanitisers) | expensive — cache miss on every object |

Exploit the compiler cache: a variant that changes no compile flags will hit
cache on almost every object, so the real cost is just the link.

**Bisect forward from the known-good build**, adding the suspect options, rather
than backward from the broken one. Keeping debug info enabled the whole way
means a symbolised stack the moment the failure reproduces.

If the build system supports **per-target** granularity for an expensive option
(debug info for one executable rather than all of it), use it. That can turn a
full rebuild into a relink while still isolating the variable — and it also
discriminates between "this option's effect on the code" and "this option's
effect on the final link".

## 4. Before any rebuild, look for a no-rebuild experiment

Often the hypothesis can be tested by editing an artifact:

- a **manifest or index** read at runtime — remove entries to simulate absent files
- a **text file inside a packed blob** — replace in place, padding to keep the
  byte length identical so offsets stay valid
- **runtime configuration** — startup arguments, environment, a copy of the entry
  point with one line added

Each of these costs minutes and can eliminate a whole class of hypotheses. Today's
value: three hypotheses eliminated without a single rebuild.

## Recording the result

Keep a matrix as you go — it is the core of any eventual bug report:

```
build dir     configuration                         result
------------  ------------------------------------  ------
build         custom flags                          CRASH
build-stock   project default                       ok
build-t1      + suspect A                           ok
build-t2      + suspect B                           ok
build-t3      custom flags, only suspect C changed  ok      <- decisive
```

State explicitly why the decisive run is decisive: which variable it isolates,
and what was held identical (ideally: byte-identical object files, via cache).

## Reporting caution

Isolating the variable is not the same as knowing the mechanism. Distinguish:

- **verified** — same inputs except X, different outcome
- **inferred** — *why* X causes it

Report the first as fact and label the second a hypothesis. Maintainers can
usually confirm or replace the mechanism quickly once the isolation is solid;
an overconfident wrong mechanism costs credibility.
