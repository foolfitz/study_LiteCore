# The dead-session guard: what was measured, and what each run does and does not show

`queue-a11y-path-drives-a-dead-session`, closed 2026-08-26.
The defect it removes is finding 081: the product-path runner kept driving a
session that had entered `recoverable-error`, so each of the remaining arms
spent its own timeout on a session refusing everything with `EDITOR_NOT_READY`.
A run cost 20–50 minutes and, because the report was written only by `finish()`,
produced nothing at all.

## The change, in three parts

1. **`class Liveness`** in `tools/run_e2_c_product_path.py`. After every recorded
   check the page's state is read once. `recoverable-error` or
   `restart-required` stops the run, names the check after which it noticed,
   lists in **source order** the checks it never reached, and reports
   `ok: false` — including under `--mutate`, where the mutation branch would
   otherwise conclude "detected" from a run that stopped before the checks it
   was confounding.
2. **Two arms hold the guard off**, because they induce that state deliberately
   and then press the product's recovery notice: finding 047's recipe and
   finding 038's endnote inducer. Each is read once more **on the way out**, so
   an arm that fails to recover stops the run naming *itself* rather than the
   innocent check that follows it.
3. **`--out` is written after every check**, stamped `complete: false`, so a run
   that is killed leaves a readable partial report. `tools/check_usable_editor.py`
   now **refuses** a report that is not `complete: true`, one that carries
   `sessionDied`, and one that carries `profileDiagnostic` — three new kinds of
   well-formed file that would otherwise have been citable as acceptance
   evidence.

## The runs, and what each one is for

| file | what it shows |
|---|---|
| `product-path-e2-editor-v8-chrome-guard-armed.json` | **No false positive, and the guard ran.** 37 PASS / 3 NOT_ESTABLISHED, `ok: true`, `liveness.probes: 39` — which is 40 declared checks minus the 3 recorded inside the two held-off regions plus the 2 region-exit reads. "It never fired" and "it never ran" are different answers and this says which. |
| `control-run-1-check-boundaries-only.json` + [`RESULT-control-run-1.md`](RESULT-control-run-1.md) | **The control that could not fire, and why.** Both inducing arms recover *before* they record their check, so a probe at check boundaries never meets the state they induce. 38 PASS / 2 NE, `ok: true`, did not stop. This is why `Liveness.under_control()` exists. |
| `control-run-2-probe-inside-the-inducer.json` + [`RESULT-control-run-2.md`](RESULT-control-run-2.md) | **It fires.** Stopped inside finding 038's arm, after the inducer wedged the engine and before the notice was pressed: `recoverable-error`, `pending: 0`, `checkpoint: 有（r2）`, toast `TIMEOUT：editorGetStateV2 timed out after 30000 ms`. `recorded: 39/40`, `ok: false`. |
| `product-path-e2-editor-v9-chrome-guard-stopped-it.json` | **It earns its keep, and nobody could have arranged this one.** On the accessibility profile the session died on its own after `format-a-paragraph-changes-that-paragraph` — the same arm, and the same page state to the field, that was read over CDP on 2026-08-24. `recorded: 17/40`, 23 arms not driven at a dead session, **5 min 22 s instead of 20–50 minutes**, and a report that can be read. |

[`PREDICTION-liveness-control.md`](PREDICTION-liveness-control.md) was written
before any control run and is kept unedited: it predicted control run 1 would
stop, and it did not.

## What none of these establishes

* That `recoverable-error` is the only way a run can be wedged. The guard reads
  the state the page publishes; a session that is slow, or a browser that has
  gone away, is a different failure and is recorded as `probeError` rather than
  claimed as this one.
* That the a11y lineage is measurable past check 17. It is not, yet — the
  remaining 23 checks on `e2-editor-v9` have never run.

## The unit test, and what it is worth

`tests/test_session_liveness.py` drives the guard's behaviours without a
browser: the predicate, a live session, a dead one, an inducing region that
recovers, one that does not, the control both ways, the once-only rule, and a
read that throws. Six mutations of the guard are each detected by it
(`DEAD_STATES` emptied, the region-exit probe removed, the probe unwired from
`check()`, the once-only rule removed, a region wrapper replaced by
`nullcontext`, and the control ignored in `__enter__`).

Three of its assertions are **static string checks** on the runner's source and
are declared as the weaker half in the test's own docstring: they say the call
sites have not been deleted, not that they work. The measurement is control
run 2.
