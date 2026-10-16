# v21 WASM shakedown: the arms (index), written before any run

Spec: `specs/SPEC-M3-link-batch-v21.md` §11 (pinned at `523871fa`), §12.1, and §12.2, which is appended in the same commit as this file. Handoff: `handoff/HANDOFF-2026-10-16b-v21-linked-shakedown-next.md`, Next 1. Task: `handoff/tasks/TASK-2026-10-16c-v21-shakedown-arms.md`.

- **`ARMS-item1.md`**: item 1 (Ctrl+Home/End), D1–D13 and the record arms. Drafted by Agent D. The main session's rulings are in its §8.
- **`ARMS-item2.md`**: item 2 (paste as Markdown), M0–M11 and the record arm. Drafted by Agent M. The main session's rulings are in its §9.
- **This file**: the rules both items share, the shared instruments, and the order of work.

These three files are committed before the first browser run of any arm. After that they are not edited; corrections are appended to the results README beside them. This is a **shakedown, not a count**: every report says `"counted": false`, and nothing is bound to v21.

## 1. Identities (measured 2026-10-16, tree `477f2a86`)

| item | value |
|---|---|
| profile `e2-editor-v21` (read-only) | wasm `db3408f55316bf67…`, loader `0b6cf02a51aba353…`, worker `0d55bcfa2ee0e4dd…`, manifest `72067d5a14a3a271…` |
| page under test | `build_cutover_page.py --profile e2-editor-v21`, **no `--write`**. Served sha256 `3d5112161b23b060b2057a25bbbeb7cbc96628cde67e3e5c3c0dab92b435b5c5`; pin `313b08d5… -> db3408f5…`; source `web/e2-editor-app.js` `bd15e7ef…` |
| shell served | `dist/` is mirrored. The five files that lag their source (`shell_lagging_source(dist)`) are served from the **tree**: `narrow-editor-v2-client.js` `c5ab9d17…`, `narrow-editor-v2-session.js` `443e0f1e…`, `paragraph-editor-client.js` `4616ae17…`, `sdk/document-sdk.js` `9dcb8312…`, and `web/e2-editor.html` `1d158149…` before instruments are inserted. Shell digest over those sources, by the v73 bundle's module list: `e0252c0b22d37a201a3476b0d32d597af5d707523cb78946c2e73ff04247bfe3` (the `dist/` digest today is `e7c4eefe…`). The v74 freeze copies exactly these sources. If the frozen v74 digest differs, every report is void (§11.0) |

## 2. Rules for both items

- **Two browsers, N=3 per arm per browser; a pass is N/N** (§11.0). Missing, NE or no reply counts as not done and takes the row's default.
- **One browser run at a time.** No browser run of ours, development or evidence, runs while another is live. This is enforced by an exclusive lock (S-9), not by memory. Chrome first, then Firefox.
- **Foreign load** (item 1 ruling D-18 A′, which also applies to M6): before each timing-bound arm, CPU is sampled for 2 s. If a process outside the runner's own tree uses more than 50 % of one core, that arm is NOT_ESTABLISHED for that run, and the sample is kept. The load average is recorded and never gated on.
- **Diagnostic reports** (a worker other than `0d55bcfa…`) carry only what spec §12.2 (a) allows. Every report says `instrumentedWorker: true|false`.
- **The judges.** Each judge is red first. Each has a `--self-test` that covers every red case and non-vacuity case named in the arm files, and it is run and committed before the first evidence run.
  - Zero instances is NOT_ESTABLISHED, never PASS.
  - A served page other than `3d511216…` is refused. The two declared exceptions are the v20-repointed page (S-5) and the 0.2.24 red cases.
- **No `make`, no `--write`, no writes under `dist/`, no ddev.** The host arms (D2, M11-autosave) run after the v74 freeze and host 0.2.25. The 0.2.24 host red case for D2 runs before 0.2.25 is installed. Each of these is asked of the owner before ddev is touched.
- **Runner errors, §34.4.** A runner that misjudged or lost an honest run gets its witness committed **before** the fix; the README tallies them. Reports flush per round. Post-arm reads are guarded, and the browser is hard-killed if it will not close (v20 README §6).

## 3. Shared instruments (one implementation each; both runners import them)

| id | what | item-1 text | item-2 text | owner in phase B |
|---|---|---|---|---|
| S-1 | the served mirror and the identity block (§1), with instrument snippets injected before the page's module as a list | §2.1, §1 | I-1, §1 | Agent D (`tools/v21_shakedown_common.py`) |
| S-2 | the observer: v20's `OBSERVER` unchanged, plus an item-1 snippet (keys, state transitions, D7 timer, D10 frame read) and an item-2 snippet (paste logging, URL-fed ask, windowed request rewrite, `#state-pill` transitions), as **separate** `<script>` blocks so neither edits the other | §2.2 | I-2 | each agent owns its own snippet; S-1 injects them |
| S-3 | the page-realm module hook that captures the page's own session and `DocumentHandle` (replaces item 1's D-7 harness) | §8 D-7 | I-3, DM-1 | Agent M (`tools/v21_page_hook.py`); item 1 imports it for D11c and D12 |
| S-4 | real input: keys, Ctrl/Cmd chords, a Ctrl-held flagged hold, a Ctrl-held unflagged burst, real click, real drag, clipboard with trusted Ctrl+V and read-back | §2.3 | I-4 | Agent D for keys, pointer and drag; Agent M for the clipboard |
| S-5 | the final page repointed to `e2-editor-v20` (D5-w, M8-v20) | D5 | M8 | Agent D |
| S-6 | the FODT→ODT converter. Deterministic; places every top-level child and refuses an unknown one; proofs (i)–(iii) | §2.5, §8 D-4 | I-11 | Agent D (`tools/fodt_to_odt.py`) |
| S-7 | the ODT container adapter. It presents `content.xml` + `styles.xml` (+ `meta.xml`) as one `office:document` root and exposes `Pictures/*` data. `read_marker.paragraphs` and the item-2 comparator both read through it, and each reader keeps its own red cases | §2.7 | I-7 | Agent D builds the adapter; Agent M builds the comparator on top of it (image data hash) |
| S-8 | engine read (`editorGetStateV2` ask) and save capture | §2.8 | I-5, I-6 | Agent D |
| S-9 | pre-run checks: KWallet `Locked`, our processes, `pgrep -c chrome`, load average, the foreign-CPU sample. Also the **browser-run lock** (`fcntl.flock` on `wasm_sdk_probe/build/v21-shakedown-browser.lock`, taken by every tool of ours that starts a browser) | §2.9, §8 D-18 | §5 | Agent D |
| S-10 | the non-shipped workers, mirror only: the trace worker (finding 117's patch, placed as v20 fixed it) and the raw-bytes carrier (§12.2 (a)) | — | I-8, DM-3 | Agent M |
| S-11 | network capture for M5: a logging proxy in both browsers with loopback forced through it, the target-port listeners, and Chrome CDP | — | I-9, DM-12 | Agent M |

## 4. Order of work (phase B)

1. **Native pre-runs, committed before the WASM arms they serve.**
   - DM-5: C1, X09–X12 at P1, 3 runs each.
   - DM-17 C: select the image and the frame in the new M10 fixture, and record what Writer sends.
   
   These belong to Agent M and run in parallel with step 2.
2. **Shared instruments S-1, S-4, S-6–S-9** (Agent D), and **S-3, S-10, S-11** (Agent M). Each instrument has its red cases first. The converter's outputs and their sums are committed with the converter.
3. **Population tools and judges**, each with `--self-test` committed before any evidence run: the D1/D7 population, and the M1/M3/M4/M5 populations.
4. **Runners.** One development pass per item in Chrome under the lock (a smoke, recorded as such, never judged). Then the evidence runs: Chrome then Firefox, item by item, under the lock.
5. **Results** in `README.md` beside this file: verdicts per criterion, defaults taken, departures, and runner-error witnesses.
6. **After the shakedown** (handoff Next 2–5): apply any §11 default to the shell, freeze v74, host 0.2.25 (asked of the owner), host arms, binding, count.

## 5. Predictions worth stating once

- **Encoding.** The WASM process's `LANG` is `navigator.language` with `-` replaced by `_`, plus `.UTF-8` (the loader's `getEnvStrings`, read in `dist/profiles/e2-editor-v21/probe.js`). So `osl_getThreadTextEncoding()` is expected to be UTF-8, and Markdown pastes are not expected to be refused with `MARKDOWN_ENCODING_UNSUPPORTED`. This is inferred from the loader. The first M1 instance decides it, and a refusal there makes M1/M2 red (`ARMS-item2.md` M1).
- **The stated red risk is M10b/c.** The engine has no `GRAPHIC_SELECTION` case. The native arm (DM-17 C) runs first so that this risk is known before the WASM run.
