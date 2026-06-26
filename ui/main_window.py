from PyQt6.QtWidgets import (QMainWindow, QWidget,
                             QVBoxLayout, QSplitter, QLabel, QMessageBox)
from PyQt6.QtCore import Qt
from .script_panel import ScriptPanel
from .edit_area import ScriptEditArea
from .operation_panel import OperationPanel
from .run_bar import RunBar
from core.script_engine import ScriptEngine
import os, json


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
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        # 三栏分割器
        mid_splitter = QSplitter(Qt.Orientation.Horizontal)
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
        main_layout.addWidget(mid_splitter)

        # 底部运行栏
        self.run_bar = RunBar()
        main_layout.addWidget(self.run_bar)

        # 信号槽连接
        self._connect_signals()

        # 启动时加载脚本
        self._load_scripts()
        # 如果没有加载到任何脚本，才新建默认脚本1
        if self.script_panel.script_list.count() == 0:
            self.script_panel.add_new_script()

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

    def _start_script_run(self, run_count):
        script_content = self.edit_area.toPlainText().strip()
        if not script_content:
            QMessageBox.warning(self, "警告", "脚本内容为空，无法运行！")
            return
        # 弹出确认提示框，询问是否执行脚本
        reply = QMessageBox.question(
            self,  # 父窗口
            "执行确认",  # 提示框标题
            "我已经检查了停止条件，确认要执行",  # 提示内容
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,  # 按钮选项
            QMessageBox.StandardButton.No  # 默认选中“否”
        )

        # 判断选择：只有点击“是”才继续执行
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.run_bar.set_running_state(True)
        self.script_engine.set_script(script_content)
        self.script_engine.set_run_count(run_count)
        self.script_engine.start()

    def _stop_script_run(self):
        self.script_engine.stop()
        self.run_bar.set_running_state(False)

    def _on_run_finished(self):
        self.run_bar.set_running_state(False)
        QMessageBox.information(self, "提示", "脚本运行完成！")

    def _on_run_error(self, error_msg):
        self.run_bar.set_running_state(False)
        QMessageBox.critical(self, "错误", f"脚本运行出错：{error_msg}")

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
        """重写关闭事件，自动保存"""
        self._save_scripts()
        event.accept()