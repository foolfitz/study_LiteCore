// The read-only spreadsheet viewer's SDK (specs/SPEC-M4-ods-in-nextcloud.md
// §3.3; the owner's D3 = A).
//
// The SHIPPED DocumentEngine, subclassed rather than copied: one protocol, and
// zero bytes change under sdk/ (shell generation v75,
// e2/editor-shell-v2-bundle-v75.json, hashes sdk/document-sdk.js).  What it
// adds is the viewer's four queries, through the shipped `_request`, and what
// it hands back is the shipped DocumentHandle with five members put on it --
// `documentType`, `partNames`, `currentPart`, `setPart(k)` and `partText(k)` --
// which are the names viewer-shell/w7-adapter.js reads.
//
// REGISTERED COUPLING (L-viewer-sdk-private-surface): this file depends on the
// shipped module's private surface -- `_request`, `_initialize` (the page calls
// it), the open reply passing through `_request`, and DocumentHandle's
// `handle` and `_assertUsable`.  If document-sdk.js changes one of those, the
// unit test of this file and E5/E9 on the real worker turn red; nothing else
// guards it, on purpose (review C5).
//
// The queries are used only when the profile declares them: a profile without
// `part-switch` gets the plain handle, and the adapter then says what it had
// to stand in for (the mirror runs on e2-editor-v14 are such a profile).
import { DocumentEngine, DocumentSdkError } from "../sdk/document-sdk.js";

export const PART_SWITCH_CAPABILITY = "part-switch";
export const PART_TEXT_CAPABILITY = "part-text";
// SPEC-M4-viewer-v2 3.2 (finding 157): ods-viewer-v2's engine only.
export const PART_INFO_CAPABILITY = "part-info";

function declares(manifest, capability) {
  return Array.isArray(manifest?.capabilities) && manifest.capabilities.includes(capability);
}

// LOK's getPartInfo JSON (ScModelObj::getPartInfo: `visible` 0 or 1, through
// tools::JsonWriter) -> a boolean.  Anything else is not guessed at.
export function partVisibleFromInfo(info, part) {
  let parsed;
  try {
    parsed = JSON.parse(info);
  } catch (error) {
    throw new DocumentSdkError("PART_INFO_UNPARSEABLE", `part ${part}: getPartInfo is not JSON: ${String(info).slice(0, 80)}`);
  }
  const visible = parsed?.visible;
  if (visible === 1 || visible === "1")
    return true;
  if (visible === 0 || visible === "0")
    return false;
  throw new DocumentSdkError("PART_INFO_UNPARSEABLE",
    `part ${part}: getPartInfo's visible is ${JSON.stringify(visible)}, not 0 or 1`);
}

function requirePart(part, operation) {
  if (!Number.isInteger(part) || part < 0)
    throw new DocumentSdkError("INVALID_ARGUMENT", `${operation} requires a non-negative integer part`);
}

export class OdsViewerEngine extends DocumentEngine {
  // The open reply carries the engine's `documentType` and `inputSuffix`, and
  // the shipped DocumentHandle keeps only the fields it knows; the reply is
  // read here, on its way through, and nowhere else.
  _request(operation, payload = {}, options = {}, transfer = []) {
    const reply = super._request(operation, payload, options, transfer);
    if (operation === "open")
      return reply.then((result) => { this._openReply = result; return result; });
    return reply;
  }

  async open(input, options = {}) {
    this._openReply = null;
    const handle = await super.open(input, options);
    const reply = this._openReply || {};
    this._openReply = null;
    if (typeof reply.documentType === "string")
      handle.documentType = reply.documentType;
    if (typeof reply.inputSuffix === "string")
      handle.inputSuffix = reply.inputSuffix;
    if (declares(this.manifest, PART_SWITCH_CAPABILITY))
      await this._addPartQueries(handle, options);
    if (declares(this.manifest, PART_TEXT_CAPABILITY))
      this._addPartText(handle);
    return handle;
  }

  async _addPartQueries(handle, options) {
    const engine = this;
    const request = (operation, payload, callOptions = {}) => {
      handle._assertUsable();
      return engine._request(operation, { documentHandle: handle.handle, ...payload },
                             { timeoutMs: options.timeoutMs, ...callOptions });
    };
    // What the engine is ON, read; never the part that was asked for.
    handle.currentPart = (await request("currentPart", {})).part;
    const names = [];
    for (let part = 0; part < handle.parts; part += 1)
      names.push((await request("partName", { part })).name);
    handle.partNames = names;
    // SPEC-M4-viewer-v2 3.2: which parts core has a tab for.  A failure here
    // does not fail the open: the handle then has no `partVisible`, says why in
    // `partInfoProblem`, and the adapter reports that it had to assume.
    if (declares(engine.manifest, PART_INFO_CAPABILITY)) {
      try {
        const visible = [];
        for (let part = 0; part < handle.parts; part += 1)
          visible.push(partVisibleFromInfo((await request("partInfo", { part })).info, part));
        handle.partVisible = visible;
      } catch (error) {
        handle.partInfoProblem = `${error?.code || "ERROR"}: ${error?.message || String(error)}`;
      }
    }

    handle.readCurrentPart = async (callOptions = {}) => {
      handle.currentPart = (await request("currentPart", {}, callOptions)).part;
      return handle.currentPart;
    };
    // The reply's `part` is what the engine read back after the switch, and
    // that, not `part`, is what the handle says it is on.
    handle.setPart = async (part, callOptions = {}) => {
      requirePart(part, "setPart");
      const result = await request("setPart", { part }, callOptions);
      handle.currentPart = result.part;
      handle.widthTwips = result.width;
      handle.heightTwips = result.height;
      return { part: result.part, widthTwips: result.width, heightTwips: result.height };
    };
  }

  _addPartText(handle) {
    const engine = this;
    // E3's read-back: the engine switches, selects all, reads, deselects and
    // switches back on its own thread, and says which part it ended on.
    handle.partText = async (part, callOptions = {}) => {
      requirePart(part, "partText");
      handle._assertUsable();
      const result = await engine._request("partText", { documentHandle: handle.handle, part },
                                           callOptions);
      if (Number.isInteger(result.partAfter) && "currentPart" in handle)
        handle.currentPart = result.partAfter;
      return { part: result.part, text: result.text, textNull: result.textNull === true,
               selectAllConfirmed: result.selectAllConfirmed === true,
               partBefore: result.partBefore, partAfter: result.partAfter,
               // SPEC-M4-viewer-v2 3.3: v2's engine only, so v1's result keeps its keys.
               ...(Number.isInteger(result.selectAllWaitMs)
                 ? { selectAllWaitMs: result.selectAllWaitMs, selectAllDeadlineMs: result.selectAllDeadlineMs,
                     lateSelectAllResults: result.lateSelectAllResults }
                 : {}) };
    };
  }
}
