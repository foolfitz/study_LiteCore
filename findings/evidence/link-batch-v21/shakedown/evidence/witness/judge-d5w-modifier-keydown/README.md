# Witness (§34.4): the item-1 judge misread D5-w in Firefox (the modifier's keydown)

Committed **before** the judge is changed.

- **Misjudged report:** `../../item1/report-firefox-d5w-xlc-table-d6-20261017T090001.json` (Firefox 157.0.1, session C of the re-run; every round `done`).
- **The judge's output on it:** `judge-item1-before-fix.txt`. It is `judge_v21_shakedown_item1.py --dir …/evidence/item1 --expect-page 605cf24b… --rounds 3` over every final report. Its `D5w firefox NOT_ESTABLISHED` reads "v21 rN ctrl+Home: the v21 positive control was not taken" for all 12 v21 chords.

## The fault

`judge_d5w` takes the chord's **first** `kd` event and its `kdp`:

```python
kd = next((e for e in log if e.get("k") == "kd"), None)
```

- **Chrome** (CDP) sends a chord as one keydown of the key, with the modifier flags set. Its first `kd` is `Home`/`End`.
- **Firefox** (one WebDriver chain) sends the modifier's own keydown first: `Control` or `Meta`, then `Shift` for Shift+Ctrl+Home, then `Home`/`End`. The judge read the `Control`/`Meta` keydown. The page never prevents that keydown, so on v21 every chord read "not taken", which is NE. On v20 and for Shift the "not prevented" half was read off the wrong event too; there it reads PASS vacuously. [observed: the chord logs of both reports]

Read on the chord's own key, the Firefox report shows exactly the clause's shape:
- v20: `Home`/`End` not prevented, 0 `move-document-*` requests;
- v21: prevented, with 1 request each;
- Shift+Ctrl+Home on v21: not prevented, 0 requests.

## The fix (next commit)

`kd` becomes the first keydown whose `key` is the chord's last part (`Home` or `End`). Nothing else in the clause changes. A self-test case with a Firefox-shaped log (the modifier's keydown first) is added. It must read PASS for the taken v21 shape, and FAIL for a prevented `Home` on v20. Tally: modified because of execution +1.
