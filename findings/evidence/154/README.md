# Finding 154: the closed Markdown dialog is displayed on the host

Diagnostic, not evidence for any criterion. `diag_markdown_dialog_on_host.py` opens one long60 copy on host 0.2.25 through the D2 host arm's route, reads the dialog's computed style, the rules that set its `display`, the entry button, and the element at the D2 arm's first-line point, clicks there, and then repeats all of it after adding one rule, `#markdown-dialog:not([open]) { display: none }`.

| file | what |
|---|---|
| `diag-154-chrome-20261017T170402.json`, `diag-154-firefox-20261017T170449.json` | the two runs (host 0.2.25, page `605cf24b…`) |
| `as-shipped-chrome.png`, `with-rule-chrome.png` | Chrome screenshots before and after the added rule |

| read | as shipped | with the added rule |
|---|---|---|
| dialog `open` / computed `display` | false / **block** (absolute, box 8,50 640×335 in Chrome; 640×330 in Firefox) | false / none |
| rule setting `display` | `css/server.css`: `article, aside, dialog, figure, footer, header, hgroup, nav, section` | that one, then the added rule |
| element at (620.5, 295.3) | `TEXTAREA#markdown-text`, inside the dialog | `CANVAS#canvas` |
| real click there | no `editorPlaceCaretV2` | `editorPlaceCaretV2`, label 「定位游標」 |
| entry button | `hidden`, `display: none` | same |

Both browsers read the same. (The `:scope` rule in `rulesSettingDisplay` is an artifact of `Element.matches(':scope')`, which outside a scope matches the element itself.)
