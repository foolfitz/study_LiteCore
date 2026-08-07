---
name: emscripten-app-debug
description: >
  Debug a WebAssembly/Emscripten application that fails inside the browser —
  blank canvas, stuck loader, a dying pthread, an uncaught exception with only
  wasm-function[N] frames. Use when a wasm build loads but does not work, when
  the browser console needs to be captured programmatically, or when a hypothesis
  about a wasm app should be tested without paying for a rebuild. Covers the
  Playwright probe pattern, reading negative evidence from the network timeline,
  and editing packaged artifacts in place.
---

## Capture the console programmatically

Do not ask the user to copy from DevTools. Drive a headless browser and record
everything on one timeline — console, network, page errors, worker lifecycle —
then dump page state and a screenshot.

`tools/pw/probe.js` in this workspace implements this. Usage:

```bash
node probe.js <URL> [seconds] [screenshot-path]
```

Launch flags that matter:

```
--enable-features=SharedArrayBuffer
--use-gl=swiftshader --enable-unsafe-swiftshader   # headless has no real GPU
--no-sandbox
```

**Keep the wait short.** Startup failures happen within a couple of seconds.
20 s is plenty; 90 s just makes the user wait. Only extend when genuinely
waiting on a slow download.

## Read the network timeline for what did *not* happen

The most valuable line in a probe log is often a request that is missing.

A wasm app that fails at startup because its data package was never fetched
looks identical, on the console alone, to one that fetched it and then failed.
The network timeline separates them immediately. Check that every expected
artifact appears: the `.wasm`, the data package, its metadata, worker blobs.

Confirm the environment too, from page state rather than assumption:

```js
crossOriginIsolated          // false => COOP/COEP headers missing
typeof SharedArrayBuffer     // undefined => no threads
```

Serve with COOP/COEP set (`emrun` does this) or nothing threaded will work.

## Enumerate Module without tripping the guards

Emscripten installs getters on names that were **not** exported, which call
`abort()` when read — touching one kills the instance and ends the session.
Inspect with descriptors instead of reading values:

```js
const d = Object.getOwnPropertyDescriptor(Module, name);
d ? (d.get ? 'getter (likely unexported guard)' : typeof d.value) : 'absent';
```

A `getter` result means that name is **not** in `EXPORTED_RUNTIME_METHODS`. This
is how to find out whether `FS`, `callMain`, `ccall` and friends are actually
available before writing JS that depends on them.

## Experiments that need no rebuild

A wasm rebuild can cost hours. Try these first:

**Startup arguments.** Copy the loader HTML, add one line before the module is
instantiated:

```js
Module.arguments = ["--writer", "--norestore"];
```

Keep the original untouched and serve the copy — cache is then a non-issue too.

**Remove files from the virtual filesystem.** When the file packager is used with
separate metadata, the manifest is fetched at runtime. Drop entries from its
`files` array and those files simply are not registered. The blob is untouched,
so any size check still passes. Good for testing "is this data causing it?".

**Edit a text file inside the data blob.** Look up the entry's `start`/`end`
offsets in the metadata, then replace bytes **keeping the length identical** so
every other offset stays valid. Pad or choose an equal-length substitute. Back
the blob up first. Good for configuration baked into the package.

## Reading a stack with no symbols

`wasm-function[177251]` means the binary has no name section. Verify before
assuming — walk the wasm custom sections and look for `name`. A build with debug
info will have one (and typically a separate `.debug.wasm` alongside).

If there is no name section, the options are: rebuild with debug info (possibly
for a single target only — see `build-variable-bisect`), or reason from what the
runtime *does* print. Thread names, subsystem log lines and the failing worker's
identity often narrow it to a module without any symbols at all.

Exception messages do not survive crossing a worker boundary: the `ErrorEvent`
reaching the main thread does not carry the original `WebAssembly.Exception`, so
`getExceptionMessage` is unavailable there even when the helper is exported.

## Toolchain hygiene

A distro-packaged Emscripten in `PATH` will shadow the SDK the project was built
with, and the versions will not match. Always source the project's `emsdk_env.sh`
before any `emcc` / `emrun` / `em++` invocation, and verify with
`which emrun` when something behaves unexpectedly.

Check what the build actually used — the generated config will name the compiler
paths. Do this before spending time on a mismatch hypothesis; it is cheap and
rules out a whole class of confusion.
