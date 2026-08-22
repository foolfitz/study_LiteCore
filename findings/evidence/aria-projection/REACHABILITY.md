# Can the engine reach the accessibility object itself? Measured 2026-08-23: **yes**

`research/DESIGN-2026-08-22-aria-projection.md` §9 said: do not start building
until this is measured. It is now measured, and it needed no rebuild — the
gate core was already on disk.

## The question

LOK's focused-paragraph payload has exactly five fields — `content`,
`position`, `start`, `end`, `listPrefixLength`
(`sfx2/source/view/viewsh.cxx:862-873`). **No role, no outline level, no list
nesting, no ordinal.** WCAG 2.1 **1.3.1 is Level A** and wants headings to be
headings, so option (i) was: go past LOK to the accessibility object, where
role is an *enum* (`AccessibleRole::HEADING`) and outline level is a UNO
property — the same place `getListPrefixSize()` already queries
`UNO_NAME_NUMBERING_LEVEL` from.

## What was tried, and what each failure said

`reachability-probe.cpp` in this directory: `SfxViewShell::Current()` →
`GetWindow()` → `GetAccessible()` → `getAccessibleContext()` →
`getAccessibleRole()`.

| attempt | result | what it meant |
|---|---|---|
| engine's own flags | `std::cmp_equal` not found | **a flag, not a wall** — core is C++20, the engine had no `-std` |
| `+ -std=c++20` | `unknown type name 'OUString'` | core headers want the internal-build define |
| `+ -DLIBO_INTERNAL_ONLY` | `rtl::Reference<comphelper::OAccessible>` mismatch | **my probe's bug**, not the tree's: `GetAccessible()` does not return `css::uno::Reference<XAccessible>` |
| type fixed | **compiles, object produced** | headers are usable from the engine |

Recorded as steps because each one looked like a wall and was a flag. Stopping
at the first would have reported "unreachable" about a reachable thing.

## Then the link question, asked of the archives rather than by linking

`llvm-nm --undefined-only` on the object, each symbol looked up across the
**310 archives on `soffice.js.linkdeps`**:

```
SfxViewShell::Current()                            libsfxlo.a
vcl::Window::GetAccessible(bool)                   libvcllo.a
comphelper::OAccessible::getAccessibleContext()    libcomphelper.a
```

All three are already on the link line. **Option (i) is reachable — compile and
link both.**

## The cost, named rather than discovered later

* **`-DLIBO_INTERNAL_ONLY` is a different contract with core.** It is how core
  compiles *itself*; these are internal APIs with no stability promise across
  releases. `SfxViewShell::Current()` and `vcl::Window::GetAccessible()` can
  change in 26.9 with no deprecation, and nothing in LOK's compatibility story
  covers them.
* **It must not be applied to the whole engine.** The existing translation
  units are a LOK client and see core through the public headers; flipping that
  define changes what those headers present. The shape that follows is a
  **separate translation unit** compiled with `-std=c++20
  -DLIBO_INTERNAL_ONLY`, exposing a narrow C interface to the rest of the
  engine — the internal-API dependency quarantined in one file, nameable in one
  place, and removable in one place.
* ⇒ (i) is the **bridge**, not the destination. The destination is (ii),
  upstream adding role/level to LOK's payload, at which point the quarantined
  file is deleted rather than maintained. Upstream submission is on hold since
  2026-08-15; that does not change which one is the end state.

## What this does NOT answer

Whether the accessible object reached this way actually reports the *focused
paragraph's* role, as opposed to the edit window's. The chain above stops at
the window's own accessible context. Getting from there to the focused
paragraph is the next question, and it is a different one — the window's
accessible is a tree, and `LOKDocumentFocusListener` walks it by listening
rather than by descending.

**No estimate of that is recorded here on purpose.** This file measured
reachability; guessing the rest of the walk would be the "shape looks light"
impression this tree already has a rule about.
