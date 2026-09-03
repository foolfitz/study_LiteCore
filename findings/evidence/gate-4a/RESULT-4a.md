# Gate condition 4a — **all seven terms PASS**, 2026-08-29

Terms fixed before the runs in
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, addendum part 1 §A-1,
and re-aimed at `e2-editor-v12` by the 2026-08-29 candidate amendment.

4a is the **only** measurement of the benefit a cutover buys. Everything else in
the gate shows the candidate is no worse than what ships.

## The precondition, discharged first

`tools/probe_aria_projection.py` gained `--candidate-profile`, making it the
**fourth caller** of `repointed_page()` rather than a fourth implementation.

Unlike the `--profile` path it replaces, the candidate path appends **nothing**
to the page: `gate_mirror()` adds an injected reader, and this probe never used
it — `Accessibility.getFullAXTree` is a CDP domain and `#a11y-para` / `#a11y-doc`
are ordinary DOM. So a candidate run carries `shim: null` and its `pageSha256`
is directly comparable with the soak reports'. The `--profile` path is kept so
the 2026-08-23 evidence stays reproducible; passing both is refused.

## The judge is a second tool

`tools/check_4a.py`. The probe reports and does not score — it says so in its
own docstring, because when it was written §3.4 had no threshold and inventing
one from the first output was the order this tree refuses. 4a's terms are that
threshold, fixed 2026-08-29, so the judging lives in a tool that cites them.

It reads the fixture's own `content.xml` and compares **in code**.

## The terms

| term | measured |
|---|---|
| **1 identity** | three runs, all `pageSha256 = 3dfdcfef4abfe6b7…` (the soak reports' value), `kind: candidate`, `shim: null` |
| **2 text** | **9 of 9** paragraphs of `list-contexts.odt` in the AX tree, three runs |
| **3 structure** | heading AX `level: [1]`, matching the ODT `outline-level="1"`; **2 `list` containers, 4 `listitem`**, three runs |
| **4 focus** | 3 placements, **3 distinct readings**, and all 3 matched the paragraph aimed at — three runs |
| **5 repetition** | three runs, **1 distinct signature** over terms 2–4 |
| **6 the instrument can fail** | see below |
| **7 delta** | v8's shipped page: `documentTextInTree: false`, region carrying `reason: "profile"` and the sentence *「這一版引擎沒有提供段落文字，所以無法朗讀文件內容。」* |

## Term 6 — exactly one check moved

```
python3 tools/run_e2_c_product_path.py --browser chrome \
    --candidate-profile e2-editor-v12 --mutate projection-not-wired
```

| | PASS | NE | FAIL |
|---|---:|---:|---:|
| clean run (soak run 3) | 38 | 2 | 0 |
| mutated | 37 | 2 | **1** |

The one that moved is `the-document-region-says-why-it-is-empty`, PASS → FAIL,
observing `{present: true, text: ""}` — the region present and empty, which is
what a screen reader reads as "document, blank". **Exactly one**: a mutation
reddening several checks would not show that *this* one can fail, and one
reddening none would mean the check was never tested at all.

The run is stamped `mutation: projection-not-wired`, so it can never be banked
as a clean run. **The page was restored**: `web/e2-editor-app.js` and
`dist/e2-editor-app.js` both hash `28e03e5bc9fcb8c4` before and after, the
baseline value.

## The judge's own red cases

A green verdict from a judge written the same day is not evidence. Four red
cases, covering all six judged terms:

| perturbation | reddens |
|---|---|
| a wrong `--expect-page-sha256` | term 1 |
| a v12 record passed as the v8 control | term 7 (`documentTextInTree: true`) |
| only two candidate runs | term 5 |
| the v8 control passed as the candidate | terms 2, 3 **and** 4 together |

The greens are non-vacuous by their own numbers: 9/9 rather than 0/0, heading
level `[1]` rather than `[]`, 2 and 4 rather than 0 and 0, 3/3/3 rather than
0/0/0.

## What this does and does not establish

**Does**: on the page that will ship, an assistive technology is handed the
document's nine paragraphs with their roles, the heading at its true level, the
lists as lists, and focus following the caret — where the shipped page hands it
a canvas and a label, and says so honestly.

**Does not**: how any particular screen reader *announces* that tree — order,
verbosity, browse mode — which is condition 4b's narrow human residue, together
with `queue-list-prefix-read-twice` and the 4096-character `textHead` cap.

## Reproducing

```bash
cd wasm_sdk_probe
for i in 1 2 3; do
  python3 tools/probe_aria_projection.py --candidate-profile e2-editor-v12 \
      --out ../findings/evidence/gate-4a/candidate-v12-run$i.json
done
python3 tools/probe_aria_projection.py --candidate-profile e2-editor-v8 \
    --out ../findings/evidence/gate-4a/control-v8.json
python3 tools/check_4a.py \
    --candidate ../findings/evidence/gate-4a/candidate-v12-run{1,2,3}.json \
    --control ../findings/evidence/gate-4a/control-v8.json \
    --expect-page-sha256 3dfdcfef4abfe6b723b573f35e8ec8f885dcc42a8ed4d8338ad2381eb386f50f
```
