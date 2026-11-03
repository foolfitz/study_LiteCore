# Handoff: Microsoft formats -- pages done, W holds, v33 / v5 frozen, generation 89; Writer nets wait for KWallet; host 0.2.56 not installed

Checkpoint **2026-11-03 23:55**. Supersedes `HANDOFF-2026-11-03h-ms-formats-ready-to-link.md`. Spec `specs/SPEC-P-ms-formats.md` (sections 10 and 11 are
tonight's). The owner is out today; next round they can hand-test.

## Done (all committed on `main`, nothing pushed)

- **Pages** (`4c866daf2`): both pages save in the document's own format (`session.documentFormat()`, from the engine's open reply via
  `DocumentHandle.format`); 儲存 / 另存新檔 with the page's own dialog (ODF preselected; the original offered for DOCX/XLSX); downloads typed and
  named by format; file inputs accept .docx / .xlsx. Writer: `NarrowEditorV2Session` overrides `save()` and `_checkpointBeforeSelection()` (the
  E1-C-bound base hard-codes odt) -- checkpoints in the document's format so a rescue never writes ODT into a .docx. Calc: `odt`/null save as
  ODS (v4's path). Unit tests 7 + 6, 17 mutations red (`tools/check_ms_formats_shell_mutations.py`). Spec 10.
- **W** (spec 6.2, 10.4, corrected by 11.3): run 02 (`findings/evidence/ms-formats/w-02/`) `W_HOLDS` on Chrome and Firefox with one tool; red
  case `W_RED` on v32/v4; R1 and R2 as ruled. Run 01 (`w/`) is the witness (W3 red on the reading). The W3 correction was **fable's ruling,
  owner-delegated** (spec 11.3). After the freeze, `--live` on the frozen dist: `W_HOLDS` both browsers (`gen-89/w-live/`).
- **Frozen**: `dist/profiles/e2-editor-v33` (wasm `444519df`) and `ods-editor-v5` (`4faad0af`), archives
  `build/archive/e2-editor-v33-444519df-worker-b35359ce`, `ods-editor-v5-4faad0af-worker-79bbafb4` (`freeze/`).
- **Calc page on v5** (`e8a180ad3`); Calc regressions all pass on the switched page (`calc-after-freeze/`): C, CU, cell 31/31, range 40/40,
  autosave 36/36, P2 33/33.
- **Writer cut over to v33** (page `08c474ea` = the bytes W run 02 measured) and **shell generation 89** frozen (`ad42cd5b`, `a2438a849`);
  generation-89 tools derived (`derive/derive_v89_tools.py`), V0' 89 (`v0-89/`, sdk/document-sdk.js restored in every stage: generation 89 is
  the first to change it since v24). Chain `chain-89.sh` (`ecd084584`): F3 `F3_83_EQUAL` 46/46, Calc sheet view, W live, `V0_PRIME_HOLDS`.
- **Units by hand** (`gen-89/units/`): shell 585, Calc 119, SDK 131, E1-C, four mutation tools, two static targets.
  `tests/calc-host-contract.test.mjs` now follows host 0.2.56 (red on 0.2.55's source first).
- **Host 0.2.56 code**: local branch `host-0.2.56` (`15abfff`) in `/home/jiajun/Projects/Nextcloud_Apps/litecore`, **working copy left on that
  branch** (the contract test reads it). Files action for DOCX/XLSX, controller mime sets + `mime` in the config, `documentFormat()` by mime,
  `saveAs()` (If-None-Match `*`, 412 = NAME_TAKEN, then the new file through the ordinary route). **Version not bumped, not packaged, not
  installed.** H8 tool written, never run: `findings/evidence/host-0.2.56/host_batch8.py`.
- **Disk** (the owner asked): 20 old `build/host-0.2.33..0.2.53` staging dirs removed (4 GB) and 944 git-ignored raw JSON copies under
  `link-batch-v23` (10.4 GB; each equal to its tracked `.json.gz`, list and restore in `LOCAL-RAW-REMOVED-2026-11-03.json`). Free 40 -> 54 GB.
  Not touched (owner's choice): `.claude/worktrees/agent-a0a3...` (2 GB, uncommitted edits inside), `libreoffice-25-2`, `libreoffice-26-2`,
  `collabora-25.04`.

## Blocked: the Writer regression nets

The owner's desktop X server died at **17:28**; kwalletd6 went with it. `v21_shakedown_common.pre_run_checks()` refuses when KWallet is
unreadable, so P5, P4, shift-lines, zoom, P1 and F4 (both browsers) refused to start in chain-89 (`gen-89/*/…stderr.txt`). That file is bound
by K's live-bound set (`k-0.2.45/live-bound-set.json`): do not edit it without the owner's decision. Starting kwalletd would not help (the
wallet would be locked). **The owner unlocks KWallet** (reconnect the desktop), then
`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`
must print `b false`. Then re-run those steps only: the first eight `step` lines of `findings/evidence/ms-formats/chain-89.sh` (P5 with
`--profile e2-editor-v33`), into a new folder (e.g. `gen-89/rerun-01/`), ~75 min.

## Waiting for the owner's decision: fable's advice on the tooling overhead

The owner asked whether the project spends too much on prose and measurement tools. **Corrected numbers** (my first answer said product
22k lines last week; 17,158 of those are per-profile worker copies): hand-written product ~4,100 lines last week vs tools+tests ~41k,
evidence scripts ~35k, prose ~17k. fable (advice, not a ruling) diagnosed **cadence**: 13 host releases, 8 shell generations, 6 links in 7 days
and two owner hand tests. Ranked advice: (1) release only for an owner hand-test slot -- between slots changes stay unfrozen on dev profiles;
(2) parametrise identity / release tools instead of deriving copies; workers derived into build/ only, never committed per profile; (3) V0'
reads the previous generation and the last counted K only; (4) a reader bug is fixed by execution and only its arm re-runs, no ruling; (5) a
version-only host bump: install, Files 52/52, the new arm; (6) one handoff per session, short commits, section 34.4 reduced to one number.
Rules it would retire or soften: CLAUDE.md "工作結論（2026-08-22）" (move to devlog); 驗收判準 §6 only for a new feature's product
criterion; §8-§10 scoped to counted K and shipped claims; §5 once per feature; memory `e2b-structural-lessons`'s "hash-bound files cannot
be edited or added beside" rewritten as "bind reports to tool sha + argv". The guard above is a deletion candidate. **Nothing of this is
adopted**: CLAUDE.md is the owner's to change. Ask first, in zh-TW, A/B/C (A = adopt fable's 1-6, B = only 1, C = keep).

## Next, in order

1. Ask the owner: KWallet unlocked? and the A/B/C above.
2. Re-run the Writer nets (above). If they hold: H8 red on 0.2.55 first (`host_batch8.py --out findings/evidence/host-0.2.56/h8-red-on-0255`,
   host-stack/bin first on PATH; expect red on H8/action-docx and -xlsx), then bump 0.2.56, package, install, H8, Files 52/52.
   The release tooling is not derived yet; if the owner adopts fable's (2) or (5), do not derive seven scripts from 0.2.55's -- write the
   lighter path the owner picks. `dist/sdk/document-sdk.js` is now the 0.2.56 one (both pages need it).
3. The owner's hand test on the newest install, one script (below), not version by version.

## Hand-test script for the owner (translate to zh-TW when handing over)

On the newest install, from Files:
1. Writer: open an .odt; zoom in/out; Shift+Up/Down/Home/End select; left/center/right/justify.
2. Writer: the 標題 menu (H1-H4, body); bullet and number lists on and off with the same button.
3. Writer: select across two paragraphs, press Enter (replaces the selection); copy a picture-only selection (the sentence says nothing to copy).
4. Calc: open an .ods; text colour, fill colour, alignment; switch sheets and back (the view is kept).
5. Calc: type, Enter, 復原 / Ctrl+Z, 重做 / Ctrl+Y; bold then one 復原.
6. Files: New spreadsheet; upload an .ods and open it.
7. Word: open a .docx from Files, type, 儲存, close, reopen: the text is there and the file is still .docx.
8. Excel: open an .xlsx, type in a cell, wait ~30 s (autosave), reopen: still .xlsx with the value.
9. 另存新檔 on the .docx and the .xlsx: ODF preselected; a taken name is refused in the dialog; then a new name -- the page opens the new
   .odt/.ods, the original unchanged.
10. A read-only shared .docx / .xlsx: opens view-only, no 另存新檔.

## Cautions

- `build/ms-formats-w/`, `build/calc-*` mirrors are tools' private dirs keyed by output name: a reused `--out` name fails at once (happened
  to the autosave probe tonight; re-run as `auto-v5`).
- `run_ms_formats_w.py --baseline` now refuses (the pages name v33/v5); the red case is run 02's.
- Do not add files under `sdk/` or `editor-shell-v2/` while a chain runs (bundle check).
- `s.wait_until` returns a truthy `{"timedOut": True}` on timeout; H8 uses `got()` for that.

## Section 34.4

- Fixed by execution: 4 (the H8 timeout reading before any run; the autosave probe's mirror-name collision; the host contract test; the
  shell mutation tool's indented anchor). Fixed by reading my own code before running: 2 (a survived mutation -- no checkpoint before the
  ODT save equivalence; the cutover-free `--baseline`). Fixed by review: 0. Fixed by ruling: 1 (W3, fable).
- Wrong statements, corrected: 2, both mine: 10.4's W3 toast clause (written from the Writer page's shape); the 22k product-lines figure to
  the owner (worker copies included).
