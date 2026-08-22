# A11y gate 0 — prepared, not run (2026-08-21)

Everything here is **ready for the user's hands**. Nothing in it has been
executed: the core rebuild is the user's scope (`user-handles-core-rebuilds`).

Roadmap §3.3 puts one question at this gate, and only one:

> **LOK 在 WASM 上吐不吐得出 focused paragraph？**
> 吐得出來 → 進 §3.4。吐不出來 → **停。**

Three things are prepared, in the order they must be used:

1. `PATCH.md` — the `configure.ac` change, with the direction chosen and why.
2. `PREDICTION.md` — **the pass/fail criterion, written before the result.**
3. `probe_a11y_gate0.py` (in `wasm_sdk_probe/tools/`) — the probe that asks the
   question.

## Read PREDICTION.md before running anything

Not a formality. The whole reason a11y was pulled forward to before M2a is that
this question **has never been measured** — finding 056 proved it does not work
*today*, not that it cannot work *after the configuration is fixed*. A threshold
written after seeing the output is not a threshold.

## What must NOT be done

**Adding `calc` back to `--with-wasm-module` is not the fix.** Finding 057
already rejected it: the objects get compiled in, the call sites are still
removed by the C++ macro, and the trade is size for nothing.

## Order

```
1. read PREDICTION.md
2. apply PATCH.md to libreoffice-26-8/configure.ac
3. archive the current build first  (wasm-build-not-reproducible)
4. lift the read-only protection
5. rebuild core                      <- the user's hours, not mine
6. rebuild the probe profile
7. run probe_a11y_gate0.py
8. compare against PREDICTION.md, and only then decide
```

Steps 3–5 are the user's. Everything else is mine and can be done in one round
once the build exists.
