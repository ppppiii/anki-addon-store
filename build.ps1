# 打包成 .ankiaddon（zip 压缩包，根目录直接放 __init__.py / manifest.json，不含 meta.json 与 user_files）
$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'anki_addon_store'
$dist = Join-Path $PSScriptRoot 'dist'
$outDefault = Join-Path $dist 'anki_addon_store.ankiaddon'

if (-not (Test-Path $source)) { throw "找不到插件源目录: $source" }
New-Item -ItemType Directory -Force -Path $dist | Out-Null

python -c @"
import os, zipfile

source = r'$source'
out_default = r'$outDefault'
exclude_dirs = {'__pycache__', 'user_files', '.git'}
exclude_files = {'meta.json'}

if os.path.exists(out_default):
    os.remove(out_default)
written = 0
with zipfile.ZipFile(out_default, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if d not in exclude_dirs)
        for name in sorted(files):
            if name in exclude_files or name.endswith(('.pyc', '.pyo')):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, source).replace(os.sep, '/')
            zf.write(full, rel)
            written += 1
print(f'已生成 {out_default} ({os.path.getsize(out_default) / 1024:.1f} KB, {written} 个文件)')
"@
if ($LASTEXITCODE -ne 0) { throw "打包 .ankiaddon 失败" }
