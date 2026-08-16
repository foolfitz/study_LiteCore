# D5, sixth operator round (Firefox, 2026-08-16) — **all four cells PASS**

Preserved exactly as exported, with the operator's own final document beside it.

## Verdict: PASS, four of four

| cell | events | revision | synthetic | saved |
|---|---|---|---|---|
| `d5-pointer-drag-single` | 2 down, 76 moves, 2 up | 0 → 1 | 0 | 12,862 B |
| `d5-pointer-drag-cross` | 2 down, 71 moves, 2 up | 1 → 2 | 0 | 12,843 B |
| `d5-ime-commit` | 2 compositions, 12 updates | 2 → **4** | 0 | 12,931 B |
| `d5-clipboard` | 1 copy, 1 paste | 4 → **5** | 0 | 13,131 B |

397 events, **zero synthetic**, one page load, one person.

## It also meets the strengthened criterion, not only the analyzer's

Round 5 showed the analyzer is weaker than its own frozen oracle: it asks
whether the revision moved, not whether it moved once per commit the oracle
names.  This round was checked both ways:

| | analyzer | strengthened |
|---|---|---|
| IME | PASS | **2 commits → revision +2** ✓ |
| clipboard | PASS | **1 paste → revision +1** ✓ |

And the documents show the effects, which is what "the saved ODT shows it"
asks:

- pristine `list-contexts.odt` has **2** `<text:list>`; after cell 1 → **3**;
  after cell 2 → **4**;
- the IME cell's document carries **both** commits:
  `E1-LC-BULLET-TWO 你好中文項目` and `E1-LC-你好`;
- the clipboard cell's document differs from the previous one by exactly:

```
-E1-LC-NUMBER-TWO
+E1-LC-NUMBER-TWONUMBER-ONE
```

**`NUMBER-ONE` came from the document itself** — copied out of it through the
engine, onto the system clipboard, and back in.  That is the half no headless
run could establish: WebDriver blocks clipboard read and write
(`NotAllowedError`), which is why the wiring shipped this morning could only be
verified as far as "the handler fires and reports typed errors".

## What this round confirms, by hand

- **[Finding 049](../../../../../049-the-product-save-button-writes-fifteen-bytes-of-object-object.md)**:
  four real ODTs, 12.8–13.1 KB.  The same button wrote 15 bytes of
  `[object Object]` this morning.
- **[Finding 050](../../../../../050-every-ime-commit-after-the-first-is-rejected-as-a-buffer-mismatch.md)**:
  **both** IME commits landed.  Before the fix the second one was rejected as a
  buffer mismatch, silently.
- **Ctrl+C**: the product had never asked the engine for its selection; now it
  does, and the round trip completes.

## The identity this is bound to

The cells were driven on **shell bundle v6 (`9b7e7d2a…`)** and artifact
`572035ac…`.  The shell moved four generations during the day (v3 → v6) as
049, 050 and the copy wiring landed, so:

- **these four cells are established on v6**, and
- D3's corpus round, D4 and D5's machine half ran on **v3**.

A phase verdict wants one shell under all of it.  That is what the second round
after the relink is for; this round is the record that the four human cells are
obtainable, on the shipped artifact, with the shell as it stands today.
