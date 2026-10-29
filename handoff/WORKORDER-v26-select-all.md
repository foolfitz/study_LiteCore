# Work order: Ctrl+A select-all as a candidate for the next engine batch (v26)

Opened 2026-10-29 ~22:10 +0800. Owner decision (zh-TW, translated): **"A: put it into the next engine batch."**
The owner noticed on host 0.2.40 that Ctrl+A does not select all. It is **not a regression**: 0.2.38 and 0.2.39
behave the same. Nothing is implemented; the first deliverable is a research note, not code.

## What is already true (read from the tree 2026-10-29; re-read before relying on it)

- **The engine has the action.** `select-all` is id **21** (`OXSDK_EDITOR_V3_SELECT_ALL`, `wasm_sdk_probe/src/editor_api.h:149-158`,
  `editor_api.cpp:156`). In `probe_engine.cpp` (~`:6508`) `OXSDK_EDITOR_SELECT_ALL` is posted on the KEY path as
  `Key::A | EditorMod1Modifier`, deliberately not through the uno-mutation route (that route would advance the revision
  for an edit that never happened -- finding 067's engine half): `mutation = false`, no revision advance.
- **The manifest withholds it.** v25's `editorContract.actions["select-all"]` is
  `{"id": 21, "gestures": [], "limits": ["withheld-pending-characterisation"]}`. Withheld is not absent: the engine
  initialises every gesture entry to all-permitted on the first mask call, so an action OMITTED from the manifest
  ships wide open (`handoff/RUNBOOK-relink-v4.md:39-43`). Never "tidy" it out of the manifest.
- **The page deliberately does not bind Ctrl+A** (`wasm_sdk_probe/web/e2-editor-app.js` ~`:3149-3158`): on 2026-08-19 a
  geometric range (0,0)-(width,height) through `selectRange` reported success in ~0.5 s while the engine still reported a
  collapsed selection and nothing was painted. "A shortcut that looks like it worked and selected nothing is worse than
  no shortcut." The page's document-key map today is only Home/End (`DOCUMENT_KEY_ACTIONS`, `:3092`).
- **The v4 design intent** (`handoff/HANDOFF-2026-08-22-abi-4-is-linked-and-measured.md:206`, RUNBOOK `:163`):
  "Granting select-all later costs a measurement of what `.uno:SelectAll` does here, not another link."
- **Unknown -- the first question**: the ordered engine (v23+, `OXSDK_E2_V23_LINK_BATCH` / `OXSDK_MAINLOOP_ENGINE`) has no
  mention of select-all in its `ordered_*.inc` files. Whether `editorActionV2` id 21 still reaches the key path above on
  v25, is refused, or takes another route is **not known**. Find out by reading the dispatch for the v25 define set and
  by a native or mirror measurement with the gesture granted in a SCRATCH manifest (never in `dist/`).

## Deliverable 1: research note (zh-TW, `research/`), before any spec

Answer, with evidence marks (已觀察 / 讀原始碼 / 推論):

1. The v25 route of action 21 (above). If the ordered engine does not route it, granting needs an engine change and
   therefore the v26 link; if it does, granting may need only a manifest + page change -- but a manifest change is a
   new profile identity (the manifest sha is bound), so check what the identity rules require (spec v24/v25 sections
   4.5 and 5; "version is identity"; the agent memory note `e2b-structural-lessons`, not a repo file).
2. The postcondition to characterise (what "worked" means), measured, not assumed: the engine's selection state after
   select-all (range, both ends), the selection wash painted, and what follows on a whole-document range -- typing
   replaces (typed-insert route, finding 168's lessons), `delete-selection` (`range-cross` is granted in v25 with limit
   `not-characterised-in-tables-or-note-apparatus`), inline formats, copy/cut, undo. Documents with tables, frames,
   notes, and an empty document (finding 173's case).
3. Which gesture grant select-all would carry, and which other limits a whole-document range runs into.
4. The page binding: Ctrl+A / Cmd+A through `session.offers("select-all")` so that an unoffered profile still binds
   nothing (the reason it is unbound today must keep holding on every profile that withholds it).

## Then

A spec (zh-TW) for the v26 batch or a manifest-only successor, with criteria pinned before implementation and red cases
(an omitted-instead-of-withheld manifest must be red; a page that binds Ctrl+A on a withholding profile must be red;
the 2026-08-19 "reported success, selected nothing" shape must be red). Batch it with the other engine changes of the
next link (owner rules: changes needing a link are batched; the count chain is batched too). The relink itself is the
owner's (`make` / relink are never the agent's).

## Do not

Bind Ctrl+A to a geometric range again; omit `select-all` from any manifest; grant it without the characterisation;
edit frozen tools or generation manifests (derive successors).
