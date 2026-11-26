# 将 anki_addon_store 同步安装到 Anki addons21 目录（保留 meta.json 与 user_files\）
param(
    [string]$AddonsPath = (Join-Path $env:APPDATA 'Anki2\addons21')
)

$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'anki_addon_store'
if (-not (Test-Path $source)) { throw "找不到插件源目录: $source" }
if (-not (Test-Path $AddonsPath)) { throw "找不到 Anki addons21 目录: $AddonsPath" }

$target = Join-Path $AddonsPath 'anki_addon_store'
$resolvedAddons = (Resolve-Path $AddonsPath).Path
$resolvedTarget = [System.IO.Path]::GetFullPath($target)
if (-not $resolvedTarget.StartsWith($resolvedAddons, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "拒绝写入 addons21 之外的路径: $resolvedTarget"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $target 'core') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $target 'ui') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $target 'ui\web') | Out-Null

$files = @(
    '__init__.py',
    'manifest.json',
    'config.json',
    'config.md',
    'addon_bridge.py',
    'core\__init__.py',
    'core\ankiweb_proto.py',
    'core\catalog.py',
    'core\classifier.py',
    'core\curated_overrides.json',
    'core\i18n.py',
    'core\seed_catalog.json.gz',
    'ui\__init__.py',
    'ui\store_dialog.py',
    'ui\web\store.html',
    'ui\web\store.css',
    'ui\web\store.js'
)

foreach ($rel in $files) {
    $src = Join-Path $source $rel
    $dst = Join-Path $target $rel
    Copy-Item -Path $src -Destination $dst -Force
}

Write-Host "已同步 $($files.Count) 个文件到 $target（meta.json 与 user_files\ 已保留）"
Write-Host "请重启 Anki 生效。"
