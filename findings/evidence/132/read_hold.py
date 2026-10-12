import json, sys
r = json.load(open(sys.argv[1]))
print(r['deskRepeat'], {k: r['static'][k] for k in ('servedPage', 'buildId', 'hostVersion')})
for run in r['runs']:
    print('==', run['browser'], run.get('version'), 'fatal' if run.get('fatal') else '')
    for arm in ('holdHigh', 'holdLow'):
        h = run.get(arm)
        if not h: continue
        g = h['geometry']
        print(' ', arm, 'caretRow', g['caretRow'], 'view', g['view'], 'winTop', g['winTop'])
        for i, rnd in enumerate(h['rounds']):
            s = rnd['hold']
            w = s['washes']
            print(f"   r{i} keys {s['keydowns']} rep {s['repeatsFlagged']} bi {s['beforeinputs']} del {s['deleted']} other {s['otherLatency']} "
                  f"doneAtRel {s['deletesDoneAtRelease']} shownAtRel {s['deletesShownAtRelease']} afterRel {s['deletesAfterRelease']} "
                  f"lastAfterRel {s['lastDeleteAfterReleaseMs']} lag {s['lagFirstMs']}->{s['lagMaxMs']} "
                  f"bandRepBeforeRel {s['caretBandRepaintsBeforeRelease']} total {s['caretBandRepaintsTotal']} fresh {s['caretBandFreshAfterReleaseMs']} "
                  f"washes {len(w)} wf {sum(x['framesWithWash'] or 0 for x in w)} persist {rnd['persistent'].get('differing')} left {rnd['leftAfterHold']}")
            d = s['doneMs']
            if len(d) > 3:
                gaps = [round(b - a, 1) for a, b in zip(d[1:], d[2:])]
                gaps.sort()
                print('      per-delete gap median', gaps[len(gaps)//2], 'min', gaps[0], 'max', gaps[-1])
            reps = [x['t'] for x in s['repaints']]
            sent0 = s  # nothing
            for sg in rnd['singles']:
                ww = sg['washes']
                print('      single lag', sg['lagsMs'], 'fresh', sg['caretBandFreshAfterReleaseMs'], 'washes', [(x['untilCaretMs'], x['framesWithWash']) for x in ww])
