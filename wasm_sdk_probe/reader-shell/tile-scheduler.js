export const TWIPS_PER_CSS_PX = 15;

export function cssPxToTwips(value, scale = 1) {
  if (!Number.isFinite(value) || value < 0 || !Number.isFinite(scale) || scale <= 0)
    throw new TypeError("CSS pixel coordinates and scale must be finite and non-negative");
  return Math.round(value * TWIPS_PER_CSS_PX / scale);
}

export function twipsToCssPx(value, scale = 1) {
  if (!Number.isFinite(value) || value < 0 || !Number.isFinite(scale) || scale <= 0)
    throw new TypeError("twips coordinates and scale must be finite and non-negative");
  return value / TWIPS_PER_CSS_PX * scale;
}

export function clampRegion(region, documentWidthTwips, documentHeightTwips) {
  if (!Number.isFinite(documentWidthTwips) || documentWidthTwips <= 0
      || !Number.isFinite(documentHeightTwips) || documentHeightTwips <= 0) {
    throw new TypeError("document dimensions must be positive");
  }
  const xTwips = Math.max(0, Math.min(Math.floor(region.xTwips), documentWidthTwips - 1));
  const yTwips = Math.max(0, Math.min(Math.floor(region.yTwips), documentHeightTwips - 1));
  const widthTwips = Math.max(
    1,
    Math.min(Math.ceil(region.widthTwips), documentWidthTwips - xTwips),
  );
  const heightTwips = Math.max(
    1,
    Math.min(Math.ceil(region.heightTwips), documentHeightTwips - yTwips),
  );
  return { xTwips, yTwips, widthTwips, heightTwips };
}

function tileKey(context, item) {
  return [
    context.documentVersion,
    context.revision,
    context.part,
    context.scale.toFixed(4),
    item.region.xTwips,
    item.region.yTwips,
    item.region.widthTwips,
    item.region.heightTwips,
    item.canvasWidthPx,
    item.canvasHeightPx,
  ].join(":");
}

export class TileScheduler {
  constructor(options) {
    if (!options?.render || typeof options.render !== "function")
      throw new TypeError("TileScheduler requires a render function");
    this._render = options.render;
    this._onTile = options.onTile || (() => {});
    this._onError = options.onError || (() => {});
    this._tileSizePx = options.tileSizePx ?? 256;
    this._prefetchTiles = options.prefetchTiles ?? 1;
    this._maxInFlight = options.maxInFlight ?? 2;
    this._maxCacheBytes = options.maxCacheBytes ?? 32 * 1024 * 1024;
    this._context = null;
    this._generation = 0;
    this._queue = [];
    this._inFlight = new Map();
    this._cache = new Map();
    this._cacheBytes = 0;
    this._closed = false;
    this._idleResolvers = [];
    this.metrics = {
      generations: 0,
      requested: 0,
      completed: 0,
      cancelled: 0,
      staleCompletions: 0,
      errors: 0,
      retries: 0,
      cacheHits: 0,
      cacheMisses: 0,
      evictions: 0,
      peakCacheBytes: 0,
      maxObservedInFlight: 0,
    };
  }

  configureDocument(context) {
    const required = ["documentVersion", "revision", "widthTwips", "heightTwips"];
    for (const key of required) {
      if (context?.[key] === undefined || context?.[key] === null)
        throw new TypeError(`missing tile document context: ${key}`);
    }
    this._cancelGeneration();
    this._context = {
      documentVersion: String(context.documentVersion),
      revision: Number(context.revision),
      part: context.part ?? 0,
      scale: Number(context.scale ?? 1),
      widthTwips: Number(context.widthTwips),
      heightTwips: Number(context.heightTwips),
    };
    this.clearCache();
  }

  get documentCssSize() {
    if (!this._context)
      return { width: 0, height: 0 };
    return {
      width: twipsToCssPx(this._context.widthTwips, this._context.scale),
      height: twipsToCssPx(this._context.heightTwips, this._context.scale),
    };
  }

  setScale(scale) {
    if (!this._context || !Number.isFinite(scale) || scale <= 0)
      throw new TypeError("scale must be positive");
    if (this._context.scale === scale)
      return;
    this._cancelGeneration();
    this._context.scale = scale;
  }

  invalidateRevision(revision) {
    if (!this._context)
      return;
    this._cancelGeneration();
    this._context.revision = Number(revision);
    this.clearCache();
  }

  scheduleViewport(viewport) {
    if (this._closed)
      throw new Error("tile scheduler is closed");
    if (!this._context)
      throw new Error("tile scheduler has no document");
    const values = [
      viewport.scrollLeft, viewport.scrollTop,
      viewport.width, viewport.height,
    ];
    if (values.some((value) => !Number.isFinite(value) || value < 0))
      throw new TypeError("viewport values must be finite and non-negative");
    this._cancelGeneration();
    const generation = ++this._generation;
    this.metrics.generations += 1;
    const size = this.documentCssSize;
    const minimumColumn = Math.max(
      0,
      Math.floor(viewport.scrollLeft / this._tileSizePx) - this._prefetchTiles,
    );
    const maximumColumn = Math.min(
      Math.max(0, Math.ceil(size.width / this._tileSizePx) - 1),
      Math.floor((viewport.scrollLeft + viewport.width) / this._tileSizePx)
        + this._prefetchTiles,
    );
    const minimumRow = Math.max(
      0,
      Math.floor(viewport.scrollTop / this._tileSizePx) - this._prefetchTiles,
    );
    const maximumRow = Math.min(
      Math.max(0, Math.ceil(size.height / this._tileSizePx) - 1),
      Math.floor((viewport.scrollTop + viewport.height) / this._tileSizePx)
        + this._prefetchTiles,
    );
    const visible = [];
    const prefetched = [];
    for (let row = minimumRow; row <= maximumRow; row += 1) {
      for (let column = minimumColumn; column <= maximumColumn; column += 1) {
        const xPx = column * this._tileSizePx;
        const yPx = row * this._tileSizePx;
        const cssWidth = Math.max(1, Math.min(this._tileSizePx, size.width - xPx));
        const cssHeight = Math.max(1, Math.min(this._tileSizePx, size.height - yPx));
        const region = clampRegion({
          xTwips: cssPxToTwips(xPx, this._context.scale),
          yTwips: cssPxToTwips(yPx, this._context.scale),
          widthTwips: cssPxToTwips(cssWidth, this._context.scale),
          heightTwips: cssPxToTwips(cssHeight, this._context.scale),
        }, this._context.widthTwips, this._context.heightTwips);
        const item = {
          generation,
          column,
          row,
          xPx,
          yPx,
          cssWidth,
          cssHeight,
          canvasWidthPx: Math.max(1, Math.ceil(cssWidth)),
          canvasHeightPx: Math.max(1, Math.ceil(cssHeight)),
          region,
          retry: 0,
        };
        item.key = tileKey(this._context, item);
        const isVisible = xPx + cssWidth > viewport.scrollLeft
          && xPx < viewport.scrollLeft + viewport.width
          && yPx + cssHeight > viewport.scrollTop
          && yPx < viewport.scrollTop + viewport.height;
        (isVisible ? visible : prefetched).push(item);
      }
    }
    for (const item of [...visible, ...prefetched])
      this._enqueue(item);
    this._pump();
    return generation;
  }

  _enqueue(item) {
    const cached = this._cache.get(item.key);
    if (cached) {
      this.metrics.cacheHits += 1;
      this._cache.delete(item.key);
      this._cache.set(item.key, cached);
      queueMicrotask(() => {
        if (!this._closed && item.generation === this._generation)
          this._onTile({ ...item, tile: cached.tile, cacheHit: true });
      });
      return;
    }
    if ([...this._inFlight.values()].some((entry) =>
      entry.item.key === item.key && entry.item.generation === item.generation)
        || this._queue.some((queued) =>
          queued.key === item.key && queued.generation === item.generation)) {
      this.metrics.cacheHits += 1;
      return;
    }
    this.metrics.cacheMisses += 1;
    this._queue.push(item);
  }

  _pump() {
    while (!this._closed && this._inFlight.size < this._maxInFlight && this._queue.length) {
      const item = this._queue.shift();
      if (item.generation !== this._generation)
        continue;
      const controller = new AbortController();
      const requestKey = `${item.key}@${item.generation}`;
      this._inFlight.set(requestKey, { controller, item });
      this.metrics.requested += 1;
      this.metrics.maxObservedInFlight = Math.max(
        this.metrics.maxObservedInFlight,
        this._inFlight.size,
      );
      Promise.resolve(this._render({
        ...item.region,
        canvasWidthPx: item.canvasWidthPx,
        canvasHeightPx: item.canvasHeightPx,
      }, { signal: controller.signal })).then((tile) => {
        if (item.generation !== this._generation || this._closed) {
          this.metrics.staleCompletions += 1;
          return;
        }
        const expected = tile.width * tile.height * 4;
        if (!(tile.pixels instanceof ArrayBuffer) || tile.pixels.byteLength !== expected)
          throw new Error(`invalid tile buffer: ${tile.pixels?.byteLength}/${expected}`);
        this.metrics.completed += 1;
        this._putCache(item.key, tile);
        this._onTile({ ...item, tile, cacheHit: false });
      }).catch((error) => {
        if (controller.signal.aborted || error?.code === "ABORTED") {
          this.metrics.cancelled += 1;
          return;
        }
        if (item.retry < 1 && item.generation === this._generation) {
          this.metrics.retries += 1;
          this._queue.unshift({ ...item, retry: item.retry + 1 });
          return;
        }
        this.metrics.errors += 1;
        this._onError(error, item);
      }).finally(() => {
        this._inFlight.delete(requestKey);
        this._pump();
        this._resolveIdle();
      });
    }
    this._resolveIdle();
  }

  _putCache(key, tile) {
    const bytes = tile.pixels.byteLength;
    if (bytes > this._maxCacheBytes)
      return;
    if (this._cache.has(key)) {
      this._cacheBytes -= this._cache.get(key).bytes;
      this._cache.delete(key);
    }
    this._cache.set(key, { tile, bytes });
    this._cacheBytes += bytes;
    this.metrics.peakCacheBytes = Math.max(this.metrics.peakCacheBytes, this._cacheBytes);
    while (this._cacheBytes > this._maxCacheBytes && this._cache.size) {
      const oldestKey = this._cache.keys().next().value;
      const oldest = this._cache.get(oldestKey);
      this._cache.delete(oldestKey);
      this._cacheBytes -= oldest.bytes;
      this.metrics.evictions += 1;
    }
  }

  _cancelGeneration() {
    this._queue = [];
    for (const { controller } of this._inFlight.values())
      controller.abort();
  }

  clearCache() {
    this._cache.clear();
    this._cacheBytes = 0;
  }

  drain() {
    if (this._queue.length === 0 && this._inFlight.size === 0)
      return Promise.resolve();
    return new Promise((resolve) => this._idleResolvers.push(resolve));
  }

  _resolveIdle() {
    if (this._queue.length || this._inFlight.size)
      return;
    for (const resolve of this._idleResolvers.splice(0))
      resolve();
  }

  close() {
    if (this._closed)
      return;
    this._closed = true;
    this._cancelGeneration();
    this.clearCache();
    this._resolveIdle();
  }
}
