# Finding 065 — the shipped runner's own evidence (2026-08-21), **and finding 065 is retracted**

> **Retracted 2026-08-22.** These two files record
> `formatting-survives-the-next-paragraph-break` failing on both browsers. That
> red was a **false negative** in `inline_styles_of()`, which could not see
> formatting carried on a paragraph's own automatic style. With the oracle
> fixed the same check **passes** on both browsers and the declaration came off
> `KNOWN_RED`. They are kept because they are the before-picture of a
> measurement error, and because points 2 and 3 below were and remain true.

These two are **not** diagnostic runs. They are `run_e2_c_product_path.py`
against the **shipped** `dist/` tree — no mirror, no patched file, no
`globalThis.__f064` — on artifact `29ec627b` and shell v25.

| file | browser |
|---|---|
| `shipped-runner-chrome.json` | Chrome |
| `shipped-runner-firefox.json` | Firefox |

They carry three things worth keeping:

1. **`formatting-survives-the-next-paragraph-break` — FAIL on both**, with
   identical observables: `boldWhenTyped: true`, `boldAfterBreak: false`,
   `carrierAfterBreak: "paragraph"`, `styleNameAfterBreak: null`. That is
   finding 065 on the shipped product, on two browsers, without any diagnostic
   apparatus in the way. It is declared `KNOWN_RED` naming 065, so if it ever
   passes the runner reports the declaration stale and fails the round.

2. **`every-inline-format-reaches-the-document` — PASS on both**, four formats,
   both directions, each arm read from its own save. This is the shipped-page
   half of finding 064's retraction: it does not depend on the diagnostic probe
   or on the mirrored page at all.

3. **`clear-format-removes-every-inline-format` — PASS**, after days of
   `NOT_ESTABLISHED`. Its precondition ("all four formats were on") had been read
   from the **cleared** document, which no longer records that moment; it now
   reads MKALLON's own save. The button never changed.

`staleKnownRedDeclarations` is `[]` in both, and both report `ok: true`.

The diagnostic evidence that established the mechanism is next door in
`findings/evidence/064/`, and it is stamped `evidenceClass: "diagnostic"`
throughout. **Keep the two apart**: these two files are what the product does;
those files are what a patched copy of it did while being asked a question.
