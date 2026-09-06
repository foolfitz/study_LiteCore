# The `open` timeout became a knob, and the knob was made to bite first

**2026-09-06.** `web/ods-decisive-probe-app.js` had `timeoutMs: 180000` written
into the `engine.open()` call, so every TIMEOUT row in this finding's evidence
means "did not finish within 180 s" — and nothing in the report said 180.

Two changes, both small:

* the value comes from `?openTimeoutMs=`, defaulting to `180000`, so every
  existing report and every re-run of one means exactly what it meant before;
* **the report records it** (`openTimeoutMs` beside `profile`). A TIMEOUT row is
  not a claim about a file until the reader knows what it timed out against, and
  "the drafting party remembers which flag they passed" is not evidence.
  `tools/probe_ods_on_profile.py` gains `--open-timeout-ms` and always sends the
  parameter, so the field is present whether or not anyone overrode it.

## The red case, first

A knob that is not wired looks exactly like a knob that is wired and did not
change anything. So before using it for a real measurement, it was pointed at a
file that always opens:

```
--fixture tdf149752-rows35.ods --control d1-anchors.odt --open-timeout-ms 400
```

| case | normally | with `--open-timeout-ms 400` |
| --- | --- | --- |
| `d1-anchors.odt` (the ODT control) | opens, ~1,800 ms | **`open timed out after 400 ms`** |
| `tdf149752-rows35.ods` | opens, ~1,250 ms | opens (its own open is under 400 ms; the control ahead of it paid the engine boot) |

The control flipped and the error message quotes the value that was passed.
Report: `openTimeout-knob-red-case.json`.

Note what the second row shows on its own: `rows35`'s open, once the engine is
warm, is under 400 ms. The ~1,250 ms in the ladder is mostly boot.

## Correction: "the report records it" was not true as first landed

The commit that introduced the knob said the report records the value. It did
not. The page put `openTimeoutMs` into its own report object, but
`probe_ods_on_profile.py` does not copy that object out of the browser — it
**projects a few named fields** (`page` carries only `done`, `caseCount`,
`cases`) — so the field stayed in the page and never reached a saved report.
`rows36-open-timeout-1800s.json`, taken before the fix, has no `openTimeoutMs`.

Fixed by reading it out of the page explicitly, after the cases are retrieved,
**from the page rather than from `args`**: what the evidence needs is the value
the `open()` call actually used, not the value someone intended to pass.

Non-vacuity, measured rather than argued:

| passed | `openTimeoutMs` in the saved report |
| --- | --- |
| `--open-timeout-ms 180000` | `180000` (`openTimeout-field-lands-180000.json`) |
| `--open-timeout-ms 400` | `400` (`openTimeout-field-lands-400.json`) |

The field moves with the flag, so it is reporting something rather than
printing a constant.

**`rows36-open-timeout-1800s.json` was not re-taken** to gain the field. It
already carries the value in-band, in the place that matters most: the error
string is `open timed out after 1800000 ms`. The payload is in the message, not
in a summary of the message, which is the only reason a 30-minute re-run would
have been worth it.
