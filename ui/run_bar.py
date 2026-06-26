from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont, QIntValidator


class RunBar(QWidget):
    start_run = pyqtSignal(int)
    stop_run = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # 开始按钮
        self.start_btn = QPushButton("开始运行")
        self.start_btn.setFont(QFont("SimHei", 14))
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {border: 1px solid #000; background: #0078d7; color: white;}
            QPushButton:hover {background: #005a9e;}
            QPushButton:disabled {background: #808080;}
        """)
        layout.addWidget(self.start_btn)

        # 运行次数
        layout.addWidget(QLabel("运行次数", font=QFont("SimHei", 14)))
        self.run_count_edit = QLineEdit()
        self.run_count_edit.setFont(QFont("SimHei", 14))
        self.run_count_edit.setFixedWidth(150)
        self.run_count_edit.setPlaceholderText("空=无限循环")
        self.run_count_edit.setValidator(QIntValidator(0, 999999, self))
        layout.addWidget(self.run_count_edit)

        layout.addStretch()

        # 停止按钮
        self.stop_btn = QPushButton("停止运行")
        self.stop_btn.setFont(QFont("SimHei", 14))
        self.stop_btn.setFixedHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {border: 1px solid #000; background: #d83b01; color: white;}
            QPushButton:hover {background: #a42600;}
            QPushButton:disabled {background: #808080;}
        """)
        layout.addWidget(self.stop_btn)

        # 信号连接
        self.start_btn.clicked.connect(self._on_start_click)
        self.stop_btn.clicked.connect(self.stop_run)

    def _on_start_click(self):
        count_text = self.run_count_edit.text().strip()
        run_count = int(count_text) if count_text else 0
        self.start_run.emit(run_count)

    def set_running_state(self, is_running):
        self.start_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        self.run_count_edit.setEnabled(not is_running)