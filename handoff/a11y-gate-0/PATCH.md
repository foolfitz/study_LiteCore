# The `configure.ac` patch for a11y gate 0

Target: `libreoffice-26-8/configure.ac`, core at `671c848b1bb8` (unmodified
upstream). Finding 057 named two directions; this picks one and says why.

## The defect, restated

`ENABLE_WASM_STRIP_ACCESSIBILITY` has **two independent existences that answer
to different inputs** (finding 057, exhaustive read — the symbol appears exactly
5 times in `configure.ac`):

| | decides | driven by |
|---|---|---|
| Make variable | whether the accessibility **objects** are compiled | `--with-wasm-module` (`:4372/4379/4386`) |
| C++ macro | whether the **call sites** are compiled | `--enable-wasm-strip` (`:3498`) |

Nothing synchronises them. And `:1280` assigns `enable_wasm_strip=yes`
**unconditionally** on Emscripten, so `--disable-wasm-strip` on the command line
is overridden. Hence 057's conclusion: **on 26.8's Emscripten no flag
combination makes Writer's LOK accessibility work.**

The call site that matters (`sw/source/uibase/docvw/edtwin.cxx:6532-6542`),
verified in the tree:

```cpp
rtl::Reference<comphelper::OAccessible> SwEditWin::CreateAccessible()
{
#if !ENABLE_WASM_STRIP_ACCESSIBILITY
    SolarMutexGuard aGuard;
    SwWrtShell *pSh = m_rView.GetWrtShellPtr();
    if( pSh )
        return pSh->CreateAccessible();
#endif
    return {};
}
```

## Direction chosen: **make the macro follow the module decision**

Not the other one. Reasons:

* **Blast radius.** Making `:1280` respect an explicit `--disable-wasm-strip`
  would change `enable_wasm_strip` for the *whole* block at `:3458` — avmedia,
  libcmis, coinmp, cups, fonts, and every other `AC_DEFINE(ENABLE_WASM_STRIP_*)`.
  That is a different, much larger change, and it is not the defect 057
  describes.
* **It fixes the actual defect.** 057's defect is *two halves, two inputs*. This
  gives them one input. After it, `--with-wasm-module 'writer calc'` means what
  the configure help says it means.
* **It is inert for everyone else.** With the default `--with-wasm-module`, the
  Make variable is `TRUE` and the macro is defined exactly as today.

### The ordering problem, and why the patch is shaped this way

`AC_DEFINE(ENABLE_WASM_STRIP_ACCESSIBILITY)` is at **`:3498`**, and the module
loop that sets the Make variable is at **`:4371-4392`** — *later*. So the
conditional cannot simply be wrapped around `:3498`: the variable does not have
its value yet. **The `AC_DEFINE` has to move after the loop.**

This is the kind of detail that makes a patch either work or waste a rebuild, so
it is stated rather than left to be discovered.

## The patch

**Step 1** — at `configure.ac:3498`, remove the unconditional define:

```diff
     dnl AC_DEFINE sets the value to 1 (TRUE) in the C++ header.
-    AC_DEFINE(ENABLE_WASM_STRIP_ACCESSIBILITY)
 #    AC_DEFINE(ENABLE_WASM_STRIP_CHART)
     AC_DEFINE(ENABLE_WASM_STRIP_EXTRA)
```

**Step 2** — after the module loop closes and before
`AC_SUBST(ENABLE_WASM_STRIP_ACCESSIBILITY)` at `:4413`, add:

```diff
 AC_SUBST(ENABLE_WASM_STRIP_CALC)
+
+dnl The C++ macro and the Make variable must answer to the SAME input.
+dnl Before this, the macro was defined at the top of the enable_wasm_strip
+dnl block while the variable was decided here by --with-wasm-module, so a
+dnl build could compile the accessibility objects in and still have every
+dnl call site removed by the macro -- size without capability.
+if test -n "$ENABLE_WASM_STRIP_ACCESSIBILITY"; then
+    AC_DEFINE(ENABLE_WASM_STRIP_ACCESSIBILITY)
+fi
 AC_SUBST(ENABLE_WASM_STRIP_ACCESSIBILITY)
```

`ENABLE_WASM_STRIP_ACCESSIBILITY` is `TRUE` or empty (`:4372` sets it, `:4379`
and `:4386` clear it), so `test -n` is the right test and matches how
`:4393` already tests `ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS`.

## Configure invocation for the gate build

The point is a Writer build whose accessibility call sites are **compiled in**.
With the patch, that is any `--with-wasm-module` value that clears the variable.
`calc` and `impress` both clear it; `impress` also drags in Basic + Draw + Math
(roadmap §6.4), so:

```
--with-wasm-module='writer calc'
```

**This is not "add calc back" as the fix.** 057 rejected that *on its own*,
because without the patch it only compiles objects in. Here `calc` is the lever
that clears the variable, and **the patch is what makes clearing it mean
something.** If that coupling is judged unacceptable, the alternative is to give
the module loop a way to say "writer, with accessibility" — a bigger upstream
change, and not needed to answer gate 0.

## As applied, 2026-08-22 — one deviation, recorded

The patch above is what was applied, with one difference in step 1: instead of
deleting the `AC_DEFINE` line and leaving nothing, three `dnl` lines take its
place saying the define now happens after `--with-wasm-module` is parsed.
`:3498` is where a reader looks for it, and a silent absence there is how this
defect got built in the first place. No behavioural difference — `dnl` is a
comment.

Validated before the rebuild, by running `autoconf` on the patched
`configure.ac` and reading the generated script: exactly one
`printf "#define ENABLE_WASM_STRIP_ACCESSIBILITY 1" >>confdefs.h`, and it sits
inside `if test -n "$ENABLE_WASM_STRIP_ACCESSIBILITY"; then`, after the module
loop. The old unconditional write is gone. That is the whole patch, checked for
about a second's cost instead of an hour's.

Snapshot: `wasm-lite/patches/libreoffice-26.8-wasm-strip-accessibility-single-input.patch`,
listed in that directory's `INVENTORY.md` with the per-configuration behaviour
it changes.

## Cost and risk

* **Cost**: one core rebuild (the user's hours). The patch itself is ~6 lines.
* **Size**: `sw/source/core/access/` is 53 files. It moves the size baseline,
  which is why roadmap §3.2 rates that as the *weak* reason for the ordering.
* **Risk of the patch being wrong**: low, and it is falsifiable before the
  rebuild finishes — `config_wasm_strip.h` in the build directory must show
  `ENABLE_WASM_STRIP_ACCESSIBILITY` as `0`/undefined. **Check that before
  waiting for the whole build.**

## Upstream

This is an upstream defect (finding 057, `是上游: 是`). Submission is on hold
since 2026-08-15; when it reopens, this patch is the fix to propose, and 057 is
the report.
