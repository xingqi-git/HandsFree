# 程序入口
import sys
import os
import tempfile
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QLockFile
from ui.main_window import MainWindow
# 打包命令：pyinstaller main.spec --clean（Windows/Linux 通用，UPX 自动探测）

def main():
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

if __name__ == "__main__":
    main()
