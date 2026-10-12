# 由 build-wasm-lite.sh 產生。手動 make 前先 source 這支。
source "/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/tools/emsdk/emsdk_env.sh" >/dev/null 2>&1
export QT5DIR="/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/tools/qt5-wasm"
# fs image 的額外字型規則靠這個變數，沒 export 的話字型會靜默消失
export LITE_EXTRA_FONTS_DIR="/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/tools/extra-fonts"
cd "/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/build"
