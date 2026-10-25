# Host 0.2.37 — installed Calc range formatting and autosave

**Installed 0.2.37 / 2f7a1193e3c296ea1c51dabe470fd2b289d3279b / package 754ae8eafd15edda.** Actual Files acceptance **54/54**, four independently parsed server ODS snapshots, two views / 56 actual DOM tiles compared with direct engine rendering. All seven reader controls reject incomplete/false/wrong-identity/cleanup-fallback reports.

```bash
python3 wasm_sdk_probe/tools/read_calc_range_autosave_host.py findings/evidence/host-0.2.37/range-autosave-host-01 --release findings/evidence/host-0.2.37/release.json --safety-dir findings/evidence/host-0.2.37 --red-cases
```

The owner built native/wasm against existing cores. Frozen **ods-editor-v2 / wasm 5bc53490 / worker 0bed22bd**, capability bits 522291, retains the owner's exact six file hashes. Native **22/22**; final range cohort `range-browser-03` **240/240**; final autosave `auto-v2-02` **108/108**; cell regression `cell-v2-02` **62/62**. See the [feature evidence](../calc-range-autosave/README.md). Source units 59 plus four independent XML tests pass; the focused format-entry mutation census rejects 15/15.

The package has 46 files, 525,930,091 raw / 175,268,233 gzip / 128,021,753 zstd bytes. **35 complete predecessor records are identical**; four existing Calc files changed, six v2 engine files and one autosave module were added, and the six v1 engine paths left the served package. The old frozen profile and package archive remain intact. Writer e2-editor-v22 / f7a40bcc and readonly ods-viewer-v3 / ebb7e0cb page/module/wasm identities are unchanged. E1-C intact.

Exact archives:

- `wasm_sdk_probe/build/archive/ods-editor-v2-5bc53490-worker-0bed22bd`
- `wasm_sdk_probe/build/archive/host-0.2.37-engine-754ae8eafd15edda`
- Predecessor `wasm_sdk_probe/build/archive/host-0.2.36-engine-2b17a0e790b24eb3`

The package and rollback were prepared in an isolated worktree, archived and committed before live mutation. Offline package verification had zero problems and **22/22** red cases. Guarded installation at 20:06:08–20:06:22 Asia/Taipei fast-forwarded the host, copied the exact archive, successfully upgraded to 0.2.37, left maintenance disabled, and returned 401 for all three unauthenticated page routes. `install-0.2.37.sh` is historical and deliberately requires the recorded 0.2.36 parent; **do not rerun it against current main**. Rollback was prepared but not executed; it restores the exact 0.2.36 engine while retaining host label 0.2.37.

Actual Files tested trusted Shift selection and toolbar mixed/on/off B/I/U; production idle autosaves through real conditional WebDAV PUT with the owned lock token and ODS MIME; independent GET bytes/styles/content; unconfirmed draft retention beyond 30 seconds; new trusted typing during one held real native export; cancel, normal leave, reopen, and normal lock release. Read-only shares route to the unchanged viewer without save controls/API or locks. Mock successful host outcomes are not used here. `range-autosave-host-01/report.json` has `ownedUnlocks: []`; all normal releases succeeded, temporary share/user/folder deletion succeeded, and independent queries show folder 404/user absent.

Before/after snapshots and `post-test-identity.json` establish owner file 24920 unchanged (31,008 bytes, sha256 a84629657cf01ea0adeb26991c6f62932e2df601637ecaee0b1fa6721afa6adb), unrelated lock list exactly `[24674]`, and identical ddev states: litecore running as found, fgp-nc/nc-bridge paused, others stopped. No global lock-table writes or root commands. Live engine bytes were directly compared with the immutable archive after testing. The isolated worktree was independently compared, then removed; branch `host-0.2.37` and both archives remain.

Astra `/root/astra_calc_scope` independently read release, preservation and host results and authorized finite closure. Full K/global pins/BINDING/chain remain deferred; nominal shipped host stays 0.2.26, section 34.4 +0/+0, cumulative 47/27. Autosave saves confirmed model changes; active drafts/IME are not forcibly committed. The pre-existing ordinary cell-commit key-reception limitation remains unmeasured follow-up, not a new human gate.
