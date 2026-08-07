# Skills

可重複使用的工作方法，從實作中萃取出來的。

真正的檔案放在這裡，`.claude/skills/` 底下是 symlink：

```
Skills/upstream-findings/SKILL.md          ← 真檔案
.claude/skills/upstream-findings  ->  ../../Skills/upstream-findings
```

這樣做的理由：skill 是**專案的產出**，不是工具的設定檔。放在可見的位置才會被讀、被改、被納入版控，而不是埋在 dot-directory 裡慢慢腐爛。

symlink 用**相對路徑**，所以整個 workspace 搬走或被 clone 到別處都還能用。

## 目前有什麼

| skill | 什麼時候會用到 |
|---|---|
| [`upstream-findings`](upstream-findings/SKILL.md) | 在別人的專案裡發現 bug，要記下來之後回報 |
| [`build-variable-bisect`](build-variable-bisect/SKILL.md) | 編一次要幾小時，要找出是哪個建置選項造成行為差異 |
| [`emscripten-app-debug`](emscripten-app-debug/SKILL.md) | WASM app 在瀏覽器裡壞掉，要抓 console、要免重編驗證假設 |

三個都在這裡，`.claude/skills/` 底下沒有實體目錄。這樣換別套 agent 工具時，只要在對方的設定位置再拉一次 symlink 就好，內容不用搬。

## 新增一個

```bash
mkdir -p Skills/<name>
$EDITOR Skills/<name>/SKILL.md          # 需要 YAML frontmatter：name、description
ln -s ../../Skills/<name> .claude/skills/<name>
```

`description` 要寫**什麼時候該用**，不只是寫它做什麼 —— 那段文字是判斷要不要載入的唯一依據。

## 什麼該寫成 skill

**方法可以，結論不行。**

結論會過期。把「Qt5 目前不支援 X」寫進 skill，半年後你會拿到一份看起來權威但已經不成立的說法，比沒有更糟。那種東西屬於 DEVLOG 或分析文件。

skill 適合放：不寫下來就會忘記或在趕時間時被跳過的做法。

## 搬到全域？

這兩個都不綁特定專案，理論上可以放 `~/.claude/skills/`。目前刻意留在專案內 —— 先在真實使用中磨過幾輪再說。要搬的時候，把目錄複製過去、或把 symlink 改指到這裡都行。
