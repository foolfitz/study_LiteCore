# S5 order preparation 01: sandbox setup refusal

The preparation runner exited 1 before opening a browser. The sandbox prohibits creation of the local server socket: `PermissionError: [Errno 1] Operation not permitted`, in `run_browser_probe.free_port()` via `v21_shakedown_common.served()`. The preceding system-service probes also printed `Failed to create stream fd: Operation not permitted`.

`report.json` retains the invocation/configuration and has zero runs. No cell verdict exists and nothing counts. The same requested two-cell population was subsequently collected outside the sandbox, with execution approval, into the separate `../s5-order-prep-02/` directory. This setup failure is not a retry of a measured cell.
