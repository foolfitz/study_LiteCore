# Control run 2: the guard fires, on a real dead session, and says the right thing

Run 2026-08-26 19:01, `--liveness-control`, chrome, shipped `e2-editor-v8`,
after `Liveness.under_control()` was added because of
[control run 1](RESULT-control-run-1.md).

## What it did

```
333.6s PASS             editing-a-long-document-stays-responsive
369.1s NOT_ESTABLISHED  the-run-stopped-because-the-session-was-dead
```

```json
{ "noticedAfter": "recovery-returns-what-the-product-promised",
  "where": "inside the arm that induces it, after the inducer wedged the engine and before the notice is pressed",
  "state": "recoverable-error", "pending": "0", "checkpoint": "有（r2）",
  "latency": "定位游標 失敗",
  "toast": "定位游標：TIMEOUT：editorGetStateV2 timed out after 30000 ms",
  "recorded": 39, "declared": 40,
  "neverReached": ["recovery-returns-what-the-product-promised"] }
```

`ok: false`; the verdict says the session was dead rather than that a product
path is broken.  37 PASS / 3 NOT_ESTABLISHED were recorded before it stopped.

## Against the prediction, line by line

| predicted | measured |
|---|---|
| the run stops, `sessionDied` present, `ok: false` | **yes** |
| it stops at `recovery-returns-what-the-product-promised` | **yes** |
| `pending: 0`, `checkpoint` NOT `無`, state `recoverable-error` | **yes** — `有（r2）`, and the reason the prediction gave is the right one: this inducer takes a checkpoint before it wedges, which is that arm's whole subject |
| `neverReached` empty or nearly so | **one entry** — the arm is the last check in the run |

The toast is finding 038's own shape (`editorGetStateV2` timing out on the read
of a selection that returned healthy), so the state the guard met is the one the
arm exists to produce, not something else that happened to look like it.

## Three runs, three different things, and none of them is the other

| run | guard | what it shows |
|---|---|---|
| shipped v8, no flag | 39 probes, never fired | **no false positive**, and the guard RAN — 39 is 40 checks minus the 3 recorded inside the two held-off regions plus the 2 region-exit reads |
| shipped v8, `--liveness-control` | fired at the endnote inducer | **it fires** on a real terminal state, names the arm, and refuses to call the run green |
| `e2-editor-v9`, no flag | fired after `format-a-paragraph-changes-that-paragraph` | **it earns its keep**: a session that died on its own, 23 arms not driven at it, 5 min 22 s instead of 20–50 minutes, and a readable report |

The third is the one the guard was written for and it is the only one nobody
could have arranged.
