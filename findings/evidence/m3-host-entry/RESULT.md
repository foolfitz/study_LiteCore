# M3 host entry — result (2026-09-28)

```
$ python3 wasm_sdk_probe/tools/check_m3_host_entry.py --score findings/evidence/m3-host-entry/runs/2026-09-28T095100Z.json
HOST_ENTRY LANDS chrome:open-save=3/3 chrome:conflict=3/3 chrome:broken=1/1 chrome:broken-no-save=1/1 firefox:open-save=3/3 firefox:conflict=3/3 problems=[]
```

**The product page now has a host entry, and the Nextcloud app opens, saves and keeps a
conflict through it**, in Chrome 151 and Firefox 156. Criteria:
`specs/SPEC-M3-host-entry.md` §4 (H1–H5), with the revisions logged there.

## What landed

| | |
| --- | --- |
| page | `web/e2-editor-app.js` `1ec7baf9…` → `fbfb59a4014995322f210812e3627ff828dbecae351d157305a75701e2d76632`, staged into `dist/` |
| shell generation | **v53** `2e3a2021ab0af4b1…` (frozen today; differs from v52 only in the page; exclusions the same) |
| engine / profile / link | untouched; the page still pins `e2-editor-v8` |
| host | `litecore` app `0dcb745` (`js/litecore-editor.js`) |

The contract: before importing the page, the host sets `globalThis.liteCoreHost = { load, save }`.
The page reads it once. With a host present, the page:
- opens what `load()` returns, and never touches the bundled sample;
- disables the two local pickers;
- hands each save's bytes to `save()` instead of starting a download;
- runs one save at a time, end to end.

A host of the wrong shape is refused. Without a host, nothing changes.

## Measured

| criterion | Chrome 151 | Firefox 156 |
| --- | --- | --- |
| **H1** open from Files, no sample: click path, isolated, the fetched bytes are the file's, `ready` with its name, pickers disabled, no `e1-fixtures/` request (Chrome) | 6/6 (both arms) | 6/6 |
| **H2** save twice (button, then an inserted marker and Ctrl+S): 204, 204. The second `If-Match` is the first save's new version. The server bytes are the second save's. The server file has a Heading 1 paragraph, and its text minus the marker equals the original's, paragraph by paragraph. No conflict copy. | 3/3 | 3/3 |
| **H3** the file is changed on the server before save, then save is pressed twice 5 s apart: 412 both times, and the page shows `存回 失敗` with the CONFLICT reason both times. The view is unchanged after 5 s: same document, same revision, `ready`. The server file is still the intruder's bytes. Two conflict copies exist, holding the two sent byte strings. | 3/3 | 3/3 |
| **H4** no host → unchanged: the product-path net (`product-path/`) on v8 and v14, each 40 PASS / 2 NE, cell for cell equal to v52's (`findings/evidence/098/product-path/v52-*.json`), served page `fbfb59a4…` / its v14 repoint `64f70410…`. `make test-e2-c-static` exit 0 (node 107 + 5, python 108). | ✔ | (Chrome runner) |
| **H5** broken host (`{}`, and `load` without `save`): stops with `HOST_ENTRY_INVALID`, no document, no sample request, pickers disabled, and the page's own document is in the same CDP drain as a positive control | 1/1 + 1/1 | not measurable here (no pre-document script injection in the Firefox driver) |
| click → document opened | 2.51–2.54 s (skeleton: 3.7–4.0) | 3.01–3.08 s (skeleton: 5.1) |

The scoring went red first. On shakedown `094839Z`, 21 mutations each go red on the
criterion they name (`--red-cases`).

## How it got here, including what went wrong

- **First H4 run on the first page draft** (`product-path/superseded/`): also 40/2, cell
  for cell. The page then changed again (save serialization), so the net was re-run on
  the final bytes.
- **H2's first oracle was wrong.** It required `<text:h`. The product's heading action
  writes `<text:p text:style-name="Heading_20_1">`. This tree measured that on
  2026-08-19 and wrote it down in `run_e2_c_product_path.py` (`document_lines`); I did
  not look before drafting. Shakedown `092749Z` was red on it in both browsers while
  the save itself worked. The payload rerun `092945Z` showed the style. The proxy was
  changed and the reason logged in the spec before any counted run.
- **The opus adversarial review, run before any counted run, broke the criteria and the
  host, not the page's no-host path.**
  - The page fix: rapid saves raced two PUTs with the same `If-Match`.
  - The host fixes: never write unconditionally, prefer `OC-ETag`, write a conflict copy
    instead of stranding the edits, send `X-Requested-With`.
  - The runner fixes: a second save that exercises version chaining and Ctrl+S, the 5 s
    wait and second press on conflict, H5's second shape, and a text check against
    "right name, other document".
  - The full list, with the two items not adopted, is in the spec's revision log.
- **Criteria ordering, as evidenced.** The spec was drafted before the page changed.
  Its last revision (09:38Z by mtime) precedes the last shakedown (09:48Z) and the
  counted run (09:51Z), and both ran runner `e39e336f…`. Unlike gate 0, the criteria and
  the runner were **committed together with this result, not before it**, so git alone
  does not show the order.

## Named limits

- **"Clean" is set before the host accepts.** `session.save()` marks the session clean
  before `save()` is called (spec §2, known limit).
- **Refusals other than a conflict strand the edits in the page.** 403 (read-only), 423
  (locked) and a lost network leave the bytes with no way out. This is for the locks and
  permissions step.
- **Conflict copies are one per refused press.** The name carries a second-resolution
  stamp, with `-2`… added on collision.
- **Not exercised:** received shares, public links and other users; a file moved or
  deleted mid-edit (Nextcloud answers If-Match on a missing path with 412, read from
  source by the review, not measured); render failure after a successful PUT (the page
  would say `存回 失敗`).
- **Environment:** Apache only. Admin user.
