# ABI6 product shell cutover preparation

The actual feature WASM is `fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658`; its manifest advertises ABI6. The existing deterministic cutover function produces page `c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490`, changing only the worker URL to e2-editor-v23 and the established sixteen-character WASM pin. This is source preparation, not a browser observation or feature acceptance.

`proposal.json` records the thirteen reachable modules, six proposed exclusions and source identities. The original three exclusions remain. The two added diagnostic tails are concatenated only into their separately bound ABI5 profile workers; neither is imported by the product. The feature worker source is also outside the page import graph, but its exact copy is selected by the product worker URL and bound by the profile worker SHA. Exclusion does not waive profile provenance or the unchanged new-file/stale-dist guards.

Read-only causal controls reject a missing worker URL, duplicate worker URL and missing pin; the transform changes exactly two lines and is idempotent. Actual artifact/archive audit must finish before writing the page or dist. After coordinator approval, synchronize the changed client/session/page source bytes to dist, retain v75 unchanged, then explicitly add v75 to FROZEN_MANIFESTS and select v76 as MANIFEST. Do not repair unrelated historical frozen-list omissions. No generation has been minted by this preparation.

The final generation command must pass all six explicit exclusions from proposal.json, with `--manifest e2/editor-shell-v2-bundle-v76.json --frozen-date 2026-10-26 --write`. It must never use `--force`. The unchanged real-tree shell guard remains outstanding until that generation exists. No browser, product build, profile edit or host action was performed here.

## Exact deferred generation command

After the root-approved tool bump and source/dist synchronization, from `wasm_sdk_probe/`:

```sh
python3 tools/build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v76.json --frozen-date 2026-10-26 --write --exclude 'sdk/sdk-worker.js=Bound separately and more precisely as workerSha256: the copy that actually runs is the one inside the profile.' --exclude 'reader-shell/reader-session.js=The R6 reader shell. Not in the editor page import graph; only reader-shell/tile-scheduler.js is.' --exclude 'reader-shell/state-machine.js=The reader shell own state machine, not the editor. Not in the editor page import graph.' --exclude 'sdk/v23-diagnostic-worker-tail.js=Private ABI5 diagnostic tail concatenated only into e2-editor-v23-diag; its resulting profile worker is separately bound by workerSha256. Not imported by the product page.' --exclude 'sdk/v23-diagnostic-r2-worker-tail.js=Private ABI5 diagnostic tail concatenated only into e2-editor-v23-diag-r2; its resulting profile worker is separately bound by workerSha256. Not imported by the product page.' --exclude 'sdk/v23-feature-worker.js=Source of the ABI6 e2-editor-v23 profile worker, separately bound by workerSha256. The product creates that profile worker by URL; this source is not a page import.'
```

Then run `python3 -m unittest discover -s tests -p test_e2_c_shell_bundle.py`. The command above is recorded only, not executed.

## Authorized finalization

After the root verified the corrected post-link audit and completed archive `build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6`, it approved finalization. The exact deferred command above has now executed successfully. The product page is the prepared `c25b11c4…e4490`; client, session and page dist copies match their sources. Generation76 binds thirteen imported modules with the six reviewed exclusions; bundle SHA256 is `f97bedeef73c7834cd5c86234d72e1ce459131153c36b8737583211a358e772c`. Generation75 remains byte-identical and is explicitly added to the frozen list; unrelated historical omissions were not changed.

`checks.json` retains every actual argv/cwd/exit and complete output: cutover and manifest creation exited0; all12 unchanged shell tests, all10 product-path mutation tests, all36 focused client/page/held-input/legacy-key tests passed; JavaScript syntax and diff checks exited0. `final-identity.json` binds all modified source/dist/tool/new-manifest files and the unchanged v75 manifest. The source/dist guard now has zero problems. This closes the final shell-binding obligation only; no browser readiness, feature population result, historical pre-red closure or host deployment follows from these static checks.
