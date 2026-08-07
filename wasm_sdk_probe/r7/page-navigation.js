export class PageHintNavigator {
  constructor(options = {}) {
    const pageCount = Number(options.pageCount);
    const documentHeightTwips = Number(options.documentHeightTwips);
    if (!Number.isInteger(pageCount) || pageCount < 1)
      throw new TypeError("pageCount must be a positive integer");
    if (!Number.isFinite(documentHeightTwips) || documentHeightTwips <= 0)
      throw new TypeError("documentHeightTwips must be positive");
    this.pageCount = pageCount;
    this.documentHeightTwips = documentHeightTwips;
    this.currentPage = 1;
  }

  target(intent) {
    const current = this.currentPage;
    const targets = {
      first: 1,
      previous: Math.max(1, current - 1),
      next: Math.min(this.pageCount, current + 1),
      last: this.pageCount,
    };
    if (!Object.hasOwn(targets, intent))
      throw new TypeError(`unknown page intent: ${intent}`);
    this.currentPage = targets[intent];
    return this.snapshot;
  }

  updateFromScroll(scrollTop, scrollHeight, clientHeight) {
    if (![scrollTop, scrollHeight, clientHeight].every(Number.isFinite)
        || scrollTop < 0 || scrollHeight <= 0 || clientHeight < 0) {
      throw new TypeError("scroll metrics must be finite and non-negative");
    }
    const maximum = Math.max(1, scrollHeight - clientHeight);
    const ratio = Math.max(0, Math.min(1, scrollTop / maximum));
    this.currentPage = Math.min(
      this.pageCount,
      Math.max(1, Math.floor(ratio * this.pageCount) + 1),
    );
    return this.snapshot;
  }

  get snapshot() {
    const ratio = this.pageCount === 1
      ? 0
      : (this.currentPage - 1) / (this.pageCount - 1);
    return Object.freeze({
      kind: "page-location-hint",
      currentPage: this.currentPage,
      pageCount: this.pageCount,
      yTwips: Math.round(ratio * Math.max(0, this.documentHeightTwips - 1)),
      label: `頁面位置提示：第 ${this.currentPage} / ${this.pageCount} 頁`,
    });
  }
}

export function classifyHyperlinkTarget(value) {
  if (typeof value !== "string" || value.length === 0)
    return { supported: false, code: "HYPERLINK_TARGET_UNAVAILABLE" };
  if (value.startsWith("#"))
    return { supported: true, kind: "internal-bookmark", target: value };
  let url;
  try {
    url = new URL(value);
  } catch {
    return { supported: false, code: "HYPERLINK_INVALID_TARGET" };
  }
  if (!["https:", "http:"].includes(url.protocol)) {
    return {
      supported: false,
      code: "HYPERLINK_SCHEME_BLOCKED",
      scheme: url.protocol,
    };
  }
  return { supported: true, kind: "external-url", target: url.href };
}

