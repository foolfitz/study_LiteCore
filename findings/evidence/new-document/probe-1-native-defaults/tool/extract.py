import sys, zipfile, re, os, glob
import xml.etree.ElementTree as ET
NS={'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','style':'urn:oasis:names:tc:opendocument:xmlns:style:1.0','fo':'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0','svg':'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0'}
def q(ns,a): return '{%s}%s'%(NS[ns],a)
out=sys.argv[1]
for path in sorted(glob.glob(os.path.join(out,'*.odt'))):
    arm=os.path.basename(path)[:-4]
    z=zipfile.ZipFile(path); root=ET.fromstring(z.read('styles.xml'))
    ds=root.find('.//office:styles/style:default-style[@style:family="paragraph"]',NS)
    tp=ds.find('style:text-properties',NS)
    g=lambda a: tp.get(a,'-')
    langs='%s-%s / %s-%s / %s-%s'%(g(q('fo','language')),g(q('fo','country')),g(q('style','language-asian')),g(q('style','country-asian')),g(q('style','language-complex')),g(q('style','country-complex')))
    fonts='%s / %s / %s'%(g(q('style','font-name')),g(q('style','font-name-asian')),g(q('style','font-name-complex')))
    pl=root.find('.//office:automatic-styles/style:page-layout/style:page-layout-properties',NS)
    page='%s x %s'%(pl.get(q('fo','page-width')),pl.get(q('fo','page-height'))) if pl is not None else '(no page-layout)'
    ffd=[f.get(q('style','name')) for f in root.findall('.//office:font-face-decls/style:font-face',NS)]
    # Heading style fonts
    hd=root.find('.//office:styles/style:style[@style:name="Heading"]/style:text-properties',NS)
    hfonts='-' if hd is None else '%s / %s / %s'%(hd.get(q('style','font-name'),'-'),hd.get(q('style','font-name-asian'),'-'),hd.get(q('style','font-name-complex'),'-'))
    env=open(os.path.join(out,arm+'.stdout')).readline().strip()
    reg=''
    rm=os.path.join(os.path.dirname(out),'profile-'+arm,'user','registrymodifications.xcu')
    if os.path.exists(rm):
        t=open(rm,encoding='utf-8').read()
        m=re.findall(r'oor:name="(ooSetupSystemLocale|ooLocale)"[^>]*>\s*<value>([^<]*)</value>',t)
        reg=' '.join('%s=%s'%kv for kv in m) or '(neither key written)'
    print('== arm %s | %s'%(arm,env))
    print('   langs (W/A/C): %s'%langs)
    print('   fonts (W/A/C): %s'%fonts)
    print('   Heading fonts: %s'%hfonts)
    print('   page         : %s'%page)
    print('   font-face-decls: %s'%', '.join(ffd))
    print('   registry     : %s'%reg)
    z.extract('styles.xml', os.path.join(out, arm+'-unzipped'))
