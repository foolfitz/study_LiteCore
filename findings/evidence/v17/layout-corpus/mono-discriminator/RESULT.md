# H-mono discriminator: result

Run 2026-10-08 (+08:00) per `PREDICTION.md` (committed `a4d79443` before the run): `run.py`, output `summary.txt`, `measure-e2-editor-v17.json`, `measure-e2-editor-v17-cjk-r5-ab.json`.

| variant | v17 band 10 top | control band 10 top | max top difference |
|---|---|---|---|
| A (the fixture) | 206 | 209 | 4 px |
| B (that paragraph's Asian font = Noto Sans CJK TC) | 206 | 209 | 4 px |
| C (that paragraph's Asian font = Liberation Mono) | 206 | 209 | 4 px |

- Positive control: HIT. A reproduces the counted run (27 bands both arms, the shift from band 10).
- **H-mono FAILS.** Naming either font in the `Preformatted Text` paragraph's Asian slot changes nothing in either arm; all three variants give identical bands. The paragraph's Asian slot is not the cause.
- Limit of this reading: nothing here proves the variant's style took effect in the engine (a slot that does not matter and a style that was not applied give the same bands). The conclusion "the slot is not the cause" holds only if the automatic style applied; that was not checked.

Next, per the prediction: look at what the engine's fontconfig is asked for that paragraph in each arm, before writing any other explanation.
