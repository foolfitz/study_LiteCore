# Finding 149 evidence: Markdown entities are dropped (native, one run)

Run 2026-10-16 by the main session with the round-1 native probe (`findings/evidence/link-batch-v21/native/markdown-paste/tool/md_paste_probe.cpp`, binary in the session scratchpad). The install is `native-lok-26-8/build/instdir/program` (buildid `671c848b`). The input document is `markdown-paste/tool/inputs/empty-template.odt`; the paste lands at the document start with `text/markdown;charset=utf-8`; `LANG=zh_TW.UTF-8`.

- Input (`E1.md`): `AT&amp;T and a &lt; b and &copy; and &#x4E2D; end`
- Saved body text (`after.fodt`): `ATT and a  b and  and  end`. Every entity is gone, named and numeric alike.
- Source (`mdcallbcks-671c848b-290-302.cxx.txt`): the text callback has `case MD_TEXT_ENTITY: … break;`, so nothing is inserted.

**One run only.** Before sending this upstream, run it 3 times and on desktop LibreOffice.
