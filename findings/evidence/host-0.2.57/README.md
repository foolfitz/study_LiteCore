# Host 0.2.57: Writer zoom no longer blanks a document with a comment

The fix for the owner's hand test of 0.2.56, item 1 (finding 185; `../zoom-comment-loop/README.md`). Released on the owner's word
("我首先要修掉白畫面", 2026-11-04 afternoon): an early hand-test slot for this one fix (CLAUDE.md, the section on cadence, item 1).
Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-04 16:04 +0800.

- Host `f56a66e` (version bump only) on `6def1da` (0.2.56), branch `host-0.2.57`. Engine `2b1a095e474beeb3`, archive
  `build/archive/host-0.2.57-engine-2b1a095e474beeb3` (not in git).
- Writer on `e2-editor-v33` (wasm `444519df`, unchanged), **shell generation 90** = generation 89 with the page's fix (page `0749bb91`,
  shell `2ee72a9a`; `../zoom-comment-loop/gen-90/`). Calc on `ods-editor-v5`, unchanged.
- Served delta, measured with the packager's closure before the inputs were written: **1 file changed** (`e2-editor-app.js`), 0 added,
  0 removed, 45 the same.
- First release on the parametrised tools (PLAN-2026-11-04 section 3.1, done before the freeze): `four_arms_identity.py` with
  `e2/generations/generation-NN.json`, `judge_product_four_arms.py`, `run_four_arms.py`, `run_f3_clipboard.py`, `v0_prime.py`.
- `host_release.py` changed for this release: a page whose module changes without a profile move is checked against its verified record
  (`pages` in the inputs), and `writerIdentity` can name `four_arms_identity` with a generation. Witness `tool-witness-0.2.56/`: `delta` on
  0.2.56 reproduces the committed `DELTA_HOLDS` field for field (only the tool's sha differs).

| Read | Result |
|---|---|
| `../zoom-comment-loop/` (feature, on the mirror) | Z on l1 `Z_RED` on 0.2.56's page, `Z_HOLDS` on the fix, both browsers |
| `../zoom-comment-loop/gen-90/v0/` | `V0_PRIME_HOLDS`, two stages: F4-89 re-read byte for byte by the parametrised reader with generation 89's page restored (red on the generation-90 tree); K 0.2.45's reader unchanged; put back, E1-C intact |
| `../zoom-comment-loop/gen-90/` (release regression) | P5, P4, S1, P1 `*_HOLDS`; Z `Z_HOLDS` on t3 and on l1; F4 24/24 PASS (`f4-90-r2`; `f4-90` refused at start on foreign CPU, another session's CppunitTest make); F3 `F3_83_EQUAL`, self-test `ALL_RED`. Calc nets not run: no Calc-served byte changed |
| `gate` | 16 of 16 |
| `package-run-01`, `delta`, `offline` | packaged in 149 s; `DELTA_HOLDS` with 7 red cases; `PACKAGE_HOLDS` |
| `offline-install-preflight`, `live-preflight`, `install` | `OFFLINE_INSTALL_READY`, `LIVE_PREFLIGHT_READY`, `CANDIDATE_INSTALLED`; documents and locks preserved; unauthenticated routes 401 |
| `z-host-red-on-0256/` | **the new arm, red first** on the live 0.2.56, Chrome: l1 from Files, zoom in step by step: `Z_HOST_RED`, blank at 100 (ink 0), 125 (ink 110, no band) and 150 percent (ink 0); fit and 200 painted |
| `z-host-0257/` | **the new arm on 0.2.57**: `Z_HOST_HOLDS` on Chrome and Firefox; ink at 100/125/150/200 percent about 171k / 239k / 319k / 493k (fit 118k), every step banded |
| `files-workflow-01/` | 52/52, both browsers and the read-only user; no owned unlocks, share and user removed, folder 204 |
| `capture-after` | `holds: true`: host `f56a66e` clean, installed 0.2.57, buildId `2b1a095e` in every entry, engine equals the archive, protected documents and **lock rows** equal the installer's after-state, owned folder 404, temporary user absent |

The new arm: `../zoom-comment-loop/fit-narrow-on-fix/zoom_host2.py` (the subagent's host repro, unchanged) read by `read_z_host.py` here:
every step needs painted bands and ink of at least a quarter of the fit step's. The rule was set after the red run's numbers and before
reading it: "ink > 0" alone would have passed 0.2.56's 125 percent (110 dark pixels on a white page).

Firefox on the host arm needed `TMPDIR` outside `/tmp`: `zoom_host2.py` puts the Firefox profile in a `tempfile` directory, and snap
Firefox cannot see the host's `/tmp` (`Failed to set preferences`, `z-host-0257/firefox-attempt-01`, `-02`). Each failed attempt left the
script's `zoom-diag/` folder on admin (it is created before the browser); deleted by hand (204) before the next run.

Rollback: `host_release.py rollback findings/evidence/host-0.2.57` with `host-stack/bin` first on PATH restores 0.2.56's engine bytes
(the page with the white zoom); the host label stays 0.2.57.

**The owner's re-test of hand-test item 1** (2026-11-04, after the install, on `手測-0.2.56/1-writer.odt`): "縮放OK了" -- zoom passes. Item 1 of 0.2.56's hand test is closed on 0.2.57. The fixture folder `手測-0.2.56/` is still on admin (its deletion is the owner's call; see the handoff).
