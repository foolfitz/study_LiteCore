# 003 — UnpackedTarball.mk：.version 目標缺少 .dir 的 order-only 相依，-j 下會 race

| | |
|---|---|
| **狀態** | 可送出（而且可以直接附 patch） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-07-31 |
| **嚴重度** | 一般（偶發，但會讓全新 build 目錄的第一次 make 直接失敗） |
| **可重現** | 全新 build 目錄 + `-j12`：**3 次中 2 次**（見下方觀測紀錄） |
| **是否上游** | **是** —— 純 gbuild 問題，與平台、與 configure 旗標都無關 |

## 現象

在**全新的** build 目錄跑 `make -j12`，隨機在某個外部套件上失敗：

```
/bin/sh: 1: cannot create .../workdir_for_build/UnpackedTarball/dragonbox.version: Directory nonexistent
make[1]: *** [solenv/gbuild/UnpackedTarball.mk:170: .../dragonbox.version] Error 2
```

### 觀測紀錄（同一台機器、同一份原始碼、`make -j12`）

| build 目錄 | 組態 | 是否中 | 卡住的套件 |
|---|---|---|---|
| `build/`（lite） | 32 旗標 | 否 | — |
| `build-stock/` | distro + symbols | **是** | dragonbox |
| `build-t1/` | + wasm-module=writer | 否 | — |
| `build-t2/` | + release-build | **是** | dragonbox |

兩次都停在 dragonbox，推測跟 gbuild 列舉外部套件的順序有關（dragonbox 排在很前面，最容易搶在 `.dir` 之前跑）。但它不是唯一可能的受害者 —— 排程一變就可能換成別的套件。

**直接重跑 `make` 就會過** —— 失敗的那一步已經把目錄建出來了。所以這是 race，不是設定錯誤。

## 重現步驟

1. 全新的 build 目錄（`workdir_for_build/UnpackedTarball/` 尚不存在）
2. `make -j$(nproc)`（核心數越多越容易中）

**預期**：正常建置
**實際**：偶發 `Directory nonexistent`

## 證據

- `evidence/003/make-error.txt` — 原始錯誤
- `evidence/003/makefile-excerpt.txt` — 相關 makefile 片段

## 分析

**根因完全確定。**

`solenv/gbuild/UnpackedTarball.mk` 有三個相關目標，只有兩個掛了建目錄的 order-only 相依：

```make
# 212
$(call gb_UnpackedTarball_get_preparation_target,$(1)) :| $(dir ...).dir    ✅
# 213
$(call gb_UnpackedTarball_get_target,$(1))             :| $(dir ...).dir    ✅

# 169 — 只有 PHONY
$(call gb_UnpackedTarball_get_version_target,%) : $(gb_Helper_PHONY)        ❌
	$(if $(and $(wildcard $@),$(filter $(UNPACKED_TARBALL),$(file < $@))),,\
		printf $(UNPACKED_TARBALL) > $@)
```

而 210–211 行讓 `.prepare` **相依於** `.version`：

```make
$(call gb_UnpackedTarball_get_preparation_target,$(1)) : $(gb_Module_CURRENTMAKEFILE) \
	$(call gb_UnpackedTarball_get_version_target,$(1))
```

GNU make 對「普通相依」與「order-only 相依」之間**不保證先後**。所以在 `-j` 下，`.version` 的 `printf ... > $@` 可能排在 `.prepare` 的 `.dir` 之前執行。目錄還沒建，shell 重導向就失敗。

平常跑得過，是因為 `UnpackedTarball/` 通常已經被別的目標先建出來了。全新 build 目錄的第一次 make 才會暴露。

### 建議修法

```diff
--- a/solenv/gbuild/UnpackedTarball.mk
+++ b/solenv/gbuild/UnpackedTarball.mk
@@ -166,7 +166,8 @@
 $(dir $(call gb_UnpackedTarball_get_target,%)).dir :
 	$(if $(wildcard $(dir $@)),,mkdir -p $(dir $@))
 
-$(call gb_UnpackedTarball_get_version_target,%) : $(gb_Helper_PHONY)
+$(call gb_UnpackedTarball_get_version_target,%) : $(gb_Helper_PHONY) \
+	| $(dir $(call gb_UnpackedTarball_get_target,%)).dir
 	$(if $(and $(wildcard $@),$(filter $(UNPACKED_TARBALL),$(file < $@))),,\
 		printf $(UNPACKED_TARBALL) > $@)
```

`$(dir $(call gb_UnpackedTarball_get_target,%))` 這個寫法在 166 行本來就用來當 target pattern，所以形式一致。

**待上游確認**：`%` 含斜線時 `$(dir ...)` 的展開是否仍正確。這點我沒有把握，回報時要寫明。

## 環境

```
LibreOffice   26.8.0.1.0+   libreoffice-26-8 @ 671c848b1bb8
OS            Ubuntu 26.04 LTS / kernel 7.0.0-28-generic / x86_64
make          -j12
shell         /bin/sh → dash
configure     --with-distro=LibreOfficeWASM32 --enable-symbols --enable-ccache
```

雖然是在 WASM cross build 上撞到（`workdir_for_build` 是 cross build 專屬的 build-side workdir），但問題本身與平台無關 —— 任何全新 build 目錄都可能中。

## 還缺什麼才能送

- [ ] 搜尋 Bugzilla 是否已有重複（關鍵字：`UnpackedTarball` `Directory nonexistent` `.version`）
- [ ] 決定是只報 bug，還是直接送 gerrit patch
- [ ] 若送 patch：`./logerrit setup` + commit message

## 為什麼這張適合當第一次 gerrit 提交

- 根因確定，不需要臆測
- 修法一行，審查者幾秒就能判斷對錯
- 不需要懂 LibreOffice 的業務邏輯，只要懂 make
- 有明確的失敗訊息可以搜尋，容易證明不是自己環境的問題

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | Build tooling |
| Version | 26.8.0.1 rc |
| Hardware / OS | All / All |
| Summary | gbuild: UnpackedTarball .version target lacks order-only dep on .dir, racing under -j |

## 時間軸

- 2026-07-31 stock build 首次 make 失敗，追到 UnpackedTarball.mk
- 2026-07-31 build-t1 未重現
- 2026-07-31 build-t2 再次重現（同樣停在 dragonbox）→ 確認為 race 而非一次性事故
- 2026-08-01 `build-headless-probe` 全新目錄首次 `make -j12` 再次停在
  `dragonbox.version`；父目錄建立後直接重跑即正常越過（見
  `evidence/003/make-error-headless-probe.txt`）
