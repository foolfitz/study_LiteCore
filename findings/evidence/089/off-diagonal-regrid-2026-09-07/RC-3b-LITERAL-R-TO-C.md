# RC-3b — the literal R→C red case, built on the inputs that produced R

Added by the main session on 2026-09-07, after the executor's `RESULT.md`
recorded that RC-3 as written could not be built: no single banked 2026-09-06
Row-A report satisfies §4.5's own RC-1 gate on its own, so the transition it
demonstrated was `void → C`, not `R → C`.

That gap matters. This tree's rule is that a red case which was already red
before the change proves nothing (AGENTS.md §6; it is what demoted gate term 6
for half a day on 2026-09-07). The same argument applies one step over: a red
case reduced from a *different* input set than the green one does not show that
**this** green can be turned red. The declaration that outcome R restores the
`Index >= 35 AND Index2 >= 36` sentence rests on `reduce.py` answering `R` on
this directory's six reports, so the red case has to be built from those six.

## What was done

The six reports and `identity.json` were copied to a scratch directory —
nothing in this directory was modified — and point **A3**
(`tdf149752-index30-index236.ods`, banked as opening in 1,223 ms) had its
`opened` object set to `null` in **all three** Shape-A repeats. One repeat
alone would be a SPLIT (outcome S) rather than a contradiction; C1 requires
the point to fail unanimously.

```python
import json
for f in ("A-1-report.json", "A-2-report.json", "A-3-report.json"):
    d = json.load(open(f))
    for c in d["page"]["cases"]:
        if "index30-index236" in c["name"]:
            c["opened"] = None
    json.dump(d, open(f, "w"))
```

Then, unmodified and with no other change:

```
python3 reduce.py --identity identity.json --reports-dir . --out flipped-verdict.json
```

## Result — red

```
outcome:  C
trigger:  C (C1) -- point(s) ['A3'] CONTRADICTED their banked verdict
          unanimously across their repeats
```

Banked here as `redcase-RC-3b-literal-R-to-C.json`. The verdict this directory
actually stands on is `regrid-verdict.json` (`outcome: R`), produced from the
six reports as measured; the flipped reports are not banked, because the
transformation above re-derives them exactly from the files that are.

`identity.json` pins the twenty §2.5 **fixture** files, not the reports, which
is why flipping a report's `opened` reaches the outcome logic instead of being
short-circuited into `void` by the identity clause — RC-4 covers that path
separately, and did go red on it.
