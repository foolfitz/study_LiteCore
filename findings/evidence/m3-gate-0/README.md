# M3 gate 0 — evidence

Question (roadmap §5.1): can the editor's cross-origin-isolated page live inside
Nextcloud, and in which shape. Criteria, predictions and the amendment from fable's
ruling: `handoff/m3-gate-0/PREDICTION.md`; the ruling verbatim:
`handoff/m3-gate-0/RULING.md`. The verdict is the one line printed by
`wasm_sdk_probe/tools/check_m3_gate0_report.py` on a counted report — never the
runner's `provisionalGate` / `gate` field.

## Layout

| path | what |
| --- | --- |
| `shakedown/` | Instrument runs. **None counts toward any criterion.** 055554Z = shakedown 1 (Chrome only; exposed the menu, whitelist and APCu defects); 060421Z = shakedown 3 (both browsers, pre-ruling instrument); 063109Z = shakedown 4 (post-ruling instrument, probe app `f837937`; the base of the reader's red cases). Shakedown 2 died on Firefox before writing a report (snap `/tmp`). |
| `runs/` | Counted runs (`--label counted`, repeats 3). Written only by the runner. |
| `runs/*.occ-*.txt` | Read-only instance evidence saved beside a counted report (`occ integrity:check-core`, `occ config:list system` with secrets masked, `occ app:list`). |
| `reader-red-cases/` | One gzipped mutated copy of shakedown 4 per predicate, and `SUMMARY.json`: the reader green on the base, red on (a) in strict mode, red on every copy where it says. |
| `external/` | Upstream precedent: richdocuments' listener as shipped, and nextcloud/richdocuments#4103 (JSON from the GitHub API, 2026-09-28). |

## Where the pieces live

- Nextcloud side: `~/Projects/Nextcloud_Apps/litecoreprobe` — its own git repo (the
  owner's DDEV scaffold, core = official `nextcloud-34.0.2.tar.bz2`, probe app
  `litecoreprobe`). Every report names its commit and the sha256 of every tracked
  file (`instance.probeApp`); `nextcloud/` itself is gitignored there, and
  `occ integrity:check-core` is what shows the core is the unmodified tarball.
- Runner: `wasm_sdk_probe/tools/probe_m3_gate0_coep.py` (its sha256 is in each report).
- Product bytes: `wasm_sdk_probe/dist` (untracked, bind-mounted read-only into the web
  container); the seven files that decide what the editor arms ran are hashed in
  `report.product`, and the reader re-hashes them when it runs.

## Re-run

```bash
cd ~/Projects/Nextcloud_Apps/litecoreprobe && ddev start      # the instance
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe/tools
python3 probe_m3_gate0_coep.py --label counted                  # ~40 min, both browsers, 3 repeats
python3 check_m3_gate0_report.py ../../findings/evidence/m3-gate-0/runs/<report>.json
python3 check_m3_gate0_report.py ../../findings/evidence/m3-gate-0/shakedown/2026-09-28T063109Z-apache-fpm.json \
    --red-cases ../../findings/evidence/m3-gate-0/reader-red-cases
```
