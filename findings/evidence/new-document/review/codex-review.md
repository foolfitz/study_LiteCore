| Question | Verdict | One-line reason |
|---|---|---|
| 1 — N1–N6 | COUNTEREXAMPLE | Hidden menu entries, incorrect engine contents, and effective style overrides can pass. |
| 1 — N8–N9 | COUNTEREXAMPLE | Permission-test prerequisites and complete engine/page identity are not established. |
| 2 | NONE | No false rejection established for inches, existing user templates, or name conflicts. |
| 3 — Delta rules | SHOULD | N9 and the host bindings describe the 0.2.19 delta and require explicit replacement. |
| 3 — Recurring rules | SHOULD | Keep document behavior checks; distinguish candidate identity from historical equality. |
| 4 | COUNTEREXAMPLE | Missing offers, generations, and paired digests can still produce WORKS. |
| 5 | COUNTEREXAMPLE | A missing-offers baseline passes the entire 30-case red-case suite. |
| 6 | COUNTEREXAMPLE | Failed setting reads collapse to None, allowing unsuccessful restoration to look successful. |

## 1. Broken products accepted — COUNTEREXAMPLE

All report mutations below start from `findings/evidence/new-document/runs/2026-10-14T035226Z.json`; unspecified fields remain unchanged. These are constructed counterexamples, not observations against the running product. Verification used in-memory variants, the ten generator unit tests, and the red-case mode. No browser, ddev, Nextcloud, or make execution was performed.

**N1 — COUNTEREXAMPLE: the menu entry is inaccessible to the user.** Make the registered entry `display: none` while retaining its handler. The recorder checks DOM existence and invokes JavaScript `.click()`, which does not require visibility. It can therefore create the document successfully through an entry the user cannot see.

Concrete inputs/report: the normal creator listing; hidden `template-new-litecore-*` DOM element; `create.entrySeen=true`, `create.entryClicked=true`; subsequent baseline creation results. N1 passes because it checks the listing and `entrySeen` only. See [check_m3_new_document.py:106](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:106), [check_m3_new_document.py:318](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:318), and [check_m3_new_document.py:475](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:475).

**N2 — NONE: no defect found.** For reports produced by this recorder, the expected template comes from the fixed arm, and the requested path’s bytes must match its manifest record. See [check_m3_new_document.py:369](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:369), [check_m3_new_document.py:386](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:386), and [check_m3_new_document.py:482](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:482).

**N3 — COUNTEREXAMPLE: correct download, incorrect engine document.** The host fetches the new blank document, but the engine opens a cached document containing `OLD`, with the correct defaults. It receives the requested display name. Typing produces `zqxOLD`, which also passes N4.

Concrete fields: `create.host.fetched.status=200`, its `sha256` equals `createdFile.sha256`, and `create.opened={state:"ready", doc:run.name}`. The saved paragraphs are `["zqxOLD"]`, with `markCount=1` and the expected described defaults.

The recorder copies `fetched` from the host/page’s `data-litecore` JSON; it does not measure the bytes consumed by the engine. See [check_m3_locks.py:86](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_locks.py:86), [check_m3_new_document.py:340](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:340), and [check_m3_new_document.py:496](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:496).

**N4 — COUNTEREXAMPLE: typing corrupts additional content.** A defective insertion or serializer adds unrelated text while correctly inserting the marker. Concrete saved content: paragraphs `["zqx", "UNEXPECTED TEXT"]`, `markCount=1`, positive byte length, valid ZIP/XML, expected defaults, and matching saved/reopened digests. All three revisions advance normally and save reports `saved`. The scorer never compares the complete paragraph sequence with the expected result; the paragraph mutation remained `WORKS`. See [check_m3_new_document.py:509](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:509) and [check_m3_new_document.py:517](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:517).

The proposed “save into another path” attack alone found no defect: both creation and save observations read the same fixed `path`. See [check_m3_new_document.py:386](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:386) and [check_m3_new_document.py:402](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:402).

**N5 — COUNTEREXAMPLE: fetched saved bytes, displayed cached contents.** Fetch the saved document containing `zqx`, but reopen the cached pre-edit document. Concrete fields: `reopen.host.fetched.sha256=savedFile.sha256`, `reopen.opened.state="ready"`, `reopen.opened.doc=run.name`, and `reopen.a11y.offers="0"`. The engine’s missing marker has no measured representation in this report, so it reads `WORKS`.

The digest proves a host fetch; the additional engine-content observation is conditional on offers being `"1"`. See [check_m3_new_document.py:353](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:353) and [check_m3_new_document.py:520](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:520).

**N6 — COUNTEREXAMPLE: defaults are correct, effective styles are wrong.** Two in-memory ODT constructions passed `gen.compare`:

- Keep the generated `styles.xml`. In `content.xml`, define automatic paragraph style `P1`, parent `Standard`, with `style:language-asian="zh"`, `style:country-asian="CN"`, and `style:font-name-asian="Noto Sans CJK KR"`. Apply `P1` to the paragraph containing `zqx`. `describe()` still reports Asian language `zh-TW` and font `Noto Sans CJK TC`. With the actual variant’s saved digest and matching reopened digest, the complete strict score was `WORKS`.
- Keep the first page layout `Mpm1` as A4. Add a Letter layout named `Wrong`, then point the `Standard` master page to `Wrong`. `describe()` still reports A4 and `compare()` returns `[]`.

The reader examines default paragraph properties and the first page layout, without following paragraph styles or master-page references. See [make_new_document_templates.py:273](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/make_new_document_templates.py:273), [make_new_document_templates.py:278](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/make_new_document_templates.py:278), and [check_m3_new_document.py:535](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:535).

These are defective **saved outputs**. Changing the initial template would additionally encounter N2 and the generator check. N6 implements its literal default-property requirement, but that requirement does not establish the effective document defaults.

**N8 — COUNTEREXAMPLE: an invalid negative-test setup passes.** Change `readOnly.sharePermissions` to `3` and `readOnly.otherSees` to `"SGDNVW"`, retaining `create.status=403` and `adminAfter.fileid=null`. Strict scoring remains `WORKS`: the test no longer establishes a read-only share, yet accepts the refusal as N8 evidence. See [check_m3_new_document.py:425](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:425) and [check_m3_new_document.py:563](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:563).

A second path conceals a real unwanted file: creation writes the file but returns 403; the subsequent admin PROPFIND returns 500. `Client.props()` produces `fileid=null` from the error body and drops the response status. With previously observed `otherSees="SGDN"`, N8 passes. Concrete report evidence is `readOnly.create.status=403`, `readOnly.adminAfter.fileid=null`, and the corresponding log entry’s PROPFIND `status=500`. See [probe_m3_lock_semantics.py:104](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/probe_m3_lock_semantics.py:104) and [check_m3_new_document.py:438](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:438).

**N9 — COUNTEREXAMPLE: complete engine and HTTP page identity are unverified.** Changing only

```text
hostStatic.engineFiles["profiles/e2-editor-v19/sdk-worker.js"] = "0" × 64
```

leaves strict scoring `WORKS`, despite the specification requiring equality of every engine-file hash. The scorer compares only `buildId` and `servedPage`. See [SPEC-M3-new-document.md:171](/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-new-document.md:171) and [check_m3_new_document.py:548](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:548).

Furthermore, `hostStatic.servedPage` is copied from `engine/MANIFEST.json`; it is not an HTTP measurement. A serving/cache defect can return different page bytes while the clean host tree, manifest fields, and exercised document behavior remain unchanged. The report retains the control `buildId`, control `servedPage`, and empty `changedOutsideAllowed`, so N9 passes. See [check_m3_new_document.py:210](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:210).

## 2. Working products rejected — NONE

**Inches — no defect found.** The generator itself writes Letter as `8.5in × 11in`. Conversion produced `215.89999999999998 × 279.4` mm and classified it as Letter. The relevant unit test also passed. See [make_new_document_templates.py:53](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/make_new_document_templates.py:53), [make_new_document_templates.py:248](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/make_new_document_templates.py:248), and [test_new_document_templates.py:96](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tests/test_new_document_templates.py:96).

**User templates containing `zqx` — no defect found.** The runner submits the picker’s preselected blank choice; it does not select the user’s populated template. N2 also requires the generated blank template’s exact bytes. Merely having such a template in Templates does not make N4’s marker count fail. See [check_m3_new_document.py:327](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:327) and [SPEC-M3-new-document.md:276](/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-new-document.md:276).

**Name de-duplication — no defect found within the specified path.** Both the server lookup and reopen selector use the explicitly typed name. A renamed result would violate N2’s specified-name requirement as well as N3, rather than expose an isolated N3 false rejection. The documented conflict behavior was refusal of an already-used name, addressed by unique names. See [check_m3_new_document.py:348](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:348), [check_m3_new_document.py:371](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:371), and [SPEC-M3-new-document.md:189](/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-new-document.md:189).

## 3. Bindings and recurring meaning — SHOULD

The spec explicitly makes this acceptance specific to 0.2.19; its successful acceptance is not an overnight count. See [SPEC-M3-new-document.md:195](/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-new-document.md:195) and [SPEC-M3-new-document.md:241](/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-new-document.md:241).

**Properties of the 0.2.19 delta:**

- N9’s equality to 0.2.18’s build/page is red by construction when v20 and shell v68 change those artifacts.
- N9’s host diff from `96a87d8`, with the existing allowed paths, rejects the new engine package and any changed host files outside that list.
- Strict `HOST_COMMIT=afbaf3c` and `HOST_VERSION=0.2.19` reject 0.2.20.
- `repo_static()` describes the historical round through its fixed start and `ROUND_PATHS`; it is not a general candidate-integrity rule.

References: [check_m3_new_document.py:89](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:89), [check_m3_new_document.py:214](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:214), [check_m3_new_document.py:239](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:239), and [check_m3_new_document.py:573](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:573).

**Recurring properties to retain:** the two-arm/two-browser document behavior in N1–N6; N8’s validated permission scenario; generator identity and N10/N12; clean committed candidate inputs; explicit candidate bindings; and verified settings restoration. The blank manifest binding need not change if its bytes remain unchanged.

**Silent meaning changes to prevent:**

1. Updating `CONTROL_BUILD_ID` and `CONTROL_PAGE_SHA256` to the candidate changes “unchanged from 0.2.18” into “matches the selected candidate.” That is a different rule, requiring an explicit amendment.
2. Updating `CONTROL_HOST_COMMIT` to the candidate makes the host diff empty by construction. It ceases to establish a bounded delta.
3. Rebinding the host alone leaves `redCorruptReport.red` accepted from an older host. That preserves historical evidence, not proof that the new candidate still cleans up failed creation. The report is chosen by `latest()` and its candidate identity is not checked.
4. When a new profile reports `offers="1"`, N5’s paragraph-text half becomes active. That conditional activation is intended, but unknown/missing offers must first be rejected.

See [check_m3_new_document.py:548](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:548), [check_m3_new_document.py:581](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:581), [check_m3_new_document.py:597](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:597), and [check_m3_new_document.py:776](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:776).

## 4. Non-vacuity — COUNTEREXAMPLE

The four requested mutations produced:

| Mutation | Strict result | Reference |
|---|---|---|
| `runs[0].keys=[]` | NOT_ESTABLISHED | `wasm_sdk_probe/tools/check_m3_new_document.py:507` |
| Remove `runs[0].reopen.a11y.offers` | **WORKS**, with `unknown (None)` | `wasm_sdk_probe/tools/check_m3_new_document.py:528` |
| N10 `validated=passed=0` | NOT_ESTABLISHED | `wasm_sdk_probe/tools/check_m3_new_document.py:558` |
| Remove `readOnly` | NOT_ESTABLISHED | `wasm_sdk_probe/tools/check_m3_new_document.py:563` |

For the three correctly rejected blocks: **no defect found**.

Additional concrete variants all produced strict `WORKS`:

| Mutation | Missing guard | Reference |
|---|---|---|
| Remove the entire `reopen.a11y` block, or set `offers="garbage", text=""` | Unknown offers do not fail scoring. | `check_m3_new_document.py:528`, `:598` |
| Remove `genBefore` and `genAfter` from all three key records | `None == None` establishes “unchanged.” | `check_m3_new_document.py:510` |
| Remove both `savedFile.sha256` and `reopen.host.fetched.sha256` | `None == None` establishes saved-byte equality. | `check_m3_new_document.py:522` |
| Set N10 `validated=passed=1`, keeping `hashesMatch=true` and the 30-file manifest | The nonzero count is not reconciled with the generated set. | `check_m3_new_document.py:558` |
| Set N12 to `{passed:true, languages:0, inputs:0, manifestFiles:0}` | Only the summary boolean is read. | `check_m3_new_document.py:560` |

The basename references above denote `wasm_sdk_probe/tools/check_m3_new_document.py`.

There is also a mode-specific vacuity: set `label="shakedown"` and `runs=[]`, retaining the baseline static/read-only fields. `score(..., strict=False)` returns `WORKS`; `--score` selects that mode from the report label. This does **not** bypass `score(..., strict=True)`, but the printed verdict has the same `NEW-DOCUMENT WORKS` wording. See [check_m3_new_document.py:545](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:545), [check_m3_new_document.py:604](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:604), and [check_m3_new_document.py:747](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:747).

## 5. Red-case census — COUNTEREXAMPLE

The committed baseline passed, and **30** entries ran and turned red with no skips. The source contains 30 entries, despite §7.1 saying 29. See [check_m3_new_document.py:611](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:611) and [SPEC-M3-new-document.md:237](/home/jiajun/LibreOffice/study_LiteCore/specs/SPEC-M3-new-document.md:237).

Concrete self-test counterexample: remove only `runs[0].reopen.a11y.offers`. Running `red_cases()` on that in-memory report returned **0**, with a green baseline and all 30 mutations red. Thus the suite accepts the vacuous N5 report identified in Q4.

All line references in the following census are to `wasm_sdk_probe/tools/check_m3_new_document.py`. “None” means no corresponding entry in `RED_CASES`.

| `score_run` clause | Line | RED_CASES coverage |
|---|---:|---|
| Fatal run rejects all N1–N6 | 470 | None |
| N1 creator present and exactly one | 476 | `N1-no-creator` covers empty; none for duplicates |
| N1 extension `.odt` | 476 | None |
| N1 exact mimetypes | 476 | `N1-ott-offered` |
| N1 menu entry seen | 478 | None |
| N2 PHP choice | 482 | `N2-php-chose-other` |
| N2 created digest | 484 | `N2-other-bytes` |
| N2 created byte length | 484 | None |
| N2 fileid present | 486 | None |
| N3 landed string and matching fileId | 492 | `N3-wrong-file` covers wrong ID; none for absent/non-string URL |
| N3 origin in Files | 494 | None |
| N3 fetched digest/status | 497 | `N3-page-fetched-other` covers digest; none for status |
| N3 ready state/document name | 500 | None for either |
| N4 click timeout/success wording | 504 | `N4-click-refused` covers failure wording; none for timeout or absent success wording |
| N4 number of keys | 507 | None |
| N4 numeric revisions | 510 | None |
| N4 revision increments | 510 | `N4-no-revision` |
| N4 unchanged generation | 511 | None |
| N4 saved outcome | 514 | `N4-save-not-saved` |
| N4 saved HTTP status | 517 | None |
| N4 nonzero saved bytes | 517 | `N4-zero-bytes` |
| N4 exactly one marker | 517 | `N4-marker-missing`; none for excess markers |
| N4 no describe error | 517 | None |
| N5 landed string | 522 | None |
| N5 reopened digest equality | 522 | `N5-reopened-other-bytes` |
| N5 ready state/document name | 525 | None for either |
| N5 offered paragraph contains marker | 528 | `N5-live-region-lies` |
| N6 manifest record present | 532 | None |
| N6 western/Asian language | 535 | `N6-western-en-GB`, `N6-asian-zh-CN` |
| N6 complex language | 535 | None |
| N6 western/Asian/complex fonts | 535 | `N6-font-KR` covers Asian; none for western or complex |
| N6 paper classification | 535 | `N6-paper-letter-in-TW`, `N6-paper-a4-in-EN` |

N6 delegates comparisons to [make_new_document_templates.py:296](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/make_new_document_templates.py:296). The automatic-style and active-layout defects have no red case.

| `score` clause | Line | RED_CASES coverage |
|---|---:|---|
| Strict arm/browser set | 545 | `one-browser`, `one-arm` |
| N9 control buildId | 548 | `N9-other-engine` |
| N9 control page digest | 548 | `N9-page-moved` |
| N9 host paths outside allowance | 550 | None |
| N9 repository product paths touched | 552 | `N9-product-touched` |
| N9/N10 generator identity | 554 | None |
| N10 passed equals validated | 558 | `N10-validator-red` |
| N10 hashes match | 558 | None |
| N10 validation nonempty | 558 | None |
| N12 passes | 560 | `N12-closure-red` |
| N8 creation status 403 | 563 | `N8-created-anyway` |
| N8 no admin-visible fileid | 563 | `N8-file-appeared` |
| N8 other permissions nonempty | 563 | None |
| Strict counted label | 566 | None |
| Strict clean host | 568 | None |
| Strict committed round tools | 571 | `N9-tools-uncommitted` |
| Strict nonempty round commits | 571 | None |
| Host commit binding: written/matching | 573 | None for either |
| Host version binding: written/matching | 573 | None for either |
| Blank manifest binding: written/matching | 574 | None for either |
| N1 historical control red | 579 | `control-not-red` |
| N7(b) corrupt-template control red | 581 | None |
| Settings restored | 584 | `settings-not-restored` |

Mutation exceptions are not counted as red: the applicable caught exceptions print `SKIP` and make the suite fail. Scoring exceptions also cannot produce successful completion. **No defect found** in that handling. See [check_m3_new_document.py:650](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:650).

## 6. Settings restoration — COUNTEREXAMPLE

**Failed restoration can leave settings changed while writing a report that says restoration succeeded.**

Concrete path:

1. Original locale is genuinely unset, so `adminSettingsBefore.locale=null`.
2. The EN arm sets locale to `en_US`.
3. Restoration’s `occ ... --delete ... locale` fails with exit 1.
4. Its readback command also fails. `user_setting()` converts every nonzero result to `None`.
5. Restoration compares that `None` with the original `None` and sets `ok=true`.

Concrete report:

```json
{
  "adminSettingsBefore": {"lang": "zh_TW", "locale": null},
  "settingsRestored": {
    "lang": {"key": "lang", "value": "zh_TW", "exit": 0, "readback": "zh_TW"},
    "locale": {"key": "locale", "value": null, "exit": 1, "readback": null},
    "ok": true
  }
}
```

The actual locale remains `en_US`. Mocked command results reproduced the erroneous locale-success comparison; inserting the failed locale result into the accepted report still produced strict `WORKS`.

A caught browser `fatal` can precede the same restoration failure: the report is still written, although its document verdict is then NOT_ESTABLISHED. Without a browser fatal, the false restoration result can accompany WORKS.

References: [check_m3_new_document.py:137](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:137), [check_m3_new_document.py:142](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:142), [check_m3_new_document.py:405](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:405), [check_m3_new_document.py:802](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:802), and [check_m3_new_document.py:819](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:819).

**An initial read failure can also destroy the original setting.** If the actual original locale is `de_DE` but its initial read fails, `original.locale` becomes `None`. Successful final deletion then removes the real original locale and is recorded as restored. Concrete fields are `adminSettingsBefore.locale=null`, successful deletion/readback-null, and `settingsRestored.ok=true`; the initial command failure is not preserved. See [check_m3_new_document.py:767](/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/tools/check_m3_new_document.py:767).

**KeyboardInterrupt — no defect found for the specific “changed settings and a newly written report” conjunction.** An interrupt inside the protected loop enters `finally`. If it propagates, or restoration itself raises, execution never reaches report writing. This leaves a separate report-persistence gap, but it is not a falsely successful newly persisted report. Successful restoration after an ordinary caught browser exception likewise restores the settings.