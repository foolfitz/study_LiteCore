"""Summarise the Language= arms from the stored evidence only (out/<arm>-r<n>/, tool/inputs/).

Usage: python3 -I summarize.py <evidence-dir>   (writes nothing; prints the summary)

Per run it reads: run.txt, probe.stdout (readouts), styles.xml, content.xml, registry-snippet.xcu.
Page size is resolved through master-page[@style:name='Standard']/@style:page-layout-name, not
"the first page-layout". It refuses to report if it finds no runs (non-vacuity).
"""
import glob
import hashlib
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
}


def q(ns, a):
    return '{%s}%s' % (NS[ns], a)


LANG_ATTRS = [q('fo', 'language'), q('fo', 'country'), q('style', 'language-asian'), q('style', 'country-asian'),
              q('style', 'language-complex'), q('style', 'country-complex')]
FONT_ATTRS = [q('style', 'font-name'), q('style', 'font-name-asian'), q('style', 'font-name-complex')]
SHORT = {a: a.split('}')[1] for a in LANG_ATTRS + FONT_ATTRS}

# probe-1 (2026-10-14) styles.xml hashes, from ../../new-document/probe-1-native-defaults/SHA256SUMS
PROBE1 = {
    'd2b08cda0de24b0eeedaead96e4a4f516a156e64a31c1dafbe7e2db923d30921': 'probe-1 A (zh_TW, none) = E',
    'b4724ec01b34ea51c958978916074cbacded80a94e338065b1eadb24c15dadce': 'probe-1 B (en_US, none) = C',
    'b21957cd574dd5c81eedb794b74596cc210d55c3478a2a4dd0ca2a30a1320100': 'probe-1 D (en_US, Language=zh-TW)',
    '3d7a024694d3324ca1026b914d828869b1102dad17204cce5c168c12b2519fbb': 'probe-1 F (zh_TW, Language=zh-TW)',
    '2cabf5c6a99fc6b1cc9effaaeaad4e877980121913333e7ad57717dbadf035a6': 'probe-1 G (en_US, Language=zh-CN)',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def to_mm(v):
    m = re.fullmatch(r'([0-9.]+)(in|cm|mm)', v or '')
    if not m:
        return None
    return round(float(m.group(1)) * {'in': 25.4, 'cm': 10.0, 'mm': 1.0}[m.group(2)], 1)


def paper_name(w, h):
    if w is None:
        return '?'
    if abs(w - 210.0) < 0.5 and abs(h - 297.0) < 0.5:
        return 'A4'
    if abs(w - 215.9) < 0.5 and abs(h - 279.4) < 0.5:
        return 'Letter'
    return 'other'


def describe_styles(xml_bytes):
    root = ET.fromstring(xml_bytes)
    ds = root.find('.//office:styles/style:default-style[@style:family="paragraph"]', NS)
    tp = ds.find('style:text-properties', NS) if ds is not None else None
    g = (lambda a: tp.get(a, '-')) if tp is not None else (lambda a: '-')
    langs = '%s-%s / %s-%s / %s-%s' % tuple(g(a) for a in LANG_ATTRS)
    fonts = ' / '.join(g(a) for a in FONT_ATTRS)
    mp = root.find('.//office:master-styles/style:master-page[@style:name="Standard"]', NS)
    plname = mp.get(q('style', 'page-layout-name')) if mp is not None else None
    page = '(no Standard master page)'
    if plname:
        pl = root.find('.//office:automatic-styles/style:page-layout[@style:name="%s"]/style:page-layout-properties' % plname, NS)
        if pl is not None:
            w, h = pl.get(q('fo', 'page-width')), pl.get(q('fo', 'page-height'))
            wm, hm = to_mm(w), to_mm(h)
            page = '%s x %s = %s x %s mm (%s) via %s' % (w, h, wm, hm, paper_name(wm, hm), plname)
    ffd = [f.get(q('style', 'name')) for f in root.findall('.//office:font-face-decls/style:font-face', NS)]
    defaults = {a: (tp.get(a) if tp is not None else None) for a in LANG_ATTRS + FONT_ATTRS}
    # The graphic default-style (shapes, text boxes) carries its own fonts, sometimes as
    # style:font-family* (a fontconfig-derived family, no font-face-decl) instead of style:font-name*.
    gtp = root.find('.//office:styles/style:default-style[@style:family="graphic"]/style:text-properties', NS)
    def gf(kind):
        if gtp is None:
            return '-'
        sfx = '' if kind == '' else '-' + kind
        fam = q('style', 'font-family' + sfx) if kind else q('fo', 'font-family')
        return gtp.get(q('style', 'font-name' + sfx)) or gtp.get(fam) or '-'
    gfonts = ' / '.join(gf(k).strip("'") for k in ('', 'asian', 'complex'))
    return {'langs': langs, 'fonts': fonts, 'page': page, 'ffd': ', '.join(ffd), 'defaults': defaults,
            'root': root, 'default_tp': tp, 'gfonts': gfonts}


def overrides(root, default_tp, defaults):
    """Every text-properties outside the paragraph default-style that sets a language, country or
    font-name differing from the paragraph default (J2's crafted-override blind spot)."""
    out = set()
    for parent in root.iter():
        for tp in parent.findall(q('style', 'text-properties')):
            if tp is default_tp:
                continue
            owner = '%s[%s]' % (parent.tag.split('}')[1],
                                parent.get(q('style', 'name')) or parent.get(q('style', 'family')) or '?')
            diff = ['%s=%s' % (SHORT[a], tp.get(a)) for a in LANG_ATTRS + FONT_ATTRS
                    if tp.get(a) is not None and tp.get(a) != defaults.get(a)]
            if diff:
                out.add('%s{%s}' % (owner, ' '.join(diff)))
    return sorted(out)


def readouts(stdout):
    r = {}
    for line in stdout.splitlines():
        m = re.match(r'\[(after-[a-z]+)\] (.*)$', line)
        if m:
            r.setdefault(m.group(1), []).append(m.group(2))
    return r


def pick(lines, key):
    for l in lines or []:
        if l.startswith(key):
            return l[len(key):].strip()
    return '-'


def main():
    ev = sys.argv[1]
    runs = sorted(d for d in glob.glob(os.path.join(ev, 'out', '*-r[12]')) if os.path.isdir(d))
    if not runs:
        sys.exit('no runs under %s/out -- refusing to report an empty summary' % ev)
    arms = {}
    for d in runs:
        arm, r = os.path.basename(d).rsplit('-r', 1)
        arms.setdefault(arm, {})[r] = d

    # Templates (Q3 baseline): the bytes as shipped by the host.
    tmpl = {}
    for t in ('en-US_zh-TW_A4.odt', 'en-US_zh-TW_Letter.odt'):
        p = os.path.join(ev, 'tool', 'inputs', t)
        b = zipfile.ZipFile(p).read('styles.xml')
        tmpl[t] = (sha(b), describe_styles(b))

    print('runs: %d, arms: %d' % (len(runs), len(arms)))
    print()
    rows = {}
    for arm in arms:
        per = {}
        for r, d in sorted(arms[arm].items()):
            run = open(os.path.join(d, 'run.txt')).read()
            stdout = open(os.path.join(d, 'probe.stdout'), encoding='utf-8').read()
            sb = open(os.path.join(d, 'styles.xml'), 'rb').read()
            cb = open(os.path.join(d, 'content.xml'), 'rb').read()
            # The date field stores a wall-clock timestamp; mask it for the run-to-run comparison.
            cb_masked = re.sub(rb'text:date-value="[^"]*"', b'text:date-value="*"', cb)
            reg = open(os.path.join(d, 'registry-snippet.xcu'), encoding='utf-8').read()
            regv = dict(re.findall(r'oor:name="(ooSetupSystemLocale|ooLocale)"[^>]*>\s*<value>([^<]*)</value>', reg))
            desc = describe_styles(sb)
            ov = overrides(desc['root'], desc['default_tp'], desc['defaults'])
            croot = ET.fromstring(cb)
            ov_c = overrides(croot, None, desc['defaults'])
            ro = readouts(stdout)
            # The readout lines minus nothing: they must be equal run to run.
            dates = re.findall(r'date-field selection text/plain="([^"]*)"', stdout)
            ds_lang = [(e.get(q('style', 'name')), e.get(q('number', 'language'), '-'), e.get(q('number', 'country'), '-'),
                        e.get(q('number', 'format-source'), '-'))
                       for e in croot.iter(q('number', 'date-style'))]
            per[r] = dict(run=run.splitlines()[0], styles_sha=sha(sb), content_sha=sha(cb), content_masked_sha=sha(cb_masked),
                          desc=desc, ov=ov, ov_c=ov_c, ro=ro, reg=regv, dates=dates, ds=ds_lang,
                          ro_text='\n'.join(l for l in stdout.splitlines() if l.startswith('[')))
        rows[arm] = per
        a = per['1']
        b = per.get('2')
        same = b is not None and a['styles_sha'] == b['styles_sha'] and a['content_masked_sha'] == b['content_masked_sha'] \
            and a['ro_text'] == b['ro_text'] and a['reg'] == b['reg'] and a['dates'] == b['dates']
        print('== %s   [%s]' % (arm, a['run'].split(' run=')[1].split(' ', 1)[1]))
        print('   r1 == r2 (styles.xml bytes, content.xml bytes with date-value masked, readouts, registry): %s' % same)
        print('   styles.xml sha256 %s%s' % (a['styles_sha'], ('   <- ' + PROBE1[a['styles_sha']]) if a['styles_sha'] in PROBE1 else ''))
        print('   content.xml sha256 %s (masked %s)' % (a['content_sha'][:16], a['content_masked_sha'][:16]))
        print('   saved default langs (W/A/C): %s' % a['desc']['langs'])
        print('   saved default fonts (W/A/C): %s' % a['desc']['fonts'])
        print('   graphic default-style fonts (W/A/C): %s' % a['desc']['gfonts'])
        print('   saved page (Standard master): %s' % a['desc']['page'])
        print('   font-face-decls: %s' % a['desc']['ffd'])
        print('   overrides vs default (styles.xml): %s' % (', '.join(a['ov']) or 'none'))
        print('   overrides vs default (content.xml): %s' % (', '.join(a['ov_c']) or 'none'))
        print('   registry after run: ooSetupSystemLocale=%s ooLocale=%s' % (a['reg'].get('ooSetupSystemLocale', '(not written)'),
                                                                          a['reg'].get('ooLocale', '(not written)')))
        for phase in ('after-init', 'after-mutation', 'after-load'):
            L = a['ro'].get(phase)
            if not L:
                continue
            print('   [%s] System/L10N: %s' % (phase, pick(L, 'cfg System/L10N')))
            print('   [%s] Setup/L10N: %s' % (phase, pick(L, 'cfg Setup/L10N')))
            print('   [%s] fallbacks: %s | resolve(SYSTEM): %s' % (phase, pick(L, 'fallbacks'), pick(L, 'resolve(SYSTEM)')))
            print('   [%s] LOK: %s | %s' % (phase, pick(L, 'LOK'), pick(L, 'PaperInfo::getSystemDefaultPaper')))
            print('   [%s] SvtSysLocale: %s' % (phase, pick(L, 'SvtSysLocale')))
            print('   [%s] glibc: %s' % (phase, pick(L, 'glibc setlocale(LC_ALL,NULL)=')))
        if a['dates']:
            print('   date field text: %s ; content.xml date-styles (name, number:language, number:country, format-source): %s'
                  % (a['dates'], a['ds']))
        print()

    print('== Compact table (run 1; "same" = run 2 identical as defined above)')
    print('arm | LANG | options | saved W / A / C | saved fonts W / A / C | graphic default fonts W / A / C | saved page | registry ooSetupSystemLocale/ooLocale | '
          'after-init System/L10N/Locale | after-init fallbacks W/A/C | after-load SvtSysLocale | date field | styles sha256[:16] | same')
    for arm, per in sorted(rows.items()):
        a = per['1']
        b = per.get('2')
        same = b is not None and a['styles_sha'] == b['styles_sha'] and a['content_masked_sha'] == b['content_masked_sha'] \
            and a['ro_text'] == b['ro_text'] and a['reg'] == b['reg'] and a['dates'] == b['dates']
        m = re.search(r'LANG=(\S+) options=(\S+)', a['run'])
        init = a['ro'].get('after-init')
        load = a['ro'].get('after-load')
        strip = lambda t: re.sub(r'\(0x[0-9a-f]+\)', '', t)
        loc = pick(init, 'cfg System/L10N').split(' ')[0].replace('Locale=', '') if init else '(tool has no readout)'
        fb = strip(pick(init, 'fallbacks')).replace('western=', '').replace(' asian=', ' / ').replace(' complex=', ' / ') if init else '-'
        sv = pick(load, 'SvtSysLocale') if load else '-'
        sv = re.sub(r'languageTag=(\S+) localeData=(\S+) currSymbol="([^"]*)" bank="([^"]*)" decimalSep="([^"]*)" dateSep="([^"]*)" date\(2026-10-16\)="([^"]*)"',
                    r'tag \1, data \2, \4 \3, dec "\5", date \7', sv)
        page = a['desc']['page'].split(' via ')[0]
        print('%s | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s | %s | %s | %s | %s' % (
            arm, m.group(1), m.group(2), a['desc']['langs'], a['desc']['fonts'], a['desc']['gfonts'], page,
            a['reg'].get('ooSetupSystemLocale', '-'), a['reg'].get('ooLocale', '-'), loc, fb, sv,
            (a['dates'][0] + ' ' + str(a['ds'])) if a['dates'] else '-', a['styles_sha'][:16], same))
    print()
    print('== Pairs (run 1 and run 2 each; styles.xml bytes, content.xml bytes with date-value masked, readouts, registry snippet)')
    PAIRS = [
        ('Q1-deDE-zhTW', 'Q2-zhTW', 'de_DE vs en_US environment, both Language=zh-TW'),
        ('Q1-deDE-none', 'Q2-none', 'de_DE vs en_US environment, no option'),
        ('L-deDE-zhTW', 'Q1-deDE-zhTW', 'glibc de_DE.UTF-8 available (LOCPATH) vs not'),
        ('L-deDE-none', 'Q1-deDE-none', 'glibc de_DE.UTF-8 available (LOCPATH) vs not'),
        ('L-jaJP-none', 'Q4-jaJP-none', 'glibc ja_JP.UTF-8 available (LOCPATH) vs not'),
        ('L-jaJP-enUS', 'Q4-jaJP-enUS', 'glibc ja_JP.UTF-8 available (LOCPATH) vs not'),
        ('R-zhTW-none', 'R-orig-zhTW-none', 'this tool vs probe-1 tool, zh_TW, no option'),
        ('Q2-none', 'R-orig-enUS-none', 'this tool vs probe-1 tool, en_US, no option'),
        ('Q2-enUS', 'Q2-none', 'Language=en-US vs no option (en_US)'),
        ('Q2-invalid', 'Q2-none', 'Language=xx_bad! vs no option'),
        ('Q2-zh_TW-underscore', 'Q2-none', 'Language=zh_TW vs no option'),
    ]
    for x, y, why in PAIRS:
        if x not in rows or y not in rows:
            print('   %s vs %s: MISSING' % (x, y))
            continue
        res = []
        for r in ('1', '2'):
            a, b = rows[x][r], rows[y][r]
            res.append('r%s styles %s content %s readouts %s registry %s' % (
                r, a['styles_sha'] == b['styles_sha'], a['content_masked_sha'] == b['content_masked_sha'],
                a['ro_text'] == b['ro_text'] if (a['ro_text'] and b['ro_text']) else 'n/a', a['reg'] == b['reg']))
        print('   %s vs %s (%s): %s' % (x, y, why, ' | '.join(res)))
    print()
    print('== Q3: templates vs saves')
    for t, (tsha, td) in tmpl.items():
        print('   template %s styles.xml sha256 %s' % (t, tsha))
        print('     template langs %s | fonts %s | page %s' % (td['langs'], td['fonts'], td['page']))
        key = 'A4' if 'A4' in t else 'Letter'
        base = rows.get('Q3-%s-none' % key)
        for opt in ('none', 'enUS', 'ja'):
            arm = 'Q3-%s-%s' % (key, opt)
            if arm not in rows:
                continue
            a = rows[arm]['1']
            sem = (a['desc']['langs'] == td['langs'] and a['desc']['fonts'] == td['fonts']
                   and a['desc']['page'].split(' = ')[1] == td['page'].split(' = ')[1])
            print('     %-16s styles==template bytes: %s | semantic (langs, fonts, page mm) == template: %s | '
                  'styles bytes == no-option save: %s | content bytes == no-option save: %s'
                  % (arm, a['styles_sha'] == tsha, sem, a['styles_sha'] == base['1']['styles_sha'],
                     a['content_sha'] == base['1']['content_sha']))
            print('       saved page: %s' % a['desc']['page'])


if __name__ == '__main__':
    main()
