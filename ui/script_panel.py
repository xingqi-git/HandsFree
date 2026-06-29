from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListWidget,
                             QListWidgetItem, QPushButton, QInputDialog, QMessageBox)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont


class ScriptPanel(QWidget):
    load_script = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.script_dict = {}
        self.script_counter = 1
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 脚本列表
        self.script_list = QListWidget()
        self.script_list.setFont(QFont("SimHei", 12))
        self.script_list.setStyleSheet("""
            QListWidget {border: 1px solid #000; background: #fff;}
            QListWidget::item {height: 30px; border-bottom: 1px solid #eee;}
            QListWidget::item:selected {background: #0078d7; color: white;}
        """)
        layout.addWidget(self.script_list)

        # 新建按钮
        self.add_btn = QPushButton("+")
        self.add_btn.setFont(QFont("SimHei", 12, QFont.Bold))
        self.add_btn.setFixedHeight(50)
        self.add_btn.setStyleSheet("""
            QPushButton {border: 1px solid #000; background: #f0f0f0;}
            QPushButton:hover {background: #e0e0e0;}
        """)
        layout.addWidget(self.add_btn)

        # 删除按钮
        self.del_btn = QPushButton("-")
        self.del_btn.setFont(QFont("SimHei", 12, QFont.Bold))
        self.del_btn.setFixedHeight(50)
        self.del_btn.setStyleSheet("""
            QPushButton {border: 1px solid #000; background: #f0f0f0;}
            QPushButton:hover {background: #e0e0e0;}
        """)
        layout.addWidget(self.del_btn)

        # 信号连接
        self.add_btn.clicked.connect(self.add_new_script)
        self.del_btn.clicked.connect(self._on_delete_script)
        self.script_list.currentItemChanged.connect(self._on_script_selected)
        self.script_list.itemChanged.connect(self._on_item_renamed)

    def add_new_script(self):
        # 弹出输入对话框
        default_name = f"脚本{self.script_counter}"
        script_name, ok = QInputDialog.getText(self, "新建脚本", "请输入脚本名称:", text=default_name)
        if not ok or not script_name.strip():
            return

        script_name = script_name.strip()

        # 查重
        if script_name in self.script_dict:
            QMessageBox.warning(self, "警告", f"脚本名称 '{script_name}' 已存在，请使用其他名称！")
            return

        self.script_counter += 1
        self.script_dict[script_name] = ""

        item = QListWidgetItem(script_name)
        item.setTextAlignment(Qt.AlignCenter)

        # 把初始名称存到item的Data里，作为唯一标识
        item.setData(Qt.UserRole, script_name)
        # 开启编辑权限
        item.setFlags(item.flags() | Qt.ItemIsEditable)

        # 阻塞信号，避免初始化时触发itemChanged
        self.script_list.blockSignals(True)
        self.script_list.addItem(item)
        self.script_list.setCurrentItem(item)
        self.script_list.blockSignals(False)

    def _on_delete_script(self):
        current_item = self.script_list.currentItem()
        if not current_item:
            return

        script_name = current_item.text()
        # 确认删除提示
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除脚本 '{script_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 使用UserRole中存储的原始名称作为key
        script_key = current_item.data(Qt.UserRole)
        if script_key in self.script_dict:
            del self.script_dict[script_key]

        # 移除列表项
        row = self.script_list.row(current_item)
        self.script_list.takeItem(row)

        # 选中相邻的项（如果还有的话）
        if self.script_list.count() > 0:
            self.script_list.setCurrentRow(max(0, row - 1))

    def _on_script_selected(self, current):
        # # 保存上一个脚本的内容
        # if previous:
        #     self.script_dict[previous.text()] = self.parent().parent().edit_area.toPlainText()
        # # 加载当前脚本
        # if current:
        #     script_name = current.text()
        #     self.script_selected.emit(script_name, self.script_dict[script_name])

        if current:
            script_name = current.text()
            self.load_script.emit(self.script_dict[script_name])

    def _on_item_renamed(self, item):
        new_name = item.text().strip()
        # 从Data里取出修改前的旧名称（绝对可靠）
        old_name = item.data(Qt.UserRole)

        # 如果名称为空，恢复为旧名称
        if not new_name:
            item.setText(old_name)
            return

        # 如果名称没有变化，不处理
        if old_name == new_name:
            return

        # 查重
        if new_name in self.script_dict:
            QMessageBox.warning(self, "警告", f"脚本名称 '{new_name}' 已存在，请使用其他名称！")
            item.setText(old_name)  # 恢复为旧名称
            return

        # 只有名称真的变了且不重复才处理
        if old_name and old_name in self.script_dict:
            # 1. 从字典弹出旧Key，存入新Key
            content = self.script_dict.pop(old_name)
            self.script_dict[new_name] = content
            # 2. 更新item的Data为新名称，方便下次修改
            item.setData(Qt.ItemDataRole.UserRole, new_name)

    def update_current_script(self, content):
        current_item = self.script_list.currentItem()
        if current_item:
            self.script_dict[current_item.text()] = content

    def get_all_scripts(self):
        """获取所有脚本字典，供保存用"""
        return self.script_dict, self.script_counter

    def load_scripts(self, script_dict, script_counter):
        """加载脚本字典，重建列表"""
        self.script_dict = script_dict
        self.script_counter = script_counter
        self.script_list.clear()

        for name in self.script_dict:
            item = QListWidgetItem(name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, name)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.script_list.addItem(item)

        if self.script_list.count() > 0:
            self.script_list.setCurrentRow(0)