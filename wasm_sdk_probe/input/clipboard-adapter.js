import { InputAdapterError, summarizeUnicode } from "./input-adapter.js";

export class ClipboardAdapterError extends InputAdapterError {
  constructor(code, message, details = {}) {
    super(code, message, details);
    this.name = "ClipboardAdapterError";
  }
}

function typedClipboardError(error, operation) {
  if (error instanceof ClipboardAdapterError)
    return error;
  const denied = ["NotAllowedError", "SecurityError"].includes(error?.name);
  return new ClipboardAdapterError(
    denied ? "CLIPBOARD_DENIED" : "CLIPBOARD_UNAVAILABLE",
    denied
      ? `clipboard ${operation} was denied`
      : `clipboard ${operation} is unavailable`,
    { operation, browserErrorName: error?.name || "Error" },
  );
}

/**
 * User-intent boundary for text/plain clipboard operations.
 *
 * Browser permission and user-gesture checks stay outside the Document SDK.
 * Only a successful read produces one HostInputAdapter commit.
 */
export class PlainTextClipboardAdapter {
  constructor(options = {}) {
    if (!options.inputAdapter)
      throw new TypeError("PlainTextClipboardAdapter requires inputAdapter");
    this._input = options.inputAdapter;
    this._clipboard = options.clipboard ?? globalThis.navigator?.clipboard ?? null;
    this._secureContext = options.secureContext ?? globalThis.isSecureContext === true;
    this._getSelection = options.getSelection || null;
    this._onTrace = options.onTrace || (() => {});
  }

  _trace(operation, fields = {}) {
    this._onTrace({ operation, ...fields });
  }

  _assertAvailable(method) {
    if (!this._secureContext || typeof this._clipboard?.[method] !== "function") {
      throw new ClipboardAdapterError(
        "CLIPBOARD_UNAVAILABLE",
        `clipboard ${method} requires a secure context and browser support`,
        { secureContext: this._secureContext, method },
      );
    }
  }

  async copySelection(metadata = {}) {
    if (typeof this._getSelection !== "function") {
      throw new ClipboardAdapterError(
        "CLIPBOARD_UNAVAILABLE", "selection provider is unavailable",
      );
    }
    this._assertAvailable("writeText");
    const selection = await this._getSelection();
    if (selection?.mimeType !== "text/plain;charset=utf-8") {
      throw new ClipboardAdapterError(
        "UNSUPPORTED_CLIPBOARD_TYPE",
        "only text/plain;charset=utf-8 selections can be copied",
        { mimeType: selection?.mimeType || null },
      );
    }
    if (!selection.text) {
      throw new ClipboardAdapterError(
        "CLIPBOARD_EMPTY_SELECTION", "there is no selected text to copy",
      );
    }
    try {
      await this._clipboard.writeText(selection.text);
    } catch (error) {
      const typed = typedClipboardError(error, "write");
      this._trace("copy", { status: "failed", code: typed.code, mutation: false });
      throw typed;
    }
    const summary = summarizeUnicode(selection.text);
    this._trace("copy", {
      status: "passed", mutation: false, revision: selection.revision, ...summary, metadata,
    });
    return { ...summary, revision: selection.revision };
  }

  async pasteFromClipboard(options = {}) {
    if (options.userGesture !== true) {
      const error = new ClipboardAdapterError(
        "CLIPBOARD_DENIED", "clipboard read requires an explicit user gesture",
        { userGesture: false },
      );
      this._trace("paste", { status: "rejected", code: error.code, mutation: false });
      throw error;
    }
    this._assertAvailable("readText");
    let text;
    try {
      text = await this._clipboard.readText();
    } catch (error) {
      const typed = typedClipboardError(error, "read");
      this._trace("paste", { status: "failed", code: typed.code, mutation: false });
      throw typed;
    }
    if (!text) {
      this._trace("paste", { status: "empty", mutation: false });
      return { committed: false, reason: "empty" };
    }
    const result = await this._input.commitClipboardText(text, {
      userGesture: true,
      clipboardSource: "async-api",
      ...options.metadata,
    });
    this._trace("paste", { status: "passed", mutation: true, ...summarizeUnicode(text) });
    return result;
  }

  async pasteEvent(event, metadata = {}) {
    event?.preventDefault?.();
    const types = Array.from(event?.clipboardData?.types || []);
    const hasPlain = types.length === 0
      ? typeof event?.clipboardData?.getData === "function"
      : types.includes("text/plain") || types.includes("Text");
    if (!hasPlain) {
      const error = new ClipboardAdapterError(
        "UNSUPPORTED_CLIPBOARD_TYPE",
        "clipboard does not contain text/plain",
        { types },
      );
      this._trace("paste-event", { status: "rejected", code: error.code, mutation: false, types });
      throw error;
    }
    const text = event?.clipboardData?.getData?.("text/plain") ?? "";
    if (!text) {
      this._trace("paste-event", { status: "empty", mutation: false, types });
      return { committed: false, reason: "empty" };
    }
    const result = await this._input.commitClipboardText(text, {
      source: "clipboard-event",
      isTrusted: event?.isTrusted === true,
      htmlPresent: types.includes("text/html"),
      ...metadata,
    });
    this._trace("paste-event", {
      status: "passed", mutation: true, types, ...summarizeUnicode(text),
    });
    return result;
  }
}

