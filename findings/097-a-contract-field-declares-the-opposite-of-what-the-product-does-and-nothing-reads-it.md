# 097 — 契約欄位宣告了一件與實測相反的事，而產品路徑上沒有人讀它

**狀態**：靜態確認 ＋ 由 096 的量測反證。
**來源**：追查 finding 096 的修法該住在哪一層時掉出來的
（`handoff/DECISION-2026-09-09-which-layer-can-carry-096s-fix-and-what-each-costs.md`）。

## 宣稱

`boundaryRejectionRequiresFreshWorker` 這個欄位：

1. **硬寫成 `True`**，不是量出來的（`tools/build_e2_b_profile.py:155`，
   以及 `build_finding_016_selection_barrier_profile.py:67`、
   `build_e2_discovery_profile.py:210`）。
2. **產品路徑上沒有任何東西讀它。**唯二的讀者是
   `web/e1-discovery-app.js:362` 與 `web/finding-016-selection-barrier-app.js:445`，
   而且它們讀的是 `manifest.diagnostic.*`——那個子物件
   在寫出契約之前就被 `build_e2_b_profile.py:138` 給 pop 掉了。
3. **實測行為與宣告相反。**096 的量測（四臂 40/40）顯示：撞到邊界之後
   **不需要**換一個新的 worker，session 就是死的——`recoverable-error`、
   `rescue: none`，而且 worker 的 JS 執行緒還活著、0.0 秒答得出 CDP。
   換言之這個欄位宣告的補救動作既沒有人執行，實測也不成立。

## 為什麼這是一張單，而不是一行清理

這棵樹在 2026-08-22 為同一個形狀付過錢，而且記在 `AGENTS.md` 裡：
**「manifest 說給了，引擎無條件拒絕」**——當時是 `kMaxInternalEditorAction`
的界限沒跟著清單走。這裡是同一個方向的反面：**契約說「補救需要 X」，
而沒有人做 X，實測也不需要 X 才會壞。**

第 1 節的判別法（動態）：**往真值源塞一個虛構的新成員，看哪個檢查轉紅。**
把這個欄位改成 `False`、或整個刪掉，**零個產品路徑上的檢查會紅**——
而契約已經說了一件假的事。這是手工枚舉的那一種。

## 不是什麼

- **不是 096 的成因**，也不是它的修法。096 的成因未定（三個解釋還在）。
- **不主張刪掉它**。宣告一件真的事、並且有人執行，跟刪掉它，是兩個不同的處置，
  而選哪一個要等 096 的成因定了才知道——那個欄位有可能本來就是要描述
  一個真實的補救路徑，只是從來沒有接上。

## 未做

- 沒有清點**還有哪些**契約欄位是硬寫的、沒有人讀的。只查了這一個。
  **這一節是「沒查」，不是「查了沒有」。**
- 沒有查 `manifest.diagnostic` 這個子物件在什麼時候、為什麼被 pop 掉。
