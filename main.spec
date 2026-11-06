# -*- coding: utf-8 -*-
# =============================================================
# HandsFree 打包配置（Windows / Linux 通用）
# 打包命令：pyinstaller main.spec --clean
#
# 基线版本：不做任何二进制/资源裁剪（之前按文件名删插件的逻辑
# 在 Linux 上误删了 libqxcb.so 平台插件导致静默无法启动，已回退）
#   - 单文件、无控制台，产物名 HandsFree
#   - UPX 自动探测：找不到时自动降级为不压缩
#   - pynput 的平台后端为延迟导入，需显式 hiddenimports
# =============================================================
import glob
import os
import sys
import shutil

APP_NAME = 'HandsFree'
IS_WIN = sys.platform == 'win32'


# ---------- UPX 自动探测 ----------
def _find_upx():
    """返回 upx 所在目录，找不到返回 None"""
    found = shutil.which('upx')
    if found:
        return os.path.dirname(found)
    d = os.environ.get('UPX_DIR')
    if d:
        cand = os.path.join(d, 'upx.exe' if IS_WIN else 'upx')
        if os.path.isfile(cand):
            return d
    if IS_WIN:
        for pattern in (r'C:\Program Files\upx*',
                        r'D:\Program Files\upx*',
                        r'C:\tools\upx*'):
            for d in glob.glob(pattern):
                if os.path.isfile(os.path.join(d, 'upx.exe')):
                    return d
    return None


UPX_DIR = _find_upx()
if UPX_DIR:
    os.environ['PATH'] = UPX_DIR + os.pathsep + os.environ.get('PATH', '')
    print('[spec] UPX: %s' % UPX_DIR)
else:
    print('[spec] 警告: 未找到 UPX，本次打包不压缩')

# Linux 上对 .so 做 strip
USE_STRIP = (not IS_WIN) and shutil.which('strip') is not None

# ---------- 延迟导入的平台后端 ----------
hiddenimports = ['pyperclip', 'pynput', 'pynput.keyboard', 'pynput.mouse']
if IS_WIN:
    hiddenimports += ['pynput.keyboard._win32', 'pynput.mouse._win32']
else:
    hiddenimports += ['pynput.keyboard._x11', 'pynput.mouse._x11']

# ---------- 可选图标 ----------
ICON = os.path.join(SPECPATH, 'app.ico') if IS_WIN else None
if ICON and not os.path.isfile(ICON):
    ICON = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=USE_STRIP,
    upx=UPX_DIR is not None,
    upx_exclude=['vcruntime140.dll', 'vcruntime140_1.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
