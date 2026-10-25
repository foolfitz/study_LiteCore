#!/usr/bin/env python3
"""Read existing 0.2.35 Files/idle observations, server ODS and cleanup."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'wasm_sdk_probe/tools'))
from run_calc_cell_native import cells_from_xml
from read_calc_format_view import score

root=Path(__file__).resolve().parent
report=json.loads((root/'format-host-01/report.json').read_text())
assert report['ok'] and report['checks'] and all(c['ok'] is True for c in report['checks'])
assert {r['browser'] for r in report['runs']}=={'chrome','firefox'}
summary={'hostChecks':len(report['checks']),'idle':{},'hostViews':0,'hostTilesCompared':0}
for run in report['runs']:
    browser=run['browser'];idle=run['idleObservation'];before=idle['before'];after=idle['after']
    assert after['at']-before['at']>=35000 and before['saves']==after['saves']==[] and after['dirty']
    summary['idle'][browser]={'milliseconds':after['at']-before['at'],'automaticSaves':len(after['saves'])}
    for fmt in ('bold','italic','underline'):
        for mode in ('inline','cell'):
            s=json.loads((root/f'format-host-01/{browser}-{fmt}-{mode}.json').read_text())
            assert s['revision']==s['context']['revision'] and s['visibleTiles']>0 and s['tiles'] and all(t['matched'] for t in s['tiles'])
            summary['hostViews']+=1;summary['hostTilesCompared']+=len(s['tiles'])
    _,cells=cells_from_xml(root/f'format-host-01/{browser}-saved.ods')
    assert ''.join(cells[(0,0,0)].itertext())=='Idle observation '+browser
    manual=next(c['raw'] for c in report['checks'] if c['id']==browser+'/manual-save-positive')
    assert len(manual)==1 and manual[0]['trigger']=='manual' and manual[0]['outcome']=='saved'
cleanup=json.loads((root/'cleanup.json').read_text());identity=json.loads((root/'post-test-identity.json').read_text())
assert cleanup['projectStatesUnchanged'] and identity['engineEqualsArchive'] and identity['hostClean']
assert identity['installedVersion']=='0.2.35' and identity['lockFileIdsBefore']==identity['lockFileIdsAfter']==(root/'locks-before.txt').read_text().split()
states=lambda name:{p['name']:p['status'] for p in json.loads((root/name).read_text())['raw']}
assert states('ddev-before.json')==states('ddev-after.json') and states('ddev-after.json')['litecore']=='running'
assert identity['temporaryUserAbsent'] and identity['ownedFolderStatus']==404
summary['mirror']=score(root.parent/'165-calc-format-blank/green-01',3);assert not summary['mirror']['problems']
print(json.dumps(summary,indent=2))
