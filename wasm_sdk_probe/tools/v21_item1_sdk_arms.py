#!/usr/bin/env python3
"""Item 1's two arms that drive the page's OWN SDK objects through S-3 (ruling D-7, superseded by S-3).

  d11c   D11c: a stale expectedRevision through the page's client, against a move-line-* control and a
         mutating control (spec §12.2 (f)); the engine's raw replies are in the item-1 snippet's log
  d12    D12: the page's client on a range: move-document-start/end must be refused with
         EDITOR_FORMAT_GESTURE_UNSUPPORTED, the selection and the document unchanged; a move-line-end
         control on the same range, and move-document-start on a caret that must complete

The hook (`tools/v21_page_hook.py`, Agent M) is used through its documented interface only: SNIPPET,
HookLog, call, state, capture_check.  Every load runs its positive control; a failed one makes the
round NOT_ESTABLISHED (`hook-not-captured`).
"""
from __future__ import annotations

import time
import traceback

import run_e2_c_product_path as pp
import v21_page_hook as hook

FLUSH = {"fn": lambda: None}


def _point(caret: dict) -> dict:
    return {"xTwips": caret["x"], "yTwips": caret["y"] + caret["height"] // 2}


def _load(ctx, round_rec: dict) -> hook.HookLog:
    from run_v21_shakedown_item1 import StepError, run_script  # noqa: F401
    log = hook.HookLog(ctx.session)
    round_rec["load"] = ctx.load("v21hook")
    log.reset()
    round_rec["open"] = ctx.open("plain3")
    round_rec["capture"] = hook.capture_check(ctx.session, log)
    if not round_rec["capture"].get("ok"):
        raise StepError(f"hook-not-captured: {round_rec['capture']}")
    round_rec["start"] = ctx.start_state()
    return log


def _raw_since(ctx, mark: int, action: str | None = None) -> list[dict]:
    ctx.log.drain()
    return [e for e in ctx.log.all[mark:] if e.get("k") == "rs" and e.get("op") == "editorActionV2"
            and (action is None or e.get("action") == action)]


def d11c(ctx, rounds: int) -> dict:
    from run_v21_shakedown_item1 import StepError
    out = {"arm": "d11c", "rounds": []}
    for round_no in range(1, rounds + 1):
        rec = {"round": round_no, "calls": []}
        out["rounds"].append(rec)
        try:
            log = _load(ctx, rec)
            rec["insert"] = hook.call(ctx.session, log, "document", "insertText", ["Z"])
            rec["stateAfterInsert"] = hook.state(ctx.session, log)
            for action, options in (("move-document-end", {"expectedRevision": 0}),
                                    ("move-line-home", {"expectedRevision": 0}),
                                    ("insert-paragraph-break", {"expectedRevision": 0})):
                before = ctx.ask().get("full")
                mark = len(ctx.log.all)
                answer = hook.call(ctx.session, log, "editor", "action", [action, options])
                time.sleep(0.5)
                after = ctx.ask().get("full")
                rec["calls"].append({"action": action, "options": options, "sdk": answer,
                                     "engine": _raw_since(ctx, mark, action), "before": before, "after": after})
            rec["outcome"] = "done"
        except StepError as error:
            rec["outcome"] = "hook-not-captured" if str(error).startswith("hook-not-captured") else "step-error"
            rec["error"] = str(error)
        except Exception as error:  # noqa: BLE001
            rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
            rec["trace"] = traceback.format_exc()[-1500:]
        FLUSH["fn"]()
    return out


def d12(ctx, rounds: int) -> dict:
    from run_v21_shakedown_item1 import StepError, run_script
    out = {"arm": "d12", "rounds": []}
    for round_no in range(1, rounds + 1):
        rec = {"round": round_no, "ranges": [], "control": None}
        out["rounds"].append(rec)
        try:
            log = _load(ctx, rec)
            points = {}
            for name, script in (("p2a", "k1024,k1027x6"), ("p2b", "k1027x6"), ("p3b", "k1024,k1028,k1027x7")):
                run_script(ctx, script, "placement", None)
                ctx.quiet()
                points[name] = (ctx.ask().get("full") or {}).get("caret")
            rec["points"] = points
            for label, end in (("single", "p2b"), ("cross", "p3b")):
                block = {"range": label}
                block["select"] = hook.call(ctx.session, log, "editor", "selectRange",
                                            [_point(points["p2a"]), _point(points[end])])
                time.sleep(0.4)
                block["before"] = ctx.ask().get("full")
                block["calls"] = []
                for action in ("move-document-start", "move-document-end", "move-line-end"):
                    mark = len(ctx.log.all)
                    answer = hook.call(ctx.session, log, "editor", "action", [action])
                    time.sleep(0.3)
                    block["calls"].append({"action": action, "sdk": answer, "engine": _raw_since(ctx, mark, action),
                                           "after": ctx.ask().get("full")})
                rec["ranges"].append(block)
            control = {"place": hook.call(ctx.session, log, "editor", "placeCaret",
                                          [points["p2a"]["x"], points["p2a"]["y"] + points["p2a"]["height"] // 2])}
            time.sleep(0.4)
            control["before"] = ctx.ask().get("full")
            mark = len(ctx.log.all)
            control["sdk"] = hook.call(ctx.session, log, "editor", "action", ["move-document-start"])
            control["engine"] = _raw_since(ctx, mark, "move-document-start")
            rec["control"] = control
            ctx.quiet()
            rec["save"] = ctx.save(f"d12-r{round_no}")
            rec["outcome"] = "done"
        except StepError as error:
            rec["outcome"] = "hook-not-captured" if str(error).startswith("hook-not-captured") else "step-error"
            rec["error"] = str(error)
        except Exception as error:  # noqa: BLE001
            rec["outcome"], rec["error"] = "runner-error", f"{type(error).__name__}: {error}"
            rec["trace"] = traceback.format_exc()[-1500:]
        FLUSH["fn"]()
    return out


def run(ctx, arm: str, rounds: int) -> dict:
    import run_v21_shakedown_item1 as runner
    FLUSH["fn"] = runner.FLUSH["fn"]
    return d11c(ctx, rounds) if arm == "d11c" else d12(ctx, rounds)
