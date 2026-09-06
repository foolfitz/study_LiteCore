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

---

# The fix, the owner's second finding, and one attempt that is NOT established

## The fix works: 18 utterances became 10

Landed as v45 (`94edc4d9`, page `39895d15…`), re-walked, counted per paragraph:

| paragraph | before | after |
|---|---:|---:|
| 第一層標題 | 1 | 1 |
| 這一行是普通內文 | **2** | **1** |
| 第二層標題 | 1 | 1 |
| 那一行也是內文… | **2** | **1** |
| • 清單第一項 | **2** | **1** |
| • 清單第二項 | **2** | **1** |
| 夾在中間的… | **2** | **1** |
| 1. 編號第一項 | **2** | **1** |
| 2. 編號第二項 | **2** | **1** |
| 最後一行 | **2** | **1** |
| **total** | **18** | **10** |

`heading 1` and `heading 2` still announced; `List with 2 items` on entering
each list and `leaving list` on leaving, once per list. **The owner confirmed by
ear: 「內文重複部份正常了」.** Evidence: `orca-AFTER-THE-FIX.log`,
`4b-walk-after-fix.json`.

## The owner's second finding was the instrument, and the instrument said so

> 「兩種清單，第一項還沒唸完好像就開始第二項了？」

The log gave the answer without another product change. Gaps between
announcements were a constant **5.80–5.82 s** — `drive_arrow_walk.py`'s
`time.sleep(5)`. And a list is the only place where **two** utterances are
queued in the same instant:

```
23:06:46.782  List with 2 items
23:06:46.782  • 清單開始了 這裡應該被唸成項目清單的第一項.
23:06:52.583  • 接下來這一項應該被唸成項目清單的第二項.
```

The container announcement plus ~20 Chinese characters does not fit in 5.8 s;
everywhere else only one utterance shares the window. **Re-walked at an
11-second dwell** (`drive_walk_slow.py`, the one-line variant): gaps 11.8 s, both
lists' first items complete, and the owner confirmed 「感覺正常了」.
`orca-AFTER-THE-FIX-slow-dwell.log`.

So the truncation was **the harness's pacing, not the product** — this tree's
own recurring lesson, this time with the harness making the product sound worse
than it is.

## One residual, found in the slow log

At the **second heading** the live region still held the *previous* paragraph's
text and Orca spoke it:

```
23:10:32  這一行應該被唸成第二層標題
23:10:32  heading 2
23:10:32  這一行是普通內文        <- the paragraph before it
```

Counted over the slow walk: 8 of 10 paragraphs exactly once,
`這一行是普通內文` **twice**. The walk records the cause: `a11y-node-2` is the
only stop in the whole walk where `#a11y-para` is non-empty. The two channels
are fed by different engine fields (`caretParagraph`, `documentOutline`) and do
not advance together across a heading boundary; v45 silences the live region
only when the two **agree**, so a one-snapshot disagreement is let out loud, and
what it says is the older of the two.

## The attempt to fix it, and why it is NOT established

Tried: silence the live region whenever the structure channel has a focused node
at all, rather than when the texts match. Built as v46 (`df5f3b6c`, page
`9b29e39b…`). The walk on it produced **no document speech at all** — 12
utterances after Orca attached, none of them a paragraph.

The page itself was in the intended state, read live over CDP:
`liveText: ""`, `deferredToStructure: "1"`, `activedescendant: a11y-node-9`,
`activeElement: sink`, structure projected with 10 paragraphs. So the code did
what it was written to do.

**v46 was reverted, uncommitted; nothing shipped.** But the reason it was
reverted is weaker than it looked, and saying so is the point of this section:

**The control does not establish it.** After reverting, the same walk on v45
announced 4 paragraphs — 第一層標題, 這一行是普通內文, 第二層標題 + `heading 2`,
那一行也是內文 — each exactly once, and then at 23:21:58 Orca announced
`study_LiteCore : claude — Konsole`: **window focus moved to the terminal
driving the walk**, and the remaining six paragraphs were driven into a window
that no longer had it. That is the exact confound `CONSENT.md` records from the
owner's own hand-driven attempts.

So of the two runs being compared, one is silent and the other is cut off at
paragraph 4 — **and both sessions lost focus to the terminal.** "v46 makes the
product silent for a screen reader" is a hypothesis with one run behind it and a
control that did not survive long enough to refute it.

**What is registered, then:**

* v45 is the shipping state, and it is the state the owner confirmed by ear.
* The heading-boundary residual is **open**, with its mechanism measured
  (`a11y-node-2` is the only non-empty live region across three walks).
* Whether v46's rule causes silence is **NOT ESTABLISHED**. Settling it needs a
  walk in which the browser keeps focus for all ten paragraphs — which no run
  tonight achieved on either version.

---

# v46 could not be settled, because the instrument stopped being reproducible

Asked to finish v46, I built the missing instrument first and it disqualified
the comparison — including the runs I had been about to compare.

## The instrument: `document.hasFocus()` at every stop

`drive_walk_focus.py` records `hasFocus` per stop and reports
`focusHeldEveryStop` / `stopsWithoutFocus`. It exists because two walks were
compared earlier tonight and **both had lost window focus**, one silently at
paragraph 4; nothing in either record said so, and it had to be read out of Orca
announcing the terminal's window title.

It earned itself immediately. Its first run: `focusHeldEveryStop: false`, and
the Orca log contains 「請輸入統一編號或是公司名稱」 and 「查詢結果清單」 —
**a company-registry page in a different window**. The keystrokes reached the
right tab, because CDP does not need OS focus; a screen reader follows the
focused *window*, so that log was about another application entirely. Any walk
without this field is a walk that cannot say which window it measured.

## Six walks tonight, on identical v45 code

| walk | `focusHeldEveryStop` | paragraphs announced |
|---|---|---|
| 5 s dwell, the fix landing | not recorded | **10** |
| 11 s dwell | not recorded | **10** |
| control after reverting v46 | not recorded | 4, then focus lost |
| `hasFocus` instrumented | **false** | 0 — Orca was on another window |
| window raised before every press | **true** | **1** |
| window raised once at the start | **true** | **1** |

**The same page bytes produced 10 announcements and then 1, with focus held by
the page's own reading in the 1 case.** Raising the window before every press
was tried and is worse, not better — the repeated activation is itself an event
and it suppressed what it was added to protect; that was reverted to a single
raise, which changed nothing.

## What this means for v46

**v46's verdict stays NOT_ESTABLISHED, and now for a stronger reason.** The
earlier reason was one silent run against a control that died at paragraph 4.
The reason now is that **the measurement does not reproduce on unchanged code**:
a method that gives 10 and then 1 on the same bytes cannot distinguish v45 from
v46, and a difference measured with it would be indistinguishable from this
variance.

v46 is reverted and was never committed. v45 is what ships, and v45 is what the
owner confirmed by ear — 「內文重複部份正常了」 — in the two runs that announced
all ten paragraphs.

## What the next session needs, named

1. **A walk that reproduces.** Until the same bytes give the same count twice in
   a row, no 4b comparison means anything. The variables not yet separated:
   whether Orca must be started before Chrome; whether repeated `orca --replace`
   cycles degrade its AT-SPI attachment; whether a tab that has already been
   walked projects differently on the second pass.
2. **Then** v45 against v46, both with `focusHeldEveryStop: true` and a
   reproducible count.
3. The heading-boundary residual stays open either way: `a11y-node-2` is the
   only stop with a non-empty live region in every walk that reached it.

Stopped rather than continuing to tune a method whose failures I was still
discovering. The four things established tonight — the fix works, the list
truncation was the harness, the residual exists, the instrument is unreliable —
are worth more than a sixth attempt at 23:40.
