Static upstream re-check, 2026-11-10T09:37Z
Repository: /home/jiajun/LibreOffice/lo-submit (remote: https://github.com/LibreOffice/core.git)
Found at:   671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb 2026-07-30
Compared:   libreoffice-26.8.2.2 = 9dea406ab7695df6325b11b0e19fdca8db4b7276 2026-10-22
Compared:   libreoffice-26.8.3.1 = 861effc5289d539f15c4c18d1ba8579ffd78728b 2026-11-09
Compared:   origin/master = 2a2335cf091104f36d44809b2fb70a9cd32258df 2026-11-10

== LibreOffice side, per ref
671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb:
  download.lst: FONTCONFIG_SHA256SUM := cf8e6576ef0484c15079bdaf77cd9c51c464df5365814ada4d3ee7331ea31eb5 FONTCONFIG_TARBALL := fontconfig-2.18.2.tar.xz 
  ExternalPackage_fontconfig_data.mk lines with 35-lang-normalize: 34:    conf.d/35-lang-normalize.conf \ 
  Module_fontconfig.mk packaging conditions: ifeq ($(COM),MSC)  ExternalPackage_fontconfig_data \  $(if $(filter EMSCRIPTEN,$(OS)),ExternalPackage_fontconfig_data) \  $(if $(filter MACOSX,$(OS)),ExternalPackage_fontconfig_data) \ 
  FC_LANG added as a string:
    vcl/unx/generic/fontmanager/fontconfig.cxx:1139:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));
    vcl/unx/generic/fontmanager/fontconfig.cxx:1420:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));
libreoffice-26.8.2.2:
  download.lst: FONTCONFIG_SHA256SUM := 4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3 FONTCONFIG_TARBALL := fontconfig-2.18.3.tar.xz 
  ExternalPackage_fontconfig_data.mk lines with 35-lang-normalize: 34:    conf.d/35-lang-normalize.conf \ 
  Module_fontconfig.mk packaging conditions: ifeq ($(COM),MSC)  ExternalPackage_fontconfig_data \  $(if $(filter EMSCRIPTEN,$(OS)),ExternalPackage_fontconfig_data) \  $(if $(filter MACOSX,$(OS)),ExternalPackage_fontconfig_data) \ 
  FC_LANG added as a string:
    vcl/unx/generic/fontmanager/fontconfig.cxx:1139:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));
    vcl/unx/generic/fontmanager/fontconfig.cxx:1420:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));
libreoffice-26.8.3.1:
  download.lst: FONTCONFIG_SHA256SUM := 4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3 FONTCONFIG_TARBALL := fontconfig-2.18.3.tar.xz 
  ExternalPackage_fontconfig_data.mk lines with 35-lang-normalize: 34:    conf.d/35-lang-normalize.conf \ 
  Module_fontconfig.mk packaging conditions: ifeq ($(COM),MSC)  ExternalPackage_fontconfig_data \  $(if $(filter EMSCRIPTEN,$(OS)),ExternalPackage_fontconfig_data) \  $(if $(filter MACOSX,$(OS)),ExternalPackage_fontconfig_data) \ 
  FC_LANG added as a string:
    vcl/unx/generic/fontmanager/fontconfig.cxx:1139:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));
    vcl/unx/generic/fontmanager/fontconfig.cxx:1420:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));
origin/master:
  download.lst: FONTCONFIG_SHA256SUM := 4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3 FONTCONFIG_TARBALL := fontconfig-2.18.3.tar.xz 
  ExternalPackage_fontconfig_data.mk lines with 35-lang-normalize: 34:    conf.d/35-lang-normalize.conf \ 
  Module_fontconfig.mk packaging conditions: ifeq ($(COM),MSC)  ExternalPackage_fontconfig_data \  $(if $(filter EMSCRIPTEN,$(OS)),ExternalPackage_fontconfig_data) \  $(if $(filter MACOSX,$(OS)),ExternalPackage_fontconfig_data) \ 
  FC_LANG added as a string:
    vcl/unx/generic/font/fontconfig.cxx:1168:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));
    vcl/unx/generic/font/fontconfig.cxx:1447:        FcPatternAddString(pPattern, FC_LANG, reinterpret_cast<FcChar8 const *>(aLangAttrib.getStr()));

fontconfig upgrade commits: 
  80b5857b97e3a5b86c48be6bbc70a9d970f10546 2026-08-18 Xisco Fauli | fontconfig: upgrade to 2.18.3
  4c68c8af2ec0382d4e24c8ccad10f73c3c5090d5 2026-08-17 Xisco Fauli | fontconfig: upgrade to 2.18.3

== fontconfig tarballs
2.18.2: local copy libreoffice-26-8/external/tarballs/fontconfig-2.18.2.tar.xz sha256 cf8e6576ef0484c15079bdaf77cd9c51c464df5365814ada4d3ee7331ea31eb5
2.18.3: https://dev-www.libreoffice.org/src/fontconfig-2.18.3.tar.xz sha256 4f7b554a38cdf78c033f666c8871f3749e14a094f65a07f630c91ed0b43d35e3 (matches download.lst of 26.8.2.2)

== fontconfig 2.18.2 -> 2.18.3
conf.d/35-lang-normalize.conf: 258 -> 315 rules; diff lines removed 0, added 285; every 2.18.2 rule present verbatim in 2.18.3 (see 35-lang-normalize.2.18.2-to-2.18.3.diff)
  identical: conf.d/write-35-lang-normalize-conf.py
  identical: src/fccfg.c
  identical: src/fcmatch.c
  identical: src/fclang.c
  differs:   src/fcxml.c
  differs:   conf.d/40-nonlatin.conf
  differs:   conf.d/60-latin.conf
  src/fcxml.c: the only changed lines naming FcOpContains are inside FcExprDup, a function new in 2.18.3 that copies expressions (switch over every operator); string comparison lives in src/fccfg.c FcConfigCompareValue, identical.

== Census (findings/evidence/114/review/census.py, unchanged)
Library: native-lok-26-8/build/instdir/program/libfontconfig-lo.so.1.16.1 (LibreOffice's bundled fontconfig 2.18.2).
Rules: the v16 profile conf.d (wasm_sdk_probe/build/wasm-fontset-v16/conf.d, 22 files; its 35-lang-normalize.conf is byte-identical to stock 2.18.2), included by absolute path as in fc-debug/native-repro/fonts-abs-include.conf with only <cachedir> moved to a scratch directory.
Control:  same rules as the committed run -> census-control-2.18.2-rules.txt, identical to review/census-abs.txt (66 rewritten).
Variant:  same 22 files with 35-lang-normalize.conf replaced by fontconfig 2.18.3's -> census-2.18.3-rules.txt (66 rewritten; zh-tw -> tw, zh-mo -> mo, zh-sg -> sg, nan -> an, hak -> ak unchanged; only change wae -> wa became wae -> ae).

Not covered: the census ran fontconfig 2.18.2's library with 2.18.3's rule file. FcGetLangs() of a 2.18.3 library has 57 more tags (the new .orth files); those tags were not censused. Building fontconfig 2.18.3 was not done. 40-nonlatin.conf and 60-latin.conf also changed in 2.18.3 (family preferences) and were not evaluated.
