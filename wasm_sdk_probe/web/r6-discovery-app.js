import {
  DocumentSdkError,
  SdkAbortError,
  createDocumentEngine,
} from "./document-sdk.js";

const statusElement = document.querySelector("#status");
const logElement = document.querySelector("#log");
const metrics = {
  schemaVersion: 1,
  release: "R6-A-discovery",
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  manifest: null,
  documents: [],
  events: [],
  complete: false,
  pass: false,
  error: null,
};
globalThis.__r6_discovery_metrics = metrics;
globalThis.__probe_metrics = metrics;

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  logElement.textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
}

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

function tileSummary(tile) {
  const expectedBytes = tile.width * tile.height * 4;
  if (!(tile.pixels instanceof ArrayBuffer) || tile.pixels.byteLength !== expectedBytes)
    throw new Error(`invalid tile bytes: ${tile.pixels?.byteLength}/${expectedBytes}`);
  return {
    width: tile.width,
    height: tile.height,
    bytes: tile.pixels.byteLength,
    revision: tile.revision,
  };
}

function selectionSignature(result) {
  return JSON.stringify(result.selections || []);
}

async function classifyAnchor(documentHandle, quote) {
  const first = await documentHandle.search(quote);
  if (!first.found) {
    return { quote, classification: "not-found", candidates: 0, searches: 1 };
  }
  const selection = await documentHandle.getSelection();
  const firstSignature = selectionSignature(first);
  const second = await documentHandle.search(quote);
  if (!second.found) {
    throw new Error(`search lost an existing quote on the second request: ${quote}`);
  }
  const secondSignature = selectionSignature(second);
  return {
    quote,
    classification: firstSignature === secondSignature ? "unique" : "ambiguous",
    candidates: firstSignature === secondSignature ? 1 : 2,
    searches: 2,
    exactSelection: selection.text === quote,
    firstSelections: first.selections,
    secondSelections: second.selections,
    signaturesEqual: firstSignature === secondSignature,
  };
}

async function renderDiscovery(documentHandle) {
  const width = documentHandle.widthTwips;
  const height = documentHandle.heightTwips;
  const regionWidth = Math.min(7680, width);
  const regionHeight = Math.min(7680, height);
  const top = await documentHandle.render({
    xTwips: 0,
    yTwips: 0,
    widthTwips: regionWidth,
    heightTwips: regionHeight,
    canvasWidthPx: 384,
    canvasHeightPx: 384,
  });
  const adjacentY = Math.max(0, Math.min(height - regionHeight, regionHeight));
  const adjacent = await documentHandle.render({
    xTwips: 0,
    yTwips: adjacentY,
    widthTwips: regionWidth,
    heightTwips: regionHeight,
    canvasWidthPx: 384,
    canvasHeightPx: 384,
  });
  const partial = await documentHandle.render({
    xTwips: Math.max(0, width - Math.max(1, Math.floor(regionWidth / 2))),
    yTwips: Math.max(0, height - Math.max(1, Math.floor(regionHeight / 2))),
    widthTwips: regionWidth,
    heightTwips: regionHeight,
    canvasWidthPx: 256,
    canvasHeightPx: 256,
  });
  return {
    top: { ...tileSummary(top), sha256: await sha256(top.pixels) },
    adjacent: {
      ...tileSummary(adjacent),
      yTwips: adjacentY,
      sha256: await sha256(adjacent.pixels),
    },
    partialBeyondBounds: {
      ...tileSummary(partial),
      sha256: await sha256(partial.pixels),
    },
  };
}

async function queueAbortDiscovery(documentHandle) {
  const completionOrder = [];
  const controller = new AbortController();
  const region = {
    xTwips: 0,
    yTwips: 0,
    widthTwips: Math.min(7680, documentHandle.widthTwips),
    heightTwips: Math.min(7680, documentHandle.heightTwips),
    canvasWidthPx: 1024,
    canvasHeightPx: 1024,
  };
  const first = documentHandle.render(region).then(() => completionOrder.push("first"));
  const aborted = documentHandle.render(region, { signal: controller.signal })
    .then(() => ({ code: "UNEXPECTED_SUCCESS" }))
    .catch((error) => ({
      code: error.code,
      isAbortError: error instanceof SdkAbortError,
    }));
  const third = documentHandle.render(region).then(() => completionOrder.push("third"));
  controller.abort();
  const abortResult = await aborted;
  await Promise.all([first, third]);
  return { completionOrder, abortResult };
}

async function inspectDocument(engine, fixture) {
  const response = await fetch(fixture.url, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed: ${response.status} ${fixture.url}`);
  const documentHandle = await engine.open(await response.arrayBuffer(), {
    name: fixture.name,
    transfer: true,
    timeoutMs: 180000,
  });
  try {
    const result = {
      fixture: fixture.name,
      parts: documentHandle.parts,
      widthTwips: documentHandle.widthTwips,
      heightTwips: documentHandle.heightTwips,
      tileMode: documentHandle.tileMode,
      revisionAtOpen: documentHandle.revision,
      render: await renderDiscovery(documentHandle),
      queueAbort: await queueAbortDiscovery(documentHandle),
      anchors: [],
      mutation: null,
    };
    for (const anchor of fixture.anchors)
      result.anchors.push(await classifyAnchor(documentHandle, anchor.quote));

    if (fixture.mutationQuote) {
      await documentHandle.search(fixture.mutationQuote);
      const selected = await documentHandle.getSelection();
      const beforeEventCount = metrics.events.length;
      await documentHandle.replaceSelection(`${fixture.mutationQuote}-R6-discovery`, {
        expectedRevision: selected.revision,
      });
      await new Promise((resolve) => setTimeout(resolve, 50));
      result.mutation = {
        selectedExact: selected.text === fixture.mutationQuote,
        revision: documentHandle.revision,
        invalidationEvents: metrics.events.slice(beforeEventCount)
          .filter((event) => event.event === "document-invalidated").length,
      };
    }
    result.pass = result.parts >= 1
      && result.widthTwips > 0
      && result.heightTwips > 0
      && result.render.top.bytes === result.render.top.width * result.render.top.height * 4
      && result.render.partialBeyondBounds.bytes
        === result.render.partialBeyondBounds.width * result.render.partialBeyondBounds.height * 4
      && result.queueAbort.abortResult.code === "ABORTED"
      && result.queueAbort.completionOrder.join(",") === "first,third"
      && result.anchors.every((anchor, index) =>
        anchor.classification === fixture.anchors[index].expected
        && (anchor.candidates === 0 || anchor.exactSelection === true))
      && (!result.mutation
          || (result.mutation.selectedExact && result.mutation.invalidationEvents > 0));
    return result;
  } finally {
    await documentHandle.close({ timeoutMs: 180000 });
  }
}

async function runDiscovery() {
  statusElement.textContent = "initializing writer-review";
  const engine = await createDocumentEngine({
    workerUrl: "./profiles/writer-review-r6/sdk-worker.js",
    timeoutMs: 30000,
  });
  engine.onEvent((event) => metrics.events.push(event));
  metrics.manifest = engine.manifest;
  let fixtures = [
    {
      name: "t1-plain-zh.odt",
      url: "./r6-fixtures/t1-plain-zh.odt",
      anchors: [
        { quote: "LibreOfficeKit", expected: "unique" },
        { quote: "R6-ANCHOR-DOES-NOT-EXIST", expected: "not-found" },
      ],
      mutationQuote: "LibreOfficeKit",
    },
    {
      name: "t2-styled.odt",
      url: "./r6-fixtures/t2-styled.odt",
      anchors: [{ quote: "RGBA tile", expected: "unique" }],
      optional: true,
    },
    {
      name: "t3-long.odt",
      url: "./r6-fixtures/t3-long.odt",
      anchors: [{ quote: "English compatibility text", expected: "ambiguous" }],
    },
  ];
  const requestedFixture = new URLSearchParams(location.search).get("fixture");
  if (requestedFixture)
    fixtures = fixtures.filter((fixture) => fixture.name === requestedFixture);
  else
    fixtures = fixtures.filter((fixture) => fixture.optional !== true);
  if (fixtures.length === 0)
    throw new Error(`unknown discovery fixture: ${requestedFixture}`);
  try {
    for (const fixture of fixtures) {
      statusElement.textContent = `inspecting ${fixture.name}`;
      const result = await inspectDocument(engine, fixture);
      metrics.documents.push(result);
      log(result);
    }
    const longDocument = metrics.documents.find((item) => item.fixture === "t3-long.odt");
    metrics.pass = metrics.crossOriginIsolated
      && metrics.manifest?.profile === "writer-review"
      && metrics.manifest?.abiVersion === 65537
      && metrics.documents.every((item) => item.pass)
      && longDocument.render.top.sha256 !== longDocument.render.adjacent.sha256;
    statusElement.textContent = metrics.pass ? "complete: pass" : "complete: failed invariants";
  } finally {
    engine.dispose();
    metrics.complete = true;
  }
  return metrics;
}

globalThis.__r6_run_discovery = runDiscovery;
runDiscovery().catch((error) => {
  metrics.error = error instanceof DocumentSdkError
    ? { code: error.code, message: error.message, details: error.details }
    : { code: "UNEXPECTED", message: String(error?.stack || error) };
  metrics.complete = true;
  metrics.pass = false;
  statusElement.textContent = `error: ${metrics.error.code}`;
  log(metrics.error);
});
