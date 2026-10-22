# E6's reopen tail on e96e01ec: repeated runs (diagnostic, 2026-10-22)

Forced by the first counted E6 run on `ods-viewer-v2` `e96e01ec` (`../e6-leak/report-2026-10-22T021502Z.json`, `--bound 0`): `one-cell-a1.ods`'s reopen series was `236,523,520 -> 246,259,712 -> 246,288,384 -> 246,296,576 -> 246,304,768`, tail steps +8,192 and +8,192 > B = 0, **FAIL**. The run just before it on the same identity (`report-2026-10-22T021348Z.json`, B measured) and both v1 runs (10-20) had `... -> 246,259,712 -> 250,454,016 -> 250,454,016 -> 250,454,016`: a 4,194,304-byte step (one 1024x1024 RGBA tile) and then flat.

That counted run stands as it is. These runs are diagnostic and count for nothing: five on v2 and five on v1, same tool (`run_ods_viewer_e6_leak.py --bound 0`), same entries, alternating profiles.

Readings, written before the runs:

- **Tail growth on v1 too** (in any of its five): the shape is not v2's; it is the allocator placing cycle 2's tile buffer either at the top (4 MiB step, then whatever happens below is hidden under the slack) or in a freed hole (small steps visible). The 8 KB per cycle would then be on both and unclassified (a small per-reopen leak, or allocator drift); E6's leak half is red on v2 by its own rule and the same rule would be red on v1 in such a run. Stop and hand to the owner with the counts.
- **Tail growth on v2 only** (v1 five times flat): v2-specific. Candidates: the engine's v2 code (157's part-info, 160's wait) or the rebuilt core (159's bridge, five sw objects). Stop and hand to the owner with the counts.
- **No tail growth anywhere in the ten**: the counted FAIL is a rare event; report the frequency (1 in 12 on v2 counting all) and hand to the owner. No criterion changes in any case.

## Result (10:17-10:23 CST; `runs.txt`, every run exit 0)

Reopen steps of `one-cell-a1.ods` (Delta_1..Delta_4, bytes of `open.begin`):

| run | v2 `e96e01ec` | v1 `f6ab3cdb` |
| --- | --- | --- |
| 1 | `021636Z` 9,736,192 / 4,194,304 / 0 / 0 | `021716Z` 9,736,192 / **28,672 / 8,192 / 8,192** |
| 2 | `021754Z` 9,736,192 / **28,672 / 8,192 / 8,192** | `021834Z` 9,736,192 / 4,194,304 / 0 / 0 |
| 3 | `021912Z` 9,736,192 / 4,194,304 / 0 / 0 | `021950Z` 9,736,192 / **28,672 / 8,192 / 4,190,208** |
| 4 | `022028Z` 9,736,192 / 4,194,304 / 0 / 0 | `022108Z` 9,736,192 / 4,194,304 / 0 / 0 |
| 5 | `022148Z` 9,736,192 / **32,768 / 8,192 / 4,186,112** | `022227Z` 9,736,192 / 4,194,304 / 0 / 0 |

`three-sheets-distinct.ods` and `numeric-100k.ods`: tail 0 / 0 in all ten.

All runs on each identity, the counted one and the B run included: v2 **3 of 7** with a rising tail on `one-cell-a1` (`021502Z` counted, `021754Z`, `022148Z`), v1 **2 of 7** (`021716Z`, `021950Z`; both 10-20 runs flat). The other two entries: 0 of 14.

Reading, as written above: **tail growth on v1 too, the shape is not v2's.** In every rising run cycle 2's tile buffer (4,194,304 bytes) did not raise the break -- it landed in a freed hole -- and the steps that follow are visible (+8,192 per cycle); in two runs the 4 MiB step comes at the last cycle instead. Whether the 8 KB per cycle is live growth or allocator drift cannot be told from the break (`sbrk` is a high-water mark, not live bytes). E6's leak half (SPEC-M4 A7.1: from cycle 3 the series no longer rises) is red by its own rule on v2 3 of 7 and would be on v1 2 of 7; v1's PASS (10-20, one counted run) was one run. Stopped; handed to the owner.
