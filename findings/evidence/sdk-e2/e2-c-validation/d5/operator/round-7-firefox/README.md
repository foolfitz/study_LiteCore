# D5, seventh operator round (Firefox, 2026-08-16) — four cells, on one shell, under the strengthened criteria

Preserved exactly as exported, with the operator's own saved document beside it.

## Verdict: PASS — and it is a stronger PASS than round 6's

| cell | status | what carried it |
|---|---|---|
| `d5-pointer-drag-single` | **PASS** | 85 trusted events, revision 0 → 1, `<text:list>` 2 → **3** in the saved ODT |
| `d5-pointer-drag-cross` | **PASS** | 76 trusted events, revision 1 → 2, `<text:list>` 3 → **4** |
| `d5-ime-commit` | **PASS** | 2 trusted `compositionend` (`中文輸入`, `阿卍`), revision 2 → **4** — one per commit — and **both strings are in the saved document** |
| `d5-clipboard` | **PASS** | a trusted `copy` **and** a trusted `paste`, revision 4 → 5 |

**411 events across the four cells, every one of them `isTrusted: true`, zero
synthetic.**

## Why this round exists when round 6 already passed

Two reasons, both about what the evidence is bound to rather than about the
product:

1. **One shell.** Round 6's four cells ran on shell bundle **v6**; findings 051
   and 052 then took the shell to **v8**.  This round runs on v8, attested from
   outside the page by `../session-attestation-2.json`
   (`4daad6b4…` before and after, unchanged), so the cells and the shell they
   are cited for are the same generation.
2. **The strengthened criteria.** Round 6 was judged by round one's rule.  This
   round is judged by `--criteria round-two`, which was written after round 4
   and round 5 showed the judge to be weaker than its own frozen oracle:

   * the drag cells' saved ODT is **read**, not merely captured — the
     `<text:list>` count must rise against the document saved immediately
     before it;
   * the IME cell requires **one revision advance per commit** and **every
     committed string present in the document**, where round one asked only
     whether the revision had moved (and passed round 5, where the product
     silently dropped two of three commits);
   * the clipboard cell requires **both** a copy and a paste, where round one
     accepted either.

Round 6's evidence and verdict are **unchanged**: it was judged honestly under
the rule of its day, and this round does not rewrite it.

## The two caret defects, from the operator's side

Rounds 1–6 were run under a product where **a click landing in the bottom half
of a line never placed the caret** (finding 051) and **a click outside the text
never placed it either** (finding 052) — each costing 30 seconds before failing.
Round 1's opening report was *"the caret cannot be placed, so I can't start"*,
which was read at the time as the product drawing no caret.  It was also
literally true.

This is the first operator round run on a build where both are fixed, and it is
the first one where all four cells were completed without the operator having to
work around a caret that would not land.

## Files

| | |
|---|---|
| `result.json` | the page's own export, byte-for-byte as handed back |
| `operator-saved.odt` | the operator's downloaded document: 9 entries, 4 `<text:list>`, and both IME strings present |
| `verdict.json` | `analyze_e2_c_d5.py --criteria round-two` |
| `../session-attestation-2.json` | what the harness could attest from outside the page |

Re-judge:

```
python3 tools/analyze_e2_c_d5.py --criteria round-two \
  findings/evidence/sdk-e2/e2-c-validation/d5/operator/round-7-firefox
```

## Still not established by this round

* **Chrome.** `compositionend` arrives `isTrusted: false` there (measured, same
  operator, same Fcitx5 Chewing), so the IME cell is not obtainable on Chrome.
  That is a recorded platform limit, not a relaxed criterion.
* **Which paragraph** each drag selected, and whether the IME's second commit
  replaced a selection rather than landing at a collapsed caret: neither is in
  the export, and both are named in the matrix as
  `notEstablishedByTheJudge`.
* **That the pasted text is the text that was copied** — the export records the
  events, not the clipboard.
