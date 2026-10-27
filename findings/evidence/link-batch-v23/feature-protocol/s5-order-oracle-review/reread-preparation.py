#!/usr/bin/env python3
"""Re-read every preserved preparation cell with its own recorded plan, without adoption."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'wasm_sdk_probe/tools'))
import judge_v23_feature_selection as judge


def sha(raw):return hashlib.sha256(raw).hexdigest()


def read(directory):
    directory=directory.resolve()
    raw=(directory/'report.json').read_bytes();report=json.loads(raw);plan=report['config']
    assert report['preparationOnly'] is True and report['runs'],'not a nonempty preparation'
    assert report['postConfig']==plan,'preparation did not finish with stable inputs'
    rows=[]
    for receipt in report['runs']:
        path=directory/receipt['path']
        data=path.read_bytes() if path.is_file() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
        assert sha(data)==receipt['sha256'],'cell receipt differs: '+receipt['path']
        cell=json.loads(data);value=judge.inspect(cell['page'],plan,cell['browser'])
        assert value==cell['inspection'],'inspection differs: '+receipt['path']
        rows.append({'browser':cell['browser'],'caseId':cell['caseId'],'verdict':value['verdict'],
                     'receiptSha256':receipt['sha256'],'inspectionUnchanged':True})
    assert len({(r['browser'],r['caseId']) for r in rows})==len(rows),'duplicate cells'
    return {'schema':1,'scope':'Historical preparation re-read only; no qualifying count',
            'report':str((directory/'report.json').relative_to(ROOT)),'reportSha256':sha(raw),
            'readerSha256':sha(Path(judge.__file__).read_bytes()),'rows':rows,
            'verdict':'PRESERVED_INSPECTIONS_UNCHANGED'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=read(args.directory)
    with args.output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({'verdict':result['verdict'],'cells':len(result['rows'])}))
