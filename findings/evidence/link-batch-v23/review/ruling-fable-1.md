# Ruling 1 (v23) — scope, the first candidate to measure, and whether now is 0.2.28's window

Ruled by fable on the owner's behalf (authorisation: owner, 2026-10-20 ~06:40, 「我不在座位，請自主執行任務，另外我授權給fable 代我做決策」; the owner chose "A+B" earlier the same morning). Brief: `findings/evidence/link-batch-v23/review/brief-fable-1-scope-and-candidate.md` (`9613bfea`). Read-only: no ddev, no browser, no make, nothing written; targeted reads only. Every number below was re-read in the cited source by me; nothing was run.

## 1. 裁決（白話，給擁有者）

三件事，先講結論。

**第一，範圍選 A（第 1、2 層）。**有序指令的修法，加上你點名要的 Shift＋方向鍵和範圍上的方向鍵。第 3 層不另外設計：候選定了之後，哪些是「順便就有」的（邊界鍵立刻回答、點擊的完成條件、編號／縮排那個殘留關掉），規格裡逐項寫「做／順便有／不做／重新登錄」，不用「包含第 3 層」一句帶過。

**第二，候選先量 C（單執行緒 unipoll），在原生量，不連結。**理由：

- 多執行緒模式下，核心的方向鍵是**分兩跳**跑的：先收到鍵，再另外排一個事件去真的移動。而一個鍵要跳幾下，是 Writer 在跑的當下看文件狀態決定的——同一個 Backspace，一般文字裡兩跳，編號段落開頭一跳。finding 142 的原生量測已經抓到：Ctrl+Home 後面接一個一跳的 Backspace，Backspace 先跑，3/3。
- 所以任何「把指令排進同一條佇列」的作法（A′ 把打字改成送鍵、B 在鍵後面放標記）都不成立：佇列只對「跳數相同」的事件保序，而跳數我們無從得知。這兩個撤回。
- 主 session 說「A 不管幾跳都對刪除有效」——**不對**。A 用復原紀錄證明「鍵跑過了」，這一點確實不受跳數影響；但「這個鍵跟前一個方向鍵誰先跑」仍然受跳數影響。核心停頓時，A 在編號／縮排那幾個位置照樣會排錯——而那正是 A 被說成能關掉的位置。A 不是這一批的退路；它頂多是另一個更小的批次。
- C 之下根本沒有「排隊中的鍵」：鍵在呼叫裡就跑完，貼字、格式、刪除全部照呼叫順序。這是 LOK 自己為單執行緒做的模式（原始碼註解 tdf#130382「全部同步」），Collabora 的 WASM 和手機版都這樣跑。
- 我上次（裁決 4）寫「C 受 finding 040 限制」，**是我寫錯的**：040 那個永遠等不到的條件，只有在「不是主執行緒」上才會去等；C 之下引擎就是主執行緒，由原始碼看不會進那條路。這裡撤回。
- C 的代價是真的：引擎的指令迴圈要改成由 tick 驅動；而今天為了「鍵是非同步的」而蓋的一整套東西（250 ms 讀回、第一個回呼就完成、barrier 的 K1、各階段期限、2.25 秒的邊界等待）前提都沒了，要一項一項決定撤掉、還是另外說明它還守什麼。這是規格的工作，不是現在的。
- 原生量測量的是「順序」本身：142 那對鍵、137 的三種後果、Shift＋方向鍵接刪除、點擊接打字，每格 5 次；多執行緒版同一組當正向對照（必須照樣排錯）；還有編號／縮排三個位置下「使用者自己的鍵」的復原紀錄（規格第 2 題規定要有的內容）。全部照 Writer 的順序就選 C；任何一格不照，C 的「由構造成立」就是假的，登錄 finding，改量 B″（等核心佇列空了才送同步指令）。
- 有一件原生量不到：WASM 上那個 tick 迴圈（finding 021 跑過一次，在 v20 之前）。那是連結後的 shakedown，連結由你做。

**第三，0.2.28 現在不裝。**你早上選 B 的那句話寫明「安裝等你給時段」；10-19 你也定過「碰 ddev 的步驟集中在你指定的時段」。「授權 fable 代我做決策」是一般性的授權，蓋不掉你同一個早上親口講的保留。裁決 7 那次我代定時段，是因為你在睡、其他專案不可能啟動；今天你是離開座位、人醒著，其他專案隨時會動，而且 0.2.27 上還有你沒做的手測。你回來講一句「現在可以」就是時段；`ddev list` 空著不是。

**接下來主 session 會做**：寫原生 unipoll 的 harness 和判讀工具（先做紅案），先跑多執行緒對照臂再跑 unipoll 臂，然後依結果寫規格（判準先釘）、跑模型、送兩席審核。不建置、不碰 ddev、不開瀏覽器。

## 2. Answers (English)

### 2.1 Q1 — Scope: PLAN §4 A (tiers 1 and 2); tier 3 only as consequences

- **In:** tier 1 (items 1–4) whole. Tier 2 items 5, 6 and 8 as named. Item 7's **cells** carry over as arms and red cases (R1's 42 + the L-129 wrap cell; S1–S5's cells; S2's 16-cell v19 pre-red; S-12); item 7's **mechanisms** (the §10.4/§12.4 resolver, rule (a), the flag, K1 fences, `AwaitingDeleteCompletion`'s wait, §12.5's pin widening) are re-derived under the chosen candidate, none carried by inertia (CLAUDE.md §4). Item 9 is dispositioned in the spec as either closed by construction or re-registered, with the trace that shows which.
- **Tier 3:** items 10, 11 and 13 enter only as consequences the candidate's arms demonstrate (no separate design); item 12 stays out (no reader exists). Items 14–17 are required content; 17 is required under C because the 2.25 s window disappears (2.8c).
- **Form.** The scope is a hand-written enumeration (form 3), so it cannot be a hard criterion. What can: *every one of the 18 census items has one disposition line in the spec's scope section, from {in, consequence, out, re-registered}* — form 1 over the census list; a fictitious 19th census item would need its line and the claim stays true.
- **Default if the chosen candidate is not buildable:** nothing from tier 2 ships (ruling 4 condition 36 and ruling 5 condition 41 stand: Shift+Arrow on no profile); tier 1 does **not** ship as candidate A; the batch returns to the facts sheet and this ruling's fallback order (C → B″ → re-plan). "A ships as the fallback" is refused (2.4).

### 2.2 Q2 — A′ is withdrawn on F1–F3

Printable characters are one hop (`edtwin.cxx:2681-2690` with `AnyInput(KEYBOARD)` false on svp, `svpinst.cxx:549-554`); accelerator keys are two (`acceleratorexecute.cxx:223-226` → `evntpost.cxx:42-46` → `Application::PostUserEvent`); and a key's hop count is decided **at run time by document state**: Backspace at a numbered start is handled inside `SwEditWin::KeyInput` (`edtwin.cxx:2047-2110`, one hop), mid-text it goes through `.uno:SwBackspace` (two). 142's Q arm observed the consequence 3/3 (`142-ctrl-home-end/README.md:39-47`, `:218`). A FIFO of posted events preserves order only among events of equal depth, and the depth is not ours to know. Typing cannot be made two-hop; formats as accelerators happen to be two-hop today, which is a coincidence of Writer's tables, not a contract. **Withdrawn.** (This is a decision; the fact that forces it is already in evidence.)

### 2.3 Q2 — B as stated is withdrawn; B″ (quiescence) is kept as the fallback

A marker at any fixed depth is unsound for the reason in 2.2; the facts sheet is right that the depth is not bounded by source (dispatcher re-post `dispatch.cxx:996-1003`, other posters). The only sound B is **"the engine issues no synchronous command while the user-event list is non-empty"**: posted keys, their `AsyncAccelExec` hops, posted dispatches and the callback flush (`init.cxx:2578-2582`) are all in that one list, and a check made under the SolarMutex cannot interleave with a hop (each tick holds the mutex while dispatching, `svpinst.cxx:303-306`). Two forms:

- **public:** `.uno:ReportWhenIdle` — handled in `doc_postUnoCommand` before dispatch (`init.cxx:5481-5497`), an `Idle` at `TaskPriority::TOOLKIT_DEBUG`, the **lowest** priority (`task.hxx:28-40`), answered by `UNO_COMMAND_RESULT` with `idleID` (`:1414-1430`). It fires only when no user event is pending **and** no higher task is ready, so it waits behind Writer's `LOWEST` layout idle; one outstanding per document (`assert`, `:5483`; overwritten under `NDEBUG`). Needs no internal TU; latency unmeasured. The brief's "B also needs a new internal-API translation unit" is true only of the next form.
- **internal:** `SalUserEventList::HasUserEvents()` exists (`vcl/inc/salusereventlist.hxx:107-116`, inline, internal header), read under the SolarMutex; the `LIBO_INTERNAL_ONLY` TU per the facts sheet Q6.

B″ is measured **only if C fails** (natively, or on the owner's link). It may be characterised in the same native session (one extra step type in the threaded harness) — that decides nothing and its latency is a record, not a criterion.

### 2.4 The main session's lean "A works for deletes whatever the hops" is wrong

The `.uno:Undo` proof makes **completion** hop-agnostic (it is by effect), not **order**. Under 137's precondition (the arrow still at its first hop), the user's own Backspace posted behind it runs at *its* first hop wherever Writer handles it inside `KeyInput` — positions (ii) and (iii) of L-C-number-or-indent and 142's `at-num` arm — and overtakes the arrow. That is exactly the 142 observation, which used A's mechanism (both as posted keys). So A: closes §15.1's residual in the **no-stall** case (Writer's `Number On/Off` instead of the barrier's silent 2.25 s no-op); narrows 137's delete effect under a stall to the one-hop positions; does nothing for typing and formats; keeps the "key that does nothing" hole. It does not deliver the property and cannot carry Shift+Arrow. A can be its own smaller batch if C and B″ both fail; it is not this batch's fallback.

### 2.5 Q2 — Candidate: C, measured first, natively, no link

**Why C.** It is the only candidate with **zero hops**, so the property holds by the call order: `postEventAsync` runs `LOKPostAsyncEvent` inline under unipoll (`lokhelper.cxx:1283-1288`); `AcceleratorExecute` dispatches inline (`acceleratorexecute.cxx:213-221`, "tdf#130382 - all synchronous really"); `doc_postUnoCommand` adds no `SynchronMode=false` (`init.cxx:5316-5322`), so a non-`Asynchron` slot takes `Call_Impl` (`dispatch.cxx:742-756`). Unipoll is LOK's own single-thread topology; COOL's kit runs it on mobile and WASM (`cool-26-04/kit/Kit.cpp:3561`, `:4353-4357`; `SetupKitEnvironment.hpp:66`).

**Ruling 4's "constrained by finding 040" is struck.** `IdlesLockGuard` waits only `if (!Application::IsMainThread())` (`scheduler.cxx:280-298`); under unipoll `lo_initialize` skips `lo_startmain` and calls `InitVCL()` on the hook thread (`init.cxx:8378-8387`), which records that thread as main (`svpinst.cxx:96`; `lo_runLoop` → `UpdateMainThread`, `init.cxx:7733`, `svapp.cxx:1407-1412`, `:522-525`). I wrote that constraint in ruling 4 (`ruling-4.md:56`) without a source reading. The product engine under C is that thread; 040's wait branch is unreachable by source, **provided every LOK call is made from it** (2.8e makes that a property with a positive control).

**A mechanism the brief leaves out, which makes completion honest for free.** Each Emscripten tick is `loop()` → `ImplYield(bWait, bHandleAllCurrentEvents=false)`: it dispatches **at most one** user event and **returns before the poll** (`svpinst.cxx:303-306`, `:440-444`); the poll callback, where the engine drains its commands, runs only on a tick with no user event pending (`:446-481`, SolarMutex released at `:471`). The callback flush is a posted user event (`init.cxx:2578-2582`). So under C the flush for command N always runs before command N+1 is drained: "completion = the call returned, and the next tick drained the list" needs no readback and no deadline.

**C's real cost.** The command loop moves from the blocking `engineLoop` (`probe_engine.cpp:6435`, waits at `:6497-6533`) to the poll drain (`:6688-6752`); the `#error` at `:15-17` is our own gate and is replaced by the wiring, not deleted. Every piece built for asynchronous keys loses its premise — the 250 ms readback, the first-callback rule, the barrier's K1 reason, the stage deadlines, `AwaitingDeleteCompletion`, the 2.25 s window, the 15 ms undo poll — and the spec must say, for each, what it still guards or withdraw it (CLAUDE.md §4). Natively unmeasurable, hence post-link: the Emscripten pthread main loop (ran once, 2026-08-06, both browsers, `findings/021-…md:224-236`, `:628-631`, before v20's machinery), the worker bridge under the tick, tick pacing (≥ 10 ms, inferred), callback latency, idle-layout interleaving, finding 122's latency.

### 2.6 Q2 — The native arms, their controls, red cases, and the reading that moves the decision

**Harness.** A unipoll variant of the 142 tool (`f142_native_ctrl_home_end.cpp`, `lok_init_2` at `:329`): `SAL_LOK_OPTIONS=unipoll` before init; `runLoop(poll, wake, <non-null>)`, which **returns at once** because `ImplSVMain` early-returns when VCL is already initialised (`svmain.cxx:189-197`, `:262-267`; measured on WASM in 021, native by the same source); then the harness enters the loop itself through `Application::Execute()`, declared out of tree as the engine does (`probe_engine.cpp:121-160`), linking `libvcllo.so`. On native svp `DoExecute` is the base virtual (`salinst.hxx:237`; only the Emscripten override installs a main loop, `svpinst.cxx:308-316`), so `Execute` loops `Yield` → `ImplYield` → the poll (`svapp.cxx:348-372`, `svpinst.cxx:473-481`). The script advances one step per poll; callbacks arrive between polls. **This is the drive shape of the engine's mainloop profile and of COOL's kit, so the arm measures the drive pattern as well as the order.** No link, no build of the engine; the owner's `make` is not needed (F12 ✔).

**Rounds.** N = 5 per arm, each round a separate process (068: the count is the measurement; 142 used 3). Per step the record holds: `effectAtReturn` (the `.uno:Undo` top and the selection/caret read immediately after the LOK call returns, no poll in between), the callbacks until the quiet window, and the saved text and paragraph shape (as 142's reader).

**Decision arms, under unipoll (expected: Writer's order, N/N):**

| arm | sequence (today's engine calls) | Writer order | reordered |
|---|---|---|---|
| D1 (142's pair) | caret at numbered P2 start; Ctrl+Home; Backspace | P2 keeps its numbering, caret at document start, undo unchanged | P2 `Number On/Off` |
| D2 (137 delete) | `abcd` caret at end; Left; `.uno:Delete` sync | `abc` | `abcd` |
| D2′ | `abcd` caret after `b`; Right; `.uno:SwBackspace` sync | `abd` | `acd` |
| D3 (137 typing) | `abcd` caret at 0; Right; `paste("x")` | `axbcd` | `xabcd` |
| D4 (137 format) | `a` selected; Left; `.uno:Bold` sync | no bold span in the saved document | `a` bold |
| D5 (extend + delete) | `abcd` caret at end; Shift+Left; `.uno:Delete` sync | `abc` | `abcd`, `d` selected |
| D6 (mouse, tier 3 item 11) | caret at 0; click after `c`; `paste("x")` | `abcxd` | `xabcd` |
| D7 (§15.1 content) | positions (i)–(iii) with the **user's own key**; plus plain P1, Backspace at document start | the `.uno:Undo` top **at return** for each; plain P1: unchanged at return and no callback in the quiet window | — |
| D8 (discriminator) | every key arm | `effectAtReturn` shows the new state | under threaded init the same read shows the old state |

D7 decides nothing; it is the content §15.1 requires of the spec's fixed question 2 (`SPEC-M3-link-batch.md:464`). D5 is built so both orders differ (a forward `.uno:Delete` on `abcd` caret-at-0 after Shift+Right gives `bcd` either way — do not use that shape).

**Positive controls:** the threaded Q form of D1–D6 (both posted from inside a callback, 142's `f142_native_queued_pair.cpp` pattern) must reorder N/N. If a control stops reordering, the harness changed, not the product.

**Red cases, made before the run (CLAUDE.md §6):** (a) the reader fed a threaded Q output labelled as unipoll → red; (b) 142's `break_one_for_red_demo.py` pattern on one round's landing → "rounds disagree" red; (c) a run whose `env` record lacks `SAL_LOK_OPTIONS=unipoll` while labelled unipoll → red; (d) a unipoll run with `effectAtReturn` unchanged for a moving key → red (a hop we did not find).

**What moves the decision.**
- D1–D6 Writer-order N/N under unipoll, controls reorder N/N, D8 holds both ways → **C is the candidate; the spec is written for C.**
- Any of D1–D6 Writer-divergent under unipoll → C's by-construction claim is false; register the finding (an asynchronous hop under unipoll, likely upstream) and run B″'s arms (the threaded harness with a `ReportWhenIdle` gate before each synchronous command; same D1–D6; latency recorded).
- D8 fails under unipoll → stop; read the source for the missing hop before any further arm.

**Form:** form 1 per instance (every arm, every round, Writer's order). **Default if never run:** no candidate is chosen and no spec is written (PLAN §4's default); Shift+Arrow stays off every profile.

### 2.7 Q2 — The model: after the native arms, not before

The model's keys are single events, "one FIFO of posted keys and flushes" (`extend_completion_model_test.cpp:17-19`); it has no hop, so it cannot discriminate A/A′/B, and under C its pending-key state space is empty. Run it **after** the arms, when the candidate's completion rule is written, in two modes: **threaded mode** must still print condition 32/33's populations (27,744 / 2,448; 5,474 / 3,868; `findings/137-…md:40-43`) — the red case that proves the generator is alive; **synchronous-key mode** (C) must print 0 Writer-divergent for every shape including condition 33's two, and what it still gates is the page side: with completion defined as "returned + the flush tick", the forged-completion class must be empty. Condition 39 stands. Record two limits in the spec's model section: condition 40's (rectangle widths) and the new one, **single-event keys (no hops)** — material only to FIFO candidates, which are withdrawn.

### 2.8 Q2 — Spec-level consequences to record now

- **(a) The three fixed questions under C** (`SPEC-M3-link-batch.md:412-415`):
  1. *A FIFO key's undo proof satisfied by a different change* — under C the engine is the only mutating thread and must not yield between the key and the read (`Application::Yield` aborts on WASM, `svapp.cxx:494-501`; `Reschedule` is a no-op, `:400-406`; `Scheduler::ProcessEventsToIdle` bypasses that gate, `:441-449`, and **would** nest dispatch on the main thread under C). The spec forbids `Yield`/`ProcessEventsToIdle`/`Reschedule` inside a command (a per-instance property; red case: a test build that drains one command between key and read must show the proof reading the other change).
  2. *A key that does nothing* — known at return (undo and caret unchanged) and confirmed by a flush tick that carries nothing; D7's three positions with their undo tops are the required content.
  3. *Tables and inline objects* — Writer's own key at a cell start/end, on a selection spanning cells, on an as-char frame: arms in the spec; where "today's refusal" and "Writer's order" conflict, the default is Writer's behaviour, because that is the property.
- **(b) L-C-number-or-indent under C:** closed only if the engine sends the **user's own key** (Writer's `Number On/Off` / `Apply attributes` is then the honest answer, read at return); if the barrier's K1 is kept, re-registered (§15.1 is right about that). The spec must name what the barrier still guards under C; if it cannot, the barrier is withdrawn. Default: the user's own key.
- **(c) The 2.25 s window and `verified-boundary-noop`** are replaced by the at-return answer; the counted 096 check `a-boundary-arrow-press-does-not-cost-the-work` needs a §34 ruling written before any run that would satisfy it, with CLAUDE.md §9's four conditions.
- **(d) Editor ABI 6;** the completion vocabulary changes (no `key-deadline`, immediate no-op); read `kMaxInternalEditorAction` before adding actions.
- **(e) Post-link arms on the owner's v23 (not now):** 040's two entries (`doc_destroy`, `doc_getTextSelection` on a frame-bearing `SwDoc`, `findings/040-…md:14-27`) must **return** under C; a diagnostic that calls one LOK entry from the JS-side thread must wedge (040 reproduced as the positive control, under a timeout); tick pacing; `keyToUndoMs` against v20's [30, 32, 33] ms (`v20-shakedown/merge/README.md:10`, `:46-47`); finding 122. The implementation order puts the loop re-wiring first on a **diagnostic** profile with a smoke arm (open, type, move, save) before any feature code, so the owner's first v23 link is the diagnostic.
- **(f) Facts-sheet notes:** COOL sets `SAL_KIT_OPTIONS` (its COKit fork, `SetupKitEnvironment.hpp:73`), not `SAL_LOK_OPTIONS` — evidence of topology only; and its same-thread rule (`Kit.cpp:3621-3623`) is the one the engine already follows (`probe_engine.cpp:6884-6886`).

### 2.9 Q3 — 0.2.28: not now; the delegation does not reach it

- The owner's option text 「安裝等你給時段」 and his 2026-10-19 rule (host steps run in a window he names; no window, no ddev — memory `ddev-is-shared-do-not-occupy`, choice A) are specific; the delegation is general and given in the same breath. A general delegation does not cancel a specific reservation made the same morning.
- Ruling 7's precedent (v22 spec §13.1: I named one window because A's purpose did not hold that night — the owner asleep, other projects stopped) does not transfer: "not at the desk" is when other projects can start, and the owner is awake. The hand tests on 0.2.27 (PLAN §5) are also pending; an install would change the host under his hand test without his knowing.
- **Form 1:** *every ddev-touching step for 0.2.28 (§14.4 steps 4–7) runs inside a window the owner named in his own words after `b6a8379f`, with a start and a `WINDOW_END`*; `ddev list` state, the owner's absence and a general delegation are not windows. A fictitious new ddev step would need its window and the claim stays true.
- **Default if the owner never names one:** 0.2.28 stays prepared and uninstalled; 0.2.27 stays the nominal candidate; finding 155 stays open with the patch attached; nothing further is decided.

### 2.10 Q4 — What the brief gets wrong or leaves out

1. "A works for deletes whatever the hops" — wrong (2.4).
2. "B needs a hop-aware marker" — any fixed-depth marker is unsound; only quiescence is; and B″'s public form needs no internal TU (2.3).
3. Ruling 4's 040 constraint on C — my own error, struck by source (2.5).
4. The one-event-per-tick return before the poll (`svpinst.cxx:440-444`) — the mechanism that makes "returned + one tick" an honest completion and removes the readback's reason (2.5).
5. C's cost is listed as re-wiring; most of it is **removal** of machinery whose premise is gone (2.5, 2.8b).
6. The native unipoll harness is a poll-driven state machine that must call `Application::Execute()` itself (`runLoop` returns at once); F12's "drive `runLoop` from the client" under-describes it (2.6).
7. The model has no hops; its role under C narrows to the page side; run after (2.7).
8. Missing arms: a mouse click before a command (D6), and the discriminator that proves which topology ran (D8).
9. N: 068's rule ("N 次全過") — 5 rounds, not 3.
10. The §34 ruling for the counted 096 check becomes mandatory under C (2.8c).
11. `ProcessEventsToIdle` becomes a re-entrancy source under C (it was a no-op's neighbour under threaded); the spec must forbid it inside a command (2.8a.1).
12. F10's variable is `SAL_KIT_OPTIONS` (2.8f).
13. Not covered by this round and stated as such: IME/ext-text input under unipoll (typing goes through `paste` today), Calc/Impress, the `.uno:ExecuteSearch` posted path, mouse hops after `MouseButtonUp`.

## 3. Facts checked

| fact | status | where (re-read by me) |
|---|---|---|
| F1 two-hop accelerator key; unipoll inline | **confirmed** | `lokhelper.cxx:1273-1291`; `acceleratorexecute.cxx:213-226`, `:496-501`; `evntpost.cxx:42-46` |
| F2 printable characters one hop; `AnyInput` timer-only on svp | **confirmed** | `edtwin.cxx:2681-2690`; `svpinst.cxx:549-554` |
| F3 142's native reorder 3/3, both B and Q; the correction that it is the product's topology | **confirmed** | `142-ctrl-home-end/README.md:39-47`, `:206-220`, `:372-386` |
| F4 `SynchronMode=false` only when not unipoll; listener forces `SYNCHRON` | **confirmed** | `init.cxx:5297-5322`, `:5513-5521`; `unoctitm.cxx:655-657`; `dispatch.cxx:730-756` |
| F5 the engine's sync/posted inventory | LOK side confirmed (above); engine lines not re-read | facts sheet Q1 |
| F6 one user event per tick, return before the poll; 10 ms pacing | tick dispatch **confirmed** (`svpinst.cxx:303-316`, `:440-444`); the 10 ms pacing **not checked** (libeventloop.js not read) | |
| F7 `Reschedule` no-op, `Yield` aborts, system loop on Emscripten; `ProcessEventsToIdle` bypasses | **confirmed** | `svapp.cxx:400-406`, `:494-501`, `:441-449`; `svpinst.cxx:102-104` |
| F8 `ReportWhenIdle` neutral, quiescence, `TOOLKIT_DEBUG`, one outstanding; `HasUserEvents()` exists | **confirmed** | `init.cxx:5481-5497`, `:1414-1430`; `task.hxx:28-40`; `salusereventlist.hxx:107-116` |
| F9 unipoll: no `lo_startmain`, `InitVCL` in the hook; `lo_runLoop` registers then `soffice_main`; `isUnipoll` = poll callback set; the `#error`; the mainloop profile; `runLoop` returns at once | **confirmed** | `init.cxx:8083-8089`, `:8378-8387`, `:7722-7743`; `lok.cxx:50-54`; `probe_engine.cpp:15-17`, `:6853-6931`, `:6688-6752`; `svmain.cxx:189-197`; `findings/021-…md:224-236`, `:628-631` |
| 040's wait branch is off-main-thread only; measured entries | **confirmed** | `scheduler.cxx:280-298`; `findings/040-…md:14-27`, `:108-109` |
| F10 COOL unipoll on the WASM path | **confirmed, with the `SAL_KIT_OPTIONS` caveat** | `SetupKitEnvironment.hpp:66`, `:73`; `Kit.cpp:3561`, `:3621-3623`, `:4353-4357` |
| F11 `keyToUndoMs` [30, 32, 33]; 129–155 ms end to end | **confirmed** | `v20-shakedown/merge/README.md:10`, `:46-47` |
| F12 native arms are standalone `lok_init_2` clients | **confirmed** | `f142_native_ctrl_home_end.cpp:329` |
| The model's keys are single events | **confirmed** | `extend_completion_model_test.cpp:17-19` |
| Ruling 4's C constraint and ruling 5's A′ | **confirmed as written; the 040 part struck here** | `ruling-4.md:56`; `ruling-5.md:25` |
| §13.4's three fixed questions; §15.1's positions and "only A closes it" | **confirmed** | `SPEC-M3-link-batch.md:402-415`, `:448-464` |
| v22 §14.4 install steps and §13.1's one-time window | **confirmed** | `SPEC-M3-link-batch-v22.md:550-571`, `:461-467` |
| whether `runLoop` returns at once **natively** | by source only (same `IsVCLInit` path); the harness author will see it in the first run | `svmain.cxx:196` |
| frequency of core-thread silences; C's WASM wiring on today's emsdk | not measured; stated as such | |

## 4. What the main session does next, in order

1. Commit this ruling verbatim as `findings/evidence/link-batch-v23/review/ruling-fable-1.md`; append to `handoff/PLAN-2026-10-20-ordered-commands-v23.md` a section "Ruling 1" that records: scope A with tier 3 as consequences, C first natively, A′ and B-as-stated withdrawn, A not a fallback for the property, B″ the fallback, ruling 4's 040 constraint struck, 0.2.28 waits for an owner-named window. Rulings 4 and 5 are not edited; the spec cites this ruling for the correction.
2. Build the native unipoll harness variant and its reader under `findings/evidence/link-batch-v23/native/ordered-commands/` with the reader's four red cases first (2.6). Run the threaded Q controls (must reorder N/N), then the unipoll arms D1–D8, N = 5, separate processes, no other runner overlapping (142's note). Native only; no engine build, no link.
3. Read the results against 2.6's decision rule. If C passes: write `specs/SPEC-M3-ordered-commands.md` (zh-TW) for C with criteria pinned first — the three fixed questions (2.8a), D7's undo tops, the barrier's disposition (2.8b), the §34 ruling for 096 (2.8c), ABI 6 (2.8d), the model section with both limits (2.7), the post-link arms and the diagnostic-first link order (2.8e), one disposition line per census item (2.1). Then the model in both modes. Then the two-seat review (opus and `codex exec -s read-only < /dev/null`; the codex MCP failed to connect this session). If C fails natively: register the finding and run B″'s arms before anything else.
4. Only after the review: engine code, red cases first; the owner links v23 (the diagnostic profile first).
5. 0.2.28: nothing on ddev. When the owner is back, the first line to him is this ruling's §1; the install waits for his window.
6. Not in this round: no build, no ddev, no browser, no push.

---

## The main session's check before adopting (opus, 2026-10-20)

The text above is fable's, committed verbatim. Re-read in source before acting on it:

- **One user event per tick, returned before the poll** (2.5): `vcl/headless/svpinst.cxx:442-444`: `DispatchUserEvents(bHandleAllCurrentEvents)`, then `if (!bHandleAllCurrentEvents && bWasEvent) return true;`. As stated.
- **`runLoop` returns at once when VCL is initialised** (2.6): `vcl/source/app/svmain.cxx:196-197`: `if ( IsVCLInit() ) return EXIT_SUCCESS;`. As stated. The engine's comment at `probe_engine.cpp:6897-6906` records the same on WASM (2026-08-06).
- **040's wait only off the main thread** (2.5): `vcl/source/app/scheduler.cxx:280-298`: the reset/post/wait sits inside `if (!Application::IsMainThread())`. As stated.
- **Unipoll skips `lo_startmain` and calls `InitVCL()`** (2.5): `desktop/source/lib/init.cxx:8378-8387`. As stated.
- **The out-of-tree `Application::Execute` declaration** (2.6): `probe_engine.cpp:150-160` declares it under `OXSDK_MAINLOOP_ENGINE`, and `:6918` calls it after `runLoop`. As stated.
- **Not re-checked:** the `ReportWhenIdle` lines, `HasUserEvents()`, `dispatch.cxx:996-1003`, `salinst.hxx:237`. They matter only for B″ and the native `DoExecute` path; the harness's first run tests the latter directly.

Adopted as written. Ruling 2.8(e)'s "frame-bearing `SwDoc`" and ruling 4's correction are left as fable states them; rulings 4 and 5 are not edited.
