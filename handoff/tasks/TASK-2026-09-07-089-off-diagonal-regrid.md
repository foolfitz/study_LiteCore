# TASK — finding 089: re-measure the OFF-DIAGONAL grid points, the ones that carry "both axes are needed"

Pre-registered measurement protocol for finding
`findings/089-a-13kb-spreadsheet-with-a-full-height-repeated-row-times-out-on-wasm-but-opens-in-269ms-natively.md`.
Drafted by the opus seat on 2026-09-07 from the banked evidence in
`findings/evidence/089/`, **before any run of this protocol has been made**.
Every criterion below is pre-registered. `AGENTS.md` §9 governs anything added
after the first invocation that counts.

**Why this exists.** On 2026-09-07 the pre-registered outcome **(ii)** obtained
in `findings/evidence/089/cpu-or-wait-2026-09-07/TIMING-RECONCILIATION.md`
(note the path: the file lives in the `cpu-or-wait-2026-09-07/` subdirectory,
not directly under `evidence/089/`). The sentence it licensed, quoted from its
own pre-registration: *"the banked ladder was measured under a condition this
session can now name, and the frontier itself (`Index ≥ 35` / `Index2 ≥ 36`)
must be re-measured before any statement about `Index`/`Index2` is repeated."*
The main session's ruling of the same day (appended to
`findings/089-a-13kb-spreadsheet-with-a-full-height-repeated-row-times-out-in-wasm.md`)
kept that obligation and recorded that the **diagonal half** was discharged the
same day — `rows35` opens 3/3, `index36/index2-35` opens 3/3, `rows36` times out
3/3. **What is owed is the off-diagonal half**, and that is what this protocol
measures and nothing else.

**The one thing this protocol may not do.** It may not name a cause. See §9,
which is a standing prohibition and not a footnote.

- **Structure rule.** The executor may write **only** two things: (a) files
  under the new directory
  `findings/evidence/089/off-diagonal-regrid-<YYYY-MM-DD>/`, where the date is
  the **UTC** date on which invocation 1 starts (created once; not renamed even
  if the runs cross midnight), and (b) one appended section under
  `## Execution record` at the end of *this* file. No file anywhere else in the
  tree may be created, edited, moved or deleted. Named explicitly, because each
  has a reason: not `wasm_sdk_probe/web/` and not `wasm_sdk_probe/dist/` and not
  any profile (the cutover gate is mid-count at 6 of 12 and the page identity
  must not move); not any `check_*.py` or other judge; nothing under
  `findings/evidence/queue-v12-*`; **nothing else under
  `findings/evidence/089/` except the new subdirectory** — §8.2 names the
  specific way this task could destroy the banked fixtures by accident; not
  `.gitignore` (`!/findings` already tracks the new directory).
- **Role.** The executor is the sonnet seat: it runs the procedure and records
  what happened. It is **not** the drafting party and carries no judgement. It
  does not name a cause, does not decide what the result means for the ODS
  milestone, and does not relax a criterion. If a criterion turns out to be
  unsatisfiable as written, the executor **stops and reports** — it does not
  rewrite the criterion and it does not build machinery to make one hold
  (`AGENTS.md` §4). The one thing it *does* build is `reduce.py` (§4.6): that is
  the `AGENTS.md` §8 form-two instrument — a tool that **reads existing
  products** so a third party can re-derive the verdict in one line — and it is
  explicitly not the "new mechanism" §4's self-check forbids.
- **The 2026-09-07 precedent for stopping rather than repairing**: that
  session's red cases R-B and R-C were unsatisfiable as literally written (no
  thread on this machine carries the comm `CrBrowserMain`), and the executor
  reported them as unsatisfiable instead of inventing a substitute selection
  rule. That is the behaviour wanted here too.

Where the brief lands: item 1 → §1; item 2 → §2; item 3 → §3; item 4 → §4;
item 5 → §5; item 6 → §6; item 7 → §7; item 8 → §8; item 9 → §9.

---

## 1. The exact question, and the pre-registered outcomes

### 1.1 The question, stated so it cannot quietly widen

> On the date this protocol runs, on profile `e2-editor-v12`, do the **six
> off-diagonal grid points** banked on 2026-09-06 still produce the same
> **opened / did-not-open** verdicts they produced then?

It is **not** "is the frontier real". A frontier is a claim about a *region*;
this measures eleven named points (six owed, two anchors, plus the ODT control
in every invocation). Whatever comes out, the residual stays registered: the
points between the measured ones (`Index` ∈ 21–24, 26–29, 31–32, and every
`Index2 ∉ {35, 36}`) are **not measured by this protocol and never were**.

**A note on the form of the criteria** (`AGENTS.md` §1). The point list in §2 is
a **hand enumeration** — form three — and therefore is not, and is not written
as, a claim that these are the points that matter. It is the *scope of a
measurement*. The per-invocation requirements in §4.5 are form-one per-instance
properties (they hold automatically for invocations that do not exist yet), and
`reduce.py`'s identity check is form two (the enumeration comes from
`identity.json`, which is generated by hashing, not typed).

### 1.2 The outcomes, and the trigger that selects each

Evaluated **in this order**; the first whose trigger fires is the outcome.
Definitions of REPRODUCES / CONTRADICTS / SPLITS are in §4.

**Outcome E — NOT RE-MEASURABLE: the instrument's variance exceeds the effect.**
*Trigger*, any one of:
- **E1** — either anchor splits within its own shape's repeats: `rows35`
  (`Index=35, Index2=35`) fails to open in some repeat, or `rows36`
  (`Index=36, Index2=36`) opens in some repeat.
- **E2** — two or more of the six owed points SPLIT after the §3.4 tie-break.
- **E3** — for any point that opened in every repeat, the spread of its own
  `elapsedMs` across repeats exceeds **4.0x** (max/min).

*Licenses*: nothing about `Index`/`Index2`. See §5.4 for the exact sentence and
where it is written.

**Outcome C — RETIRED: a banked point does not reproduce.**
*Trigger*: no E trigger fires, and at least one of the six owed points
CONTRADICTS its banked verdict **unanimously** across its repeats.

*Licenses*: exactly one bounded sentence per contradicting point — "on
`<date>`, on `e2-editor-v12`, `(Index=a, Index2=b)` <opened in X ms / did not
open within 180 s> in all N repeats, against a banked `<verdict>` from
`<artefact>`". It licenses **no replacement frontier**: a frontier is a region
claim and this samples points. The standing obligation (the two-axes sentence
may not be repeated) **remains in force** in this outcome — a contradicted
banked point does not restore a claim, it removes its support.

**Outcome S — UNDECIDED: a point splits.**
*Trigger*: no E or C trigger fires, and at least one owed point SPLITS after
the tie-break (with the anchors both unanimous, or E1 would have fired).

*Licenses*: the split, reported as measured, per point and per repeat. The
obligation remains in force.

**Outcome R — RESTORED: the off-diagonal reproduces.**
*Trigger*: all eleven measured points REPRODUCE their banked category
unanimously; the ODT control opened in every invocation; both anchors behave as
they did on 2026-09-07; no invocation is void; and every §4.5 non-vacuity gate
passed.

*Licenses*, and only this: "Re-measured on `<date>` on `e2-editor-v12`, three
invocations per row. At `Index2 = 36` the document opens at `Index` ∈ {20, 25,
30, 33, 34} and does not open within 180 s at `Index` = 35. At `Index2 = 35` it
opens at `Index` ∈ {35, 36, 100}. On these eleven points the 2026-09-06 grid
reproduces." **Only after this outcome may the sentence `Index ≥ 35` AND
`Index2 ≥ 36` be repeated**, and then only with the date and the point list
attached — never as a timeless fact and never extended to the unmeasured
interior.

**Outcome V — VOID: the protocol did not produce a measurement.**
*Trigger*: the budget (§3.5) is exhausted without three non-void repeats of both
shapes; or the identity check (§8.3) fails; or `reduce.py` fails a red case of
§6 in a way that voids its own verdicts.

*Licenses*: nothing. Same written record as E, with the obstacle named instead
of the variance.

### 1.3 The default if this is never run — written now (`AGENTS.md` §2)

If this protocol is never executed, or is executed and lands on E, S or V, the
standing conclusion is:

> The claim "`Index ≥ 35` AND `Index2 ≥ 36` — both axes" **stays out of use**.
> It is not repeated in any summary, handoff, plan, or upstream text. It is also
> **not refuted**: the 2026-09-06 grid section of 089 stays exactly as written,
> as the record of what was measured on that day under conditions this tree can
> now name. "Un-repeatable" and "false" are two different registrations
> (`AGENTS.md` §3) and this is the first one.

---

## 2. The grid points, with every banked figure quoted from its artefact

Profile for every row below: `e2-editor-v12`. Every banked report also carries
`nameSpoofed: true` — the SDK rejects any name not ending `.odt` before the
engine queue (finding 013), so the probe hands each `.ods` over as `.odt`.
Reports are `evidenceClass: "diagnostic"` and may never be quoted as the product
opening a spreadsheet.

`Index` = `$Liste.$A$2:.$A$n`; `Index2` = `$Auswertung.$A$2:.$A$n`. Fixtures were
built by `findings/evidence/089/build_row_ladder.py --split INDEX INDEX2`.

### 2.1 Row A — the owed points at `Index2 = 36` (the "`Index2 ≥ 36` is not sufficient" half)

| # | `Index` | `Index2` | fixture (in `findings/evidence/089/`) | banked verdict | banked `elapsedMs` | quoted from |
| --- | ---: | ---: | --- | --- | ---: | --- |
| A1 | 20 | 36 | `tdf149752-index20-index236.ods` | opened | **1,228** | `grid-index100-35-and-index20-36.json`, `page.cases[]` where `name == "tdf149752-index20-index236.ods"`, field `elapsedMs`; tabulated at `grid-2026-09-06.txt:15` |
| A2 | 25 | 36 | `tdf149752-index25-index236.ods` | opened | **1,484** | `grid-index25-30-33-with-index2-36.json`, same case/field; `grid-2026-09-06.txt:16` |
| A3 | 30 | 36 | `tdf149752-index30-index236.ods` | opened | **1,223** | `grid-index25-30-33-with-index2-36.json`; `grid-2026-09-06.txt:17` |
| A4 | 33 | 36 | `tdf149752-index33-index236.ods` | opened | **1,274** | `grid-index25-30-33-with-index2-36.json`; `grid-2026-09-06.txt:18` |
| A5 | 34 | 36 | `tdf149752-index34-index236.ods` | opened | **1,496** | `grid-index34-and-35-with-index2-36.json`; `grid-2026-09-06.txt:20`. **This case also carries `workerCrashed: true`** — see §7.2 |
| A6 | 35 | 36 | `tdf149752-index35-index236.ods` | **did not open**, `error.code == "TIMEOUT"`, `"open timed out after 180000 ms"` | **180,969** and **181,017** (two independent invocations) | `grid-index34-and-35-with-index2-36.json` (`grid-2026-09-06.txt:22`) and `grid-index35-index2-36.json` (`grid-2026-09-06.txt:23`) |

A6 is the corner: it is what makes A1–A5 mean something. Without it, "everything
at `Index2 = 36` opens" and "the harness cannot produce a timeout today" are the
same picture.

### 2.2 Row B — the owed points at `Index2 = 35` (the "`Index ≥ 35` is not sufficient" half)

| # | `Index` | `Index2` | fixture | banked verdict | banked `elapsedMs` | quoted from |
| --- | ---: | ---: | --- | --- | ---: | --- |
| B1 | 100 | 35 | `tdf149752-index100-index235.ods` | opened | **1,486** | `grid-index100-35-and-index20-36.json`, `page.cases[]` `name == "tdf149752-index100-index235.ods"`, field `elapsedMs`; `grid-2026-09-06.txt:26`. **`workerCrashed: true`** — §7.2 |
| B2 | 36 | 35 | `tdf149752-index36-index235.ods` | opened | **1,589** | `grid-index36-index2-35.json`; `grid-2026-09-06.txt:24`. **`workerCrashed: true`**. **Already re-measured 2026-09-07**: 1,172 / 1,136 / 1,162 ms (`cpu-or-wait-2026-09-07/timing/timing-repeat-{1,2,3}.json`) |

B2 is carried even though it is discharged, because a row of one point has no
in-band cross-check and because three more measurements of it, in a different
session, are nearly free.

### 2.3 The two anchors (already discharged on 2026-09-07; carried in-band)

| # | `Index` | `Index2` | fixture | banked | 2026-09-07 | role |
| --- | ---: | ---: | --- | --- | --- | --- |
| K1 | 35 | 35 | `tdf149752-rows35.ods` | opened, **1,245** (`ladder-2026-09-06.txt:19`, from `ladder-rows34-35-36-confirm.json`) and **1,260** (`ladder-2026-09-06.txt:12`, from `ladder-rows25-rows40.json`) | 1,422 / 1,372 / 1,353 ms | the cheap-open anchor |
| K2 | 36 | 36 | `tdf149752-rows36.ods` | **did not open**, TIMEOUT **180,919** (`ladder-2026-09-06.txt:20`) and **180,991** (`ladder-2026-09-06.txt:15`); also **1,800,901 ms, still TIMEOUT** at the raised ceiling (`rows36-open-timeout-1800s.json`) | TIMEOUT 180,836 / 180,854 / 180,835 ms | the hang anchor |

**`tdf149752-index35-index235.ods` is byte-identical to `tdf149752-rows35.ods`**
(both `sha256 a16ac9c5a1e450d6de1a5f586a1a18595dcabf72654dec4852d4aa2bf70524ee`,
both 13,353 bytes, two copies on disk). Opening it as a separate case would
measure the same bytes twice under two names; it is therefore **not** in the
grid, and `rows35` stands for `(35,35)`.

### 2.4 Points the grid needs and does not have — said plainly, not invented

The brief asks for `Index2 = 36` with `Index` **in 20–34**. Fixtures exist for
`Index` ∈ {20, 25, 30, 33, 34} and for no other value in that interval.
**There is no fixture for `Index` ∈ {21, 22, 23, 24, 26, 27, 28, 29, 31, 32} at
`Index2 = 36`, and none may be built by this task.** Three reasons, all
pre-registered:

1. This protocol's obligation is **re-measurement of banked points**. Building
   new ones is new measurement, and it would not discharge the obligation any
   faster.
2. `build_row_ladder.py`'s `main()` writes to
   `OUT_DIR = Path(__file__).resolve().parent`, which **is** the banked
   `findings/evidence/089/`. `--split` therefore overwrites banked fixtures in
   place, and since zip metadata is not reproduced, the whole-zip `sha256` would
   change even where `content.xml` did not — breaking the `inputs[].sha256` line
   of every report already banked (this is the §1.4 trap the 2026-09-07 task
   named, and it is still live).
3. Building elsewhere would require either editing that script or importing it
   as a module and calling `build()` with a scratch `dest` — the first is
   forbidden by the Structure rule, and the second is a new mechanism, which
   §4 of `AGENTS.md` says to stop and report rather than write.

**In scope for a later, separately budgeted task**, if the owner wants the
interior: a densifying run at `Index` ∈ {31, 32} and one at {21…24}, built into
a scratch directory by a builder change made deliberately rather than in
passing. Not here.

### 2.5 Fixture identity, computed 2026-09-07 while this task was drafted

**Any mismatch: stop and report. Do not "update the table".**

| file | sha256 |
| --- | --- |
| `findings/evidence/089/tdf149752-index20-index236.ods` | `5a01fb9221366b625bbdaff56b32ed75e3f87e64615f623b9e86190158d81c96` |
| `findings/evidence/089/tdf149752-index25-index236.ods` | `e33d60165d3b94900e4d1ff53bbb85a7f6e2a9b2347c8d0061bb5adf9a019453` |
| `findings/evidence/089/tdf149752-index30-index236.ods` | `7a9350f4f981a7118038fe7377c1fa87ba1315bb3ad858d4e2a3b47faf4d18de` |
| `findings/evidence/089/tdf149752-index33-index236.ods` | `2782759ebc948173540c8c322eadedc9a0de4baab36cb1a3bcf8d81c4089e330` |
| `findings/evidence/089/tdf149752-index34-index236.ods` | `0c2d917c493c588bb4add896abd23f74c1dc5ed15e7c0a98b307197377f2361d` |
| `findings/evidence/089/tdf149752-index35-index236.ods` | `b28d71507d28b6b789636b7e182cd8bacc5cf929c8342b0f9ca9bb3cbdd33809` |
| `findings/evidence/089/tdf149752-index100-index235.ods` | `d0529333d4a1f441fd22b3b8fe7d5c54ab5f83cf9e16b52709fdfdd17bc3435b` |
| `findings/evidence/089/tdf149752-index36-index235.ods` | `ea10861849df43dbf4e54a1ac34a64434f262090a8b7ce74f835e1da39efc6e6` |
| `findings/evidence/089/tdf149752-rows35.ods` | `a16ac9c5a1e450d6de1a5f586a1a18595dcabf72654dec4852d4aa2bf70524ee` |
| `findings/evidence/089/tdf149752-rows36.ods` | `87b92dbeb653fefcfc9d3017ad646e25431fa51a6981f26220036881b7649a70` |
| `findings/evidence/089/build_row_ladder.py` | `53c771637bc72b25a36adb7f66c6aed8163eaa963d5ad7beda5abbe3c77252c6` |
| `wasm_sdk_probe/test-docs/ods/upstream/tdf149752.ods` | `2d6a2c6aa63c33b0971ef7e3e67b7fc5727639387e5a6eb8c73ae86194f0052e` |
| `wasm_sdk_probe/test-docs/ods/ladder/one-cell-a1.ods` | `bb6142d5b93e58f4a282569956ec5f482e2a41be28f0548c3cee4c5dfa64cb1d` |
| `wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt` | `f89f1e63dcf7c8956f3986257dd79a7ed02bb7825c844a63f73abc4a5c68d241` |
| `wasm_sdk_probe/tools/probe_ods_on_profile.py` | `5c8d567f7a92b39274379a6d9ec3e01c4981b16743b7f64eaf4af88851e34c8a` |
| `wasm_sdk_probe/tools/run_browser_probe.py` | `663b2ffab8174afc070401a15afac18c9ba12950b6a39f146b331ceeab7d8e3e` |
| `wasm_sdk_probe/web/ods-decisive-probe-app.js` | `36326957b26199082ca4667bc8ed95798e9eca57cd4978e81a0f11d395f3099e` |
| `wasm_sdk_probe/web/ods-decisive-probe.html` | `4009fc481d589838d2750831b6e95b4c6802982200ecb1d05a7c9fca40f9a204` |
| `wasm_sdk_probe/dist/profiles/e2-editor-v12/probe.wasm` | `4ec1e389aaab3b0335875d06044639e33e94de777d04f15bb133d0d9e34ef452` |
| `wasm_sdk_probe/dist/profiles/e2-editor-v12/sdk-manifest.json` | `2734229351dac1da514df08ada878a47af442d729ff42195d43e5d9c6794d5be` |

All twenty are re-hashed into `identity.json` before invocation 1, together
with `google-chrome --version`, `uname -r`, `git rev-parse HEAD`, and the
sha256 of every script the executor writes (taken **after** writing, **before**
invocation 1). Each probe report also carries `inputs[].sha256` in band, and
§4.5 requires the two to agree.

**Also before invocation 1, once**: run the builder's own verifier and save its
output to `build-verify.txt` —

```
python3 /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/build_row_ladder.py --verify
```

It must print `content.xml identical=True` for `rows20` and `rows50` and the
line `verify: the banked fixtures are what this script produces`. `--verify`
builds into a `TemporaryDirectory` and writes nothing to `OUT_DIR`. **Run
`--verify` and nothing else** — never `--rows`, never `--split` (§2.4 item 2).

---

## 3. Repeats, the two run shapes, and the budget

### 3.1 Repeats are the measurement

- **N = 1 is disqualified by house rule.** `AGENTS.md`'s own wording: an
  intermittent defect measured once gives you a confident and wrong conclusion.
  Finding 068's arm was FAIL then PASS on the same page.
- **N = 2 cannot break a tie.** Two disagreeing runs give a split with no
  information about which is typical.
- **N = 3** is what the 2026-09-07 timing reconciliation used and what the main
  session accepted as discharging the diagonal half. Using less here would make
  the off-diagonal half weaker evidence than the half it completes.
- **Unanimity, not majority.** A 2-of-3 result is **SPLIT**, not "reproduced".
  The effect being measured is categorical — 1.4 s versus does-not-finish — and
  a categorical effect that flickers is precisely outcome E's subject, not a
  vote to be won.
- **Why not more than 3**: each Row-A repeat spends a 180 s timeout, and the
  banked evidence being checked is itself N = 1 per point (N = 2 for A6, N ≥ 3
  for the anchors). Three already exceeds the evidence under test.

The handoff's estimate for this work was "roughly ten opens". That is the N = 1
count. This protocol deliberately triples it: 30 spreadsheet opens plus 6
control opens.

### 3.2 Shape A — the `Index2 = 36` row

One invocation of `wasm_sdk_probe/tools/probe_ods_on_profile.py`, cwd
`wasm_sdk_probe`, absolute paths, all six points plus the control in **one
browser session** (the probe creates and disposes a fresh engine per case):

```
python3 tools/probe_ods_on_profile.py \
  --profile e2-editor-v12 \
  --control /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-index20-index236.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-index25-index236.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-index30-index236.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-index33-index236.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-index34-index236.ods \
  --fixture /home/jiajun/LibreOffice/study_LiteCore/findings/evidence/089/tdf149752-index35-index236.ods \
  --open-timeout-ms 180000 --timeout 900 \
  --out <evdir>/A-<n>-report.json
```

`--open-timeout-ms 180000` is the SDK's own default and the value every banked
row was taken at. **Do not raise it to 1,800,000**: that question
(`rows36-open-timeout-1800s.json`) is already answered once and re-answering it
is not this protocol's question. `--timeout 900` is a ceiling, not a duration —
it exists so that up to four *unexpected* hangs cannot cut the invocation short
the way `ladder-rows36-first-timeout.json` was cut short.

Expected page time ≈ 190 s (1.8 s control + five ~1.3 s opens + one ~181 s
timeout); expected wall clock ≈ 4 min including browser boot and teardown.

### 3.3 Shape B — the `Index2 = 35` row, plus both anchors

```
python3 tools/probe_ods_on_profile.py \
  --profile e2-editor-v12 \
  --control .../dist/e2-fixtures/d1-anchors.odt \
  --fixture .../findings/evidence/089/tdf149752-index100-index235.ods \
  --fixture .../findings/evidence/089/tdf149752-index36-index235.ods \
  --fixture .../findings/evidence/089/tdf149752-rows35.ods \
  --fixture .../findings/evidence/089/tdf149752-rows36.ods \
  --open-timeout-ms 180000 --timeout 700 \
  --out <evdir>/B-<n>-report.json
```

**Why the hang anchor `rows36` is in Shape B at all**, given that it is already
discharged: without it, every case in a Shape B invocation is expected to open,
and "the harness produced only `opened: true` because everything opened" and
"the harness can only produce `opened: true`" are the same picture. This is the
§6 red-case principle applied in band, and it is the same reason `--control` is
mandatory. The 180 s is the price.

**The hang is last in both shapes**, matching every banked invocation that
contained one (`grid-index34-and-35-with-index2-36.json`,
`ladder-rows25-rows40.json`, `ladder-rows34-35-36-confirm.json`).

### 3.4 Order, the session-position confound, and the tie-break

The banked Row A points were taken across **three** invocations (A1 with B1; A2,
A3, A4 together; A5 with A6). Shape A puts all six in **one** session, which the
banked data never did. That difference is named here rather than discovered
later:

- **Ordering control.** Repeats 1 and 2 of each shape run the fixtures in the
  order written above (ascending `Index` for Shape A). **Repeat 3 reverses the
  order of the opening fixtures**, keeping the hang last: Shape A becomes 34,
  33, 30, 25, 20, then 35; Shape B becomes `rows35`, `index36-index235`,
  `index100-index235`, then `rows36`. If a point's verdict depends on its
  position in the session, the two orders disagree and the point SPLITS.
- **Tie-break, pre-registered.** If **exactly one** point splits across its
  three repeats, the executor may spend up to **two reserve invocations** on a
  shape containing the control, that point alone, and the shape's hang case, in
  that order. If the five measurements are then unanimous, the point takes that
  verdict; if not, it stays SPLIT. If **two or more** points split, no tie-break
  is run — trigger E2 has already fired.

### 3.5 Budget

**One invocation** = one `probe_ods_on_profile.py` run (~4 min expected;
worst case ~19 min for Shape A if every point hangs).

**Budget: 8 invocations.**

| invocation | what |
| --- | --- |
| 1, 2, 3 | Shape A, repeats 1–3 (repeat 3 reversed) |
| 4, 5, 6 | Shape B, repeats 1–3 (repeat 3 reversed) |
| 7, 8 | reserve |

Reserve invocations may be spent **only** on: replacing a voided invocation, or
the §3.4 single-point tie-break. No other variation may be introduced, and
nothing may be added to the criteria mid-flight (`AGENTS.md` §9 — an addition
must precede satisfaction, be forced and named, pass the form test, and carry a
deadline; a variation invented after seeing invocation 1 satisfies none of
them).

Expected total wall clock ≈ 25 min of runs (18 min of which is timeouts), ≤ 90
min worst case.

**Stop rule.** Stop as soon as both shapes have three non-void repeats and
`reduce.py` has produced a verdict with all §6 red cases recorded. Stop
unconditionally after the 8th invocation.

**Default if the budget is exhausted without three non-void repeats of both
shapes**: outcome **V** (§1.2), whose written record is §5.4's, with the
obstacle named instead of the variance.

---

## 4. The numeric predicate, fixed before any run

### 4.1 The primary predicate is categorical

The claim under test is made of open-versus-does-not-open, not of milliseconds.
So:

**For a point banked as OPENED**, one repeat REPRODUCES iff, in that
invocation's report, the case with that `name` has `opened` truthy, `error ==
null`, `opened.parts == 2`, and a `tile.ok == true`. It CONTRADICTS iff `opened`
is falsy.

**For a point banked as TIMEOUT** (A6, K2), one repeat REPRODUCES iff `opened`
is falsy, `error.code == "TIMEOUT"`, `error.message` contains `180000`, and
`180000 ≤ elapsedMs ≤ 182000`. It CONTRADICTS iff `opened` is truthy. Anything
else (a non-TIMEOUT error, an `elapsedMs` outside that window) makes **that
repeat void for that point**, named, and does not count toward N.

**A case with `elapsedMs: null`, `opened: false` and `error: null` is an ABSENT
MEASUREMENT, not a failure** — the reading rule `ladder-2026-09-06.txt:31-36`
already wrote for `rows37`. It is void for that point, and if it occurs the
invocation's `progress.done` / `timedOut` fields say why.

**Across repeats**: a point REPRODUCES iff all three (or five, after tie-break)
non-void repeats reproduce; CONTRADICTS iff all of them contradict; SPLITS
otherwise.

### 4.2 The timing band, for points banked as opened

Let `r = median(today's elapsedMs across the repeats) / banked elapsedMs`.

| band | verdict recorded |
| --- | --- |
| `0.5 ≤ r ≤ 2.0` | **reproduces the banked figure** |
| `0.25 ≤ r < 0.5` or `2.0 < r ≤ 4.0` | **outside the band, same order of magnitude** — recorded on its own line, never folded into "reproduced" |
| `r < 0.25` or `r > 4.0` | **does not reproduce the banked figure** — the `tdf161948` class |

The timing band **never overrides the categorical verdict**. A point that opened
in all three repeats but landed at `r = 0.1` is categorically REPRODUCES and
timing-wise DOES-NOT; both are written, and the outcome selection in §1.2 uses
the categorical one. This is deliberate: the 2026-09-07 reconciliation already
showed that this machine can move a wall-clock figure by 26.6x without changing
whether the file opens.

### 4.3 Why those bands, against what 2026-09-07 already measured

| observation | ratio | how it was read |
| --- | ---: | --- |
| `rows35` banked twice on 2026-09-06: 1,245 ms (`ladder-2026-09-06.txt:19`) vs 1,260 ms (`:12`) | 1.01x | same-day, same-file spread |
| `rows35`, 2026-09-07 mean 1,382 ms vs banked 1,245 ms | **1.10x** | **reproduced** |
| `index36/index2-35`, 2026-09-07 mean 1,157 ms vs banked 1,589 ms | **0.73x** (1.37x the other way) | **reproduced** |
| whole banked off-diagonal open population, 1,223–1,589 ms | 1.30x extreme-to-extreme | context |
| `tdf161948`, 2026-09-07 mean 1,155 ms vs banked 30,688 ms | **0.038x** (26.6x) | **did not reproduce** |

So **2.0** sits at least 1.45x above every ratio this tree has ever read as
"reproduced", and **4.0** sits 6.6x below the only ratio it has read as "did
not". The interval between 1.4x and 26.6x is **unpopulated by any measurement on
this tree**. Splitting it at 2 and 4 puts a deliberate *indeterminate* band over
the region where nothing has ever landed, so a novel result is recorded as
unanticipated rather than rounded into "fine" or "broken".

**No timing band applies to a TIMEOUT.** The 180 s ceiling truncates the
measurement; the banked spread (180,919–181,017) and 2026-09-07's
(180,835–180,854) differ by about 0.1% and measure the harness's own overhead,
not the document. `ladder-2026-09-06.txt:27-30` says the same thing.

### 4.4 Recorded per case, never interpreted

`workerCrashed`, `warnings[]` (verbatim, including any `worker sent an error!`
line), `inputBytes`, `inputSha256`, `tile.sha256`, `tile.nonPaperPixels`,
`opened.parts`, `viewReady.atMs`, and every `stages[]` entry. These go into the
per-repeat table in `RESULT.md` under a heading that says they are recorded and
not interpreted. **None of them may change a verdict**, and none may be named as
a cause (§9). §7.2 explains why `workerCrashed` in particular must be recorded.

### 4.5 Per-invocation non-vacuity gate

An invocation is usable only if all of:

- `verdict.controlOdtOpened == true`;
- `openTimeoutMs == 180000`;
- every `inputs[].sha256` equals §2.5;
- `progress.fatal == null`;
- **both outcome values are present among the spreadsheet cases**: at least one
  `opened` truthy and at least one `opened` falsy. This is red case RC-1 (§6)
  evaluated in band, on every invocation, and it is why each shape carries a
  hang.

If the ODT control did not open, **nothing in that report is about Calc** — the
report's own `verdict.note` says so. The invocation is void, the executor does
not read its spreadsheet rows, and a reserve invocation replaces it.

### 4.6 `reduce.py` — the form-two instrument

Written by the executor into the evidence directory. Input: the `A-*.json` /
`B-*.json` reports and `identity.json`. Output: `regrid-verdict.json`,
containing per point — the banked verdict and figure with its source string, the
per-repeat categorical verdicts, `r`, the band, and the point verdict
(REPRODUCES / CONTRADICTS / SPLITS / VOID) — plus the selected outcome letter
and the trigger that selected it. It must:

- **refuse to run on zero reports** (`status: "no-reports"`, non-zero exit);
- **void** any report failing §4.5;
- name every point it could not decide, rather than omitting it;
- print the outcome letter **and** the trigger clause it fired on, verbatim from
  §1.2.

It contains no threshold that is not written in this document.

---

## 5. The discriminator: what retires the claim, what restores it, what leaves it undecided

### 5.1 The claim, decomposed

"`Index ≥ 35` AND `Index2 ≥ 36` — both axes, neither alone" is two sub-claims,
and the off-diagonal points are the only evidence either has:

- **N1 — `Index2 ≥ 36` is necessary and not sufficient.** Supported by A1–A5
  opening at `Index2 = 36`, and by A6 not opening. Killed if any of A1–A5 fails
  to open (then `Index2 = 36` is closer to sufficient than banked), or if A6
  opens (then the corner is not there).
- **N2 — `Index ≥ 35` is necessary and not sufficient.** Supported by B1 and B2
  opening at `Index2 = 35` with `Index` at 100 and 36. Killed if either fails to
  open.

### 5.2 What restores it

Outcome **R** of §1.2 and nothing weaker. All eleven points unanimous and
reproducing; controls clean. The sentence it licenses is written out in §1.2 and
must be quoted with its date and its point list. It does **not** license the
region between the sampled points, and any later summary that drops the date or
the point list has widened the claim again.

### 5.3 What retires it

Outcome **C**, with the sub-case named:

- **C1** — one of A1–A5 does not open. N1 falls.
- **C2** — B1 or B2 does not open. N2 falls.
- **C3** — A6 opens. The corner falls, and the 2026-09-07 diagonal discharge
  does not save the claim, because the diagonal never contained A6.

In every sub-case the licensed record is the bounded per-point sentence of
§1.2 plus a correction appended to 089 (`AGENTS.md` §10: append only, name what
it supersedes, leave the original text). **No replacement frontier is proposed
by this task under any circumstances** — proposing one from eleven points is the
same move that produced the one-axis ladder reading that 089 already had to
correct.

### 5.4 What leaves it undecided — including the case the brief names explicitly

Outcomes **S**, **E** and **V**.

**Outcome E is the one worth writing out in full: the instrument's own
run-to-run variance exceeds the effect.** Its triggers are E1/E2/E3 in §1.2. In
that outcome the following is written, in these places, and nothing more:

1. **`findings/evidence/089/off-diagonal-regrid-<date>/RESULT.md`** — the full
   per-repeat table for every point (nothing omitted, including the repeats that
   disagree), which trigger fired and its measured value, the anchors' behaviour
   run by run, the ODT control's figure in every invocation, and this sentence
   verbatim:

   > **NOT RE-MEASURED.** On `<date>`, on `e2-editor-v12`, the run-to-run
   > variance of this instrument on this machine exceeded the effect the grid is
   > made of: `<trigger E1/E2/E3, with its measured value>`. The obligation
   > therefore stands — `Index ≥ 35` AND `Index2 ≥ 36` may not be repeated. It
   > is **not** retired either: a claim that could not be measured has not been
   > refuted. What is registered is the obstacle, named above, so that the next
   > attempt starts from it rather than from the question.

2. **One appended section under `## Execution record`** at the end of this file
   — the pointer and the headline, not a duplicate of `RESULT.md`.

3. **A named-unmeasured registration proposed for 089** (landing it is the
   owner's call, not the executor's). `AGENTS.md` §3 requires saying which of
   the two kinds it is, and this is the second kind: **there is a claim and no
   instrument that can currently decide it** — not "there is behaviour and
   nothing guarding it". Proposed id and wording:

   > **NU-089-3 — the off-diagonal grid could not be re-measured.** The
   > instrument's run-to-run variance on this machine exceeds the categorical
   > effect. Status: open. Default if never resolved: §1.3.

**Do not, in outcome E, quote any point's numbers as if they were the answer**,
and do not report "mostly reproduced". That is the specific misreading this
protocol exists to prevent, and it is the reading a noisy instrument produces
for free.

---

## 6. Red cases — the harness must be shown to produce a different answer

`AGENTS.md` §6: a checker that returns green only proves it can return green.
Each is written to `redcase-RC-<n>.json` in the evidence directory. RC-3, RC-4
and RC-5 need no browser: they are re-derivations over banked reports, which is
possible because `reduce.py` reads reports rather than the world.

**RC-1 — both outcomes, live, in every invocation.** Already stated as §4.5's
last clause. In Shape A the same session must produce `opened: true` for A5 and
`opened: false` for A6; in Shape B, `opened: true` for `rows35` and
`opened: false` for `rows36`. **Required record**: `"bothOutcomesSeen": true`
per invocation. An invocation where every spreadsheet opened, or every one timed
out, is void — not because the result is unwelcome but because that invocation
did not demonstrate it could have said the other thing.

**RC-2 — a third value in the "did not open" column.** One extra invocation
(Shape B plus `--truncated`), where the truncated control is a copy of
`tdf149752-index20-index236.ods` cut to its first 4,096 bytes, written **into
the scratchpad, never into `findings/evidence/089/`**. `probe_ods_on_profile.py`
stages `--truncated` **last**, after every fixture, so it costs nothing if a
fixture hangs first. **Required record**: that case has `opened` falsy with an
`error` whose `code != "TIMEOUT"` — proving "did not open" is not a constant
that only ever means the 180 s ceiling. **Pre-registered alternative**: if the
truncated file instead times out, or opens, record that verbatim and state
plainly that RC-2 did not demonstrate a third value. **Do not repair it** by
choosing a different corrupt file until one gives the wanted answer — that is
selecting a red case for its colour. This invocation is charged to the reserve
budget only if a reserve invocation is still free after §3.5; otherwise RC-2 is
recorded as not attempted, with the reason.

**RC-3 — the reducer must be able to say RETIRED.** Copy one banked
`A-<n>-report.json` into the scratchpad, flip A3's `opened` object to `null`,
and run `reduce.py` over the copied set. **Required record**: the outcome letter
changes from `R` to `C`, with sub-case `C1` and the point named. If the letter
does not change, `reduce.py` is not reading the field it claims to read,
**every verdict it produced is void**, the fix is made in `reduce.py`, and all
verdicts are re-derived over the **same banked reports** — no browser is re-run.

**RC-4 — the reducer must notice a fixture swap.** Same copy, with one
`inputs[].sha256` altered by a single hex digit. **Required record**:
`{"status": "void", "reason": "...", "mismatches": ["<path>"]}` naming the
path. A reducer that reports a clean grid over reports whose inputs it cannot
vouch for is measuring documents it has not identified.

**RC-5 — non-vacuity.** Point `reduce.py` at an empty directory. **Required
record**: `{"status": "no-reports"}` and a non-zero exit. Not "0 of 11 points
inconsistent, all good". Same rule as `probe_ods_on_profile.py`'s own
`--corpus selected nothing` guard and the 2026-08-29 census scripts: a sweep
that found zero files must be red.

---

## 7. Named-unmeasured registrations — open questions, not hypotheses this run will confirm

### 7.1 NU-089-1 — only the 30-s-class file moved between 2026-09-06 and 2026-09-07

**The fact.** `tdf161948_NaturalSortSaveLoad.ods` is banked at **30,688 ms**
(`findings/evidence/m4-ods/04-sweep-v12.json:33191`, field `elapsedMs`) and
measured at 1,014–1,397 ms in three repeats on 2026-09-07, plus 1,046 and
1,090 ms in the two phase-1 runs earlier the same day — five measurements, two
sessions, one day, all in the 1.0–1.4 s band. In the *same three repeats*,
`rows35` came in at 1.10x its banked figure and `index36/index2-35` at 0.73x —
i.e. **the two second-class opens did not move at all.**

**Why it is registered rather than explained.** The live hypothesis is that
2026-09-06 carried an orphaned headless Chrome for about four hours plus the
owner's own browser
(`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`). If contention were
the whole story, the second-class opens should have inflated on 09-06 too, and
they did not. **That asymmetry is unexplained. It is open.**

**What this protocol does about it: nothing, deliberately.**

- No point in this grid is 30-s class. Every opening point here is 1.2–1.6 s.
- Therefore **a clean outcome R here is not evidence about NU-089-1** in either
  direction. It re-measures the same class of file that already reproduced.
  Writing "the regrid reproduced, so the 09-06 contention story holds" would be
  exactly the substitution this tree keeps catching: signing for B with A's
  measurement.
- The executor may not add a 30-s-class fixture to any shape to "check this at
  the same time". That is an addition to a running protocol (`AGENTS.md` §9) and
  it would change the wall-clock shape of every invocation it appears in.

**Default if never measured**: NU-089-1 stays open and is quoted as open. The
26.6x figure is a measured discrepancy with an unexplained selectivity, not a
solved one.

### 7.2 NU-089-2 — `workerCrashed: true` on cases that nonetheless opened

**The fact, counted rather than eyeballed.** Across the eight banked
`grid-*.json` / `ladder-*.json` / `rows36-open-timeout-1800s.json` reports there
are 14 spreadsheet cases that opened. **Six of them carry
`workerCrashed: true`** together with a warning reading `worker sent an error!
http://127.0.0.1:<port>/profiles/e2-editor-v12/probe.js:7: Uncaught
RuntimeError: memory access out of bounds`, while still recording `opened`,
`viewReady`, `parts: 2` and a tile:

- `(100,35)` in `grid-index100-35-and-index20-36.json`
- `(34,36)` in `grid-index34-and-35-with-index2-36.json`
- `(36,35)` in `grid-index36-index2-35.json`
- `(35,35)` — `rows35` — in `ladder-rows34-35-36-confirm.json`,
  `ladder-rows25-rows40.json` and `rows36-open-timeout-1800s.json`

The eight cases without it are `(20,36)`, `(25,36)`, `(30,36)`, `(33,36)`,
`(34,34)`, `(25,25)`, `(30,30)`, `(20,20)`. **It also reproduced on
2026-09-07**: `rows35` and `index36/index2-35` both carry
`workerCrashed: true` in all three of
`cpu-or-wait-2026-09-07/timing/timing-repeat-{1,2,3}.json`, while the ODT
control and `tdf161948` in the same invocations do not.

The field is set when the case's engine emits a `worker-crashed` event
(`wasm_sdk_probe/web/ods-decisive-probe-app.js:163-164`).

**Why it is registered.** It is a second, stable, reproducing dependent variable
that no section of 089 has ever remarked on, and **three of the six banked
instances are grid points this protocol re-measures**, including B1 and B2 —
the entire evidential support for "`Index ≥ 35` is not sufficient". "That point
opened in 1,486 ms" is therefore not the whole of what the banked artefact says
about it.

**What this protocol does about it**: records `workerCrashed` per case (§4.4),
in the per-repeat table, with the warning text verbatim. It does **not** enter
any verdict, does **not** void a case, and **no cause, mechanism, or
correlation-as-explanation may be written for it** (§9). Whether an
`opened: true` with a crashed worker is the same event as an `opened: true`
without one has never been measured, and this protocol does not measure it.

**Default if never measured**: NU-089-2 stays open, and any future quotation of
a banked open figure for `(100,35)`, `(34,36)`, `(36,35)` or `(35,35)` carries
the crash flag with it.

---

## 8. Operational constraints for the executor

### 8.1 The machine

- **Headless only.** `ChromeSession` already passes `--headless=new`. Do not
  launch a headed browser, do not connect to the owner's Chrome, do not touch
  the desktop session, **do not start or use Orca** — the owner is at the
  machine.
- **Count the Chrome processes before starting anything**, and record the count
  in each invocation's meta file. Iterate `pgrep -x chrome` and `pgrep -x
  google-chrome` and read `/proc/$p/cmdline` for each pid found. **Never
  `pkill -f` and never `pgrep -f`** — they match the agent's own command line
  and have killed a shell mid-command on this machine. If cleanup after an abort
  is needed, kill **by pid**, and only pids whose `/proc/$p/cmdline` contains
  that invocation's own recorded `--user-data-dir=` value.
- **The 2026-09-07 discriminator for a dirty machine**, worth knowing: a busy
  desktop is what produced 26.6x once already. A non-zero foreign Chrome count
  does not void an invocation, but it is recorded, and if it is non-zero the
  executor says so at the top of `RESULT.md`.
- **The soak schedule is with the owner** as of 2026-09-07; there are no longer
  fixed clock windows. Before each invocation, check that no soak run is in
  flight (foreign Chrome count, plus `git log -3` for a fresh
  `queue-v12-cutover-soak` commit). If one is, wait. A second headless Chrome
  contending with a gate measurement is the thing the old windows existed to
  prevent.

### 8.2 `/tmp`

- `/tmp` is **tmpfs, 16 GB**, and it filled to **98%** on 2026-09-06; two runs
  were killed for low memory. Check `df /tmp` before invocation 1 and record it.
- After each invocation, remove only `/tmp/ods-decisive-*` and
  `/tmp/wasm-sdk-probe-chrome-*` whose mtime falls inside that invocation's own
  window. The probe removes its own scratch in a `finally`, but an aborted run
  leaves both.
- **Leave every `/tmp/candidate-round-*` directory alone.** They belong to the
  cutover soak; `/tmp/candidate-round-tx3ue8b9` in particular mirrors the v46
  page and is cited as evidence. The rule is the prefix, not the list.
- Delete nothing outside the two prefixes named above, and delete nothing that
  predates the invocation.
- Scratch for anything that is not evidence — the RC-2 truncated file, the RC-3
  and RC-4 mutated report copies — goes under
  `/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/5553bcc0-16b3-4240-9ee3-0570a4c16e23/scratchpad`.

### 8.3 The tree

- **Nothing identity-bound to the v12 cutover gate may move.** The gate is at
  6 of 12 clean soak runs and every bound identity is load-bearing: profile
  `e2-editor-v12`, candidate page
  `9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c`, frozen
  shell generation **v48**, cutover generation **v47**. A page move voids every
  identity-bound measurement; the count has gone 10 → 0 twice this week because
  of exactly that.
- **Nothing may be written** under `wasm_sdk_probe/web/`,
  `wasm_sdk_probe/dist/`, any profile, any `check_*.py` or other judge, or
  anywhere under `findings/evidence/queue-v12-*`. Reading them is required and
  fine — the probe mirrors `dist/` with symlinks into a scratch root and its own
  docstring states that a run writes nothing under `dist/`, `web/` or `sdk/`.
- **Never pass `--write`**, or any other mutating flag, to any tool that has
  one. This is a measurement, not a landing.
- **Do not run `make`, do not relink, do not rebuild anything.**
- **`build_row_ladder.py --verify` only** — never `--rows`, never `--split`
  (§2.4 item 2: they overwrite banked fixtures in place).
- **The guard, in band.** `git status --porcelain` immediately before and
  immediately after every invocation, both saved into that invocation's meta
  file, compared **against that invocation's own "before" snapshot** rather than
  a baseline written here — the soak commits into this tree between runs and a
  frozen baseline would go stale. The only delta this task may cause is **new
  files under `findings/evidence/089/off-diagonal-regrid-<date>/`**. Any other
  delta that is not plainly the soak's own paths under
  `findings/evidence/queue-v12-cutover-soak/`: **stop and report**. Touch none
  of the soak's paths for any reason.
- Each invocation's meta file records `startedAt` / `completedAt` in **both UTC
  and CST**. A report with no wall-clock time is not a dated report — the
  2026-09-03 adjudication on the soak bank.
- **The executor commits nothing.** It writes the evidence directory and the
  `## Execution record` section, and reports. Whether any of it is committed is
  the owner's call.

---

## 9. Standing prohibition: no cause may be named for 089, anywhere

This is not advice and it is not scoped to `RESULT.md`. It binds every file this
task produces, the `## Execution record` section, and the executor's report to
the caller.

**089 has refused attribution twice on the record.**

1. The 2026-09-05 bisect named `number-rows-repeated` as the only conspicuous
   difference; a single-variable test **refuted** it, and the finding says
   plainly that writing it up would have sent a triager after a dead direction.
2. The 2026-09-06 ladder was read as "something switches between a range of 34
   rows and 35" — and the ladder had moved **both** ranges together, so
   everything it established was about a diagonal. The correction is in the
   finding.

Two candidate mechanisms are already excluded on the record (a forced hard
recalculation on load — the default is `RECALC_NEVER` and is shared with native;
and `ScQueryCellIteratorSortedCache` — compiled out entirely, tdf#151958), and
**neither exclusion points at a replacement.**

**`futex_do_wait` is a measurement, not an explanation.** So is `ep_poll`, so is
"~1,600 voluntary context switches", so is "~1% of one core across 160.5 s".
Those are recorded in `cpu-or-wait-2026-09-07/` under a heading that says they
are not interpreted, and they stay that way.

Specifically forbidden in anything this task writes: naming `COUNTIF`, the
array-criterion evaluation, formula evaluation at load, the overlap between
`Index2` and the 99 cells that resolve through it, the `memory access out of
bounds` worker error of §7.2, thread wake-ups, machine contention, or any other
mechanism **as the cause of 089 or of any point's verdict**. The structural
difference between the axes (`Index` is plain data on `Liste`; `Index2` is the
same column as the 99 array formulas on `Auswertung`) is recorded in 089
explicitly **as a structural difference and not as a cause** — repeating it is
fine; upgrading it to an explanation is not.

Every sentence this task may write about a point has the same shape: *on this
date, on this profile, this file did or did not open within 180 s, N times.*
Nothing is licensed past that. Finding 040's precedent, quoted in 089 itself: a
confident wrong attribution costs more than the open question.

---

## Execution record

*(appended by the executor after the runs; nothing above this line is edited)*
