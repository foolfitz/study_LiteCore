# Host 0.2.54: New spreadsheet, LibreOffice's document icons, upload-and-open of .ods

Spec `specs/SPEC-P-demo-batch-6.md`. Uncounted candidate on the own stack; the nominal shipped host stays 0.2.45. Installed 2026-11-03 14:07 +0800.

- Host `8c95b50`, branch `host-0.2.54`, parent `6b1660c` (0.2.53). Host source only: 41 files, `SOURCE_DECLARED` in `prepare-release.py` plus `blank-ods/` (its `MANIFEST.json` and the 30 spreadsheets it lists).
- Engine `89860962782b3a21`, the same bytes as 0.2.53's package (no served file changed; `prepare-release.py` refuses another buildId). Archive `build/archive/host-0.2.54-engine-89860962782b3a21` (not in git).
- Release tools derived from 0.2.53's by `derive_host_0254.py` (closed list of replacements, each with its count).

| Read | Result |
|---|---|
| `static/` (before this release) | G1 byte-identical regeneration and its one-byte red, G2 odfvalidator 30/30 with hashes matching, G3 102 language/locale pairs and its missing-manifest red |
| `h6-red-on-0253-02` | `H6_RED` on both browsers, before the install, on `H6/new-menu/spreadsheet-offered`, `H6/new-menu/icons`, `H6/create-ods/the-chosen-blank` only. On 0.2.53 upload-and-open of .ods already holds (the file action took .ods before this batch), and New document holds. No fatal |
| `prepare-release.py --gate-only` (`gate-only.*`) | 0.2.53's gate plus G1, G1's red, G2, G3, G3's red |
| `prepare-release.py` (`package-run-01.*`) | packaged in 153 s; G1 and G3 run again on the candidate tree before packaging, argv and output in `release.json` `staticOnCandidate` |
| `check-delta.py`, `offline-package-check.py` | `DELTA_HOLDS` (nothing changed, added or removed, 46 same) with 9 red cases, `PACKAGE_HOLDS` with 22 |
| `install-0.2.54.py` | `CANDIDATE_INSTALLED`, documents and locks preserved |
| `host_batch6.py`, `host-features` | `H6_HOLDS`, Chrome 12/12, Firefox 12/12: 新文字文件 and 新試算表 in `+ 新增` with the two SVGs; the new .ods is byte for byte `en-US_zh-TW_A4.ods`, what `BlankDocument::chooseSpreadsheet` picks for admin (zh_TW, no locale); it opens in Calc, A1 typed and saved, read back over WebDAV with the blank's stated defaults; an .ods uploaded through Files' upload input opens in Calc, D9 saved and read back; an .odt uploaded the same way opens in Writer; New document still writes `en-US_zh-TW_A4.odt` and opens in Writer |
| `host_calc_theme.py`, `host-calc-theme` | `T6_HOLDS`, 94 controls |
| Files workflow | 52/52 |
| `host_batch.py`, `host_layout.py` | `HOST_BATCH_HOLDS`, `LAYOUT_HOLDS` |
| `capture-after.py` | `holds: true` |

Read by eye: `host-features/chrome-menu.png` (blue document, green spreadsheet, LibreOffice's icons), `host-features/firefox-calc.png` (the new spreadsheet in Calc, `Sheet1`, A1 saved).

## Two fixes to `host_batch6.py` before it counted

Both are in its docstring.

1. **By review, before the first run.** With no New spreadsheet entry the scenario returned at once, so `H6/create-ods` could never be red on 0.2.53 (the spec's red names it) and the upload and New document cells never ran there. The missing entry is now recorded as `H6/create-ods/the-chosen-blank` false; the rest runs on every host.
2. **By execution, on the first red run (`h6-red-on-0253`).** Every `landed` value was `{"timedOut": true}` and every cell took it as true: the route redirects to a versioned path (`/r/<buildId>-<hash>/ods-editor.html`, `tool-fixes/`), the predicate matched the unversioned one, and `bool()` of the timeout record is true. The routes are now the page names, as `host_layout.go` waits for them, and a cell takes `landed` only as the href string. `h6-red-on-0253` is kept; `h6-red-on-0253-02` is the red on the fixed tool, and its `landed` values are hrefs.

Section 34.4: fixed-by-execution +1, fixed-by-review +1.

## Rollback

`rollback-package.sh` restores 0.2.53's engine bytes, which are these bytes: it does nothing useful here. Batch 6 is host source; taking it back is a host commit on a new version.

**Pending:** the owner's hand test (handoff).
