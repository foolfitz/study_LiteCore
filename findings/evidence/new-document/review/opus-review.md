# Seat 1 (opus): review of `check_m3_new_document.py` before its first counted use (§34.3)

The tool is `wasm_sdk_probe/tools/check_m3_new_document.py` at repo HEAD `3b818514` (runner sha in the committed report: `f9a46a05…`). The report under review is `findings/evidence/new-document/runs/2026-10-14T035226Z.json`. All work was done read-only. The tool, its sibling modules and the report were copied to `scratchpad/opus-newdoc/{tools,report}/`. Every verdict marked "demonstrated" below is the output of the copied tool's own CLI (`--score` or `--red-cases`) on a mutated copy of the committed report, or of the tool's own reader (`gen.describe` / `gen.compare`) on a crafted ODT. The harness scripts are `harness/demos.py`, `harness/crafted.py` and `harness/census.py`. Their outputs are in `report/*.out`.

Threat-model filter (§34.2): every counterexample below can be produced by an honest run of the committed runner against a defective product or after an operator accident. None needs a forged report or an edited constant. The Q5 checker mutants are the one exception: that is the census the brief asked for.

## Summary

| # | Verdict | One line |
|---|---|---|
| 1 | **COUNTEREXAMPLE** | Five broken products read `WORKS`. (a) A save that replaces the file under a new fileid passes N4 and N5, because fileid continuity is never compared. (b) N5's "the engine got the marked bytes" rests only on the host's own GET, and nothing on the engine side is read on reopen. (c) N6 reads only `default-style`, and takes the *first* `page-layout`, not the master page's; four crafted saves with wrong languages, fonts or paper read `[]`. (d) N8's 403 is produced by core before our listener runs, and there is no positive control, so "non-owner creation is broken" passes. (e) N9 hashes the engine manifest's *declaration* and not the served page, and the host's `engine/` is gitignored, so git sees nothing. N1, N2, N3: no defect found. |
| 2 | **COUNTEREXAMPLE** (latent) + NONE on the three named candidates | On any profile that offers caret paragraph text *and* has the structure projection, the page empties `#a11y-para` by design (`deferredToStructure="1"`). N5 ignores that field and goes red on a working product (demonstrated). Lower: N6 compares font-face *declaration names*, so a collision-suffixed `Noto Sans CJK TC1` reads red. Inches, a Templates `.odt` containing `zqx`, and de-duplication: NONE. |
| 3 | **COUNTEREXAMPLE** | N9's engine half (`CONTROL_BUILD_ID`/`CONTROL_PAGE_SHA256`) is red by construction on 0.2.20 (demonstrated). If only the constants are updated, `CONTROL_HOST_COMMIT`=HEAD makes the host-diff clause a tautology. `redCorruptReport` (N7(b)) is taken by `latest()` with no host binding (the report has no `hostCommit` field), so 0.2.19's measurement is silently inherited. |
| 4 | **COUNTEREXAMPLE** | A report with `reopen.a11y` missing, or `offers: null`, reads `WORKS` (the N5 registry says `unknown (None)` but that is not a problem). The same holds for generations that were never read, and for a non-counted report with zero runs under `--score`. The other three named inputs (empty `keys`, `N10.validated` 0, no `readOnly`) are correctly red. |
| 5 | **COUNTEREXAMPLE** | Census: 14 top-level clauses have no red case. N2's byte comparison is guarded only *collaterally*: `N2-other-bytes` goes red via N3. `red_cases` checks `not works`, not *which rule* fired. Three checker mutants (N2 bytes deleted; bindings + N7(b) deleted; five clauses deleted) all pass `--red-cases` with exit 0 (demonstrated). |
| 6 | **COUNTEREXAMPLE** | `user_setting` returns `None` both for "not set" (occ exit 1) and for any occ failure. If the first read fails, the restore *deletes* the owner's `core/lang`, the readback `None` matches, `ok: true`, and the report reads `WORKS` (demonstrated). Separately, `preflight` excludes this tool's own name, so a second instance takes the first's switched values as "original" and restores to them. SHOULD: SIGTERM skips `finally`, and the `run_readonly` teardown is not in a `finally`. |

---

## 1. Find a broken product that this tool passes: COUNTEREXAMPLE

### N1: no defect found
Every N1 failure mode I could build is either outside the spec's N1 text (the label is a D8 ruling and not part of N1) or makes the run die downstream. For example, a disabled entry means `dialogSeen` is false, `landed` fails and the run ends `fatal`.

### N2: no defect found
The created bytes are compared with the manifest record of the arm's *expected* file (`check_m3_new_document.py:484`). The manifest is pinned by `MANIFEST_SHA256` and `blankGeneratorCheck` (`:554`, `:573-578`). The PHP half is called with the arm's intended inputs (`:376`), not with what the listener actually read, but a listener that read the wrong locale writes the other paper's file, and the sha check catches that. One minor SHOULD tied to N7's wording ("不會悄悄產生…的檔"): nothing lists the folder before and after creation. A stray second file, such as a 0-byte twin from a double-fired submit, would be invisible. A PROPFIND diff of `新文件 測試資料夾` that requires exactly one new entry would cover it.

### N3: no defect found
`fetched.sha256` (`:497`) is the host's own measurement (see N5). N3 is still backed on the engine side, because N4 finds `zqx` in a file the engine saved and N6 finds the template's defaults in it.

### N4 + N5: COUNTEREXAMPLE, the file is replaced under a new fileid (demonstrated)
The brief's candidate ("N4 reads `savedFile` by which path?"): N4 reads by **path** (`run_once:402`, `file_facts(admin, f"{FOLDER}/{name}")`). A save that writes the marker into a *different* file therefore leaves the original without `zqx` and reads red. That case is covered.

What is not covered is **identity at the same path**. `score_run` never compares `savedFile.fileid` with `createdFile.fileid` (`:516-518`). N5 checks only `isinstance(reopen.landed, str)` (`:522`), not that its `fileId` is the created one. A host that saves by "PUT to a temp file, then MOVE over the original" gives Nextcloud a new fileid. That is a plausible atomic-save change, and it loses versions, shares and comments. Such a host passes N4 and N5: Files reopens the new id by name, and the host fetches the marked bytes.

- Inputs that would be mis-judged: `runs[*].savedFile.fileid`, `runs[*].reopen.landed` (`fileId=`), `runs[*].reopen.host.file.id`.
- Demonstration: `report/q1-fileid-replaced.json`, with all four cells moved to fileid+50000, gives `NEW-DOCUMENT WORKS … problems=[]`.
- Fix: one equality, `saved.fileid == created.fileid == reopen fileId`. The counted report already has `18245 == 18245`, so the change is free.

### N5: COUNTEREXAMPLE, "who fills `fetched`?" (by construction, low plausibility)
`fetched` is written by the **host**, from its own WebDAV GET (`~/Projects/Nextcloud_Apps/litecore/js/litecore-editor.js:416-428`). That happens before the page has the bytes. The page then opens whatever `HOST.load()` returns (`wasm_sdk_probe/web/e2-editor-app.js:3182`). On reopen, N5 reads only three things: the host's GET hash, `state == ready`, and the display name. The only engine-side readback is the a11y half, and that is `NOT_OFFERED` in all four cells. A page that reopens a cached or recovered document instead of the handed bytes therefore reads `WORKS`, and no report field would differ.

The spec text "(引擎拿到的就是含標記的那份)" (the engine got the marked copy) is carried by a proxy upstream of the engine. A cheap engine-side witness: after reopen, press End, type one more key and save, then require the server paragraphs to equal `["zqx"+key]`.

### N6: COUNTEREXAMPLE, the reader sees only two elements (demonstrated with the tool's own reader)
`describe()` (`make_new_document_templates.py:274-280`) reads `office:styles/style:default-style[paragraph]/style:text-properties`. It also reads the **first** `office:automatic-styles/style:page-layout`, whichever master page uses it. `compare()` (`:302-308`) compares the `style:font-name*` *declaration names*. `harness/crafted.py` starts from the generator's own `en-US_zh-TW_A4.odt` and applies one change per case:

| crafted save (TW arm, expects A4 / zh-TW / TC) | `gen.compare` |
|---|---|
| 1. `content.xml`: the typed paragraph uses automatic style `P1` with `zh-CN`, `Noto Sans CJK KR`, `en-GB` (the brief's candidate) | `[]` |
| 2. `styles.xml`: the `Standard` paragraph style overrides asian `zh-CN` / KR over a correct default-style | `[]` |
| 3. `styles.xml`: master page `Standard` → `Mpm2` = **Letter**; an unused `Mpm1` = A4 comes first | `[]` (reads A4) |
| 4. `styles.xml`: font-face declared as `style:name="Noto Sans CJK TC"` with `svg:font-family="'Noto Sans CJK KR'"` | `[]` |

The report stores only `savedFile.described`, which is the output of `describe()`. Each of these engine defects therefore produces a report identical to the committed one and reads `WORKS`.

Case 1 is the spec's own motivating leak (browser language → asian language), moved from the default style onto the typed text. The spec's N6 row names only the default style, so the tool matches the spec. The predicate is what is too narrow.

Fixes, both cheap:
- Resolve the page through `master-page[@style:name='Standard']/@style:page-layout-name`.
- Assert that no `style:text-properties` in `content.xml` or `styles.xml` sets a `language*`, `country*` or `font-name*` that differs from the default. The template sets none, so any such attribute is a leak.

### N8: COUNTEREXAMPLE, no positive control (whole-tool gap that N8 is the only place to close)
In a read-only folder, core's `newFile()` throws (`nextcloud/lib/private/Files/Template/TemplateManager.php:171`) **before** `FileCreatedFromTemplateEvent` is dispatched (`:173`). Our listener never runs there, so N8's `403 + no file` (`check_m3_new_document.py:563`) measures Nextcloud only. Nothing in the tool runs our listener for any user other than admin, in admin's own folder.

The broken product: creation fails for every non-owner, or in any shared folder. For example, a listener that derives language or locale from `$target->getOwner()` and throws, or a `putContent` path that fails on shared storage. That product reads `WORKS`. Its `readOnly` block is byte-for-byte the committed one, because `message` is "Failed to create file from template" in both cases.

Fix: the same `lcprobe` creates once in a **writable** share (permissions 31), or in its own home, and the tool requires 200 with bytes equal to the file `choose()` gives for lcprobe's language. That also makes N8's 403 attributable to the permission.

### N9: COUNTEREXAMPLE, a declaration in place of the served bytes (demonstrated in part)
- `servedPage` is the manifest's **declared** hash, `manifest.files["e2-editor-app.js"].sha256` (`check_m3_new_document.py:219`). It is not an HTTP read. The spec's N9 row says "HTTP 讀到的 e2-editor-app.js 解碎後 sha256" (the sha256 of the e2-editor-app.js read over HTTP) (`specs/SPEC-M3-new-document.md:171`).
- The host serves the packed file from disk without verifying it, and the ETag comes from the manifest (`lib/Controller/EditorController.php:263-300`).
- The host's `engine/` is **gitignored** (`~/Projects/Nextcloud_Apps/litecore/.gitignore:4`, `/engine/`). Neither `hostDirty` (`git status --porcelain`) nor `changedSinceControl` (`git diff 96a87d8..HEAD`) can ever see an engine change.

So if `engine/e2-editor-app.js.gz`, or a worker, is swapped while `MANIFEST.json` stays stale, N9 is green. That is "頁面被移動" (the page was moved) in §34.2's own threat list, and the 068 mirror swap in CLAUDE.md is a precedent for it.

In addition, the spec asks for "每個檔的雜湊等於 0.2.18 的" (every file's hash equal to 0.2.18's). `engineFiles` is recorded (`:220`) but never read by `score`, and `buildId` is taken as declared rather than recomputed. Demonstration: `report/q1-engine-files-changed.json` declares a different `sdk-worker.js` and session JS under the same buildId and gives `WORKS`. The buildId is the first 16 hex characters of sha256 over `{path: sha256}` (`package_m3_engine.py:16,109`), so it can be recomputed from `engineFiles` at no cost. The served-bytes half needs one GET.

---

## 2. Find a working product that this tool fails: COUNTEREXAMPLE (latent), NONE on the named candidates

- **N6 tolerance against Letter written in inches: NONE.** `to_mm` handles `in`/`inch` (`make_new_document_templates.py:251-255`). `8.5in × 11in` gives 215.9 × 279.4. The WASM engine writes A4 *in inches* (`8.2681in × 11.6929in`, hand-test README), and that classifies as A4 at 210.01 × 297.0 (crafted case 6, and the counted report's `pageMm`). Lower note: ODF-legal `pc`/`px` are not parsed, and `51pc × 66pc` reads `paper None` (crafted 6c). LibreOffice does not write those units for page sizes.
- **N4 `markCount == 1` with a Templates `.odt` containing `zqx`: NONE.** The listener leaves `template !== null` alone, and the runner submits the picker with "Blank" preselected (`templatePath ''`). SHOULD: `PICKER_TILES` records `checked: ["on"]` (`check_m3_new_document.py:116-119`), which is the radio's *value* and not *which* tile. If a core change preselected a user template, the run would go red on N2 and the report could not say why. Record the checked tile's title.
- **N3 `opened.doc == run.name` under de-duplication: NONE.** Core does not de-duplicate. An existing path throws "File already exists" and gets a 403 (`TemplateManager.php:146-149`), and the dialog refuses the name. With amendment 5's per-run names, a collision ends the run `fatal`, which is red on the instrument and never `WORKS`.
- **COUNTEREXAMPLE (latent): N5's conditional half on a structure-projection profile.** The page deliberately sets `#a11y-para` to `""` whenever the structure projection has a focused node, and says so in `data-deferred-to-structure="1"` (`web/e2-editor-app.js:408-419`, "so a probe can tell 'silent because the structure has it' from 'silent because there is nothing to say'"). `A11Y` records `deferred` (`check_m3_new_document.py:113-115`), but `score_run:528` ignores it. On a profile that offers caret paragraph text *and* the projection, every cell reads N5 red. Demonstration: `report/q2-a11y-deferred-to-structure.json` (`offers "1"`, `text ""`, `deferred "1"`) gives `NOT_ESTABLISHED … N5` in all four cells. This does **not** bite on 0.2.20: v20's `editorContract` has no `caretParagraphText` (`dist/profiles/e2-editor-v20/sdk-manifest.json`), so the half stays `NOT_OFFERED`. It bites on the first a11y-core profile.
- **Lower:** N6 compares declaration names. LibreOffice suffixes a font-face name on collision, and a save with `style:font-name-asian="Noto Sans CJK TC1"` whose family is TC reads red (crafted case 5). Resolving the name through `font-face-decls` to `svg:font-family` fixes both this and Q1's case 4.
- **SHOULD:** the N4 click predicate and the `click()` wait are bound to the page's zh-TW strings `定位游標` and `失敗` (`score_run:504`; `check_m3_production_ui.py:273`). A page that localizes `#s-latency` reads N4 red, including in the EN arm. Also, `定位游標：唯讀` (the view-only refusal, `e2-editor-app.js:1937`) passes the click predicate. The keys then catch it.

---

## 3. Bindings that belong to 0.2.19 only: COUNTEREXAMPLE

| Rule | Class | On 0.2.20 |
|---|---|---|
| N9 engine package `buildId == CONTROL_BUILD_ID`, `servedPage == CONTROL_PAGE_SHA256` (`:548`) | **0.2.19 delta** ("engine unchanged since 0.2.18") | **Red by construction**: engine v20 changes both. Demonstrated: `report/q3-next-host.json` with only `HOST_*` moved gives `NOT_ESTABLISHED`, `N9 engine package …`. |
| N9 host diff `96a87d8..HEAD` ⊆ `ALLOWED_CHANGED` (`:214`, `:550`) | **0.2.19 delta** | Red if 0.2.20 touches `js/`, `lib/Controller/`, and so on. Blind to `engine/` either way (gitignored). |
| N9 repo half: round commits since `0e7f7f64` touch no product path (`:244-250`, `:552`) | **0.2.19 delta** | Goes red the first time a commit that touches `ROUND_PATHS` also touches a product path. That includes `findings/evidence/new-document/`, so a "bind v20 in every runner" commit that also edits `web/` would trip it. Clean today (recomputed: five round commits, no product hits). |
| `HOST_COMMIT`, `HOST_VERSION`, `MANIFEST_SHA256`; `hostDirty`; `roundToolsUncommitted` | Recurring bindings and hygiene | Update and keep. |
| N1–N6, N8, N10, N12, arms × browsers, `settingsRestored` | Recurring properties of "New document" | Keep. Caveats: N1's "exactly one litecore creator" is D1's scope and goes red when `.ods` arrives. N4's click strings are bound to the page (Q2). |
| `controlReport.red` (N1's red case) | Tool property, red once on 0.2.18 | Inheriting it is correct. |
| `redCorruptReport.red` (N7(b)) | **A product property**, measured on 0.2.19 | **Silently inherited.** See below. |

**Rules whose meaning changes silently when only a binding is updated:**
1. **`CONTROL_HOST_COMMIT`.** The obvious way to make N9 green on 0.2.20 is to move the three `CONTROL_*` constants to 0.2.20's values. Then `git diff <HEAD>..HEAD` is empty, `changedOutsideAllowed` is `[]` for every possible host, and `ALLOWED_CHANGED` constrains nothing: a tautology. The buildId/page clause becomes an identity binding ("the host serves package X"). That is a legitimate recurring check, but it still runs under the name "only the host changed", which would be false for 0.2.20.
2. **`redCorruptReport`.** It is picked by `latest(EVIDENCE/"red-corrupt")` (`:726-728`, `:776`), and strict mode checks only `.red` (`:581`). The red-corrupt report records no `hostCommit` (`red_corrupt`, `:689-705`), only `hostDirty`, so it cannot even be bound after the fact. After the next listener change (D12 / `Language=`), N7(b) would still read "refused, no file" from 0.2.19's run.
3. **N5's a11y half** flips from `NOT_OFFERED` to a live clause on whichever profile first offers caret paragraph text, with no binding change. It has never run live, so its first green or red would be inside a count (§6 "先讓它紅一次", make it go red once first). Combined with Q2, its first live run would read red.

Recommendation, within §34.5's spirit of adding no new bindings: count the 0.2.19 delta clauses (N9 engine-vs-0.2.18, host diff, repo half) as 0.2.19's acceptance only, and drop them from the chain's count. Bind the red-corrupt report to the host commit, or re-run it whenever `lib/Template/` or `lib/Listener/` changes.

---

## 4. Non-vacuity: COUNTEREXAMPLE

| Input | Verdict | Where |
|---|---|---|
| `keys` empty | red (N4, `len(keys) != 3`, `:507`) | `report/q4-ctl-keys-empty.json` |
| `reopen.a11y.offers` missing | **`WORKS`** | `report/q4-no-a11y.json` (`reopen.a11y` deleted in all cells) and `q4-a11y-offers-null.json` (`offers: null`). `score_run:528` fires only on `offers == "1"`. `n5ParagraphTextHalf` says `unknown (None)` (`:598`) but nothing makes that a problem. A page that renames or removes `#a11y-doc` produces exactly this. Per CLAUDE.md §3, `unknown` is neither "nothing to guard" nor "guarded", and it must not pass. |
| `checks.N10.validated` 0 | red (`:558`, `not validated`) | `report/q4-ctl-n10-zero.json` |
| `readOnly` absent | red (`:563`) | `report/q4-ctl-readonly-absent.json` |

Two more vacuous inputs read `WORKS`:
- **Generations never read.** `score_run:510-511` applies `digits()` to revisions but compares `genBefore == genAfter` raw. A page that leaves `#s-generation` empty or constant reads "generation unchanged". That is a worker restart going undetected. Demonstrated: `report/q4-generation-unread.json` (all `None`) gives `WORKS`.
- **Non-counted label, zero runs.** `score(..., strict=False)` skips arms × browsers (`:545`). `--score` uses strict only for `label == "counted"` (`:747`). Demonstrated: `report/q4-shakedown-no-runs.json` gives `NEW-DOCUMENT WORKS - problems=[]`. A shakedown never counts, but the tool should not print `WORKS` over nothing.

---

## 5. Red-case coverage: COUNTEREXAMPLE

Census of every clause in `score_run` (`:468-536`) and `score` (`:539-599`). The column "red case" names the `RED_CASES` entry (`:611-642`) that exercises the clause. "Guarded" means the following: neutralizing the clause in a copy of the tool makes at least one red case go GREEN while the baseline stays GREEN (`harness/census.py`, output `report/census.out`).

| Clause (line) | Red case | Guarded |
|---|---|---|
| `fatal` (470) | — | no |
| N1 listing (476): not lite / len≠1 / extension / mimetypes | `N1-no-creator`, `N1-ott-offered` | yes as a clause. `len == 2` and `extension ≠ .odt` have no case. |
| N1 `entrySeen` (478) | — | no |
| N2 PHP choice (482) | `N2-php-chose-other` | yes |
| **N2 bytes (484)** | `N2-other-bytes` | **no, collateral only.** The case also fires N3 (`fetched ≠ created`). With the clause deleted, `--red-cases` still exits 0 (`report/mutant_n2_bytes_gone.out`: `RED N2-other-bytes … TW/chrome=N3`). |
| N2 fileid (486) | — | no |
| N3 landed fileId (492) | `N3-wrong-file` | yes |
| N3 `clickedFrom` (494) | — | no |
| N3 fetched sha / status (497) | `N3-page-fetched-other` | sha yes; status no |
| N3 opened state/doc (500) | — | no |
| N4 click (504) | `N4-click-refused` | yes |
| N4 `len(keys)` (507) | — | no |
| N4 per key (510): revision / generation | `N4-no-revision` | revision yes; generation no |
| N4 save (514) | `N4-save-not-saved` | yes |
| N4 saved file (517): getStatus / bytes / markCount / describeError | `N4-zero-bytes`, `N4-marker-missing` | bytes and markCount yes; getStatus and describeError no |
| N5 landed / fetched (522) | `N5-reopened-other-bytes` | fetched yes; landed no |
| N5 reopened state/doc (525) | — | no |
| N5 a11y (528) | `N5-live-region-lies` | yes |
| N6 no record (532) | — | no |
| N6 compare (535) | five N6 cases | yes. Complex language and the western and complex fonts have no case, but `compare` is one loop. |
| arms × browsers (545) | `one-browser`, `one-arm` | yes |
| N9 buildId / page (548) | `N9-other-engine`, `N9-page-moved` | yes |
| N9 `changedOutsideAllowed` (550) | — | no |
| N9 product touched (552) | `N9-product-touched` | yes |
| `blankGeneratorCheck.identical` (554) | — | no |
| N10 (558): passed / hashesMatch / validated>0 | `N10-validator-red` | passed yes; the other two no |
| N12 (560) | `N12-closure-red` | yes |
| N8 (563): 403 / adminAfter / otherSees | `N8-created-anyway`, `N8-file-appeared` | first two yes; otherSees no |
| label (566) | — | no |
| `hostDirty` (568) | — | no |
| round committed (571): uncommitted / empty `roundCommits` | `N9-tools-uncommitted` | first yes; second no |
| **bindings × 3 (573-578)** | — | **no.** Deleting the comparison keeps `--red-cases` at exit 0 (`report/mutant_bindings_gone.out`). |
| `controlReport.red` (579) | `control-not-red` | yes |
| **`redCorruptReport.red` (581)** | — | **no** |
| `settingsRestored.ok` (584) | `settings-not-restored` | yes |

The census finds **14 top-level clauses with no red case**: fatal, entrySeen, N2 fileid, clickedFrom, N3 opened, `len(keys)`, N5 reopened, N6 no-record, host diff, generator check, label, hostDirty, the three bindings, and N7(b). It also finds one clause guarded only collaterally (N2 bytes) and ten disjuncts with no case.

The structural cause is `red_cases:659`, `ok = ok and not result["works"]`. It never asks *which* rule fired, so every red case is satisfied by whatever rule fires first. Demonstrated: `report/mutant_five_clauses_gone.out` deletes fatal, N3 opened, N5 reopened, `len(keys)` and N2 fileid together, and `--red-cases` still prints 30 × RED and exits 0.

Cheap fix: give each `RED_CASES` entry the rule id it targets, and require that id among the failing rules. The exception handling is as the brief says: `KeyError`/`StopIteration`/`IndexError`/`TypeError` count as a failure of the self-test (`:654-657`). Any other exception type escapes as a traceback, which is also not green.

---

## 6. What the tool restores: COUNTEREXAMPLE

**A. A failed first read deletes the owner's language, and the report says restored (demonstrated).**
- `user_setting()` returns `None` whenever `occ` exits non-zero (`check_m3_new_document.py:137-139`).
- `occ user:setting` exits 1 for a key that is not set (`nextcloud/core/Command/User/Setting.php:150-153`, `213-216`), and also for any ddev or container failure. "Unset" and "failed" are therefore the same value.
- If the read at `:767` fails transiently (for example a ddev hiccup, or another runner holding the container), `original = {lang: None, …}`. The arms run normally. The `finally` (`:802-805`) "restores" `lang` with `--delete`, the readback `None` equals the failed read, and `ok: true`.
- The owner's `zh_TW` is gone. The report exists and reads `WORKS` (`report/q6-lang-deleted.json`). The only trace is `adminSettingsBefore.lang: null`, which a reader cannot tell apart from an owner who never set a language.
- Fix: read with `--default-value=<sentinel>` (exit 0 when unset), or treat any exit other than "does not exist" as an abort *before* switching.

**B. Two instances of this tool.**
- `preflight()` drops every process line that contains `check_m3_new_document` (`:278`), so a second instance is never seen. The docstring's "Never run two M3 runners at once" has no guard for the tool itself.
- Instance B starts while A is in the EN arm and reads `en`/`en_US` as "original". A restores `zh_TW`/unset. B finishes later and restores `en`/`en_US`. B's report exists with `settingsRestored.ok: true`, and the owner is left in English with a US locale.
- B's arms would also run under A's settings, so B's verdict is likely red overall. But `ok: true` is wrong on its own terms.
- Related: `preflight` runs **after** the arm's settings are switched (`:786-790`), so while this tool waits for another runner (`sleep 150` loop), that runner's admin session runs in the switched language.

**SHOULD (no report, or not a settings path):**
- **SIGTERM** (a chain abort or timeout of a detached overnight run) does not run `finally`. The owner is left `en`/`en_US` with no report.
- **KeyboardInterrupt** restores the settings, but the report is never written, including the record that the settings were switched. A second Ctrl-C during the 300 s `occ` in `finally` leaves `locale` unrestored.
- A `TimeoutExpired` from the `lang` restore skips the `locale` restore.
- `run_readonly` creates user `lcprobe` and a share of admin's folder, and its teardown (`:456-457`) is not in a `finally`. An exception from `other.props`/`admin.call` leaves both behind.
- `--red-corrupt` renames `blank/MANIFEST.json` and restores it in `finally` (`:699-701`). SIGTERM in that window leaves the owner's "New document" answering 403.
- Fix for the first two: a SIGTERM handler that raises `SystemExit`, and a "switched" marker written to disk before the first switch and cleared after the restore, so a later run can repair a killed one.

Not a defect: a dead browser or any `Exception` inside `run_once` is recorded as `fatal`, the settings are restored, the report is written, and it is red.
