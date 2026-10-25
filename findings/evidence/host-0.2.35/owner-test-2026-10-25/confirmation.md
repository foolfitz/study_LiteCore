# Owner manual observations and next request

The owner reported the following after the 0.2.35 repaint correction and source analysis:

> 人工測試完成，
> - B／I／U 整格套用 => 測試通過
> - 雙擊：保留原內容，進入文字編輯 => 測試通過
> - 選格後直接打字，F2 進入文字編輯 => 沒反應
>
> 然後我希望加上「區域選取」的功能
> 我們context很長了，請幫我寫交接文件

Explicit passes: whole-cell B/I/U and double-click preserving existing content and entering editing. Preserve these observations; do not ask for them again. The earlier text/formula input pass also remains accepted.

Direct typing into the selected grid cell and F2 are not implemented in this candidate. The owner observation is consistent with the current source: viewport has click/dblclick handlers and global save/format shortcuts, but no grid printable-input or F2 route. This is an outstanding expected behavior, not evidence that a previously shipped implementation regressed. The earlier report described Collabora's behavior; it did not implement it in LiteCore. Multi-cell range selection is a new requested feature and is not implemented. It is not textarea character selection or partial rich text.

Identity scope: this observation follows the installed 0.2.35 / host 858a07c / package b007f950b2e18cd2 context. This handoff turn freshly read the clean host checkout and local manifest, matching release.json. The owner did not repeat the tested browser/version, served URL or package identity; none is invented. No browser/container/service/build operation or new acceptance run occurred in this handoff-only turn. This manual report does not advance full K or the nominal shipped version.
