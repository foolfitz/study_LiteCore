from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

root = Path('/tmp/litecore-review114-native')
root.mkdir(exist_ok=True)
source = Path('/tmp/litecore-review114-fonts')
for mode in ('with35', 'without35'):
    dest = root / mode
    dest.mkdir(exist_ok=True)
    (dest / 'cache').mkdir(exist_ok=True)
    (dest / 'xdg').mkdir(exist_ok=True)
    (dest / 'user-profile').mkdir(exist_ok=True)
    (dest / 'conf.d').mkdir(exist_ok=True)
    for file in sorted((source / 'conf.d').glob('*.conf')):
        if mode == 'without35' and file.name == '35-lang-normalize.conf':
            continue
        shutil.copyfile(file, dest / 'conf.d' / file.name)
    config = (source / 'fonts.conf').read_text()
    config = config.replace('<include ignore_missing="yes">conf.d</include>',
                            f'<include ignore_missing="yes">{dest}/conf.d</include>')
    config = config.replace(f'<cachedir>{source}/cache</cachedir>',
                            f'<cachedir>{dest}/cache</cachedir>')
    (dest / 'fonts.conf').write_text(config)

head = '''<?xml version="1.0" encoding="UTF-8"?>
<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
 office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.text">
<office:font-face-decls>
<style:font-face style:name="Siyuan" svg:font-family="'思源黑體'" style:font-family-generic="system" style:font-pitch="variable"/>
<style:font-face style:name="Noto" svg:font-family="'Noto Sans CJK TC'" style:font-family-generic="system" style:font-pitch="variable"/>
<style:font-face style:name="Liberation" svg:font-family="'Liberation Sans'" style:font-family-generic="swiss" style:font-pitch="variable"/>
</office:font-face-decls><office:styles>
<style:default-style style:family="paragraph"><style:paragraph-properties fo:margin-top="0cm" fo:margin-bottom="0cm"/><style:text-properties style:font-name="Liberation" fo:font-size="12pt" style:font-size-asian="12pt" style:language-asian="zh" style:country-asian="TW"/></style:default-style>
</office:styles><office:automatic-styles>'''
items = [('a', 'Siyuan', 12, '第一組中文字'), ('b', 'Noto', 12, '第二組中文字'),
         ('c', 'Siyuan', 18, '第三組中文字'), ('d', 'Liberation', 12, 'Latin control')]
styles = ''.join(f'<style:style style:name="{name}" style:family="paragraph"><style:text-properties style:font-name-asian="{font}" fo:font-size="{size}pt" style:font-size-asian="{size}pt" style:language-asian="zh" style:country-asian="TW"/></style:style>' for name, font, size, text in items)
body = ''.join(f'<text:p text:style-name="{name}">{text}</text:p>' * 2 for name, font, size, text in items)
doc = head + styles + '</office:automatic-styles><office:body><office:text>' + body + '</office:text></office:body></office:document>'
ET.fromstring(doc)
(root / 'fixture.fodt').write_text(doc)
for mode in ('with35', 'without35'):
    shutil.copyfile(root / 'fixture.fodt', root / mode / 'fixture.fodt')
print(root)
