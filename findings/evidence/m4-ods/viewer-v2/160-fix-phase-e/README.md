# Phase E on ods-viewer-v2 `aa576ce7` (the 160-fix link), 2026-10-22

`chain.sh` (11:27-11:58 CST, `chain.txt`), mirror only, every Chrome under `--password-store=basic`.

| run | result |
| --- | --- |
| `targeted/` (ladder, fdo67682-2, 159's two, the five control files, tdf138507, the ODT control) | E1, E2, E3, E4a, E5, E6, V2-157, V2-160 all PASS; the five control files refused `FORM_CONTROLS_UNSUPPORTED` (158-A); tdf138507 opens; 50 reads, 0 unconfirmed |
| `e6/` (record-only, SPEC-M4 addendum 12) | B = 0 (one-cell-a1 x5 equal; the other two too); boots and reopen shape PASS on all three; reopen series recorded (flat shape this run) |
| `full-corpus/` x3 | E1, E2, E4a, E5, E6, V2-157, **V2-160 PASS in all three (0, 0, 0 unconfirmed of 464)**; E3 red only on `user-defined-function.ods` (`L-no-basic-udf`) in each; confirmed waits at most 107 ms |
| `full-corpus/v2-160-d.jsonl` | **V2-160-D PASS in all three.** LOK's failed-dispatch lines 1, 0, 5, each matched by the engine's own line, each read then confirmed, none `never dispatched` |

The six redispatched reads (all part 0): `tdf103092_RotatedImage`, `tdf115655_HideDetail`, `tdf125938_anchor_after_copy_paste`, `tdf139258_rotated_image`, `tdf160329_sortWithHiddenRows`, `tdf167450_source`; each confirmed after one 50 ms pause, waits 67-97 ms. Four of the six are the files that failed before (v1 10-20: tdf139258, tdf160329; e96e01ec: tdf115655, tdf125938) -- the failure prefers some files [observed], it is not uniformly random.

Reading (SPEC-M4-viewer-v2 §8.3, the first one): **160 is fixed** -- the redispatch was exercised (6 times) and worked every time. The judge's red cases: `judge-v2-160-d-selftest.txt` (9/9) and `judge-v2-160-d-red-on-e96e01ec.jsonl` (red on exactly e96e01ec's three failed-dispatch files).

Not run here: E4b and E9 -- their runner drives the product page (`web/ods-viewer.html`), which names `ods-viewer-v1` and is deliberately not retargeted; they run once the page names v2 (the next package).
