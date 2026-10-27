#!/usr/bin/env python3
"""Replay R1 ruling 1 C1's exact stale-state scenarios on model pages, including the old reader.

No browser is involved. The archived reader must accept the clean model before it is used as
the negative control. Both public-call results and raw replies are edited consistently.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(ROOT/'wasm_sdk_probe/tools'),str(ROOT/'wasm_sdk_probe/tests')]
import judge_v23_feature_selection as current
import test_v23_feature_r1 as model


def main():
    revision='2b561678'
    old_source=subprocess.check_output(['git','show',revision+':wasm_sdk_probe/tools/judge_v23_feature_selection.py'],cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='r1-stale-control-') as tmp:
        path=Path(tmp)/'archived_reader.py';path.write_bytes(old_source)
        spec=importlib.util.spec_from_file_location('archived_reader',path)
        previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
        plan=model.live_plan();baseline=model.r1_page('main/p2-forward/Left')
        assert previous.inspect(baseline,plan,'chrome')['verdict']=='PASS','archived reader rejects the clean model'
        records=[]
        for kind in ('candidate-pre-move-caret','candidate-range-selection','control-pre-move-caret','candidate-state-absent'):
            page=model.r1_page('main/s1/Down' if kind=='control-pre-move-caret' else 'main/p2-forward/Left')
            arm='r1control' if kind=='control-pre-move-caret' else 'r1cand'
            if kind.endswith('pre-move-caret'):
                before=copy.deepcopy(page[arm]['controlState' if arm=='r1control' else 'before']['caret'])
                assert before!=page[arm]['reply']['state']['caret'],'control did not change the reply caret'
                def edit(reply):reply['state']['caret']=copy.deepcopy(before)
            elif kind=='candidate-range-selection':
                before=copy.deepcopy(page[arm]['before']['selection'])
                assert before['collapsed'] is False
                def edit(reply):reply['state']['selection']=copy.deepcopy(before)
            else:
                def edit(reply):reply.pop('state')
            model.edit_call(page,arm+'-move',edit);edit(page[arm]['reply'])
            now=current.inspect(page,plan,'chrome');old=previous.inspect(page,plan,'chrome')
            expected='NOT_ESTABLISHED' if kind in ('control-pre-move-caret','candidate-state-absent') else 'FAIL'
            assert now['verdict']==expected,(kind,now)
            assert old['verdict']=='PASS',(kind,old)
            records.append({'id':kind,'current':now,'previous':old})
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    print(json.dumps({'schema':1,'verdict':'FOUR_PREVIOUS_FALSE_PASSES_REJECTED',
        'scope':'Model controls only; not new browser observations',
        'readerSha256':sha(Path(current.__file__).read_bytes()),'modelSha256':sha(Path(model.__file__).read_bytes()),
        'controlScriptSha256':sha(Path(__file__).read_bytes()),'previousRevision':revision,
        'previousReaderSha256':sha(old_source),'controls':records},indent=2))


if __name__=='__main__':main()
