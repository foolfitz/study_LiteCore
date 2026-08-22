# Operator round two — 2026-08-22

Six ODTs saved by hand through the shipped product page on shell **v26**
(finding 066 already fixed), following
`handoff/RUNBOOK-operator-2026-08-22-round-2.md`.

## Part 1 — the three formats nobody had typed by hand: all correct

Read with the corrected `inline_styles_of()`:

| file | marker | result |
|---|---|---|
| `r2-italic.odt` | `KBITALIC` | `italic: true`, `span T1` |
| `r2-under.odt` | `KBUNDER` | `underline: true`, `span T1` |
| `r2-strike.odt` | `KBSTRIKE` | `strikethrough: true`, `span T1` |

These agree exactly with the automated `keyboard-formats` arm run the same
night, and they agree through the **same** path: a real click on the button and
real typing on the keyboard. Human and machine, same question, same answer.

## Part 2 — the real Enter, and this is sharper than the automated arm

| | |
|---|---|
| `r2-enter-1.odt` | 10 paragraphs, one of them `ENTERBEFORE` |
| `r2-enter-2.odt` | 10 paragraphs, that one now `ENTERBEFOREENTERFATER` |

The Enter added **no paragraph**, and the text typed after it landed
**contiguously in the same paragraph**. The automated arm had compared the two
sides of the key with nothing typed between and got byte-identical
`content.xml`; this adds that the caret did not move either. Finding 067.

(`ENTERFATER` is the operator's typo for `ENTERAFTER`. It changes nothing: the
marker's job is to be findable.)

## Part 3 — the caret: still wrong, and finding 068

`r2-caret.odt` is clean — `<text:p text:style-name="P1">CARETHERE</text:p>` —
which is the point: the **document** is right and the **drawing** is not. The
screenshot is in `../068/`.

## Part 4 — the line break: correct

`r2-linebreak.odt`:

```xml
<text:p text:style-name="P1">CARETHERE<text:line-break/>AFTERBREAK</text:p>
```

The break is there and the text follows it, and the operator reports the caret
moved to the next line on screen too. **This contradicts their 2026-08-21
report** that the caret did not move after a line break. The only change in
between is finding 066's fix; that explanation is plausible and **was not
independently measured**.
