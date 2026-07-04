from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtCore import pyqtSignal, Qt


class ScriptEditArea(QTextEdit):
    content_changed = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setFont(QFont("SimHei", 12))
        self.setPlaceholderText("脚本编辑区域")
        self.setStyleSheet("QTextEdit {border: 1px solid #000; background: #fff;}")
        self.textChanged.connect(lambda: self.content_changed.emit(self.toPlainText()))

    def load_script_content(self, content):
        self.blockSignals(True)
        self.setPlainText(content)
        self.blockSignals(False)

    def insert_operation_line(self, operation_text):
        cursor = self.textCursor()
        # 获取当前行内容
        cursor.select(QTextCursor.LineUnderCursor)
        current_line = cursor.selectedText().strip()
        
        if not current_line:
            # 当前行为空，直接插入到当前行
            cursor.insertText(operation_text)
        else:
            # 当前行有内容，插入到下一行
            cursor.movePosition(QTextCursor.EndOfLine)
            cursor.insertText(f"\n{operation_text}")
        self.setTextCursor(cursor)

    def insert_mouse_move_line(self, x, y):
        self.insert_operation_line(f"鼠标移动到({x},{y})")