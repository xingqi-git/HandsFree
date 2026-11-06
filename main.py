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
