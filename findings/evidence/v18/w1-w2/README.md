# v18: W1 (the pack) and W2 (identity), spec SPEC-M3-paragraph-merge section 28.4

Run 2026-10-08 (+08:00). Tool `wasm_sdk_probe/tools/build_cjk_subset_mono_pack.py` (new; the e5 tool and the subset tool are not edited).

## W1: HIT

- `self-test.txt`, the red cases. On the unaltered collection, 0 problems. With one Sans face's `OS/2` altered, exactly that is reported (face 0, `OS/2`). With one Mono face's name record altered, exactly that is reported (face 6, "name records differ from the full TTC's own Noto Sans Mono CJK KR"). `SELF-TEST PASS`.
- `build.txt`, then `check.txt` (`--check`: two builds in scratch directories, byte-identical).
  - Verified: the five Sans faces are table-for-table e5's (`head` too, apart from `checkSumAdjustment`).
  - The five Mono faces are table-for-table the Mono subset's, and their name records equal the full TTC's own Mono faces for each region.
  - The Mono subset passes the subset tool's `verify` against face 8 (cmap, hmtx/vmtx, every outline).
  - The rebuilt e5 collection is first required to be byte-identical to the shipped `cjk-sub-e5`.
- Size: pack data 14,384,632 bytes raw. zstd -19 is 5,748,639 against e5's 5,604,052, **+144,587**, within the criterion's +300,000. It is within 143 bytes zstd (and 224 bytes raw) of M1's E5+M5 (`../../v17/mono-reach/mono-cost.json`). The difference was measured by counting the table blobs in both collections. M1's collection stores 6 `head` blobs: the five Sans faces each got their own, because M1 re-loaded them without `recalcTimestamp=False`. This pack stores 2: one shared by the five Sans faces and one shared by the five Mono faces. 4 × 56 bytes = 224.

## W2: HIT

- `manifest-diff.txt`: `sdk/v18-writer-review-manifest.json` differs from v17's only in the CJK pack entry.
- `profile-manifest-diff.txt`: the built profile manifest differs from v17's in that entry and in the identity fields `profile` and `sdkVersion`, which a new name changes by construction.
- `profile-files.txt`: `probe.js`, `probe.wasm` and `sdk-worker.js` are byte-identical to v17's (`46b2f40a…`, `ad3f68bb…`, `00882139…`). The file list is the same.
- `make.txt`: the make run. It was packaged from v15's archive, with no link, and `make -n` showed only v18's recipe. `other-manifests-after.txt`: the v8, v16, v17 and control manifests are unchanged (`d70481cb…`, `99cf5f13…`, `1e7de91f…`, `584ba6b8…`, the values the 10-08 handoff records).
- v18 manifest sha256 `456e9a72…` (`v18-manifest.sha256`). Archived at `wasm_sdk_probe/build/archive/e2-editor-v18-ad3f68bb-worker-00882139-cjk-e10-06976180/` (not in git; `SHA256SUMS` and `ATTRIBUTION.md` there).

## Addendum, 2026-10-08 after the W4/W6 chain: opus review item 5 fixed in the tool

Spec §28.5 recorded two gaps. `--check` matched the pack by name only and never compared the bytes on disk. W1's size clause was compared by hand. The fix waited until the chain had ended (`../chain.log` `CHAIN DONE` 09:57:58), because the tool is a prerequisite of the v18 make target the chain used (handoff rule m). It was made then, not as an alternative wording: the review offered either, and only one was done.

- `--check` now also requires two things:
  - the pack's data and metadata on disk have the sha256 of what it just built (`on_disk_problems`);
  - zstd -19 is at most `cjk-sub-e5`'s + 300,000 bytes (`size_problems`, `ZSTD_ALLOWANCE`).
- `--self-test` gained five cases for these two functions (`review5-self-test.txt`, `SELF-TEST PASS`):
  - must be reported: a file on disk with other bytes, a missing file, a size one byte over the allowance;
  - must not be reported: the built bytes, a size exactly at the allowance.
  - The two original red cases are unchanged and still caught.
- End-to-end red case: `review5_check_red.py`, output `review5-check-red.txt`.
  - It runs the tool's own `main()` with `--check` against a temporary copy of the resources in which one bit of the e10 data is flipped.
  - Result: exit 1 with exactly one FAIL, naming the e10 data (`2433867706779ecd` on disk, `06976180177c8bd2` built).
  - This shows `--check` calls the comparison, not only that the function works.
- On the real resources, `--check` prints `ok` with sizes `zstd19` 5,748,639 against `e5Zstd19` 5,604,052 (the same numbers as W1).
- The make, `review5-make.txt`:
  - `make -n` first showed only v18's recipe. That recipe runs `--check` and rebuilds the profile from the committed manifest and v15's archive; it does not rewrite the pack.
  - `make` exit 0.
  - After it, the v18 manifest `456e9a72…`, `probe.js` `46b2f40a…`, `probe.wasm` `ad3f68bb…`, `sdk-worker.js` `00882139…`, data `06976180…` and metadata `4144b2b2…` all equal the archive's `SHA256SUMS`.
  - The v8, v16, v17 and control manifests are unchanged (`d70481cb…`, `99cf5f13…`, `1e7de91f…`, `584ba6b8…`).
  - So the W4/W6 evidence (`../RESULT.md`) is still about these bytes.
