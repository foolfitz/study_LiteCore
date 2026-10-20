import json, sys, pathlib, collections
out = pathlib.Path(sys.argv[1])
for arm in sorted(p.name for p in out.iterdir() if p.is_dir()):
    for f in sorted((out/arm).glob('*.jsonl')):
        recs=[json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        m=[r for r in recs if r['rec']=='measured']
        if not m: print(arm, f.name, 'NO MEASURED'); continue
        m=m[0]
        for o in m['ops']:
            late=o.get('lateCallbacks',[])
            types=collections.Counter(c['type'].replace('LOK_CALLBACK_','') for c in late)
            # callbacks between return and first poll: from the measured callbacks list, by index
            print(f"{arm:8} {f.stem:10} op={o['op']:14} ret={o['returnedMs']:.2f} fp={o.get('firstPollAfterReturnMs')} idx={o.get('cbIndexAtFirstPoll')} late={dict(types)}")
        print(f"{'':8} {f.stem:10} capped={m['capped']} settle={m['settleMs']:.0f} nCb={m['nCallbacks']} types={dict(collections.Counter(c['type'].replace('LOK_CALLBACK_','') for c in m['callbacks']))}")
