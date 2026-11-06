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
    pip install -q -r requirements.txt
    # Python 3.7 与 requirements 中的 pyinstaller>=6.0.0 冲突，单独降级安装
    if [ "$PI_SPECIFIER" = "pyinstaller<6" ]; then
        pip install -q "pyinstaller<6"
    fi
    echo "$REQ_MD5" > "$VENV_DIR/.requirements.md5"
fi

echo "==> 清理旧的 build/dist 及 PyInstaller 缓存 ..."
# 可能残留其他用户（如 root）打包产生的文件，普通 rm 失败时用 sudo
rm -rf build dist "$HOME/.cache/pyinstaller" 2>/dev/null \
    || sudo rm -rf build dist "$HOME/.cache/pyinstaller"

echo "==> PyInstaller 打包..."
# PyInstaller 官方在非 Windows 平台默认禁用 UPX（configure.py：已知兼容问题名单），
# 不开此开关 Linux 产物只有 zlib 压缩、体积大一半。
# 风险：UPX 压缩 .so 后在个别发行版上可能 dlopen 段错误；
#       若打包产物在目标机器运行异常，删除下面这行重新打包即可回退。
# export PYINSTALLER_FORCE_UPX=1
pyinstaller main.spec --clean

echo "==> 打包完成: $(pwd)/dist/HandsFree"
