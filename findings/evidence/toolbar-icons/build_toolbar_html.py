#!/usr/bin/env python3
"""The icon toolbar (owner 2026-11-01): web/e2-editor.html with Material Symbols icons and hover tooltips, Collabora's pattern
(icon-only tool buttons, the name in a tooltip on hover or keyboard focus, `data-cooltip`, browser/css/tooltip.css).

Each button keeps its text, unchanged, in a visually hidden span.  That is not tidiness: `run()` puts it in the status strip,
`check_m3_page_honesty.py` and `run_e2_c_product_path.py` read `textContent`, and it is the accessible name.  So the page's
logic, the bound tools and the AX tree see the same strings; only pixels change.  web/e2-editor-app.js is not touched.

Icons: @material-symbols/svg-400 0.48.2, outlined, Apache-2.0, the same visual family as Nextcloud's own icons.  Inline, as a
sprite in the page, so there is no new file for the package tables and no request for COEP to judge.

  build_toolbar_html.py PACKAGE.tgz IN.html OUT.html
"""
import hashlib
import html
import re
import sys
import tarfile

PACKAGE_SHA256 = "435f5393b5d3f7ee19ae683aaeb9a9a1b87636e459b0d38ca254e6e1e409f349"
# data-action or id -> (icon, tooltip).  A shortcut is named only where the page really handles it (e2-editor-app.js:3147-3186).
BUTTONS = {
    'id="open-file"': ("folder_open", "開啟檔案"),
    'data-action="undo"': ("undo", "復原 (Ctrl+Z)"),
    'data-action="redo"': ("redo", "重做 (Ctrl+Y)"),
    'data-action="move-character-left"': ("arrow_back", "游標左移"),
    'data-action="move-character-right"': ("arrow_forward", "游標右移"),
    'data-action="delete-backward"': ("backspace", "刪除"),
    'data-action="delete-forward"': ("backspace", "前刪"),
    'data-action="insert-paragraph-break"': ("keyboard_return", "分段 (Enter)"),
    'data-action="insert-line-break"': ("wrap_text", "換行 (Shift+Enter)"),
    'data-action="set-bold"': ("format_bold", "粗體 (Ctrl+B)"),
    'data-action="set-italic"': ("format_italic", "斜體 (Ctrl+I)"),
    'data-action="set-underline"': ("format_underlined", "底線 (Ctrl+U)"),
    'data-action="set-strikethrough"': ("format_strikethrough", "刪除線"),
    'id="clear-format"': ("format_clear", "清除格式"),
    'data-action="set-paragraph-heading"': ("title", "標題"),
    'data-action="set-paragraph-body"': ("format_paragraph", "內文"),
    'data-action="set-list-unordered"': ("format_list_bulleted", "項目符號"),
    'data-action="set-list-ordered"': ("format_list_numbered", "編號"),
    'data-action="set-list-none"': ("playlist_remove", "移除清單"),
    'data-action="insert-text"': ("input", "插入文字"),
    'data-action="paste-markdown"': ("markdown", "貼上為 Markdown…"),
    'data-action="save"': ("save", "儲存 ODT (Ctrl+S)"),
}
# The toolbar's two ends: a centred tooltip would leave the viewport there.
EDGE = {'id="open-file"': "tip-start", 'data-action="undo"': "tip-start", 'data-action="save"': "tip-end"}
CSS = """
  /* Icon toolbar, Collabora's pattern: icon-only tool buttons, the name in a tooltip on hover or keyboard focus.
     `.lbl` is the button's text, unchanged and out of sight: the page, the runners and the accessibility tree all read it. */
  .toolbar { position: relative; z-index: 6; }
  .toolbar button { position: relative; display: inline-flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; min-width: 32px; padding: 0; border-color: transparent; background: transparent; }
  /* `display` above would otherwise beat the user-agent rule for [hidden]: redo and Markdown stay off until declared. */
  .toolbar button[hidden] { display: none; }
  .toolbar button:hover:not(:disabled) { background: #e9eff5; border-color: transparent; }
  .toolbar button[aria-pressed="true"] { background: #dbe7f3; border-color: var(--accent); }
  .toolbar button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .toolbar button.primary:hover:not(:disabled) { background: var(--accent); filter: brightness(1.1); }
  .toolbar button:disabled { opacity: 1; }
  .toolbar button:disabled .ic { opacity: .4; }
  .toolbar .ic { width: 20px; height: 20px; fill: currentColor; pointer-events: none; }
  .toolbar .ic.flip { transform: scaleX(-1); }
  .toolbar .lbl { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; overflow: hidden;
    clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap; pointer-events: none; }
  .toolbar button[data-tip]::after { content: attr(data-tip); position: absolute; top: calc(100% + 6px); left: 50%;
    transform: translateX(-50%); padding: 5px 9px; border-radius: 6px; background: #fff; color: #1f2933;
    box-shadow: 0 0 4px rgba(0, 0, 0, .3); font-size: 12px; font-weight: 400; font-style: normal; text-decoration: none;
    white-space: nowrap; pointer-events: none; opacity: 0; visibility: hidden; }
  .toolbar button.tip-start[data-tip]::after { left: 0; transform: none; }
  .toolbar button.tip-end[data-tip]::after { left: auto; right: 0; transform: none; }
  .toolbar button[data-tip]:hover::after, .toolbar button[data-tip]:focus-visible::after {
    opacity: 1; visibility: visible; transition: opacity .1s .3s, visibility 0s .3s; }
"""
BUTTON = re.compile(r'<button ((?:[^>]*))>([^<]*)</button>')


def main() -> int:
    package, source, target = sys.argv[1:4]
    if hashlib.sha256(open(package, "rb").read()).hexdigest() != PACKAGE_SHA256:
        raise SystemExit("not the pinned icon package")
    with tarfile.open(package) as tar:
        def symbol(name):
            svg = tar.extractfile(f"package/outlined/{name}.svg").read().decode("utf-8")
            box = re.search(r'viewBox="([^"]+)"', svg).group(1)
            body = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
            return f'<symbol id="i-{name}" viewBox="{box}">{body}</symbol>'
        symbols = "".join(symbol(n) for n in sorted({icon for icon, _ in BUTTONS.values()}))
    page = open(source, encoding="utf-8").read()
    head, toolbar_and_rest = page.split('<div class="toolbar" id="toolbar">', 1)
    toolbar, rest = toolbar_and_rest.split("</div>\n\n  <div class=\"desk\" id=\"desk\">", 1)
    seen = set()

    def one(match):
        attrs, text = match.group(1), match.group(2)
        key = next((k for k in BUTTONS if k in attrs), None)
        if key is None:
            raise SystemExit(f"a toolbar button with no icon: {attrs}")
        seen.add(key)
        icon, tip = BUTTONS[key]
        attrs = re.sub(r'\s*title="[^"]*"', "", attrs)
        if key in EDGE:
            attrs = re.sub(r'class="([^"]*)"', rf'class="\1 {EDGE[key]}"', attrs) if "class=" in attrs else f'{attrs} class="{EDGE[key]}"'
        flip = " flip" if key == 'data-action="delete-forward"' else ""
        return (f'<button {attrs} data-tip="{html.escape(tip, quote=True)}"><svg class="ic{flip}" aria-hidden="true" focusable="false">'
                f'<use href="#i-{icon}"></use></svg><span class="lbl">{text}</span></button>')
    toolbar = BUTTON.sub(one, toolbar)
    missing = set(BUTTONS) - seen
    if missing:
        raise SystemExit(f"buttons not in the toolbar: {sorted(missing)}")
    if head.count("</style>") != 1:
        raise SystemExit("not exactly one style element")
    head = head.replace("</style>", CSS + "</style>")
    sprite = ('\n  <!-- Material Symbols (outlined, @material-symbols/svg-400 0.48.2), Copyright Google LLC, Apache License 2.0.'
              ' Inline so the page has no new request. -->\n'
              f'  <svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">{symbols}</svg>\n  ')
    out = head + sprite + '<div class="toolbar" id="toolbar">' + toolbar + "</div>\n\n  <div class=\"desk\" id=\"desk\">" + rest
    open(target, "w", encoding="utf-8").write(out)
    print(f"buttons {len(seen)}, symbols {len(set(i for i, _ in BUTTONS.values()))}, bytes {len(page.encode())} -> {len(out.encode())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
