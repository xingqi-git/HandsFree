# 程序入口
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
# 打包命令：pyinstaller -F -w main.py --upx-dir ../upx-5.1.1/upx.exe

def main():
    if sys.platform.startswith('linux'):
        # Linux桌面环境适配
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
    app = QApplication(sys.argv)
    app.setApplicationName("HandsFree")
    app.setApplicationVersion("1.0.0")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()