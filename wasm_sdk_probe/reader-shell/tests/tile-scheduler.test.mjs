import assert from "node:assert/strict";
import test from "node:test";

import {
  TileScheduler,
  clampRegion,
  cssPxToTwips,
  twipsToCssPx,
} from "../tile-scheduler.js";

function tile(width, height, revision = 0) {
  return { pixels: new ArrayBuffer(width * height * 4), width, height, revision };
}

function context(overrides = {}) {
  return {
    documentVersion: "v1",
    revision: 0,
    part: 0,
    scale: 1,
    widthTwips: 15360,
    heightTwips: 30720,
    ...overrides,
  };
}

test("CSS/twips adapter and boundary clamp are deterministic", () => {
  assert.equal(cssPxToTwips(100, 1), 1500);
  assert.equal(cssPxToTwips(100, 2), 750);
  assert.equal(twipsToCssPx(1500, 1), 100);
  assert.deepEqual(
    clampRegion({ xTwips: 950, yTwips: 1900, widthTwips: 500, heightTwips: 500 }, 1000, 2000),
    { xTwips: 950, yTwips: 1900, widthTwips: 50, heightTwips: 100 },
  );
});

test("visible tiles precede prefetch and the in-flight ceiling is enforced", async () => {
  let active = 0;
  let maximum = 0;
  const calls = [];
  const scheduler = new TileScheduler({
    tileSizePx: 128,
    prefetchTiles: 1,
    maxInFlight: 2,
    render: async (region) => {
      active += 1;
      maximum = Math.max(maximum, active);
      calls.push(region);
      await new Promise((resolve) => setTimeout(resolve, 2));
      active -= 1;
      return tile(region.canvasWidthPx, region.canvasHeightPx);
    },
  });
  scheduler.configureDocument(context());
  scheduler.scheduleViewport({ scrollLeft: 0, scrollTop: 0, width: 128, height: 128 });
  await scheduler.drain();
  assert.ok(calls.length >= 4);
  assert.ok(maximum <= 2);
  assert.equal(calls[0].xTwips, 0);
  assert.equal(calls[0].yTwips, 0);
  assert.equal(scheduler.metrics.maxObservedInFlight, 2);
});

test("same key uses cache and revision invalidation clears it", async () => {
  let renders = 0;
  const scheduler = new TileScheduler({
    tileSizePx: 128,
    prefetchTiles: 0,
    maxInFlight: 1,
    render: async (region) => {
      renders += 1;
      return tile(region.canvasWidthPx, region.canvasHeightPx);
    },
  });
  scheduler.configureDocument(context());
  const viewport = { scrollLeft: 0, scrollTop: 0, width: 100, height: 100 };
  scheduler.scheduleViewport(viewport);
  await scheduler.drain();
  scheduler.scheduleViewport(viewport);
  await scheduler.drain();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(renders, 1);
  assert.ok(scheduler.metrics.cacheHits >= 1);
  scheduler.invalidateRevision(1);
  scheduler.scheduleViewport(viewport);
  await scheduler.drain();
  assert.equal(renders, 2);
});

test("late completion from an old generation never paints the new viewport", async () => {
  const pending = [];
  const painted = [];
  const scheduler = new TileScheduler({
    tileSizePx: 128,
    prefetchTiles: 0,
    maxInFlight: 1,
    render: (region) => new Promise((resolve) => pending.push({ region, resolve })),
    onTile: (entry) => painted.push({ generation: entry.generation, yPx: entry.yPx }),
  });
  scheduler.configureDocument(context());
  const firstGeneration = scheduler.scheduleViewport({
    scrollLeft: 0, scrollTop: 0, width: 100, height: 100,
  });
  const secondGeneration = scheduler.scheduleViewport({
    scrollLeft: 0, scrollTop: 256, width: 100, height: 100,
  });
  assert.notEqual(firstGeneration, secondGeneration);
  pending[0].resolve(tile(pending[0].region.canvasWidthPx, pending[0].region.canvasHeightPx));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(pending.length, 2);
  pending[1].resolve(tile(pending[1].region.canvasWidthPx, pending[1].region.canvasHeightPx));
  await scheduler.drain();
  assert.deepEqual(painted, [{ generation: secondGeneration, yPx: 256 }]);
  assert.equal(scheduler.metrics.staleCompletions, 1);
});

test("LRU cache respects its byte ceiling", async () => {
  const scheduler = new TileScheduler({
    tileSizePx: 64,
    prefetchTiles: 0,
    maxInFlight: 1,
    maxCacheBytes: 64 * 64 * 4,
    render: async (region) => tile(region.canvasWidthPx, region.canvasHeightPx),
  });
  scheduler.configureDocument(context());
  scheduler.scheduleViewport({ scrollLeft: 0, scrollTop: 0, width: 64, height: 128 });
  await scheduler.drain();
  assert.ok(scheduler.metrics.evictions >= 1);
  assert.ok(scheduler.metrics.peakCacheBytes <= 2 * 64 * 64 * 4);
});
