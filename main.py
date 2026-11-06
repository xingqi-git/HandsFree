# 程序入口
import sys
import os
import tempfile
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# 打包命令：pyinstaller main.spec --clean（Windows/Linux 通用，UPX 自动探测）
# 注意：PyQt5 等所有导入都放在 main() 的 try 内，保证任何导入失败都能落盘日志

LOG_PATH = os.path.join(tempfile.gettempdir(), "handsfree_error.log")

def _log_fatal(msg: str):
    """致命错误写入日志文件（打包成窗口模式后 stderr 会被吞，必须落盘）"""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def main():
    import traceback
    sys.excepthook = lambda t, v, tb: _log_fatal(traceback.format_exception(t, v, tb))
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from PyQt5.QtCore import QLockFile
        from ui.main_window import MainWindow
        if sys.platform.startswith('linux'):
            # Linux桌面环境适配
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
        app = QApplication(sys.argv)
        app.setApplicationName("HandsFree")
        app.setApplicationVersion("1.0.0")

        # 单实例限制：已有实例运行时提示并退出
        lock = QLockFile(os.path.join(tempfile.gettempdir(), "HandsFree.lock"))
        if not lock.tryLock(100):
            QMessageBox.warning(None, "HandsFree", "HandsFree 已在运行中，请勿重复启动！")
            sys.exit(0)

        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception:
        tb = traceback.format_exc()
        _log_fatal(tb)
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "HandsFree 启动失败",
                                 "程序启动出错，日志已保存到：\n%s\n\n%s" % (LOG_PATH, tb[-1500:]))
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
