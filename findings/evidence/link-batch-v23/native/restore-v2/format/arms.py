"""Frozen finite FORMAT residue population; register before counted execution."""
HOME, END, DOWN = 1028, 1029, 1024
BODY = 'U.uno:StyleApply|{"Style":{"type":"string"`"value":"Text body"}`"FamilyName":{"type":"string"`"value":"ParagraphStyles"}}'
F_ARMS = []
for continuation in ('shift', 'handles'):
    for variant in ('direct', 'reset', 'candidate', 'wrong'):
        point = 'wrong' if variant == 'wrong' else 'before'
        ops = [BODY]
        if variant != 'direct':
            ops += ['Rbefore', 'U.uno:SelectText',
                    ('R' if variant == 'reset' else 'Q') + point]
        if continuation == 'handles':
            ops += ['R' + point, 'Eend', 'R' + point]
        F_ARMS.append({
            'name': f'format-{continuation}-{variant}', 'fixture': 'plain3',
            'script': f'rwrong,k{DOWN},k{HOME},rbefore,k{END},rend,k{HOME},Xformat@{HOME}=' + ';'.join(ops) + ',S,L',
            'note': f'FORMAT residue: {variant}, next {continuation}; one-line plain P2 only',
            'decides': True,
        })


def expected_ops(arm):
    return [op.split('|')[0] for op in arm['script'].split('=', 1)[1].split(',S,L')[0].split(';')]
