# Host 0.2.48: Save and Close where Collabora has them

Spec `specs/SPEC-P-demo-batch-2.md`. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-02 15:08 +0800.

- Host `0411329`, branch `host-0.2.48`, parent `d6cbbd9` (0.2.47). Source delta: `appinfo/info.xml` and `templates/viewer.php` (the viewer bar's padding, 12 to 14 px, so Close sits at the same distance on all three pages). Engine `a632c4463e700493`, archive `build/archive/host-0.2.48-engine-a632c4463e700493` (not in git).
- Writer on `e2-editor-v29`, shell generation 84 unchanged (page `c377b9f2`), HTML `80162183`. Calc HTML `714dba8f`. No engine changed.
- Delta against 0.2.47: `e2-editor.html`, `ods-editor.html`.

| Read | Result |
|---|---|
| `prepare-release.py` gate | K 0.2.45, the two reds on earlier hosts, C, Z, F3-84, F4-84, V0', E1-C on these pages |
| `check-delta.py` | `DELTA_HOLDS`, seven red cases |
| `offline-package-check.py` | `PACKAGE_HOLDS`, 22 red cases |
| `install-0.2.48.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| Files workflow | 52/52, `ok: true`, cleanup clean |
| `host_batch.py` | `HOST_BATCH_HOLDS`, 11/11 on both browsers |
| `demo-batch-2/host_layout.py` (`host-layout/`) | `LAYOUT_HOLDS`: 14/14 on both browsers, dark arm 2/2 |
| `capture-after.py` | **`holds: false`, one clause, read below** |

## `capture-after.py` is red on one clause, and it is not this release

`lockRowsEqualInstallAfter` is false. Every other clause holds. `capture-after-reading.json`: the four lock rows are equal once `ttl` is left out; two rows moved, files 29431 and 29432, ttl +120 each. Those are `files/demo/`, the two documents in the owner's screenshots: their tabs were still open and the page refreshes its lock, seen in the access log as `LOCK` requests at 15:13:42 and 15:13:45 for those paths.

So the reader compared the full lock table across a window in which a live editor legitimately extended its own lock. A third shape of the same weakness as L-capture-after-expired-lock-lazily-deleted (host-0.2.43). Named **L-capture-after-live-lock-refreshed**. No tool changed.

The same tabs loaded their page before this install, so they show 0.2.47 until reloaded.

**Pending:** the owner's hand test. Rollback: `rollback-package.sh` with `host-stack/bin` first on PATH restores 0.2.47's engine bytes.
