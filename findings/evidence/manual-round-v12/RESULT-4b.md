# 4b: the text reaches the screen reader; the structure does not

Agent-driven under the owner's consent recorded in `CONSENT.md`, 2026-09-03, on
the candidate page `3dfdcfef…` served from a headed Chrome on the owner's own
desktop session with `--force-renderer-accessibility`. Orca's speech captured to
`orca-speech-3-agent.log` (15,216,073 bytes). The walk that produced it is
`4b-agent-walk.json`: nine paragraphs, each reached by clicking its own ink,
each verified in the page's own projection before moving on.

## Term 1 — the words of the focused paragraphs reach the log: **8 of 9**

| paragraph | spoken |
|---|---|
| `E1-LC-HEADING` | ✅ (twice) |
| `E1-LC-ISOLATED 前後都不是清單的段落` | ✅ |
| `E1-LC-SPACER` | ✅ |
| `• E1-LC-BULLET-ONE` | ✅ |
| `• E1-LC-BULLET-TWO 中文項目` | ✅ |
| `E1-LC-BETWEEN` | ✅ |
| `1. E1-LC-NUMBER-ONE` | ✅ |
| `2. E1-LC-NUMBER-TWO` | ❌ |
| `E1-LC-END` | ✅ |

The caret **did** reach `E1-LC-NUMBER-TWO` — `4b-agent-walk.json` records it at
`y=0.280` with the page's own projection reading `2. E1-LC-NUMBER-TWO`. Orca did
not speak it: the log shows focus moving to the terminal one line after
`1. E1-LC-NUMBER-ONE`. **Attributed to focus leaving the browser, not to the
projection** — and that attribution is a reading of the log, so a re-run that
holds focus is what would settle it.

## Term 2 — the heading announced as a heading with its level: **NO**

`E1-LC-HEADING` was spoken twice, both times as bare text:

```
18:15:41.151744 - SPEECH OUTPUT: 'E1-LC-HEADING'
18:16:45.450255 - SPEECH OUTPUT: 'E1-LC-HEADING'
```

**No role and no level, anywhere in the log.** Searching every `SPEECH OUTPUT`
line for `heading`, `標題`, `level` or `層級` returns those two lines and
nothing else.

### Why, in the page's own source

There are two projections and they carry different things:

| | carries | announced when |
|---|---|---|
| `#a11y-structure` | `role="heading"` + `aria-level`, `role="list"`, `role="listitem"` | only when an AT **browses** the region |
| `#a11y-para` — `aria-live="polite"` | `textContent` **only** | every time the caret moves |

`projectFocusedParagraph()` assigns `el.a11yPara.textContent` and nothing else.
So caret movement — the thing a person editing a document does constantly —
announces text with no structure at all.

**4a is not contradicted.** The tree really does carry the heading at
`level: 1`, and 4a measured that correctly through `Accessibility.getFullAXTree`.
**4b measures a different link**: what one AT actually says when focus moves.
That the two disagree is exactly why the plan split them, and it is the first
time the split has paid.

## The double announcement, heard as predicted

`• E1-LC-BULLET-ONE` and `• E1-LC-BULLET-TWO 中文項目` were spoken with the
bullet character **inside the text**, from a live region that carries no
`listitem` role. So on this path the marker is spoken once, not twice — the
double announcement `queue-list-prefix-read-twice` describes needs the role,
and the live region does not have it. **The defect measured in the AX tree this
morning is not the defect a caret-moving user meets; they meet the opposite
one — a bullet with no list.** Both are recorded; neither was predicted
correctly by the other.

## What is NOT concluded here

Whether term 2's failure blocks the cutover. The criterion's gating half names
both requirements, and its "blocks until root-caused" sentence names only the
text case. **That ambiguity is in the criterion, not in the measurement**, and
the drafting party deciding it in their own favour is the failure mode
`AGENTS.md` §2 exists to stop. Sent for adjudication.

The judgement half — announcement order, verbosity, browse-mode behaviour —
remains the owner's and is not recorded here beyond their two remarks during the
round: 「他一直在念文件標題」 (the window title, repeatedly, whenever focus
returned to Chrome) and 「有啦有念到內文了」.

---

## Correction, same day: two numbers in this file were wrong, and why

**The log is 15,216,073 bytes, not 10 MB.** Quoted from memory of a `ls` rather
than re-read.

**The transcript first handed to the owner had 283 speech lines; the analysed
log has 174.** The transcript was generated from the working-tree file *after*
it had been committed — and Orca was still running, still appending, still
reading the terminal aloud. The file grew by 42 MB between the analysis and the
transcript.

So the transcript described a longer session than the one every conclusion in
this file rests on. Both transcripts have been regenerated from the **committed**
bytes; the post-walk growth is kept, unedited, as
`orca-speech-3-continued-after-the-walk.log`.

**The lesson is not "check file sizes".** It is that **evidence keeps growing
while the process that writes it is alive**, and banking it does not stop that.
Every number in this file was re-derived from the committed bytes after the
correction: `E1-LC-HEADING` spoken twice, `E1-LC-NUMBER-TWO` zero times, and
exactly two `SPEECH OUTPUT` lines matching `heading|標題|level|層級` — both of
them the bare-text heading lines. The conclusions are unchanged; the numbers
that describe the corpus they came from were not.
