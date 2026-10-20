// The read-only spreadsheet viewer's session (DRAFT, plan W9 / gate G9).
//
// Opens bytes through an engine, owns a TileScheduler whose document context
// carries the PART (the sheet) being shown, and exposes the state the page
// renders.  It is read-only by construction: the only engine object it touches
// is the adapter's view, which has render / setPart / close and nothing that
// edits, types or saves.
//
// WHAT THIS FILE DOES NOT KNOW: that W7 (the engine's `documentType`, `set_part`,
// `part_name`, ods open) does not exist yet.  Everything that depends on that is
// in `w7-adapter.js`, and arrives here only as a value or as a typed error.  A
// test scans this directory to keep it that way.
//
// Imports `reader-shell/tile-scheduler.js` UNMODIFIED, and sits outside the five
// bundle-scoped directories, so the product page's import graph cannot reach it.
import { TileScheduler } from "../reader-shell/tile-scheduler.js";
import { probeOdfPackage } from "./odf-package-probe.js";
import { ViewerError } from "./viewer-error.js";
import { adaptHandle, engineOpenName, SPREADSHEET } from "./w7-adapter.js";

export { ViewerError } from "./viewer-error.js";

const DEFAULT_OPEN_TIMEOUT_MS = 180000;

function publicError(error, fallback) {
  return {
    code: error?.code || fallback,
    message: error?.message || String(error),
    details: error?.details || {},
  };
}

export class OdsViewerSession {
  // `engineFactory({ onEvent })` must return an engine that is ALREADY
  // initialised and must attach `onEvent` BEFORE initialising it: the engine's
  // preRun diagnostics are emitted during `init`, and a listener added after
  // `createDocumentEngine` resolves hears none of them (finding 089 E0,
  // commit 88472109).  The session therefore hands the sink in rather than
  // subscribing afterwards.
  constructor(options) {
    if (typeof options?.engineFactory !== "function")
      throw new TypeError("OdsViewerSession requires engineFactory");
    this._engineFactory = options.engineFactory;
    this._onState = options.onState || (() => {});
    this._onTile = options.onTile || (() => {});
    this._onEvent = options.onEvent || (() => {});
    this._tileOptions = options.tileOptions || {};
    this._openTimeoutMs = options.openTimeoutMs ?? DEFAULT_OPEN_TIMEOUT_MS;

    this._state = "idle";
    this._engine = null;
    this._view = null;
    this._scheduler = null;
    this._documentVersion = null;
    this._fileName = null;
    this._openName = null;
    this._nameSpoofed = false;
    this._packageProbe = null;
    this._packageProbeMs = null;
    this._engineRequested = false;
    this._currentPart = null;
    this._readBack = null;
    this._fitted = null;
    this._lastRefusal = null;
    this._error = null;
    this._liveGeneration = null;
    this._droppedTiles = 0;
    this._tileErrors = 0;
    this._lastTileError = null;
    this._chain = Promise.resolve();
    this._viewClosed = false;
    this._closeRequested = false;
    this._eventSink = (event) => this._handleEngineEvent(event);
  }

  get scheduler() { return this._scheduler; }
  get droppedTiles() { return this._droppedTiles; }

  get state() {
    const view = this._view;
    const fallbacks = [
      ...(this._nameSpoofed ? ["name-spoofed"] : []),
      ...(view ? view.fallbacks : []),
    ];
    return {
      state: this._state,
      // Diagnostic for as long as the adapter had to stand in for anything.
      // "unbound" is the best a draft can say: no gate has measured it.
      evidenceClass: fallbacks.length ? "diagnostic" : "unbound",
      adapterFallbacks: fallbacks,
      fileName: this._fileName,
      openName: this._openName,
      nameSpoofed: this._nameSpoofed,
      // What the package said before any engine was asked (C6), and whether one
      // was asked at all: an encrypted file is refused with this still false.
      packageProbe: this._packageProbe ? { ...this._packageProbe } : null,
      // How long the probe took (it streams content.xml, addendum 8); null until it ran.
      packageProbeMs: this._packageProbeMs,
      engineRequested: this._engineRequested,
      documentType: view ? view.documentType : null,
      documentTypeKnown: view ? view.documentTypeKnown : false,
      parts: view ? view.parts : 0,
      partNames: view ? view.partNames.slice() : [],
      namesFromEngine: view ? view.namesFromEngine : false,
      partNamesProblem: view ? view.partNamesProblem : null,
      canSwitchParts: view ? view.canSwitchParts : false,
      currentPart: this._currentPart,
      // What the ENGINE said, or null.  Never the part that was asked for.
      currentPartReadBack: this._readBack,
      tabs: this._tabs(),
      widthTwips: view ? view.widthTwips : null,
      heightTwips: view ? view.heightTwips : null,
      lastRefusal: this._lastRefusal,
      tileErrors: this._tileErrors,
      lastTileError: this._lastTileError,
      error: this._error,
    };
  }

  _tabs() {
    const view = this._view;
    if (!view)
      return [];
    return view.partNames.map((label, index) => {
      const current = index === this._currentPart;
      const enabled = view.canSwitchParts || current;
      return {
        index,
        label,
        current,
        enabled,
        disabledReason: enabled ? null : view.partSwitchDisabledReason,
      };
    });
  }

  _emit() {
    this._onState(this.state);
  }

  async open({ bytes, name }) {
    if (this._state !== "idle")
      throw new ViewerError("ALREADY_OPENED", "this viewer session has already been used");
    if (!(bytes instanceof ArrayBuffer) || bytes.byteLength === 0)
      throw new ViewerError("INVALID_ARGUMENT", "open requires a non-empty ArrayBuffer");
    this._fileName = String(name || "");
    this._state = "opening";
    this._emit();

    // BEFORE the engine queue (SPEC-M4 E2, 09-03's G2): an encrypted package is
    // a typed refusal and no engine is started for it.  A package the probe
    // cannot read goes on to the engine, which says what it says.
    const probeStarted = performance.now();
    this._packageProbe = await probeOdfPackage(bytes);
    this._packageProbeMs = Math.round(performance.now() - probeStarted);
    this._assertNotClosedDuringOpen();
    if (this._packageProbe.encrypted === true) {
      const refusal = new ViewerError("ENCRYPTED_DOCUMENT",
        "the document is password-protected; this viewer cannot open encrypted files");
      this._fail("refused", refusal, "ENCRYPTED_DOCUMENT");
      throw refusal;
    }
    // SPEC-M4 addendum 8 (finding 158, the owner's 158-A): a form control shape
    // cannot be drawn on this core (no com.sun.star.form.Forms), so the file is
    // refused here, typed, rather than opened onto a canvas that stays blank.
    if (this._packageProbe.formControls === true) {
      const refusal = new ViewerError("FORM_CONTROLS_UNSUPPORTED",
        "the document contains form controls, which this viewer cannot draw");
      this._fail("refused", refusal, "FORM_CONTROLS_UNSUPPORTED");
      throw refusal;
    }

    try {
      this._engineRequested = true;
      this._engine = await this._engineFactory({ onEvent: this._eventSink });
      this._assertNotClosedDuringOpen();
      const { openName, nameSpoofed } = engineOpenName(this._fileName, this._engine.manifest);
      this._openName = openName;
      this._nameSpoofed = nameSpoofed;
      const handle = await this._engine.open(bytes, {
        name: openName,
        transfer: true,
        timeoutMs: this._openTimeoutMs,
      });
      this._view = adaptHandle(handle);
      this._assertNotClosedDuringOpen();
    } catch (error) {
      await this._release();
      if (this._closeRequested)
        throw error;
      this._fail("error", error, "OPEN_FAILED");
      throw error;
    }

    if (this._view.documentTypeKnown && this._view.documentType !== SPREADSHEET) {
      // Known and wrong: refuse, and give the engine its document back.  A text
      // document shown as sheet tabs would be a page count wearing sheet names.
      const type = this._view.documentType;
      const refusal = new ViewerError("DOCUMENT_TYPE_REFUSED",
        `the document is "${type}", not "${SPREADSHEET}"`, { documentType: type });
      await this._release();
      this._fail("refused", refusal, "DOCUMENT_TYPE_REFUSED");
      throw refusal;
    }

    // The part the engine is ON, if it will say; otherwise part 0, assumed.
    const initial = this._view.readBackPart();
    this._scheduler = new TileScheduler({
      ...this._tileOptions,
      render: (region, requestOptions) => this._view.render(region, requestOptions),
      onTile: (entry) => this._deliverTile(entry),
      onError: (error) => {
        this._tileErrors += 1;
        this._lastTileError = publicError(error, "TILE_ERROR");
        this._emit();
      },
    });
    this._documentVersion = `${this._fileName}#${bytes.byteLength}`;
    this._applyPart(initial ?? 0, initial, {
      widthTwips: this._view.widthTwips, heightTwips: this._view.heightTwips,
    });
    this._state = "ready";
    this._emit();
    return this.state;
  }

  // A `close()` that arrives while the engine is still starting or the document
  // still opening must not be undone by the open finishing later: the engine and
  // the document that arrive after the close are handed back, not adopted.
  _assertNotClosedDuringOpen() {
    if (this._closeRequested)
      throw new ViewerError("CLOSED_DURING_OPEN", "the viewer was closed while the document was opening");
  }

  // Reconfigure the scheduler for `part` and forget every tile and generation of
  // the previous one.  Nothing is scheduled here: the page asks for its viewport
  // after the switch, and until it does no tile is accepted.
  _applyPart(part, readBack, dimensions) {
    this._currentPart = part;
    this._readBack = readBack;
    this._fitted = { widthTwips: dimensions.widthTwips, heightTwips: dimensions.heightTwips };
    this._liveGeneration = null;
    this._scheduler.configureDocument({
      documentVersion: this._documentVersion,
      revision: this._view.revision,
      part,
      scale: 1,
      widthTwips: dimensions.widthTwips,
      heightTwips: dimensions.heightTwips,
    });
  }

  // A tile is delivered only if it belongs to the generation scheduled AFTER the
  // latest part switch.  The scheduler cancels in-flight work on reconfigure, but
  // a render that ignored its abort signal -- or resolved in the same tick --
  // still reaches `onTile`, and a tile of the previous sheet drawn under the new
  // tab is exactly the failure G5 exists to catch.
  _deliverTile(entry) {
    if (this._state !== "ready" || entry.generation !== this._liveGeneration) {
      this._droppedTiles += 1;
      return;
    }
    this._onTile(entry);
  }

  scheduleViewport(viewport) {
    if (this._state !== "ready" || !this._scheduler)
      throw new ViewerError("NOT_READY", `viewer cannot render in state ${this._state}`);
    this._liveGeneration = this._scheduler.scheduleViewport(viewport);
    return this._liveGeneration;
  }

  drain() {
    return this._scheduler ? this._scheduler.drain() : Promise.resolve();
  }

  // SPEC-M4 E4b (review B2).  A paint can lay the sheet out wider than the open
  // or the switch said -- the W9 smoke saw 26593 twips at open and 26775 after
  // the first paint, and the page left the difference unpainted.  The handle's
  // size follows every paint reply (DocumentHandle.render), so this compares
  // what the scheduler was configured with against what the engine says NOW
  // and, if either differs, reconfigures for the same part.  True when it did;
  // the caller then sizes its surface and asks for its viewport again.
  refit() {
    if (this._state !== "ready" || !this._scheduler || !this._fitted)
      return false;
    const widthTwips = this._view.widthTwips;
    const heightTwips = this._view.heightTwips;
    if (widthTwips === this._fitted.widthTwips && heightTwips === this._fitted.heightTwips)
      return false;
    this._applyPart(this._currentPart, this._readBack, { widthTwips, heightTwips });
    this._emit();
    return true;
  }

  // Show part k.  Switches are serialised: two clicks in quick succession run
  // one after the other, so the last request is the one the engine ends on and
  // the state ends describing.  Resolves with the new state; rejects with a
  // ViewerError for a refusal (nothing is repainted) or a read-back mismatch
  // (the state then follows the ENGINE, not the request).
  showPart(k) {
    const run = this._chain.then(() => this._showPart(k));
    this._chain = run.catch(() => {});
    return run;
  }

  async _showPart(k) {
    if (this._state !== "ready")
      throw new ViewerError("NOT_READY", `viewer cannot switch parts in state ${this._state}`);
    if (!Number.isInteger(k) || k < 0 || k >= this._view.parts) {
      this._refuse(new ViewerError("PART_OUT_OF_RANGE",
        `part ${k} is not in 0..${this._view.parts - 1}`, { requested: k }));
    }
    let reply;
    try {
      reply = await this._view.setPart(k);
    } catch (error) {
      this._lastRefusal = { ...publicError(error, "PART_SWITCH_FAILED"), requested: k };
      this._emit();
      throw error;
    }
    if (this._state !== "ready")
      throw new ViewerError("NOT_READY", "viewer was closed during the part switch");
    const readBack = this._view.readBackPart();
    const shown = readBack ?? k;
    this._applyPart(shown, readBack, reply);
    if (readBack !== null && readBack !== k) {
      const mismatch = new ViewerError("PART_READBACK_MISMATCH",
        `asked for part ${k}, the engine reports part ${readBack}`,
        { requested: k, readBack });
      this._lastRefusal = { ...publicError(mismatch), requested: k };
      this._emit();
      throw mismatch;
    }
    this._lastRefusal = null;
    this._emit();
    return this.state;
  }

  _refuse(error) {
    this._lastRefusal = { ...publicError(error), requested: error.details?.requested ?? null };
    this._emit();
    throw error;
  }

  _fail(state, error, fallbackCode) {
    this._state = state;
    this._error = publicError(error, fallbackCode);
    this._emit();
  }

  _handleEngineEvent(event) {
    this._onEvent(event);
    if (event?.event === "worker-crashed"
        && this._state !== "closed" && this._state !== "error") {
      this._scheduler?.close();
      this._fail("error", event.error || {}, "WORKER_CRASHED");
    }
  }

  // Gives the document and the engine back.  Idempotent PER RESOURCE, not per
  // call: a close() that races an open runs this once with nothing to give back,
  // and the open, finishing later, runs it again for what had not arrived yet.
  // `_view` is kept afterwards on purpose: the state of a refused or closed
  // session still describes what it was looking at.
  async _release() {
    this._scheduler?.close();
    if (this._view && !this._viewClosed) {
      this._viewClosed = true;
      try { await this._view.close({ timeoutMs: 30000 }); } catch { /* the worker is disposed next */ }
    }
    const engine = this._engine;
    this._engine = null;
    try { engine?.dispose(); } catch { /* nothing left to do */ }
  }

  async close() {
    if (this._state === "closed")
      return;
    this._closeRequested = true;
    await this._release();
    this._scheduler = null;
    this._state = "closed";
    this._emit();
  }
}
