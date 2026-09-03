# Consent to agent-driven keystrokes for 4b

Gate condition 4b (`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`,
addendum A-1) names this route explicitly:

> The escape, named. If the owner cannot or will not operate Orca at the manual
> round, that is recorded and 4b converts to a deferred obligation: one Orca
> session on the live page before the institutional-buyer demonstration —
> owner-run, **or agent-driven with the owner's explicit consent to an agent
> driving their desktop session, since the log-based mechanical checks are
> equally valid however the keystrokes were produced.**

**The owner's words, 2026-09-03, verbatim:** 「同意你操作桌面 session」

## What this consent covers, and what it does not

**Covers**: launching a headed browser on the owner's desktop session
(`DISPLAY=:0`, Wayland), starting and stopping Orca, and sending clicks and
keystrokes to that browser window so the caret walks the fixture's paragraphs.

**Does not cover, and is not claimed**: the judgement half of 4b. The plan
assigns that to human observation and says so — *"a criterion satisfied by human
judgement, and it is created knowingly"*. Announcement order, verbosity and
browse-mode behaviour remain the owner's to report; an agent has no ears.

**Why it was asked for at all**: the owner's two hand-driven attempts produced
logs in which the document's content never appeared (`orca-speech.log`) and then
appeared once (`orca-speech-2.log`, `E1-LC-ISOLATED` spoken twice with the
product's own 「無障礙資訊目前不可用。」 between them), because focus moved
between the browser and the terminal. Agent-driven keystrokes make the walk
deterministic and repeatable; both hand-driven logs are kept, because they are
what the round actually looked like for a person.
