from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QSplitter, 
                             QLabel, QMessageBox, QMenuBar, QDialog, 
                             QTextEdit, QPushButton, QVBoxLayout, QShortcut)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QKeySequence
from .script_panel import ScriptPanel
from .edit_area import ScriptEditArea
from .operation_panel import OperationPanel
from .run_bar import RunBar
from core.script_engine import ScriptEngine
import os, json, sys, platform

# 平台判断
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# Windows API 常量（仅 Windows 使用）
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    WM_HOTKEY = 0x0312
    VK_F9 = 0x78
    VK_F10 = 0x79


class HelpDialog(QDialog):
    """使用说明对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用说明")
        self.setMinimumSize(700, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建文本编辑器用于显示帮助内容
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml(self.get_help_content())
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(100)
        
        layout.addWidget(help_text)
        layout.addWidget(close_btn, 0, Qt.AlignCenter)
    
    def get_help_content(self):
        """获取帮助内容"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: "Microsoft YaHei", sans-serif; font-size: 14px; line-height: 1.6; }
                h1 { color: #2c3e50; font-size: 24px; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                h2 { color: #34495e; font-size: 18px; margin-top: 20px; }
                h3 { color: #7f8c8d; font-size: 16px; margin-top: 15px; }
                .code { background-color: #f8f9fa; padding: 2px 8px; border-radius: 4px; font-family: Consolas, monospace; }
                .hotkey { background-color: #e3f2fd; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
                ul { margin: 8px 0; padding-left: 20px; }
                li { margin: 5px 0; }
                .warning { color: #e74c3c; font-weight: bold; }
                .note { color: #f39c12; font-style: italic; }
            </style>
        </head>
        <body>
            <h1>🛠️ HandsFree 使用说明</h1>
            
            <h2>📋 软件简介</h2>
            <p>HandsFree 是一款自动化脚本执行工具，类似"按键精灵"，可以帮助您自动执行重复的鼠标和键盘操作，提高工作效率。</p>
            
            <h2>📝 界面布局</h2>
            <p>软件界面分为三个主要区域：</p>
            <ul>
                <li><strong>左侧 - 脚本列表</strong>：管理您的所有自动化脚本</li>
                <li><strong>中间 - 脚本编辑区</strong>：编写和编辑脚本内容</li>
                <li><strong>右侧 - 操作面板</strong>：快速插入常用操作命令</li>
                <li><strong>底部 - 运行控制栏</strong>：设置运行次数，控制脚本启停</li>
            </ul>
            
            <h2>📁 脚本管理</h2>
            
            <h3>创建新脚本</h3>
            <ul>
                <li>点击左侧脚本列表下方的 <span class="code">+</span> 按钮</li>
                <li>输入脚本名称（如"自动签到"、"重复点击"等）</li>
                <li>点击确定后，新脚本会出现在列表中</li>
            </ul>
            
            <h3>重命名脚本</h3>
            <ul>
                <li>双击脚本名称进入编辑状态</li>
                <li>输入新名称</li>
                <li>按回车键确认或点击其他位置取消</li>
            </ul>
            
            <h3>删除脚本</h3>
            <ul>
                <li>选中要删除的脚本</li>
                <li>点击 <span class="code">-</span> 按钮</li>
                <li>在确认对话框中点击"是"</li>
            </ul>
            
            <h3>切换脚本</h3>
            <ul>
                <li>点击列表中的脚本名称即可切换</li>
                <li>编辑内容会自动保存</li>
            </ul>
            
            <h2>✏️ 脚本编辑</h2>
            
            <h3>脚本语法</h3>
            <p>每行一条命令，支持以下命令：</p>
            <ul>
                <li><span class="code">等待 秒数</span> - 等待指定时间（支持小数）</li>
                <li><span class="code">鼠标移动到 x, y</span> - 移动鼠标到指定坐标</li>
                <li><span class="code">鼠标左键点击</span> - 单击鼠标左键</li>
                <li><span class="code">鼠标左键双击</span> - 双击鼠标左键</li>
                <li><span class="code">鼠标右键点击</span> - 单击鼠标右键</li>
                <li><span class="code">键盘输入 文本</span> - 输入指定文本</li>
                <li><span class="code">键盘按下 键名</span> - 按下键盘按键</li>
                <li><span class="code">键盘松开 键名</span> - 松开键盘按键</li>
                <li><span class="code">键盘按键 键名</span> - 按一下键盘按键（按下并松开）</li>
            </ul>
            
            <h3>示例脚本</h3>
            <pre style="background-color: #f8f9fa; padding: 10px; border-radius: 4px;">
等待 1.5
鼠标移动到 100, 200
鼠标左键点击
等待 0.5
键盘输入 Hello, World!
键盘按下 ctrl
键盘按键 s
键盘松开 ctrl
            </pre>
            
            <h3>注释</h3>
            <p>以 <span class="code">#</span> 开头的行将被视为注释，不会执行。</p>
            
            <h2>🎮 操作面板</h2>
            
            <h3>快速插入操作</h3>
            <p>点击右侧操作面板中的按钮，可以快速插入常用操作命令：</p>
            <ul>
                <li><strong>等待</strong> - 插入等待命令</li>
                <li><strong>鼠标移动</strong> - 获取鼠标坐标并插入</li>
                <li><strong>鼠标左键点击</strong> - 插入左键点击命令</li>
                <li><strong>鼠标左键双击</strong> - 插入双击命令</li>
                <li><strong>鼠标右键点击</strong> - 插入右键点击命令</li>
                <li><strong>键盘输入</strong> - 插入文本输入命令</li>
                <li><strong>键盘按下/松开</strong> - 插入键盘按键操作</li>
            </ul>
            
            <h3>获取鼠标坐标</h3>
            <p>点击"鼠标移动"按钮后：</p>
            <ul>
                <li>屏幕会显示十字准线</li>
                <li>移动鼠标到目标位置</li>
                <li>点击鼠标左键确认坐标</li>
                <li>按鼠标右键或 ESC 键取消</li>
            </ul>
            
            <h2>▶️ 运行控制</h2>
            
            <h3>设置运行次数</h3>
            <ul>
                <li>在底部运行栏的"运行次数"输入框中输入数字</li>
                <li>默认运行 1 次</li>
                <li>设置为 0 表示无限循环（需要手动停止）</li>
            </ul>
            
            <h3>开始运行</h3>
            <ul>
                <li>点击 <span class="code">开始运行</span> 按钮</li>
                <li>在确认对话框中点击"是"</li>
                <li>软件会自动最小化并开始执行脚本</li>
            </ul>
            
            <h3>停止运行</h3>
            <ul>
                <li>点击 <span class="code">停止运行</span> 按钮</li>
                <li>脚本会在当前循环执行完毕后停止</li>
            </ul>
            
            <h2>⌨️ 全局热键</h2>
            <p>即使窗口最小化也能使用热键控制：</p>
            <ul>
                <li><span class="hotkey">F10</span> - 开始运行脚本</li>
                <li><span class="hotkey">F9</span> - 停止运行脚本</li>
            </ul>
            
            <p class="note">注意：如果热键被其他程序占用，会弹出提示窗口告知。</p>
            
            <h2>💾 数据保存</h2>
            <ul>
                <li>脚本数据自动保存在软件同级目录的 <span class="code">handsfree_scripts.json</span> 文件中</li>
                <li>关闭软件时自动保存</li>
                <li>重新打开软件时会自动加载之前的脚本</li>
            </ul>
            
            <h2>⚠️ 注意事项</h2>
            <ul>
                <li><span class="warning">运行脚本前请确保已检查停止条件！</span></li>
                <li>建议先用简单脚本测试，熟悉功能后再用于重要操作</li>
                <li>无限循环模式下请牢记 F9 停止热键</li>
                <li>脚本运行时不要手动操作鼠标键盘可能影响执行效果</li>
                <li>不同屏幕分辨率变化时，鼠标坐标可能需要重新获取</li>
            </ul>
            
            <h2>💡 使用技巧</h2>
            <ul>
                <li>录制重复操作时，建议在每个操作之间添加适当的等待时间</li>
                <li>对于需要精确点击的场景，建议移动鼠标后等待 0.5-1 秒再点击</li>
                <li>复杂操作可以拆分成多个脚本，分别测试通过后再合并</li>
                <li>使用注释记录脚本用途和注意事项</li>
            </ul>
            
            <h2>❓ 常见问题</h2>
            
            <h3>Q: 脚本运行时如何停止？</h3>
            <p>A: 点击停止按钮或按 F9 热键。脚本会在完成当前循环后停止。</p>
            
            <h3>Q: 鼠标坐标怎么获取？</h3>
            <p>A: 点击右侧操作面板的"鼠标移动"按钮，然后用鼠标点击目标位置即可。</p>
            
            <h3>Q: 支持哪些键盘按键？</h3>
            <p>A: 支持常用按键名称：ctrl, shift, alt, enter, space, tab, escape, 以及字母 a-z, 数字 0-9 等。</p>
            
            <h3>Q: 脚本保存在哪里？</h3>
            <p>A: 保存在软件同级目录的 handsfree_scripts.json 文件中，可以备份此文件。</p>
            
            <h3>Q: Linux 系统可以用吗？</h3>
            <p>A: 可以！HandsFree 支持 Windows 和 Linux 系统。</p>
            
            <hr>
            <p style="text-align: center; color: #7f8c8d; margin-top: 20px;">
                HandsFree v1.0<br>
                让双手解放出来，让效率提升起来！ 🚀
            </p>
        </body>
        </html>
        """


class GlobalHotkeyThread(QThread):
    """全局热键监听线程（跨平台）"""
    f10_pressed = pyqtSignal()
    f9_pressed = pyqtSignal()
    register_result = pyqtSignal(bool, bool)  # f10_success, f9_success

    def run(self):
        if IS_WINDOWS:
            self._run_windows()
        else:
            self._run_linux()

    def _run_windows(self):
        """Windows 平台：使用 ctypes + RegisterHotKey"""
        f10_success = ctypes.windll.user32.RegisterHotKey(None, 1, 0, VK_F10)
        f9_success = ctypes.windll.user32.RegisterHotKey(None, 2, 0, VK_F9)
        
        self.register_result.emit(f10_success, f9_success)
        
        try:
            msg = wintypes.MSG()
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

    def _run_linux(self):
        """Linux 平台：使用 pynput 监听全局快捷键"""
        try:
            from pynput import keyboard
        except ImportError:
            self.register_result.emit(False, False)
            return

        self.register_result.emit(True, True)
        
        def on_press(key):
            try:
                if key == keyboard.Key.f10:
                    self.f10_pressed.emit()
                elif key == keyboard.Key.f9:
                    self.f9_pressed.emit()
            except Exception:
                pass
        
        self._listener = keyboard.Listener(on_press=on_press)
        self._listener.start()
        self._listener.join()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandsFree")
        self.setMinimumSize(500, 500)

        # 核心运行引擎
        self.script_engine = ScriptEngine()

        # 创建菜单栏
        self._create_menu_bar()

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

    def _create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")
        
        # 使用说明动作
        help_action = help_menu.addAction("使用说明(&U)")
        help_action.triggered.connect(self._show_help)
        
        # 添加分隔线
        help_menu.addSeparator()
        
        # 关于动作
        about_action = help_menu.addAction("关于(&A)")
        about_action.triggered.connect(self._show_about)

    def _show_help(self):
        """显示使用说明对话框"""
        dialog = HelpDialog(self)
        dialog.exec_()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 HandsFree", 
            """<h3>HandsFree v1.0</h3>
            <p>自动化脚本执行工具</p>
            <p>让双手解放出来，让效率提升起来！</p>
            <p><br>支持平台：Windows / Linux</p>
            <p>开发：PyQt5 + pyautogui</p>""")

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
        """初始化快捷键（窗口级 + 全局热键）"""
        # 窗口级快捷键：当窗口有焦点时生效
        self.f10_shortcut = QShortcut(QKeySequence("F10"), self)
        self.f10_shortcut.activated.connect(lambda: self._start_script_run(self.run_bar.get_run_count()))
        
        self.f9_shortcut = QShortcut(QKeySequence("F9"), self)
        self.f9_shortcut.activated.connect(self._stop_script_run)
        
        # 全局热键线程（Windows / Linux X11）
        self.hotkey_thread = GlobalHotkeyThread(self)
        self.hotkey_thread.f10_pressed.connect(self._on_f10_start)
        self.hotkey_thread.f9_pressed.connect(self._stop_script_run)
        self.hotkey_thread.register_result.connect(self._on_hotkey_registered)
        self.hotkey_thread.start()

    def _on_hotkey_registered(self, f10_success, f9_success):
        """处理热键注册结果"""
        # 窗口级热键始终可用，先设置热键提示
        self.run_bar.set_hotkey_hint(start_hotkey="F10", stop_hotkey="F9")
        
        failed_keys = []
        if not f10_success:
            failed_keys.append("F10")
        if not f9_success:
            failed_keys.append("F9")
        
        if failed_keys:
            # 全局热键注册失败，弹出提示（但窗口级热键仍可用）
            msg = QMessageBox(QMessageBox.Warning, "提示", 
                              "全局热键注册失败。\n\n热键仅在窗口有焦点时可用。",
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

        # 判断选择：只有点击"是"才继续执行
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
        # 置顶显示手动停止提示
        msg = QMessageBox(QMessageBox.Information, "提示", "已手动停止脚本运行", QMessageBox.Ok, self)
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowStaysOnTopHint)
        msg.exec_()

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
        # 停止热键线程
        if IS_LINUX and hasattr(self.hotkey_thread, '_listener'):
            self.hotkey_thread._listener.stop()
        self.hotkey_thread.terminate()
        self.hotkey_thread.wait()
        self._save_scripts()
        event.accept()
