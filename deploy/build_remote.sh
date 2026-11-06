#!/usr/bin/env bash
# =============================================================
# HandsFree 服务器端打包脚本
# 由本地 deploy.ps1 通过 ssh 调用，调用前代码已解压到当前目录
# 说明: 虚拟环境持久保存在 ~/handsfree-venv，不会每次重建；
#       requirements.txt 未变化时跳过依赖安装
# =============================================================
set -e

VENV_DIR="$HOME/handsfree-venv"

# 优先使用较新的 Python（>=3.8），没有则回退 python3
PY=python3
for v in 3.12 3.11 3.10 3.9 3.8; do
    if command -v "python$v" >/dev/null 2>&1; then
        PY="python$v"
        break
    fi
done
echo "==> 使用解释器: $PY ($($PY --version 2>&1))"

# 虚拟环境持久保存，只在首次创建
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "==> 首次运行，创建虚拟环境 $VENV_DIR ..."
    "$PY" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Python 3.7 及以下不支持 PyInstaller 6.x，自动降级
PYVER=$("$VENV_DIR/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "==> 虚拟环境 Python: $PYVER"
case "$PYVER" in
    3.[0-7]|2.*) PI_SPECIFIER="pyinstaller<6" ;;
    *)           PI_SPECIFIER="pyinstaller" ;;
esac

# 依赖未变化时跳过安装（秒级），变化时才重装
REQ_MD5=$(md5sum requirements.txt | cut -d' ' -f1)
if [ -f "$VENV_DIR/.requirements.md5" ] && [ "$(cat "$VENV_DIR/.requirements.md5")" = "$REQ_MD5" ]; then
    echo "==> 依赖无变化，跳过安装"
else
    echo "==> 安装依赖..."
    pip install -q -r requirements.txt "$PI_SPECIFIER"
    echo "$REQ_MD5" > "$VENV_DIR/.requirements.md5"
fi

echo "==> PyInstaller 打包..."
pyinstaller main.spec --clean

echo "==> 打包完成: $(pwd)/dist/HandsFree"
