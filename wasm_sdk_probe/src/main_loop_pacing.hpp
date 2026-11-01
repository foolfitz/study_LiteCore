#pragma once
// SPEC-M3-v29-tick-pacing, finding 177.  Core runs the main loop at 100 fps
// (vcl/headless/svpinst.cxx DoExecute, setTimeout pacing) and ImplYield returns
// after one user event, so it reaches the poll only when no event is left.  The
// ordered engine answers at the poll, and a typed character leaves 8-9 events
// behind it: 85 ms of waiting for ticks, against 4 ms before v23.  Taking the
// pacing away (immediate) gives 9.8 ms, but a loop that never waits spins a core
// on an idle document.  So: no pacing while there is work and for a short grace
// after it, core's own pacing otherwise.
//
// Pure, so the rule is tested without a browser.  The engine applies a Change
// through emscripten_set_main_loop_timing, on the engine thread, inside the poll.
//
// The poll is the only caller and is not reached on a tick that dispatched an
// event, so a mode cannot change in the middle of an event drain: a run of event
// ticks stays immediate until the poll next sees nothing to do for the grace.

namespace probe::pacing {

// Core's fps=100, as emscripten_set_main_loop_arg turns it into a timeout.
constexpr int kPacedTickMs = 10;
// Longer than the slowest gap C2 types at (200 ms), so steady typing never waits
// for a tick; short enough that an idle document spins for a fraction of a second.
constexpr double kGraceMs = 300.0;

enum class Mode { Paced, Immediate };
enum class Change { None, ToImmediate, ToPaced };

struct State {
  Mode mode = Mode::Paced;
  double lastWorkMs = 0.0;
};

// One poll.  `work`: this poll dispatched or replied, or something is waiting.
inline Change step(State &state, bool work, double nowMs) {
  if (work) {
    state.lastWorkMs = nowMs;
    if (state.mode == Mode::Immediate)
      return Change::None;
    state.mode = Mode::Immediate;
    return Change::ToImmediate;
  }
  if (state.mode == Mode::Immediate && nowMs - state.lastWorkMs >= kGraceMs) {
    state.mode = Mode::Paced;
    return Change::ToPaced;
  }
  return Change::None;
}

} // namespace probe::pacing
