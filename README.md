# 🛒 Anki Add-on Store (插件市场)

An open-source, native Anki add-on providing an in-app community add-on marketplace — browse all AnkiWeb add-ons by category, check compatibility & maintenance activity, read reviews, and install, toggle, update, or uninstall directly inside Anki.

- **AnkiWeb Add-on Code**: `2006528466` ([AnkiWeb Page](https://ankiweb.net/shared/info/2006528466))
- **GitHub Repository**: [ppppiii/anki-addon-store](https://github.com/ppppiii/anki-addon-store)

[中文说明](#中文说明)

## Features

- **In-App Store UI (`AnkiWebView`)**: Category sidebar, instant search, compatibility & 1-year activity filters, sorting (Popular / Rating % / Recently Updated / Name, Asc/Desc), and slide-over detail drawer with adaptive Light/Dark theme.
- **Hybrid Index (Zero Server Cost)**: Uses a daily GitHub Actions static index (`data/catalog.json.gz`), bundled seed snapshot (`seed_catalog.json.gz`), and automatic fallback to AnkiWeb's `/svc/shared/list-addons` endpoint + local disk cache.
- **In-Drawer Reviews**: Scroll inside the detail drawer to read AnkiWeb user reviews and developer replies (filterable by Up/Down), with a 1-click shortcut to write reviews on AnkiWeb.
- **Safe Native Management**: Installs strictly via Anki's built-in `aqt.addons.download_addons`, plus Enable/Disable, Uninstall, and Check Updates.
- **Bilingual UI (English / 中文)**: Automatically follows Anki's UI language with live switching under `Tools → Add-on Store → Language`.

## Development, Build & Test

- **Run offline unit tests**:
  ```powershell
  python -m unittest discover -s tests -v
  ```
- **Build `.ankiaddon`**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\build.ps1
  ```
- **Install locally (`addons21`)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install.ps1
  ```

---

## 中文说明

开源、纯原生 Anki 插件市场（AnkiWeb 安装代码 **`2006528466`**）：在 Anki 内按分类逛全量 AnkiWeb 插件、自动识别当前 Anki 版本兼容性与近 1 年维护活跃度、直接浏览真实用户评论与作者回复，并支持原生一键安装 / 启停 / 卸载 / 检查更新。

- **插件入口**：Anki 菜单栏 `工具 → 插件市场 → 打开插件市场...`
- **双语切换**：默认跟随 Anki 语言，可在 `工具 → 插件市场 → 语言 / Language` 即时切换。
- **社区贡献**：欢迎通过 PR 补充 [curated_overrides.json](anki_addon_store/core/curated_overrides.json) 中的中文简介与精准分类。
