# Runbook: finding 082's fix on the accessibility lineage (`e2-editor-v10`)

Written 2026-08-26. Follows the structure of
[`RUNBOOK-relink-v8.md`](RUNBOOK-relink-v8.md).

**This link mints a NEW name.** It does not relink `e2-editor-v8`, `v9`,
`a11y-calloc` or any other frozen profile, and `make -n` on the target was
checked to touch nothing outside `build/e2/e2-editor-v10/` and
`dist/profiles/e2-editor-v10/`. Prior verdicts keep describing what they
describe.

## What this link ships — measured, not read

`tools/what_the_link_ships.py --variant a11y --since c82a642` — `c82a642` being
the commit `a11y-calloc`'s artifact (and therefore `e2-editor-v9`'s) was linked
from:

| unit | verdict |
|---|---|
| `sdk_api.cpp`, `unoembind_stub.cpp`, `editor_api.cpp` | preprocess **identically** |
| `probe_engine.cpp` | **14 hunks, all of them finding 082's** |
| `sdk-worker.js` | **byte-identical** — `070229cd10bda4a0` both sides |

`configurationDrift: []`. The `calloc` hunk is absent from this diff, which is
how the baseline is confirmed: v9 already carries it.

So this is **one variable against `e2-editor-v9`**: same core
(`wasm-lite/build-a11y-gate0`), same defines, same worker, same manifest flags,
same gestures. The engine's identity gate is the only thing that differs.

### The change

The format barrier's paragraph-identity gate stops comparing a fingerprint that
identifies nothing.

* The fingerprint is FNV-1a 64 over the focused paragraph's content **with
  `listPrefixLength` characters stripped**. Stripping is deliberate and it
  works: `E1-LC-END甲一乙二丙三插入鈕標記` and the same text with a bullet in
  front of it report one fingerprint (`76f09d751bb341f7`, measured).
* Finding 074 makes that length the **whole paragraph** for an outline-numbered
  paragraph with uniform character formatting — a heading, in practice. The
  slice is then empty and the fingerprint is the FNV-1a offset basis, the value
  that means *nothing was hashed*. Measured on `list-contexts.odt`:
  `E1-LC-HEADING` (13 of 13) and a paragraph holding only `• ` (2 of 2) report
  the same number, `cbf29ce484222325`.
* v9 therefore refused a **correct** `set-paragraph-body` on that heading as "a
  different paragraph", with a `rollback` disposition, on a session with no
  checkpoint. 4 runs of 4. That is finding 082.

The gate now **declines** the comparison when either end's fingerprint is
degenerate, rather than failing it — the same fail-open the surrounding comment
already argues for, extended from "the value is absent" to "the value is present
and meaningless". Three new payload fields say which of the three reasons it
was, so `checked: false` never has to be guessed at again.

`src/a11y_paragraph_identity.hpp` holds the rule and the hash together, and
`tests/a11y_paragraph_identity_test.cpp` drives them **on the host**: it
reproduces six fingerprints the accessibility engine really reported, so it is a
cross-implementation check rather than a restatement. Four mutations of the rule
are each detected by it. It runs in `make test-e2-b-static`.

**Inert on the product core, by construction**: `refreshCaretParagraph()`
returns false when accessibility is off, so `dispatchParagraphKnown` was already
false there and the gate already declined. The product build gains three false
fields in a payload and no behaviour. `e2-editor-v8` does not need relinking.

## The command

```sh
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v10/sdk-manifest.json
```

`ALLOW_FROZEN_RELINK=1` is required because the guard sits in the link recipe
unconditionally. Nothing frozen is being relinked; the flag is the price of the
guard, not a description of what is happening.

## The four things to do after it, before believing anything

1. **Record the hashes.** `dist/profiles/e2-editor-v10/sdk-manifest.json` →
   `editorContract.wasmSha256`, `loaderSha256`, `workerSha256`, and the manifest's
   own digest. A profile is five bound identities, not one artifact
   (`ATTRIBUTION.md`).
2. **Check the gestures survived.** `python3 tools/check_gesture_offers.py` and
   `--self-test`. `--inline-range-gestures all` is what makes this comparable to
   v9; a narrower set would silently make it a different experiment.
3. **Archive it** before anything is measured against it:
   `build/archive/e2-editor-v10-<wasm>-worker-<worker>-manifest-<manifest>/`,
   named after what it contains, because a build path cannot say *which*
   artifact (finding 042).
4. **Then measure**, and only then:
   ```sh
   python3 tools/run_e2_c_product_path.py --browser chrome \
       --profile e2-editor-v10 --barrier-details-diagnostic --out <path>
   ```

## What the answer should look like — written BEFORE the run

**The prediction, so the run can contradict it.**

1. The run does **not** stop after `format-a-paragraph-changes-that-paragraph`.
   `sessionDied` is absent and `recorded` is 40 of 40.
2. In the format arm, `set-paragraph-body` **PASSES**: the readback markup
   already showed `<p>E1-LC-HEADING</p>` on v9, so the mutation was landing all
   along and only the gate refused it.
3. `pageErrors` carries **no** `readback-is-a-different-paragraph`. If a barrier
   still declines on that heading, the payload says
   `paragraphIdentity.declined: "the reported list prefix consumed the whole
   paragraph…"` and `checked: false` — declined, not failed.
4. `bulleting-a-blank-line-does-not-demand-a-rollback` is **still red**, with
   `stage-deadline:awaiting-selection`. That is a different defect and nothing
   here touches it. A run where it goes green means something else changed and
   the change has not been understood.
5. Consequently `notice-action-recovers-the-session` keeps PASSING on this
   lineage (the pair in `finish()` holds: bulleting FAIL ⇒ the recovery check is
   judged), and the 23 checks v9 never reached get their first reading.

**What would refute the fix**: the run still stops at the same arm, or
`set-paragraph-body` fails for a *different* shape. Either means the empty-slice
fingerprint was not the whole cause, and finding 082 needs rewriting rather than
closing.

**What this link does NOT fix**, and it must not be read as fixing:

* **Finding 074 itself**, which is upstream (`sfx2/source/view/viewsh.cxx`).
  The engine stops trusting a bad number; the number is still bad, and every
  other consumer of `listPrefixLength` is still exposed.
* **The fingerprint as an identity in general.** 22% of paragraphs in the
  r7-compat corpus collide on text alone
  (`queue-a11y-prefix-swallows-the-paragraph`). This makes the gate honest about
  one failure mode; it does not make a fingerprint join workable.
* **The `stage-deadline` barrier failure**, item 4 above.
