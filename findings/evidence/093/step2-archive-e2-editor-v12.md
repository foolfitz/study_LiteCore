# Finding 093, option B, step 2 — `e2-editor-v12` archived

Written 2026-09-08, executing `handoff/RUNBOOK-operator-093-engine-geometry.md`
§5 step 2. This profile had never been archived (the runbook's §4(b) names
this as an existing gap that option B would turn into a loss if left
unaddressed). Archived now, before option B's step 4 relink mints
`e2-editor-v13` and before its step 3 source changes touch the same
`Makefile` recipe that links `e2-editor-v12`.

## Where

```
wasm_sdk_probe/build/archive/e2-editor-v12-4ec1e389-worker-03f5b69a-manifest-27342293/
```

The three hash segments were derived, not guessed, by running `sha256sum` on
the live files in `dist/profiles/e2-editor-v12/` before naming the directory:
`probe.wasm` → `4ec1e389…`, `sdk-worker.js` → `03f5b69a…`,
`sdk-manifest.json` → `27342293…` (first 8 hex each, matching this tree's
existing convention — every directory under `build/archive/` uses 8, not the
16 shown in the runbook's `<wasm16>` placeholder, which names a role, not a
length).

## What is in it

Ten files copied (`cp -p`, never moved) from `dist/profiles/e2-editor-v12/`,
totalling 244,222,612 bytes (~233 MiB):

| file | bytes |
|---|---|
| `probe.js` | 144,547 |
| `probe.wasm` | 135,232,655 |
| `sdk-worker.js` | 64,752 |
| `sdk-manifest.json` | 8,092 |
| `base-e2-editor-v12.9901e9be29c9ded2.data` | 39,940,977 |
| `base-e2-editor-v12.b1e48f2b7ac50b60.metadata` | 218,954 |
| `cjk-e2-editor-v12.b76b0433203017ca.data` | 19,484,784 |
| `cjk-e2-editor-v12.fafab99558ab6f8b.metadata` | 263 |
| `fallback-fonts-e2-editor-v12.33856e2a082148dd.data` | 49,102,042 |
| `fallback-fonts-e2-editor-v12.924fb0ed8b459946.metadata` | 15,665 |

Plus `ATTRIBUTION.md` and `SHA256SUMS`, written in the archive directory
itself. No `SHA256SUMS.shared`: unlike v8/v9/v10, v12's manifest
(`artifactFiles`, `resourcePacks`) references none of the shared
`dist/profiles/resources/` files — grepped for `resources/` in
`sdk-manifest.json`, zero matches — so there is nothing to pin by reference.

## Verification

Re-read the copies after writing (not trusted from the `cp` exit status):

```
$ cd wasm_sdk_probe && sha256sum -c build/archive/e2-editor-v12-4ec1e389-worker-03f5b69a-manifest-27342293/SHA256SUMS
(all ten: OK)
```

Also cross-checked as an order-independent set against a fresh `sha256sum` of
the ten source files still in `dist/profiles/e2-editor-v12/`: identical
hash set both ways.

## The candidate page's hash

`ATTRIBUTION.md` records the sha256 of the candidate cutover page —
`9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c` — as a
reference, not a copy (it is a git blob, already permanent). Traced to commit
`000a57e2` ("T1c 落地：… 殼層完成 e2-editor-v8 → v12 的 cutover",
2026-09-07 01:31:32 +0800):

```
$ git show 000a57e2:wasm_sdk_probe/web/e2-editor-app.js | sha256sum
9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c  -
```

matching `wasm_sdk_probe/e2/editor-shell-v2-bundle-v47.json`'s
`web/e2-editor-app.js` entry. The very next commit, `2d319677`, reverted the
page back to pinning v8 ("修正過早的 cutover"), so the working tree's
`wasm_sdk_probe/web/e2-editor-app.js` today hashes to a different value
(`df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143`) —
verified directly, not assumed, so the two are not confused with each other.

## Disk space

| | bytes | approx |
|---|---|---|
| Available before copy | ~70,066,387,604 | ~65.3 GiB |
| Available after copy | 69,822,164,992 | ~65.0 GiB |
| Filesystem | `/dev/nvme0n1p2`, 93% used both before and after at `df -h` resolution | |

("Before" is reconstructed as after-copy plus the copy's exact byte count,
since the pre-copy `df -h` reading only had 1-GiB resolution and showed the
same `66G`/`93%` both times.) 66 GiB free was ample headroom for a 233 MiB
copy; the disk was never at risk of filling.

## Git tracking

Nothing under `wasm_sdk_probe/build/archive/` is tracked, including this new
directory. `.gitignore`'s `/wasm_sdk_probe/*` rule allowlists only specific
top-level subdirectories of `wasm_sdk_probe/` (`assets`, `sdk`, `src`, `web`,
`tools`, etc.) and none of them is `build`, so `ATTRIBUTION.md` and
`SHA256SUMS` are ignored here exactly as they are in the `e2-editor-v8`
precedent — confirmed with `git check-ignore -v` on both. This document is
the tracked record of what the archive contains; the archive itself is not
in git, matching every existing archive in `build/archive/`.

## Interpreting the precedent

The task naming this archive after the v8 precedent
(`e2-editor-v8-4a2710bb-worker-070229cd-manifest-d70481cb`) asked for a
`SHA256SUMS.shared` "if the precedent has one". It does, but for a reason
that does not transfer: v8/v9/v10 reference the shared
`dist/profiles/resources/` directory (34 profiles do), so pinning those six
files by reference avoids duplicating ~98 MiB per archive. v12 carries its
own data packs and references none of `resources/`, so there is nothing
shared to pin — this is not an omission, it is the correct instantiation of
the same reasoning against a different premise.

## Not addressed here

This step archives bytes; it draws no conclusion about whether v12 is a good
option-B candidate or about the geometry question in the runbook's §2 —
that is step 1 (`findings/evidence/093/step1-native-geometry/`) and step 3.
