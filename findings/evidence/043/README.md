# Finding 043: duplicate search and component check

**Date** 2026-08-15. Raw results:
[`duplicate-search-2026-08-15.json`](duplicate-search-2026-08-15.json).

Method: the Bugzilla REST API (`/rest/bug?quicksearch=…`). The HTML search is
behind Anubis and cannot be fetched non-interactively; the REST endpoint is not.

## Result: no duplicate

The seven queries the draft listed, run verbatim:

| # | quicksearch | hits |
|---|---|---|
| 1 | `summary:SelectText` | 0 |
| 2 | `summary:SttSelect` | 0 |
| 3 | `summary:setTextSelection` | 0 |
| 4 | `summary:FN_SELECT_PARA` | 0 |
| 5 | `ALL content:m_bInSelect` | 0 |
| 6 | `ALL content:SttSelect` | 4 |
| 7 | `summary:tiledrendering summary:selection` | 0 |

Query 6's four hits, all `LibreOffice/Writer`, all already fixed, none about
LOK selection:

- **39015** RESOLVED/FIXED — Hard to select a hyperlink; instead it enters
  drag-and-drop mode
- **43390** RESOLVED/FIXED — Cannot cancel selections in Writer using at-spi
- **129809** VERIFIED/FIXED — crash while moving one letter with hyperlink
  (gtk3/kf5)
- **137542** CLOSED/FIXED — SIGSEGV on tab cycling focus to input field in a
  table cell

## The zeros are real zeros: five positive controls

A duplicate search that returns nothing and a duplicate search whose syntax is
wrong look identical from the outside, so the zeros are only worth anything
next to a query that had to return something.

| control | quicksearch | hits | what it shows |
|---|---|---|---|
| C2 | `summary:selection` | 200 (limit) | `summary:` works |
| C3 | `ALL content:setTextSelection` | 1 | `ALL content:` works, and reaches text no `summary:` query would |
| C1 | `summary:tiledrendering` | 0 | a genuine zero: no summary carries the directory name |
| C4 | `ALL content:FN_SELECT_PARA` | 0 | genuine zero |
| C5 | `summary:SelectAll` | 0 | genuine zero |

C3's single hit was read rather than counted: **94601**, `LibreOffice
Online/Writer`, NEW, opened 2015-09-29, "LOOL UX: Resizing of tables / changing
columns". Not related.

C3 also shows query 3 was too narrow on its own — `summary:setTextSelection`
misses a bug that mentions the call in its text. The `ALL content:` form is the
one that carries the search, and it was run for the two identifiers that matter
(`m_bInSelect`, `SttSelect`).

## Component: `LibreOffice` / `Writer`

The defect is in `sw/uibase/wrtsh/select.cxx` and `sw/uibase/shells/textsh1.cxx`,
reached through the LOK interface in `sw/uibase/uno`. LibreOffice's Bugzilla has
no `sw` subcomponent, and the convention for Writer-side LOK defects is the
`Writer` component of the `LibreOffice` product: of 100 bugs matching
`ALL product:LibreOffice content:LOK content:Writer`, 41 are `LibreOffice/Writer`
— the largest single bucket, and the rest are other applications or
non-application components.

`Writer` is therefore confirmed, not assumed.

## Still open before this can be sent

- Reproduce on a **pristine tree**. The native build carries five local
  modifications; each was inspected and none is under `sw/`, but inspected is
  not reproduced. Needs a full rebuild.
- Compile and run the cppunit test in the draft and **show it red** before the
  fix. Needs a `sw` rebuild.
- Decide whether to send a patch alongside.
- **Sending is the user's call.**
