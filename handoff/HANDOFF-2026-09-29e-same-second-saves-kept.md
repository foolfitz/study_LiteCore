# Handoff, 2026-09-29e — `SAME-SECOND SAVES KEPT`; ruling D done, stopped at condition 10

Entry points: this file, `findings/evidence/m3-same-second/README.md` (condition 1, the fix, the
counted verdict, condition 7, condition 4), `findings/evidence/m3-same-second/ruling-2026-09-29-fable-d.md`,
`specs/SPEC-M3-versions.md` §4 R2/R3 and §6.

Picks up from `handoff/HANDOFF-2026-09-29d-same-second-measured.md` (condition 1 done). The owner
started this session with "展開後續工作" on that handoff; fable's ruling D was already in force, so
no new decision was sent to fable. Everything below is the ruling's conditions 2–10 carried out.

## Status

**`SAME-SECOND SAVES KEPT`** — counted run `findings/evidence/m3-same-second/runs/2026-09-29T035833+0000.json`:
R2 `same-second` Chrome 3/3, Firefox 3/3; R3 `same-second-foreign` Chrome 3/3, Firefox 3/3; host
`litecore` `695d9ad` (0.2.2) clean; page `fbfb59a4…`; 70 red cases all red.

- **Host 0.2.2** (only `js/litecore-editor.js` and `appinfo/info.xml`): a PUT to the file waits
  until 1.1 s after the host's previous PUT was answered; before every PUT (after the wait) the
  file is read back and the same version with other bytes goes to a conflict copy (finding 103's
  half B, admitted: read-back GET median 24 ms vs PUT 46 ms). A read-back body that breaks off
  decides nothing — the PUT does.
- **Red before the fix**: on 0.2.1 through the real page, R2 was red in every run on (a) same
  ETag, (b) lost first saves, (c) and the 104 cell itself (the later save gone after a restore);
  R3 was red in every run (S2 overwrote the same-second foreign write with a 204). Findings 103
  and 104 are therefore reproduced end to end through the product, not only over raw HTTP.
- **Condition 7**: `LOCKS LAND` (22 cells, 52/52, red 87), `VERSIONS CORRECT` (red 68),
  `ASSETS DELIVERED` (red 84), `HOST_ENTRY LANDS` (red 23) — all on 0.2.2, no expectation
  amended; the only change was `check_m3_versions.HOST_COMMIT`, written down as a binding first.
- **Condition 4**: held Ctrl+S is still 30 PUTs per 1-s hold, now ~35 s long, every save kept →
  **finding 106** (page, `event.repeat` unfiltered). Nothing added to the host.
- **Condition 8**: `litecore-0.2.2.tar.gz` `39dd48e3…` recorded in `m3-install/release-0.2.2.json`;
  `release.json` stays the 0.2.1 record (litecoreprobe still runs 0.2.1). No install window.
- **Condition 9**: fable's WHY and the outcome are in the 「裁決」 sections of findings 103 and 104.
- An opus read-only review ran before counting (`review-2026-09-29-opus.md`, 13 items, disposition
  table at its end). It found two blocking issues: the read-back could throw with no way out, and
  the R1 `HOST_COMMIT` pin was not written down before the run. It also found the R3 gap (R3 did
  not show that the read-back, not If-Match, stopped the save) and 11 uncovered sub-clauses. All
  were fixed before counting.

## State

- `study_LiteCore`: `main`, clean after this handoff's commit, not pushed (no `origin`; `github`
  remote far behind, pre-existing).
- `~/Projects/Nextcloud_Apps/litecore`: `695d9ad` (0.2.2), clean, not pushed; the dev instance
  has run `occ upgrade` to 0.2.2.
- `litecoreprobe`: still `litecore` 0.2.1 from the 0.2.1 archive; its `INSTALLS ELSEWHERE`
  baseline is unchanged (still only valid within the current web-container lifetime).

## What is open — the owner's choice (condition 10: stop here)

From `HANDOFF-2026-09-29c`: **A** distribution channel, **C** page read-only mode + the "clean"
semantic, **F** finding 105's Firefox repro, **G** zstd/brotli, **H** fresh instance. New this round:

- **I. Finding 106 (page)**: `if (event.repeat) return;` on Ctrl+S (still `preventDefault`), or
  coalesce queued saves. Either changes the page's sha256 → every counted verdict bound to
  `fbfb59a4…` must be re-run; same class as C, so doing them together is cheaper.
- **J. An install window for 0.2.2** on litecoreprobe (`INSTALLS ELSEWHERE` is a 0.2.1 fact).
  Would need `release.json` switched to the 0.2.2 record and a reinstall from the 0.2.2 archive.

Registered, not done:

- **Residual 103 windows** (source reading, unmeasured): the first save's read-back landing in the
  same second as the file's last write before open; a foreign writer that stamps its own mtime
  (`X-OC-Mtime`) equal to the host's version second; restoring the "current" row.
- **The read-back's failure path is exercised by no net** (no runner can break a body mid-way).
- **Read-back cost on large documents is unmeasured** (admitted on a 9.5 KB fixture only; it
  downloads the whole document before every save).
- **Timer coarsening** (Firefox `resistFingerprinting`) is the reason for 1.1 s rather than 1.0 s;
  the coarsening itself was not measured.

## Things this round taught (for the next agent)

- **"About half" was a phase, not a probability.** The condition-1 probe pressed every 3.01 s, so
  the phase drifted ~13 ms per pair and the same-ETag pairs were one contiguous block. Look at the
  time series before modelling a rate; a controlled phase then made every 0.2.1 run red.
- **Commit criteria alone, before the runner.** R2's criteria (`b498d213`) are provably first. R3
  and a later paragraph went in with the runner and two shakedowns (`2e473813`), so their
  precedence is only the author's account (spec §6 says so).
- **Red cases on an already-red base prove little**: a mutation can "add a line" by changing a
  message's text. The harness now prefers a clean base; cite the synthetic cases on clean reports
  and use the unfixed runs themselves as the product-level red.
- **Ablate each sub-clause and look for a GREEN case** — that found 11 clauses with no red case
  that the red-case list looked like it covered.
- **After a restore that follows a same-second pair, that version row's `Content-Length` is off by
  one byte** (both directions seen): Python's `http.client` raises `IncompleteRead`. The R2 runner
  records it as `GET incomplete`; R1 never met it because it never writes twice in a second.
- `build_m3_release.py` rewrites `findings/evidence/m3-install/release.json` in place, and the
  install-elsewhere runners bind litecoreprobe to that file — keep the installed version's record.

## Standing rules (unchanged)

- Don't start or restart other ddev projects during a counted run; every M3 runner clears the
  whole `oc_files_lock` table, so never run two at once.
- Counted runners refuse an uncommitted host tree; a host JS change needs an `info.xml` bump and
  `ddev occ upgrade`.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/`, findings'
  prose are zh-TW.
