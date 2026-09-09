# Finding 093, option B after the link — the pinned oracle, measured

Measured 2026-09-09 by agent, immediately after the owner ran step 4 of
`handoff/RUNBOOK-operator-093-engine-geometry.md` (the first real compile and
link since the a11y build). **The acceptance was not written for this run**: it
is `findings/evidence/093/ORACLE-fix-shape.md`, committed `8edd7cf8` on
2026-09-08 *before the probe that reads it existed*, and nothing in it was
moved. The instrument is `tools/probe_093_fix_shape_oracle.py`, also unchanged
(`git diff` empty for both).

O-FIX, restated so the claim and the number sit together:

> after arriving at paragraph N, the band in which the engine **renders**
> paragraph N overlaps `.desk`'s visible band by at least **half a line**.

## What was and was not done

* **Nothing was landed.** Every measurement ran against a scratch mirror of
  `dist/` (`build_mirror`) with the page repointed in the mirror only.
  `web/`, `dist/`, `src/` and `sdk/` are byte-unchanged; no pin was moved, no
  shell generation was frozen, `build_cutover_page.py --write` was not run.
* **The soak bank was not touched** and no soak run was taken. The six banked
  2026-09-07 runs are where they were.
* Browser: headless Chrome, its own temporary profile, 1920x1080. One Chrome
  instance was running before this session (the owner's, browser main pid
  171724) and the same one after; nothing was killed.
* `make test-e2-c-static` exit 0 immediately before the product-path run
  (finding 090's rule). `make -n test-e2-c-static | grep -c 'em++'` = 0 first;
  no bare `make` was run at any point.

## The artifact under test

The five hashes of `dist/profiles/e2-editor-v13/`, recorded before measuring:

| file | sha256 |
|---|---|
| `probe.wasm` | `0fe25650bec1bac50a959b1b0a45687cb289b60463c12b40d2c9d031da12fc74` |
| `probe.js` | `6bdb3a78295be93ecb159a2bf54096ab8e5da71ac40aed5b4d296196323aaa8a` |
| `sdk-worker.js` | `6e75829a2911c1dffa9457f64f6f04a67f0f7bb0bfdda82a663747c0f8b0bc97` |
| `sdk-manifest.json` | `76b895761d10fc7b0987868ef18e7efa9b5b7b81b19ce9bf13794a4b185ed07e` |
| directory | 10 files: the four above plus six data-pack files (base/cjk/fallback, `.data` + `.metadata`) |

`sdk-manifest.json` declares `documentOutlineGeometry:
"accessible-paragraph-geometry"` alongside `documentOutline`, ABI 4.

**The three baselines are unmoved after the link** — re-read at the start of
this session, the check the runbook makes a stop condition:

| profile | `probe.wasm` sha256 (first 16) | expected | verdict |
|---|---|---|---|
| `e2-editor-v8` (shipping) | `4a2710bba1ef07d9` | `4a2710bba1ef07d9` | unmoved |
| `e2-editor-v10` | `4ec1e389aaab3b03` | `4ec1e389aaab3b03` | unmoved |
| `e2-editor-v12` | `4ec1e389aaab3b03` | `4ec1e389aaab3b03` | unmoved |

v13's wasm differs from the repackaged `4ec1e389…` bytes, so this is a genuine
new link and not a repackage.

## The commands

```
python3 tools/probe_093_fix_shape_oracle.py \
    --profile e2-editor-v13 --profile e2-editor-v12 \
    --shape S0 --fixture a11y-long --fixture a11y-audible \
    --viewport 1920x1080 \
    --out findings/evidence/093/post-link-oracle-v13-v12.json

python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v13 \
    --out findings/evidence/093/post-link-product-path-v13.json
```

Both profiles were measured **in one invocation of the instrument**, so the
control was exercised in the same session as the candidate, per this tree's
rule that a green whose control was not exercised in the same session is not
evidence.

**`S0` means "the page exactly as it is in `web/` today"** — which since step 3
already contains option B's page half. That is the shape under test: the whole
point of option B is that the page needs the engine to deliver geometry, so the
same page byte-for-byte is the candidate on v13 and the control on v12.

## 1. The candidate: `e2-editor-v13`, `a11y-long` (133 paragraphs)

Canvas 27,198px, `.desk` 864px, line height 22px, threshold 11.0px. Targets are
the first, middle and last stop the caret walk reached: paragraphs 11, 14, 16 —
**the same three the pre-link red case measured** (`step3-source-landing/
oracle-S0-a11y-long.json`), so the two are directly comparable.

| arm | paragraph | overlap | threshold | band top in viewport | band bottom | scroll fraction | caret at target | O-FIX |
|---|---|---|---|---|---|---|---|---|
| browse | 11 | 22px | 11.0px | 828 | 850 | 0.0517 | yes | **PASS** |
| browse | 14 | 22px | 11.0px | 703 | 725 | 0.0802 | **no** | **PASS** |
| browse | 16 | 22px | 11.0px | 703 | 725 | 0.0924 | **no** | **PASS** |
| focus | 11 | 22px | 11.0px | 828 | 850 | 0.0517 | yes | **PASS** |
| focus | 14 | 22px | 11.0px | 703 | 725 | 0.0802 | yes | **PASS** |
| focus | 16 | 22px | 11.0px | 703 | 725 | 0.0924 | yes | **PASS** |

**3/3 on both arms.** Unrounded: the overlap is 22px of a 22px line — the whole
line, not the half the threshold asks for — in six of six cells.

`#a11y-doc.offsetTop` = 0 against a 27,198px canvas. 133 projected nodes,
`truncated: 0`.

**The browse arm is the one that carries the result, and its `caret at target:
no` column is the evidence.** For paragraphs 14 and 16 the caret stayed in
paragraph 11 (scroll fraction 0.0517) while the desk moved to 0.0802 and
0.0924 — the viewport followed the **browsed node**, not the caret. That is
precisely the signature S2b failed to produce (phase 3: browse 1/3, passing
only for the paragraph the caret happened to be in). B is not S2b with extra
steps.

## 2. The control: `e2-editor-v12`, `a11y-long`, same session, same page bytes

| arm | paragraph | overlap | threshold | band top in viewport | scroll fraction | O-FIX |
|---|---|---|---|---|---|---|
| browse | 11 | **0px** | 11.0px | 2192 | 0.0000 | **FAIL** |
| browse | 14 | **0px** | 11.0px | 2818 | 0.0000 | **FAIL** |
| browse | 16 | **0px** | 11.0px | 3140 | 0.0000 | **FAIL** |
| focus | 11 | **0px** | 11.0px | 2192 | 0.0000 | **FAIL** |
| focus | 14 | **0px** | 11.0px | 2818 | 0.0000 | **FAIL** |
| focus | 16 | **0px** | 11.0px | 3140 | 0.0000 | **FAIL** |

**0/3 on both arms, and it reproduces the pre-link red case to the pixel** —
`step3-source-landing/oracle-S0-a11y-long.json` recorded band tops 2192 / 2818
/ 3140 and overlap 0 for the same six cells on 2026-09-08. The instrument still
discriminates, and the discrimination is worth exactly one thing: v12 declares
the outline and delivers no geometry, v13 delivers it, and nothing else about
the page differs.

Scroll fraction **0.0000 with 0/3 visible** is phase 3's S1 row appearing again
on the profile that cannot fix it: the proxy scores perfectly while the reader
sees nothing. It is in this evidence file for the same reason it was in that
one.

## 3. The `a11y-audible` rows, and the surprise in them

| profile | fixture | browse | focus |
|---|---|---|---|
| `e2-editor-v13` | `a11y-audible` | 3/3 (24px of 24, threshold 12.0) | 3/3 |
| `e2-editor-v12` | `a11y-audible` | **3/3** | **3/3** |

**The control PASSES on `a11y-audible`.** Stated as a surprise rather than
smoothed over, because the oracle document names `a11y-audible` as its fixture
and because phase 3 measured S0/v12/audible at **1/3** the day before.

The cause is known and is not the link: `a11y-audible` is 10 paragraphs, paper
y 100..415, and the whole document fits inside an 864px viewport. Step 3
already landed the page half of option B (`#a11y-doc { top: 0; left: 0 }`), so
on v12 the page now behaves like phase 3's **S1** — pinned to the top of the
paper — and S1 scored 3/3 on this fixture in phase 3 too. A document that fits
on one screen cannot separate "the node is at its paragraph" from "the node is
at the top of the paper".

**Consequence to carry forward: `a11y-audible` is no longer a discriminating
control for this oracle.** It was one on 2026-09-08 (S0 = unfixed page = node
at the *bottom* of the paper, 1/3); it stopped being one the moment the page
half landed. The 133-paragraph fixture is the only control in this pair that
does any work, and requirement "keep the controls" is satisfied by the
`a11y-long` rows alone. Any future run of this oracle that reports only the
audible fixture is reporting a property of the fixture.

The pre-registered stopping condition ("if S0 passes O-FIX everywhere, the
oracle is wrong; stop") did **not** fire: S0 fails 0/3 on `a11y-long` under
v12. It is checked here explicitly rather than assumed, because half of its
antecedent is now true.

## 4. Clause C3 of the 41st check: it executed

`the-projection-is-placed-where-the-document-is` on the candidate page for a
cutover to v13, fixture `list-contexts.odt`:

```
"geometry": "present", "carried": "24", "placed": "24", "nodes": 24,
"docOffsetTop": 0, "docOffsetLeft": 0, "docHeight": 929, "canvasHeight": 929,
"sinkTop": 250, "sinkHeight": 16,
"focusedId": "a11y-node-7", "focusedTop": 259, "focusedHeight": 20,
"verdict": { "ok": true, "C1": true, "C2": true, "C3": true,
             "clausesExercised": ["C1", "C2", "C3"] }
```

**`clausesExercised` contains C3 for the first time.** Before the link it was
`["C1", "C2"]` on every profile in the tree, and the amendment of 2026-09-08
said in as many words that a green run could not be quoted for a clause that
never ran. It has now run and it is true: the node for the paragraph the caret
is in (`a11y-node-7`, band 259..279) overlaps the caret's band (250..266) by
7px.

Geometry was carried for **24 of 24** paragraphs and placed for 24 of 24 — no
per-paragraph miss on this fixture.

Recorded rather than smoothed: C3's own predicate is a **bare overlap**, not
O-FIX's half-line. On this reading the margin is 7px of a 16px caret band, and
the projected node's band (20px) is not the caret's band (16px) — they are two
different rectangles that agree about which line they are on. That is what the
clause was written to assert; O-FIX is the half-line criterion, and it is
satisfied separately in §1.

## 5. The product-path composition

`post-link-product-path-v13.json`, `--candidate-profile e2-editor-v13`,
`mutation: none`, fixture `list-contexts.odt`, Chrome.

* **41 checks: 39 PASS / 2 NE / 0 FAIL.** `ok: true`, `complete: true`.
* The NE set is unchanged and is exactly the two the amendment named:
  `notice-action-recovers-the-session`,
  `a-refused-action-is-reported-and-changes-nothing`.
* `knownRed: {}`, `staleKnownRedDeclarations: []`, `pageErrors: null`,
  `offPageInk.worst: 0` over 37 scans.
* `recoveryPairing.held: true`.
* `startedAt` 2026-09-09T12:23:06+08:00, `completedAt` 2026-09-09T12:29:13+08:00
  (2026-09-09T04:23:06Z / 04:29:13Z).

**39 PASS / 2 NE is the composition the amendment pinned** when the check
landed at count zero, moving the predicate from 38/2. It is met exactly.

Identity of what was measured, from the report rather than from intent:

* `candidateCutover.pageSha256` =
  `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`,
  `pinBefore` `4a2710bba1ef07d9`, `pinAfter` `0fe25650bec1bac5`.
* `servedShell.bundle` = `e2/editor-shell-v2-bundle-v49.json`,
  `servedSha256` `ea69984c8ad25c4048de0313a49f3db9e7c4ab3fc6ded0f4cebc84a1a5b0fe52`,
  `differingPaths: ["web/e2-editor-app.js"]`, `differsOnlyInTheEntrypoint: true`
  — the expected shape for a candidate run, where the entrypoint is the
  repointed page.

**This is not a soak run and must not be counted as one.** It was taken to
answer the C3 and composition questions; the pins have not moved, so the page
this run served is not yet the page the product serves.

## What this run does NOT establish

Repeated here rather than left in an earlier section, because the numbers above
are the kind that get quoted alone:

* **No screen reader was run.** Every verdict rests on
  `node.scrollIntoView({block: "nearest"})` being what an AT browse cursor
  causes. That link is finding 069's precedent and the owner's two walks of
  2026-09-08; it was not measured in phase 2, phase 3, or here. It remains the
  weakest joint in the chain, and it is the joint the whole result hangs from.
* **Three paragraphs of 133, in one viewport size.** The oracle asks for the
  first, a middle and the last stop the caret walk reaches; the walk reached 6
  stops and the targets were paragraphs 11, 14 and 16. Paragraphs 0–10 and
  17–132 were not judged.
* **The cost of 133 `getBounds()` calls per state read is still unmeasured**
  (runbook §7, item 3). This run gives no number for it.
* **Empty paragraphs, tables, frames and multi-column are still unreached** —
  `getBoundsImpl`'s non-root-parent and empty-preview-page branches.
* **The wasm device's twip conversion was not compared against the caret the
  way the native device was** (step 1: 20/20, sub-pixel). O-FIX passing at
  22px-of-22px is strong indirect evidence that the conversion is right, but it
  is a different measurement, and a systematic error smaller than half a line
  would pass O-FIX unnoticed.
* **`a11y-long` is one document.** It is 133 plain paragraphs; it is not a real
  user document.

## Outstanding after this measurement — not done here, deliberately

Runbook step 5 items that this measurement did not perform, in the runbook's
order:

1. **`e2-editor-v13` is not archived.** The directory name its convention
   implies is
   `build/archive/e2-editor-v13-0fe25650-worker-6e75829a-manifest-76b89576/`.
   A wasm hash is not a function of its source (finding 036), so until this
   exists the artifact is protected only by `refuse_unasked_relink`.
2. The page is **not repointed** (`workerUrl` and `PINNED_WASM_SHA256`, both
   lines, in `web/` and in `dist/`), and no new shell generation is frozen.
3. `check_soak_bank.py`'s three constants (`EXPECTED_PASS` 38 → 39,
   `DEFAULT_SHA`, `DEFAULT_SERVED_SHELL`) have not moved, and the six banked
   2026-09-07 runs have not been voided — per the handoff, that move follows
   the first post-link clean run rather than preceding it.
