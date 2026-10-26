#!/usr/bin/env python3
"""Losslessly store or restore large raw cell records, without judging them."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parent


def identity(path, compressed=False):
    digest = hashlib.sha256()
    length = 0
    opener = gzip.open if compressed else open
    with opener(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
            length += len(block)
    return {'sha256': digest.hexdigest(), 'bytes': length}


def local(name):
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('storage path must remain under the evidence directory')
    return BASE / path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['pack', 'verify', 'restore'])
    parser.add_argument('--index', required=True)
    parser.add_argument('cohorts', nargs='*')
    args = parser.parse_args()
    index_path = local(args.index)
    if args.mode == 'pack':
        if index_path.exists() or not args.cohorts:
            parser.error('pack needs a new index and explicit nonempty cohorts')
        index = {'schema': 1, 'scope': 'byte storage only; no product verdict', 'reports': [], 'payloads': []}
        for name in args.cohorts:
            directory = local(name)
            report_path = directory / 'report.json'
            report = json.loads(report_path.read_text())
            index['reports'].append({'path': str(report_path.relative_to(BASE)), **identity(report_path)})
            for row in report['runs']:
                raw = directory / row['path']
                relative = raw.relative_to(BASE)
                local(relative)  # Reject traversal before any write.
                before = identity(raw)
                if before['sha256'] != row['sha256']:
                    raise ValueError('raw record differs from runner report: ' + str(relative))
                stored = raw.with_suffix(raw.suffix + '.gz')
                with raw.open('rb') as source, stored.open('xb') as destination:
                    with gzip.GzipFile(filename='', fileobj=destination, mode='wb', mtime=0) as compressed:
                        shutil.copyfileobj(source, compressed)
                if identity(stored, compressed=True) != before or identity(raw) != before:
                    raise ValueError('compression or source reread differs: ' + str(relative))
                index['payloads'].append({'path': str(relative), **before,
                    'gzipPath': str(stored.relative_to(BASE)), 'gzipIdentity': identity(stored)})
        if not index['payloads']:
            raise ValueError('no raw cells in requested cohorts; no storage completion claim')
        with index_path.open('x') as stream:
            json.dump(index, stream, indent=2)
            stream.write('\n')
    else:
        if args.cohorts:
            parser.error('verify and restore use only the recorded index')
        index = json.loads(index_path.read_text())
        if not index['reports'] or not index['payloads']:
            raise ValueError('empty storage inventory')
        for row in index['reports']:
            if identity(local(row['path'])) != {k: row[k] for k in ('sha256', 'bytes')}:
                raise ValueError('report bytes changed: ' + row['path'])
        for row in index['payloads']:
            stored, raw = local(row['gzipPath']), local(row['path'])
            expected = {k: row[k] for k in ('sha256', 'bytes')}
            if identity(stored) != row['gzipIdentity'] or identity(stored, compressed=True) != expected:
                raise ValueError('stored payload bytes changed: ' + row['path'])
            if args.mode == 'restore' and not raw.exists():
                with gzip.open(stored, 'rb') as source, raw.open('xb') as destination:
                    shutil.copyfileobj(source, destination)
            if raw.exists() and identity(raw) != expected:
                raise ValueError('existing raw payload differs; never overwrite: ' + row['path'])
    print(json.dumps({'scope': index['scope'], 'reports': len(index['reports']),
        'payloads': len(index['payloads']), 'mode': args.mode}))


if __name__ == '__main__':
    main()
