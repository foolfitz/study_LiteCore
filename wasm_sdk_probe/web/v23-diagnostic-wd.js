// W-D inputs are the fixed native sequences, with their public/private route
// recorded explicitly. No public gesture permission is changed by this page.
export const WD_FIXTURES = Object.freeze({
  d1: 'numbered-second', d2: 'abcd', d2p: 'abcd', d3: 'abcd',
  d4: 'abcd', d5: 'abcd', d6: 'abcd', merge: 'plain3',
  d7i: 'bullet', d7ii: 'bullet', d7iii: 'indent', d7plain: 'plain3',
});

export async function runWd({session, step, b64}, {caseId}) {
  if (!Object.hasOwn(WD_FIXTURES, caseId)) throw new Error(`unknown W-D case ${caseId}`);
  const engine = session.engine, doc = session.document;
  const result = {caseId, fixture: WD_FIXTURES[caseId], sequence: [], locator: null};
  const invoke = async (route, name, fn) => {
    const item = {route, name}; result.sequence.push(item);
    const value = await step(`wd/${name}`, fn);
    item.result = value;
    if (Number.isInteger(value?.revision)) doc.revision = value.revision;
    return value;
  };
  const action = (name, enabled = false) => invoke('public', name, () => engine._request('editorActionV2', {
    documentHandle: doc.handle, expectedRevision: doc.revision,
    action: name, extendSelection: false, enabled,
  }));
  const control = (kind, name) => invoke('private-closed-input', name,
    () => engine._request('v23Diagnostic', {kind}));
  const state = () => invoke('public-observer', 'state', () => engine._request('editorGetStateV2', {
    documentHandle: doc.handle,
  }));
  const selection = () => invoke('public-observer', 'selection', () => doc.getSelection());
  const right = () => action('move-character-right');
  const left = () => action('move-character-left');
  const times = async (n, fn) => {for (let i = 0; i < n; ++i) await fn();};
  // Issue the whole burst immediately, bypassing the shell's serial action
  // queue. The real engine still owns ordering and post-command completion.
  const burst = (...calls) => Promise.all(calls.map(fn => fn()));
  result.before = await state();

  if (caseId === 'd1') {
    await burst(() => action('move-line-down'), () => action('move-document-start'),
      () => action('delete-backward'));
  } else if (caseId === 'd2') {
    await times(3, right);
    await burst(right, left, () => action('delete-forward'));
  } else if (caseId === 'd2p') {
    await right();
    await burst(right, right, () => action('delete-backward'));
  } else if (caseId === 'd3') {
    await right();
    await burst(left, right, () => invoke('public', 'insert-x', () => doc.insertText('x')));
  } else if (caseId === 'd4') {
    await burst(() => control(6, 'shift-right'), () => control(4, 'left-on-range'),
      () => action('set-bold', true));
  } else if (caseId === 'd5') {
    await times(3, right);
    await burst(right, () => control(5, 'shift-left'), () => action('delete-selection'));
  } else if (caseId === 'd6') {
    await times(3, right);
    const point = (await state()).caret;
    if (!point || !Number.isInteger(point.x) || !Number.isInteger(point.y)
        || !Number.isInteger(point.height)) throw new Error('missing actual click target');
    result.clickTarget = point;
    await times(2, left);
    await burst(left, () => invoke('public', 'place-recorded-caret', () => engine._request('editorPlaceCaretV2', {
      documentHandle: doc.handle, xTwips: point.x, yTwips: point.y + Math.trunc(point.height / 2),
    })), () => invoke('public', 'insert-x', () => doc.insertText('x')));
  } else if (caseId === 'merge') {
    await action('move-line-down'); await action('move-line-home');
    result.deleteResult = await action('delete-backward');
  } else {
    // The shipping-core D7 limitation remains open: a K1 NONE response does
    // not send the user's raw destructive key. Save the same-process control.
    if (caseId === 'd7i') await left();
    else {await right(); await left();}
    result.unchangedBeforeBase64 = b64(await doc.save());
    result.revisionBeforeDelete = doc.revision;
    result.deleteResult = await action(caseId === 'd7i' ? 'delete-forward' : 'delete-backward');
  }
  result.after = await state();
  // Save BEFORE the locator changes any selection, just like native S,L.
  result.savedBase64 = b64(await doc.save());
  result.locatorBefore = await selection();
  await control(7, 'locator-shift-end');
  const suffix = await selection();
  await control(8, 'locator-shift-home');
  const prefix = await selection();
  result.locator = [prefix.text, suffix.text];
  return result;
}
