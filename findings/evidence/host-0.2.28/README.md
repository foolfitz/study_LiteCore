# Host 0.2.28 (prepared 2026-10-20, not installed): finding 155's host rule

What it is: SPEC-M3-link-batch-v22 §14. The owner chose "A+B" on 2026-10-20; B is "prepare 0.2.28": the criterion, the patch as a file, no change to the host repo that ddev serves. **Installing needs a window the owner names (§13).**

**State: prepared. ddev still runs 0.2.27** (host `d7c0a5e`, buildId `817413d5ad5bd502`). Nothing in this directory has touched `~/Projects/Nextcloud_Apps/litecore`.

## What changes

`host-0.2.28.patch` (sha256 `daff034e…`), against host `d7c0a5e`:

- `templates/editor.php`: one rule after 0.2.26's `dialog:not([open])`, with its comment: `#litecore-editor-root dialog[open] { margin: auto; }`.
- `appinfo/info.xml`: 0.2.27 → 0.2.28.

`git apply --check -v` against `d7c0a5e` passed on 2026-10-20 (dry run; nothing was written).

The engine package is unchanged (buildId `817413d5ad5bd502`, archive `wasm_sdk_probe/build/archive/host-0.2.27-engine-817413d5ad5bd502/`). The shell is not refrozen, and item 2 is not re-run (finding 155; ruling 5 item 19).

Do not apply the patch before the window. `templates/editor.php` is the file ddev serves: PHP reads the template on every request, so an edited file is live at once, without `occ upgrade` (inferred from how the template is served; not measured).

## Before the window (done)

- **Reduced reproduction** (`../155/precheck/`; it satisfies no criterion). In headless Chrome and Firefox, a page built from Nextcloud's own two `dialog` reset rules (read from the installed `server.css`) and the page's own style and dialog markup gives these readings:
  - without the rule, the open dialog sits at `[0, 0, …]`, as H-154o read on the host;
  - with the rule, its centre offset is `[0, 0]` in both browsers;
  - the positive control (no Nextcloud CSS) is centred too.
- **H-155 in the judge** (`../154/diag_markdown_dialog_on_host.py`, sha256 `991b1efb…`). It is a new verdict key on the same open reading, and H-154o's clauses are unchanged. `--require-h155` makes `--judge` exit 1 unless H-155 is PASS.
  - Self-test: 16/16 (`diag-self-test.txt`). The six new cases are 0.2.27's two committed host reports (FAIL), a synthetic centred report (PASS), 16 px off centre (PASS), 17 px off centre (FAIL), and no open reading (NOT_ESTABLISHED).
  - The self-test's first run caught a mistake in the cases themselves: the synthetic reports carried host version 0.2.27, so the version pin failed them when judged as 0.2.28. The fix was to the test data only.
  - **Red case on 0.2.27** (`h155-red-on-0.2.27.txt`): both host reports read H-155 FAIL, 3/3 rounds, with centre offsets [-605.0, -322.5] (Chrome) and [-605.0, -326.0] (Firefox), exit 1 with `--require-h155`. H-154c and H-154o stay PASS, and the judgement without the flag still exits 0.

## In the window (§14.4; not done)

1. Desk gate clean; read-only `ddev list` shows only `litecore` as OK.
2. Restore, written here before anything touches the host repo:
   - **If refused or failed before `ddev occ upgrade` ran:** run `git -C ~/Projects/Nextcloud_Apps/litecore revert --no-edit HEAD`, only if the 0.2.28 commit was made. No ddev command is needed.
   - **After `ddev occ upgrade` succeeded:** the same revert, then `cd ~/Projects/Nextcloud_Apps/litecore && ddev occ upgrade`. Nextcloud does not downgrade an app, so `app:list` stays at 0.2.28 while the template served is 0.2.27's.
   - `engine/` is not touched in either case.
3. Check before applying:
   - the host HEAD is `d7c0a5e` and the tree is clean;
   - `diff -rq` of `engine/` against the 0.2.27 archive differs only in `ATTRIBUTION.md`;
   - `engine/MANIFEST.json` has buildId `817413d5ad5bd502`.
   
   If any of these differs, stop before applying.
4. `git -C ~/Projects/Nextcloud_Apps/litecore apply <this dir>/host-0.2.28.patch`, then commit locally: Co-Authored-By, no Claude-Session, no push.
5. `ddev occ upgrade`. `app:list` should show 0.2.28, with maintenance false.
6. HTTP: rerun `../host-0.2.27/http_served_page.py` unchanged. It should be as green as `../host-0.2.27/http-served.txt`, with an address that still starts with `817413d5ad5bd502`.
7. H-155: `diag_markdown_dialog_on_host.py --h154 --rounds 3 --expect-version 0.2.28 --expect-build-id 817413d5ad5bd502`, Chrome then Firefox, with the desk gate before each. Read each report with `--judge <report> --expect-version 0.2.28 --expect-build-id 817413d5ad5bd502 --require-h155`. `chain-h155.sh` does this step: `WINDOW_END='YYYY-MM-DD HH:MM' setsid nohup bash chain-h155.sh &`. Its guards are the same as 0.2.27's chain (window, `ddev list`, desk gate), and the window's end is absolute, so a window that crosses midnight works. Without `WINDOW_END`, or with an unparsable value, it exits 1 before doing anything (checked).
8. Not re-run: D2-v22 and M11-autosave (§14.4 item 8).

Outcome rules:
- **Any FAIL** (H-154c, H-154o or H-155): restore as in step 2.
- **NE only:** 0.2.28 stays installed but not established, and the owner decides.
- **All PASS:** 0.2.28 replaces 0.2.27 as the uncounted candidate for daily use.

## The window and the desk gate (2026-10-20, before the H-155 chain)

- **Window:** at 14:00 the owner wrote 「現在可以裝 0.2.28」 and chose 14:45 as its end (`WINDOW_END='2026-10-20 14:45'`). This is the window ruling 1 §2.9 form 1 asks for.
- **The desk gate is withdrawn for 0.2.28** (spec §14.5; the owner chose A). It guards timing cells (ruling 6 addendum 1 item 9), and H-155 is a geometry reading. At 14:02 it read dirty for two reasons: desktop Chrome (28 processes), and two containers whose main process is `make run` (`oxool-dev`, `modaodfweb-rhtest`). Those are services, not builds; the 1-minute load was 0.49.
- `chain-h155.sh` now guards each step on three things: the window, `ddev list`, and KWallet (`pre_run_checks()["refuse"]`, the runners' own refusal). It records the full `pre_run_checks` reading in `guard.log`. Red cases are in `chain-guard-red.txt`. `desk_gate.py` is unchanged.
