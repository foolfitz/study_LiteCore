# S-init preparation 02: effective-opacity normalization defect

This uncounted preparation stopped at the first inspected failure. Three Chrome cells completed before the stop: v22 and r2 `direct-load-reopen`, plus v22 `input-teh`. The fourth cell, r2 `input-teh`, was interrupted while the browser constructor was waiting, before page navigation; its record has no page payload. There are **zero counted S-init cells**. The sibling runner log preserves the interruption traceback. A process check after interruption found no remaining Chrome user-data-dir process or HTTP server.

Both completed direct-load cells used actual `insertText` method `paste`, revision1, and preserved `S_INIT_ROUNDTRIP_MARKERLanguage tagged authority paragraph.` through the exact saved-byte fresh-worker reopen. The original semantic reader refused both because the second saved ODT made one effective default explicit: text property `loext:opacity="100%"`. There was no other normalized property/text/structure delta, and no observed v22/r2 difference. The completed v22 input cell used `paste`, revision1, and saved literal `teh `. The interrupted r2 input has no outcome.

## Why the correction is semantic normalization, not erased profile drift

The checked core source establishes the default:

- `editeng/source/items/textitem.cxx:1546`: default `SvxColorItem` uses `COL_BLACK`.
- `include/tools/color.hxx:442`: `COL_BLACK` is the three-channel RGB constructor; that constructor delegates with transparency0 (`color.hxx:96`).
- `textitem.cxx:1591`: `MID_COLOR_ALPHA` reports transparency as `(255-alpha)*100/255`.
- `sw/source/core/unocore/unomap1.cxx:189`: `CharTransparence` uses that color member.
- `xmloff/source/text/txtprmap.cxx:140-141`: `CharTransparence` maps to `loext:opacity` with `XML_TYPE_NEG_PERCENT16`.
- `xmloff/source/style/xmlbahdl.cxx:479`: that handler exports `100-transparency`.

The reader now seeds only the effective paragraph text-opacity default,100%, before applying inherited and explicit properties. Explicit nondefault opacity remains observable and can differ. The focused regression uses the actual first/reopened saved bytes from both profiles: it failed before the correction and passes afterward. Changing explicit opacity to50% remains unequal, so the fix does not discard the property.

`inspection-01.json` is a separate post-correction interpretation of these retained raw records, with the corrected reader hash. It is not a relabelled counted run: the original failure and four written records remain intact, and the old report's source identities are not rewritten. The finite72-cell acceptance is still NOT_ESTABLISHED. A fresh preparation output is required after coordination; no further browser run occurred during this correction.
