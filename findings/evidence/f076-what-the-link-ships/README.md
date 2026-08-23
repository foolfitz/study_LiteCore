# Finding 076's link — what it actually ships, measured

Taken 2026-08-24 with `wasm_sdk_probe/tools/what_the_link_ships.py --since eab775c`,
before the link, because a link mints a new identity and unbinds every verdict
that named the old one. "What changed" is the question the decision turns on.

`eab775c` is the commit `e2-editor-v4` was linked from, and `e2-editor-v7` —
the profile shipped until this link — is that same artifact under a wider
manifest.

## Result

`preprocessed-diff-since-eab775c.json`

| translation unit | verdict |
|---|---|
| `sdk_api.cpp` | preprocesses identically |
| `unoembind_stub.cpp` | preprocesses identically |
| `editor_api.cpp` | preprocesses identically |
| `probe_engine.cpp` | **two hunks** |

The two hunks in the engine:

1. `std::malloc(byteCount)` → `std::calloc(byteCount, 1)` for the tile pixel
   buffer — **finding 076**. `paintTile` draws only the page and `putImageData`
   blits the whole buffer, so uninitialised heap reached a canvas the user can
   screenshot.
2. An early return in `refreshCaretParagraph()` so `a11yParagraphFresh` is false
   on a build where no accessibility read can succeed —
   **`queue-fresh-is-true-where-no-read-can-succeed`**.

## And a third thing, which this tool missed on its first run

`sdk-worker.js` `e6ee92ca290b7966` → `070229cd10bda4a0`: **+93 lines, 21 of them
code.** The profile builder hashes *whichever worker is in the tree*, so a link
ships every accumulated worker change too — the v4 runbook already knew this
("finding 068's fix rides this link for free"), and this tool answered as if the
engine were the whole story until a dry packaging run showed `workerSha256`
moving under it.

**That is this file's own failure mode, one level in**: a confident answer to
half a question. The tool now compares the tree's worker against the one the
shipped profile carries, and separates comment lines from code so ninety lines
of rationale cannot be mistaken for ninety lines of forwarding.

What the 21 code lines do: forward `a11y.paragraphText` as `text` and
`a11y.outline` as `documentOutline`, plus `caretParagraph`/`documentOutline` on
two event payloads. All additive, all presence-guarded.

**Expected to be inert on this core, and that is a derivation, not a
measurement**: the product core emits neither field, so both project as `null`,
and v8's manifest declares neither `caretParagraphText` nor `documentOutline`, so
the page does not read them. The first run is where that gets checked.

## Why it was measured rather than read

Two cheaper answers were available and both are wrong:

* **Reading commit messages** answers about the repository, not the build. Since
  `eab775c`, `src/probe_engine.cpp` gained 153 lines across five commits, four
  of them accessibility work for a *different core*.
* **Reading the `#ifdef`s** is closer and still misses hunk 2. That fix is gated
  on a **runtime** flag, deliberately — its own comment says "this also covers
  the runtime cases (no document, LOK missing an entry point)" — so it sits
  behind no `OXSDK_A11Y_*` and does reach the product build.

Hunk 2 was found by the preprocessor and would have shipped unannounced. It is
wanted, and it is a second thing this link ships; the runbook says so rather than
calling this "the 076 link" and leaving a reader to discover the rest.

Deliberately **not** an object-file comparison: finding 032 recorded that
comparing object files is a coin flip, not an isolation check.

## Pre-link gates

`pre-link-gates.txt` — queue (0 drifted, P1 complete, nothing blocking),
`check_relink_queue --self-test`, `check_product_build_reaches` (`ok: true`),
the ABI header syntax check, `tests.test_e2_editor_v4_profile` (11 tests),
`editor-shell-v2` (83 tests). `test-e2-c-static`, `test-e2-b-static` and
`test-e2-c-reachability` all exit 0. Shell generation **v40**,
`d8720b8b7281a8cf`.

## The tool asserts its own configuration

`what_the_link_ships.py` re-reads `E2_V4_OBJECTS` and the product defines from
`make -pn` and reports `configurationDrift` if the Makefile has moved away from
what it measures. Without that it would go on preprocessing a configuration
nobody links and answer confidently about it — which is the failure this whole
directory exists to avoid one level up.
