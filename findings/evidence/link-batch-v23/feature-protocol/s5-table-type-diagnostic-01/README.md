# Table selection followed by type: paste differs from the keyboard oracle

## Observed

The first counted S5-02 failure is Chrome `shift-Right@cell-end/type`, after 401 PASS cells. A1 initially contains `A1 cell text`; B1 contains `B1 cell text`. The original public fixture/save is correct. Shift+Right from A1's text end creates the cross-cell selection, then the real typed `x` produces exactly one public `insertText(text='x')`. Its successful terminal explicitly reports **`method: paste`**. The insert request is posted after the successful extension terminal; this is not an insert sent before the ordered move has answered.

| Saved paragraphs | A1 | B1 |
| --- | --- | --- |
| Product counted Chrome | `A1 cell textx` | `B1 cell textx#` |
| Product diagnostic Chrome | `A1 cell textx` | `B1 cell textx#` |
| Product diagnostic Firefox | `A1 cell textx` | `B1 cell textx#` |
| Bound native keyboard reference | empty | `x` |

The fresh diagnostic has one table case and one plain-text type control in each browser. Both plain-text controls PASS; both table cases FAIL under the existing oracle. These are three product table observations sharing one native reference, not three native repetitions. The type cell uses native run-03's `selection-before-x` witness. Astra's A ruling changes only a deletion partition and does not apply here. No criterion or oracle was changed.

`read-diagnostic.py` re-reads the counted first failure and all four fresh diagnostic controls, checks every complete inspection/raw/native-save hash and direct original/native-before paragraph equality, and derives the exact source anchors. All five page configurations have the same frozen config hash. `comparison.json` keeps full paragraph sequences and insert/extension request/response payloads without duplicating binary paint/save buffers.

From the repository root, choose a fresh output name:

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/s5-table-type-diagnostic-01/read-diagnostic.py --output FRESH-OUTPUT.json
```

## Source reading and inference

Current core source HEAD is `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`. `comparison.json` binds each read file and line anchor. These source readings are not a runtime trace of the saved artifact.

- `wasm_sdk_probe/src/probe_engine.cpp::handleInsertText` calls LOK `paste(text/plain;charset=utf-8, data, size)` first, with a postKeyEvent fallback only if paste returns false. The actual public response confirms paste was chosen here.
- `desktop/source/lib/init.cxx::doc_paste` sets the clipboard from the given bytes, then dispatches `.uno:Paste`. `lokclipboard.cxx` constructs an explicit-length UTF-8 `OUString`; this inspected constructor does not ignore the supplied length.
- `sw/source/uibase/dochdl/swdtflvr.cxx::PasteData` explicitly skips deleting selected contents in table mode. `PasteFileContent` obtains an `OUString`, constructs a UTF-16 stream and sets the reader's ASCII options to UCS2 before invoking `SwReader`.
- `sw/source/filter/basflt/shellio.cxx::SwReader::Read` loops over the PaM ring, reusing/rewinding the stream. `sw/source/filter/ascii/parasc.cxx::AsciiReader::Read` resets ASCII options after each read; `SwAsciiOptions::Reset` restores the thread/system charset. `SwASCIIParser::ReadChars` has encoding detection and converts control characters below space into `#`.

**Inference, not established cause:** later PaMs may reread the same UTF-16 `x` stream using the reset charset/detection path; interpreting its NUL as a character can produce `x#`. This is consistent with the second-cell output, but no debugger trace, core patch, direct native-plain-paste comparison or encoding-perturbation experiment has been run. Do not claim a buffer overread, heap contamination, inherited R1 marker or identified responsible layer from these records. The replacement-versus-append difference is already independently visible, regardless of why `#` appears.

Related existing observation: `findings/evidence/link-batch-v21/native/markdown-paste/round-2/README.md` documents native paste over two selected cells appending in each, with differently decoded later-cell source text. That is a different MIME/corpus and is context, not proof that this plain-text WASM mechanism is identical.

## Next bounded task

Choose and verify the product's intended type behavior at a cross-cell selection under the existing native-type requirement. A native direct-paste versus key-input comparison and targeted character/charset controls can separate generic paste semantics from the `#` decoding issue. A product fix may require an engine/core successor build and fresh identity; never overwrite frozen v23. A proposed semantic narrowing instead requires an explicit prospective ruling, not an implicit extension of Astra A. Preserve this failure and the completed R1 result. No new counted S5 run should start until that choice is resolved and its controls/preparation/bindings are ready. The owner requested a Claude handoff at this checkpoint.
