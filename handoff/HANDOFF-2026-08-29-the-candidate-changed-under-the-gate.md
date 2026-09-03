# Handoff: the candidate changed under the gate

Written 2026-08-29. Continues
[`HANDOFF-2026-08-28-instruments-that-hid-what-they-were-built-to-find.md`](HANDOFF-2026-08-28-instruments-that-hid-what-they-were-built-to-find.md).

**In one line.** The cost figure the cutover was waiting on turned out to be
**65% packaging**, so the candidate is no longer `e2-editor-v11` but a split
profile `e2-editor-v12` at **+24.5 MiB instead of +71.4** — and getting there
cost one struck criterion, one new finding, and four corrections to gate
documents, three of which were errors this session wrote itself.

## State

`e2-editor-v8` still ships. `web/e2-editor-app.js` and `dist/e2-editor-app.js`
both hash `28e03e5bc9fcb8c4` — the baseline. **Nothing was pushed**; 27 commits
are local and the working tree carries the day's uncommitted work.

| | |
|---|---|
| candidate | **`e2-editor-v12`**, page sha `3dfdcfef4abfe6b7…` |
| v12 soak | **4 of 12**, all 2026-08-29, all 38 PASS / 2 NE, all on the same page sha |
| gate condition 4a | **discharged, 7 of 7 terms** |
| criterion 3′-iii | **measured**, and the owner has ruled on it |
| D-2 (the archive) | **discharged** |
| B-2 split probe | **VERIFIED** |
| new finding | **085** |

## 1. The cost was 65% packaging, and that changed the candidate

The plan said v11's core image is "three times v8's — that is the writer+calc
core the ruling accepted". Measured by comparing file manifests (1,606 entries
against 1,358): v11's image is a **strict superset** of the product core's; the
248 extra files are **Calc UI configuration, 5.5 MiB**; and
`base-r5 + cjk-r5 + fallback-fonts-r5 = full-qa-r5` **to the byte**.

So +71.4 MiB decomposes as **+19.0 loader/wasm, +5.5 Calc config, +46.8
fallback fonts no longer split out**. The writer+calc core costs 5.5 MiB in the
data image, not +70.9.

`build_r5_profiles.create_pack()` slices a pack out of an existing
`soffice.data` by byte ranges from its metadata — post-processing, no relink.
An adjudication ordered a **bounded probe**: attempt the split in parallel with
the soak, hard bound 2026-08-30, verdict rule fixed in advance.

**All criteria passed inside the bound**, and `e2-editor-v12` is now the
candidate. Its five bound identities, build provenance (direct invocation, the
Makefile deliberately untouched per finding 042) and the full re-earn list are
in the plan's 2026-08-29 amendment.

**The soak count restarted at zero.** Five clean v11 runs are void for the count
and retained in place as incumbent-lineage evidence.

## 2. Finding 085 — `loadAtStartup: false` means never loaded

Found by checking the *premise* of a criterion, not by running it.

`loadResourcePack()` has exactly one caller, guarded on `loadAtStartup === true`,
called once from `handleInit`. Census over **26 workers**, live and archived
back to `e2-editor-v2` including v8's own: all with exactly two occurrences,
zero callers outside the worker across 100 files.

So v8's 46.8 MiB fallback-font pack is declared and **has never been fetched by
the editor**. The plan's word was "on demand"; the behaviour is absence.

Consequences: the arithmetic was unaffected (161.4 is right *because* the pack
is not fetched), but **criterion 3 was unsatisfiable on every profile including
the incumbent** — a criterion the incumbent cannot clear is not measuring the
candidate. It was **struck and replaced by 3′**, not patched.

## 3. What 3′-iii measured, and the owner's ruling

A fixture requiring fallback-only fonts (family `Amiri`, chosen from the pack's
own metadata), opened on all three profiles:

| | canvas PNG sha256 |
|---|---|
| `e2-editor-v8` | `5d78ff2e559d826e…` |
| `e2-editor-v12` | **`5d78ff2e559d826e…`** |
| `e2-editor-v11` | `f16d4770de2af000…` |

**v8 and v12 render this document to byte-identical pixels.** Arabic renders as
missing-glyph boxes on both — as it does on the product today — and correctly on
unsplit v11. **Hebrew renders on all three**: the loss is Arabic alone, not
"complex scripts".

**The owner ruled 2026-08-29: Arabic is not in scope.** So the fallback pack
stays `loadAtStartup: false`, the confirmation figure is **+24.5 MiB (+15.2%)**,
and the record's font sentence is a measured statement rather than the
"unmeasured, option preserved" fallback. Enabling the fonts later is one
manifest field plus its own gate; the pack is banked and byte-identical.

## 4. Gate condition 4a, discharged

Condition 4 as written had **no pass criterion** — it said to record what a
screen reader announced, so the verdict fell to whoever was in the room. It was
split into 4a (machine-checkable, blocking) and 4b (folded into the human manual
round; mechanical half gates, judgement half records; escape named).

Precondition first: `probe_aria_projection.py` became the **fourth caller** of
`repointed_page()`. It never used `gate_mirror()`'s injected reader, so the
candidate path carries **no shim at all** and its `pageSha256` is comparable
with the soak reports'.

All seven terms pass. On the page that will ship, an AT is handed the document's
**9 of 9 paragraphs**, the heading at AX `level: 1` matching the ODT, **2 `list`
containers and 4 `listitem`**, and focus following the caret (3 placements, 3
distinct readings, all 3 matching what they aimed at) — three runs, one distinct
signature. The v8 control: `documentTextInTree: false` and the region saying
honestly why it is empty.

Term 6: `--mutate projection-not-wired` moved **exactly one** check,
`the-document-region-says-why-it-is-empty`, observing `{present: true,
text: ""}`. Page restored to `28e03e5bc9fcb8c4`.

`check_4a.py` is a separate tool from the probe — the probe reports, the judge
judges — and it has **four red cases covering all six judged terms**.

## 5. The instruments, again — this is still the part worth reading

**A criterion can rest on a premise nobody checked.** Criterion 3's second half
tested a property no profile has ever had. The premise came from this side: the
ticket and the addendum both said v8 "defers to on demand", copied from the
plan's table without checking it.

**Insisting on the reading rather than the derivation paid, but not the way it
looks.** An adjudication refused a derived font inventory and demanded a
`Module.FS` read. The two agreed exactly. The value was elsewhere: the first
reader unwrapped the CDP envelope one level too deep and reported "the worker
did not answer with a string" **while printing the worker's correct answer
inside the error**. A tidy one-line error would have sent me back to the
derivation, claiming the direct read was unavailable. *Errors should carry the
payload, not a summary of it.*

**I was wrong about one of the two standing NEs**, and the correction came from
an adjudicator reading the runner. `notice-action-recovers-the-session` is a
designed sentinel whose capability is driven in every plain run;
`a-refused-action-is-reported-and-changes-nothing` is diagnostic-only by
construction. Calling them one thing said both wrong.

**I doubted a correct correction.** Told the 130th font file was at
`/instdir/program/resource/common/fonts/`, I believed it wrong because I had
seen `opens___.ttf` under `/instdir/share/fonts/truetype/`. There are **two
copies**. The bridge is now written where the two published counts meet.

**An instrument I designed had no discriminating power** — the ink-band
statistic collapsed to one band on all three profiles because the page border
inks every row. The PNG comparison carried 3′-iii; the band numbers are recorded
and unused.

## 6. Corrections landed, append-only

Four, three of them this session's own errors: "on demand" (never loaded),
"three times the core image" (writer+calc is 5.5 MiB), "twelve profiles"
(**34** reference all three data files; 35 reference `../resources/`), and the
130-vs-129 font count bridge.

## 7. `AGENTS.md` gained a section

**Acceptance-criterion forms**, adapted from the neighbouring tree's ADR
convergence note — which explicitly disclaims extrapolation, so only the rules
that actually bit here were kept, each with this tree's own instance. Eleven
short rules; the ones that earned their place today are §1 (the three forms and
the injection test), §2 (no criterion resolved by a future judgement), §3 (two
kinds of registration), §4 (withdraw the claim, don't build machinery), §6 (a
green checker is not evidence), §8 (termination must not rest on the drafting
party), and §9 (how a running gate may gain criteria).

## What is left, in order

1. **Eight more clean runs on v12**, across ≥3 calendar days from 2026-08-29,
   ≥2 per day. Four are banked, all on 08-29.
2. **Three diagnostic runs** at `--caret-rounds 12`, `staleWritesRefusedTotal > 0`
   in at least one.
3. **The revert rehearsal with v12's hashes, including step 3** — the
   freeze-and-repoint, which has still never been rehearsed.
4. **The ODT round-trip**, both directions, on v12.
5. **The human manual round with 4b folded in.** Needs the user.
   `/usr/bin/orca` is installed on this machine.
6. **W-3**: four inline-format checks carry no mutation
   (`a-format-that-worked-is-not-reported-as-failed`,
   `every-inline-format-reaches-the-document`,
   `clear-format-removes-every-inline-format`,
   `formatting-survives-the-next-paragraph-break`). Page-modifying — must not
   overlap a soak run.
7. **W-4**: a soak aggregator, so "the gate is open" is checkable by someone who
   was not here. Define the calendar-day boundary in it: the report's completion
   timestamp. A v11-lineage run started 23:54 and finished 00:01.
8. **D-1's record sentences** R1 and R2. R2's facts are gathered: the refusal
   check PASSED exactly once in 146 product-path reports
   (`queue-cut-refusal-lost-its-inducer/product-path-refusal-diagnostic.json`,
   2026-08-26) with a deliberately mutated companion that FAILs.
9. **The owner's confirmation** against +24.5 MiB (+15.2%).
10. **27 unpushed commits**, plus this day's uncommitted work.

## The push

Nothing has been pushed. `git log --oneline github/main..HEAD` is 27, and the
working tree has the day's changes uncommitted.
