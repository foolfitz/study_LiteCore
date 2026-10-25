# Claude input review request

Read-only adversarial review of the new direct-entry / F2 code and section 13 acceptance. Invocation: `claude -p --output-format json --permission-mode dontAsk --tools Read,Glob,Grep --strict-mcp-config`. No writes, builds, service operations or agent spawning are authorized for the reviewer. Findings must be concrete, reproducible and cite current source locations. Scope includes first-character/IME/focus handling, shortcut isolation, selection races and readonly/protection. Review uses its own Claude Code authentication and context; the work order points to the repository instructions/spec/handoff explicitly.

The initial Firefox failure in browser-entry-01 was a runner key-code error (WebDriver U+E031 = F1, U+E032 = F2), corrected in the runner. The preserved failure is not relabeled as a product failure.
