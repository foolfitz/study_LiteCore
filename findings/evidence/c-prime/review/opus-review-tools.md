# opus review of the six C′ tools (subagent, read-only, 2026-10-11; prompt: review-prompt-tools.md)

Hashes reviewed: judge_c2 63c9953d, compare cb6c3df1 + red_cases a7b4179c, importers e5dd92ea, c6 7a31fba6,
124/125 488e10cc, C3/C4 c8bd2bf4 (= f9842ce5~1); C′ page at 57d21411, the 125 page at bbdde806.
B1–B4 are the defects codex also found (fixed in f9842ce5); the rest is new or still open at that HEAD.

BLOCKING
- B1 probe_c_prime_window.py:83 matches operation "render"; DocumentHandle.render() posts "paint" (sdk/document-sdk.js:398-399). Nothing is tagged, so C3 and every C4 cell FAIL on a correct C′ page, and both §17.9 (c) red cases go "red" for the same reason. With "paint" the tagging is sound (Worker built after the inline shim; the page's only `new ImageData` is e2-editor-app.js:1114).
- B2 C4: nothing ties the judged window to the scrolled-to position and sinceMs has no lower bound; the page moves its window only in a passive scroll listener (fires at the next rendering update). A READ before it sees the old, current window and passes with a negative sinceMs; the prefetch can fold 0.5 -> 1.0 -> 0 into one scroll event. A page whose window never moves also passes. (Frequency a hypothesis; the code path certain.)
- B3 The 124/125 probe implements §17.4's 125-B, which §17.9 (d) replaced: on bbdde806 #state-pill is the visible parent, never hidden; its observed textContent is the shown, delayed word, so the positive control fails. A correct page FAILs twice over.
- B4 judge_c2.py: a --browsers or --slots override still prints "PASS: both browsers, every cell"; --slots prints no OVERRIDE line.

NON-BLOCKING
- N1 Nothing reads C2's second half (ratio-1 P2 cells) on a C′ page: judge_p2.py:35 pins the P page; re-pinning is a step to name. judge_c2 binds the requested ratio, not the achieved one (low risk).
- N2 compare.py records no provenance (servedShell.entrypointSha256, candidateSource, M3 runnerSha256); --cand-runner optional and reads chain.log not the reports; no page check; the --m3 list is hand-typed, not checked against importers.py; no P1 (complete/liveness/pageErrors) check.
- N3 None of the six reads C5 (ii); §17.10's caret-ignores-x rule is encoded nowhere.
- N4 importers.py considers only the chain's runners (install_elsewhere, skeleton_open, gate0_report also reach page smoke); fine for C5 (i). git diff BASE includes uncommitted edits (over-includes, safe); subprocess calls invisible to ast.
- N5 probe_c6 computes no verdict; fix the threshold before the C′ run (controls 66k-155k dark, blanks 0): last-page and top dark above a fixed N, no 重繪失敗, a report present.
- N6 (a) C3 also requires no listed band outside the window (stricter; harmless). (b) The bold arm has no positive control that the document changed; gate on data-changes advancing >= 2 across the click. (c) The bold arm's whole-window time counts from the last ArrowLeft (recorded only).
- N7 The wheel segment never ran on a following page; afterWheel read could race smooth scrolling (false FAIL only, hypothesis). Batched data-state writes in one observer callback are logged as the final value; use oldValue.

Checked, no defect: bands_of = renderBands; data-window published before any draw at the new place; data-changes published at both increments and read synchronously by the shim; the 6,000-entry cap; page-clock C4 times; compare's §23 and row 1′; judge_c2's strict comparisons and runner string; the four registered items.

C (red cases): judge_c2 none for every-key committed/on screen, gap 200, Firefox on-screen, overrides; compare none for row 1′, ids-differ, a key missing from an M3 score; 124/125 the wheel, pulled-back, first-letter, shown-busy and every (d) branch unexercised; C3/C4 none run -- §17.5's C3 red case ("blitted only at the end of a pass") cannot turn this probe red (end state after >= 1.5 s quiet): rule it out or add a time bound; never-stale-outside catches only if the mutant keeps off-window bands and the prefetch really visits 0.5 and 1.0; label-at-reply reliable only in the bold arm, and only if the bold changes the document.
