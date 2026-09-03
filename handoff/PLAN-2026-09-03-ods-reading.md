# Reading ODS: what is owed, written down before the runs that would satisfy it

Written 2026-09-03, after the owner reordered the roadmap: **reading ODS comes
before M3 (the Nextcloud app)**. This is the first third of M4 in
`research/ROADMAP-2026-08-20-milestones.md`. **ODP and ODG are not in scope**;
§7 records what they would cost separately so the decision is not made by
drift.

This file follows the rule the v11/v12 cutover horizon established: the criteria
are fixed **before** any run that would satisfy them, and thereafter the file is
**append-only** — corrections go at the end and name what they supersede, so
`git diff` on it only ever adds lines.

Acceptance criteria obey `AGENTS.md` §1: every gate criterion is form 1
(per-instance) or form 2 (tool-closed enumeration). Every criterion carries the
sentence required by §2: *if this is never done, the default conclusion is …*.

## 0. Owner's decisions, 2026-09-03

**Route: B — a separate read-only viewer.** Not the existing editor page with
editing disabled. The reasons, recorded because a later reader will otherwise
re-open this: route A would touch `sdk/document-sdk.js`,
`editor-shell/editor-session.js` and `web/e2-editor-app.js`, all three bound by
the E1-C and E2-C verdicts and all three inside the shell bundle; and it would
put a Writer-shaped `getState` handshake in front of every spreadsheet. Route B
touches none of them and is the shape a Files-app preview needs. **Whether a
spreadsheet can be edited is M5's question, not this milestone's.**

**Must-open class: up to 10 sheets, up to 100,000 populated cells, no images.**
Taken as proposed. A fixture outside the class may still be measured and
recorded; it just does not gate.

## 1. The premise this milestone rests on, and its measured limits

M4's gate 0 asks whether a core carrying the spreadsheet module builds and
loads. **For ODS it already does**, as a side effect of the accessibility work,
and no owner rebuild is owed:

* `wasm-lite/build-a11y-gate0/autogen.input:3` — `--with-wasm-module=writer calc`
* `.../instdir/program/soffice.js.linkdeps` lists `-lsclo -lscdlo -lscfiltlo
  -lscuilo -lwpftcalclo`
* `.../instdir/program/services/services.rdb` registers
  `com.sun.star.comp.Calc.SpreadsheetDocument` and `Calc.XMLOasisImporter`
* literal symbol counts, `grep -a -o -F … | wc -l` over `probe.wasm`:

| | `e2-editor-v12` | `e2-editor-v8` (ships today) |
|---|---|---|
| `com.sun.star.sheet` | **398** | 16 |
| `ScDocument` | **53** | 1 |
| `ScDocShell` | **18** | 0 |
| `SdDrawDocument` | **0** | 0 |

and that core is the one `e2-editor-v12` is built from, with 8 clean
product-path runs banked on it.

**Three limits on that premise, all measured, all recorded here so they are not
rediscovered:**

1. **The core is `writer calc`, not the `calc impress writer` M4 asks for.**
   `config_host.mk` carries `ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS=TRUE`.
   Gate 0 is paid for **for ODS only**.
2. **Configuration was never the missing half; code was.** v8's image already
   carries `/instdir/share/registry/calc.xcd`. Presence of the type
   registration says nothing about whether the module is linked.
3. **XLSX does not ride along.** `calc_MS_Excel_2007_XML` does not occur in the
   a11y core's `calc.xcd` (the Excel 97/95/4.0 types do).

## 2. The constraint everything is sequenced against

The `e2-editor-v12` cutover gate is **running** (8 of 12 clean runs;
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`). Its criteria may not be
moved.

**What actually disturbs it** — stated precisely, because the loose version
("any shell change") over-forbids and would have stalled this work for no
reason. A run is refused, or the count restarts, when either:

* one of v12's five bound identities changes, or
* one of the **13 paths in `e2/editor-shell-v2-bundle-v43.json`'s `included`
  list** changes — `served_shell_identity()` hashes exactly those
  (`tools/run_e2_c_product_path.py:2205`).

A relink that writes a **different** profile directory touches neither. New
files outside those 13 paths touch neither.

**And one that is not about files at all: W0.** Nothing that drives a browser
may overlap a soak run. CPU contention can push a check to NOT_ESTABLISHED, and
an unexpected NE restarts the count at zero. This is the one way ODS work can
damage the gate without editing a gated file.

## 3. The gate — "we can read ODS"

Against the relinked candidate (`e2-editor-v13` or whatever it is named) on its
own candidate page, built through `repointed_page()`.

**Truth source**: `test-docs/ods/manifest.json`, **generated** by
`tools/create_ods_corpus.py` from the directory's contents — sheet count and
per-sheet expected text from the generator for synthetic fixtures, from the
native oracle for upstream ones. Injection test: add a `.ods` without
regenerating and G1 reddens; edit a fixture in place and its sha256 stops
matching.

| id | criterion | form | if this is never done, the default conclusion is |
|---|---|---|---|
| **G1** | **Closure.** Every `.ods` under `test-docs/ods/` has a manifest entry with a matching sha256, every entry has a file, and the sweep report holds exactly one record per entry, keyed by sha256. | 2 | …no corpus claim exists; the gate stays closed. |
| **G2** | **Open.** For every entry: `opened` arrives, `view-ready` within 60 s, `documentType == "spreadsheet"`, `parts == manifest.sheets`, no `LOK_ERROR`/`BUSY`/wedge. An entry may declare `expect: "refused"` with a reason; then a **typed refusal before the engine queue** is the required outcome and the entry is listed by id. | 1 | …no file has been shown to open on the candidate; the gate stays closed. |
| **G3** | **Content, read from state and not from pixels.** For every entry and sheet: `set_part(k)` then `.uno:SelectAll` + `getTextSelection("text/plain")` equals the manifest's expected text, byte-equal after CRLF normalisation. | 1 | …fidelity is unmeasured; the gate stays closed. **This is the criterion a blank canvas cannot satisfy.** |
| **G4** | **Paint.** For every entry and sheet: a 1024×1024 tile at (0,0) returns OK, `documentSizeChanged == false` on the second paint, and the tile is **not** byte-equal to the empty-sheet control where the manifest says there is content in that region and **is** where it says empty. Both controls are corpus entries. | 1 | …tiles have never been observed on a spreadsheet; the gate stays closed. |
| **G5** | **Sheet switching.** `three-sheets-distinct.ods`: tiles of parts 0/1/2 pairwise distinct. `three-sheets-identical.ods`: pairwise identical. `part_name` list equals the manifest's names. | 1 | …sheet switching is unmeasured; the gate stays closed. |
| **G6** | **Memory.** For every entry: peak `sbrk` over open + one tile per sheet + close is **< 939,524,096 bytes (896 MiB)**. Leak bound: `open.begin` sbrk of open *n+1* minus open *n*, over 5 opens of one entry, ≤ a bound fixed from W1's noise floor **before any ODS run counts**. | 1 | …the milestone would ship with the memory question open on a fixed 1 GiB link. **That is not allowed**; the gate stays closed. |
| **G7** | **No ODT regression.** The existing 40-check net on the candidate page: `ok: true`, 38 PASS / 2 NE with the NE set exactly `{notice-action-recovers-the-session, a-refused-action-is-reported-and-changes-nothing}`, reconciled `kind == "candidate-cutover"`. | 2 | …the ODT product is assumed unaffected; the gate stays closed. |
| **G8** | **Same core, byte for byte.** The candidate's `base`/`cjk`/`fallback` packs are byte-identical to v12's (`9901e9be…`, `b76b0433…`, `33856e2a…`), `probe.wasm` differs, and the link's `soffice.js.linkdeps` is the a11y core's. Catches a relink against the wrong `LOBUILD`. | 1 | …the candidate may carry a different core than the one measured; the gate stays closed. |
| **G9** | **The user's path.** Through the viewer page's own file input, not the harness's `open`: for `three-sheets-distinct.ods` the page reports `parts == 3`, three tab elements whose text equals `part_name`, clicking tab *k* makes the **engine's** current part *k* (read back, not inferred), and each first tile is G5's tile. | 1 | …only the harness's path was measured; the gate stays closed. |
| **G10** | **Human round**, once, on the final candidate, in a real browser. Open one upstream file with charts and one synthetic 100k-cell file; switch sheets; scroll to the bottom-right used cell; zoom. **Mechanical half, gating**: the page state after each action matches what G9 reads. **Judgement half, recorded only**: what the human saw. | 1 mechanical / recorded | …the cutover proceeds on G1–G9 with the deferral written into the record and carried by the existing revert trigger — the same escape 4b has. |

### Injection tests, exhibited before the first green run (§6)

1. add `test-docs/ods/zzz.ods` without regenerating → **G1 red**
2. feed the ODT control down the ODS path → **G2 red** on `documentType`
3. set an entry's `sheets` to 1 for the three-sheet fixture → **G2 red**
4. swap two sheets' expected text → **G3 red**
5. a truncated zip → typed refusal, and an `expect: "refused"` entry shows
   refusals are enumerable rather than merely absent
6. point the sweep at an empty directory → **G1 red**; "zero files" must be red,
   never "zero problems"

### Registrations (`AGENTS.md` §3)

* `refreshEditorAccessibility()` runs at every open and calls
  `setAccessibilityState(view, true)`. Its effect on a **Calc** view is
  **unknown**: registered as *has behaviour, nothing guarding it*, until W2
  measures it. If it wedges or errors that is a finding, not a criterion change.
* W2's and W5's opens spoof an `.odt` name to get past finding 013's extension
  check. Registered as **diagnostic**: every such report carries
  `nameSpoofed: true` and is never banked as product evidence.

## 4. Memory: the model, the kill line, and the one number that decides

Linear memory is fixed at 1,073,741,824 bytes by a **probe link flag**
(`-sTOTAL_MEMORY=1GB`, no `ALLOW_MEMORY_GROWTH`) — raising it is a relink of
ours, not an owner rebuild, and would need its own gate. `sbrk` is the break
address; the abort is `sbrk` failing near 1 GiB. The MEMFS data image lives in
JS typed arrays **outside** linear memory, which is why PSS exceeds `sbrk`. PSS
has no abort attached to it and is therefore recorded but not thresholded.

**The roadmap's framing is corrected here.** "A single Writer document is `sbrk`
290.8 MB" reads as the document's cost. The D4 stage events say `open.begin` =
**287,248,384** and `open.documentLoad-returned` = 290,983,936: **boot costs
287.2 MB, the document costs 3.7 MB** — and that was measured on
`e2-editor-v2`, a writer-only core. **v12's boot `sbrk` has never been
recorded.** W1 records it, and the headroom calculation depends on it rather
than on the document size.

**Fixed now, before the ladder runs:**

* **Kill line: peak `sbrk` ≥ 939,524,096 bytes (896 MiB) on any must-open
  fixture.** Rationale for 896: the incumbent's measured cross-open growth
  (48 MB over 8 opens) × ~2.5, plus tile buffers (finding 076: malloc'd), leaves
  128 MiB of margin below the abort.
* **"Kill" means: not on the fixed 1 GiB link.** The escape — a larger
  `-sTOTAL_MEMORY`, or growth with shared memory — is named so the line is not
  misread as "M4 is dead", and is **not proposed**: it carries an unmeasured
  browser-support question and would get its own gate.
* The leak bound of G6 is set only **after** W1 gives v12's noise floor. A
  threshold below the noise floor of the quantity it measures is not a
  criterion.

**The ladder** (synthetic, generated by W3), measured in this order with `sbrk`
at `open.begin`, after `documentLoad`, after each sheet's first paint, and after
close, over 3 opens: 1 sheet × 1 cell; 1 × 10k numeric; 1 × 100k numeric;
1 × 100k formula (`=A1+1` chains); 10 sheets × 10k; 1 × 1M numeric (the class
boundary probe); 5 charts; 3 images. The 302 upstream fixtures from
`libreoffice-26-8/sc/qa/unit/data/ods/` measure feature spread, not size.

**The one number that decides the shape of the work**: the 100k-cell fixture's
peak `sbrk` minus v12's boot `sbrk`. Under ~100 MB and memory is not the risk
for the default class. Over ~400 MB and the class shrinks, or the link-flag
question opens, **before** any shell work is spent.

## 5. The first decisive measurement (W2)

**Question.** Does the a11y+calc core, as linked into v12, actually load and
render an ODS through LOK — services, static constructor map, type detection,
headless Calc view, the `view-ready` handshake, and the accessibility switch at
open, all at once?

**Why it is first.** Everything else assumes the core half is paid for. If
`documentLoad` returns null, or `view-ready` never arrives, or
`setAccessibilityState` wedges a Calc view, this becomes an owner question and
the calendar moves by weeks — and **nothing has been spent on the shell.**

**How, without disturbing the gate.** Mirror `dist/` into a scratch root with
`build_mirror()`; write a one-file page into the mirror only; serve it with
`web/serve.py --root <scratch>`. Open bytes as `{name: "<stem>.odt"}` — the
documented diagnostic bypass, since `oxsdk_document_open` checks only the suffix
and content detection then reads the zip `mimetype`. Record
`opened.{parts,width,height,tileMode}`, whether `view-ready` arrived within
60 s, one 1024×1024 tile at (0,0) (sha256 + non-blank count, against the same
page's tile for `empty-one-sheet.ods`), and `sbrk` at every stage. Nothing under
`dist/`, `web/` or `sdk/` is written.

**Fixtures.** `three-sheets-distinct.ods` (the discriminator: Calc reports
`parts == 3`, the ODT control reports its page count), `empty-one-sheet.ods`,
`d1-anchors.odt` (positive control), and a truncated `.ods` (negative control:
typed `LOK_ERROR`, worker still healthy).

**What each outcome flips**, decided before the run:

* `opened` with `parts == 3`, `view-ready`, tile ≠ empty tile → the plan stands;
  proceed to the ladder.
* `opened` never arrives, or `LOK_ERROR` → **the "rebuild already paid for"
  premise is false in practice.** Stop; hand the owner a specific question
  (which of: static constructor map, `--disable-gui` view creation for Calc,
  type detection) with the engine log. No SDK work until answered.
* `opened` arrives but `view-ready` does not → the handshake is Writer-only in
  practice despite the sfx2 code path; an engine change enters the relink work
  and W2 is re-run on the relinked profile before anything else.
* opens, but the a11y refresh errors → registered under §3; a finding only if it
  changes a later criterion's outcome.

## 6. Work items, ordered, with what each disturbs

**Gate** = disturbs the running v12 cutover gate. **Who** = owner (core rebuild)
or us.

| # | item | gate | who |
|---|---|---|---|
| W0 | Serialisation: nothing that drives a browser overlaps a soak run | N if obeyed | us |
| W1 | v12 boot `sbrk` baseline — existing tool, no new code | N | us |
| W2 | **The decisive measurement** (§5) | N | us |
| W3 | Corpus `test-docs/ods/` + generator + generated `manifest.json` | N | us |
| W4 | Native oracle on the **same commit** (`build-native-26-8`, from `libreoffice-26-8`). **Not** `native-lok-26-8` — different commit. | N | us |
| W5 | Pre-relink sweep of the corpus on v12 with W2's instrument. Diagnostic, **not gate evidence**. | N | us |
| W6 | `tools/check_core_build_provides.py` gains a `calc` capability; self-test: the writer-only build must fail it | N | us |
| W7 | Engine + worker source: `format` allowlist `{odt, ods}` per finding 013, `documentType` on `opened`, `set_part`/`part_name` exports, capability bit. `src/*` and `sdk/sdk-worker.js` are gate-safe (the worker is excluded from the bundle and v12 carries its own copy). **`sdk/document-sdk.js` and `.d.ts` are NOT** — they are in the bundle's `included`. | N for src+worker, **Y** for `document-sdk.js` | us |
| W8 | Relink → new profile, **into `build/` only**; archive first; package with `--core-data ../wasm-lite/build-a11y-gate0 --split-core-data` | N into `build/`; **Y** if the Makefile is edited or `dist/` written | us |
| W9 | Viewer route: new `viewer-shell/` + `web/ods-viewer*.js`, importing `reader-shell/tile-scheduler.js` **unmodified**. **Do not add files under the five bundle-scoped directories.** Staged to `dist/` post-cutover. | N in source | us |
| W10 | ODS reader net + checklist + mutations, with a tool-closed census (the W-3 shape) | N | us |
| W11 | Human round (G10) | N | owner |
| W12 | Cutover of the new candidate, using the existing four-step machinery. Run count is the owner's call; **default if never decided: 12**, the standing rule. | it *is* the next gate | both |

**Traps recorded so they are not stepped on:**

* `Makefile:2` — `LOBUILD ?= ../wasm-lite/build-headless-probe`, which is
  **writer-only**. A plain `make` of a new target links a writer-only engine and
  the ODS open fails for a reason that has nothing to do with this work. Only
  the v10 rule points at `E2_V5_CORE := ../wasm-lite/build-a11y-gate0`.
* `tools/check_core_build_provides.py` — `PRODUCT_CORE_BUILD` still names the
  incumbent's core; it must be repointed at cutover, and that obligation is
  registered here rather than left to be noticed.
* `native-lok-26-8` is built from a different commit than `libreoffice-26-8`.
  The oracle must use `build-native-26-8`.

## 7. ODP / ODG later: free versus extra

**Free, built for ODS and reused as-is**: the `format` allowlist and the honest
`documentType`; part switching, since LOK models sheets, slides and Draw pages
all as parts through `getParts`/`setPart`/`getPartName`; the tile viewer and tab
UI with "sheet" renamed; the corpus/oracle/sweep shape and the memory
instrument; G1–G10 as templates.

**Extra, and it is not small:**

* **An owner core rebuild** with `--with-wasm-module='writer calc impress'`.
  `configure.ac:4371-4392` accepts only `writer|calc|impress`, and `impress`
  clears `ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS` — so **Basic + Draw + Math
  + Impress arrive together, and there is no `draw` value at all: ODG cannot be
  had without Impress and Basic.** Whether the Basic engine ships is a product
  decision about attack surface, not a technical one.
* A new core means a new data image, hence a **new profile lineage and a full
  re-earn of the cutover gate** — twelve runs, diagnostics, rehearsal, ODT
  round-trip, 4a — by the version-is-identity rule. The memory baseline moves
  with it and §4 is re-run, not inherited.
* Impress/Draw headless view creation and per-slide `getDocumentSize` have never
  been exercised here; §5 must be repeated on that core with different fixtures
  before any shell work.
* G3's oracle degrades: `SelectAll` + text covers Impress **outline** text, not
  shapes.
