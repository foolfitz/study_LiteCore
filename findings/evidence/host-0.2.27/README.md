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

(Filled in as the steps run.)
