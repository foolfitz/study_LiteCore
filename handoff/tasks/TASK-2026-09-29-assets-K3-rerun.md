# TASK 2026-09-29 — K3 of the asset-delivery spec: re-run the three M3 counted runs on the new host

Spec: `specs/SPEC-M3-asset-delivery.md` §4 K3. Owner of this brief: the main session.
Executor: one agent, in the main tree (needs ddev, Chrome, Firefox). Report back with a
`## SUMMARY` of ≤30 lines at the top.

## What changed and why these runs

The `litecore` host now serves its own packaged engine from
`/index.php/apps/litecore/r/<buildId>-<policy>/…` (address `9076b0b425222c0e-566647db`; host commit **`5e53362`**, engine buildId
**`9076b0b425222c0e`**), and releases its lock at `beforeunload` as well as `pagehide`
(finding 105). The host-entry, locks and versions counted runs were made against the old
host `49cc4ab` (or earlier). They must be repeated, unchanged in criteria, against the new
host. The only runner changes: `check_m3_skeleton_open.ROUTE` is now the suffix
`/e2-editor.html` (committed), and `check_m3_versions.HOST_COMMIT` names the new host
(committed by the main session before you start).

## Preconditions — check each, stop and report if one fails

1. `git -C ~/Projects/Nextcloud_Apps/litecore log -1 --format=%h` is `5e53362` and
   `git -C ~/Projects/Nextcloud_Apps/litecore status --short` is empty.
2. `python3 -c "import json;print(json.load(open('/home/jiajun/Projects/Nextcloud_Apps/litecore/engine/MANIFEST.json'))['buildId'])"`
   is `9076b0b425222c0e`.
3. `sha256sum wasm_sdk_probe/dist/e2-editor-app.js wasm_sdk_probe/web/e2-editor-app.js` both
   `fbfb59a4…`.
4. Nobody holds a lock on the test files (the runners reset them; if a setup step gets 423,
   wait 6 minutes and retry once — a lock left by an earlier run lapses in about 306 s).
5. Record `docker ps --format '{{.Names}} {{.CreatedAt}}'` before and after each counted run.
   **Do not start, stop or restart any ddev project.** If a run's setup shows the router's
   `404 page not found`, follow rule 2 of `findings/evidence/m3-locks/README.md`
   "Counted run: rules fixed before it started".

## The runs (in this order; each is one full counted run; never re-run only the red arms)

    cd wasm_sdk_probe
    python3 tools/check_m3_versions.py   --label counted
    python3 tools/check_m3_host_entry.py --label counted
    python3 tools/check_m3_locks.py      --label counted

Then, for each written report:

    python3 tools/check_m3_<name>.py --score      <report>
    python3 tools/check_m3_<name>.py --red-cases  <report>

Expected verdicts: `VERSIONS CORRECT`, `HOST_ENTRY LANDS`, `LOCKS LAND`; `--red-cases` exit 0.
A red cell is **read as a finding first**: copy its failing entry verbatim into your report,
with the run's report path. Do not fix anything, do not edit runners, criteria, the host or
the product. Do not use any `--write`/cutover mode of any tool.

## Report back

- `## SUMMARY` (≤30 lines): the three verdict lines exactly as printed; red-case exit codes
  and counts; container list before/after identical or not; any red cell verbatim.
- The three report paths.
- Wall-clock start/end of each run (UTC).

Do not commit. The main session commits the reports with the RESULT update.
