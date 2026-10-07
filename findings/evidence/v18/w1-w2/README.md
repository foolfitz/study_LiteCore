# v18: W1 (the pack) and W2 (identity), spec SPEC-M3-paragraph-merge section 28.4

Run 2026-10-08 (+08:00). Tool `wasm_sdk_probe/tools/build_cjk_subset_mono_pack.py` (new; the e5 tool and the subset tool are not edited).

## W1: HIT

- `self-test.txt`, the red cases. On the unaltered collection, 0 problems. With one Sans face's `OS/2` altered, exactly that is reported (face 0, `OS/2`). With one Mono face's name record altered, exactly that is reported (face 6, "name records differ from the full TTC's own Noto Sans Mono CJK KR"). `SELF-TEST PASS`.
- `build.txt`, then `check.txt` (`--check`: two builds in scratch directories, byte-identical).
  - Verified: the five Sans faces are table-for-table e5's (`head` too, apart from `checkSumAdjustment`).
  - The five Mono faces are table-for-table the Mono subset's, and their name records equal the full TTC's own Mono faces for each region.
  - The Mono subset passes the subset tool's `verify` against face 8 (cmap, hmtx/vmtx, every outline).
  - The rebuilt e5 collection is first required to be byte-identical to the shipped `cjk-sub-e5`.
- Size: pack data 14,384,632 bytes raw. zstd -19 is 5,748,639 against e5's 5,604,052, **+144,587**, within the criterion's +300,000. This agrees with M1's +144,730 for the same construction (`../../v17/mono-reach/mono-cost.json`, E5+M5). The 143-byte difference is M1's `head.modified` artefact, recorded there.

## W2: HIT

- `manifest-diff.txt`: `sdk/v18-writer-review-manifest.json` differs from v17's only in the CJK pack entry.
- `profile-manifest-diff.txt`: the built profile manifest differs from v17's in that entry and in the identity fields `profile` and `sdkVersion`, which a new name changes by construction.
- `profile-files.txt`: `probe.js`, `probe.wasm` and `sdk-worker.js` are byte-identical to v17's (`46b2f40a…`, `ad3f68bb…`, `00882139…`). The file list is the same.
- `make.txt`: the make run. It was packaged from v15's archive, with no link, and `make -n` showed only v18's recipe. `other-manifests-after.txt`: the v8, v16, v17 and control manifests are unchanged (`d70481cb…`, `99cf5f13…`, `1e7de91f…`, `584ba6b8…`, the values the 10-08 handoff records).
- v18 manifest sha256 `456e9a72…` (`v18-manifest.sha256`). Archived at `wasm_sdk_probe/build/archive/e2-editor-v18-ad3f68bb-worker-00882139-cjk-e10-06976180/` (not in git; `SHA256SUMS` and `ATTRIBUTION.md` there).
