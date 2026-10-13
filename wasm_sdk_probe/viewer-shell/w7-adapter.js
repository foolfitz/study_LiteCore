// THE ONLY PLACE IN THE VIEWER THAT KNOWS W7 IS MISSING.
//
// `handoff/PLAN-2026-09-03-ods-reading.md` §6 W7 (engine + worker source:
// `format` allowlist {odt, ods}, `documentType` on `opened`, `set_part` /
// `part_name` exports, a capability bit) does not exist yet.  The viewer draft
// has to run anyway, so every place where it would have asked W7 a question and
// cannot is HERE, and every answer given in W7's absence says so in the state
// (`adapterFallbacks`), never by quietly looking like W7's answer.
//
// The pre-W7 list -- delete the matching branch below when W7 supplies the thing:
//
//   1. NAME SPOOF.  `oxsdk_document_open` refuses a name not ending `.odt`
//      (finding 013).  A `.ods` file is handed over as `<stem>.odt`; content
//      detection then reads the zip's own `mimetype`.  Recorded as
//      `nameSpoofed: true`.  W7 removes it (the manifest lists `OPEN_ODS`).
//   2. DOCUMENT TYPE.  The handle's `documentType` if there is one, else the
//      string `UNKNOWN_DOCUMENT_TYPE`.  A KNOWN type that is not "spreadsheet"
//      is refused by the session; an unknown one cannot be.
//   3. PART NAMES.  The handle's `partNames` if present and consistent, else
//      `工作表 1..N` with `namesFromEngine: false`.
//   4. PART SWITCH.  A handle without `setPart` cannot switch: a request for
//      part k > 0 is refused with a typed error, and the tab is rendered
//      disabled with `PART_SWITCH_DISABLED_REASON`.  There is no faked switch
//      that repaints part 0 under another tab.
//   5. PART READ-BACK.  `handle.currentPart` if the engine supplies one, else
//      `null`.  The viewer never echoes the requested part in its place.
//
// Names below that W7 will have to match are ASSUMPTIONS written down here so
// the day W7 lands they can be checked in one place: the capability string
// `open-ods`, and the handle members `documentType`, `partNames`,
// `setPart(k, options)` and `currentPart`.
import { ViewerError } from "./viewer-error.js";

export const UNKNOWN_DOCUMENT_TYPE = "unknown (pre-W7)";
export const SPREADSHEET = "spreadsheet";
export const OPEN_ODS_CAPABILITY = "open-ods";
export const PART_SWITCH_DISABLED_REASON =
  "引擎尚無分頁切換（W7 的 set_part），目前只能顯示開檔時的那一頁";

export const FALLBACK = Object.freeze({
  NAME_SPOOFED: "name-spoofed",
  DOCUMENT_TYPE_UNKNOWN: "document-type-unknown",
  PART_NAMES_SYNTHESISED: "part-names-synthesised",
  PART_SWITCH_UNAVAILABLE: "part-switch-unavailable",
  PART_READBACK_UNAVAILABLE: "part-readback-unavailable",
});

function engineAcceptsOds(manifest) {
  return Array.isArray(manifest?.capabilities)
    && manifest.capabilities.includes(OPEN_ODS_CAPABILITY);
}

// The name to hand `engine.open`, and whether it was changed.  Only a `.ods`
// name is ever rewritten, and only when the engine does not list the capability;
// any other name goes through untouched so the engine's own extension check
// still refuses what it refuses (an `.xlsx` is a typed engine refusal, not a
// file this viewer quietly relabels).
export function engineOpenName(fileName, manifest) {
  const name = String(fileName || "").trim() || "viewer-input.ods";
  if (/\.ods$/i.test(name) && !engineAcceptsOds(manifest))
    return { openName: name.replace(/\.ods$/i, "") + ".odt", nameSpoofed: true };
  return { openName: name, nameSpoofed: false };
}

function synthesisedNames(parts) {
  return Array.from({ length: parts }, (_, index) => `工作表 ${index + 1}`);
}

// What the session may do with an opened document, and nothing else: the view
// exposes render / setPart / close and the read-only facts below.  A viewer that
// can only reach the engine through this object cannot call `click`,
// `insertText`, `save`, ... by accident.
export function adaptHandle(handle) {
  const parts = handle?.parts;
  if (!Number.isInteger(parts) || parts < 1) {
    throw new ViewerError("BAD_HANDLE",
      `the engine opened a document with parts=${JSON.stringify(parts)}`, { parts });
  }
  const fallbacks = [];

  const typeKnown = typeof handle.documentType === "string" && handle.documentType !== "";
  const documentType = typeKnown ? handle.documentType : UNKNOWN_DOCUMENT_TYPE;
  if (!typeKnown)
    fallbacks.push(FALLBACK.DOCUMENT_TYPE_UNKNOWN);

  const namesUsable = Array.isArray(handle.partNames)
    && handle.partNames.length === parts
    && handle.partNames.every((entry) => typeof entry === "string" && entry !== "");
  const partNames = namesUsable ? handle.partNames.slice() : synthesisedNames(parts);
  // A names array that EXISTS but disagrees with `parts` is W7 being wrong, which
  // is different from W7 being absent; it is kept apart so it is not read as the
  // second.
  const partNamesProblem = !namesUsable && handle.partNames !== undefined
    ? `partNames is not ${parts} non-empty strings` : null;
  if (!namesUsable)
    fallbacks.push(FALLBACK.PART_NAMES_SYNTHESISED);

  const canSwitchParts = typeof handle.setPart === "function";
  if (!canSwitchParts)
    fallbacks.push(FALLBACK.PART_SWITCH_UNAVAILABLE);

  const readBackExists = Number.isInteger(handle.currentPart);
  if (!readBackExists)
    fallbacks.push(FALLBACK.PART_READBACK_UNAVAILABLE);

  return {
    parts,
    documentType,
    documentTypeKnown: typeKnown,
    partNames,
    namesFromEngine: namesUsable,
    partNamesProblem,
    canSwitchParts,
    partSwitchDisabledReason: canSwitchParts ? null : PART_SWITCH_DISABLED_REASON,
    fallbacks,

    get revision() { return handle.revision; },
    get widthTwips() { return handle.widthTwips; },
    get heightTwips() { return handle.heightTwips; },

    // The engine's own answer to "which part are you on", or null when it has
    // none.  Read fresh every time -- never cached from what was asked for.
    readBackPart() {
      return Number.isInteger(handle.currentPart) ? handle.currentPart : null;
    },

    render(region, options) {
      return handle.render(region, options);
    },

    async setPart(k, options = {}) {
      if (!canSwitchParts) {
        if (k !== 0) {
          throw new ViewerError("PART_SWITCH_UNAVAILABLE",
            `the engine has no part switch; part ${k} cannot be shown`,
            { requested: k });
        }
        // Part 0 with nothing to switch: there is no engine call to make, and
        // the caller must not read this as "the engine confirmed part 0".
        return { switched: false, widthTwips: handle.widthTwips, heightTwips: handle.heightTwips };
      }
      const result = await handle.setPart(k, options);
      return {
        switched: true,
        widthTwips: Number.isFinite(result?.widthTwips) ? result.widthTwips : handle.widthTwips,
        heightTwips: Number.isFinite(result?.heightTwips) ? result.heightTwips : handle.heightTwips,
      };
    },

    close(options) {
      return handle.close(options);
    },
  };
}
