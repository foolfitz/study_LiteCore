# Evidence for finding 099

Finding 099 was found and fixed together with 098, in the same file and the same
change (shell generation v52). Its evidence lives with 098's:
`findings/evidence/098/README.md`, section 1 (unit level).

Measured at unit level only: the real session code against the test file's fixture
engine, which restarts revisions at zero on every open as the engine does
(`src/probe_engine.cpp`, `gState.revision = 0` in open). A browser reproduction needs
two induced deaths and a revision coincidence and has not been run.
