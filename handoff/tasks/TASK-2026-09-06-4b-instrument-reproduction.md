# TASK — make the 4b walk reproduce on `39895d15…`, or register that it does not

Expansion of task **T1a** of `handoff/PLAN-2026-09-06-after-the-page-moved-twice.md`
(section "T1a — the 4b instrument-reproduction protocol"). Drafted by the opus
seat on 2026-09-06 from the banked evidence in
`findings/evidence/manual-round-v12b-20f09cc9/`, **before any walk on the new
page has been run**. Every criterion below is pre-registered; §9 of `AGENTS.md`
governs anything added after the first walk that counts.

- **Structure rule.** The executor may write **only** two things: (a) files
  under the new directory `findings/evidence/manual-round-v12c-39895d15/`, and
  (b) one appended section under `## Execution record` at the end of *this*
  file. No file anywhere else in the tree may be created, edited, moved or
  deleted — not `wasm_sdk_probe/`, not `web/`, not `dist/`, not the banked
  `manual-round-v12b-20f09cc9/` directory, not `.gitignore` (`!/findings` on
  line 22 already tracks the new directory), and not the instrument
  `drive_walk_focus.py` in its banked location. The instrument is used by
  **copying it verbatim** into the new directory.
- **Role.** The executor is the sonnet seat: it runs the procedure and records
  what happened. It is **not** the drafting party and carries no judgement. It
  does not decide whether v46 lands, whether the gate freezes, or whether a
  criterion should be relaxed. If a criterion turns out to be unsatisfiable as
  written, the executor **stops and reports** — it does not rewrite the
  criterion, and it does not build machinery to make one hold (`AGENTS.md` §4,
  self-check: "if you find yourself writing a new mechanism rather than a test
  or a sentence, stop and report"). `AGENTS.md` §11 is why: on 2026-08-29 the
  drafting party's own measurements were wrong six times in one session, and
  the remedy adopted was `AGENTS.md` §8 — the terminating declaration is not carried by the
  party that drafted it.

Where the plan's brief lands: item 1 → §1; item 2 → §2; item 3 → §3; item 4 →
§6; item 5 → §5; item 6 → §7; item 7 → §8. §4 is the per-walk procedure the
other sections refer to.

---

## 1. Object, identity, and where the evidence goes

### 1.1 The object under test

The instrument is
`findings/evidence/manual-round-v12b-20f09cc9/drive_walk_focus.py`, copied
**byte for byte** into the new evidence directory. It is the only banked walk
driver that records `document.hasFocus()` per stop and reports
`focusHeldEveryStop` / `stopsWithoutFocus`, which the reproduction criterion
requires.

It drives the `a11y-audible` fixture, places the caret by `LINE_INK` +
`place_caret_and_settle` until `aria-activedescendant` is `a11y-node-0`, then
presses ArrowDown until the pointer changes, ten stops, 11 s dwell after each
stop. It connects to an **already-running headed Chrome** on CDP port **9341**;
it does not launch a browser.

**Named limit, registered now.** Line 110 is `while len(rows) < 10 and presses
< 90`. The "10" is a hand-written constant, not derived from the document — it
is `AGENTS.md` §1's third form (hand enumeration) living inside the instrument.
It is left exactly as it is: changing it produces a different instrument and
voids the comparison with the banked walks. The consequence is that the count's
denominator is fixed at 10 by the tool, and a fixture with eleven paragraphs
would silently be walked as ten. That is registered as a limit, not fixed here.

### 1.2 Identity of the page and the shell

| | value |
|---|---|
| candidate page `pageSha256` | `39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e` |
| built by | `wasm_sdk_probe/tools/build_cutover_page.py --profile e2-editor-v12` |
| pins | `4a2710bba1ef07d9` -> `4ec1e389aaab3b03` |
| frozen generation | `wasm_sdk_probe/e2/editor-shell-v2-bundle-v45.json` |
| `bundleSha256` (v45) | `a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578` |

`build_cutover_page.py` writes nothing unless given `--write` or `--out`; run
without either it prints the page's sha256 and exits, which is how the executor
reads the identity. **Never pass `--write` in this task.** The bytes are served
by `wasm_sdk_probe/tools/serve_candidate_page.py --profile e2-editor-v12
--expect-sha256 39895d15…`, which builds the same page through the same
`repointed_page()` function, mirrors `dist/` around it with symlinks, and serves
the mirror. Nothing under `dist/`, `web/` or `sdk/` is written by it.

### 1.3 The identity gate, before the first walk and after the last

Run this **before the first walk of the session** and again **after the last
walk, before anything is committed**:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe

# (a) the page the cutover would ship
python3 tools/build_cutover_page.py --profile e2-editor-v12
#     pageSha256 must be 39895d1530c2e30f7ddcb45cb0ada8d704412f5bcb3dd330134167739c5dad0e

# (b) the served bytes, fetched over HTTP and hashed -- not the tool's claim
curl -s http://127.0.0.1:8765/e2-editor-app.js | sha256sum
#     must be the same 39895d15… ; the page is served at /e2-editor-app.js
#     because web/e2-editor.html:265 loads "./e2-editor-app.js"

# (c) the frozen generation
python3 -c "import json;print(json.load(open('e2/editor-shell-v2-bundle-v45.json'))['bundleSha256'])"
#     must be a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578

# (d) the shell the tree actually serves matches the frozen manifest, INCLUDING
#     the dist/ copy of every bound path.  This is an existing check; do not
#     build another one.
python3 -m pytest tests/test_e2_c_shell_bundle.py \
        -k the_real_manifest_matches_the_real_tree -q
```

(d) is the check `HANDOFF-2026-09-06` §E-6 says had been red since finding 087's
fix while **nobody ran it**. `problems()` in `tools/build_e2_c_shell_bundle.py`
lines 539–542 compares `distHashes[path]` against `hashes[path]` for every
included path, so this test *does* compare `web/` with `dist/` for the thirteen
bound paths. It does not compare the two directories in full and it does not
check the served mirror, so finding 090's guard is still owed — but it is not
true that nothing compares them, and no new comparison is to be written here.

**Refuse to bank** if (a) and (b) disagree, if either differs from `39895d15…`
before the first walk or after the last, if (c) is not `a46c8518…`, or if (d) is
not green. A mismatch after the last walk means the tree moved during the
session: the walks are void and the correct action is to report, not to
re-measure quietly.

### 1.4 Consent — obtain it again, for this page

`findings/evidence/manual-round-v12b-20f09cc9/CONSENT.md` records the owner's
words of 2026-09-06, verbatim 「同意你操作桌面 session」, given for a 4b walk on
page `20f09cc9…`, and itself re-records rather than cites the 2026-09-03 consent
given for `3dfdcfef…` — because "treating a consent as transferable across the
thing it was given about is the same error as treating evidence that way".

**The page has moved again.** Before the first walk the executor asks the owner
for consent naming this page (`39895d15…`) and this purpose (the instrument
reproduction walks, not condition 3 and not 4b's judgement half), and writes
`findings/evidence/manual-round-v12c-39895d15/CONSENT.md` recording the reply
verbatim, in the shape of the v12b file: what it covers (headed browser on the
owner's desktop session, starting and stopping Orca, clicks and keystrokes into
that browser window) and what it does not (condition 3's six manual cells; 4b's
judgement half — announcement order, verbosity, what it sounded like). **If the
owner does not reply, no walk runs.** That is not a delay to work around; the
consent is the authority for touching the desktop at all.

### 1.5 Files in the new evidence directory

`findings/evidence/manual-round-v12c-39895d15/`, in English (`AGENTS.md`: the
upstream-and-evidence rule):

| file | what it is |
|---|---|
| `CONSENT.md` | §1.4 |
| `drive_walk_focus.py` | verbatim copy of the banked instrument; its sha256 in every record |
| `drive_walk_focus_noraise.py` | arm A0 only; see §3.1 |
| `walk-<id>.json` | the instrument's stdout, unedited |
| `walk-<id>.record.json` | the executor's sidecar (§1.6) |
| `orca-<id>.log.gz` | full Orca debug log, `gzip -n -9` |
| `orca-<id>.walk-slice.log` | plain text, the bytes between the two bounds (§4.3) |
| `orca-<id>.walk-bounds.txt` | two lines: START then END, integers only |
| `orca-<id>.speech.txt` | every `SPEECH OUTPUT` line of the slice — the payload, not a summary |
| `RESULT-4b-instrument-reproduction.md` | the executor's report, written last |

The full logs are gzipped because a `--debug-file` run writes 3–16 MB per walk
(the banked ones are 3.1 MB to 16.0 MB) and this task may produce twenty of
them; `zcat` reproduces the exact bytes and the record carries the uncompressed
sha256 and byte size. Logs are written **on disk under this directory**, never
under `/tmp` — `/tmp` is a 16 GB tmpfs on this machine and it reached 98% on
2026-09-06, killing two runs and one `git commit` with ENOSPC.

### 1.6 `walk-<id>.record.json` — what every walk record must carry

Written by the executor, because the instrument does not emit these and the
instrument must not be edited. Minimum fields:

```json
{
  "walkId": "a0-raise-1",
  "arm": "A0", "setting": "raise-once", "pairPosition": 1,
  "startedAt": "2026-09-07T…Z", "completedAt": "2026-09-07T…Z",
  "pageSha256": "39895d15…",
  "pageSha256Source": "curl http://127.0.0.1:8765/e2-editor-app.js | sha256sum",
  "servedShellBundleSha256": "a46c8518a7ebfb12a65b5d0a14d0e82263956ed4fbe34f49b1a1efdb43fdb578",
  "shellManifest": "wasm_sdk_probe/e2/editor-shell-v2-bundle-v45.json",
  "pinBefore": "4a2710bba1ef07d9", "pinAfter": "4ec1e389aaab3b03",
  "instrumentFile": "drive_walk_focus.py", "instrumentSha256": "…",
  "gitHead": "…", "gitStatusPorcelain": "",
  "orcaLogSha256": "…", "orcaLogBytes": 0,
  "walkBounds": {"start": 0, "end": 0},
  "focusHeldEveryStop": true, "stopsWithoutFocus": [],
  "attachUtterances": 2,
  "announcedParagraphs": 10,
  "utterancesPerParagraph": [1,1,1,1,1,1,1,1,1,1],
  "speechLinesInSlice": 24,
  "verdict": "VALID | VOID(<gate>) | REFUTED(<setting>)"
}
```

Timestamps in UTC (the 2026-09-03 ruling: reports had no wall-clock time; the
runner now writes `startedAt`/`completedAt` and the UTC day rolls at 08:00 CST).

---

## 2. The reproduction criterion

### 2.1 "Announced", defined operationally

Orca's `--debug-file` log writes one line per utterance in the form

```
23:06:29.372961 - SPEECH OUTPUT: '這一行是普通內文.' {'established': False, 'family': {…}}
```

**No script in this tree parses Orca logs.** `grep -rln "SPEECH OUTPUT"
--include=*.py --include=*.sh .` over the whole repository returns nothing:
every count in `RESULT-4b-a11y-audible.md` was made by hand. Counting here is
therefore done by the shell pipeline below, and by nothing else — no eye-count
goes in the record.

The denominator is **not typed into this protocol**. It is read out of the
walk's own JSON (`rows[].node`, the text the page put on the caret path at each
stop), so it is `AGENTS.md` §1's second form — tool-closed enumeration from the
truth source — rather than the third. A protocol that listed the ten strings
would be a mirror of the fixture and could go stale without anything turning
red.

```bash
D=findings/evidence/manual-round-v12c-39895d15
ID=a0-raise-1

# the paragraphs the walk actually visited, one per line, from the walk record
python3 -c 'import json,sys;[print(r["node"]) for r in json.load(open(sys.argv[1]))["rows"]]' \
        "$D/walk-$ID.json" > "$D/$ID.nodes.txt"

# the walk slice, bounded at BOTH ends (§4.3), speech lines only
START=$(sed -n 1p "$D/orca-$ID.walk-bounds.txt")
END=$(sed -n 2p "$D/orca-$ID.walk-bounds.txt")
tail -c +$((START+1)) "$D/orca-$ID.log" | head -c $((END-START)) \
  > "$D/orca-$ID.walk-slice.log"
grep -a "SPEECH OUTPUT" "$D/orca-$ID.walk-slice.log" > "$D/orca-$ID.speech.txt"

# ANNOUNCED: how many of the visited paragraphs reached the log
while IFS= read -r n; do
  grep -q -a -F -- "$n" "$D/orca-$ID.speech.txt" && echo "$n"
done < "$D/$ID.nodes.txt" | wc -l

# per-paragraph utterance counts (this is what shows a doubled paragraph)
while IFS= read -r n; do
  printf '%s\t%s\n' "$(grep -c -a -F -- "$n" "$D/orca-$ID.speech.txt")" "$n"
done < "$D/$ID.nodes.txt"

# ATTACH: did Orca ever enter the page's document group?  (§2.4)
grep -c -a -F "SPEECH OUTPUT: '文件內容'" "$D/orca-$ID.speech.txt"
```

`tail -c +N` is 1-based, so a byte count of `START` becomes `+$((START+1))`.
`grep -a` because Orca logs contain bytes that make grep treat them as binary.
`grep -F --` because two of the fixture's lines begin with `•` and two with a
digit and a dot.

### 2.2 The criterion, per-instance

Let W1 and W2 be two walks executed **consecutively under one setting's written
procedure, with nothing else changed between them**, on page bytes verified by
§1.3, with the same instrument file (same sha256). Write `announced(W)` for the
number produced by §2.1 and `n` for their common value. The instrument
**reproduces at n** iff all of the following hold:

1. W1 and W2 are both VALID (§2.3);
2. `focusHeldEveryStop == true` in both walk JSONs;
3. `announced(W1) == announced(W2) == n`;
4. `n` equals the number of stops at which focus was held **and** the focused
   paragraph's text reached the Orca log — which is what §2.1 computes, given
   clause 2. This clause is what forbids satisfying the criterion from the walk
   JSON alone: the JSON says what the page did, and the page did the right
   thing in every failing walk banked so far (§2.4). Only the log says what a
   screen reader said.

This is a per-instance property: it is stated about any two walks, including
walks that do not exist yet, and no walk needs to be named in it.

### 2.3 Validity, and what is a result rather than a void

**Identity voids** — nothing was measured; the walk does **not** count against
the budget:

- V1 the page identity gate of §1.3 fails at any point;
- V2 the shell gate of §1.3 fails;
- V6 the instrument exits non-zero (`{"error": "caret never reached the first
  heading"}`) or the walk JSON has fewer than ten rows, or its refs are not
  `a11y-node-0` … `a11y-node-9` in order.

**Environment void** — the desktop was not idle; the walk **does** count against
the exemption allowance of §6:

- V5 more than one Chrome browser process on the desktop during the walk
  (§7.4), or any `SPEECH OUTPUT` line in the slice that belongs to another
  application (§7.5).

**Everything else is a result, never a void.** In particular
`focusHeldEveryStop: false`, `attachUtterances: 0` and a low `announced` are
*outcomes of the setting under test* and must be recorded as such. Do not
promote them to voids: a setting that never attaches is exactly the finding the
task is looking for, and voiding it would make the failure invisible.

### 2.4 Two walks agreeing at 1 (or 0) is a reproducibly BROKEN instrument

Stated before anything runs, and grounded in the banked evidence rather than in
intuition. Recount of the six banked walks with the pipeline of §2.1:

| banked log | announced | utterances | `'文件內容'` spoken |
|---|---:|---:|---:|
| `orca-AFTER-THE-FIX.log` (5 s dwell) | **10** | 10 | 2 |
| `orca-AFTER-THE-FIX-slow-dwell.log` (11 s) | **10** | 11 | 2 |
| `orca-v45-CONTROL-after-reverting-v46.log` | 4 | 4 | 2 |
| `orca-v45-focus-instrumented.log` | 0 | 0 | **0** |
| `orca-v45-focus-held.log` (raise every press) | **1** | 1 | **0** |
| `orca-v45-raise-once.log` | **1** | 1 | **0** |

`文件內容` is the `aria-label` of `#a11y-doc`, the `role="group"` at
`wasm_sdk_probe/web/e2-editor.html:236` that contains both `#a11y-para` (the
live region) and `#a11y-structure` (the caret path). Orca speaks it when it
enters that group. **It was never spoken in any walk that failed to announce**,
and it was spoken twice in every walk that announced 4 or 10. Separation is
perfect over the six banked walks.

And in both n=1 walks the single utterance was `這一行是普通內文` with no
`heading 1`, no `List with 2 items`, no `Browse mode` and no `leaving list` —
i.e. it was a live-region update reaching an unattached Orca, not a caret-path
announcement. Meanwhile `walk-v45-held.json` and `walk-v45-raise-once.json`
record all ten stops with the correct `ref`, `role` and `level`, and the same
live-region pattern (`a11y-node-2` the only non-empty one) as the walks that
announced ten. **The page behaved identically in the walks that announced 10 and
in the walks that announced 1.** The variance is entirely on Orca's side of the
AT-SPI boundary.

Therefore: **if two consecutive walks agree at n ∈ {0, 1}, the criterion is NOT
met.** What the executor does:

1. Record the pair as `REFUTED(<setting>)` with its full `speech.txt` payload;
2. Do **not** report "the instrument reproduces";
3. Do **not** run T1c;
4. Move to the next arm in the order of §3 and continue the budget.

An agreement at n ∈ {0,1} is the instrument reproducing its own failure, and a
comparison of v45 against v46 made on it would compare two silences.

---

## 3. The arms: one variable at a time, each against a control

Every arm is a **pair of pairs**: two walks under setting X, then two walks
under setting Y, with everything not named in the arm held identical, and the
two settings run adjacent in time (never one tonight and one tomorrow — the
banked data is already confounded that way; see §3.1).

**Ruled in for every arm, not varied:** the window is **never raised before
every press.** `orca-v45-focus-held.log` is that configuration and it announced
1 of 10 with focus held at every stop; the repeated activation is itself an
event. `drive_walk_focus.py` as banked already raises only once, at line 57.

*One correction to the wording this rule inherits.* The plan says raising before
every press was "measured worse". The recount of §2.4 says something narrower:
raise-before-every-press and raise-once both announced **1**, so the two are
measured *equal*, and `RESULT-4b-a11y-audible.md` says as much in its own words
("reverted to a single raise, which changed nothing"). What the banked numbers
separate is **raising at all** (1, 1) from **not raising at all** (10, 10). The
rule is kept as written — nothing here argues for raising before every press —
but the variable it names is not settled by it, which is exactly why A0 exists.

**Ruled in for every arm:** the 11 s dwell, the `a11y-audible` fixture, the
`LINE_INK` caret placement, CDP port 9341, `--force-renderer-accessibility`.

### 3.1 A0 — the instrument raises once (control) vs the instrument does not raise

**First, and it is an addition to the three variables the handoff names.**
`AGENTS.md` §9 permits adding a criterion to a running pursuit if four things
hold; all four are stated here because the addition is being made before any
walk that counts:

1. *Prior to satisfaction* — written now, before the first walk on `39895d15…`;
2. *Forced and named* — forced by this measurement: **the only two banked walks
   that announced 10 were driven by scripts with no `Page.bringToFront` at all**
   (`findings/evidence/087/drive_arrow_walk.py` and
   `manual-round-v12b-20f09cc9/drive_walk_slow.py`), and **both walks driven by
   `drive_walk_focus.py`, which raises, announced 1.** `drive_walk_focus.py`
   differs from `drive_walk_slow.py` in exactly two ways: the single
   `raise_window()` call and the `hasFocus` field. So "the same bytes gave 10
   and then 1" is true of the *page* but not of the *instrument*: a different
   driver was used. That confound has to be removed before anything else is
   asked.
3. *Passes the form test* — the criterion is §2.2, form one/two, unchanged;
4. *Has a deadline* — §6's budget and calendar close it.

- **Held constant:** everything in §1 and the two "ruled in" lists.
- **Setting X (control, the banked instrument):** `drive_walk_focus.py`,
  verbatim copy, sha256 recorded. Two walks.
- **Setting Y:** `drive_walk_focus_noraise.py` — a copy of the same file with
  **exactly one change**: line 57's `raise_window()` call commented out. The
  function definition stays so the diff is one line. The file's header must
  carry a comment naming the single difference, and the record must carry
  `diff -u` of the two files and both sha256s. This is a control, not new
  machinery: it exists to remove a confound, not to keep a claim alive.
  Two walks.
- **Attributes the variance to A0 if:** one setting's pair meets §2.2 at
  n ≥ 2 and the other setting's pair does not (or refutes at n ≤ 1). Then the
  raise is the variable, and the settled configuration is the setting that met
  it.
- **Exonerates A0 if:** both settings' pairs behave the same — both meet §2.2 at
  the same n, or both fail to agree. Record and move to A1.

**Ordering note carried into every later arm:** in the banked data A0 is
confounded with A2 (the 10-count walks are at 23:06 and 23:09, after few
`--replace` cycles; the 1-count walks are at 23:34 and 23:36, after many) and
with the presence of a second Chrome window belonging to another agent's ODS
probe. That is precisely why each arm here runs its two settings adjacent in
time and why §7.4 forbids a second Chrome.

### 3.2 A1 — Orca started before Chrome vs Chrome started before Orca

Second, because §2.4 shows the failure is an **attachment** failure — Orca never
enters `#a11y-doc` — and the start order is the variable that decides which
window Orca's context is built on when it attaches. In every banked failure the
first thing Orca announced after `Screen reader on.` was a window that was not
the walk's: `study_LiteCore : claude — Konsole` (the terminal driving the walk)
or `ODS decisive probe (diagnostic) - Google Chrome` (another agent's browser).

- **Held constant:** the instrument settled by A0 (or the banked one if A0
  exonerated), a fresh Orca process per walk, a fresh Chrome process per walk,
  the served page, everything in §1.
- **Setting X:** start Orca, wait for `Screen reader on.` in the log, then
  launch Chrome on the URL, wait for the page to be ready, then run the walk.
  Two walks.
- **Setting Y:** launch Chrome on the URL, wait for the page to be ready, then
  start Orca, wait for `Screen reader on.`, then run the walk. Two walks.
- **Attributes to A1 if:** one setting's pair meets §2.2 at n ≥ 2 and the other
  does not.
- **Exonerates A1 if:** both settings behave the same. Record which window Orca
  announced first in each of the four logs regardless of the verdict — that
  line is the cheapest observation in this whole task and it was the thing that
  eventually explained the 2026-09-06 confusion.

### 3.3 A2 — a fresh Orca process per walk vs `orca --replace` cycling

Third, because it is a property of a **sequence** of walks and can only be
measured once a single walk is repeatable — which A0 and A1 must establish
first.

Mechanism, read from the installed source rather than assumed: `/usr/bin/orca`
line 323–324 is `if args.replace: cleanup(signal.SIGKILL)`, and `cleanup()`
(lines ~215–240) sends that signal to every pid from `pgrep -u <uid> -x orca`,
escalating to SIGKILL again after a 2 s alarm. So `--replace` **never lets the
previous Orca run its shutdown path** (`orca/orca.py:97 shutdown()`, reached
from the SIGTERM/SIGINT handlers at lines 174–175 and 193–194). Every banked
walk after the first was started with `--replace`.

- **Held constant:** the configuration settled by A0 and A1.
- **Setting X (control):** before each walk, stop Orca cleanly (§7.3), wait
  until `pgrep -x orca` is empty, then start Orca **without** `--replace`.
  Two walks.
- **Setting Y:** leave the previous Orca running and start the next one with
  `orca --replace`. Two walks. The first walk of this pair must itself follow a
  live Orca, so run one throwaway Orca start before it (that start is not a
  walk and does not count against the budget).
- **Attributes to A2 if:** setting X's pair meets §2.2 and setting Y's does not,
  or the two pairs meet it at different n.
- **Exonerates A2 if:** both settings' pairs meet §2.2 at the same n.

### 3.4 A3 — the same tab twice vs a fresh tab vs a fresh browser process

Last, because it has the least support: the walk JSONs show every stop reached
with the correct `ref`, `role`, `level` and live-region text in **every** walk,
including the ones that announced nothing. Whatever changed, the tab's DOM is
not it.

Three settings rather than two, because a fresh tab is **not** a fresh
accessibility bridge: Chrome's AT-SPI bridge belongs to the browser process, and
a new tab in the same `--user-data-dir` reuses it. Testing "fresh tab" alone
would leave the process-level question unasked, which is the trap
`AGENTS.md` §7 names — verifying a proxy instead of the claim.

- **Held constant:** the configuration settled by A0–A2.
- **Setting X:** walk the same tab twice — run the instrument, then run it again
  against the same CDP target without reloading. Two walks.
- **Setting Y:** a fresh tab in the same Chrome process for the second walk
  (open a new tab on the URL, close the old one). Two walks.
- **Setting Z:** a fresh Chrome process for each walk (stop the browser, remove
  its `--user-data-dir`, launch again). Two walks.
- **Attributes to A3 if:** the settings differ in whether §2.2 is met, or in n.
  Note which boundary the difference falls on — tab or process — because they
  are different remedies.
- **Exonerates A3 if:** all three settings behave alike.

---

## 4. Running one walk

### 4.1 Before

1. §1.3 identity gate (first walk of the session) or the abbreviated form
   (curl + sha256sum of the served page) for every later walk.
2. Desktop idle: confirmed with the owner for the session (§7.2).
3. Exactly one Chrome (§7.4), no stray Orca (`pgrep -x orca` empty unless the
   arm calls for a live one).
4. `git rev-parse HEAD` and `git status --porcelain` recorded.

### 4.2 The walk

Start Orca with the log **inside the evidence directory**:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
D=$PWD/findings/evidence/manual-round-v12c-39895d15
DISPLAY=:0 orca --debug-file="$D/orca-$ID.log" &     # add --replace only for A2/Y
```

Wait until `Screen reader on.` appears in the log before doing anything else.

Then, in the arm's order, launch Chrome (§7.4) and run the instrument:

```bash
START=$(stat -c%s "$D/orca-$ID.log")
python3 "$D/drive_walk_focus.py" > "$D/walk-$ID.json" 2>"$D/walk-$ID.stderr"
END=$(stat -c%s "$D/orca-$ID.log")
printf '%s\n%s\n' "$START" "$END" > "$D/orca-$ID.walk-bounds.txt"
```

Only then stop Orca (§7.3) and wait for `Screen reader off.` in the log.

### 4.3 Bound the slice at BOTH ends — this is not optional

The banked directory records only a start offset
(`*.walk-offset.txt`, a single integer). Reading from there to EOF pulls in
whatever the operator did **after** the walk. Measured: slicing
`orca-AFTER-THE-FIX-slow-dwell.log` from its banked offset 745907 to EOF gives
`announced=10, utterances=12` with `最後一行到了 整份文件到這裡結束` counted
twice; bounding the end at the operator's return to the terminal (`23:11:59`)
gives `announced=10, utterances=11` with only `這一行是普通內文` doubled — which
is exactly what `RESULT-4b-a11y-audible.md` reports. The write-up was right and
an unbounded slice would have contradicted it. Record both bounds, always.

### 4.4 After

1. Compute the counts with §2.1 and write `walk-<id>.record.json`.
2. Paste every line of `orca-<id>.speech.txt` into the record's per-walk section
   (§7.5). It is 3–40 lines. The payload goes in, not a summary of it
   (`AGENTS.md` §7: an error message carries its payload, not a tidy one-liner).
3. `gzip -n -9` the full log; record the **uncompressed** sha256 and byte size
   first.
4. Clean up (§7.6).

---

## 5. What each outcome means — written before anything runs

Six outcomes, exhaustive over the stop rules of §6. The meaning is fixed here so
that the party present at the last walk is not the party deciding what it meant
(`AGENTS.md` §2 and §8).

**O-A — the criterion is met at n = 10.** The instrument reproduces, and on this
page every one of the ten visited paragraphs reaches a screen reader. 4b's
mechanical half is measurable again on `39895d15…`. Report the settled
configuration and **stop; T1c (§8) runs only when the main session says so.**
Record the per-paragraph utterance counts as well as `announced`: if
`這一行是普通內文` is at 2 while the rest are at 1, the heading-boundary residue
is present and reproducing, which is the very thing v46 targets and is what
makes T1c worth running. If every paragraph is at 1, the residue did not appear
in these walks — say so plainly and do not claim it is gone; the banked evidence
puts it at the second heading in every walk that reached it, and two walks are
not a refutation of that.

**O-B — the criterion is met at 2 ≤ n ≤ 9.** The instrument reproduces but the
product does not announce every paragraph. This is a **product** result, not an
instrument result, and it must be reported to D1 **before** v46 is considered:
a page that announces six of ten is not shippable on 4b's own terms. Record
*which* paragraphs are missing and whether they are contiguous at the tail
(which looks like a mid-walk attachment loss) or scattered (which looks like a
per-paragraph gap) — the record states the pattern; it does not name a cause.
T1c may still be run on the main session's instruction, because a reproducing
instrument can compare, but the comparison's meaning changes and §8.3's clause 1
must be read as "`announced == n`, the same n, on both versions".

**O-C — the criterion is met at n ∈ {0, 1}.** A reproducibly broken instrument,
not a reproducing one (§2.4). Do not run T1c, do not report reproduction, move
to the next arm; if this is the last arm, fall through to O-D.

**O-D — no arm reached the criterion within the budget or the calendar.** The
default conclusion of §6 applies verbatim: the instrument is registered
NOT_REPRODUCIBLE on this page, v46 stays NOT_ESTABLISHED and is not landed, and
D1 falls back to freezing on v45 with the residue recorded.

**O-E — two different arms reach the criterion at different n.** The arms are
not independent and one of them changed something the other held constant.
Report the pair and the two configurations; **do not run T1c** until the main
session names one configuration. A comparison run on a configuration that is one
of two equally supported ones would carry the difference between them into the
v45/v46 result.

**O-F — five walks voided by the desktop (§6).** Stop. The report is that a
quiet window did not exist, not that the instrument failed: nothing about the
instrument was measured in those walks. 4b's mechanical half then needs a
scheduled quiet block agreed with the owner, and that scheduling is the owner's,
not the executor's.

In every outcome the executor writes
`RESULT-4b-instrument-reproduction.md` in the evidence directory carrying: the
identity gate's before/after values, the arm table with one row per walk, every
`speech.txt` payload, the outcome letter, and nothing that is a judgement about
what should ship.

---

## 6. Budget and stop rule, pre-registered — in walks, not minutes

**Budget: 20 walks**, allocated 4 (A0) + 4 (A1) + 4 (A2) + 6 (A3) = 18, plus 2
spare for a re-run the executor must justify in the record. D1 bounds the whole
pursuit at **two sonnet sessions or 2026-09-08, whichever comes first**; no walk
starts after **2026-09-08 23:59 CST**.

Counting semantics, written now so they cannot be adjusted later:

- Every walk that produces an Orca log counts against the 20, **including** a
  walk whose setting is refuted and a walk with `focusHeldEveryStop: false`.
  Those are results.
- An **identity void** (V1/V2/V6, §2.3) does not count: nothing was measured.
- An **environment void** (V5) counts, and is additionally capped: after the
  **fifth** walk voided by desktop activity or by a second Chrome, the executor
  stops the pursuit and reports outcome O-F. Four such voids are tolerated
  because the desktop is the owner's; a fifth means the quiet window did not
  exist and the honest report is that, not more walks.

**Stop rules**, in order of precedence:

- **STOP-SUCCESS.** The moment any setting's pair meets §2.2 at n ≥ 2, stop. Do
  not run the remaining arms — the question was whether the instrument can be
  made to reproduce, and it has been. Name the settled configuration (arm,
  setting, instrument sha256, start order, Orca lifecycle, tab/process
  lifecycle) and report.
- **STOP-REFUTED-EVERYWHERE.** All four arms exhausted with no pair meeting
  §2.2 at n ≥ 2 → outcome O-D.
- **STOP-BUDGET.** 20 counted walks reached → outcome O-D.
- **STOP-CALENDAR.** 2026-09-08 23:59 CST → outcome O-D.
- **STOP-DIRTY.** Five environment voids → outcome O-F.
- **STOP-IDENTITY.** The §1.3 gate fails after the last walk → nothing is
  banked as 4b evidence; report the mismatch and stop.

### Default conclusion if the budget is exhausted without reproduction

Written here, beside the criterion, as `AGENTS.md` §2 requires — so that "the
instrument never reproduced" has a decided meaning rather than waiting on a
future judgement:

> **The 4b walk instrument is registered NOT_REPRODUCIBLE on page
> `39895d15…`.** T1c is not run. **v46 stays NOT_ESTABLISHED and is not
> landed** — not because it was shown to be worse, but because no instrument
> exists that could show either. D1 falls back to its own option A fallback:
> **freeze the gate on v45**, and record the heading-boundary residue (at
> `a11y-node-2` the live region still holds the previous paragraph's text and
> Orca speaks it) under 4b's named-residue clause.
>
> The residue's registration kind, per `AGENTS.md` §3, is explicit: it is a
> **measured, open defect with nothing guarding it** — not a designed sentinel
> and not "declared but unmeasured". Its mechanism is measured (`a11y-node-2` is
> the only stop with a non-empty live region in every walk that reached it) and
> `check_4a.py`'s eight terms cannot express it, because terms 4 and 8 are about
> a paragraph *reaching* the tree and are satisfied by one channel; a duplicate
> is invisible to a criterion written about presence.
>
> 4b's mechanical half is then unmeasured by agent-driven walk on this page, and
> the owner's ear remains the only instrument — which is what the plan already
> assigns to 4b's judgement half, and what `CONSENT.md` already says an agent
> cannot do.

---

## 7. Environment, as instructions

### 7.1 Display and session

Every desktop-touching command carries `DISPLAY=:0`. The session is Wayland
(`XDG_SESSION_TYPE=wayland`, `WAYLAND_DISPLAY=wayland-0`, `loginctl … Type=wayland`)
running KDE; Chrome reaches the compositor through XWayland at `:0`, and Orca
reaches applications over AT-SPI, not over the display protocol.

**Stated as a hypothesis, not as established** (it has not been measured and
nothing in this task turns on it): KWin's focus-stealing prevention would
explain how a CDP `Page.bringToFront` can leave `document.hasFocus()` true in
the renderer while the compositor keeps input focus on the terminal — which is
the shape of the two banked n=1 walks. A0 is the arm that would show it; do not
report it as a cause on anything less.

### 7.2 Consent and an idle desktop

Consent: §1.4. The scope is the owner's words 「同意你操作桌面 session」 of
2026-09-03, re-given 2026-09-06 for page `20f09cc9…`, and to be given again for
`39895d15…` before the first walk. It covers launching a headed browser on the
owner's desktop session, starting and stopping Orca, and sending clicks and
keystrokes to that browser window. It does **not** cover condition 3's six
manual cells and it does not cover 4b's judgement half.

The owner must be told **beforehand** that a block of walks is starting and that
the desktop must be left alone for its duration — not asked afterwards whether
it was quiet. `orca-v45-focus-instrumented.log` is what the alternative looks
like: 203 utterances in the walk slice, none of them a fixture paragraph, and in
them Dolphin, Okular, a PDF in `~/Documents/公司/2026帳務/`, a course website
and 「請輸入統一編號或是公司名稱」 from a company-registry page. That walk
measured the owner's evening.

### 7.3 Starting and stopping Orca

- **Start:** `DISPLAY=:0 orca --debug-file="$D/orca-$ID.log" &`. `--debug-file`
  implies `--debug` (LEVEL_ALL) — that is why the logs are 3–16 MB. Wait for
  `Screen reader on.` in the log before proceeding.
- **`--replace`** kills every other Orca of this user with **SIGKILL**
  (`/usr/bin/orca:323-324`), so the replaced process never speaks
  `Screen reader off.` and never runs its shutdown path. Use it only where arm
  A2's setting Y calls for it.
- **Clean stop:** SIGTERM, which Orca handles at `orca/orca.py:174-175` and
  `193-194` and which makes it speak `Screen reader off.` — that utterance in
  the log is the marker that the log is complete. Never `pkill`:

```bash
for p in $(pgrep -x orca); do kill -TERM "$p"; done
while pgrep -x orca >/dev/null; do sleep 0.5; done
```

- **Never `pkill -f` or `pgrep -f`.** Those patterns match this agent's own
  command line; it happened three times on 2026-09-06 and once killed the shell
  mid-command (exit 144). Orca itself uses `pgrep -u <uid> -x orca` for the same
  reason. Where a match on the command line is genuinely needed, iterate
  `pgrep -x <name>` and read `/proc/$p/cmdline`:

```bash
for p in $(pgrep -x chrome; pgrep -x google-chrome); do
  if tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q "v12c-$ID"; then
    kill -TERM "$p"
  fi
done
```

(Both names are tried because the launcher `google-chrome` execs a binary whose
`comm` is `chrome`; confirm which one `pgrep -x` actually matches on the first
walk and record it, rather than assuming.)

### 7.4 Chrome: headed, one instance, one profile per walk

```bash
DISPLAY=:0 google-chrome \
  --remote-debugging-port=9341 --remote-allow-origins='*' \
  --force-renderer-accessibility \
  --user-data-dir="/tmp/wasm-sdk-probe-chrome-v12c-$ID" \
  --no-first-run --no-default-browser-check \
  "http://127.0.0.1:8765/e2-editor.html" &
```

Port 9341 is what `drive_walk_focus.py:22` connects to and it is not
configurable without editing the instrument, so it is fixed.

**Exactly one Chrome browser process may exist on the desktop for the duration
of a walk.** Check before each walk by iterating `pgrep -x chrome` (and
`pgrep -x google-chrome`) and reading each `/proc/$p/cmdline` for
`--user-data-dir`; the set of distinct
`--user-data-dir` values must be exactly one, the walk's. Four of the six banked
walks ran while another agent's `ODS decisive probe (diagnostic) - Google
Chrome` window was open, and Orca announced that window instead of the walk's;
a second browser is a confound, not background noise. If one is found, wait or
ask — do not kill another agent's browser.

### 7.5 Detecting a walk that measured something else

After every walk, list the slice's speech lines:

```bash
sed 's/ {.*//' "$D/orca-$ID.speech.txt"
```

All of them go into the record verbatim. Every line must be attributable to the
candidate page or to Orca's own vocabulary. Expected page and Orca strings seen
in a good walk: the ten paragraph texts, `文件內容`, `heading 1`, `heading 2`,
`List with 2 items`, `leaving list.`, `Browse mode`, `Focus mode`, `輸入`,
`entry.`, `尚未開啟文件。`, `Screen reader on.`, `Screen reader off.`,
`LiteCore 編輯器 — 產品 v2（十五個動作） - Google Chrome`, `frame`, `document web`,
`page tab.`.

**Any line naming another application voids the walk (V5).** Seen in the banked
logs, as concrete examples: `study_LiteCore : claude — Konsole`,
`study_OxODF : claude`, `ODS decisive probe (diagnostic) - Google Chrome`,
`0506 — Dolphin`, `… — Okular`, `中小企業網路大學校 - 課程`,
`請輸入統一編號或是公司名稱`, `layered pane 0 items`, `split pane.`, `書籤(B)`.

This list is a hand enumeration — `AGENTS.md` §1's third form — so it is used
only in the **voiding** direction and never as a passing criterion. The passing
side is the count of §2.1, which is generated from the walk's own rows. A line
the executor cannot attribute is treated as foreign and voids the walk; if the
executor believes such a line is benign, it says so in the record with its
reason rather than deleting it.

### 7.6 Cleaning up after every walk

```bash
rm -rf "/tmp/wasm-sdk-probe-chrome-v12c-$ID"
```

and, when the candidate server is stopped, remove its scratch mirror: it is a
`candidate-round-*` directory created by `tempfile.mkdtemp` in
`serve_candidate_page.py`. Also sweep any `aria-baseline-*` left by earlier
probes. On 2026-09-06 roughly 700 MB of these had accumulated, one per run, and
`/tmp` is a 16 GB tmpfs — it hit 98%, two runs were killed for low memory and a
`git commit` failed with ENOSPC. Check `df -h /tmp` at the start of the session
and again halfway through. Never write an Orca log under `/tmp`.

---

## 8. Appendix, conditional — T1c: v45 against v46

**This section runs only if §6's STOP-SUCCESS fired at n ≥ 2, and only after the
main session says to proceed.** If the criterion was not met, T1c does not
happen and the default conclusion of §6 stands.

### 8.1 v46 is not in the tree, and the executor does not invent it

v46 was built, walked once, and **reverted uncommitted**; nothing of it exists in
git. The description on file is that it changed `projectFocusedParagraph`'s test
from *"do the two channels agree"* to *"does the structure channel have a focused
node"* — that is, silence the live region whenever `#a11y-structure` has a
focused node at all, rather than only when the two channels carry the same text.

The executor must **obtain the edit from the previous session's description**,
not reconstruct it from that sentence. If what is available does not determine
the exact edit, **stop and report**: guessing the diff and then measuring it
would produce a verdict about a page nobody wrote, and §8 of `AGENTS.md` exists
because a terminating declaration must not rest on the drafting party's memory.
`AGENTS.md` §11 records that the drafting party supplied a false premise to an
outsourced task once already.

### 8.2 A v46 page is a different page and a different generation

`projectFocusedParagraph` lives in `web/e2-editor-app.js`, one of the thirteen
paths the shell bundle binds and the source of the candidate page itself.
Therefore:

- a v46 page has a **different `pageSha256`**, so §1.3's V1 pins that value, not
  `39895d15…`;
- landing v46 requires a **new frozen generation (v47) in the same commit as the
  change** — ruling E-1's rule, which v43 paid for;
- v46's walks go in **their own directory**,
  `findings/evidence/manual-round-v12d-<first 8 of the v46 page sha>/`, with
  their own `CONSENT.md` naming that page. They are not banked beside the v45
  walks, for the same reason the v12b directory is not reused here.

### 8.3 What "v46 measures better" means, in log terms, before it is run

The residue this comparison is about is at the **second heading**: the live
region still holds the previous paragraph's text and Orca speaks it. In the
bounded walk slice of a v45 walk it appears as a `SPEECH OUTPUT` line whose text
is `這一行是普通內文` occurring **after** the `這一行應該被唸成第二層標題` /
`heading 2` pair and before the next stop's paragraph — i.e. the per-paragraph
utterance count of §2.1 shows `這一行是普通內文` at **2** while every other
paragraph is at 1, in a walk whose `announced` is 10. That is the exact shape of
`orca-AFTER-THE-FIX-slow-dwell.log` when bounded at both ends (§4.3).

**v46 measures better iff, on the settled configuration and with the criterion
of §2.2 met on both versions:**

1. `announced == 10` on v46 — every paragraph still reaches the log; **and**
2. the per-paragraph utterance count on v46 is 1 for **every** paragraph,
   including `這一行是普通內文`; **and**
3. the same v45 pair, run in the same session, still shows `這一行是普通內文` at
   2.

Clause 1 is not optional: a version that removes the stale utterance by removing
all utterances is the v46 hypothesis this task exists to distinguish from an
attachment failure. Clause 3 is a **return control**, and it is what the
2026-09-06 comparison lacked — its control died at paragraph 4.

### 8.4 T1c's own budget

Eight walks, separate from §6's twenty: a v45 pair, a v46 pair, a v45 return
pair, and two spare. Same stop rules, same voids, same records. If the v45
return pair does not reproduce the first v45 pair's n, the session drifted and
the comparison is void — report that rather than the difference.

---

## Execution record
