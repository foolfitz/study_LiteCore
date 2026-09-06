# RESULT — 4b instrument-reproduction protocol on `39895d15…`

Executor: sonnet, task T1b of
`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`, running
`handoff/tasks/TASK-2026-09-06-4b-instrument-reproduction.md` as written.
Session date: 2026-09-07 (CST).

**Outcome: zero walks were executed. The session stopped before Walk 1
because the environment precondition of the protocol's section 4.1 item 3 /
section 7.4 ("exactly one Chrome browser process on the desktop") was never
satisfied during the observation window, and the executor is not authorised
to force it to hold.** None of the six outcomes named in section 5 (O-A
through O-F) applies, because they are all defined over walks that were
attempted; here no walk was attempted at all. This is recorded as its own,
distinct condition rather than folded into O-F, per `AGENTS.md`'s rule that
"has behaviour with nothing guarding it" and "nothing to guard" are two
different registrations that must not be written as the same sentence.

## 1. What was prepared

- `CONSENT.md` written from the paragraph the plan's main session ruled on
  ("Consent for the T1b walks", `PLAN-2026-09-06-after-the-page-moved-twice.md`),
  quoting the owner's verbatim reply of 2026-09-07, 「現在可以」. Not re-asked.
- `drive_walk_focus.py` copied byte-for-byte from
  `manual-round-v12b-20f09cc9/`. sha256
  `414f1245c8fd02056e52906d420c6e58bbe2046897749aa273282f7371f29813`,
  identical to the banked source (`diff` empty).
- `drive_walk_focus_noraise.py` prepared for arm A0 setting Y: one line
  changed (`raise_window()` call at the banked file's line 57 commented out),
  a header comment naming the single difference, `diff -u` saved as
  `drive_walk_focus_noraise.diff.txt`. sha256
  `692826175979af718bae4b561423fa247f2f7dd465dcb05d5cb2189a42449700`.

Neither instrument file was executed. They are staged for whenever the
environment blocker below is cleared.

## 2. Identity gate (protocol section 1.3)

Run once, before attempting Walk 1. No walk ran, so there is no "after the
last walk" gate to compare it against; the same four checks were re-run
immediately before writing this report, after the candidate server was
stopped, to confirm nothing moved while the session was blocked.

| check | expected | before (00:20 CST) | re-checked (00:29 CST) |
|---|---|---|---|
| (a) `build_cutover_page.py --profile e2-editor-v12` `pageSha256` | `39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e` | match | match |
| (b) served bytes, `curl \| sha256sum` | same as (a) | match | match |
| (c) `editor-shell-v2-bundle-v45.json` `bundleSha256` | `a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578` | match | match |
| (d) `pytest tests/test_e2_c_shell_bundle.py -k the_real_manifest_matches_the_real_tree` | pass | `1 passed, 11 deselected in 0.03s` | not re-run (identical tree, (a)-(c) unchanged) |

(d) needed `pytest`, `psutil` and `websockets` installed; none were present in
the system Python (`/usr/bin/python3`, 3.14) and `pip install --user` refused
with `externally-managed-environment`. A venv was created under this agent's
scratchpad (`/tmp/claude-1000/.../scratchpad/venv-pytest`, outside the repo
and outside `/tmp` in the sense the protocol warns about -- it is on the
tmpfs but is a few megabytes of interpreter packages, not walk evidence) and
used only to invoke the existing test; nothing in the repository was edited
to make it importable. This is an environment fix, not the "no new
comparison" this section rules out -- the test itself was not touched.

The candidate page was served with:

```
python3 tools/serve_candidate_page.py --profile e2-editor-v12 --port 8765 \
  --expect-sha256 39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e
```

Server stopped and its scratch mirror (`/tmp/candidate-round-79fb9l69`) removed
before this report was written (protocol section 7.6). `git rev-parse HEAD`
throughout: `f71a33c60b7ec781b67c3b2ba2d1e6819e5fb367`; `git status --porcelain`
showed only this evidence directory as untracked, both before and after.

## 3. The environment blocker

Protocol section 4.1 item 3 requires, before starting any walk: "Exactly one
Chrome (§7.4), no stray Orca." Section 7.4 requires the set of distinct
`--user-data-dir` values across every `chrome`/`google-chrome` process to be
exactly one -- the walk's own -- and instructs: **"If one is found, wait or
ask -- do not kill another agent's browser."**

At the first check (00:21 CST, before any walk-related process was launched
by this session), two pre-existing Chrome process families were already
running, neither belonging to this task:

1. **An orphaned headless instance**, `--headless=new
   --user-data-dir=/tmp/wasm-sdk-probe-chrome-cearp5rb
   --remote-debugging-port=36945`, started 2026-09-06 20:21:55 (running
   ~4 hours by the time of the last check). The `/tmp/wasm-sdk-probe-chrome-*`
   naming matches this project's own probe tooling, so this is very likely
   debris from an earlier, unrelated automated run in this tree that did not
   clean up after itself -- but the executor did not trace which task left
   it, and is not authorised to decide it is safe to kill on that inference
   alone.
2. **What the process evidence indicates is the owner's own browser**:
   `/opt/google/chrome/chrome` with no arguments at all -- no
   `--remote-debugging-port`, no `--user-data-dir`, i.e. the default profile,
   consistent with a normal desktop launch rather than any automation in this
   repository (every automated Chrome launch this protocol or this tree uses
   carries `--remote-debugging-port` and an explicit `--user-data-dir`).
   First seen 2026-09-07 00:09:31 CST. This family was not static: between
   the first check (00:21) and the last (00:29) it grew from 20 processes to
   22, with new renderer PIDs appearing at 00:11:36, 00:12:11, 00:26:36 and
   00:29:17 -- i.e. new tabs or navigations continued to occur throughout the
   session, which is inconsistent with an idle desktop and is not something
   this executor caused (no CDP connection was ever opened to this Chrome;
   this session's only browser-facing action was `curl` against the static
   file server on port 8765).

Per section 7.4's instruction, the executor did not kill either process
family. A single **bounded** wait was run rather than an open-ended one --
`AGENTS.md`'s rule against quantifying a criterion on "wait until it looks
quiet" applies to the executor's own conduct as much as to the protocol's --
so a 310-second poll (`until pgrep -x chrome and pgrep -x google-chrome are
both empty`) was set and run to completion:

```
exit=124
```

(`124` is `timeout`'s own "deadline reached" code -- the loop never observed
a clear desktop in those 310 seconds.) Combined with the process-count growth
observed independently before and after that window, the desktop was not
idle at any point this session was able to check.

The executor has no synchronous channel to the owner (this task's role is
executor, reporting to the plan's main session at the end of the run), so
"ask" resolves to this report. No walk was started, because starting one
while already knowing the precondition fails would be choosing to run it
dirty rather than reporting that it could not be run clean -- and every such
walk would, by the protocol's own definition (§2.3, V5), come back voided
regardless of what it measured, telling the pursuit nothing about the
instrument.

## 4. What this is not

- **Not O-F.** O-F requires five walks that were actually run and voided by
  desktop activity, after which the pursuit reports "a quiet window did not
  exist." Here zero walks were attempted, so the void counter never moved.
  Writing this as O-F would overstate what was measured.
- **Not a judgement that the pursuit is dead.** The budget (20 walks) and the
  calendar (2026-09-08 23:59 CST) are both untouched. If a window opens where
  `pgrep -x chrome` (and `-x google-chrome`) return nothing before this
  session's own Chrome is launched, Walk 1 of arm A0 can start immediately --
  the instrument files are already staged (§1 above).
- **Not a decision about the orphaned headless Chrome or the owner's
  browser.** The executor is not deciding whether the orphan is safe to
  kill, or asking the owner to close their browser -- both of those are calls
  for the main session (or the owner) to make, not this task's role.

## 5. Recommendation for whoever reads this next (not a ruling)

Stated as a fact pattern, not an instruction, because the role does not carry
judgement: for a Walk 1 to be attempted, the desktop needs a state where
`pgrep -x chrome; pgrep -x google-chrome` returns nothing before this
session's own Chrome is launched (protocol §7.4's launch command). That
requires the owner's browser to be closed and, separately, someone with more
context than this executor to decide whether the orphaned headless instance
(`/tmp/wasm-sdk-probe-chrome-cearp5rb`, running since 2026-09-06 20:21:55) is
safe to stop.

## 6. Files in this directory

| file | status |
|---|---|
| `CONSENT.md` | written, protocol §1.4 |
| `drive_walk_focus.py` | staged, unexecuted, sha256 recorded above |
| `drive_walk_focus_noraise.py` | staged, unexecuted, sha256 recorded above |
| `drive_walk_focus_noraise.diff.txt` | the one-line diff between the two |
| `RESULT-4b-instrument-reproduction.md` | this file |

No `walk-*.json`, no `orca-*.log`, no `speech.txt` exist, because no walk ran.
