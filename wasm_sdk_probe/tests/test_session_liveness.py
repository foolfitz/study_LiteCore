"""The dead-session guard, driven without a browser.

Finding 081: on the accessibility profile a save failed early, the session went
to `recoverable-error` with no checkpoint, and the runner drove the remaining
arms at a session that refused all of them with EDITOR_NOT_READY.  `pending` was
0 -- nothing was waiting on the engine -- so the twenty to fifty minutes were
not a hang, they were forty timeouts spent one after another on a session that
was already gone.  The report is written at the end, so the run yielded nothing.

`queue-a11y-path-drives-a-dead-session` is the fix, and this is the part of it
that can be held to its behaviour cheaply.  What it CANNOT establish is that the
guard is wired into the run -- that is what `--liveness-control` is for, and it
costs a browser.  Both exist because either one alone is a guard nobody has
seen fire.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_e2_c_product_path as probe  # noqa: E402

RUNNER = ROOT / "tools" / "run_e2_c_product_path.py"

ALIVE = {"state": "ready", "pending": "0", "latency": "存檔 120 ms"}
DEAD = {"state": "recoverable-error", "pending": "0", "checkpoint": "無",
        "latency": "儲存 失敗", "toast": "儲存：EDITOR_NOT_READY"}


def reader(*states):
    """A state source that answers each read in turn, then repeats the last."""
    queue = list(states)

    def read():
        return queue.pop(0) if len(queue) > 1 else queue[0]
    return read


class DeadSessionPredicate(unittest.TestCase):

    def test_the_states_that_refuse_everything_are_named(self):
        self.assertEqual(probe.dead_session(DEAD), "recoverable-error")
        self.assertEqual(
            probe.dead_session({"state": "restart-required"}),
            "restart-required")
        # `showExpired` hides the paper and disables every control, and nothing
        # recovers from it. It writes the pill directly, so the guard sees it
        # only because this list names it.
        self.assertEqual(probe.dead_session({"state": "expired"}), "expired")

    def test_a_working_session_is_not_dead(self):
        for state in (ALIVE, {"state": "busy"}, {}, None):
            with self.subTest(state=state):
                self.assertIsNone(probe.dead_session(state))

    def test_stopped_is_not_in_the_list_and_that_is_deliberate(self):
        """It is written in one place, the boot catch, and boot has its own gate.

        Named here so that adding it later is a decision somebody makes rather
        than a gap somebody finds.
        """
        self.assertIsNone(probe.dead_session({"state": "stopped"}))


class TheGuard(unittest.TestCase):

    def test_a_live_session_is_probed_and_the_run_continues(self):
        guard = probe.Liveness(reader(ALIVE))
        guard.probe("product-save-button-writes-a-real-odt", "after the check")
        self.assertEqual(guard.probes, 1)
        self.assertEqual(guard.last_state, "ready")
        self.assertIsNone(guard.died)

    def test_a_dead_session_stops_the_run_and_names_where_it_was_noticed(self):
        guard = probe.Liveness(reader(DEAD))
        with self.assertRaises(probe.SessionDied) as raised:
            guard.probe("format-a-paragraph-changes-that-paragraph",
                        "after this check was recorded")
        self.assertEqual(raised.exception.arm,
                         "format-a-paragraph-changes-that-paragraph")
        # The fields finding 081 was read off the stalled page, carried into
        # the report rather than re-derived by whoever opens it.
        self.assertEqual(guard.died["state"], "recoverable-error")
        self.assertEqual(guard.died["pending"], "0")
        self.assertEqual(guard.died["checkpoint"], "無")
        self.assertIn("EDITOR_NOT_READY", guard.died["toast"])

    def test_an_arm_that_induces_the_state_is_not_stopped_by_it(self):
        """The two recovery arms drive this state on purpose.

        And the guard does not merely forgive the state inside the region -- it
        does not ASK, which is what keeps the cost at one read per check.  The
        read on the way out is the one that matters, and here it finds the arm
        recovered.
        """
        reads = []

        def read():
            reads.append("read")
            return ALIVE          # the arm pressed the notice and recovered

        guard = probe.Liveness(read)
        with guard.expecting("notice-action-recovers-the-session", "047"):
            guard.probe("inside", "the inducer")     # must not raise
            self.assertEqual(reads, [], "no read is taken inside the region")
        self.assertEqual(len(reads), 1, "exactly one read on the way out")
        self.assertIsNone(guard.died)
        self.assertIsNone(guard.expected, "the region must not leak")

    def test_an_arm_that_leaves_the_session_dead_stops_the_run_naming_itself(self):
        """The innocent check that follows must not be blamed for it."""
        guard = probe.Liveness(reader(DEAD))
        with self.assertRaises(probe.SessionDied) as raised:
            with guard.expecting("recovery-returns-what-the-product-promised",
                                 "038"):
                pass
        self.assertEqual(raised.exception.arm,
                         "recovery-returns-what-the-product-promised")
        self.assertIn("leaving", guard.died["where"])

    def test_the_control_makes_the_inducing_arms_stop_the_run(self):
        """`--liveness-control` is the guard's positive control.

        Without this the two regions are the only places a dead session is
        known to occur on the shipped profile, and the guard could be dead code
        on every green run.
        """
        guard = probe.Liveness(reader(DEAD), control=True)
        with self.assertRaises(probe.SessionDied) as raised:
            with guard.expecting("notice-action-recovers-the-session", "047"):
                guard.probe("inside-the-inducer", "the arm's own probe")
        # WHERE it stopped, not merely THAT it stopped.  A region that still
        # holds the guard off under the control would let the arm run to its
        # end and stop on the way out, which raises the same exception and
        # measures nothing about the flag.
        self.assertEqual(raised.exception.arm, "inside-the-inducer")
        self.assertNotIn("leaving", guard.died["where"])
        self.assertEqual(guard.died["insideAnArmThatExpectedIt"], None,
                         "under the control the region holds nothing off")

    def test_the_controls_own_probe_is_silent_without_the_flag(self):
        """`under_control` must not add a probe to an ordinary run.

        It sits INSIDE the two inducing arms, where an ordinary run is supposed
        to see the dead state and carry on -- so a version of it that probed
        unconditionally would stop every run at the endnote inducer, which is
        the opposite of the defect being fixed.
        """
        guard = probe.Liveness(reader(DEAD))
        guard.under_control("recovery-returns-what-the-product-promised",
                            "after the inducer wedged")
        self.assertEqual(guard.probes, 0)
        self.assertIsNone(guard.died)

    def test_the_controls_own_probe_stops_the_run_with_the_flag(self):
        """And WHERE the arm is dead, which the check boundaries never see.

        The first control run went green end to end: the inducing arms recover
        before they record their check, so a probe that only runs at check
        boundaries can never meet the state they induce.
        """
        guard = probe.Liveness(reader(DEAD), control=True)
        with self.assertRaises(probe.SessionDied) as raised:
            guard.under_control("recovery-returns-what-the-product-promised",
                                "after the inducer wedged")
        self.assertEqual(raised.exception.arm,
                         "recovery-returns-what-the-product-promised")
        self.assertEqual(guard.died["state"], "recoverable-error")

    def test_the_guard_asks_once_and_then_stops_asking(self):
        """So the stopped run can record its own verdict without re-raising."""
        guard = probe.Liveness(reader(DEAD))
        with self.assertRaises(probe.SessionDied):
            guard.probe("first", "after the check")
        guard.probe("second", "after the check")     # must not raise
        self.assertEqual(guard.probes, 1)
        self.assertEqual(guard.died["noticedAfter"], "first")

    def test_a_read_that_fails_is_recorded_and_does_not_stop_the_run(self):
        """A browser that has gone away is a different failure.

        Recorded either way: a guard that could not ask must not look like a
        guard that asked and was satisfied.
        """
        def explode():
            raise RuntimeError("websocket closed")

        guard = probe.Liveness(explode)
        guard.probe("an-aborted-gesture-stops-selecting", "after the check")
        self.assertIsNone(guard.died)
        self.assertEqual(guard.probes, 0)
        self.assertIn("websocket closed", guard.probe_error)


class WhatTheGuardRecordsAboutItself(unittest.TestCase):
    """Raised by adversarial review, 2026-08-26.

    All three are about the RECORD rather than about stopping, and all three
    have the same shape: a guard that could not ask must not look like a guard
    that asked and was satisfied.
    """

    def test_a_page_with_no_state_pill_is_not_a_live_session(self):
        """`READ_STATE` answers `state: null` when `#state-pill` is gone.

        The page navigated, the document was replaced, the boot failed.  Before
        this, the guard counted the probe, wrote `lastState: null` and carried
        on -- satisfied by a page that is not there.
        """
        guard = probe.Liveness(reader({"state": None, "pending": None}))
        guard.probe("ctrl-v-reaches-the-document", "after the check")
        self.assertEqual(guard.probes, 0, "that was not a reading")
        self.assertEqual(guard.read_failures, 1)
        self.assertIsNone(guard.last_state)
        self.assertIn("#state-pill", guard.probe_error)

    def test_a_failed_read_clears_the_last_state_it_had(self):
        """Otherwise a read that died at check 10 leaves `ready` standing.

        And `lastState` in the report then reads as a statement about the end
        of the run, which is the opposite of what happened.
        """
        def read(state=[ALIVE]):
            if state:
                return state.pop()
            raise RuntimeError("target closed")

        guard = probe.Liveness(read)
        guard.probe("first", "after the check")
        self.assertEqual(guard.last_state, "ready")
        guard.probe("second", "after the check")
        self.assertIsNone(guard.last_state, "a stale state must not stand")
        self.assertEqual(guard.read_failures, 1)
        self.assertEqual(guard.probes, 1)

    def test_a_region_names_the_check_recorded_inside_it(self):
        """Region 1 is named for the notice check and encloses another one.

        `bulleting-a-blank-line-does-not-demand-a-rollback` is the check that
        puts the session into the state on the accessibility core.  Naming the
        REGION would report the run as stopping after the notice check when the
        bulleting cell was what killed it.
        """
        guard = probe.Liveness(reader(DEAD))
        with self.assertRaises(probe.SessionDied) as raised:
            with guard.expecting("notice-action-recovers-the-session", "047"):
                guard.recorded_inside = "bulleting-a-blank-line-does-not-demand-a-rollback"
        self.assertEqual(raised.exception.arm,
                         "bulleting-a-blank-line-does-not-demand-a-rollback")

    def test_a_region_that_recorded_nothing_says_so(self):
        guard = probe.Liveness(reader(DEAD))
        with self.assertRaises(probe.SessionDied) as raised:
            with guard.expecting("recovery-returns-what-the-product-promised",
                                 "038"):
                pass
        self.assertEqual(raised.exception.arm,
                         "recovery-returns-what-the-product-promised")
        self.assertIn("no check was recorded inside it", guard.died["where"])


class WhatAStoppedRunSaysItNeverReached(unittest.TestCase):

    def test_every_check_id_in_the_runner_is_found(self):
        ids = probe.declared_check_ids(RUNNER.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(ids), 40)
        self.assertEqual(len(ids), len(set(ids)), "ids must be deduplicated")
        # Two the reader can verify by eye, one at each end of the run.
        self.assertEqual(ids[0], "product-save-button-writes-a-real-odt")
        self.assertIn("recovery-returns-what-the-product-promised", ids)

    def test_the_stop_is_not_counted_as_a_check_the_run_should_have_reached(self):
        ids = probe.declared_check_ids(RUNNER.read_text(encoding="utf-8"))
        self.assertNotIn(probe.STOPPED_CHECK, ids)


class TheRecoveryPairIsHeldToItsRelation(unittest.TestCase):
    """Finding 046's cell is read twice; the two reads must agree.

    Added 2026-08-26 after an adversarial review pointed out that
    `notice-action-recovers-the-session`'s nine-day abstention is not a dead
    check -- it is the sentinel reading "046's disposition is still correct",
    and its partner is `bulleting-a-blank-line-does-not-demand-a-rollback`.
    Both directions are exercised by real runs on the same day: v8 gave
    PASS/NOT_ESTABLISHED and the accessibility profile gave FAIL/PASS.
    """

    def test_the_cell_that_does_not_block_leaves_nothing_to_press(self):
        self.assertTrue(probe.recovery_pairing_holds("PASS", "NOT_ESTABLISHED"))

    def test_the_cell_that_blocks_makes_the_recovery_check_judgeable(self):
        self.assertTrue(probe.recovery_pairing_holds("FAIL", "PASS"))

    def test_both_green_is_impossible(self):
        """There was no notice to press, so a PASS there read something else."""
        self.assertFalse(probe.recovery_pairing_holds("PASS", "PASS"))

    def test_a_blocked_queue_with_an_abstaining_recovery_check_is_impossible(self):
        """The precondition was reached; abstaining means it stopped looking."""
        self.assertFalse(probe.recovery_pairing_holds("FAIL", "NOT_ESTABLISHED"))

    def test_a_red_recovery_check_beside_a_green_cell_is_allowed(self):
        """`047's recipe dispatched nothing` is a product failure, not a
        pairing one, and a rule forbidding it would turn a real red into a
        confusing one."""
        self.assertTrue(probe.recovery_pairing_holds("PASS", "FAIL"))

    def test_a_run_that_recorded_only_one_of_them_has_no_relation_to_hold(self):
        self.assertIsNone(probe.recovery_pairing_holds(None, "PASS"))
        self.assertIsNone(probe.recovery_pairing_holds("PASS", None))


class TheGuardIsWiredIn(unittest.TestCase):
    """Static, and it is the weaker half on purpose.

    A substring is worth what a substring is worth (this tree has the scar):
    what these assert is that the call sites have not been deleted, not that
    they work.  The measurement is `--liveness-control`, which stops a real run
    on a real dead session.
    """

    def test_every_recorded_check_is_followed_by_a_probe(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('liveness.probe(cid, "after this check was recorded")',
                      source)

    def test_both_inducing_arms_hold_the_guard_off(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertEqual(source.count("with liveness.expecting("), 2,
                         "two arms induce the dead state on purpose; a third "
                         "would be a new claim and a missing one would stop "
                         "the run on a recovery it was measuring")

    def test_a_stopped_run_cannot_report_ok(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('if report.get("sessionDied"):', source)


if __name__ == "__main__":
    unittest.main()
