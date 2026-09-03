# B-2 criteria 2, 3′-i, 3′-ii and 4 — all **PASS**, 2026-08-29

Criteria fixed before the runs in `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`,
addendum part 2 (B-2) and part 3 (C-2). Criterion 1 is banked separately in
[`RESULT-criterion-1.md`](RESULT-criterion-1.md).

The candidate under test is **`e2-editor-v12`**: `e2-editor-v11`'s artifact,
byte-identical loader and wasm (`pinAfter: 4ec1e389aaab3b03` on both), with its
filesystem image split into base + cjk + fallback packs cut from its **own**
image and declared under its own manifest.

Built with a new `--split-core-data` flag on
`tools/build_e2_editor_v4_profile.py`. The flag refuses without `--core-data`
(shown red). `loadAtStartup` mirrors the product core's split exactly — CJK at
startup, fallback not — deliberately, because the question this profile answers
is what the *same* packaging costs on *this* core, and moving two variables
would answer neither.

## Criterion 2 — the split profile boots and the net reconciles clean

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --out criterion-2-net-v12.json
python3 tools/check_usable_editor.py --report criterion-2-net-v12.json
```

**38 PASS / 2 NOT_ESTABLISHED**, `ok: true`, `complete: true`, reconciled
`ok: true` with `reconciledFor.kind == "candidate-cutover"` and
`profile == "e2-editor-v12"`, `problems: []`. The NE set is the same two.
Candidate page sha256 `3dfdcfef4abfe6b7…`.

## Criterion 3′-i — the startup fetch pattern, from the server's own log

The oracle is `web/serve.py`'s access log, **not** the worker's
`resource-pack-loaded` events: those would be the loader reporting on itself,
and the question is what crossed the wire.

| profile | `.data` requests | startup packs all fetched | non-startup packs never fetched |
|---|---|---|---|
| `e2-editor-v8` | `base-r5…`, `cjk-r5…` | yes | yes |
| `e2-editor-v11` | `soffice.data` | yes (none declared) | yes (none declared) |
| `e2-editor-v12` | `base-e2-editor-v12…`, `cjk-e2-editor-v12…` | **yes** | **yes** |

On v12: the cjk pack **is** fetched at startup, the fallback pack is **not**,
and no other pack fetch occurs anywhere in the run. 33 requests were logged —
the probe asserts the log is non-empty, so a silent server cannot read as
"nothing was fetched".

## Criterion 3′-ii — font parity

| profile | font files | font bytes | inventory sha |
|---|---:|---:|---|
| `e2-editor-v8` | 13 | 23,843,948 | `5ddc280ae48dd9c1` |
| `e2-editor-v12` | **13** | **23,843,948** | **`5ddc280ae48dd9c1`** |
| `e2-editor-v11` | 129 | 72,945,990 | `43825cda2c8b8d21` |

* **The split profile's font inventory is identical to the incumbent's** —
  name for name and byte for byte, same hash.
* **Unsplit v11's is that set plus exactly the fallback slice**: the difference
  is **116 files / 49,102,042 bytes**, and the fallback pack's own metadata
  lists **116 files / 49,102,042 bytes**, with the name sets equal. v12's
  inventory is a strict subset of v11's.

### Read from the running worker, not derived

The first pass derived the inventory from the metadata of the packs the client
fetched. An adjudication refused that as the *reading* — accepting it only as
corroboration — on the grounds that this tree's current handoff is titled
*instruments that hid what they were built to find*, and three of its five
instrument failures were readers that derived where they could have looked.

So the probe now reads `Module.FS` out of the **running document worker**,
reached with `Target.setAutoAttach` — the route `induce_worker_failure` records
as the only one that works, because `Target.getTargets` reports the pthread
targets with empty urls and `attachToTarget` returns a session nothing answers.

| profile | mounted files | mounted bytes | mounted sha | derivation agrees |
|---|---:|---:|---|---|
| `e2-editor-v8` | 13 | 23,843,948 | `5ddc280ae48dd9c1` | **yes** |
| `e2-editor-v12` | 13 | 23,843,948 | `5ddc280ae48dd9c1` | **yes** |
| `e2-editor-v11` | 129 | 72,945,990 | `43825cda2c8b8d21` | **yes** |

Both halves hold on the **mounted** inventories, not only the derived ones: v12
equals v8 name-for-name and size-for-size, and v11 equals that set plus
**exactly** the 116 files / 49,102,042 bytes of the fallback slice — names and
sizes equal, v12 a strict subset of v11.

The two readings agree on all three profiles (`derivationMatchesTheMount:
true`), and that agreement is itself a result: a loader that fetched bytes it
did not mount, or mounted bytes it did not fetch, would surface here as a
discovery about every profile rather than as a blemish on this probe.

*The instrument's own bug, recorded*: the first version unwrapped the CDP
envelope one level too deep and reported "the worker did not answer with a
string" — while printing the worker's correct answer inside the error. Caught
in the run it was written in, because the error carried the payload rather than
a summary of it.

### The 130th font file — why two published counts differ by one

Addendum part 1 §A-3 measured **130 font files / 73,153,982 bytes** in v11's
image. The mount walk reports **129 / 72,945,990**. Bridged here so a reader
comparing the two finds the explanation rather than an unexplained gap.

The walk covers `/instdir/share/fonts`. §A-3 used a looser predicate — that
prefix **or** a font extension anywhere — and caught one more file:

```
/instdir/program/resource/common/fonts/opens___.ttf   207,992 bytes
```

OpenSymbol, and there are **two** copies of it in the image: one under
`/instdir/share/fonts/truetype/` (inside the walk, counted in the 129) and this
one outside it. Measured: it sits in the **base** slice, and it is 207,992
bytes in v11's image and in the product core's alike — it is not one of the two
size-differing common files (`images_colibre.zip` and `services.rdb`, neither a
font). So it reaches v8, v11 and v12 identically and parity is undisturbed.

**The discrepancy is the walk's scope, not the split.** 129 + 1 = 130 and
72,945,990 + 207,992 = 73,153,982.

## Criterion 4 — the figure

Counted by the plan's own method, from every file each manifest references:

| profile | required before usable | declared but never fetched | vs v8 |
|---|---:|---:|---:|
| `e2-editor-v8` | **161.4 MiB** | 46.8 | — |
| `e2-editor-v11` | **232.8 MiB** | 0.0 | **+71.3 (+44.2%)** |
| `e2-editor-v12` | **186.0 MiB** | 46.8 | **+24.5 (+15.2%)** |

The probe **reproduces the plan's own figures for v8 (161.4) and v11 (232.8)**,
which is why the v12 number is worth anything — the method was validated
against numbers counted independently a day earlier, not invented here. It also
asserts non-vacuity: a manifest referencing fewer than four files, or a total
under 100 MiB, is a red.

The column is named `declaredButNeverFetched`, per finding 085. It is not
"deferred".

## Reproducing

```bash
cd wasm_sdk_probe
python3 ../findings/evidence/queue-v11-split-probe/probe_required_before_usable.py
python3 ../findings/evidence/queue-v11-split-probe/probe_pack_fetch_pattern.py \
    --profile e2-editor-v12
```

## Still owed

**3′-iii** — the functional consequence of the missing fallback fonts, measured
on all three profiles. It does **not** gate this probe; it gates the owner's
confirmation. Until it exists, the confirmation carries: *"the functional value
of the fallback font set is unmeasured; the option is preserved."*
