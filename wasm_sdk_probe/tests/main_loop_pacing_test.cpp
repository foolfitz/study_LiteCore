// SPEC-M3-v29-tick-pacing 5: the pacing rule, without a browser.
#include "main_loop_pacing.hpp"
#include <cstdio>
using namespace probe::pacing;
static int failures = 0;
#define CHECK(condition) do { if (!(condition)) { std::printf("FAIL %d: %s\n", __LINE__, #condition); ++failures; } } while (0)

int main() {
  {  // Idle from the start: nothing ever changes, core's pacing stays.
    State s;
    for (int t = 0; t < 100000; t += 10)
      CHECK(step(s, false, t) == Change::None);
    CHECK(s.mode == Mode::Paced);
  }
  {  // Work takes the pacing away once, and only once.
    State s;
    CHECK(step(s, true, 1000) == Change::ToImmediate);
    CHECK(step(s, true, 1001) == Change::None);
    CHECK(s.mode == Mode::Immediate);
  }
  {  // Idle polls inside the grace keep it; the first one past the grace returns it, once.
    State s;
    step(s, true, 1000);
    CHECK(step(s, false, 1000 + kGraceMs - 1) == Change::None);
    CHECK(s.mode == Mode::Immediate);
    CHECK(step(s, false, 1000 + kGraceMs) == Change::ToPaced);
    CHECK(step(s, false, 1000 + kGraceMs + 1) == Change::None);
    CHECK(s.mode == Mode::Paced);
  }
  {  // Steady typing at C2's slowest gap never returns to the pacing.
    State s;
    int changes = 0;
    for (int t = 0; t < 60000; ++t) {
      const Change c = step(s, t % 200 == 0, t);
      changes += c != Change::None;
    }
    CHECK(changes == 1);
    CHECK(s.mode == Mode::Immediate);
  }
  {  // Work after the return takes it away again: the loop cannot stick paced.
    State s;
    step(s, true, 0);
    CHECK(step(s, false, 1000) == Change::ToPaced);
    CHECK(step(s, true, 2000) == Change::ToImmediate);
  }
  CHECK(kPacedTickMs == 10);
  std::printf(failures ? "RED %d\n" : "main_loop_pacing OK\n", failures);
  return failures != 0;
}
