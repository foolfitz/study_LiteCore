# Handoff, 2026-09-29b — Install elsewhere: spec written, tools built, reviewed twice, not counted

Entry points: this file, `specs/SPEC-M3-install-elsewhere.md`,
`findings/evidence/m3-install/README.md`,
`findings/evidence/m3-install/review-2026-09-29-opus.md`,
`findings/evidence/m3-install/review-2026-09-29-opus-2.md`,
`findings/evidence/m3-install/ruling-2026-09-29-fable-h3.md`,
`research/ROADMAP-2026-08-20-milestones.md` §5.5.

Picks up from `handoff/HANDOFF-2026-09-29-asset-delivery-lands.md`. The owner picked, in their
own words, option **"B＋E (Recommended)"**, instance **"litecoreprobe 原樣加裝"** (install the
release archive into the existing `litecoreprobe` as-is — no Nextcloud reinstall, no new ddev
project). The owner then said they were away and authorized fable to decide anything needing a
call in their place: "我不在座位，請自主執行，如果有任何需要我裁決的，我授權fable代我下決定".

## Status

**No counted run of this step exists.** Spec `specs/SPEC-M3-install-elsewhere.md` (criteria
I0–I4, verdict name `INSTALLS ELSEWHERE`, two qualifiers that must travel with the verdict —
see its §4 end) has been through two read-only adversarial reviews and one fable ruling; three
window shakedowns and several host-entry shakedowns ran, each surfacing and then retiring an
instrument bug rather than a product failure. The second review stopped at context limit with
2 of 17 items fixed and the other 15 **adopted but not done** — that is this session's main
queue. `study_LiteCore` is at `4bddaf8c`, working tree clean, not pushed (no `origin` remote
configured; the `github` remote is 165 commits behind, a pre-existing gap). Host repo
`~/Projects/Nextcloud_Apps/litecore` unchanged at `5e53362` (app version 0.2.1), clean, not
pushed.

## Correction to the previous handoff (fable's ruling, condition 7)

The previous handoff's option E said "host entry's only check not covered elsewhere is H5".
fable's ruling (`ruling-2026-09-29-fable-h3.md`, fact check F6) found this **false**: also
uncovered elsewhere are H3's "second press after a conflict is still refused, not silently
overwritten" and H2's "the heading really landed in the server file" (neither the locks nor the
versions runner has a `Heading`/`text:h` check). Both remain host-entry-only. That is why H3 is
being kept in the runner (ruling: option B) rather than retired per
`SPEC-M3-locks-and-permissions.md:94`.

## What happened this session, in order

1. Spec drafted before any tool or run: instance `litecoreprobe` taken "as it was" (§2 lists
   four ways it isn't a fresh install, and what keeps each from deciding a result); release
   archive shape (§3.1); install procedure (§3.2); the four counted runners made to accept
   `--ddev-root` (§3.3); host-entry runner adapted for a locking host (§3.4); the server-process
   measurement method (§3.5); acceptance criteria I0–I4 (§4).
2. `wasm_sdk_probe/tools/build_m3_release.py` and
   `wasm_sdk_probe/tools/check_m3_install_elsewhere.py` written. First install (06:2x). First
   window shakedown (`findings/evidence/m3-install/shakedown/2026-09-28T223255+0000.json`) —
   red on I2-1 (a prior run's 408 debris landing inside the window; fixed by requiring the dev
   instance quiet ≥60s before opening), I3-6 (expected: only a locks-arm subset was run), I3-7
   (a scoring-mode mismatch; fixed).
3. First adversarial review (opus, read-only, 19 items, `review-2026-09-29-opus.md`) corrected
   three factual errors in the draft (`dist/` does have `.gz` files; a backgrounded process gets
   adopted by PID 1 and stops being a php-fpm descendant; a long-lived document server is not
   automatically caught) and added criteria — I1-2 reweigh at window time / `app:getpath` /
   binding self-test; I2-1 health-check line count and post-window quiet; I2-3 mount reads;
   I2-4 probe-app routes; I3-5 report timestamps; I3-6 red-case rerun at scoring time; I3-8
   recording-path diff and module shas; I4-1b PID-1 orphans against a pre-install baseline
   (hence a reinstall); I4-2 sample-gap ≤1.0s; I4-3 container-lifecycle event stream; three
   positive controls. No criterion was loosened.
4. fable ruling (owner-authorized) on host-entry's H3: kept it (option B), rationale corrected
   to same-principal WebDAV semantics (RFC 4918 §6.4) rather than finding 102; the scorer now
   pins H3 to the branch it claims (`intruder.mode == "lock-token"`), adding red cases
   `H3-intruder-refused` / `H3-lock-died`.
5. Second and third window shakedowns (`…230921+0000.json`, `…231953+0000.json`) — second red
   only on two sampler bugs (the positive control's own `docker exec` dragging a sample to
   1.6s; an untracked short-lived control process); third red only on the expected locks-arm
   subset. Sampler rewritten between the two to one persistent `docker exec` loop (§3.5
   revision; the acceptance criteria did not change).
6. Host-entry shakedowns run directly on the dev instance:
   `findings/evidence/m3-host-entry/shakedown/2026-09-28T223038Z.json` (pre-pin, all arms
   clean) and `…230636Z.json` (post-pin H3, all arms clean, the new red cases red). No counted
   host-entry run exists on either instance yet.
7. Reinstall (`--reinstall`) for I4-1b's pre-install baseline
   (`findings/evidence/m3-install/install.json`); the from-nothing install survives only inside
   the first shakedown's embedded `install` key. Second review, item 1, then found that
   `occ app:remove` leaves `litecore`'s app config behind, so this reinstall's `app:enable`
   re-enabled a known version rather than truly installing from nothing.
8. Second adversarial review (opus, read-only, 17 items,
   `findings/evidence/m3-install/review-2026-09-29-opus-2.md`) against the post-review-1 spec,
   tool, and shakedowns. **Stopped at context limit** with items 5 (host-entry `--red-cases`
   crashed on every pre-lock report) and 6(d) (the scorer crashed on 2-tuple fds in every
   stored shakedown) fixed; the other 15 are adopted, not yet done.

## State

- `study_LiteCore`: `main` at `4bddaf8c`, clean, not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `5e53362` (app version 0.2.1), clean, not pushed.
- `litecoreprobe` currently has `litecore` installed via the `--reinstall` path
  (`findings/evidence/m3-install/install.json`, README's "Install" section). Its leftover app
  config (item 7 above) means item 1 below must delete that config before the next
  `app:enable`.
- Release archive `wasm_sdk_probe/build/release/litecore-0.2.1.tar.gz` is on disk (63,431,712
  bytes, sha256 `849f29f7…`), untracked (gitignored); rebuild with `build_m3_release.py` if
  missing. Record and member hashes: `findings/evidence/m3-install/release.json`.
- No counted run of I0–I4 exists on `litecoreprobe`; no counted host-entry run exists on either
  instance.

## What is next

The owner's choice (B+E) is already made — this is a to-do, not a menu.

1. Implement every "Adopt" row of `review-2026-09-29-opus-2.md` (items 5 and 6(d) already
   fixed; 15 remain): #1 delete `litecore`'s app config in `--reinstall` after `app:remove`;
   #2 make I4-1b flag any *descendant* of PID 1 whose (pid, start time) is not among the
   baseline's PID-1 descendants, instead of checking direct children by `comm`,
   and correct the spec's rejected-lineage sentence; #3 confirm the I4-3 event-stream process
   is alive before `terminate()`, plus a second create/rm control near window end; #4 restate
   I2-3's reach as statistical (large files only) and decide on a php-fpm-faithful control;
   #6(a,b,c) `find` before `ps` in the sampler loop, redirect the control exec's stdio (the
   stale baseline is retaken by #1's reinstall); #7 one red-case mutation per still-uncovered
   branch; #8 register (don't gate) that `docker exec`-rooted processes are unseen by I4-1;
   #9 use `ddev/ddev-utilities:latest` for the event control, and state that any container
   activity on the host during the window turns I4-3 red; #10 strengthen the equivalence
   recording test against `git show 9748b714:`; #11 correct the spec's "scoring functions never
   changed" claim (host-entry's did); #12 decide how `module_shas` covers lazily imported
   modules; #13 close I4-1a's gap for a php-fpm-named child of a worker (`pcntl_fork`): flag any php-fpm
   whose parent is not the master, and add `pcntl_fork` to the registered scan; #14 mark or measure "no subreaper in the
   container"; #15 several sampler/scorer robustness fixes (`ps -ww`, stderr draining, a
   guarded `red_cases_now`); #16 strike stale §3.5 text, cite
   `shakedown/2026-09-28T231953+0000.json` for the 0.515s max gap; #17 `tree_listing` should
   account for sockets, FIFOs, empty directories.
2. `check_m3_install_elsewhere.py install --reinstall` after item 1's change (deletes
   litecore's app config; re-takes the I4-1b baseline with the current sampler).
3. `equivalence` — re-run after any change under `tools/`; the counted scorer checks runner
   and module shas against it.
4. A window shakedown (all four runners, `--repeats 1`, locks may stay on a subset), then
   `check_m3_install_elsewhere.py --strict --red-cases <that report>`: must be 0 SKIP, 0 GREEN,
   0 failed.
5. Host-entry counted run on the dev instance (`check_m3_host_entry.py --label counted`) with
   the final runner, then its own `--red-cases`.
6. The counted window: `check_m3_install_elsewhere.py run --label counted --dev-host-entry
   <that report>` (~1.5h: assets, versions, host entry, locks on `litecoreprobe`), then
   `--score` and `--red-cases`.
7. Write `findings/evidence/m3-install/RESULT.md`; add the `INSTALLS ELSEWHERE` result
   paragraph (with both qualifiers from spec §4's end) to
   `research/ROADMAP-2026-08-20-milestones.md` §5.5; update memory.

Worth considering: splitting the ~1.5h counted window (and the dev host-entry counted run) to a
sonnet executor with the main session re-scoring from the stored reports, the same division
used for the K3 rerun in the asset-delivery session.

After the verdict, the options carried over from the previous handoff remain open: **A**
distribution channel, **C** page read-only mode + the "clean" semantic, **D** host hardening
for findings 103/104, **F** finding 105's unfixed guarded-leave path plus a Firefox-only repro,
**G** zstd/brotli for the engine.

## Standing rules

- Don't start or restart other ddev projects during a window.
- The window waits for the dev instance to be quiet ≥60s before opening; nothing may touch the
  dev instance during it (the dev host-entry counted run must finish before the window starts).
- Counted runners refuse to run against an uncommitted/dirty host binding.
- Any container activity on the host during the window turns I4-3 red (review-2, item 9).
- `findings/evidence/**` and `handoff/**` are English (repo rule, `CLAUDE.md`/`AGENTS.md`).

## Discrepancies

None left. (The drafting agent had noted that `--strict` / `--red-cases` order does not matter; the
main session measured otherwise: `--red-cases --strict FILE` is rejected by argparse
("argument --red-cases: expected one argument"), because `--red-cases` must be followed by
its file. Write `--strict --red-cases FILE` or `--red-cases FILE --strict`.)
