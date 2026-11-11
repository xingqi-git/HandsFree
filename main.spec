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
hiddenimports = ['pyperclip']
if IS_WIN:
    # Windows 热键用 ctypes，但保留 pynput 以防其他引用
    hiddenimports += ['pynput', 'pynput.keyboard', 'pynput.mouse',
                      'pynput.keyboard._win32', 'pynput.mouse._win32']
else:
    # Linux 全局热键改用 python-xlib 的 XGrabKey（不再用 pynput/XRecord，
    # 后者在统信上 XRecordEnableContext 段错误）。显式列出 Xlib 子模块。
    hiddenimports += [
        'Xlib', 'Xlib.display', 'Xlib.X', 'Xlib.XK', 'Xlib.keysymdef',
        'Xlib.protocol.event', 'Xlib.ext', 'Xlib.support',
        'Xlib.xobject', 'Xlib.xobject.drawable',
    ]

# ---------- 可选图标 ----------
ICON = os.path.join(SPECPATH, 'app.ico') if IS_WIN else None
if ICON and not os.path.isfile(ICON):
    ICON = None

# ---------- 安全裁剪（按路径/文件名匹配，平台无关写法） ----------
# 本程序只用 QtWidgets，不用 QML/Quick/WebGL/EGL/打印/多媒体，故可删除
_DROP_KEYWORDS = [
    # 软件光栅化 / ANGLE（仅 Win，走原生显卡不需要）
    'opengl32sw', 'libglesv2', 'libegl', 'd3dcompiler',
    # QML / Quick 全家桶
    'qt5quick', 'qt5qml', 'qt5qmlmodels', 'qt5quickwidgets', 'qt5quickshapes',
    'qt5quickparticles', 'qt5quicktemplates2', 'qt5quickcontrols2',
    # 网络/打印/SQL/多媒体/传感器
    'qt5network', 'qt5printsupport', 'qt5sql', 'qt5multimedia',
    'qt5multimediawidgets', 'qt5sensors', 'qt5websockets', 'qt5webchannel',
    'qt5webengine', 'qt5webview', 'qt5positioning', 'qt5serialport',
    'qt5test', 'qt5help',
    # 用不到的平台插件（qwindows / xcb 保留，由白名单兜底）
    'qminimal', 'qoffscreen', 'qwebgl',
    # 用不到的图像格式（png/jpg/gif/bmp/ico 由 Qt 内建或保留）
    '/imageformats/qtiff', '/imageformats/qwebp', '/imageformats/qpdf',
    '/imageformats/qsvg',
    # Qt 翻译文件（本软件界面为中文且自带文案）
    '/translations/',
    # bearer 网络连接插件（随 Qt5Network 一起无用）
    '/bearer/',
    # tkinter 运行时（Linux 已注入 mouseinfo 空壳，不需要真 tk）
    'tcl86', 'tk86', '/tcl/', '/tk/', '/tkinter',
]

# PIL：pyautogui 截图只用核心，可删各种编解码器扩展
_DROP_PIL = ['_avif', '_webp', '_tiff', '_imagingft', '_imagingmath',
             '_imagingcms', '_imagingtk', '_psd', '_jpeg2k', '_xcb',
             '_freetype', '_lcms', '_tkinter_finder']

# 平台插件白名单：这些即使名字命中规则也绝不能删（xcb 是 Linux 命脉）
_KEEP_SUBSTR = ['/platforms/qwindows', '/platforms/libqxcb', '/platforms/qxcb']


def _is_dropped(dest):
    low = dest.replace('\\', '/').lower()
    if any(k in low for k in _KEEP_SUBSTR):
        return False
    if '/pil/' in low:
        base = low.rsplit('/', 1)[-1]
        if any(base.startswith(tok) for tok in _DROP_PIL):
            return True
    return any(tok in low for tok in _DROP_KEYWORDS)


_excludes = ['tkinter', 'unittest', 'lib2to3', 'test',
             'PyQt5.QtQml', 'PyQt5.QtQuick', 'PyQt5.QtQuickWidgets',
             'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets',
             'PyQt5.QtMultimedia', 'PyQt5.QtSql', 'PyQt5.QtNetwork',
             'PyQt5.QtSensors', 'PyQt5.QtPrintSupport']
if not IS_WIN:
    # Linux 不再使用 pynput，整体排除（Windows 暂保留）
    _excludes += ['pynput']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_excludes,
    noarchive=False,
)

before = len(a.binaries) + len(a.datas)
a.binaries = [t for t in a.binaries if not _is_dropped(t[0])]
a.datas = [t for t in a.datas if not _is_dropped(t[0])]
removed = before - len(a.binaries) - len(a.datas)
print('[spec] 裁剪移除 %d 个文件（保留 qwindows/xcb 平台插件）' % removed)

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
