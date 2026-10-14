"""Count each product-path mutation's `find` anchor in a page: every anchor must occur exactly once."""
import ast, sys, json
page = open(sys.argv[1], encoding="utf-8").read()
out = {}
for path in sys.argv[2:]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MUTATIONS" for t in node.targets)):
            continue
        if isinstance(node.value, ast.Dict):
            pairs = [(k.value if isinstance(k, ast.Constant) else "?", v) for k, v in zip(node.value.keys, node.value.values)]
        elif isinstance(node.value, ast.List):
            pairs = [(f"#{i}", v) for i, v in enumerate(node.value.elts)]
        else:
            continue
        for key, entry in pairs:
            if not isinstance(entry, ast.Dict):
                continue
            fields = {}
            for k, v in zip(entry.keys, entry.values):
                if isinstance(k, ast.Constant) and k.value in ("path", "find") and isinstance(v, ast.Constant):
                    fields[k.value] = v.value
            if fields.get("path") == "e2-editor-app.js" and "find" in fields:
                out[f"{path.split('/')[-1]}::{key}"] = page.count(fields["find"])
bad = {k: v for k, v in out.items() if v != 1}
print(json.dumps({"page": sys.argv[1], "anchors": len(out), "notExactlyOnce": bad}))
