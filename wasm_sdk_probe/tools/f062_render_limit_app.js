// Finding 062: WHICH LAYER loses the pixels above a canvas height of ~32,767?
//
// The product path cannot answer this. `render()` does not throw there, and the
// page deliberately publishes no session handle, so from the product's seat a
// blank canvas is consistent with two very different stories:
//
//   1. the engine returned an empty (or short) bitmap and reported success;
//   2. the bitmap was fine and the page lost it in `new ImageData(...)` or
//      `putImageData`.
//
// Which one it is decides whether the fix needs a link, so it is not an
// academic question -- and findings 040 and 048 are why it is being measured
// instead of named.
//
// This page is the SAME engine and the SAME artifact the product loads: the
// factory is copied from `web/e2-editor-app.js:585`. What it does differently
// is ask the engine directly, at several canvas heights that straddle the wall,
// and report what came back BEFORE anything draws it:
//
//   * the width and height the engine says the tile is
//   * the byte length of the pixel buffer, against the width x height x 4 the
//     request implies
//   * how much of that buffer is not white -- an all-white buffer of the right
//     size is a rendered blank page, which is a different answer again
//
// No canvas is involved at any point. If the numbers are right here, the loss
// is on the page side; if they are not, it is on the engine side.

import { createDocumentEngine } from "./sdk/document-sdk.js";

const report = {
  schemaVersion: 1,
  release: "f062-render-limit",
  crossOriginIsolated: globalThis.crossOriginIsolated,
  document: null,
  arms: [],
  error: null,
  done: false,
};
globalThis.__f062 = report;

const params = new URLSearchParams(location.search);
const documentPath = params.get("document") || "./f062-long.odt";
const canvasWidth = Number(params.get("width") || 725);
const heights = (params.get("heights")
  || "31048,32590,32767,32768,32889,34847")
  .split(",").map((value) => Number(value.trim())).filter(Boolean);

function dpr() { return globalThis.devicePixelRatio || 1; }

function say(message) {
  const node = document.querySelector("#log");
  node.textContent += message + "\n";
}

async function main() {
  const engine = await createDocumentEngine({
    workerUrl: "./profiles/e2-editor-v3/sdk-worker.js",
    timeoutMs: 60000,
  });
  const bytes = await (await fetch(documentPath, { cache: "no-cache" }))
    .arrayBuffer();
  const handle = await engine.open(bytes, {
    name: "f062-long.odt", transfer: true, timeoutMs: 180000,
  });
  report.document = {
    widthTwips: handle.widthTwips,
    heightTwips: handle.heightTwips,
    revision: handle.revision,
  };
  say(`document ${handle.widthTwips} x ${handle.heightTwips} twips`);

  for (const canvasHeightPx of heights) {
    const arm = { canvasWidthPx: canvasWidth, canvasHeightPx,
                  expectedBytes: canvasWidth * canvasHeightPx * 4 };
    const started = performance.now();
    try {
      const tile = await handle.render({
        xTwips: 0, yTwips: 0,
        widthTwips: handle.widthTwips,
        heightTwips: handle.heightTwips,
        canvasWidthPx: canvasWidth,
        canvasHeightPx,
      }, { timeoutMs: 180000 });
      arm.ms = Math.round(performance.now() - started);
      arm.reportedWidth = tile.width;
      arm.reportedHeight = tile.height;
      const pixels = new Uint8Array(tile.pixels);
      arm.byteLength = pixels.byteLength;
      arm.byteLengthMatchesRequest = pixels.byteLength === arm.expectedBytes;
      // What is IN the buffer.  A correctly sized buffer of white pixels is a
      // rendered blank page; a buffer of zeros is a bitmap nobody drew into;
      // and either is different from a short buffer.
      let dark = 0;
      let zero = 0;
      let opaque = 0;
      const step = 4 * Math.max(1, Math.floor(pixels.length / 4 / 2_000_000));
      let sampled = 0;
      for (let i = 0; i + 3 < pixels.length; i += step) {
        sampled += 1;
        if (pixels[i + 3] > 128) opaque += 1;
        if (pixels[i] === 0 && pixels[i + 1] === 0 && pixels[i + 2] === 0
            && pixels[i + 3] === 0) zero += 1;
        else if (pixels[i] < 100 && pixels[i + 1] < 100 && pixels[i + 2] < 100
                 && pixels[i + 3] > 128) dark += 1;
      }
      arm.sampledPixels = sampled;
      arm.darkPixels = dark;
      arm.fullyTransparentPixels = zero;
      arm.opaquePixels = opaque;
      // The one thing the page would have done next, tried here so that "the
      // page could not build an ImageData from this" is an observation rather
      // than a guess.
      try {
        const image = new ImageData(new Uint8ClampedArray(tile.pixels),
                                    tile.width, tile.height);
        arm.imageDataBuilt = true;
        arm.imageDataHeight = image.height;
        // And the call after that, which is the whole of what the product
        // does with the tile: paste it onto a canvas of the same size and read
        // a strip back.  This is the last step before the user sees pixels, so
        // if the tile is good and this is empty, the loss is HERE.
        // TWICE: once on a detached canvas and once on a canvas that is IN
        // THE DOCUMENT and CSS-sized the way the product's is.  The first
        // version of this probe only did the detached one, found it painting
        // happily at every height, and would have concluded "the page loses it
        // somewhere" without saying where.  The product's canvas is attached,
        // displayed, and 725 CSS pixels wide by tens of thousands tall -- and
        // that is the only difference left.
        for (const attached of [false, true]) {
          const key = attached ? "attached" : "detached";
          try {
            const canvas = document.createElement("canvas");
            canvas.width = tile.width;
            canvas.height = tile.height;
            if (attached) {
              // The product's own sizing: layoutCanvas sets a CSS width of the
              // desk and a CSS height in the same ratio as the backing store.
              canvas.style.width = `${Math.round(tile.width / dpr())}px`;
              canvas.style.height = `${Math.round(tile.height / dpr())}px`;
              document.querySelector("#stage").replaceChildren(canvas);
            }
            arm[key + "AcceptedSize"] =
              canvas.width === tile.width && canvas.height === tile.height;
            const context = canvas.getContext("2d");
            arm[key + "HasContext"] = Boolean(context);
            if (context) {
              context.putImageData(image, 0, 0);
              const strip = context.getImageData(
                0, 0, canvas.width, Math.min(400, canvas.height)).data;
              let painted = 0;
              const columns = new Uint8Array(canvas.width);
              for (let i = 0; i + 3 < strip.length; i += 4) {
                if (strip[i + 3] > 128 && strip[i] < 100 && strip[i + 1] < 100
                    && strip[i + 2] < 100) {
                  painted += 1;
                  columns[(i / 4) % canvas.width] = 1;
                }
              }
              let inkedColumns = 0;
              for (let x = 0; x < canvas.width; x += 1)
                if (columns[x]) inkedColumns += 1;
              arm[key + "DarkPixelsInTopStrip"] = painted;
              arm[key + "InkedColumns"] = inkedColumns;
            }
            if (attached)
              document.querySelector("#stage").replaceChildren();
          } catch (error) {
            arm[key + "Threw"] = `${error?.name}: ${error?.message}`;
          }
        }
      } catch (error) {
        arm.imageDataBuilt = false;
        arm.imageDataError = `${error?.name}: ${error?.message}`;
      }
    } catch (error) {
      arm.ms = Math.round(performance.now() - started);
      arm.threw = true;
      arm.errorCode = error?.code ?? null;
      arm.error = `${error?.name ?? "Error"}: ${error?.message ?? error}`;
    }
    report.arms.push(arm);
    say(`${canvasHeightPx}: ${arm.threw ? "THREW " + arm.error
        : `${arm.reportedWidth}x${arm.reportedHeight} bytes=${arm.byteLength}`
          + ` (expected ${arm.expectedBytes})`
          + ` dark=${arm.darkPixels}/${arm.sampledPixels}`
          + ` imageData=${arm.imageDataBuilt}`
          + ` detachedCols=${arm.detachedInkedColumns}`
          + ` attachedCols=${arm.attachedInkedColumns}`} ${arm.ms}ms`);
  }
  await handle.close?.().catch?.(() => {});
  report.done = true;
  say("done");
}

main().catch((error) => {
  report.error = `${error?.name ?? "Error"}: ${error?.message ?? error}`;
  report.done = true;
  say("FAILED " + report.error);
});
