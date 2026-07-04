from PyQt5.QtWidgets import (QMainWindow, QWidget,
                             QVBoxLayout, QSplitter, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import ctypes
from ctypes import wintypes
from .script_panel import ScriptPanel
from .edit_area import ScriptEditArea
from .operation_panel import OperationPanel
from .run_bar import RunBar
from core.script_engine import ScriptEngine
import os, json

# Windows API 常量
WM_HOTKEY = 0x0312
VK_F9 = 0x78
VK_F10 = 0x79


class GlobalHotkeyThread(QThread):
    """全局热键监听线程"""
    f10_pressed = pyqtSignal()
    f9_pressed = pyqtSignal()
    register_result = pyqtSignal(bool, bool)  # f10_success, f9_success

    def run(self):
        # 注册热键（不绑定窗口句柄，使用None表示线程消息队列）
        f10_success = ctypes.windll.user32.RegisterHotKey(None, 1, 0, VK_F10)
        f9_success = ctypes.windll.user32.RegisterHotKey(None, 2, 0, VK_F9)
        
        # 发送注册结果
        self.register_result.emit(f10_success, f9_success)
        
        try:
            msg = wintypes.MSG()
            # 使用GetMessageW阻塞等待消息，这样更可靠
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == WM_HOTKEY:
                    if msg.wParam == 1:
                        self.f10_pressed.emit()
                    elif msg.wParam == 2:
                        self.f9_pressed.emit()
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if f10_success:
                ctypes.windll.user32.UnregisterHotKey(None, 1)
            if f9_success:
                ctypes.windll.user32.UnregisterHotKey(None, 2)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandsFree")
        self.setMinimumSize(500, 500)

        # 核心运行引擎
        self.script_engine = ScriptEngine()

        # 中心布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 标题栏
        title = QLabel("HandsFree")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        # 三栏分割器
        mid_splitter = QSplitter(Qt.Horizontal)
        mid_splitter.setHandleWidth(2)

        # 初始化三个核心面板
        self.script_panel = ScriptPanel()
        self.edit_area = ScriptEditArea()
        self.operation_panel = OperationPanel()

        mid_splitter.addWidget(self.script_panel)
        mid_splitter.addWidget(self.edit_area)
        mid_splitter.addWidget(self.operation_panel)
        mid_splitter.setStretchFactor(0, 2)
        mid_splitter.setStretchFactor(1, 3)
        mid_splitter.setStretchFactor(2, 1)
        main_layout.addWidget(mid_splitter, stretch=1)  # 设置拉伸因子

        # 底部运行栏
        self.run_bar = RunBar()
        main_layout.addWidget(self.run_bar)

        # 信号槽连接
        self._connect_signals()

        # 初始化热键
        self._init_shortcuts()

        self._load_scripts()

    def _connect_signals(self):
        # 脚本管理信号
        # self.script_panel.script_selected.connect(self.edit_area.load_script_content)
        self.script_panel.load_script.connect(self.edit_area.load_script_content)
        # 内容编辑：编辑区告诉面板更新数据
        self.edit_area.content_changed.connect(self.script_panel.update_current_script)
        # 操作插入信号
        self.operation_panel.operation_inserted.connect(self.edit_area.insert_operation_line)
        self.operation_panel.coordinate_picked.connect(self.edit_area.insert_mouse_move_line)
        # 运行控制信号
        self.run_bar.start_run.connect(self._start_script_run)
        self.run_bar.stop_run.connect(self._stop_script_run)
        # 引擎运行反馈
        self.script_engine.run_finished.connect(self._on_run_finished)
        self.script_engine.run_error.connect(self._on_run_error)

    def _init_shortcuts(self):
        """初始化全局热键（使用独立线程监听系统级热键）"""
        self.hotkey_thread = GlobalHotkeyThread(self)
        self.hotkey_thread.f10_pressed.connect(self._on_f10_start)
        self.hotkey_thread.f9_pressed.connect(self._stop_script_run)
        self.hotkey_thread.register_result.connect(self._on_hotkey_registered)
        self.hotkey_thread.start()

    def _on_hotkey_registered(self, f10_success, f9_success):
        """处理热键注册结果"""
        failed_keys = []
        if f10_success:
            self.run_bar.set_hotkey_hint(start_hotkey="F10")
        else:
            failed_keys.append("F10")
        
        if f9_success:
            self.run_bar.set_hotkey_hint(stop_hotkey="F9")
        else:
            failed_keys.append("F9")
        
        if failed_keys:
            # 有热键注册失败，弹出提示
            msg = QMessageBox(QMessageBox.Warning, "热键冲突", 
                              f"热键 {', '.join(failed_keys)} 注册失败，可能被其他程序占用。\n\n将无法使用对应热键功能。",
                              QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()

    def _on_f10_start(self):
        """F10热键触发开始运行"""
        # 直接触发运行栏的开始运行信号
        self.run_bar.start_run.emit(self.run_bar.get_run_count())

    def _start_script_run(self, run_count):
        script_content = self.edit_area.toPlainText().strip()
        if not script_content:
            msg = QMessageBox(QMessageBox.Warning, "警告", "脚本内容为空，无法运行！", QMessageBox.Ok, self)
            msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
            msg.exec_()
            return
        # 弹出确认提示框，询问是否执行脚本（置顶显示）
        msg_box = QMessageBox(QMessageBox.Question, "执行确认", 
                             "我已经检查了停止条件，确认要执行",
                             QMessageBox.Yes | QMessageBox.No, self)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
        reply = msg_box.exec_()

        # 判断选择：只有点击“是”才继续执行
        if reply != QMessageBox.Yes:
            return

        self.run_bar.set_running_state(True)
        self.showMinimized()  # 运行开始时最小化窗口
        self.script_engine.set_script(script_content)
        self.script_engine.set_run_count(run_count)
        self.script_engine.start()

    def _stop_script_run(self):
        self.script_engine.stop()
        self.run_bar.set_running_state(False)
        self.showNormal()  # 手动停止时恢复窗口
        self.activateWindow()  # 激活窗口到前端

    def _on_run_finished(self):
        self.run_bar.set_running_state(False)
        self.showNormal()  # 运行完成时恢复窗口
        self.activateWindow()  # 激活窗口到前端
        # 置顶显示提示框
        msg = QMessageBox(QMessageBox.Information, "提示", "脚本运行完成！", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec_()

    def _on_run_error(self, error_msg):
        self.run_bar.set_running_state(False)
        self.showNormal()  # 运行出错时恢复窗口
        self.activateWindow()  # 激活窗口到前端
        # 置顶显示错误提示
        msg = QMessageBox(QMessageBox.Critical, "错误", f"脚本运行出错：{error_msg}", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec_()

    def _load_scripts(self):
        """从当前目录加载脚本"""
        if not os.path.exists("handsfree_scripts.json"):
            return
        try:
            with open("handsfree_scripts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            script_dict = data.get("scripts", {})
            script_counter = data.get("counter", 1)
            self.script_panel.load_scripts(script_dict, script_counter)
        except Exception as e:
            print(f"加载脚本失败: {e}")

    def _save_scripts(self):
        """保存脚本到当前目录"""
        script_dict, script_counter = self.script_panel.get_all_scripts()
        data = {
            "scripts": script_dict,
            "counter": script_counter
        }
        try:
            with open("handsfree_scripts.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存脚本失败: {e}")

    def closeEvent(self, event):
        """重写关闭事件，停止热键线程并保存"""
        # 停止热键线程（terminate会立即终止，finally块会执行注销）
        self.hotkey_thread.terminate()
        self.hotkey_thread.wait()
        self._save_scripts()
        event.accept()