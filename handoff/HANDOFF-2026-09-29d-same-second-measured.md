# Handoff, 2026-09-29d — condition 1 measured, conditions 2–10 open

Entry points: this file, `findings/evidence/m3-same-second/ruling-2026-09-29-fable-d.md`,
`findings/evidence/m3-same-second/README.md`, `specs/SPEC-M3-versions.md` §4/§5/§6.

Picks up from `handoff/HANDOFF-2026-09-29c-installs-elsewhere.md`. The owner was away and
authorized fable to decide in their place. After `INSTALLS ELSEWHERE` (09-29c, commit
`71e0ac8e`), the main session asked fable what to do next (STOP included, on the owner's
authority). fable ruled **D**: host-only hardening against finding 104 (data loss), and against
103 only under condition 6 — measure first. The ruling and its WHY (for the owner, zh-TW) are in
the ruling file; quote its condition numbers verbatim, do not paraphrase them.

This handoff exists because the main session's context passed its soft limit. Only condition 1
is done. Nothing else of D has started.

## Status

**Condition 1 — DONE, MET** (commit `b0b21b19`). Through the real page, both browsers, no host
change: Chrome 5/12 and Firefox 6/12 button+Ctrl+S pairs (no wait) landed on the same ETag
(send-to-send gap 140–195 ms); each same-ETag pair cost exactly one version in the history. A
1-second held Ctrl+S sent 30 PUTs every trial (burst 3.7–5.2 s) — already past condition 4's
`> 5` threshold on 0.2.1. Per the ruling, this is to be registered as a finding against the
**page** (`event.repeat` unfiltered) after the host fix lands, not answered with a host
mechanism. Unexplained and registered, not gating: only about half of the ~160 ms-gap pairs
actually shared a second; the fix (≥1 s between the host's own PUTs) does not depend on why.

Full numbers: `findings/evidence/m3-same-second/README.md`.

## State

- `study_LiteCore`: `main` at `b0b21b19`, clean, not pushed (no `origin`; `github` remote far
  behind, pre-existing).
- `~/Projects/Nextcloud_Apps/litecore`: `5e53362` (0.2.1), clean, untouched this session.
- `litecoreprobe` has `litecore` 0.2.1 installed from the release archive (reinstall 3, per
  09-29c). That install baseline holds only within the current web-container lifetime — a
  container restart invalidates it (I4-1b).

## What is next — ordered, following ruling conditions 2–10

1. **Condition 2 — criteria before code.** Revise `specs/SPEC-M3-versions.md` §5 in place:
   strike (`~~ ~~`) the sentence "宿主可以讓兩次存檔至少隔一秒⋯不做，除非擁有者要" and write the
   correction naming fable's ruling. Add a row to §6 (newest row first in that table). Add a new
   arm to §4 — suggested name **R2 `same-second`** — in criterion form 1 or 2 (CLAUDE.md
   "驗收判準的形式"), with an "if never done" default sentence.

   Suggested R2 content, per browser, one editor session, through the real page: ≥10
   button+Ctrl+S pairs with no wait →
   (a) no two consecutive 2xx host saves share an ETag;
   (b) after one more (third) save, every earlier save's bytes (host record sha256) are in the
   version list (the HTTP probe's V2 shape, `findings/evidence/m3-versions/README.md:61` — "the
   first of the two is in no version once a third save lands" — must not occur);
   (c) the finding-104 chain end to end: one more pair, then restore the oldest version (the
   runner sends the Files-tab request: `MOVE` to `versions/admin/restore/target`, no token), then
   the pair's later save's bytes must be in the version list;
   (d) record first- and second-save latencies (host `saves[].at`, `attempts[].at`, and the
   page's "存回 N ms") before/after the fix — registered, not gated.
   Held Ctrl+S: count PUTs and tail seconds, registered (condition 4).

   Every clause needs a red case that is red on 0.2.1 before the fix lands. The measurement
   shows 0.2.1 fails (a) roughly half the time per pair, so ≥10 pairs makes (a) red with near
   certainty — the red case for (a) is **the run on 0.2.1 itself**, not only a synthetic
   mutation; keep synthetic mutations too, in the runner's `--red-cases`.

   Put R2 in `wasm_sdk_probe/tools/check_m3_versions.py` (already the R1 runner). Reuse from
   `probe_m3_same_second_saves.py`: the PAIR/HELD scripts and the `versions()` reader. Note:
   Firefox's `evaluate` wraps scripts as `return <expr>;`, so PAIR is written as one array
   expression for that reason — keep that shape. R1 deletes the file first (fresh fileid, empty
   history); the probe does not (the file keeps its id across resets, ~500 revisions) — R2
   should do the same as R1 (delete first).

2. **Shakedown on 0.2.1**: run R2 unfixed. It must be red — this is the red run the criteria
   require before the fix.

3. **Conditions 3/5 — host change.** Only `js/litecore-editor.js` and `appinfo/info.xml`
   (bump to 0.2.2) change. Ruling's words: "the host sends no PUT to the file until ≥ 1.0 s after
   the previous PUT's response was received (client clock)"; "the wait applies only to a
   second-in-a-row save".
   Suggest recording `respondedAt` on each attempt so spacing is checkable from the host's own
   record. Reminders: the app's JS is served `immutable` with `?v=` = md5 of the app version, so
   the `info.xml` version bump is required, then `ddev occ upgrade`. Counted runners refuse an
   uncommitted host tree — commit in the host repo first. The host repo is under `~/Projects`,
   not `~/OSSII`, so the normal `Co-Authored-By` trailer applies; never a `Claude-Session` line.

4. **Condition 6 — half B (103, compare-before-save)**, only if all its sub-conditions hold
   (GET + sha256 against the host's own last bytes, no server-side mechanism, extra latency ≤ one
   PUT, its own red case per the ruling text). Otherwise register half B as not done, with the
   reason — do not build a server-side mechanism to force it through.

5. Consider an adversarial review (opus, read-only) of the R2 criteria and the host diff before
   counting anything — every earlier review in this project found real problems.

6. **Counted R2** on 0.2.2, both browsers, green; then its `--red-cases`.

7. **Condition 7** — re-run the four existing counted runners on the dev instance against 0.2.2:
   locks (22 cells, 52 runs, ~46 min), versions R1 (3+3), assets (3+3), host entry
   (`check_m3_host_entry.py --label counted`). Verdicts unchanged, red cases all red. A red run
   is a finding, never a test fix. An expectation changes only with a written reason naming the
   prescription that changed (fable's F2 caveat: the nets assert shapes such as one attempt per
   save and the second save chaining on the first's version — a wait or extra GET may need
   amended expectations, only with that reason).

8. **Condition 8** — rebuild the archive for 0.2.2 with `build_m3_release.py` (record only). No
   new `INSTALLS ELSEWHERE` window — that verdict stays a fact about 0.2.1.

9. **Condition 9** — write fable's WHY into the 「裁決」 sections of `findings/103-*.md` and
   `findings/104-*.md` (those finding files are zh-TW). Register the page finding for held
   Ctrl+S (`event.repeat` unfiltered) as a new numbered finding — check `ls findings/ | sort |
   tail` for the next free number (106 as of this handoff; confirm before using it).

10. **Condition 10 — stop; hand back.** Options A (distribution channel), C (page read-only +
    the "clean" semantic), F (finding 105's Firefox repro), G (zstd/brotli), H (fresh instance)
    remain the owner's choice, as listed in `handoff/HANDOFF-2026-09-29c-installs-elsewhere.md`.

## Standing rules

- Don't start or restart other ddev projects during a counted run.
- Counted runners refuse an uncommitted host tree.
- `findings/evidence/**` and `handoff/**` are English; `specs/`, `research/`, `devlog/` are
  zh-TW.
- Write `--strict --red-cases FILE` (argparse needs the file right after `--red-cases`).
- The owner's away-authorization covers decisions via fable: send any genuine decision to fable
  with options A/B/C, facts F1..Fn with `file:line`, and the main session's lean; ask for
  RULING / WHY (zh-TW, for the owner) / FACT CHECK / CONDITIONS. Re-check fable's cited numbers
  before acting on them.
