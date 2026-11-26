# DESIGN.md · anki-addon-store 架构设计

## 1. 模块分层

- **`anki_addon_store/core/`（纯 Python，严禁导入 `aqt`/`anki`/`PyQt*`）**：
  - `ankiweb_proto.py`：最小 protobuf wire 解码器（解码 `/svc/shared/list-addons` 与 `/svc/shared/item-info`）、HTML XSS 清洗、GitHub 链接提取、版本号解析（兼容 `2.1.x` 与 `YY.MM.p`）及兼容性/活跃度判定。
  - `classifier.py` + `curated_overrides.json`：10 大业务分类关键词打分器 + 精选人工双语摘要覆盖表。
  - `catalog.py`：混合目录加载器（`cache` → 可选静态 `catalog_url` → AnkiWeb 实时 protobuf 回退 → 过期缓存兜底）与多维筛选排序。
  - `i18n.py`：中英双语词库与前端 JSON 包导出。
- **`anki_addon_store/addon_bridge.py`（Anki AddonManager 适配层）**：
  - 封装 `allAddons`、`isEnabled`、`download_addons`、`toggleEnabled`、`deleteAddon`、`check_and_install_addon_updates` 与单条详情异步拉取缓存。
- **`anki_addon_store/ui/`（`AnkiWebView` 商店界面）**：
  - `store_dialog.py`：宿主 `QDialog`，通过 `stdHtml(..., default_css=False)` + `set_bridge_command` + `mw.taskman.run_in_background` 异步驱动前端。
  - `web/store.html` / `store.css` / `store.js`：左侧分类导航、顶部搜索筛选栏、分页卡片网格与右侧滑出详情抽屉（自适应 `night-mode`）。
- **GitHub 开源基建**：
  - `scripts/build_catalog.py` + `.github/workflows/update-catalog.yml`：每日生成静态 `data/catalog.json.gz`。

## 2. 安全边界

1. **安装只走官方通道**：所有一键安装一律通过 `aqt.addons.download_addons` 下载 AnkiWeb 官方包，绝不直接下载执行未审核第三方代码。
2. **HTML 净洗与外链隔离**：AnkiWeb 插件详情 HTML 经 `sanitize_html` 剥离 `<script>`/`<iframe>`/`on*=`/`javascript:`；外链通过 `openLink` 交由系统浏览器打开。
3. **无服务器冷启动依赖**：不自建评价后端；聚合 AnkiWeb 原生赞踩、版本兼容性、维护活跃度与 GitHub 主页入口，同时提供本地磁盘缓存避免高频请求 AnkiWeb。
