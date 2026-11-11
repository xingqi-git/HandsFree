# 程序入口
import sys
import os
import tempfile
import types
import traceback

# 应用目录：打包后取可执行文件所在目录，源码运行为脚本所在目录（禁止相对路径）
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(APP_DIR)

LOG_PATH = os.path.join(APP_DIR, "handsfree.log")


def _setup_logging():
    """日志同时写 handsfree.log 和终端"""
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logging.getLogger("handsfree")


log = _setup_logging()
log.info("========== HandsFree 启动 ==========")
log.info("sys.executable=%s", sys.executable)
log.info("APP_DIR=%s", APP_DIR)
log.info("platform=%s, DISPLAY=%s", sys.platform, os.environ.get("DISPLAY"))

# 拦截 sys.exit：第三方库（如 mouseinfo）可能静默 exit(1)，记录调用栈
_real_sys_exit = sys.exit
def _traced_exit(code=0):
    if code:
        log.error("sys.exit(%r) 被调用，调用栈:\n%s",
                  code, "".join(traceback.format_stack()))
    _real_sys_exit(code)
sys.exit = _traced_exit

# 未捕获异常写入日志
def _excepthook(etype, value, tb):
    log.error("未捕获异常:\n%s",
              "".join(traceback.format_exception(etype, value, tb)))
sys.excepthook = _excepthook

# 原生层段错误也输出到日志
try:
    import faulthandler
    _fh_log = open(LOG_PATH, "a", encoding="utf-8")
    faulthandler.enable(_fh_log)
except Exception as e:
    log.warning("faulthandler 启用失败: %s", e)

# Linux 上 mouseinfo 依赖 tkinter；无 tkinter 时 import mouseinfo 会 exit(1)。
# 本程序不使用鼠标坐标悬浮窗，用空壳替换，避免整个进程被拖死。
if sys.platform.startswith("linux"):
    try:
        import tkinter  # noqa: F401
    except Exception:
        log.warning("tkinter 不可用，注入 mouseinfo 空壳")
        _stub = types.ModuleType("mouseinfo")
        _stub.main = lambda *a, **k: None
        _stub.mouseInfo = lambda *a, **k: None
        sys.modules["mouseinfo"] = _stub


def _setup_linux_inputmethod():
    """
    统信等 Linux 桌面默认使用 fcitx，而 PyQt5 wheel/PyInstaller 只内置
    ibus/compose 插件且插件搜索被限制在包内，导致编辑区无法唤起输入法。
    做法：在系统 Qt 插件目录里找 fcitx/fcitx5/ibus 的 inputmethods 插件，
    建一个只含 inputmethods 的临时插件根目录并加入 QT_PLUGIN_PATH，
    同时设置 QT_IM_MODULE，让 Qt 加载系统输入法插件（不影响其他插件）。
    必须在创建 QApplication 之前调用。
    """
    import glob

    def _im_module():
        m = os.environ.get("QT_IM_MODULE")
        if m:
            return m
        # 探测当前运行的输入法守护进程
        found = ""
        try:
            procs = " ".join(os.listdir("/proc"))
        except Exception:
            procs = ""
        try:
            import subprocess
            out = subprocess.run(["pgrep", "-a", "fcitx"], capture_output=True,
                                 text=True, timeout=2).stdout
        except Exception:
            out = ""
        if "fcitx5" in out or os.path.isdir("/usr/lib/fcitx5"):
            found = "fcitx"
        elif "fcitx" in out or os.path.isdir("/usr/lib/fcitx"):
            found = "fcitx"
        elif "ibus-daemon" in out or procs and "ibus" in procs:
            found = "ibus"
        return found

    module = _im_module()
    if not module:
        log.info("未检测到 Linux 输入法模块，跳过输入法适配")
        return

    # 系统 Qt 插件搜索根（多架构目录都覆盖）
    roots = [
        "/usr/lib/qt/plugins", "/usr/lib/qt5/plugins",
        "/usr/lib/x86_64-linux-gnu/qt5/plugins",
        "/usr/lib64/qt5/plugins", "/usr/lib/qt/plugins/platforminputcontexts",
    ]
    # 插件名：fcitx 与 fcitx5 的插件都叫 libfcitxplatforminputcontextplugin.so
    want = module
    plugin_files = []
    for r in roots:
        for sub in ("inputmethods", "platforminputcontexts"):
            d = os.path.join(r, sub) if not r.endswith("platforminputcontexts") else r
            for so in glob.glob(os.path.join(d, "*.so")):
                base = os.path.basename(so).lower()
                hit = ((want.startswith("fcitx") and "fcitx" in base) or
                       (want == "ibus" and base.startswith("libibus")))
                if hit and so not in plugin_files:
                    plugin_files.append(so)

    if not plugin_files:
        log.warning("检测到输入法 %s 但未找到系统 Qt 输入法插件", module)
        os.environ.setdefault("QT_IM_MODULE", module)
        return

    tmp_root = tempfile.mkdtemp(prefix="hf-im-")
    im_dir = os.path.join(tmp_root, "platforminputcontexts")
    os.makedirs(im_dir, exist_ok=True)
    for src in plugin_files:
        link = os.path.join(im_dir, os.path.basename(src))
        try:
            os.symlink(src, link)
        except Exception:
            import shutil
            shutil.copy2(src, link)

    # Qt 从 QT_PLUGIN_PATH 额外搜索插件；只含 platforminputcontexts，不污染其他
    old = os.environ.get("QT_PLUGIN_PATH", "")
    os.environ["QT_PLUGIN_PATH"] = tmp_root + (os.pathsep + old if old else "")
    os.environ["QT_IM_MODULE"] = "fcitx" if module.startswith("fcitx") else "ibus"
    # 部分 fcitx 插件需要
    os.environ.setdefault("XMODIFIERS", "@im=fcitx" if module.startswith("fcitx") else "@im=ibus")
    log.info("Linux 输入法适配: module=%s, plugins=%s",
             os.environ["QT_IM_MODULE"], plugin_files)


log.info("开始导入依赖库...")
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QLockFile
log.info("PyQt5 导入完成")
from ui.main_window import MainWindow
log.info("业务模块导入完成")
# 打包命令：pyinstaller main.spec --clean（Windows/Linux 通用，UPX 自动探测）


def main():
    if sys.platform.startswith('linux'):
        # Linux桌面环境适配
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
        _setup_linux_inputmethod()
    log.info("创建 QApplication...")
    app = QApplication(sys.argv)
    app.setApplicationName("HandsFree")
    app.setApplicationVersion("1.0.0")

    # 单实例限制：已有实例运行时提示并退出
    lock = QLockFile(os.path.join(tempfile.gettempdir(), "HandsFree.lock"))
    if not lock.tryLock(100):
        log.warning("已有实例在运行，退出")
        QMessageBox.warning(None, "HandsFree", "HandsFree 已在运行中，请勿重复启动！")
        sys.exit(0)

    log.info("创建主窗口...")
    window = MainWindow()
    window.show()
    log.info("进入事件循环")
    exit_code = app.exec()
    log.info("事件循环结束, exit=%s", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
