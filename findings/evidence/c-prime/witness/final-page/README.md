# The witness on the final page: result (2026-10-11)

Prediction: `PREDICTION.md` (committed in `0c9a8394` before any run on this page). Script: `run-witness-final.sh`;
log `chain.log` (02:57:49–03:22:59Z; every swap's runner hashes checked, `HEAD runners … OK` after the last run).
Page: `dist/e2-editor-app.js` = `web/` = `8909564eb2316afa…` (C′ + 124 + 125), tree `0c9a8394`. Reader:
`../judge_witness.py` (unchanged since its red cases, `../judge-red-cases.txt`); output `judge-output.txt`.

| Run | Runners | Exit | Witness-red | Other movements |
|---|---|---|---|---|
| Chrome unported | `08d73cff` (`5f26e3bd…`, `a6e31896…`, `505f4f3a…`) | 0 | **0** | 0 |
| Chrome ported | HEAD (`cc38ee97…`, `bd6fc0ca…`, `17a38fe7…`) | 0 | **0** | **1** (below) |
| Firefox unported | `08d73cff` | 1 | **0** | 0 |
| Firefox ported | HEAD | 1 | **0** | 0 |

Firefox's exit 1 is the known red `an-inline-format-reaches-a-selection` (FAIL in all three 0.2.11 rounds).

**Port-witness cells: 0. Page-effect cells: 0.** Both as predicted. By PREDICTION.md's "What follows": the
ports of `run_e2_c_product_path.py` and `check_m3_page_honesty.py` have no witness on either page and are
registered (§34.4, the owner's fallback); the page-smoke port waits for production UI `Rdel` with the pre-port
`run_e2_c_page_smoke.py` on the first host build carrying this page.

## The movement the prediction did not have

PREDICTION.md said "no other movements". One cell moved, in the ported Chrome run only:
`clear-format-removes-every-inline-format` is **NOT_ESTABLISHED** (0.2.11: PASS, PASS, PASS). Not witness-red by
the rule (NE is not FAIL), but outside the prediction, so recorded here rather than passed over.

What the report says: the check's precondition, four formats accumulated at a collapsed caret
(`MKPREOLD` → `MKPRELIC` → `MKPREINE` → `MKALLON`), failed at its first step. The `set-bold` press right
after the clear-format normalisation answered in 3 ms (`formatPressLatency "B 3 ms"`, `formatPressWaitedMs 0`;
the unported run on the same page: 14 ms, 406 ms), the page's own format cache moved false → true, the button
was offered — and the saved `MKPREOLD` is not bold. Italic, underline and strikethrough then accumulated
normally, so `MKALLON` lacked only bold.

What the record already holds (every committed `findings/evidence/**/e2-editor-v*-*.json` carrying this check,
tabulated from `observed.allOnWhenTyped`): **Firefox, NE in 59 of 68 runs** (release sets 0.2.9–0.2.11, the
v15–v19 measurements, C5 (i) on the P page, the C′-only witness), both arms, with each of the four formats
being the one that did not reach the text in different runs; **Chrome, PASS in 67 of 67 runs before this
one**. The mechanism class is finding 077's (the toolbar toggles;
what it sends follows the page's format cache, so a cache one step behind the engine inverts the request).
So this is an existing intermittent, seen in Chrome for the first time; one run cannot say whether the final
page made it more frequent there. The port does not touch this path (`PRESS`, `READ_STATE` and `format_arm`
are the same text in both runners).

**Registered, with its own reading** (a watch item, not a gate criterion): the release step's product-path
net runs this page six times in Chrome (v8 and v19 arms, three rounds). Base rate 0 of 67. If this cell is NE
in **two or more of those six** (about 0.4 % at a 1.5 % rate), it is treated as a page effect and diagnosed
before the count; one or none, it stays registered here. If the net is never run, this stays a registered
single occurrence.
