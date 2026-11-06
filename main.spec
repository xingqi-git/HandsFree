# -*- coding: utf-8 -*-
# =============================================================
# HandsFree 打包配置（Windows / Linux 通用）
# 打包命令：pyinstaller main.spec --clean
#
# 特性：
#   - 单文件、无控制台，产物名 HandsFree（.exe / 无后缀）
#   - UPX 自动探测：PATH -> UPX_DIR 环境变量 -> Windows 常见安装目录
#     找不到时自动降级为不压缩（打印警告，不中断打包）
#   - 精简：排除未使用的 PyQt5 模块、Qt 翻译文件、QML/WebEngine 残留、
#     非必需的 imageformats/iconengines 插件
#   - pynput/pyautogui 的平台后端为延迟导入，需显式 hiddenimports
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
    # 1. PATH 中查找
    found = shutil.which('upx')
    if found:
        return os.path.dirname(found)
    # 2. UPX_DIR 环境变量
    d = os.environ.get('UPX_DIR')
    if d:
        cand = os.path.join(d, 'upx.exe' if IS_WIN else 'upx')
        if os.path.isfile(cand):
            return d
    # 3. Windows 常见安装位置
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
    # PyInstaller 从 PATH 查找 upx，把找到的目录插到最前面
    os.environ['PATH'] = UPX_DIR + os.pathsep + os.environ.get('PATH', '')
    print('[spec] UPX: %s' % UPX_DIR)
else:
    print('[spec] 警告: 未找到 UPX，本次打包不压缩'
          '（Linux 服务器可: apt install upx-ucl）')
USE_UPX = UPX_DIR is not None

# Windows 下这些 DLL 压缩后可能引发崩溃/杀软误报，不参与 UPX
UPX_EXCLUDE = ['vcruntime140.dll', 'vcruntime140_1.dll']

# Linux 上对 .so 做 strip（很多发行版 .so 带完整符号表，可减 10-30%）
USE_STRIP = (not IS_WIN) and shutil.which('strip') is not None

# ---------- 依赖裁剪 ----------
excludes = [
    # 标准库中本项目用不到的大块
    'tkinter', 'unittest', 'pydoc_data', 'distutils', 'lib2to3',
    # PyQt5 中未使用的模块（本项目只用 QtCore/QtGui/QtWidgets）
    'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtQml', 'PyQt5.QtQuick', 'PyQt5.QtQuickWidgets', 'PyQt5.QtQuick3D',
    'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets',
    'PyQt5.QtNetwork', 'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtSvg',
    'PyQt5.QtXml', 'PyQt5.QtBluetooth', 'PyQt5.QtNfc', 'PyQt5.QtPositioning',
    'PyQt5.QtLocation', 'PyQt5.QtSensors', 'PyQt5.QtSerialPort',
    'PyQt5.QtTextToSpeech', 'PyQt5.QtDBus', 'PyQt5.QtDesigner', 'PyQt5.QtHelp',
    'PyQt5.QtOpenGL', 'PyQt5.QtPdf', 'PyQt5.QtPrintSupport',
]

# ---------- 延迟导入的平台后端 ----------
hiddenimports = ['pyperclip', 'pynput', 'pynput.keyboard', 'pynput.mouse']
if IS_WIN:
    hiddenimports += ['pyautogui._pyautogui_win',
                      'pynput.keyboard._win32', 'pynput.mouse._win32']
else:
    hiddenimports += ['pyautogui._pyautogui_x11',
                      'pynput.keyboard._x11', 'pynput.mouse._x11']

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
    excludes=excludes,
    noarchive=False,
)


# ---------- 二进制/资源二次裁剪 ----------
# 纯 Widgets 应用用不到的组件，按文件名（去扩展名小写）前缀匹配删除
DROP_BINARIES = (
    # OpenGL / ANGLE / 软件 GL：Qt 为动态 GL 构建，纯光栅界面不加载
    'opengl32sw', 'd3dcompiler_47', 'libegl', 'libglesv2',
    'qt5opengl', 'libqt5opengl',
    # QML/Quick 全家桶（由 qwebgl 平台插件牵入）
    # 注意 Linux 库名带 lib 前缀（libQt5Quick.so.5），两种写法都要匹配
    'qt5quick', 'libqt5quick', 'qt5qml', 'libqt5qml',
    'qt5websockets', 'libqt5websockets',
    # PIL 中本项目用不到的扩展及配套库（pyscreeze 截图只需 _imaging/_grab）
    '_avif', 'libavif', '_webp', 'libwebp',
    '_imagingft', 'freetype', '_imagingcms', '_imagingtk', '_imagingmorph',
)


def _keep(item):
    """True=保留。过滤翻译文件、非当前平台插件、无用 Qt 组件"""
    name = item[0].replace('\\', '/').lower()
    base = os.path.splitext(os.path.basename(name))[0].lower()
    if '/translations/' in name:
        return False
    for bad in ('webengine', '/qml/', 'designer'):
        if bad in name:
            return False
    # 平台插件只保留必需的一个（qminimal/qoffscreen/qwebgl 全砍）
    if '/platforms/' in name:
        return base in (('qwindows',) if IS_WIN else ('qxcb',))
    # GL 积分插件（Linux xcb 下只有 GL 渲染才需要）
    if 'glintegrations' in name:
        return False
    # imageformats 只保留最常用三种（PNG 由 QtGui 内建支持）
    if '/imageformats/' in name:
        return base in ('qgif', 'qico', 'qjpeg')
    # 本项目无 SVG 图标：去掉 iconengines 插件
    if '/iconengines/' in name:
        return False
    if base.startswith(DROP_BINARIES):
        return False
    return True


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

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
    upx=USE_UPX,
    upx_exclude=UPX_EXCLUDE,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
