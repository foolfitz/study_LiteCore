#!/usr/bin/env python3
"""Write the Markdown corpus (UTF-8 bytes) into tool/corpus/. Deterministic.

Usage: make_corpus.py OUT_DIR [LISTENER_PORT]
LISTENER_PORT (default 18765) is baked into M11b's image URL: a local HTTP
listener the runner starts, so whether the process fetches the URL is observed.
LISTENER_PORT + 1 is M11c's: a local socket that accepts and never answers.
"""

import base64
import os
import struct
import sys
import zlib


def png(width, height, rgb=(200, 30, 30)):
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


BLOCK = """## Section {n}

Paragraph {n} with **bold {n}**, *italic {n}* and `code {n}`; 中文段落 {n}。

- item {n}.1
- item {n}.2
  - nested {n}

1. step {n}.1
2. step {n}.2

```
code block {n}
```

| k | v |
| --- | --- |
| a{n} | {n} |

"""


def big(target):
    out, n = [], 0
    size = 0
    while size < target:
        n += 1
        block = BLOCK.format(n=n)
        out.append(block)
        size += len(block.encode("utf-8"))
    return "".join(out)


def corpus(port):
    data_url = "data:image/png;base64," + base64.b64encode(png(4, 3)).decode("ascii")
    return {
        "M1": "# Heading one\n\n## Heading two\n\n### Heading three\n",
        "M2": "Plain **bold** and *italic* and `inline code` end.\n",
        "M3": "```\ncode line 1\n  indented line 2\n```\n",
        "M4": ("- apple\n- banana\n  - nested one\n  - nested two\n- cherry\n\n"
               "1. first\n2. second\n3. third\n"),
        "M5": "| Name | Value |\n| --- | --- |\n| a | 1 |\n| b | 2 |\n",
        "M6": "See [example](https://example.org) here.\n",
        "M7": "> quoted line one\n> quoted line two\n\n---\n\nafter rule\n",
        "M8": "# 標題\n\n**粗體中文**\n\n- 第一項\n- 第二項\n- 第三項\n",
        # sw/qa/filter/md/md.cxx:1047-1055 testCTLPaste (tdf#172084): exactly this, no newline.
        "M9": "שלום",
        "M10": "Before ![dot](" + data_url + ") after.\n",
        # Refuses fast: nothing listens on the discard port (checked by the runner).
        "M11": "Before ![remote](http://127.0.0.1:9/x.png) after.\n",
        # A local listener that logs any request (runner), returns 404.
        "M11b": "Before ![remote](http://127.0.0.1:%d/x.png) after.\n" % port,
        # Added after the first full run: a local "tarpit" (runner) that accepts
        # the connection and never answers -- how long does paste() wait?
        "M11c": "Before ![slow](http://127.0.0.1:%d/x.png) after.\n" % (port + 1),
        "M12": "See [[Page]] here.\n",
        "M13": "",
        "M14a": big(16 * 1024),
        "M14b": big(256 * 1024),
        # Red control C1: M1 + M2 pasted as text/plain (must stay literal).
        "C1": "# Heading one\n\n## Heading two\n\n### Heading three\n" +
              "Plain **bold** and *italic* and `inline code` end.\n",
    }


def main(argv):
    out = argv[1]
    port = int(argv[2]) if len(argv) > 2 else 18765
    os.makedirs(out, exist_ok=True)
    for name, text in corpus(port).items():
        with open(os.path.join(out, name + ".md"), "wb") as handle:
            handle.write(text.encode("utf-8"))
    # Encoding variant (observed arm E-u16): M8 as UTF-16LE bytes, to be sent
    # with "text/markdown;charset=utf-16".
    with open(os.path.join(out, "M8-utf16le.bin"), "wb") as handle:
        handle.write(corpus(port)["M8"].encode("utf-16-le"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
