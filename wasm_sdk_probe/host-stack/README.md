# host-stack

這個專案自己的測試宿主，不依賴 ddev。規格：`specs/SPEC-M3-own-stack.md`。

    docker compose --env-file rehearsal.env up -d      # 或 stop

`bin/ddev` 不是 ddev：只給被證據綁住、不能改的工具用，放在 PATH 最前面。`certs/` 不進版控，用 `mkcert` 產生。
