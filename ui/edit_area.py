from PyQt5.QtWidgets import QPlainTextEdit, QWidget
from PyQt5.QtGui import QFont, QTextCursor, QPainter, QColor
from PyQt5.QtCore import pyqtSignal, Qt, QSize


class _LineNumberArea(QWidget):
    """行号绘制区域"""
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_width(), 0)

    def paintEvent(self, event):
        self._editor.paint_line_numbers(event)


class ScriptEditArea(QPlainTextEdit):
    content_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._line_area = _LineNumberArea(self)
        self._init_ui()
        self._connect_line_number_signals()

    def _init_ui(self):
        self.setFont(QFont("SimHei", 12))
        self.setPlaceholderText("脚本编辑区域")
        self.setStyleSheet("QPlainTextEdit {border: 1px solid #000; background: #fff;}")
        self.textChanged.connect(lambda: self.content_changed.emit(self.toPlainText()))
        self._update_line_number_width()

    def _connect_line_number_signals(self):
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._line_area.update)

    def line_number_width(self):
        """根据最大行数计算行号栏宽度"""
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits

    def _update_line_number_width(self, _new_block_count=0):
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(cr.left(), cr.top(), self.line_number_width(), cr.height())

    def paint_line_numbers(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor(245, 245, 245))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        offset = self.contentOffset()
        top = round(self.blockBoundingGeometry(block).translated(offset).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current_line = self.textCursor().blockNumber() + 1
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_no = block_number + 1
                # 当前行高亮显示
                painter.setPen(QColor(0, 120, 215) if line_no == current_line else QColor(150, 150, 150))
                painter.drawText(0, top, self._line_area.width() - 6,
                                 self.fontMetrics().height(), Qt.AlignRight, str(line_no))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def load_script_content(self, content):
        self.blockSignals(True)
        self.setPlainText(content)
        self.blockSignals(False)
        # blockSignals 会拦截 blockCountChanged，手动刷新行号栏
        self._update_line_number_width()
        self._line_area.update()

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
