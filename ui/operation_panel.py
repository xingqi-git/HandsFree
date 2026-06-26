from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QMessageBox, QInputDialog, QDialog, QGridLayout
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QFont
from core.mouse_listener import CoordinatePicker


class OperationPanel(QWidget):
    operation_inserted = pyqtSignal(str)
    coordinate_picked = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.operation_list = [
            "移动到", "左键点击", "右键点击", "输入", "按下", "抬起",
            "键盘按键", "等待", "循环开始", "循环结束"
        ]
        # 常用按键映射
        self.key_map = {
            "回车": "enter", "Tab": "tab", "Shift": "shift", "Alt": "alt",
            "Ctrl": "ctrl", "Backspace": "backspace", "Delete": "delete",
            "PageUp": "pageup", "PageDown": "pagedown", "PrtSc": "printscreen",
            "↑": "up", "↓": "down", "←": "left", "→": "right",
            "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5", "F6": "f6",
            "F7": "f7", "F8": "f8", "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
            "Home": "home", "End": "end", "Insert": "insert", "Esc": "esc",
            "空格": "space"
        }
        self.loop_counter = 1
        self.loop_stack = []
        self.coordinate_picker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        for op_text in self.operation_list:
            btn = QPushButton(op_text)
            btn.setFont(QFont("SimHei", 14))
            btn.setFixedHeight(45)
            btn.setStyleSheet("""
                QPushButton {border: 1px solid #000; background: #f0f0f0;}
                QPushButton:hover {background: #e0e0e0;}
            """)
            btn.clicked.connect(lambda checked, t=op_text: self._on_op_clicked(t))
            layout.addWidget(btn)

        layout.addStretch()

    def _on_op_clicked(self, op_text):
        if op_text == "移动到":
            self._start_coord_pick()
        elif op_text == "等待":
            self._insert_wait()
        elif op_text == "输入":
            self._insert_input()
        elif op_text == "循环开始":
            self._insert_loop_start()
        elif op_text == "键盘按键":
            self._insert_key_press()
        elif op_text == "循环结束":
            self._insert_loop_end()
        else:
            self.operation_inserted.emit(op_text)

    def _start_coord_pick(self):
        if not self.coordinate_picker:
            self.coordinate_picker = CoordinatePicker()
            self.coordinate_picker.picked.connect(self._on_coord_picked)
            self.coordinate_picker.canceled.connect(self._on_pick_canceled)
        self.coordinate_picker.start_pick()

    def _on_coord_picked(self, x, y):
        self.coordinate_picked.emit(x, y)
        self.coordinate_picker = None

    def _on_pick_canceled(self):
        self.coordinate_picker = None

    def _insert_loop_start(self):
        loop_num = self.loop_counter
        count, ok = QInputDialog.getInt(self, "循环次数", f"请输入循环{loop_num}的次数:", min=1, value=10)
        if ok:
            self.loop_stack.append(loop_num)
            self.loop_counter += 1
            self.operation_inserted.emit(f"循环开始{loop_num}({count}次)")

    def _insert_wait(self):
        seconds, ok = QInputDialog.getInt(self, "等待时长", "请输入等待时长(秒):", min=1, value=1)
        if ok:
            self.operation_inserted.emit(f"等待({seconds}秒)")

    def _insert_input(self):
        text, ok = QInputDialog.getText(self, "输入内容", "请输入要输入的内容\n(提示: 数字后加{{+N}}表示递增, 如: 100{{+1}}abcd)")
        if ok and text:
            self.operation_inserted.emit(f"输入({text})")

    def _insert_loop_end(self):
        if not self.loop_stack:
            QMessageBox.warning(self, "警告", "无对应循环开始，无法插入结束循环")
            return
        loop_num = self.loop_stack.pop()
        self.operation_inserted.emit(f"结束循环{loop_num}")

    def _insert_key_press(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("选择按键")
        dialog.setFixedSize(400, 350)
        layout = QGridLayout(dialog)

        # 创建按键按钮
        keys = list(self.key_map.keys())
        row, col = 0, 0
        for key_name in keys:
            btn = QPushButton(key_name)
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, k=key_name: self._on_key_selected(dialog, k))
            layout.addWidget(btn, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        dialog.exec()

    def _on_key_selected(self, dialog, key_name):
        self.operation_inserted.emit(f"键盘按键({key_name})")
        dialog.accept()