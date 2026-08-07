import assert from "node:assert/strict";
import test from "node:test";

import { PageHintNavigator, classifyHyperlinkTarget } from "../page-navigation.js";

test("page intents clamp to first and last page", () => {
  const navigator = new PageHintNavigator({ pageCount: 100, documentHeightTwips: 1_000_000 });
  assert.equal(navigator.target("previous").currentPage, 1);
  assert.equal(navigator.target("next").currentPage, 2);
  assert.equal(navigator.target("last").currentPage, 100);
  assert.equal(navigator.target("next").currentPage, 100);
  assert.equal(navigator.target("first").currentPage, 1);
});

test("scroll produces an explicitly approximate page hint", () => {
  const navigator = new PageHintNavigator({ pageCount: 10, documentHeightTwips: 100_000 });
  const middle = navigator.updateFromScroll(450, 1000, 100);
  assert.equal(middle.kind, "page-location-hint");
  assert.equal(middle.currentPage, 6);
  assert.match(middle.label, /頁面位置提示/);
});

test("hyperlink policy allows HTTP and bookmarks but blocks dangerous schemes", () => {
  assert.equal(classifyHyperlinkTarget("https://example.test/path").supported, true);
  assert.equal(classifyHyperlinkTarget("#bookmark").kind, "internal-bookmark");
  for (const value of ["javascript:alert(1)", "file:///etc/passwd", "macro:Run"])
    assert.equal(classifyHyperlinkTarget(value).code, "HYPERLINK_SCHEME_BLOCKED");
  assert.equal(classifyHyperlinkTarget("").code, "HYPERLINK_TARGET_UNAVAILABLE");
});
