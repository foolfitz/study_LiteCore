// Every action the shipped profile declares must be reachable by a shipped shell.
//
// The four-way inventory check (tools/check_e2_b_inventory.py) asks whether the
// header, the manifest, the worker map and the client allowlists *name* the same
// actions.  They do.  What it cannot see is that it reaches the client side by
// taking the UNION of two shells, and one of those two refuses to attach to the
// v2 profile at all: editor-shell/editor-client.js gates on
// `narrow-editor-v1` AND `editorContract.version === 1`, and the v2 manifest
// says `narrow-editor-v2` and version 2.
//
// So "the four lists agree" and "a host can actually perform these fifteen
// actions" are different claims, and only the first one was ever checked.  This
// is the second one.  It runs against the manifests in dist/profiles, not
// against fixtures, because the question is about what shipped.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorClient } from "../../editor-shell/editor-client.js";
import { ParagraphEditorClient } from "../paragraph-editor-client.js";
import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";

const profileDir = (name) =>
  fileURLToPath(new URL(`../../dist/profiles/${name}/sdk-manifest.json`,
                        import.meta.url));

function manifestOf(profile) {
  return JSON.parse(readFileSync(profileDir(profile), "utf8"));
}

/** The action names a manifest declares, whichever shape it uses. */
function declaredActions(manifest) {
  const actions = manifest?.editorContract?.actions;
  return Array.isArray(actions) ? [...actions] : Object.keys(actions ?? {});
}

// A handle that records whether the shell issued an engine request.  Reaching
// the engine is the question; whether the stub's reply then satisfies the
// shell's postcondition rules is a different mechanism, and conflating the two
// would make a closed gate and a malformed stub look identical.
function handleFor(manifest) {
  const issued = [];
  return {
    handle: 1,
    revision: 0,
    issued,
    _assertUsable() {},
    _engine: {
      manifest,
      async _request(operation, payload) {
        issued.push({ operation, action: payload.action });
        return {
          action: payload.action,
          beforeRevision: payload.expectedRevision,
          revision: payload.expectedRevision,
          changed: false,
          state: {},
          completion: "documented-callback-stub",
        };
      },
    },
  };
}

const FORMAT_ACTIONS = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);

async function issues(handle, client, action) {
  const before = handle.issued.length;
  try {
    await client.action(action, FORMAT_ACTIONS.has(action) ? { enabled: true } : {});
  } catch {
    // Swallowed on purpose: a postcondition complaint still means the request
    // left the shell, and that is what is being counted.
  }
  return handle.issued.length > before;
}

const SHELLS = [
  ["editor-shell/editor-client.js", NarrowEditorClient],
  ["editor-shell-v2/paragraph-editor-client.js", ParagraphEditorClient],
  ["editor-shell-v2/narrow-editor-v2-client.js", NarrowEditorV2Client],
];

/** Which of `actions` any shipped shell can get as far as the engine with. */
async function reachableOn(profile, actions) {
  const manifest = manifestOf(profile);
  const reached = new Set();
  for (const [, Client] of SHELLS) {
    const handle = handleFor(manifest);
    const client = new Client(handle);
    for (const action of actions)
      if (await issues(handle, client, action)) reached.add(action);
  }
  return reached;
}

test("every action the v2 profile declares is reachable by a shipped shell",
     async () => {
       const declared = declaredActions(manifestOf("e2-editor-v2"));
       assert.equal(declared.length, 15,
                    "the v2 contract is expected to declare fifteen actions");
       const reached = await reachableOn("e2-editor-v2", declared);
       const unreachable = declared.filter((a) => !reached.has(a)).sort();
       assert.deepEqual(unreachable, [],
                        "declared by the manifest, reachable by no shipped shell");
     });

test("control: the v1 shell reaches all ten on the v1 profile", async () => {
  // Without this the test above could pass by measuring nothing at all.
  const declared = declaredActions(manifestOf("e1-editor-v1"));
  const reached = await reachableOn("e1-editor-v1", declared);
  assert.equal(declared.length, 10);
  assert.deepEqual(declared.filter((a) => !reached.has(a)), []);
});

test("control: an action no manifest declares is reachable by nobody",
     async () => {
       // And without this, a shell that let everything through would look like
       // a shell that satisfies the contract.
       const reached = await reachableOn("e2-editor-v2", ["set-superscript"]);
       assert.deepEqual([...reached], []);
     });
