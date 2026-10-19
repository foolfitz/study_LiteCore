# Host 0.2.27 (2026-10-20): engine v22 with shell generation v75

What it is: SPEC-M3-link-batch-v22 §11.7 steps 8–9, in the ddev window that §13.1 names (fable ruling 7: by delegation, this window only, until 07:00 or until the owner is awake). Ruling 5 item 17's eight conditions apply verbatim. This README is written before anything touches the app directory.

## How to go back (written first, item 17 (5))

The restore source is checked (`restore-source-check.txt`): the installed `~/Projects/Nextcloud_Apps/litecore/engine/` (0.2.26) and `wasm_sdk_probe/build/archive/host-0.2.25-engine-f5f0df762e1855f2/` are equal under `diff -rq`, except for the archive's `ATTRIBUTION.md`. Their `MANIFEST.json` files are byte-equal (`54bebc4d…`), with buildId `f5f0df762e1855f2`. The host repo is at `3c01876`, with a clean tree and `<version>0.2.26</version>`. `engine/` is git-ignored (`.gitignore:4`).

**Shape 1: refused or failed before `ddev occ upgrade` has run.** The registered version never changed, so no ddev command is needed:

```
rm -rf ~/Projects/Nextcloud_Apps/litecore/engine
cp -a wasm_sdk_probe/build/archive/host-0.2.25-engine-f5f0df762e1855f2 ~/Projects/Nextcloud_Apps/litecore/engine
rm ~/Projects/Nextcloud_Apps/litecore/engine/ATTRIBUTION.md
git -C ~/Projects/Nextcloud_Apps/litecore revert --no-edit HEAD   # only if the 0.2.27 bump commit was made
```

Then check that `diff -rq` against the archive shows only `ATTRIBUTION.md`.

**Shape 2: after `ddev occ upgrade` succeeded.** Use the same three file steps, then:

```
cd ~/Projects/Nextcloud_Apps/litecore && ddev occ upgrade
```

Nextcloud does not downgrade an app. `app:list` will still say 0.2.27 while every served byte is 0.2.26's. Clearing that label is the owner's call (ruling 7 item 9).

## Steps and results

**State at the end: 0.2.27 is installed, all four host arms PASS in both browsers, and it stays installed as the uncounted candidate for daily use** (ruling 7 item 9, first-line shape (a)).

| step (§13.1) | result | file |
|---|---|---|
| 1. desk gate and `ddev list` | clean at 03:20; `litecore` is the only running project | `step1-desk-and-ddev.txt` |
| 2. restore source | the installed engine/ and the 0.2.25 archive are equal, apart from `ATTRIBUTION.md`; buildId `f5f0df762e1855f2` | `restore-source-check.txt` |
| 3. HTTP checker | copied, and only `PATHS` (v21 → v22) and `NAME` changed (`http-tool-diff.txt`). Red case on the untouched 0.2.26: the four v22 path lines are red (404, not in the manifest). The tool exits 0 either way; red means the mismatch lines it prints | `http-served-red-on-untouched-0226.txt` |
| 4. package | buildId **`817413d5ad5bd502`**, 22 files; profile `e2-editor-v22`, page `3b96cb16…`, HTML `b9c2b975…`. `check_engine_decoded.py` passed (44 copies). Archived read-only to `wasm_sdk_probe/build/archive/host-0.2.27-engine-817413d5ad5bd502/` with `ATTRIBUTION.md`. It differs from 0.2.26's package in the v22 profile (4 files), `e2-editor-app.js` and `e2-editor.html` | `package.txt`, `check-engine-decoded.txt` |
| 5. version bump | host commit `d7c0a5e` (`info.xml` 0.2.26 → 0.2.27), local, not pushed | |
| 6. install | `ddev occ upgrade` was run by the session and was not refused, exit 0. `app:list` shows 0.2.27; maintenance false, needsDbUpgrade false, debug false | `install.txt` |
| 7. HTTP | entry 303 → address `817413d5ad5bd502-90d7bc2c`. Page `3b96cb16…`, worker `0d55bcfa…` and wasm `f7a40bcc…` decode to the manifest's sha256 under gzip and zstd. Against 0.2.26's archived manifest, 6 lines are red | `http-served.txt`, `http-served-red-against-0226-manifest.txt` |
| 8. `HOST_EXPECT["v22"]` | `--identity-only --page v22` gives `[]`. `--page v21` is refused on exactly hostVersion, servedPage and hostWasm (exit 1). `--self-test` 19/19 | `identity-*.txt`, `run-v21-d2-self-test.txt` |
| 9. host arms | `chain-host-arms.sh` ran 03:25–03:35; every step exited 0, and the desk gate was clean before each step | `chain.log`, `desk.log` |

### The host arms (each N=3, Chrome then Firefox; judged by each arm's own judge, `judge-host-arms.txt`)

| arm | Chrome | Firefox | criterion |
|---|---|---|---|
| H-154c (the closed dialog, at ready and after cancel) | PASS | PASS | §11.5 |
| H-154o (the open dialog) | PASS | PASS | §11.5 |
| D2-v22 (`run_v21_d2.py --mode host --page v22`) | PASS 3/3 | PASS 3/3 | §11.4 |
| M11-autosave (paste M2 through the dialog, then no input) | PASS 3/3; an auto save 30.6 s after the paste | PASS 3/3; an auto save 30.2 s after the paste | §11.5, §12 (d) |

**H-154o's position reading (recorded, not gated).**
- The open dialog sits at the **top left** of the viewport, not in its centre: Chrome's box is `[0, 0, 640, 335]` in 1850×980, Firefox's `[0, 0, 640, 342]` in 1850×994, with `margin: 0px` in both. Focus is in the text box, and both buttons are hit at their centres.
- This is what §11.5 predicted from Nextcloud's `dialog` reset.
- Registered as finding 155. The fix, `#litecore-editor-root dialog[open] { margin: auto; }`, waits for the next host version (ruling 5 item 19).

## Not done

- **The owner's hand tests on 0.2.27** (F3-hand: type after 插入 and after 取消; Ctrl/Cmd+Home/End; how the dialog looks closed and open).
- **K**, deferred and batched (§13).
