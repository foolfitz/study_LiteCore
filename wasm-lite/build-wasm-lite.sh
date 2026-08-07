#!/usr/bin/env bash
#
# build-wasm-lite.sh — 把 libreoffice-26-8 編成精簡的 Writer-only WASM 核心
#
# 規劃與理由見 README.md。這支腳本只是把那份規劃自動化。
#
# 用法:
#   ./build-wasm-lite.sh doctor        # 檢查環境（不改任何東西）
#   ./build-wasm-lite.sh all           # 全自動
#   ./build-wasm-lite.sh <step>        # 單獨跑某一步
#
# 步驟: emsdk qt5 submodules fonts patch unpatch configure build report serve clean
#
set -euo pipefail

# ---------------------------------------------------------------------------
# 設定（全部可用環境變數覆蓋）
# ---------------------------------------------------------------------------
LITE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 預設 26-8（見 README §5.5 分支選擇）。要退回 26-2 就 LO_SRC=.../libreoffice-26-2 ./build-wasm-lite.sh ...
LO_SRC="${LO_SRC:-$(cd "$LITE_ROOT/.." && pwd)/libreoffice-26-8}"
LITE_BUILDDIR="${LITE_BUILDDIR:-$LITE_ROOT/build}"
LITE_TOOLS="${LITE_TOOLS:-$LITE_ROOT/tools}"
LITE_LOGDIR="${LITE_LOGDIR:-$LITE_ROOT/logs}"

LITE_LANGS="${LITE_LANGS:-en-US zh-TW}"
LITE_LTO="${LITE_LTO:-1}"
LITE_JOBS="${LITE_JOBS:-$(nproc)}"
LITE_QT="${LITE_QT:-5}"

EMSDK_VERSION="${EMSDK_VERSION:-4.0.10}"
EMSDK_DIR="${EMSDK_DIR:-$LITE_TOOLS/emsdk}"

QT5_REPO="${QT5_REPO:-https://github.com/allotropia/qt5.git}"
QT5_BRANCH="${QT5_BRANCH:-5.15.2+wasm}"
QT5_SRC="${QT5_SRC:-$LITE_TOOLS/qt5-src}"
QT5_PREFIX="${QT5_PREFIX:-$LITE_TOOLS/qt5-wasm}"

# CJK 字型：冒號分隔的檔案路徑清單，留空則自動偵測 / 下載
LITE_CJK_FONT_FILES="${LITE_CJK_FONT_FILES:-}"
LITE_EXTRA_FONTS_DIR="${LITE_EXTRA_FONTS_DIR:-$LITE_TOOLS/extra-fonts}"

NOTO_TC_URL="https://github.com/notofonts/noto-cjk/releases/download/Sans2.004/13_NotoSansTC.zip"

FS_IMAGE_MK="$LO_SRC/static/CustomTarget_emscripten_fs_image.mk"
PATCH_MARKER="# litecore-lite: i18n + extra fonts"

# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
c_r=$'\033[31m'; c_g=$'\033[32m'; c_y=$'\033[33m'; c_b=$'\033[36m'; c_0=$'\033[0m'
[ -t 1 ] || { c_r=; c_g=; c_y=; c_b=; c_0=; }

say()  { printf '%s==>%s %s\n' "$c_b" "$c_0" "$*"; }
ok()   { printf '%s ok %s %s\n' "$c_g" "$c_0" "$*"; }
warn() { printf '%s!!!%s %s\n' "$c_y" "$c_0" "$*" >&2; }
die()  { printf '%sERR%s %s\n' "$c_r" "$c_0" "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

# 載入 emsdk 環境（emsdk_env.sh 對 set -u 不友善）
load_emsdk() {
    [ -f "$EMSDK_DIR/emsdk_env.sh" ] || die "找不到 emsdk，先跑: $0 emsdk"
    set +u
    # shellcheck disable=SC1091
    source "$EMSDK_DIR/emsdk_env.sh" >/dev/null 2>&1
    set -u
    have emcc || die "載入 emsdk 後仍找不到 emcc"
}

# ---------------------------------------------------------------------------
# doctor — 只檢查，不動任何東西
# ---------------------------------------------------------------------------
step_doctor() {
    local fail=0

    say "原始碼樹"
    if [ -f "$LO_SRC/configure.ac" ]; then
        ok "$LO_SRC"
        printf '     版本: %s\n' "$(sed -n 's/^AC_INIT(\[LibreOffice\],\[\([^]]*\)\].*/\1/p' "$LO_SRC/configure.ac" | head -1)"
    else
        warn "$LO_SRC 不是 LibreOffice 原始碼樹"; fail=1
    fi

    say "host 工具"
    local missing=()
    for t in gcc g++ make git ccache autoconf flex bison gperf \
             msgfmt msguniq python3 perl zip unzip pkg-config; do
        have "$t" || missing+=("$t")
    done
    if [ ${#missing[@]} -eq 0 ]; then
        ok "齊全"
    else
        warn "缺少: ${missing[*]}"
        printf '     sudo apt install build-essential git ccache autoconf automake libtool \\\n'
        printf '       pkg-config flex bison gperf gettext python3 python3-dev zip unzip \\\n'
        printf '       nasm libxml2-utils xsltproc perl\n'
        fail=1
    fi

    say "Emscripten"
    if [ -f "$EMSDK_DIR/emsdk_env.sh" ]; then
        load_emsdk
        ok "$(emcc --version 2>/dev/null | head -1)"
    else
        warn "未安裝 → $0 emsdk"; fail=1
    fi

    say "Qt"
    if [ "$LITE_QT" = 5 ]; then
        if [ -x "$QT5_PREFIX/bin/qmake" ]; then
            ok "$QT5_PREFIX"
        else
            warn "未建置 → $0 qt5"; fail=1
        fi
    else
        [ -n "${QT6DIR:-}" ] && [ -x "${QT6DIR:-}/bin/qmake" ] \
            && ok "QT6DIR=$QT6DIR" || { warn "LITE_QT=6 需要自備 QT6DIR"; fail=1; }
    fi

    say "translations submodule"
    if [ -f "$LO_SRC/translations/.git" ] || [ -d "$LO_SRC/translations/.git" ]; then
        ok "已 init"
    else
        warn "未 init → $0 submodules（--with-lang 非 en-US 時 Makefile.in:271 會擋）"; fail=1
    fi

    say "CJK 字型"
    if compgen -G "$LITE_EXTRA_FONTS_DIR/*" >/dev/null 2>&1; then
        ok "$(cd "$LITE_EXTRA_FONTS_DIR" && ls | tr '\n' ' ')"
    else
        warn "尚未準備 → $0 fonts（不做的話繁中會是豆腐字）"
    fi

    say "fs image patch"
    if grep -qF "$PATCH_MARKER" "$FS_IMAGE_MK" 2>/dev/null; then
        ok "已套用"
    else
        warn "未套用 → $0 patch（不做的話 zh-TW 語言包進不了 soffice.data）"
    fi

    say "資源"
    local ram_gb swap_gb swap_disp disk_gb
    ram_gb=$(awk '/MemTotal/{printf "%d", $2/1048576}' /proc/meminfo)
    swap_gb=$(awk '/SwapTotal/{printf "%d", $2/1048576}' /proc/meminfo)
    # 不足 1 GB 時改用 MB 顯示，免得 512 MB 被整數除法印成「0 GB」
    if [ "$swap_gb" -eq 0 ]; then
        swap_disp="$(awk '/SwapTotal/{printf "%d MB", $2/1024}' /proc/meminfo)"
    else
        swap_disp="$swap_gb GB"
    fi
    disk_gb=$(df -BG --output=avail "$LITE_ROOT" | tail -1 | tr -dc '0-9')
    printf '     CPU %s 核 / RAM %s GB / Swap %s / 可用磁碟 %s GB\n' \
        "$(nproc)" "$ram_gb" "$swap_disp" "$disk_gb"

    if [ "$((ram_gb + swap_gb))" -lt 48 ]; then
        warn "RAM+Swap = $((ram_gb + swap_gb)) GB。最後 link soffice.wasm 可能 OOM。"
        printf '     建議加 swap:\n'
        # 已經有 /swapfile 而且掛著的話，fallocate 會失敗（Text file busy），要先 swapoff
        if [ -e /swapfile ]; then
            printf '       （偵測到 /swapfile 已存在，必須先 swapoff 才能改大小）\n'
            printf '       sudo swapoff /swapfile\n'
        fi
        printf '       sudo fallocate -l 64G /swapfile && sudo chmod 600 /swapfile\n'
        printf '       sudo mkswap /swapfile && sudo swapon /swapfile\n'
        [ "$LITE_LTO" = 1 ] && printf '     或改用 LITE_LTO=0（LTO 會再吃更多）\n'
    fi
    [ "$disk_gb" -lt 120 ] && warn "磁碟 $disk_gb GB，建議 120 GB 以上"

    echo
    [ "$fail" -eq 0 ] && ok "可以開始：$0 all" || warn "先解決上面標示的項目"
    return 0
}

# ---------------------------------------------------------------------------
# emsdk
# ---------------------------------------------------------------------------
step_emsdk() {
    mkdir -p "$LITE_TOOLS"
    if [ ! -d "$EMSDK_DIR/.git" ]; then
        say "clone emsdk"
        git clone https://github.com/emscripten-core/emsdk.git "$EMSDK_DIR"
    else
        say "更新 emsdk"
        git -C "$EMSDK_DIR" fetch --quiet origin && git -C "$EMSDK_DIR" reset --hard --quiet origin/main
    fi

    say "安裝 emscripten $EMSDK_VERSION（README.wasm.md 指定版本）"
    "$EMSDK_DIR/emsdk" install "$EMSDK_VERSION"
    "$EMSDK_DIR/emsdk" activate "$EMSDK_VERSION"

    load_emsdk
    ok "$(emcc --version | head -1)"
}

# ---------------------------------------------------------------------------
# qt5 — allotropia 的 wasm fork
# ---------------------------------------------------------------------------
step_qt5() {
    [ "$LITE_QT" = 5 ] || { warn "LITE_QT=$LITE_QT，跳過 Qt5 建置"; return 0; }
    if [ -x "$QT5_PREFIX/bin/qmake" ]; then
        ok "Qt5 已存在於 $QT5_PREFIX（要重建請先刪掉它）"; return 0
    fi

    load_emsdk
    mkdir -p "$LITE_TOOLS" "$LITE_LOGDIR"

    if [ ! -d "$QT5_SRC/.git" ]; then
        say "clone $QT5_REPO ($QT5_BRANCH)"
        git clone --branch "$QT5_BRANCH" --depth 1 "$QT5_REPO" "$QT5_SRC"
    fi

    if [ ! -d "$QT5_SRC/qtbase/.git" ]; then
        say "init-repository --module-subset=qtbase"
        ( cd "$QT5_SRC" && ./init-repository --module-subset=qtbase )
    fi

    say "configure Qt5 for wasm-emscripten（照 static/README.wasm.md）"
    (
        cd "$QT5_SRC"
        # 注意：這裡刻意「不」加 -fwasm-exceptions，README 說明它跟
        # simulate_infinite_loop 衝突。
        ./configure \
            -opensource -confirm-license \
            -xplatform wasm-emscripten \
            -feature-thread \
            -prefix "$QT5_PREFIX" \
            -nomake tests -nomake examples \
            -no-pch -ccache \
            QMAKE_CFLAGS+=-sSUPPORT_LONGJMP=wasm \
            QMAKE_CXXFLAGS+=-sSUPPORT_LONGJMP=wasm
    ) 2>&1 | tee "$LITE_LOGDIR/qt5-configure.log"

    say "編譯 qtbase（約 60 分鐘，可以去做別的事）"
    ( cd "$QT5_SRC" && make -j"$LITE_JOBS" module-qtbase ) 2>&1 | tee "$LITE_LOGDIR/qt5-build.log"

    say "安裝到 $QT5_PREFIX"
    ( cd "$QT5_SRC" && make -j"$LITE_JOBS" install ) 2>&1 | tee "$LITE_LOGDIR/qt5-install.log"

    [ -x "$QT5_PREFIX/bin/qmake" ] || die "Qt5 安裝後找不到 qmake"
    [ -f "$QT5_PREFIX/plugins/platforms/libqwasm.a" ] \
        || warn "找不到 libqwasm.a，LO configure 會在 configure.ac:14135 報錯"
    ok "Qt5 wasm 就緒"
}

# ---------------------------------------------------------------------------
# submodules — 只要 translations
# ---------------------------------------------------------------------------
step_submodules() {
    say "init translations submodule（--with-lang=$LITE_LANGS 需要）"
    if [ -e "$LO_SRC/translations/.git" ]; then
        ok "已 init"; return 0
    fi
    ( cd "$LO_SRC" && git submodule update --init --depth 1 translations )
    [ -e "$LO_SRC/translations/.git" ] || die "translations submodule init 失敗"
    ok "完成"
    # dictionaries / helpcontent2 因為 --without-myspell-dicts / --without-help 而不需要
}

# ---------------------------------------------------------------------------
# fonts — 準備 CJK 字型
# ---------------------------------------------------------------------------
step_fonts() {
    mkdir -p "$LITE_EXTRA_FONTS_DIR"

    if compgen -G "$LITE_EXTRA_FONTS_DIR/*" >/dev/null 2>&1; then
        ok "已有字型：$(cd "$LITE_EXTRA_FONTS_DIR" && ls | tr '\n' ' ')"
        return 0
    fi

    # 1) 使用者指定
    if [ -n "$LITE_CJK_FONT_FILES" ]; then
        say "使用 LITE_CJK_FONT_FILES 指定的字型"
        local IFS=:
        for f in $LITE_CJK_FONT_FILES; do
            [ -f "$f" ] || die "找不到字型: $f"
            cp -v "$f" "$LITE_EXTRA_FONTS_DIR/"
        done
        return 0
    fi

    # 2) 系統既有
    local sys_font
    for sys_font in \
        /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc \
        /usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf \
        /usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc
    do
        if [ -f "$sys_font" ]; then
            say "採用系統字型 $sys_font ($(du -h "$sys_font" | cut -f1))"
            cp "$sys_font" "$LITE_EXTRA_FONTS_DIR/"
            warn "這是 TTC，含 JP/KR/SC/TC，會原封不動進 soffice.data。"
            warn "在乎首載大小的話，見 README.md 第 8 節的 pyftsubset 指令。"
            return 0
        fi
    done

    # 3) 下載 TC 專用（比 TTC 小一半）
    say "系統沒有 CJK 字型，下載 Noto Sans TC"
    have curl || die "需要 curl"
    local tmp; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' RETURN
    curl -fL --progress-bar -o "$tmp/tc.zip" "$NOTO_TC_URL" \
        || die "下載失敗。請手動準備字型後用 LITE_CJK_FONT_FILES 指定。"
    unzip -j -o "$tmp/tc.zip" '*Regular*' -d "$LITE_EXTRA_FONTS_DIR" >/dev/null \
        || die "解壓失敗"
    ok "$(cd "$LITE_EXTRA_FONTS_DIR" && ls | tr '\n' ' ')"
}

# ---------------------------------------------------------------------------
# patch / unpatch — fs image 的語言與字型
# ---------------------------------------------------------------------------
step_patch() {
    [ -f "$FS_IMAGE_MK" ] || die "找不到 $FS_IMAGE_MK"
    say "修改 static/CustomTarget_emscripten_fs_image.mk"
    MARKER="$PATCH_MARKER" python3 - "$FS_IMAGE_MK" <<'PYEOF'
import os, sys, pathlib

path   = pathlib.Path(sys.argv[1])
marker = os.environ["MARKER"]
text   = path.read_text()

if marker in text:
    print("   已套用過，跳過")
    sys.exit(0)

S = "$(INSTROOT)/$(LIBO_SHARE_FOLDER)"

# --- 1. 語言：把寫死的 en-US 換成 gb_Configuration_LANGS -------------------
# gb_Configuration_LANGS (solenv/gbuild/Configuration.mk:64) 就是
# postprocess/Package_registry.mk 拿來裝進 instdir 的同一個變數。
subs = [
    (f"    {S}/registry/Langpack-en-US.xcd \\\n",
     f"    $(foreach lang,$(gb_Configuration_LANGS),{S}/registry/Langpack-$(lang).xcd) \\\n"),
    (f"    {S}/registry/res/fcfg_langpack_en-US.xcd \\\n",
     f"    $(foreach lang,$(gb_Configuration_LANGS),{S}/registry/res/fcfg_langpack_$(lang).xcd) \\\n"),
    (f"    {S}/registry/res/registry_en-US.xcd \\\n",
     f"    $(foreach lang,$(gb_Configuration_LANGS),{S}/registry/res/registry_$(lang).xcd) \\\n"),
]
for old, new in subs:
    n = text.count(old)
    if n != 1:
        sys.exit(f"   !! 預期 1 處，實際 {n} 處，上游可能改過:\n      {old.strip()}")
    text = text.replace(old, new)

# --- 2. 額外字型：由 LITE_EXTRA_FONTS_DIR 驅動 -----------------------------
anchor = "#\n# Ruleset\n#\n"
if anchor not in text:
    sys.exit("   !! 找不到 Ruleset 錨點")

block = f"""{marker}
# 上游 external/more_fonts 一套 CJK 字型都沒有，而 WASM 的虛擬檔案系統
# 抓不到系統字型 —— 不塞進來的話繁中會整片豆腐字。
# LITE_EXTRA_FONTS_DIR 由 wasm-lite/build-wasm-lite.sh 匯出。
ifneq ($(LITE_EXTRA_FONTS_DIR),)
lite_extra_font_names := $(notdir \\
    $(wildcard $(LITE_EXTRA_FONTS_DIR)/*.ttf) \\
    $(wildcard $(LITE_EXTRA_FONTS_DIR)/*.ttc) \\
    $(wildcard $(LITE_EXTRA_FONTS_DIR)/*.otf) \\
    $(wildcard $(LITE_EXTRA_FONTS_DIR)/*.otc))

gb_emscripten_fs_image_files += $(foreach f,$(lite_extra_font_names),\\
    {S}/fonts/truetype/$(f))

define lite_extra_font_rule
{S}/fonts/truetype/$(1) : $(LITE_EXTRA_FONTS_DIR)/$(1)
\tmkdir -p $$(dir $$@) && cp -f $$< $$@
endef
$(foreach f,$(lite_extra_font_names),$(eval $(call lite_extra_font_rule,$(f))))
endif

{anchor}"""

text = text.replace(anchor, block, 1)
path.write_text(text)
print("   完成：語言 3 處 + 字型區塊 1 處")
PYEOF
    ok "已套用（還原：$0 unpatch）"
}

step_unpatch() {
    say "還原 fs image 修改"
    ( cd "$LO_SRC" && git checkout -- static/CustomTarget_emscripten_fs_image.mk )
    ok "已還原"
}

# ---------------------------------------------------------------------------
# LTO 探針 — 見 README 7.3 風險 A
# ---------------------------------------------------------------------------
# com_GCC_defs.mk:189 在 clang+LTO 時設 gb_LTOPLUGINFLAGS := --plugin LLVMgold.so，
# unxgcc.mk:211 拿去餵 $(gb_AR)。Emscripten 下 AR=emar（llvm-ar），未必吃這個
# 空格形式。這裡實測一次，不行就用命令列變數覆蓋（命令列優先於 makefile 賦值）。
LTO_MAKE_OVERRIDE=""
probe_lto_plugin() {
    [ "$LITE_LTO" = 1 ] || return 0
    say "探測 emar 是否接受 --plugin LLVMgold.so"
    local tmp; tmp=$(mktemp -d)
    echo 'int lite_probe(void){return 0;}' > "$tmp/p.c"
    if ! emcc -flto -c "$tmp/p.c" -o "$tmp/p.o" >/dev/null 2>&1; then
        rm -rf "$tmp"; warn "emcc -flto 都編不過，LTO 可能不可用"; return 0
    fi
    if emar --plugin LLVMgold.so -rsu "$tmp/p.a" "$tmp/p.o" >/dev/null 2>&1; then
        ok "接受，不需要覆蓋"
    else
        LTO_MAKE_OVERRIDE="gb_LTOPLUGINFLAGS="
        warn "不接受 → build 時會帶 gb_LTOPLUGINFLAGS= 覆蓋"
    fi
    rm -rf "$tmp"
}

# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------
build_configure_args() {
    CONF_ARGS=(
        # --- 平台骨幹（distro-configs/LibreOfficeWASM32.conf）---------------
        --host=wasm32-local-emscripten
        --disable-gen
        --disable-scripting
        --with-package-format=emscripten

        # --- 模組範圍：只要 Writer（預設是 'calc writer'）-------------------
        --with-wasm-module=writer

        # --- 語言 ----------------------------------------------------------
        "--with-lang=$LITE_LANGS"

        # --- 字型：上游沒有 --enable-noto-font，Noto 由 --with-fonts 帶入 ---
        --with-fonts

        # --- 體積 / 除錯 ---------------------------------------------------
        --enable-release-build
        --disable-debug
        --disable-dbgutil
        --disable-symbols            # 效益第一名
        --disable-sal-log
        --disable-assert-always-abort
        --disable-crashdump
        --disable-breakpad
        --disable-pch                # 非可選：configure.ac:6832 會 error

        # --- 拿掉用不到的 --------------------------------------------------
        --without-help
        --without-helppack-integration
        --without-myspell-dicts      # 字典本來就沒被打包進 soffice.data
        --without-java
        --without-doxygen
        --without-export-validation
        --disable-python
        --disable-cve-tests
        --disable-odk
        --disable-online-update
        --disable-firebird-sdbc
        --disable-postgresql-sdbc
        --with-theme=colibre

        # --- 建置速度 ------------------------------------------------------
        --enable-ccache
        --with-build-platform-configure-options=--enable-ccache
    )

    [ "$LITE_LTO" = 1 ] && CONF_ARGS+=(--enable-lto)

    if [ "$LITE_QT" = 5 ]; then
        CONF_ARGS+=(--enable-qt5)
    else
        CONF_ARGS+=(--enable-qt6)
    fi
}

step_configure() {
    load_emsdk

    if [ "$LITE_QT" = 5 ]; then
        [ -x "$QT5_PREFIX/bin/qmake" ] || die "Qt5 未就緒，先跑: $0 qt5"
        export QT5DIR="$QT5_PREFIX"
    else
        [ -n "${QT6DIR:-}" ] || die "LITE_QT=6 需要 QT6DIR"
    fi

    grep -qF "$PATCH_MARKER" "$FS_IMAGE_MK" \
        || warn "fs image 尚未 patch，zh-TW 與 CJK 字型不會進 soffice.data（$0 patch）"

    mkdir -p "$LITE_BUILDDIR" "$LITE_LOGDIR"
    build_configure_args

    say "configure（out-of-tree: $LITE_BUILDDIR）"
    printf '     %s\n' "${CONF_ARGS[@]}"

    # 留一份給人看 / 給 autogen.lastrun 比對
    printf '%s\n' "${CONF_ARGS[@]}" > "$LITE_BUILDDIR/lite-configure-args.txt"

    ( cd "$LITE_BUILDDIR" && "$LO_SRC/autogen.sh" "${CONF_ARGS[@]}" ) \
        2>&1 | tee "$LITE_LOGDIR/configure.log"

    [ -f "$LITE_BUILDDIR/config_host.mk" ] || die "configure 沒有產出 config_host.mk"

    write_env_file
    ok "configure 完成 → $LITE_BUILDDIR"
}

# 之後手動下 make 時可以 source 這支
write_env_file() {
    cat > "$LITE_BUILDDIR/lite-env.sh" <<EOF
# 由 build-wasm-lite.sh 產生。手動 make 前先 source 這支。
source "$EMSDK_DIR/emsdk_env.sh" >/dev/null 2>&1
export QT5DIR="$QT5_PREFIX"
# fs image 的額外字型規則靠這個變數，沒 export 的話字型會靜默消失
export LITE_EXTRA_FONTS_DIR="$LITE_EXTRA_FONTS_DIR"
cd "$LITE_BUILDDIR"
EOF
    ok "環境檔：$LITE_BUILDDIR/lite-env.sh"
}

# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
step_build() {
    [ -f "$LITE_BUILDDIR/config_host.mk" ] || die "尚未 configure，先跑: $0 configure"
    load_emsdk
    export QT5DIR="$QT5_PREFIX"
    export LITE_EXTRA_FONTS_DIR

    probe_lto_plugin
    mkdir -p "$LITE_LOGDIR"

    local make_args=(-j"$LITE_JOBS")
    [ -n "$LTO_MAKE_OVERRIDE" ] && make_args+=("$LTO_MAKE_OVERRIDE")

    say "make ${make_args[*]}"
    printf '     LTO=%s  字型=%s\n' "$LITE_LTO" "$LITE_EXTRA_FONTS_DIR"
    warn "這一步要 4-8 小時。最後 link soffice.wasm 是單執行緒且極吃記憶體。"

    local t0=$SECONDS
    ( cd "$LITE_BUILDDIR" && make "${make_args[@]}" ) 2>&1 | tee "$LITE_LOGDIR/build.log"
    ok "build 完成，耗時 $(( (SECONDS - t0) / 60 )) 分鐘"

    step_report
}

# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
step_report() {
    local out="$LITE_BUILDDIR/workdir/installation/LibreOffice/emscripten"
    [ -d "$out" ] || { warn "找不到 $out"; return 0; }

    say "產出：$out"
    ( cd "$out" && ls -lhS | tail -n +2 | awk '{printf "     %-34s %s\n", $9, $5}' )

    echo
    say "gzip 後（瀏覽器實際下載量的近似）"
    local f sz
    for f in soffice.wasm soffice.data soffice.js; do
        [ -f "$out/$f" ] || continue
        sz=$(gzip -c "$out/$f" 2>/dev/null | wc -c)
        printf '     %-34s %s\n' "$f" "$(numfmt --to=iec "$sz" 2>/dev/null || echo "$sz")"
    done

    echo
    say "驗證語言與字型是否真的進了 soffice.data"
    local meta="$out/soffice.data.js.metadata"
    if [ -f "$meta" ]; then
        local lang
        for lang in $LITE_LANGS; do
            if grep -q "Langpack-$lang.xcd" "$meta"; then
                ok "$lang 語言包"
            else
                warn "$lang 語言包不在 soffice.data（fs image 沒 patch？）"
            fi
        done
        if grep -qiE 'NotoSans(CJK|TC)|CJK' "$meta"; then
            ok "CJK 字型"
        else
            warn "沒有 CJK 字型 → 繁中會是豆腐字（$0 fonts && $0 patch 後重編）"
        fi
    else
        warn "找不到 $meta"
    fi
}

# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------
step_serve() {
    local out="$LITE_BUILDDIR/workdir/installation/LibreOffice/emscripten"
    [ -f "$out/qt_soffice.html" ] || die "找不到 $out/qt_soffice.html"
    load_emsdk
    say "emrun http://127.0.0.1:6931/qt_soffice.html"
    warn "務必開「新分頁」測試 —— 重新整理會拿到快取的舊版本。"
    emrun --hostname 127.0.0.1 --port 6931 --serve_after_close "$out/qt_soffice.html"
}

# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------
step_clean() {
    warn "即將刪除 $LITE_BUILDDIR（emsdk / Qt5 / 字型會保留）"
    read -r -p "確定？[y/N] " a
    [ "${a:-n}" = y ] || { say "取消"; return 0; }
    rm -rf "$LITE_BUILDDIR"
    ok "已刪除"
}

# ---------------------------------------------------------------------------
# all
# ---------------------------------------------------------------------------
step_all() {
    step_emsdk
    step_qt5
    step_submodules
    step_fonts
    step_patch
    step_configure
    step_build
}

# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
build-wasm-lite.sh — LibreOffice 26.8 → Writer-only WASM lite core

  doctor       檢查環境（不改任何東西）
  emsdk        安裝 Emscripten $EMSDK_VERSION
  qt5          建置 Qt 5.15.2+wasm（allotropia fork，約 60 分鐘）
  submodules   init translations submodule
  fonts        準備 CJK 字型（不做的話繁中是豆腐字）
  patch        修改 fs image：語言 + 額外字型
  unpatch      還原上述修改
  configure    LO configure（out-of-tree）
  build        make（4-8 小時）
  report       印出產出大小並驗證語言/字型有進 soffice.data
  serve        emrun 起本機伺服器
  clean        刪掉建置目錄
  all          emsdk → qt5 → submodules → fonts → patch → configure → build

環境變數:
  LO_SRC=$LO_SRC
  LITE_BUILDDIR=$LITE_BUILDDIR
  LITE_LANGS="$LITE_LANGS"
  LITE_LTO=$LITE_LTO      LITE_JOBS=$LITE_JOBS      LITE_QT=$LITE_QT
  LITE_CJK_FONT_FILES     冒號分隔的字型路徑，留空則自動偵測/下載

規劃與理由：$LITE_ROOT/README.md
EOF
}

case "${1:-}" in
    doctor)     step_doctor ;;
    emsdk)      step_emsdk ;;
    qt5)        step_qt5 ;;
    submodules) step_submodules ;;
    fonts)      step_fonts ;;
    patch)      step_patch ;;
    unpatch)    step_unpatch ;;
    configure)  step_configure ;;
    build)      step_build ;;
    report)     step_report ;;
    serve)      step_serve ;;
    clean)      step_clean ;;
    all)        step_all ;;
    ""|-h|--help|help) usage ;;
    *)          die "未知步驟: $1（$0 --help）" ;;
esac
