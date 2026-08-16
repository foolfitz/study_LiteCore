#!/usr/bin/env python3
"""Serve the probe dist directory with cross-origin isolation headers."""

from __future__ import annotations

import argparse
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ProbeRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        if re.search(
            r"\.[0-9a-f]{12,64}\.(?:js|wasm|data|metadata|json)$",
            self.path.split("?", 1)[0],
        ):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    # A root other than dist/ exists for exactly one purpose: serving a mirror
    # of dist in which one file has been deliberately broken, so that a check
    # can be shown to go red.  It must never be pointed at dist itself with an
    # edit in place -- the mirror is built in a scratch directory and dist stays
    # byte-identical (tools/run_e2_c_product_path.py --mutate).
    parser.add_argument("--root", default=None,
                        help="serve this directory instead of dist/")
    args = parser.parse_args()

    dist = (Path(args.root).resolve() if args.root
            else Path(__file__).resolve().parent.parent / "dist")
    handler = partial(ProbeRequestHandler, directory=str(dist))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving {dist} at http://{args.host}:{args.port}/index.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
