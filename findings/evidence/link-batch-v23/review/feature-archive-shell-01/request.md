Review this completed ABI6 owner-link archive and product shell cutover adversarially. Review supplied source only, no tools. Report concrete correctness or provenance faults with exact paths and consequences; otherwise say NO_CONCRETE_FINDING. Do not require a new population, threshold, runtime retry, or rewrite of frozen generations. Actual binary/loader contracts, 250 compiled inputs and 2337 old files were checked separately; no runtime acceptance is claimed. The page changes exactly workerUrl e2-editor-v22 to e2-editor-v23 and WASM pin f7a40bcce073d913 to fe1f99cddf27ff6a. Actual worker SHA is 3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5. New shell includes13 reachable modules and excludes6 explicitly reasoned files. Oldv75 remains unchanged. Identify a real falsifiable omission rather than a speculative best practice. Reply in English.

FILE findings/evidence/link-batch-v23/post-link/feature-01/archive_feature.py
```
#!/usr/bin/env python3
"""One-shot archive of the audited owner-linked ABI6 candidate; no build."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
SDK = ROOT / 'wasm_sdk_probe'
ARCHIVE = SDK / 'build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6'
EXPECTED = {
    'exports.txt': '78d4750fd2f98747ac2c677d9459873d4cf253ba14cfc86aa3f05e76b178a2a6',
    'probe.js': '4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e',
    'probe.wasm': 'fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658',
    'sdk-manifest.json': '2b23901ff94edd4c52611d03a31242c9ecfbf33fcf89835c1af13ac04a1e2a91',
    'sdk-worker.js': '3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    audit_path = OUT / 'audit-01/audit.json'
    audit = json.loads(audit_path.read_text())
    if audit['status'] != 'PASS' or audit['problems']:
        raise ValueError('post-link audit is not PASS')
    if ARCHIVE.exists():
        raise FileExistsError('preserve existing archive; never overwrite or retry')
    sources = {name: SDK / ('build/e2/editor-v23' if name == 'exports.txt'
                           else 'dist/profiles/e2-editor-v23') / name for name in EXPECTED}
    for name, path in sources.items():
        if sha(path) != EXPECTED[name]:
            raise ValueError('actual source identity differs: ' + name)
    ARCHIVE.mkdir()
    rows = []
    for name, source in sources.items():
        target = ARCHIVE / name
        shutil.copyfile(source, target)
        if sha(target) != EXPECTED[name] or sha(source) != EXPECTED[name]:
            raise ValueError('copy/source reread differs; preserve partial archive: ' + name)
        rows.append({'name': name, 'source': source.relative_to(ROOT).as_posix(),
                     'archive': target.relative_to(ROOT).as_posix(),
                     'bytes': target.stat().st_size, 'sha256': EXPECTED[name]})
    sums = ''.join(f'{digest}  {name}\n' for name, digest in EXPECTED.items())
    attribution = '''# ABI6 feature candidate attribution

This archive contains the exact owner-linked `e2-editor-v23` candidate: editor ABI6, 23 public actions, and select-all present with no granted gestures. It is a feature candidate, not a feature acceptance or host deployment verdict.

The WASM identity is `fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658`; the isolated worker identity is `3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5`. The worker derives from frozen v22 `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`, with the reviewed ABI6 six-move extension validation. No diagnostic tail or diagnostic entry point is included. Existing public IDs and the 36 inherited public function exports are preserved.

The five bound artifacts are probe.js, probe.wasm, sdk-worker.js, sdk-manifest.json and exports.txt. SHA256SUMS binds their actual bytes; the archive name identifies both WASM and worker. Never overwrite this identity. The shared Calc worker and all previous archives/profiles were unchanged by the owner build.

Evidence: `findings/evidence/link-batch-v23/post-link/feature-01/audit-01/audit.json`, the copied actual build log in that directory, and the one-shot archive receipt `feature-01/archive.json`. Runtime acceptance remains subject to final shell binding, readiness, required independent references and the fixed feature protocol.
'''
    for name, value in (('SHA256SUMS', sums), ('ATTRIBUTION.md', attribution)):
        (ARCHIVE / name).write_text(value)
        (OUT / name).write_text(value)
    result = {'status': 'PASS', 'archive': ARCHIVE.relative_to(ROOT).as_posix(),
              'audit': audit_path.relative_to(ROOT).as_posix(), 'auditSha256': sha(audit_path),
              'artifacts': rows,
              'metadata': [{'name': name, 'sha256': sha(ARCHIVE / name)}
                           for name in ('SHA256SUMS', 'ATTRIBUTION.md')],
              'runtimeAcceptance': 'NOT_ESTABLISHED', 'productBuildExecutedByAgent': False}
    (OUT / 'archive.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

```

FILE findings/evidence/link-batch-v23/post-link/feature-01/archive.json
```
{
  "status": "PASS",
  "archive": "wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6",
  "audit": "findings/evidence/link-batch-v23/post-link/feature-01/audit-01/audit.json",
  "auditSha256": "ccdb00ab5ddca30a42d1d01e043b74a65093c168eee82b048283c5f6fe82812f",
  "artifacts": [
    {
      "name": "exports.txt",
      "source": "wasm_sdk_probe/build/e2/editor-v23/exports.txt",
      "archive": "wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/exports.txt",
      "bytes": 871,
      "sha256": "78d4750fd2f98747ac2c677d9459873d4cf253ba14cfc86aa3f05e76b178a2a6"
    },
    {
      "name": "probe.js",
      "source": "wasm_sdk_probe/dist/profiles/e2-editor-v23/probe.js",
      "archive": "wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/probe.js",
      "bytes": 144322,
      "sha256": "4d90d587cd24a2d75056e7e3400acce009f5841ae2e5df033adba3031a74578e"
    },
    {
      "name": "probe.wasm",
      "source": "wasm_sdk_probe/dist/profiles/e2-editor-v23/probe.wasm",
      "archive": "wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/probe.wasm",
      "bytes": 115331584,
      "sha256": "fe1f99cddf27ff6aca9f39f6286770f68981291e5a3505dc58dd88ef6ed05658"
    },
    {
      "name": "sdk-manifest.json",
      "source": "wasm_sdk_probe/dist/profiles/e2-editor-v23/sdk-manifest.json",
      "archive": "wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/sdk-manifest.json",
      "bytes": 8828,
      "sha256": "2b23901ff94edd4c52611d03a31242c9ecfbf33fcf89835c1af13ac04a1e2a91"
    },
    {
      "name": "sdk-worker.js",
      "source": "wasm_sdk_probe/dist/profiles/e2-editor-v23/sdk-worker.js",
      "archive": "wasm_sdk_probe/build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/sdk-worker.js",
      "bytes": 76901,
      "sha256": "3fd3e1e66fec54c571ab803555d51512ebf27eec61e85767c824dc5d79d76cd5"
    }
  ],
  "metadata": [
    {
      "name": "SHA256SUMS",
      "sha256": "93db9049ac11198fa432248c8dcf5792a2d635972ebdcaa911260a4b3594ad63"
    },
    {
      "name": "ATTRIBUTION.md",
      "sha256": "9872d99433775a2148c7226632fc46f4541def3505301398e5315547ac2adb73"
    }
  ],
  "runtimeAcceptance": "NOT_ESTABLISHED",
  "productBuildExecutedByAgent": false
}

```

FILE wasm_sdk_probe/e2/editor-shell-v2-bundle-v76.json
```
{
  "schemaVersion": 1,
  "release": "E2-C-editor-shell-v2-bundle",
  "frozenDate": "2026-10-26",
  "entrypoint": "web/e2-editor-app.js",
  "scope": "JavaScript modules reached by the E2-C product page's import graph, plus every *.js in editor-shell-v2, editor-shell, input, sdk, reader-shell",
  "algorithm": "SHA-256 of UTF-8 path + NUL + lowercase file SHA-256 + LF for each included path in lexicographic order",
  "included": [
    {
      "path": "editor-shell-v2/narrow-editor-v2-client.js",
      "sha256": "34378dec62df9b02af8d85616b038fc176d6c94fad268773bf77eb2d495b9a55"
    },
    {
      "path": "editor-shell-v2/narrow-editor-v2-session.js",
      "sha256": "a4cf3105835fa57621e1d8afd9a4b9eb5dd44ccf35aa46a9cd5b475ac6746f0d"
    },
    {
      "path": "editor-shell-v2/paragraph-editor-client.js",
      "sha256": "4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6"
    },
    {
      "path": "editor-shell-v2/paragraph-editor-session.js",
      "sha256": "d853d420d794af4d79edd0956e504a5e61eef3c98bd95f112a03f53d248279c9"
    },
    {
      "path": "editor-shell/editor-client.js",
      "sha256": "b779f157c3e3588ab46bffdae657430c6fba7ae1ce402d652ba2f9c49d88698a"
    },
    {
      "path": "editor-shell/editor-session.js",
      "sha256": "95bc60cc655074e958ab2d5f174ebf682c54a551f0ee04cf25a989d5c34ca14a"
    },
    {
      "path": "editor-shell/recovery-notice.js",
      "sha256": "a6f916bc78268c42f717bb996223cd1b0ad248d1023890abf6ee3e0c24d66e43"
    },
    {
      "path": "editor-shell/state-machine.js",
      "sha256": "7b1d9e2d6619d408004cd2eb49f3cdf845f7d8f16c2e3e9c24b6e2243b9a8cf3"
    },
    {
      "path": "input/clipboard-adapter.js",
      "sha256": "ec84cec0494697d7ce4045769bc47e7f665f2e0386d99ce2fd8ae468d9318bd8"
    },
    {
      "path": "input/input-adapter.js",
      "sha256": "f815e156a901ac6b05614cae16e69e2157fefaaeced3ebe1225668f496334d16"
    },
    {
      "path": "reader-shell/tile-scheduler.js",
      "sha256": "4c60ab4e5ed11e32155af50a7b6983500cdab47431c8fc494aaf2369f046e722"
    },
    {
      "path": "sdk/document-sdk.js",
      "sha256": "9dcb83120c144cad5cf04cabcc14452255d0a640200b8e08f5eed4d4c2d63539"
    },
    {
      "path": "web/e2-editor-app.js",
      "sha256": "c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490"
    }
  ],
  "excluded": [
    {
      "path": "sdk/sdk-worker.js",
      "reason": "Bound separately and more precisely as workerSha256: the copy that actually runs is the one inside the profile."
    },
    {
      "path": "reader-shell/reader-session.js",
      "reason": "The R6 reader shell. Not in the editor page import graph; only reader-shell/tile-scheduler.js is."
    },
    {
      "path": "reader-shell/state-machine.js",
      "reason": "The reader shell own state machine, not the editor. Not in the editor page import graph."
    },
    {
      "path": "sdk/v23-diagnostic-worker-tail.js",
      "reason": "Private ABI5 diagnostic tail concatenated only into e2-editor-v23-diag; its resulting profile worker is separately bound by workerSha256. Not imported by the product page."
    },
    {
      "path": "sdk/v23-diagnostic-r2-worker-tail.js",
      "reason": "Private ABI5 diagnostic tail concatenated only into e2-editor-v23-diag-r2; its resulting profile worker is separately bound by workerSha256. Not imported by the product page."
    },
    {
      "path": "sdk/v23-feature-worker.js",
      "reason": "Source of the ABI6 e2-editor-v23 profile worker, separately bound by workerSha256. The product creates that profile worker by URL; this source is not a page import."
    }
  ],
  "bundleSha256": "f97bedeef73c7834cd5c86234d72e1ce459131153c36b8737583211a358e772c"
}

```

FILE findings/evidence/link-batch-v23/post-link/feature-01/shell-01/final-identity.json
```
{
  "status": "SOURCE_AND_DIST_BOUND_NO_BROWSER_ACCEPTANCE",
  "bundleSha256": "f97bedeef73c7834cd5c86234d72e1ce459131153c36b8737583211a358e772c",
  "includedCount": 13,
  "excludedCount": 6,
  "problems": [],
  "files": {
    "web/e2-editor-app.js": "c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490",
    "dist/e2-editor-app.js": "c25b11c463a24fc183a046a5c26ebe6ad71d04d22dcc7830ba77997d231e4490",
    "editor-shell-v2/narrow-editor-v2-client.js": "34378dec62df9b02af8d85616b038fc176d6c94fad268773bf77eb2d495b9a55",
    "dist/editor-shell-v2/narrow-editor-v2-client.js": "34378dec62df9b02af8d85616b038fc176d6c94fad268773bf77eb2d495b9a55",
    "editor-shell-v2/narrow-editor-v2-session.js": "a4cf3105835fa57621e1d8afd9a4b9eb5dd44ccf35aa46a9cd5b475ac6746f0d",
    "dist/editor-shell-v2/narrow-editor-v2-session.js": "a4cf3105835fa57621e1d8afd9a4b9eb5dd44ccf35aa46a9cd5b475ac6746f0d",
    "tools/build_e2_c_shell_bundle.py": "407afdffe13dea08a9b4e6975f0e3b2230747ef8d03c9e3e4790fd44498170ad",
    "e2/editor-shell-v2-bundle-v75.json": "b67bd6558b1e25f6b77d84abeb721635548a113b0d53a52dfe41f5e34f250a90",
    "e2/editor-shell-v2-bundle-v76.json": "555590f6eb6e7600ed313b7d866a6a0ba30f190efc6e9c97bb86483b05627093"
  }
}

```

FILE wasm_sdk_probe/tools/build_e2_c_shell_bundle.py (lines780 onward)
```
# The host arms on 0.2.27 (H-154c, H-154o, D2-v22, M11-autosave) are the checks still ahead; K is deferred (§13).
# v76: actual ABI6 feature page cutover and client/session source, after the
# feature archive audit. Diagnostic tails and feature worker stay profile-bound.
MANIFEST = Path("e2/editor-shell-v2-bundle-v76.json")
ENTRYPOINT = Path("web/e2-editor-app.js")

# The directories whose *.js files must all be accounted for.  `editor-shell`
# is in the list even though E2 does not own it: the v2 session extends the v1
# session, so v1's bytes are part of what E2-C measures, and a change there must
# break E2's binding as well as E1's.  `reader-shell` is in it because the
# session's tile scheduler lives there -- a directory that contributes a module
# to the graph has to be scanned, or a file dropped in beside that module is
# invisible to this check.
SCOPE = ("editor-shell-v2", "editor-shell", "input", "sdk",
         "reader-shell")

IMPORT_PATTERN = re.compile(
    r"""(?:import|export)[^"']*?from\s*["']([^"']+)["']|import\s*\(\s*["']([^"']+)["']\s*\)""")


def imports_of(text: str) -> list[str]:
    return [a or b for a, b in IMPORT_PATTERN.findall(text)]


def reachable(project: Path, entry_relative: Path) -> list[str]:
    """Local modules reachable from the entry point, project-relative."""
    entry = project / entry_relative
    pending = [entry]
    visited: set[Path] = set()
    found: set[str] = set()
    while pending:
        path = pending.pop()
        resolved = path.resolve()
        if resolved in visited or not path.is_file():
            continue
        visited.add(resolved)
        text = path.read_text(encoding="utf-8")
        # The entry point lives under web/ but is served from the dist ROOT, so
        # its relative specifiers resolve from the project root.  Everything it
        # pulls in keeps its own directory.
        base = project if path == entry else path.parent
        for specifier in imports_of(text):
            if not specifier.startswith("."):
                continue
            dependency = (base / specifier).resolve()
            try:
                relative = dependency.relative_to(project.resolve())
            except ValueError:
                continue
            pending.append(dependency)
            if relative.suffix == ".js":
                found.add(relative.as_posix())
    return sorted(found)


def available(project: Path) -> list[str]:
    return sorted(path.relative_to(project).as_posix()
                  for directory in SCOPE
                  for path in (project / directory).glob("*.js"))


def compute(project: Path) -> dict[str, Any]:
    entry = ENTRYPOINT.as_posix()
    included = sorted({entry, *reachable(project, ENTRYPOINT)})
    hashes = {path: sha256(project / path) for path in included}
    # The dist copy of every included module, and of every available one: a
    # stale copy of a module this bundle excludes is still a stale server.
    dist_root = project / "dist"
    dist_name = {path: ("e2-editor-app.js" if path == entry else path)
                 for path in set(included) | set(available(project))}
    dist_hashes = {
        path: (sha256(dist_root / name) if (dist_root / name).is_file() else None)
        for path, name in dist_name.items()
    }
    return {
        "included": included,
        "hashes": hashes,
        "available": available(project),
        "distHashes": dist_hashes,
        "digest": shell_bundle_digest(hashes),
    }


def manifest_body(state: dict[str, Any], excluded: list[dict[str, str]],
                  frozen_date: str) -> dict:
    return {
        "schemaVersion": 1,
        "release": "E2-C-editor-shell-v2-bundle",
        # A generation's own date, not the first generation's.  It was hard
        # coded, so v4 came out claiming it was frozen on the day v1 was --
        # a manifest whose own record of when it was written is wrong is a poor
        # thing to bind a verdict to.
        "frozenDate": frozen_date,
        "entrypoint": ENTRYPOINT.as_posix(),
        "scope": "JavaScript modules reached by the E2-C product page's import "
                 "graph, plus every *.js in " + ", ".join(SCOPE),
        "algorithm": "SHA-256 of UTF-8 path + NUL + lowercase file SHA-256 + LF "
                     "for each included path in lexicographic order",
        "included": [{"path": path, "sha256": state["hashes"][path]}
                     for path in state["included"]],
        "excluded": excluded,
        "bundleSha256": state["digest"],
    }


def problems(project: Path, state: dict[str, Any],
             manifest: dict[str, Any] | None) -> list[str]:
    out: list[str] = []
    covered = set(state["included"]) | {
        str(item.get("path")) for item in (manifest or {}).get("excluded", [])}
    uncovered = sorted(set(state["available"]) - covered)
    if uncovered:
        out.append(f"in scope but neither included nor excluded: {uncovered}")
    # A path in BOTH lists is a manifest that contradicts itself, and the
    # exclusion's stated reason is by then describing a file that is imported
    # after all.  It happened on 2026-08-19: the page started importing
    # recovery-notice.js, the builder correctly moved it into `included`, and
    # the inherited exclusion -- "the product page never imports it" -- came
    # along for the ride.  The digest was right; the document was lying.
    both = sorted(set(state["included"]) & {
        str(item.get("path")) for item in (manifest or {}).get("excluded", [])})
    if both:
        out.append(f"included AND excluded, so one of the two is wrong: {both}")
    for path in state["included"]:
        if state["distHashes"].get(path) != state["hashes"][path]:
            out.append(f"dist copy differs from source: {path} "
                       f"(run `make e2-c-assets`)")
    for path in state["available"]:
        if path in state["included"]:
            continue
        source = project / path
        # A path with no source file has nothing to be stale against.  Reading
        # it unconditionally made this function crash instead of reporting,
        # which the unit test found before the tree ever produced the case.
        if not source.is_file():
            continue
        if state["distHashes"].get(path) not in (None, sha256(source)):
            out.append(f"dist copy of an excluded module is stale: {path}")
    if manifest is not None:
        recorded = {item["path"]: item["sha256"]
                    for item in manifest.get("included", [])}
        if recorded != state["hashes"]:
            added = sorted(set(state["hashes"]) - set(recorded))
            removed = sorted(set(recorded) - set(state["hashes"]))
            changed = sorted(p for p in set(recorded) & set(state["hashes"])
                             if recorded[p] != state["hashes"][p])
            out.append(f"manifest is out of date: added={added} "
                       f"removed={removed} changed={changed}")
        elif manifest.get("bundleSha256") != state["digest"]:
            out.append("manifest records a digest that does not match its own "
                       "file list")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST,
                        help="which bundle manifest to check or write; the "
                             "default is round two's, and round one's is frozen")
    parser.add_argument("--write", action="store_true",
                        help="write the manifest; the diff is printed either way")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="PATH=REASON",
                        help="exclude a module from the bundle, with a reason; "
                             "'this file is not covered' is a claim somebody has "
                             "to make, so it does not get a default")
    parser.add_argument("--force", action="store_true",
                        help="rewrite an existing manifest whose digest would "
                             "change -- discards the record of what a round ran "
                             "on, so it is never the routine answer")
    parser.add_argument("--frozen-date", default=None,
                        help="the date THIS generation was frozen; defaults to "
                             "the existing manifest's, and a new generation "
                             "should be given one explicitly")
    args = parser.parse_args()

    state = compute(PROJECT)
    manifest_path = PROJECT / args.manifest
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.is_file() else None)

    excluded = [{"path": item.split("=", 1)[0], "reason": item.split("=", 1)[1]}
                for item in args.exclude if "=" in item]
    if manifest and not excluded:
        excluded = manifest.get("excluded", [])
    if not manifest and not excluded:
        # Starting a NEW generation used to silently produce an empty exclusion
        # list, and an empty one breaks the rule this bundle is built on:
        # `available - included - excluded` must be empty, so that dropping a
        # file beside the covered ones is a change.  A v4 that inherits nothing
        # binds LESS than the v3 it replaces, while looking like progress.
        # Measured on 2026-08-16 while freezing v4 for finding 049.
        for candidate in reversed(FROZEN_MANIFESTS):
            path = PROJECT / candidate
            if not path.is_file():
                continue
            inherited = json.loads(path.read_text(encoding="utf-8")).get("excluded")
            if inherited:
                excluded = inherited
                report_inherited = str(candidate)
                break
        else:
            report_inherited = None
    else:
        report_inherited = None

    found = problems(PROJECT, state, manifest if not args.write else None)
    report = {
        "manifest": str(args.manifest),
        "included": state["included"],
        "excluded": [item["path"] for item in excluded],
        "bundleSha256": state["digest"],
        "problems": found,
        # Said out loud: a new generation that inherited its exclusions did not
        # decide them, and the reader should know which manifest did.
        "exclusionsInheritedFrom": report_inherited,
    }
    # Refuse to change a generation that already exists.
    #
    # 2026-08-17: bumping MANIFEST to v15 was done with a string replace that did
    # not match, so MANIFEST was still v14 and `--write` regenerated it in place
    # with a DIFFERENT digest -- the generation `e2/validation-matrix-v2.json`
    # and finding 046's evidence both name.  It was restored from git and no
    # measurement had been taken against the rewritten copy, so the damage was
    # nil, but only by luck: nothing complained.
    #
    # A generation is the record of what some round ran on (the comment at the
    # top of this file has said so since v1).  Adding it to FROZEN_MANIFESTS is
    # a manual step, so "not yet listed there" cannot be what protects it.  What
    # protects it is this: an existing manifest may be rewritten only when the
    # bytes it describes are unchanged.
    rewrites_existing = (manifest is not None
                         and manifest.get("bundleSha256") != state["digest"])
    if rewrites_existing and not args.force:
        # `.append`, not `found = found + [...]`: `report["problems"]` already
        # holds a reference to this list, and rebinding would leave the refusal
        # out of the report -- a guard that stops the write and says nothing,
        # which is the failure mode it was written for.
        found.append(
            f"refusing to rewrite {args.manifest} -- it exists with digest "
            f"{manifest.get('bundleSha256', '')[:16]}... and the tree now hashes "
            f"{state['digest'][:16]}.... A changed shell needs a NEW generation: "
            f"bump MANIFEST and add this one to FROZEN_MANIFESTS. --force only if "
            f"you mean to discard the record of what a round actually ran on.")
    if args.write and not rewrites_existing and not [p for p in found if "dist copy" in p]:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        body = manifest_body(state, excluded, args.frozen_date
                             or (manifest or {}).get("frozenDate")
                             or "unrecorded")
        manifest_path.write_text(
            json.dumps(body, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        report["written"] = True
        # Re-checked against what was just written.  `found` above was computed
        # with no manifest (a new generation has none yet), so it reports every
        # exclusion as unaccounted for -- a report that reads like four problems
        # when the file on disk has none.  A tool that prints stale problems
        # trains its reader to ignore the field.
        found = problems(PROJECT, state,
                         json.loads(manifest_path.read_text(encoding="utf-8")))
        report["problems"] = found
        report["problemsRecheckedAfterWrite"] = True
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not found else 1


if __name__ == "__main__":
    sys.exit(main())
```

ACTUAL CUTOVER DIFF
```diff
commit 0e748b8255de984c708ce79ba47421bf24c8f7ba
Author: foolfitz <foolfitz@gmail.com>
Date:   Mon Oct 26 11:41:40 2026 +0800

    Bind the ABI6 feature page to shell generation 76
    
    Cut the worker URL and WASM pin over together, synchronize the served modules, and preserve generation 75. Record explicit profile worker exclusions and the unchanged binding controls.
    
    Co-Authored-By: Codex <noreply@openai.com>

diff --git a/wasm_sdk_probe/tools/build_e2_c_shell_bundle.py b/wasm_sdk_probe/tools/build_e2_c_shell_bundle.py
index 98ddbe24..d40dd075 100644
--- a/wasm_sdk_probe/tools/build_e2_c_shell_bundle.py
+++ b/wasm_sdk_probe/tools/build_e2_c_shell_bundle.py
@@ -142,7 +142,8 @@ FROZEN_MANIFESTS = (Path("e2/editor-shell-v2-bundle-v1.json"),
                     Path("e2/editor-shell-v2-bundle-v37.json"),
                     Path("e2/editor-shell-v2-bundle-v38.json"),
                     Path("e2/editor-shell-v2-bundle-v39.json"),
-                    Path("e2/editor-shell-v2-bundle-v40.json"))
+                    Path("e2/editor-shell-v2-bundle-v40.json"),
+                    Path("e2/editor-shell-v2-bundle-v75.json"))
 FROZEN_MANIFEST = FROZEN_MANIFESTS[0]
 # v41, 2026-08-24: the page runs `e2-editor-v8` -- finding 076's link.
 #
@@ -777,7 +778,9 @@ FROZEN_MANIFEST = FROZEN_MANIFESTS[0]
 # page 3b96cb16…; findings/evidence/link-batch-v22/shakedown/): F3 PASS, E2 PASS (item 2, both browsers, composed
 # per §11.2.1, fable ruling 6), I1-rerun PASS with E0-v22 (§11.4.1, §11.4.2, ruling 6 addendum 1), I2-v22 PASS.
 # The host arms on 0.2.27 (H-154c, H-154o, D2-v22, M11-autosave) are the checks still ahead; K is deferred (§13).
-MANIFEST = Path("e2/editor-shell-v2-bundle-v75.json")
+# v76: actual ABI6 feature page cutover and client/session source, after the
+# feature archive audit. Diagnostic tails and feature worker stay profile-bound.
+MANIFEST = Path("e2/editor-shell-v2-bundle-v76.json")
 ENTRYPOINT = Path("web/e2-editor-app.js")
 
 # The directories whose *.js files must all be accounted for.  `editor-shell`
diff --git a/wasm_sdk_probe/web/e2-editor-app.js b/wasm_sdk_probe/web/e2-editor-app.js
index c915f911..f7626810 100644
--- a/wasm_sdk_probe/web/e2-editor-app.js
+++ b/wasm_sdk_probe/web/e2-editor-app.js
@@ -47,7 +47,7 @@ import { EDITOR_V2_ACTIONS } from "./editor-shell-v2/narrow-editor-v2-client.js"
 // move together or the page pins one artifact and loads another -- and the
 // expiry screen exists to make exactly that mismatch loud, so a half-move
 // would look like a broken build rather than a mistake.
-const PINNED_WASM_SHA256 = "f7a40bcce073d913";
+const PINNED_WASM_SHA256 = "fe1f99cddf27ff6a";
 
 // M3's host entry (specs/SPEC-M3-host-entry.md).  A host that embeds this page
 // -- the Nextcloud app -- puts `globalThis.liteCoreHost = { load, save }` in
@@ -3746,7 +3746,7 @@ el.desk.addEventListener("scroll", onDeskScroll, { passive: true });
 // The harness pages (`e2-c-d*-app.js`) do take `?profile=`; they are harnesses.
 function engineFactory() {
   return createDocumentEngine({
-    workerUrl: "./profiles/e2-editor-v22/sdk-worker.js",
+    workerUrl: "./profiles/e2-editor-v23/sdk-worker.js",
     timeoutMs: 30000,
   });
 }

```
