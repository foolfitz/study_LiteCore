# 4b on `20f09cc9…`: the mechanical half passes 10/10, and the owner heard the 088 residue

**2026-09-06.** Agent-driven keystrokes under `CONSENT.md`; the listening is the
owner's. Candidate page served by `serve_candidate_page.py --expect-sha256
20f09cc9…`, and the served bytes were fetched over HTTP and hashed rather than
taken from the tool's claim. Fixture: **`a11y-audible`** — the fixture whose
every line states what it should be announced as, chosen by the owner. Headed
Chrome on the owner's own desktop session with
`--force-renderer-accessibility`. Orca speech: `orca-a11y-audible.log`
(12,005,821 bytes); the walk's portion begins at byte 4,730,673 and is banked
separately as `orca-a11y-audible-WALK-SLICE.log`. Walk:
`4b-walk-a11y-audible.json`, 10 paragraphs, 9 ArrowDown presses.

## Mechanical half — gating: **passes**

**Every focused paragraph's words reached the log: 10 of 10.** (The 2026-09-03
round on `list-contexts` was 8 of 9.)

**The headings are announced as headings, with their levels, on the caret path:**

```
22:53:54.717  '這一行應該被唸成第一層標題'
22:53:54.718  'heading 1'
22:54:10.770  '這一行應該被唸成第二層標題'
22:54:10.771  'heading 2'
```

That is finding 087's fix, heard. The 2026-09-03 round found **no role and no
level anywhere in the log**; this one has both levels, on the paragraphs the
fixture says should carry them.

Lists: `List with 2 items` on entering each of the two lists and `leaving list`
on leaving, once per list rather than once per item.

## Judgement half — the owner's, and it found something

**The owner, listening, reported: 「有些內文行好像重複唸了」.**

The log corroborates it exactly, and the walk's own record gives the mechanism.
Every non-heading paragraph is spoken **twice, ~117 ms apart, as two separate
utterances** — the first carrying a trailing `.` and a language family, the
second bare:

| paragraph | first | second | gap |
|---|---|---|---|
| 這一行是普通內文 | 22:54:04.971 | 22:54:05.088 | 117 ms |
| 那一行也是內文… | 22:54:16.579 | 22:54:16.693 | 114 ms |
| • 清單開始了… | 22:54:22.390 | 22:54:22.503 | 113 ms |
| • 接下來… | 22:54:28.193 | 22:54:28.312 | 119 ms |
| 夾在中間的… | 22:54:34.005 | 22:54:34.123 | 118 ms |
| 1. 編號的部分… | 22:54:39.817 | 22:54:39.934 | 117 ms |
| 2. 再來這一項… | 22:54:45.616 | 22:54:45.734 | 118 ms |
| 最後一行到了… | 22:54:51.421 | 22:54:51.538 | 117 ms |

**The two headings are spoken once.** And the walk records why — the live region
`#a11y-para` at each stop:

| caret on | `#a11y-para` holds | spoken |
|---|---|---|
| heading 1 | **empty** | once |
| heading 2 | **stale** — still the previous body line | once |
| the other 8 | **the same text as the focused node** | **twice** |

The correlation is 10 of 10 with no exception: **where two channels carry the
same text, the paragraph is spoken twice; where the live region is empty or
stale, once.** That is finding 088's residue — *"兩條路同時說話"* — measured on
the shipping candidate, with the owner's ear as the instrument that noticed it
and the log as the instrument that named it.

## Why this was not caught by 4a

4a term 4 asks whether the caret's paragraph *reaches* the accessibility tree,
and term 8 whether the focused node carries the fixture's role. Both are
satisfied by one channel. **Neither term can express "and only one channel
spoke"** — a duplicate is invisible to a criterion written about presence.

## What is already known about the fix

The fix — empty the live region when `aria-activedescendant` already points at a
node carrying the same text — **exists and was reverted**, because it turned 4a
terms 4 and 8 red. Both of those reds were the instrument, which the adjudication
of 2026-09-05 corrected; replayed against the corrected judge on 2026-09-06 the
same held record passes all eight terms
(`findings/evidence/088/replay_the_reverted_fix.py`).

**Landing it moves `web/e2-editor-app.js`, so `pageSha256` moves, and the ten
banked soak runs are void.** That is the whole of the cost and it is not the
drafting party's to weigh.
