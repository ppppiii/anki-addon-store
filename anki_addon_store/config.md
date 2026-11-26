# 插件市场配置 · Anki Add-on Store Config

- `language`: `"auto"`（跟随 Anki 界面语言）/ `"zh"` / `"en"`
- `catalog_url`: 可选的 GitHub 静态索引地址（如 `https://raw.githubusercontent.com/<user>/anki-addon-store/main/data/catalog.json.gz`）；留空则直接拉取 AnkiWeb 实时索引并缓存
- `cache_ttl_hours`: 本地索引缓存有效小时数（默认 `12`）
