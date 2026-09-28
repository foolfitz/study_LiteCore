# Handoff, 2026-09-28 (c) — M3 gate 0: protocol ruled by fable, counted run next

Entry points, in order: this file, `handoff/m3-gate-0/PREDICTION.md` (criteria +
Amendment 1), `handoff/m3-gate-0/RULING.md` (fable, verbatim),
`findings/evidence/m3-gate-0/README.md`.

The owner chose option B of the previous handoff (M3 gate 0, COOP/COEP inside
Nextcloud) and was away for the round, authorising fable to rule on their behalf.

## Where things stand

- Nextcloud side: `~/Projects/Nextcloud_Apps/litecoreprobe` (the owner's DDEV
  scaffold; its own git repo; core = official `nextcloud-34.0.2.tar.bz2`, sha256
  checked; `https://litecoreprobe.ddev.site:8443`, admin password in
  `.ddev/config.local.yaml`). Probe app HEAD `f837937`, tree clean.
- Four shakedowns (none counted). Shakedown 4
  (`findings/evidence/m3-gate-0/shakedown/2026-09-28T063109Z-apache-fpm.json`) is the
  post-ruling instrument and meets ruling CONDITION 2 on the runner's scores: noisy
  `[]`, A5 toggle verified `[true, true]`, A5 isolated, E1h and E3 1/1, E1 and E0 fail
  at boot — both browsers.
- Reader `wasm_sdk_probe/tools/check_m3_gate0_report.py` written (ruling CONDITION 3
  a–h, 24 red cases). **Not yet run on shakedown 4, red cases not yet generated** —
  the session's Bash permission classifier failed transiently six times in a row at
  this point.
- PREDICTION.md Amendment 1 appended (CONDITION 5). Not committed yet, together with
  RULING.md, the reader, the evidence README and two small runner edits
  (`provisionalGate`, canvas in C2).

## Next, in order (ruling CONDITIONS 3–9)

1. `python3 wasm_sdk_probe/tools/check_m3_gate0_report.py <shakedown 4> --allow-shakedown`
   must print `VERDICT E1h`; then `--red-cases findings/evidence/m3-gate-0/reader-red-cases`
   must exit 0 (base green, strict red on (a), all 24 copies red). Fix the reader
   until it does; never loosen a predicate to make a case red.
2. Commit everything above **before** the counted run (git shows the criteria
   preceded the data).
3. Counted run: `python3 probe_m3_gate0_coep.py --label counted` (both browsers, 3
   repeats, ~40 min, in the background). Beside the report save
   `ddev occ integrity:check-core`, `ddev occ config:list system`, `ddev occ app:list`
   as `runs/<stamp>.occ-*.txt`.
4. Verdict = the reader's one line on the counted report. Write
   `findings/evidence/m3-gate-0/RESULT.md` with the PASS sentence and named limits
   exactly as RULING.md CONDITIONS 6–9 fix them (E1 fails; nginx unmeasured; third-party
   apps — cite nextcloud/richdocuments#4103; Safari; interactions beyond the smoke
   sequence; the four asset routes of CONDITION 7 as an M3 item).
5. Roadmap `research/ROADMAP-2026-08-20-milestones.md` §5.1/§5.3 and the research
   note §3.2 (zh-TW): record the gate result; correct "`credentialless` 只有 Chrome"
   (Firefox 156 isolates too); replace "壞掉一片" with the measured clean-instance
   result plus #4103 for third-party apps; C7 as "Apache `.htaccess` whitelist with
   pretty URLs" (v14's `.data`/`.metadata` and `.json` are 404 as static app files).

## Measured so far (shakedowns — indicative, not the verdict)

A1 (Nextcloud chrome + COOP/COEP): no Nextcloud load failed, header identical, app menu
opens (6 entries), both browsers. Worker scripts need their own COEP (W-static blocked,
`coep-frame-resource-needs-coep-header`); app `.htaccess` and PHP-served both work on
Apache. `credentialless` isolates in Chrome **and** Firefox. An iframe in a
non-isolated page is never isolated; `Document-Isolation-Policy` isolates it in
Chrome only. The Files page can be isolated by an app (A5) with no new failures on a
clean instance — but that is the shape of #4103.
