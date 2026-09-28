# M3 host entry — evidence

Criteria: `specs/SPEC-M3-host-entry.md` §4. Verdict: `RESULT.md`, from
`wasm_sdk_probe/tools/check_m3_host_entry.py --score runs/2026-09-28T095100Z.json`.

| path | what |
| --- | --- |
| `RESULT.md` | The result, how it got there (two wrong turns), named limits. |
| `runs/` | Counted run (`--label counted`: 3 per arm per browser, refuses a dirty app tree, a dist page that differs from `web/`, or a served shell that is not a frozen generation). |
| `shakedown/` | Never counted. `092749Z`: H2 red on the `<text:h` oracle, both browsers. `092945Z`: Chrome open-save only, with the style payload that showed `Heading_20_1`. `093031Z`: first all-arm pass, dirty app tree. `093154Z`: clean. `094839Z`: after the review's changes (page, host, runner); the base of `--red-cases` (21/21 red). |
| `product-path/` | H4: `run_e2_c_product_path.py --browser chrome` on the final page, shipping v8 and `--profile e2-editor-v14`, each 40 PASS / 2 NE, the same cells as v52's. `superseded/` holds the same net on the first page draft (also 40/2), before save serialization changed the page again. |
