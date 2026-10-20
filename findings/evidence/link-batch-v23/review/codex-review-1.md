| Question | Verdict | One line |
|---|---|---|
| 1. False positive | COUNTEREXAMPLE | **Inferred, in-model:** N1 can miss callbacks outside its observation window and can mistake timing separation for a working `anyInput` term. |
| 2. False negative | COUNTEREXAMPLE | **Inferred, in-model:** scheduling variation can make a correct implementation read NE or FAIL in N1c. |
| 3. Non-vacuity | COUNTEREXAMPLE | **Inferred, in-model:** an unfired D7 queued step can be skipped while the overall verdict remains C-HOLDS. |
| 4. Exit and completeness | COUNTEREXAMPLE | **Inferred, in-model:** missing D7 cells and cells retained from previous invocations can escape completeness checking. |
| 5. Red-case coverage | SHOULD | **Read:** several implemented rules have no discriminating red case; the inventory below identifies them. |
| 6. Three fixed questions | COUNTEREXAMPLE | **Inferred from read source:** an asynchronous slot can remain posted under unipoll; “every command finishes inside its call” is too broad. |
| 7. Completion vocabulary | NONE | **Read:** the specified tuples fit the frozen client when the existing distinction between caret deletion and `delete-selection` is preserved. |
| 8. `anyInput` and polling | COUNTEREXAMPLE | **Inferred from read source:** a pending reply still waits behind the scheduler task executed before `anyInput` is consulted. |
| 9. Model C | SHOULD | **Read/inferred:** its zero establishes a conditional geometry property, not complete reply truthfulness or the actual scheduler’s behaviour. |

Paths below use the brief’s absolute-root abbreviations. Additionally, `N/` means `ev/native/ordered-commands/`; `spec` means `R/specs/SPEC-M3-ordered-commands.md`; `model` means `R/wasm_sdk_probe/tests/extend_completion_model_test.cpp`; and `client` means `R/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js`.

**Read:** the committed outputs report C-HOLDS and N1-HOLDS. The counterexamples below concern what those readers can establish, particularly on future uses; they do not demonstrate a wrong landing in the committed runs. (`N/out/reader-output.txt:22–28`; `N/out-n1/reader-output.txt:1–9`.)

## 1. Broken behaviour accepted as HOLDS

**COUNTEREXAMPLE — in-model, inferred: a late callback outside the per-operation window.**

Consider an operation whose first following poll is at time 0. Its `lateCallbacks` record is collected after the fixed 1500 ms idle. A reply-type callback then arrives at 1700 ms, during the subsequent settling period. The harness can record that callback in the complete measured-step `callbacks` array, but it is absent from the already collected per-operation `lateCallbacks`. The reader examines only the latter. With otherwise passing cells, it can print N1-HOLDS despite that late reply-type callback. (`N/tool/oc_native.cpp:483–503`, `507–521`; `N/tool/read_n1.py:87–95`, `130–138`.)

**Read:** the observation is explicitly bounded in the reader’s header. The hard claim in the spec is unbounded: the relevant callbacks must *all* precede the first poll. These are different propositions. Withdraw the claim that this bounded negative observation establishes the latter proposition. (`N/tool/read_n1.py:10–15`; `spec:178`.)

**NOTE — inferred:** I have not established that this core produces that particular late path in the committed arms. The settling experiment is to repeat the existing N1 arms and compare their full measured-step callback timelines with each operation’s collection cutoff, including callbacks after that cutoff. This is a recording blind spot, not an observed diagnosis of the committed core.

**COUNTEREXAMPLE — in-model, inferred: broken `anyInput`, accidentally separated timings.**

Suppose the registered pending-reply callback has no effect on polling. Both modes then follow the same scheduler path, but their elapsed times still vary. Five `uni1` samples can all exceed five `uni1ai` samples purely through scheduling variation. That satisfies the complete N1c PASS condition: there is no additional observation tying the difference to whether the callback was consulted or changed the path. The harness measures elapsed clock time, while its registration record merely states which mode registered the callback. (`N/tool/oc_native.cpp:130–131`, `478–500`, `671–679`; `N/tool/read_n1.py:118–127`.)

**Inferred:** this is an honest-harness input for a future broken implementation, without editing a report. It is not evidence that the committed timing separation was accidental. (`N/out-n1/reader-output.txt:7`.)

## 2. Correct C accepted as FAIL or NE

**COUNTEREXAMPLE — in-model, inferred: N1c is sensitive to unrelated scheduling delay.**

A correct `uni1ai` run can be descheduled between returning from the operation and recording the next poll. One sufficiently delayed sample makes the ranges overlap and yields NE; delaying every `uni1ai` sample sufficiently can reverse their separation and yield FAIL. Neither outcome requires incorrect command ordering or an incorrect pending-reply callback. (`N/tool/oc_native.cpp:478–500`; `N/tool/read_n1.py:119–127`, `135–140`.)

**Read:** overlap deliberately means “not told apart.” Thus NE here is an inconclusive measurement, not evidence against C. The reversed-range FAIL is stronger than the timing observation alone warrants as a causal diagnosis. (`N/tool/read_n1.py:20–24`, `124–127`.)

**NONE — read/inferred:** I found no demonstrated order-independent variation of the committed seq landings. The reader compares literal list-style names and directly stored style properties, rather than resolved effective styles, but an actual harmless serializer variation in these fixtures remains unestablished. It should not be promoted into an in-model counterexample without that witness. (`N/tool/read_results.py:61–69`, `107–119`, `179–180`.)

## 3. Non-vacuity

**COUNTEREXAMPLE — in-model, inferred: D7’s queued X step never fires.**

The queued executor gives the trigger callback approximately five seconds to fire. It can finish that wait with `fired:false` and an empty operation list, then continue the script. A sufficiently delayed trigger callback is one honest way to reach this path. (`N/tool/oc_native.cpp:315–339`, `435–454`.)

For a D7 cell, the reader reports the cleanliness problem but does not incorporate it into the decision-arm verdicts. D8 then skips a measured record with no operations. Consequently, clean passing decision arms can still produce C-HOLDS although the D7 queued key used by D8 was never issued. (`N/tool/read_results.py:157–161`, `207–234`, `236–240`, `255–259`.)

**NONE — read/inferred:** I found no comparable topology substitution produced by the committed harness itself. Its mode selects the executor; the unipoll executor performs the registrations and calls `Execute`, and missing registration symbols produce a fatal record. Merely forging an affirmative init record would be out-of-model. (`N/tool/oc_native.cpp:623–648`, `658–684`.)

## 4. Exit and completeness

**COUNTEREXAMPLE — in-model, inferred: omit all D7 cells.**

A fresh runner invocation selecting only `d1,d2,d2p,d3,d4,d5,d6` still writes the complete arm table. The reader discovers the absent D7 cells, but their problems do not prevent C-HOLDS; their absent D8 observations are skipped. This contradicts the reader’s stated requirement that every cell be clean. (`N/tool/run_arms.py:98–105`; `N/tool/read_results.py:20–22`, `197–209`, `227–259`.)

**COUNTEREXAMPLE — in-model, inferred: reuse an output directory.**

The runner preserves the output directory, appends to its run log, and overwrites only the selected arm/mode/round files. After a complete run, a later partial invocation can therefore leave earlier cells in place. The reader accepts those retained files as cells of the requested reading and never checks which invocation produced them. A missing current round can consequently be supplied by an older run without any report editing. (`N/tool/run_arms.py:97–107`, `126–137`; `N/tool/read_results.py:128–134`, `193–200`; `N/tool/read_n1.py:45–55`, `82–89`.)

**Read:** neither reader checks the subprocess exit statuses stored in `run-log.jsonl`. Both inspect JSON records instead. Duplicate executions appended by rerunning a cell are likewise outside their accounting. (`N/tool/run_arms.py:128–137`; `N/tool/read_results.py:128–176`, `193–200`; `N/tool/read_n1.py:45–79`, `82–89`.)

**COUNTEREXAMPLE — in-model, inferred: exit 0 with incomplete cells.**

Both CLIs return 0 for a FAIL verdict. A failure takes precedence over unrelated missing or unclean cells, so a run containing both can return 0 although the reading is incomplete. Returning 0 for a complete negative result is intentional; returning it despite incompleteness contradicts the documented “exit 0 iff … complete” contract. (`N/tool/read_results.py:5`, `203–217`, `256–261`, `332–334`; `N/tool/read_n1.py:5`, `130–140`, `219–221`.)

**NOTE — out-of-model:** duplicate JSON records and removal or duplication of entries in `arms.json` are also insufficiently validated, but the committed runner does not generate those malformed tables or duplicate measured records within a cell. They are not additional in-model findings. (`N/tool/run_arms.py:33–37`, `98–99`, `126`; `N/tool/read_results.py:138–153`, `194–200`; `N/tool/read_n1.py:56–70`, `83`.)

## 5. Red-case coverage

**SHOULD. Read:** the following distinguishes a rule actually discriminated by a red case from a branch merely reached while another failure already guarantees the verdict.

For `read_results.py`:

| Rule | Self-test coverage |
|---|---|
| A recorded passing dataset is accepted | `control`. (`N/tool/read_results.py:315`.) |
| Unipoll landing differs from seq | `(a)` and `(b)`. (`N/tool/read_results.py:286–302`, `316–317`.) |
| Unipoll rounds disagree | None: every self-test judges one round. (`N/tool/read_results.py:275`, `214–215`.) |
| Seq rounds disagree | None. (`N/tool/read_results.py:210–211`, `275`.) |
| Q rounds disagree, or Q equals seq | None. (`N/tool/read_results.py:212–213`, `315–319`.) |
| Unipoll environment requires `SAL_LOK_OPTIONS=unipoll` | `(c)`. (`N/tool/read_results.py:304–306`, `318`.) |
| Threaded modes must lack that option; environment mode must match | None. (`N/tool/read_results.py:149–152`, `315–319`.) |
| Required unipoll init flags | None. (`N/tool/read_results.py:146–148`, `315–319`.) |
| Output, measured record and `done` required; fatal rejected | None. (`N/tool/read_results.py:131–155`, `315–319`.) |
| X must fire; settle must not cap | None. (`N/tool/read_results.py:157–160`, `315–319`.) |
| Successful save, readable saved file and locator required | None. (`N/tool/read_results.py:162–175`, `315–319`.) |
| D8: unipoll Shift+Left has selected text at return | `(d)`, with its diagnostic asserted. (`N/tool/read_results.py:308–313`, `319`.) |
| D8: unipoll undo effect is present | `(a)` reaches failures after copying Q records, but its assertion requires a landing failure; it does not independently discriminate this rule. (`N/tool/read_results.py:286–298`, `316`, `241–249`.) |
| D8: Q has no effect at return | No discriminating red case; the passing control exercises the expected branch. (`N/tool/read_results.py:236–249`, `315–319`.) |
| D8: last operation agrees with settled undo and selection | `(a)` can reach this failure, but does not independently assert it. (`N/tool/read_results.py:250–253`, `286–298`, `316`.) |
| Child exit status, duplicate cells and invocation completeness | No implemented checks and no red cases. See question 4. |

For `read_n1.py`:

| Rule | Self-test coverage |
|---|---|
| A recorded passing dataset is accepted | `control`. (`N/tool/read_n1.py:201`.) |
| Late reply-type callback causes FAIL | `late_cursor`, specifically `INVALIDATE_VISIBLE_CURSOR`. No separate red case for the other five types. (`N/tool/read_n1.py:40–42`, `164–170`, `202`.) |
| Every tleave round needs a positive late `STATE_CHANGED` | `no_control` exercises absence. No red case exercises present-but-nonpositive delay. (`N/tool/read_n1.py:102–107`, `172–178`, `203`.) |
| N1c equal/overlapping ranges are NE | `equal` exercises equality. (`N/tool/read_n1.py:126–127`, `189–191`, `204`.) |
| N1c reversed separation is FAIL | `reversed_`. (`N/tool/read_n1.py:193–195`, `205`.) |
| Correct `anyInputRegistered` value required | `no_anyinput` exercises false in `uni1ai`; no opposite-direction red case for `uni1`. (`N/tool/read_n1.py:68–69`, `197–199`, `206`.) |
| Output, measured record and `done` required; fatal rejected | None. (`N/tool/read_n1.py:48–61`, `70–72`, `201–206`.) |
| Environment mode/option and unipoll init required | None. (`N/tool/read_n1.py:62–67`, `201–206`.) |
| Capped settle rejected | None. (`N/tool/read_n1.py:74–75`, `201–206`.) |
| Nonempty operations, each with a late-callback record | None. (`N/tool/read_n1.py:76–78`, `201–206`.) |
| Missing N1c round/delay gives NE | None. (`N/tool/read_n1.py:116–121`, `201–206`.) |
| Full late-callback observation, child exits, duplicate cells, invocation completeness | No implemented checks and no red cases. (`N/tool/read_n1.py:45–79`, `87–95`, `201–206`.) |

**Read:** the requested `N/smoke-n1/NOTES.md` does not exist at the supplied path. Its purported additional rules could not be reviewed; the available self-test record confirms the six cases listed above. (`ev/review/REVIEW-BRIEF-two-seat-1.md:29`; `N/smoke-n1/self-test.txt:1–8`.)

## 6. The three fixed questions

**COUNTEREXAMPLE — inferred from read source: unipoll does not make every UNO slot synchronous.**

The comment path calls `.uno:Escape` without requesting completion notification. Under unipoll, `doc_postUnoCommand` omits its injected `SynchronMode=false`, but omission is not equivalent to forcing `SYNCHRON`: the dispatch controller defaults to `RECORD`, and Escape is an `Asynchron` slot. `SfxDispatcher::Execute_` therefore posts the request and returns before executing its effect. (`src/probe_engine.cpp:2875–2880`; `lo/desktop/source/lib/init.cxx:5314–5322`, `5513–5521`; `lo/sfx2/source/control/unoctitm.cxx:619–632`; `lo/sw/sdi/swriter.sdi:1181–1191`; `lo/sfx2/source/control/dispatch.cxx:740–757`.)

**Inferred:** moving that call out of the callback, as already specified, removes the callback re-entry but does not change the slot’s asynchronous dispatch mode. Withdraw the blanket statement that all such commands finish inside their LOK calls. This counterexample does not by itself refute the narrower synchronous Backspace/Delete proof. (`spec:22`, `140–141`; cited dispatch path above.)

For the fixed questions individually:

1. **NONE for a demonstrated interleaving inside the ordinary supported key-and-undo path. Read:** unipoll runs the key event inline and removes the accelerator’s extra posted hop. On the WASM system loop, `Reschedule` returns without yielding and `Yield` aborts. (`lo/sfx2/source/view/lokhelper.cxx:1283–1288`; `lo/svtools/source/misc/acceleratorexecute.cxx:213–226`; `lo/vcl/source/app/svapp.cxx:400–406`, `494–502`.) **Inferred:** absence of interleaving remains a required premise, not a consequence of the word “unipoll” for arbitrary commands. The existing diagnostic drain command explicitly invokes the test-only idle pump, and the existing poll guard documents nested pumping. Its inclusion in v23 must not silently contradict the universal no-pumping rule. (`src/probe_engine.cpp:6166–6178`, `6822–6834`; `spec:140`.)

2. **SHOULD. Read/inferred:** “returned, then next poll” is a coherent completion location for effects and callbacks established to precede that poll. N1’s bounded observation does not establish that premise universally; question 1 identifies the gap. Withdraw that stronger evidentiary claim. (`spec:97`, `162`, `178`; `N/tool/oc_native.cpp:483–503`; `N/tool/read_n1.py:87–95`.)

3. **NONE against the default policy. Read:** Writer explicitly restores the caret and declines Backspace when probing crosses a table/cell boundary. Forward Delete similarly probes, restores, and can decline deletion. A selected frame/graphic/OLE/drawing object follows an object-deletion path. Those are concrete Writer behaviours, rather than a uniform SDK refusal. (`lo/sw/source/uibase/wrtsh/delete.cxx:139–164`, `194–236`, `335–402`.) **Read:** the spec leaves the product arms for these cases pending. It must not describe them as already measured under C. (`spec:163`, `202`.)

**NOTE — inferred:** actual product reachability and completion on table and as-character-object cases require the already promised §9.3 arms, recording the key’s before/after state and undo payload. No build or browser result is asserted here. (`spec:202`.)

## 7. Completion vocabulary

**NONE — read:** I found no incompatible tuple required by the specified mapping:

| Operation | Required accepted tuple |
|---|---|
| Move | `changed:false`, unchanged revision, `documented-callback-*` or `verified-move-readback`. (`client:146–148`, `355–360`.) |
| Effective caret deletion | `changed:true`, revision +1, `verified-key-undo` with integral `actionsAfter ≥ 1`. (`client:161–166`, `375–377`; `spec:124`.) |
| Unchanged caret deletion | `verified-boundary-noop`, `changed:false`, unchanged revision. (`client:372–374`; `spec:124`, `131`.) |
| Explicit `delete-selection` | Mutation completion `uno-command-result`, `changed:true`, revision +1. (`client:176–197`, `383–390`; `src/probe_engine.cpp:5607–5625`.) |

**Read:** the retained `judgeAfterKey` refuses a changed but unparseable/empty undo payload; it does not verify `actionsAfter:0`. The spec also requires unchanged caret **and** selection before calling a deletion a boundary no-op. Those two suggested malformed replies therefore contradict the proposed rules rather than follow from them. (`src/merge_key_undo.hpp:399–413`; `spec:124`.)

**Inferred:** the range-delete mapping remains compatible only when it means the existing `delete-selection` action. Returning `uno-command-result` for an action still named `delete-backward` or `delete-forward` would be rejected, because classification uses the action name. The existing code and “as today” wording preserve that distinction; I do not count an imagined renaming as a counterexample. (`client:193–197`, `362–390`; `spec:125`; `src/probe_engine.cpp:5607–5625`.)

## 8. `anyInput`, scheduler ordering and pacing

**COUNTEREXAMPLE — inferred from read source:**

1. Tick A polls, executes a command, and leaves its reply pending.
2. Tick B dispatches its flush user event and returns.
3. Tick C has no user event at entry. `CheckTimeout()` runs a due scheduler task **before** the `anyInput` test. Only after that task returns does true `anyInput` allow the poll to send the reply.

Thus the reply waits behind that task although the pending-reply term is true throughout. (`lo/vcl/headless/svpinst.cxx:442–455`, `471–481`.)

**Read:** the scheduler directly invokes the task; the client’s `anyInput` is not a preemption mechanism for that invocation. Writer’s document idle can run layout or field-update work. (`lo/vcl/source/app/scheduler.cxx:568–615`; `lo/sw/source/core/doc/DocumentTimerManager.cxx:175–213`.)

**Inferred:** this does not invalidate “send at the first following poll.” It invalidates a fixed one-tick timing guarantee inferred from that rule. Even the simple trace above needs a flush tick followed by a polling tick, and intervening user events can add more. Withdraw the stronger timing claim in §5.8 and the addendum. The source installs a requested 100 fps loop; it does not supply a bound on task duration or browser scheduling delay. (`spec:149`; `ev/review/ruling-fable-1-addendum-1.md:38`; `lo/vcl/headless/svpinst.cxx:308–316`, `442–478`.)

**NONE — inferred:** for a command that has already queued its complete flush before returning, the specified one-operation-per-poll rule prevents the next command overtaking that queued flush. The existing drain violates that rule, but the spec explicitly requires replacing it; that existing loop is not a new counterexample to the proposed implementation. (`src/probe_engine.cpp:6690–6750`; `spec:93`, `96`.)

**NOTE — inferred:** “no user event was dispatched at tick entry” is weaker than “no user event is pending when poll begins.” A scheduler task can post an event, and `ImplYield` performs no second user-event check before polling. Whether a reply-dependent flush takes that route in the relevant arms needs a timeline of scheduler execution, flush posting and poll entry on the diagnostic profile. (`lo/vcl/headless/svpinst.cxx:442–478`; `lo/desktop/source/lib/init.cxx:2578–2587`.)

**NONE — read/inferred:** I found no source proof that making poll nonblocking itself starves the scheduler: `CheckTimeout()` still precedes poll on event-free ticks. Browser/pthread pacing remains a measurement, not an established starvation defect. (`lo/vcl/headless/svpinst.cxx:303–315`, `442–478`.)

## 9. Model C

**SHOULD — read/inferred: retain the result as a conditional model result and withdraw broader interpretations.**

**Read:** C’s zero is earned within explicitly constructed premises: `syncKey` applies the operation immediately; changed geometry schedules a flush; the engine phase waits for `lokIdle()`; and a reply is scheduled as a later engine action. These premises are meaningful, but the model does not derive them from core execution. (`model:423–437`, `606–618`, `649–659`.)

**Read:** the two mutations independently weaken reply placement and flush atomicity. Neither models a missing pending-reply term, blocking WASM poll, or scheduler task running before poll. The README already correctly withdraws discrimination of one-command-per-poll. The generator has no scheduler action corresponding to the tick sequence in question 8. (`model:330–337`, `608–618`, `1660–1677`; `ev/model/README.md:42–57`.)

**Inferred:** the untested premise most relevant beyond that acknowledged limitation is that every required state update is scheduled before the model reaches its permitted reply point. Delayed task-generated callbacks are absent from this state space. The model therefore cannot independently validate N1a or the stronger core-quiescence interpretation of §5.2. (`model:423–437`, `445–470`, `606–618`; `spec:178`.)

**Read:** “forged” checks only selection rectangles and caret geometry. It does not inspect a serialized revision, `changed`, action name, completion string, undo proof, or document/format state. (`model:661–683`.)

**Inferred:** a reply can therefore carry current geometry while falsely reporting `verified-boundary-noop` after an edit, or lack the undo proof required by the client, without satisfying this forged predicate. Checking that completion names occur somewhere does not establish that each occurrence has the required meaning. Withdraw “empty forged class” as a claim about every way the page can be misled; its demonstrated meaning is geometry-cache agreement. (`model:665–678`, `1656–1658`; `client:161–166`, `372–390`.)

**Read/inferred:** comparing text, caret and mark is the right improvement over text-only end-state comparison: it catches misplaced carets and differing selection direction. It is still only the modeled end state. The oracle shares `applyKey` with the implementation model, and insertion formatting at a collapsed caret is omitted, so it does not independently establish Writer’s full semantics. (`model:151–154`, `173–190`, `259–293`, `649–652`, `1396`.)

**Inferred:** the defensible conclusion is: under the model’s synchronous-operation, flush and polling assumptions, the enumerated scenarios finish with equal modeled state and equal reply geometry. The broader implementation and reply-truthfulness claims remain outside that zero. (`model:79–90`, `1378–1398`; `ev/model/README.md:24–29`.)