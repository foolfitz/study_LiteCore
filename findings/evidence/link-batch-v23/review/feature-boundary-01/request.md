Adversarial review of these completed ABI6 source units. Reply in English. No tools. Focus on concrete runtime bugs, accidental capability widening, old ABI drift, incorrect mapping/flags or false tests. No feature WASM/runtime result is claimed yet. Authorized delta: external IDs1,2,16..19 map internal1..6, ABI6 only on explicitFEATURE_ABI6 plus orderedV23, diagnostics remainABI5; six extend flags, range gestures handled by later exactmanifest; docmoves22/23 noextend, selectall21 remainswithheld. Full isolated product worker is copied from frozen v22 SHA0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350; the supplied diff is its ONLYchange, and existing exactruntimeABI handshake is retained. Shared Calc worker untouched. Client gates line extension by ABI6/actualgrants; legacy char extension must remain callable for the pending v19 expected-red. Identify file/line, a concrete causal mutation/input, and consequence; do not infer defects from missing runtime that is explicitly future. State NO_CONCRETE_FINDING when appropriate.

===== d98abffd =====
--- wasm_sdk_probe/build/archive/e2-editor-v22-f7a40bcc-worker-0d55bcfa/sdk-worker.js	2026-10-16 18:52:29.145410954 +0800
+++ wasm_sdk_probe/sdk/v23-feature-worker.js	2026-10-26 08:09:17.891997495 +0800
@@ -146,6 +146,17 @@
   "move-character-left",
   "move-character-right",
 ]);
+// Feature ABI6 widens only editorActionV2; legacy V1 keeps its two-move rule.
+const EDITOR_V23_EXTEND_ACTIONS = new Set([
+  "move-character-left", "move-character-right", "move-line-up",
+  "move-line-down", "move-line-home", "move-line-end",
+]);
+function featureExtendPermitted(action) {
+  return activeManifest?.profile === "e2-editor-v23"
+    && activeManifest?.editorContract?.abiVersion === 6
+    && EDITOR_V23_EXTEND_ACTIONS.has(action);
+}
+
 const EDITOR_V1_FORMAT_ACTIONS = new Set([
   "set-bold", "set-italic", "set-underline", "set-strikethrough",
 ]);
@@ -1575,6 +1586,7 @@
       const validMoveOption = paragraph
         ? payload.extendSelection === false
         : (EDITOR_V1_MOVE_ACTIONS.has(payload.action)
+           || featureExtendPermitted(payload.action)
            || payload.extendSelection === false);
       const validFormatOption = paragraph
         ? payload.enabled === false

===== c6d3db0d =====
commit c6d3db0d88c72581e1dfdcca9ffb8a714036c674
Author:     foolfitz <foolfitz@gmail.com>
AuthorDate: Mon Oct 26 08:13:55 2026 +0800
Commit:     foolfitz <foolfitz@gmail.com>
CommitDate: Mon Oct 26 08:13:55 2026 +0800

    Select ABI 6 and validate flags for the six existing moves
    
    Co-Authored-By: Codex <noreply@openai.com>

diff --git a/wasm_sdk_probe/src/editor_api.cpp b/wasm_sdk_probe/src/editor_api.cpp
index 68ca8362..d6eb7c79 100644
--- a/wasm_sdk_probe/src/editor_api.cpp
+++ b/wasm_sdk_probe/src/editor_api.cpp
@@ -91,8 +91,17 @@ enum InternalSelectionMethod : std::uint32_t {
 bool validRequest(oxsdk_request_id requestId) { return requestId != 0; }
 
 bool isMove(std::uint32_t action) {
+#ifdef OXSDK_E2_V23_FEATURE_ABI6
+  return action == OXSDK_EDITOR_V1_MOVE_CHARACTER_LEFT ||
+         action == OXSDK_EDITOR_V1_MOVE_CHARACTER_RIGHT ||
+         action == OXSDK_EDITOR_V3_MOVE_LINE_UP ||
+         action == OXSDK_EDITOR_V3_MOVE_LINE_DOWN ||
+         action == OXSDK_EDITOR_V3_MOVE_LINE_HOME ||
+         action == OXSDK_EDITOR_V3_MOVE_LINE_END;
+#else
   return action == OXSDK_EDITOR_V1_MOVE_CHARACTER_LEFT ||
          action == OXSDK_EDITOR_V1_MOVE_CHARACTER_RIGHT;
+#endif
 }
 
 bool isFormat(std::uint32_t action) {
diff --git a/wasm_sdk_probe/src/editor_api.h b/wasm_sdk_probe/src/editor_api.h
index a6991db3..534a60fe 100644
--- a/wasm_sdk_probe/src/editor_api.h
+++ b/wasm_sdk_probe/src/editor_api.h
@@ -44,8 +44,21 @@ extern "C" {
  * 4.1): a successor identity again.  Ids 1-21 inherited verbatim, 22 and 23
  * appended (move-document-start / -end, finding 142).  v8-v20 stay at 4: the
  * define keeps their preprocessed output what it was.
+ *
+ * 6 is selected only by OXSDK_E2_V23_FEATURE_ABI6: the same IDs 1-23,
+ * with extend_selection accepted by character and line moves (1,2,16-19).
+ * The feature manifest grants those six existing actions the three gesture
+ * classes. Diagnostic v23 builds retain ABI 5; the Document SDK ABI is separate.
  */
-#ifdef OXSDK_E2_V21_LINK_BATCH
+#if defined(OXSDK_E2_V23_FEATURE_ABI6)
+#if !defined(OXSDK_E2_V23_LINK_BATCH) || !defined(OXSDK_E2_V21_LINK_BATCH)
+#error "ABI6 feature requires the ordered v23 engine and inherited v21 actions"
+#endif
+#ifdef OXSDK_E2_V23_DIAGNOSTIC
+#error "ABI6 feature cannot be combined with diagnostic instrumentation"
+#endif
+#define OXSDK_EDITOR_ABI_VERSION 6u
+#elif defined(OXSDK_E2_V21_LINK_BATCH)
 #define OXSDK_EDITOR_ABI_VERSION 5u
 #else
 #define OXSDK_EDITOR_ABI_VERSION 4u
@@ -72,8 +85,8 @@ typedef enum oxsdk_editor_v1_action {
  * that exists to pin v1 is how a freeze test turns into something that follows
  * the implementation around.
  *
- * Neither flag is accepted by any of these: extend_selection is for the two
- * movement actions and enabled is for the four inline format actions, so both
+ * Neither flag is accepted by any of these: extend_selection is for movement
+ * actions admitted by the selected ABI and enabled is for the four inline format actions, so both
  * must be strictly 0 here (SPEC E2-B 5.11, negative matrix N7).
  *
  * set_paragraph_heading takes no level: narrowing 2 promises H1 only, so the
@@ -96,12 +109,12 @@ typedef enum oxsdk_editor_v2_action {
  *
  * MOVE_LINE_* are the caret movements the engine has always had and the product
  * ABI never named. They take the same shape as the two character movements and
- * are subject to the same rule below: `extend_selection` is accepted ONLY by
+ * retain the legacy ABI 4/5 rule: `extend_selection` is accepted ONLY by
  * the two character movements, NOT by these four. That is deliberate and it is
  * a narrowing, not an oversight -- a shift-selected line movement is a
  * selection this build has never classified, and granting it here would let a
  * caller build a range the gesture router cannot describe. It can be added
- * later by a version that measures it first.
+ * by ABI 6 under the feature-only selector, after its protocol boundary.
  *
  * DELETE_SELECTION is the one genuinely new behaviour. It exists because
  * `delete-backward` is characterised caret-only and cut runs on a range by
@@ -137,7 +150,7 @@ typedef enum oxsdk_editor_v3_action {
  *
  * Ctrl+Home / Ctrl+End (finding 142).  Caret moves like 1-2 and 16-19 --
  * revision unchanged, `changed: false`, completed by a caret callback or by
- * `verified-move-readback` -- and, like 16-19, they take NO extend_selection:
+ * `verified-move-readback` -- and they take NO extend_selection in every ABI:
  * Ctrl+Shift+Home/End is a selection this build has never classified.  Inside
  * a table, a header or a section Writer goes up one level per press
  * (L-142-steps); nothing here merges the presses.
@@ -159,7 +172,8 @@ typedef enum oxsdk_editor_v4_action {
 #define OXSDK_EDITOR_GESTURE_RANGE_CROSS 4u
 
 /*
- * extend_selection is accepted only by the two movement actions.
+ * extend_selection is accepted by character moves (1,2) in every ABI, and
+ * additionally by line moves (16-19) only in the ABI 6 feature build.
  * enabled is accepted only by the inline format actions
  * (SET_BOLD, SET_ITALIC, SET_UNDERLINE, SET_STRIKETHROUGH).
  * Both flags are strict 0/1 values. Mutations are revision guarded.

===== 9a0d171e =====
commit 9a0d171ea52208f0b662f45762b724c5c8b52363
Author:     foolfitz <foolfitz@gmail.com>
AuthorDate: Mon Oct 26 08:13:55 2026 +0800
Commit:     foolfitz <foolfitz@gmail.com>
CommitDate: Mon Oct 26 08:13:55 2026 +0800

    Expose six selection moves only for the advertised ABI 6 contract
    
    Co-Authored-By: Codex <noreply@openai.com>

diff --git a/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.d.ts b/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.d.ts
index 89a7f491..2d4dda45 100644
--- a/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.d.ts
+++ b/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.d.ts
@@ -87,12 +87,10 @@ export class NarrowEditorV2Client {
     : Promise<EditorV2InheritedResult>;
   action(action: EditorV2ParagraphAction,
          options?: RevisionOptions): Promise<EditorV2ActionResult>;
-  /**
-   * `extendSelection` is absent on purpose: the ABI refuses that flag for
-   * anything but the two character moves, so offering it here would type a
-   * call the engine rejects.
-   */
-  action(action: EditorV3AppendedAction,
+  /** ABI6 grants extension on the four existing line moves. */
+  action(action: Exclude<EditorV3AppendedAction, "delete-selection">,
+         options?: RevisionOptions & { extendSelection?: boolean }): Promise<EditorV2InheritedResult>;
+  action(action: "delete-selection",
          options?: RevisionOptions): Promise<EditorV2InheritedResult>;
   /** ABI 5's two moves: no `extendSelection`, for the reason above. */
   action(action: EditorV4AppendedAction,
@@ -102,7 +100,7 @@ export class NarrowEditorV2Client {
                 options?: RevisionOptions & { extendSelection?: boolean })
     : Promise<EditorV2InheritedResult>;
   moveLine(direction: "up" | "down" | "home" | "end",
-           options?: RevisionOptions): Promise<EditorV2InheritedResult>;
+           options?: RevisionOptions & { extendSelection?: boolean }): Promise<EditorV2InheritedResult>;
   delete(direction: "backward" | "forward",
          options?: RevisionOptions): Promise<EditorV2InheritedResult>;
   /** The caller makes the selection; this removes it.  No direction, no arity. */
@@ -127,6 +125,7 @@ export class NarrowEditorV2Client {
               end: { xTwips: number; yTwips: number },
               options?: AbortableOptions): Promise<unknown>;
   gesturesFor(action: EditorV4Action): EditorV2Gesture[] | null;
+  offersSelectionMove(action: EditorV4Action, gesture: EditorV2Gesture): boolean;
   limitsFor(action: EditorV4Action): string[];
   /**
    * SPEC-M3-link-batch 10.8: whether the profile declares the page-rectangles
diff --git a/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js b/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js
index 21a1a024..4993a102 100644
--- a/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js
+++ b/wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js
@@ -102,20 +102,18 @@ const MOVE_ACTIONS = new Set(["move-character-left", "move-character-right"]);
 // point: these inherit one somebody measured instead of getting a new one
 // nobody has.
 //
-// They are NOT in MOVE_ACTIONS, and that is deliberate rather than an
-// oversight: MOVE_ACTIONS is also what permits `extendSelection`, and the ABI
-// refuses that flag for anything but the two character moves
-// (editor_api.cpp:159).  A shift+Up that the client accepts and the engine
-// rejects is worse than one the client refuses.
+// Older ABIs permit extension only for character moves. ABI6 adds extension
+// on these existing IDs only when the active contract grants it; the move
+// postcondition is unchanged.
 const LINE_MOVE_ACTIONS = new Set([
   "move-line-up", "move-line-down", "move-line-home", "move-line-end",
 ]);
-// SPEC-M3-link-batch-v21 4.1: the same route again -- a posted key,
-// `mutation = false`, the 250 ms readback always armed -- so the same
-// postcondition, and at a document boundary (where Ctrl+Home is silent,
+// SPEC-M3-link-batch-v21 4.1: the same non-mutation move postcondition,
+// and at a document boundary (where Ctrl+Home is silent,
 // measured natively) the same `verified-move-readback` completion.  Not in
-// MOVE_ACTIONS, for the reason LINE_MOVE_ACTIONS is not: that set also permits
-// `extendSelection`, which the ABI refuses for anything but the character moves.
+// MOVE_ACTIONS: document extension remains refused, including on ABI6.
+// ABI6's ordered engine completes from its first poll rather than the legacy
+// 250ms readback; the accepted completion names and postcondition stay the same.
 const DOCUMENT_MOVE_ACTIONS = new Set(["move-document-start", "move-document-end"]);
 // FINDING 096.  The two completions a movement is allowed to come back with,
 // and the SECOND one is why this is a function rather than a prefix test.
@@ -237,6 +235,16 @@ export class NarrowEditorV2Client {
     return Array.isArray(spec?.gestures) ? spec.gestures : null;
   }
 
+  /** ABI6's six selection moves, for the actual advertised gesture only. */
+  offersSelectionMove(action, gesture) {
+    const contract = this.document._engine.manifest?.editorContract;
+    return contract?.abiVersion === 6
+      && (MOVE_ACTIONS.has(action) || LINE_MOVE_ACTIONS.has(action))
+      && ["collapsed", "range-single", "range-cross"].includes(gesture)
+      && this.gesturesFor(action)?.includes(gesture) === true
+      && !this.limitsFor(action).includes("no-extend-selection");
+  }
+
   /**
    * Whether this profile offers the action at all.
    *
@@ -410,11 +418,16 @@ export class NarrowEditorV2Client {
       );
     }
     const extendSelection = options.extendSelection ?? false;
+    const lineExtension = LINE_MOVE_ACTIONS.has(action)
+      && ["collapsed", "range-single", "range-cross"]
+        .some((gesture) => this.offersSelectionMove(action, gesture));
     if (typeof extendSelection !== "boolean"
-        || (!MOVE_ACTIONS.has(action) && extendSelection)) {
+        || (!MOVE_ACTIONS.has(action) && !lineExtension && extendSelection)) {
       throw new DocumentSdkError(
         "INVALID_ARGUMENT",
-        "extendSelection is a boolean restricted to character movement",
+        this.document._engine.manifest?.editorContract?.abiVersion === 6
+          ? "extendSelection requires character movement or an advertised ABI6 line move"
+          : "extendSelection is a boolean restricted to character movement",
       );
     }
     const enabled = FORMAT_ACTIONS.has(action) ? options.enabled : false;
