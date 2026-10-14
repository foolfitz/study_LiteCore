// SPEC-M3-scroll-page-bubble (the owner's request of 2026-10-14: a bubble next
// to the scrollbar thumb showing the current page while scrolling; the owner
// ruled it shows on ANY scroll of the desk and fades after scrolling stops).
//
// U1-U3 of the spec.  The page's pure functions and its wiring are taken from
// the page source and driven here against a fake desk, a fake document and
// mocked time, as page-held-deletes.test.mjs does.  `PAGE_SOURCE=<path>` runs
// the same tests against another copy of the page: on the page before this
// change (`aa50cd20…`, host 0.2.22) everything is red because the functions do
// not exist, which is the witness kept in findings/evidence/scroll-page-bubble/.
// The spec's mutations (U2: no clamp, thumb minimum 0; U3: the timer not
// reset) are red on copies of the new page, same directory.

import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const SOURCE = readFileSync(process.env.PAGE_SOURCE || here("../../web/e2-editor-app.js"), "utf8");

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => new RegExp(`^function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m");
const constant = (name) => slice(new RegExp(`^const ${name} = [^\\n]*$`, "m"), name);   // the whole line, trailing comment and all

/** The two pure functions and the constants they read, compiled from the page. */
function pure() {
  // eslint-disable-next-line no-new-func
  return new Function(`
    ${["SCROLL_BUBBLE_HOLD_MS", "SCROLL_BUBBLE_FADE_MS", "SCROLL_BUBBLE_THUMB_MIN_PX", "SCROLL_BUBBLE_ARROW_PX",
       "SCROLL_BUBBLE_RAIL_MIN_PX", "SCROLL_BUBBLE_GAP_PX"].map(constant).join("\n")}
    ${slice(fn("scrollBubbleText"), "scrollBubbleText()")}
    ${slice(fn("scrollBubblePlace"), "scrollBubblePlace()")}
    return { scrollBubbleText, scrollBubblePlace,
             HOLD: SCROLL_BUBBLE_HOLD_MS, FADE: SCROLL_BUBBLE_FADE_MS };
  `)();
}

// The desks K4 measured on the host (findings/evidence/host-0.2.21/README.md):
// Firefox 157, an overlay scrollbar (no rail, no arrows); Chrome 151, a classic
// bar 15 px wide with arrow buttons.  Both at scrollTop 4900 of the 60-page
// fixture, where the screenshots put the thumb's centre at about 230 / 234.
const FIREFOX = Object.freeze({ top: 160, bottom: 954, left: 8, right: 1842, scrollTop: 4900, scrollHeight: 74182,
                                clientHeight: 794, offsetWidth: 1834, clientWidth: 1834, clientLeft: 0, direction: "ltr" });
const CHROME = Object.freeze({ top: 160, bottom: 940, left: 8, right: 1842, scrollTop: 4900, scrollHeight: 74182,
                               clientHeight: 780, offsetWidth: 1834, clientWidth: 1819, clientLeft: 0, direction: "ltr" });
const BUBBLE = Object.freeze({ width: 80, height: 26 });

test("U1: the bubble says the status line's page part and nothing else", () => {
  const { scrollBubbleText } = pure();
  assert.equal(scrollBubbleText("第 4–5 頁，共 60 頁"), "第 4–5 頁");
  assert.equal(scrollBubbleText("第 4 頁，共 60 頁"), "第 4 頁");
  assert.equal(scrollBubbleText("第 60 頁，共 60 頁"), "第 60 頁");
  assert.equal(scrollBubbleText(null), null);
  assert.equal(scrollBubbleText(""), null);
  assert.equal(scrollBubbleText(undefined), null);
  assert.equal(scrollBubbleText("—"), null, "a dash is not a page");
});

test("U2: the place follows the thumb's proportion and stays inside the desk", () => {
  const { scrollBubblePlace } = pure();
  // The model on K4's two desks: a = 0 / 17, t = 20 (spec §5: 222 / 236, ±1).
  const firefox = scrollBubblePlace(FIREFOX, BUBBLE);
  assert.ok(Math.abs(firefox.centreY - 222) <= 1, `firefox centre ${firefox.centreY}`);
  assert.equal(firefox.side, "right");
  assert.equal(firefox.edgeX, FIREFOX.right - 18, "overlay scrollbar: 12 px rail minimum + 6 px gap");
  const chrome = scrollBubblePlace(CHROME, BUBBLE);
  assert.ok(Math.abs(chrome.centreY - 236) <= 1, `chrome centre ${chrome.centreY}`);
  assert.equal(chrome.edgeX, CHROME.right - 21, "classic scrollbar: 15 px rail + 6 px gap");
  // The ends: clamped so the whole bubble stays inside the desk.
  const atTop = scrollBubblePlace({ ...FIREFOX, scrollTop: 0 }, BUBBLE);
  assert.ok(atTop.centreY >= FIREFOX.top + BUBBLE.height / 2, `top ${atTop.centreY}`);
  const atEnd = scrollBubblePlace({ ...FIREFOX, scrollTop: FIREFOX.scrollHeight - FIREFOX.clientHeight }, BUBBLE);
  assert.ok(atEnd.centreY <= FIREFOX.bottom - BUBBLE.height / 2, `end ${atEnd.centreY}`);
  assert.ok(atEnd.centreY > atTop.centreY);
  // Past the end (overscroll) is the end.
  const past = scrollBubblePlace({ ...FIREFOX, scrollTop: FIREFOX.scrollHeight }, BUBBLE);
  assert.equal(past.centreY, atEnd.centreY);
  // A short document: the thumb is long, so the proportion runs over a short track.
  const short = scrollBubblePlace({ ...FIREFOX, scrollHeight: 1588, scrollTop: 397 }, BUBBLE);   // t = 397, f = 0.5
  assert.ok(Math.abs(short.centreY - (160 + 397 / 2 + 0.5 * (794 - 397))) <= 1, `short ${short.centreY}`);
});

test("U2: nothing to scroll -> null; the scrollbar's side is read from the desk, not the locale", () => {
  const { scrollBubblePlace } = pure();
  assert.equal(scrollBubblePlace({ ...FIREFOX, scrollHeight: 794 }, BUBBLE), null);
  assert.equal(scrollBubblePlace({ ...FIREFOX, scrollHeight: 500 }, BUBBLE), null);
  assert.equal(scrollBubblePlace({ ...FIREFOX, scrollHeight: NaN }, BUBBLE), null);
  // RTL with a classic bar: clientLeft carries the bar's width (MDN), the bubble mirrors.
  const rtlClassic = scrollBubblePlace({ ...CHROME, clientLeft: 15, direction: "rtl" }, BUBBLE);
  assert.equal(rtlClassic.side, "left");
  assert.equal(rtlClassic.edgeX, CHROME.left + 21);
  // RTL with an overlay bar: no width to read, the direction decides.
  const rtlOverlay = scrollBubblePlace({ ...FIREFOX, direction: "rtl" }, BUBBLE);
  assert.equal(rtlOverlay.side, "left");
  assert.equal(rtlOverlay.edgeX, FIREFOX.left + 18);
});

/** The page's wiring compiled against a fake desk, document and clock. */
function page({ status = "第 4–5 頁，共 60 頁", hidden = false, desk = FIREFOX, reduce = false } = {}) {
  const inserted = [];
  const nodes = [];
  const makeNode = () => {
    const node = { id: "", style: {}, dataset: {}, attributes: {}, textContent: "",
                   offsetWidth: BUBBLE.width, offsetHeight: BUBBLE.height,
                   setAttribute(name, value) { this.attributes[name] = String(value); },
                   getAttribute(name) { return this.attributes[name] ?? null; } };
    nodes.push(node);
    return node;
  };
  const el = {
    desk: { ...desk, getBoundingClientRect: () => ({ top: desk.top, bottom: desk.bottom, left: desk.left, right: desk.right }),
            insertAdjacentElement(where, node) { inserted.push([where, node]); } },
    pageStatus: { hidden, textContent: status },
    canvas: { height: 0 },
  };
  const updates = [];
  // eslint-disable-next-line no-new-func
  const api = new Function("el", "session", "docRows", "document", "matchMedia", "getComputedStyle", "updatePageStatus", `
    ${["SCROLL_BUBBLE_HOLD_MS", "SCROLL_BUBBLE_FADE_MS", "SCROLL_BUBBLE_THUMB_MIN_PX", "SCROLL_BUBBLE_ARROW_PX",
       "SCROLL_BUBBLE_RAIL_MIN_PX", "SCROLL_BUBBLE_GAP_PX"].map(constant).join("\n")}
    ${slice(fn("scrollBubbleText"), "scrollBubbleText()")}
    ${slice(fn("scrollBubblePlace"), "scrollBubblePlace()")}
    ${slice(/^const scrollBubble = \{[^\n]*\};$/m, "the scrollBubble record")}
    ${slice(fn("scrollBubbleElement"), "scrollBubbleElement()")}
    ${slice(fn("showScrollBubble"), "showScrollBubble()")}
    ${slice(fn("hideScrollBubble"), "hideScrollBubble()")}
    ${slice(fn("onDeskScroll"), "onDeskScroll()")}
    return { scroll: onDeskScroll, hide: hideScrollBubble, node: () => scrollBubble.element };
  `)(el, null, 0, { createElement: () => makeNode() },
     (query) => ({ media: query, matches: reduce && /prefers-reduced-motion: reduce/.test(query) }),
     () => ({ direction: desk.direction }), () => updates.push(Date.now()));
  return { api, el, inserted, nodes, updates };
}

test("U3: a scroll shows the bubble with the page part next to the thumb; the resize hides it", () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });   // setTimeout's mock covers clearTimeout
  try {
    const { api, el, inserted, updates } = page();
    api.scroll();
    const node = api.node();
    assert.ok(node, "the element is made on the first scroll");
    assert.equal(updates.length, 1, "the page number is recomputed first (page-number.test's pin)");
    assert.deepEqual(inserted, [["afterend", node]], "a sibling after #desk, not a child of the scroller");
    assert.equal(node.id, "scroll-bubble");
    assert.equal(node.dataset.shown, "1");
    assert.equal(node.textContent, "第 4–5 頁");
    assert.equal(node.style.position, "fixed");
    assert.equal(node.style.visibility, "visible");
    assert.equal(node.style.opacity, "1");
    const centre = parseFloat(node.style.top);
    assert.ok(Math.abs(centre - 222) <= 1, `top ${node.style.top} is the thumb's centre (translateY(-50%))`);
    assert.match(node.style.transform, /translateY\(-50%\)/);
    assert.equal(parseFloat(node.style.left), FIREFOX.right - 18 - BUBBLE.width, "right-aligned to the rail's gap");
    // Finding 087/088: scrolling must not speak, and the bubble takes no focus.
    assert.equal(node.attributes["aria-hidden"], "true");
    assert.equal(node.attributes.role, undefined);
    assert.equal(node.attributes["aria-live"], undefined);
    assert.equal(node.attributes.tabindex, undefined);
    assert.equal(node.style.pointerEvents, "none");
    assert.equal(el.pageStatus.textContent, "第 4–5 頁，共 60 頁", "the status line is untouched");
    api.hide();
    assert.equal(node.dataset.shown, "0");
  } finally {
    mock.timers.reset();
  }
});

test("U3: every scroll resets the clock; 1,000 ms after the last one it hides, 180 ms later it is gone", () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });   // setTimeout's mock covers clearTimeout
  try {
    const { api } = page();
    api.scroll();
    const node = api.node();
    mock.timers.tick(600);
    api.scroll();                       // the second event, 600 ms in
    mock.timers.tick(500);              // 1,100 ms after the first: a timer that was not reset would have fired
    assert.equal(node.dataset.shown, "1", "the timer is reset by the second scroll");
    assert.equal(node.style.opacity, "1");
    mock.timers.tick(499);              // 999 ms after the second
    assert.equal(node.dataset.shown, "1");
    mock.timers.tick(1);                // 1,000 ms after the second
    assert.equal(node.dataset.shown, "0");
    assert.equal(node.style.opacity, "0");
    assert.equal(node.style.visibility, "visible", "still visible while it fades");
    mock.timers.tick(180);
    assert.equal(node.style.visibility, "hidden");
    assert.match(node.style.transition, /opacity 180ms/);
    // A scroll during the fade brings it straight back.
    api.scroll();
    assert.equal(node.dataset.shown, "1");
    assert.equal(node.style.visibility, "visible");
    mock.timers.tick(1000);             // the hold; the hide schedules the fade from here
    mock.timers.tick(180);              // (one tick(1180) skips a timer scheduled inside it at its boundary -- the mock, not the page)
    assert.equal(node.style.visibility, "hidden");
  } finally {
    mock.timers.reset();
  }
});

test("U3: reduced motion -> no transition, hidden at once; the 1 s hold is not motion and stays", () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });   // setTimeout's mock covers clearTimeout
  try {
    const { api } = page({ reduce: true });
    api.scroll();
    const node = api.node();
    assert.equal(node.style.transition, "none");
    assert.equal(node.dataset.shown, "1");
    mock.timers.tick(999);
    assert.equal(node.dataset.shown, "1");
    mock.timers.tick(1);
    assert.equal(node.dataset.shown, "0");
    assert.equal(node.style.visibility, "hidden", "no fade to wait for");
  } finally {
    mock.timers.reset();
  }
});

test("U3: no page number, or nothing to scroll -> the bubble never shows", () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });   // setTimeout's mock covers clearTimeout
  try {
    for (const options of [{ hidden: true }, { status: "" }, { desk: { ...FIREFOX, scrollHeight: 794 } }]) {
      const { api } = page(options);
      api.scroll();
      const node = api.node();
      assert.ok(!node || node.dataset.shown !== "1", `shown for ${JSON.stringify(options)}`);
      assert.ok(!node || node.style.visibility !== "visible");
    }
    // The positive control of the same clauses: the same page with a number and a scroll shows.
    const { api } = page();
    api.scroll();
    assert.equal(api.node().dataset.shown, "1");
  } finally {
    mock.timers.reset();
  }
});

test("U3: a window resize hides the bubble (its own listener; the canvas's keeps its mutation-anchored bytes)", () => {
  slice(/^globalThis\.addEventListener\("resize", hideScrollBubble\);$/m, "the bubble's resize listener");
  const canvasListener = slice(/^globalThis\.addEventListener\("resize", \(\) => \{[\s\S]*?\n\}\);$/m, "the canvas's resize listener");
  assert.doesNotMatch(canvasListener, /ScrollBubble/, "resize-does-not-repaint's anchor is untouched");
});
