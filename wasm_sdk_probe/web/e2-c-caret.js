// The product's caret gesture, with proof that it landed.
//
// Two things this exists to reconcile, both of them measured:
//
//   * SPEC E2-C 9.5.6: the gesture is not a detail.  A caret formed by a
//     zero-width `selectRange` and a caret formed by a click are different
//     states as far as the format barrier is concerned -- the same dispatch on
//     the same empty paragraph comes back `postcondition-not-met` after a click
//     and `multi-block-readback` after a selectRange.  A phase that drives the
//     product's failure paths with the non-product gesture measures a different
//     product.
//   * Finding 048: `placeCaret` returns before the click has taken effect.  Its
//     predicate -- some collapsed, observed caret exists -- is already true when
//     the document opens, while the click itself needs 22-28 ms.  A dispatch
//     that follows it immediately lands wherever the caret was BEFORE.
//
// So: click, then poll the caret until it reaches the line that was asked for,
// and fail rather than dispatch if it never does.  Not a fixed delay -- a delay
// long enough today is a delay that silently stops being long enough on a
// slower machine, a bigger document, or a build that got slower, and the
// failure it produces is a green cell that measured the wrong paragraph.
//
// This file is deliberately not under `editor-shell-v2/`: it is harness code,
// and the E2 shell bundle binds the product's modules.  A helper the product
// does not import has no business changing the shell digest.

/** Half the E1/E2 corpus's 390-twip line pitch: the widest slack that still
 *  cannot confuse two adjacent paragraphs. */
export const CARET_TOLERANCE_TWIPS = 195;

export function caretOf(state) {
  // The engine emits the rectangle as JSON `null` when it has none and as
  // `{x,y,width,height}` when it has one.  There is no `available` field --
  // asking for one yields undefined for a caret that is perfectly well
  // reported, which is how the first version of this check managed to refuse
  // every cell in both arms.
  const caret = state?.caret ?? null;
  return {
    available: caret !== null && caret !== undefined,
    x: caret?.x ?? null, y: caret?.y ?? null, height: caret?.height ?? null,
    observed: state?.selection?.observed ?? null,
    collapsed: state?.selection?.collapsed ?? null,
    selectionType: state?.selectionType ?? null,
  };
}

/** Is the reported caret on the line that was asked for?
 *
 *  Measured against the TOP of the caret rectangle, not against the rectangle
 *  plus slack: the corpus's heading line is 414 twips tall, and a rule that
 *  accepted anywhere inside it would have accepted a caret stranded on
 *  paragraph one for a click 532 twips below -- passing the very case the
 *  check exists to catch. */
export function caretCovers(caret, yTwips) {
  if (!caret?.available || !Number.isFinite(caret.y)) return false;
  return Math.abs(yTwips - caret.y) <= CARET_TOLERANCE_TWIPS;
}

/**
 * Click at (x, y) and return once the engine reports the caret there.
 *
 * Resolves to `{caret, arrivedAfterMs}`.  Throws `CARET_NOT_AT_ANCHOR` if the
 * caret has not arrived by the deadline, carrying the last reading so a failed
 * cell says where the caret actually was.
 */
export async function placeCaretVerified(session, xTwips, yTwips, options = {}) {
  const tolerance = options.toleranceTwips ?? CARET_TOLERANCE_TWIPS;
  const started = performance.now();
  // The PRODUCT does the waiting now: `EditorSession.placeCaret` returns only
  // once the engine has acknowledged the click and the caret is on the clicked
  // line (finding 048's fix).  This used to carry its own polling loop, and
  // keeping it would mean the harness proved a property of the harness.
  const placed = await session.placeCaret(xTwips, yTwips, options);
  const caret = caretOf(placed?.state ?? await session.editor.getState());
  // Checked again anyway, and deliberately: the point of a harness gate is to
  // fail when the thing it drives is wrong, and the thing it drives is the code
  // that just claimed success.  A gate that trusts its subject is decoration.
  if (!caret.available || Math.abs(yTwips - caret.y) > tolerance) {
    throw Object.assign(
      new Error(`the product reported the caret placed, but it reads back at `
                + `${caret?.y ?? "none"} for a click at y=${yTwips}`),
      { code: "CARET_NOT_AT_ANCHOR", details: { xTwips, yTwips, caret } });
  }
  return {
    caret,
    arrivedAfterMs: placed?.caretWaitedMs ?? Math.round(performance.now() - started),
    confirmedBy: placed?.caretConfirmedBy ?? null,
  };
}
