#!/usr/bin/env bash
# Runs every arm twice, strictly one LOK process at a time, each under `nice -n 10`, each with
# a fresh empty user profile and an explicit environment built with `env -i`:
#   HOME, PATH, TMPDIR (scratch), LANG (per arm), SAL_USE_VCLPLUGIN=svp, plus the arm's extra
#   probe switch if any (PROBE_DATE_FIELD=1 for Q5, PROBE_FORCE_WESTERN_FALLBACK=de-DE for the
#   mutation control M1, LOCPATH=<scratch>/locales for the L-* controls, whose de_DE.UTF-8 and
#   ja_JP.UTF-8 were compiled with `localedef -i <xx_YY> -f UTF-8 <scratch>/locales/<xx_YY>.UTF-8`
#   because this host's glibc has neither). Nothing else: no LC_*, no LANGUAGE, no PAPERSIZE.
# The input is copied into the run directory first (LibreOffice writes a lock file next to the
# document it loads), so nothing under tool/inputs is touched.
#
# Usage: run_arms.sh <new-probe-binary> <probe-1-binary> <scratch-dir> <evidence-dir> [arm-filter-regex]
set -u
PROBE=$1; ORIG=$2; SCR=$3; EV=$4; FILTER=${5:-.}
INST=/home/jiajun/LibreOffice/study_LiteCore/native-lok-26-8/build/instdir/program
IN=$EV/tool/inputs

# id | tool (new = lok_language_probe, orig = probe-1's lok_defaults_probe) | LANG | load options | input | extra env (- = none)
ARMS='
R-orig-enUS-none|orig|en_US.UTF-8||styleless-template.odt|-
R-orig-zhTW-none|orig|zh_TW.UTF-8||styleless-template.odt|-
R-zhTW-none|new|zh_TW.UTF-8||styleless-template.odt|-
Q1-deDE-zhTW|new|de_DE.UTF-8|Language=zh-TW|styleless-template.odt|-
Q1-deDE-none|new|de_DE.UTF-8||styleless-template.odt|-
M1-deDE-zhTW-forceW-deDE|new|de_DE.UTF-8|Language=zh-TW|styleless-template.odt|PROBE_FORCE_WESTERN_FALLBACK=de-DE
Q2-none|new|en_US.UTF-8||styleless-template.odt|-
Q2-en|new|en_US.UTF-8|Language=en|styleless-template.odt|-
Q2-enUS|new|en_US.UTF-8|Language=en-US|styleless-template.odt|-
Q2-enGB|new|en_US.UTF-8|Language=en-GB|styleless-template.odt|-
Q2-de|new|en_US.UTF-8|Language=de|styleless-template.odt|-
Q2-zhTW|new|en_US.UTF-8|Language=zh-TW|styleless-template.odt|-
Q2-invalid|new|en_US.UTF-8|Language=xx_bad!|styleless-template.odt|-
Q2-zh_TW-underscore|new|en_US.UTF-8|Language=zh_TW|styleless-template.odt|-
Q3-A4-none|new|en_US.UTF-8||en-US_zh-TW_A4.odt|-
Q3-A4-enUS|new|en_US.UTF-8|Language=en-US|en-US_zh-TW_A4.odt|-
Q3-A4-ja|new|en_US.UTF-8|Language=ja|en-US_zh-TW_A4.odt|-
Q3-Letter-none|new|en_US.UTF-8||en-US_zh-TW_Letter.odt|-
Q3-Letter-enUS|new|en_US.UTF-8|Language=en-US|en-US_zh-TW_Letter.odt|-
Q3-Letter-ja|new|en_US.UTF-8|Language=ja|en-US_zh-TW_Letter.odt|-
L-deDE-zhTW|new|de_DE.UTF-8|Language=zh-TW|styleless-template.odt|LOCPATH=@SCR@/locales
L-deDE-none|new|de_DE.UTF-8||styleless-template.odt|LOCPATH=@SCR@/locales
L-jaJP-none|new|ja_JP.UTF-8||styleless-template.odt|LOCPATH=@SCR@/locales
L-jaJP-enUS|new|ja_JP.UTF-8|Language=en-US|styleless-template.odt|LOCPATH=@SCR@/locales
Q4-jaJP-none|new|ja_JP.UTF-8||styleless-template.odt|-
Q4-jaJP-enUS|new|ja_JP.UTF-8|Language=en-US|styleless-template.odt|-
Q4-enUS-ja|new|en_US.UTF-8|Language=ja|styleless-template.odt|-
Q5-none|new|en_US.UTF-8||styleless-template.odt|PROBE_DATE_FIELD=1
Q5-enUS|new|en_US.UTF-8|Language=en-US|styleless-template.odt|PROBE_DATE_FIELD=1
Q5-de|new|en_US.UTF-8|Language=de|styleless-template.odt|PROBE_DATE_FIELD=1
Q5-zhTW|new|en_US.UTF-8|Language=zh-TW|styleless-template.odt|PROBE_DATE_FIELD=1
'

mkdir -p "$SCR/tmp" "$EV/out"
echo "$ARMS" | while IFS='|' read -r id tool lang opts input extra; do
  [ -z "$id" ] && continue
  echo "$id" | grep -Eq -- "$FILTER" || continue
  for r in 1 2; do
    run="$id-r$r"; dir="$SCR/runs/$run"
    rm -rf "$dir"; mkdir -p "$dir/profile"
    cp "$IN/$input" "$dir/in.odt"
    bin=$PROBE; [ "$tool" = orig ] && bin=$ORIG
    envs=(HOME="$HOME" PATH=/usr/bin:/bin TMPDIR="$SCR/tmp" LANG="$lang" SAL_USE_VCLPLUGIN=svp)
    [ "$extra" != - ] && envs+=("${extra//@SCR@/$SCR}")
    args=("$INST" "file://$dir/profile" "file://$dir/in.odt" "$dir/out.odt")
    [ -n "$opts" ] && args+=("$opts")
    start=$(date +%s.%N)
    env -i "${envs[@]}" timeout 300 nice -n 10 "$bin" "${args[@]}" > "$dir/stdout" 2> "$dir/stderr"
    rc=$?
    end=$(date +%s.%N)
    o="$EV/out/$run"; rm -rf "$o"; mkdir -p "$o"
    cp "$dir/stdout" "$o/probe.stdout"; cp "$dir/stderr" "$o/probe.stderr"
    {
      echo "id=$id run=$r tool=$tool LANG=$lang options=${opts:-(none)} input=$input extra_env=$extra rc=$rc"
      echo "seconds=$(echo "$end - $start" | bc)"
      echo "input_sha256=$(sha256sum "$dir/in.odt" | cut -d' ' -f1)"
      [ -f "$dir/out.odt" ] && echo "out_odt_sha256=$(sha256sum "$dir/out.odt" | cut -d' ' -f1)"
      reg="$dir/profile/user/registrymodifications.xcu"
      [ -f "$reg" ] && echo "registrymodifications_sha256=$(sha256sum "$reg" | cut -d' ' -f1) bytes=$(stat -c %s "$reg")"
    } > "$o/run.txt"
    if [ -f "$dir/out.odt" ]; then
      python3 -I -c 'import sys,zipfile
z=zipfile.ZipFile(sys.argv[1])
for n in ("styles.xml","content.xml"):
    open(sys.argv[2]+"/"+n,"wb").write(z.read(n))' "$dir/out.odt" "$o"
    fi
    reg="$dir/profile/user/registrymodifications.xcu"
    [ -f "$reg" ] && grep -E 'L10N|Linguistic/General|I18N' "$reg" > "$o/registry-snippet.xcu"
    echo "$run rc=$rc"
  done
done
