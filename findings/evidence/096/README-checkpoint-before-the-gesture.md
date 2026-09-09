# 096 half C — the red case for the checkpoint before the gesture

`probe_096_checkpoint_before_the_gesture.py`, run 2026-09-09 on the **shipping**
bytes (`e2-editor-v8`, the profile `web/e2-editor-app.js` pins). No build, no
link, no product byte moved: the two arms are symlink mirrors of `dist/` in
which exactly one file differs, and only in these two lines of
`editor-shell-v2/narrow-editor-v2-session.js` —

```
        if (BOUNDARY_CAPABLE_MOVES.has(action))
          await this._checkpointBeforeBoundaryMove(document);
```

## Files

| file | what it is |
| --- | --- |
| `probe_096_checkpoint_before_the_gesture.py` | the instrument; its docstring carries the protocol and its own limits |
| `checkpoint-before-the-gesture-shakedown-1.json` | the shakedown, `--attempts 1`. It forced **no change** to the probe, and is banked so that claim can be checked rather than believed |
| `checkpoint-before-the-gesture.json` | the counted run, `--attempts 3` per arm |

## Result — 6 counted attempts, 6 as predicted, 0 VOID

| arm | outcome | `data-rescue` | `#s-checkpoint` after the key | the typed text came back |
| --- | --- | --- | --- | --- |
| `without` — the two lines removed (the product as it shipped this morning) | **WORK_LOST** 3/3 | `none` | `無` | **no** |
| `with` — the tree as it is now | **RECOVERED** 3/3 | `checkpoint` | `有（r1）` | **yes** |

`verdict.armsDisagree: true`.

## What is judged, and what is only recorded

**Judged**: `content.xml` of the bytes the product's own save button produced,
after the product's own recovery button was pressed. A checkpoint nobody
restored from is not a checkpoint, so `hasCheckpoint` is not the verdict and
neither is the state pill.

**Recorded, not judged**: the notice's sentence. The `without` arm reproduces
the owner's quote character for character in all three attempts
(`noticeMatchesOwnerQuote: true`); an oracle on wording would go green the day
somebody rephrases it.

## The instrument's own controls

* The mutation must MATCH. The probe asserts its replacement changed the source
  and refuses to run otherwise — a pattern that matched nothing would serve the
  fixed product in both arms and report agreement between two identical
  mirrors.
* The checkpoint must be ABSENT before the key (`checkpointBeforeTheKey: "無"`,
  6/6). Without that, a checkpoint left behind by an earlier gesture reads as
  one this arrow key banked.
* The typing must REACH the document: the attempt is VOID unless the revision
  moved (0 → 1 in all six).
* The caret must be on the FIRST line, found from the canvas ink rather than
  from a viewport fraction. A click one line lower measures an ordinary move,
  which answers in about 40 ms and proves nothing about a boundary.

## What this cannot measure

**Half A.** No artifact in this tree carries the engine's move-path deadline,
so in BOTH arms the boundary press is never answered and the session dies after
the SDK's 30 s. `boundaryPressAnsweredSeconds` is `null` in all six attempts.
The probe carries an `ENGINE_ANSWERED` outcome for the world after the owner's
link: **a `RECOVERED` in the `with` arm after the link means the deadline is not
in the artifact.**

Also not measured here: Home/End and the two character moves (096 measured
Up/Down, 018 measured End); the deadline's behaviour under load; and a physical
keyboard — keys are injected at the renderer.
