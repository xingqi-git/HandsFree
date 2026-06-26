from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import pyqtSignal, Qt, QObject
from PyQt6.QtGui import QFont, QPainter, QColor, QPen


class ScreenMaskWidget(QWidget):
    picked = pyqtSignal(int, int)
    canceled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        # 设置全屏无边框窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # 设置窗口透明度效果
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 全屏显示
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        # 设置鼠标追踪
        self.setMouseTracking(True)
        # 设置光标样式
        self.setCursor(Qt.CursorShape.CrossCursor)

        # 创建坐标提示标签
        self.tip_label = QLabel(self)
        self.tip_label.setFont(QFont("SimHei", 11))
        self.tip_label.setStyleSheet("""
            color: white; 
            background: rgba(0,0,0,200); 
            padding: 6px 10px; 
            border-radius: 4px;
        """)
        self.tip_label.setText("左键确认坐标 | 右键取消")
        self.tip_label.adjustSize()

    def paintEvent(self, event):
        # 绘制半透明遮罩
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

    def mouseMoveEvent(self, event):
        # 更新提示标签位置
        pos = event.position()
        x, y = int(pos.x()), int(pos.y())
        self.tip_label.setText(f"坐标: ({x}, {y})\n左键确认 | 右键取消")
        self.tip_label.adjustSize()
        # 将标签放在鼠标右下方，避免遮挡
        self.tip_label.move(x + 20, y + 20)

    def mousePressEvent(self, event):
        pos = event.position()
        x, y = int(pos.x()), int(pos.y())
        if event.button() == Qt.MouseButton.LeftButton:
            # 左键确认坐标
            self.close()
            self.picked.emit(x, y)
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键取消
            self.close()
            self.canceled.emit()

    def keyPressEvent(self, event):
        # ESC键取消
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.canceled.emit()


class CoordinatePicker(QObject):
    picked = pyqtSignal(int, int)
    canceled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.mask_widget = None

    def start_pick(self):
        self.mask_widget = ScreenMaskWidget()
        self.mask_widget.picked.connect(self._on_picked)
        self.mask_widget.canceled.connect(self._on_canceled)
        self.mask_widget.show()

    def _on_picked(self, x, y):
        self.mask_widget = None
        self.picked.emit(x, y)

    def _on_canceled(self):
        self.mask_widget = None
        self.canceled.emit()
