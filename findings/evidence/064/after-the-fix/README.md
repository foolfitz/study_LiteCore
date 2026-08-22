# The shipped runner, after `inline_styles_of()` was fixed (2026-08-22)

`run_e2_c_product_path.py` against the **shipped** `dist/` tree — no mirror, no
patched file, no diagnostic apparatus — on artifact `29ec627b`, shell v25, with
`KNOWN_RED` **empty**.

| | Chrome | Firefox |
|---|---|---|
| `ok` | **true** | **true** |
| `knownRed` | `[]` | `[]` |
| `staleKnownRedDeclarations` | `[]` | `[]` |
| `every-inline-format-reaches-the-document` | **PASS** | **PASS** |
| `clear-format-removes-every-inline-format` | **PASS** | **PASS** |
| `formatting-survives-the-next-paragraph-break` | **PASS** | **PASS** |

The remaining `NOT_ESTABLISHED` results are the ones that abstain on purpose and
say why in their own `notEstablished` text: `notice-action-recovers-the-session`
and `an-aborted-gesture-stops-selecting` on both, plus
`ctrl-x-is-handled-by-the-product` and
`recovery-returns-what-the-product-promised` on Firefox, which has no CDP and
therefore no clipboard grant.

**This is the after-picture.** The before-picture — the same three checks with
two of them red and one abstaining — is in `../../065-retracted/`, and the
reason they were wrong is in `../RESULT-render-between-format-and-typing.md`.

The runner file's sha256 was printed before and after the pair of runs and was
identical (`9005d3d2f9b24f1d…`), because an earlier attempt at this confirmation
ran against a version whose edit had been silently reverted.
