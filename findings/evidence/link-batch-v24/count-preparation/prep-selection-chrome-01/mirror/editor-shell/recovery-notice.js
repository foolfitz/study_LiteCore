/**
 * What a host should tell the user about a stopped session, decided from the
 * state snapshot alone.
 *
 * The session takes a checkpoint save before every selection gesture, because
 * the engine defect behind finding 038 leaves it able to save right up until
 * the first selection *read* and unable to save for ever after.  By the time a
 * host renders an error, therefore, the rescued bytes either already exist or
 * never will -- and until this module existed nothing told the user which.
 * The work sat in memory, the user looked at a dead editor, and the two facts
 * never met.
 *
 * This returns decisions, not wording.  Hosts differ in language and layout;
 * what they must not differ on is whether they claim work was preserved.
 */
export function recoveryNotice(snapshot = {}) {
  const hidden = {
    visible: false,
    hasCheckpoint: false,
    checkpointRevision: null,
    canRescue: false,
    restartPossible: false,
    checkpointFailed: false,
  };
  const stopped = snapshot.state === "recoverable-error"
    || snapshot.state === "restart-required";
  const hasCheckpoint = snapshot.hasCheckpoint === true;
  // A session that never got an engine has no "since the last save" to talk
  // about, and telling someone whose page load failed that their unsaved edits
  // are gone would be inventing a loss.  `generation` counts the engines this
  // session has had, so it is 0 exactly in that case.
  const hadEngine = hasCheckpoint || snapshot.generation > 0;
  if (!stopped || !hadEngine)
    return hidden;
  // A generation-limited session cannot restart, so the download stops being a
  // convenience and becomes the only way out.  A host that still points at its
  // restart button here is sending the user to a control that will refuse them.
  const exhausted = snapshot.error?.code === "WORKER_GENERATION_LIMIT"
    || snapshot.error?.details?.requiresPageReload === true;
  // "There is nothing to rescue" and "we tried to protect your work and the
  // save failed" both arrive here as canRescue: false, and they are not the
  // same thing to say to someone.  The second one is the case where the user
  // is about to lose work they believe is safe, so it gets its own decision
  // rather than being folded into silence (SPEC-E1-C 4.1, v8).
  const checkpointFailed = !hasCheckpoint && Boolean(snapshot.checkpointError);
  return {
    visible: true,
    hasCheckpoint,
    checkpointRevision: hasCheckpoint && Number.isInteger(snapshot.checkpointRevision)
      ? snapshot.checkpointRevision
      : null,
    canRescue: hasCheckpoint,
    restartPossible: !exhausted,
    checkpointFailed,
  };
}
