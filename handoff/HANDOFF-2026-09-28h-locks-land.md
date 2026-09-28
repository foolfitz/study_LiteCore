# Handoff, 2026-09-28 (h) — Locks and permissions land; finding 102

Entry points: this file, `findings/evidence/m3-locks/RESULT.md`,
`findings/evidence/m3-locks/README.md`, `specs/SPEC-M3-locks-and-permissions.md`,
`findings/102-files-lock-token-lock-accepts-the-holders-token-from-anyone.md`.

Picks up from `HANDOFF-2026-09-28g-locks-host-patched-full-shakedown-next.md`. Its steps
1–4 are done; step 5 (named limits) is carried into `RESULT.md`'s last section.

## Result

Counted run `findings/evidence/m3-locks/runs/2026-09-28T131020+0000.json`: **`LOCKS LAND`**,
52/52 runs (K1–K12, Chrome 151 and Firefox 156, full repeat counts), against host
`litecore` `49cc4ab` (tree clean), page `fbfb59a4…`, runner `735c998a…`. Re-scored from
the stored report: same verdict. `--red-cases` against it: 87 `red`, nothing else.
Page, shell (v53), engine, profile: untouched.

## What happened this session, in order

1. **Full shakedown** (`shakedown/2026-09-28T121837+0000.json`): 21/22 clean. Chrome K7
   died at setup, before the host ran: every request got the ddev-router's text/plain
   `404 page not found`, and the owner's other project `fgp-nc` had its containers
   created 5 s earlier (`docker inspect … {{.Created}}`). Attributed by timing and
   signature, not by a reproduced mechanism. Chrome K7 re-run alone (`…130528…`): clean.
   Red cases over the two reports together: every mutation × browser red once.
2. **Probe L7/L8** (`probe_m3_lock_semantics.py --only L7 L8`; reports `semantics-…130648Z`,
   `…130750Z`): K12's premise (a refused unlock still moves the ETag) is now measured;
   finding 101's minimal repro holds, with the host's fix as the control (A: 204 at
   22.3 s, lock gone; B: 423 at 23.2 s, lock held).
3. **Finding 102**, found while doing step 2: the refused unlock's 423 body carries the
   holder's token (it was already in the 09-28 L5 evidence, unread), so L7 got an arm
   where the recipient PUTs with it. 204, and the holder reads back the recipient's
   bytes (2/2). The recipient's own PROPFIND `lockdiscovery` also shows the token; RFC
   4918 treats tokens as public, and §6.4 requires a principal check that Sabre's
   `validateTokens` does not do (source read: string compare only). The host loses no
   data — `saveOnce` does not retry on a live-token 412, and a dead-token retry reuses the
   old ETag, so both branches end in the copy. Recorded as a named limit in the spec
   (added during the counted run, before its result; no criterion touched). No K13: the
   host branch is the one K12 already drives.
4. **Counted-run rules** committed before the run (README, last sections): judge the run
   whole, never patch or merge reports; an unreachable-instance red means a full repeat.
   Not needed — no red.

## State

- `study_LiteCore`: all of the above committed on `main`, not pushed.
- `~/Projects/Nextcloud_Apps/litecore`: `49cc4ab`, clean, not pushed. No host change this session.
- Memory updated (ddev scaffold note): finding 102, and the router 404 when another ddev
  project starts.

## What is next — owner's choice

The roadmap's M3 completion criterion (§5.5) is: from Files, open an ODT → edit → save →
**versions correct** → locks correct, with no server-side document process. Locks are
now done; three things remain, and none of them blocks the others:

- **A. Versions** (recommended first; the last unmeasured item in §5.5, cheap). What
  Nextcloud's own file versions look like after our conditional saves (one version per
  save? the conflict copy's history?), and what happens when someone restores a version
  from Files while the page holds the lock (restore is a write: does it get 423, or go
  through like finding 102?). HTTP probe first, then at most one browser arm. No page change.
- **B. Page read-only mode and the "clean" semantic.** Today a read-only file is editable
  and save goes to the copy; "clean" is set before the host accepts the save. Both are
  page/shell changes → new page identity and shell generation, the owner's call.
- **C. Asset delivery (§5.3).** The v14 split package's `.data`/`.metadata` and every
  `.json` are 404 through Apache's extension allow-list; they have to go through PHP or
  another route, and 169 MB is not an App Store tarball. This is the bigger obstacle to
  shipping, and it is independent of A and B.

Standing rules for whoever runs next: ask the owner not to start or restart other ddev
projects during a long run; findings 100–102 stay on the submission freeze, and 102
needs a security-policy check (HackerOne vs a public issue) before it goes anywhere.
