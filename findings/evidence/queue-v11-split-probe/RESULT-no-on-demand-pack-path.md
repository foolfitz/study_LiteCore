# `loadAtStartup: false` means never loaded — measured 2026-08-29

Found while checking the **premise** of B-2 criterion 3, not while running it.

## The claim, and why it gets a census

> `loadAtStartup: false` means never loaded, by anything, in every version this
> tree has shipped.

That is a universal claim, so it carries a rerunnable census rather than a
sentence: `probe_no_on_demand_pack_path.py`, run from the repository root.

```
workers scanned                     26   (live + every archive)
workers with other than 2 hits       0
the single call is the guarded one   yes
callers outside the worker           0    (100 files searched)
verdict                              CONFIRMED
```

`loadResourcePack()` (`sdk/sdk-worker.js:557`) has exactly one caller:
`loadStartupResourcePacks()` at line 620, guarded on `loadAtStartup === true`,
itself called once from `handleInit` at line 1085. `web/e2-editor-app.js` and
`sdk/document-sdk.js` contain **zero** occurrences of `resourcePack`. Every
archived worker back to `e2-editor-v2` — including `e2-editor-v8`'s own — has
the same two occurrences.

**The census asserts its own non-vacuity**: it fails if a named surface
directory is missing (a renamed surface would otherwise make "zero callers"
true by searching nothing) and if fewer than 20 files were read outside the
worker. A census reports zero whether it looked or not; that is the failure
mode it has and a spot-check does not.

## What it means

`e2-editor-v8`'s `fallback-fonts-r5` — 46.8 MiB, `loadAtStartup: false` — is
declared in its manifest and **has never been fetched by the editor**. There is
no demand that fetches it. The word in the plan's table is "on demand"; the
behaviour is absence.

* **The arithmetic is unaffected.** v8's required-before-usable of 161.4 MiB is
  correct precisely *because* the pack is not fetched at startup. That figure
  never depended on it being fetched later.
* **The trade changes.** Splitting v11's image does not create a lazy path — it
  creates the same absence v8 has. The split's real terms are −46.8 MiB at
  startup **in exchange for those fonts no longer being in the filesystem at
  all**, which is a limitation the shipping product already has.
* **Unsplit v11 has an uncounted benefit.** Its image carries the complex-script
  and fidelity fallback fonts that v8's client never receives.

## Explicitly not measured

What either profile *does* with a document needing one of those fonts —
substitute silently, draw boxes, something else — is **unmeasured**. The claim
here is about the filesystem (present in v11's image, absent from v8's client),
not about rendering. Nothing in this file may be quoted as a rendering result.

## Consequence for the gate

B-2 criterion 3's second half — "opening a document that requires a fallback
font triggers the pack fetch and renders it" — is unsatisfiable on **every**
profile, v8 included. The criterion was fixed before the probe and is not being
rewritten here; it has been referred back for adjudication, together with
whether the `loadAtStartup: false` wording should be filed as a finding.

The premise came from this side: the D-4 ticket and addendum part 1 §A-3 both
said v8 "defers a 46.8 MB font pack to on demand", taken from the plan's own
table without checking it.
